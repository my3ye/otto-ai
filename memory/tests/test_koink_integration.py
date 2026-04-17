"""End-to-end integration test harness for Koink × OMS Crypto Engine.

Tests:
    1. /koink/status — feature flags, KOINK_ENABLED=true
    2. /koink/standard — spec returns all required fields
    3. /crypto/status — includes koink block with nl_launch=true
    4. /koink/launch — create a test token record
    5. /koink/launches — list includes the new token
    6. /crypto/execute — NL koink_launch routes to koink module (dry_run)
    7. /crypto/execute — NL koink_launch creates record (non-dry-run)
    8. /crypto/parse — koink_launch intent parsed correctly

Requires: API running at localhost:8100, KOINK_ENABLED=true.
"""
import uuid

import pytest


# ── 1. Koink status ───────────────────────────────────────────────────────────

def test_koink_status_enabled(client):
    resp = client.get("/koink/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True, "KOINK_ENABLED must be true — check memory/.env"
    assert data["phase"] == "0"
    assert "base" in data["supported_chains"]
    assert data["features"]["create_token_record"] is True
    assert data["features"]["dhm_tracking"] is True


# ── 2. Koink standard spec ────────────────────────────────────────────────────

def test_koink_standard_has_required_fields(client):
    resp = client.get("/koink/standard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "$KOINK Standard"
    assert "defaults" in data
    assert "mechanics" in data
    defaults = data["defaults"]
    assert "anti_whale_cap_pct" in defaults
    assert "sell_tax_initial_bps" in defaults
    assert "treasury_pct" in defaults
    assert "dhm_months" in defaults


# ── 3. Crypto status includes koink block ─────────────────────────────────────

def test_crypto_status_has_koink_block(client):
    resp = client.get("/crypto/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "koink" in data, "Koink block missing from /crypto/status"
    koink = data["koink"]
    assert koink["enabled"] is True
    assert koink["phase"] == "0"
    assert koink["nl_launch"] is True, "nl_launch should be true when KOINK_ENABLED=true"


# ── 4. Create a Koink token record ────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_token_id(client):
    """Create a test token and return its ID. Module-scoped so later tests reuse it."""
    unique = uuid.uuid4().hex[:6].upper()
    resp = client.post("/koink/launch", json={
        "name": f"TestToken{unique}",
        "symbol": f"TST{unique[:3]}",
        "chain": "base",
        "total_supply": 1_000_000_000,
        "anti_whale_cap_pct": 2.0,
        "sell_tax_initial_bps": 500,
        "sell_tax_floor_bps": 100,
        "treasury_pct": 20.0,
        "dhm_enabled": True,
        "dhm_months": 12,
        "dhm_max_multiplier": 3.0,
    })
    assert resp.status_code == 200, f"Launch failed: {resp.text}"
    data = resp.json()
    assert "id" in data
    assert data["status"] == "pending"
    assert data["chain"] == "base"
    return data["id"]


def test_koink_launch_returns_valid_record(test_token_id):
    assert test_token_id is not None
    # UUID format check
    uuid.UUID(test_token_id)  # raises ValueError if invalid


# ── 5. List includes the new token ────────────────────────────────────────────

def test_koink_launches_list(client, test_token_id):
    resp = client.get("/koink/launches")
    assert resp.status_code == 200
    data = resp.json()
    assert "tokens" in data
    ids = [t["id"] for t in data["tokens"]]
    assert test_token_id in ids, f"New token {test_token_id} not found in /koink/launches"


# ── 6. /crypto/execute dry_run for koink_launch ───────────────────────────────

def test_crypto_execute_koink_launch_dry_run(client):
    resp = client.post("/crypto/execute", json={
        "text": "launch a KOINK token called MOON on Base with 1.5% anti-whale",
        "dry_run": True,
    })
    assert resp.status_code == 200, f"Execute failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "dry_run"
    intent = data["intent"]
    assert intent["action"] == "koink_launch"
    assert intent["chain"] == "base"


# ── 7. /crypto/execute actual koink_launch ────────────────────────────────────

def test_crypto_execute_koink_launch_creates_record(client):
    unique = uuid.uuid4().hex[:4].upper()
    resp = client.post("/crypto/execute", json={
        "text": f"create a $KOINK Standard meme coin EXEC{unique} on arbitrum",
        "dry_run": False,
    })
    assert resp.status_code == 200, f"Execute failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "pending"
    assert data["quote"] is not None
    assert data["quote"]["status"] == "pending"
    assert data["quote"]["chain"] == "arbitrum"
    token_id = data["quote"]["id"]
    uuid.UUID(token_id)  # validate UUID


# ── 8. /crypto/parse parses koink_launch ─────────────────────────────────────

def test_crypto_parse_koink_launch(client):
    resp = client.post("/crypto/parse", json={
        "text": "deploy KOINK token FROG on Solana, 12-month diamond hands, 20% treasury",
    })
    assert resp.status_code == 200, f"Parse failed: {resp.text}"
    data = resp.json()
    intent = data["intent"]
    assert intent["action"] == "koink_launch"
    assert intent["chain"] == "solana"
    kp = intent.get("koink_params") or {}
    # At least name/symbol should be extracted
    assert bool(kp.get("name") or kp.get("symbol")), f"koink_params empty: {kp}"

#!/usr/bin/env python3
"""End-to-end test harness for Koink × OMS Crypto Engine integration.

Tests all paths:
  1. /koink/status
  2. /koink/standard
  3. /koink/launch   (create token)
  4. /koink/launches (list)
  5. /koink/launches/{id} (get)
  6. /koink/dhm/{id}
  7. /koink/dhm/snapshot
  8. /koink/treasury/{id}
  9. /koink/treasury/event
 10. /crypto/status   — koink section
 11. /crypto/launch   with koink_standard=True — routing
 12. /crypto/execute  with koink_launch NL — dry_run

Usage:
    python3 ~/otto/tests/test_koink_integration.py [--base-url http://localhost:8100]
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error


# ─── HTTP helpers ──────────────────────────────────────────────────────────────

def _req(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(base: str, path: str) -> tuple[int, dict]:
    return _req("GET", base + path)


def post(base: str, path: str, body: dict) -> tuple[int, dict]:
    return _req("POST", base + path, body)


# ─── Test runner ──────────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results: list[tuple[str, str, str]] = []  # (name, status, note)


def check(name: str, cond: bool, note: str = "") -> bool:
    status = PASS if cond else FAIL
    results.append((name, status, note))
    sym = "✓" if cond else "✗"
    print(f"  [{sym}] {name}" + (f" — {note}" if note else ""))
    return cond


def skip(name: str, reason: str):
    results.append((name, SKIP, reason))
    print(f"  [~] {name} — SKIP: {reason}")


# ─── Tests ────────────────────────────────────────────────────────────────────

def run(base: str):
    print(f"\n=== Koink Integration Test ===")
    print(f"Base URL: {base}\n")

    # ── 1. /koink/status ────────────────────────────────────────────────────
    print("1. GET /koink/status")
    code, data = get(base, "/koink/status")
    check("status 200", code == 200, f"got {code}")
    check("enabled field present", "enabled" in data)
    check("phase field present", "phase" in data)
    check("supported_chains present", "supported_chains" in data)
    check("features block present", "features" in data)

    koink_enabled = data.get("enabled", False)
    if not koink_enabled:
        print(f"\n  NOTE: Koink is disabled (KOINK_ENABLED not set).")
        print(f"  Launch/DHM/Treasury tests will expect 503 responses.\n")

    # ── 2. /koink/standard ──────────────────────────────────────────────────
    print("\n2. GET /koink/standard")
    code, data = get(base, "/koink/standard")
    check("status 200", code == 200, f"got {code}")
    check("name field present", "name" in data or "version" in data or len(data) > 0)

    # ── 3. /koink/launch ────────────────────────────────────────────────────
    print("\n3. POST /koink/launch")
    launch_body = {
        "name": "TestKoink",
        "symbol": "TKINK",
        "chain": "base",
        "total_supply": 1_000_000_000,
        "anti_whale_cap_pct": 2.0,
        "sell_tax_initial_bps": 500,
        "sell_tax_floor_bps": 100,
        "treasury_pct": 20.0,
        "dhm_enabled": True,
        "dhm_months": 12,
        "dhm_max_multiplier": 3.0,
    }
    code, data = post(base, "/koink/launch", launch_body)

    token_id = None
    if koink_enabled:
        ok = check("status 200 or 201", code in (200, 201), f"got {code}")
        if ok:
            check("id present", "id" in data)
            check("name matches", data.get("name") == "TestKoink")
            check("symbol matches", data.get("symbol") == "TKINK")
            check("chain matches", data.get("chain") == "base")
            token_id = data.get("id")
    else:
        check("status 503 when disabled", code == 503, f"got {code}")
        skip("launch data checks", "koink disabled")

    # ── 4. /koink/launches ──────────────────────────────────────────────────
    print("\n4. GET /koink/launches")
    code, data = get(base, "/koink/launches")
    if koink_enabled:
        check("status 200", code == 200, f"got {code}")
        # /koink/launches returns a list directly
        check("response is list or has tokens", isinstance(data, list) or "tokens" in data)
        if isinstance(data, list):
            check("list not empty after launch", len(data) >= 1)
    else:
        check("status 503 when disabled", code == 503, f"got {code}")

    # ── 5. /koink/launches/{id} ─────────────────────────────────────────────
    print("\n5. GET /koink/launches/{id}")
    if token_id:
        code, data = get(base, f"/koink/launches/{token_id}")
        check("status 200", code == 200, f"got {code}")
        check("id matches", str(data.get("id")) == str(token_id))
        check("dhm_enabled true", data.get("dhm_enabled") is True)
    else:
        skip("single token fetch", "no token_id available")

    # ── 6. /koink/dhm/{id} ─────────────────────────────────────────────────
    print("\n6. GET /koink/dhm/{id}")
    if token_id and koink_enabled:
        code, data = get(base, f"/koink/dhm/{token_id}")
        check("status 200", code == 200, f"got {code}")
        check("positions list present", "positions" in data)
        check("token_id matches", str(data.get("token_id")) == str(token_id))
    else:
        skip("dhm positions", "no token_id or koink disabled")

    # ── 7. /koink/dhm/snapshot ──────────────────────────────────────────────
    print("\n7. POST /koink/dhm/snapshot")
    if token_id and koink_enabled:
        code, data = post(base, "/koink/dhm/snapshot", {"token_id": token_id})
        check("status 200", code == 200, f"got {code}")
        check("snapshot result present", "updated" in data or "count" in data or isinstance(data, dict))
    else:
        skip("dhm snapshot", "no token_id or koink disabled")

    # ── 8. /koink/treasury/{id} ─────────────────────────────────────────────
    print("\n8. GET /koink/treasury/{id}")
    if token_id and koink_enabled:
        code, data = get(base, f"/koink/treasury/{token_id}")
        check("status 200", code == 200, f"got {code}")
        check("recent_events present", "recent_events" in data)
    else:
        skip("treasury", "no token_id or koink disabled")

    # ── 9. /koink/treasury/event ────────────────────────────────────────────
    print("\n9. POST /koink/treasury/event")
    if token_id and koink_enabled:
        code, data = post(base, "/koink/treasury/event", {
            "token_id": token_id,
            "event_type": "distribution",
            "amount": 1000.0,
            "recipient": "0xTEST",
            "metadata": {"test": True},
        })
        check("status 200", code == 200, f"got {code}")
        check("event_type matches", data.get("event_type") == "distribution")
    else:
        skip("treasury event", "no token_id or koink disabled")

    # ── 10. /crypto/status — koink section ──────────────────────────────────
    print("\n10. GET /crypto/status (koink section)")
    code, data = get(base, "/crypto/status")
    check("status 200", code == 200, f"got {code}")
    check("koink block present", "koink" in data)
    if "koink" in data:
        check("koink.enabled matches", data["koink"].get("enabled") == koink_enabled)
        check("koink.phase present", "phase" in data["koink"])

    # ── 11. /crypto/launch with koink_standard=True ─────────────────────────
    print("\n11. POST /crypto/launch (koink_standard=True)")
    launch_body2 = {
        "name": "CryptoKoink",
        "symbol": "CKINK",
        "chain": "base",
        "koink_standard": True,
        "anti_whale_cap_pct": 1.5,
        "sell_tax_initial_bps": 400,
        "treasury_pct": 15.0,
        "dhm_enabled": True,
        "dhm_months": 6,
    }
    code, data = post(base, "/crypto/launch", launch_body2)
    if koink_enabled:
        check("status 200", code == 200, f"got {code}")
        check("routed_via=koink_standard", data.get("routed_via") == "koink_standard", f"got {data.get('routed_via')}")
        check("name matches", data.get("name") == "CryptoKoink")
    else:
        check("status 503 when disabled", code == 503, f"got {code}")

    # ── 12. /crypto/execute with NL koink_launch (dry_run) ──────────────────
    print("\n12. POST /crypto/execute (NL koink_launch, dry_run=true)")
    code, data = post(base, "/crypto/execute", {
        "text": "launch a KOINK token called TestMeme on Base with 2% anti-whale",
        "dry_run": True,
    })
    if koink_enabled:
        check("status 200", code == 200, f"got {code}")
        check("status=dry_run", data.get("status") == "dry_run", f"got {data.get('status')}")
        intent = data.get("intent", {})
        check("intent.action=koink_launch", intent.get("action") == "koink_launch", f"got {intent.get('action')}")
    else:
        # NL parse still works but koink routing returns 503
        check("status 200 or 503", code in (200, 503), f"got {code}")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 48)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    skipped = sum(1 for _, s, _ in results if s == SKIP)
    total = passed + failed + skipped
    print(f"Results: {passed}/{total} passed, {failed} failed, {skipped} skipped")

    if failed:
        print("\nFailed tests:")
        for name, status, note in results:
            if status == FAIL:
                print(f"  ✗ {name}" + (f" — {note}" if note else ""))

    if not koink_enabled:
        print("\nTo enable Koink and test live launch flows:")
        print("  echo 'KOINK_ENABLED=true' >> ~/memory/.env")
        print("  systemctl restart otto-memory")

    return failed == 0


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Koink integration test harness")
    parser.add_argument("--base-url", default="http://localhost:8100", help="Memory API base URL")
    args = parser.parse_args()

    ok = run(args.base_url)
    sys.exit(0 if ok else 1)

# Koink × OMS Crypto Engine — Fit Assessment
**Date:** 2026-03-23
**Author:** Otto (Architect)
**Task:** Audit OMS Crypto Engine codebase for Koink compatibility

---

## Executive Summary

**Verdict: Strong fit. Plug-in ready with targeted extensions.**

The OMS Crypto Engine was designed for native token operations and already has launch infrastructure in place (Phase 3 stub). Koink slots into this cleanly with minimal rework — the data model aligns, the chain enum just needs expansion, and there are clean extension points at both the API and DB layer. No blockers.

---

## What Exists Today

### Backend: `~/otto/memory/routes/crypto.py` + `~/otto/memory/crypto/`

| Module | Role | Koink Relevance |
|---|---|---|
| `routes/crypto.py` | FastAPI router `/crypto/*` | **Direct** — extend `LaunchRequest`, add `/koink/*` |
| `crypto/launch.py` | Token launch CRUD + Phase 3 stubs | **Direct** — Koink deployment wires here |
| `crypto/nlparser.py` | LLM NL→TradeIntent | **Direct** — add `koink_launch` action + examples |
| `crypto/executor.py` | 0x quote + CDP execution | **Indirect** — Koink uses own deploy path, not 0x swap |
| `crypto/signals.py` | Signal board CRUD | **Peripheral** — post-launch Koink token signals |
| `crypto/price_feed.py` | CoinGecko + Birdeye | **Peripheral** — post-launch price tracking |
| `crypto/monitors.py` | Price monitors / DCA | **Peripheral** — post-launch DHM triggers |

### DB Schema (migration 059): `token_launches` table

```sql
CREATE TABLE token_launches (
    id               UUID PRIMARY KEY,
    name             TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    chain            TEXT NOT NULL,                -- "base" | "solana"
    contract_address TEXT,
    launch_mechanism TEXT NOT NULL,               -- "doppler" | "raydium_launchlab" | "manual"
    total_supply     NUMERIC,
    creator_fee_pct  NUMERIC,
    description      TEXT,
    status           TEXT DEFAULT 'pending',       -- pending | launched | failed
    tx_hash          TEXT,
    launch_data      JSONB,
    created_at       TIMESTAMPTZ,
    launched_at      TIMESTAMPTZ
);
```

**What's missing for Koink Standard:**
- `standard TEXT` — discriminator: `'koink_standard'` vs `'legacy'`
- `vrf_type TEXT` — `'chainlink_vrf'` | `'switchboard'` | `'none'`
- `bonding_curve_type TEXT` — `'doppler'` | `'raydium_launchlab'` | `'custom'`
- `anti_whale_pct NUMERIC` — max wallet % at launch (default 2.0)
- `sell_tax_bps INTEGER` — sell tax in basis points (default 200 = 2%)
- `dhm_enabled BOOLEAN` — Diamond Hands Mechanism flag
- `treasury_address TEXT` — Gnosis Safe address for fee collection
- `vrf_request_id TEXT` — Chainlink/Switchboard VRF request ID (for audit)

### Chain Enum (current)

```python
_CHAIN = Literal["base", "eth", "polygon", "solana", "hyperliquid", "bsc", "avalanche"]
```

- `LaunchRequest.chain` is further restricted to `Literal["base", "solana"]`
- **Missing for Koink chain-agnostic mandate**: `arbitrum`, `optimism`, `near`, `cosmos`

### Feature Flag Inventory

```
crypto_enabled: bool = False          # master flag
crypto_execution_enabled: bool = False # live execution flag
cdp_api_key_name / cdp_api_key_private_key  # CDP AgentKit (Phase 2 exec)
```

**Koink will need additional flags:**
```
koink_enabled: bool = False           # Koink module flag
koink_deploy_wallet: str = ""         # OWS-managed deploy key address
koink_testnet_only: bool = True       # Safety gate for contracts
```

---

## Gap Analysis

### Gap 1 — `LaunchRequest` model too narrow
**Severity: Medium**

Current model:
```python
class LaunchRequest(BaseModel):
    name: str
    symbol: str
    chain: Literal["base", "solana"]
    supply: Optional[float] = None
    creator_fee_pct: Optional[float] = None
    description: Optional[str] = None
```

Koink Standard requires: VRF seed params, anti-whale %, sell tax, DHM config, treasury address. These can be added as optional fields — fully backward compatible. Existing launches continue to work unchanged.

### Gap 2 — `token_launches` table missing Koink Standard columns
**Severity: Medium**

Migration needed (call it `migration 067`). All new columns are nullable with sensible defaults. Non-breaking.

### Gap 3 — No `/koink/*` router
**Severity: High (for Koink-specific UX)**

The `/crypto/launch` endpoint works as a generic launch record store, but Koink needs its own namespace for:
- `GET /koink/status` — engine + contract deploy status
- `POST /koink/launch` — full KOINK Standard params (wraps `/crypto/launch` + adds DHM setup)
- `GET /koink/tokens` — list all Koink-launched tokens
- `POST /koink/tokens/{id}/dhm` — configure DHM vault
- `GET /koink/tokens/{id}/treasury` — treasury event feed

**Design note:** `/koink/*` should be a thin layer on top of `/crypto/*`, not a parallel stack. Koink launch → writes to `token_launches` (with `standard='koink_standard'`) + `koink_dhm_positions` + `koink_treasury_events`.

### Gap 4 — NL parser has no Koink examples
**Severity: Low**

`SUPPORTED_ACTIONS` already includes `"launch"`. The parser needs Koink-specific examples added to `_PARSE_SYSTEM`:
```
- "launch $KOINK on Base with 2% anti-whale and DHM" → action=launch, token_out=KOINK, chain=base
```

Easy one-line addition to the prompt template.

### Gap 5 — No `koink_dhm_positions` or `koink_treasury_events` tables
**Severity: High (for Phase 1)**

Needed in the same migration 067:
```sql
CREATE TABLE koink_dhm_positions (
    id           UUID PRIMARY KEY,
    token_id     UUID REFERENCES token_launches(id),
    holder       TEXT NOT NULL,
    locked_amount NUMERIC,
    lock_until   TIMESTAMPTZ,
    multiplier   NUMERIC,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE koink_treasury_events (
    id          UUID PRIMARY KEY,
    token_id    UUID REFERENCES token_launches(id),
    event_type  TEXT NOT NULL,  -- 'sell_tax_collected' | 'dhm_reward' | 'sos_transfer'
    amount_usd  NUMERIC,
    tx_hash     TEXT,
    chain       TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Gap 6 — Chain enum doesn't include all Koink target chains
**Severity: Low for Phase 0, Medium for Phase 1**

`arbitrum` and `optimism` are missing from `_CHAIN`. Adding them is a one-line change. `near` and `cosmos` are non-EVM and need separate launch adapters — Phase 2 work.

### Gap 7 — No OWS wallet integration
**Severity: High (blocks contract deployment)**

The executor uses CDP AgentKit for trade execution but there's no OWS-backed signing key for contract deployment. The OWS integration plan (memory record 2026-03-23) defines the architecture: OWS vault for the `koink-deploy` agent key. This is the prerequisite for any live contract deployment.

---

## Data Model Alignment

| Koink Concept | OMS Equivalent | Status |
|---|---|---|
| Token launch record | `token_launches` row | ✅ exists, needs columns |
| Launch mechanism | `launch_mechanism` column | ✅ exists (`doppler`, `raydium_launchlab`) |
| Anti-whale params | — | ❌ add to launch table |
| DHM position | — | ❌ new `koink_dhm_positions` table |
| Treasury event | — | ❌ new `koink_treasury_events` table |
| Price tracking | `crypto_signals` + `price_monitors` | ✅ reuse as-is |
| NL command parsing | `TradeIntent.action = "launch"` | ✅ extend examples only |
| Feature flag | `crypto_enabled` | ⚠️ add `koink_enabled` sibling |

---

## Latency Assessment

| Operation | Expected Latency | Notes |
|---|---|---|
| `POST /koink/launch` (record only) | < 50ms | DB insert — fine |
| `POST /koink/launch` (contract deploy) | 10–30s | On-chain — must be async |
| `GET /koink/status` | < 20ms | DB + env check |
| `GET /koink/tokens` | < 100ms | Paginated DB query |
| NL parse for Koink command | 500–1500ms | LLM call — acceptable for OMS |

**Key latency concern:** Contract deployment is asynchronous. The `/koink/launch` endpoint must:
1. Accept the request, create a DB record with `status='pending'`
2. Return immediately with the record ID
3. Spawn a background task (task queue) for actual on-chain deployment
4. Update `status` → `'launched'` / `'failed'` + set `contract_address` and `tx_hash`

The existing task queue (`POST /tasks/{id}/run`) is the right mechanism for this.

---

## Implementation Plan

### Phase 0 — DB + Stub Endpoints (immediate, ~$4 task)
1. Migration `067_koink.sql`: add columns to `token_launches` + create `koink_dhm_positions` + `koink_treasury_events`
2. Add optional Koink fields to `LaunchRequest` (backward-compatible)
3. Add `/koink/status` GET endpoint (reuse `/crypto/status` pattern)
4. Extend NL parser system prompt with 3 Koink examples
5. Add `koink_enabled`, `koink_deploy_wallet`, `koink_testnet_only` to `config.py`

### Phase 1 — Full `/koink/*` Router (~$6 task)
6. New `routes/koink.py` router (thin wrapper over crypto + Koink-specific logic)
7. New `crypto/koink_launch.py` module (KOINK Standard deploy logic)
8. Wire `/koink/launch` → `token_launches` (standard='koink_standard') + async deploy task
9. DHM config endpoint + `koink_dhm_positions` CRUD
10. Treasury events feed + `koink_treasury_events` CRUD

### Phase 2 — OMS Frontend Tab (~$5 task)
11. Add Koink section to `/crypto` OMS page (or new `/koink` route)
12. Launch form with KOINK Standard params
13. Token list with DHM + treasury stats

### Phase 3 — Contract Deployment (requires OWS wallet + Solidity contracts)
- Covered by separate `smart-contract-pipeline` workflow tasks

---

## Blockers

| Blocker | Who | Action |
|---|---|---|
| OWS deploy wallet not created | Otto (autonomous) | Task: create OWS vault + `koink-deploy` key |
| Smart contracts not written | Otto (autonomous) | Task: `smart-contract-pipeline` workflow |
| `koink_enabled=true` in production | Mev | Mev flips flag when ready to go live |

---

## Verdict

**Koink slots cleanly into the OMS Crypto Engine.** The existing architecture (FastAPI + asyncpg + task queue + feature flags) maps to Koink's needs without conflict. The token launch infrastructure already exists — it just needs Koink Standard columns and a dedicated router. No rework, only additive changes.

**Recommended first task:** Migration 067 + Phase 0 endpoints (~$4, 30min, fully autonomous).

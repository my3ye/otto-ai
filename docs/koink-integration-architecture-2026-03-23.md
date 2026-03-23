# Koink Integration Module — Architecture & Implementation Plan
**Date:** 2026-03-23 | **Status:** Design Complete | **Author:** Architect Agent

---

## Design: Koink Integration Module

### Problem

Koink.fun is our platform implementing the $KOINK Standard — a chain-agnostic tokenomics spec. Currently:
- OMS has `/crypto/launch` as a Phase 3 stub (DB record only, no execution)
- No `/koink/*` routes exist
- No dedicated Koink tables exist — only a bare `token_launches` table
- No DHM position tracking, treasury event tracking, or fair-launch VRF support

The task: build the Koink integration module into the OMS crypto engine so that Mev (and agents) can create, track, and eventually deploy $KOINK Standard tokens from a single, consistent interface.

---

### Approach

Three-phase rollout. Phase 0 ships immediately (no contract deployment needed). Phases 1–2 are follow-on tasks.

**Phase 0 — API Foundation (this implementation):**
- Migration 067: new Koink tables + extend `token_launches`
- New `otto/memory/koink/` module
- New `/koink/*` FastAPI router
- Feature flag `koink_enabled` in config
- Extend `LaunchRequest` + NL parser for KOINK params

**Phase 1 — EVM Contracts (next task, separate):**
- `KoinkToken.sol`, `KoinkLauncher.sol`, `DiamondHandsVault.sol`, `KoinkTreasury.sol`
- Async deploy pipeline via task queue
- OWS deploy wallet (Mev action required)

**Phase 2 — Solana (future, not scoped here):**
- Raydium LaunchLab integration
- Switchboard VRF

---

### Key Decisions

- **New `/koink/*` router, not extending `/crypto/launch`**: Koink has distinct lifecycle (VRF seed → anti-whale params → deploy → DHM tracking → treasury events). Cramming this into `/crypto/launch` would bloat that route. Alternative: extend `/crypto/launch` — rejected as too coupled.

- **Async deploy pattern**: `/koink/launch` accepts request → returns `pending` record immediately → task queue handles actual contract deployment → status polled via GET. Matches existing task queue pattern. Alternative: synchronous — rejected (contract deploy = 10-30s, HTTP timeout risk).

- **Separate `koink_tokens` table, not just extending `token_launches`**: Koink tokens have 7+ KOINK-specific columns (DHM, anti-whale, VRF, treasury pct, graduated tax), plus new relationship tables. Adding to `token_launches` would create sparse columns for non-Koink launches. Decision: extend `token_launches` with nullable KOINK columns for backward compat, plus create `koink_tokens` as the authoritative Koink record (FK to `token_launches`). Both exist. Alternative: Koink-only table with no link to `token_launches` — rejected (breaks `/crypto/launches` unified view).

- **DHM tracked off-chain**: Diamond Hands Multiplier (hold duration → governance weight) is tracked in `koink_dhm_positions` table. On-chain source of truth for Phase 1. Off-chain table mirrors state for OMS display. Alternative: query chain live — rejected (no contracts yet in Phase 0; too slow for dashboard).

- **No OWS wallet in Phase 0**: OWS deploy wallet is required for actual contract deployment. Phase 0 just records intent + validates parameters. Phase 1 wires OWS signing. Mev must register the wallet before Phase 1 can go live.

---

### API / Interface

#### New Routes — `/koink/*`

```
GET  /koink/status           — feature flags, wallet status, chain support, DHM stats
POST /koink/launch           — create a $KOINK Standard token (async, returns pending record)
GET  /koink/launches         — list all Koink token launches with KOINK metadata
GET  /koink/launches/{id}    — single launch record with full KOINK params
GET  /koink/dhm/{token_id}   — DHM positions for a token (holder rankings + multipliers)
POST /koink/dhm/snapshot     — trigger off-chain DHM snapshot (admin)
GET  /koink/treasury/{token_id} — treasury balance + recent events
POST /koink/treasury/event   — record a treasury distribution event
GET  /koink/standard         — the $KOINK Standard spec (machine-readable JSON)
```

#### LaunchRequest Extension (backward-compatible)

Add optional KOINK Standard fields to existing `LaunchRequest`:
```python
# All optional — if koink_standard=True, validated together
koink_standard: bool = False
anti_whale_cap_pct: float = 2.0        # max % of supply per wallet at launch
sell_tax_initial_bps: int = 500        # initial sell tax (500 = 5%)
sell_tax_floor_bps: int = 100          # floor sell tax for diamond hands (100 = 1%)
treasury_pct: float = 20.0             # % of each tx to treasury
dhm_enabled: bool = True               # enable Diamond Hands Multiplier
dhm_max_multiplier: float = 3.0        # max governance weight at 12 months
dhm_months: int = 12                   # months to reach max multiplier
vrf_type: str = "chainlink"            # chainlink | switchboard | none
vrf_seed: Optional[str] = None         # set after VRF fulfillment
```

#### KoinkLaunchRequest (dedicated — full spec enforcement)

```python
class KoinkLaunchRequest(BaseModel):
    # Core identity
    name: str
    symbol: str
    chain: Literal["base", "eth", "arbitrum", "optimism", "solana"]
    total_supply: float = 1_000_000_000    # 1B default
    description: Optional[str] = None

    # $KOINK Standard params (validated against standard defaults)
    anti_whale_cap_pct: float = 2.0
    sell_tax_initial_bps: int = 500
    sell_tax_floor_bps: int = 100
    treasury_pct: float = 20.0
    dhm_enabled: bool = True
    dhm_max_multiplier: float = 3.0
    dhm_months: int = 12
    vrf_type: Literal["chainlink", "switchboard", "none"] = "chainlink"

    # Creator config
    creator_fee_pct: float = 2.0
    liquidity_pct: float = 60.0         # % of raise to LP
```

---

### DB Schema — Migration 067

```sql
-- Extend token_launches with nullable KOINK Standard columns
ALTER TABLE token_launches
    ADD COLUMN IF NOT EXISTS koink_standard        BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS anti_whale_cap_pct    NUMERIC,
    ADD COLUMN IF NOT EXISTS sell_tax_initial_bps  INTEGER,
    ADD COLUMN IF NOT EXISTS sell_tax_floor_bps    INTEGER,
    ADD COLUMN IF NOT EXISTS treasury_pct          NUMERIC,
    ADD COLUMN IF NOT EXISTS dhm_enabled           BOOLEAN,
    ADD COLUMN IF NOT EXISTS dhm_max_multiplier    NUMERIC,
    ADD COLUMN IF NOT EXISTS dhm_months            INTEGER,
    ADD COLUMN IF NOT EXISTS vrf_type              TEXT,
    ADD COLUMN IF NOT EXISTS vrf_seed              TEXT;

-- Authoritative Koink token record (FK to token_launches)
CREATE TABLE koink_tokens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    launch_id           UUID REFERENCES token_launches(id),
    chain               TEXT NOT NULL,
    contract_address    TEXT,
    deployer_address    TEXT,                    -- OWS wallet used
    total_supply        NUMERIC NOT NULL,
    anti_whale_cap_pct  NUMERIC NOT NULL DEFAULT 2.0,
    sell_tax_initial_bps INTEGER NOT NULL DEFAULT 500,
    sell_tax_floor_bps  INTEGER NOT NULL DEFAULT 100,
    treasury_pct        NUMERIC NOT NULL DEFAULT 20.0,
    treasury_address    TEXT,
    dhm_enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    dhm_max_multiplier  NUMERIC NOT NULL DEFAULT 3.0,
    dhm_months          INTEGER NOT NULL DEFAULT 12,
    vrf_type            TEXT NOT NULL DEFAULT 'chainlink',
    vrf_seed            TEXT,
    vrf_request_id      TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    deployment_task_id  UUID,               -- links to task queue
    deploy_tx_hash      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deployed_at         TIMESTAMPTZ
);

-- DHM holder positions (off-chain mirror of on-chain vault)
CREATE TABLE koink_dhm_positions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id        UUID NOT NULL REFERENCES koink_tokens(id),
    holder_address  TEXT NOT NULL,
    balance         NUMERIC NOT NULL DEFAULT 0,
    hold_start_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    multiplier      NUMERIC NOT NULL DEFAULT 1.0,    -- current governance weight
    last_snapshot   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(token_id, holder_address)
);

-- Treasury events (on-chain distributions, off-chain records)
CREATE TABLE koink_treasury_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id        UUID NOT NULL REFERENCES koink_tokens(id),
    event_type      TEXT NOT NULL,          -- distribution | allocation | withdrawal
    amount          NUMERIC NOT NULL,
    recipient       TEXT,
    tx_hash         TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

### Module Structure

```
otto/memory/
├── koink/
│   ├── __init__.py            # exports, koink_enabled guard
│   ├── standard.py            # $KOINK Standard constants + validation
│   ├── launch.py              # create/get/list koink token records
│   ├── dhm.py                 # DHM position tracking + multiplier calculation
│   └── treasury.py            # treasury event recording + balance queries
└── routes/
    └── koink.py               # FastAPI router /koink/*
```

**`koink/standard.py`** — single source of truth for the $KOINK Standard spec:
```python
KOINK_DEFAULTS = {
    "anti_whale_cap_pct": 2.0,
    "sell_tax_initial_bps": 500,
    "sell_tax_floor_bps": 100,
    "treasury_pct": 20.0,
    "dhm_max_multiplier": 3.0,
    "dhm_months": 12,
    "vrf_type": "chainlink",
}
SUPPORTED_CHAINS = ["base", "eth", "arbitrum", "optimism", "solana"]
CHAIN_VRF_MAP = {
    "base": "chainlink",
    "eth": "chainlink",
    "arbitrum": "chainlink",
    "optimism": "chainlink",
    "solana": "switchboard",
}

def validate_koink_params(params: dict) -> tuple[bool, list[str]]:
    """Validate KOINK Standard parameters. Returns (valid, errors)."""
    ...

def calculate_dhm_multiplier(hold_days: int, dhm_months: int = 12, max_mult: float = 3.0) -> float:
    """Calculate governance weight multiplier based on hold duration."""
    # Linear ramp from 1.0x to max_mult over dhm_months
    ...
```

---

### Implementation Plan

**Step 1 — Migration 067** (15min, no dependency)
- File: `otto/memory/migrations/067_koink.sql`
- Extend `token_launches` with 10 KOINK columns
- Create `koink_tokens`, `koink_dhm_positions`, `koink_treasury_events`
- Run migration

**Step 2 — Koink module** (30min)
- `otto/memory/koink/__init__.py` — feature flag guard
- `otto/memory/koink/standard.py` — constants, validation, DHM calc
- `otto/memory/koink/launch.py` — DB CRUD for koink_tokens
- `otto/memory/koink/dhm.py` — DHM position CRUD + multiplier updates
- `otto/memory/koink/treasury.py` — treasury event CRUD

**Step 3 — Router** (20min)
- `otto/memory/routes/koink.py` — 9 endpoints (see API section)
- Wire in `otto/memory/api.py`

**Step 4 — Config + Feature Flag** (5min)
- `otto/memory/config.py` — add `koink_enabled: bool = False`
- All `/koink/*` endpoints guard on this flag

**Step 5 — Extend LaunchRequest + NL Parser** (15min)
- Add optional KOINK fields to `LaunchRequest` in `routes/crypto.py`
- Add `koink_launch` action + 3 examples to `crypto/nlparser.py`

**Step 6 — OMS Page** (30min, optional in this task)
- `interfaces/web-next/app/koink/page.tsx`
- Status panel, launch form, DHM tracker table, treasury events feed
- shadcn/ui: Card, Table, Badge, Dialog for launch form

---

### Smart Contract Interfaces (Phase 1 reference)

These are NOT implemented in Phase 0. Defined here for the Phase 1 coder task.

**KoinkToken.sol** (ERC-20 + KOINK Standard):
```solidity
interface IKoinkToken {
    function antiWhaleCapPct() external view returns (uint256);  // in bps
    function sellTaxBps() external view returns (uint256);       // current sell tax
    function getSellTaxForHolder(address holder) external view returns (uint256);
    function dhm() external view returns (address);              // DiamondHandsVault
    function treasury() external view returns (address);         // KoinkTreasury
}
```

**KoinkLauncher.sol** (VRF consumer + deployment coordinator):
```solidity
interface IKoinkLauncher {
    function requestLaunchSeed(bytes32 tokenId) external returns (uint256 requestId);
    function deployToken(bytes32 tokenId, address deployer) external returns (address tokenAddr);
}
```

**DiamondHandsVault.sol**:
```solidity
interface IDiamondHandsVault {
    function getMultiplier(address holder) external view returns (uint256);  // 100 = 1.0x
    function holdStartTime(address holder) external view returns (uint256);
}
```

**KoinkTreasury.sol**:
```solidity
interface IKoinkTreasury {
    function balance() external view returns (uint256);
    function distribute(address[] calldata recipients, uint256[] calldata amounts) external;
}
```

---

### Risks

- **OWS wallet blocker**: Phase 0 stores intent only. Phase 1 can't go live until Mev registers a deploy wallet with OWS. Mitigation: Phase 0 ships standalone; Phase 1 explicitly gates on `koink_ows_wallet` being set.

- **Chainlink VRF subscription**: Requires LINK tokens + subscription setup on each chain. Phase 0 stores `vrf_request_id = null`. Phase 1 task must budget for subscription creation. Mitigation: document the requirement in Phase 1 task prompt.

- **DHM off-chain drift**: The `koink_dhm_positions` table mirrors on-chain state but can drift. Until contracts exist, snapshots are synthetic (calculated from hold times). Mitigation: snapshot endpoint triggers recalculation; clear `synthetic=true` flag until contracts live.

- **Chain enum expansion**: `token_launches.chain` currently only has "base" and "solana". Adding arbitrum/optimism requires either a DB CHECK constraint change or removal. Mitigation: migration 067 drops the constraint and uses application-level validation.

---

### Cost Estimate (Phase 0)

| Task | Agent | Budget |
|---|---|---|
| Migration 067 | coder | ~$1 |
| Koink module (4 files) | coder | ~$3 |
| Router (routes/koink.py) | coder | ~$3 |
| Config + LaunchRequest extend | coder | ~$1 |
| NL parser extension | coder | ~$1 |
| OMS page (optional) | frontend-developer | ~$4 |
| **Total Phase 0** | | **~$9-13** |
| **Phase 1 (EVM contracts)** | solidity-engineer | ~$15-20 |

---

### Files to Modify or Create

**New files:**
- `otto/memory/migrations/067_koink.sql`
- `otto/memory/koink/__init__.py`
- `otto/memory/koink/standard.py`
- `otto/memory/koink/launch.py`
- `otto/memory/koink/dhm.py`
- `otto/memory/koink/treasury.py`
- `otto/memory/routes/koink.py`
- `interfaces/web-next/app/koink/page.tsx` (optional in Phase 0)

**Modified files:**
- `otto/memory/api.py` — add koink router import + include
- `otto/memory/config.py` — add `koink_enabled` flag
- `otto/memory/routes/crypto.py` — extend `LaunchRequest` with KOINK fields
- `otto/memory/crypto/nlparser.py` — add `koink_launch` action + examples

# ONEON + Remaining Integrations — Architecture Plan
*Architect design — 2026-03-23*
*Step 0 of workflow: Architecture & Planning*

---

## Design: ONEON Integration Module

### Problem

Koink is fully integrated into the Memory API (`otto/memory/koink/`, `/koink/*` routes, migration 067/068). Mev directed: implement ONEON and remaining integrations using the same template.

ONEON is the ZEN Network — ONEON's primary surface in the Memory API is:
1. **Identity registry** — handles, tiers (waitlist → custodial → self-sovereign → sovereign)
2. **Waitlist management** — the oneon-web landing page collects handle + email + origin
3. **Governance proposals** — Phase 0 placeholder, Phase 2 full DAO
4. **WalletAdapter interface** — abstract signing contract (OWS Phase 0 prerequisite)

"Remaining integrations" covers two additional ecosystem projects with clear data-layer needs:
- **Tusita** — community spaces, bookings, revenue tracking (Tusita is a physical Parallel Civilization, needs capacity + booking management)
- **SOS Systems** — learner profiles, contribution tracking, refuge cases (two-system unified ladder)

---

## Key Decisions

- **WalletAdapter first**: A single abstract interface file that both Koink and ONEON reference. OWS (Phase 1) plugs in here. Without this seam, we bake OWS into both integrations directly.
- **ONEON module follows Koink exactly**: Same structure — module package + routes file + migration. No exceptions.
- **Tusita + SOS as lightweight modules**: Less complex than Koink/ONEON. One migration each, one module package each, routes file.
- **Feature flags on all integrations**: `oneon_enabled`, `tusita_enabled`, `sos_enabled` in config.py. All disabled by default.
- **No frontend yet**: OMS pages come after API is solid. Step 1 focuses on API + DB only.

---

## Architecture

### File Map

```
otto/memory/
├── wallet_adapter.py                  # NEW — abstract WalletAdapter interface
├── oneon/                             # NEW — ONEON module package
│   ├── __init__.py                    #   exports
│   ├── identity.py                    #   CRUD for oneon_identities
│   ├── governance.py                  #   CRUD for oneon_governance_proposals
│   ├── did.py                         #   did:oneon derivation stubs (Phase 0)
│   └── spec.py                        #   ONEON_SPEC constant (machine-readable)
├── tusita/                            # NEW — Tusita module package
│   ├── __init__.py
│   ├── locations.py                   #   CRUD for tusita_locations
│   └── bookings.py                    #   CRUD for tusita_bookings
├── sos/                               # NEW — SOS Systems module package
│   ├── __init__.py
│   ├── learners.py                    #   CRUD for sos_learners
│   └── cases.py                       #   CRUD for sos_cases
├── routes/
│   ├── oneon.py                       # NEW — /oneon/* router (9 endpoints)
│   ├── tusita.py                      # NEW — /tusita/* router (7 endpoints)
│   └── sos.py                         # NEW — /sos/* router (7 endpoints)
├── config.py                          # MODIFY — add oneon_enabled, tusita_enabled, sos_enabled
├── api.py                             # MODIFY — import + register 3 new routers
└── migrations/
    ├── 069_oneon.sql                  # NEW — oneon_identities, oneon_governance_proposals
    ├── 070_tusita.sql                 # NEW — tusita_locations, tusita_bookings
    └── 071_sos.sql                    # NEW — sos_learners, sos_contributions, sos_cases
```

---

## DB Schema

### Migration 069 — ONEON

```sql
-- oneon_identities: ZEN Network identity registry
CREATE TABLE IF NOT EXISTS oneon_identities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT NOT NULL UNIQUE,           -- @handle (ZEN Network handle)
    email           TEXT,
    origin          TEXT,                           -- self-reported origin (country/city)
    tier            TEXT NOT NULL DEFAULT 'waitlist', -- waitlist | custodial | self_sovereign | sovereign
    did             TEXT,                           -- did:oneon:... (Phase 2+)
    ows_vault_id    TEXT,                           -- OWS vault ref (Phase 1+)
    agent_token_hash TEXT,                         -- SHA-256 of OWS agent token (Phase 1+)
    chain_addresses JSONB DEFAULT '{}',             -- {chain: address} via OWS (Phase 1+)
    invite_code     TEXT,
    referred_by     UUID REFERENCES oneon_identities(id),
    metadata        JSONB DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | active | suspended
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oneon_identities_handle ON oneon_identities(handle);
CREATE INDEX IF NOT EXISTS idx_oneon_identities_tier ON oneon_identities(tier);
CREATE INDEX IF NOT EXISTS idx_oneon_identities_status ON oneon_identities(status);
CREATE INDEX IF NOT EXISTS idx_oneon_identities_created_at ON oneon_identities(created_at DESC);

-- oneon_governance_proposals: Phase 0 placeholder, Phase 2 DAO
CREATE TABLE IF NOT EXISTS oneon_governance_proposals (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title       TEXT NOT NULL,
    description TEXT,
    proposer_id UUID REFERENCES oneon_identities(id),
    category    TEXT DEFAULT 'general',       -- general | protocol | treasury | membership
    vote_start  TIMESTAMPTZ,
    vote_end    TIMESTAMPTZ,
    status      TEXT NOT NULL DEFAULT 'draft', -- draft | active | passed | failed | executed
    yes_votes   INTEGER DEFAULT 0,
    no_votes    INTEGER DEFAULT 0,
    votes       JSONB DEFAULT '{}',           -- {identity_id: "yes"/"no"/"abstain"}
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_oneon_proposals_status ON oneon_governance_proposals(status);
CREATE INDEX IF NOT EXISTS idx_oneon_proposals_created_at ON oneon_governance_proposals(created_at DESC);
```

### Migration 070 — Tusita

```sql
-- tusita_locations: Dome/space registry for the Parallel Civilization
CREATE TABLE IF NOT EXISTS tusita_locations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    location_type   TEXT NOT NULL DEFAULT 'dome',   -- dome | space | garden | workshop | sanctuary
    country         TEXT,
    city            TEXT,
    capacity        INTEGER DEFAULT 0,
    description     TEXT,
    amenities       JSONB DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'planned', -- planned | development | open | closed
    monthly_revenue NUMERIC DEFAULT 0,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

-- tusita_bookings: Visitor/resident reservation system
CREATE TABLE IF NOT EXISTS tusita_bookings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    location_id     UUID REFERENCES tusita_locations(id) ON DELETE SET NULL,
    visitor_name    TEXT NOT NULL,
    visitor_email   TEXT,
    booking_type    TEXT NOT NULL DEFAULT 'visit',   -- visit | residency | retreat | pilgrimage
    check_in        DATE NOT NULL,
    check_out       DATE NOT NULL,
    party_size      INTEGER DEFAULT 1,
    status          TEXT NOT NULL DEFAULT 'pending', -- pending | confirmed | cancelled | completed
    amount          NUMERIC DEFAULT 0,
    currency        TEXT DEFAULT 'USD',
    notes           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_tusita_bookings_location_id ON tusita_bookings(location_id);
CREATE INDEX IF NOT EXISTS idx_tusita_bookings_check_in ON tusita_bookings(check_in);
CREATE INDEX IF NOT EXISTS idx_tusita_bookings_status ON tusita_bookings(status);
```

### Migration 071 — SOS Systems

```sql
-- sos_learners: Unified education + refuge ladder profile
CREATE TABLE IF NOT EXISTS sos_learners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT UNIQUE,                    -- ties to ONEON identity if they have one
    oneon_id        UUID,                           -- optional reference to oneon_identities
    name            TEXT,
    email           TEXT,
    tier            TEXT NOT NULL DEFAULT 'seed',   -- seed | sapling | grower | builder | guide | elder
    origin_type     TEXT NOT NULL DEFAULT 'general', -- general | refugee | displaced | underprivileged | homeless
    origin_country  TEXT,
    skills          JSONB DEFAULT '[]',
    contributions   INTEGER DEFAULT 0,
    reputation      NUMERIC DEFAULT 0.0,
    passion_tags    JSONB DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'active', -- active | graduated | paused | withdrawn
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sos_learners_tier ON sos_learners(tier);
CREATE INDEX IF NOT EXISTS idx_sos_learners_origin_type ON sos_learners(origin_type);

-- sos_contributions: Learning contributions tracked for advancement
CREATE TABLE IF NOT EXISTS sos_contributions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id      UUID NOT NULL REFERENCES sos_learners(id) ON DELETE CASCADE,
    contribution_type TEXT NOT NULL,               -- code | content | teaching | operations | design | research
    title           TEXT NOT NULL,
    description     TEXT,
    impact_score    NUMERIC DEFAULT 0.0,
    verified        BOOLEAN DEFAULT FALSE,
    verifier_id     UUID REFERENCES sos_learners(id),
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sos_contributions_learner_id ON sos_contributions(learner_id);
CREATE INDEX IF NOT EXISTS idx_sos_contributions_type ON sos_contributions(contribution_type);

-- sos_cases: Refuge/extraction case management
CREATE TABLE IF NOT EXISTS sos_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_type       TEXT NOT NULL DEFAULT 'refuge', -- refuge | extraction | emergency | support
    learner_id      UUID REFERENCES sos_learners(id),
    origin_country  TEXT,
    situation       TEXT NOT NULL,
    urgency         TEXT NOT NULL DEFAULT 'medium', -- low | medium | high | critical
    status          TEXT NOT NULL DEFAULT 'open',   -- open | in_progress | resolved | closed
    assigned_to     TEXT,                           -- agent handle / team member
    resolution      TEXT,
    tusita_location_id UUID,                        -- if referred to Tusita
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_sos_cases_urgency ON sos_cases(urgency);
CREATE INDEX IF NOT EXISTS idx_sos_cases_status ON sos_cases(status);
CREATE INDEX IF NOT EXISTS idx_sos_cases_case_type ON sos_cases(case_type);
```

---

## API Routes

### ONEON — `/oneon/*` (9 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/oneon/status` | Feature flags, network stats, tier distribution |
| GET | `/oneon/standard` | Machine-readable ONEON spec |
| POST | `/oneon/register` | Create identity record (waitlist join) |
| GET | `/oneon/identities` | List identities with filters (tier, status) |
| GET | `/oneon/identities/{id}` | Single identity detail |
| PUT | `/oneon/identities/{id}/tier` | Upgrade identity tier (admin) |
| GET | `/oneon/governance` | List governance proposals |
| POST | `/oneon/governance` | Create proposal (Phase 0 admin) |
| GET | `/oneon/did/{handle}` | DID resolution stub (returns `did:oneon:<handle>` format) |

### Tusita — `/tusita/*` (7 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/tusita/status` | Feature flags, location count, booking stats |
| GET | `/tusita/locations` | List locations with status filter |
| POST | `/tusita/locations` | Create location record (admin) |
| GET | `/tusita/locations/{id}` | Location detail |
| POST | `/tusita/bookings` | Create booking request |
| GET | `/tusita/bookings` | List bookings with filters |
| GET | `/tusita/bookings/{id}` | Booking detail |

### SOS Systems — `/sos/*` (7 endpoints)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/sos/status` | Feature flags, learner counts by tier, open cases |
| POST | `/sos/learners` | Register learner profile |
| GET | `/sos/learners` | List learners with tier/origin filters |
| GET | `/sos/learners/{id}` | Learner detail |
| POST | `/sos/contributions` | Record a contribution |
| POST | `/sos/cases` | Submit refuge/support case |
| GET | `/sos/cases` | List cases with urgency/status filters |

---

## WalletAdapter Interface

**File:** `otto/memory/wallet_adapter.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

class WalletAdapter(ABC):
    """Abstract signing interface — OWS (Phase 1) plugs in here.

    Both Koink (fair launch agents) and ONEON (custodial + agent delegation)
    reference this interface. Phase 0: stub only. Phase 1: OWS implementation.

    Interface per OWS strategic brief 2026-03-23:
      - sign(): All on-chain signing goes through here
      - get_address(): CAIP-10 multi-chain address derivation
      - delegate_agent(): Issue scoped signing token to an agent
      - revoke_agent(): Revoke a previously issued token
    """

    @abstractmethod
    async def sign(self, chain: str, payload: dict, policy: dict) -> str:
        """Sign a transaction payload on the given chain with policy enforcement."""
        ...

    @abstractmethod
    async def get_address(self, chain: str, account_index: int = 0) -> str:
        """Return the CAIP-10 address for this chain + account index."""
        ...

    @abstractmethod
    async def delegate_agent(self, agent_id: str, policy_rules: dict) -> str:
        """Issue a scoped signing token for an agent. Returns token (show once)."""
        ...

    @abstractmethod
    async def revoke_agent(self, token_id: str) -> bool:
        """Revoke an agent's signing token."""
        ...


class NullWalletAdapter(WalletAdapter):
    """Phase 0 stub — raises NotImplementedError for all signing operations.
    Replace with OWSWalletAdapter in Phase 1.
    """

    async def sign(self, chain: str, payload: dict, policy: dict) -> str:
        raise NotImplementedError("Phase 0: OWS not yet integrated. WalletAdapter is abstract.")

    async def get_address(self, chain: str, account_index: int = 0) -> str:
        raise NotImplementedError("Phase 0: OWS not yet integrated.")

    async def delegate_agent(self, agent_id: str, policy_rules: dict) -> str:
        raise NotImplementedError("Phase 0: OWS not yet integrated.")

    async def revoke_agent(self, token_id: str) -> bool:
        raise NotImplementedError("Phase 0: OWS not yet integrated.")


# Singleton — swap this for OWSWalletAdapter in Phase 1
wallet_adapter: WalletAdapter = NullWalletAdapter()
```

---

## Config Changes

Add to `otto/memory/config.py`:

```python
# ── ONEON integration ──────────────────────────────────────────────
oneon_enabled: bool = False        # Master feature flag

# ── Tusita integration ─────────────────────────────────────────────
tusita_enabled: bool = False       # Master feature flag

# ── SOS Systems integration ────────────────────────────────────────
sos_enabled: bool = False          # Master feature flag
```

---

## Implementation Plan

### Step 1 — WalletAdapter + ONEON (implement first)
1. Write `otto/memory/wallet_adapter.py` (abstract interface + NullWalletAdapter stub)
2. Write migration `069_oneon.sql`
3. Run migration against DB
4. Write `otto/memory/oneon/spec.py` (ONEON_SPEC constant)
5. Write `otto/memory/oneon/identity.py` (CRUD functions)
6. Write `otto/memory/oneon/governance.py` (CRUD functions)
7. Write `otto/memory/oneon/did.py` (did:oneon derivation stubs)
8. Write `otto/memory/oneon/__init__.py` (exports)
9. Write `otto/memory/routes/oneon.py` (9 endpoints)
10. Add `oneon_enabled` to config.py
11. Wire oneon router into api.py
12. Test all endpoints with curl

### Step 2 — Tusita integration
13. Write migration `070_tusita.sql`
14. Run migration
15. Write `otto/memory/tusita/locations.py` + `bookings.py` + `__init__.py`
16. Write `otto/memory/routes/tusita.py` (7 endpoints)
17. Add `tusita_enabled` to config.py
18. Wire tusita router into api.py
19. Test endpoints

### Step 3 — SOS Systems integration
20. Write migration `071_sos.sql`
21. Run migration
22. Write `otto/memory/sos/learners.py` + `cases.py` + `__init__.py`
23. Write `otto/memory/routes/sos.py` (7 endpoints)
24. Add `sos_enabled` to config.py
25. Wire sos router into api.py
26. Test endpoints

### Step 4 — Store architecture + notify
27. Store semantic memory of this architecture
28. Update task output with summary

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Migration conflicts (069/070/071 collide with existing tables) | Use `CREATE TABLE IF NOT EXISTS` + `ADD COLUMN IF NOT EXISTS` throughout |
| Feature flag off = 503 on all routes | Same pattern as Koink `_require_enabled()` guard |
| ONEON identity handle uniqueness across ecosystem | `UNIQUE` constraint on `handle` column; future: cross-reference with Koink symbol namespace |
| SOS learner tier advancement logic is complex | Phase 0: manual tier updates only. Phase 2: automated advancement rules |
| Tusita bookings need calendar/availability logic | Phase 0: simple date records. Phase 2: availability engine |

---

## What This Unlocks

After these integrations:
- **ONEON waitlist** from oneon-web landing page can write directly to `oneon_identities` via API
- **Governance proposals** have a tracking system for the DAO layer
- **Tusita** can track community locations and visitor bookings from day 1
- **SOS Systems** has a learner registry and case management foundation
- **WalletAdapter** is the seam that makes OWS (Phase 1, ~$8K) plug-in rather than baked-in

---

*Full OWS strategic context: `~/otto/docs/ows-strategic-brief-2026-03-23.md`*
*ONEON × OWS compatibility: `~/otto/docs/oneon-ows-compatibility-2026-03-23.md`*
*Koink reference implementation: `~/otto/memory/koink/`, `~/otto/memory/routes/koink.py`*

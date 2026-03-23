---
name: ONEON + Tusita + SOS integrations architecture
description: Architecture plan for 3 new Memory API integration modules following Koink template, with WalletAdapter abstract interface
type: project
---

3 new integration modules + WalletAdapter designed 2026-03-23. All follow the Koink pattern (module package + routes/*.py + migration + config flag + api.py wiring).

**WalletAdapter first** — abstract signing interface at `otto/memory/wallet_adapter.py`. Both Koink and ONEON reference it. OWS plugs in here for Phase 1. NullWalletAdapter stub for Phase 0.

**ONEON** (migration 069):
- `oneon_identities` table — handle, email, origin, tier (waitlist→custodial→self_sovereign→sovereign), did, ows_vault_id, chain_addresses
- `oneon_governance_proposals` table — Phase 0 placeholder for DAO
- `otto/memory/oneon/` package: identity.py, governance.py, did.py, spec.py, __init__.py
- 9 endpoints at `/oneon/*` (register, identities CRUD, governance, DID stub)
- Config: `oneon_enabled: bool = False`

**Tusita** (migration 070):
- `tusita_locations` — dome/space registry (name, type, country, capacity, status, monthly_revenue)
- `tusita_bookings` — visitor/resident reservations (check_in, check_out, type, status, amount)
- `otto/memory/tusita/` package: locations.py, bookings.py, __init__.py
- 7 endpoints at `/tusita/*`
- Config: `tusita_enabled: bool = False`

**SOS Systems** (migration 071):
- `sos_learners` — unified education+refuge profile (tier: seed→elder, origin_type, skills, contributions, reputation)
- `sos_contributions` — contribution records for advancement tracking
- `sos_cases` — refuge/extraction case management (urgency: low→critical, status, tusita_location_id)
- `otto/memory/sos/` package: learners.py, cases.py, __init__.py
- 7 endpoints at `/sos/*`
- Config: `sos_enabled: bool = False`

**Why:** Mev directed "implement the others after autonomously" (following Koink). These 3 give the ecosystem API coverage for its core projects.

**Full design:** ~/otto/docs/oneon-remaining-integrations-architecture-2026-03-23.md

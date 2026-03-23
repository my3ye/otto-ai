---
name: ONEON/Tusita/SOS Phase 0 integrations review
description: End-to-end review of Koink+ONEON+Tusita+SOS (commit a0de0a0 + step-3 fixes, 2026-03-23)
type: project
---

## Pass 1 (commit a0de0a0): NEEDS_CHANGES

Critical: FK contradiction on proposer_id (NOT NULL + ON DELETE SET NULL). Voter weight uncapped.
Warnings: no auth on admin endpoints, list_proposals/list_cases missing offset, revenue_ytd naming.
Good: route ordering, UUID params, atomic transactions, feature flags default=false, WalletAdapter seam.

## Pass 2 (step-3 fixes + end-to-end review, 2026-03-23): NEEDS_CHANGES

**Critical:**
1. **Migration 072 broken on fresh DB** (`migrations/072_fix_oneon_tusita.sql:25`): Tries to `RENAME COLUMN revenue_ytd TO revenue_total` on `tusita_locations` — but migration 070 was corrected in-place to already create `revenue_total`. Fresh install runs 070→071→072; migration 072 will fail with "column revenue_ytd does not exist". Step-3 fix patched 070 directly but didn't remove/update 072.

**Warnings:**
2. **Admin guard before enabled guard** — `oneon.py:276-277`, `tusita.py:188-190`, `tusita.py:201-203`: `_require_admin()` raises 501 unconditionally before `_require_enabled()`. Disabled integrations return 501 instead of 503. Swap call order.
3. **Voter weight manipulation still open** — `oneon.py:100` `CastVoteRequest.weight=Field(ge=1, le=100)` with no auth guard. Flagged Pass 1, still unresolved. Any caller votes with weight 100.
4. **`list_locations` missing offset pagination** — `tusita/locations.py` function and route both lack `offset`. Inconsistent with ONEON/SOS equivalents.

**Good (new in Pass 2):**
- FK contradictions from Pass 1 fixed via migration 072 (RESTRICT on proposer_id, voter_id).
- revenue_ytd → revenue_total rename fixed (though migration path is broken as noted above).
- All 4 routers registered in api.py. All feature flags default False in config.py.
- UUID path params correct in all new routes (Koink previous critical fix verified still intact).
- Koink module clean — no regressions.

**Why:** In-place migration edits without updating the fix migration create broken fresh-install sequences. Always check migration order when a fix modifies both a prior migration AND creates a new one.
**How to apply:** flag migration 072 line 25 as needing IF EXISTS guard or removal before next DB setup.

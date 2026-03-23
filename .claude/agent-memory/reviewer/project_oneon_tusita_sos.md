---
name: ONEON/Tusita/SOS Phase 0 integrations review
description: Review of commit a0de0a0 — ONEON identity, Tusita locations, SOS Systems modules + WalletAdapter (2026-03-23)
type: project
---

Verdict: NEEDS_CHANGES (2 critical, 3 warnings, 4 suggestions)

**Critical:**
1. `oneon_governance_proposals.proposer_id` is `NOT NULL` but FK is `ON DELETE SET NULL` — contradictory. Deleting an identity with proposals will fail at runtime with a constraint violation. Fix: change FK to `ON DELETE RESTRICT` (can't delete a proposer) or remove `NOT NULL` to allow NULL.
2. `CastVoteRequest.weight: int = 1` is caller-supplied with no server-side cap. Open governance manipulation vector for Phase 1 — anyone votes with weight=999999.

**Warnings:**
1. No auth on admin endpoints: `PUT /oneon/governance/proposals/{id}/status`, `PUT /tusita/locations/{id}/status`, `POST /tusita/locations/{id}/revenue`. Feature flags=false masks this in Phase 0, but needs auth guards before enable.
2. `list_proposals` and `list_cases` have no `offset` parameter — can't paginate past limit.
3. `revenue_ytd` increments forever with no year-reset — naming misleading for long-running use.

**Good patterns:**
- Route ordering correct: `/by-handle/{handle}` and `/by-slug/{slug}` declared before `/{id}` routes in all 3 routers.
- UUID path params used throughout — no 500s from invalid IDs.
- Atomic transactions for vote tallying and XP/tier advancement.
- Feature flags default=false — safe to deploy, nothing active until explicitly enabled.
- WalletAdapter seam clean — NullWalletAdapter raises NotImplementedError, ready for OWS Phase 1 swap.

**Why:** governance weight manipulation is a classic Phase 0→1 transition trap — looks fine in testing, breaks badly with real users.
**How to apply:** flag voter weight capping and admin auth as pre-Phase-1 requirements before ONEON_ENABLED=true.

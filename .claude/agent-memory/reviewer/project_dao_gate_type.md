---
name: DAO gate type implementation review
description: DAO-in-the-loop gate type review — dao_module.py dead code, tally logic quadruplicated, early rejection flaw
type: project
---

DAO gate type (WF Step 2 Code Review, 2026-03-24): NEEDS_CHANGES (2 critical, 3 warnings).

**Critical:**
1. `dao_module.py` is entirely dead code — `LocalDAOModule`, `cast_vote`, `compute_tally`, `get_votes`, and `get_dao_module()` are never imported by workflows.py or any other file. The vote UPSERT and tally logic was reimplemented inline in workflows.py.
2. Tally computation (approve_w, reject_w, approve_pct, threshold) is copy-pasted 4 times: `dao_module.compute_tally`, `_check_dao_quorum`, `get_gate`, `get_pending_gate`. Divergence guaranteed over time.

**Warnings:**
1. Early rejection in `_check_dao_quorum` (`reject_pct > (1 - threshold)`) fires without a closed voter pool. Phase 1 allows unlimited new voters — a gate with quorum=2, threshold=0.5 can auto-reject with 2 reject votes even though a 3rd voter could approve. Architecturally unsound for open-registration DAO.
2. `voter_address` field accepts empty string. `weight` has no upper bound — same unconstrained voter weight issue flagged in ONEON/Tusita SOS review.
3. No auth on `/gates/{id}/vote` or `/gates/{id}/resolve` — flagged in security audit, still present.

**Why:** dao_module.py was designed as a clean protocol module, but the implementer re-coded the logic inline for speed. Both copies now exist independently.

**How to apply:** When reviewing modules that are described as "protocol modules" or "external adapters", verify they are actually imported. Dead protocol modules are a recurring pattern in this codebase.

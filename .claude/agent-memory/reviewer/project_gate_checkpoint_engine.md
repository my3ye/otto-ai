---
name: project_gate_checkpoint_engine
description: Gate checkpoint engine review (commit f69f938, 2026-03-24): NEEDS_CHANGES. 2 critical issues — skip_step unimplemented, pre-gate bypasses gate_notifier. 4 warnings.
type: project
---

Gate checkpoint engine Phase 1 review (commit f69f938, 2026-03-24).

**VERDICT: NEEDS_CHANGES (2 critical, 4 warnings)**

**Why:** Implementation is structurally sound and matches the architecture spec. Migration applied, endpoints live, gate engine functions correct for the approve/reject path. Two bugs prevent production-readiness.

**Critical Issues:**
1. `on_rejection: "skip_step"` is a no-op — falls through to `fail_workflow` at line 1619 (`else:  # fail_workflow (default) or skip_step`). Any template using skip_step policy will incorrectly fail the entire workflow.
2. Pre-step gate notification in `_advance_workflow` (line 789) calls `_whastsapp_notify(msg)` directly instead of `gate_notifier.gate_pending()`. Webhook subscribers miss ALL pre-gate creation events. Post-step gates correctly use `gate_notifier.gate_pending()` — the inconsistency is in the pre-step path only.

**Warnings:**
3. Duplicate tally logic: `_check_dao_quorum()` includes abstain in `total_weight` denominator; `dao_module.compute_tally()` excludes abstain (correct). The vote endpoint uses `_check_dao_quorum`, so abstain votes dilute approval percentage. Should use `dao_module.compute_tally()` consistently.
4. `get_dao_module` imported at line 29 but never called — dead import.
5. No DB-level UNIQUE constraint on (instance_id, step_position, gate_position, status='pending') — double-gate protection is application-level only. Asyncio race via two simultaneous `create_task(_advance_workflow)` calls could create duplicate pre-gates.
6. `list_gates` and `list_instance_gates` return `dict(r)` without `_row_to_dict` processing — inconsistent with rest of API (FastAPI handles the types, so no crash, but inconsistent).

**Pattern noted:** Pre-step gate creation path was wired separately from the notification task's work on post-step notifications. Always check both pre and post gate code paths when reviewing gating code.

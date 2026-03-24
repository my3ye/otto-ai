---
name: Gate Resume API + Workflow Config Schema Review
description: Code review of gate resume API, config schema endpoints, and OMS approve/reject bug fix (commit 18aa16e, 2026-03-24)
type: project
---

Gate Resume API review (commit 18aa16e, 2026-03-24): NEEDS_CHANGES.

**Why:** 2 issues found, 1 confirmed duplicate-error bug in validate endpoint.

**How to apply:** Fix both before marking this step approved.

## Confirmed Bug: Duplicate gate validation errors in `POST /templates/validate`

`workflows.py` lines 262-286: The validate loop first calls `StepSpec(**step)` (which internally validates `GateConfig`), then explicitly calls `GateConfig(**gate)` on the same data. Gate validation errors are reported **twice** — once from StepSpec with loc `('gate', 'field')` and once from GateConfig with loc `('field',)` (prefixed to `gate.field`). Verified with Python test.

Fix: skip the explicit `GateConfig(**gate)` call — StepSpec validation already covers it. Keep the timeout warning check (that's independent and correct).

## Warning: Double template DB fetch in `get_pending_gate`

`workflows.py` lines 588-593 and 604-611: Template is fetched twice from DB when `gate_position == "pre"` — once for prompt preview, once for step_name. Endpoint is polled every 10s by the OMS (GateContextPanel useApi).

Fix: cache `tmpl` in a variable before the if/else block and reuse it.

## What's good
- `decision`/`action` alias fix is clean and backward-compatible
- Route ordering verified: `/templates/schema`, `/templates/validate` before `/templates/{template_id}`; `/instances/{id}/gate` after `/instances/{id}` (different path depths — no conflict)
- `context_snapshot` truncated at 5000 chars to avoid bloat
- `seconds_remaining = max(0, ...)` prevents negative countdown
- Frontend polling guard `enabled: instance?.status === "paused"` is correct
- Abstain votes excluded from tally denominator consistently
- TypeScript types (PendingGateSummary, GateTally, PendingGateDetail) accurately match API response

## Minor
- `TemplateValidateRequest.name: str = "validate"` — default never used in logic (dead field)
- `action`/`decision` fields not constrained with `Literal["approve","reject","skip"]` — consistent with existing pattern but worth noting

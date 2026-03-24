---
name: Gate Resume API and Workflow Config Schema Architecture
description: Architecture for gate resume API (bug fix + new endpoints) and workflow config schema validation. 3 gaps identified, no migration needed.
type: project
---

Three gaps in gating system completion (2026-03-24):

1. **CRITICAL BUG** — OMS sends `{decision: "approve|reject|skip"}` but `WorkflowApproveRequest` reads `action` field (default `"approve"`). Reject/Skip buttons on OMS actually approve the gate. Fix: add `model_validator` to accept `decision` as alias.

2. **Missing GET /instances/{id}/gate** — Returns current pending gate with context_snapshot + DAO tally. Needed for OMS to show what Mev is actually approving.

3. **No template validation** — Add `GET /templates/schema` (Pydantic v2 `model_json_schema()`) and `POST /templates/validate` for pre-save validation.

**Why:** Bug causes incorrect gate resolution; context panel needed for usable approvals; schema endpoint needed for OMS workflow builder.
**How to apply:** Implementation step follows this arch step. Files: `workflows.py` + `detail/page.tsx`. No migration. ~350 lines total. ~$3 budget. Full doc at `~/otto/docs/gate-resume-api-architecture-2026-03-24.md`.

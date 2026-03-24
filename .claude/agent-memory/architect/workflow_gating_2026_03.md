---
name: workflow_gating_system_2026_03
description: Workflow gating system architecture designed 2026-03-24. Gate data model, state machine, DAO voting, timeout handling, notification interface.
type: project
---

Workflow gating system architecture designed 2026-03-24.

**Why:** Mev requested configurable Human-in-the-Loop / DAO-in-the-Loop gates at any step in workflow pipelines. Existing engine had only implicit single-step human_approval with no audit trail, no timeout, and no DAO support.

**Key decisions:**
- Gate records as first-class DB entities (`workflow_gates` table) — not JSONB blobs in instances
- Overlay pattern: `review_mode: "human_approval"` auto-creates a gate record (backward compat)
- Two gate positions: `pre` (before step runs) and `post` (after step output)
- Two gate types: `human` (Mev via OMS/WhatsApp) and `dao` (weighted votes)
- `timeout_action: escalate` as default (re-notify + extend 1h) — safer than auto-resolve
- Phase 1 DAO = local votes in `workflow_gate_votes` table; Phase 2 = on-chain SOS contracts
- `GateNotifier` and `DAOVotingModule` as Protocol interfaces (pluggable, swappable)

**Migration:** 074 (workflow_gates + workflow_gate_votes + pending_gate_id on workflow_instances)

**New API endpoints:** GET /workflows/gates, GET /workflows/gates/{id}, POST /workflows/gates/{id}/resolve, POST /workflows/gates/{id}/vote

**Full spec:** ~/otto/docs/workflow-gating-architecture-2026-03-24.md

**Implementation plan written (2026-03-24):** ~/otto/docs/gating-implementation-plan-2026-03-24.md
- Phase 1 scope: human gates (pre + post), migration 074, 6 new API endpoints, backward-compat with review_mode=human_approval
- Critical codebase note: `timedelta` and `Protocol` not currently imported in workflows.py — must add
- Integration points: `_advance_workflow` line 564 (pre-gate), `handle_step_completion` lines 720-743 (replace review_mode block), `approve_step` line 396 (delegate to _resolve_gate)
- New helper: `_whastsapp_notify()` extracts inline WhatsApp subprocess calls

**How to apply:** When building the implementation, follow the spec exactly. Migration 074 runs first. Phase 1 covers human+post-step gates. Pre-step + DAO are Phase 2.

# Gate Resume API + Workflow Config Schema — Architecture
*Architect: Otto | Date: 2026-03-24*

---

## Design: Gate Resume API + Workflow Config Schema

### Problem

The gating system (migration 074, gate engine, notifications, DAO gates) is implemented.
Three gaps remain before it's production-usable:

**1. Critical Bug — OMS always approves regardless of Reject/Skip click**
The OMS `handleAction` sends `{decision: "approve|reject|skip"}` but the API
`WorkflowApproveRequest` model reads the `action` field (default `"approve"`).
The `decision` field is ignored. Result: clicking Reject or Skip on the OMS
actually approves the gate. Any workflow paused at a gate cannot be rejected
via the OMS UI.

**2. Missing gate context panel in OMS**
When a workflow is paused at a gate, the OMS shows Approve/Reject/Skip buttons
but no context: what step output is being reviewed? What prompt is about to run?
For DAO gates: what's the vote tally? How much time is left before timeout?
The `context_snapshot` data exists in the DB but no endpoint surfaces it cleanly
for the OMS panel.

**3. No workflow template validation**
Templates are stored as raw JSONB. No API validates a template structure before
saving. Template authors (OMS workflow builder, future SDK) have no machine-
readable schema to validate against. Malformed templates fail silently at runtime.

---

### Approach

Three targeted changes — no new infrastructure, all in existing files.

#### Change 1: Fix the approve/reject/skip bug (critical)

**Backend fix** — `WorkflowApproveRequest` accept both `action` and `decision`:

```python
class WorkflowApproveRequest(BaseModel):
    action: str = "approve"         # approve | reject | skip
    decision: Optional[str] = None  # OMS alias for action (legacy compat)
    reason: Optional[str] = None

    @model_validator(mode="after")
    def resolve_action(self):
        # Accept decision as alias for action (OMS sends decision, not action)
        if self.decision and self.action == "approve":
            self.action = self.decision
        return self
```

This is backward-compatible. `action` field still works; `decision` field is an
alias that takes precedence when action isn't explicitly set. One-line backend
fix, no OMS change required.

#### Change 2: Gate Resume API — pending gate detail endpoint

New endpoint: `GET /workflows/instances/{id}/gate`

Returns the current pending gate with full context for the OMS approval panel.
The `context_snapshot` field contains the step output (post-gate) or input
prompt (pre-gate) that the approver needs to see.

```python
@router.get("/instances/{instance_id}/gate")
async def get_pending_gate(instance_id: UUID):
    """Get the currently pending gate for a paused workflow instance.
    Returns gate details with context_snapshot and DAO tally if applicable.
    404 if no pending gate exists.
    """
```

Response shape:
```json
{
  "gate_id": "uuid",
  "gate_type": "human | dao",
  "gate_position": "pre | post",
  "step_position": 2,
  "step_name": "Security Audit",
  "status": "pending",
  "expires_at": "2026-03-25T05:00:00Z",
  "seconds_remaining": 82800,
  "timeout_action": "escalate",
  "context_snapshot": {
    "step_output": "...",     // for post-gate
    "prompt_preview": "...",   // for pre-gate
    "variables": {}
  },
  "tally": null,             // null for human gates; populated for DAO
  "created_at": "..."
}
```

For DAO gates, `tally` is populated via `_check_dao_quorum()`:
```json
"tally": {
  "vote_count": 3,
  "approve_weight": 2.0,
  "reject_weight": 1.0,
  "approve_pct": 0.6667,
  "quorum_required": 3,
  "quorum_reached": true,
  "threshold": 0.5,
  "threshold_met": true
}
```

**Enrich `GET /instances/{id}` response**: Add `pending_gate_summary` when there's
a pending gate. This lets the OMS instance view show a gate status indicator
without a separate API call.

```json
// Added to GET /instances/{id} response when status = "paused":
"pending_gate_summary": {
  "gate_id": "uuid",
  "gate_type": "human",
  "gate_position": "post",
  "expires_at": "2026-03-25T05:00:00Z",
  "seconds_remaining": 82800
}
```

#### Change 3: Workflow Config Schema

Two new endpoints:

**`GET /workflows/templates/schema`**
Returns the JSON Schema for a workflow template, derived from Pydantic models.
Used by OMS workflow builder and external template tools.

```python
@router.get("/templates/schema")
async def get_template_schema():
    """Return JSON Schema for workflow template structure (StepSpec + GateConfig)."""
    return {
        "template": TemplateCreate.model_json_schema(),
        "step": StepSpec.model_json_schema(),
        "gate": GateConfig.model_json_schema(),
        "version": "1.0",
    }
```

**`POST /workflows/templates/validate`**
Validates a template config before saving. Returns structured errors.

```python
class TemplateValidateRequest(BaseModel):
    name: str
    steps: List[dict]   # raw dicts — we validate them

@router.post("/templates/validate")
async def validate_template(req: TemplateValidateRequest):
    """Validate a workflow template config. Returns errors and warnings."""
    errors = []
    warnings = []

    for i, step in enumerate(req.steps):
        try:
            StepSpec(**step)
        except ValidationError as e:
            for err in e.errors():
                errors.append({
                    "step": i,
                    "field": ".".join(str(x) for x in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                })
        # Gate config validation
        gate = step.get("gate")
        if gate:
            try:
                GateConfig(**gate)
            except ValidationError as e:
                for err in e.errors():
                    errors.append({
                        "step": i,
                        "field": "gate." + ".".join(str(x) for x in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"],
                    })
            # Warn if gate timeout < 10 minutes (operational risk)
            if gate.get("timeout_seconds", 86400) < 600:
                warnings.append({
                    "step": i,
                    "field": "gate.timeout_seconds",
                    "message": f"Timeout {gate['timeout_seconds']}s is less than 600s. "
                               "Otto's heartbeat runs every 30 minutes — short timeouts may "
                               "not be processed in time.",
                })

    return {
        "valid": len(errors) == 0,
        "step_count": len(req.steps),
        "errors": errors,
        "warnings": warnings,
    }
```

---

### Key Decisions

- **Backend-only fix for decision/action bug**: Accept both `decision` and `action`
  in `WorkflowApproveRequest`. Alternative: fix the OMS JS. Backend fix is safer
  (no deploy required, backward-compatible, protects against other callers).

- **New endpoint vs enrich existing**: `GET /instances/{id}/gate` as a separate
  endpoint (not embedded in instance response). Reason: the context_snapshot can
  be large (3KB+). The instance list page shouldn't pay that cost. Clients that
  need the full gate context call the dedicated endpoint. The instance response
  only gets a lightweight `pending_gate_summary`.

- **Pydantic `model_json_schema()` for schema endpoint**: Auto-derived from
  existing models. No separate schema maintenance burden. Alternative: hand-write
  JSON Schema — rejected (drift risk).

- **No new migration needed**: All changes are API layer only. The DB schema (074)
  is already correct.

---

### API Contract Summary

| Method | Endpoint | New/Changed |
|--------|----------|-------------|
| POST | `/workflows/instances/{id}/approve` | Fixed: accepts `decision` as alias |
| GET  | `/workflows/instances/{id}/gate`    | **New**: pending gate with context |
| GET  | `/workflows/instances/{id}`         | Enhanced: includes `pending_gate_summary` |
| GET  | `/workflows/templates/schema`       | **New**: JSON Schema for templates |
| POST | `/workflows/templates/validate`     | **New**: validate template before save |

---

### Files to Modify

1. **`otto/memory/routes/workflows.py`** (primary)
   - Add `@model_validator` to `WorkflowApproveRequest` (fix decision/action bug)
   - Add `TemplateValidateRequest` Pydantic model
   - Add `GET /instances/{id}/gate` endpoint (~40 lines)
   - Enrich `GET /instances/{id}` response with `pending_gate_summary` (~15 lines)
   - Add `GET /templates/schema` endpoint (~15 lines)
   - Add `POST /templates/validate` endpoint (~50 lines)

2. **`interfaces/web-next/src/app/workflows/detail/page.tsx`** (OMS UI)
   - Add gate context panel when `instance.status === "paused"` (shows context_snapshot)
   - Add DAO tally bar for DAO gates
   - Add expiry countdown
   - Use `GET /instances/{id}/gate` for data
   - Uses shadcn/ui: `Card`, `Badge`, `Progress`, `Alert`, `Separator`

---

### Implementation Plan

1. **[backend]** Fix `WorkflowApproveRequest` — add `decision` alias + model_validator
2. **[backend]** Add `GET /instances/{id}/gate` endpoint (pending gate + context + tally)
3. **[backend]** Enrich `GET /instances/{id}` with `pending_gate_summary`
4. **[backend]** Add `GET /templates/schema` endpoint
5. **[backend]** Add `TemplateValidateRequest` + `POST /templates/validate` endpoint
6. **[frontend]** Fetch gate context when workflow is paused (`/instances/{id}/gate`)
7. **[frontend]** Render gate context panel: context_snapshot preview, expiry, gate type
8. **[frontend]** For DAO gates: render vote tally bar with Progress component
9. **[frontend]** Add `Alert` for escalation warning (<1h remaining)
10. **[test]** Verify OMS Reject/Skip now correctly reject/skip a paused gate

Total estimate: ~200 lines backend, ~150 lines frontend. No migration. ~$3 budget.

---

### Risks

- **`model_json_schema()` availability**: Pydantic v1 uses `.schema()`, v2 uses
  `model_json_schema()`. Check which version is installed. Fallback: use `.schema()`.
- **Gate context panel performance**: If `context_snapshot` is large (50KB+),
  the frontend panel could be slow. Mitigation: truncate context display to 5000
  chars with "Show more" expansion.
- **Route ordering**: FastAPI route `GET /instances/{id}/gate` must be registered
  BEFORE `GET /instances/{id}/{action}` patterns. Verify no shadowing.

---

*Implementation: `otto/memory/routes/workflows.py` + `interfaces/web-next/src/app/workflows/detail/page.tsx`*
*No migration required — all API layer changes*
*Prerequisite: Migration 074 (workflow_gates) — already applied*

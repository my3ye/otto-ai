# Workflow Gating System — Architecture Spec
*Architect: Otto | Date: 2026-03-24*

---

## Design: Workflow Gating System

### Problem

The existing workflow engine supports a single implicit gate: `review_mode: "human_approval"` on a step. When a step completes with that mode, the workflow pauses and Otto sends a WhatsApp ping to Mev. Approval is via `POST /workflows/instances/{id}/approve`.

This works for simple human-in-the-loop but is insufficient for:

1. **DAO gates** — approval by a quorum of token holders, not just Mev
2. **Pre-step gates** — review the *input* (prompt, variables) before an agent runs
3. **Timeout handling** — gates that wait forever are a reliability hazard
4. **Gate audit trail** — no record of who approved what, when, and why
5. **Multi-gate workflows** — workflows with several checkpoints need individual gate tracking
6. **Notification abstraction** — WhatsApp hardcoded; OMS and on-chain notification missing

---

### Approach

The gating system is an **overlay** on the existing workflow engine, not a replacement. The state machine stays the same (`pending → running → paused → running → completed`). Gates are first-class records that own the pause/resume lifecycle.

**Core principle**: every pause in a workflow is now backed by a `workflow_gate` row. The gate owns the timeout clock, the resolution record, and the approver identity.

#### Gate Placement Model

A gate can fire at two positions relative to a step:

| Position | Fires when | Use case |
|----------|-----------|----------|
| `pre`    | Before the step's task is created | Review the input prompt / variables before sending to an LLM agent |
| `post`   | After the step's task completes   | Review the agent output before continuing |

Both use the same gate record and resolution flow.

#### Gate Types

| Type    | Who resolves | Mechanism |
|---------|-------------|-----------|
| `human` | Mev (or any admin) | OMS UI button + WhatsApp reply |
| `dao`   | Token holders      | On-chain vote OR OMS weighted voting (Phase 1 = OMS only) |

---

### State Machine

```
Workflow execution hit a gate
          │
          ▼
    [gate_pending]  ──── timeout expires ────►  [gate_timed_out]
          │                                            │
          │                                    timeout_action:
          │                                      approve / reject
          │                                      skip / escalate
   resolved by approver
          │
     ┌────┴────┐
     ▼         ▼
[approved]  [rejected]
     │         │
  continue   apply
  workflow  on_rejection policy
              (fail_workflow | skip_step | retry_step)
```

Workflow-level state mirrors the gate:

```
workflow.status = 'running'
→ gate created → workflow.status = 'paused' + gate.status = 'pending'
→ gate approved → workflow.status = 'running' + gate.status = 'approved'
→ gate rejected → workflow.status = 'failed' (or next step per policy)
→ gate timed_out → apply timeout_action (see above)
```

---

### Data Model

#### Table: `workflow_gates`

```sql
CREATE TABLE workflow_gates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Owning workflow
    instance_id         UUID NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
    step_position       INTEGER NOT NULL,       -- which step (matches steps[N].position)
    gate_position       TEXT NOT NULL           -- 'pre' | 'post'
        CHECK (gate_position IN ('pre', 'post')),

    -- Gate identity
    gate_type           TEXT NOT NULL DEFAULT 'human'
        CHECK (gate_type IN ('human', 'dao')),

    -- Lifecycle
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'timed_out', 'skipped')),

    -- Timeout
    timeout_seconds     INTEGER NOT NULL DEFAULT 86400,  -- 24h default
    expires_at          TIMESTAMPTZ NOT NULL,             -- created_at + timeout_seconds
    timeout_action      TEXT NOT NULL DEFAULT 'escalate'
        CHECK (timeout_action IN ('approve', 'reject', 'skip', 'escalate')),

    -- DAO quorum config (ignored for human gates)
    quorum_required     INTEGER DEFAULT NULL,             -- min votes needed
    approval_threshold  NUMERIC(4,3) DEFAULT 0.500,       -- fraction of votes that must be 'approve'

    -- Resolution
    resolved_by         TEXT,                             -- wallet address, 'mev', agent ID
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT,

    -- Structured context for approvers
    context_snapshot    JSONB NOT NULL DEFAULT '{}',      -- step output, prompt, variables at gate time
    metadata            JSONB NOT NULL DEFAULT '{}',      -- extensible: dao_proposal_id, oms_notification_id, etc.

    -- Audit
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wf_gates_instance    ON workflow_gates(instance_id);
CREATE INDEX idx_wf_gates_status      ON workflow_gates(status) WHERE status = 'pending';
CREATE INDEX idx_wf_gates_expires     ON workflow_gates(expires_at) WHERE status = 'pending';
CREATE INDEX idx_wf_gates_step        ON workflow_gates(instance_id, step_position, gate_position);
```

#### Table: `workflow_gate_votes` (DAO only)

```sql
CREATE TABLE workflow_gate_votes (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id             UUID NOT NULL REFERENCES workflow_gates(id) ON DELETE CASCADE,

    voter_address       TEXT NOT NULL,          -- wallet address or user ID
    vote                TEXT NOT NULL
        CHECK (vote IN ('approve', 'reject', 'abstain')),
    weight              NUMERIC(18,8) NOT NULL DEFAULT 1.0,   -- voting power (token balance or 1.0 for equal)
    signature           TEXT,                                  -- on-chain signature (Phase 2)
    reason              TEXT,                                  -- optional comment

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One vote per address per gate
    UNIQUE (gate_id, voter_address)
);

CREATE INDEX idx_wf_gate_votes_gate ON workflow_gate_votes(gate_id);
```

#### StepSpec Extension (workflow_templates.steps JSONB)

Extend each step object with an optional `gate` config block:

```json
{
  "position": 2,
  "name": "Security Audit",
  "agent_type": "blockchain-security-auditor",
  "prompt_template": "...",
  "review_mode": "auto",

  "gate": {
    "type": "human",
    "position": "post",
    "timeout_seconds": 86400,
    "timeout_action": "escalate",
    "quorum_required": null,
    "approval_threshold": null,
    "context_fields": ["prev_output", "variables"]
  }
}
```

The `gate` block is optional. If absent, no gate fires. If present, `review_mode` is superseded by the gate config (the gate owns the pause/resume; `review_mode: "human_approval"` remains as a backward-compat alias that creates a `post` human gate with 24h timeout + escalate).

#### Pydantic Models (routes/workflows.py additions)

```python
class GateConfig(BaseModel):
    type: str = "human"                    # human | dao
    position: str = "post"                 # pre | post
    timeout_seconds: int = 86400
    timeout_action: str = "escalate"       # approve | reject | skip | escalate
    quorum_required: Optional[int] = None
    approval_threshold: float = 0.5
    context_fields: List[str] = Field(default_factory=lambda: ["prev_output"])

class StepSpec(BaseModel):
    # ... existing fields ...
    gate: Optional[GateConfig] = None      # NEW

class GateVoteRequest(BaseModel):
    vote: str                              # approve | reject | abstain
    reason: Optional[str] = None
    signature: Optional[str] = None
    weight: float = 1.0

class GateResolveRequest(BaseModel):
    action: str                            # approve | reject | skip
    reason: Optional[str] = None
    resolved_by: str = "mev"
```

---

### Gate Engine (Core Logic)

Three new functions inside `workflows.py`:

#### `_create_gate(pool, instance_id, step_position, gate_config, context_snapshot) → gate_id`

```python
async def _create_gate(pool, instance_id, step_position, gate_position,
                        gate_cfg: dict, context_snapshot: dict) -> UUID:
    """
    Insert a workflow_gate row, pause the workflow instance.
    Returns the gate ID.
    """
    timeout_s = gate_cfg.get("timeout_seconds", 86400)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)

    row = await pool.fetchrow("""
        INSERT INTO workflow_gates
            (instance_id, step_position, gate_position, gate_type,
             timeout_seconds, expires_at, timeout_action,
             quorum_required, approval_threshold,
             context_snapshot)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb)
        RETURNING id
    """,
        instance_id, step_position, gate_position,
        gate_cfg.get("type", "human"),
        timeout_s, expires_at,
        gate_cfg.get("timeout_action", "escalate"),
        gate_cfg.get("quorum_required"),
        gate_cfg.get("approval_threshold", 0.5),
        json.dumps(context_snapshot),
    )
    gate_id = row["id"]

    # Pause the workflow
    await pool.execute(
        """UPDATE workflow_instances
           SET status = 'paused',
               metadata = jsonb_set(
                   COALESCE(metadata, '{}')::jsonb,
                   '{pending_gate_id}',
                   to_jsonb($2::text)
               )
           WHERE id = $1""",
        instance_id, str(gate_id),
    )

    return gate_id
```

#### `_resolve_gate(pool, gate_id, action, resolved_by, reason) → resolution_data`

```python
async def _resolve_gate(pool, gate_id: UUID, action: str,
                         resolved_by: str, reason: str = None) -> dict:
    """
    Resolve a gate (approve/reject/skip). Updates gate row and
    resumes or fails the workflow accordingly.
    Returns {"gate_status": ..., "workflow_action": ...}
    """
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    if not gate:
        raise ValueError(f"Gate {gate_id} not found")
    if gate["status"] != "pending":
        raise ValueError(f"Gate {gate_id} is {gate['status']}, not pending")

    # Map action → gate status
    status_map = {"approve": "approved", "reject": "rejected", "skip": "skipped"}
    gate_status = status_map.get(action)
    if not gate_status:
        raise ValueError(f"Unknown action: {action}")

    # Persist resolution
    await pool.execute("""
        UPDATE workflow_gates
        SET status = $2, resolved_by = $3, resolved_at = now(), resolution_reason = $4
        WHERE id = $1
    """, gate_id, gate_status, resolved_by, reason)

    # Resume or fail workflow
    instance_id = gate["instance_id"]
    step_position = gate["step_position"]
    gate_position = gate["gate_position"]

    if action == "approve":
        if gate_position == "pre":
            # Gate was pre-step: now run the step
            await pool.execute(
                "UPDATE workflow_instances SET status = 'running' WHERE id = $1",
                instance_id,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))
        else:
            # Gate was post-step: advance to next step
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'running', current_step = current_step + 1
                   WHERE id = $1""",
                instance_id,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))

    elif action == "skip":
        # Record as skipped output, advance
        inst = await pool.fetchrow(
            "SELECT step_outputs, current_step FROM workflow_instances WHERE id = $1",
            instance_id,
        )
        step_outputs = _jsonb(inst["step_outputs"])
        step_outputs[str(step_position)] = f"[GATE-SKIPPED] {reason or ''}"
        await pool.execute(
            """UPDATE workflow_instances
               SET status = 'running',
                   current_step = current_step + 1,
                   step_outputs = $2::jsonb
               WHERE id = $1""",
            instance_id, json.dumps(step_outputs),
        )
        asyncio.create_task(_advance_workflow(pool, instance_id))

    elif action == "reject":
        inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
        tmpl = await pool.fetchrow("SELECT steps FROM workflow_templates WHERE id = $1", inst["template_id"])
        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        step = steps[step_position] if step_position < len(steps) else {}
        on_rejection = step.get("gate", {}).get("on_rejection", "fail_workflow")

        if on_rejection == "fail_workflow":
            await pool.execute(
                "UPDATE workflow_instances SET status = 'failed', error = $2, completed_at = now() WHERE id = $1",
                instance_id, f"Gate rejected: {reason or 'no reason'}",
            )
        elif on_rejection == "retry_step":
            # Reset current_step to step_position and re-run
            await pool.execute(
                "UPDATE workflow_instances SET status = 'running', current_step = $2 WHERE id = $1",
                instance_id, step_position,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))

    return {"gate_status": gate_status, "workflow_action": action}
```

#### `_check_gate_timeouts(pool)` — called by heartbeat/reflection

```python
async def _check_gate_timeouts(pool):
    """
    Poll for expired pending gates and apply their timeout_action.
    Called every heartbeat cycle (every 30 minutes minimum).
    """
    expired = await pool.fetch("""
        SELECT g.*, wi.name as workflow_name
        FROM workflow_gates g
        JOIN workflow_instances wi ON wi.id = g.instance_id
        WHERE g.status = 'pending' AND g.expires_at < now()
    """)

    for gate in expired:
        action = gate["timeout_action"]
        gate_id = gate["id"]
        log.warning(f"Gate {gate_id} timed out (action={action}, workflow={gate['workflow_name']})")

        if action == "escalate":
            # Send escalation notification and extend by 1h
            await pool.execute("""
                UPDATE workflow_gates
                SET expires_at = now() + interval '1 hour',
                    metadata = jsonb_set(COALESCE(metadata, '{}')::jsonb,
                                         '{escalated_at}',
                                         to_jsonb(now()::text))
                WHERE id = $1
            """, gate_id)
            await _notify_gate_escalated(gate)
        else:
            # Auto-resolve with the configured action
            await _resolve_gate(pool, gate_id, action, "system:timeout")
```

#### DAO Gate: Vote Tally Check

```python
async def _check_dao_quorum(pool, gate_id: UUID) -> dict:
    """
    Compute vote tally for a DAO gate. If quorum + threshold reached,
    auto-resolve the gate.
    Returns tally dict.
    """
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    votes = await pool.fetch(
        "SELECT vote, weight FROM workflow_gate_votes WHERE gate_id = $1", gate_id
    )

    approve_weight = sum(v["weight"] for v in votes if v["vote"] == "approve")
    reject_weight  = sum(v["weight"] for v in votes if v["vote"] == "reject")
    total_weight   = sum(v["weight"] for v in votes)
    vote_count     = len(votes)

    quorum_needed    = gate["quorum_required"] or 1
    threshold        = float(gate["approval_threshold"] or 0.5)
    quorum_reached   = vote_count >= quorum_needed
    threshold_met    = (approve_weight / max(total_weight, 1)) >= threshold

    tally = {
        "vote_count": vote_count,
        "approve_weight": float(approve_weight),
        "reject_weight": float(reject_weight),
        "total_weight": float(total_weight),
        "quorum_reached": quorum_reached,
        "threshold_met": threshold_met,
    }

    if quorum_reached:
        if threshold_met:
            await _resolve_gate(pool, gate_id, "approve", "dao:quorum")
        else:
            await _resolve_gate(pool, gate_id, "reject", "dao:quorum")

    return tally
```

---

### API Endpoints (New)

```
GET  /workflows/gates                              — list gates (filter: instance_id, status)
GET  /workflows/gates/{gate_id}                    — gate detail + vote tally
POST /workflows/gates/{gate_id}/resolve            — admin resolve (approve/reject/skip)
POST /workflows/gates/{gate_id}/vote               — cast a vote (DAO gates)
GET  /workflows/instances/{id}/gates               — all gates for a workflow instance
```

Existing endpoint kept for backward compatibility:
```
POST /workflows/instances/{id}/approve             — wraps _resolve_gate() internally
```

#### GET /workflows/gates

```python
@router.get("/gates")
async def list_gates(
    instance_id: Optional[str] = None,
    status: Optional[str] = None,
    gate_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    ...
```

#### POST /workflows/gates/{gate_id}/resolve

Request:
```json
{"action": "approve", "reason": "Looks good", "resolved_by": "mev"}
```

Response:
```json
{"gate_id": "...", "gate_status": "approved", "workflow_action": "approve"}
```

#### POST /workflows/gates/{gate_id}/vote (DAO)

Request:
```json
{"vote": "approve", "reason": "Strong architecture", "signature": "0x...", "weight": 100.0}
```

Response:
```json
{
  "vote_id": "...",
  "tally": {
    "vote_count": 3,
    "approve_weight": 250.0,
    "reject_weight": 50.0,
    "quorum_reached": true,
    "threshold_met": false
  }
}
```

---

### Notification Interface

Abstract the notification layer so it's pluggable.

```python
from typing import Protocol

class GateNotifier(Protocol):
    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None:
        """Notify that a gate is waiting for approval."""
        ...

    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None:
        """Notify that a gate was resolved."""
        ...

    async def gate_escalated(self, gate: dict, instance: dict) -> None:
        """Notify that a gate timed out and is escalating."""
        ...


class WhatsAppGateNotifier:
    """Default notifier — sends to Mev via WhatsApp."""

    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None:
        gate_type = gate["gate_type"]
        step_name = step.get("name", f"Step {gate['step_position']}")
        position  = gate["gate_position"]

        if gate_type == "human":
            msg = (
                f"🔒 Gate pending: '{instance['name']}'\n"
                f"Step: {step_name} ({position}-step)\n"
                f"Approve: POST /workflows/gates/{gate['id']}/resolve\n"
                f"Expires: {gate['expires_at'][:19]} UTC"
            )
        else:  # dao
            msg = (
                f"🗳️ DAO vote open: '{instance['name']}'\n"
                f"Step: {step_name}\n"
                f"Quorum needed: {gate['quorum_required']}\n"
                f"Vote: POST /workflows/gates/{gate['id']}/vote"
            )
        await _send_whatsapp(msg)

    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None:
        msg = (
            f"{'✅' if resolution == 'approved' else '❌'} Gate {resolution}: '{instance['name']}'\n"
            f"By: {gate['resolved_by']} | Step {gate['step_position']}"
        )
        await _send_whatsapp(msg)

    async def gate_escalated(self, gate: dict, instance: dict) -> None:
        msg = (
            f"⚠️ Gate timed out (escalated): '{instance['name']}'\n"
            f"Step {gate['step_position']} — extended 1h. Please review."
        )
        await _send_whatsapp(msg)


# OMS notifier stub (Phase 2)
class OMSGateNotifier:
    """Posts in-app notification to OMS notification feed."""
    async def gate_pending(self, gate, instance, step): ...
    async def gate_resolved(self, gate, instance, resolution): ...
    async def gate_escalated(self, gate, instance): ...


# Default notifier (can be swapped by config)
gate_notifier: GateNotifier = WhatsAppGateNotifier()
```

---

### DAO Module Interface

```python
class DAOVotingModule(Protocol):
    """
    Phase 1: OMS-based weighted voting (off-chain, signed)
    Phase 2: On-chain via SOS governance contracts
    """

    async def create_proposal(self, gate: dict, context: str) -> str:
        """Create a governance proposal. Returns proposal_id."""
        ...

    async def cast_vote(self, proposal_id: str, voter: str,
                        vote: str, weight: float, signature: str) -> dict:
        """Submit a vote. Returns updated tally."""
        ...

    async def get_tally(self, proposal_id: str) -> dict:
        """Returns {approve_weight, reject_weight, vote_count, quorum_reached, threshold_met}."""
        ...

    async def is_resolved(self, proposal_id: str) -> Optional[str]:
        """Returns 'approve'|'reject' if quorum+threshold reached, else None."""
        ...


class LocalDAOModule:
    """Phase 1 implementation: votes stored in workflow_gate_votes table."""

    async def create_proposal(self, gate: dict, context: str) -> str:
        # proposal_id = gate_id (no external system yet)
        return str(gate["id"])

    async def cast_vote(self, proposal_id, voter, vote, weight, signature):
        pool = await get_pool()
        # Upsert into workflow_gate_votes
        await pool.execute("""
            INSERT INTO workflow_gate_votes (gate_id, voter_address, vote, weight, signature)
            VALUES ($1::uuid, $2, $3, $4, $5)
            ON CONFLICT (gate_id, voter_address) DO UPDATE
                SET vote = EXCLUDED.vote, weight = EXCLUDED.weight
        """, proposal_id, voter, vote, weight, signature)
        return await self.get_tally(proposal_id)

    async def get_tally(self, proposal_id) -> dict:
        pool = await get_pool()
        return await _check_dao_quorum(pool, UUID(proposal_id))

    async def is_resolved(self, proposal_id) -> Optional[str]:
        pool = await get_pool()
        gate = await pool.fetchrow(
            "SELECT status FROM workflow_gates WHERE id = $1::uuid", proposal_id
        )
        if gate and gate["status"] in ("approved", "rejected"):
            return gate["status"]
        return None
```

---

### Integration into `_advance_workflow`

```python
async def _advance_workflow(pool, instance_id: UUID):
    ...
    step = steps[current]

    # ── PRE-STEP GATE ────────────────────────────────────────────────
    gate_cfg = step.get("gate") or {}
    if gate_cfg and gate_cfg.get("position", "post") == "pre":
        # Check if there's already an approved pre-gate for this step
        existing_gate = await pool.fetchrow("""
            SELECT status FROM workflow_gates
            WHERE instance_id = $1
              AND step_position = $2
              AND gate_position = 'pre'
            ORDER BY created_at DESC LIMIT 1
        """, instance_id, current)

        if not existing_gate:
            # No gate yet — create one and pause
            context = {
                "prompt_preview": _interpolate(step.get("prompt_template", ""), dict(inst))[:2000],
                "variables": dict(inst.get("variables") or {}),
            }
            gate_id = await _create_gate(pool, instance_id, current, "pre", gate_cfg, context)
            await gate_notifier.gate_pending(
                {"id": str(gate_id), **gate_cfg}, dict(inst), step
            )
            return  # Pause execution; resume when gate is resolved

        elif existing_gate["status"] != "approved":
            # Gate exists but not approved — still waiting
            return

    # Gate approved (or no pre-gate) → proceed with step execution
    ...
    # (existing task creation code)
    ...
```

### Integration into `handle_step_completion`

```python
async def handle_step_completion(pool, instance_id, task_id, task_status):
    ...
    if task_status == "completed":
        step = steps[current]
        gate_cfg = step.get("gate") or {}
        review_mode = step.get("review_mode", "auto")

        # Normalize: review_mode=human_approval → gate_cfg with defaults
        if not gate_cfg and review_mode == "human_approval":
            gate_cfg = {"type": "human", "position": "post",
                        "timeout_seconds": 86400, "timeout_action": "escalate"}

        if gate_cfg and gate_cfg.get("position", "post") == "post":
            # Check if approved gate already exists for this step
            existing = await pool.fetchrow("""
                SELECT status FROM workflow_gates
                WHERE instance_id = $1 AND step_position = $2 AND gate_position = 'post'
                ORDER BY created_at DESC LIMIT 1
            """, instance_id, current)

            if existing and existing["status"] == "approved":
                pass  # Already approved — fall through to advance
            else:
                # Create post-step gate
                context = {"step_output": output[:3000]}
                gate_id = await _create_gate(
                    pool, instance_id, current, "post", gate_cfg, context
                )
                # Also store step output for review
                step_outputs = _jsonb(inst["step_outputs"])
                step_outputs[str(current)] = output[:50000]
                await pool.execute(
                    "UPDATE workflow_instances SET step_outputs = $2::jsonb WHERE id = $1",
                    instance_id, json.dumps(step_outputs),
                )
                await gate_notifier.gate_pending(
                    {"id": str(gate_id), **gate_cfg}, dict(inst), step
                )
                return  # Pause; resume when gate resolved

        # No gate or already resolved → advance normally
        ...
```

---

### Migration 074

```sql
-- Migration 074: Workflow Gating System
-- Adds first-class gate records with timeout, DAO support, and audit trail.

BEGIN;

CREATE TABLE workflow_gates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instance_id         UUID NOT NULL REFERENCES workflow_instances(id) ON DELETE CASCADE,
    step_position       INTEGER NOT NULL,
    gate_position       TEXT NOT NULL DEFAULT 'post'
        CHECK (gate_position IN ('pre', 'post')),
    gate_type           TEXT NOT NULL DEFAULT 'human'
        CHECK (gate_type IN ('human', 'dao')),
    status              TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'approved', 'rejected', 'timed_out', 'skipped')),
    timeout_seconds     INTEGER NOT NULL DEFAULT 86400,
    expires_at          TIMESTAMPTZ NOT NULL,
    timeout_action      TEXT NOT NULL DEFAULT 'escalate'
        CHECK (timeout_action IN ('approve', 'reject', 'skip', 'escalate')),
    quorum_required     INTEGER,
    approval_threshold  NUMERIC(4,3) DEFAULT 0.500,
    resolved_by         TEXT,
    resolved_at         TIMESTAMPTZ,
    resolution_reason   TEXT,
    context_snapshot    JSONB NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_wf_gates_instance ON workflow_gates(instance_id);
CREATE INDEX idx_wf_gates_pending  ON workflow_gates(expires_at) WHERE status = 'pending';
CREATE INDEX idx_wf_gates_step     ON workflow_gates(instance_id, step_position, gate_position);

CREATE TABLE workflow_gate_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gate_id         UUID NOT NULL REFERENCES workflow_gates(id) ON DELETE CASCADE,
    voter_address   TEXT NOT NULL,
    vote            TEXT NOT NULL CHECK (vote IN ('approve', 'reject', 'abstain')),
    weight          NUMERIC(18,8) NOT NULL DEFAULT 1.0,
    signature       TEXT,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (gate_id, voter_address)
);

CREATE INDEX idx_wf_gate_votes_gate ON workflow_gate_votes(gate_id);

-- Add pending_gate_id to workflow_instances for fast lookup
ALTER TABLE workflow_instances
    ADD COLUMN IF NOT EXISTS pending_gate_id UUID REFERENCES workflow_gates(id) ON DELETE SET NULL;

COMMIT;
```

---

### Implementation Plan

#### Phase 1 — Core gates (human only, post-step)
1. **Migration 074** — run the SQL above
2. **Extend StepSpec** — add `gate: Optional[GateConfig]` field
3. **Gate engine functions** — `_create_gate`, `_resolve_gate`, `_check_gate_timeouts`
4. **GateNotifier interface** — `WhatsAppGateNotifier` implementation
5. **Modify `handle_step_completion`** — check for post-step gate config
6. **Update `/approve` endpoint** — delegate to `_resolve_gate` internally
7. **New API endpoints** — `GET /gates`, `GET /gates/{id}`, `POST /gates/{id}/resolve`
8. **Timeout checker** — add to reflection heartbeat's step 3 (infrastructure maintenance)
9. **OMS UI** — Gate approval panel on workflow detail page

#### Phase 2 — Pre-step gates + DAO
10. **Pre-step gate support** — modify `_advance_workflow` gate check
11. **DAO vote endpoint** — `POST /gates/{id}/vote`
12. **`LocalDAOModule`** — vote storage + tally computation
13. **Quorum auto-resolve** — after each vote, check if gate can be finalized
14. **OMS voting panel** — vote breakdown, weights, approve/reject buttons

#### Phase 3 — On-chain DAO (future)
15. **`OnchainDAOModule`** — integrate with SOS governance contracts
16. **Signature verification** — validate wallet signatures on votes
17. **Token-weight oracle** — query token balances for voting power

---

### Key Decisions

- **Gate records as first-class entities**: Chosen over embedding state in `workflow_instances.metadata`. Reasoning: independent audit trail, queryable timeout list, DAO vote association. Alternative: JSONB blob in instances — rejected (opaque, unindexable).

- **Overlay pattern (not replacement)**: Existing `review_mode: "human_approval"` becomes a backward-compat alias that auto-creates a gate record. No breaking change to existing templates. Alternative: migrate all templates — rejected (operational risk, existing templates work).

- **Pre-step and post-step positions**: Both needed. Pre-step gates let Mev/DAO review the AI prompt before it runs (high-value for security reviews, code deployments). Post-step gates let Mev/DAO review the output. Alternative: post-only — rejected (Mev specifically asked for input review capability).

- **`timeout_action: "escalate"` as default**: Auto-approve/reject on timeout is risky for sensitive gates. Escalate (re-notify + extend 1h) is safer. Operators can opt into `auto-approve` for low-stakes gates. Alternative: fail workflow on timeout — rejected (too disruptive for 24h gates that are just waiting for Mev).

- **Phase 1 DAO = local votes in PostgreSQL**: On-chain voting requires deployed contracts (SOS Phase 2). Phase 1 uses `workflow_gate_votes` table with weighted votes and optional signatures. Design is forward-compatible — `LocalDAOModule` is swapped for `OnchainDAOModule` when contracts deploy. Alternative: skip DAO entirely in Phase 1 — rejected (data model must support it now to avoid migration pain).

- **Single `gate_notifier` global**: Simple for Phase 1. When OMS notifications land, replace with `[WhatsAppGateNotifier(), OMSGateNotifier()]`. Alternative: per-gate notifier config — over-engineered for now.

---

### Risks

- **Timeout checker frequency**: Reflection runs at :30, heartbeat at :00 — max 30min lag before an expired gate is processed. For short timeouts (<30min), this is a known gap. **Mitigation**: don't configure timeouts under 30min; add `_check_gate_timeouts` call to task completion path for gates with timeout ≤ 3600s.

- **Gate + task concurrency**: Between `_create_gate` pausing the workflow and the task completing, there's a brief window where both a gate and a task completion can race. **Mitigation**: `handle_step_completion` checks for existing pending gates before creating a new one; database UNIQUE constraints prevent double gates.

- **DAO vote replay**: Without on-chain signatures, votes can be forged locally. **Mitigation**: Phase 1 is explicitly trust-based (OMS login required). Phase 2 adds signature verification.

- **On-chain latency (Phase 3)**: If SOS governance contracts are on a slow chain, gate resolution can take hours. **Mitigation**: DAO gate `timeout_action: "escalate"` auto-extends; `quorum_required` should be set conservatively for critical gates.

---

### OMS UI Contract

The OMS gate approval panel (workflow detail page) needs:

```
GET /workflows/instances/{id}/gates
→ [{gate_id, step_position, gate_position, gate_type, status, expires_at,
    context_snapshot, tally (for DAO)}]

POST /workflows/gates/{gate_id}/resolve  (human gates)
Body: {"action": "approve|reject|skip", "reason": "..."}

POST /workflows/gates/{gate_id}/vote   (DAO gates)
Body: {"vote": "approve|reject", "reason": "..."}
```

Gate card components (shadcn/ui):
- `Card` — gate container
- `Badge` — status pill (pending=yellow, approved=green, rejected=red)
- `Button` — Approve / Reject / Skip actions
- `Textarea` — reason input
- `Progress` — DAO vote tally bar (approve% vs reject%)
- `Tooltip` — voter list on hover
- `Alert` — escalation warning when < 1h to timeout

---

*Full doc: ~/otto/docs/workflow-gating-architecture-2026-03-24.md*
*Migration: 074*
*Implementation tasks: ~10 (Phase 1), ~5 (Phase 2)*

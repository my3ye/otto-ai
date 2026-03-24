# Gate Checkpoint Engine — Implementation Plan
*Otto | Step 0: Architecture & Planning | 2026-03-24*

---

## Summary

This document translates the workflow gating architecture spec into a precise, file-by-file implementation plan for the coder agent. It covers Phase 1 only (human gates, post-step + pre-step). DAO voting is scaffolded but not wired up.

**Source architecture spec**: `~/otto/docs/workflow-gating-architecture-2026-03-24.md`
**Primary file**: `~/otto/memory/routes/workflows.py` (1439 lines)
**Migration**: `074_workflow_gating.sql` (next available)

---

## File Changes

### 1. NEW: `memory/migrations/074_workflow_gating.sql`

Create this file wholesale (see SQL below). Run it via:
```bash
docker exec memory-postgres-1 psql -U otto -d memory -f /dev/stdin < ~/otto/memory/migrations/074_workflow_gating.sql
```

SQL content:
```sql
-- Migration 074: Workflow Gating System
-- Adds first-class gate records with timeout, DAO support, and audit trail.
BEGIN;

CREATE TABLE IF NOT EXISTS workflow_gates (
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

CREATE INDEX IF NOT EXISTS idx_wf_gates_instance ON workflow_gates(instance_id);
CREATE INDEX IF NOT EXISTS idx_wf_gates_pending  ON workflow_gates(expires_at) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_wf_gates_step     ON workflow_gates(instance_id, step_position, gate_position);

CREATE TABLE IF NOT EXISTS workflow_gate_votes (
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

CREATE INDEX IF NOT EXISTS idx_wf_gate_votes_gate ON workflow_gate_votes(gate_id);

-- Add pending_gate_id to workflow_instances for fast lookup
ALTER TABLE workflow_instances
    ADD COLUMN IF NOT EXISTS pending_gate_id UUID REFERENCES workflow_gates(id) ON DELETE SET NULL;

COMMIT;
```

---

### 2. MODIFY: `memory/routes/workflows.py`

#### 2a. Imports (line 20-21)

**Change**:
```python
# BEFORE
from datetime import datetime, timezone
from typing import Optional, List
```
```python
# AFTER
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Protocol
```

#### 2b. Pydantic Models (insert after WorkflowApproveRequest, ~line 86)

Add 3 new models and update `StepSpec`:

```python
class GateConfig(BaseModel):
    type: str = "human"                        # human | dao
    position: str = "post"                     # pre | post
    timeout_seconds: int = 86400               # 24h default
    timeout_action: str = "escalate"           # approve | reject | skip | escalate
    quorum_required: Optional[int] = None
    approval_threshold: float = 0.5
    context_fields: List[str] = Field(default_factory=lambda: ["prev_output"])
    on_rejection: str = "fail_workflow"        # fail_workflow | retry_step | skip_step


class GateResolveRequest(BaseModel):
    action: str                                # approve | reject | skip
    reason: Optional[str] = None
    resolved_by: str = "mev"


class GateVoteRequest(BaseModel):
    vote: str                                  # approve | reject | abstain
    reason: Optional[str] = None
    signature: Optional[str] = None
    weight: float = 1.0
```

And update `StepSpec` to add the `gate` field:
```python
# In StepSpec, after working_directory field:
    gate: Optional[GateConfig] = None          # NEW: gate config for this step
```

#### 2c. Gate Engine (insert after `_smart_truncate` helper, ~line 1237)

Insert the full gate engine block:

```python
# ── Gate Engine ─────────────────────────────────────────────────────────


async def _whastsapp_notify(msg: str) -> None:
    """Fire-and-forget WhatsApp notification."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "/home/web3relic/otto/tools/whatsapp_send.sh", msg,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
    except Exception as e:
        log.warning(f"WhatsApp gate notify failed: {e}")


async def _create_gate(
    pool, instance_id: UUID, step_position: int,
    gate_position: str, gate_cfg: dict, context_snapshot: dict
) -> UUID:
    """Insert a workflow_gate row, pause the workflow instance. Returns gate ID."""
    timeout_s = gate_cfg.get("timeout_seconds", 86400)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=timeout_s)

    row = await pool.fetchrow("""
        INSERT INTO workflow_gates
            (instance_id, step_position, gate_position, gate_type,
             timeout_seconds, expires_at, timeout_action,
             quorum_required, approval_threshold, context_snapshot)
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

    # Pause the workflow and record the pending gate
    await pool.execute(
        """UPDATE workflow_instances
           SET status = 'paused',
               pending_gate_id = $2
           WHERE id = $1""",
        instance_id, gate_id,
    )

    log.info(f"Gate {gate_id} created for workflow {instance_id} step {step_position} ({gate_position})")
    return gate_id


async def _resolve_gate(
    pool, gate_id: UUID, action: str,
    resolved_by: str, reason: str = None
) -> dict:
    """Resolve a gate (approve/reject/skip). Resumes or fails workflow. Returns resolution dict."""
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    if not gate:
        raise ValueError(f"Gate {gate_id} not found")
    if gate["status"] != "pending":
        raise ValueError(f"Gate {gate_id} is already {gate['status']}")

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

    # Clear pending_gate_id on the instance
    await pool.execute(
        "UPDATE workflow_instances SET pending_gate_id = NULL WHERE id = $1",
        gate["instance_id"],
    )

    instance_id = gate["instance_id"]
    step_position = gate["step_position"]
    gate_position = gate["gate_position"]

    if action == "approve":
        if gate_position == "pre":
            # Pre-gate approved → run the step now
            await pool.execute(
                "UPDATE workflow_instances SET status = 'running' WHERE id = $1",
                instance_id,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))
        else:
            # Post-gate approved → advance to next step
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'running', current_step = current_step + 1
                   WHERE id = $1""",
                instance_id,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))

    elif action == "skip":
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
        on_rejection = step.get("gate", {}).get("on_rejection", "fail_workflow") if step.get("gate") else "fail_workflow"

        if on_rejection == "retry_step":
            await pool.execute(
                "UPDATE workflow_instances SET status = 'running', current_step = $2 WHERE id = $1",
                instance_id, step_position,
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))
        else:  # fail_workflow (default) or skip_step
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'failed', error = $2, completed_at = now()
                   WHERE id = $1""",
                instance_id, f"Gate rejected: {reason or 'no reason'}",
            )

    return {"gate_id": str(gate_id), "gate_status": gate_status, "workflow_action": action}


async def _check_gate_timeouts(pool) -> int:
    """Poll for expired pending gates and apply their timeout_action.
    Returns number of gates processed.
    Called by reflection heartbeat every 30 min.
    """
    expired = await pool.fetch("""
        SELECT g.*, wi.name as workflow_name
        FROM workflow_gates g
        JOIN workflow_instances wi ON wi.id = g.instance_id
        WHERE g.status = 'pending' AND g.expires_at < now()
    """)

    processed = 0
    for gate in expired:
        action = gate["timeout_action"]
        gate_id = gate["id"]
        log.warning(f"Gate {gate_id} timed out (action={action}, workflow={gate['workflow_name']})")

        if action == "escalate":
            # Extend by 1 hour and re-notify
            await pool.execute("""
                UPDATE workflow_gates
                SET expires_at = now() + interval '1 hour',
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}')::jsonb,
                        '{escalated_at}',
                        to_jsonb(now()::text)
                    )
                WHERE id = $1
            """, gate_id)
            # Send escalation WhatsApp
            msg = (
                f"⚠️ Gate timed out (escalated): '{gate['workflow_name']}'\n"
                f"Step {gate['step_position']} — extended 1h. Please review.\n"
                f"Approve: POST /workflows/gates/{gate_id}/resolve"
            )
            asyncio.create_task(_whastsapp_notify(msg))
        else:
            # Auto-resolve with configured action (approve/reject/skip)
            try:
                await _resolve_gate(pool, gate_id, action, "system:timeout", "Auto-resolved on timeout")
            except Exception as e:
                log.error(f"Failed to auto-resolve gate {gate_id}: {e}")

        processed += 1

    return processed


async def _check_dao_quorum(pool, gate_id: UUID) -> dict:
    """Compute vote tally for a DAO gate. Auto-resolves if quorum + threshold reached."""
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    votes = await pool.fetch(
        "SELECT vote, weight FROM workflow_gate_votes WHERE gate_id = $1", gate_id
    )

    approve_weight = sum(float(v["weight"]) for v in votes if v["vote"] == "approve")
    reject_weight  = sum(float(v["weight"]) for v in votes if v["vote"] == "reject")
    total_weight   = sum(float(v["weight"]) for v in votes)
    vote_count     = len(votes)

    quorum_needed  = gate["quorum_required"] or 1
    threshold      = float(gate["approval_threshold"] or 0.5)
    quorum_reached = vote_count >= quorum_needed
    threshold_met  = (approve_weight / max(total_weight, 1)) >= threshold

    tally = {
        "vote_count": vote_count,
        "approve_weight": approve_weight,
        "reject_weight": reject_weight,
        "total_weight": total_weight,
        "quorum_reached": quorum_reached,
        "threshold_met": threshold_met,
    }

    if quorum_reached:
        if threshold_met:
            await _resolve_gate(pool, gate_id, "approve", "dao:quorum", "Quorum reached with approval threshold")
        else:
            await _resolve_gate(pool, gate_id, "reject", "dao:quorum", "Quorum reached but threshold not met")

    return tally
```

#### 2d. Pre-step gate check in `_advance_workflow` (insert after line 564: `step = steps[current]`)

```python
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
                # First time hitting this step — create pre-gate and pause
                context = {
                    "prompt_preview": _interpolate(step.get("prompt_template", ""), dict(inst))[:2000],
                    "variables": dict(_jsonb(inst.get("variables")) if inst.get("variables") else {}),
                    "step_name": step.get("name", f"Step {current}"),
                }
                gate_id = await _create_gate(pool, instance_id, current, "pre", gate_cfg, context)
                step_name = step.get("name", f"Step {current}")
                gate_type = gate_cfg.get("type", "human")
                if gate_type == "human":
                    msg = (
                        f"🔒 Pre-step gate: '{inst['name']}'\n"
                        f"Step: {step_name} (about to run)\n"
                        f"Review prompt before execution.\n"
                        f"Approve: POST /workflows/gates/{gate_id}/resolve"
                    )
                    asyncio.create_task(_whastsapp_notify(msg))
                return  # Pause — resume when gate is resolved

            elif existing_gate["status"] != "approved":
                # Gate exists but not approved yet — still waiting
                log.info(f"Workflow {instance_id} step {current}: pre-gate still pending")
                return
        # ── END PRE-STEP GATE ─────────────────────────────────────────────
```

#### 2e. Post-step gate check in `handle_step_completion` (replace lines 720-743)

Replace the current `review_mode == "human_approval"` block:

```python
            # CURRENT CODE (lines 720-743) — REPLACE THIS ENTIRE BLOCK:
            # Success — check review_mode before advancing
            review_mode = step.get("review_mode", "auto")
            if review_mode == "human_approval":
                ... (pause + whatsapp inline code) ...
                return
            # auto or agent_review — advance to next step
            await pool.execute(...)
            await _advance_workflow(...)
```

With:

```python
            # Success — check for gate config before advancing
            gate_cfg = step.get("gate") or {}
            review_mode = step.get("review_mode", "auto")

            # Backward compat: review_mode=human_approval → create human post-gate
            if not gate_cfg and review_mode == "human_approval":
                gate_cfg = {
                    "type": "human", "position": "post",
                    "timeout_seconds": 86400, "timeout_action": "escalate"
                }

            if gate_cfg and gate_cfg.get("position", "post") == "post":
                # Check if we already have an approved post-gate for this step
                existing = await pool.fetchrow("""
                    SELECT status FROM workflow_gates
                    WHERE instance_id = $1 AND step_position = $2 AND gate_position = 'post'
                    ORDER BY created_at DESC LIMIT 1
                """, instance_id, current)

                if not existing or existing["status"] == "pending":
                    if not existing:
                        # Create post-step gate
                        context = {"step_output": output[:3000]}
                        gate_id = await _create_gate(
                            pool, instance_id, current, "post", gate_cfg, context
                        )
                        # Persist step outputs before pausing
                        await pool.execute(
                            """UPDATE workflow_instances
                               SET step_outputs = $2::jsonb, step_durations = $3::jsonb
                               WHERE id = $1""",
                            instance_id, json.dumps(step_outputs), json.dumps(step_durations),
                        )
                        # Notify
                        step_name = step.get("name", f"Step {current}")
                        gate_type = gate_cfg.get("type", "human")
                        if gate_type == "human":
                            msg = (
                                f"🔒 Gate pending: '{inst['name']}'\n"
                                f"Step: {step_name} (post)\n"
                                f"Approve: POST /workflows/gates/{gate_id}/resolve\n"
                                f"Expires in {gate_cfg.get('timeout_seconds', 86400)//3600}h"
                            )
                        else:
                            msg = (
                                f"🗳️ DAO vote open: '{inst['name']}'\n"
                                f"Step: {step_name}\n"
                                f"Vote: POST /workflows/gates/{gate_id}/vote"
                            )
                        asyncio.create_task(_whastsapp_notify(msg))
                    return  # Pause; gate_notifier already called (or gate already pending)

                # Existing gate was approved or skipped — fall through to advance

            # No gate (or already resolved) — advance to next step
            await pool.execute(
                """UPDATE workflow_instances
                   SET current_step = current_step + 1,
                       step_outputs = $2::jsonb,
                       step_durations = $3::jsonb
                   WHERE id = $1""",
                instance_id, json.dumps(step_outputs), json.dumps(step_durations),
            )
            await _advance_workflow(pool, instance_id)
```

#### 2f. Update `approve_step` endpoint (replace lines 396-442)

Modernize to delegate to `_resolve_gate()` when a pending gate exists:

```python
@router.post("/instances/{instance_id}/approve")
async def approve_step(instance_id: UUID, req: WorkflowApproveRequest):
    """Human approves, rejects, or skips a paused workflow step.

    Delegates to gate system if a pending gate exists.
    Legacy fallback: direct status manipulation if no gate record found.
    """
    pool = await get_pool()
    inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
    if not inst:
        raise HTTPException(404, "Instance not found")
    if inst["status"] != "paused":
        raise HTTPException(400, f"Instance is {inst['status']}, not paused")

    # Check for a pending gate record
    pending_gate = await pool.fetchrow("""
        SELECT id FROM workflow_gates
        WHERE instance_id = $1 AND status = 'pending'
        ORDER BY created_at DESC LIMIT 1
    """, instance_id)

    if pending_gate:
        # Delegate to gate resolution engine
        result = await _resolve_gate(
            pool, pending_gate["id"], req.action,
            resolved_by="mev", reason=req.reason,
        )
        return result

    # Legacy fallback (no gate record — old-style workflow)
    if req.action == "approve":
        await pool.execute(
            "UPDATE workflow_instances SET current_step = current_step + 1, status = 'running' WHERE id = $1",
            instance_id,
        )
        asyncio.create_task(_advance_workflow(pool, instance_id))
        return {"status": "approved", "next_step": inst["current_step"] + 1}
    elif req.action == "reject":
        await pool.execute(
            "UPDATE workflow_instances SET status = 'failed', error = $2 WHERE id = $1",
            instance_id, f"Rejected: {req.reason or 'no reason'}",
        )
        return {"status": "rejected"}
    elif req.action == "skip":
        step_outputs = _jsonb(inst["step_outputs"])
        step_outputs[str(inst["current_step"])] = f"[SKIPPED] {req.reason or ''}"
        await pool.execute(
            """UPDATE workflow_instances
               SET current_step = current_step + 1, status = 'running',
                   step_outputs = $2::jsonb
               WHERE id = $1""",
            instance_id, json.dumps(step_outputs),
        )
        asyncio.create_task(_advance_workflow(pool, instance_id))
        return {"status": "skipped", "next_step": inst["current_step"] + 1}
    raise HTTPException(400, f"Invalid action: {req.action}")
```

#### 2g. New API Endpoints (insert before `@router.post("/instances/{instance_id}/cancel")`, ~line 445)

```python
# ── Gate API Endpoints ────────────────────────────────────────────────────


@router.get("/gates")
async def list_gates(
    instance_id: Optional[str] = None,
    status: Optional[str] = None,
    gate_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    """List gates, optionally filtered by instance, status, or type."""
    pool = await get_pool()
    conditions = ["1=1"]
    params = []
    i = 1
    if instance_id:
        conditions.append(f"g.instance_id = ${i}::uuid")
        params.append(instance_id); i += 1
    if status:
        conditions.append(f"g.status = ${i}")
        params.append(status); i += 1
    if gate_type:
        conditions.append(f"g.gate_type = ${i}")
        params.append(gate_type); i += 1

    rows = await pool.fetch(f"""
        SELECT g.*, wi.name as workflow_name
        FROM workflow_gates g
        JOIN workflow_instances wi ON wi.id = g.instance_id
        WHERE {' AND '.join(conditions)}
        ORDER BY g.created_at DESC
        LIMIT ${i}
    """, *params, limit)
    return [dict(r) for r in rows]


@router.get("/gates/{gate_id}")
async def get_gate(gate_id: UUID):
    """Gate detail including vote tally for DAO gates."""
    pool = await get_pool()
    gate = await pool.fetchrow("""
        SELECT g.*, wi.name as workflow_name, wi.current_step
        FROM workflow_gates g
        JOIN workflow_instances wi ON wi.id = g.instance_id
        WHERE g.id = $1
    """, gate_id)
    if not gate:
        raise HTTPException(404, "Gate not found")

    result = dict(gate)

    # Include vote tally for DAO gates
    if gate["gate_type"] == "dao":
        votes = await pool.fetch(
            "SELECT vote, weight, voter_address, reason FROM workflow_gate_votes WHERE gate_id = $1",
            gate_id,
        )
        approve_w = sum(float(v["weight"]) for v in votes if v["vote"] == "approve")
        reject_w  = sum(float(v["weight"]) for v in votes if v["vote"] == "reject")
        total_w   = sum(float(v["weight"]) for v in votes)
        result["tally"] = {
            "vote_count": len(votes),
            "approve_weight": approve_w,
            "reject_weight": reject_w,
            "total_weight": total_w,
            "quorum_reached": len(votes) >= (gate["quorum_required"] or 1),
            "threshold_met": (approve_w / max(total_w, 1)) >= float(gate["approval_threshold"] or 0.5),
        }
        result["votes"] = [dict(v) for v in votes]

    return result


@router.post("/gates/{gate_id}/resolve")
async def resolve_gate(gate_id: UUID, req: GateResolveRequest):
    """Admin resolve a gate (approve/reject/skip)."""
    pool = await get_pool()
    try:
        result = await _resolve_gate(pool, gate_id, req.action, req.resolved_by, req.reason)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/gates/{gate_id}/vote")
async def vote_on_gate(gate_id: UUID, req: GateVoteRequest):
    """Cast a vote on a DAO gate."""
    pool = await get_pool()
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    if not gate:
        raise HTTPException(404, "Gate not found")
    if gate["gate_type"] != "dao":
        raise HTTPException(400, "Vote only allowed on DAO gates")
    if gate["status"] != "pending":
        raise HTTPException(400, f"Gate is {gate['status']}, not pending")
    if not req.vote in ("approve", "reject", "abstain"):
        raise HTTPException(400, f"Invalid vote: {req.vote}")

    # Upsert vote
    vote_row = await pool.fetchrow("""
        INSERT INTO workflow_gate_votes (gate_id, voter_address, vote, weight, signature, reason)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (gate_id, voter_address) DO UPDATE
            SET vote = EXCLUDED.vote, weight = EXCLUDED.weight, signature = EXCLUDED.signature
        RETURNING id
    """, gate_id, req.vote, req.vote, req.weight, req.signature, req.reason)

    # Check quorum after vote
    tally = await _check_dao_quorum(pool, gate_id)
    return {"vote_id": str(vote_row["id"]), "tally": tally}


@router.get("/instances/{instance_id}/gates")
async def list_instance_gates(instance_id: UUID):
    """All gates for a workflow instance."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT * FROM workflow_gates
        WHERE instance_id = $1
        ORDER BY step_position, gate_position, created_at
    """, instance_id)
    return [dict(r) for r in rows]
```

---

## Integration: Reflection Heartbeat

Add `_check_gate_timeouts` to the reflection heartbeat maintenance step.

**File**: `~/otto/.claude/agents/reflection.md`

**Find** the maintenance/infrastructure step (step 3 area) and **add**:
```markdown
### 3e. Gate Timeout Check
```python
import requests
# Call the gate timeout checker via Memory API
# (The actual call happens inside the heartbeat's Python context)
```
```

Actually, the simpler integration is to call the API endpoint from reflection.sh or add it as a step in the reflection agent prompt. The best path is to add a call to the Memory API's gate timeout checker endpoint.

Add a new API endpoint `POST /workflows/gates/check-timeouts` that triggers `_check_gate_timeouts(pool)` and is called by the reflection heartbeat.

---

## Implementation Order

1. **Write migration file** (074_workflow_gating.sql)
2. **Run migration** — verify tables created
3. **Update imports** in workflows.py
4. **Add Pydantic models** (GateConfig, GateResolveRequest, GateVoteRequest) + update StepSpec
5. **Add gate engine functions** (_whastsapp_notify, _create_gate, _resolve_gate, _check_gate_timeouts, _check_dao_quorum)
6. **Modify `_advance_workflow`** — add pre-step gate check
7. **Modify `handle_step_completion`** — replace human_approval block with gate-aware logic
8. **Update `approve_step` endpoint** — delegate to _resolve_gate
9. **Add new API endpoints** (list, get, resolve, vote, instance gates)
10. **Add `POST /workflows/gates/check-timeouts`** endpoint
11. **Restart Memory API** — `sudo systemctl restart otto-memory`
12. **Integration test** — start a workflow with a human post-gate and verify pause + resolution

---

## Verification Tests

After implementation:

```bash
# 1. Check migration applied
docker exec memory-postgres-1 psql -U otto -d memory -c "\d workflow_gates"

# 2. Check Memory API healthy
curl -s http://localhost:8100/health | jq .

# 3. List gates (should be empty initially)
curl -s http://localhost:8100/workflows/gates | jq .

# 4. Start a test workflow with a gate in the template
# (or manually add gate config to an existing template's step)
```

---

## Risk Notes

1. **Import `timedelta`** — missing from current imports; will cause NameError if forgotten
2. **`pending_gate_id` column** — migration adds it to workflow_instances; existing rows get NULL (fine)
3. **Backward compat** — `review_mode=human_approval` is preserved by auto-creating a gate record; existing workflows that use it will now get a gate record but behavior is identical
4. **`_advance_workflow` paused check** — current guard at line 532 checks `status in ("pending", "running")`. After a gate approves and sets status=running, `_advance_workflow` will be called by `_resolve_gate` directly so this is fine.
5. **Race condition** — `handle_step_completion` checks for an existing gate before creating one. The check is not atomic but the practical race window is <1ms (both callers are in the same process). Acceptable for Phase 1.

"""Workflow Engine — multi-agent pipeline orchestration.

Workflows chain specialist agents through sequential steps, piping
output from one to the next. Each step becomes a task executed by
task_runner.sh. Step advancement is event-driven: when a task completes,
the workflow engine checks if it belongs to a workflow and advances.

Auto-eval (autoresearch pattern): after a workflow completes, an evaluator
agent scores the output. Fitness scores drive evolutionary optimization
of templates across runs.
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, model_validator

from ..db import get_pool
from ..gate_notifier import gate_notifier

log = logging.getLogger("otto.workflows")
router = APIRouter(prefix="/workflows", tags=["workflows"])

TASK_RUNNER = "/home/web3relic/otto/task_runner.sh"


# ── Pydantic Models ──────────────────────────────────────────────────────

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
    voter_address: str
    vote: str                                  # approve | reject | abstain
    reason: Optional[str] = None
    signature: Optional[str] = None
    weight: float = 1.0


class StepSpec(BaseModel):
    position: int
    name: str
    agent_type: Optional[str] = None
    prompt_template: str = ""
    action: Optional[str] = None          # "notify" for non-task steps
    notify_template: Optional[str] = None
    review_mode: str = "auto"             # auto | human_approval | agent_review
    max_budget_usd: float = 5.0
    max_turns: int = 50
    timeout_seconds: int = 900
    on_failure: str = "pause"             # retry_once | pause | skip | fail_workflow
    working_directory: Optional[str] = None
    gate: Optional[GateConfig] = None     # gate config for this step


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[StepSpec]
    default_priority: int = 5
    default_working_dir: str = "/home/web3relic/otto"
    tags: List[str] = Field(default_factory=list)
    created_by: str = "otto"


class TemplateUpdate(BaseModel):
    description: Optional[str] = None
    steps: Optional[List[StepSpec]] = None
    default_priority: Optional[int] = None
    default_working_dir: Optional[str] = None
    tags: Optional[List[str]] = None
    archived: Optional[bool] = None


class WorkflowStartRequest(BaseModel):
    template_id: Optional[str] = None
    template_name: Optional[str] = None
    name: str
    variables: dict = Field(default_factory=dict)
    priority: int = 5
    working_directory: Optional[str] = None
    trigger_source: str = "manual"
    trigger_message: Optional[str] = None
    created_by: str = "otto"


class WorkflowApproveRequest(BaseModel):
    action: str = "approve"         # approve | reject | skip
    decision: Optional[str] = None  # OMS alias for action (OMS sends decision, not action)
    reason: Optional[str] = None

    @model_validator(mode="after")
    def resolve_action(self) -> "WorkflowApproveRequest":
        # Accept decision as alias for action; only override if action is still at default
        if self.decision and self.action == "approve":
            self.action = self.decision
        return self


class TemplateValidateRequest(BaseModel):
    name: str = "validate"
    steps: List[dict]   # raw dicts — we validate them


# ── Helpers ──────────────────────────────────────────────────────────────

def _jsonb(val) -> dict:
    """Safely convert a JSONB value from asyncpg (may be str, dict, or None) to a dict."""
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


def _row_to_dict(row) -> dict:
    d = dict(row)
    for k in ("created_at", "updated_at", "started_at", "completed_at",
              "expires_at", "resolved_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    d["id"] = str(d["id"])
    if d.get("template_id"):
        d["template_id"] = str(d["template_id"])
    if d.get("parent_version_id"):
        d["parent_version_id"] = str(d["parent_version_id"])
    if d.get("instance_id"):
        d["instance_id"] = str(d["instance_id"])
    # Normalize JSONB
    for k in ("steps", "variables", "step_outputs", "step_task_ids",
              "step_durations", "eval_scores", "mutation_diff", "metadata",
              "context_snapshot"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


def _resolve_artifact(s: str, limit: int) -> str:
    """If *s* is an [ARTIFACT: path] reference, read up to *limit* chars from the file.

    Falls back to returning *s* unchanged if the path is missing or unreadable.
    """
    m = re.search(r'\[ARTIFACT: ([^\]]+)\]', s)
    if m:
        artifact_path = m.group(1).strip()
        if os.path.exists(artifact_path):
            try:
                with open(artifact_path, "r") as f:
                    return f.read(limit)
            except Exception:
                pass
    return s


def _interpolate(template: str, instance: dict) -> str:
    """Interpolate {variables}, {prev_output}, {step_N_output} into a prompt template."""
    values = defaultdict(str)

    # User-provided variables
    variables = instance.get("variables") or {}
    if isinstance(variables, str):
        try:
            variables = json.loads(variables)
        except Exception:
            variables = {}
    values.update(variables)

    # Step outputs
    step_outputs = instance.get("step_outputs") or {}
    if isinstance(step_outputs, str):
        try:
            step_outputs = json.loads(step_outputs)
        except Exception:
            step_outputs = {}

    for pos, output in step_outputs.items():
        output_str = str(output)
        # GAP-2: if output is an artifact reference, read the full file
        if output_str.startswith("[ARTIFACT:"):
            output_str = _resolve_artifact(output_str, 8000)
        values[f"step_{pos}_output"] = output_str[:8000]

    # prev_output = output of the step before current
    current = instance.get("current_step", 0)
    prev_pos = str(current - 1)
    if prev_pos in step_outputs:
        prev_str = str(step_outputs[prev_pos])
        # GAP-2: resolve artifact reference for prev_output too
        if prev_str.startswith("[ARTIFACT:"):
            prev_str = _resolve_artifact(prev_str, 8000)
        values["prev_output"] = prev_str[:8000]

    # Workflow metadata
    values["workflow_name"] = instance.get("name", "")
    values["working_directory"] = instance.get("working_directory", "/home/web3relic/otto")

    try:
        return template.format_map(values)
    except (KeyError, ValueError):
        # Fallback: manual replacement for unresolved keys
        result = template
        for k, v in values.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result


# ── Template Schema & Validation ─────────────────────────────────────────

@router.get("/templates/schema")
async def get_template_schema():
    """Return JSON Schema for workflow template structure.

    Derived from Pydantic models — always in sync with the API contract.
    Use this to validate templates client-side or build editor tooling.
    """
    return {
        "template": TemplateCreate.model_json_schema(),
        "step": StepSpec.model_json_schema(),
        "gate": GateConfig.model_json_schema(),
        "version": "1.0",
    }


@router.post("/templates/validate")
async def validate_template(req: TemplateValidateRequest):
    """Validate a workflow template config before saving.

    Returns structured errors and warnings with step/field granularity.
    Does not persist anything — pure validation.
    """
    from pydantic import ValidationError

    errors: list = []
    warnings: list = []

    for i, step in enumerate(req.steps):
        # Validate step structure
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

        # Warn on very short gate timeouts (heartbeat-lag risk)
        # Note: structural gate validation is already covered by StepSpec(**step) above.
        gate = step.get("gate")
        if gate and isinstance(gate, dict):
            timeout = gate.get("timeout_seconds", 86400)
            if isinstance(timeout, int) and timeout < 600:
                warnings.append({
                    "step": i,
                    "field": "gate.timeout_seconds",
                    "message": (
                        f"Timeout {timeout}s is less than 600s. "
                        "Otto's heartbeat runs every 30 minutes — short timeouts "
                        "may not be processed in time."
                    ),
                })

    return {
        "valid": len(errors) == 0,
        "step_count": len(req.steps),
        "errors": errors,
        "warnings": warnings,
    }


# ── Template CRUD ────────────────────────────────────────────────────────

@router.post("/templates")
async def create_template(req: TemplateCreate):
    pool = await get_pool()
    steps_json = json.dumps([s.model_dump() for s in req.steps])
    row = await pool.fetchrow(
        """INSERT INTO workflow_templates
           (name, description, steps, default_priority, default_working_dir, tags, created_by)
           VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7)
           RETURNING *""",
        req.name, req.description, steps_json,
        req.default_priority, req.default_working_dir,
        req.tags, req.created_by,
    )
    return _row_to_dict(row)


@router.get("/templates")
async def list_templates(
    tag: Optional[str] = None,
    archived: bool = False,
):
    pool = await get_pool()
    if tag:
        rows = await pool.fetch(
            "SELECT * FROM workflow_templates WHERE $1 = ANY(tags) AND archived = $2 ORDER BY updated_at DESC",
            tag, archived,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM workflow_templates WHERE archived = $1 ORDER BY updated_at DESC",
            archived,
        )
    return {"count": len(rows), "templates": [_row_to_dict(r) for r in rows]}


@router.get("/templates/{template_id}")
async def get_template(template_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", template_id)
    if not row:
        raise HTTPException(404, "Template not found")
    return _row_to_dict(row)


@router.put("/templates/{template_id}")
async def update_template(template_id: UUID, req: TemplateUpdate):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", template_id)
    if not existing:
        raise HTTPException(404, "Template not found")

    updates = {}
    if req.description is not None:
        updates["description"] = req.description
    if req.steps is not None:
        updates["steps"] = json.dumps([s.model_dump() for s in req.steps])
    if req.default_priority is not None:
        updates["default_priority"] = req.default_priority
    if req.default_working_dir is not None:
        updates["default_working_dir"] = req.default_working_dir
    if req.tags is not None:
        updates["tags"] = req.tags
    if req.archived is not None:
        updates["archived"] = req.archived

    if not updates:
        return _row_to_dict(existing)

    set_clauses = []
    values = [template_id]
    for i, (k, v) in enumerate(updates.items(), 2):
        if k == "steps":
            set_clauses.append(f"{k} = ${i}::jsonb")
        else:
            set_clauses.append(f"{k} = ${i}")
        values.append(v)

    row = await pool.fetchrow(
        f"UPDATE workflow_templates SET {', '.join(set_clauses)} WHERE id = $1 RETURNING *",
        *values,
    )
    return _row_to_dict(row)


# ── Instance Lifecycle ───────────────────────────────────────────────────

@router.post("/start")
async def start_workflow(req: WorkflowStartRequest):
    """Create and start a workflow instance."""
    pool = await get_pool()

    # Resolve template
    tmpl = None
    if req.template_id:
        tmpl = await pool.fetchrow(
            "SELECT * FROM workflow_templates WHERE id = $1 AND NOT archived",
            UUID(req.template_id),
        )
    elif req.template_name:
        tmpl = await pool.fetchrow(
            "SELECT * FROM workflow_templates WHERE name = $1 AND NOT archived",
            req.template_name,
        )
    if not tmpl:
        raise HTTPException(404, "Workflow template not found")

    work_dir = req.working_directory or tmpl["default_working_dir"]

    # Create instance
    row = await pool.fetchrow(
        """INSERT INTO workflow_instances
           (template_id, name, variables, priority, working_directory,
            trigger_source, trigger_message, created_by)
           VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8)
           RETURNING *""",
        tmpl["id"], req.name, json.dumps(req.variables),
        req.priority, work_dir,
        req.trigger_source, req.trigger_message, req.created_by,
    )
    instance_id = row["id"]
    log.info(f"Workflow started: {req.name} (id={instance_id}, template={tmpl['name']})")

    # Advance to first step (async, non-blocking)
    asyncio.create_task(_advance_workflow(pool, instance_id))

    return _row_to_dict(row)


@router.get("/instances")
async def list_instances(
    status: Optional[str] = None,
    template_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
):
    pool = await get_pool()
    conditions = []
    values = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}")
        values.append(status)
        idx += 1
    if template_id:
        conditions.append(f"template_id = ${idx}")
        values.append(UUID(template_id))
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = await pool.fetch(
        f"SELECT * FROM workflow_instances {where} ORDER BY created_at DESC LIMIT {limit}",
        *values,
    )
    # Enrich each instance with template name and step count
    instances = []
    tmpl_cache: dict = {}
    for r in rows:
        d = _row_to_dict(r)
        tid = r["template_id"]
        if tid and tid not in tmpl_cache:
            tmpl = await pool.fetchrow(
                "SELECT name, steps FROM workflow_templates WHERE id = $1", tid
            )
            if tmpl:
                steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
                tmpl_cache[tid] = {"name": tmpl["name"], "steps": steps}
        if tid and tid in tmpl_cache:
            d["template_name"] = tmpl_cache[tid]["name"]
            d["template_steps"] = tmpl_cache[tid]["steps"]
            d["total_steps"] = len(tmpl_cache[tid]["steps"])
        instances.append(d)
    return {"count": len(rows), "instances": instances}


@router.get("/instances/{instance_id}")
async def get_instance(instance_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
    if not row:
        raise HTTPException(404, "Workflow instance not found")

    result = _row_to_dict(row)

    # Enrich with template info
    if row["template_id"]:
        tmpl = await pool.fetchrow(
            "SELECT name, steps FROM workflow_templates WHERE id = $1",
            row["template_id"],
        )
        if tmpl:
            result["template_name"] = tmpl["name"]
            steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
            result["template_steps"] = steps
            result["total_steps"] = len(steps)

    # Lightweight pending gate summary (avoids a second round-trip for the OMS status panel)
    if row["status"] == "paused":
        pending_gate = await pool.fetchrow("""
            SELECT id, gate_type, gate_position, step_position, expires_at
            FROM workflow_gates
            WHERE instance_id = $1 AND status = 'pending'
            ORDER BY created_at DESC LIMIT 1
        """, instance_id)
        if pending_gate:
            seconds_remaining: Optional[int] = None
            if pending_gate["expires_at"]:
                delta = pending_gate["expires_at"] - datetime.now(timezone.utc)
                seconds_remaining = max(0, int(delta.total_seconds()))
            result["pending_gate_summary"] = {
                "gate_id": str(pending_gate["id"]),
                "gate_type": pending_gate["gate_type"],
                "gate_position": pending_gate["gate_position"],
                "step_position": pending_gate["step_position"],
                "expires_at": pending_gate["expires_at"].isoformat() if pending_gate["expires_at"] else None,
                "seconds_remaining": seconds_remaining,
            }

    return result


@router.get("/instances/{instance_id}/gate")
async def get_pending_gate(instance_id: UUID):
    """Get the currently pending gate for a paused workflow instance.

    Returns full gate context including context_snapshot (step output for post-gates,
    prompt preview for pre-gates) and DAO vote tally for DAO gates.

    Returns 404 if the instance has no pending gate.
    """
    pool = await get_pool()
    inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
    if not inst:
        raise HTTPException(404, "Instance not found")

    gate = await pool.fetchrow("""
        SELECT g.*, wi.name as workflow_name
        FROM workflow_gates g
        JOIN workflow_instances wi ON wi.id = g.instance_id
        WHERE g.instance_id = $1 AND g.status = 'pending'
        ORDER BY g.created_at DESC LIMIT 1
    """, instance_id)
    if not gate:
        raise HTTPException(404, "No pending gate for this instance")

    result = _row_to_dict(gate)

    # Compute seconds_remaining
    if gate["expires_at"]:
        delta = gate["expires_at"] - datetime.now(timezone.utc)
        result["seconds_remaining"] = max(0, int(delta.total_seconds()))
    else:
        result["seconds_remaining"] = None

    # Enrich context_snapshot: pull step output or prompt preview from instance
    step_pos = gate["step_position"]
    gate_position = gate["gate_position"]
    step_outputs = _jsonb(inst["step_outputs"])

    context_snapshot = _jsonb(gate["context_snapshot"]) if gate["context_snapshot"] else {}

    # Fetch template once — reused for both prompt preview (pre-gate) and step name
    template_steps = []
    if inst["template_id"]:
        tmpl = await pool.fetchrow(
            "SELECT steps FROM workflow_templates WHERE id = $1", inst["template_id"]
        )
        if tmpl:
            template_steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])

    if gate_position == "post":
        # Step has already run — surface its output
        raw_output = step_outputs.get(str(step_pos), "")
        if raw_output:
            output_str = str(raw_output)
            if output_str.startswith("[ARTIFACT:"):
                output_str = _resolve_artifact(output_str, 5000)
            context_snapshot["step_output"] = output_str[:5000]
    else:
        # Pre-gate: surface interpolated prompt preview
        if template_steps and step_pos < len(template_steps):
            step_spec = template_steps[step_pos]
            prompt_raw = step_spec.get("prompt_template", "")
            instance_dict = _row_to_dict(inst)
            prompt_preview = _interpolate(prompt_raw, instance_dict)
            context_snapshot["prompt_preview"] = prompt_preview[:5000]

    result["context_snapshot"] = context_snapshot

    # Step name from template (uses already-fetched template_steps)
    if template_steps and step_pos < len(template_steps):
        result["step_name"] = template_steps[step_pos].get("name", f"Step {step_pos}")

    # DAO tally for DAO gates
    if gate["gate_type"] == "dao":
        votes = await pool.fetch(
            """SELECT vote, weight FROM workflow_gate_votes WHERE gate_id = $1""",
            gate["id"],
        )
        approve_w = sum(float(v["weight"]) for v in votes if v["vote"] == "approve")
        reject_w  = sum(float(v["weight"]) for v in votes if v["vote"] == "reject")
        total_w   = approve_w + reject_w  # abstain excluded from threshold calc
        threshold = float(gate["approval_threshold"] or 0.5)
        quorum_req = gate["quorum_required"] or 1
        vote_cnt  = len(votes)
        approve_pct = round(approve_w / max(total_w, 0.0001), 4)
        result["tally"] = {
            "vote_count":      vote_cnt,
            "approve_weight":  approve_w,
            "reject_weight":   reject_w,
            "total_weight":    total_w,
            "approve_pct":     approve_pct,
            "reject_pct":      round(reject_w / max(total_w, 0.0001), 4),
            "quorum_required": quorum_req,
            "quorum_reached":  vote_cnt >= quorum_req,
            "threshold":       threshold,
            "threshold_met":   approve_pct >= threshold,
        }
    else:
        result["tally"] = None

    return result


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
        try:
            result = await _resolve_gate(
                pool, pending_gate["id"], req.action,
                resolved_by="mev", reason=req.reason,
            )
            return result
        except ValueError as e:
            raise HTTPException(400, str(e))

    # Legacy fallback (no gate record — old-style workflow)
    if req.action == "approve":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} approved by human (legacy)")
        await pool.execute(
            """UPDATE workflow_instances
               SET current_step = current_step + 1, status = 'running'
               WHERE id = $1""",
            instance_id,
        )
        asyncio.create_task(_advance_workflow(pool, instance_id))
        return {"status": "approved", "next_step": inst["current_step"] + 1}

    elif req.action == "reject":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} rejected (legacy): {req.reason}")
        await pool.execute(
            "UPDATE workflow_instances SET status = 'failed', error = $2 WHERE id = $1",
            instance_id, f"Rejected by human: {req.reason or 'no reason'}",
        )
        return {"status": "rejected"}

    elif req.action == "skip":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} skipped (legacy)")
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
    params: list = []
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
    return [_row_to_dict(r) for r in rows]


@router.get("/gates/check-timeouts")
async def check_timeouts_status():
    """Check how many gates are currently pending and expired."""
    pool = await get_pool()
    pending = await pool.fetchval("SELECT COUNT(*) FROM workflow_gates WHERE status = 'pending'")
    expired = await pool.fetchval(
        "SELECT COUNT(*) FROM workflow_gates WHERE status = 'pending' AND expires_at < now()"
    )
    return {"pending_gates": pending, "expired_gates": expired}


@router.post("/gates/check-timeouts")
async def run_check_timeouts():
    """Trigger gate timeout processing. Called by reflection heartbeat every 30 min."""
    pool = await get_pool()
    processed = await _check_gate_timeouts(pool)
    return {"processed": processed}


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
            """SELECT vote, weight, voter_address, reason, created_at
               FROM workflow_gate_votes WHERE gate_id = $1
               ORDER BY created_at""",
            gate_id,
        )
        approve_w  = sum(float(v["weight"]) for v in votes if v["vote"] == "approve")
        reject_w   = sum(float(v["weight"]) for v in votes if v["vote"] == "reject")
        total_w    = approve_w + reject_w   # abstain excluded from threshold calc
        threshold  = float(gate["approval_threshold"] or 0.5)
        quorum_req = gate["quorum_required"] or 1
        vote_cnt   = len(votes)
        approve_pct = round(approve_w / max(total_w, 0.0001), 4)
        reject_pct  = round(reject_w  / max(total_w, 0.0001), 4)
        result["tally"] = {
            "vote_count":      vote_cnt,
            "quorum_required": quorum_req,
            "quorum_reached":  vote_cnt >= quorum_req,
            "approve_weight":  approve_w,
            "reject_weight":   reject_w,
            "total_weight":    total_w,
            "approve_pct":     approve_pct,
            "reject_pct":      reject_pct,
            "threshold":       threshold,
            "threshold_met":   approve_pct >= threshold,
        }
        result["votes"] = [
            {
                "voter_address": v["voter_address"],
                "vote":          v["vote"],
                "weight":        float(v["weight"]),
                "reason":        v["reason"],
                "created_at":    v["created_at"].isoformat() if v["created_at"] else None,
            }
            for v in votes
        ]

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
    if req.vote not in ("approve", "reject", "abstain"):
        raise HTTPException(400, f"Invalid vote: {req.vote}")

    # Upsert vote
    vote_row = await pool.fetchrow("""
        INSERT INTO workflow_gate_votes (gate_id, voter_address, vote, weight, signature, reason)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (gate_id, voter_address) DO UPDATE
            SET vote = EXCLUDED.vote, weight = EXCLUDED.weight,
                signature = EXCLUDED.signature, reason = EXCLUDED.reason
        RETURNING id
    """, gate_id, req.voter_address, req.vote, req.weight, req.signature, req.reason)

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
    return [_row_to_dict(r) for r in rows]


# ── End Gate API Endpoints ────────────────────────────────────────────────


@router.post("/instances/{instance_id}/cancel")
async def cancel_workflow(instance_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE workflow_instances
           SET status = 'cancelled', completed_at = now()
           WHERE id = $1 AND status IN ('pending', 'running', 'paused')
           RETURNING *""",
        instance_id,
    )
    if not row:
        raise HTTPException(404, "Instance not found or already terminal")
    log.info(f"Workflow {instance_id} cancelled")
    return _row_to_dict(row)


@router.post("/instances/{instance_id}/retry")
async def retry_step(instance_id: UUID):
    """Retry the current failed/paused step."""
    pool = await get_pool()
    inst = await pool.fetchrow(
        "SELECT * FROM workflow_instances WHERE id = $1", instance_id
    )
    if not inst:
        raise HTTPException(404, "Instance not found")
    if inst["status"] not in ("failed", "paused"):
        raise HTTPException(400, f"Instance is {inst['status']}, cannot retry")

    await pool.execute(
        """UPDATE workflow_instances
           SET status = 'running', retry_count = retry_count + 1, error = NULL
           WHERE id = $1""",
        instance_id,
    )
    asyncio.create_task(_advance_workflow(pool, instance_id))
    return {"status": "retrying", "step": inst["current_step"], "retry_count": inst["retry_count"] + 1}


# ── Dashboard ────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def workflow_dashboard():
    pool = await get_pool()
    stats = await pool.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'running') AS running,
            COUNT(*) FILTER (WHERE status = 'paused') AS paused,
            COUNT(*) FILTER (WHERE status = 'pending') AS pending,
            COUNT(*) FILTER (WHERE status = 'completed') AS completed,
            COUNT(*) FILTER (WHERE status = 'failed') AS failed,
            COUNT(*) AS total
        FROM workflow_instances
    """)
    templates_count = await pool.fetchval("SELECT COUNT(*) FROM workflow_templates WHERE NOT archived")
    return {
        "instances": dict(stats),
        "templates_count": templates_count,
    }


# ── Experiments (evolution history) ──────────────────────────────────────

@router.get("/templates/{template_id}/experiments")
async def list_experiments(template_id: UUID, limit: int = 20):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM workflow_experiments
           WHERE template_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        template_id, limit,
    )
    return {"count": len(rows), "experiments": [_row_to_dict(r) for r in rows]}


# ── Workflow Runner (core engine) ────────────────────────────────────────

async def _advance_workflow(pool, instance_id: UUID):
    """Advance a workflow to its next step. Creates and launches the step's task.

    This is the core state machine. Called:
    - On workflow start (step 0)
    - On task completion (step N+1)
    - On human approval (resume from paused)
    - On retry
    """
    try:
        inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
        if not inst or inst["status"] not in ("pending", "running"):
            return

        tmpl = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", inst["template_id"])
        if not tmpl:
            log.error(f"Workflow {instance_id}: template not found")
            return

        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        current = inst["current_step"]

        # All steps done?
        if current >= len(steps):
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'completed', completed_at = now()
                   WHERE id = $1""",
                instance_id,
            )
            log.info(f"Workflow {instance_id} completed ({len(steps)} steps)")

            # Notify Mev
            asyncio.create_task(_notify_workflow_complete(inst, tmpl))

            # Auto-eval (async, non-blocking)
            asyncio.create_task(_auto_eval_workflow(pool, instance_id))

            # Plans: notify plan coordinator task if this workflow belongs to one
            from .task_plans import check_plan_workflow_complete
            asyncio.create_task(check_plan_workflow_complete(pool, instance_id, "completed"))
            return

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
                # First time hitting this step — create pre-gate and pause
                context = {
                    "prompt_preview": _interpolate(step.get("prompt_template", ""), dict(inst))[:2000],
                    "variables": dict(_jsonb(inst.get("variables")) if inst.get("variables") else {}),
                    "step_name": step.get("name", f"Step {current}"),
                }
                gate_id = await _create_gate(pool, instance_id, current, "pre", gate_cfg, context)
                # Notify via gate_notifier (WhatsApp + webhooks)
                gate_row = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
                step_name = step.get("name", f"Step {current}")
                asyncio.create_task(
                    gate_notifier.gate_pending(
                        dict(gate_row),
                        {"id": str(instance_id), "name": inst["name"]},
                        {"name": step_name},
                    )
                )
                return  # Pause — resume when gate is resolved

            elif existing_gate["status"] != "approved":
                # Gate exists but not approved yet — still waiting
                log.info(f"Workflow {instance_id} step {current}: pre-gate still pending")
                return
        # ── END PRE-STEP GATE ─────────────────────────────────────────────

        # Mark as running if still pending
        if inst["status"] == "pending":
            await pool.execute(
                "UPDATE workflow_instances SET status = 'running', started_at = now() WHERE id = $1",
                instance_id,
            )

        # Handle non-task actions (notify)
        if step.get("action") == "notify":
            raw_msg = _interpolate(step.get("notify_template", "Workflow step complete."), dict(inst))

            # For research pipelines, replace {prev_output} with a proper deliverable extract
            # (The raw_msg may already contain the full step output — trim it intelligently)
            msg = _smart_truncate(raw_msg, 3500)
            log.info(f"Workflow {instance_id} step {current}: notify action ({len(msg)} chars)")

            # Send WhatsApp notification
            try:
                proc = await asyncio.create_subprocess_exec(
                    "/home/web3relic/otto/tools/whatsapp_send.sh", msg,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.communicate(), timeout=15)
            except Exception as e:
                log.warning(f"Workflow notify failed: {e}")

            # Store output and advance
            step_outputs = _jsonb(inst["step_outputs"])
            step_outputs[str(current)] = f"[NOTIFIED] {msg[:200]}"
            await pool.execute(
                """UPDATE workflow_instances
                   SET current_step = $2, step_outputs = $3::jsonb
                   WHERE id = $1""",
                instance_id, current + 1, json.dumps(step_outputs),
            )
            # Recurse to next step
            await _advance_workflow(pool, instance_id)
            return

        # Build task prompt from template
        prompt = _interpolate(step.get("prompt_template", ""), dict(inst))

        # Create task for this step
        work_dir = step.get("working_directory") or inst["working_directory"] or tmpl["default_working_dir"]
        task_row = await pool.fetchrow(
            """INSERT INTO tasks
               (title, prompt, priority, model, cli, agent_type,
                max_budget_usd, max_turns, timeout_seconds,
                working_directory, created_by, metadata)
               VALUES ($1, $2, $3, 'sonnet', 'claude', $4,
                       $5, $6, $7, $8, 'workflow', $9)
               RETURNING id, title""",
            f"[WF] {inst['name']} / Step {current}: {step['name']}",
            prompt,
            inst["priority"],
            step.get("agent_type"),
            step.get("max_budget_usd", 5.0),
            step.get("max_turns", 50),
            step.get("timeout_seconds", 900),
            work_dir,
            json.dumps({
                "workflow_instance_id": str(instance_id),
                "workflow_step": current,
                "workflow_step_name": step.get("name", ""),
            }),
        )
        task_id = task_row["id"]

        # Record task ID in instance
        step_task_ids = _jsonb(inst["step_task_ids"])
        step_task_ids[str(current)] = str(task_id)
        await pool.execute(
            "UPDATE workflow_instances SET step_task_ids = $2::jsonb WHERE id = $1",
            instance_id, json.dumps(step_task_ids),
        )

        log.info(f"Workflow {instance_id} step {current}: created task {task_id} (agent={step.get('agent_type')})")

        # Launch the task
        try:
            from .tasks import _count_running_by_cli, CLI_CONCURRENCY
            cli_counts = await _count_running_by_cli(pool)
            claude_running = cli_counts.get("claude", 0)

            if claude_running < CLI_CONCURRENCY["claude"]:
                task_env = os.environ.copy()
                task_env.pop("CLAUDECODE", None)
                task_env.setdefault("HOME", "/home/web3relic")
                task_env.setdefault("USER", "web3relic")
                task_env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"

                proc = subprocess.Popen(
                    [TASK_RUNNER, str(task_id)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    env=task_env,
                )
                await pool.execute(
                    "UPDATE tasks SET status = 'running', pid = $2, started_at = now() WHERE id = $1",
                    task_id, proc.pid,
                )
                log.info(f"Workflow {instance_id} step {current}: launched task {task_id} as PID {proc.pid}")
            else:
                log.info(f"Workflow {instance_id} step {current}: task {task_id} queued (no slots)")
        except Exception as e:
            log.warning(f"Workflow {instance_id}: task launch failed: {e}")

    except Exception as e:
        log.error(f"Workflow advance failed for {instance_id}: {e}", exc_info=True)
        try:
            await pool.execute(
                "UPDATE workflow_instances SET status = 'failed', error = $2 WHERE id = $1",
                instance_id, str(e),
            )
        except Exception:
            pass


async def handle_step_completion(pool, instance_id: UUID, task_id: UUID, task_status: str):
    """Called when a task that belongs to a workflow completes.

    Stores output, handles failure policies, and advances to next step.
    """
    try:
        inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
        if not inst or inst["status"] not in ("running",):
            return

        tmpl = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", inst["template_id"])
        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        current = inst["current_step"]
        step = steps[current] if current < len(steps) else {}

        # Get task output
        task = await pool.fetchrow("SELECT output, error, exit_code FROM tasks WHERE id = $1", task_id)
        output = task["output"] or ""

        # Store step output and duration
        step_outputs = _jsonb(inst["step_outputs"])
        step_outputs[str(current)] = output[:50000]

        step_durations = _jsonb(inst["step_durations"])
        task_full = await pool.fetchrow(
            "SELECT started_at, completed_at FROM tasks WHERE id = $1", task_id
        )
        if task_full["started_at"] and task_full["completed_at"]:
            duration = (task_full["completed_at"] - task_full["started_at"]).total_seconds()
            step_durations[str(current)] = round(duration, 1)

        if task_status == "completed":
            # Success — check for gate config before advancing
            gate_cfg = step.get("gate") or {}
            review_mode = step.get("review_mode", "auto")

            # Backward compat: review_mode=human_approval → create human post-gate
            if not gate_cfg and review_mode == "human_approval":
                gate_cfg = {
                    "type": "human", "position": "post",
                    "timeout_seconds": 86400, "timeout_action": "escalate",
                }

            if gate_cfg and gate_cfg.get("position", "post") == "post":
                # Check if we already have an approved/skipped post-gate for this step
                existing = await pool.fetchrow("""
                    SELECT status FROM workflow_gates
                    WHERE instance_id = $1 AND step_position = $2 AND gate_position = 'post'
                    ORDER BY created_at DESC LIMIT 1
                """, instance_id, current)

                if not existing or existing["status"] == "pending":
                    if not existing:
                        # Persist step outputs before pausing
                        await pool.execute(
                            """UPDATE workflow_instances
                               SET step_outputs = $2::jsonb, step_durations = $3::jsonb
                               WHERE id = $1""",
                            instance_id, json.dumps(step_outputs), json.dumps(step_durations),
                        )
                        # Create gate record (also sets instance status=paused)
                        context = {"step_output": output[:3000]}
                        gate_id = await _create_gate(
                            pool, instance_id, current, "post", gate_cfg, context
                        )
                        log.info(f"Workflow {instance_id} step {current}: gate {gate_id} created (post)")
                        # Notify via gate_notifier (WhatsApp + webhooks)
                        gate_row = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
                        step_name = step.get("name", f"Step {current}")
                        asyncio.create_task(
                            gate_notifier.gate_pending(
                                dict(gate_row),
                                {"id": str(instance_id), "name": inst["name"]},
                                {"name": step_name},
                            )
                        )
                    return  # Pause; gate pending (new or existing)

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

        else:
            # Task failed — apply on_failure policy
            on_failure = step.get("on_failure", "pause")
            retry_count = inst["retry_count"]

            if on_failure == "retry_once" and retry_count < 1:
                log.info(f"Workflow {instance_id} step {current}: retrying (attempt {retry_count + 1})")
                await pool.execute(
                    """UPDATE workflow_instances
                       SET retry_count = retry_count + 1,
                           step_outputs = $2::jsonb
                       WHERE id = $1""",
                    instance_id, json.dumps(step_outputs),
                )
                await _advance_workflow(pool, instance_id)

            elif on_failure == "skip":
                log.info(f"Workflow {instance_id} step {current}: skipping failed step")
                step_outputs[str(current)] = f"[FAILED-SKIPPED] {task['error'] or output[:200]}"
                await pool.execute(
                    """UPDATE workflow_instances
                       SET current_step = current_step + 1,
                           step_outputs = $2::jsonb,
                           retry_count = 0
                       WHERE id = $1""",
                    instance_id, json.dumps(step_outputs),
                )
                await _advance_workflow(pool, instance_id)

            elif on_failure == "fail_workflow":
                await pool.execute(
                    """UPDATE workflow_instances
                       SET status = 'failed', error = $2,
                           step_outputs = $3::jsonb, completed_at = now()
                       WHERE id = $1""",
                    instance_id, task["error"] or "Step failed", json.dumps(step_outputs),
                )
                log.info(f"Workflow {instance_id}: failed at step {current}")
                # Plans: notify plan coordinator
                from .task_plans import check_plan_workflow_complete
                asyncio.create_task(check_plan_workflow_complete(pool, instance_id, "failed"))

            else:  # pause (default)
                await pool.execute(
                    """UPDATE workflow_instances
                       SET status = 'paused', error = $2,
                           step_outputs = $3::jsonb
                       WHERE id = $1""",
                    instance_id, task["error"] or "Step failed", json.dumps(step_outputs),
                )
                log.info(f"Workflow {instance_id} step {current}: paused after failure")

    except Exception as e:
        log.error(f"Workflow step completion failed for {instance_id}: {e}", exc_info=True)


async def check_workflow_advance(pool, task_id: UUID, task_status: str):
    """Check if a completed task belongs to a workflow; if so, advance it.

    Called from tasks.py:complete_task as a fire-and-forget hook.
    """
    try:
        # Look up workflow_instance_id from task metadata
        meta_raw = await pool.fetchval("SELECT metadata FROM tasks WHERE id = $1", task_id)
        if not meta_raw:
            return
        meta = meta_raw if isinstance(meta_raw, dict) else json.loads(meta_raw)
        wf_id = meta.get("workflow_instance_id")
        if not wf_id:
            return

        instance_id = UUID(wf_id)
        await handle_step_completion(pool, instance_id, task_id, task_status)

    except Exception as e:
        log.debug(f"Workflow advance check for task {str(task_id)[:8]}: {e}")


# ── Auto-Eval (autoresearch pattern) ─────────────────────────────────────

async def _auto_eval_workflow(pool, instance_id: UUID):
    """Evaluate a completed workflow run — per-step and overall.

    Scores each step individually, identifies weak spots, records fitness,
    and triggers evolution if enough data has accumulated.
    """
    try:
        inst = await pool.fetchrow("SELECT * FROM workflow_instances WHERE id = $1", instance_id)
        if not inst or inst["status"] != "completed":
            return

        tmpl = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", inst["template_id"])
        if not tmpl:
            return

        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        step_outputs = inst["step_outputs"] or {}
        if isinstance(step_outputs, str):
            step_outputs = json.loads(step_outputs)
        step_durations = inst["step_durations"] or {}
        if isinstance(step_durations, str):
            step_durations = json.loads(step_durations)

        # Build per-step summary for the evaluator
        step_summaries = []
        for i, step in enumerate(steps):
            output = step_outputs.get(str(i), "")
            duration = step_durations.get(str(i), "?")
            step_summaries.append(
                f"Step {i} ({step.get('name', '?')}, agent={step.get('agent_type', 'none')}):\n"
                f"  Duration: {duration}s\n"
                f"  Output preview: {str(output)[:500]}\n"
            )

        from ..kernel.provider import provider_chat
        eval_prompt = (
            f"Evaluate this multi-step workflow execution. Score each step AND the overall pipeline.\n\n"
            f"Workflow: {inst['name']}\n"
            f"Template: {tmpl['name']}\n"
            f"Trigger: {inst.get('trigger_message', 'manual')}\n\n"
            f"Step-by-step execution:\n{''.join(step_summaries)}\n\n"
            f"Score each step 0.0-1.0 on output quality. Score overall pipeline 0.0-1.0.\n"
            f"Identify the WEAKEST step and suggest ONE specific improvement.\n\n"
            f"Return ONLY valid JSON:\n"
            f'{{"step_scores": [0.8, 0.6, ...], "overall": 0.0-1.0, '
            f'"quality": 0.0-1.0, "relevance": 0.0-1.0, "efficiency": 0.0-1.0, '
            f'"weakest_step": <int>, "weakness": "<what was wrong>", '
            f'"mutation_suggestion": "<specific change to improve the weakest step>", '
            f'"notes": "<brief overall assessment>"}}'
        )

        response = await provider_chat(
            messages=[{"role": "user", "content": eval_prompt}],
            max_tokens=500,
            temperature=0.1,
        )

        from ..llm import extract_json
        scores = extract_json(response)
        if not scores or "overall" not in scores:
            log.warning(f"Workflow eval: could not parse scores")
            return

        # Store eval results
        await pool.execute(
            """UPDATE workflow_instances
               SET eval_scores = $2::jsonb, eval_output = $3
               WHERE id = $1""",
            instance_id, json.dumps(scores), response,
        )

        overall = float(scores["overall"])
        current_fitness = tmpl["fitness_score"]

        # Update template fitness if improved
        if current_fitness is None or overall > float(current_fitness):
            await pool.execute(
                "UPDATE workflow_templates SET fitness_score = $2 WHERE id = $1",
                tmpl["id"], overall,
            )
            log.info(f"Workflow eval: {tmpl['name']} new best fitness={overall:.3f}")
        else:
            log.info(f"Workflow eval: {tmpl['name']} fitness={overall:.3f} (best={current_fitness})")

        # Record experiment (even without mutation — baseline tracking)
        await pool.execute(
            """INSERT INTO workflow_experiments
               (template_id, template_version, mutation_type, mutation_detail,
                instance_id, fitness_score, baseline_score, improvement, kept, cost_usd)
               VALUES ($1, $2, 'baseline', 'No mutation — baseline run', $3, $4, $5, $6, $7, $8)""",
            tmpl["id"], tmpl["version"], instance_id, overall,
            float(current_fitness) if current_fitness else None,
            overall - float(current_fitness) if current_fitness else None,
            current_fitness is None or overall > float(current_fitness),
            float(inst["cost_total"] or 0),
        )

        # Check if we should trigger evolution
        # Evolve after every 3 completed runs of the same template
        run_count = await pool.fetchval(
            """SELECT COUNT(*) FROM workflow_instances
               WHERE template_id = $1 AND status = 'completed'""",
            tmpl["id"],
        )
        if run_count > 0 and run_count % 3 == 0 and scores.get("mutation_suggestion"):
            log.info(f"Workflow eval: triggering evolution for {tmpl['name']} (run #{run_count})")
            asyncio.create_task(
                _evolve_template(pool, tmpl["id"], scores)
            )

    except Exception as e:
        log.warning(f"Workflow auto-eval failed for {instance_id}: {e}")


# ── Evolution Engine (autoresearch pattern) ──────────────────────────────

async def _evolve_template(pool, template_id: UUID, eval_scores: dict):
    """Mutate a workflow template based on evaluation feedback.

    Autoresearch pattern: Modify → (next run will) Execute → Measure → Keep/Discard.

    The mutation is applied to the template. The NEXT run using this template
    will use the mutated version. After that run's eval, we compare fitness:
    - If improved: keep (version incremented, mutation recorded as kept=True)
    - If worse: revert (restore previous version, mutation recorded as kept=False)
    """
    try:
        tmpl = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", template_id)
        if not tmpl:
            return

        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        weakest = eval_scores.get("weakest_step")
        suggestion = eval_scores.get("mutation_suggestion", "")

        if weakest is None or not suggestion or weakest >= len(steps):
            log.info(f"Evolution: no actionable mutation for {tmpl['name']}")
            return

        weak_step = steps[weakest]
        current_version = tmpl["version"]

        # Use LLM to generate the actual mutation
        from ..kernel.provider import provider_chat
        mutate_prompt = (
            f"You are optimizing a workflow template step. Apply this improvement:\n\n"
            f"Suggestion: {suggestion}\n\n"
            f"Current step (position {weakest}):\n"
            f"  Name: {weak_step.get('name')}\n"
            f"  Agent: {weak_step.get('agent_type')}\n"
            f"  Prompt template: {weak_step.get('prompt_template', '')[:1000]}\n"
            f"  Budget: ${weak_step.get('max_budget_usd', 5.0)}\n"
            f"  Timeout: {weak_step.get('timeout_seconds', 900)}s\n\n"
            f"Return ONLY valid JSON with the modified step fields. Only include fields you're changing:\n"
            f'{{"prompt_template": "<improved prompt>", "max_budget_usd": <if changed>, '
            f'"timeout_seconds": <if changed>, "agent_type": "<if changed>"}}\n\n'
            f"Keep changes minimal and targeted. Do NOT change the step name or position."
        )

        response = await provider_chat(
            messages=[{"role": "user", "content": mutate_prompt}],
            max_tokens=800,
            temperature=0.3,
        )

        from ..llm import extract_json
        mutation = extract_json(response)
        if not mutation:
            log.warning(f"Evolution: could not parse mutation for {tmpl['name']}")
            return

        # Apply mutation to the step
        old_step = dict(weak_step)
        for k, v in mutation.items():
            if k in ("prompt_template", "max_budget_usd", "timeout_seconds",
                      "max_turns", "agent_type", "on_failure"):
                weak_step[k] = v

        steps[weakest] = weak_step
        new_version = current_version + 1

        # Save the mutated template
        await pool.execute(
            """UPDATE workflow_templates
               SET steps = $2::jsonb, version = $3, parent_version_id = $4
               WHERE id = $1""",
            template_id, json.dumps(steps), new_version, template_id,
        )

        # Build diff for experiment record
        diff = {}
        for k in mutation:
            if k in old_step and old_step[k] != weak_step.get(k):
                diff[k] = {"old": str(old_step[k])[:200], "new": str(weak_step[k])[:200]}

        mutation_type = "prompt_edit"
        if "agent_type" in mutation:
            mutation_type = "agent_swap"
        elif "max_budget_usd" in mutation or "timeout_seconds" in mutation:
            mutation_type = "budget_adjust"

        # Record the experiment (kept=None — pending next run's eval)
        await pool.execute(
            """INSERT INTO workflow_experiments
               (template_id, template_version, mutation_type, mutation_detail,
                mutation_diff, baseline_score, kept)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6, NULL)""",
            template_id, new_version, mutation_type,
            f"Step {weakest} ({weak_step.get('name')}): {suggestion[:200]}",
            json.dumps(diff),
            float(tmpl["fitness_score"]) if tmpl["fitness_score"] else None,
        )

        log.info(
            f"Evolution: {tmpl['name']} v{current_version}→v{new_version} "
            f"mutated step {weakest} ({mutation_type}): {suggestion[:100]}"
        )

    except Exception as e:
        log.warning(f"Evolution failed for template {template_id}: {e}")


@router.post("/templates/{template_id}/evolve")
async def trigger_evolution(template_id: UUID):
    """Manually trigger an evolution cycle for a template.

    Uses the latest completed run's eval scores to generate a mutation.
    """
    pool = await get_pool()

    tmpl = await pool.fetchrow("SELECT * FROM workflow_templates WHERE id = $1", template_id)
    if not tmpl:
        raise HTTPException(404, "Template not found")

    # Find latest completed instance with eval scores
    latest = await pool.fetchrow(
        """SELECT * FROM workflow_instances
           WHERE template_id = $1 AND status = 'completed'
             AND eval_scores != '{}'::jsonb
           ORDER BY completed_at DESC LIMIT 1""",
        template_id,
    )
    if not latest:
        raise HTTPException(400, "No completed runs with eval scores found")

    scores = latest["eval_scores"]
    if isinstance(scores, str):
        scores = json.loads(scores)

    if not scores.get("mutation_suggestion"):
        # Generate a suggestion — including structural mutations
        from ..kernel.provider import provider_chat
        from ..llm import extract_json
        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        step_details = [f"  {i}. {s.get('name')} (agent={s.get('agent_type')}, ${s.get('max_budget_usd',5)}, {s.get('timeout_seconds',900)}s)" for i, s in enumerate(steps)]

        # Check experiment history for stagnation
        exp_count = await pool.fetchval(
            "SELECT COUNT(*) FROM workflow_experiments WHERE template_id = $1", template_id
        )
        recent_improvements = await pool.fetchval(
            "SELECT COUNT(*) FROM workflow_experiments WHERE template_id = $1 AND kept = TRUE AND created_at > NOW() - INTERVAL '7 days'",
            template_id,
        )

        stagnation_note = ""
        if exp_count > 5 and recent_improvements == 0:
            stagnation_note = "\nWARNING: Template is STAGNATING — no improvements in last 7 days. Consider STRUCTURAL mutations (add step, remove step, reorder, change agent type) not just prompt edits."

        response = await provider_chat(
            messages=[{"role": "user", "content": (
                f"Workflow template '{tmpl['name']}' v{tmpl['version']} has fitness {tmpl['fitness_score']}.\n"
                f"Steps:\n{''.join(step_details)}\n"
                f"Last eval: {json.dumps(scores)}\n"
                f"Experiments so far: {exp_count} (recent improvements: {recent_improvements})\n"
                f"{stagnation_note}\n\n"
                f"Suggest ONE specific mutation to improve fitness. Options:\n"
                f"- prompt_edit: improve a step's prompt template\n"
                f"- budget_adjust: change budget/timeout for a step\n"
                f"- agent_swap: change which agent handles a step\n"
                f"- step_add: add a new step (provide full step spec)\n"
                f"- step_remove: remove a redundant step\n"
                f"- step_reorder: swap two steps\n\n"
                f"Return JSON: {{\"weakest_step\": <int>, \"mutation_suggestion\": \"<specific change>\", \"mutation_type\": \"<type>\"}}"
            )}],
            max_tokens=300,
            temperature=0.3,
        )
        suggestion = extract_json(response)
        if suggestion:
            scores.update(suggestion)

    await _evolve_template(pool, template_id, scores)
    updated = await pool.fetchrow("SELECT version, fitness_score FROM workflow_templates WHERE id = $1", template_id)

    return {
        "status": "evolved",
        "template": tmpl["name"],
        "new_version": updated["version"],
        "fitness_score": float(updated["fitness_score"]) if updated["fitness_score"] else None,
    }


@router.get("/templates/{template_id}/fitness")
async def get_fitness_history(template_id: UUID, limit: int = 20):
    """Get fitness score history for a template across runs."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT wi.id, wi.name, wi.eval_scores, wi.cost_total,
                  wi.completed_at, wi.step_durations,
                  we.mutation_type, we.mutation_detail, we.kept, we.template_version
           FROM workflow_instances wi
           LEFT JOIN workflow_experiments we ON we.instance_id = wi.id
           WHERE wi.template_id = $1 AND wi.status = 'completed'
           ORDER BY wi.completed_at DESC LIMIT $2""",
        template_id, limit,
    )
    history = []
    for r in rows:
        scores = r["eval_scores"] or {}
        if isinstance(scores, str):
            try:
                scores = json.loads(scores)
            except Exception:
                scores = {}
        history.append({
            "instance_id": str(r["id"]),
            "name": r["name"],
            "fitness": float(scores.get("overall", 0)),
            "quality": float(scores.get("quality", 0)),
            "relevance": float(scores.get("relevance", 0)),
            "efficiency": float(scores.get("efficiency", 0)),
            "cost": float(r["cost_total"] or 0),
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "mutation_type": r["mutation_type"],
            "mutation_detail": r["mutation_detail"],
            "kept": r["kept"],
            "version": r["template_version"],
        })
    return {"template_id": str(template_id), "history": history}


# ── Notifications ────────────────────────────────────────────────────────

def _extract_deliverable(text: str, max_chars: int = 3000) -> str:
    """Extract the most relevant content from a workflow step output.

    Priority:
    1. Content between [DELIVERABLE] ... [/DELIVERABLE] markers
    2. A '## WHATSAPP DELIVERY' or '## RESEARCH DELIVERABLE' section
    3. A '### Top 3' or '## Final Report' or '## Summary' section
    4. Last N chars (findings usually at the end)
    5. First N chars truncated at newline boundary
    """
    if not text:
        return "(no output)"

    # 1. Explicit delivery markers
    import re
    marker_match = re.search(r'\[DELIVERABLE\](.*?)\[/DELIVERABLE\]', text, re.DOTALL | re.IGNORECASE)
    if marker_match:
        return marker_match.group(1).strip()[:max_chars]

    # 2. Named delivery sections
    for section_header in ['## WHATSAPP DELIVERY', '## RESEARCH DELIVERABLE', '## DELIVERY SUMMARY']:
        idx = text.find(section_header)
        if idx >= 0:
            section = text[idx:idx + max_chars]
            # Cut at next ## heading if present
            next_heading = re.search(r'\n##\s', section[3:])
            if next_heading:
                section = section[:next_heading.start() + 3]
            return section.strip()

    # 3. Summary/report sections
    for section_header in ['### Top 3 Actionable', '## Final Report', '## Summary', '### Summary']:
        idx = text.find(section_header)
        if idx >= 0:
            return text[idx:idx + max_chars].strip()

    # 4. If text is short enough, return it all
    if len(text) <= max_chars:
        return text.strip()

    # 5. Take the last max_chars chars (findings usually at the end), break at newline
    tail = text[-max_chars:]
    nl = tail.find('\n')
    if nl > 0:
        tail = tail[nl + 1:]
    return tail.strip()


def _smart_truncate(msg: str, limit: int = 3500) -> str:
    """Truncate at a newline boundary near the limit."""
    if len(msg) <= limit:
        return msg
    cutoff = msg[:limit].rfind('\n')
    if cutoff > limit // 2:
        return msg[:cutoff] + "\n...[truncated]"
    return msg[:limit] + "...[truncated]"


# ── Gate Engine ─────────────────────────────────────────────────────────


async def _create_gate(
    pool, instance_id: UUID, step_position: int,
    gate_position: str, gate_cfg: dict, context_snapshot: dict
) -> UUID:
    """Insert a workflow_gate row and pause the workflow instance. Returns gate ID."""
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
        elif on_rejection == "skip_step":
            inst_s = await pool.fetchrow(
                "SELECT step_outputs FROM workflow_instances WHERE id = $1", instance_id
            )
            step_outputs = _jsonb(inst_s["step_outputs"])
            step_outputs[str(step_position)] = f"[GATE-SKIP] {reason or ''}"
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'running',
                       current_step = current_step + 1,
                       step_outputs = $2::jsonb
                   WHERE id = $1""",
                instance_id, json.dumps(step_outputs),
            )
            asyncio.create_task(_advance_workflow(pool, instance_id))
        else:  # fail_workflow (default)
            await pool.execute(
                """UPDATE workflow_instances
                   SET status = 'failed', error = $2, completed_at = now()
                   WHERE id = $1""",
                instance_id, f"Gate rejected: {reason or 'no reason'}",
            )

    # Notify gate resolved (WhatsApp + webhooks)
    try:
        inst_row = await pool.fetchrow(
            "SELECT id, name FROM workflow_instances WHERE id = $1", instance_id
        )
        gate_final = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
        if inst_row and gate_final:
            asyncio.create_task(
                gate_notifier.gate_resolved(
                    dict(gate_final),
                    {"id": str(instance_id), "name": inst_row["name"]},
                    gate_status,
                )
            )
    except Exception as e:
        log.warning(f"gate_resolved notification failed: {e}")

    return {"gate_id": str(gate_id), "gate_status": gate_status, "workflow_action": action}


async def _check_gate_timeouts(pool) -> int:
    """Poll for expired pending gates and apply their timeout_action.
    Returns number of gates processed.
    Called by reflection heartbeat via POST /workflows/gates/check-timeouts.
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
            # Notify via gate_notifier (WhatsApp + webhooks)
            gate_row = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
            if gate_row:
                asyncio.create_task(
                    gate_notifier.gate_escalated(
                        dict(gate_row),
                        {"id": str(gate["instance_id"]), "name": gate["workflow_name"]},
                    )
                )
        else:
            # Auto-resolve with configured action (approve/reject/skip)
            try:
                await _resolve_gate(pool, gate_id, action, "system:timeout", "Auto-resolved on timeout")
            except Exception as e:
                log.error(f"Failed to auto-resolve gate {gate_id}: {e}")

        processed += 1

    return processed


async def _check_dao_quorum(pool, gate_id: UUID) -> dict:
    """Compute vote tally for a DAO gate. Auto-resolves if quorum + threshold reached.

    Auto-approval:    quorum reached AND approve_pct >= threshold.
    Early-rejection:  quorum reached AND reject_pct > (1 - threshold), making
                      approval threshold mathematically unreachable.
    """
    gate = await pool.fetchrow("SELECT * FROM workflow_gates WHERE id = $1", gate_id)
    if not gate or gate["status"] != "pending":
        return {
            "resolved": False,
            "reason": f"gate status={gate['status'] if gate else 'not found'}",
        }

    votes = await pool.fetch(
        "SELECT vote, weight FROM workflow_gate_votes WHERE gate_id = $1", gate_id
    )

    approve_weight = sum(float(v["weight"]) for v in votes if v["vote"] == "approve")
    reject_weight  = sum(float(v["weight"]) for v in votes if v["vote"] == "reject")
    total_weight   = approve_weight + reject_weight   # abstain excluded from threshold calc
    vote_count     = len(votes)

    quorum_needed  = gate["quorum_required"] or 1
    threshold      = float(gate["approval_threshold"] or 0.5)
    quorum_reached = vote_count >= quorum_needed
    approve_pct    = approve_weight / max(total_weight, 0.0001)
    reject_pct     = reject_weight  / max(total_weight, 0.0001)

    tally = {
        "vote_count":      vote_count,
        "approve_weight":  approve_weight,
        "reject_weight":   reject_weight,
        "total_weight":    total_weight,
        "approve_pct":     round(approve_pct, 4),
        "reject_pct":      round(reject_pct, 4),
        "quorum_required": quorum_needed,
        "quorum_reached":  quorum_reached,
        "threshold":       threshold,
        "threshold_met":   approve_pct >= threshold,
        "resolved":        False,
    }

    if quorum_reached:
        if approve_pct >= threshold:
            try:
                await _resolve_gate(pool, gate_id, "approve", "dao:quorum",
                                    "Quorum reached with approval threshold")
            except ValueError:
                pass  # Concurrent resolve — ignore
            tally["resolved"] = True
            tally["resolution"] = "approved"
        elif reject_pct > (1.0 - threshold):
            # Approval is now mathematically impossible even if all remaining voters approve
            try:
                await _resolve_gate(pool, gate_id, "reject", "dao:quorum",
                                    "Quorum reached — approval threshold cannot be met")
            except ValueError:
                pass  # Concurrent resolve — ignore
            tally["resolved"] = True
            tally["resolution"] = "rejected"

    return tally


# ── End Gate Engine ──────────────────────────────────────────────────────


async def _notify_workflow_complete(inst: dict, tmpl: dict):
    """Notify Mev when a workflow completes.

    For research pipelines, include the research findings summary.
    For other workflows, include the last step output preview.
    """
    try:
        steps = tmpl["steps"] if isinstance(tmpl["steps"], list) else json.loads(tmpl["steps"])
        step_count = len(steps)
        name = inst.get("name", "Workflow")
        instance_id = inst.get("id", "")

        # Determine if this is a research pipeline
        tags = tmpl.get("tags") or []
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except Exception:
                tags = []
        is_research = "research" in tags or "research" in tmpl.get("name", "").lower()

        step_outputs = inst.get("step_outputs") or {}
        if isinstance(step_outputs, str):
            try:
                step_outputs = json.loads(step_outputs)
            except Exception:
                step_outputs = {}

        # Check if the last step is a notify action (already sent a delivery WhatsApp)
        last_step = steps[-1] if steps else {}
        has_notify_step = last_step.get("action") == "notify"

        if has_notify_step:
            # The notify step already sent the research findings via WhatsApp.
            # Send only a brief confirmation so Mev isn't double-pinged.
            log.info(f"Workflow {name}: notify step already sent delivery — skipping duplicate notification")
            return

        if is_research and step_outputs:
            # No notify step — find the last non-notify step output and deliver it
            last_output = ""
            for i in range(step_count - 1, -1, -1):
                step = steps[i] if i < len(steps) else {}
                if step.get("action") != "notify":
                    last_output = step_outputs.get(str(i), "")
                    break

            variables = inst.get("variables") or {}
            if isinstance(variables, str):
                try:
                    variables = json.loads(variables)
                except Exception:
                    variables = {}
            topic = variables.get("topic", name)

            deliverable = _extract_deliverable(last_output, max_chars=2500)
            msg = f"✅ Research complete: {topic}\n\n{deliverable}"
        else:
            # Generic workflow completion — include last step preview
            last_output = step_outputs.get(str(step_count - 2), "") if step_count >= 2 else ""
            preview = _smart_truncate(last_output, 500) if last_output else ""
            msg = f"✅ Workflow complete: {name}\n{step_count} steps done."
            if preview:
                msg += f"\n\nLast step output:\n{preview}"
            msg += f"\nID: {instance_id}"

        msg = _smart_truncate(msg, 3500)
        proc = await asyncio.create_subprocess_exec(
            "/home/web3relic/otto/tools/whatsapp_send.sh", msg,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        log.info(f"Workflow completion notified: {name} ({len(msg)} chars)")
    except Exception as e:
        log.warning(f"Workflow completion notification failed: {e}")


# ── Agent Directory ───────────────────────────────────────────────────────────

AGENCY_AGENTS_DIR = "/mnt/media/projects/agency-agents"
OTTO_AGENTS_DIR = "/home/web3relic/otto/.claude/agents"

# Files to skip at the root of the repo
_SKIP_NAMES = {"README.md", "CONTRIBUTING.md", "LICENSE", "LICENSE.md"}


def _parse_frontmatter(content: str) -> dict:
    """Extract key: value pairs from YAML frontmatter block."""
    import re
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    fm: dict = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


@router.get("/agents/available")
async def list_available_agents():
    """List all agents from the agency-agents repo (unemployed agents ready to activate)."""
    import glob as glob_module

    agents_dir = AGENCY_AGENTS_DIR
    otto_dir = OTTO_AGENTS_DIR

    # Collect names of already-activated agents (files present in otto agents dir)
    activated_names: set[str] = set()
    try:
        for fname in os.listdir(otto_dir):
            if fname.endswith(".md"):
                activated_names.add(fname[:-3].lower())  # strip .md, lowercase
    except OSError:
        pass

    results = []

    # Recursively find all .md files one level deep (category/file.md)
    pattern = os.path.join(agents_dir, "*", "*.md")
    for path in sorted(glob_module.glob(pattern)):
        filename = os.path.basename(path)
        if filename in _SKIP_NAMES:
            continue

        # Determine category from parent directory name
        category = os.path.basename(os.path.dirname(path))

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(4096)
        except OSError:
            continue

        fm = _parse_frontmatter(content)
        name = fm.get("name") or filename.replace(".md", "").replace("-", " ").title()
        description = fm.get("description") or ""

        # Check activation: name slug match or exact filename match
        slug = name.lower().replace(" ", "-")
        file_stem = filename[:-3].lower()
        activated = slug in activated_names or file_stem in activated_names

        results.append({
            "name": name,
            "description": description,
            "category": category,
            "file_path": path,
            "activated": activated,
        })

    return {"agents": results, "count": len(results)}


class ActivateAgentRequest(BaseModel):
    name: str
    source_path: str


@router.post("/agents/activate")
async def activate_agent(req: ActivateAgentRequest):
    """Copy an agent from agency-agents repo to Otto's agents directory and register it."""
    import shutil

    source = req.source_path
    if not os.path.isfile(source):
        raise HTTPException(404, f"Source file not found: {source}")

    # Sanitise destination filename — use the slugified name
    slug = req.name.lower().replace(" ", "-").replace("/", "-")
    dest_filename = f"{slug}.md"
    dest = os.path.join(OTTO_AGENTS_DIR, dest_filename)

    try:
        shutil.copy2(source, dest)
    except OSError as e:
        raise HTTPException(500, f"Failed to copy agent file: {e}")

    log.info(f"Activated agent '{req.name}' from {source} → {dest}")

    # Register in the skill registry (in-memory, for the current process lifespan)
    # The persistent record is the file on disk; skill suggestions pick up from there.
    from .skills import SKILL_REGISTRY
    already = any(s["name"] == slug for s in SKILL_REGISTRY)
    if not already:
        SKILL_REGISTRY.append({
            "name": slug,
            "description": req.name,
            "keywords": [w for w in req.name.lower().split() if len(w) > 3],
            "skill_type": "agent",
            "agent_type": slug,
            "cost": "medium",
        })

    return {
        "status": "activated",
        "name": req.name,
        "slug": slug,
        "dest": dest,
    }

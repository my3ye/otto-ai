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
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import get_pool

log = logging.getLogger("otto.workflows")
router = APIRouter(prefix="/workflows", tags=["workflows"])

TASK_RUNNER = "/home/web3relic/otto/task_runner.sh"


# ── Pydantic Models ──────────────────────────────────────────────────────

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
    action: str = "approve"   # approve | reject | skip
    reason: Optional[str] = None


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
    for k in ("created_at", "updated_at", "started_at", "completed_at"):
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
              "step_durations", "eval_scores", "mutation_diff", "metadata"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except (json.JSONDecodeError, TypeError):
                pass
    return d


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
        values[f"step_{pos}_output"] = str(output)[:8000]

    # prev_output = output of the step before current
    current = instance.get("current_step", 0)
    prev_pos = str(current - 1)
    if prev_pos in step_outputs:
        values["prev_output"] = str(step_outputs[prev_pos])[:8000]

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

    return result


@router.post("/instances/{instance_id}/approve")
async def approve_step(instance_id: UUID, req: WorkflowApproveRequest):
    """Human approves, rejects, or skips a paused workflow step."""
    pool = await get_pool()
    inst = await pool.fetchrow(
        "SELECT * FROM workflow_instances WHERE id = $1", instance_id
    )
    if not inst:
        raise HTTPException(404, "Instance not found")
    if inst["status"] != "paused":
        raise HTTPException(400, f"Instance is {inst['status']}, not paused")

    if req.action == "approve":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} approved by human")
        # Move to next step
        await pool.execute(
            """UPDATE workflow_instances
               SET current_step = current_step + 1, status = 'running'
               WHERE id = $1""",
            instance_id,
        )
        asyncio.create_task(_advance_workflow(pool, instance_id))
        return {"status": "approved", "next_step": inst["current_step"] + 1}

    elif req.action == "reject":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} rejected: {req.reason}")
        await pool.execute(
            "UPDATE workflow_instances SET status = 'failed', error = $2 WHERE id = $1",
            instance_id, f"Rejected by human: {req.reason or 'no reason'}",
        )
        return {"status": "rejected"}

    elif req.action == "skip":
        log.info(f"Workflow {instance_id}: step {inst['current_step']} skipped")
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
            # Success — check review_mode before advancing
            review_mode = step.get("review_mode", "auto")

            if review_mode == "human_approval":
                await pool.execute(
                    """UPDATE workflow_instances
                       SET status = 'paused', step_outputs = $2::jsonb, step_durations = $3::jsonb
                       WHERE id = $1""",
                    instance_id, json.dumps(step_outputs), json.dumps(step_durations),
                )
                log.info(f"Workflow {instance_id} step {current}: paused for human approval")

                # Notify Mev
                step_name = step.get("name", f"Step {current}")
                msg = f"Workflow '{inst['name']}' paused at step: {step_name}\nAwaiting your approval.\nApprove at: POST /workflows/instances/{instance_id}/approve"
                try:
                    proc = await asyncio.create_subprocess_exec(
                        "/home/web3relic/otto/tools/whatsapp_send.sh", msg,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=10)
                except Exception:
                    pass
                return

            # auto or agent_review — advance to next step
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

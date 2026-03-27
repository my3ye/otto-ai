"""Task Plans — DAG-based multi-task orchestration.

One instruction → N tasks with dependency edges → auto-execution.
Plans decompose complex instructions into a DAG of tasks (some backed by
workflows, some standalone) and execute them as dependencies clear.

Key concepts:
- Task Plan: a set of tasks sharing plan_id with depends_on edges
- Plan Executor: event-driven — on task completion, run newly unblocked tasks
- Agent Auto-Employment: activates agents from agency-agents/ if needed
- Dynamic Workflows: creates ad-hoc workflow templates when no existing one fits
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import get_pool
from ..llm import extract_json, extract_json_array, provider_chat
from .routing import model_for_agent

log = logging.getLogger("otto.task_plans")
router = APIRouter(prefix="/task-plans", tags=["task-plans"])

TASK_RUNNER = "/home/web3relic/otto/task_runner.sh"
AGENCY_AGENTS_DIR = "/mnt/media/projects/agency-agents"
ACTIVE_AGENTS_DIR = "/home/web3relic/otto/.claude/agents"


# ── Pydantic Models ──────────────────────────────────────────────────────

class PlanItemSpec(BaseModel):
    """Specification for one item in a task plan (from the classifier)."""
    temp_id: str
    title: str
    prompt: str
    agent_type: str | None = None
    depends_on: list[str] = Field(default_factory=list)  # temp_ids
    workflow_template: str | None = None
    workflow_variables: dict = Field(default_factory=dict)
    priority: int = 5
    working_directory: str = "/home/web3relic/otto"


class CreatePlanRequest(BaseModel):
    """Create a task plan from a pre-decomposed specification."""
    title: str
    instruction: str
    items: list[PlanItemSpec]
    created_by: str = "reactive_dispatch"
    trigger_message: str | None = None


class PlanOut(BaseModel):
    id: UUID
    title: str
    instruction: str
    status: str
    topology: str | None
    total_items: int
    completed_items: int
    failed_items: int
    agents_employed: list[str]
    created_by: str
    created_at: str
    completed_at: str | None = None
    tasks: list[dict] = Field(default_factory=list)


# ── Topology Detection ───────────────────────────────────────────────────

def _compute_topology(items: list[PlanItemSpec]) -> str:
    """AdaptOrch-inspired topology classification from dependency edges."""
    n = len(items)
    if n <= 1:
        return "sequential"
    total_edges = sum(len(it.depends_on) for it in items)
    if total_edges == 0:
        return "parallel"
    # Check for linear chain: exactly n-1 edges and each node has at most 1 dep
    if total_edges == n - 1 and all(len(it.depends_on) <= 1 for it in items):
        return "sequential"
    return "hybrid"


# ── Agent Auto-Employment ────────────────────────────────────────────────

async def _auto_employ_agents(agent_types: list[str]) -> list[str]:
    """Check if needed agents are active. Activate from agency-agents if not.

    Returns list of newly employed agent names.
    """
    employed = []
    for agent_type in set(agent_types):
        if not agent_type:
            continue
        agent_path = os.path.join(ACTIVE_AGENTS_DIR, f"{agent_type}.md")
        if os.path.exists(agent_path):
            continue  # Already active

        # Search agency-agents directory for a match
        match = _find_agency_agent(agent_type)
        if match:
            try:
                shutil.copy2(match, agent_path)
                employed.append(agent_type)
                log.info(f"Auto-employed agent '{agent_type}' from {match}")
            except Exception as e:
                log.warning(f"Failed to activate agent '{agent_type}': {e}")

    return employed


def _find_agency_agent(agent_type: str) -> str | None:
    """Find an agent file in agency-agents/ that matches the requested type.

    Searches by exact filename match first, then by partial match.
    Returns the source file path or None.
    """
    if not os.path.isdir(AGENCY_AGENTS_DIR):
        return None

    # Exact match: look for {agent_type}.md in any category subdirectory
    for category in os.listdir(AGENCY_AGENTS_DIR):
        cat_dir = os.path.join(AGENCY_AGENTS_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        for fname in os.listdir(cat_dir):
            if not fname.endswith(".md"):
                continue
            # agency-agents convention: {category}-{name}.md
            slug = fname.replace(".md", "")
            # Remove category prefix if present
            name_part = slug.split("-", 1)[-1] if "-" in slug else slug
            full_slug = slug

            if agent_type == full_slug or agent_type == name_part:
                return os.path.join(cat_dir, fname)

    # Partial match: check if agent_type is a substring
    for category in os.listdir(AGENCY_AGENTS_DIR):
        cat_dir = os.path.join(AGENCY_AGENTS_DIR, category)
        if not os.path.isdir(cat_dir):
            continue
        for fname in os.listdir(cat_dir):
            if not fname.endswith(".md"):
                continue
            slug = fname.replace(".md", "")
            if agent_type in slug or slug in agent_type:
                return os.path.join(cat_dir, fname)

    return None


# ── Plan Executor (DAG Scheduler) ────────────────────────────────────────

async def _launch_task(pool, task_id: UUID) -> bool:
    """Launch a single task if CLI capacity allows. Returns True if launched."""
    from .tasks import _count_running_by_cli, CLI_CONCURRENCY, TASK_RUNNER as TR

    try:
        cli_counts = await _count_running_by_cli(pool)
        claude_running = cli_counts.get("claude", 0)
        if claude_running >= CLI_CONCURRENCY["claude"]:
            log.info(f"Plan executor: no claude slots for task {str(task_id)[:8]}")
            return False

        task_env = os.environ.copy()
        task_env.pop("CLAUDECODE", None)
        task_env.setdefault("HOME", "/home/web3relic")
        task_env.setdefault("USER", "web3relic")
        task_env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"

        proc = subprocess.Popen(
            [TR, str(task_id)],
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
        log.info(f"Plan executor launched task {str(task_id)[:8]} as PID {proc.pid}")
        return True
    except Exception as e:
        log.warning(f"Plan executor launch failed for {str(task_id)[:8]}: {e}")
        return False


async def _spawn_workflow_for_plan_task(pool, task_id: UUID):
    """Create a workflow instance for a plan task that needs one.

    The plan task becomes a coordinator — it doesn't run task_runner.sh directly.
    Instead the workflow runs its steps. When the workflow completes, the task
    gets marked completed via check_plan_workflow_complete().
    """
    from .workflows import _advance_workflow

    row = await pool.fetchrow(
        "SELECT id, title, metadata, priority FROM tasks WHERE id = $1",
        task_id,
    )
    if not row:
        return

    meta = row["metadata"] if isinstance(row["metadata"], dict) else json.loads(row["metadata"] or "{}")
    template_name = meta.get("workflow_template")
    variables = meta.get("workflow_variables", {})

    if not template_name:
        return

    tmpl = await pool.fetchrow(
        "SELECT id FROM workflow_templates WHERE name = $1 AND NOT archived",
        template_name,
    )
    if not tmpl:
        log.warning(f"Plan task {str(task_id)[:8]}: workflow template '{template_name}' not found, running as direct task")
        # Fall back to running as a direct task
        await _launch_task(pool, task_id)
        return

    # Create workflow instance linked to this plan task
    inst_row = await pool.fetchrow(
        """INSERT INTO workflow_instances
           (template_id, name, variables, priority, working_directory,
            trigger_source, trigger_message, created_by)
           VALUES ($1, $2, $3::jsonb, $4, '/home/web3relic/otto',
                   'plan_executor', $5, 'plan_executor')
           RETURNING id""",
        tmpl["id"], row["title"],
        json.dumps(variables),
        row["priority"],
        f"Plan task: {row['title']}",
    )
    instance_id = inst_row["id"]

    # Link the plan task to the workflow instance
    meta["workflow_instance_id"] = str(instance_id)
    meta["is_plan_coordinator"] = True
    await pool.execute(
        "UPDATE tasks SET status = 'running', started_at = now(), metadata = $2 WHERE id = $1",
        task_id, meta,
    )

    log.info(f"Plan task {str(task_id)[:8]} spawned workflow instance {str(instance_id)[:8]}")
    asyncio.create_task(_advance_workflow(pool, instance_id))


async def execute_plan(pool, plan_id: UUID):
    """Find tasks with all dependencies satisfied and run them.

    Called on plan creation and after each task completion.
    This is the core DAG scheduler.
    """
    # Check plan is still active
    plan = await pool.fetchrow(
        "SELECT id, status, total_items, completed_items, failed_items FROM task_plans WHERE id = $1",
        plan_id,
    )
    if not plan or plan["status"] not in ("pending", "executing"):
        return

    # Mark plan as executing if still pending
    if plan["status"] == "pending":
        await pool.execute(
            "UPDATE task_plans SET status = 'executing' WHERE id = $1",
            plan_id,
        )

    # Find all pending tasks where every dependency is completed
    ready_tasks = await pool.fetch("""
        SELECT t.id, t.metadata
        FROM tasks t
        WHERE t.plan_id = $1
          AND t.status = 'pending'
          AND NOT EXISTS (
              SELECT 1 FROM unnest(t.depends_on) AS dep_id
              WHERE NOT EXISTS (
                  SELECT 1 FROM tasks d
                  WHERE d.id = dep_id AND d.status = 'completed'
              )
          )
        ORDER BY t.priority DESC
    """, plan_id)

    if not ready_tasks:
        # Check if plan is done (no pending or running tasks left)
        remaining = await pool.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE plan_id = $1 AND status IN ('pending', 'running')",
            plan_id,
        )
        if remaining == 0:
            await _finalize_plan(pool, plan_id)
        return

    for task_row in ready_tasks:
        meta = task_row["metadata"] if isinstance(task_row["metadata"], dict) else json.loads(task_row["metadata"] or "{}")

        if meta.get("workflow_template"):
            # This task is workflow-backed — spawn workflow instance
            await _spawn_workflow_for_plan_task(pool, task_row["id"])
        else:
            # Direct task — inject dependency outputs into prompt, then launch
            await _inject_dep_outputs(pool, task_row["id"])
            launched = await _launch_task(pool, task_row["id"])
            if not launched:
                log.info(f"Plan {str(plan_id)[:8]}: task {str(task_row['id'])[:8]} stays pending (no slots)")


async def _inject_dep_outputs(pool, task_id: UUID):
    """Enrich a task's prompt with outputs from its completed dependencies.

    GAP-2: if a dependency has an artifact_path in metadata, read the full
    artifact file (up to 6000 chars) instead of the truncated DB output field.
    Falls back to DB output if the file is absent or unreadable.
    """
    row = await pool.fetchrow(
        "SELECT depends_on, prompt FROM tasks WHERE id = $1",
        task_id,
    )
    if not row or not row["depends_on"]:
        return

    deps = await pool.fetch("""
        SELECT title, LEFT(output, 6000) as output, metadata
        FROM tasks
        WHERE id = ANY($1) AND status = 'completed' AND output IS NOT NULL
    """, row["depends_on"])

    if not deps:
        return

    enrichment = "\n\n--- Context from completed prerequisites ---\n"
    for dep in deps:
        dep_meta = dep["metadata"] or {}
        if isinstance(dep_meta, str):
            try:
                dep_meta = json.loads(dep_meta)
            except Exception:
                dep_meta = {}

        dep_output = dep["output"]
        artifact_path = dep_meta.get("artifact_path") if isinstance(dep_meta, dict) else None
        used_artifact = False
        if artifact_path and os.path.exists(artifact_path):
            try:
                with open(artifact_path, "r") as f:
                    dep_output = f.read(6000)
                used_artifact = True
                log.debug(f"GAP-2: injecting artifact for dep '{dep['title'][:40]}'")
            except Exception:
                pass  # fall back to DB output already set above

        header = f"{dep['title']} [artifact]" if used_artifact else dep['title']
        enrichment += f"\n### {header}\n{dep_output}\n"

    new_prompt = row["prompt"] + enrichment
    await pool.execute(
        "UPDATE tasks SET prompt = $2 WHERE id = $1",
        task_id, new_prompt,
    )


async def _finalize_plan(pool, plan_id: UUID):
    """Mark a plan as completed or failed based on its tasks."""
    stats = await pool.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'skipped') as skipped,
            COUNT(*) as total
        FROM tasks WHERE plan_id = $1
    """, plan_id)

    if not stats:
        return

    all_done = (stats["completed"] + stats["failed"] + stats["skipped"]) >= stats["total"]
    if not all_done:
        return

    has_failures = stats["failed"] > 0
    plan_status = "failed" if has_failures and stats["completed"] == 0 else "completed"

    await pool.execute(
        """UPDATE task_plans
           SET status = $2, completed_items = $3, failed_items = $4, completed_at = now()
           WHERE id = $1""",
        plan_id, plan_status, stats["completed"], stats["failed"],
    )
    log.info(f"Plan {str(plan_id)[:8]} finalized as '{plan_status}' "
             f"({stats['completed']}/{stats['total']} completed, {stats['failed']} failed)")

    # Notify Mev
    plan = await pool.fetchrow("SELECT title FROM task_plans WHERE id = $1", plan_id)
    if plan:
        try:
            emoji = "done" if plan_status == "completed" else "partial"
            msg = (
                f"Plan {emoji}: {plan['title']}\n"
                f"{stats['completed']}/{stats['total']} tasks completed"
                + (f", {stats['failed']} failed" if stats['failed'] else "")
            )
            proc = await asyncio.create_subprocess_exec(
                "/home/web3relic/otto/tools/whatsapp_send.sh", msg,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        except Exception:
            pass


async def on_plan_task_complete(pool, task_id: UUID, status: str):
    """Called when any task completes. If it belongs to a plan, advance the DAG.

    Hooked into tasks.py:complete_task().
    """
    row = await pool.fetchrow(
        "SELECT plan_id FROM tasks WHERE id = $1",
        task_id,
    )
    if not row or not row["plan_id"]:
        return

    plan_id = row["plan_id"]

    # Update counters
    if status == "completed":
        await pool.execute(
            "UPDATE task_plans SET completed_items = completed_items + 1 WHERE id = $1",
            plan_id,
        )
    elif status == "failed":
        await pool.execute(
            "UPDATE task_plans SET failed_items = failed_items + 1 WHERE id = $1",
            plan_id,
        )
        # Check if any pending tasks depend on this failed task — mark them skipped
        await pool.execute("""
            UPDATE tasks SET status = 'skipped',
                   error = 'Dependency failed: ' || $2,
                   completed_at = now()
            WHERE plan_id = $3
              AND status = 'pending'
              AND $1 = ANY(depends_on)
        """, task_id, str(task_id), plan_id)

    # Re-run executor to check for newly unblocked tasks
    await execute_plan(pool, plan_id)


async def check_plan_workflow_complete(pool, workflow_instance_id: UUID, wf_status: str):
    """When a workflow instance completes, check if its coordinator plan task should too.

    Called from workflows.py after workflow completion.
    """
    # Find the plan task that owns this workflow instance
    row = await pool.fetchrow("""
        SELECT id, plan_id FROM tasks
        WHERE metadata->>'workflow_instance_id' = $1
          AND metadata->>'is_plan_coordinator' = 'true'
          AND status = 'running'
    """, str(workflow_instance_id))

    if not row:
        return

    # Gather workflow output (concatenate step outputs)
    inst = await pool.fetchrow(
        "SELECT step_outputs, eval_scores FROM workflow_instances WHERE id = $1",
        workflow_instance_id,
    )
    output = ""
    if inst and inst["step_outputs"]:
        step_outputs = inst["step_outputs"] if isinstance(inst["step_outputs"], dict) else json.loads(inst["step_outputs"])
        for k in sorted(step_outputs.keys(), key=lambda x: int(x)):
            val = step_outputs[k]
            if val and not val.startswith("[NOTIFIED]"):
                output += val + "\n\n"

    task_status = "completed" if wf_status == "completed" else "failed"
    exit_code = 0 if wf_status == "completed" else 1

    await pool.execute(
        """UPDATE tasks SET status = $2, output = $3, exit_code = $4,
              completed_at = now(), pid = NULL
           WHERE id = $1""",
        row["id"], task_status, output[:50000] if output else "Workflow completed.", exit_code,
    )

    log.info(f"Plan coordinator task {str(row['id'])[:8]} marked '{task_status}' (workflow {str(workflow_instance_id)[:8]})")

    # Trigger plan advancement
    if row["plan_id"]:
        await on_plan_task_complete(pool, row["id"], task_status)


# ── Plan Creation ────────────────────────────────────────────────────────

async def create_plan(
    pool,
    title: str,
    instruction: str,
    items: list[PlanItemSpec],
    created_by: str = "reactive_dispatch",
    trigger_message: str | None = None,
) -> UUID:
    """Create a task plan with all its tasks and start execution.

    1. Auto-employ needed agents
    2. Create plan row
    3. Create all task rows with plan_id and depends_on
    4. Start the DAG executor
    """
    # 1. Auto-employ agents
    agent_types = [it.agent_type for it in items if it.agent_type]
    employed = await _auto_employ_agents(agent_types)

    # 2. Compute topology
    topology = _compute_topology(items)

    # 3. Create plan
    plan_row = await pool.fetchrow(
        """INSERT INTO task_plans (title, instruction, topology, total_items,
               agents_employed, created_by, trigger_message)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           RETURNING id""",
        title, instruction[:2000], topology, len(items),
        employed, created_by, (trigger_message or "")[:500],
    )
    plan_id = plan_row["id"]

    # 4. Create tasks — first pass to get real UUIDs
    temp_to_uuid: dict[str, UUID] = {}
    for item in items:
        metadata = {}
        if item.workflow_template:
            metadata["workflow_template"] = item.workflow_template
            metadata["workflow_variables"] = item.workflow_variables

        # Coding agents (coder, debugger, architect, etc.) run on opus per Mev directive 2026-03-27
        task_model = model_for_agent(item.agent_type)
        row = await pool.fetchrow(
            """INSERT INTO tasks (title, prompt, priority, model, cli, agent_type,
                   max_budget_usd, max_turns, timeout_seconds,
                   working_directory, created_by, metadata, plan_id)
               VALUES ($1, $2, $3, $10, 'claude', $4,
                   $5, 50, 900, $6, $7, $8, $9)
               RETURNING id""",
            item.title, item.prompt, item.priority, item.agent_type,
            10.0 if item.priority >= 8 else 5.0,
            item.working_directory, created_by, metadata, plan_id, task_model,
        )
        temp_to_uuid[item.temp_id] = row["id"]

    # 5. Second pass: resolve depends_on temp_ids to real UUIDs
    for item in items:
        if not item.depends_on:
            continue
        dep_uuids = [temp_to_uuid[dep] for dep in item.depends_on if dep in temp_to_uuid]
        if dep_uuids:
            await pool.execute(
                "UPDATE tasks SET depends_on = $2 WHERE id = $1",
                temp_to_uuid[item.temp_id], dep_uuids,
            )

    log.info(f"Plan created: '{title}' ({len(items)} tasks, topology={topology}, "
             f"agents_employed={employed})")

    # 6. Start execution
    await execute_plan(pool, plan_id)

    return plan_id


# ── Plan Classifier ──────────────────────────────────────────────────────

_PLAN_CLASSIFIER_SYSTEM = """You decompose an instruction into a task plan — a set of tasks with dependency edges.

RULES:
1. Each task should be a single, focused unit of work (one agent can handle it).
2. Use depends_on to express data/order dependencies between tasks.
3. Tasks with no dependencies run in parallel automatically.
4. Pick the best agent_type for each task from: content-creator, researcher, coder, debugger, architect, reviewer, memory-curator, landing-page, security-audit, twitter-engager, social-media-strategist, growth-hacker, blockchain-security-auditor, solidity-smart-contract-engineer, outbound-strategist, sprint-prioritizer
5. If the task needs a multi-step pipeline, set workflow_template to one of:
   - "content-publishing-pipeline" — articles, blog posts, content that needs review
   - "feature-development" — code features that need architecture + review
   - "research-pipeline" — deep research with synthesis + validation
   - "social-content-pipeline" — social media content creation
   - null — for simple single-step tasks
6. workflow_variables should contain the data the workflow template needs.
7. Each task gets a temp_id (t1, t2, t3...) for dependency references.
8. Priority: 1-10 where 10 is most urgent. Default 5-7 for normal work.
9. If the instruction is a SINGLE simple task, return plan_needed=false.
10. Only return plan_needed=true when there are genuinely MULTIPLE distinct tasks or the work has clear stages with different specialists.

Return ONLY valid JSON (no markdown, no code fences):
{
  "plan_needed": true/false,
  "plan_title": "short descriptive title",
  "tasks": [
    {
      "temp_id": "t1",
      "title": "imperative task title",
      "prompt": "detailed actionable prompt (100-500 chars)",
      "agent_type": "specialist-name",
      "depends_on": [],
      "workflow_template": null,
      "workflow_variables": {},
      "priority": 7,
      "working_directory": "/home/web3relic/otto"
    }
  ]
}

If plan_needed is false, return: {"plan_needed": false, "plan_title": null, "tasks": null}
Also return plan_needed=false for: simple fixes, single tasks, quick lookups, one-off jobs."""


async def classify_for_plan(user_message: str, otto_reply: str) -> dict | None:
    """Classify whether an instruction needs a multi-task plan.

    Returns plan spec if multi-task, None if single-task (caller falls through
    to legacy single-dispatch).

    Uses dynamic tool composition to inject capability-aware hints into the
    LLM prompt, so the classifier knows which agents produce/consume what.
    """
    # Dynamic tool composition hints (STEM Agent pattern)
    composition_hints = ""
    try:
        from ..composition import find_compositions
        from .skills import SKILL_REGISTRY
        chains = find_compositions(user_message[:400], registry=SKILL_REGISTRY)
        if chains:
            hint_lines = []
            for chain in chains[:3]:
                steps = " → ".join(
                    f"{s.agent_type}(produces:{s.output_type})"
                    for s in chain.steps
                )
                hint_lines.append(f"  - {steps} [relevance={chain.total_relevance}]")
            composition_hints = (
                "\n\nCOMPOSITION HINTS (suggested agent chains based on input/output compatibility):\n"
                + "\n".join(hint_lines)
                + "\nUse these as guidance for agent selection and task ordering."
            )
    except Exception as e:
        log.debug(f"Composition hints skipped: {e}")

    system_prompt = _PLAN_CLASSIFIER_SYSTEM + composition_hints
    user_msg = f"Instruction from Mev: {user_message[:800]}\n\nOtto's conversational reply: {otto_reply[:400]}"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    try:
        response = await provider_chat(messages, max_tokens=1500, temperature=0.0)
        log.info(f"Plan classifier response: {response[:300] if response else 'EMPTY'}")
        parsed = extract_json(response)
        if not parsed:
            return None
        if not parsed.get("plan_needed"):
            return None
        if not parsed.get("tasks") or len(parsed["tasks"]) < 2:
            return None  # Not really a plan if it's just 1 task

        return parsed
    except Exception as e:
        log.warning(f"Plan classifier error: {e}")
        return None


# ── API Endpoints ────────────────────────────────────────────────────────

@router.get("")
async def list_plans(
    status: str | None = None,
    limit: int = Query(default=20, le=100),
):
    """List task plans with optional status filter."""
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            "SELECT * FROM task_plans WHERE status = $1 ORDER BY created_at DESC LIMIT $2",
            status, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM task_plans ORDER BY created_at DESC LIMIT $1",
            limit,
        )

    plans = []
    for r in rows:
        plans.append({
            "id": str(r["id"]),
            "title": r["title"],
            "instruction": r["instruction"][:200],
            "status": r["status"],
            "topology": r["topology"],
            "total_items": r["total_items"],
            "completed_items": r["completed_items"],
            "failed_items": r["failed_items"],
            "agents_employed": r["agents_employed"] or [],
            "created_by": r["created_by"],
            "created_at": r["created_at"].isoformat(),
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
        })
    return {"count": len(plans), "plans": plans}


@router.get("/{plan_id}")
async def get_plan(plan_id: UUID):
    """Get plan detail with all its tasks and DAG structure."""
    pool = await get_pool()
    plan = await pool.fetchrow("SELECT * FROM task_plans WHERE id = $1", plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    tasks = await pool.fetch(
        """SELECT id, title, status, agent_type, depends_on, priority,
                  exit_code, started_at, completed_at,
                  LEFT(output, 500) as output_preview,
                  metadata
           FROM tasks WHERE plan_id = $1
           ORDER BY created_at""",
        plan_id,
    )

    task_list = []
    for t in tasks:
        meta = t["metadata"] if isinstance(t["metadata"], dict) else json.loads(t["metadata"] or "{}")
        task_list.append({
            "id": str(t["id"]),
            "title": t["title"],
            "status": t["status"],
            "agent_type": t["agent_type"],
            "depends_on": [str(d) for d in (t["depends_on"] or [])],
            "priority": t["priority"],
            "exit_code": t["exit_code"],
            "started_at": t["started_at"].isoformat() if t["started_at"] else None,
            "completed_at": t["completed_at"].isoformat() if t["completed_at"] else None,
            "output_preview": t["output_preview"],
            "workflow_template": meta.get("workflow_template"),
            "is_plan_coordinator": meta.get("is_plan_coordinator", False),
        })

    return {
        "id": str(plan["id"]),
        "title": plan["title"],
        "instruction": plan["instruction"],
        "status": plan["status"],
        "topology": plan["topology"],
        "total_items": plan["total_items"],
        "completed_items": plan["completed_items"],
        "failed_items": plan["failed_items"],
        "agents_employed": plan["agents_employed"] or [],
        "created_by": plan["created_by"],
        "created_at": plan["created_at"].isoformat(),
        "completed_at": plan["completed_at"].isoformat() if plan["completed_at"] else None,
        "tasks": task_list,
    }


@router.post("/{plan_id}/cancel")
async def cancel_plan(plan_id: UUID):
    """Cancel a plan and all its pending tasks."""
    pool = await get_pool()
    plan = await pool.fetchrow("SELECT id, status FROM task_plans WHERE id = $1", plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if plan["status"] in ("completed", "cancelled"):
        raise HTTPException(409, f"Plan is already '{plan['status']}'")

    # Cancel all pending tasks
    result = await pool.execute(
        """UPDATE tasks SET status = 'cancelled', completed_at = now()
           WHERE plan_id = $1 AND status = 'pending'""",
        plan_id,
    )
    # Extract count from "UPDATE N"
    cancelled = int(result.split()[-1]) if result else 0

    await pool.execute(
        "UPDATE task_plans SET status = 'cancelled', completed_at = now() WHERE id = $1",
        plan_id,
    )

    return {"plan_id": str(plan_id), "status": "cancelled", "tasks_cancelled": cancelled or 0}


@router.post("")
async def create_plan_endpoint(req: CreatePlanRequest):
    """Manually create a task plan via API (for testing/OMS)."""
    pool = await get_pool()
    plan_id = await create_plan(
        pool,
        title=req.title,
        instruction=req.instruction,
        items=req.items,
        created_by=req.created_by,
        trigger_message=req.trigger_message,
    )
    return {"plan_id": str(plan_id), "status": "executing"}


@router.get("/dashboard/status")
async def plan_dashboard():
    """Dashboard summary of plan execution."""
    pool = await get_pool()
    stats = await pool.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'executing') as executing,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            COUNT(*) FILTER (WHERE status = 'pending') as pending,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled,
            COUNT(*) as total
        FROM task_plans
    """)
    return dict(stats) if stats else {}

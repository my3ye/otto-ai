import asyncio
import json
import os
import signal
import subprocess
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool
from ..models import TaskCreate, TaskOut, TaskComplete, TaskRunResponse, TaskPlanRequest, TaskPlanResponse, ApproachCandidate, TaskRouteRequest, TaskRouteResponse, PlanCacheMatch, PreflectResult, PreflectResultOut, JitRLOptimizeRequest, DecomposeRequest, HandoffRequest
from ..config import settings
from ..llm import llm_chat, extract_json, extract_json_array

log = logging.getLogger("otto.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_RUNNER = "/home/web3relic/otto/task_runner.sh"

TASK_COLUMNS = """id, title, prompt, context, priority, status, model, cli, agent_type,
    max_budget_usd, max_turns, timeout_seconds, working_directory,
    pid, started_at, completed_at, output, error, exit_code,
    reviewed, reviewed_at, created_by, session_id,
    created_at, updated_at, metadata,
    qa_status, qa_output, qa_reviewer, commit_hash, owner,
    parent_id, task_type, position, requires_decomposition, decomposed,
    children_total, children_completed,
    upvotes, dependency_score, chain_id, chain_hash, chain_anchored_at"""

# Per-CLI concurrency limits: 3 claude, 1 gemini, 1 kimi (total max 5)
CLI_CONCURRENCY = {"claude": 3, "gemini": 1, "kimi": 1}
MAX_CONCURRENT_TASKS = sum(CLI_CONCURRENCY.values())  # 5


# ── Helpers ────────────────────────────────────────────────────────

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


async def _count_running(pool) -> int:
    """Count running tasks whose process is still alive. Auto-fail dead ones."""
    rows = await pool.fetch(
        "SELECT id, pid, cli FROM tasks WHERE status = 'running'"
    )
    alive = 0
    for row in rows:
        pid = row["pid"]
        if pid and _pid_alive(pid):
            alive += 1
        elif pid:
            await pool.execute(
                """UPDATE tasks SET status = 'failed', completed_at = now(),
                   error = 'Process died unexpectedly (PID not found)'
                   WHERE id = $1 AND status = 'running'""",
                row["id"],
            )
    return alive


async def _count_running_by_cli(pool) -> dict[str, int]:
    """Return per-CLI count of running alive tasks. Auto-fail dead ones too."""
    rows = await pool.fetch(
        "SELECT id, pid, cli FROM tasks WHERE status = 'running'"
    )
    counts: dict[str, int] = {k: 0 for k in CLI_CONCURRENCY}
    for row in rows:
        pid = row["pid"]
        cli = row["cli"] or "claude"
        if pid and _pid_alive(pid):
            counts[cli] = counts.get(cli, 0) + 1
        elif pid:
            await pool.execute(
                """UPDATE tasks SET status = 'failed', completed_at = now(),
                   error = 'Process died unexpectedly (PID not found)'
                   WHERE id = $1 AND status = 'running'""",
                row["id"],
            )
    return counts


# ── Queue Status (must be before /{task_id} routes) ───────────────

@router.get("/queue/status")
async def queue_status():
    """Summary of the task queue state including per-CLI concurrency."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    )
    counts = {r["status"]: r["count"] for r in rows}
    running_alive = await _count_running(pool)
    cli_counts = await _count_running_by_cli(pool)
    cli_capacity = {
        cli: CLI_CONCURRENCY[cli] - cli_counts.get(cli, 0)
        for cli in CLI_CONCURRENCY
    }
    needs_review_row = await pool.fetchrow(
        "SELECT COUNT(*) as count FROM tasks WHERE status = 'completed' AND reviewed = FALSE"
    )
    needs_review = needs_review_row["count"] if needs_review_row else 0
    return {
        "pending": counts.get("pending", 0),
        "running": counts.get("running", 0),
        "running_alive": running_alive,
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "cancelled": counts.get("cancelled", 0),
        "needs_review": needs_review,
        "max_concurrent": MAX_CONCURRENT_TASKS,
        "can_run_more": running_alive < MAX_CONCURRENT_TASKS,
        "cli_running": cli_counts,
        "cli_capacity": cli_capacity,
        "cli_limits": CLI_CONCURRENCY,
    }


# ── Hindsight (Chain-of-Hindsight context injection) ───────────────

@router.get("/hindsight")
async def get_task_hindsight(
    query: str = Query(..., min_length=3, description="Task title to match against past tasks"),
    limit: int = Query(default=3, le=5),
):
    """Return hindsight from similar past tasks for pre-task context injection.

    Implements Chain-of-Hindsight (Liu et al., ICLR 2024): surfaces what worked
    and what failed in similar tasks so the new task can avoid known pitfalls.
    Called by task_runner.sh before every task execution.
    """
    pool = await get_pool()
    try:
        rows = await pool.fetch(
            """SELECT title, status, exit_code,
                      LEFT(output, 800)  AS output_excerpt,
                      LEFT(error,  400)  AS error_excerpt,
                      completed_at
               FROM tasks
               WHERE status IN ('completed', 'failed')
                 AND completed_at > NOW() - INTERVAL '30 days'
                 AND similarity(title, $1) > 0.08
               ORDER BY similarity(title, $1) DESC
               LIMIT $2""",
            query, limit,
        )
    except Exception as exc:
        log.debug(f"Hindsight query failed (pg_trgm unavailable?): {exc}")
        return {"hindsight": [], "count": 0}

    items = []
    for row in rows:
        succeeded = row["exit_code"] == 0
        if not succeeded and row["error_excerpt"]:
            lesson = (row["error_excerpt"] or "")[:300]
        elif row["output_excerpt"]:
            excerpt = row["output_excerpt"] or ""
            lesson = excerpt[-400:] if len(excerpt) > 400 else excerpt
        else:
            lesson = ""

        items.append({
            "title": row["title"],
            "outcome": "succeeded" if succeeded else "failed",
            "lesson": lesson.strip(),
            "when": row["completed_at"].isoformat() if row["completed_at"] else None,
        })

    return {"hindsight": items, "count": len(items)}


# ── LATS Planning ──────────────────────────────────────────────────

_LATS_SYSTEM = """You are Otto's strategic planning module. Otto is a persistent AGI agent.
Given a goal, generate {n} distinct candidate approaches to accomplish it.
Each approach must be meaningfully different (different tools, strategies, or decompositions).

For each approach, score it on three dimensions:
- success_probability (0.0-1.0): How likely is this to work given Otto's current capabilities?
- estimated_cost (0.0-1.0): Relative resource cost (0=cheap/fast, 1=expensive/slow)
- priority_alignment (0.0-1.0): How well does this serve Otto's mission priorities?
  (Otto priorities: self-improvement > crypto/alpha > evolution > viral chars > assistive tech > brand)

Composite score = 0.5 * success_probability + 0.3 * priority_alignment + 0.2 * (1 - estimated_cost)

Return ONLY a JSON array (no markdown, no code fences) of {n} objects:
[
  {{
    "title": "<short approach name>",
    "prompt": "<the full task prompt Otto would execute — actionable, ~200-400 chars>",
    "success_probability": <float 0-1>,
    "estimated_cost": <float 0-1>,
    "priority_alignment": <float 0-1>,
    "composite_score": <float, computed per formula above>,
    "reasoning": "<1-2 sentences explaining the score>",
    "failure_fallback": "<what to try if this approach fails, or null>"
  }},
  ...
]"""

_LATS_USER = """Goal: {goal}

Context: {context}

Priority level: P{priority}/10

Generate {n} candidate approaches."""


@router.post("/plan", response_model=TaskPlanResponse, status_code=200)
async def plan_task(req: TaskPlanRequest):
    """LATS-inspired multi-approach task planning.

    Generates N candidate approaches for a goal, scores each on success probability,
    cost, and priority alignment, and returns the highest-scoring recommendation.
    Implements a lightweight version of Language Agent Tree Search (Zhou et al., 2023)
    adapted for Otto's task execution context.

    The alternatives are preserved so that if the selected approach fails, the
    orchestrator can retry with the next-best approach (stored in task metadata).
    """
    if not settings.kimi_api_key:
        raise HTTPException(503, "Gemini API key not configured — LATS planning unavailable")

    n = req.n_approaches
    context_text = req.context or "No additional context provided."

    # ── APC: Check plan cache before calling Gemini ─────────────────
    cached_candidate: ApproachCandidate | None = None
    try:
        from .plans import match_plan
        cache_result = await match_plan(PlanCacheMatch(
            task_prompt=req.goal,
            threshold=0.85,
            limit=1,
        ))
        if cache_result.matched and cache_result.entries:
            best = cache_result.entries[0]
            cached_candidate = ApproachCandidate(
                title=f"[cached] {best.task_title}",
                prompt=best.selected_plan,
                success_probability=0.90,   # historical success boost
                estimated_cost=0.1,         # cheap — no generation needed
                priority_alignment=0.75,    # reasonable default
                composite_score=round(0.5 * 0.90 + 0.3 * 0.75 + 0.2 * (1 - 0.1), 4),
                reasoning=f"APC cache hit (similarity={best.similarity}, used {best.used_count}x). Reusing proven plan.",
                failure_fallback="Fall back to fresh LATS-generated approach",
            )
            log.info(
                f"APC cache hit: similarity={best.similarity} "
                f"title='{best.task_title[:50]}' — injecting as top candidate"
            )
    except Exception as e:
        log.warning(f"APC cache check failed (non-fatal): {e}")

    system_prompt = _LATS_SYSTEM.format(n=n)
    user_prompt = _LATS_USER.format(
        goal=req.goal,
        context=context_text[:1500],  # truncate to avoid token waste
        priority=req.priority,
        n=n,
    )

    try:
        text = await llm_chat(
            [{"role": "user", "content": user_prompt}],
            max_tokens=2000, temperature=0.3,
            system_instruction=system_prompt,
        )
        raw_approaches = extract_json_array(text)
        if raw_approaches is None:
            log.error(f"LATS planning: LLM returned non-JSON:\nRaw: {text[:400]}")
            raise HTTPException(502, "Planning model returned invalid JSON")

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"LATS planning failed: {e}")
        raise HTTPException(502, f"Planning model error: {e}")

    approaches = []
    for raw in raw_approaches[:n]:
        # Recompute composite score server-side to ensure formula consistency
        sp = float(raw.get("success_probability", 0.5))
        ec = float(raw.get("estimated_cost", 0.5))
        pa = float(raw.get("priority_alignment", 0.5))
        composite = round(0.5 * sp + 0.3 * pa + 0.2 * (1 - ec), 4)

        approaches.append(ApproachCandidate(
            title=str(raw.get("title", "Approach"))[:80],
            prompt=str(raw.get("prompt", ""))[:2000],
            success_probability=round(sp, 3),
            estimated_cost=round(ec, 3),
            priority_alignment=round(pa, 3),
            composite_score=composite,
            reasoning=str(raw.get("reasoning", ""))[:400],
            failure_fallback=raw.get("failure_fallback") or None,
        ))

    if not approaches:
        raise HTTPException(502, "Planning model returned no approaches")

    # ── APC: Prepend cached candidate if found ──────────────────────
    if cached_candidate is not None:
        approaches.insert(0, cached_candidate)

    # Select highest composite score
    selected_idx = max(range(len(approaches)), key=lambda i: approaches[i].composite_score)

    log.info(
        f"LATS plan: goal='{req.goal[:60]}' | "
        f"{len(approaches)} approaches | selected={selected_idx} "
        f"(score={approaches[selected_idx].composite_score})"
    )

    return TaskPlanResponse(
        goal=req.goal,
        approaches=approaches,
        selected_index=selected_idx,
        selected=approaches[selected_idx],
    )


# ── JitRL: Historical success rate lookup ─────────────────────────

# Map AdaptOrch task_type → JitRL action_type(s) for experience lookup
_TASK_TYPE_TO_JITRL = {
    "build":    ["implement", "fix", "deploy"],
    "research": ["research"],
    "lookup":   ["review", "generic"],
    "eval":     ["review", "generic"],
    "standard": ["generic", "implement"],
}


async def _get_jitrl_hint(title: str, prompt: str | None, task_type: str) -> dict | None:
    """Query JitRL experience buffer for historical success rates for this task type.

    Returns None if there are insufficient experiences (< 3) to draw signal from.
    The returned dict contains 'matched_type', 'success_rate', 'support_count',
    and 'avg_reward' for the best-matched action type.
    """
    try:
        from .jitrl import optimize as jitrl_optimize

        context = f"Task: {title}"
        if prompt:
            context += f"\nContext: {prompt[:400]}"

        result = await jitrl_optimize(JitRLOptimizeRequest(
            context=context,
            top_k=20,
            beta=1.0,
        ))

        if result.retrieved_count < 3:
            return None  # not enough data to act on

        # Find the recommendation that best matches the AdaptOrch task_type
        relevant_types = _TASK_TYPE_TO_JITRL.get(task_type, ["generic"])
        matching = [
            r for r in result.recommendations
            if r.action_type in relevant_types and r.support_count >= 3
        ]

        if not matching:
            return None

        # Pick the best-supported matching recommendation
        best = max(matching, key=lambda r: r.support_count)
        return {
            "matched_type": best.action_type,
            "success_rate": best.success_rate,
            "avg_reward": best.avg_reward,
            "support_count": best.support_count,
            "advantage": best.advantage,
            "retrieved_count": result.retrieved_count,
            "baseline_reward": result.baseline_reward,
        }
    except Exception as e:
        log.debug(f"JitRL hint failed (non-fatal): {e}")
        return None


# ── AdaptOrch Routing ──────────────────────────────────────────────

@router.post("/route", response_model=TaskRouteResponse)
async def route_task_endpoint(req: TaskRouteRequest):
    """AdaptOrch rule-based task routing.

    Given task characteristics (inline or by task_id), returns the optimal
    execution strategy: express | research_chunked | full_budget_build |
    eval_focused | lats_fallback | standard.

    If task_id is provided, real task data is fetched from the DB.
    If apply=True (requires task_id), the recommended params are written
    back to the task record (only if task is still pending).

    Routing rules (priority order):
    1. lats_fallback    — metadata.attempt_count > 0 AND metadata.failure_fallback set
    2. express          — lookup type OR budget≤0.5 OR timeout≤180s
    3. full_budget_build— P8+ priority AND build-type task
    4. research_chunked — research-type task
    5. eval_focused     — eval-type task
    6. standard         — everything else (use task params as-is)
    """
    from .routing import route_task as _route_task

    pool = await get_pool()
    route_req = req

    # If task_id provided, hydrate request from real task data
    if req.task_id:
        row = await pool.fetchrow(
            """SELECT title, prompt, priority, max_budget_usd, max_turns,
                      timeout_seconds, model, metadata
               FROM tasks WHERE id = $1""",
            req.task_id,
        )
        if not row:
            raise HTTPException(404, f"Task {req.task_id} not found")

        _meta = row["metadata"]
        if isinstance(_meta, str):
            import json as _json_meta
            try:
                _meta = _json_meta.loads(_meta)
            except Exception:
                _meta = {}
        route_req = TaskRouteRequest(
            task_id=req.task_id,
            title=row["title"],
            prompt=row["prompt"],
            priority=row["priority"],
            max_budget_usd=float(row["max_budget_usd"]),
            max_turns=row["max_turns"],
            timeout_seconds=row["timeout_seconds"],
            metadata=dict(_meta) if _meta else {},
            apply=req.apply,
        )

    strategy = _route_task(route_req)
    applied = False

    # Optionally apply recommended params back to DB (pending tasks only)
    if req.apply and req.task_id:
        result = await pool.execute(
            """UPDATE tasks
               SET model = $2,
                   max_turns = $3,
                   timeout_seconds = $4,
                   max_budget_usd = $5,
                   updated_at = now()
               WHERE id = $1 AND status = 'pending'""",
            req.task_id,
            strategy.recommended_model,
            strategy.recommended_max_turns,
            strategy.recommended_timeout_seconds,
            strategy.recommended_max_budget_usd,
        )
        # UPDATE returns "UPDATE <count>" — check if a row was actually modified
        applied = result.endswith("1")
        if applied:
            log.info(
                f"AdaptOrch applied to task {req.task_id}: "
                f"strategy={strategy.strategy}, type={strategy.task_type}, "
                f"turns={strategy.recommended_max_turns}, "
                f"timeout={strategy.recommended_timeout_seconds}s, "
                f"budget=${strategy.recommended_max_budget_usd}"
            )
        else:
            log.warning(
                f"AdaptOrch apply skipped for task {req.task_id} "
                f"(not found or not pending)"
            )

    # ── JitRL integration: adjust strategy based on historical success rates ───
    # Only applies when task_id is provided (real task) — enough to have a context.
    # Modulates timeout/turns upward when JitRL shows poor past success for this type.
    jitrl_hint = await _get_jitrl_hint(
        route_req.title or "", route_req.prompt, strategy.task_type
    )
    if jitrl_hint:
        success_rate = jitrl_hint["success_rate"]
        support_count = jitrl_hint["support_count"]
        matched_type = jitrl_hint["matched_type"]

        orig_timeout = strategy.recommended_timeout_seconds
        orig_turns = strategy.recommended_max_turns
        orig_budget = strategy.recommended_max_budget_usd
        jitrl_note = (
            f" JitRL({matched_type}): {success_rate:.0%} success "
            f"({support_count} samples, avg_reward={jitrl_hint['avg_reward']:.2f})"
        )

        if success_rate < 0.4:
            # Low historical success → boost resources to give task a better chance
            new_timeout = int(orig_timeout * 1.5)
            new_turns = int(orig_turns * 1.25)
            new_budget = orig_budget
            if success_rate < 0.3:
                new_budget = round(orig_budget * 1.5, 2)
            strategy = strategy.model_copy(update={
                "recommended_timeout_seconds": new_timeout,
                "recommended_max_turns": new_turns,
                "recommended_max_budget_usd": new_budget,
                "reasoning": strategy.reasoning + jitrl_note
                    + f" → boosted (timeout {orig_timeout}→{new_timeout}s,"
                    f" turns {orig_turns}→{new_turns}).",
            })
            log.info(
                f"JitRL boosted '{(route_req.title or '')[:40]}': "
                f"success_rate={success_rate:.0%}, "
                f"timeout {orig_timeout}→{new_timeout}s, turns {orig_turns}→{new_turns}"
            )
            # If apply=True, write JitRL-adjusted params back to DB
            if req.apply and req.task_id:
                await pool.execute(
                    """UPDATE tasks
                       SET max_turns = $2,
                           timeout_seconds = $3,
                           max_budget_usd = $4,
                           updated_at = now()
                       WHERE id = $1 AND status = 'pending'""",
                    req.task_id,
                    strategy.recommended_max_turns,
                    strategy.recommended_timeout_seconds,
                    strategy.recommended_max_budget_usd,
                )
                log.info(
                    f"JitRL params applied to task {req.task_id} "
                    f"(timeout={new_timeout}s, turns={new_turns})"
                )
        else:
            # Good or sufficient success rate — just annotate, no changes
            strategy = strategy.model_copy(update={
                "reasoning": strategy.reasoning + jitrl_note + " — params confirmed.",
            })

    return TaskRouteResponse(strategy=strategy, applied=applied, task_id=req.task_id)


# ── CRUD ───────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=201)
async def create_task(req: TaskCreate):
    """Create a new task in the queue."""
    pool = await get_pool()
    # Ensure metadata is always a dict (guard against list/string corruption)
    import json as _json
    metadata = req.metadata
    if not isinstance(metadata, dict):
        if isinstance(metadata, list) and metadata and isinstance(metadata[0], dict):
            metadata = metadata[0]
        else:
            metadata = {}
    cli = req.cli if req.cli in CLI_CONCURRENCY else "claude"
    # Enforce minimum resource limits per CLI backend to prevent premature failures
    max_budget_usd = req.max_budget_usd
    max_turns = req.max_turns
    if cli == "gemini":
        max_budget_usd = max(max_budget_usd, 1.0)   # gemini fails at $0.30
    elif cli == "kimi":
        max_turns = max(max_turns, 25)               # kimi hits step limit at 15
    owner = req.owner if req.owner in ("otto", "mev") else "otto"
    # Validate hierarchy fields
    task_type = req.task_type if req.task_type in ("epic", "task", "subtask") else "task"
    row = await pool.fetchrow(
        f"""INSERT INTO tasks (title, prompt, context, priority, model, cli, agent_type,
               max_budget_usd, max_turns, timeout_seconds, working_directory,
               created_by, session_id, metadata, owner,
               parent_id, task_type, position, requires_decomposition, decomposed)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                   $16,$17,$18,$19,$20)
           RETURNING {TASK_COLUMNS}""",
        req.title, req.prompt, req.context, req.priority, req.model, cli,
        req.agent_type,
        max_budget_usd, max_turns, req.timeout_seconds,
        req.working_directory, req.created_by, req.session_id,
        metadata, owner,
        req.parent_id, task_type, req.position, req.requires_decomposition, req.decomposed,
    )
    return TaskOut(**dict(row))


@router.get("")
async def list_tasks(
    status: str | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    owner: str | None = Query(default=None, description="Filter by owner: 'otto' or 'mev'"),
    limit: int = Query(default=20, le=100),
    offset: int | None = Query(default=None, ge=0),
):
    """List tasks with optional filters. Returns paginated response when offset is provided."""
    pool = await get_pool()
    conditions = []
    params: list = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    if reviewed is not None:
        conditions.append(f"reviewed = ${idx}")
        params.append(reviewed)
        idx += 1

    if owner and owner in ("otto", "mev"):
        conditions.append(f"owner = ${idx}")
        params.append(owner)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    paginated = offset is not None
    actual_offset = offset if offset is not None else 0

    total = 0
    if paginated:
        count_row = await pool.fetchrow(
            f"SELECT COUNT(*) as total FROM tasks {where}", *params,
        )
        total = count_row["total"] if count_row else 0

    params.append(limit)
    limit_idx = idx
    idx += 1
    params.append(actual_offset)
    offset_idx = idx

    rows = await pool.fetch(
        f"""SELECT {TASK_COLUMNS} FROM tasks {where}
            ORDER BY
                CASE status
                    WHEN 'running' THEN 0
                    WHEN 'pending' THEN 1
                    WHEN 'completed' THEN 2
                    WHEN 'failed' THEN 3
                    ELSE 4
                END,
                created_at DESC
            LIMIT ${limit_idx} OFFSET ${offset_idx}""",
        *params,
    )
    results = []
    for r in rows:
        d = dict(r)
        if not isinstance(d.get("metadata"), dict):
            d["metadata"] = {}
        results.append(TaskOut(**d))

    if paginated:
        return {"tasks": results, "total": total, "limit": limit, "offset": actual_offset}
    return results


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: UUID):
    """Get a single task by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = $1", task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")
    d = dict(row)
    if not isinstance(d.get("metadata"), dict):
        d["metadata"] = {}
    return TaskOut(**d)


# ── Execution ──────────────────────────────────────────────────────

@router.post("/{task_id}/run", response_model=TaskRunResponse)
async def run_task(task_id: UUID):
    """Spawn a detached task runner for the given task."""
    pool = await get_pool()

    row = await pool.fetchrow(
        """SELECT id, status, title, cli, requires_decomposition, decomposed
           FROM tasks WHERE id = $1""",
        task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")
    if row["status"] != "pending":
        raise HTTPException(409, f"Task is '{row['status']}', must be 'pending' to run")
    # Decomposition gate: block tasks that require decomposition before execution
    if row["requires_decomposition"] and not row["decomposed"]:
        raise HTTPException(
            409,
            "Task requires decomposition before execution. "
            "Call POST /tasks/{id}/decompose first.",
        )

    task_cli = row["cli"] or "claude"
    if task_cli not in CLI_CONCURRENCY:
        task_cli = "claude"

    running = await _count_running(pool)
    if running >= MAX_CONCURRENT_TASKS:
        raise HTTPException(
            429,
            f"Max concurrent tasks ({MAX_CONCURRENT_TASKS}) reached. {running} running.",
        )

    cli_counts = await _count_running_by_cli(pool)
    cli_running = cli_counts.get(task_cli, 0)
    cli_limit = CLI_CONCURRENCY[task_cli]
    if cli_running >= cli_limit:
        raise HTTPException(
            429,
            f"CLI '{task_cli}' at capacity ({cli_running}/{cli_limit}). "
            f"Wait for a {task_cli} slot to free up.",
        )

    # Build explicit env so Claude CLI can find ~/.claude/ auth when spawned from systemd
    task_env = os.environ.copy()
    task_env.setdefault("HOME", "/home/web3relic")
    task_env.setdefault("USER", "web3relic")
    task_env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"

    try:
        proc = subprocess.Popen(
            [TASK_RUNNER, str(task_id)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=task_env,
        )
        pid = proc.pid
    except Exception as e:
        raise HTTPException(500, f"Failed to spawn task runner: {e}")

    await pool.execute(
        """UPDATE tasks SET status = 'running', pid = $2, started_at = now()
           WHERE id = $1""",
        task_id, pid,
    )

    log.info(f"Task {task_id} ({row['title']}) spawned as PID {pid}")
    return TaskRunResponse(
        id=task_id, status="running", pid=pid,
        message=f"Task runner spawned (PID {pid})",
    )


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(task_id: UUID, req: TaskComplete):
    """Called by task_runner.sh when a task finishes."""
    import json as _json
    pool = await get_pool()
    status = "completed" if req.exit_code == 0 else "failed"

    if req.metadata:
        # Fetch existing metadata, merge, and write back
        existing = await pool.fetchval("SELECT metadata FROM tasks WHERE id = $1", task_id)
        merged = {}
        if existing:
            try:
                merged = dict(existing) if isinstance(existing, dict) else _json.loads(existing)
            except Exception:
                merged = {}
        merged.update(req.metadata)
        row = await pool.fetchrow(
            f"""UPDATE tasks
                SET status = $2, output = $3, error = $4, exit_code = $5,
                    completed_at = now(), pid = NULL, metadata = $6
                WHERE id = $1
                RETURNING {TASK_COLUMNS}""",
            task_id, status, req.output, req.error, req.exit_code,
            merged,
        )
    else:
        row = await pool.fetchrow(
            f"""UPDATE tasks
                SET status = $2, output = $3, error = $4, exit_code = $5,
                    completed_at = now(), pid = NULL
                WHERE id = $1
                RETURNING {TASK_COLUMNS}""",
            task_id, status, req.output, req.error, req.exit_code,
        )
    if not row:
        raise HTTPException(404, "Task not found")

    # ── JitRL: Feed outcome back into experience buffer ─────────────
    asyncio.create_task(_jitrl_ingest_task(task_id))

    # ── AgentOS: Fire interrupt for task completion/failure ────────
    asyncio.create_task(_fire_task_interrupt(task_id, status))

    # ── Hierarchy: Propagate completion up the tree ─────────────────
    asyncio.create_task(_propagate_completion(pool, task_id, status))

    # ── Workflows: Advance workflow if this task belongs to one ────
    from .workflows import check_workflow_advance
    asyncio.create_task(check_workflow_advance(pool, task_id, status))

    return TaskOut(**dict(row))


async def _propagate_completion(pool, task_id: UUID, status: str):
    """After a task completes/fails, check if parent should auto-close.

    Implements auto-close propagation: when all children of a parent are done
    (completed/failed/cancelled), the parent auto-closes with the aggregate status.
    Recurses up the tree (max 3 levels so no infinite loop risk).
    """
    try:
        row = await pool.fetchrow(
            "SELECT parent_id FROM tasks WHERE id = $1", task_id
        )
        if not row or not row["parent_id"]:
            return  # Root task — no propagation needed

        parent_id = row["parent_id"]

        # Update denormalized counter on parent
        if status in ("completed", "failed", "cancelled"):
            await pool.execute(
                "UPDATE tasks SET children_completed = children_completed + 1 WHERE id = $1",
                parent_id,
            )

        # Check if all children are done
        sibling_stats = await pool.fetchrow(
            """SELECT COUNT(*) as total,
                      COUNT(*) FILTER (WHERE status IN ('completed','failed','cancelled')) as done
               FROM tasks WHERE parent_id = $1""",
            parent_id,
        )
        if not sibling_stats:
            return

        total = sibling_stats["total"]
        done = sibling_stats["done"]
        if total > 0 and total == done:
            # All children are done — auto-close parent
            all_succeeded = await pool.fetchval(
                "SELECT COUNT(*) = 0 FROM tasks WHERE parent_id = $1 AND status = 'failed'",
                parent_id,
            )
            parent_status = "completed" if all_succeeded else "failed"
            updated = await pool.fetchval(
                """UPDATE tasks
                   SET status = $1, completed_at = now(),
                       output = 'Auto-closed: all subtasks completed.'
                   WHERE id = $2 AND status NOT IN ('completed','failed','cancelled')
                   RETURNING id""",
                parent_status, parent_id,
            )
            if updated:
                log.info(
                    f"Auto-closed parent {str(parent_id)[:8]} as '{parent_status}' "
                    f"({done}/{total} children done)"
                )
                # Recurse up the tree (max 3 levels deep so safe)
                await _propagate_completion(pool, parent_id, parent_status)
    except Exception as e:
        log.debug(f"Propagation failed for {str(task_id)[:8]}: {e}")


async def _jitrl_ingest_task(task_id: UUID):
    """Fire-and-forget: ingest completed/failed task as JitRL experience.

    Silently skips if task is not in a terminal state or if JitRL ingestion fails.
    """
    try:
        from .jitrl import ingest_task_as_experience
        await ingest_task_as_experience(task_id)
        log.debug(f"JitRL ingested task {str(task_id)[:8]} as experience")
    except Exception as e:
        log.debug(f"JitRL ingest skipped for {str(task_id)[:8]}: {e}")


async def _fire_task_interrupt(task_id: UUID, status: str):
    """Fire-and-forget: submit kernel interrupt for task completion/failure."""
    try:
        from ..kernel.types import InterruptType
        from ..kernel import ivt

        itype = (
            InterruptType.SIG_TASK_COMPLETE if status == "completed"
            else InterruptType.SIG_TASK_FAILED
        )
        await ivt.enqueue(
            interrupt_type=itype,
            source="task_engine",
            payload={"task_id": str(task_id), "status": status},
        )
    except Exception as e:
        log.debug(f"Task interrupt skipped for {str(task_id)[:8]}: {e}")


# ── Hierarchy Endpoints ─────────────────────────────────────────────

@router.post("/{task_id}/decompose", response_model=list[TaskOut])
async def decompose_task(task_id: UUID, req: DecomposeRequest):
    """Atomically create child tasks under a parent. Sets decomposed=TRUE on parent.

    The parent task must be in 'pending' or 'running' status and must have
    requires_decomposition=TRUE. Children are created with parent_id pointing
    to this task and task_type set to the next level down (epic→task, task→subtask).
    Children are assigned sequential position values (0, 1, 2, ...).
    """
    import json as _json
    pool = await get_pool()

    parent = await pool.fetchrow(
        "SELECT id, status, task_type, decomposed, requires_decomposition FROM tasks WHERE id = $1",
        task_id,
    )
    if not parent:
        raise HTTPException(404, "Task not found")
    if parent["decomposed"]:
        raise HTTPException(409, "Task is already decomposed")
    if parent["task_type"] == "subtask":
        raise HTTPException(400, "Subtasks cannot be decomposed further (max depth is 3)")

    # Determine child task_type
    child_type = "task" if parent["task_type"] == "epic" else "subtask"

    if not req.subtasks:
        raise HTTPException(400, "Must provide at least one subtask")

    # Create all children in a single transaction
    children = []
    async with pool.acquire() as conn:
        async with conn.transaction():
            for i, child_req in enumerate(req.subtasks):
                # Validate child metadata
                metadata = child_req.metadata
                if not isinstance(metadata, dict):
                    metadata = {}
                cli = child_req.cli if child_req.cli in CLI_CONCURRENCY else "claude"
                max_budget_usd = child_req.max_budget_usd
                max_turns = child_req.max_turns
                if cli == "gemini":
                    max_budget_usd = max(max_budget_usd, 1.0)
                elif cli == "kimi":
                    max_turns = max(max_turns, 25)
                owner = child_req.owner if child_req.owner in ("otto", "mev") else "otto"

                child_row = await conn.fetchrow(
                    f"""INSERT INTO tasks (title, prompt, context, priority, model, cli,
                           agent_type, max_budget_usd, max_turns, timeout_seconds,
                           working_directory, created_by, session_id, metadata, owner,
                           parent_id, task_type, position,
                           requires_decomposition, decomposed)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                               $16,$17,$18,$19,$20)
                       RETURNING {TASK_COLUMNS}""",
                    child_req.title, child_req.prompt, child_req.context,
                    child_req.priority, child_req.model, cli, child_req.agent_type,
                    max_budget_usd, max_turns, child_req.timeout_seconds,
                    child_req.working_directory, child_req.created_by,
                    child_req.session_id, metadata, owner,
                    task_id, child_type, i,
                    child_req.requires_decomposition, False,
                )
                children.append(TaskOut(**dict(child_row)))

            # Update parent: set decomposed=TRUE, children_total
            await conn.execute(
                """UPDATE tasks
                   SET decomposed = TRUE,
                       children_total = $2,
                       children_completed = 0
                   WHERE id = $1""",
                task_id, len(children),
            )

    log.info(
        f"Decomposed task {str(task_id)[:8]} into {len(children)} "
        f"'{child_type}' subtasks"
    )
    return children


@router.get("/{task_id}/tree")
async def get_task_tree(task_id: UUID):
    """Return the full task tree rooted at this task.

    Uses a recursive CTE to traverse the adjacency list. Returns nested JSON:
    { task: TaskOut, children: [{ task: TaskOut, children: [...] }] }
    Max depth 3 (epic → task → subtask).
    """
    pool = await get_pool()

    # Verify root exists
    root_exists = await pool.fetchval("SELECT id FROM tasks WHERE id = $1", task_id)
    if not root_exists:
        raise HTTPException(404, "Task not found")

    # Recursive CTE: fetch all nodes in tree order
    rows = await pool.fetch(
        f"""WITH RECURSIVE tree AS (
                SELECT {TASK_COLUMNS}, 0 as depth FROM tasks WHERE id = $1
                UNION ALL
                SELECT {', '.join(f't.{c.strip()}' for c in TASK_COLUMNS.split(','))},
                       tree.depth + 1
                FROM tasks t
                JOIN tree ON t.parent_id = tree.id
                WHERE tree.depth < 3
            )
            SELECT * FROM tree ORDER BY depth, position, created_at""",
        task_id,
    )

    if not rows:
        raise HTTPException(404, "Task not found")

    # Build nested structure
    nodes: dict = {}
    for row in rows:
        d = dict(row)
        depth = d.pop("depth")
        if not isinstance(d.get("metadata"), dict):
            d["metadata"] = {}
        node = {"task": TaskOut(**d), "children": [], "depth": depth}
        nodes[str(d["id"])] = node

    root_node = nodes.get(str(task_id))
    if not root_node:
        raise HTTPException(404, "Task not found")

    # Wire parent→child relationships
    for row in rows:
        parent_id = row["parent_id"]
        node_id = str(row["id"])
        if parent_id and str(parent_id) in nodes and node_id != str(task_id):
            nodes[str(parent_id)]["children"].append(nodes[node_id])

    def _serialize(node: dict) -> dict:
        return {
            "task": node["task"].model_dump(),
            "depth": node["depth"],
            "children": [_serialize(c) for c in node["children"]],
        }

    return _serialize(root_node)


@router.post("/{task_id}/handoff", response_model=TaskOut)
async def handoff_task(task_id: UUID, req: HandoffRequest):
    """Transfer task ownership between Otto and Mev with a reason note.

    Updates the owner field and appends to metadata['handoff_log'] for audit trail.
    Any node in the task tree can be handed off independently.
    """
    import json as _json
    pool = await get_pool()

    if req.to not in ("otto", "mev"):
        raise HTTPException(400, "to must be 'otto' or 'mev'")

    task = await pool.fetchrow(
        "SELECT id, owner, metadata FROM tasks WHERE id = $1", task_id
    )
    if not task:
        raise HTTPException(404, "Task not found")

    # Build handoff log entry
    log_entry = {
        "from": task["owner"],
        "to": req.to,
        "note": req.note,
        "at": datetime.now(timezone.utc).isoformat(),
    }

    # Deep-merge handoff_log into existing metadata
    existing_meta = task["metadata"] or {}
    if not isinstance(existing_meta, dict):
        existing_meta = {}
    handoff_log = existing_meta.get("handoff_log", [])
    if not isinstance(handoff_log, list):
        handoff_log = []
    handoff_log.append(log_entry)
    existing_meta["handoff_log"] = handoff_log

    row = await pool.fetchrow(
        f"""UPDATE tasks
            SET owner = $2, metadata = $3, updated_at = now()
            WHERE id = $1
            RETURNING {TASK_COLUMNS}""",
        task_id, req.to, existing_meta,
    )
    if not row:
        raise HTTPException(404, "Task not found")

    log.info(
        f"Task {str(task_id)[:8]} handed off from '{task['owner']}' to '{req.to}': "
        f"{req.note[:60]}"
    )
    return TaskOut(**dict(row))


@router.post("/{task_id}/review", response_model=TaskOut)
async def mark_reviewed(task_id: UUID):
    """Mark a completed/failed task as reviewed by the heartbeat.

    If the task completed successfully (exit_code=0), triggers background
    skill extraction via Gemini Flash to auto-populate procedural memory.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""UPDATE tasks SET reviewed = TRUE, reviewed_at = now()
            WHERE id = $1 AND status IN ('completed', 'failed')
            RETURNING {TASK_COLUMNS}""",
        task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found or not in completed/failed status")

    task_data = dict(row)
    # Guard against corrupted metadata (JSON string instead of dict)
    if not isinstance(task_data.get("metadata"), dict):
        try:
            import json as _json
            task_data["metadata"] = _json.loads(task_data["metadata"]) if task_data.get("metadata") else {}
        except Exception:
            task_data["metadata"] = {}
    # Fire-and-forget skill extraction for successful completions
    if task_data.get("status") == "completed" and task_data.get("exit_code") == 0:
        asyncio.create_task(_extract_skill_from_task(task_data))

    # Fire-and-forget JitRL experience ingestion (all terminal states)
    asyncio.create_task(_jitrl_ingest_task(task_id))

    return TaskOut(**task_data)


async def _extract_skill_from_task(task: dict):
    """Use Gemini Flash to extract a reusable skill from a completed task.

    Checks for novelty (name not already in procedures) before creating.
    """
    if not settings.kimi_api_key:
        return

    title = task.get("title", "")
    prompt_text = (task.get("prompt") or "")[:600]
    output = (task.get("output") or "")[:2000]

    if not output.strip():
        log.debug(f"Skill extraction skipped — no output for task {str(task['id'])[:8]}")
        return

    gemini_prompt = (
        "You are analyzing a completed AI agent task to extract a reusable skill pattern.\n\n"
        f"Task title: {title}\n"
        f"Task prompt: {prompt_text}\n"
        f"Task output (truncated): {output}\n\n"
        "Extract a reusable skill/procedure if this task represents a repeatable pattern.\n"
        "Return ONLY a JSON object (no markdown, no code fences) with these fields:\n"
        '{"name": "<snake_case_name max 40 chars>", '
        '"description": "<1-2 sentence description>", '
        '"steps": ["<step 1>", "<step 2>", ...], '
        '"is_novel": <true|false>, '
        '"skip_reason": "<why skip, or null if extracting>"}\n\n'
        "Rules:\n"
        "- steps: 3-7 concise action steps that could guide future task execution\n"
        "- name: snake_case, descriptive (e.g. 'wallet_discovery_pipeline', 'reflact_agent_implementation')\n"
        "- is_novel=false if: one-off task, too specific, debugging only, or no reusable pattern\n"
        "- skip_reason: set if is_novel=false, else null"
    )

    try:
        text = await llm_chat([{"role": "user", "content": gemini_prompt}], max_tokens=500, temperature=0.1)
        skill = extract_json(text)
        if not skill:
            log.warning(f"Skill extraction returned unparseable response for '{title[:40]}'")
            return

        if not skill.get("is_novel"):
            log.info(
                f"Skill extraction skipped for '{title[:40]}': "
                f"{skill.get('skip_reason', 'not novel')}"
            )
            return

        name = (skill.get("name") or "").strip().lower().replace(" ", "_")[:40]
        description = (skill.get("description") or "").strip()
        steps = skill.get("steps") or []

        if not name or not steps:
            log.warning(f"Skill extraction returned incomplete data for task {str(task['id'])[:8]}")
            return

        pool = await get_pool()

        # Check novelty: skip if a procedure with this name already exists
        existing = await pool.fetchrow(
            "SELECT id FROM procedures WHERE name = $1", name
        )
        if existing:
            log.info(f"Skill '{name}' already exists — skipping auto-extract")
            return

        # Create the new procedure
        await pool.execute(
            """INSERT INTO procedures (name, description, steps)
               VALUES ($1, $2, $3)
               ON CONFLICT (name) DO NOTHING""",
            name, description, steps,
        )
        log.info(
            f"Auto-extracted skill: '{name}' from task '{title[:40]}' "
            f"({str(task['id'])[:8]})"
        )

    except Exception as e:
        log.warning(f"Skill extraction failed for task {str(task.get('id', '?'))[:8]}: {e}")


@router.post("/{task_id}/preflect", response_model=PreflectResultOut)
async def store_preflect(task_id: UUID, req: PreflectResult):
    """Store PreFlect prospective critique in task metadata.

    Called by the reflection agent before a task is launched. Stores risk assessment
    so the orchestrator can gate high-risk tasks before execution.

    Implements PreFlect (Ye et al., arXiv:2602.07187): prospective reflection that
    critiques upcoming tasks against known failure patterns before execution, shifting
    from reactive correction to proactive foresight.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, metadata FROM tasks WHERE id = $1", task_id
    )
    if not row:
        raise HTTPException(404, "Task not found")

    existing_meta = dict(row["metadata"]) if isinstance(row["metadata"], dict) else {}
    existing_meta["preflect"] = {
        "risk_score": req.risk_score,
        "risk_factors": req.risk_factors,
        "suggested_modifications": req.suggested_modifications,
        "failure_patterns_matched": req.failure_patterns_matched,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
    }

    await pool.execute(
        "UPDATE tasks SET metadata = $2, updated_at = now() WHERE id = $1",
        task_id, existing_meta,
    )

    log.info(
        f"PreFlect stored for task {task_id}: "
        f"risk_score={req.risk_score:.2f}, factors={req.risk_factors}"
    )
    return PreflectResultOut(
        task_id=task_id,
        risk_score=req.risk_score,
        risk_factors=req.risk_factors,
        suggested_modifications=req.suggested_modifications,
        failure_patterns_matched=req.failure_patterns_matched,
    )


@router.get("/preflect/patterns", tags=["tasks"])
async def get_failure_patterns():
    """Return the PreFlect failure pattern database distilled from historical task failures.

    These patterns are used by the reflection agent to score risk on pending tasks
    before launch. Based on analysis of all 11 failed tasks in Otto's history.
    """
    return {
        "patterns": [
            {
                "name": "timeout_broad_research",
                "description": "Research tasks with scope covering 3+ topics in a single prompt",
                "indicators": ["research", "latest", "papers", "cutting-edge", "find", "survey"],
                "risk_factors": ["broad_scope", "multi_topic_research"],
                "recommended_timeout_min": 900,
                "recommended_turns_min": 50,
                "historical_failures": 3,
                "notes": "Research: AI architectures (300s), Research sweep #7 (600s), "
                         "Viral characters guide (600s) all timed out. Scope too broad.",
            },
            {
                "name": "timeout_multi_deliverable",
                "description": "Tasks requiring 4+ distinct deliverables (signals, features, dims)",
                "indicators": ["SM_11", "SM_12", "SM_13", "SM_14", "SM_15",
                               "5 new signals", "multiple signals", "and paper trading",
                               "debugging + hallucination"],
                "risk_factors": ["multiple_deliverables", "scope_too_broad"],
                "recommended_timeout_min": 1200,
                "recommended_turns_min": 60,
                "historical_failures": 2,
                "notes": "Alpha Phase 4 (5 signals + paper trading, 600s) and "
                         "Eval push (2 dims, 900s) both timed out despite decent budgets.",
            },
            {
                "name": "low_timeout_implementation",
                "description": "Implementation/build tasks with timeout <= 300s",
                "indicators": [],
                "risk_factors": ["timeout_too_low"],
                "timeout_threshold": 300,
                "task_types": ["build", "implement", "fix", "create", "add"],
                "historical_failures": 2,
                "notes": "Research + Alpha backtest (both 300s) hit timeout immediately. "
                         "Any implementation needs >= 600s.",
            },
            {
                "name": "low_turns_implementation",
                "description": "Implementation tasks with max_turns < 30",
                "indicators": [],
                "risk_factors": ["turns_too_low"],
                "turns_threshold": 30,
                "task_types": ["build", "implement", "fix", "create", "add"],
                "historical_failures": 2,
                "notes": "WhatsApp semantic search (turns=10) failed with exit_code=1. "
                         "Implementation tasks need >= 40 turns minimum.",
            },
            {
                "name": "process_death_external_tools",
                "description": "Tasks spawning external processes or sub-agents (eval harness, nested Claude)",
                "indicators": ["eval_harness", "eval harness", "run eval", "baseline benchmark",
                               "nested", "subprocess", "spawn"],
                "risk_factors": ["external_process", "nested_session_risk"],
                "historical_failures": 3,
                "notes": "3 tasks failed with PID not found (process death). "
                         "Eval harness must run as detached task. Nested Claude sessions fail.",
            },
            {
                "name": "ambiguous_success_criteria",
                "description": "Tasks with vague or unmeasurable success criteria",
                "indicators": ["try to", "best effort", "if possible", "whatever you can"],
                "risk_factors": ["unclear_success_criteria"],
                "historical_failures": 1,
                "notes": "Vague tasks tend to report partial completion as done.",
            },
        ],
        "summary": {
            "total_failures_analyzed": 11,
            "timeout_failures": 7,
            "process_death_failures": 3,
            "error_failures": 1,
            "top_root_cause": "Scope too broad for allocated timeout (7/11 exit_code=124)",
            "generated_from": "POST /tasks?status=failed historical analysis",
        },
    }


@router.post("/{task_id}/cancel", response_model=TaskOut)
async def cancel_task(task_id: UUID):
    """Cancel a pending task."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""UPDATE tasks SET status = 'cancelled'
            WHERE id = $1 AND status = 'pending'
            RETURNING {TASK_COLUMNS}""",
        task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found or not in pending status")
    return TaskOut(**dict(row))


@router.post("/{task_id}/stop", response_model=TaskOut)
async def stop_task(task_id: UUID):
    """Stop a running task by killing its process."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, pid, title FROM tasks WHERE id = $1", task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")

    status = row["status"]
    pid = row["pid"]

    # If pending, just cancel it
    if status == "pending":
        r = await pool.fetchrow(
            f"""UPDATE tasks SET status = 'cancelled'
                WHERE id = $1 RETURNING {TASK_COLUMNS}""",
            task_id,
        )
        log.info(f"Task {task_id} ({row['title']}) cancelled (was pending)")
        return TaskOut(**dict(r))

    if status != "running":
        raise HTTPException(409, f"Task is '{status}', not running or pending")

    # Kill the process group (task_runner uses start_new_session=True)
    killed = False
    if pid:
        try:
            os.killpg(pid, signal.SIGTERM)
            killed = True
            log.info(f"Sent SIGTERM to process group {pid} for task {task_id}")
        except ProcessLookupError:
            log.info(f"Process {pid} already dead for task {task_id}")
            killed = True
        except PermissionError:
            log.warning(f"Permission denied killing PID {pid} for task {task_id}")
        except Exception as e:
            log.warning(f"Failed to kill PID {pid} for task {task_id}: {e}")

    r = await pool.fetchrow(
        f"""UPDATE tasks SET status = 'failed', pid = NULL,
                completed_at = now(),
                error = 'Stopped by admin',
                exit_code = -15
            WHERE id = $1 RETURNING {TASK_COLUMNS}""",
        task_id,
    )
    log.info(f"Task {task_id} ({row['title']}) stopped (killed={killed})")
    return TaskOut(**dict(r))


# ── QA Layer ───────────────────────────────────────────────────────

class TaskQAUpdate(BaseModel):
    """QA status update from qa_runner.sh after review."""
    qa_status: str                         # pending_qa | approved | rejected
    qa_reviewer: str | None = None         # which CLI did the QA
    qa_output: str | None = None           # QA agent's review text
    commit_hash: str | None = None         # git SHA if committed


@router.post("/{task_id}/qa-update", response_model=TaskOut)
async def update_qa_status(task_id: UUID, req: TaskQAUpdate):
    """Called by qa_runner.sh to update QA fields on a completed task.

    Tracks whether the task's output was approved or rejected by the independent
    QA reviewer (always a different CLI than the one that ran the task).
    """
    valid_statuses = {"pending_qa", "approved", "rejected", "needs_manual_review", "failed"}
    if req.qa_status not in valid_statuses:
        raise HTTPException(400, f"Invalid qa_status '{req.qa_status}'. Must be one of: {valid_statuses}")

    pool = await get_pool()
    row = await pool.fetchrow(
        f"""UPDATE tasks
            SET qa_status = $2,
                qa_reviewer = $3,
                qa_output = $4,
                commit_hash = COALESCE($5, commit_hash),
                updated_at = now()
            WHERE id = $1
            RETURNING {TASK_COLUMNS}""",
        task_id,
        req.qa_status,
        req.qa_reviewer,
        req.qa_output,
        req.commit_hash,
    )
    if not row:
        raise HTTPException(404, "Task not found")

    d = dict(row)
    if not isinstance(d.get("metadata"), dict):
        d["metadata"] = {}

    log.info(
        f"QA update for task {task_id}: "
        f"status={req.qa_status}, reviewer={req.qa_reviewer}, "
        f"commit={req.commit_hash or 'none'}"
    )
    return TaskOut(**d)


@router.get("/{task_id}/qa-status")
async def get_qa_status(task_id: UUID):
    """Get QA review status for a task.

    Returns qa_status, qa_reviewer, qa_output, and commit_hash so the
    heartbeat can quickly check which tasks have been reviewed and committed.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, title, status, qa_status, qa_reviewer, qa_output, commit_hash
           FROM tasks WHERE id = $1""",
        task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")

    return {
        "task_id": str(task_id),
        "title": row["title"],
        "task_status": row["status"],
        "qa_status": row["qa_status"],
        "qa_reviewer": row["qa_reviewer"],
        "qa_output": row["qa_output"],
        "commit_hash": row["commit_hash"],
    }


@router.post("/{task_id}/qa-review", response_model=TaskOut)
async def trigger_qa_review(task_id: UUID):
    """Manually trigger QA review for a completed task.

    Spawns qa_runner.sh as a detached process. Useful for re-running QA
    on a task that was approved/rejected but needs a second look, or for tasks
    that completed before the QA layer was active.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = $1", task_id
    )
    if not row:
        raise HTTPException(404, "Task not found")

    task_data = dict(row)
    if task_data["status"] not in ("completed",):
        raise HTTPException(409, f"Task must be 'completed' to trigger QA (current: {task_data['status']})")

    if not isinstance(task_data.get("metadata"), dict):
        task_data["metadata"] = {}

    cli_backend = task_data.get("cli") or "claude"
    qa_runner = "/home/web3relic/otto/qa_runner.sh"
    log_dir = "/home/web3relic/otto/logs/tasks"

    import os as _os
    _os.makedirs(log_dir, exist_ok=True)

    from datetime import datetime as _dt
    ts = _dt.now().strftime("%Y%m%d_%H%M%S")
    qa_log = f"{log_dir}/{str(task_id)[:8]}-qa-{ts}.log"

    task_env = _os.environ.copy()
    task_env.setdefault("HOME", "/home/web3relic")
    task_env.setdefault("USER", "web3relic")
    task_env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"

    try:
        proc = subprocess.Popen(
            ["bash", qa_runner, str(task_id), cli_backend, qa_log],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            env=task_env,
        )
        pid = proc.pid
    except Exception as e:
        raise HTTPException(500, f"Failed to spawn qa_runner: {e}")

    # Reset qa_status to pending_qa
    updated = await pool.fetchrow(
        f"""UPDATE tasks SET qa_status = 'pending_qa', updated_at = now()
            WHERE id = $1 RETURNING {TASK_COLUMNS}""",
        task_id,
    )
    if not updated:
        raise HTTPException(404, "Task not found during update")

    d = dict(updated)
    if not isinstance(d.get("metadata"), dict):
        d["metadata"] = {}

    log.info(f"Manual QA review triggered for task {task_id} (PID {pid})")
    return TaskOut(**d)


@router.patch("/{task_id}/metadata", response_model=TaskOut)
async def patch_task_metadata(task_id: UUID, updates: dict):
    """Merge key-value pairs into a task's metadata JSON.

    Used by qa_runner.sh (Phase 2) to store rl2f_feedback_id after rejection,
    so the heartbeat can pass it to the retry task's metadata.
    """
    import json as _json
    pool = await get_pool()

    # Fetch existing metadata
    row = await pool.fetchrow(f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = $1", task_id)
    if not row:
        raise HTTPException(404, "Task not found")

    d = dict(row)
    existing_meta = d.get("metadata") or {}
    if not isinstance(existing_meta, dict):
        try:
            existing_meta = _json.loads(existing_meta) if isinstance(existing_meta, str) else {}
        except Exception:
            existing_meta = {}

    merged = {**existing_meta, **updates}

    updated = await pool.fetchrow(
        f"""UPDATE tasks SET metadata = $2, updated_at = now()
            WHERE id = $1 RETURNING {TASK_COLUMNS}""",
        task_id,
        merged,
    )
    d = dict(updated)
    if not isinstance(d.get("metadata"), dict):
        d["metadata"] = {}
    return TaskOut(**d)


# ── Onchain Task System ──────────────────────────────────────────────────────

@router.post("/{task_id}/upvote")
async def upvote_task(task_id: UUID):
    """Increment upvote count on a task. Returns new upvote count.

    Part of the onchain task priority system. Higher upvotes increase
    computed_priority_score: final = 0.5*base + 0.3*dependency + 0.2*upvote_factor
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE tasks SET upvotes = upvotes + 1, updated_at = now() WHERE id = $1 RETURNING id, title, upvotes, priority",
        task_id
    )
    if not row:
        raise HTTPException(404, "Task not found")
    d = dict(row)
    upvote_factor = round(d["upvotes"] / (d["upvotes"] + 10), 3)
    computed_score = round(
        0.5 * (d["priority"] / 10.0) + 0.2 * upvote_factor,
        3
    )
    return {
        "id": str(d["id"]),
        "title": d["title"],
        "upvotes": d["upvotes"],
        "upvote_factor": upvote_factor,
        "computed_score": computed_score,
    }


@router.post("/{task_id}/set-dependency-score")
async def set_dependency_score(task_id: UUID, score: float = 0.0):
    """Set the dependency score (0.0-1.0) for a task.

    Higher score = more critical systems depend on this task.
    Drives the dependency component of computed_priority_score.
    """
    if not 0.0 <= score <= 1.0:
        raise HTTPException(400, "dependency_score must be between 0.0 and 1.0")
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE tasks SET dependency_score = $2, updated_at = now() WHERE id = $1 RETURNING id, title, dependency_score, upvotes, priority",
        task_id, score
    )
    if not row:
        raise HTTPException(404, "Task not found")
    d = dict(row)
    upvote_factor = d["upvotes"] / (d["upvotes"] + 10)
    computed_score = round(
        0.5 * (d["priority"] / 10.0) + 0.3 * d["dependency_score"] + 0.2 * upvote_factor,
        3
    )
    return {
        "id": str(d["id"]),
        "title": d["title"],
        "dependency_score": d["dependency_score"],
        "computed_score": computed_score,
    }

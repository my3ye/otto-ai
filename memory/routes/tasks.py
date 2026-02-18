import os
import subprocess
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..models import TaskCreate, TaskOut, TaskComplete, TaskRunResponse

log = logging.getLogger("otto.tasks")

router = APIRouter(prefix="/tasks", tags=["tasks"])

TASK_RUNNER = "/home/web3relic/otto/task_runner.sh"
MAX_CONCURRENT_TASKS = 3

TASK_COLUMNS = """id, title, prompt, context, priority, status, model,
    max_budget_usd, max_turns, timeout_seconds, working_directory,
    pid, started_at, completed_at, output, error, exit_code,
    reviewed, reviewed_at, created_by, session_id,
    created_at, updated_at, metadata"""


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
        "SELECT id, pid FROM tasks WHERE status = 'running'"
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


# ── Queue Status (must be before /{task_id} routes) ───────────────

@router.get("/queue/status")
async def queue_status():
    """Summary of the task queue state."""
    pool = await get_pool()
    rows = await pool.fetch(
        "SELECT status, COUNT(*) as count FROM tasks GROUP BY status"
    )
    counts = {r["status"]: r["count"] for r in rows}
    running_alive = await _count_running(pool)
    return {
        "pending": counts.get("pending", 0),
        "running": counts.get("running", 0),
        "running_alive": running_alive,
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "cancelled": counts.get("cancelled", 0),
        "max_concurrent": MAX_CONCURRENT_TASKS,
        "can_run_more": running_alive < MAX_CONCURRENT_TASKS,
    }


# ── CRUD ───────────────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=201)
async def create_task(req: TaskCreate):
    """Create a new task in the queue."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""INSERT INTO tasks (title, prompt, context, priority, model,
               max_budget_usd, max_turns, timeout_seconds, working_directory,
               created_by, session_id, metadata)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
           RETURNING {TASK_COLUMNS}""",
        req.title, req.prompt, req.context, req.priority, req.model,
        req.max_budget_usd, req.max_turns, req.timeout_seconds,
        req.working_directory, req.created_by, req.session_id,
        req.metadata,
    )
    return TaskOut(**dict(row))


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    status: str | None = Query(default=None),
    reviewed: bool | None = Query(default=None),
    limit: int = Query(default=20, le=100),
):
    """List tasks with optional filters."""
    pool = await get_pool()
    conditions = []
    params = []
    idx = 1

    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    if reviewed is not None:
        conditions.append(f"reviewed = ${idx}")
        params.append(reviewed)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

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
                priority DESC, created_at ASC
            LIMIT ${idx}""",
        *params,
    )
    return [TaskOut(**dict(r)) for r in rows]


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: UUID):
    """Get a single task by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = $1", task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")
    return TaskOut(**dict(row))


# ── Execution ──────────────────────────────────────────────────────

@router.post("/{task_id}/run", response_model=TaskRunResponse)
async def run_task(task_id: UUID):
    """Spawn a detached task runner for the given task."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT id, status, title FROM tasks WHERE id = $1", task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found")
    if row["status"] != "pending":
        raise HTTPException(409, f"Task is '{row['status']}', must be 'pending' to run")

    running = await _count_running(pool)
    if running >= MAX_CONCURRENT_TASKS:
        raise HTTPException(
            429,
            f"Max concurrent tasks ({MAX_CONCURRENT_TASKS}) reached. {running} running.",
        )

    try:
        proc = subprocess.Popen(
            [TASK_RUNNER, str(task_id)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
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
    pool = await get_pool()
    status = "completed" if req.exit_code == 0 else "failed"
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
    return TaskOut(**dict(row))


@router.post("/{task_id}/review", response_model=TaskOut)
async def mark_reviewed(task_id: UUID):
    """Mark a completed/failed task as reviewed by the heartbeat."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"""UPDATE tasks SET reviewed = TRUE, reviewed_at = now()
            WHERE id = $1 AND status IN ('completed', 'failed')
            RETURNING {TASK_COLUMNS}""",
        task_id,
    )
    if not row:
        raise HTTPException(404, "Task not found or not in completed/failed status")
    return TaskOut(**dict(row))


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

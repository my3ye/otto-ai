import json
import subprocess
import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from ..db import get_pool
from ..models import TaskCreate, TaskOut, TaskQueueStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut)
async def create_task(req: TaskCreate):
    """Create a task in the queue. Tasks are detached executions — your agent creates
    them and they run independently, reporting back when done.

    Priority: 1 (low) to 10 (critical). Budget is in USD (cost ceiling for LLM calls).
    """
    pool = await get_pool()
    meta_str = json.dumps(req.metadata) if req.metadata else None

    row = await pool.fetchrow(
        """INSERT INTO tasks
               (title, prompt, priority, status, budget_usd, timeout_seconds,
                agent_type, model, created_by, metadata)
           VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7, $8, $9::jsonb)
           RETURNING id, title, prompt, priority, status, budget_usd, agent_type,
                     model, created_by, created_at, started_at, completed_at,
                     output, exit_code""",
        req.title,
        req.prompt,
        req.priority or 5,
        req.budget_usd or 1.0,
        req.timeout_seconds or 300,
        req.agent_type or "general-purpose",
        req.model or "sonnet",
        req.created_by or "user",
        meta_str,
    )
    return TaskOut(**dict(row))


@router.get("/queue/status", response_model=TaskQueueStatus)
async def queue_status():
    """Get a summary of the task queue."""
    pool = await get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    pending = await pool.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
    running = await pool.fetchval("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
    completed = await pool.fetchval(
        "SELECT COUNT(*) FROM tasks WHERE status = 'completed' AND completed_at >= $1", cutoff
    )
    failed = await pool.fetchval(
        "SELECT COUNT(*) FROM tasks WHERE status = 'failed' AND completed_at >= $1", cutoff
    )

    return TaskQueueStatus(
        pending=pending or 0,
        running=running or 0,
        completed_24h=completed or 0,
        failed_24h=failed or 0,
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str):
    """Get a single task by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, title, prompt, priority, status, budget_usd, agent_type,
                  model, created_by, created_at, started_at, completed_at,
                  output, exit_code
           FROM tasks WHERE id = $1""",
        task_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut(**dict(row))


@router.post("/{task_id}/run")
async def run_task(task_id: str):
    """Launch a pending task as a detached subprocess.

    The task runner (task_runner.sh) picks it up, runs the agent, and reports
    back via POST /tasks/{id}/complete when done.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, title FROM tasks WHERE id = $1", task_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Task not found")
    if row["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Task is '{row['status']}', not pending. Only pending tasks can be launched.",
        )

    # Resolve runner path — task_runner.sh lives outside the Docker build context (context: ./memory),
    # so it is NOT present in the Docker image. Check before marking the task running to avoid
    # creating a zombie task (status=running with no process behind it).
    runner_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../task_runner.sh")
    )
    if not os.path.exists(runner_script):
        raise HTTPException(
            status_code=400,
            detail=(
                "task_runner.sh not found. When running in Docker the runner must be "
                "mounted into the container or run on the host. "
                f"Expected path: {runner_script}"
            ),
        )

    # Mark as running only after we know the runner exists
    await pool.execute(
        "UPDATE tasks SET status = 'running', started_at = NOW() WHERE id = $1",
        task_id,
    )

    subprocess.Popen(
        ["bash", runner_script, task_id],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    return {"status": "launched", "task_id": task_id, "title": row["title"]}


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, output: str = "", exit_code: int = 0):
    """Called by the task runner to report completion. Not typically called by users directly."""
    pool = await get_pool()
    status = "completed" if exit_code == 0 else "failed"
    await pool.execute(
        """UPDATE tasks
           SET status = $1, output = $2, exit_code = $3, completed_at = NOW()
           WHERE id = $4""",
        status, output, exit_code, task_id,
    )
    return {"status": status, "task_id": task_id}

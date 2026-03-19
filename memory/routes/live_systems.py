"""
/live-systems — Live System registry and weekly auto-improvement cycle.

Distinction enforced here:
  - Tasks: have a deliverable + done state. Finite.
  - Live Systems: registered services with heartbeat + weekly improvement loop. Never "done".

Endpoints:
  GET    /live-systems              — list all registered live systems
  POST   /live-systems              — register a new live system
  GET    /live-systems/{id}         — get a single live system
  PUT    /live-systems/{id}         — update a live system
  DELETE /live-systems/{id}         — soft-delete (set status=paused)
  GET    /live-systems/{id}/health  — check health endpoint + last improvement status
  GET    /live-systems/{id}/improvements — improvement cycle history
  POST   /live-systems/{id}/improve — trigger a manual improvement cycle
  POST   /live-systems/{id}/improvements/{imp_id}/complete — record improvement outcome
  GET    /live-systems/due          — systems where next_improvement_at <= now()
  POST   /live-systems/weekly-run   — trigger improvement for all due systems (called by timer)
"""
import json
import subprocess
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool
from ..llm import llm_chat

log = logging.getLogger("otto.live_systems")

router = APIRouter(prefix="/live-systems", tags=["live-systems"])

WEEKLY_INTERVAL = timedelta(days=7)


# ── Pydantic models ─────────────────────────────────────────────────────────

class LiveSystemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    service_name: Optional[str] = None     # e.g. "otto-memory"
    repo_path: Optional[str] = None        # e.g. "/home/web3relic/otto"
    health_endpoint: Optional[str] = None  # e.g. "http://localhost:8100/health"
    eval_criteria: list = []               # [{name, check, threshold}]
    improvement_prompt: Optional[str] = None
    metadata: dict = {}


class LiveSystemUpdate(BaseModel):
    description: Optional[str] = None
    service_name: Optional[str] = None
    repo_path: Optional[str] = None
    health_endpoint: Optional[str] = None
    eval_criteria: Optional[list] = None
    improvement_prompt: Optional[str] = None
    status: Optional[str] = None
    metadata: Optional[dict] = None


class ImprovementComplete(BaseModel):
    improvement_identified: Optional[str] = None
    improvement_applied: bool = False
    eval_results: dict = {}
    eval_passed: Optional[bool] = None
    rollback_performed: bool = False
    rollback_reason: Optional[str] = None
    status: str = "completed"
    notes: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    d = dict(row)
    for field in ("eval_criteria", "metadata", "pre_state", "eval_results"):
        val = d.get(field)
        if isinstance(val, str):
            try:
                d[field] = json.loads(val)
            except Exception:
                pass
    return d


async def _check_health(endpoint: str) -> dict:
    """GET the health endpoint and return {ok, status_code, detail}."""
    if not endpoint:
        return {"ok": None, "detail": "no health endpoint configured"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(endpoint)
        ok = resp.status_code < 400
        return {"ok": ok, "status_code": resp.status_code, "detail": resp.text[:200]}
    except Exception as e:
        return {"ok": False, "status_code": None, "detail": str(e)[:200]}


async def _run_evals(system: dict) -> dict:
    """
    Run eval_criteria checks against the live system.
    Returns {passed: bool, checks: [{name, passed, value, threshold, detail}]}.
    """
    criteria = system.get("eval_criteria") or []
    if not criteria:
        return {"passed": True, "checks": [], "note": "no criteria defined — assumed passing"}

    results = []
    all_passed = True

    for criterion in criteria:
        name = criterion.get("name", "unnamed")
        check_type = criterion.get("check", "health")
        threshold = criterion.get("threshold")

        if check_type == "health":
            health = await _check_health(system.get("health_endpoint"))
            passed = health.get("ok", False)
            results.append({"name": name, "passed": passed, "value": health.get("status_code"), "threshold": threshold, "detail": health.get("detail")})

        elif check_type == "command":
            cmd = criterion.get("command")
            if cmd:
                try:
                    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                    passed = result.returncode == 0
                    results.append({"name": name, "passed": passed, "value": result.returncode, "threshold": 0, "detail": result.stdout[:200] or result.stderr[:200]})
                except subprocess.TimeoutExpired:
                    results.append({"name": name, "passed": False, "value": None, "threshold": threshold, "detail": "command timed out"})
                except Exception as e:
                    results.append({"name": name, "passed": False, "value": None, "threshold": threshold, "detail": str(e)})
            else:
                results.append({"name": name, "passed": False, "value": None, "threshold": threshold, "detail": "no command specified"})

        elif check_type == "endpoint_field":
            endpoint = criterion.get("endpoint") or system.get("health_endpoint")
            field = criterion.get("field")
            if endpoint and field:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(endpoint)
                    data = resp.json()
                    # Support dot notation: "db.healthy"
                    val = data
                    for part in field.split("."):
                        val = val.get(part) if isinstance(val, dict) else None
                    if threshold is not None:
                        passed = val is not None and float(val) >= float(threshold)
                    else:
                        passed = bool(val)
                    results.append({"name": name, "passed": passed, "value": val, "threshold": threshold, "detail": f"field={field}"})
                except Exception as e:
                    results.append({"name": name, "passed": False, "value": None, "threshold": threshold, "detail": str(e)[:200]})
            else:
                results.append({"name": name, "passed": False, "value": None, "threshold": threshold, "detail": "endpoint or field missing"})
        else:
            results.append({"name": name, "passed": True, "value": None, "threshold": threshold, "detail": f"unknown check type: {check_type}"})

        if not results[-1]["passed"]:
            all_passed = False

    return {"passed": all_passed, "checks": results}


async def _identify_improvement(system: dict, health: dict, eval_results: dict) -> str:
    """Use LLM to identify the top improvement opportunity for this live system."""
    default_prompt = (
        f"You are analyzing the live system '{system['name']}': {system.get('description', '')}. "
        f"Health status: {json.dumps(health)}. "
        f"Eval results: {json.dumps(eval_results)}. "
        f"Recent improvement cycles: {system.get('cycle_count', 0)} completed. "
        f"Identify ONE specific, actionable improvement for this system. "
        f"Be concrete: what file to change, what config to adjust, what metric to optimize. "
        f"Return just the improvement description in 1-3 sentences."
    )
    prompt = system.get("improvement_prompt") or default_prompt
    if system.get("improvement_prompt"):
        # Append context to custom prompt
        prompt += (
            f"\n\nCurrent health: {json.dumps(health)}. "
            f"Eval results: {json.dumps(eval_results)}."
        )
    try:
        result = await llm_chat([{"role": "user", "content": prompt}], max_tokens=300)
        return result.strip()
    except Exception as e:
        log.warning(f"LLM improvement identification failed: {e}")
        return f"LLM identification failed: {e}"


async def _create_checkpoint(system: dict, cycle_number: int) -> Optional[str]:
    """Create a git tag checkpoint if repo_path is set. Returns tag name or None."""
    repo_path = system.get("repo_path")
    if not repo_path:
        return None
    tag = f"live-system/{system['name'].lower().replace(' ', '-')}/cycle-{cycle_number}"
    try:
        result = subprocess.run(
            ["git", "tag", "-f", tag],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return tag
        log.warning(f"Git tag failed for {system['name']}: {result.stderr}")
        return None
    except Exception as e:
        log.warning(f"Checkpoint failed for {system['name']}: {e}")
        return None


async def _rollback_checkpoint(system: dict, tag: str) -> dict:
    """Attempt to git reset to a checkpoint tag. Returns {ok, detail}."""
    repo_path = system.get("repo_path")
    if not repo_path or not tag:
        return {"ok": False, "detail": "no repo_path or tag"}
    try:
        result = subprocess.run(
            ["git", "reset", "--hard", tag],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True, "detail": result.stdout.strip()}
        return {"ok": False, "detail": result.stderr.strip()}
    except Exception as e:
        return {"ok": False, "detail": str(e)}


# ── Routes ──────────────────────────────────────────────────────────────────

@router.get("")
async def list_live_systems(status: Optional[str] = Query(None)):
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            "SELECT * FROM live_systems WHERE status = $1 ORDER BY name", status
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM live_systems ORDER BY name"
        )
    return [_row_to_dict(r) for r in rows]


@router.post("", status_code=201)
async def register_live_system(body: LiveSystemCreate):
    pool = await get_pool()
    # Schedule first improvement 7 days from now
    next_run = datetime.now(timezone.utc) + WEEKLY_INTERVAL
    row = await pool.fetchrow(
        """INSERT INTO live_systems
               (name, description, service_name, repo_path, health_endpoint,
                eval_criteria, improvement_prompt, metadata, next_improvement_at)
           VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb, $9)
           RETURNING *""",
        body.name,
        body.description,
        body.service_name,
        body.repo_path,
        body.health_endpoint,
        json.dumps(body.eval_criteria),
        body.improvement_prompt,
        json.dumps(body.metadata),
        next_run,
    )
    return _row_to_dict(row)


@router.get("/due")
async def get_due_systems():
    """Return systems where next_improvement_at <= now() and status = active."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM live_systems
           WHERE status = 'active'
             AND next_improvement_at IS NOT NULL
             AND next_improvement_at <= now()
           ORDER BY next_improvement_at"""
    )
    return [_row_to_dict(r) for r in rows]


@router.get("/{system_id}")
async def get_live_system(system_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM live_systems WHERE id = $1", system_id)
    if not row:
        raise HTTPException(status_code=404, detail="Live system not found")
    return _row_to_dict(row)


@router.put("/{system_id}")
async def update_live_system(system_id: UUID, body: LiveSystemUpdate):
    pool = await get_pool()
    existing = await pool.fetchrow("SELECT * FROM live_systems WHERE id = $1", system_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Live system not found")

    updates = body.dict(exclude_none=True)
    if not updates:
        return _row_to_dict(existing)

    set_clauses = []
    params = []
    idx = 1
    for key, val in updates.items():
        if key in ("eval_criteria", "metadata"):
            set_clauses.append(f"{key} = ${idx}::jsonb")
            params.append(json.dumps(val))
        else:
            set_clauses.append(f"{key} = ${idx}")
            params.append(val)
        idx += 1
    set_clauses.append(f"updated_at = ${idx}")
    params.append(datetime.now(timezone.utc))
    idx += 1
    params.append(system_id)

    row = await pool.fetchrow(
        f"UPDATE live_systems SET {', '.join(set_clauses)} WHERE id = ${idx} RETURNING *",
        *params,
    )
    return _row_to_dict(row)


@router.delete("/{system_id}")
async def pause_live_system(system_id: UUID):
    """Soft-delete: set status to paused."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE live_systems SET status = 'paused', updated_at = now() WHERE id = $1 RETURNING *",
        system_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Live system not found")
    return {"status": "paused", "id": str(system_id)}


@router.get("/{system_id}/health")
async def get_system_health(system_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM live_systems WHERE id = $1", system_id)
    if not row:
        raise HTTPException(status_code=404, detail="Live system not found")
    system = _row_to_dict(row)

    health = await _check_health(system.get("health_endpoint"))

    # Latest improvement
    latest = await pool.fetchrow(
        """SELECT * FROM live_system_improvements
           WHERE system_id = $1
           ORDER BY started_at DESC LIMIT 1""",
        system_id,
    )

    return {
        "system_id": str(system_id),
        "name": system["name"],
        "status": system["status"],
        "health": health,
        "cycle_count": system["cycle_count"],
        "consecutive_failures": system["consecutive_failures"],
        "last_improved_at": system.get("last_improved_at"),
        "next_improvement_at": system.get("next_improvement_at"),
        "latest_improvement": _row_to_dict(latest) if latest else None,
    }


@router.get("/{system_id}/improvements")
async def list_improvements(
    system_id: UUID,
    limit: int = Query(20, ge=1, le=100),
):
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM live_system_improvements
           WHERE system_id = $1
           ORDER BY started_at DESC LIMIT $2""",
        system_id, limit,
    )
    return [_row_to_dict(r) for r in rows]


@router.post("/{system_id}/improve", status_code=201)
async def trigger_improvement(system_id: UUID):
    """
    Run the full improvement cycle for a live system:
    1. Check health
    2. Run evals
    3. Create git checkpoint
    4. Identify improvement via LLM
    5. Log improvement record (actual implementation happens via task queue)
    6. Update next_improvement_at
    """
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM live_systems WHERE id = $1", system_id)
    if not row:
        raise HTTPException(status_code=404, detail="Live system not found")
    system = _row_to_dict(row)

    if system["status"] != "active":
        raise HTTPException(status_code=400, detail=f"System is {system['status']} — not active")

    cycle_number = system["cycle_count"] + 1
    log.info(f"Starting improvement cycle {cycle_number} for {system['name']}")

    # 1. Health check
    health = await _check_health(system.get("health_endpoint"))

    # 2. Run evals (pre-improvement baseline)
    eval_results = await _run_evals(system)

    # 3. Create git checkpoint
    checkpoint_tag = await _create_checkpoint(system, cycle_number)

    # 4. Identify improvement
    improvement_identified = await _identify_improvement(system, health, eval_results)

    # 5. Log improvement record
    imp_row = await pool.fetchrow(
        """INSERT INTO live_system_improvements
               (system_id, cycle_number, checkpoint_tag, pre_state,
                improvement_identified, status)
           VALUES ($1, $2, $3, $4::jsonb, $5, 'running')
           RETURNING *""",
        system_id,
        cycle_number,
        checkpoint_tag,
        json.dumps({"health": health, "eval_results": eval_results}),
        improvement_identified,
    )

    # 6. Update system
    await pool.execute(
        """UPDATE live_systems
           SET cycle_count = $1,
               last_improved_at = now(),
               next_improvement_at = now() + INTERVAL '7 days',
               updated_at = now()
           WHERE id = $2""",
        cycle_number,
        system_id,
    )

    return {
        "improvement_id": str(imp_row["id"]),
        "system_id": str(system_id),
        "cycle_number": cycle_number,
        "checkpoint_tag": checkpoint_tag,
        "health": health,
        "eval_baseline": eval_results,
        "improvement_identified": improvement_identified,
        "status": "running",
        "note": (
            "Improvement identified. Create a task to implement it, then call "
            f"POST /live-systems/{system_id}/improvements/{imp_row['id']}/complete "
            "with the results."
        ),
    }


@router.post("/{system_id}/improvements/{imp_id}/complete")
async def complete_improvement(
    system_id: UUID,
    imp_id: UUID,
    body: ImprovementComplete,
):
    """
    Record the outcome of an improvement cycle.
    If eval_passed=False, optionally trigger rollback.
    """
    pool = await get_pool()

    # Verify existence
    imp = await pool.fetchrow(
        "SELECT * FROM live_system_improvements WHERE id = $1 AND system_id = $2",
        imp_id, system_id,
    )
    if not imp:
        raise HTTPException(status_code=404, detail="Improvement record not found")

    system_row = await pool.fetchrow("SELECT * FROM live_systems WHERE id = $1", system_id)
    system = _row_to_dict(system_row)

    rollback_result = None
    if body.rollback_performed and imp["checkpoint_tag"]:
        rollback_result = await _rollback_checkpoint(system, imp["checkpoint_tag"])
        log.warning(f"Rolled back {system['name']} to {imp['checkpoint_tag']}: {rollback_result}")

    # Update improvement record
    await pool.execute(
        """UPDATE live_system_improvements
           SET completed_at = now(),
               improvement_identified = COALESCE($1, improvement_identified),
               improvement_applied = $2,
               eval_results = $3::jsonb,
               eval_passed = $4,
               rollback_performed = $5,
               rollback_reason = $6,
               status = $7,
               notes = $8
           WHERE id = $9""",
        body.improvement_identified,
        body.improvement_applied,
        json.dumps(body.eval_results),
        body.eval_passed,
        body.rollback_performed,
        body.rollback_reason,
        body.status,
        body.notes,
        imp_id,
    )

    # Update system consecutive failures
    if body.eval_passed is False:
        await pool.execute(
            """UPDATE live_systems
               SET consecutive_failures = consecutive_failures + 1,
                   status = CASE WHEN consecutive_failures + 1 >= 3 THEN 'failed' ELSE status END,
                   updated_at = now()
               WHERE id = $1""",
            system_id,
        )
    elif body.eval_passed is True:
        await pool.execute(
            "UPDATE live_systems SET consecutive_failures = 0, updated_at = now() WHERE id = $1",
            system_id,
        )

    return {
        "improvement_id": str(imp_id),
        "status": body.status,
        "eval_passed": body.eval_passed,
        "rollback_performed": body.rollback_performed,
        "rollback_result": rollback_result,
    }


@router.post("/weekly-run")
async def run_weekly_improvements():
    """
    Trigger improvement cycle for all due active systems.
    Called by the weekly systemd timer (weekly_improve.sh).
    Returns summary of what was triggered.
    """
    pool = await get_pool()
    due_rows = await pool.fetch(
        """SELECT * FROM live_systems
           WHERE status = 'active'
             AND next_improvement_at IS NOT NULL
             AND next_improvement_at <= now()
           ORDER BY next_improvement_at"""
    )

    results = []
    for row in due_rows:
        system = _row_to_dict(row)
        try:
            # Delegate to per-system improve endpoint logic inline
            cycle_number = system["cycle_count"] + 1
            health = await _check_health(system.get("health_endpoint"))
            eval_results = await _run_evals(system)
            checkpoint_tag = await _create_checkpoint(system, cycle_number)
            improvement_identified = await _identify_improvement(system, health, eval_results)

            imp_row = await pool.fetchrow(
                """INSERT INTO live_system_improvements
                       (system_id, cycle_number, checkpoint_tag, pre_state,
                        improvement_identified, status)
                   VALUES ($1, $2, $3, $4::jsonb, $5, 'running')
                   RETURNING id""",
                row["id"],
                cycle_number,
                checkpoint_tag,
                json.dumps({"health": health, "eval_results": eval_results}),
                improvement_identified,
            )

            await pool.execute(
                """UPDATE live_systems
                   SET cycle_count = $1,
                       last_improved_at = now(),
                       next_improvement_at = now() + INTERVAL '7 days',
                       updated_at = now()
                   WHERE id = $2""",
                cycle_number,
                row["id"],
            )

            results.append({
                "system": system["name"],
                "improvement_id": str(imp_row["id"]),
                "cycle": cycle_number,
                "health_ok": health.get("ok"),
                "evals_passed": eval_results.get("passed"),
                "improvement_identified": improvement_identified,
                "checkpoint": checkpoint_tag,
                "status": "triggered",
            })
            log.info(f"Weekly improvement triggered for {system['name']} (cycle {cycle_number})")

        except Exception as e:
            log.error(f"Weekly improvement failed for {system['name']}: {e}")
            results.append({
                "system": system["name"],
                "status": "error",
                "error": str(e),
            })

    return {
        "systems_due": len(due_rows),
        "triggered": len([r for r in results if r.get("status") == "triggered"]),
        "errors": len([r for r in results if r.get("status") == "error"]),
        "results": results,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }

"""
/metrics — Heartbeat performance tracking and self-improvement evaluation.

Endpoints:
  POST /metrics/heartbeat        — Record a heartbeat run's metrics
  GET  /metrics/heartbeat        — Query recent heartbeat metrics
  GET  /metrics/trends           — Week-over-week performance trends
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from ..db import get_pool
from ..models import HeartbeatMetricCreate, HeartbeatMetricOut, HeartbeatTrend, MetricsSummary

router = APIRouter(prefix="/metrics", tags=["metrics"])

_NUMERIC_COLS = ["duration_s", "budget_used", "tasks_created", "tasks_launched",
                 "tasks_reviewed", "messages_sent"]


# ── Helpers ────────────────────────────────────────────────────────────────

def _row_to_out(row) -> HeartbeatMetricOut:
    d = dict(row)
    # asyncpg returns JSONB as str or dict depending on driver; normalise.
    for field in ("errors", "metadata"):
        val = d.get(field)
        if isinstance(val, str):
            d[field] = json.loads(val)
        elif val is None:
            d[field] = [] if field == "errors" else {}
    return HeartbeatMetricOut(**d)


def _week_avg(rows) -> dict:
    """Compute averages for numeric columns across a list of DB rows."""
    if not rows:
        return {col: None for col in _NUMERIC_COLS}
    totals = {col: 0.0 for col in _NUMERIC_COLS}
    counts = {col: 0 for col in _NUMERIC_COLS}
    for row in rows:
        for col in _NUMERIC_COLS:
            val = row[col]
            if val is not None:
                totals[col] += float(val)
                counts[col] += 1
    return {
        col: round(totals[col] / counts[col], 4) if counts[col] else None
        for col in _NUMERIC_COLS
    }


def _delta(current: dict, prior: dict) -> dict:
    """current - prior; None if either side is None."""
    result = {}
    for col in _NUMERIC_COLS:
        c, p = current.get(col), prior.get(col)
        result[col] = round(c - p, 4) if (c is not None and p is not None) else None
    return result


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/heartbeat", response_model=HeartbeatMetricOut, status_code=201)
async def record_heartbeat_metric(body: HeartbeatMetricCreate):
    """Record metrics for a completed heartbeat run."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO heartbeat_metrics
               (heartbeat_type, duration_s, budget_used,
                tasks_created, tasks_launched, tasks_reviewed,
                messages_sent, errors, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb)
           RETURNING *""",
        body.heartbeat_type,
        body.duration_s,
        body.budget_used,
        body.tasks_created,
        body.tasks_launched,
        body.tasks_reviewed,
        body.messages_sent,
        json.dumps(body.errors),
        json.dumps(body.metadata),
    )
    return _row_to_out(row)


@router.get("/heartbeat", response_model=list[HeartbeatMetricOut])
async def get_heartbeat_metrics(
    heartbeat_type: str | None = Query(None, description="Filter by type: orchestrator|reflection|alpha"),
    limit: int = Query(50, ge=1, le=500),
    since_hours: int = Query(168, ge=1, description="Look back N hours (default 7 days)"),
):
    """Return recent heartbeat metrics, newest first."""
    pool = await get_pool()
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)

    if heartbeat_type:
        rows = await pool.fetch(
            """SELECT * FROM heartbeat_metrics
               WHERE heartbeat_type = $1 AND timestamp >= $2
               ORDER BY timestamp DESC LIMIT $3""",
            heartbeat_type, since, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT * FROM heartbeat_metrics
               WHERE timestamp >= $1
               ORDER BY timestamp DESC LIMIT $2""",
            since, limit,
        )
    return [_row_to_out(r) for r in rows]


@router.get("/trends", response_model=list[HeartbeatTrend])
async def get_trends(
    heartbeat_type: Literal["orchestrator", "reflection", "alpha", "all"] = Query("all"),
):
    """
    Week-over-week performance trends.

    Compares current 7-day window to the prior 7-day window for each metric.
    A positive delta means improvement (more tasks done, lower errors, etc.).
    budget_used delta is intentionally raw — caller decides if higher spend is good or bad.
    """
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    types = (
        ["orchestrator", "reflection", "alpha"]
        if heartbeat_type == "all"
        else [heartbeat_type]
    )

    results = []
    for htype in types:
        current_rows = await pool.fetch(
            """SELECT duration_s, budget_used, tasks_created, tasks_launched,
                      tasks_reviewed, messages_sent
               FROM heartbeat_metrics
               WHERE heartbeat_type = $1 AND timestamp >= $2 AND timestamp < $3""",
            htype, week_ago, now,
        )
        prior_rows = await pool.fetch(
            """SELECT duration_s, budget_used, tasks_created, tasks_launched,
                      tasks_reviewed, messages_sent
               FROM heartbeat_metrics
               WHERE heartbeat_type = $1 AND timestamp >= $2 AND timestamp < $3""",
            htype, two_weeks_ago, week_ago,
        )

        current_avg = _week_avg(current_rows)
        prior_avg = _week_avg(prior_rows)

        results.append(HeartbeatTrend(
            heartbeat_type=htype,
            current_week={**current_avg, "run_count": len(current_rows)},
            prior_week={**prior_avg, "run_count": len(prior_rows)},
            deltas=_delta(current_avg, prior_avg),
        ))

    return results


@router.get("/summary", response_model=MetricsSummary)
async def get_metrics_summary():
    """Unified dashboard: tasks, heartbeats, communication, memory counts."""
    pool = await get_pool()

    # Tasks
    task_rows = await pool.fetch(
        """SELECT
               COUNT(*)                                                         AS total,
               COUNT(*) FILTER (WHERE status = 'completed')                    AS completed,
               COUNT(*) FILTER (WHERE status = 'failed')                       AS failed,
               COUNT(*) FILTER (WHERE status IN ('pending', 'running'))        AS pending,
               AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
                   FILTER (WHERE completed_at IS NOT NULL AND started_at IS NOT NULL) AS avg_completion_s
           FROM tasks"""
    )
    t = dict(task_rows[0])
    completed = int(t["completed"] or 0)
    failed = int(t["failed"] or 0)
    denom = completed + failed
    success_rate = round(completed / denom, 4) if denom else None

    tasks = {
        "total": int(t["total"] or 0),
        "completed": completed,
        "failed": failed,
        "pending": int(t["pending"] or 0),
        "avg_completion_s": round(float(t["avg_completion_s"]), 2) if t["avg_completion_s"] else None,
        "success_rate": success_rate,
    }

    # Heartbeats
    hb_rows = await pool.fetch(
        """SELECT COUNT(*) AS total, AVG(duration_s) AS avg_duration_s, AVG(budget_used) AS avg_budget_used
           FROM heartbeat_metrics"""
    )
    h = dict(hb_rows[0])
    heartbeats = {
        "total": int(h["total"] or 0),
        "avg_duration_s": round(float(h["avg_duration_s"]), 2) if h["avg_duration_s"] else None,
        "avg_budget_used": round(float(h["avg_budget_used"]), 4) if h["avg_budget_used"] else None,
    }

    # Communication
    pq_rows = await pool.fetch(
        """SELECT
               COUNT(*) FILTER (WHERE resolved_at IS NULL)     AS open_questions,
               COUNT(*) FILTER (WHERE resolved_at IS NOT NULL) AS resolved_questions
           FROM pending_questions"""
    )
    p = dict(pq_rows[0])
    communication = {
        "open_questions": int(p["open_questions"] or 0),
        "resolved_questions": int(p["resolved_questions"] or 0),
    }

    # Memory
    mem_rows = await pool.fetch(
        """SELECT
               (SELECT COUNT(*) FROM semantic_memories) AS total_semantic,
               (SELECT COUNT(*) FROM episodic_events)   AS total_episodic"""
    )
    m = dict(mem_rows[0])
    memory = {
        "total_semantic": int(m["total_semantic"] or 0),
        "total_episodic": int(m["total_episodic"] or 0),
    }

    return MetricsSummary(
        tasks=tasks,
        heartbeats=heartbeats,
        communication=communication,
        memory=memory,
        generated_at=datetime.now(timezone.utc),
    )

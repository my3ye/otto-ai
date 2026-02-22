"""APC Plan Cache routes — Adaptive Plan Caching (arXiv 2506.14852).

POST /plans/cache  — Store a successful plan execution for future reuse
POST /plans/match  — Find cached plans similar to a new task (cosine > threshold)
GET  /plans/cache  — Browse cached plans (recent, by success rate)
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..db import get_pool
from ..embeddings import get_embedding
from ..models import PlanCacheStore, PlanCacheMatch, PlanCacheMatchResponse, PlanCacheEntry

log = logging.getLogger(__name__)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/cache", status_code=201)
async def cache_plan(req: PlanCacheStore):
    """Store a successful task execution plan in the cache.

    Called by the task runner or heartbeat after a task completes successfully.
    Embeds the task_prompt so future tasks can find it via cosine similarity.
    """
    embedding = await get_embedding(req.task_prompt)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO plan_cache
            (task_id, task_title, task_prompt, task_embedding,
             selected_plan, plan_metadata, success, execution_time_s, model_used)
        VALUES ($1, $2, $3, $4::vector, $5, $6::jsonb, $7, $8, $9)
        RETURNING id, created_at
        """,
        req.task_id,
        req.task_title[:200],
        req.task_prompt,
        embedding_str,
        req.selected_plan,
        json.dumps(req.plan_metadata),
        req.success,
        req.execution_time_s,
        req.model_used,
    )

    log.info(f"Plan cached: id={row['id']} title='{req.task_title[:60]}' success={req.success}")
    return {"id": str(row["id"]), "cached_at": row["created_at"].isoformat()}


@router.post("/match", response_model=PlanCacheMatchResponse)
async def match_plan(req: PlanCacheMatch):
    """Find cached plans similar to a new task prompt.

    Uses pgvector cosine similarity to find plans with score >= threshold.
    Only returns plans that previously succeeded.
    Updates used_count and last_used_at on matched entries.

    Returns up to `limit` entries sorted by similarity descending.
    The LATS planner calls this before generating new approaches —
    if matched=True, the best cached plan is injected as the top candidate.
    """
    embedding = await get_embedding(req.task_prompt)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()

    rows = await pool.fetch(
        """
        SELECT
            id,
            task_title,
            task_prompt,
            selected_plan,
            plan_metadata,
            success,
            used_count,
            created_at,
            1 - (task_embedding <=> $1::vector) AS similarity
        FROM plan_cache
        WHERE success = TRUE
          AND 1 - (task_embedding <=> $1::vector) >= $2
        ORDER BY similarity DESC
        LIMIT $3
        """,
        embedding_str,
        req.threshold,
        req.limit,
    )

    if not rows:
        return PlanCacheMatchResponse(matched=False, entries=[], best_similarity=None)

    # Update usage stats for all matched entries
    matched_ids = [r["id"] for r in rows]
    await pool.execute(
        """
        UPDATE plan_cache
        SET used_count = used_count + 1, last_used_at = now()
        WHERE id = ANY($1::uuid[])
        """,
        matched_ids,
    )

    entries = [
        PlanCacheEntry(
            id=r["id"],
            task_title=r["task_title"],
            task_prompt=r["task_prompt"],
            selected_plan=r["selected_plan"],
            plan_metadata=json.loads(r["plan_metadata"]) if r["plan_metadata"] else {},
            success=r["success"],
            similarity=round(float(r["similarity"]), 4),
            used_count=r["used_count"] + 1,  # reflect increment
            created_at=r["created_at"],
        )
        for r in rows
    ]

    best = entries[0].similarity
    log.info(
        f"Plan cache match: query='{req.task_prompt[:60]}' "
        f"found={len(entries)} best_similarity={best}"
    )

    return PlanCacheMatchResponse(matched=True, entries=entries, best_similarity=best)


@router.get("/cache")
async def list_cached_plans(limit: int = 20, success_only: bool = True):
    """Browse the plan cache — most recently cached first."""
    pool = await get_pool()
    where = "WHERE success = TRUE" if success_only else ""
    rows = await pool.fetch(
        f"""
        SELECT id, task_title, task_prompt, selected_plan,
               plan_metadata, success, used_count, created_at, last_used_at
        FROM plan_cache
        {where}
        ORDER BY created_at DESC
        LIMIT $1
        """,
        limit,
    )

    return {
        "count": len(rows),
        "entries": [
            {
                "id": str(r["id"]),
                "task_title": r["task_title"],
                "task_prompt": r["task_prompt"][:200],
                "success": r["success"],
                "used_count": r["used_count"],
                "created_at": r["created_at"].isoformat(),
                "last_used_at": r["last_used_at"].isoformat() if r["last_used_at"] else None,
            }
            for r in rows
        ],
    }

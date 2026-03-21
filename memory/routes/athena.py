"""Athena OMS API — prospect management and conversation visibility."""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool
from ..gateway.athena_handler import VALID_STAGES

log = logging.getLogger("otto.routes.athena")
router = APIRouter(prefix="/athena", tags=["athena"])


class StageUpdateBody(BaseModel):
    stage: str
    notes: str | None = None


@router.get("/prospects")
async def list_prospects(
    stage: str | None = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
):
    """List all Athena prospects, optionally filtered by stage."""
    pool = await get_pool()
    if stage:
        rows = await pool.fetch(
            """SELECT id, jid, phone, name, stage, business_name, lead_type, city,
                      qualification_notes, stage_updated_at, created_at
               FROM athena_prospects
               WHERE stage = $1
               ORDER BY stage_updated_at DESC
               LIMIT $2 OFFSET $3""",
            stage, limit, offset
        )
    else:
        rows = await pool.fetch(
            """SELECT id, jid, phone, name, stage, business_name, lead_type, city,
                      qualification_notes, stage_updated_at, created_at
               FROM athena_prospects
               ORDER BY stage_updated_at DESC
               LIMIT $1 OFFSET $2""",
            limit, offset
        )
    return [dict(r) for r in rows]


@router.get("/prospects/{prospect_id}")
async def get_prospect(prospect_id: str):
    """Get a single prospect with full details."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM athena_prospects WHERE id = $1", prospect_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return dict(row)


@router.get("/prospects/{prospect_id}/conversations")
async def get_prospect_conversations(prospect_id: str, limit: int = Query(50, le=500)):
    """Get conversation history for a prospect."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, direction, content, stage_at, created_at
           FROM athena_conversations
           WHERE prospect_id = $1
           ORDER BY created_at ASC
           LIMIT $2""",
        prospect_id, limit
    )
    return [dict(r) for r in rows]


@router.get("/stats")
async def get_athena_stats():
    """Funnel stats: count by stage, total prospects, recent activity."""
    pool = await get_pool()

    stage_counts = await pool.fetch(
        """SELECT stage, COUNT(*) as count
           FROM athena_prospects
           GROUP BY stage
           ORDER BY count DESC"""
    )

    total = await pool.fetchval("SELECT COUNT(*) FROM athena_prospects")

    recent = await pool.fetch(
        """SELECT id, name, business_name, stage, stage_updated_at
           FROM athena_prospects
           ORDER BY stage_updated_at DESC
           LIMIT 5"""
    )

    total_conversations = await pool.fetchval(
        "SELECT COUNT(*) FROM athena_conversations"
    )

    return {
        "total_prospects": total,
        "total_conversations": total_conversations,
        "by_stage": {r["stage"]: r["count"] for r in stage_counts},
        "recent_activity": [dict(r) for r in recent],
    }


@router.patch("/prospects/{prospect_id}/stage")
async def update_prospect_stage(prospect_id: str, body: StageUpdateBody):
    """Manually update a prospect's stage (Mev override)."""
    new_stage = body.stage
    if new_stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Valid: {sorted(VALID_STAGES)}")

    pool = await get_pool()
    result = await pool.execute(
        """UPDATE athena_prospects
           SET stage = $1, stage_updated_at = NOW(), updated_at = NOW()
           WHERE id = $2""",
        new_stage, prospect_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Prospect not found")

    return {"ok": True, "stage": new_stage}

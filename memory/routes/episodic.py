import json
from datetime import datetime, timezone
from fastapi import APIRouter
from ..db import get_pool
from ..models import EpisodicEventCreate, EpisodicEventOut, TimelineQuery

router = APIRouter(prefix="/episodic", tags=["episodic"])


@router.post("/events", response_model=EpisodicEventOut)
async def create_event(req: EpisodicEventCreate):
    """Log an episodic event. Use this to record what your agent did, saw, or decided.

    Events are timestamped and can be queried by session, type, or importance.
    Higher importance events are surfaced more prominently in timeline queries.
    """
    pool = await get_pool()
    meta_str = json.dumps(req.metadata) if req.metadata else "{}"

    row = await pool.fetchrow(
        """INSERT INTO episodic_events
               (session_id, content, event_type, importance, metadata)
           VALUES ($1, $2, $3, $4, $5::jsonb)
           RETURNING id, session_id, content, event_type, importance, created_at""",
        req.session_id,
        req.content,
        req.event_type or "general",
        req.importance or 0.5,
        meta_str,
    )
    return EpisodicEventOut(**dict(row))


@router.post("/timeline", response_model=list[EpisodicEventOut])
async def get_timeline(req: TimelineQuery):
    """Query episodic events. Filter by session, event type, or minimum importance.

    Returns events in reverse chronological order (newest first).
    """
    pool = await get_pool()
    conditions = ["importance >= $1"]
    params: list = [req.min_importance or 0.0]
    idx = 2

    if req.event_type:
        conditions.append(f"event_type = ${idx}")
        params.append(req.event_type)
        idx += 1

    if req.session_id:
        conditions.append(f"session_id = ${idx}")
        params.append(req.session_id)
        idx += 1

    where = " AND ".join(conditions)
    params.append(req.limit or 50)

    rows = await pool.fetch(
        f"""SELECT id, session_id, content, event_type, importance, created_at
            FROM episodic_events
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx}""",
        *params,
    )
    return [EpisodicEventOut(**dict(r)) for r in rows]

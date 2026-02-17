from fastapi import APIRouter
from ..db import get_pool
from ..models import EpisodicEventCreate, EpisodicEventOut, TimelineQuery

router = APIRouter(prefix="/episodic", tags=["episodic"])


@router.post("/events", response_model=EpisodicEventOut)
async def create_event(req: EpisodicEventCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO episodic_events (session_id, content, event_type, importance, metadata)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING id, session_id, content, event_type, importance, created_at""",
        req.session_id, req.content, req.event_type, req.importance,
        req.metadata,
    )
    return EpisodicEventOut(**dict(row))


@router.post("/timeline", response_model=list[EpisodicEventOut])
async def get_timeline(req: TimelineQuery):
    pool = await get_pool()
    conditions = ["importance >= $1"]
    params: list = [req.min_importance]
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
    params.append(req.limit)

    rows = await pool.fetch(
        f"""SELECT id, session_id, content, event_type, importance, created_at
            FROM episodic_events
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx}""",
        *params,
    )
    return [EpisodicEventOut(**dict(r)) for r in rows]

import json
from fastapi import APIRouter
from ..db import get_pool
from ..models import EpisodicEventCreate, EpisodicEventOut, TimelineQuery

router = APIRouter(prefix="/episodic", tags=["episodic"])


def _compute_surprise(metadata: dict) -> float:
    """Derive surprise score from metadata if possible, else return default 0.5.

    SuRe heuristics (in priority order):
    1. Caller explicitly sets metadata['surprise_score'] (float 0-1).
    2. event_type 'error' → 0.85 (errors are inherently surprising).
    3. metadata contains 'expected' + 'actual' strings → Jaccard distance proxy.
    4. Default: 0.5 (moderate/unknown surprise).
    """
    if "surprise_score" in metadata:
        try:
            return max(0.0, min(1.0, float(metadata["surprise_score"])))
        except (TypeError, ValueError):
            pass
    return 0.5  # default; event_type back-fill handled by migration & route below


@router.post("/events", response_model=EpisodicEventOut)
async def create_event(req: EpisodicEventCreate):
    pool = await get_pool()

    # Compute surprise score from metadata heuristics
    surprise = _compute_surprise(req.metadata)
    # Error events are inherently surprising
    if req.event_type == "error" and surprise == 0.5:
        surprise = 0.85

    meta_str = json.dumps(req.metadata) if req.metadata else "{}"

    row = await pool.fetchrow(
        """INSERT INTO episodic_events
               (session_id, content, event_type, importance, metadata, surprise_score)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6)
           RETURNING id, session_id, content, event_type, importance, created_at""",
        req.session_id, req.content, req.event_type, req.importance,
        meta_str, surprise,
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

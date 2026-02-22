from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..db import get_pool
from ..models import PrincipleCreate, PrincipleOut

router = APIRouter(prefix="/principles", tags=["principles"])


@router.post("", response_model=PrincipleOut)
async def create_principle(req: PrincipleCreate):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO principles (principle, category, source_events, confidence)
           VALUES ($1, $2, $3, $4)
           RETURNING id, principle, category, source_events, confidence,
                     times_applied, times_violated, created_at, updated_at""",
        req.principle, req.category, req.source_events, req.confidence,
    )
    return PrincipleOut(**dict(row))


@router.get("", response_model=list[PrincipleOut])
async def list_principles(category: str | None = None):
    pool = await get_pool()
    if category:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               WHERE category = $1
               ORDER BY confidence DESC, created_at DESC""",
            category,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               ORDER BY confidence DESC, created_at DESC""",
        )
    return [PrincipleOut(**dict(r)) for r in rows]


@router.get("/active", response_model=list[PrincipleOut])
async def list_active_principles(category: str | None = None):
    """Return principles with confidence > 0.3, sorted by confidence desc."""
    pool = await get_pool()
    if category:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               WHERE confidence > 0.3 AND category = $1
               ORDER BY confidence DESC""",
            category,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               WHERE confidence > 0.3
               ORDER BY confidence DESC""",
        )
    return [PrincipleOut(**dict(r)) for r in rows]


@router.get("/top", response_model=list[PrincipleOut])
async def top_principles(limit: int = 5, category: str | None = None):
    """Return top N active principles sorted by confidence (for context injection)."""
    pool = await get_pool()
    if category:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               WHERE confidence > 0.3 AND category = $1
               ORDER BY confidence DESC LIMIT $2""",
            category, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, principle, category, source_events, confidence,
                      times_applied, times_violated, created_at, updated_at
               FROM principles
               WHERE confidence > 0.3
               ORDER BY confidence DESC LIMIT $1""",
            limit,
        )
    return [PrincipleOut(**dict(r)) for r in rows]


@router.put("/{principle_id}/applied", response_model=PrincipleOut)
async def record_applied(principle_id: UUID):
    """Increment times_applied and boost confidence by 0.05 (cap at 1.0)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE principles
           SET times_applied = times_applied + 1,
               confidence = LEAST(1.0, confidence + 0.05)
           WHERE id = $1
           RETURNING id, principle, category, source_events, confidence,
                     times_applied, times_violated, created_at, updated_at""",
        principle_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Principle '{principle_id}' not found")
    return PrincipleOut(**dict(row))


@router.put("/{principle_id}/violated", response_model=PrincipleOut)
async def record_violated(principle_id: UUID):
    """Decrement confidence by 0.1 (floor at 0.0) and increment times_violated."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE principles
           SET times_violated = times_violated + 1,
               confidence = GREATEST(0.0, confidence - 0.1)
           WHERE id = $1
           RETURNING id, principle, category, source_events, confidence,
                     times_applied, times_violated, created_at, updated_at""",
        principle_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"Principle '{principle_id}' not found")
    return PrincipleOut(**dict(row))

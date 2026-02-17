from uuid import UUID
from fastapi import APIRouter
from ..db import get_pool
from ..models import SessionStart, SessionEnd, SessionOut

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionOut)
async def start_session(req: SessionStart):
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO sessions (session_type, metadata)
           VALUES ($1, $2)
           RETURNING id, session_type, started_at, ended_at, summary, key_decisions""",
        req.session_type, req.metadata,
    )
    return SessionOut(**dict(row))


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(session_id: UUID, req: SessionEnd):
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE sessions
           SET ended_at = now(), summary = $2, key_decisions = $3
           WHERE id = $1
           RETURNING id, session_type, started_at, ended_at, summary, key_decisions""",
        session_id, req.summary, req.key_decisions,
    )
    return SessionOut(**dict(row))


@router.get("/last", response_model=SessionOut | None)
async def last_session():
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, session_type, started_at, ended_at, summary, key_decisions
           FROM sessions WHERE ended_at IS NOT NULL
           ORDER BY ended_at DESC LIMIT 1""",
    )
    if row is None:
        return None
    return SessionOut(**dict(row))

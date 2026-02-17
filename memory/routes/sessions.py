from uuid import UUID
from fastapi import APIRouter
from ..db import get_pool
from ..models import SessionStart, SessionEnd, SessionOut
from ..graphiti import graphiti_ingest, make_message

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
    session = SessionOut(**dict(row))

    # Ingest session summary into Graphiti knowledge graph
    summary_text = req.summary
    if req.key_decisions:
        summary_text += "\nKey decisions: " + "; ".join(req.key_decisions)
    await graphiti_ingest("sessions", [
        make_message(summary_text, "system", "Otto", session.ended_at),
    ])

    return session


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

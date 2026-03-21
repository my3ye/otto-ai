import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from ..db import get_pool
from ..models import SessionStart, SessionOut, SessionEnd

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionOut)
async def start_session(req: SessionStart):
    """Start a new agent session. Returns a session ID to use in episodic events."""
    pool = await get_pool()
    agent_id = req.agent_id or "default"
    row = await pool.fetchrow(
        """INSERT INTO sessions (agent_id, context)
           VALUES ($1, $2::jsonb)
           RETURNING id, agent_id, started_at, ended_at, summary""",
        agent_id,
        req.context,
    )
    return SessionOut(**dict(row))


@router.post("/{session_id}/end", response_model=SessionOut)
async def end_session(session_id: str, req: SessionEnd):
    """End an active session and optionally store a summary."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE sessions
           SET ended_at = NOW(), summary = $1
           WHERE id = $2
           RETURNING id, agent_id, started_at, ended_at, summary""",
        req.summary, session_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut(**dict(row))


@router.get("/last", response_model=SessionOut)
async def get_last_session():
    """Get the most recently completed session."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, agent_id, started_at, ended_at, summary
           FROM sessions
           WHERE ended_at IS NOT NULL
           ORDER BY ended_at DESC
           LIMIT 1"""
    )
    if not row:
        raise HTTPException(status_code=404, detail="No completed sessions found")
    return SessionOut(**dict(row))

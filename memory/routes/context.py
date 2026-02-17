import httpx
from fastapi import APIRouter
from ..db import get_pool
from ..config import settings
from ..models import (
    ContextBriefing, SessionOut, SemanticMemoryOut,
    EpisodicEventOut, ProcedureOut,
)

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/briefing", response_model=ContextBriefing)
async def get_briefing(session_id: str | None = None):
    """Aggregate all memory layers into a single context briefing."""
    pool = await get_pool()

    # Current session (if provided)
    current_session = None
    if session_id:
        row = await pool.fetchrow(
            """SELECT id, session_type, started_at, ended_at, summary, key_decisions
               FROM sessions WHERE id = $1""",
            session_id,
        )
        if row:
            current_session = SessionOut(**dict(row))

    # Last completed session
    last_row = await pool.fetchrow(
        """SELECT id, session_type, started_at, ended_at, summary, key_decisions
           FROM sessions WHERE ended_at IS NOT NULL
           ORDER BY ended_at DESC LIMIT 1""",
    )
    last_session = SessionOut(**dict(last_row)) if last_row else None

    # Identity facts
    identity_rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at
           FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT 20""",
    )
    identity_facts = [SemanticMemoryOut(**dict(r)) for r in identity_rows]

    # High-confidence semantic facts
    fact_rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at
           FROM semantic_memories
           WHERE category != 'identity' AND confidence >= 0.7
           ORDER BY confidence DESC, updated_at DESC LIMIT 30""",
    )
    high_confidence_facts = [SemanticMemoryOut(**dict(r)) for r in fact_rows]

    # Recent important events
    event_rows = await pool.fetch(
        """SELECT id, session_id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE importance >= 5
           ORDER BY created_at DESC LIMIT 20""",
    )
    recent_events = [EpisodicEventOut(**dict(r)) for r in event_rows]

    # Active procedures
    proc_rows = await pool.fetch(
        """SELECT id, name, description, steps, success_count, failure_count, last_used, created_at
           FROM procedures ORDER BY last_used DESC NULLS LAST LIMIT 10""",
    )
    procedures = [ProcedureOut(**dict(r)) for r in proc_rows]

    # Graph context from Graphiti
    graph_context = {}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.graphiti_url}/healthcheck")
            if resp.status_code == 200:
                graph_context["status"] = "connected"
    except Exception:
        graph_context["status"] = "unavailable"

    return ContextBriefing(
        session=current_session,
        last_session=last_session,
        identity_facts=identity_facts,
        high_confidence_facts=high_confidence_facts,
        recent_events=recent_events,
        procedures=procedures,
        graph_context=graph_context,
    )

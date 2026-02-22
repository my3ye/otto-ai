"""Persistent reasoning chain across heartbeat cycles.

Each heartbeat writes a ReasoningEntry at the end of its cycle:
  - reasoning: WHY it made the choices it did
  - decisions: WHAT it decided to do
  - expected: WHAT it expects to happen next cycle

The NEXT heartbeat, before writing its own entry, updates the prior entry:
  - actual: what it actually observed
  - outcome_match: matched | partial | miss

This creates a feedback loop: decide → act → observe → calibrate → decide better.
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..models import ReasoningEntryCreate, ReasoningEntryOut, ReasoningOutcomeUpdate

router = APIRouter(prefix="/reasoning", tags=["reasoning-chain"])


@router.post("", response_model=ReasoningEntryOut, status_code=201)
async def create_reasoning_entry(body: ReasoningEntryCreate):
    """Write a reasoning entry at the end of a heartbeat cycle."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO reasoning_chain
               (heartbeat_type, reasoning, decisions, expected, metadata)
           VALUES ($1, $2, $3, $4, $5)
           RETURNING id, heartbeat_type, cycle_ts, reasoning, decisions,
                     expected, actual, outcome_match""",
        body.heartbeat_type,
        body.reasoning,
        body.decisions,
        body.expected,
        body.metadata,
    )
    return ReasoningEntryOut(**dict(row))


@router.get("/recent", response_model=list[ReasoningEntryOut])
async def get_recent_reasoning(
    limit: int = Query(default=5, ge=1, le=20),
    heartbeat_type: str | None = Query(default=None),
):
    """Return the most recent reasoning entries, newest first.

    Used by heartbeat context injection to reconstruct prior reasoning.
    """
    pool = await get_pool()
    if heartbeat_type:
        rows = await pool.fetch(
            """SELECT id, heartbeat_type, cycle_ts, reasoning, decisions,
                      expected, actual, outcome_match
               FROM reasoning_chain
               WHERE heartbeat_type = $1
               ORDER BY cycle_ts DESC LIMIT $2""",
            heartbeat_type, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, heartbeat_type, cycle_ts, reasoning, decisions,
                      expected, actual, outcome_match
               FROM reasoning_chain
               ORDER BY cycle_ts DESC LIMIT $1""",
            limit,
        )
    # Return oldest-first so the chain reads chronologically in context
    return [ReasoningEntryOut(**dict(r)) for r in reversed(rows)]


@router.get("/pending-outcome", response_model=ReasoningEntryOut | None)
async def get_pending_outcome(
    heartbeat_type: str = Query(default="orchestrator"),
):
    """Return the most recent entry that still has outcome_match = 'pending'.

    The next heartbeat should call PATCH /reasoning/{id}/outcome to close the loop.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, heartbeat_type, cycle_ts, reasoning, decisions,
                  expected, actual, outcome_match
           FROM reasoning_chain
           WHERE heartbeat_type = $1 AND outcome_match = 'pending'
           ORDER BY cycle_ts DESC LIMIT 1""",
        heartbeat_type,
    )
    if not row:
        return None
    return ReasoningEntryOut(**dict(row))


@router.patch("/{entry_id}/outcome", response_model=ReasoningEntryOut)
async def update_outcome(entry_id: UUID, body: ReasoningOutcomeUpdate):
    """Close the feedback loop: record what actually happened vs what was expected."""
    if body.outcome_match not in ("matched", "partial", "miss"):
        raise HTTPException(status_code=422, detail="outcome_match must be: matched | partial | miss")
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE reasoning_chain
           SET actual = $2, outcome_match = $3
           WHERE id = $1
           RETURNING id, heartbeat_type, cycle_ts, reasoning, decisions,
                     expected, actual, outcome_match""",
        entry_id, body.actual, body.outcome_match,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Reasoning entry not found")
    return ReasoningEntryOut(**dict(row))


@router.get("/{entry_id}", response_model=ReasoningEntryOut)
async def get_reasoning_entry(entry_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, heartbeat_type, cycle_ts, reasoning, decisions,
                  expected, actual, outcome_match
           FROM reasoning_chain WHERE id = $1""",
        entry_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return ReasoningEntryOut(**dict(row))

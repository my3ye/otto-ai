import json
import logging

from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..db import get_pool
from ..models import (
    PendingQuestionCreate, PendingQuestionOut, CrossBrainNote,
    DecisionProposalCreate, DecisionProposalOut, DecisionProposalResolve,
)

logger = logging.getLogger(__name__)


class ResolveQuestion(BaseModel):
    answer: str

router = APIRouter(prefix="/pending", tags=["pending"])


@router.post("/ask", response_model=PendingQuestionOut)
async def register_question(req: PendingQuestionCreate):
    """Register a question Otto is asking Admin. Called when heartbeat sends a WhatsApp question."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO pending_questions (question, intent, context, channel, direction, source_brain)
           VALUES ($1, $2, $3, $4, 'outbound', 'kernel')
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain""",
        req.question, req.intent, req.context, req.channel,
    )
    return PendingQuestionOut(**dict(row))


@router.get("/open", response_model=list[PendingQuestionOut])
async def get_open_questions(
    direction: str = Query(default=None, description="Filter by direction (omit for all)"),
):
    """Get all unresolved pending questions/notes, optionally filtered by direction."""
    pool = await get_pool()
    if direction:
        rows = await pool.fetch(
            """SELECT id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain
               FROM pending_questions
               WHERE resolved_at IS NULL AND direction = $1
               ORDER BY asked_at DESC""",
            direction,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain
               FROM pending_questions
               WHERE resolved_at IS NULL
               ORDER BY asked_at DESC""",
        )
    return [PendingQuestionOut(**dict(r)) for r in rows]


@router.post("/note", response_model=PendingQuestionOut, deprecated=True)
async def create_cross_brain_note(req: CrossBrainNote):
    """Deprecated: dual-brain artifact. Use kernel interrupts (POST /kernel/interrupt) instead.

    Kept for backward compatibility — creates a pending question entry."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO pending_questions
               (question, intent, context, channel, direction, source_brain, metadata)
           VALUES ($1, $2, $3, 'whatsapp', 'inbound', 'kernel', $4)
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain""",
        req.content,
        req.note_type,
        req.source_summary,
        json.dumps({"urgency": req.urgency}),
    )
    return PendingQuestionOut(**dict(row))


@router.post("/{question_id}/resolve", response_model=PendingQuestionOut)
async def resolve_question(question_id: str, req: ResolveQuestion):
    """Mark a pending question/note as resolved with the given answer."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE pending_questions
           SET resolved_at = now(), answer = $2
           WHERE id = $1
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain""",
        question_id, req.answer,
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Question not found")
    return PendingQuestionOut(**dict(row))


# ── Decision Proposals (Collaboration Framework) ─────────────────────────────

@router.post("/propose", response_model=DecisionProposalOut)
async def create_proposal(req: DecisionProposalCreate):
    """Create a structured decision proposal for Mev.

    Otto presents options with a recommendation; Mev resolves via WhatsApp or API.
    """
    pool = await get_pool()
    options_json = json.dumps([opt.model_dump() for opt in req.options])
    row = await pool.fetchrow(
        """INSERT INTO decision_proposals
               (question, context, options, recommendation, recommendation_reason,
                source, source_task_id, urgency)
           VALUES ($1, $2, $3::jsonb, $4, $5, $6, $7, $8)
           RETURNING *""",
        req.question, req.context, options_json,
        req.recommendation, req.recommendation_reason,
        req.source, str(req.source_task_id) if req.source_task_id else None,
        req.urgency,
    )
    result = dict(row)
    if isinstance(result.get("options"), str):
        result["options"] = json.loads(result["options"])
    logger.info(f"Proposal created: {req.question[:80]} (urgency={req.urgency})")
    return DecisionProposalOut(**result)


@router.get("/proposals", response_model=list[DecisionProposalOut])
async def list_proposals(
    status: str = Query(default="open", description="Filter by status: open, resolved, all"),
):
    """List decision proposals, filtered by status."""
    pool = await get_pool()
    if status == "all":
        rows = await pool.fetch(
            "SELECT * FROM decision_proposals ORDER BY created_at DESC LIMIT 50"
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM decision_proposals WHERE status = $1 ORDER BY created_at DESC LIMIT 50",
            status,
        )
    results = []
    for r in rows:
        d = dict(r)
        if isinstance(d.get("options"), str):
            d["options"] = json.loads(d["options"])
        results.append(DecisionProposalOut(**d))
    return results


@router.post("/proposals/{proposal_id}/resolve", response_model=DecisionProposalOut)
async def resolve_proposal(proposal_id: str, req: DecisionProposalResolve):
    """Resolve a decision proposal with Mev's answer."""
    pool = await get_pool()

    # Resolve the proposal
    row = await pool.fetchrow(
        """UPDATE decision_proposals
           SET status = 'resolved', resolution = $2, resolved_at = NOW()
           WHERE id = $1
           RETURNING *""",
        proposal_id, req.resolution,
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found")

    result = dict(row)
    if isinstance(result.get("options"), str):
        result["options"] = json.loads(result["options"])

    # Store resolution as semantic memory for future context
    question = result["question"]
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance, metadata)
           VALUES ($1, 'decision', 7, $2::jsonb)""",
        f"Mev resolved proposal: {question} → {req.resolution}",
        json.dumps({"proposal_id": proposal_id, "source": result.get("source")}),
    )

    logger.info(f"Proposal resolved: {question[:80]} → {req.resolution[:80]}")
    return DecisionProposalOut(**result)

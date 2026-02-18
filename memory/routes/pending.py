from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..db import get_pool
from ..models import PendingQuestionCreate, PendingQuestionOut, CrossBrainNote


class ResolveQuestion(BaseModel):
    answer: str

router = APIRouter(prefix="/pending", tags=["pending"])


@router.post("/ask", response_model=PendingQuestionOut)
async def register_question(req: PendingQuestionCreate):
    """Register a question Otto is asking Admin. Called when heartbeat sends a WhatsApp question."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO pending_questions (question, intent, context, channel, direction, source_brain)
           VALUES ($1, $2, $3, $4, 'claude_to_gemini', 'claude')
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain""",
        req.question, req.intent, req.context, req.channel,
    )
    return PendingQuestionOut(**dict(row))


@router.get("/open", response_model=list[PendingQuestionOut])
async def get_open_questions(
    direction: str = Query(default="claude_to_gemini", description="Filter by direction"),
):
    """Get all unresolved pending questions/notes, filtered by direction."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain
           FROM pending_questions
           WHERE resolved_at IS NULL AND direction = $1
           ORDER BY asked_at DESC""",
        direction,
    )
    return [PendingQuestionOut(**dict(r)) for r in rows]


@router.post("/note", response_model=PendingQuestionOut)
async def create_cross_brain_note(req: CrossBrainNote):
    """Gemini creates a cross-brain note for Claude to process during heartbeat."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO pending_questions
               (question, intent, context, channel, direction, source_brain, metadata)
           VALUES ($1, $2, $3, 'whatsapp', 'gemini_to_claude', 'gemini', $4)
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer, direction, source_brain""",
        req.content,
        req.note_type,
        req.source_summary,
        '{"urgency": "' + req.urgency + '"}',
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
    return PendingQuestionOut(**dict(row))

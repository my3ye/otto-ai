from fastapi import APIRouter
from pydantic import BaseModel
from ..db import get_pool
from ..models import PendingQuestionCreate, PendingQuestionOut


class ResolveQuestion(BaseModel):
    answer: str

router = APIRouter(prefix="/pending", tags=["pending"])


@router.post("/ask", response_model=PendingQuestionOut)
async def register_question(req: PendingQuestionCreate):
    """Register a question Otto is asking Admin. Called when heartbeat sends a WhatsApp question."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO pending_questions (question, intent, context, channel)
           VALUES ($1, $2, $3, $4)
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer""",
        req.question, req.intent, req.context, req.channel,
    )
    return PendingQuestionOut(**dict(row))


@router.get("/open", response_model=list[PendingQuestionOut])
async def get_open_questions():
    """Get all unresolved pending questions."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, question, intent, context, channel, asked_at, resolved_at, answer
           FROM pending_questions
           WHERE resolved_at IS NULL
           ORDER BY asked_at DESC""",
    )
    return [PendingQuestionOut(**dict(r)) for r in rows]


@router.post("/{question_id}/resolve", response_model=PendingQuestionOut)
async def resolve_question(question_id: str, req: ResolveQuestion):
    """Mark a pending question as resolved with the given answer."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE pending_questions
           SET resolved_at = now(), answer = $2
           WHERE id = $1
           RETURNING id, question, intent, context, channel, asked_at, resolved_at, answer""",
        question_id, req.answer,
    )
    return PendingQuestionOut(**dict(row))

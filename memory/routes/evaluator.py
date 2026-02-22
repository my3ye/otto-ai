"""TAME-inspired evaluator memory routes.

Dual-memory architecture from TAME (arXiv:2602.03224):
- Executor memory: generalizable task methodologies → semantic_memories table
- Evaluator memory: safety/utility assessments from historical feedback → evaluator_memories table

The evaluator brain guards quality by surfacing relevant past failure modes and
performance patterns when the reflection agent reviews completed task results.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID

from ..db import get_pool

router = APIRouter(prefix="/evaluator", tags=["evaluator"])


# ── Models ────────────────────────────────────────────────────────

class EvaluatorMemoryCreate(BaseModel):
    category: str = Field(..., description="quality_check | safety_flag | performance_pattern | failure_mode")
    criterion: str = Field(..., description="The rule/pattern being captured")
    evidence: str = Field(..., description="Concrete observed evidence supporting this criterion")
    confidence: float = Field(0.7, ge=0.0, le=1.0)


class EvaluatorMemoryOut(BaseModel):
    id: UUID
    category: str
    criterion: str
    evidence: str
    confidence: float
    times_triggered: int
    times_confirmed: int
    created_at: str

    class Config:
        from_attributes = True


class EvaluatorSearchRequest(BaseModel):
    text: str = Field(..., description="Task result summary or context to check against evaluator memories")
    category: Optional[str] = Field(None, description="Filter by category (optional)")
    min_confidence: float = Field(0.5, ge=0.0, le=1.0)
    limit: int = Field(5, ge=1, le=20)


class EvaluatorCheckResult(BaseModel):
    flags: list[EvaluatorMemoryOut]
    flag_count: int
    highest_confidence: float
    summary: str


# ── Helpers ───────────────────────────────────────────────────────

def _row_to_out(row) -> EvaluatorMemoryOut:
    return EvaluatorMemoryOut(
        id=row["id"],
        category=row["category"],
        criterion=row["criterion"],
        evidence=row["evidence"],
        confidence=float(row["confidence"]),
        times_triggered=int(row["times_triggered"]),
        times_confirmed=int(row["times_confirmed"]),
        created_at=row["created_at"].isoformat(),
    )


def _keyword_relevance(text: str, criterion: str, evidence: str) -> float:
    """Simple keyword overlap score for evaluator memory matching.
    Returns 0.0-1.0. Used for lightweight retrieval without embeddings.
    """
    text_lower = text.lower()
    words = set(text_lower.split())

    # Extract meaningful words from criterion + evidence (skip stop words)
    stop = {"a", "an", "the", "is", "are", "was", "were", "and", "or", "but",
            "in", "on", "at", "to", "for", "of", "with", "by", "from", "as",
            "this", "that", "it", "its", "be", "been", "have", "has", "had",
            "not", "no", "when", "if", "then", "always", "usually", "often"}
    combined = (criterion + " " + evidence).lower()
    pattern_words = {w for w in combined.split() if len(w) > 4 and w not in stop}

    if not pattern_words:
        return 0.0

    overlap = words & pattern_words
    return len(overlap) / len(pattern_words)


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/store", response_model=EvaluatorMemoryOut)
async def store_evaluator_memory(req: EvaluatorMemoryCreate):
    """Store a new evaluator memory (quality pattern or failure mode observed during reflection)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO evaluator_memories (category, criterion, evidence, confidence)
           VALUES ($1, $2, $3, $4)
           RETURNING id, category, criterion, evidence, confidence,
                     times_triggered, times_confirmed, created_at""",
        req.category, req.criterion, req.evidence, req.confidence,
    )
    return _row_to_out(row)


@router.post("/search", response_model=list[EvaluatorMemoryOut])
async def search_evaluator_memories(req: EvaluatorSearchRequest):
    """Search evaluator memories by category and/or text relevance.
    Returns memories ranked by confidence that might be relevant to the given context.
    """
    pool = await get_pool()

    if req.category:
        rows = await pool.fetch(
            """SELECT id, category, criterion, evidence, confidence,
                      times_triggered, times_confirmed, created_at
               FROM evaluator_memories
               WHERE category = $1 AND confidence >= $2
               ORDER BY confidence DESC
               LIMIT $3""",
            req.category, req.min_confidence, req.limit * 3,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, category, criterion, evidence, confidence,
                      times_triggered, times_confirmed, created_at
               FROM evaluator_memories
               WHERE confidence >= $1
               ORDER BY confidence DESC
               LIMIT $2""",
            req.min_confidence, req.limit * 3,
        )

    # Re-rank by keyword relevance to the input text
    scored = []
    for row in rows:
        relevance = _keyword_relevance(req.text, row["criterion"], row["evidence"])
        scored.append((relevance, row))

    scored.sort(key=lambda x: (x[0], float(x[1]["confidence"])), reverse=True)
    top = scored[: req.limit]

    return [_row_to_out(row) for _, row in top]


@router.post("/check", response_model=EvaluatorCheckResult)
async def check_task_result(req: EvaluatorSearchRequest):
    """Given a task result summary, return matching evaluator memories that flag quality issues.
    This is the core TAME dual-memory quality guard — call this during reflection after each task review.
    """
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, category, criterion, evidence, confidence,
                  times_triggered, times_confirmed, created_at
           FROM evaluator_memories
           WHERE confidence >= $1
           ORDER BY confidence DESC
           LIMIT 50""",
        req.min_confidence,
    )

    # Score all evaluator memories against the task result text
    scored = []
    for row in rows:
        relevance = _keyword_relevance(req.text, row["criterion"], row["evidence"])
        if relevance >= 0.05:  # minimal threshold to avoid random noise
            scored.append((relevance, row))

    scored.sort(key=lambda x: (x[0], float(x[1]["confidence"])), reverse=True)
    flags = scored[: req.limit]

    if not flags:
        return EvaluatorCheckResult(
            flags=[],
            flag_count=0,
            highest_confidence=0.0,
            summary="No evaluator flags raised — result appears clean.",
        )

    flag_rows = [_row_to_out(row) for _, row in flags]
    highest_conf = max(float(row["confidence"]) for _, row in flags)

    # Increment times_triggered for matched memories
    matched_ids = [row["id"] for _, row in flags]
    await pool.execute(
        "UPDATE evaluator_memories SET times_triggered = times_triggered + 1 WHERE id = ANY($1::uuid[])",
        matched_ids,
    )

    # Build summary
    categories = list({row["category"] for _, row in flags})
    summary = f"{len(flags)} evaluator flag(s) raised [{', '.join(categories)}]. Top: {flags[0][1]['criterion'][:120]}..."

    return EvaluatorCheckResult(
        flags=flag_rows,
        flag_count=len(flags),
        highest_confidence=highest_conf,
        summary=summary,
    )


@router.get("", response_model=list[EvaluatorMemoryOut])
async def list_evaluator_memories(
    category: Optional[str] = None,
    min_confidence: float = 0.0,
    limit: int = 50,
):
    """List all evaluator memories, optionally filtered by category."""
    pool = await get_pool()
    if category:
        rows = await pool.fetch(
            """SELECT id, category, criterion, evidence, confidence,
                      times_triggered, times_confirmed, created_at
               FROM evaluator_memories
               WHERE category = $1 AND confidence >= $2
               ORDER BY confidence DESC LIMIT $3""",
            category, min_confidence, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, category, criterion, evidence, confidence,
                      times_triggered, times_confirmed, created_at
               FROM evaluator_memories
               WHERE confidence >= $1
               ORDER BY confidence DESC LIMIT $2""",
            min_confidence, limit,
        )
    return [_row_to_out(row) for row in rows]


@router.put("/{memory_id}/confirmed", response_model=EvaluatorMemoryOut)
async def record_confirmed(memory_id: UUID):
    """Mark that this evaluator memory was confirmed accurate — boosts confidence."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE evaluator_memories
           SET times_confirmed = times_confirmed + 1,
               confidence = LEAST(1.0, confidence + 0.05),
               updated_at = NOW()
           WHERE id = $1
           RETURNING id, category, criterion, evidence, confidence,
                     times_triggered, times_confirmed, created_at""",
        memory_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluator memory not found")
    return _row_to_out(row)


@router.put("/{memory_id}/refuted", response_model=EvaluatorMemoryOut)
async def record_refuted(memory_id: UUID):
    """Mark that this evaluator memory was wrong — reduces confidence."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE evaluator_memories
           SET confidence = GREATEST(0.0, confidence - 0.1),
               updated_at = NOW()
           WHERE id = $1
           RETURNING id, category, criterion, evidence, confidence,
                     times_triggered, times_confirmed, created_at""",
        memory_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluator memory not found")
    return _row_to_out(row)

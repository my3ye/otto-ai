"""RL2F: Reinforcement Learning from Teacher Feedback.

Two feedback layers:
  1. Heartbeat-level teacher critiques (Abhidharma framework) — rl2f_feedback table
     Used by teacher_loop.sh and the model fine-tuning pipeline.
  2. Task-level retry feedback chain (Phase 2) — task_retry_feedback table
     Tracks QA rejections → retry task → outcome per task. Enables:
     - Feedback injection into retry prompts (RL2F paper §3 student-teacher loop)
     - Retry success rate metrics: with vs without structured feedback
     - Training signal: rejection → feedback → success/failure turns

Used by:
  - teacher_loop.sh: stores heartbeat-level feedback after each cycle
  - qa_runner.sh: stores task rejection + structured feedback (Phase 2)
  - task_runner.sh: marks feedback_injected + updates outcome on retry (Phase 2)
  - extract_rl2f_data.py: pulls untrained entries for next training batch
  - format_rl2f_training.py: formats into Citta Vithi training dialogues
"""

from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..models import (
    RL2FFeedbackCreate, RL2FFeedbackOut, RL2FTrainingBatch,
    TaskRetryFeedbackCreate, TaskRetryFeedbackOut, TaskRetryFeedbackResolve,
    RetryMetrics, QAFeedbackCreate,
)

router = APIRouter(prefix="/rl2f", tags=["rl2f-feedback"])


@router.post("", response_model=RL2FFeedbackOut, status_code=201)
async def create_feedback(body: RL2FFeedbackCreate):
    """Store a teacher feedback entry after a heartbeat cycle."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO rl2f_feedback
               (cycle_ts, heartbeat_type, system_state, decision,
                teacher_feedback, root_condition_analysis, mental_factor_scores,
                outcome, outcome_match)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           RETURNING id, cycle_ts, heartbeat_type, system_state, decision,
                     teacher_feedback, root_condition_analysis, mental_factor_scores,
                     outcome, outcome_match, used_in_training, created_at""",
        body.cycle_ts,
        body.heartbeat_type,
        body.system_state,
        body.decision,
        body.teacher_feedback,
        body.root_condition_analysis,
        body.mental_factor_scores,
        body.outcome,
        body.outcome_match,
    )
    return RL2FFeedbackOut(**dict(row))


@router.get("/recent", response_model=list[RL2FFeedbackOut])
async def get_recent_feedback(
    limit: int = Query(default=10, ge=1, le=50),
    heartbeat_type: str | None = Query(default=None),
):
    """Return the most recent feedback entries."""
    pool = await get_pool()
    if heartbeat_type:
        rows = await pool.fetch(
            """SELECT id, cycle_ts, heartbeat_type, system_state, decision,
                      teacher_feedback, root_condition_analysis, mental_factor_scores,
                      outcome, outcome_match, used_in_training, created_at
               FROM rl2f_feedback
               WHERE heartbeat_type = $1
               ORDER BY cycle_ts DESC LIMIT $2""",
            heartbeat_type, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, cycle_ts, heartbeat_type, system_state, decision,
                      teacher_feedback, root_condition_analysis, mental_factor_scores,
                      outcome, outcome_match, used_in_training, created_at
               FROM rl2f_feedback
               ORDER BY cycle_ts DESC LIMIT $1""",
            limit,
        )
    return [RL2FFeedbackOut(**dict(r)) for r in rows]


@router.get("/untrained", response_model=RL2FTrainingBatch)
async def get_untrained_feedback(
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return feedback entries not yet used in training — for the next training batch."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, cycle_ts, heartbeat_type, system_state, decision,
                  teacher_feedback, root_condition_analysis, mental_factor_scores,
                  outcome, outcome_match, used_in_training, created_at
           FROM rl2f_feedback
           WHERE used_in_training = FALSE
             AND teacher_feedback IS NOT NULL
           ORDER BY created_at ASC LIMIT $1""",
        limit,
    )
    entries = [RL2FFeedbackOut(**dict(r)) for r in rows]
    return RL2FTrainingBatch(entries=entries, count=len(entries))


@router.post("/mark-trained", status_code=200)
async def mark_as_trained(ids: list[UUID]):
    """Mark feedback entries as used in training after a training run."""
    if not ids:
        raise HTTPException(status_code=422, detail="Must provide at least one ID")
    pool = await get_pool()
    count = await pool.execute(
        """UPDATE rl2f_feedback
           SET used_in_training = TRUE
           WHERE id = ANY($1::uuid[])""",
        ids,
    )
    return {"marked": len(ids), "status": "ok"}


@router.patch("/{entry_id}/outcome", response_model=RL2FFeedbackOut)
async def update_outcome(entry_id: UUID, outcome: str, outcome_match: str):
    """Update an entry's outcome after observing results."""
    if outcome_match not in ("matched", "partial", "miss"):
        raise HTTPException(status_code=422, detail="outcome_match must be: matched | partial | miss")
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE rl2f_feedback
           SET outcome = $2, outcome_match = $3
           WHERE id = $1
           RETURNING id, cycle_ts, heartbeat_type, system_state, decision,
                     teacher_feedback, root_condition_analysis, mental_factor_scores,
                     outcome, outcome_match, used_in_training, created_at""",
        entry_id, outcome, outcome_match,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Feedback entry not found")
    return RL2FFeedbackOut(**dict(row))


@router.get("/stats")
async def feedback_stats():
    """Summary statistics for the RL2F feedback table."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT
               COUNT(*) as total,
               COUNT(*) FILTER (WHERE used_in_training) as trained,
               COUNT(*) FILTER (WHERE NOT used_in_training AND teacher_feedback IS NOT NULL) as untrained_ready,
               COUNT(*) FILTER (WHERE teacher_feedback IS NULL) as awaiting_feedback,
               COUNT(*) FILTER (WHERE outcome_match = 'matched') as matched,
               COUNT(*) FILTER (WHERE outcome_match = 'partial') as partial,
               COUNT(*) FILTER (WHERE outcome_match = 'miss') as miss,
               AVG((root_condition_analysis->>'amoha_score')::float)
                   FILTER (WHERE root_condition_analysis IS NOT NULL) as avg_amoha,
               AVG((mental_factor_scores->>'sati')::float)
                   FILTER (WHERE mental_factor_scores IS NOT NULL) as avg_sati
           FROM rl2f_feedback"""
    )
    return dict(row)


# ── Phase 2: Task-level Retry Feedback Chain ──────────────────────
# Note: All fixed-path Phase 2 routes registered BEFORE /{entry_id} to prevent
# route shadowing (FastAPI matches in registration order).

def _parse_trf_row(row) -> "TaskRetryFeedbackOut":
    """Convert asyncpg row to TaskRetryFeedbackOut, parsing JSONB feedback field."""
    import json as _json
    d = dict(row)
    # asyncpg returns JSONB columns as str; Pydantic expects dict
    if isinstance(d.get("feedback"), str):
        d["feedback"] = _json.loads(d["feedback"])
    return TaskRetryFeedbackOut(**d)


@router.post("/task-feedback", response_model=TaskRetryFeedbackOut, status_code=201)
async def create_task_feedback(body: TaskRetryFeedbackCreate):
    """Store a task rejection feedback turn.
    Called by qa_runner.sh when a task is rejected.
    Returns the feedback ID so it can be linked to the retry task.
    """
    import json as _json
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO task_retry_feedback
               (original_task_id, retry_task_id, attempt_number, feedback,
                qa_rejection_reason, feedback_injected, outcome)
           VALUES ($1, $2, $3, $4, $5, $6, 'pending')
           RETURNING id, original_task_id, retry_task_id, attempt_number,
                     feedback, qa_rejection_reason, feedback_injected,
                     outcome, outcome_details, created_at, resolved_at""",
        body.original_task_id,
        body.retry_task_id,
        body.attempt_number,
        _json.dumps(body.feedback),
        body.qa_rejection_reason,
        body.feedback_injected,
    )
    return _parse_trf_row(row)


@router.patch("/task-feedback/{feedback_id}/resolve", response_model=TaskRetryFeedbackOut)
async def resolve_task_feedback(feedback_id: UUID, body: TaskRetryFeedbackResolve):
    """Update the outcome of a feedback turn after the retry task completes.
    Called by task_runner.sh (or qa_runner.sh) when a retry is approved or fails.
    Also used to link the retry_task_id if it was not set at creation.
    """
    if body.outcome not in ("succeeded", "failed", "abandoned"):
        raise HTTPException(
            status_code=422,
            detail="outcome must be: succeeded | failed | abandoned",
        )
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE task_retry_feedback
           SET outcome = $2,
               outcome_details = COALESCE($3, outcome_details),
               retry_task_id   = COALESCE($4, retry_task_id),
               resolved_at     = now()
           WHERE id = $1
           RETURNING id, original_task_id, retry_task_id, attempt_number,
                     feedback, qa_rejection_reason, feedback_injected,
                     outcome, outcome_details, created_at, resolved_at""",
        feedback_id,
        body.outcome,
        body.outcome_details,
        body.retry_task_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Feedback entry not found")
    return _parse_trf_row(row)


@router.patch("/task-feedback/{feedback_id}/mark-injected", response_model=TaskRetryFeedbackOut)
async def mark_feedback_injected(feedback_id: UUID, retry_task_id: UUID | None = None):
    """Mark that this feedback was injected into the retry prompt.
    Called by task_runner.sh when RL2F feedback block is built.
    Optionally links the retry_task_id at this point.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE task_retry_feedback
           SET feedback_injected = TRUE,
               retry_task_id = COALESCE($2, retry_task_id)
           WHERE id = $1
           RETURNING id, original_task_id, retry_task_id, attempt_number,
                     feedback, qa_rejection_reason, feedback_injected,
                     outcome, outcome_details, created_at, resolved_at""",
        feedback_id,
        retry_task_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Feedback entry not found")
    return _parse_trf_row(row)


@router.get("/feedback/{task_id}", response_model=list[TaskRetryFeedbackOut])
async def get_task_feedback_chain(task_id: UUID):
    """Retrieve the full feedback chain for a task.
    Returns all rejection turns where this task was the original (rejected) task,
    ordered by attempt_number ascending — the full learning dialogue.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, original_task_id, retry_task_id, attempt_number,
                  feedback, qa_rejection_reason, feedback_injected,
                  outcome, outcome_details, created_at, resolved_at
           FROM task_retry_feedback
           WHERE original_task_id = $1
           ORDER BY attempt_number ASC""",
        task_id,
    )
    return [_parse_trf_row(r) for r in rows]


@router.get("/retry-metrics", response_model=RetryMetrics)
async def get_retry_metrics():
    """Return retry success rate with vs without structured feedback injection.

    Compares two populations:
    - Retries WHERE feedback_injected = TRUE (RL2F active)
    - Retries WHERE feedback_injected = FALSE (baseline, no structured feedback)

    This measures whether RL2F feedback actually improves retry success rates.
    From RL2F paper (arXiv 2602.16066): structured NL feedback should improve
    student performance over baseline retries.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT
               COUNT(*) as total_rejections,
               COUNT(*) FILTER (WHERE retry_task_id IS NOT NULL) as total_retries,
               COUNT(*) FILTER (WHERE feedback_injected = TRUE) as retries_with_feedback,
               COUNT(*) FILTER (WHERE feedback_injected = FALSE AND retry_task_id IS NOT NULL) as retries_without_feedback,
               COUNT(*) FILTER (WHERE feedback_injected = TRUE AND outcome = 'succeeded') as success_with_feedback,
               COUNT(*) FILTER (WHERE feedback_injected = FALSE AND outcome = 'succeeded') as success_without_feedback,
               COUNT(*) FILTER (WHERE outcome = 'pending') as pending_outcomes
           FROM task_retry_feedback"""
    )
    d = dict(row)

    # Compute success rates (avoid division by zero)
    rwf = d["retries_with_feedback"] or 0
    rwof = d["retries_without_feedback"] or 0
    swf = d["success_with_feedback"] or 0
    swof = d["success_without_feedback"] or 0

    rate_with = round(swf / rwf, 3) if rwf > 0 else 0.0
    rate_without = round(swof / rwof, 3) if rwof > 0 else 0.0
    delta = round(rate_with - rate_without, 3)

    return RetryMetrics(
        total_rejections=d["total_rejections"],
        total_retries=d["total_retries"],
        retries_with_feedback=rwf,
        retries_without_feedback=rwof,
        success_with_feedback=swf,
        success_without_feedback=swof,
        success_rate_with_feedback=rate_with,
        success_rate_without_feedback=rate_without,
        improvement_delta=delta,
        pending_outcomes=d["pending_outcomes"],
    )


# ── QA Feedback Bridge ──────────────────────────────────────────────────────
# Simple endpoint for qa_runner.sh to log every QA decision as RL2F training signal.
# Converts task QA outcomes (approve/reject) into rl2f_feedback table records.
# This closes the learning loop: every QA decision becomes a teacher feedback entry.

@router.post("/feedback", response_model=RL2FFeedbackOut, status_code=201)
async def create_qa_feedback(body: QAFeedbackCreate):
    """Store a QA decision as RL2F training signal.

    Called by qa_runner.sh after every QA decision (APPROVE or REJECT).
    Maps task QA outcomes into the rl2f_feedback table so they can be
    used as training data for the model fine-tuning pipeline.

    Mapping:
      heartbeat_type = "qa"
      system_state   = task_id + task_title + output excerpt
      decision       = task_title (the action that was evaluated)
      teacher_feedback = feedback_text (the QA reviewer's assessment)
      outcome        = approved | rejected
      outcome_match  = matched (if approved) | miss (if rejected)
    """
    now = datetime.now(timezone.utc)
    outcome_match = "matched" if body.outcome == "approved" else "miss"

    # Build system_state: task context for training record
    state_parts = [f"task_id:{body.task_id}"]
    if body.task_title:
        state_parts.append(f"title:{body.task_title}")
    if body.task_output:
        state_parts.append(f"output_excerpt:{body.task_output[:300]}")
    system_state = " | ".join(state_parts)

    decision = body.task_title or f"task:{body.task_id[:8]}"

    # Include QA reviewer in feedback text for provenance
    reviewer_note = f"[qa_reviewer:{body.qa_reviewer}] " if body.qa_reviewer else ""
    teacher_feedback = f"{reviewer_note}{body.feedback_text}"

    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO rl2f_feedback
               (cycle_ts, heartbeat_type, system_state, decision,
                teacher_feedback, outcome, outcome_match)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           RETURNING id, cycle_ts, heartbeat_type, system_state, decision,
                     teacher_feedback, root_condition_analysis, mental_factor_scores,
                     outcome, outcome_match, used_in_training, created_at""",
        now, "qa", system_state, decision,
        teacher_feedback, body.outcome, outcome_match,
    )
    return RL2FFeedbackOut(**dict(row))


# ── IMPORTANT: Wildcard route LAST — must come after all fixed-path routes ──
# Moving /{entry_id} here prevents it from shadowing /retry-metrics, /feedback/*, etc.

@router.get("/{entry_id}", response_model=RL2FFeedbackOut)
async def get_feedback_entry(entry_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, cycle_ts, heartbeat_type, system_state, decision,
                  teacher_feedback, root_condition_analysis, mental_factor_scores,
                  outcome, outcome_match, used_in_training, created_at
           FROM rl2f_feedback WHERE id = $1""",
        entry_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Not found")
    return RL2FFeedbackOut(**dict(row))

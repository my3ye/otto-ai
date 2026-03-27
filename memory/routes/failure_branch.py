"""Failure-Branch Adaptation API routes.

Hooks into the RL2F feedback loop to provide in-task failure detection,
root-cause analysis, correction, and retest validation.

Endpoints:
  POST /failure-branch/detect     — scan task output for failure signals
  POST /failure-branch/correct    — LLM root-cause analysis + prompt adjustment
  POST /failure-branch/retest     — validate correction resolved the failure
  GET  /failure-branch/history    — adaptation history (optionally by task_id)
  GET  /failure-branch/stats      — aggregate adaptation metrics
"""

from uuid import UUID
from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..models import (
    FailureBranchDetectRequest,
    FailureBranchDetectResult,
    FailureBranchCorrectRequest,
    FailureBranchCorrectResult,
    FailureBranchRetestRequest,
    FailureBranchAdaptationOut,
)
from ..failure_branch import detect_failure, analyze_root_cause, validate_retest

router = APIRouter(prefix="/failure-branch", tags=["failure-branch"])


@router.post("/detect", response_model=FailureBranchDetectResult)
async def detect(body: FailureBranchDetectRequest):
    """Scan task output for failure signals.

    Returns detection result with failure type and confidence.
    If detected, creates a record in the adaptations table.
    Does NOT modify existing RL2F feedback — additive only.
    """
    result = detect_failure(
        task_output=body.task_output,
        exit_code=body.exit_code,
        task_metadata=body.task_metadata,
    )

    if result.detected:
        pool = await get_pool()
        await pool.execute(
            """INSERT INTO failure_branch_adaptations
                   (task_id, agent_type, failure_type, failure_signal, confidence, status)
               VALUES ($1, $2, $3, $4, $5, 'detected')""",
            body.task_id,
            body.agent_type,
            result.failure_type,
            result.failure_signal,
            result.confidence,
        )

    return FailureBranchDetectResult(
        detected=result.detected,
        failure_type=result.failure_type,
        failure_signal=result.failure_signal,
        confidence=result.confidence,
    )


@router.post("/correct", response_model=FailureBranchCorrectResult)
async def correct(body: FailureBranchCorrectRequest):
    """Run root-cause analysis and generate corrected approach.

    Updates the most recent adaptation record for this task, or creates one.
    Returns the corrected prompt with failure-branch instructions prepended.
    """
    pool = await get_pool()

    # Update status to analyzing
    row = await pool.fetchrow(
        """UPDATE failure_branch_adaptations
           SET status = 'analyzing'
           WHERE task_id = $1 AND status = 'detected'
           RETURNING id""",
        body.task_id,
    )

    # If no detected record, create one
    adaptation_id = row["id"] if row else None
    if not adaptation_id:
        new_row = await pool.fetchrow(
            """INSERT INTO failure_branch_adaptations
                   (task_id, agent_type, failure_type, failure_signal, confidence,
                    attempt_number, status)
               VALUES ($1, $2, $3, $4, 0.5, $5, 'analyzing')
               RETURNING id""",
            body.task_id,
            body.agent_type,
            body.failure_type,
            body.failure_signal,
            body.attempt_number,
        )
        adaptation_id = new_row["id"]

    # Run LLM root-cause analysis
    analysis = await analyze_root_cause(
        failure_type=body.failure_type,
        failure_signal=body.failure_signal,
        original_prompt=body.original_prompt,
        task_output=body.task_output,
    )

    # Store results
    await pool.execute(
        """UPDATE failure_branch_adaptations
           SET root_cause = $2,
               root_cause_category = $3,
               correction_strategy = $4,
               corrected_prompt = $5,
               status = 'correcting',
               attempt_number = $6
           WHERE id = $1""",
        adaptation_id,
        analysis.root_cause,
        analysis.category,
        analysis.correction_strategy,
        analysis.corrected_prompt[:10000],  # cap storage
        body.attempt_number,
    )

    return FailureBranchCorrectResult(
        root_cause=analysis.root_cause,
        root_cause_category=analysis.category,
        correction_strategy=analysis.correction_strategy,
        corrected_prompt=analysis.corrected_prompt,
    )


@router.post("/retest", response_model=FailureBranchAdaptationOut)
async def retest(body: FailureBranchRetestRequest):
    """Record retest results for a correction.

    Validates the correction and updates the adaptation record.
    Links back to the RL2F feedback chain via task_id.
    """
    pool = await get_pool()

    # Get the adaptation to know its failure type
    adapt_row = await pool.fetchrow(
        """SELECT failure_type FROM failure_branch_adaptations WHERE id = $1""",
        body.adaptation_id,
    )
    if not adapt_row:
        raise HTTPException(status_code=404, detail="Adaptation not found")

    original_failure_type = adapt_row["failure_type"]

    # Validate retest
    retest_result = validate_retest(
        retest_output=body.retest_output,
        retest_passed=body.retest_passed,
        original_failure_type=original_failure_type,
    )

    # Update record
    new_status = "resolved" if retest_result.passed else "failed"
    row = await pool.fetchrow(
        """UPDATE failure_branch_adaptations
           SET retest_passed = $2,
               retest_details = $3,
               status = $4,
               resolved_at = CASE WHEN $4 IN ('resolved', 'failed') THEN now() ELSE NULL END
           WHERE id = $1
           RETURNING id, task_id, agent_type, failure_type, failure_signal, confidence,
                     root_cause, root_cause_category, correction_strategy,
                     corrected_prompt, retest_passed, retest_details,
                     status, attempt_number, created_at, resolved_at""",
        body.adaptation_id,
        retest_result.passed,
        retest_result.details,
        new_status,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Adaptation not found")

    return FailureBranchAdaptationOut(**dict(row))


@router.get("/history", response_model=list[FailureBranchAdaptationOut])
async def get_history(
    task_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get adaptation history, optionally filtered by task or status."""
    pool = await get_pool()
    conditions = []
    params: list = []
    idx = 1

    if task_id:
        conditions.append(f"task_id = ${idx}")
        params.append(task_id)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = await pool.fetch(
        f"""SELECT id, task_id, agent_type, failure_type, failure_signal, confidence,
                   root_cause, root_cause_category, correction_strategy,
                   corrected_prompt, retest_passed, retest_details,
                   status, attempt_number, created_at, resolved_at
            FROM failure_branch_adaptations
            {where}
            ORDER BY created_at DESC
            LIMIT ${idx}""",
        *params,
    )
    return [FailureBranchAdaptationOut(**dict(r)) for r in rows]


@router.get("/stats")
async def get_stats():
    """Aggregate adaptation metrics."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT
               COUNT(*) as total,
               COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
               COUNT(*) FILTER (WHERE status = 'failed') as failed,
               COUNT(*) FILTER (WHERE status = 'detected') as pending,
               COUNT(*) FILTER (WHERE retest_passed = TRUE) as retest_passed,
               COUNT(*) FILTER (WHERE retest_passed = FALSE) as retest_failed,
               AVG(confidence) as avg_confidence,
               -- Breakdown by failure type
               COUNT(*) FILTER (WHERE failure_type = 'error') as type_error,
               COUNT(*) FILTER (WHERE failure_type = 'timeout') as type_timeout,
               COUNT(*) FILTER (WHERE failure_type = 'quality') as type_quality,
               COUNT(*) FILTER (WHERE failure_type = 'approach') as type_approach,
               COUNT(*) FILTER (WHERE failure_type = 'dependency') as type_dependency,
               -- Breakdown by root cause category
               COUNT(*) FILTER (WHERE root_cause_category = 'prompt') as cause_prompt,
               COUNT(*) FILTER (WHERE root_cause_category = 'scope') as cause_scope,
               COUNT(*) FILTER (WHERE root_cause_category = 'logic') as cause_logic,
               COUNT(*) FILTER (WHERE root_cause_category = 'dependency') as cause_dependency,
               COUNT(*) FILTER (WHERE root_cause_category = 'environment') as cause_environment
           FROM failure_branch_adaptations"""
    )
    result = dict(row)
    # Compute correction success rate
    total_retested = (result.get("retest_passed") or 0) + (result.get("retest_failed") or 0)
    result["correction_success_rate"] = (
        round((result.get("retest_passed") or 0) / total_retested, 3)
        if total_retested > 0
        else None
    )
    return result

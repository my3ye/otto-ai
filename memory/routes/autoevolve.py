"""AutoEvolve — autoresearch-inspired self-improvement experiment tracker.

Adapted from karpathy/autoresearch (2026-03):
  - program.md → target_file (heartbeat.md, reflection.md, etc.)
  - val_bpb metric → RL2F accuracy / task success rate
  - results.tsv → autoevolve_experiments table
  - keep/discard loop → outcome field + generation counter

The reflection agent calls /autoevolve/insights to get a hypothesis,
proposes a targeted change to a system file, logs it as an experiment,
and after N evaluation cycles updates the outcome (keep/discard).
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import get_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autoevolve", tags=["autoevolve"])


# ── Models ─────────────────────────────────────────────────────────────────────

class ExperimentCreate(BaseModel):
    target_file: str = Field(..., description="System file being modified, e.g. '.claude/agents/heartbeat.md'")
    hypothesis: str = Field(..., description="Why this change is expected to help")
    change_description: str = Field(..., description="What was changed (human-readable summary)")
    metric_name: str = Field(default="rl2f_accuracy")
    metric_before: Optional[float] = None
    git_checkpoint: Optional[str] = None
    source: str = Field(default="reflection")


class ExperimentOut(BaseModel):
    id: UUID
    target_file: str
    hypothesis: str
    change_description: str
    metric_name: str
    metric_before: Optional[float]
    metric_after: Optional[float]
    evaluation_cycles: int
    status: str
    outcome: Optional[str]
    git_checkpoint: Optional[str]
    generation: int
    source: str
    created_at: datetime
    evaluated_at: Optional[datetime]
    resolved_at: Optional[datetime]


class OutcomeUpdate(BaseModel):
    status: str = Field(..., description="keep | discard | crashed")
    metric_after: Optional[float] = None
    evaluation_cycles: Optional[int] = None
    outcome: Optional[str] = None


class InsightsOut(BaseModel):
    """Hypothesis proposal for the next experiment, derived from system data."""
    hypothesis: str
    target_file: str
    change_type: str  # 'prompt_edit' | 'budget_adjust' | 'threshold_tune' | 'procedure_add'
    supporting_data: dict
    current_generation: int
    confidence: float  # 0.0-1.0


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/experiments", response_model=ExperimentOut, status_code=201)
async def create_experiment(body: ExperimentCreate):
    """Log a new self-improvement experiment proposal."""
    pool = await get_pool()

    # Get current generation
    gen_row = await pool.fetchrow("SELECT current_generation FROM autoevolve_generation WHERE id = 1")
    generation = (gen_row["current_generation"] + 1) if gen_row else 1

    row = await pool.fetchrow(
        """INSERT INTO autoevolve_experiments
               (target_file, hypothesis, change_description, metric_name,
                metric_before, git_checkpoint, source, generation)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           RETURNING id, target_file, hypothesis, change_description, metric_name,
                     metric_before, metric_after, evaluation_cycles, status, outcome,
                     git_checkpoint, generation, source, created_at, evaluated_at, resolved_at""",
        body.target_file, body.hypothesis, body.change_description,
        body.metric_name, body.metric_before, body.git_checkpoint,
        body.source, generation,
    )
    return ExperimentOut(**dict(row))


@router.get("/experiments", response_model=list[ExperimentOut])
async def list_experiments(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List autoevolve experiments, newest first."""
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            """SELECT id, target_file, hypothesis, change_description, metric_name,
                      metric_before, metric_after, evaluation_cycles, status, outcome,
                      git_checkpoint, generation, source, created_at, evaluated_at, resolved_at
               FROM autoevolve_experiments
               WHERE status = $1
               ORDER BY created_at DESC LIMIT $2""",
            status, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, target_file, hypothesis, change_description, metric_name,
                      metric_before, metric_after, evaluation_cycles, status, outcome,
                      git_checkpoint, generation, source, created_at, evaluated_at, resolved_at
               FROM autoevolve_experiments
               ORDER BY created_at DESC LIMIT $1""",
            limit,
        )
    return [ExperimentOut(**dict(r)) for r in rows]


@router.put("/experiments/{experiment_id}/outcome", response_model=ExperimentOut)
async def update_outcome(experiment_id: UUID, body: OutcomeUpdate):
    """Record the result of an experiment (keep/discard/crashed)."""
    if body.status not in ("keep", "discard", "crashed"):
        raise HTTPException(status_code=400, detail="status must be keep, discard, or crashed")

    pool = await get_pool()
    now = datetime.now(timezone.utc)

    row = await pool.fetchrow(
        """UPDATE autoevolve_experiments
           SET status = $2,
               metric_after = COALESCE($3, metric_after),
               evaluation_cycles = COALESCE($4, evaluation_cycles),
               outcome = COALESCE($5, outcome),
               evaluated_at = $6,
               resolved_at = $6
           WHERE id = $1
           RETURNING id, target_file, hypothesis, change_description, metric_name,
                     metric_before, metric_after, evaluation_cycles, status, outcome,
                     git_checkpoint, generation, source, created_at, evaluated_at, resolved_at""",
        experiment_id, body.status, body.metric_after,
        body.evaluation_cycles, body.outcome, now,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # If kept, advance the generation counter
    if body.status == "keep":
        await pool.execute(
            """UPDATE autoevolve_generation
               SET current_generation = current_generation + 1, last_updated = NOW()
               WHERE id = 1""",
        )

    return ExperimentOut(**dict(row))


@router.post("/experiments/{experiment_id}/tick")
async def tick_evaluation(experiment_id: UUID):
    """Increment evaluation_cycles counter (called each heartbeat while experiment is active)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE autoevolve_experiments
           SET evaluation_cycles = evaluation_cycles + 1,
               evaluated_at = NOW(),
               status = CASE WHEN status = 'proposed' THEN 'active' ELSE status END
           WHERE id = $1
           RETURNING evaluation_cycles, status""",
        experiment_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return {"evaluation_cycles": row["evaluation_cycles"], "status": row["status"]}


@router.get("/generation")
async def get_generation():
    """Get current Otto software generation number (total kept experiments)."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT current_generation, last_updated FROM autoevolve_generation WHERE id = 1")
    return {
        "current_generation": row["current_generation"] if row else 0,
        "last_updated": row["last_updated"] if row else None,
    }


@router.get("/insights", response_model=InsightsOut)
async def get_insights():
    """Analyze system data and return the highest-value hypothesis for next experiment.

    Looks at:
    - RL2F misses/partial matches from last 50 cycles
    - Principles with low confidence (applied but violated)
    - Failed procedures
    - Active experiments (to avoid duplicating)

    Returns the most actionable improvement hypothesis.
    """
    pool = await get_pool()

    # Gather RL2F data
    rl2f_rows = await pool.fetch(
        """SELECT outcome_match, heartbeat_type, teacher_feedback
           FROM rl2f_feedback
           WHERE created_at > NOW() - INTERVAL '7 days'
           ORDER BY created_at DESC LIMIT 50""",
    )
    total = len(rl2f_rows)
    matches = sum(1 for r in rl2f_rows if r["outcome_match"] == "matched")
    misses = sum(1 for r in rl2f_rows if r["outcome_match"] == "miss")
    partials = sum(1 for r in rl2f_rows if r["outcome_match"] == "partial")
    accuracy = (matches / total) if total > 0 else 0.0

    # Gather principles violations
    principle_rows = await pool.fetch(
        """SELECT principle, category, confidence, times_applied, times_violated
           FROM principles
           WHERE times_violated > 0 AND confidence > 0.3
           ORDER BY (times_violated::float / GREATEST(times_applied, 1)) DESC
           LIMIT 5""",
    )

    # Gather failed procedures
    procedure_rows = await pool.fetch(
        """SELECT name, trust_score, success_count, failure_count
           FROM procedures
           WHERE (success_count + failure_count) > 0
           ORDER BY trust_score ASC LIMIT 5""",
    )

    # Check active experiments (don't duplicate)
    active_rows = await pool.fetch(
        """SELECT target_file FROM autoevolve_experiments
           WHERE status IN ('proposed', 'active')""",
    )
    active_files = {r["target_file"] for r in active_rows}

    # Get current generation
    gen_row = await pool.fetchrow("SELECT current_generation FROM autoevolve_generation WHERE id = 1")
    current_generation = gen_row["current_generation"] if gen_row else 0

    # Decide best hypothesis based on data
    hypothesis, target_file, change_type, confidence = _select_best_hypothesis(
        accuracy=accuracy,
        misses=misses,
        partials=partials,
        total=total,
        principle_rows=principle_rows,
        procedure_rows=procedure_rows,
        active_files=active_files,
    )

    return InsightsOut(
        hypothesis=hypothesis,
        target_file=target_file,
        change_type=change_type,
        supporting_data={
            "rl2f_accuracy": round(accuracy, 3),
            "rl2f_misses": misses,
            "rl2f_partials": partials,
            "rl2f_total": total,
            "top_violated_principle": principle_rows[0]["principle"][:200] if principle_rows else None,
            "lowest_trust_procedure": procedure_rows[0]["name"] if procedure_rows else None,
            "active_experiments": len(active_files),
        },
        current_generation=current_generation,
        confidence=confidence,
    )


def _select_best_hypothesis(
    accuracy: float,
    misses: int,
    partials: int,
    total: int,
    principle_rows,
    procedure_rows,
    active_files: set,
) -> tuple[str, str, str, float]:
    """Rule-based hypothesis selection. Returns (hypothesis, target_file, change_type, confidence)."""

    heartbeat_file = ".claude/agents/heartbeat.md"
    reflection_file = ".claude/agents/reflection.md"
    task_runner_file = "task_runner.sh"

    # Priority 1: RL2F accuracy < 70% → fix heartbeat reasoning
    if accuracy < 0.70 and total >= 5 and heartbeat_file not in active_files:
        return (
            f"RL2F accuracy is {accuracy:.0%} ({misses} misses in {total} cycles). "
            "The orchestrator heartbeat is making predictions that don't match reality. "
            "Adding a structured 'State Delta' section to heartbeat.md — forcing the agent "
            "to explicitly compare previous cycle's expected vs actual before deciding — "
            "should reduce prediction errors by anchoring reasoning to observed facts.",
            heartbeat_file,
            "prompt_edit",
            0.85,
        )

    # Priority 2: High partials → reflection is missing real issues
    if partials > misses and total >= 10 and reflection_file not in active_files:
        return (
            f"RL2F shows {partials} partial matches vs {misses} full misses. "
            "Partials indicate the reflection agent is identifying issues but not fully resolving them. "
            "Adding a mandatory 'Unresolved Items' checklist at the end of each reflection cycle "
            "would force explicit tracking of partially-addressed issues across cycles.",
            reflection_file,
            "prompt_edit",
            0.75,
        )

    # Priority 3: Principle violations → encode violated principles into agent prompts
    if principle_rows and heartbeat_file not in active_files:
        top_principle = principle_rows[0]
        violation_rate = top_principle["times_violated"] / max(top_principle["times_applied"], 1)
        if violation_rate > 0.2:
            return (
                f"Principle '{top_principle['principle'][:100]}...' is violated {violation_rate:.0%} of the time. "
                "High-violation principles should be embedded directly in the heartbeat agent prompt "
                "as explicit constraints, not left to be recalled from memory under load.",
                heartbeat_file,
                "prompt_edit",
                0.70,
            )

    # Priority 4: Low-trust procedures → improve procedure descriptions
    if procedure_rows and task_runner_file not in active_files:
        low_trust = procedure_rows[0]
        if low_trust["trust_score"] < 0.5:
            return (
                f"Procedure '{low_trust['name']}' has trust score {low_trust['trust_score']:.2f}. "
                "Low-trust procedures indicate the task runner is not following documented patterns. "
                "Adding procedure lookup as a mandatory pre-flight step in task_runner.sh "
                "would ensure procedures are consulted before each task type.",
                task_runner_file,
                "procedure_add",
                0.65,
            )

    # Default: meta-improvement of the autoevolve loop itself
    return (
        "No acute failure signals detected. System performing within normal bounds. "
        "Proactive improvement: add a 'WHAT WOULD I DO DIFFERENTLY?' prompt to the "
        "reflection agent's final step to generate novel improvement candidates even "
        "when metrics are green. This prevents improvement stagnation in stable periods.",
        reflection_file,
        "prompt_edit",
        0.50,
    )

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


# ── IMPL-02: Stagnation Detection + Auto-Pivot ───────────────────────────────
# CORAL (2604.01658): 5 consecutive non-improving evals → forced strategy pivot.
# AutoEvolve has been frozen at gen 7, 0 experiments, for 30+ days. The prompt
# fix (forward_plan "move to Step 1") is marked done but ineffective. This gives
# the reflection agent a code-level endpoint it can call reliably.


class StagnationReport(BaseModel):
    stagnation_detected: bool
    cycles_since_improvement: int
    current_accuracy: Optional[float]
    active_accuracy: Optional[float]
    pivot_recommendation: Optional[str] = None
    pivot_actions: list[str] = Field(default_factory=list)
    autoevolve_generation: int = 0
    experiments_proposed: int = 0
    experiments_kept: int = 0


class ForceExperimentRequest(BaseModel):
    hypothesis: str = Field(..., description="Why this experiment should help")
    target_file: str = Field(default=".claude/agents/heartbeat.md")
    change_description: str = Field(..., description="What to change")
    metric_name: str = Field(default="rl2f_active_accuracy")
    source: str = Field(default="stagnation_pivot")


@router.post("/stagnation-check", response_model=StagnationReport)
async def check_stagnation():
    """Detect if Otto's learning systems are stagnant and recommend pivots.

    Reads meta_memory.json for trend data, cross-references with reasoning_chain
    for active accuracy, and returns specific pivot actions if stagnation detected.
    Threshold: 5+ cycles with no accuracy improvement (CORAL paper recommendation).
    """
    import json as _json
    from pathlib import Path

    pool = await get_pool()

    # Read meta_memory.json
    meta_path = Path("/home/web3relic/otto/meta_memory.json")
    meta = {}
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text())
        except Exception:
            pass

    rl2f_trend = meta.get("rl2f_trend", {})
    cycles_since = rl2f_trend.get("cycles_since_improvement", 0)
    current_accuracy = rl2f_trend.get("last_7d_accuracy")

    # Get active accuracy (excluding idle cycles) from reasoning_chain
    active_row = await pool.fetchrow(
        """SELECT
               COUNT(*) FILTER (
                   WHERE COALESCE(metadata->>'idle_cycle', 'false') != 'true'
               ) as active_total,
               COUNT(*) FILTER (
                   WHERE outcome_match = 'matched'
                     AND COALESCE(metadata->>'idle_cycle', 'false') != 'true'
               ) as active_matched
           FROM reasoning_chain
           WHERE cycle_ts > NOW() - INTERVAL '7 days'
             AND outcome_match IS NOT NULL
             AND outcome_match != 'pending'"""
    )
    active_total = active_row["active_total"] or 0
    active_matched = active_row["active_matched"] or 0
    active_accuracy = round(active_matched / active_total, 4) if active_total > 0 else None

    # Get AutoEvolve state
    ae_state = meta.get("autoevolve_state", {})
    gen = ae_state.get("generation", 0)
    exp_count = await pool.fetchval(
        "SELECT COUNT(*) FROM autoevolve_experiments"
    ) or 0
    kept_count = await pool.fetchval(
        "SELECT COUNT(*) FROM autoevolve_experiments WHERE status = 'keep'"
    ) or 0

    # Stagnation threshold: 5+ cycles (CORAL paper)
    stagnation_detected = cycles_since >= 5
    pivot_recommendation = None
    pivot_actions = []

    if stagnation_detected:
        # Determine specific pivot actions based on data
        if active_accuracy is not None and current_accuracy is not None:
            inflation = round(current_accuracy - active_accuracy, 4)
            if inflation > 0.05:
                pivot_actions.append(
                    f"Idle-cycle inflation is {inflation:.1%} — active accuracy ({active_accuracy:.1%}) "
                    f"is significantly lower than total ({current_accuracy:.1%}). "
                    "Focus improvements on active-cycle decision quality."
                )

        if ae_state.get("experiments_this_generation", 0) == 0:
            pivot_actions.append(
                "AutoEvolve has 0 experiments this generation. "
                "Use POST /autoevolve/force-experiment to create one directly."
            )

        if cycles_since >= 10:
            pivot_actions.append(
                "Extended stagnation (10+ cycles). Consider rotating the RL2F feature set: "
                "change which dimensions the teacher evaluates (root_condition_analysis fields)."
            )

        pivot_actions.append(
            "Run POST /autoevolve/insights to get the highest-value hypothesis, "
            "then POST /autoevolve/force-experiment with that hypothesis."
        )

        pivot_recommendation = (
            f"Stagnation detected: {cycles_since} cycles without improvement. "
            f"Active accuracy: {active_accuracy}. {len(pivot_actions)} actions recommended."
        )

    return StagnationReport(
        stagnation_detected=stagnation_detected,
        cycles_since_improvement=cycles_since,
        current_accuracy=current_accuracy,
        active_accuracy=active_accuracy,
        pivot_recommendation=pivot_recommendation,
        pivot_actions=pivot_actions,
        autoevolve_generation=gen,
        experiments_proposed=exp_count,
        experiments_kept=kept_count,
    )


@router.post("/force-experiment", response_model=ExperimentOut, status_code=201)
async def force_experiment(body: ForceExperimentRequest):
    """Create an experiment directly, bypassing the normal reflection cycle gate.

    Used by the stagnation pivot system: when AutoEvolve is frozen because the
    budget/prompt gate blocks experiment creation during DEGRADED cycles, this
    endpoint creates the experiment unconditionally. The experiment IS the fix
    for stagnation — blocking it perpetuates the problem.

    Also updates meta_memory.json to track the forced pivot.
    """
    import json as _json
    from pathlib import Path

    pool = await get_pool()

    # Get current generation
    gen_row = await pool.fetchrow(
        "SELECT current_generation FROM autoevolve_generation WHERE id = 1"
    )
    generation = (gen_row["current_generation"] + 1) if gen_row else 1

    # Get current active accuracy as metric_before
    active_row = await pool.fetchrow(
        """SELECT
               COUNT(*) FILTER (
                   WHERE COALESCE(metadata->>'idle_cycle', 'false') != 'true'
               ) as active_total,
               COUNT(*) FILTER (
                   WHERE outcome_match = 'matched'
                     AND COALESCE(metadata->>'idle_cycle', 'false') != 'true'
               ) as active_matched
           FROM reasoning_chain
           WHERE cycle_ts > NOW() - INTERVAL '7 days'
             AND outcome_match IS NOT NULL
             AND outcome_match != 'pending'"""
    )
    at = active_row["active_total"] or 0
    am = active_row["active_matched"] or 0
    metric_before = round(am / at, 4) if at > 0 else None

    # Create the experiment
    row = await pool.fetchrow(
        """INSERT INTO autoevolve_experiments
               (target_file, hypothesis, change_description, metric_name,
                metric_before, source, generation)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           RETURNING id, target_file, hypothesis, change_description, metric_name,
                     metric_before, metric_after, evaluation_cycles, status, outcome,
                     git_checkpoint, generation, source, created_at, evaluated_at, resolved_at""",
        body.target_file,
        body.hypothesis,
        body.change_description,
        body.metric_name,
        metric_before,
        body.source,
        generation,
    )

    # Update meta_memory.json with pivot record
    meta_path = Path("/home/web3relic/otto/meta_memory.json")
    meta = {}
    if meta_path.exists():
        try:
            meta = _json.loads(meta_path.read_text())
        except Exception:
            pass

    now_str = datetime.now(timezone.utc).isoformat()

    # Add stagnation_pivots array if missing
    if "stagnation_pivots" not in meta:
        meta["stagnation_pivots"] = []
    meta["stagnation_pivots"].append({
        "timestamp": now_str,
        "experiment_id": str(row["id"]),
        "hypothesis": body.hypothesis[:200],
        "target_file": body.target_file,
        "metric_before": metric_before,
    })

    # Update autoevolve_state
    ae_state = meta.get("autoevolve_state", {})
    ae_state["active_experiment_id"] = str(row["id"])
    ae_state["experiments_this_generation"] = ae_state.get("experiments_this_generation", 0) + 1
    meta["autoevolve_state"] = ae_state

    # Enable auto-pivot flag
    if "auto_pivot_enabled" not in meta:
        meta["auto_pivot_enabled"] = True

    meta["last_updated"] = now_str

    meta_path.write_text(_json.dumps(meta, indent=2))
    logger.info(f"Force-experiment created: {row['id']} (stagnation pivot)")

    return ExperimentOut(**dict(row))


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

    # Gather RL2F data from reasoning_chain (authoritative source)
    # IMPL-01: Use active-only accuracy (exclude idle cycles) for hypothesis selection.
    # Idle cycles inflate accuracy by counting trivial "do nothing" predictions.
    rl2f_rows = await pool.fetch(
        """SELECT outcome_match, COALESCE(metadata->>'idle_cycle', 'false') as idle
           FROM reasoning_chain
           WHERE outcome_match != 'pending'
           ORDER BY cycle_ts DESC LIMIT 50""",
    )
    # Active-only counts (what actually matters)
    active_rows = [r for r in rl2f_rows if r["idle"] != "true"]
    total = len(active_rows)
    matches = sum(1 for r in active_rows if r["outcome_match"] == "matched")
    misses = sum(1 for r in active_rows if r["outcome_match"] == "miss")
    partials = sum(1 for r in active_rows if r["outcome_match"] == "partial")
    accuracy = (matches / total) if total > 0 else 0.0
    # Also track total for context
    total_all = len(rl2f_rows)
    idle_count = total_all - total

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
            "rl2f_active_accuracy": round(accuracy, 3),
            "rl2f_misses": misses,
            "rl2f_partials": partials,
            "rl2f_active_total": total,
            "rl2f_idle_excluded": idle_count,
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


# ── Reflection Versions ──────────────────────────────────────────────────────
# EMRS Phase 2 — versioned manifest for self-modifications (2026-03-24)

from datetime import timedelta  # noqa: E402 (appended after module body)


class ReflectionVersionCreate(BaseModel):
    target_file: str
    version: int
    content_hash: str
    diff: str
    patch_summary: str
    hypothesis: Optional[str] = None
    experiment_id: Optional[UUID] = None
    rl2f_before: Optional[float] = None
    source: str = "autoevolve"


class ReflectionVersionOut(BaseModel):
    id: UUID
    version: int
    target_file: str
    content_hash: str
    diff: str
    patch_summary: str
    hypothesis: Optional[str]
    rl2f_before: Optional[float]
    rl2f_after: Optional[float]
    status: str
    applied_at: Optional[datetime]
    veto_expires_at: Optional[datetime]
    evaluated_at: Optional[datetime]
    created_at: datetime


@router.post("/versions", response_model=ReflectionVersionOut, status_code=201)
async def create_version(body: ReflectionVersionCreate):
    """Record a self-modification patch — enters pending_veto state."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)
        veto_exp = now + timedelta(hours=48)
        row = await conn.fetchrow(
            """
            INSERT INTO reflection_versions
              (version, target_file, content_hash, diff, patch_summary, hypothesis,
               experiment_id, rl2f_before, source, applied_at, veto_expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING *
            """,
            body.version, body.target_file, body.content_hash, body.diff,
            body.patch_summary, body.hypothesis, body.experiment_id,
            body.rl2f_before, body.source, now, veto_exp,
        )
        return dict(row)


@router.get("/versions", response_model=list[ReflectionVersionOut])
async def list_versions(
    target_file: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        q = "SELECT * FROM reflection_versions WHERE archived=FALSE AND deleted_at IS NULL"
        params: list = []
        if target_file:
            params.append(target_file)
            q += f" AND target_file=${len(params)}"
        if status:
            params.append(status)
            q += f" AND status=${len(params)}"
        params.append(limit)
        q += f" ORDER BY created_at DESC LIMIT ${len(params)}"
        rows = await conn.fetch(q, *params)
        return [dict(r) for r in rows]


@router.get("/versions/{version_id}", response_model=ReflectionVersionOut)
async def get_version(version_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM reflection_versions WHERE id=$1", version_id
        )
        if not row:
            raise HTTPException(404, "Version not found")
        return dict(row)


@router.post("/versions/{version_id}/veto")
async def veto_version(version_id: UUID):
    """Mev (or auto-rollback) rejects a patch within the veto window."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE reflection_versions SET status='vetoed', evaluated_at=NOW() "
            "WHERE id=$1 RETURNING id, status",
            version_id,
        )
        if not row:
            raise HTTPException(404, "Version not found")
        return {"id": str(row["id"]), "status": row["status"]}


@router.post("/versions/check-rollbacks")
async def check_rollbacks():
    """Called by reflection Step 6. Returns patches that need rolling back
    (RL2F dropped >15% after this patch went active)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM rollback_candidates ORDER BY created_at ASC"
        )
        return {"rollback_needed": [dict(r) for r in rows]}


@router.get("/meta-state")
async def get_meta_state():
    """Current EMRS summary — useful for OMS dashboard and reflection Step 0.5."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM reflection_versions "
            "WHERE status='pending_veto' AND archived=FALSE AND deleted_at IS NULL"
        )
        active = await conn.fetchval(
            "SELECT COUNT(*) FROM reflection_versions "
            "WHERE status='active' AND archived=FALSE AND deleted_at IS NULL"
        )
        rollbacks = await conn.fetchval("SELECT COUNT(*) FROM rollback_candidates")
        gen_row = await conn.fetchrow(
            "SELECT generation FROM autoevolve_experiments "
            "ORDER BY created_at DESC LIMIT 1"
        )
        return {
            "pending_patches": pending,
            "active_patches": active,
            "rollback_candidates": rollbacks,
            "current_generation": gen_row["generation"] if gen_row else 1,
        }

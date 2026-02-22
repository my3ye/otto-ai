"""
/eval — Benchmark-gated self-modification evaluation.

Endpoints:
  POST /eval/run      — Store a completed eval result (called by eval_harness.py)
  GET  /eval/history  — Retrieve past eval runs for trend tracking
  GET  /eval/latest   — Get the single most recent eval result
  GET  /eval/trend    — Aggregate score trend over time
  GET  /eval/gaps     — Metacognitive gap analysis: identify weak capabilities + propose tasks
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from ..db import get_pool

router = APIRouter(prefix="/eval", tags=["eval"])


def _row_to_dict(row) -> dict:
    d = dict(row)
    for field in ("per_task_json",):
        val = d.get(field)
        if isinstance(val, str):
            d[field] = json.loads(val)
    # Normalise key for external callers (per_task_json → per_task)
    d["per_task"] = d.pop("per_task_json", [])
    return d


@router.post("/run", status_code=201)
async def store_eval_result(body: dict):
    """
    Store a completed eval run. Called by eval_harness.py --store.

    Expected body fields:
      aggregate_score  float       0.0–1.0
      per_task         list        per-task scores and details
      context          str|None    what changed before this run
      triggered_by     str         manual | self_patch | scheduled
      duration_s       float|None
      model_used       str|None
    """
    pool = await get_pool()

    aggregate_score = float(body.get("aggregate_score", 0.0))
    per_task = body.get("per_task", body.get("per_task_json", []))
    context = body.get("context") or None
    triggered_by = body.get("triggered_by", "manual")
    duration_s = body.get("duration_s")
    model_used = body.get("model_used", "claude-haiku-4-5-20251001")

    row = await pool.fetchrow(
        """INSERT INTO eval_results
               (aggregate_score, per_task_json, context, triggered_by, duration_s, model_used)
           VALUES ($1, $2::jsonb, $3, $4, $5, $6)
           RETURNING *""",
        aggregate_score,
        json.dumps(per_task),
        context,
        triggered_by,
        duration_s,
        model_used,
    )
    return _row_to_dict(row)


@router.get("/history")
async def get_eval_history(
    limit: int = Query(20, ge=1, le=200),
    triggered_by: Optional[str] = Query(None, description="Filter: manual|self_patch|scheduled"),
):
    """Return past eval runs, newest first."""
    pool = await get_pool()

    if triggered_by:
        rows = await pool.fetch(
            """SELECT * FROM eval_results
               WHERE triggered_by = $1
               ORDER BY run_at DESC LIMIT $2""",
            triggered_by, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT * FROM eval_results
               ORDER BY run_at DESC LIMIT $1""",
            limit,
        )
    return [_row_to_dict(r) for r in rows]


@router.get("/latest")
async def get_latest_eval():
    """Return the single most recent eval result, or null if none exist."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM eval_results ORDER BY run_at DESC LIMIT 1"
    )
    if not row:
        return {"result": None, "message": "No eval runs recorded yet"}
    return _row_to_dict(row)


@router.get("/trend")
async def get_eval_trend(limit: int = Query(10, ge=2, le=50)):
    """Return aggregate scores over time for plotting performance trends."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, run_at, aggregate_score, context, triggered_by
           FROM eval_results
           ORDER BY run_at DESC LIMIT $1""",
        limit,
    )
    entries = [dict(r) for r in rows]
    if len(entries) >= 2:
        first = entries[-1]["aggregate_score"]
        last = entries[0]["aggregate_score"]
        trend_delta = round(last - first, 4)
        trend_direction = "improving" if trend_delta > 0 else ("declining" if trend_delta < 0 else "stable")
    else:
        trend_delta = None
        trend_direction = "insufficient_data"

    return {
        "entries": entries,
        "trend_delta": trend_delta,
        "trend_direction": trend_direction,
    }


# ── Capability improvement proposals (used by metacognitive planning layer) ──

_CAPABILITY_PROPOSALS = {
    "reasoning": (
        "Improve Otto's chain-of-thought reasoning capability. "
        "Steps: (1) Review GET /eval/history for reasoning task scores + justifications. "
        "(2) Identify what reasoning patterns score lowest (multi-step deduction, syllogisms, uncertainty handling). "
        "(3) Research Tree-of-Thought or Self-Ask prompting strategies. "
        "(4) Propose a reasoning scaffold: add explicit 'Let me break this into sub-problems' step to task prompts. "
        "(5) Store improvement as a procedural memory (POST /procedural, name=reasoning_scaffold). "
        "(6) Create a task to run: python3 ~/otto/tools/eval_harness.py --store --context 'reasoning_improvement' "
        "(note: must run as a detached task, NOT from inside a Claude Code session)."
    ),
    "code_gen": (
        "Improve Otto's Python code generation capability. "
        "Steps: (1) Review GET /eval/history for code_gen task scores + justifications. "
        "(2) Identify failure patterns (missing edge cases, incomplete solutions, no docstrings). "
        "(3) Implement a code self-review checklist: after generating code, check: docstring present? "
        "edge cases handled? no mutation bugs? types consistent? "
        "(4) Store this as procedural memory (name=code_generation_checklist). "
        "(5) Create a task to run the eval harness as a detached session to measure delta."
    ),
    "planning": (
        "Improve Otto's structured planning capability. "
        "Steps: (1) Review GET /eval/history for planning task scores + justifications. "
        "(2) Identify what makes plans vague vs. actionable (missing specifics, wrong granularity). "
        "(3) Research LATS (Language Agent Tree Search) decomposition strategies. "
        "(4) Implement a planning template: Context → Constraints → Steps (numbered, specific, testable) → Success criteria. "
        "(5) Store as procedural memory (name=structured_planning_template). "
        "(6) Create a detached eval task to measure improvement."
    ),
    "debugging": (
        "Improve Otto's debugging and root cause analysis capability. "
        "Steps: (1) Review GET /eval/history for debugging task scores + justifications. "
        "(2) Identify what bugs are being missed (mutation aliasing, type errors, off-by-one, scope issues). "
        "(3) Create a systematic debugging checklist: "
        "mutation/aliasing check, type assumption check, None/empty check, off-by-one check. "
        "(4) Store as procedural memory (name=debugging_systematic_checklist). "
        "(5) Create a detached eval task to measure improvement."
    ),
    "conciseness": (
        "Improve Otto's concise technical writing capability. "
        "Steps: (1) Review GET /eval/history for conciseness task scores + justifications. "
        "(2) Identify what causes verbosity (padding, repetition, unnecessary qualifiers). "
        "(3) Add a self-edit pass: after drafting, cut any sentence that doesn't add information. "
        "Target: ≤ 3 sentences for explanations, no bullet points unless explicitly requested. "
        "(4) Store as procedural memory (name=concise_writing_self_edit). "
        "(5) Create a detached eval task to measure improvement."
    ),
}

_EVAL_RUN_TASK = {
    "title": "[P1] Run eval baseline — establish capability scores",
    "prompt": (
        "Run the Otto eval harness to establish capability baseline scores. "
        "IMPORTANT: This must run OUTSIDE a Claude Code session. Execute as a shell command:\n"
        "cd ~/otto && CLAUDECODE= python3 tools/eval_harness.py --store --context 'baseline_retry'\n"
        "If CLAUDECODE unset does not work, use a subprocess approach:\n"
        "  import subprocess, os\n"
        "  env = {k:v for k,v in os.environ.items() if k != 'CLAUDECODE'}\n"
        "  subprocess.run(['python3', 'tools/eval_harness.py', '--store', '--context', 'baseline_retry'], "
        "env=env, cwd='/home/web3relic/otto')\n"
        "Report the aggregate score and per-task scores when done."
    ),
    "priority": 9,
    "model": "sonnet",
    "max_budget_usd": 2.00,
    "timeout_seconds": 900,
    "created_by": "reflection_metacognitive",
}


@router.get("/gaps")
async def get_capability_gaps(
    lookback: int = Query(10, ge=1, le=50, description="Number of recent eval runs to analyze"),
    threshold: float = Query(0.7, ge=0.0, le=1.0, description="Score below which a capability is a gap"),
    include_task_failures: bool = Query(True, description="Also analyze task failure patterns"),
):
    """
    Metacognitive gap analysis: identify capability gaps from eval history and return
    ranked improvement proposals. Called by the reflection agent each cycle.

    Returns:
      - status: 'no_eval_data' | 'invalid_baseline' | 'analyzed'
      - gaps: list of capabilities ranked by weakness (lowest avg score first)
      - proposals: ready-to-use task specs targeting each gap
      - overall_trend: improving | declining | stable | insufficient_data
      - task_failure_patterns: common failure modes from task history (if requested)
    """
    pool = await get_pool()

    # Fetch recent eval history
    rows = await pool.fetch(
        """SELECT per_task_json, aggregate_score, run_at, context
           FROM eval_results
           ORDER BY run_at DESC LIMIT $1""",
        lookback,
    )

    if not rows:
        return {
            "status": "no_eval_data",
            "message": "No eval runs recorded. Must run eval harness to establish baseline.",
            "gaps": [],
            "gap_count": 0,
            "proposals": [dict(_EVAL_RUN_TASK)],
            "baseline": None,
            "overall_trend": "insufficient_data",
            "overall_trend_delta": None,
            "task_failure_patterns": [],
        }

    # Collect per-task scores — skip runs where all scores are 0 from nested-session errors
    capability_scores: dict[str, list[float]] = {}
    valid_run_count = 0
    invalid_run_count = 0

    for row in rows:
        per_task_raw = row["per_task_json"]
        if isinstance(per_task_raw, str):
            try:
                per_task = json.loads(per_task_raw)
            except json.JSONDecodeError:
                continue
        else:
            per_task = per_task_raw or []

        if not per_task:
            continue

        # Detect invalid run: all outputs are error messages (nested session failure)
        all_zero = all(float(t.get("score", 0)) == 0.0 for t in per_task)
        any_error_output = any(
            "[ERROR:" in str(t.get("output", "")) for t in per_task
        )
        if all_zero and any_error_output:
            invalid_run_count += 1
            continue  # skip this run — not real capability data

        valid_run_count += 1
        for task in per_task:
            tid = task.get("task_id") or task.get("id") or "unknown"
            score = float(task.get("score", 0.5))
            if tid not in capability_scores:
                capability_scores[tid] = []
            capability_scores[tid].append(score)

    # If we have no valid runs but have invalid ones, return a specific status
    if not capability_scores and invalid_run_count > 0:
        return {
            "status": "invalid_baseline",
            "message": (
                f"All {invalid_run_count} eval run(s) failed due to nested Claude Code session error. "
                "The eval harness must be run as a detached task (not inside Claude Code). "
                "Use the proposal below to schedule a proper baseline run."
            ),
            "gaps": [],
            "gap_count": 0,
            "proposals": [dict(_EVAL_RUN_TASK)],
            "baseline": None,
            "overall_trend": "insufficient_data",
            "overall_trend_delta": None,
            "invalid_runs": invalid_run_count,
            "task_failure_patterns": [],
        }

    # Analyze each capability
    gaps = []
    for cap_id, scores in capability_scores.items():
        avg = round(sum(scores) / len(scores), 4)
        min_score = round(min(scores), 4)
        max_score = round(max(scores), 4)

        # Trend: compare recent half vs older half (scores list is newest-first)
        if len(scores) >= 4:
            half = len(scores) // 2
            recent_avg = sum(scores[:half]) / half
            older_avg = sum(scores[half:]) / (len(scores) - half)
            trend_delta = round(recent_avg - older_avg, 4)
            trend = (
                "improving" if trend_delta > 0.02
                else ("declining" if trend_delta < -0.02 else "stable")
            )
        else:
            trend_delta = None
            trend = "insufficient_data"

        severity = "critical" if avg < 0.4 else ("moderate" if avg < threshold else "ok")
        is_gap = avg < threshold

        # Compute a sort key: lower avg = worse; declining trend makes it worse
        sort_key = avg + (0.05 if trend == "improving" else (-0.05 if trend == "declining" else 0))

        gaps.append({
            "capability": cap_id,
            "avg_score": avg,
            "min_score": min_score,
            "max_score": max_score,
            "run_count": len(scores),
            "trend": trend,
            "trend_delta": trend_delta,
            "is_gap": is_gap,
            "severity": severity,
            "_sort_key": sort_key,
        })

    # Sort: worst gaps first
    gaps.sort(key=lambda g: g["_sort_key"])
    for g in gaps:
        del g["_sort_key"]

    # Generate proposals for actual gaps only
    proposals = []
    for gap in gaps:
        if not gap["is_gap"]:
            continue
        cap = gap["capability"]
        severity_priority = 9 if gap["severity"] == "critical" else 8
        proposal_prompt = _CAPABILITY_PROPOSALS.get(
            cap,
            (
                f"Investigate and improve Otto's '{cap}' capability (current avg score: {gap['avg_score']:.2f}). "
                f"Review eval history for this capability, identify failure patterns, "
                f"implement a concrete improvement (procedural memory or prompt scaffold), "
                f"then schedule an eval run (as a detached task) to measure delta."
            ),
        )
        proposals.append({
            "priority": severity_priority,
            "capability": cap,
            "gap_score": gap["avg_score"],
            "severity": gap["severity"],
            "title": f"[P{severity_priority}] Close capability gap: {cap} (score={gap['avg_score']:.2f})",
            "prompt": proposal_prompt,
            "reason": (
                f"Avg score {gap['avg_score']:.2f} below threshold {threshold:.2f}. "
                f"Severity: {gap['severity']}. Trend: {gap['trend']} (delta={gap['trend_delta']})."
            ),
        })

    # Overall aggregate trend
    aggregate_scores = [float(r["aggregate_score"]) for r in rows]
    valid_aggregates = [s for s in aggregate_scores if s > 0]
    if len(valid_aggregates) >= 2:
        overall_trend_delta = round(valid_aggregates[0] - valid_aggregates[-1], 4)
        overall_trend = (
            "improving" if overall_trend_delta > 0.02
            else ("declining" if overall_trend_delta < -0.02 else "stable")
        )
        latest_aggregate = valid_aggregates[0]
    else:
        overall_trend_delta = None
        overall_trend = "insufficient_data"
        latest_aggregate = valid_aggregates[0] if valid_aggregates else None

    # Task failure pattern analysis
    task_failure_patterns = []
    if include_task_failures:
        try:
            failure_rows = await pool.fetch(
                """SELECT title, error, exit_code, COUNT(*) as count
                   FROM tasks
                   WHERE status = 'failed'
                     AND completed_at > NOW() - INTERVAL '7 days'
                   GROUP BY title, error, exit_code
                   ORDER BY count DESC
                   LIMIT 5""",
            )
            for fr in failure_rows:
                task_failure_patterns.append({
                    "title": fr["title"],
                    "error": (fr["error"] or "")[:200],
                    "exit_code": fr["exit_code"],
                    "occurrences": fr["count"],
                })
        except Exception:
            pass  # Non-blocking — task analysis is supplementary

    return {
        "status": "analyzed",
        "runs_analyzed": len(rows),
        "valid_runs": valid_run_count,
        "invalid_runs": invalid_run_count,
        "threshold": threshold,
        "gaps": gaps,
        "gap_count": len(proposals),
        "proposals": proposals,
        "latest_aggregate": latest_aggregate,
        "overall_trend": overall_trend,
        "overall_trend_delta": overall_trend_delta,
        "task_failure_patterns": task_failure_patterns,
        "analysis_note": (
            f"Analyzed {len(rows)} eval runs ({valid_run_count} valid, {invalid_run_count} invalid). "
            f"{len(proposals)} capability gap(s) identified."
        ),
    }

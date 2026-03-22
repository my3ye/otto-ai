"""Persistent reasoning chain across heartbeat cycles.

Each heartbeat writes a ReasoningEntry at the end of its cycle:
  - reasoning: WHY it made the choices it did
  - decisions: WHAT it decided to do
  - expected: WHAT it expects to happen next cycle

The NEXT heartbeat, before writing its own entry, updates the prior entry:
  - actual: what it actually observed
  - outcome_match: matched | partial | miss

This creates a feedback loop: decide → act → observe → calibrate → decide better.

RL2F Layer 2 (migration 039): When outcome_match = 'miss' or 'partial',
extract-lessons analyzes WHY the prediction failed, stores a learning principle
in the principles table, and marks the entry as processed. The pre-decision-brief
endpoint surfaces these lessons before the next cycle's DECIDE step.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from ..db import get_pool
from ..models import ReasoningEntryCreate, ReasoningEntryOut, ReasoningOutcomeUpdate

logger = logging.getLogger(__name__)

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


# ── RL2F Layer 2: Reasoning Chain Learning Loop ───────────────────


@router.post("/extract-lessons")
async def extract_lessons(
    limit: int = Query(default=10, ge=1, le=50),
):
    """Extract learning principles from unprocessed misses/partials.

    For each miss or partial:
    1. Constructs a lesson from expected vs actual
    2. Checks for duplicate principles (same category + similar text)
    3. If new: creates a principle with category='reasoning_chain'
    4. Marks the reasoning entry as lesson_extracted=TRUE

    Called by reflection heartbeat after MARS sweep.
    Returns list of extracted lessons with any new principles created.
    """
    pool = await get_pool()

    # Fetch unprocessed misses and partials
    rows = await pool.fetch(
        """SELECT id, heartbeat_type, cycle_ts, reasoning, decisions,
                  expected, actual, outcome_match
           FROM reasoning_chain
           WHERE outcome_match IN ('miss', 'partial')
             AND lesson_extracted = FALSE
           ORDER BY cycle_ts DESC
           LIMIT $1""",
        limit,
    )

    if not rows:
        return {"lessons": [], "principles_created": 0, "entries_processed": 0}

    # Fetch existing reasoning_chain principles to avoid duplicates
    existing = await pool.fetch(
        """SELECT id, principle FROM principles
           WHERE category = 'reasoning_chain'
           ORDER BY created_at DESC LIMIT 50"""
    )
    existing_texts = [r["principle"].lower() for r in existing]

    lessons = []
    principles_created = 0

    for row in rows:
        entry_id = row["id"]
        expected = row["expected"] or "(no prediction recorded)"
        actual = row["actual"] or "(no observation recorded)"
        reasoning = row["reasoning"] or ""
        decisions = row["decisions"] or ""
        outcome = row["outcome_match"]
        hb_type = row["heartbeat_type"]

        # Construct the lesson: what went wrong and why
        if outcome == "miss":
            lesson_text = (
                f"MISS in {hb_type} cycle: "
                f"Expected: {expected[:200]} | "
                f"Actual: {actual[:200]} | "
                f"Decision was: {decisions[:150]}"
            )
            principle_text = (
                f"When {_extract_condition(reasoning, decisions)}, "
                f"beware: prediction '{expected[:100]}' led to miss "
                f"(actual: '{actual[:100]}'). "
                f"Adjust expectations for similar situations."
            )
        else:  # partial
            lesson_text = (
                f"PARTIAL in {hb_type} cycle: "
                f"Expected: {expected[:200]} | "
                f"Actual: {actual[:200]} | "
                f"Partially correct — refine prediction granularity."
            )
            principle_text = (
                f"When {_extract_condition(reasoning, decisions)}, "
                f"prediction was partially right but missed: "
                f"'{actual[:100]}' vs expected '{expected[:100]}'. "
                f"Refine scope of predictions."
            )

        # Check for near-duplicate principles
        principle_lower = principle_text.lower()
        is_duplicate = any(
            _text_overlap(principle_lower, ex) > 0.6 for ex in existing_texts
        )
        # Extra dedup for template-generated principles: signature match
        # Prevents bloat where each entry creates a near-identical principle
        # with different condition prefixes that fool Jaccard similarity
        if not is_duplicate and outcome == "partial":
            partial_sig = "prediction was partially right but missed"
            is_duplicate = any(partial_sig in ex for ex in existing_texts)
        if not is_duplicate and outcome == "miss":
            miss_sig = "led to miss (actual:"
            is_duplicate = any(miss_sig in ex for ex in existing_texts)
        # Also check if ANY existing reasoning_chain principle exists —
        # after consolidation, the consolidated principle won't match templates
        if not is_duplicate and len(existing_texts) >= 1:
            # If there's already a reasoning_chain principle about predictions,
            # skip creating more template-based ones
            prediction_keywords = ["predict", "expectation", "beware"]
            has_prediction_principle = any(
                any(kw in ex for kw in prediction_keywords) for ex in existing_texts
            )
            new_is_prediction = any(kw in principle_lower for kw in prediction_keywords)
            if has_prediction_principle and new_is_prediction:
                is_duplicate = True

        new_principle_id = None
        if not is_duplicate:
            p_row = await pool.fetchrow(
                """INSERT INTO principles
                       (principle, category, source_reasoning_ids, confidence)
                   VALUES ($1, 'reasoning_chain', ARRAY[$2]::uuid[], $3)
                   RETURNING id""",
                principle_text,
                entry_id,
                0.5 if outcome == "partial" else 0.6,
            )
            new_principle_id = str(p_row["id"])
            existing_texts.append(principle_lower)
            principles_created += 1

        # Mark as extracted
        await pool.execute(
            "UPDATE reasoning_chain SET lesson_extracted = TRUE WHERE id = $1",
            entry_id,
        )

        lessons.append({
            "entry_id": str(entry_id),
            "outcome": outcome,
            "lesson": lesson_text,
            "principle_created": new_principle_id is not None,
            "principle_id": new_principle_id,
            "duplicate_skipped": is_duplicate,
        })

    return {
        "lessons": lessons,
        "principles_created": principles_created,
        "entries_processed": len(lessons),
    }


@router.get("/accuracy")
async def reasoning_accuracy(
    window: int = Query(default=50, ge=5, le=200, description="Number of recent entries to analyze"),
    heartbeat_type: str | None = Query(default=None),
):
    """Rolling accuracy of reasoning predictions.

    Returns hit/miss/partial counts and percentages over the last N resolved
    entries (excludes 'pending'). Includes trend comparison: last window vs
    prior window.
    """
    pool = await get_pool()

    type_filter = "AND heartbeat_type = $2" if heartbeat_type else ""
    params: list = [window * 2]  # fetch double for trend comparison
    if heartbeat_type:
        params.append(heartbeat_type)

    rows = await pool.fetch(
        f"""SELECT outcome_match, cycle_ts
            FROM reasoning_chain
            WHERE outcome_match != 'pending'
            {type_filter}
            ORDER BY cycle_ts DESC
            LIMIT $1""",
        *params,
    )

    if not rows:
        return {
            "total": 0, "matched": 0, "partial": 0, "miss": 0,
            "accuracy_pct": 0.0, "partial_pct": 0.0, "miss_pct": 0.0,
            "trend": "insufficient_data",
        }

    # Split into current window and prior window
    current = rows[:window]
    prior = rows[window:]

    def _stats(entries):
        total = len(entries)
        if total == 0:
            return {"total": 0, "matched": 0, "partial": 0, "miss": 0, "accuracy_pct": 0.0}
        matched = sum(1 for r in entries if r["outcome_match"] == "matched")
        partial = sum(1 for r in entries if r["outcome_match"] == "partial")
        miss = sum(1 for r in entries if r["outcome_match"] == "miss")
        return {
            "total": total,
            "matched": matched,
            "partial": partial,
            "miss": miss,
            "accuracy_pct": round(matched / total * 100, 1),
            "partial_pct": round(partial / total * 100, 1),
            "miss_pct": round(miss / total * 100, 1),
        }

    curr_stats = _stats(current)
    prev_stats = _stats(prior)

    # Determine trend
    if prev_stats["total"] < 5:
        trend = "insufficient_prior_data"
    elif curr_stats["accuracy_pct"] > prev_stats["accuracy_pct"] + 5:
        trend = "improving"
    elif curr_stats["accuracy_pct"] < prev_stats["accuracy_pct"] - 5:
        trend = "declining"
    else:
        trend = "stable"

    return {
        **curr_stats,
        "trend": trend,
        "prior_accuracy_pct": prev_stats["accuracy_pct"],
        "window": window,
    }


@router.get("/pre-decision-brief")
async def pre_decision_brief(
    heartbeat_type: str = Query(default="orchestrator"),
    miss_limit: int = Query(default=5, ge=1, le=10),
    principle_limit: int = Query(default=10, ge=1, le=20),
):
    """Context brief for injection before the DECIDE step.

    Surfaces:
    1. Recent misses/partials with their lessons
    2. Active high-confidence principles from reasoning_chain category
    3. Rolling accuracy stats

    The heartbeat should read this and incorporate it into its reasoning.
    """
    pool = await get_pool()

    # 1. Recent misses with lessons
    misses = await pool.fetch(
        """SELECT cycle_ts, reasoning, decisions, expected, actual, outcome_match
           FROM reasoning_chain
           WHERE heartbeat_type = $1
             AND outcome_match IN ('miss', 'partial')
           ORDER BY cycle_ts DESC
           LIMIT $2""",
        heartbeat_type, miss_limit,
    )

    miss_briefs = []
    for m in misses:
        miss_briefs.append({
            "when": m["cycle_ts"].isoformat(),
            "outcome": m["outcome_match"],
            "expected": (m["expected"] or "")[:200],
            "actual": (m["actual"] or "")[:200],
            "decision_was": (m["decisions"] or "")[:150],
        })

    # 1b. Last pending entry (needs scoring by current cycle)
    pending_row = await pool.fetchrow(
        """SELECT id, cycle_ts, reasoning, decisions, expected
           FROM reasoning_chain
           WHERE heartbeat_type = $1
             AND outcome_match = 'pending'
           ORDER BY cycle_ts DESC
           LIMIT 1""",
        heartbeat_type,
    )
    last_pending = None
    if pending_row:
        last_pending = {
            "id": str(pending_row["id"]),
            "when": pending_row["cycle_ts"].isoformat(),
            "expected": (pending_row["expected"] or "")[:300],
            "decisions": (pending_row["decisions"] or "")[:200],
        }

    # 2. Active reasoning_chain principles (high confidence)
    principles = await pool.fetch(
        """SELECT principle, confidence, times_applied, times_violated
           FROM principles
           WHERE category = 'reasoning_chain' AND confidence > 0.3
           ORDER BY confidence DESC, times_applied DESC
           LIMIT $1""",
        principle_limit,
    )

    principle_briefs = [
        {
            "rule": p["principle"],
            "confidence": p["confidence"],
            "applied": p["times_applied"],
            "violated": p["times_violated"],
        }
        for p in principles
    ]

    # 3. Quick accuracy stats (last 20 resolved entries)
    acc_rows = await pool.fetch(
        """SELECT outcome_match FROM reasoning_chain
           WHERE heartbeat_type = $1 AND outcome_match != 'pending'
           ORDER BY cycle_ts DESC LIMIT 20""",
        heartbeat_type,
    )
    total = len(acc_rows)
    matched = sum(1 for r in acc_rows if r["outcome_match"] == "matched")
    accuracy_pct = round(matched / total * 100, 1) if total > 0 else 0.0

    # Build guidance
    guidance_parts = []
    if last_pending:
        guidance_parts.append(
            f"SCORE PREVIOUS PREDICTION: Entry {last_pending['id']} is pending. "
            f"Compare expected outcome vs what actually happened, then PUT /reasoning/{last_pending['id']}/outcome."
        )
    if miss_briefs:
        guidance_parts.append(
            "Review recent misses before making predictions. "
            "Apply active principles. Track if your accuracy is improving."
        )
    if not guidance_parts:
        guidance_parts.append("No recent misses — predictions are on track.")

    return {
        "recent_misses": miss_briefs,
        "last_pending": last_pending,
        "active_principles": principle_briefs,
        "accuracy": {
            "last_20": {"total": total, "matched": matched, "accuracy_pct": accuracy_pct},
        },
        "guidance": " ".join(guidance_parts),
    }


def _extract_condition(reasoning: str, decisions: str) -> str:
    """Extract a short condition phrase from reasoning/decisions for principle text."""
    # Use first meaningful clause from reasoning, capped for readability
    text = reasoning or decisions or "making a prediction"
    # Take first sentence or first 80 chars
    first_sentence = text.split(".")[0].strip()
    if len(first_sentence) > 80:
        first_sentence = first_sentence[:77] + "..."
    return first_sentence.lower()


def _text_overlap(a: str, b: str) -> float:
    """Simple word-level Jaccard similarity for dedup check."""
    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


# ── Catch-all UUID routes (must be LAST to avoid shadowing named routes) ──


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

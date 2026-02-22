"""JitRL: Just-In-Time Reinforcement Learning.

arXiv:2601.18510 (Yibo Li et al., Jan 2026)

Training-free framework for test-time policy optimization in LLM agents.
Core mechanism:
  1. Store experience tuples: (state, action, reward, outcome)
  2. At inference: embed current context, retrieve k most similar past states
  3. Group by action_type, compute advantage = avg_reward - baseline
  4. Apply additive update: policy_weight ∝ exp(advantage / β)
     (exact closed-form solution to KL-constrained policy optimization)
  5. Return ranked action recommendations — no gradient updates required

Integrated into Otto's task execution loop for continual adaptation.
"""

import math
from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import (
    JitRLExperienceCreate, JitRLExperienceOut,
    JitRLOptimizeRequest, JitRLOptimizeResponse, JitRLRecommendation,
)

router = APIRouter(prefix="/jitrl", tags=["jitrl"])

_COLS = """id, state_description, context_tags, action, action_type,
           reward, outcome_label, outcome_details, policy_logit, advantage,
           source, source_id, created_at"""


def _row_to_out(row) -> JitRLExperienceOut:
    d = dict(row)
    if d.get("context_tags") is None:
        d["context_tags"] = []
    return JitRLExperienceOut(**d)


# ── Store Experience ───────────────────────────────────────────────

@router.post("/experience", response_model=JitRLExperienceOut, status_code=201)
async def store_experience(body: JitRLExperienceCreate):
    """Store an experience tuple (state, action, reward, outcome).

    Called after any significant action — task completion, QA review,
    heartbeat decision — to build up the non-parametric experience buffer.

    reward: -1.0 (total failure) to +1.0 (full success)
    outcome_label: succeeded | failed | partial | timeout
    action_type: research | implement | fix | deploy | review | plan | generic
    """
    embedding = await get_embedding(body.state_description)
    pool = await get_pool()

    row = await pool.fetchrow(
        f"""INSERT INTO jitrl_experience
               (state_description, state_embedding, context_tags,
                action, action_type, reward, outcome_label, outcome_details,
                policy_logit, source, source_id)
           VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8, $9, $10, $11)
           RETURNING {_COLS}""",
        body.state_description,
        str(embedding),
        body.context_tags or [],
        body.action,
        body.action_type,
        body.reward,
        body.outcome_label,
        body.outcome_details,
        body.policy_logit,
        body.source,
        body.source_id,
    )
    return _row_to_out(row)


# ── Optimize: Test-Time Policy Recommendation ─────────────────────

@router.post("/optimize", response_model=JitRLOptimizeResponse)
async def optimize(body: JitRLOptimizeRequest):
    """Retrieve similar experiences and recommend optimal action via JitRL.

    Algorithm (arXiv:2601.18510 §3):
    1. Embed current context
    2. Retrieve top_k most similar past states (cosine similarity)
    3. Compute baseline = mean reward across all retrieved experiences
    4. For each action_type: advantage = avg_reward(action_type) - baseline
    5. policy_weight = exp(advantage / beta)  — KL-constrained additive update
    6. Return recommendations sorted by policy_weight descending

    beta (temperature): lower = sharper preference for high-advantage actions
    """
    embedding = await get_embedding(body.context)
    pool = await get_pool()

    # Retrieve top_k similar experiences via cosine similarity
    if body.action_type_filter:
        rows = await pool.fetch(
            f"""SELECT {_COLS},
                       1 - (state_embedding <=> $1::vector) AS similarity
                FROM jitrl_experience
                WHERE state_embedding IS NOT NULL
                  AND action_type = $2
                ORDER BY state_embedding <=> $1::vector
                LIMIT $3""",
            str(embedding), body.action_type_filter, body.top_k,
        )
    else:
        rows = await pool.fetch(
            f"""SELECT {_COLS},
                       1 - (state_embedding <=> $1::vector) AS similarity
                FROM jitrl_experience
                WHERE state_embedding IS NOT NULL
                ORDER BY state_embedding <=> $1::vector
                LIMIT $2""",
            str(embedding), body.top_k,
        )

    if not rows:
        return JitRLOptimizeResponse(
            context=body.context,
            recommendations=[],
            retrieved_count=0,
            baseline_reward=0.0,
        )

    # Compute baseline (mean reward across retrieved experiences)
    rewards = [float(r["reward"]) for r in rows]
    baseline = sum(rewards) / len(rewards)

    # Group by action_type, collect rewards and representative actions
    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r["action_type"]].append({
            "action": r["action"],
            "reward": float(r["reward"]),
            "outcome_label": r["outcome_label"],
            "similarity": float(r["similarity"]),
        })

    # Build recommendations
    recommendations = []
    for action_type, entries in groups.items():
        avg_reward = sum(e["reward"] for e in entries) / len(entries)
        advantage = avg_reward - baseline
        policy_weight = math.exp(advantage / body.beta)

        # Pick representative action: highest reward among entries
        best = max(entries, key=lambda e: (e["reward"], e["similarity"]))
        success_count = sum(
            1 for e in entries if e["outcome_label"] in ("succeeded", "partial")
        )

        recommendations.append(JitRLRecommendation(
            action_type=action_type,
            representative_action=best["action"],
            advantage=round(advantage, 4),
            policy_weight=round(policy_weight, 4),
            support_count=len(entries),
            avg_reward=round(avg_reward, 4),
            success_rate=round(success_count / len(entries), 3),
        ))

    # Sort by policy_weight descending (highest advantage first)
    recommendations.sort(key=lambda r: r.policy_weight, reverse=True)

    return JitRLOptimizeResponse(
        context=body.context,
        recommendations=recommendations,
        retrieved_count=len(rows),
        baseline_reward=round(baseline, 4),
    )


# ── Stats ──────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Experience memory statistics."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT
               COUNT(*) as total_experiences,
               COUNT(DISTINCT action_type) as action_types,
               AVG(reward) as avg_reward,
               COUNT(*) FILTER (WHERE outcome_label = 'succeeded') as succeeded,
               COUNT(*) FILTER (WHERE outcome_label = 'failed') as failed,
               COUNT(*) FILTER (WHERE outcome_label = 'partial') as partial,
               COUNT(*) FILTER (WHERE outcome_label = 'timeout') as timeout,
               COUNT(*) FILTER (WHERE state_embedding IS NOT NULL) as with_embeddings,
               MAX(created_at) as last_experience_at
           FROM jitrl_experience"""
    )
    d = dict(row)
    d["avg_reward"] = round(float(d["avg_reward"]), 4) if d["avg_reward"] else 0.0
    return d


@router.get("/recent", response_model=list[JitRLExperienceOut])
async def get_recent(
    limit: int = Query(default=10, ge=1, le=50),
    action_type: str | None = Query(default=None),
    outcome_label: str | None = Query(default=None),
):
    """Return most recent experience entries, optionally filtered."""
    pool = await get_pool()

    filters, params = [], []
    if action_type:
        params.append(action_type)
        filters.append(f"action_type = ${len(params)}")
    if outcome_label:
        params.append(outcome_label)
        filters.append(f"outcome_label = ${len(params)}")

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    params.append(limit)

    rows = await pool.fetch(
        f"""SELECT {_COLS} FROM jitrl_experience
            {where}
            ORDER BY created_at DESC
            LIMIT ${len(params)}""",
        *params,
    )
    return [_row_to_out(r) for r in rows]


@router.get("/action-types")
async def get_action_type_summary():
    """Return reward statistics grouped by action type."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT
               action_type,
               COUNT(*) as count,
               AVG(reward) as avg_reward,
               MAX(reward) as max_reward,
               MIN(reward) as min_reward,
               COUNT(*) FILTER (WHERE outcome_label = 'succeeded') as succeeded,
               COUNT(*) FILTER (WHERE outcome_label = 'failed') as failed
           FROM jitrl_experience
           GROUP BY action_type
           ORDER BY avg_reward DESC"""
    )
    return [
        {
            **dict(r),
            "avg_reward": round(float(r["avg_reward"]), 4) if r["avg_reward"] else 0.0,
            "success_rate": round(r["succeeded"] / r["count"], 3) if r["count"] > 0 else 0.0,
        }
        for r in rows
    ]


# ── Bootstrap: ingest task outcomes as experiences ─────────────────

@router.post("/ingest-task/{task_id}", response_model=JitRLExperienceOut, status_code=201)
async def ingest_task_as_experience(task_id: UUID):
    """Convert a completed task into a JitRL experience entry.

    Reads task from the tasks table, maps status → reward, embeds the
    task title+prompt as the state description, stores the experience.

    Reward mapping:
      completed → +1.0 (succeeded)
      failed    → -0.5 (failed, not catastrophic)
      timeout   → -0.3 (timeout)
      other     → 0.0 (unknown)
    """
    pool = await get_pool()
    task = await pool.fetchrow(
        """SELECT id, title, prompt, status, priority, model,
                  output, created_at, completed_at
           FROM tasks WHERE id = $1""",
        task_id,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    status = task["status"]
    if status not in ("completed", "failed", "timeout"):
        raise HTTPException(
            status_code=422,
            detail=f"Task status '{status}' has no reward signal (need completed/failed/timeout)"
        )

    reward_map = {"completed": 1.0, "failed": -0.5, "timeout": -0.3}
    outcome_map = {"completed": "succeeded", "failed": "failed", "timeout": "timeout"}

    reward = reward_map.get(status, 0.0)
    outcome_label = outcome_map.get(status, "unknown")

    # State = task description; action = what was attempted
    state = f"Task: {task['title']}"
    if task["prompt"]:
        state += f"\nContext: {task['prompt'][:500]}"

    # Infer action_type from title keywords
    title_lower = (task["title"] or "").lower()
    action_type = "generic"
    for kw, atype in [
        ("research", "research"), ("sweep", "research"), ("implement", "implement"),
        ("fix", "fix"), ("deploy", "deploy"), ("review", "review"),
        ("build", "implement"), ("create", "implement"), ("test", "review"),
        ("plan", "plan"), ("analyse", "plan"), ("analyze", "plan"),
    ]:
        if kw in title_lower:
            action_type = atype
            break

    embedding = await get_embedding(state)
    row = await pool.fetchrow(
        f"""INSERT INTO jitrl_experience
               (state_description, state_embedding, context_tags,
                action, action_type, reward, outcome_label, outcome_details,
                source, source_id)
           VALUES ($1, $2::vector, $3, $4, $5, $6, $7, $8, $9, $10)
           RETURNING {_COLS}""",
        state,
        str(embedding),
        [f"priority:{task['priority']}", f"model:{task['model']}"],
        task["title"],
        action_type,
        reward,
        outcome_label,
        f"Task status: {status}. Output preview: {str(task['output'] or '')[:200]}",
        "task",
        task_id,
    )
    return _row_to_out(row)

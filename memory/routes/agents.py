"""
Agent prompt self-tuning + Caller Profiler (STEM Agent 2603.22359).

- Tuning: Analyzes task history to propose targeted improvements to agent .md prompts.
  Proposals are stored in agent_tuning table and NEVER auto-applied.
- Profiler: Tracks tool usage patterns per agent_type for behavioral profiling.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_pool
from ..config import settings
from ..llm import llm_chat, extract_json_array

log = logging.getLogger("otto.agents")
router = APIRouter(prefix="/agents", tags=["agents"])

# Absolute paths to agent prompt files
AGENT_FILES = {
    "heartbeat": Path("/home/web3relic/otto/.claude/agents/heartbeat.md"),
    "reflection": Path("/home/web3relic/otto/.claude/agents/reflection.md"),
    "alpha_heartbeat": Path("/home/web3relic/otto/.claude/agents/alpha_heartbeat.md"),
}


# ── Pydantic models ─────────────────────────────────────────────────

class TuningProposal(BaseModel):
    id: UUID
    agent_name: str
    proposed_change: str
    rationale: str
    applied: bool
    applied_at: Optional[str]
    created_at: str


class TuneResponse(BaseModel):
    proposals_created: int
    proposals: list[TuningProposal]
    analysis_summary: str


# ── Helpers ──────────────────────────────────────────────────────────

def _row_to_proposal(row: dict) -> TuningProposal:
    return TuningProposal(
        id=row["id"],
        agent_name=row["agent_name"],
        proposed_change=row["proposed_change"],
        rationale=row["rationale"],
        applied=row["applied"],
        applied_at=row["applied_at"].isoformat() if row["applied_at"] else None,
        created_at=row["created_at"].isoformat(),
    )


async def _generate_proposals_with_gemini(
    task_history: list[dict],
    agent_name: str,
    agent_content: str,
) -> list[dict]:
    """
    Ask Gemini Flash to analyze task history and propose specific prompt improvements.
    Returns list of {proposed_change, rationale} dicts.
    """
    if not settings.kimi_api_key:
        log.warning("KIMI_API_KEY not set — skipping LLM-based proposal generation")
        return []

    # Build compact task summary
    completed = [t for t in task_history if t.get("status") == "completed"]
    failed = [t for t in task_history if t.get("status") == "failed"]

    failure_lines = []
    for t in failed:
        exit_code = t.get("exit_code")
        title = t.get("title", "")[:80]
        output_snippet = str(t.get("output") or t.get("error") or "")[:200]
        failure_lines.append(f"  - [{exit_code}] {title}: {output_snippet}")

    success_lines = [f"  - {t.get('title','')[:80]}" for t in completed[:10]]

    failure_summary = "\n".join(failure_lines) if failure_lines else "  (none)"
    success_summary = "\n".join(success_lines) if success_lines else "  (none)"

    prompt = f"""You are analyzing the performance of an AI agent called Otto to improve its prompt.

Agent: {agent_name}
Task history (last 50):
  Total completed: {len(completed)}
  Total failed: {len(failed)}

FAILURES:
{failure_summary}

RECENT SUCCESSES (sample):
{success_summary}

Current agent prompt (first 3000 chars):
---
{agent_content[:3000]}
---

Based on the failure patterns above, propose 2-4 SPECIFIC, ACTIONABLE improvements to the agent prompt.

Return ONLY a JSON array (no markdown, no code fences). Each item must have:
- "proposed_change": the exact text to ADD to the prompt (or instruction to change a specific section). Must be specific, not vague.
- "rationale": which failure pattern this addresses and why

Rules:
- Changes must be specific (e.g. "Add this check before creating tasks: ...") not vague (e.g. "be more careful")
- Each proposal should address ONE concrete failure mode
- If a failure mode is exit_code=124 (timeout), propose scoping/sizing changes
- If exit_code=None (never started), propose process lifecycle checks
- Maximum 4 proposals
- Return [] if there are no clear failure patterns

Example format:
[
  {{
    "proposed_change": "Before launching any task with timeout_seconds < 300, add: 'NOTE: This task has a short timeout. Scope tightly — deliver ONE thing.' to the task prompt.",
    "rationale": "3 tasks failed with exit_code=124 (timeout). They had ambitious scope (research + implement) but short timeouts. Splitting scope or extending timeouts prevents this."
  }}
]"""

    try:
        response = await llm_chat([{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.2)
        parsed = extract_json_array(response)
        if not parsed:
            return []
        if not isinstance(parsed, list):
            return []
        return [
            {"proposed_change": str(p["proposed_change"]), "rationale": str(p["rationale"])}
            for p in parsed
            if "proposed_change" in p and "rationale" in p
        ]
    except Exception as e:
        log.error(f"Gemini proposal generation failed for {agent_name}: {e}")
        return []


def _analyze_failure_patterns(task_history: list[dict]) -> dict:
    """Rule-based analysis of failure patterns (fallback / supplement to Gemini)."""
    failed = [t for t in task_history if t.get("status") == "failed"]
    completed = [t for t in task_history if t.get("status") == "completed"]

    patterns = {
        "timeout_count": sum(1 for t in failed if t.get("exit_code") == 124),
        "silent_fail_count": sum(1 for t in failed if t.get("exit_code") is None),
        "runtime_error_count": sum(1 for t in failed if t.get("exit_code") not in (None, 124) and t.get("exit_code") is not None and t.get("exit_code") != 0),
        "total_failed": len(failed),
        "total_completed": len(completed),
        "success_rate": len(completed) / (len(completed) + len(failed)) if (completed or failed) else 1.0,
    }
    return patterns


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/tune", response_model=TuneResponse)
async def run_tuning_pass(agents: Optional[list[str]] = None):
    """
    Analyze task history and generate prompt improvement proposals via Gemini Flash.

    Stores proposals in agent_tuning table. Does NOT auto-apply anything.

    Args:
        agents: list of agent names to tune. Defaults to ["heartbeat", "reflection"].
    """
    if agents is None:
        agents = ["heartbeat", "reflection"]

    pool = await get_pool()

    # Fetch last 50 tasks
    rows = await pool.fetch(
        """SELECT id, title, status, exit_code, output, error, model, priority,
                  max_budget_usd, timeout_seconds, created_at, completed_at
           FROM tasks
           ORDER BY created_at DESC
           LIMIT 50"""
    )
    task_history = [dict(r) for r in rows]

    patterns = _analyze_failure_patterns(task_history)
    analysis_summary = (
        f"Tasks analyzed: {len(task_history)} | "
        f"Completed: {patterns['total_completed']} | "
        f"Failed: {patterns['total_failed']} | "
        f"Success rate: {patterns['success_rate']:.1%} | "
        f"Timeouts: {patterns['timeout_count']} | "
        f"Silent fails: {patterns['silent_fail_count']} | "
        f"Runtime errors: {patterns['runtime_error_count']}"
    )

    all_proposals = []

    for agent_name in agents:
        agent_path = AGENT_FILES.get(agent_name)
        if not agent_path or not agent_path.exists():
            log.warning(f"Agent file not found for '{agent_name}': {agent_path}")
            continue

        agent_content = agent_path.read_text()

        # Generate proposals with Gemini
        raw_proposals = await _generate_proposals_with_gemini(
            task_history, agent_name, agent_content
        )

        # Store proposals in DB
        for prop in raw_proposals:
            row = await pool.fetchrow(
                """INSERT INTO agent_tuning (agent_name, proposed_change, rationale)
                   VALUES ($1, $2, $3)
                   RETURNING id, agent_name, proposed_change, rationale, applied, applied_at, created_at""",
                agent_name,
                prop["proposed_change"],
                prop["rationale"],
            )
            all_proposals.append(_row_to_proposal(dict(row)))

    log.info(f"Tuning pass complete: {len(all_proposals)} proposals created for {agents}")

    return TuneResponse(
        proposals_created=len(all_proposals),
        proposals=all_proposals,
        analysis_summary=analysis_summary,
    )


@router.get("/tune/proposals", response_model=list[TuningProposal])
async def list_proposals(applied: Optional[bool] = None, agent_name: Optional[str] = None):
    """
    List tuning proposals.

    Args:
        applied: filter by applied status (True/False). None = all.
        agent_name: filter by agent name.
    """
    pool = await get_pool()

    conditions = []
    args = []
    i = 1

    if applied is not None:
        conditions.append(f"applied = ${i}")
        args.append(applied)
        i += 1
    if agent_name:
        conditions.append(f"agent_name = ${i}")
        args.append(agent_name)
        i += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = await pool.fetch(
        f"""SELECT id, agent_name, proposed_change, rationale, applied, applied_at, created_at
            FROM agent_tuning {where}
            ORDER BY created_at DESC""",
        *args,
    )
    return [_row_to_proposal(dict(r)) for r in rows]


@router.post("/tune/{proposal_id}/apply")
async def apply_proposal(proposal_id: UUID):
    """
    Apply a tuning proposal to the agent's .md file.

    Appends the proposed_change as a new section at the end of the agent prompt
    under a ## Agent Tuning Notes section.

    This is a MANUAL action — the heartbeat calls this after reviewing proposals.
    """
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT * FROM agent_tuning WHERE id = $1",
        proposal_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Proposal not found")

    proposal = dict(row)

    if proposal["applied"]:
        raise HTTPException(status_code=409, detail="Proposal already applied")

    agent_name = proposal["agent_name"]
    agent_path = AGENT_FILES.get(agent_name)

    if not agent_path or not agent_path.exists():
        raise HTTPException(
            status_code=422,
            detail=f"Agent file not found for '{agent_name}': {agent_path}",
        )

    # Read current content
    current_content = agent_path.read_text()

    # Build the appended note
    prop_id_short = str(proposal_id)[:8]
    note = (
        f"\n\n---\n\n"
        f"## Agent Tuning Note [{prop_id_short}]\n\n"
        f"**Rationale:** {proposal['rationale']}\n\n"
        f"**Applied instruction:**\n\n{proposal['proposed_change']}\n"
    )

    # Safety check: don't apply if the note is already in the file
    if prop_id_short in current_content:
        raise HTTPException(status_code=409, detail="Proposal content appears to already be in the agent file")

    # Append the note
    new_content = current_content.rstrip() + note
    agent_path.write_text(new_content)

    # Mark as applied in DB
    await pool.execute(
        "UPDATE agent_tuning SET applied = TRUE, applied_at = now() WHERE id = $1",
        proposal_id,
    )

    log.info(f"Applied tuning proposal {proposal_id} to {agent_name}.md")

    return {
        "status": "applied",
        "proposal_id": str(proposal_id),
        "agent_name": agent_name,
        "agent_file": str(agent_path),
    }


@router.delete("/tune/{proposal_id}")
async def dismiss_proposal(proposal_id: UUID):
    """Dismiss (delete) a proposal without applying it."""
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM agent_tuning WHERE id = $1 AND applied = FALSE",
        proposal_id,
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Proposal not found or already applied")
    return {"status": "dismissed", "proposal_id": str(proposal_id)}


# ── Agent Activity Log ────────────────────────────────────────────────────────

@router.get("/activity")
async def get_agent_activity(
    agent_id: Optional[str] = None,
    event_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Paginated agent activity log for OMS display."""
    pool = await get_pool()

    conditions = []
    args: list = []
    idx = 1

    if agent_id:
        conditions.append(f"agent_id = ${idx}")
        args.append(agent_id)
        idx += 1
    if event_type:
        conditions.append(f"event_type = ${idx}")
        args.append(event_type)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    total_row = await pool.fetchrow(
        f"SELECT COUNT(*) AS n FROM agent_activity_log {where}", *args
    )
    total = total_row["n"] if total_row else 0

    rows = await pool.fetch(
        f"""
        SELECT id, agent_id, event_type, details, created_at
        FROM agent_activity_log
        {where}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *args, limit, offset,
    )

    entries = [
        {
            "id": str(r["id"]),
            "agent_id": r["agent_id"],
            "event_type": r["event_type"],
            "details": json.loads(r["details"]) if isinstance(r["details"], str) else (r["details"] or {}),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]

    return {"total": total, "entries": entries}


# ── Caller Profiler (STEM Agent 2603.22359) ────────────────────────


class ToolUsageLog(BaseModel):
    agent_type: str
    tool_name: str
    success: bool = True
    latency_ms: float | None = None
    session_id: str | None = None
    task_id: str | None = None


class ToolUsageBatch(BaseModel):
    entries: list[ToolUsageLog]


@router.post("/tool-usage")
async def log_tool_usage(req: ToolUsageLog):
    """Log a single tool invocation for an agent."""
    pool = await get_pool()
    await _upsert_tool_usage(pool, req)
    return {"status": "ok"}


@router.post("/tool-usage/batch")
async def log_tool_usage_batch(req: ToolUsageBatch):
    """Log multiple tool invocations at once (post-task bulk upload)."""
    pool = await get_pool()
    for entry in req.entries:
        await _upsert_tool_usage(pool, entry)
    return {"status": "ok", "logged": len(req.entries)}


@router.get("/tool-usage/profile")
async def get_agent_profile(
    agent_type: str = Query(..., description="Agent type to profile"),
):
    """Get tool usage profile for a specific agent type."""
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT tool_name, invocation_count, success_count, failure_count,
                  avg_latency_ms, last_used
           FROM agent_tool_usage
           WHERE agent_type = $1
           ORDER BY invocation_count DESC""",
        agent_type,
    )

    total_invocations = sum(r["invocation_count"] for r in rows)
    total_successes = sum(r["success_count"] for r in rows)

    return {
        "agent_type": agent_type,
        "total_tools": len(rows),
        "total_invocations": total_invocations,
        "overall_success_rate": (
            total_successes / total_invocations if total_invocations > 0 else 0.0
        ),
        "tools": [
            {
                "tool_name": r["tool_name"],
                "invocations": r["invocation_count"],
                "success_rate": (
                    r["success_count"] / r["invocation_count"]
                    if r["invocation_count"] > 0
                    else 0.0
                ),
                "avg_latency_ms": r["avg_latency_ms"],
                "last_used": r["last_used"].isoformat() if r["last_used"] else None,
            }
            for r in rows
        ],
    }


@router.get("/tool-usage/anomalies")
async def detect_tool_anomalies(
    min_invocations: int = Query(5, description="Minimum invocations to consider"),
):
    """Detect unusual tool usage patterns across agents.

    Flags:
    - High failure rates (>30% failure on 5+ invocations)
    - Unusually slow tools (>2x average latency)
    - Abandoned tools (not used in 7+ days with 10+ prior uses)
    """
    pool = await get_pool()

    # High failure rate
    high_failure = await pool.fetch(
        """SELECT agent_type, tool_name, invocation_count, failure_count,
                  ROUND(failure_count::numeric / NULLIF(invocation_count, 0), 2) AS failure_rate
           FROM agent_tool_usage
           WHERE invocation_count >= $1
             AND failure_count::float / NULLIF(invocation_count, 0) > 0.30
           ORDER BY failure_count DESC
           LIMIT 20""",
        min_invocations,
    )

    # Slow tools (>2x average latency)
    avg_latency = await pool.fetchval(
        "SELECT AVG(avg_latency_ms) FROM agent_tool_usage WHERE avg_latency_ms IS NOT NULL"
    )

    slow_tools = []
    if avg_latency and avg_latency > 0:
        slow_tools = await pool.fetch(
            """SELECT agent_type, tool_name, avg_latency_ms, invocation_count
               FROM agent_tool_usage
               WHERE avg_latency_ms > $1 * 2
                 AND invocation_count >= $2
               ORDER BY avg_latency_ms DESC
               LIMIT 10""",
            avg_latency, min_invocations,
        )

    # Abandoned tools
    abandoned = await pool.fetch(
        """SELECT agent_type, tool_name, invocation_count, last_used
           FROM agent_tool_usage
           WHERE invocation_count >= 10
             AND last_used < NOW() - INTERVAL '7 days'
           ORDER BY invocation_count DESC
           LIMIT 10""",
    )

    return {
        "high_failure_rate": [
            {
                "agent_type": r["agent_type"],
                "tool_name": r["tool_name"],
                "failure_rate": float(r["failure_rate"]) if r["failure_rate"] else 0,
                "invocations": r["invocation_count"],
            }
            for r in high_failure
        ],
        "slow_tools": [
            {
                "agent_type": r["agent_type"],
                "tool_name": r["tool_name"],
                "avg_latency_ms": r["avg_latency_ms"],
                "global_avg_ms": round(avg_latency, 1) if avg_latency else None,
            }
            for r in slow_tools
        ],
        "abandoned_tools": [
            {
                "agent_type": r["agent_type"],
                "tool_name": r["tool_name"],
                "invocations": r["invocation_count"],
                "last_used": r["last_used"].isoformat() if r["last_used"] else None,
            }
            for r in abandoned
        ],
    }


@router.get("/tool-usage/summary")
async def tool_usage_summary():
    """High-level tool usage summary across all agents."""
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT agent_type,
                  COUNT(*) AS tools_used,
                  SUM(invocation_count) AS total_invocations,
                  SUM(success_count) AS total_successes,
                  AVG(avg_latency_ms) AS avg_latency
           FROM agent_tool_usage
           GROUP BY agent_type
           ORDER BY SUM(invocation_count) DESC"""
    )

    return [
        {
            "agent_type": r["agent_type"],
            "tools_used": r["tools_used"],
            "total_invocations": r["total_invocations"],
            "success_rate": (
                float(r["total_successes"]) / float(r["total_invocations"])
                if r["total_invocations"] and r["total_invocations"] > 0
                else 0.0
            ),
            "avg_latency_ms": round(float(r["avg_latency"]), 1) if r["avg_latency"] else None,
        }
        for r in rows
    ]


async def _upsert_tool_usage(pool, entry: ToolUsageLog):
    """Upsert tool usage with exponential moving average for latency."""
    session_id = None
    task_id = None
    try:
        if entry.session_id:
            session_id = UUID(entry.session_id)
        if entry.task_id:
            task_id = UUID(entry.task_id)
    except ValueError:
        pass

    await pool.execute(
        """INSERT INTO agent_tool_usage
               (agent_type, tool_name, invocation_count, success_count, failure_count,
                avg_latency_ms, session_id, task_id, last_used, updated_at)
           VALUES ($1, $2, 1, $3, $4, $5, $6, $7, NOW(), NOW())
           ON CONFLICT (agent_type, tool_name) DO UPDATE SET
               invocation_count = agent_tool_usage.invocation_count + 1,
               success_count = agent_tool_usage.success_count + $3,
               failure_count = agent_tool_usage.failure_count + $4,
               avg_latency_ms = CASE
                   WHEN $5 IS NOT NULL THEN
                       COALESCE(agent_tool_usage.avg_latency_ms, 0) * 0.9 + $5 * 0.1
                   ELSE agent_tool_usage.avg_latency_ms
               END,
               session_id = COALESCE($6, agent_tool_usage.session_id),
               task_id = COALESCE($7, agent_tool_usage.task_id),
               last_used = NOW(),
               updated_at = NOW()""",
        entry.agent_type,
        entry.tool_name,
        1 if entry.success else 0,
        0 if entry.success else 1,
        entry.latency_ms,
        session_id,
        task_id,
    )

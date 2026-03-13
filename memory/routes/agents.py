"""
Agent prompt self-tuning route.

Analyzes task history to propose targeted improvements to agent .md prompts.
Proposals are stored in agent_tuning table and NEVER auto-applied.
The heartbeat reviews proposals and applies them with POST /agents/tune/{id}/apply.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
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

"""Dynamic Tool Composition — STEM Agent-inspired runtime chain assembly.

Backward-chaining algorithm: given a desired output type, find agent chains
that can produce it from the task's inputs. Chains are scored by relevance
to the task description and sorted by (relevance, -length).

Reference: STEM Agent (arXiv 2603.22359) — dynamic tool composition.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("otto.composition")

# ── Output type inference from task keywords ─────────────────────────────────
_OUTPUT_HINTS: dict[str, str] = {
    "build": "code",
    "implement": "code",
    "create": "code",
    "develop": "code",
    "fix": "code",
    "deploy": "code",
    "install": "code",
    "research": "research_report",
    "investigate": "research_report",
    "explore": "research_report",
    "analyze": "research_report",
    "find": "findings",
    "write": "content_draft",
    "draft": "content_draft",
    "article": "content_draft",
    "blog": "content_draft",
    "review": "code_review",
    "audit": "security_report",
    "security": "security_report",
    "design": "architecture_spec",
    "architect": "architecture_spec",
    "plan": "architecture_spec",
    "tweet": "social_content",
    "post": "social_content",
    "social": "social_content",
    "growth": "growth_strategy",
    "debug": "debug_report",
    "diagnose": "debug_report",
}


@dataclass
class CompositionStep:
    agent_type: str
    role: str
    inputs_from: str  # "user" or previous agent_type
    output_type: str


@dataclass
class CompositionChain:
    steps: list[CompositionStep] = field(default_factory=list)
    total_relevance: float = 0.0
    reasoning: str = ""
    incomplete: bool = False  # True when max depth hit with unsatisfied inputs


def _infer_output_type(task_description: str) -> str | None:
    """Infer desired output type from task keywords.

    Scans all matching keywords and picks the longest match (most specific).
    E.g. "create an article" matches both "create"→code and "article"→content_draft;
    "article" (7 chars) > "create" (6 chars) → returns content_draft.
    """
    task_lower = task_description.lower()
    best_keyword = ""
    best_output: str | None = None
    for keyword, output_type in _OUTPUT_HINTS.items():
        if keyword in task_lower and len(keyword) > len(best_keyword):
            best_keyword = keyword
            best_output = output_type
    return best_output


def _agent_produces(agent: dict, output_type: str) -> bool:
    """Check if an agent can produce the given output type."""
    return output_type in agent.get("outputs", [])


def _agent_needs(agent: dict) -> list[str]:
    """Get non-universal input types an agent needs (excluding 'question')."""
    return [i for i in agent.get("inputs", []) if i != "question"]


def _score_agent(agent: dict, task_description: str) -> float:
    """Score agent relevance to task. Delegates to skills._score_skill."""
    from .routes.skills import _score_skill
    return _score_skill(agent, task_description)


def find_compositions(
    task_description: str,
    required_output: str | None = None,
    max_chain_length: int = 3,
    registry: list[dict] | None = None,
) -> list[CompositionChain]:
    """Find multi-agent composition chains for a task.

    Algorithm (backward chaining from desired output):
    1. Infer or use required_output type
    2. Find agents that produce it with relevance > threshold
    3. Walk backwards: for each producer, find agents that produce its inputs
    4. No cycles. Max depth = max_chain_length
    5. Return top 3 chains sorted by (total_relevance, -chain_length)
    """
    if registry is None:
        return []

    # Only compose agent-type skills
    agents = [s for s in registry if s.get("skill_type") == "agent"]
    if not agents:
        return []

    # Determine target output
    target = required_output or _infer_output_type(task_description)
    if not target:
        return []

    # Score all agents against the task
    agent_scores: dict[str, float] = {}
    for a in agents:
        agent_scores[a["name"]] = _score_agent(a, task_description)

    # Build index: output_type -> [agents that produce it]
    producers: dict[str, list[dict]] = {}
    for a in agents:
        for out in a.get("outputs", []):
            producers.setdefault(out, []).append(a)

    # Backward chain search
    chains: list[CompositionChain] = []
    relevance_threshold = 0.1

    def _build_chains(
        current_agent: dict,
        chain_so_far: list[CompositionStep],
        visited: set[str],
        depth: int,
    ):
        """Recursively build chains backwards from current_agent."""
        needed = _agent_needs(current_agent)
        # Filter to inputs not already satisfied by prior steps
        satisfied = set()
        for step in chain_so_far:
            satisfied.add(step.output_type)
        unsatisfied = [n for n in needed if n not in satisfied]

        if not unsatisfied or depth >= max_chain_length:
            # Chain is complete (or max depth) — finalize
            total_rel = sum(
                agent_scores.get(s.agent_type, 0) for s in chain_so_far
            )
            if total_rel > relevance_threshold:
                final_steps = list(chain_so_far)
                incomplete = bool(unsatisfied) and depth >= max_chain_length
                reasoning = " → ".join(s.agent_type for s in final_steps)
                chains.append(CompositionChain(
                    steps=final_steps,
                    total_relevance=round(total_rel, 3),
                    reasoning=reasoning,
                    incomplete=incomplete,
                ))
            return

        # Try to find producers for unsatisfied inputs
        for input_type in unsatisfied:
            for producer in producers.get(input_type, []):
                if producer["name"] in visited:
                    continue  # No cycles
                if agent_scores.get(producer["name"], 0) < relevance_threshold:
                    continue

                step = CompositionStep(
                    agent_type=producer["agent_type"],
                    role=producer["name"],
                    inputs_from="user",  # Will be corrected in finalization
                    output_type=input_type,
                )
                new_chain = [step] + list(chain_so_far)
                new_visited = visited | {producer["name"]}
                _build_chains(producer, new_chain, new_visited, depth + 1)

    # Start from agents that produce the target output
    for producer in producers.get(target, []):
        if agent_scores.get(producer["name"], 0) < relevance_threshold:
            continue

        terminal_step = CompositionStep(
            agent_type=producer["agent_type"],
            role=producer["name"],
            inputs_from="user",
            output_type=target,
        )
        visited = {producer["name"]}
        _build_chains(producer, [terminal_step], visited, 1)

    # Deduplicate by reasoning string, sort by relevance desc then length asc
    seen_reasoning: set[str] = set()
    unique_chains: list[CompositionChain] = []
    for c in chains:
        if c.reasoning not in seen_reasoning:
            seen_reasoning.add(c.reasoning)
            unique_chains.append(c)

    unique_chains.sort(key=lambda c: (-c.total_relevance, len(c.steps)))

    # Fix inputs_from for multi-step chains
    for chain in unique_chains:
        for i, step in enumerate(chain.steps):
            if i == 0:
                chain.steps[i] = CompositionStep(
                    agent_type=step.agent_type,
                    role=step.role,
                    inputs_from="user",
                    output_type=step.output_type,
                )
            else:
                chain.steps[i] = CompositionStep(
                    agent_type=step.agent_type,
                    role=step.role,
                    inputs_from=chain.steps[i - 1].agent_type,
                    output_type=step.output_type,
                )

    # Filter: only return multi-step chains (single-step = no composition needed)
    multi_step = [c for c in unique_chains if len(c.steps) > 1]

    return multi_step[:3]

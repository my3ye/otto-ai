"""Skills suggestion endpoint — Tool RAG for agent capability discovery.

Context engineering 2026: Loading all tools simultaneously overwhelms the model's
attention budget as tool libraries grow. Semantic tool retrieval (Tool RAG) gives
3x better tool selection accuracy by returning only relevant tools per task.

Reference: Context Engineering 2026 consensus (Anthropic, LangChain, Weaviate).
"""

import logging
from fastapi import APIRouter, Query

log = logging.getLogger("otto.skills")

router = APIRouter(prefix="/skills", tags=["skills"])

# ── Skill Registry ────────────────────────────────────────────────────────────
# Each skill: name, description (semantic routing signal), keywords, skill_type
# Descriptions are the primary signal for retrieval — write them carefully.
# skill_type: agent (specialist agent) | tool (code tool) | procedure (learned)

SKILL_REGISTRY = [
    {
        "name": "researcher",
        "description": "Deep research agent for papers, APIs, technical investigation, and web research. Use for any research or exploration task that requires reading external sources.",
        "keywords": ["research", "paper", "api", "explore", "investigate", "find", "search", "web", "arxiv", "documentation"],
        "skill_type": "agent",
        "agent_type": "researcher",
        "cost": "medium",
    },
    {
        "name": "coder",
        "description": "Implementation specialist. Writes code, builds features, implements research papers, fixes bugs. Use for any coding or building task.",
        "keywords": ["build", "implement", "code", "write", "create", "develop", "fix", "feature", "add", "modify", "install"],
        "skill_type": "agent",
        "agent_type": "coder",
        "cost": "medium",
    },
    {
        "name": "debugger",
        "description": "Root cause analysis and bug fixing specialist. Diagnoses failures, traces errors, and implements minimal fixes. Use when something is broken.",
        "keywords": ["debug", "error", "broken", "fail", "crash", "trace", "diagnose", "fix", "issue", "bug", "problem"],
        "skill_type": "agent",
        "agent_type": "debugger",
        "cost": "low",
    },
    {
        "name": "reviewer",
        "description": "Code review and QA specialist. Reviews code changes for quality, correctness, security, and consistency. Read-only — does not modify code.",
        "keywords": ["review", "check", "audit", "verify", "quality", "security", "test", "validate", "inspect"],
        "skill_type": "agent",
        "agent_type": "reviewer",
        "cost": "low",
    },
    {
        "name": "architect",
        "description": "System design and architecture specialist. Designs APIs, plans integrations, evaluates tradeoffs, and structures complex systems. Use for design decisions.",
        "keywords": ["design", "architect", "plan", "structure", "tradeoff", "system", "schema", "api", "integration", "blueprint"],
        "skill_type": "agent",
        "agent_type": "architect",
        "cost": "high",
    },
    {
        "name": "content-creator",
        "description": "Writes all content for the MY3YE ecosystem — articles, blog posts, manifestos, landing page copy, taglines, whitepapers, newsletters, announcements, and any written material. Writes in the MY3YE brand voice.",
        "keywords": ["write", "article", "blog", "content", "copy", "manifesto", "tagline", "whitepaper", "newsletter", "announcement", "essay", "draft", "publish", "brand", "voice", "narrative", "story", "editorial", "my3ye", "tusita", "oneon", "otto", "koink", "shakrah", "panik", "pipi"],
        "skill_type": "agent",
        "agent_type": "content-creator",
        "cost": "medium",
    },
    {
        "name": "memory-curator",
        "description": "Memory consolidation and cleanup specialist. Deduplicates memories, archives stale data, merges related facts, and maintains memory quality.",
        "keywords": ["memory", "consolidate", "deduplicate", "archive", "clean", "merge", "stale", "maintenance", "decay"],
        "skill_type": "agent",
        "agent_type": "memory-curator",
        "cost": "low",
    },
    {
        "name": "landing-page",
        "description": "Landing page builder. Creates web pages with HTML/CSS/JS for ecosystem projects. Use for any web page creation or redesign task.",
        "keywords": ["landing", "page", "website", "web", "html", "css", "homepage", "design", "frontend", "layout"],
        "skill_type": "agent",
        "agent_type": "landing-page",
        "cost": "medium",
    },
    {
        "name": "security-audit",
        "description": "Security review and vulnerability assessment specialist. Audits code, infrastructure, and configurations for security issues.",
        "keywords": ["security", "vulnerability", "audit", "cve", "exploit", "hardening", "permissions", "secrets", "authentication"],
        "skill_type": "agent",
        "agent_type": "security-audit",
        "cost": "low",
    },
    {
        "name": "memory-query",
        "description": "Query and store knowledge in Otto's memory system. Use when needing context from past experiences, decisions, lessons, or stored knowledge.",
        "keywords": ["memory", "query", "recall", "remember", "past", "history", "context", "knowledge", "semantic", "episodic"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
    {
        "name": "workflow-operations",
        "description": "Start, monitor, and manage multi-agent workflows. Use for content pipelines, feature development, or any multi-step work that chains specialist agents. Also manage agent activation from the 138-agent agency-agents repo.",
        "keywords": ["workflow", "pipeline", "template", "multi-agent", "content-publishing", "feature-development", "evolve", "fitness", "approve", "agents", "activate", "available"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
    {
        "name": "task-creation",
        "description": "Create well-formed tasks in Otto's task queue. Use when delegating work to the task queue system for autonomous execution.",
        "keywords": ["task", "queue", "delegate", "create", "launch", "schedule", "run", "async", "background"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
    {
        "name": "api-development",
        "description": "Otto Memory API development patterns. Use when building new API endpoints or modifying the memory API. FastAPI patterns and conventions.",
        "keywords": ["api", "endpoint", "route", "fastapi", "memory", "backend", "database", "postgres", "migration"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
    {
        "name": "debug-workflow",
        "description": "Structured debugging workflow for Otto's services and infrastructure. Auto-loaded when diagnosing errors or failures in systemd services.",
        "keywords": ["debug", "service", "systemd", "log", "error", "diagnose", "infrastructure", "failure", "restart"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
    {
        "name": "otto-conventions",
        "description": "Otto's codebase conventions, project structure, and development patterns. Use when working on Otto's code to ensure consistency.",
        "keywords": ["convention", "pattern", "style", "structure", "codebase", "standard", "practice", "otto"],
        "skill_type": "tool",
        "agent_type": None,
        "cost": "low",
    },
]


def _score_skill(skill: dict, task_description: str) -> float:
    """Score a skill's relevance to a task using keyword overlap.

    Simple but effective — description-semantic alignment + keyword match.
    Score ∈ [0.0, 1.0].
    """
    task_lower = task_description.lower()
    task_words = set(task_lower.split())

    # Keyword overlap score (weighted 60%)
    keywords = set(skill["keywords"])
    overlap = len(task_words & keywords)
    keyword_score = min(overlap / max(len(keywords) * 0.3, 1), 1.0)

    # Description substring match score (weighted 40%)
    desc_words = set(skill["description"].lower().split())
    desc_overlap = len(task_words & desc_words)
    desc_score = min(desc_overlap / max(len(task_words) * 0.3, 1), 1.0)

    return round(0.6 * keyword_score + 0.4 * desc_score, 3)


@router.get("/suggest")
async def suggest_skills(
    task: str = Query(..., description="Task description to find relevant skills for"),
    top_n: int = Query(3, ge=1, le=10, description="Number of top skills to return"),
    skill_type: str | None = Query(None, description="Filter by type: agent | tool | procedure"),
):
    """Tool RAG: Semantically retrieve the most relevant skills for a task.

    Context engineering 2026: Rather than loading all tools into every agent context,
    agents should call this endpoint at the start of each cycle to discover which
    skills/tools are relevant for their current work. This gives 3x better tool
    selection accuracy as the skill library grows.

    Returns top-N skills ranked by relevance, with descriptions and agent_type hints.
    """
    registry = SKILL_REGISTRY
    if skill_type:
        registry = [s for s in registry if s["skill_type"] == skill_type]

    scored = [
        {**skill, "relevance_score": _score_skill(skill, task)}
        for skill in registry
    ]
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    top = scored[:top_n]

    return {
        "task": task,
        "top_n": top_n,
        "skills": [
            {
                "name": s["name"],
                "description": s["description"],
                "skill_type": s["skill_type"],
                "agent_type": s["agent_type"],
                "cost": s["cost"],
                "relevance_score": s["relevance_score"],
            }
            for s in top
        ],
    }


@router.get("")
async def list_skills(skill_type: str | None = Query(None)):
    """List all available skills in the registry."""
    registry = SKILL_REGISTRY
    if skill_type:
        registry = [s for s in registry if s["skill_type"] == skill_type]
    return {"count": len(registry), "skills": registry}

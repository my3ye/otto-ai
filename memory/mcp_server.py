"""MCP Server for Otto Memory API.

Exposes 15 curated tools, 4 resources, and 3 prompt templates via
the Model Context Protocol (SSE transport on :8100/mcp).

Each tool is a thin wrapper around existing route logic — no HTTP hop,
shares the asyncpg pool.
"""

import json
import logging
from pathlib import Path
from uuid import UUID

from mcp.server.fastmcp import FastMCP

from .db import get_pool

logger = logging.getLogger("otto.mcp")

mcp = FastMCP(
    "Otto Memory API",
    instructions="Otto's autonomous intelligence tools — memory, tasks, communication, system management",
)


# ── Helper: serialize DB rows / Pydantic models to JSON-friendly dicts ────────

def _serialize(obj) -> str:
    """Convert route responses to JSON string for MCP tool output."""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, list):
        return json.dumps([_to_dict(item) for item in obj], default=str)
    return json.dumps(_to_dict(obj), default=str)


def _to_dict(obj):
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, dict):
        return obj
    return str(obj)


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS (15)
# ═══════════════════════════════════════════════════════════════════════════════


# ── Memory (5) ────────────────────────────────────────────────────────────────

@mcp.tool()
async def semantic_search(query: str, top_k: int = 5, category: str | None = None) -> str:
    """Search Otto's semantic memory for relevant facts and knowledge.

    Args:
        query: Natural language search query
        top_k: Maximum number of results to return (default 5)
        category: Optional category filter (e.g. 'infrastructure', 'project', 'mission')
    """
    from .models import SemanticSearchQuery
    from .routes.semantic import search

    req = SemanticSearchQuery(query=query, limit=top_k, category=category)
    results = await search(req, compress=False)
    return _serialize(results)


@mcp.tool()
async def semantic_remember(content: str, category: str = "observation", confidence: float = 0.8, source: str | None = None) -> str:
    """Store a fact or observation in Otto's semantic memory.

    Args:
        content: The fact or knowledge to remember
        category: Memory category (infrastructure, project, mission, capability, etc.)
        confidence: Confidence level 0.0-1.0 (default 0.8)
        source: Optional source attribution
    """
    from .models import SemanticMemoryCreate
    from .routes.semantic import remember

    req = SemanticMemoryCreate(content=content, category=category, confidence=confidence, source=source)
    result = await remember(req)
    return _serialize(result)


@mcp.tool()
async def graph_search(query: str) -> str:
    """Search Otto's knowledge graph for entities and relationships.

    Args:
        query: Natural language query for the knowledge graph
    """
    import httpx
    from .config import settings

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.graphiti_url}/search",
                json={"query": query},
                timeout=30.0,
            )
            return resp.text
    except Exception as e:
        logger.warning(f"Graph search failed: {e}")
        return json.dumps({"error": f"Knowledge graph unavailable: {e}"})


@mcp.tool()
async def episodic_timeline(limit: int = 20, min_importance: int = 1, event_type: str | None = None) -> str:
    """Query Otto's event history / timeline.

    Args:
        limit: Maximum events to return (default 20)
        min_importance: Minimum importance level 1-10 (default 1)
        event_type: Optional filter by event type
    """
    from .models import TimelineQuery
    from .routes.episodic import get_timeline

    req = TimelineQuery(limit=limit, min_importance=min_importance, event_type=event_type)
    results = await get_timeline(req)
    return _serialize(results)


@mcp.tool()
async def episodic_log(content: str, event_type: str = "observation", importance: int = 5) -> str:
    """Log an event to Otto's episodic memory.

    Args:
        content: Description of the event
        event_type: Type of event (observation, action, decision, error, etc.)
        importance: Importance level 1-10 (default 5)
    """
    from .models import EpisodicEventCreate
    from .routes.episodic import create_event

    req = EpisodicEventCreate(content=content, event_type=event_type, importance=importance)
    result = await create_event(req)
    return _serialize(result)


# ── Tasks (4) ─────────────────────────────────────────────────────────────────

@mcp.tool()
async def task_create(
    title: str,
    prompt: str,
    priority: int = 5,
    agent_type: str | None = None,
    model: str = "sonnet",
    max_budget_usd: float = 5.00,
    working_directory: str = "/home/web3relic/otto",
) -> str:
    """Create a task in Otto's task queue.

    Args:
        title: Short task title
        prompt: Detailed task instructions
        priority: Priority 1-10 (10 = highest)
        agent_type: Specialist agent (coder, researcher, reviewer, debugger, architect, etc.)
        model: LLM model (sonnet, opus, haiku)
        max_budget_usd: Budget limit in USD (default $5)
        working_directory: Working directory for the task
    """
    from .models import TaskCreate
    from .routes.tasks import create_task

    req = TaskCreate(
        title=title,
        prompt=prompt,
        priority=priority,
        agent_type=agent_type,
        model=model,
        max_budget_usd=max_budget_usd,
        working_directory=working_directory,
        created_by="mcp",
    )
    result = await create_task(req)
    return _serialize(result)


@mcp.tool()
async def task_status(task_id: str) -> str:
    """Get the status and output of a specific task.

    Args:
        task_id: UUID of the task to check
    """
    from .routes.tasks import get_task

    result = await get_task(UUID(task_id))
    return _serialize(result)


@mcp.tool()
async def task_queue() -> str:
    """Get a summary of Otto's current task queue — running, pending, and recent completions."""
    from .routes.tasks import queue_status

    result = await queue_status()
    return _serialize(result)


@mcp.tool()
async def task_plan_create(title: str, instruction: str, items: list[dict]) -> str:
    """Create a DAG-based task plan that decomposes one instruction into multiple tasks with dependencies.

    Args:
        title: Plan title
        instruction: The high-level instruction being decomposed
        items: List of plan items, each with: temp_id, title, prompt, agent_type, depends_on (list of temp_ids)
    """
    from .routes.task_plans import create_plan, PlanItemSpec

    pool = await get_pool()
    plan_items = [PlanItemSpec(**item) for item in items]
    plan_id = await create_plan(pool, title=title, instruction=instruction, items=plan_items, created_by="mcp")
    return json.dumps({"plan_id": str(plan_id)})


# ── Communication (2) ─────────────────────────────────────────────────────────

@mcp.tool()
async def whatsapp_send(message: str) -> str:
    """Send a WhatsApp message to Mev (admin only).

    Args:
        message: Message text to send
    """
    import httpx
    from .config import settings

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.whatsapp_url}/send",
                json={"message": message},
                timeout=15.0,
            )
            return resp.text
    except Exception as e:
        logger.warning(f"WhatsApp send failed: {e}")
        return json.dumps({"error": f"WhatsApp unavailable: {e}"})


@mcp.tool()
async def email_send(to: str, subject: str, body: str) -> str:
    """Send an email from Otto (admin@otto.lk).

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
    """
    from .routes.email import send_email, SendRequest

    req = SendRequest(to=to, subject=subject, body=body)
    result = await send_email(req)
    return _serialize(result)


# ── System (2) ────────────────────────────────────────────────────────────────

@mcp.tool()
async def health() -> str:
    """Check Otto's system health — database connectivity and service status."""
    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 as ok")
    return json.dumps({"status": "healthy", "db": row["ok"] == 1})


@mcp.tool()
async def kernel_status() -> str:
    """Get the AgentOS kernel state — queue depth, drift measurements, active providers."""
    from .routes.kernel_routes import kernel_status as _kernel_status

    result = await _kernel_status()
    return _serialize(result)


# ── Content (2) ───────────────────────────────────────────────────────────────

@mcp.tool()
async def skill_suggest(task_description: str) -> str:
    """Find the most relevant Otto skills/agents for a given task description (Tool RAG).

    Args:
        task_description: Description of what needs to be done
    """
    from .routes.skills import suggest_skills

    result = await suggest_skills(task=task_description)
    return _serialize(result)


@mcp.tool()
async def workflow_start(template_name: str, name: str, variables: dict | None = None, priority: int = 5) -> str:
    """Start a multi-agent workflow pipeline.

    Args:
        template_name: Name of the workflow template (e.g. 'content-publishing-pipeline', 'feature-development')
        name: Descriptive name for this workflow instance
        variables: Template variables (content_type, topic, requirements, etc.)
        priority: Priority 1-10 (default 5)
    """
    from .routes.workflows import start_workflow, WorkflowStartRequest

    req = WorkflowStartRequest(
        template_name=template_name,
        name=name,
        variables=variables or {},
        priority=priority,
        working_directory="/home/web3relic/otto",
    )
    result = await start_workflow(req)
    return _serialize(result)


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES (4)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("otto://context/briefing")
async def resource_context_briefing() -> str:
    """Otto's full context aggregation — identity, memory, events, task queue."""
    from .routes.context import get_briefing

    result = await get_briefing()
    return _serialize(result)


@mcp.resource("otto://identity/constitution")
async def resource_constitution() -> str:
    """Otto's constitutional identity spec — mission, boundaries, admin relationship."""
    path = Path("/home/web3relic/otto/CONSTITUTION.md")
    return path.read_text() if path.exists() else "CONSTITUTION.md not found"


@mcp.resource("otto://identity/personality")
async def resource_personality() -> str:
    """Otto's voice, tone, and language patterns."""
    path = Path("/home/web3relic/otto/otto_core/personality.md")
    return path.read_text() if path.exists() else "personality.md not found"


@mcp.resource("otto://tasks/queue")
async def resource_task_queue() -> str:
    """Current task queue state — running, pending, recent completions."""
    from .routes.tasks import queue_status

    result = await queue_status()
    return _serialize(result)


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS (3)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
async def research_task(topic: str, depth: str = "thorough") -> str:
    """Template for creating a well-structured research task.

    Args:
        topic: Research topic or question
        depth: Research depth — 'quick', 'thorough', or 'deep'
    """
    return f"""Create a research task with the following structure:

Title: Research: {topic}
Agent: researcher
Priority: 7

Prompt:
Research the following topic: {topic}

Depth: {depth}
- quick: 15-minute scan, key findings only
- thorough: comprehensive analysis with sources
- deep: multi-source synthesis with actionable recommendations

Output format:
1. Executive summary (3-5 sentences)
2. Key findings (bulleted)
3. Sources and confidence levels
4. Actionable recommendations
5. Open questions / gaps"""


@mcp.prompt()
async def content_pipeline(content_type: str, topic: str, requirements: str = "") -> str:
    """Template for starting a content publishing workflow.

    Args:
        content_type: Type of content (article, blog post, thread, manifesto)
        topic: Content topic
        requirements: Additional requirements or constraints
    """
    return f"""Start a content publishing workflow:

Template: content-publishing-pipeline
Name: {content_type}: {topic}

Variables:
- content_type: {content_type}
- topic: {topic}
- requirements: {requirements or 'Standard MY3YE brand voice. Calm authority, short declarations, poetic but clear.'}

The pipeline will:
1. Content creator drafts the piece
2. Reviewer checks quality and accuracy
3. Content creator applies revisions
4. Coder formats and deploys
5. Notification on completion"""


@mcp.prompt()
async def bug_report(error_description: str, file_path: str = "", steps_to_reproduce: str = "") -> str:
    """Template for creating a debugging task from an error description.

    Args:
        error_description: What went wrong
        file_path: File where the error occurs (if known)
        steps_to_reproduce: Steps to reproduce the issue
    """
    return f"""Create a debugging task:

Title: Fix: {error_description[:60]}
Agent: debugger
Priority: 8

Prompt:
Diagnose and fix the following issue:

Error: {error_description}
{'File: ' + file_path if file_path else ''}
{'Steps to reproduce: ' + steps_to_reproduce if steps_to_reproduce else ''}

Approach:
1. Read the relevant code to understand current behavior
2. Identify the root cause (not just the symptom)
3. Implement the minimal fix
4. Verify the fix works
5. Check for similar patterns elsewhere"""

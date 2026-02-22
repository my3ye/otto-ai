"""Graph bridge — G2CP-style structured cross-brain communication.

Implements Graph-Grounded Context Protocol (G2CP, arXiv 2602.13370):
- Both brains (Claude, Gemini) write typed graph nodes instead of lossy text
- Nodes stored in cross_brain_graph (PostgreSQL) for reliable retrieval
- Also ingested to Graphiti for NLP entity/relationship extraction
- Both brains read the same structured graph layer via context_builder

Node types:
  directive   — mission/behavioral directive from Mev
  decision    — a decision made by Mev or Otto
  task_state  — task status update from Claude brain
  context     — working memory key/value shared between brains
"""

import json
import logging
import uuid
from datetime import datetime, timezone

import httpx
from .config import settings

log = logging.getLogger("otto.graph_bridge")

GRAPHITI_TIMEOUT = 10.0

# Priority map for note types
_NOTE_TYPE_PRIORITY = {
    "mission": 10,
    "priority_change": 9,
    "directive": 8,
    "goal": 8,
    "decision": 7,
    "approval": 7,
    "task": 6,
    "context": 5,
    "general": 4,
}

# Node type classification for cross-brain notes
_NOTE_TYPE_TO_NODE = {
    "mission": "directive",
    "priority_change": "directive",
    "directive": "directive",
    "goal": "directive",
    "approval": "decision",
    "decision": "decision",
    "task": "task_state",
    "context": "context",
}


async def write_directive(
    pool,
    content: str,
    priority: int = 8,
    source: str = "gemini",
    category: str = "directive",
) -> str | None:
    """Write a DirectiveNode to the cross-brain graph.

    Returns the node id (UUID string) on success, None on failure.
    """
    name = content[:100].strip().replace("\n", " ")
    node_content = {
        "text": content,
        "priority": priority,
        "category": category,
    }
    return await _write_node(pool, "directive", name, node_content, source, priority)


async def write_decision(
    pool,
    content: str,
    decided_by: str = "mev",
    context: str | None = None,
    source: str = "gemini",
) -> str | None:
    """Write a DecisionNode to the cross-brain graph.

    Returns the node id on success, None on failure.
    """
    name = content[:100].strip().replace("\n", " ")
    node_content = {
        "text": content,
        "decided_by": decided_by,
        "context": context or "",
    }
    return await _write_node(pool, "decision", name, node_content, source, priority=7)


async def update_task_state(
    pool,
    task_id: str,
    title: str,
    status: str,
    summary: str = "",
    source: str = "claude",
) -> str | None:
    """Upsert a TaskStateNode — deactivates previous nodes for the same task_id.

    Returns the new node id on success, None on failure.
    """
    # Deactivate prior nodes for this task
    try:
        await pool.execute(
            """UPDATE cross_brain_graph
               SET active = FALSE, updated_at = NOW()
               WHERE node_type = 'task_state'
                 AND content->>'task_id' = $1
                 AND active = TRUE""",
            str(task_id),
        )
    except Exception as e:
        log.warning(f"graph_bridge: task state deactivation failed: {e}")

    node_content = {
        "task_id": str(task_id),
        "title": title,
        "status": status,
        "summary": summary,
    }
    return await _write_node(pool, "task_state", title[:100], node_content, source, priority=5)


async def write_context(
    pool,
    key: str,
    value: str,
    source: str = "claude",
) -> str | None:
    """Upsert a ContextNode — deactivates previous nodes for the same key.

    Returns the new node id on success, None on failure.
    """
    # Deactivate prior nodes for this key
    try:
        await pool.execute(
            """UPDATE cross_brain_graph
               SET active = FALSE, updated_at = NOW()
               WHERE node_type = 'context'
                 AND content->>'key' = $1
                 AND active = TRUE""",
            key,
        )
    except Exception as e:
        log.warning(f"graph_bridge: context deactivation failed: {e}")

    node_content = {"key": key, "value": value}
    return await _write_node(pool, "context", key, node_content, source, priority=5)


async def write_from_cross_brain_note(
    pool,
    note_type: str,
    content: str,
    context: str | None = None,
    source: str = "gemini",
) -> str | None:
    """Write a structured graph node from a classified cross-brain note.

    This is the main integration point: called from whatsapp.py when a
    cross-brain note is created. Maps note_type to the appropriate node type
    and write helper.

    Returns the node id on success, None on failure.
    """
    node_type = _NOTE_TYPE_TO_NODE.get(note_type, "context")
    priority = _NOTE_TYPE_PRIORITY.get(note_type, 5)

    if node_type == "directive":
        node_id = await write_directive(pool, content, priority, source, note_type)
    elif node_type == "decision":
        node_id = await write_decision(pool, content, decided_by="mev", context=context, source=source)
    elif node_type == "task_state":
        node_id = await _write_node(
            pool, "task_state", content[:100].strip().replace("\n", " "),
            {"title": content[:200], "status": "requested", "summary": context or ""},
            source, priority,
        )
    else:
        node_id = await _write_node(
            pool, "context", content[:100].strip().replace("\n", " "),
            {"key": note_type, "value": content, "context": context or ""},
            source, priority,
        )

    # Also ingest to Graphiti for NLP entity extraction (fire-and-forget)
    if node_id:
        await _ingest_to_graphiti(node_type, content, source)

    return node_id


async def get_recent_nodes(
    pool,
    node_types: list[str] | None = None,
    limit: int = 20,
) -> list[dict]:
    """Fetch recent active graph nodes, optionally filtered by type.

    Returns list of node dicts sorted by priority DESC, created_at DESC.
    """
    try:
        if node_types:
            rows = await pool.fetch(
                """SELECT id, node_type, name, content, source_brain, priority, created_at
                   FROM cross_brain_graph
                   WHERE active = TRUE AND node_type = ANY($1)
                   ORDER BY priority DESC, created_at DESC
                   LIMIT $2""",
                node_types, limit,
            )
        else:
            rows = await pool.fetch(
                """SELECT id, node_type, name, content, source_brain, priority, created_at
                   FROM cross_brain_graph
                   WHERE active = TRUE
                   ORDER BY priority DESC, created_at DESC
                   LIMIT $1""",
                limit,
            )
        results = []
        for r in rows:
            raw = r["content"]
            if isinstance(raw, dict):
                content = raw
            elif isinstance(raw, str):
                try:
                    content = json.loads(raw)
                except Exception:
                    content = {"text": raw}
            else:
                content = {}
            results.append({
                "id": str(r["id"]),
                "node_type": r["node_type"],
                "name": r["name"],
                "content": content,
                "source_brain": r["source_brain"],
                "priority": r["priority"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
        return results
    except Exception as e:
        log.warning(f"graph_bridge: get_recent_nodes failed: {e}")
        return []


async def deactivate_node(pool, node_id: str) -> bool:
    """Soft-delete a graph node by id."""
    try:
        result = await pool.execute(
            "UPDATE cross_brain_graph SET active = FALSE, updated_at = NOW() WHERE id = $1",
            uuid.UUID(node_id),
        )
        return result == "UPDATE 1"
    except Exception as e:
        log.warning(f"graph_bridge: deactivate_node failed: {e}")
        return False


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _write_node(
    pool,
    node_type: str,
    name: str,
    content: dict,
    source_brain: str,
    priority: int,
) -> str | None:
    """Insert a node into cross_brain_graph. Returns id string or None."""
    try:
        row = await pool.fetchrow(
            """INSERT INTO cross_brain_graph
                   (node_type, name, content, source_brain, priority)
               VALUES ($1, $2, $3::jsonb, $4, $5)
               RETURNING id""",
            node_type, name, json.dumps(content), source_brain, priority,
        )
        if row:
            node_id = str(row["id"])
            log.info(f"graph_bridge: wrote {node_type} node {node_id[:8]} from {source_brain}")
            return node_id
    except Exception as e:
        log.warning(f"graph_bridge: _write_node ({node_type}) failed: {e}")
    return None


async def _ingest_to_graphiti(node_type: str, content: str, source_brain: str) -> None:
    """Fire-and-forget Graphiti ingestion for NLP entity extraction."""
    group_map = {
        "directive": "otto_directives",
        "decision": "otto_decisions",
        "task_state": "otto_tasks",
        "context": "otto_context",
    }
    group_id = group_map.get(node_type, "otto_context")
    ts = datetime.now(timezone.utc).isoformat()

    try:
        async with httpx.AsyncClient(timeout=GRAPHITI_TIMEOUT) as client:
            await client.post(
                f"{settings.graphiti_url}/messages",
                json={
                    "group_id": group_id,
                    "messages": [
                        {
                            "content": content,
                            "role_type": "user",
                            "role": source_brain,
                            "timestamp": ts,
                            "source_description": f"Otto cross-brain {node_type}",
                        }
                    ],
                },
            )
    except Exception as e:
        log.debug(f"graph_bridge: Graphiti ingest skipped ({e})")

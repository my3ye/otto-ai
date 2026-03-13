"""G2CP graph node API routes — structured kernel communication.

Provides REST endpoints for reading/writing structured graph nodes
in the cross_brain_graph table (legacy name, now used by the unified kernel).
"""

import logging
from fastapi import APIRouter
from pydantic import BaseModel

from ..db import get_pool
from ..graph_bridge import (
    write_directive,
    write_decision,
    update_task_state,
    write_context,
    write_from_classified_note,
    get_recent_nodes,
    deactivate_node,
)

log = logging.getLogger("otto.graph_nodes")
router = APIRouter(prefix="/graph/nodes", tags=["graph_nodes"])


class WriteNodeRequest(BaseModel):
    note_type: str  # directive, decision, task_state, context, goal, mission, etc.
    content: str
    context: str | None = None
    source: str = "kernel"


class WriteDirectiveRequest(BaseModel):
    content: str
    priority: int = 8
    source: str = "kernel"
    category: str = "directive"


class WriteDecisionRequest(BaseModel):
    content: str
    decided_by: str = "otto"
    context: str | None = None
    source: str = "kernel"


class UpdateTaskStateRequest(BaseModel):
    task_id: str
    title: str
    status: str
    summary: str = ""
    source: str = "kernel"


class WriteContextRequest(BaseModel):
    key: str
    value: str
    source: str = "kernel"


@router.get("")
async def list_nodes(node_type: str | None = None, limit: int = 20):
    """List recent active graph nodes."""
    pool = await get_pool()
    types = [node_type] if node_type else None
    nodes = await get_recent_nodes(pool, node_types=types, limit=limit)
    return {"nodes": nodes, "count": len(nodes)}


@router.post("")
async def write_node(req: WriteNodeRequest):
    """Write a structured graph node from a classified note type.

    This is the generic endpoint — maps note_type to the right write helper.
    """
    pool = await get_pool()
    node_id = await write_from_classified_note(
        pool,
        note_type=req.note_type,
        content=req.content,
        context=req.context,
        source=req.source,
    )
    if node_id:
        return {"status": "ok", "id": node_id, "note_type": req.note_type}
    return {"status": "error", "message": "Failed to write node"}


@router.post("/directive")
async def post_directive(req: WriteDirectiveRequest):
    """Write a DirectiveNode (mission/behavioral directive from Mev or Otto)."""
    pool = await get_pool()
    node_id = await write_directive(pool, req.content, req.priority, req.source, req.category)
    if node_id:
        return {"status": "ok", "id": node_id}
    return {"status": "error", "message": "Failed to write directive node"}


@router.post("/decision")
async def post_decision(req: WriteDecisionRequest):
    """Write a DecisionNode (a decision made by Mev or Otto)."""
    pool = await get_pool()
    node_id = await write_decision(pool, req.content, req.decided_by, req.context, req.source)
    if node_id:
        return {"status": "ok", "id": node_id}
    return {"status": "error", "message": "Failed to write decision node"}


@router.post("/task-state")
async def post_task_state(req: UpdateTaskStateRequest):
    """Upsert a TaskStateNode. Deactivates prior nodes for the same task_id."""
    pool = await get_pool()
    node_id = await update_task_state(
        pool, req.task_id, req.title, req.status, req.summary, req.source
    )
    if node_id:
        return {"status": "ok", "id": node_id}
    return {"status": "error", "message": "Failed to write task_state node"}


@router.post("/context")
async def post_context(req: WriteContextRequest):
    """Upsert a ContextNode (working memory key/value). Deactivates prior nodes for the same key."""
    pool = await get_pool()
    node_id = await write_context(pool, req.key, req.value, req.source)
    if node_id:
        return {"status": "ok", "id": node_id}
    return {"status": "error", "message": "Failed to write context node"}


@router.post("/{node_id}/deactivate")
async def deactivate(node_id: str):
    """Soft-delete a graph node (marks active=FALSE)."""
    pool = await get_pool()
    success = await deactivate_node(pool, node_id)
    if success:
        return {"status": "ok", "id": node_id}
    return {"status": "error", "message": "Node not found or already inactive"}

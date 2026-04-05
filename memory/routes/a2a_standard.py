"""
A2A Standard — Google A2A v1.0 cross-vendor agent-to-agent protocol.

Implements:
  - Agent Card discovery (GET /.well-known/agent.json)
  - JSON-RPC 2.0 dispatcher (POST /a2a/jsonrpc)
  - SSE task streaming (GET /a2a/tasks/{id}/stream)
  - Task lifecycle: submitted → working → [input-required] → completed | failed | canceled

Additive to existing internal A2A mailbox (routes/a2a.py).
"""

import asyncio
import json
import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_pool

logger = logging.getLogger("otto.a2a_standard")

router = APIRouter(prefix="/a2a", tags=["a2a-standard"])

# ── A2A Task States ──────────────────────────────────────────────────────────

VALID_STATES = {"submitted", "working", "input-required", "completed", "failed", "canceled"}
TERMINAL_STATES = {"completed", "failed", "canceled"}


# ── Pydantic Models (A2A v1.0 spec) ─────────────────────────────────────────

class A2APart(BaseModel):
    type: str = "text"  # text, data, file
    text: str | None = None
    data: dict | None = None
    mimeType: str | None = None  # noqa: N815


class A2AMessage(BaseModel):
    role: str  # user, agent
    parts: list[A2APart]


class A2AArtifact(BaseModel):
    name: str | None = None
    description: str | None = None
    parts: list[A2APart]
    index: int = 0


class A2ATaskStatus(BaseModel):
    state: str
    message: str | None = None
    timestamp: datetime | None = None


class A2ATask(BaseModel):
    id: str
    status: A2ATaskStatus
    artifacts: list[A2AArtifact] = Field(default_factory=list)
    history: list[A2AMessage] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class JsonRpcRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict = Field(default_factory=dict)


class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Any = None


# ── Agent Card ───────────────────────────────────────────────────────────────

AGENT_CARD = {
    "name": "Otto AI",
    "description": "Sovereign AI agent — memory, task orchestration, multi-agent workflows",
    "url": "https://api.otto.lk/a2a/jsonrpc",
    "version": "1.0",
    "capabilities": {
        "streaming": True,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    "authentication": {
        "schemes": ["bearer"],
    },
    "defaultInputModes": ["text/plain", "application/json"],
    "defaultOutputModes": ["text/plain", "application/json"],
    "skills": [
        {"id": "research", "name": "Deep Research", "description": "Multi-source research with synthesis"},
        {"id": "code", "name": "Code Implementation", "description": "Write, review, debug code"},
        {"id": "content", "name": "Content Creation", "description": "Articles, copy, technical writing"},
        {"id": "task-orchestration", "name": "Task Orchestration", "description": "Multi-agent plan DAG execution"},
    ],
}


def get_agent_card() -> dict:
    """Return the Agent Card. Mounted at app root as /.well-known/agent.json."""
    return AGENT_CARD


# ── Auth Helper ──────────────────────────────────────────────────────────────

def _check_bearer_auth(request: Request) -> str | None:
    """Validate bearer token from Authorization header. Returns sender identity or raises."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None

    token = auth[7:].strip()
    if not token:
        return None

    # Reuse MCP token for Phase 1
    if settings.mcp_token and token == settings.mcp_token:
        return "mcp-authenticated"

    return None


def _require_auth(request: Request) -> str:
    """Require valid bearer auth. Raises 401 if invalid."""
    identity = _check_bearer_auth(request)
    if identity is None:
        raise HTTPException(401, "Invalid or missing bearer token")
    return identity


# ── JSON-RPC Helpers ─────────────────────────────────────────────────────────

def _jsonrpc_success(req_id: str | int | None, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _jsonrpc_error(req_id: str | int | None, code: int, message: str, data: Any = None) -> dict:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


# ── DB Helpers ───────────────────────────────────────────────────────────────

async def _create_a2a_task(
    pool,
    message: A2AMessage,
    external_task_id: str | None = None,
    metadata: dict | None = None,
    created_by: str | None = None,
) -> dict:
    """Create a new a2a_tasks row and initial history entry."""
    task_id = _uuid.uuid4()
    input_messages = [message.model_dump()]

    row = await pool.fetchrow(
        """INSERT INTO a2a_tasks
           (id, external_task_id, state, status_message, input_messages, metadata, created_by)
           VALUES ($1, $2, 'submitted', 'Task received', $3::jsonb, $4::jsonb, $5)
           RETURNING *""",
        task_id,
        external_task_id,
        json.dumps(input_messages),
        json.dumps(metadata or {}),
        created_by,
    )

    # Record initial history
    await pool.execute(
        """INSERT INTO a2a_task_history (task_id, state, message)
           VALUES ($1, 'submitted', 'Task created')""",
        task_id,
    )

    return dict(row)


async def _update_a2a_task_state(
    pool, task_id: UUID, new_state: str, message: str | None = None,
    artifacts: list | None = None,
) -> dict | None:
    """Transition a2a task to a new state. Returns updated row or None."""
    if new_state not in VALID_STATES:
        return None

    updates = ["state = $2", "status_message = $3", "updated_at = now()"]
    params: list[Any] = [task_id, new_state, message]

    if artifacts is not None:
        updates.append(f"artifacts = ${len(params) + 1}::jsonb")
        params.append(json.dumps(artifacts))

    row = await pool.fetchrow(
        f"""UPDATE a2a_tasks SET {', '.join(updates)}
            WHERE id = $1 RETURNING *""",
        *params,
    )

    if row:
        await pool.execute(
            """INSERT INTO a2a_task_history (task_id, state, message)
               VALUES ($1, $2, $3)""",
            task_id, new_state, message,
        )

    return dict(row) if row else None


def _row_to_a2a_task(row: dict) -> dict:
    """Convert DB row to A2A Task response dict."""
    input_msgs = row.get("input_messages") or []
    if isinstance(input_msgs, str):
        input_msgs = json.loads(input_msgs)

    artifacts = row.get("artifacts") or []
    if isinstance(artifacts, str):
        artifacts = json.loads(artifacts)

    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        metadata = json.loads(metadata)

    return {
        "id": str(row["id"]),
        "status": {
            "state": row["state"],
            "message": row.get("status_message"),
            "timestamp": row["updated_at"].isoformat() if row.get("updated_at") else None,
        },
        "artifacts": artifacts,
        "history": input_msgs,
        "metadata": metadata,
    }


# ── Bridge: Otto Task Queue → A2A Task ──────────────────────────────────────

async def _bridge_to_otto_task(pool, a2a_task_id: UUID, message: A2AMessage) -> UUID | None:
    """Create an internal Otto task linked to the A2A task. Returns Otto task ID."""
    # Extract text content from parts
    text_parts = [p.text for p in message.parts if p.type == "text" and p.text]
    if not text_parts:
        return None

    prompt = "\n\n".join(text_parts)

    # Create internal task
    from .tasks import TASK_COLUMNS
    row = await pool.fetchrow(
        f"""INSERT INTO tasks
            (title, prompt, priority, status, model, agent_type,
             max_budget_usd, max_turns, timeout_seconds,
             working_directory, created_by, metadata)
            VALUES ($1, $2, 5, 'pending', 'sonnet', 'general-purpose',
                    5.00, 50, 600,
                    '/home/web3relic/otto', 'a2a-standard',
                    $3::jsonb)
            RETURNING {TASK_COLUMNS}""",
        f"A2A: {prompt[:80]}",
        prompt,
        json.dumps({"a2a_task_id": str(a2a_task_id)}),
    )

    if row:
        otto_task_id = row["id"]
        # Link back
        await pool.execute(
            "UPDATE a2a_tasks SET linked_task_id = $1 WHERE id = $2",
            otto_task_id, a2a_task_id,
        )
        return otto_task_id
    return None


# ── JSON-RPC Method Handlers ─────────────────────────────────────────────────

async def _handle_message_send(params: dict, created_by: str) -> dict:
    """Handle message/send — create or continue a task."""
    pool = await get_pool()

    msg_data = params.get("message")
    if not msg_data:
        raise ValueError("Missing 'message' in params")

    message = A2AMessage(**msg_data)
    task_id_str = params.get("taskId")
    metadata = params.get("metadata", {})

    if task_id_str:
        # Continue existing task — append message
        try:
            task_id = UUID(task_id_str)
        except ValueError:
            raise ValueError(f"Invalid taskId: {task_id_str}")

        row = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
        if not row:
            raise ValueError(f"Task not found: {task_id_str}")

        existing_msgs = row["input_messages"] or []
        if isinstance(existing_msgs, str):
            existing_msgs = json.loads(existing_msgs)
        existing_msgs.append(message.model_dump())

        await pool.execute(
            """UPDATE a2a_tasks
               SET input_messages = $2::jsonb, updated_at = now()
               WHERE id = $1""",
            task_id, json.dumps(existing_msgs),
        )

        # If task was input-required, move back to working
        if row["state"] == "input-required":
            await _update_a2a_task_state(pool, task_id, "working", "Resumed with new input")

        updated = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
        return _row_to_a2a_task(dict(updated))
    else:
        # New task
        row = await _create_a2a_task(pool, message, metadata=metadata, created_by=created_by)
        task_id = row["id"]

        # Move to working
        await _update_a2a_task_state(pool, task_id, "working", "Processing...")

        # Bridge to internal task queue (fire-and-forget)
        asyncio.create_task(_bridge_to_otto_task(pool, task_id, message))

        updated = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
        return _row_to_a2a_task(dict(updated))


async def _handle_tasks_get(params: dict) -> dict:
    """Handle tasks/get — return task state + history."""
    pool = await get_pool()
    task_id_str = params.get("taskId") or params.get("id")
    if not task_id_str:
        raise ValueError("Missing 'taskId' in params")

    try:
        task_id = UUID(task_id_str)
    except ValueError:
        raise ValueError(f"Invalid taskId: {task_id_str}")

    row = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
    if not row:
        raise ValueError(f"Task not found: {task_id_str}")

    return _row_to_a2a_task(dict(row))


async def _handle_tasks_cancel(params: dict) -> dict:
    """Handle tasks/cancel — cancel a running task."""
    pool = await get_pool()
    task_id_str = params.get("taskId") or params.get("id")
    if not task_id_str:
        raise ValueError("Missing 'taskId' in params")

    try:
        task_id = UUID(task_id_str)
    except ValueError:
        raise ValueError(f"Invalid taskId: {task_id_str}")

    row = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
    if not row:
        raise ValueError(f"Task not found: {task_id_str}")

    if row["state"] in TERMINAL_STATES:
        raise ValueError(f"Task already in terminal state: {row['state']}")

    updated = await _update_a2a_task_state(pool, task_id, "canceled", "Canceled by caller")

    # Cancel linked Otto task if exists
    if row.get("linked_task_id"):
        await pool.execute(
            """UPDATE tasks SET status = 'cancelled'
               WHERE id = $1 AND status IN ('pending', 'running')""",
            row["linked_task_id"],
        )

    return _row_to_a2a_task(updated) if updated else {}


async def _handle_tasks_list(params: dict) -> dict:
    """Handle tasks/list — list tasks with optional filters."""
    pool = await get_pool()
    state_filter = params.get("state")
    limit = min(int(params.get("limit", 20)), 100)
    offset = int(params.get("offset", 0))

    conditions = []
    query_params: list[Any] = []

    if state_filter:
        conditions.append(f"state = ${len(query_params) + 1}")
        query_params.append(state_filter)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query_params.extend([limit, offset])

    rows = await pool.fetch(
        f"""SELECT * FROM a2a_tasks {where}
            ORDER BY created_at DESC
            LIMIT ${len(query_params) - 1} OFFSET ${len(query_params)}""",
        *query_params,
    )

    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM a2a_tasks {where}",
        *query_params[:-2] if query_params[:-2] else [],
    )

    return {
        "tasks": [_row_to_a2a_task(dict(r)) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


# ── JSON-RPC Dispatcher ─────────────────────────────────────────────────────

METHOD_HANDLERS = {
    "message/send": _handle_message_send,
    "message/sendStream": _handle_message_send,  # Same handler, streaming handled at transport level
    "tasks/get": _handle_tasks_get,
    "tasks/cancel": _handle_tasks_cancel,
    "tasks/list": _handle_tasks_list,
}


@router.post("/jsonrpc")
async def jsonrpc_dispatch(request: Request):
    """JSON-RPC 2.0 dispatcher for A2A standard methods."""
    identity = _require_auth(request)

    # Parse request body
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(_jsonrpc_error(None, PARSE_ERROR, "Parse error"))

    # Validate JSON-RPC envelope
    if not isinstance(body, dict):
        return JSONResponse(_jsonrpc_error(None, INVALID_REQUEST, "Request must be a JSON object"))

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params", {})

    if body.get("jsonrpc") != "2.0":
        return JSONResponse(_jsonrpc_error(req_id, INVALID_REQUEST, "jsonrpc must be '2.0'"))

    if not method or not isinstance(method, str):
        return JSONResponse(_jsonrpc_error(req_id, INVALID_REQUEST, "Missing or invalid 'method'"))

    handler = METHOD_HANDLERS.get(method)
    if not handler:
        return JSONResponse(_jsonrpc_error(req_id, METHOD_NOT_FOUND, f"Unknown method: {method}"))

    # Dispatch to handler
    try:
        # message/send and message/sendStream need created_by
        if method.startswith("message/"):
            result = await handler(params, created_by=identity)
        else:
            result = await handler(params)

        # For message/sendStream, return SSE instead
        if method == "message/sendStream" and isinstance(result, dict) and "id" in result:
            task_id = result["id"]
            return StreamingResponse(
                _sse_task_stream(UUID(task_id)),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        return JSONResponse(_jsonrpc_success(req_id, result))

    except ValueError as e:
        return JSONResponse(_jsonrpc_error(req_id, INVALID_PARAMS, str(e)))
    except Exception as e:
        logger.error(f"JSON-RPC internal error: {e}", exc_info=True)
        return JSONResponse(_jsonrpc_error(req_id, INTERNAL_ERROR, "Internal error"))


# ── SSE Streaming ────────────────────────────────────────────────────────────

async def _sse_task_stream(task_id: UUID):
    """Generator that yields SSE events as an A2A task progresses."""
    pool = await get_pool()
    last_state = None
    poll_count = 0
    max_polls = 600  # 10 minutes at 1s interval

    while poll_count < max_polls:
        row = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
        if not row:
            yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
            return

        current_state = row["state"]

        # Emit event on state change
        if current_state != last_state:
            task_data = _row_to_a2a_task(dict(row))
            yield f"event: task-update\ndata: {json.dumps(task_data)}\n\n"
            last_state = current_state

            # Terminal state — send final event and close
            if current_state in TERMINAL_STATES:
                yield f"event: task-complete\ndata: {json.dumps(task_data)}\n\n"
                return

        poll_count += 1
        await asyncio.sleep(1)

    # Timeout
    yield f"event: error\ndata: {json.dumps({'error': 'Stream timeout'})}\n\n"


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: UUID, request: Request):
    """SSE stream for task state updates."""
    _require_auth(request)

    pool = await get_pool()
    row = await pool.fetchrow("SELECT 1 FROM a2a_tasks WHERE id = $1", task_id)
    if not row:
        raise HTTPException(404, "A2A task not found")

    return StreamingResponse(
        _sse_task_stream(task_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── REST Convenience Endpoints ───────────────────────────────────────────────

@router.get("/standard/tasks/{task_id}")
async def get_task_rest(task_id: UUID, request: Request):
    """REST convenience: get A2A task by ID (alternative to JSON-RPC)."""
    _require_auth(request)

    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM a2a_tasks WHERE id = $1", task_id)
    if not row:
        raise HTTPException(404, "A2A task not found")
    return _row_to_a2a_task(dict(row))


@router.get("/standard/tasks")
async def list_tasks_rest(
    request: Request,
    state: str | None = None,
    limit: int = 20,
    offset: int = 0,
):
    """REST convenience: list A2A tasks."""
    _require_auth(request)
    result = await _handle_tasks_list({"state": state, "limit": limit, "offset": offset})
    return result


@router.get("/standard/task-history/{task_id}")
async def get_task_history(task_id: UUID, request: Request):
    """Get state transition history for an A2A task."""
    _require_auth(request)

    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM a2a_task_history
           WHERE task_id = $1 ORDER BY timestamp ASC""",
        task_id,
    )
    return [dict(r) for r in rows]


# ── Hook: Update A2A task when linked Otto task completes ────────────────────

async def on_otto_task_complete(pool, otto_task_id: UUID, status: str, output: str | None = None):
    """Called from tasks.py complete_task() to bridge Otto task completion to A2A task."""
    row = await pool.fetchrow(
        "SELECT id, state FROM a2a_tasks WHERE linked_task_id = $1",
        otto_task_id,
    )
    if not row:
        return  # Not linked to any A2A task

    a2a_task_id = row["id"]
    if row["state"] in TERMINAL_STATES:
        return  # Already terminal

    if status == "completed":
        artifacts = []
        if output:
            artifacts = [{"name": "result", "parts": [{"type": "text", "text": output[:4000]}], "index": 0}]
        await _update_a2a_task_state(pool, a2a_task_id, "completed", "Task completed", artifacts=artifacts)
    elif status == "failed":
        await _update_a2a_task_state(pool, a2a_task_id, "failed", f"Task failed: {(output or '')[:200]}")
    elif status == "cancelled":
        await _update_a2a_task_state(pool, a2a_task_id, "canceled", "Task cancelled")

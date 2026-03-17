"""Gateway API routes — channel-agnostic endpoints + WebSocket + dashboard."""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..config import settings
from ..db import get_pool
from .models import GatewayMessage, GatewayResponse
from .handler import handle_message, handle_message_stream

log = logging.getLogger("otto.gateway.routes")

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.post("/incoming", response_model=GatewayResponse)
async def gateway_incoming(msg: GatewayMessage):
    """Accept a normalized message from any channel adapter.

    Routes through kernel (if enabled) or legacy path.
    """
    return await handle_message(msg)


@router.get("/health")
async def gateway_health():
    """Gateway health check."""
    kernel_status = "enabled" if settings.kernel_enabled else "disabled"
    return {"status": "ok", "channels": ["whatsapp", "web"], "kernel": kernel_status}


@router.websocket("/ws")
async def websocket_chat(ws: WebSocket, token: str = Query(default="")):
    """WebSocket endpoint for the web chat interface.

    Routes through kernel (if enabled) or legacy path.
    """
    # Auth check
    if not settings.web_auth_token or token != settings.web_auth_token:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()
    log.info("Web chat WebSocket connected")

    try:
        while True:
            data = await ws.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await ws.send_json({"error": "Invalid JSON"})
                continue

            content = payload.get("content", "").strip()
            if not content:
                await ws.send_json({"error": "Empty message"})
                continue

            msg = GatewayMessage(
                channel="web",
                sender_id="admin",
                sender_name="Mev",
                content=content,
                metadata={"authenticated": True},
            )

            # Stream response chunks to client
            msg_id = None
            try:
                from uuid import uuid4
                msg_id = str(uuid4())
                await ws.send_json({"type": "stream_start", "id": msg_id})

                async for chunk in handle_message_stream(msg):
                    await ws.send_json({"type": "chunk", "content": chunk})

                await ws.send_json({"type": "stream_end", "id": msg_id})
            except WebSocketDisconnect:
                # Client disconnected mid-stream — clean exit, don't re-raise
                log.info("Client disconnected during streaming")
                return
            except Exception as e:
                log.error(f"Streaming failed: {e}", exc_info=True)
                # Fallback: send error as complete message (only if WS still open)
                try:
                    await ws.send_json({
                        "type": "message",
                        "content": "Hey Mev — hit an error processing that. Try again?",
                        "id": msg_id,
                    })
                except Exception:
                    pass  # WS already closed, ignore
    except WebSocketDisconnect:
        log.info("Web chat WebSocket disconnected")


@router.get("/dashboard")
async def dashboard_data():
    """Dashboard data: tasks, heartbeats, memory stats, pending questions, recent messages."""
    pool = await get_pool()

    # Task queue summary
    task_rows = await pool.fetch(
        """SELECT status, count(*) as cnt FROM tasks GROUP BY status"""
    )
    task_counts = {r["status"]: r["cnt"] for r in task_rows}

    # Recent heartbeat health
    heartbeat_rows = await pool.fetch(
        """SELECT content, created_at, importance FROM episodic_events
           WHERE event_type = 'heartbeat' OR content LIKE '%heartbeat%'
           ORDER BY created_at DESC LIMIT 10"""
    )
    heartbeats = [
        {"content": r["content"][:200], "at": r["created_at"].isoformat(), "importance": r["importance"]}
        for r in heartbeat_rows
    ]

    # Memory stats
    semantic_count = await pool.fetchval("SELECT count(*) FROM semantic_memories WHERE archived IS NOT TRUE")
    episodic_count = await pool.fetchval("SELECT count(*) FROM episodic_events")
    message_count = await pool.fetchval("SELECT count(*) FROM whatsapp_messages")

    # Pending questions (simplified: no direction filter needed with kernel)
    pending_rows = await pool.fetch(
        """SELECT id, question, intent, asked_at FROM pending_questions
           WHERE resolved_at IS NULL ORDER BY asked_at DESC LIMIT 10"""
    )
    pending = [
        {"id": str(r["id"]), "question": r["question"][:200], "intent": r["intent"],
         "at": r["asked_at"].isoformat()}
        for r in pending_rows
    ]

    # Kernel status
    kernel_info = {}
    if settings.kernel_enabled:
        try:
            from ..kernel import ivt
            kernel_info = await ivt.queue_depth()
        except Exception:
            kernel_info = {"error": "kernel not available"}

    # Recent messages
    msg_rows = await pool.fetch(
        """SELECT direction, content, channel, push_name, created_at
           FROM whatsapp_messages ORDER BY created_at DESC LIMIT 20"""
    )
    messages = [
        {"direction": r["direction"], "content": r["content"][:300],
         "channel": r["channel"] or "whatsapp", "name": r["push_name"],
         "at": r["created_at"].isoformat() if r["created_at"] else None}
        for r in msg_rows
    ]

    return {
        "tasks": task_counts,
        "heartbeats": heartbeats,
        "memory": {
            "semantic": semantic_count,
            "episodic": episodic_count,
            "messages": message_count,
        },
        "pending_questions": pending,
        "kernel": kernel_info,
        "recent_messages": messages,
    }


@router.get("/conversation/history")
async def conversation_history(limit: int = 50, offset: int = 0, channel: str | None = None):
    """Paginated message history across all channels."""
    pool = await get_pool()

    if channel:
        rows = await pool.fetch(
            """SELECT id, direction, content, jid, push_name, channel, created_at
               FROM whatsapp_messages
               WHERE channel = $1
               ORDER BY created_at DESC
               LIMIT $2 OFFSET $3""",
            channel, limit, offset,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, direction, content, jid, push_name, channel, created_at
               FROM whatsapp_messages
               ORDER BY created_at DESC
               LIMIT $1 OFFSET $2""",
            limit, offset,
        )

    return {
        "messages": [
            {
                "id": str(r["id"]),
                "direction": r["direction"],
                "content": r["content"],
                "sender": r["push_name"],
                "channel": r["channel"] or "whatsapp",
                "at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
        "limit": limit,
        "offset": offset,
    }

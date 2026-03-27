"""
A2A (Agent-to-Agent) messaging — PostgreSQL mailbox for inter-agent coordination.

Agents in plans/workflows can send messages to peers, share artifacts,
ask questions, and receive completion signals via channel-scoped messaging.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..db import get_pool

logger = logging.getLogger("otto.a2a")

router = APIRouter(prefix="/a2a", tags=["a2a"])

# ── Models ────────────────────────────────────────────────────────────────────

VALID_MESSAGE_TYPES = {"message", "question", "artifact", "signal", "completion"}


class A2ASend(BaseModel):
    channel_id: UUID
    sender_id: str
    sender_agent_type: Optional[str] = None
    recipient_id: Optional[str] = None  # None = broadcast to channel
    message_type: str = "message"
    content: str = Field(..., max_length=4096)
    metadata: dict = Field(default_factory=dict)
    in_reply_to: Optional[UUID] = None


class A2AMessage(BaseModel):
    id: UUID
    channel_id: UUID
    sender_id: str
    sender_agent_type: Optional[str] = None
    recipient_id: Optional[str] = None
    message_type: str
    content: str
    metadata: dict = Field(default_factory=dict)
    in_reply_to: Optional[UUID] = None
    read_by: list[str] = Field(default_factory=list)
    created_at: datetime
    expires_at: Optional[datetime] = None


class A2AChannelInfo(BaseModel):
    channel_id: UUID
    participants: list[str]
    message_count: int
    source_type: str  # "plan", "workflow", or "ad-hoc"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/send", response_model=A2AMessage)
async def send_message(req: A2ASend):
    """Send a message to a channel. Validates type and rate limits per sender."""
    if req.message_type not in VALID_MESSAGE_TYPES:
        raise HTTPException(400, f"Invalid message_type. Must be one of: {VALID_MESSAGE_TYPES}")

    if not req.content.strip():
        raise HTTPException(400, "Content cannot be empty")

    pool = await get_pool()

    # Rate limit: 20 messages per sender per channel per hour
    recent_count = await pool.fetchval(
        """SELECT COUNT(*) FROM a2a_messages
           WHERE channel_id = $1 AND sender_id = $2
           AND created_at > now() - interval '1 hour'""",
        req.channel_id, req.sender_id,
    )
    if recent_count >= 20:
        raise HTTPException(429, "Rate limit: max 20 messages per sender per channel per hour")

    # Validate in_reply_to exists in same channel
    if req.in_reply_to:
        exists = await pool.fetchval(
            "SELECT 1 FROM a2a_messages WHERE id = $1 AND channel_id = $2",
            req.in_reply_to, req.channel_id,
        )
        if not exists:
            raise HTTPException(404, "in_reply_to message not found in this channel")

    row = await pool.fetchrow(
        """INSERT INTO a2a_messages
           (channel_id, sender_id, sender_agent_type, recipient_id,
            message_type, content, metadata, in_reply_to)
           VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
           RETURNING *""",
        req.channel_id, req.sender_id, req.sender_agent_type,
        req.recipient_id, req.message_type, req.content,
        json.dumps(req.metadata), req.in_reply_to,
    )
    logger.info(f"A2A message sent: {req.sender_id} -> channel {req.channel_id} ({req.message_type})")
    return _row_to_message(row)


@router.get("/poll", response_model=list[A2AMessage])
async def poll_messages(
    channel_id: UUID = Query(..., description="Channel to poll"),
    reader_id: str = Query(..., description="ID of the polling agent"),
    since: Optional[datetime] = Query(None, description="Only messages after this timestamp"),
    limit: int = Query(20, ge=1, le=50),
):
    """Poll messages from a channel. Returns broadcast + directed messages, auto-marks as read."""
    pool = await get_pool()

    conditions = ["channel_id = $1", "(recipient_id IS NULL OR recipient_id = $2)"]
    params: list = [channel_id, reader_id]

    if since:
        conditions.append(f"created_at > ${len(params) + 1}")
        params.append(since)

    where = " AND ".join(conditions)
    rows = await pool.fetch(
        f"""SELECT * FROM a2a_messages
            WHERE {where}
            ORDER BY created_at ASC
            LIMIT ${len(params) + 1}""",
        *params, limit,
    )

    messages = [_row_to_message(r) for r in rows]

    # Auto-mark as read (batch update)
    if rows:
        unread_ids = [r["id"] for r in rows if reader_id not in (r["read_by"] or [])]
        if unread_ids:
            await pool.execute(
                """UPDATE a2a_messages
                   SET read_by = array_append(read_by, $1)
                   WHERE id = ANY($2::uuid[]) AND NOT ($1 = ANY(read_by))""",
                reader_id, unread_ids,
            )

    return messages


@router.get("/channel/{channel_id}", response_model=A2AChannelInfo)
async def get_channel_info(channel_id: UUID):
    """Get channel metadata: participants, message count, source type."""
    pool = await get_pool()

    # Get participants and count
    stats = await pool.fetchrow(
        """SELECT
               array_agg(DISTINCT sender_id) as participants,
               count(*) as message_count
           FROM a2a_messages
           WHERE channel_id = $1""",
        channel_id,
    )

    if not stats or stats["message_count"] == 0:
        raise HTTPException(404, "Channel not found or empty")

    # Detect source type
    source_type = "ad-hoc"
    plan_exists = await pool.fetchval(
        "SELECT 1 FROM task_plans WHERE id = $1", channel_id,
    )
    if plan_exists:
        source_type = "plan"
    else:
        wf_exists = await pool.fetchval(
            "SELECT 1 FROM workflow_instances WHERE id = $1", channel_id,
        )
        if wf_exists:
            source_type = "workflow"

    return A2AChannelInfo(
        channel_id=channel_id,
        participants=stats["participants"] or [],
        message_count=stats["message_count"],
        source_type=source_type,
    )


@router.get("/peers", response_model=list[dict])
async def get_peers(
    plan_id: Optional[UUID] = Query(None),
    workflow_instance_id: Optional[UUID] = Query(None),
):
    """Get running peer agents in the same plan or workflow."""
    pool = await get_pool()

    if not plan_id and not workflow_instance_id:
        raise HTTPException(400, "Provide plan_id or workflow_instance_id")

    if plan_id:
        rows = await pool.fetch(
            """SELECT id, title, agent_type, status
               FROM tasks WHERE plan_id = $1 AND status = 'running'
               ORDER BY created_at""",
            plan_id,
        )
    else:
        rows = await pool.fetch(
            """SELECT t.id, t.title, t.agent_type, t.status
               FROM tasks t
               WHERE t.metadata->>'workflow_instance_id' = $1::text
               AND t.status = 'running'
               AND EXISTS (SELECT 1 FROM workflow_instances WHERE id = $1)
               ORDER BY t.created_at""",
            workflow_instance_id,
        )

    return [dict(r) for r in rows]


class A2ACreateChannel(BaseModel):
    channel_id: Optional[UUID] = None
    creator_id: str
    purpose: str = ""


@router.post("/channel", response_model=A2AMessage)
async def create_channel(req: A2ACreateChannel):
    """Create an ad-hoc channel by posting an initial signal message."""
    import uuid as _uuid

    cid = req.channel_id or _uuid.uuid4()
    pool = await get_pool()

    row = await pool.fetchrow(
        """INSERT INTO a2a_messages
           (channel_id, sender_id, message_type, content, metadata)
           VALUES ($1, $2, 'signal', $3, '{"event": "channel_created"}'::jsonb)
           RETURNING *""",
        cid, req.creator_id, f"Channel created: {req.purpose}" if req.purpose else "Channel created",
    )

    logger.info(f"A2A channel created: {cid} by {req.creator_id}")
    return _row_to_message(row)


# ── Cleanup (called from maintenance) ─────────────────────────────────────────

async def cleanup_expired_messages(pool=None):
    """Delete expired messages and messages from completed plans older than 7 days."""
    if pool is None:
        pool = await get_pool()

    # Delete expired messages
    expired = await pool.fetchval(
        """WITH deleted AS (
               DELETE FROM a2a_messages
               WHERE expires_at IS NOT NULL AND expires_at < now()
               RETURNING 1
           ) SELECT count(*) FROM deleted"""
    )

    # Delete messages from completed plans older than 7 days
    old_plan = await pool.fetchval(
        """WITH deleted AS (
               DELETE FROM a2a_messages
               WHERE channel_id IN (
                   SELECT id FROM task_plans
                   WHERE status IN ('completed', 'failed', 'cancelled')
                   AND updated_at < now() - interval '7 days'
               ) RETURNING 1
           ) SELECT count(*) FROM deleted"""
    )

    # Delete messages from completed workflows older than 7 days
    old_wf = await pool.fetchval(
        """WITH deleted AS (
               DELETE FROM a2a_messages
               WHERE channel_id IN (
                   SELECT id FROM workflow_instances
                   WHERE status IN ('completed', 'failed', 'cancelled')
                   AND updated_at < now() - interval '7 days'
               ) RETURNING 1
           ) SELECT count(*) FROM deleted"""
    )

    total = (expired or 0) + (old_plan or 0) + (old_wf or 0)
    if total > 0:
        logger.info(f"A2A cleanup: {expired or 0} expired, {old_plan or 0} old plan, {old_wf or 0} old workflow messages deleted")
    return total


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_message(row) -> A2AMessage:
    """Convert asyncpg Record to A2AMessage."""
    d = dict(row)
    if isinstance(d.get("metadata"), str):
        d["metadata"] = json.loads(d["metadata"])
    elif d.get("metadata") is None:
        d["metadata"] = {}
    if d.get("read_by") is None:
        d["read_by"] = []
    return A2AMessage(**d)

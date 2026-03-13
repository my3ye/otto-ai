"""WhatsApp channel adapter — thin wrapper over the gateway.

Translates WhatsAppIncoming → GatewayMessage, calls handle_message(),
then delivers the response via the WhatsApp service on :3001.
"""

import logging
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import WhatsAppIncoming
from ..gateway.models import GatewayMessage
from ..gateway.handler import handle_message

log = logging.getLogger("otto.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

OWNER_JID = "94743806705@s.whatsapp.net"


@router.post("/incoming")
async def handle_incoming(req: WhatsAppIncoming):
    """WhatsApp incoming → gateway → deliver reply via WhatsApp service."""
    # Translate to normalized gateway message
    gw_msg = GatewayMessage(
        channel="whatsapp",
        sender_id=req.from_jid,
        sender_name=req.push_name,
        content=req.message,
    )

    # Process through the gateway
    response = await handle_message(gw_msg)

    # If ignored (not admin), return early
    if response.metadata.get("status") == "ignored":
        return {"status": "ignored", "reason": response.metadata.get("reason")}

    # Deliver reply via WhatsApp service
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(
                f"{settings.whatsapp_url}/send",
                json={"jid": req.from_jid, "message": response.content},
            )
    except Exception as e:
        return {"status": "generated", "reply": response.content, "send_error": str(e)}

    return {
        "status": "sent",
        "reply": response.content,
        "resolved_question": response.metadata.get("resolved_question", False),
        "cross_brain_note": response.metadata.get("cross_brain_note", False),
        "claude_delegated": response.metadata.get("claude_delegated", False),
    }


class WhatsAppSearchQuery(BaseModel):
    query: str
    limit: int = 10


@router.post("/search")
async def search_whatsapp(req: WhatsAppSearchQuery):
    """Semantic search over stored WhatsApp messages."""
    pool = await get_pool()
    embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    rows = await pool.fetch(
        """SELECT id, direction, content, jid, push_name, created_at, metadata,
                  1 - (embedding <=> $1::halfvec) AS score
           FROM whatsapp_messages
           WHERE embedding IS NOT NULL
           ORDER BY embedding <=> $1::halfvec
           LIMIT $2""",
        embedding_str, req.limit,
    )
    return {
        "query": req.query,
        "results": [
            {
                "id": str(r["id"]),
                "direction": r["direction"],
                "content": r["content"],
                "jid": r["jid"],
                "push_name": r["push_name"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "score": float(r["score"]),
                "metadata": r["metadata"],
            }
            for r in rows
        ],
        "count": len(rows),
    }

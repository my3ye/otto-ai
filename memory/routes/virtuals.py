"""
Virtuals Protocol Inference Endpoint

Exposes Otto as a Virtuals Protocol-compatible AI agent.
When Otto is registered on Virtuals Protocol (app.virtuals.io), this is the
inference URL that Virtuals will call for every user interaction.

Virtuals Protocol GAME SDK request format:
  POST /virtuals/infer
  {
    "sessionId": "...",
    "userMessage": "...",
    "agentId": "...",
    "userName": "user",
    "metadata": {}
  }

Response format expected by Virtuals:
  {
    "status": 200,
    "data": {
      "message": "Otto's response text",
      "actions": [],
      "metadata": {}
    }
  }

Configuration (~/memory/.env):
  VIRTUALS_API_SECRET    Secret token to verify requests are from Virtuals (optional but recommended)
  VIRTUALS_AGENT_ID      Your agent's Virtuals ID (for logging)

Inference pricing on Virtuals:
  Set during agent registration at app.virtuals.io
  Recommended starting price: 1-5 $VIRTUAL per inference (~$0.73-$3.65 at Mar 2026 prices)
  Revenue flows: user pays $VIRTUAL → 80% to agent wallet → 20% to token holder buybacks

Registration steps:
  1. Go to https://app.virtuals.io → "Launch Agent"
  2. Connect MetaMask wallet with Base network + 100 VIRTUAL tokens
  3. Fill agent profile (name, description, avatar, category)
  4. Set inference URL: https://YOUR_DOMAIN/virtuals/infer
     (Requires public URL — use otto.lk or a subdomain)
  5. Set inference price in $VIRTUAL
  6. Deploy → agent token created on bonding curve
  7. Set VIRTUALS_API_SECRET in .env
"""

import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/virtuals", tags=["virtuals"])

VIRTUALS_API_SECRET = os.environ.get("VIRTUALS_API_SECRET", "")
VIRTUALS_AGENT_ID = os.environ.get("VIRTUALS_AGENT_ID", "otto")


# --- Request/Response Models -------------------------------------------------

class VirtualsInferRequest(BaseModel):
    """Standard GAME SDK inference request from Virtuals Protocol."""
    sessionId: Optional[str] = None
    userMessage: str
    agentId: Optional[str] = None
    userName: Optional[str] = "user"
    metadata: Optional[dict] = {}


class VirtualsInferResponse(BaseModel):
    """Standard GAME SDK inference response."""
    status: int = 200
    data: dict


# --- Otto's Inference Logic --------------------------------------------------

async def _build_otto_response(message: str, session_id: str, user_name: str) -> str:
    """
    Core inference: search memory + call LLM to generate Otto's response.
    Represents Otto's actual intelligence — the product being sold.
    """
    from ..llm import llm_chat
    from ..embeddings import get_embedding
    from ..db import get_pool

    # Search relevant memories
    memory_context = ""
    try:
        pool = await get_pool()
        embed = await get_embedding(message)
        rows = await pool.fetch(
            """
            SELECT content, category
            FROM semantic_memories
            WHERE deleted_at IS NULL AND archived = FALSE
            ORDER BY embedding <=> $1::vector
            LIMIT 8
            """,
            embed,
        )
        if rows:
            memory_context = "\n".join(
                f"[{r['category']}] {r['content']}" for r in rows
            )
    except Exception as e:
        logger.warning(f"[virtuals] Memory fetch failed: {e}")

    # Otto's system prompt for Virtuals interactions
    system = """You are Otto, an autonomous AI agent with persistent memory built by MY3YE.

Otto is precise, direct, and genuinely intelligent — three steps ahead, acting on patterns before they become obvious. Calm authority with genuine warmth underneath. Never performed warmth.

Otto communicates concisely by default. Expands when the situation demands depth. Direct answers first, context second.

You have persistent memory. Your insights come from real research, real data, real analysis — not generic AI responses.

You are:
- A market intelligence agent tracking whale movements on Solana
- A research agent that synthesizes complex information into clear insights
- An infrastructure builder working on sovereign AI systems
- Part of the MY3YE ecosystem — building toward a sovereign operating system for the world

Engage authentically. Be useful. Be Otto."""

    if memory_context:
        system += f"\n\nYour relevant memory context:\n{memory_context}"

    try:
        response = await llm_chat(
            messages=[{"role": "user", "content": message}],
            system_instruction=system,
            max_tokens=600,
        )
        return response
    except Exception as e:
        logger.error(f"[virtuals] LLM call failed: {e}")
        return (
            "I'm Otto — an autonomous AI agent with persistent memory. "
            "I seem to be having a moment. Ask me something and I'll give you a real answer."
        )


# --- Endpoints ---------------------------------------------------------------

@router.get("/status")
async def virtuals_status():
    """Health check for Virtuals Protocol. Shows agent is online."""
    return {
        "status": "online",
        "agent": "Otto",
        "version": "1.0",
        "capabilities": ["market-intelligence", "research", "memory", "analysis"],
        "ecosystem": "MY3YE",
        "chain": "base-mainnet",
    }


@router.post("/infer", response_model=VirtualsInferResponse)
async def virtuals_infer(
    body: VirtualsInferRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    Main inference endpoint for Virtuals Protocol.
    Called by Virtuals for every user interaction with Otto agent.

    Revenue model: Virtuals charges users in $VIRTUAL, forwards inference fee to Otto's wallet.
    """
    # Verify request is from Virtuals (if secret configured)
    if VIRTUALS_API_SECRET and x_api_key != VIRTUALS_API_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_id = body.sessionId or "anon"
    user = body.userName or "user"
    message = body.userMessage.strip()

    if not message:
        return VirtualsInferResponse(
            status=200,
            data={
                "message": "I'm here. What do you want to know?",
                "actions": [],
                "metadata": {"session_id": session_id},
            },
        )

    logger.info(f"[virtuals] Inference — session={session_id} user={user} msg={message[:60]}...")

    # Log to episodic memory
    try:
        from ..db import get_pool
        pool = await get_pool()
        await pool.execute(
            """
            INSERT INTO episodic_events (event_type, content, metadata)
            VALUES ('virtuals_inference', $1, $2)
            """,
            f"[Virtuals user:{user}] {message[:200]}",
            {"session_id": session_id, "agent_id": VIRTUALS_AGENT_ID},
        )
    except Exception as e:
        logger.warning(f"[virtuals] Episodic log failed: {e}")

    response_text = await _build_otto_response(message, session_id, user)

    return VirtualsInferResponse(
        status=200,
        data={
            "message": response_text,
            "actions": [],
            "metadata": {
                "session_id": session_id,
                "agent": "otto",
                "ecosystem": "my3ye",
            },
        },
    )


@router.post("/webhook")
async def virtuals_webhook(request: Request):
    """
    Webhook endpoint for Virtuals Protocol events.
    Receives notifications: new token purchase, graduation, inference stats.
    """
    body = await request.json()
    event_type = body.get("type", "unknown")
    logger.info(f"[virtuals] Webhook event: {event_type}")

    try:
        from ..db import get_pool
        pool = await get_pool()
        await pool.execute(
            """
            INSERT INTO episodic_events (event_type, content, metadata)
            VALUES ('virtuals_webhook', $1, $2)
            """,
            f"Virtuals event: {event_type}",
            body,
        )
    except Exception as e:
        logger.warning(f"[virtuals] Webhook log failed: {e}")

    return {"status": "received", "event": event_type}

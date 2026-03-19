"""Core gateway message handler — unified agent loop through AgentOS kernel.

All channels funnel through handle_message(). Messages become interrupts
processed by the Reasoning Kernel.

Channel adapters only need to:
1. Normalize their input to GatewayMessage
2. Call handle_message() (or handle_message_stream() for WebSocket)
3. Deliver the GatewayResponse back to the platform
"""

import logging

from ..config import settings
from ..db import get_pool
from .models import GatewayMessage, GatewayResponse

log = logging.getLogger("otto.gateway.handler")

# Admin verification per channel
ADMIN_IDS = {
    "whatsapp": {
        "94743806705@s.whatsapp.net",   # Classic JID
        "26822473420906@lid",            # WhatsApp LID format
    },
    "email": {
        "abraottomev@gmail.com",        # Mev's personal Gmail
        "admin@otto.lk",                # Otto admin (self-sent / OTP)
    },
}


def is_admin(msg: GatewayMessage) -> bool:
    """Check if the sender is Admin (Mev)."""
    if msg.channel == "whatsapp":
        return msg.sender_id in ADMIN_IDS["whatsapp"]
    if msg.channel == "web":
        return msg.metadata.get("authenticated", False)
    if msg.channel == "email":
        return msg.sender_id.lower() in ADMIN_IDS["email"]
    return False


async def handle_message(msg: GatewayMessage) -> GatewayResponse:
    """Core agent loop — process any incoming message regardless of channel.

    Admin messages → kernel (RIC full context loop)
    Contact messages → contact_handler (per-contact conversation system)
    Unknown → ignored

    Returns GatewayResponse with Otto's reply.
    """
    if is_admin(msg):
        return await _handle_via_kernel(msg)

    # Route non-admin WhatsApp messages to contact conversation system
    if msg.channel == "whatsapp":
        from .contact_handler import handle_contact_message
        return await handle_contact_message(msg)

    return GatewayResponse(
        content="",
        channel=msg.channel,
        recipient_id=msg.sender_id,
        metadata={"status": "ignored", "reason": "not admin"},
    )


async def _handle_via_kernel(msg: GatewayMessage) -> GatewayResponse:
    """Kernel path: create interrupt → wait for result → return response.

    The kernel handles all context building, LLM calls, and post-processing.
    """
    from ..kernel import ivt, InterruptType
    from ..kernel.ric import process_interrupt
    from ..kernel.reasoning_kernel import is_kernel_running

    pool = await get_pool()

    # Classify message: is it a directive or a regular message?
    interrupt_type = InterruptType.SIG_MSG_ADMIN

    # Create interrupt
    interrupt_id = await ivt.enqueue(
        interrupt_type=interrupt_type,
        source=msg.channel,
        payload={
            "content": msg.content,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name or "Mev",
            "channel": msg.channel,
            "metadata": msg.metadata,
        },
    )

    # If kernel loop is running, wait for it to process
    if is_kernel_running():
        result = await ivt.wait_for_result(
            interrupt_id,
            timeout=settings.interrupt_timeout_seconds,
        )
    else:
        # Kernel loop not running — process synchronously
        interrupt = await ivt.dequeue()
        if interrupt:
            result_data = await process_interrupt(interrupt)
            result = await ivt.get_result(interrupt_id)
        else:
            result = None

    # Extract response
    if result and result.get("status") == "completed" and result.get("result"):
        reply = result["result"].get("content", "")
    elif result and result.get("status") == "failed":
        error = result.get("error", "unknown error")
        log.error(f"Kernel failed for interrupt {interrupt_id}: {error}")
        reply = "Hey Mev — I hit a processing error. Your message is logged and I'll handle it on the next heartbeat."
    else:
        log.warning(f"Kernel timed out for interrupt {interrupt_id}")
        reply = "Hey Mev — my processing is taking longer than expected. I'll catch up on the next heartbeat."

    return GatewayResponse(
        content=reply,
        channel=msg.channel,
        recipient_id=msg.sender_id,
        metadata={
            "status": "sent",
            "kernel": True,
            "interrupt_id": str(interrupt_id),
        },
    )


async def handle_message_stream(msg: GatewayMessage):
    """Streaming version of handle_message(). Yields text chunks.

    Used by the WebSocket endpoint for real-time partial responses.
    Falls back to non-streaming for non-admin or errors.

    Bypasses IVT enqueue/dequeue to avoid the race condition where the
    kernel background loop claims the interrupt before dequeue_by_id can.
    Instead, builds a synthetic interrupt dict and calls the stream handler
    directly. The ivt.complete() call inside will silently no-op on the
    fake UUID (UPDATE 0 rows, no error), while post-processing still runs.
    """
    if not is_admin(msg):
        return

    from uuid import uuid4
    from datetime import datetime, timezone
    from ..kernel.ric import _handle_admin_message_stream

    # Build synthetic interrupt dict — bypasses IVT to avoid race with kernel loop
    interrupt = {
        "id": uuid4(),
        "interrupt_type": "SIG_MSG_ADMIN",
        "priority": 1,
        "source": msg.channel,
        "payload": {
            "content": msg.content,
            "sender_id": msg.sender_id,
            "sender_name": msg.sender_name or "Mev",
            "channel": msg.channel,
            "metadata": msg.metadata,
        },
        "status": "processing",
        "agent_id": "otto",
        "created_at": datetime.now(timezone.utc),
        "started_at": datetime.now(timezone.utc),
        "metadata": {},
        "correlation_id": None,
    }

    async for chunk in _handle_admin_message_stream(interrupt):
        yield chunk



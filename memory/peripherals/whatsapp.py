"""WhatsApp peripheral — creates interrupts from WhatsApp messages.

Incoming messages from service.mjs arrive via POST /gateway/incoming.
This peripheral creates SIG_MSG_ADMIN interrupts and delivers responses
back to WhatsApp via the :3001 HTTP API.
"""

import logging

import httpx

from ..config import settings
from ..kernel.types import InterruptType
from ..kernel import ivt
from .base import Peripheral

log = logging.getLogger("otto.peripherals.whatsapp")

ADMIN_JID = "94743806705@s.whatsapp.net"


class WhatsAppPeripheral(Peripheral):
    """WhatsApp I/O device."""

    @property
    def name(self) -> str:
        return "whatsapp"

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{settings.whatsapp_url}/health")
                if r.status_code == 200:
                    return {"status": "ok", "peripheral": "whatsapp"}
        except Exception as e:
            return {"status": "error", "peripheral": "whatsapp", "error": str(e)}
        return {"status": "error", "peripheral": "whatsapp"}

    async def create_interrupt(
        self,
        content: str,
        sender_id: str,
        sender_name: str | None = None,
    ) -> str:
        """Create a kernel interrupt from a WhatsApp message.

        Returns the interrupt UUID.
        """
        is_admin = sender_id == ADMIN_JID
        itype = InterruptType.SIG_MSG_ADMIN if is_admin else InterruptType.SIG_MSG_ADMIN

        interrupt_id = await ivt.enqueue(
            interrupt_type=itype,
            source="whatsapp",
            payload={
                "content": content,
                "sender_id": sender_id,
                "sender_name": sender_name or "Mev",
                "channel": "whatsapp",
            },
        )
        return str(interrupt_id)

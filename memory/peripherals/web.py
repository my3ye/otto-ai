"""Web peripheral — creates interrupts from web chat messages.

Web chat messages arrive via WebSocket at /gateway/ws.
This peripheral creates SIG_MSG_ADMIN interrupts.
"""

import logging

from ..kernel.types import InterruptType
from ..kernel import ivt
from .base import Peripheral

log = logging.getLogger("otto.peripherals.web")


class WebPeripheral(Peripheral):
    """Web chat I/O device."""

    @property
    def name(self) -> str:
        return "web"

    async def health(self) -> dict:
        return {"status": "ok", "peripheral": "web"}

    async def create_interrupt(
        self,
        content: str,
        sender_name: str = "Mev",
    ) -> str:
        """Create a kernel interrupt from a web chat message.

        Returns the interrupt UUID.
        """
        interrupt_id = await ivt.enqueue(
            interrupt_type=InterruptType.SIG_MSG_ADMIN,
            source="web",
            payload={
                "content": content,
                "sender_id": "admin",
                "sender_name": sender_name,
                "channel": "web",
            },
        )
        return str(interrupt_id)

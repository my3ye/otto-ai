"""Scheduler peripheral — creates interrupts from systemd timers.

Generates SIG_HEARTBEAT and SIG_MAINTENANCE interrupts on schedule.
Heartbeats still run as detached Claude sessions (Phase 6 may migrate).
"""

import logging

from ..kernel.types import InterruptType
from ..kernel import ivt
from .base import Peripheral

log = logging.getLogger("otto.peripherals.scheduler")


class SchedulerPeripheral(Peripheral):
    """Timer-based I/O device for scheduled events."""

    @property
    def name(self) -> str:
        return "scheduler"

    async def health(self) -> dict:
        return {"status": "ok", "peripheral": "scheduler"}

    async def fire_heartbeat(self, heartbeat_type: str = "orchestrator") -> str:
        """Fire a heartbeat interrupt."""
        interrupt_id = await ivt.enqueue(
            interrupt_type=InterruptType.SIG_HEARTBEAT,
            source="scheduler",
            payload={"heartbeat_type": heartbeat_type},
        )
        return str(interrupt_id)

    async def fire_maintenance(self) -> str:
        """Fire a nightly maintenance interrupt."""
        interrupt_id = await ivt.enqueue(
            interrupt_type=InterruptType.SIG_MAINTENANCE,
            source="scheduler",
            payload={"trigger": "nightly"},
        )
        return str(interrupt_id)

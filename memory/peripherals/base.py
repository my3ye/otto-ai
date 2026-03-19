"""Abstract Peripheral interface for AgentOS I/O devices.

All peripherals (WhatsApp, Web, Scheduler, etc.) implement this interface.
They convert external events into kernel interrupts via the IVT.
"""

from abc import ABC, abstractmethod


class Peripheral(ABC):
    """Base class for kernel peripherals."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this peripheral (e.g., 'whatsapp', 'web', 'scheduler')."""
        ...

    @abstractmethod
    async def health(self) -> dict:
        """Check peripheral health. Returns {"status": "ok"|"error", ...}."""
        ...

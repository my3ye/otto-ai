"""AgentOS Peripherals — I/O device adapters that create kernel interrupts.

Each peripheral converts external events into interrupts for the kernel's IVT.
"""

from .base import Peripheral

__all__ = ["Peripheral"]

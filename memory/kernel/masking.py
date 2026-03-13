"""Interrupt Masking — defer non-critical interrupts during sync pulses.

Reference: arXiv 2602.20934v1 §3.1 (Interrupt Masking)

Masked interrupt types stay pending in the IVT (not lost, just deferred).
The IVT dequeue query excludes masked types.
"""

import logging
from contextlib import asynccontextmanager

log = logging.getLogger("otto.kernel.masking")

_masked_types: set[str] = set()


def mask(interrupt_type: str) -> None:
    """Mask an interrupt type (defer it during dequeue)."""
    _masked_types.add(interrupt_type)
    log.info(f"Masked interrupt type: {interrupt_type}")


def unmask(interrupt_type: str) -> None:
    """Unmask an interrupt type (allow dequeue again)."""
    _masked_types.discard(interrupt_type)
    log.info(f"Unmasked interrupt type: {interrupt_type}")


def get_masked_types() -> set[str]:
    """Get currently masked interrupt types."""
    return set(_masked_types)


def is_masked(interrupt_type: str) -> bool:
    """Check if an interrupt type is currently masked."""
    return interrupt_type in _masked_types


@asynccontextmanager
async def critical_section(*types_to_mask: str):
    """Context manager that masks interrupt types for the duration.

    Usage:
        async with critical_section("sig_heartbeat", "sig_maintenance"):
            # These types are deferred during this block
            await do_sync_work()
    """
    for t in types_to_mask:
        mask(t)
    try:
        yield
    finally:
        for t in types_to_mask:
            unmask(t)

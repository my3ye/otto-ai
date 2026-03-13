"""Reasoning Kernel — central async processing loop for AgentOS.

Reference: arXiv 2602.20934v1 §3 (Reasoning Kernel Architecture)

Thin wrapper around CognitiveScheduler — preserves the existing API
so all callers (api.py, kernel_routes.py, etc.) continue working.
"""

import logging

from .scheduler import get_scheduler

log = logging.getLogger("otto.kernel.reasoning_kernel")


async def start_kernel_loop():
    """Start the kernel's async interrupt processing loop."""
    scheduler = get_scheduler()
    scheduler.start()
    log.info("Reasoning Kernel started (via CognitiveScheduler)")


async def stop_kernel_loop():
    """Stop the kernel processing loop."""
    scheduler = get_scheduler()
    await scheduler.stop()
    log.info("Reasoning Kernel shutdown complete")


def ensure_kernel_running():
    """Ensure the kernel loop is running (called during app startup)."""
    scheduler = get_scheduler()
    if not scheduler.is_running:
        scheduler.start()
        log.info("Kernel loop task created (via CognitiveScheduler)")


def is_kernel_running() -> bool:
    """Check if the kernel loop is active."""
    return get_scheduler().is_running

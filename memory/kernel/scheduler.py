"""Cognitive Scheduler — multi-agent interrupt processing orchestrator.

Reference: arXiv 2602.20934v1 §8 (Multi-Agent Coordination)

Replaces the raw kernel loop with agent-aware processing:
- "otto" agent: inline RIC processing (low-latency conversational path)
- CLI agents (heartbeat, reflection, task_worker): lifecycle tracking only
  (actual work runs as detached Claude Code CLI sessions)

The scheduler watches the global IVT event and dispatches to the right agent.
"""

import asyncio
import logging

from ..config import settings
from . import ivt
from .ric import process_interrupt
from .agents import update_agent_status, log_agent_activity, get_agent

log = logging.getLogger("otto.kernel.scheduler")

_scheduler: "CognitiveScheduler | None" = None


class CognitiveScheduler:
    """Central scheduler for multi-agent interrupt processing."""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running: bool = False

    @property
    def is_running(self) -> bool:
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> None:
        """Start the scheduler loop as a background task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())
            log.info("Cognitive Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        log.info("Cognitive Scheduler stopped")

    async def _loop(self) -> None:
        """Main processing loop — watches IVT and dispatches interrupts."""
        self._running = True
        event = ivt.get_interrupt_event()

        log.info("Cognitive Scheduler loop running")

        while self._running:
            try:
                # Wait for interrupt notification or periodic check
                try:
                    await asyncio.wait_for(event.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    pass

                event.clear()

                # Process all pending interrupts
                while self._running:
                    interrupt = await ivt.dequeue()
                    if not interrupt:
                        break

                    agent_id = interrupt.get("agent_id", "otto")

                    if agent_id == "otto":
                        # Inline RIC processing for conversational agent
                        try:
                            await asyncio.wait_for(
                                process_interrupt(interrupt),
                                timeout=settings.interrupt_timeout_seconds,
                            )
                        except asyncio.TimeoutError:
                            log.error(f"Interrupt {interrupt['id']} timed out after {settings.interrupt_timeout_seconds}s")
                            await ivt.fail(interrupt["id"], "timeout")
                    else:
                        # CLI agents: acknowledge interrupt, track lifecycle
                        try:
                            await update_agent_status(agent_id, "active", last_interrupt_id=interrupt["id"])
                            await log_agent_activity(
                                agent_id, "interrupt_received",
                                interrupt_id=interrupt["id"],
                                details={"type": interrupt["interrupt_type"]},
                            )
                            await ivt.complete(interrupt["id"], {"content": f"Routed to agent {agent_id}"})
                        except Exception as e:
                            log.warning(f"Agent {agent_id} interrupt handling failed: {e}")
                            await ivt.fail(interrupt["id"], str(e))

            except Exception as e:
                log.error(f"Scheduler loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

        log.info("Cognitive Scheduler loop stopped")

    async def record_cli_agent_start(self, agent_id: str) -> None:
        """Called when a CLI agent (heartbeat/reflection/task) starts."""
        await update_agent_status(agent_id, "active")
        await log_agent_activity(agent_id, "started")
        log.info(f"CLI agent {agent_id} started")

    async def record_cli_agent_end(self, agent_id: str, success: bool = True) -> None:
        """Called when a CLI agent completes."""
        status = "idle" if success else "error"
        error_msg = None if success else "CLI agent reported failure"
        await update_agent_status(agent_id, status, error_message=error_msg)
        await log_agent_activity(
            agent_id,
            "completed" if success else "failed",
            details={"success": success},
        )
        log.info(f"CLI agent {agent_id} ended (success={success})")


def get_scheduler() -> CognitiveScheduler:
    """Get or create the singleton CognitiveScheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CognitiveScheduler()
    return _scheduler

"""Interrupt Vector Table — priority queue and dispatch for kernel interrupts.

Reference: arXiv 2602.20934v1 §3.1 (Interrupt-Driven Processing)

The IVT manages the lifecycle of interrupts:
1. Enqueue: peripherals submit interrupts with type + priority + payload
2. Dequeue: kernel pulls next highest-priority pending interrupt
3. Complete/Fail: kernel records the result

Multi-agent: interrupts are scoped to agents via agent_id column.
Auto-routing assigns interrupts based on agent config.interrupt_types.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from ..db import get_pool
from .types import InterruptType, InterruptStatus, INTERRUPT_PRIORITIES

log = logging.getLogger("otto.kernel.ivt")

# Global event: signaled when any interrupt arrives
_interrupt_event: asyncio.Event | None = None
# Per-agent events: signaled when an interrupt for a specific agent arrives
_agent_events: dict[str, asyncio.Event] = {}


def get_interrupt_event(agent_id: str | None = None) -> asyncio.Event:
    """Get an interrupt notification event.

    Args:
        agent_id: If provided, returns agent-specific event.
                  If None, returns the global event (any agent).
    """
    if agent_id is None:
        global _interrupt_event
        if _interrupt_event is None:
            _interrupt_event = asyncio.Event()
        return _interrupt_event
    else:
        if agent_id not in _agent_events:
            _agent_events[agent_id] = asyncio.Event()
        return _agent_events[agent_id]


async def enqueue(
    interrupt_type: InterruptType | str,
    source: str,
    payload: dict,
    priority: int | None = None,
    correlation_id: UUID | None = None,
    metadata: dict | None = None,
    agent_id: str | None = None,
) -> UUID:
    """Submit an interrupt to the queue.

    Args:
        interrupt_type: Signal type (e.g., SIG_MSG_ADMIN).
        source: Origin (whatsapp, web, scheduler, task_engine, system).
        payload: Interrupt-specific data.
        priority: Override priority (default: looked up from INTERRUPT_PRIORITIES).
        correlation_id: Link related interrupts (e.g., request/response).
        metadata: Extra metadata.
        agent_id: Target agent. If None, auto-routes based on interrupt_type.

    Returns:
        UUID of the created interrupt.
    """
    itype = interrupt_type if isinstance(interrupt_type, str) else interrupt_type.value

    if priority is None:
        try:
            priority = INTERRUPT_PRIORITIES[InterruptType(itype)]
        except (KeyError, ValueError):
            priority = 5

    # Auto-route to agent if not specified
    if agent_id is None:
        try:
            from .agents import route_interrupt_to_agent
            agent_id = route_interrupt_to_agent(itype)
        except Exception:
            agent_id = "otto"

    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO interrupt_queue
           (interrupt_type, priority, source, payload, status, correlation_id, metadata, agent_id)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           RETURNING id""",
        itype,
        priority,
        source,
        payload,
        InterruptStatus.PENDING.value,
        correlation_id,
        metadata or {},
        agent_id,
    )

    interrupt_id = row["id"]
    log.info(f"Enqueued interrupt {interrupt_id}: {itype} (P{priority}) → agent={agent_id} from {source}")

    # Signal both global and agent-specific events
    get_interrupt_event().set()
    if agent_id:
        get_interrupt_event(agent_id).set()

    return interrupt_id


async def dequeue(agent_id: str | None = None) -> dict | None:
    """Atomically dequeue the next highest-priority pending interrupt.

    Args:
        agent_id: If provided, only dequeue for this agent.
                  If None, dequeues any agent's interrupt (existing behavior).

    Uses UPDATE ... RETURNING with a subquery to ensure atomic claim.
    Respects interrupt masking — masked types are skipped (deferred, not lost).
    Returns the full interrupt row as a dict, or None if queue is empty.
    """
    from .masking import get_masked_types

    pool = await get_pool()
    masked = get_masked_types()

    # Build WHERE conditions
    conditions = ["status = $2"]
    params: list = [InterruptStatus.PROCESSING.value, InterruptStatus.PENDING.value]
    param_idx = 3

    if agent_id is not None:
        conditions.append(f"agent_id = ${param_idx}")
        params.append(agent_id)
        param_idx += 1

    if masked:
        excluded = list(masked)
        conditions.append(f"interrupt_type != ALL(${param_idx})")
        params.append(excluded)
        param_idx += 1

    where_clause = " AND ".join(conditions)

    row = await pool.fetchrow(
        f"""UPDATE interrupt_queue
           SET status = $1, started_at = NOW()
           WHERE id = (
               SELECT id FROM interrupt_queue
               WHERE {where_clause}
               ORDER BY priority ASC, created_at ASC
               LIMIT 1
               FOR UPDATE SKIP LOCKED
           )
           RETURNING id, interrupt_type, priority, source, payload,
                     status, correlation_id, created_at, started_at, metadata, agent_id""",
        *params,
    )

    if not row:
        return None

    result = dict(row)
    log.info(f"Dequeued interrupt {result['id']}: {result['interrupt_type']} (P{result['priority']}) agent={result.get('agent_id', 'otto')}")
    return result


async def dequeue_by_id(interrupt_id: UUID) -> dict | None:
    """Atomically claim and dequeue a specific interrupt by ID.

    Used by the WebSocket streaming handler to avoid racing with the kernel loop.
    Marks the interrupt as PROCESSING and returns it.
    Returns None if already claimed or not found.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """UPDATE interrupt_queue
           SET status = $1, started_at = NOW()
           WHERE id = $2 AND status = $3
           RETURNING id, interrupt_type, priority, source, payload,
                     status, correlation_id, created_at, started_at, metadata, agent_id""",
        InterruptStatus.PROCESSING.value,
        interrupt_id,
        InterruptStatus.PENDING.value,
    )
    if not row:
        return None
    result = dict(row)
    log.info(f"Dequeued-by-id interrupt {result['id']}: {result['interrupt_type']} (P{result['priority']})")
    return result


async def complete(
    interrupt_id: UUID,
    result: dict | None = None,
) -> None:
    """Mark an interrupt as completed with its result."""
    pool = await get_pool()
    await pool.execute(
        """UPDATE interrupt_queue
           SET status = $1, completed_at = NOW(), result = $2
           WHERE id = $3""",
        InterruptStatus.COMPLETED.value,
        result or {},
        interrupt_id,
    )
    log.info(f"Completed interrupt {interrupt_id}")


async def fail(
    interrupt_id: UUID,
    error: str,
) -> None:
    """Mark an interrupt as failed with an error message."""
    pool = await get_pool()
    await pool.execute(
        """UPDATE interrupt_queue
           SET status = $1, completed_at = NOW(), error = $2
           WHERE id = $3""",
        InterruptStatus.FAILED.value,
        error,
        interrupt_id,
    )
    log.warning(f"Failed interrupt {interrupt_id}: {error[:100]}")


async def get_result(interrupt_id: UUID) -> dict | None:
    """Poll for an interrupt's result. Returns None if not yet completed."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, status, result, error, completed_at
           FROM interrupt_queue WHERE id = $1""",
        interrupt_id,
    )
    if not row:
        return None
    return dict(row)


async def wait_for_result(
    interrupt_id: UUID,
    timeout: float = 30.0,
    poll_interval: float = 0.1,
) -> dict | None:
    """Wait for an interrupt to complete, with timeout.

    Returns the result dict or None on timeout.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        result = await get_result(interrupt_id)
        if result and result["status"] in (
            InterruptStatus.COMPLETED.value,
            InterruptStatus.FAILED.value,
        ):
            return result
        await asyncio.sleep(poll_interval)
    return None


async def queue_depth(agent_id: str | None = None) -> dict:
    """Get current queue statistics, optionally scoped to an agent."""
    pool = await get_pool()

    if agent_id:
        rows = await pool.fetch(
            """SELECT status, COUNT(*) as cnt FROM interrupt_queue
               WHERE agent_id = $1 GROUP BY status""",
            agent_id,
        )
    else:
        rows = await pool.fetch(
            """SELECT status, COUNT(*) as cnt FROM interrupt_queue
               GROUP BY status"""
        )

    counts = {r["status"]: r["cnt"] for r in rows}
    return {
        "pending": counts.get("pending", 0),
        "processing": counts.get("processing", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
        "total": sum(counts.values()),
    }


async def recent_interrupts(limit: int = 20) -> list[dict]:
    """Get recent interrupts for monitoring."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, interrupt_type, priority, source, status,
                  created_at, started_at, completed_at, error, agent_id
           FROM interrupt_queue
           ORDER BY created_at DESC LIMIT $1""",
        limit,
    )
    return [dict(r) for r in rows]

"""Price Monitors — Conditional order polling (limit/stop-loss/DCA).

Phase 2 feature. Phase 1: CRUD only, polling engine in Phase 2.
"""

import logging
from typing import Optional
from ..db import get_pool

log = logging.getLogger("otto.crypto.monitors")


async def create_monitor(
    monitor_type: str,
    chain: str,
    token_in: str,
    token_out: Optional[str] = None,
    amount_usd: Optional[float] = None,
    trigger_price: Optional[float] = None,
    trigger_type: Optional[str] = None,
    trigger_pct: Optional[float] = None,
    dca_interval_hours: Optional[int] = None,
    dca_max_runs: Optional[int] = None,
    nl_description: Optional[str] = None,
    expires_at=None,
) -> dict:
    """Create a price monitor (conditional order) in the DB."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO price_monitors
            (monitor_type, chain, token_in, token_out, amount_usd, trigger_price,
             trigger_type, trigger_pct, dca_interval_hours, dca_max_runs,
             nl_description, expires_at)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING *
    """, monitor_type, chain, token_in, token_out, amount_usd, trigger_price,
        trigger_type, trigger_pct, dca_interval_hours, dca_max_runs,
        nl_description, expires_at)
    return dict(row)


async def list_monitors(status: str = "active", limit: int = 50) -> list[dict]:
    """List price monitors by status."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT * FROM price_monitors
        WHERE status = $1
        ORDER BY created_at DESC
        LIMIT $2
    """, status, limit)
    return [dict(r) for r in rows]


async def cancel_monitor(monitor_id: str) -> bool:
    """Cancel an active price monitor."""
    pool = await get_pool()
    result = await pool.execute("""
        UPDATE price_monitors
        SET status = 'cancelled'
        WHERE id = $1 AND status = 'active'
    """, monitor_id)
    return result == "UPDATE 1"


async def check_monitors() -> list[dict]:
    """Check all active monitors and trigger any that are due.

    Phase 2: This will call executor.py when conditions are met.
    Phase 1: Stub — just returns due monitors without executing.
    """
    pool = await get_pool()
    # Get monitors due for checking
    rows = await pool.fetch("""
        SELECT * FROM price_monitors
        WHERE status = 'active'
        AND (next_run_at IS NULL OR next_run_at <= NOW())
        ORDER BY created_at ASC
        LIMIT 50
    """)
    due_monitors = [dict(r) for r in rows]
    log.info(f"check_monitors: {len(due_monitors)} monitors due (Phase 2 execution not yet wired)")
    return due_monitors

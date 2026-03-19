"""Native Signal Board — CRUD + analytics for crypto trade signals.

Replaces bankrsignals.com with Otto's own sovereign signal board.
"""

import logging
from typing import Optional
from ..db import get_pool

log = logging.getLogger("otto.crypto.signals")


async def publish_signal(
    token: str,
    chain: str,
    direction: str,
    confidence: Optional[float] = None,
    rationale: Optional[str] = None,
    entry_price: Optional[float] = None,
    target_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    tx_hash: Optional[str] = None,
    trade_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Publish a new signal to the native signal board."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO crypto_signals
            (token, chain, direction, confidence, rationale, entry_price,
             target_price, stop_price, tx_hash, trade_id, metadata)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        RETURNING *
    """, token.upper(), chain, direction, confidence, rationale, entry_price,
        target_price, stop_price, tx_hash,
        trade_id if trade_id else None,
        metadata)
    return dict(row)


async def list_signals(status: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List signals from the signal board."""
    pool = await get_pool()
    if status:
        rows = await pool.fetch("""
            SELECT * FROM crypto_signals
            WHERE status = $1
            ORDER BY published_at DESC
            LIMIT $2
        """, status, limit)
    else:
        rows = await pool.fetch("""
            SELECT * FROM crypto_signals
            ORDER BY published_at DESC
            LIMIT $1
        """, limit)
    return [dict(r) for r in rows]


async def close_signal(signal_id: str, win: bool, exit_price: float, pnl_pct: float) -> Optional[dict]:
    """Close a signal with outcome."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        UPDATE crypto_signals
        SET status = 'closed', win = $2, exit_price = $3, pnl_pct = $4, closed_at = NOW()
        WHERE id = $1 AND status = 'open'
        RETURNING *
    """, signal_id, win, exit_price, pnl_pct)
    return dict(row) if row else None


async def get_signal_stats() -> dict:
    """Compute win rate and PnL stats for the signal board."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT
            COUNT(*) FILTER (WHERE status = 'open') AS open_count,
            COUNT(*) FILTER (WHERE status = 'closed') AS closed_count,
            COUNT(*) FILTER (WHERE win = TRUE) AS wins,
            COUNT(*) FILTER (WHERE win = FALSE) AS losses,
            ROUND(AVG(pnl_pct) FILTER (WHERE status = 'closed'), 2) AS avg_pnl_pct,
            ROUND(AVG(confidence), 2) AS avg_confidence
        FROM crypto_signals
    """)
    data = dict(row)
    closed = data.get("closed_count") or 0
    wins = data.get("wins") or 0
    data["win_rate"] = round(wins / closed, 3) if closed > 0 else None
    return data

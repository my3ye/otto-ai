"""Koink Treasury — event recording and balance queries.

Tracks treasury distributions, allocations, and withdrawals off-chain.
In Phase 0: manual entry only. Phase 1+: synced from KoinkTreasury.sol events.
"""

import json
import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.koink.treasury")

VALID_EVENT_TYPES = {"distribution", "allocation", "withdrawal"}


async def record_treasury_event(
    token_id: str,
    event_type: str,
    amount: float,
    recipient: Optional[str] = None,
    tx_hash: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Record a treasury event (distribution, allocation, or withdrawal).

    Args:
        token_id: koink_tokens.id
        event_type: distribution | allocation | withdrawal
        amount: Token amount involved
        recipient: Wallet address of the recipient (optional)
        tx_hash: On-chain transaction hash (optional — None in Phase 0)
        metadata: Additional JSONB data

    Returns:
        Created event record dict.

    Raises:
        ValueError: If event_type is invalid or token not found.
    """
    if event_type not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type '{event_type}'. Must be: {', '.join(VALID_EVENT_TYPES)}")

    pool = await get_pool()

    # Verify token exists
    try:
        token_uuid = UUID(token_id)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid token_id format: {token_id}")
    exists = await pool.fetchval("SELECT 1 FROM koink_tokens WHERE id = $1", token_uuid)
    if not exists:
        raise ValueError(f"koink_token not found: {token_id}")

    row = await pool.fetchrow("""
        INSERT INTO koink_treasury_events
            (token_id, event_type, amount, recipient, tx_hash, metadata)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
    """, token_uuid, event_type, amount,
        recipient.lower() if recipient else None,
        tx_hash,
        json.dumps(metadata) if metadata else None)

    log.info(f"Treasury event recorded: {row['id']} ({event_type} {amount} for token {token_id})")
    return dict(row)


async def get_treasury_events(
    token_id: str,
    event_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Fetch treasury events for a token."""
    pool = await get_pool()

    try:
        token_uuid = UUID(token_id)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid token_id format: {token_id}")

    if event_type:
        rows = await pool.fetch("""
            SELECT * FROM koink_treasury_events
            WHERE token_id = $1 AND event_type = $2
            ORDER BY created_at DESC
            LIMIT $3
        """, token_uuid, event_type, limit)
    else:
        rows = await pool.fetch("""
            SELECT * FROM koink_treasury_events
            WHERE token_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        """, token_uuid, limit)

    return [dict(r) for r in rows]


async def get_treasury_balance(token_id: str) -> dict:
    """Compute treasury balance and event summary for a token.

    Returns:
        {
          "token_id": ...,
          "total_inflow": float,    # sum of allocation events
          "total_outflow": float,   # sum of distribution + withdrawal events
          "balance": float,         # inflow - outflow
          "event_counts": {type: count},
          "last_event_at": datetime | None,
        }
    """
    pool = await get_pool()

    try:
        token_uuid = UUID(token_id)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid token_id format: {token_id}")

    # Verify token exists
    exists = await pool.fetchval("SELECT 1 FROM koink_tokens WHERE id = $1", token_uuid)
    if not exists:
        raise ValueError(f"koink_token not found: {token_id}")

    stats = await pool.fetchrow("""
        SELECT
            COALESCE(SUM(CASE WHEN event_type = 'allocation' THEN amount ELSE 0 END), 0) AS total_inflow,
            COALESCE(SUM(CASE WHEN event_type IN ('distribution', 'withdrawal') THEN amount ELSE 0 END), 0) AS total_outflow,
            MAX(created_at) AS last_event_at
        FROM koink_treasury_events
        WHERE token_id = $1
    """, token_uuid)

    counts = await pool.fetch("""
        SELECT event_type, COUNT(*) AS cnt
        FROM koink_treasury_events
        WHERE token_id = $1
        GROUP BY event_type
    """, token_uuid)

    total_inflow = float(stats["total_inflow"])
    total_outflow = float(stats["total_outflow"])

    return {
        "token_id": token_id,
        "total_inflow": total_inflow,
        "total_outflow": total_outflow,
        "balance": total_inflow - total_outflow,
        "event_counts": {r["event_type"]: r["cnt"] for r in counts},
        "last_event_at": stats["last_event_at"],
        "note": "Phase 0: manual entries only. Phase 1 will sync from KoinkTreasury.sol on-chain events.",
    }

"""Koink DHM — Diamond Hands Multiplier position tracking.

Tracks off-chain mirrors of DiamondHandsVault on-chain state.
In Phase 0, positions are synthetic (calculated from hold times).
In Phase 1+, positions are synced from contract events.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from ..db import get_pool
from .standard import calculate_dhm_multiplier, calculate_sell_tax_for_holder

log = logging.getLogger("otto.koink.dhm")


async def upsert_dhm_position(
    token_id: str,
    holder_address: str,
    balance: float,
    hold_start_at: Optional[datetime] = None,
    synthetic: bool = True,
) -> dict:
    """Create or update a DHM position for a holder.

    Args:
        token_id: koink_tokens.id
        holder_address: Wallet address of the holder
        balance: Token balance held
        hold_start_at: When the holder first acquired (defaults to NOW)
        synthetic: True = calculated locally, False = from on-chain event

    Returns:
        Updated position dict with calculated multiplier.
    """
    pool = await get_pool()

    if hold_start_at is None:
        hold_start_at = datetime.now(timezone.utc)

    # Fetch token's DHM params to calculate multiplier
    token_row = await pool.fetchrow("""
        SELECT dhm_months, dhm_max_multiplier FROM koink_tokens WHERE id = $1
    """, UUID(token_id))

    if not token_row:
        raise ValueError(f"koink_token not found: {token_id}")

    hold_days = (datetime.now(timezone.utc) - hold_start_at).days
    multiplier = calculate_dhm_multiplier(
        hold_days=hold_days,
        dhm_months=token_row["dhm_months"],
        max_multiplier=float(token_row["dhm_max_multiplier"]),
    )

    row = await pool.fetchrow("""
        INSERT INTO koink_dhm_positions
            (token_id, holder_address, balance, hold_start_at, multiplier, synthetic, last_snapshot)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (token_id, holder_address)
        DO UPDATE SET
            balance = EXCLUDED.balance,
            multiplier = EXCLUDED.multiplier,
            synthetic = EXCLUDED.synthetic,
            last_snapshot = NOW()
        RETURNING *
    """, UUID(token_id), holder_address.lower(), balance, hold_start_at, multiplier, synthetic)

    return dict(row)


async def get_dhm_positions(
    token_id: str,
    limit: int = 100,
) -> list[dict]:
    """Get DHM positions for a token, ranked by multiplier (desc)."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT p.*,
               EXTRACT(EPOCH FROM (NOW() - p.hold_start_at)) / 86400 AS hold_days
        FROM koink_dhm_positions p
        WHERE p.token_id = $1
        ORDER BY p.multiplier DESC, p.balance DESC
        LIMIT $2
    """, UUID(token_id), limit)
    return [dict(r) for r in rows]


async def snapshot_dhm_positions(token_id: str) -> dict:
    """Recalculate all DHM multipliers for a token based on current hold times.

    Used by the admin /koink/dhm/snapshot endpoint to refresh synthetic state.

    Returns:
        Summary of positions updated.
    """
    pool = await get_pool()

    token_row = await pool.fetchrow("""
        SELECT dhm_months, dhm_max_multiplier FROM koink_tokens WHERE id = $1
    """, UUID(token_id))

    if not token_row:
        raise ValueError(f"koink_token not found: {token_id}")

    positions = await pool.fetch("""
        SELECT id, hold_start_at FROM koink_dhm_positions WHERE token_id = $1
    """, UUID(token_id))

    updated = 0
    for pos in positions:
        hold_days = (datetime.now(timezone.utc) - pos["hold_start_at"]).days
        multiplier = calculate_dhm_multiplier(
            hold_days=hold_days,
            dhm_months=token_row["dhm_months"],
            max_multiplier=float(token_row["dhm_max_multiplier"]),
        )
        await pool.execute("""
            UPDATE koink_dhm_positions
            SET multiplier = $1, last_snapshot = NOW()
            WHERE id = $2
        """, multiplier, pos["id"])
        updated += 1

    log.info(f"DHM snapshot complete for token {token_id}: {updated} positions updated")
    return {"token_id": token_id, "positions_updated": updated}


async def get_holder_stats(token_id: str, holder_address: str) -> Optional[dict]:
    """Get a single holder's DHM stats including current sell tax."""
    pool = await get_pool()

    row = await pool.fetchrow("""
        SELECT p.*,
               kt.sell_tax_initial_bps,
               kt.sell_tax_floor_bps,
               kt.dhm_months,
               EXTRACT(EPOCH FROM (NOW() - p.hold_start_at)) / 86400 AS hold_days
        FROM koink_dhm_positions p
        JOIN koink_tokens kt ON kt.id = p.token_id
        WHERE p.token_id = $1 AND p.holder_address = $2
    """, UUID(token_id), holder_address.lower())

    if not row:
        return None

    d = dict(row)
    hold_days = int(d.get("hold_days", 0) or 0)
    d["current_sell_tax_bps"] = calculate_sell_tax_for_holder(
        hold_days=hold_days,
        sell_tax_initial_bps=d["sell_tax_initial_bps"],
        sell_tax_floor_bps=d["sell_tax_floor_bps"],
        dhm_months=d["dhm_months"],
    )
    return d

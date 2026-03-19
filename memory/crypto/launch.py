"""Token Launch — Doppler (Base) and Raydium LaunchLab (Solana).

Phase 3 feature. Phase 1: DB record CRUD only.
"""

import logging
from typing import Optional
from ..db import get_pool

log = logging.getLogger("otto.crypto.launch")


async def create_launch_record(
    name: str,
    symbol: str,
    chain: str,
    launch_mechanism: str,
    total_supply: Optional[float] = None,
    creator_fee_pct: Optional[float] = None,
    description: Optional[str] = None,
) -> dict:
    """Create a token launch record in the DB."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO token_launches
            (name, symbol, chain, launch_mechanism, total_supply, creator_fee_pct, description)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        RETURNING *
    """, name, symbol.upper(), chain, launch_mechanism, total_supply, creator_fee_pct, description)
    return dict(row)


async def list_launches(limit: int = 50) -> list[dict]:
    """List token launches."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT * FROM token_launches
        ORDER BY created_at DESC
        LIMIT $1
    """, limit)
    return [dict(r) for r in rows]


async def launch_on_base(params: dict) -> dict:
    """Launch a token on Base using Doppler.

    Phase 3 — not yet implemented.
    """
    record = await create_launch_record(
        name=params.get("name", ""),
        symbol=params.get("symbol", ""),
        chain="base",
        launch_mechanism="doppler",
        total_supply=params.get("supply"),
        creator_fee_pct=params.get("creator_fee_pct"),
        description=params.get("description"),
    )
    log.info(f"Token launch record created: {record['id']} — Phase 3 execution not yet implemented")
    return {**record, "message": "Launch recorded. Doppler execution will be wired in Phase 3."}


async def launch_on_solana(params: dict) -> dict:
    """Launch a token on Solana using Raydium LaunchLab.

    Phase 3 — not yet implemented.
    """
    record = await create_launch_record(
        name=params.get("name", ""),
        symbol=params.get("symbol", ""),
        chain="solana",
        launch_mechanism="raydium_launchlab",
        total_supply=params.get("supply"),
        creator_fee_pct=params.get("creator_fee_pct"),
        description=params.get("description"),
    )
    log.info(f"Token launch record created: {record['id']} — Phase 3 execution not yet implemented")
    return {**record, "message": "Launch recorded. Raydium LaunchLab execution will be wired in Phase 3."}

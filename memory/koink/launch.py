"""Koink Token Launch — DB CRUD for koink_tokens + token_launches.

Phase 0: Records intent, validates params, creates DB records.
Phase 1: Will wire OWS signing + async contract deployment via task queue.
"""

import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool
from .standard import validate_koink_params, get_vrf_type_for_chain, KOINK_DEFAULTS

log = logging.getLogger("otto.koink.launch")


async def create_koink_token(
    name: str,
    symbol: str,
    chain: str,
    total_supply: float = 1_000_000_000,
    description: Optional[str] = None,
    anti_whale_cap_pct: float = 2.0,
    sell_tax_initial_bps: int = 500,
    sell_tax_floor_bps: int = 100,
    treasury_pct: float = 20.0,
    dhm_enabled: bool = True,
    dhm_max_multiplier: float = 3.0,
    dhm_months: int = 12,
    vrf_type: Optional[str] = None,
    creator_fee_pct: float = 2.0,
    liquidity_pct: float = 60.0,
) -> dict:
    """Create a new $KOINK Standard token record.

    Validates parameters, creates both token_launches (unified view) and
    koink_tokens (authoritative Koink record) in a single transaction.

    Returns:
        dict with both the launch record and koink_token record merged.

    Raises:
        ValueError: If parameters fail KOINK Standard validation.
    """
    # Auto-select VRF type if not specified
    if vrf_type is None:
        vrf_type = get_vrf_type_for_chain(chain)

    # Validate all params
    params = {
        "name": name,
        "symbol": symbol,
        "chain": chain,
        "total_supply": total_supply,
        "anti_whale_cap_pct": anti_whale_cap_pct,
        "sell_tax_initial_bps": sell_tax_initial_bps,
        "sell_tax_floor_bps": sell_tax_floor_bps,
        "treasury_pct": treasury_pct,
        "dhm_max_multiplier": dhm_max_multiplier,
        "dhm_months": dhm_months,
        "creator_fee_pct": creator_fee_pct,
        "liquidity_pct": liquidity_pct,
        "vrf_type": vrf_type,
    }
    valid, errors = validate_koink_params(params)
    if not valid:
        raise ValueError(f"KOINK Standard validation failed: {'; '.join(errors)}")

    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Create base launch record (for unified /crypto/launches view)
            launch_row = await conn.fetchrow("""
                INSERT INTO token_launches
                    (name, symbol, chain, launch_mechanism, total_supply,
                     creator_fee_pct, description,
                     koink_standard, anti_whale_cap_pct, sell_tax_initial_bps,
                     sell_tax_floor_bps, treasury_pct, dhm_enabled,
                     dhm_max_multiplier, dhm_months, vrf_type)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
                RETURNING *
            """, name, symbol.upper(), chain, "koink_standard",
                total_supply, creator_fee_pct, description,
                True, anti_whale_cap_pct, sell_tax_initial_bps,
                sell_tax_floor_bps, treasury_pct, dhm_enabled,
                dhm_max_multiplier, dhm_months, vrf_type)

            # 2. Create authoritative koink_tokens record
            koink_row = await conn.fetchrow("""
                INSERT INTO koink_tokens
                    (launch_id, name, symbol, chain, total_supply, description,
                     anti_whale_cap_pct, sell_tax_initial_bps, sell_tax_floor_bps,
                     treasury_pct, dhm_enabled, dhm_max_multiplier, dhm_months,
                     vrf_type, creator_fee_pct, liquidity_pct, status)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
                RETURNING *
            """, launch_row["id"], name, symbol.upper(), chain, total_supply, description,
                anti_whale_cap_pct, sell_tax_initial_bps, sell_tax_floor_bps,
                treasury_pct, dhm_enabled, dhm_max_multiplier, dhm_months,
                vrf_type, creator_fee_pct, liquidity_pct, "pending")

    log.info(f"Koink token created: {koink_row['id']} ({symbol.upper()} on {chain})")
    return {
        **dict(koink_row),
        "launch_id": str(launch_row["id"]),
        "message": (
            "Token record created with KOINK Standard parameters. "
            "Phase 1 contract deployment will be wired after OWS deploy wallet registration."
        ),
    }


async def get_koink_token(token_id: str) -> Optional[dict]:
    """Fetch a single koink_token by ID."""
    try:
        token_uuid = UUID(token_id)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid token_id format: {token_id}")
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT kt.*, tl.status as launch_status
        FROM koink_tokens kt
        LEFT JOIN token_launches tl ON tl.id = kt.launch_id
        WHERE kt.id = $1
    """, token_uuid)
    return dict(row) if row else None


async def list_koink_tokens(
    chain: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List koink_tokens with optional filters."""
    pool = await get_pool()

    conditions = []
    args: list = []

    if chain:
        args.append(chain)
        conditions.append(f"kt.chain = ${len(args)}")
    if status:
        args.append(status)
        conditions.append(f"kt.status = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.append(limit)

    rows = await pool.fetch(f"""
        SELECT kt.*, tl.status as launch_status
        FROM koink_tokens kt
        LEFT JOIN token_launches tl ON tl.id = kt.launch_id
        {where}
        ORDER BY kt.created_at DESC
        LIMIT ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def update_koink_status(
    token_id: str,
    status: str,
    contract_address: Optional[str] = None,
    deploy_tx_hash: Optional[str] = None,
    deployment_task_id: Optional[str] = None,
) -> Optional[dict]:
    """Update deployment status of a koink_token record."""
    pool = await get_pool()

    updates = ["status = $2"]
    args: list = [UUID(token_id), status]

    if contract_address is not None:
        args.append(contract_address)
        updates.append(f"contract_address = ${len(args)}")
    if deploy_tx_hash is not None:
        args.append(deploy_tx_hash)
        updates.append(f"deploy_tx_hash = ${len(args)}")
    if deployment_task_id is not None:
        args.append(UUID(deployment_task_id))
        updates.append(f"deployment_task_id = ${len(args)}")
    if status == "deployed":
        updates.append("deployed_at = NOW()")

    set_clause = ", ".join(updates)
    row = await pool.fetchrow(f"""
        UPDATE koink_tokens SET {set_clause}
        WHERE id = $1
        RETURNING *
    """, *args)
    return dict(row) if row else None

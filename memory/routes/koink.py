"""Koink Standard API routes (/koink/*).

All endpoints are guarded by the koink_enabled feature flag.
Phase 0: DB/API only — no contract deployment.

Routes:
    GET  /koink/status                — feature flags, chain support, DHM stats
    POST /koink/launch                — create a $KOINK Standard token (async, pending)
    GET  /koink/launches              — list all Koink token records
    GET  /koink/launches/{token_id}   — single Koink token with full KOINK params
    GET  /koink/dhm/{token_id}        — DHM positions for a token
    POST /koink/dhm/snapshot          — recalculate DHM multipliers (admin)
    GET  /koink/treasury/{token_id}   — treasury balance + recent events
    POST /koink/treasury/event        — record a treasury distribution event
    GET  /koink/standard              — machine-readable $KOINK Standard spec
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..koink import (
    KOINK_STANDARD_SPEC,
    SUPPORTED_CHAINS,
    create_koink_token,
    get_koink_token,
    list_koink_tokens,
    get_dhm_positions,
    snapshot_dhm_positions,
    get_treasury_events,
    get_treasury_balance,
    record_treasury_event,
)

log = logging.getLogger("otto.routes.koink")

router = APIRouter(prefix="/koink", tags=["koink"])


def _require_enabled():
    """Raise 503 if koink_enabled is False."""
    if not settings.koink_enabled:
        raise HTTPException(
            status_code=503,
            detail="Koink integration is disabled. Set KOINK_ENABLED=true to enable.",
        )


# ─── Request / Response Models ────────────────────────────────────────────────

class KoinkLaunchRequest(BaseModel):
    # Core identity
    name: str
    symbol: str
    chain: str = "base"
    total_supply: float = 1_000_000_000
    description: Optional[str] = None

    # $KOINK Standard params
    anti_whale_cap_pct: float = 2.0
    sell_tax_initial_bps: int = 500
    sell_tax_floor_bps: int = 100
    treasury_pct: float = 20.0
    dhm_enabled: bool = True
    dhm_max_multiplier: float = 3.0
    dhm_months: int = 12
    vrf_type: Optional[str] = None    # auto-selected if None

    # Creator config
    creator_fee_pct: float = 2.0
    liquidity_pct: float = 60.0


class TreasuryEventRequest(BaseModel):
    token_id: str
    event_type: Literal["distribution", "allocation", "withdrawal"]
    amount: float
    recipient: Optional[str] = None
    tx_hash: Optional[str] = None
    metadata: Optional[dict] = None


class DHMSnapshotRequest(BaseModel):
    token_id: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_koink_status():
    """Koink feature flags, chain support, and Phase 0 status overview."""
    return {
        "enabled": settings.koink_enabled,
        "phase": "0",
        "phase_description": "API foundation — DB records, validation, DHM tracking. No contract deployment yet.",
        "supported_chains": SUPPORTED_CHAINS,
        "vrf_providers": {
            "evm": "Chainlink VRF v2.5",
            "solana": "Switchboard VRF",
        },
        "phase_1_blocker": "OWS deploy wallet registration required (Mev action)",
        "features": {
            "create_token_record": True,
            "dhm_tracking": True,
            "treasury_events": True,
            "contract_deployment": False,    # Phase 1
            "vrf_integration": False,        # Phase 1
            "ows_signing": False,            # Phase 1
        },
    }


@router.get("/standard")
async def get_koink_standard():
    """Machine-readable $KOINK Standard specification."""
    return KOINK_STANDARD_SPEC


@router.post("/launch")
async def launch_koink_token(req: KoinkLaunchRequest):
    """Create a new $KOINK Standard token record.

    Phase 0: Validates parameters and creates DB records immediately.
    Returns a pending record. Actual contract deployment will be wired in Phase 1.
    """
    _require_enabled()
    try:
        result = await create_koink_token(
            name=req.name,
            symbol=req.symbol,
            chain=req.chain,
            total_supply=req.total_supply,
            description=req.description,
            anti_whale_cap_pct=req.anti_whale_cap_pct,
            sell_tax_initial_bps=req.sell_tax_initial_bps,
            sell_tax_floor_bps=req.sell_tax_floor_bps,
            treasury_pct=req.treasury_pct,
            dhm_enabled=req.dhm_enabled,
            dhm_max_multiplier=req.dhm_max_multiplier,
            dhm_months=req.dhm_months,
            vrf_type=req.vrf_type,
            creator_fee_pct=req.creator_fee_pct,
            liquidity_pct=req.liquidity_pct,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/launches")
async def list_koink_launches(
    chain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List all Koink token records with optional chain/status filters."""
    _require_enabled()
    return await list_koink_tokens(chain=chain, status=status, limit=limit)


@router.get("/launches/{token_id}")
async def get_koink_launch(token_id: str):
    """Fetch a single Koink token with full KOINK Standard params."""
    _require_enabled()
    token = await get_koink_token(token_id)
    if not token:
        raise HTTPException(status_code=404, detail=f"Koink token not found: {token_id}")
    return token


@router.get("/dhm/{token_id}")
async def get_dhm_positions_route(
    token_id: str,
    limit: int = Query(100, ge=1, le=500),
):
    """DHM positions for a token — holder rankings and current multipliers."""
    _require_enabled()
    # Verify token exists
    token = await get_koink_token(token_id)
    if not token:
        raise HTTPException(status_code=404, detail=f"Koink token not found: {token_id}")
    positions = await get_dhm_positions(token_id=token_id, limit=limit)
    return {
        "token_id": token_id,
        "token_name": token.get("name"),
        "token_symbol": token.get("symbol"),
        "dhm_months": token.get("dhm_months"),
        "dhm_max_multiplier": float(token.get("dhm_max_multiplier", 3.0)),
        "position_count": len(positions),
        "positions": positions,
        "note": "Phase 0: positions are synthetic (calculated from hold times). Phase 1: synced from DiamondHandsVault.sol.",
    }


@router.post("/dhm/snapshot")
async def snapshot_dhm(req: DHMSnapshotRequest):
    """Recalculate all DHM multipliers for a token based on current hold durations.

    Use this to refresh synthetic DHM state after the dhm_months or dhm_max_multiplier
    parameters are updated, or on a scheduled basis.
    """
    _require_enabled()
    token = await get_koink_token(req.token_id)
    if not token:
        raise HTTPException(status_code=404, detail=f"Koink token not found: {req.token_id}")
    try:
        result = await snapshot_dhm_positions(req.token_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/treasury/{token_id}")
async def get_treasury(
    token_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    """Treasury balance and recent events for a Koink token."""
    _require_enabled()
    try:
        balance = await get_treasury_balance(token_id)
        events = await get_treasury_events(token_id=token_id, limit=limit)
        return {**balance, "recent_events": events}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/treasury/event")
async def record_treasury_event_route(req: TreasuryEventRequest):
    """Record a treasury event (distribution, allocation, or withdrawal).

    Phase 0: Manual entry. Phase 1: Auto-synced from KoinkTreasury.sol on-chain events.
    """
    _require_enabled()
    try:
        event = await record_treasury_event(
            token_id=req.token_id,
            event_type=req.event_type,
            amount=req.amount,
            recipient=req.recipient,
            tx_hash=req.tx_hash,
            metadata=req.metadata,
        )
        return event
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

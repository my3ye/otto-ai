"""
Trading route — Hyperliquid integration.

Provides read-only visibility into Otto's trading wallets via the
Hyperliquid info API (no auth required for reads).

Endpoints:
  GET /trading/wallets       — wallet addresses + account summaries
  GET /trading/positions     — open perp positions for trading wallet
  GET /trading/orders        — open orders for trading wallet
  GET /trading/fills         — recent fills (last 50)
  GET /trading/markets       — top markets by OI
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trading", tags=["trading"])

HL_INFO_URL = "https://api.hyperliquid.xyz/info"

# Wallet addresses from settings (loaded from ~/memory/.env)
OTTO_WALLET = settings.otto_wallet_address
TRADING_WALLET = settings.otto_trading_wallet_address


async def _hl_post(payload: dict) -> Any:
    """POST to Hyperliquid info API."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(HL_INFO_URL, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error("Hyperliquid API error: %s", e)
            raise HTTPException(status_code=502, detail=f"Hyperliquid error: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error("Hyperliquid request error: %s", e)
            raise HTTPException(status_code=503, detail="Hyperliquid unreachable")


@router.get("/wallets")
async def get_wallets():
    """Return wallet addresses and account summaries."""
    wallets = {}

    for label, address in [("otto", OTTO_WALLET), ("trading", TRADING_WALLET)]:
        if not address:
            wallets[label] = {"address": None, "configured": False}
            continue

        state = await _hl_post({"type": "clearinghouseState", "user": address})
        summary = state.get("marginSummary", {})
        wallets[label] = {
            "address": address,
            "configured": True,
            "account_value": summary.get("accountValue", "0"),
            "total_notional": summary.get("totalNtlPos", "0"),
            "margin_used": summary.get("totalMarginUsed", "0"),
            "withdrawable": state.get("withdrawable", "0"),
            "position_count": len(state.get("assetPositions", [])),
        }

    return {"wallets": wallets}


@router.get("/positions")
async def get_positions():
    """Return open perp positions for the trading wallet."""
    if not TRADING_WALLET:
        return {"positions": [], "error": "Trading wallet not configured"}

    state = await _hl_post({"type": "clearinghouseState", "user": TRADING_WALLET})
    raw_positions = state.get("assetPositions", [])

    positions = []
    for item in raw_positions:
        pos = item.get("position", {})
        if float(pos.get("szi", 0)) == 0:
            continue  # skip zero-size positions
        positions.append({
            "coin": pos.get("coin"),
            "size": pos.get("szi"),
            "entry_price": pos.get("entryPx"),
            "pnl_unrealized": pos.get("unrealizedPnl"),
            "leverage": pos.get("leverage", {}).get("value"),
            "liquidation_price": pos.get("liquidationPx"),
            "margin_used": pos.get("marginUsed"),
            "side": "long" if float(pos.get("szi", 0)) > 0 else "short",
        })

    return {
        "wallet": TRADING_WALLET,
        "positions": positions,
        "account_value": state.get("marginSummary", {}).get("accountValue", "0"),
        "withdrawable": state.get("withdrawable", "0"),
    }


@router.get("/orders")
async def get_orders():
    """Return open orders for the trading wallet."""
    if not TRADING_WALLET:
        return {"orders": [], "error": "Trading wallet not configured"}

    raw = await _hl_post({"type": "openOrders", "user": TRADING_WALLET})

    orders = []
    for o in raw:
        orders.append({
            "oid": o.get("oid"),
            "coin": o.get("coin"),
            "side": "buy" if o.get("side") == "B" else "sell",
            "size": o.get("sz"),
            "price": o.get("limitPx"),
            "filled": o.get("origSz"),
            "order_type": o.get("orderType"),
            "timestamp": o.get("timestamp"),
        })

    return {"wallet": TRADING_WALLET, "orders": orders}


@router.get("/fills")
async def get_fills(limit: int = 50):
    """Return recent fills for the trading wallet."""
    if not TRADING_WALLET:
        return {"fills": [], "error": "Trading wallet not configured"}

    raw = await _hl_post({"type": "userFills", "user": TRADING_WALLET})

    fills = []
    for f in (raw or [])[-limit:]:
        fills.append({
            "coin": f.get("coin"),
            "side": "buy" if f.get("side") == "B" else "sell",
            "size": f.get("sz"),
            "price": f.get("px"),
            "fee": f.get("fee"),
            "timestamp": f.get("time"),
            "closed_pnl": f.get("closedPnl"),
        })

    return {"wallet": TRADING_WALLET, "fills": list(reversed(fills))}


@router.get("/markets")
async def get_markets(limit: int = 20):
    """Return top perp markets by open interest."""
    data = await _hl_post({"type": "metaAndAssetCtxs"})
    universe = data[0].get("universe", [])
    ctxs = data[1] if len(data) > 1 else []

    markets = []
    for i, asset in enumerate(universe):
        ctx = ctxs[i] if i < len(ctxs) else {}
        markets.append({
            "name": asset.get("name"),
            "max_leverage": asset.get("maxLeverage"),
            "open_interest": ctx.get("openInterest"),
            "mark_price": ctx.get("markPx"),
            "funding": ctx.get("funding"),
            "volume_24h": ctx.get("dayNtlVlm"),
        })

    # Sort by 24h volume descending
    markets.sort(key=lambda m: float(m.get("volume_24h") or 0), reverse=True)
    return {"markets": markets[:limit]}

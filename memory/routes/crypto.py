"""Native Crypto Engine API routes (/crypto/*).

Provides the full Bankr-equivalent feature set built natively:
- GET  /crypto/status          — engine health, wallet info, feature flags
- POST /crypto/parse           — NL → TradeIntent (dry-run, no execution)
- POST /crypto/execute         — parse + execute trade (requires CRYPTO_EXECUTION_ENABLED)
- GET  /crypto/portfolio       — multi-chain balances + equity
- GET  /crypto/price           — current token prices
- GET  /crypto/history         — trade history
- POST /crypto/monitor         — create conditional order (limit/SL/DCA)
- GET  /crypto/monitors        — list active price monitors
- DELETE /crypto/monitors/{id} — cancel a price monitor
- POST /crypto/signals         — publish a signal
- GET  /crypto/signals         — list signals + stats
- PATCH /crypto/signals/{id}/close — close signal with outcome
- POST /crypto/launch          — launch a token (Phase 3)
- GET  /crypto/launches        — list token launches
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..crypto.nlparser import parse as nl_parse
from ..crypto.price_feed import get_price, get_prices
from ..crypto.portfolio import get_portfolio_summary
from ..crypto.monitors import create_monitor, list_monitors, cancel_monitor
from ..crypto.signals import publish_signal, list_signals, close_signal, get_signal_stats
from ..crypto.launch import launch_on_base, launch_on_solana, list_launches
from ..crypto.executor import get_quote

log = logging.getLogger("otto.routes.crypto")

router = APIRouter(prefix="/crypto", tags=["crypto"])


# ─── Request/Response Models ────────────────────────────────────────────────

class ParseRequest(BaseModel):
    text: str


class ExecuteRequest(BaseModel):
    text: str
    dry_run: bool = True
    chain: Optional[str] = None


class MonitorRequest(BaseModel):
    monitor_type: str                    # limit_buy | limit_sell | stop_loss | dca | take_profit
    chain: str = "base"
    token_in: str
    token_out: Optional[str] = None
    amount_usd: Optional[float] = None
    trigger_price: Optional[float] = None
    trigger_type: Optional[str] = None   # above | below
    trigger_pct: Optional[float] = None
    dca_interval_hours: Optional[int] = None
    dca_max_runs: Optional[int] = None
    nl_description: Optional[str] = None


class SignalRequest(BaseModel):
    token: str
    chain: str = "base"
    direction: str                       # long | short | neutral | exit
    confidence: Optional[float] = None
    rationale: Optional[str] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    tx_hash: Optional[str] = None
    trade_id: Optional[str] = None
    metadata: Optional[dict] = None


class CloseSignalRequest(BaseModel):
    win: bool
    exit_price: float
    pnl_pct: float


class LaunchRequest(BaseModel):
    name: str
    symbol: str
    chain: str                           # base | solana
    supply: Optional[float] = None
    creator_fee_pct: Optional[float] = None
    description: Optional[str] = None


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/status")
async def get_status():
    """Engine health, feature flags, wallet addresses."""
    wallet = settings.otto_wallet_address
    return {
        "engine": "native_crypto",
        "enabled": settings.crypto_enabled,
        "execution_enabled": settings.crypto_execution_enabled,
        "wallet_address": wallet or None,
        "trading_wallet": settings.otto_trading_wallet_address or None,
        "features": {
            "price_feed": True,                          # CoinGecko (no key needed)
            "portfolio": bool(settings.alchemy_api_key), # Alchemy required
            "nl_parse": True,                            # LLM-powered, always available
            "execute": settings.crypto_execution_enabled,
            "monitors": settings.crypto_enabled,
            "signals": True,                             # DB-only, always available
            "launch": False,                             # Phase 3
        },
        "external_apis": {
            "alchemy": bool(settings.alchemy_api_key),
            "zerox": bool(settings.zerox_api_key),
            "coingecko": True,                           # free tier, no key needed
            "birdeye": bool(settings.birdeye_api_key),
            "cdp_agentkit": bool(settings.cdp_api_key_name if hasattr(settings, 'cdp_api_key_name') else False),
        },
        "note": "Phase 1 — price, portfolio, NL parse, and signals active. Execution wired in Phase 2.",
    }


@router.post("/parse")
async def parse_intent(req: ParseRequest):
    """Parse a natural language trading command into a structured TradeIntent.

    This endpoint is always safe — no execution occurs regardless of intent.
    Use it to preview what Otto would do before executing.
    """
    intent = await nl_parse(req.text)
    valid, reason = intent.is_valid_for_execution()
    return {
        "intent": intent.to_dict(),
        "valid_for_execution": valid,
        "validation_message": reason if not valid else "Ready to execute",
    }


@router.post("/execute")
async def execute_trade(req: ExecuteRequest):
    """Parse NL command and execute trade (or dry-run).

    Requires CRYPTO_EXECUTION_ENABLED=true for actual execution.
    dry_run=true (default) returns the quote without broadcasting.
    """
    if not settings.crypto_enabled:
        raise HTTPException(status_code=503, detail="Crypto engine disabled. Set CRYPTO_ENABLED=true to activate.")

    # Override chain if provided
    intent = await nl_parse(req.text)
    if req.chain:
        intent.chain = req.chain

    valid, reason = intent.is_valid_for_execution()
    if not valid:
        raise HTTPException(status_code=400, detail=f"Intent not executable: {reason}")

    if intent.is_query:
        raise HTTPException(status_code=400, detail="This is an information query, not a trade. Use /crypto/parse.")

    # Get quote (Phase 1: returns None for actual swaps)
    quote = await get_quote(intent)
    if not quote and not req.dry_run:
        raise HTTPException(status_code=501, detail="Trade execution not yet implemented (Phase 2)")

    return {
        "intent": intent.to_dict(),
        "quote": None,  # Phase 2 will populate
        "status": "dry_run" if req.dry_run else "phase2_pending",
        "message": "Phase 1: parse + quote complete. Actual execution wired in Phase 2.",
    }


@router.get("/portfolio")
async def get_portfolio(chains: str = Query(default="base,eth")):
    """Get multi-chain portfolio balances and equity.

    Args:
        chains: Comma-separated chain list. E.g. "base,eth" or "all"
    """
    chain_list = [c.strip() for c in chains.split(",") if c.strip()]
    if "all" in chain_list:
        chain_list = ["base", "eth", "polygon"]

    summary = await get_portfolio_summary(chain_list if chain_list else None)

    # Serialize dataclasses to dicts
    def _chain_to_dict(cp) -> dict:
        return {
            "chain": cp.chain,
            "wallet_address": cp.wallet_address,
            "native_balance": {
                "symbol": cp.native_balance.symbol,
                "amount": cp.native_balance.amount,
                "price_usd": cp.native_balance.price_usd,
                "value_usd": cp.native_balance.value_usd,
            },
            "token_balances": [
                {"symbol": t.symbol, "amount": t.amount, "value_usd": t.value_usd,
                 "contract_address": t.contract_address}
                for t in cp.token_balances
            ],
            "total_value_usd": cp.total_value_usd,
            "error": cp.error,
        }

    return {
        "chains": [_chain_to_dict(cp) for cp in summary.chains],
        "total_value_usd": summary.total_value_usd,
        "hyperliquid_equity": summary.hyperliquid_equity,
        "error": summary.error,
    }


@router.get("/price")
async def get_token_price(tokens: str = Query(description="Comma-separated token symbols, e.g. ETH,BTC,SOL"),
                          chain: Optional[str] = Query(default=None)):
    """Get current USD price for one or more tokens.

    Args:
        tokens: Comma-separated symbols (e.g. "ETH,BTC,SOL")
        chain: Optional chain hint (affects Birdeye routing for Solana tokens)
    """
    symbols = [s.strip().upper() for s in tokens.split(",") if s.strip()]
    if not symbols:
        raise HTTPException(status_code=400, detail="No tokens specified")

    if len(symbols) == 1:
        price = await get_price(symbols[0], chain)
        if not price:
            raise HTTPException(status_code=404, detail=f"Price not found for {symbols[0]}")
        return {
            "symbol": price.symbol,
            "price_usd": price.price_usd,
            "change_24h": price.change_24h,
            "market_cap": price.market_cap,
            "volume_24h": price.volume_24h,
            "source": price.source,
        }
    else:
        prices = await get_prices(symbols)
        return {
            sym: {
                "price_usd": p.price_usd,
                "change_24h": p.change_24h,
                "source": p.source,
            }
            for sym, p in prices.items()
        }


@router.get("/history")
async def get_trade_history(limit: int = 50, chain: Optional[str] = None, status: Optional[str] = None):
    """Get trade history from crypto_trades table."""
    from ..db import get_pool
    pool = await get_pool()

    conditions = []
    params = []
    param_idx = 1

    if chain:
        conditions.append(f"chain = ${param_idx}")
        params.append(chain)
        param_idx += 1

    if status:
        conditions.append(f"status = ${param_idx}")
        params.append(status)
        param_idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    rows = await pool.fetch(f"""
        SELECT * FROM crypto_trades
        {where}
        ORDER BY created_at DESC
        LIMIT ${param_idx}
    """, *params)

    return {"trades": [dict(r) for r in rows], "count": len(rows)}


# ─── Price Monitors ──────────────────────────────────────────────────────────

@router.post("/monitor")
async def create_price_monitor(req: MonitorRequest):
    """Create a conditional order (limit buy/sell, stop-loss, DCA)."""
    if not settings.crypto_enabled:
        raise HTTPException(status_code=503, detail="Crypto engine disabled")

    monitor = await create_monitor(
        monitor_type=req.monitor_type,
        chain=req.chain,
        token_in=req.token_in,
        token_out=req.token_out,
        amount_usd=req.amount_usd,
        trigger_price=req.trigger_price,
        trigger_type=req.trigger_type,
        trigger_pct=req.trigger_pct,
        dca_interval_hours=req.dca_interval_hours,
        dca_max_runs=req.dca_max_runs,
        nl_description=req.nl_description,
    )
    return monitor


@router.get("/monitors")
async def get_price_monitors(status: str = "active", limit: int = 50):
    """List price monitors (conditional orders)."""
    monitors = await list_monitors(status=status, limit=limit)
    return {"monitors": monitors, "count": len(monitors)}


@router.delete("/monitors/{monitor_id}")
async def delete_price_monitor(monitor_id: str):
    """Cancel a price monitor."""
    cancelled = await cancel_monitor(monitor_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Monitor not found or already inactive")
    return {"status": "cancelled", "id": monitor_id}


# ─── Signal Board ─────────────────────────────────────────────────────────────

@router.post("/signals")
async def create_signal(req: SignalRequest):
    """Publish a new signal to the native signal board."""
    signal = await publish_signal(
        token=req.token,
        chain=req.chain,
        direction=req.direction,
        confidence=req.confidence,
        rationale=req.rationale,
        entry_price=req.entry_price,
        target_price=req.target_price,
        stop_price=req.stop_price,
        tx_hash=req.tx_hash,
        trade_id=req.trade_id,
        metadata=req.metadata,
    )
    return signal


@router.get("/signals")
async def get_signals(status: Optional[str] = None, limit: int = 50):
    """List signals and performance stats."""
    signals = await list_signals(status=status, limit=limit)
    stats = await get_signal_stats()
    return {"signals": signals, "stats": stats, "count": len(signals)}


@router.patch("/signals/{signal_id}/close")
async def close_signal_endpoint(signal_id: str, req: CloseSignalRequest):
    """Close an open signal with outcome."""
    signal = await close_signal(signal_id, req.win, req.exit_price, req.pnl_pct)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found or already closed")
    return signal


# ─── Token Launch ─────────────────────────────────────────────────────────────

@router.post("/launch")
async def launch_token(req: LaunchRequest):
    """Launch a new token (Phase 3 — records intent, execution wired later)."""
    params = req.dict()
    if req.chain == "base":
        result = await launch_on_base(params)
    elif req.chain == "solana":
        result = await launch_on_solana(params)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported launch chain: {req.chain}")
    return result


@router.get("/launches")
async def get_launches(limit: int = 50):
    """List token launches."""
    launches = await list_launches(limit=limit)
    return {"launches": launches, "count": len(launches)}

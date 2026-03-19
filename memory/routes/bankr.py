"""
BANKR Bot integration routes.

Endpoints:
  GET  /bankr/status           — API key health, wallet, balances summary
  POST /bankr/trade            — NL trade execution → BANKR Agent API
  GET  /bankr/portfolio        — Cross-chain balances
  GET  /bankr/history          — Local trade log + PnL
  POST /bankr/limit-order      — Structured limit order → NL → BANKR
  POST /bankr/dca              — DCA strategy → NL → BANKR
  POST /bankr/stop-loss        — Stop-loss → NL → BANKR
  POST /bankr/signal/publish   — Publish signal to bankrsignals.com
  GET  /bankr/signals          — Otto's signal history + win rate
  POST /bankr/launch           — Token launch (Doppler/Raydium)
  GET  /bankr/jobs/{id}        — Poll BANKR job status

All execution endpoints gate on BANKR_ENABLED. Status, history, and signals
endpoints work even when disabled (show config state + local DB records).
"""

import json
import logging
import uuid
from typing import Literal, Optional, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..db import get_pool
from ..bankr.client import (
    BankrClient,
    BankrDisabledError,
    BankrError,
    compose_trade_prompt,
    compose_limit_prompt,
    compose_dca_prompt,
    compose_stop_loss_prompt,
    compose_launch_prompt,
)
from ..bankr.signals import BankrSignals

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bankr", tags=["bankr"])


# ── Helper: disabled response ──────────────────────────────────────────────────

def _disabled_response(extra: dict | None = None) -> dict:
    base = {
        "enabled": False,
        "message": "BANKR integration is disabled. Set BANKR_ENABLED=true and BANKR_API_KEY in ~/memory/.env.",
        "setup": "Obtain a bk_... key from bankr.bot → Dashboard → API Keys, then run: bankr login email <email>",
    }
    if extra:
        base.update(extra)
    return base


# ── Pydantic models ────────────────────────────────────────────────────────────

class TradeRequest(BaseModel):
    prompt: str
    thread_id: Optional[str] = None


class LimitOrderRequest(BaseModel):
    action: Literal["buy", "sell"]
    token: str
    amount: str
    amount_unit: str = "USD"
    trigger_type: Literal["price", "pct_change"] = "price"
    trigger_value: str
    chain: Optional[str] = None
    thread_id: Optional[str] = None


class DCARequest(BaseModel):
    token: str
    amount: str
    amount_unit: str = "USD"
    frequency: Literal["daily", "weekly", "monthly"] = "weekly"
    duration: Optional[str] = None
    chain: Optional[str] = None
    thread_id: Optional[str] = None


class StopLossRequest(BaseModel):
    token: str                     # required — no default to avoid accidental all-holdings stop-loss
    trigger_pct: str               # e.g. "-20%"
    chain: Optional[str] = None
    all_holdings: bool = False
    thread_id: Optional[str] = None


class SignalPublishRequest(BaseModel):
    token: str
    direction: Literal["long", "short", "neutral"]
    chain: Optional[str] = None
    confidence: float = 0.7
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    signal_type: Literal["whale_convergence", "limit_trigger", "manual"] = "whale_convergence"
    metadata: Optional[dict] = None


class LaunchRequest(BaseModel):
    token_name: str
    token_symbol: str
    supply: str                    # e.g. "1000000000"
    platform: Literal["doppler", "raydium"] = "doppler"
    description: Optional[str] = None
    chain: Optional[str] = None
    thread_id: Optional[str] = None


# ── Helper: persist trade to DB ────────────────────────────────────────────────

async def _save_trade(pool, prompt: str, job_result: dict, chain: Optional[str] = None) -> str:
    """Save a trade execution to bankr_trades. Returns trade ID."""
    trade_id = str(uuid.uuid4())
    status = job_result.get("status", "pending")
    job_id = job_result.get("job_id")
    raw_result = job_result.get("result")
    error = job_result.get("error")

    # Try to extract tx_hash from result
    tx_hash = None
    if raw_result and isinstance(raw_result, dict):
        tx_hash = (
            raw_result.get("txHash")
            or raw_result.get("tx_hash")
            or raw_result.get("transactionHash")
        )

    await pool.execute(
        """
        INSERT INTO bankr_trades (id, job_id, prompt, chain, tx_hash, status, raw_result, error)
        VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
        """,
        trade_id,
        job_id,
        prompt,
        chain,
        tx_hash,
        status,
        json.dumps(raw_result) if raw_result else None,
        error,
    )
    return trade_id


async def _save_job(pool, job_id: str, job_type: str, prompt: str, trade_id: Optional[str] = None) -> None:
    """Save a pending BANKR job for async tracking."""
    await pool.execute(
        """
        INSERT INTO bankr_jobs (job_id, job_type, prompt, status, trade_id)
        VALUES ($1, $2, $3, 'pending', $4)
        ON CONFLICT (job_id) DO NOTHING
        """,
        job_id,
        job_type,
        prompt,
        trade_id,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/status")
async def bankr_status():
    """
    BANKR integration status.
    Shows API key health, config flags, wallet balances if enabled.
    """
    base_status = {
        "enabled": settings.bankr_enabled,
        "api_key_configured": bool(settings.bankr_api_key),
        "signals_enabled": settings.bankr_signals_enabled,
        "llm_gateway_enabled": settings.bankr_llm_gateway_enabled,
        "api_url": settings.bankr_api_url,
    }

    if not settings.bankr_enabled or not settings.bankr_api_key:
        return {**base_status, **_disabled_response()}

    try:
        client = BankrClient.from_settings()
        account = await client.get_status()
        return {**base_status, "account": account, "healthy": True}
    except BankrError as e:
        return {**base_status, "healthy": False, "error": str(e)}


@router.post("/trade")
async def execute_trade(req: TradeRequest):
    """
    Execute a NL trade via BANKR Agent API.

    Polls up to 30s inline. If timed out, returns job_id for async tracking.
    Pass raw NL prompt (e.g. "Buy $100 of ETH on Base") or use /limit-order,
    /dca, /stop-loss for structured inputs.
    """
    if not settings.bankr_enabled:
        return _disabled_response({"prompt": req.prompt})

    client = BankrClient.from_settings()
    pool = await get_pool()

    try:
        result = await client.execute(req.prompt, req.thread_id)
        trade_id = await _save_trade(pool, req.prompt, result)

        if result["timed_out"]:
            # Save job for async polling
            if result.get("job_id"):
                await _save_job(pool, result["job_id"], "trade", req.prompt, trade_id)

        return {
            "trade_id": trade_id,
            "job_id": result.get("job_id"),
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
            "timed_out": result.get("timed_out", False),
            "elapsed_s": round(result.get("elapsed", 0), 1),
        }
    except BankrDisabledError as e:
        return _disabled_response({"error": str(e)})
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/portfolio")
async def get_portfolio():
    """
    Fetch cross-chain wallet balances from BANKR.
    Returns all balances across chains (Base, Solana, ETH, etc.).
    """
    if not settings.bankr_enabled:
        return _disabled_response()

    client = BankrClient.from_settings()
    try:
        data = await client.get_portfolio()
        return {"portfolio": data}
    except BankrDisabledError as e:
        return _disabled_response({"error": str(e)})
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/history")
async def get_trade_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    chain: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """
    Local trade log from bankr_trades table.
    Includes all trades with status and tx hashes.
    """
    pool = await get_pool()

    conditions = ["1=1"]
    params: list[Any] = []
    idx = 1

    if chain:
        conditions.append(f"chain = ${idx}")
        params.append(chain)
        idx += 1
    if status:
        conditions.append(f"status = ${idx}")
        params.append(status)
        idx += 1

    where = " AND ".join(conditions)
    rows = await pool.fetch(
        f"SELECT * FROM bankr_trades WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}",
        *params, limit, offset,
    )
    total = await pool.fetchval(f"SELECT COUNT(*) FROM bankr_trades WHERE {where}", *params)

    trades = [dict(r) for r in rows]
    # Compute basic PnL stats
    completed = [t for t in trades if t["status"] == "completed"]

    return {
        "trades": trades,
        "total": total,
        "limit": limit,
        "offset": offset,
        "stats": {
            "total": total,
            "completed": len(completed),
            "pending": len([t for t in trades if t["status"] == "pending"]),
            "failed": len([t for t in trades if t["status"] == "failed"]),
        },
    }


@router.post("/limit-order")
async def place_limit_order(req: LimitOrderRequest):
    """
    Structured limit order — converts to BANKR NL prompt and executes.
    """
    if not settings.bankr_enabled:
        return _disabled_response({"request": req.model_dump()})

    prompt = compose_limit_prompt(
        action=req.action,
        token=req.token,
        amount=req.amount,
        amount_unit=req.amount_unit,
        trigger_type=req.trigger_type,
        trigger_value=req.trigger_value,
        chain=req.chain,
    )
    logger.debug("Limit order prompt: %s", prompt)

    client = BankrClient.from_settings()
    pool = await get_pool()

    try:
        result = await client.execute(prompt, req.thread_id)
        trade_id = await _save_trade(pool, prompt, result, req.chain)

        if result["timed_out"] and result.get("job_id"):
            await _save_job(pool, result["job_id"], "limit", prompt, trade_id)

        return {
            "trade_id": trade_id,
            "prompt": prompt,
            "job_id": result.get("job_id"),
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
            "timed_out": result.get("timed_out", False),
        }
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/dca")
async def setup_dca(req: DCARequest):
    """
    DCA strategy — converts to BANKR NL and submits.
    DCA jobs typically take longer; returns job_id for async tracking if timed out.
    """
    if not settings.bankr_enabled:
        return _disabled_response({"request": req.model_dump()})

    prompt = compose_dca_prompt(
        token=req.token,
        amount=req.amount,
        amount_unit=req.amount_unit,
        frequency=req.frequency,
        duration=req.duration,
        chain=req.chain,
    )
    logger.debug("DCA prompt: %s", prompt)

    client = BankrClient.from_settings()
    pool = await get_pool()

    try:
        result = await client.execute(prompt, req.thread_id)
        trade_id = await _save_trade(pool, prompt, result, req.chain)

        if result["timed_out"] and result.get("job_id"):
            await _save_job(pool, result["job_id"], "dca", prompt, trade_id)

        return {
            "trade_id": trade_id,
            "prompt": prompt,
            "job_id": result.get("job_id"),
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
            "timed_out": result.get("timed_out", False),
            "note": "DCA strategies may take longer — track via /bankr/jobs/{job_id}" if result["timed_out"] else None,
        }
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/stop-loss")
async def set_stop_loss(req: StopLossRequest):
    """
    Set a stop-loss via BANKR NL.
    """
    if not settings.bankr_enabled:
        return _disabled_response({"request": req.model_dump()})

    prompt = compose_stop_loss_prompt(
        token=req.token,
        trigger_pct=req.trigger_pct,
        chain=req.chain,
        all_holdings=req.all_holdings,
    )
    logger.debug("Stop-loss prompt: %s", prompt)

    client = BankrClient.from_settings()
    pool = await get_pool()

    try:
        result = await client.execute(prompt, req.thread_id)
        trade_id = await _save_trade(pool, prompt, result, req.chain)

        if result["timed_out"] and result.get("job_id"):
            await _save_job(pool, result["job_id"], "stop_loss", prompt, trade_id)

        return {
            "trade_id": trade_id,
            "prompt": prompt,
            "job_id": result.get("job_id"),
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
        }
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/signal/publish")
async def publish_signal(req: SignalPublishRequest):
    """
    Publish an alpha signal to bankrsignals.com with TX proof.
    Also saves to bankr_signals table for local tracking.
    """
    pool = await get_pool()
    signal_id = str(uuid.uuid4())

    # Save locally first
    await pool.execute(
        """
        INSERT INTO bankr_signals (
            id, signal_type, token, chain, direction, confidence,
            entry_price, target_price, stop_price, metadata
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
        """,
        signal_id,
        req.signal_type,
        req.token,
        req.chain,
        req.direction,
        req.confidence,
        req.entry_price,
        req.target_price,
        req.stop_price,
        json.dumps(req.metadata) if req.metadata else None,
    )

    # Publish to bankrsignals.com if enabled
    pub_result = {"published": False, "reason": "signals disabled"}
    if settings.bankr_signals_enabled:
        sig_client = BankrSignals.from_settings()
        pub_result = await sig_client.publish(
            token=req.token,
            direction=req.direction,
            chain=req.chain,
            confidence=req.confidence,
            entry_price=req.entry_price,
            target_price=req.target_price,
            stop_price=req.stop_price,
            signal_type=req.signal_type,
            metadata=req.metadata,
        )

        if pub_result.get("published"):
            # Update with external IDs
            await pool.execute(
                "UPDATE bankr_signals SET published=TRUE, bankr_signal_id=$1, tx_hash=$2 WHERE id=$3",
                pub_result.get("signal_id"),
                pub_result.get("tx_hash"),
                signal_id,
            )

    return {
        "signal_id": signal_id,
        "token": req.token,
        "direction": req.direction,
        "confidence": req.confidence,
        "published": pub_result.get("published", False),
        "bankr_signal_id": pub_result.get("signal_id"),
        "tx_hash": pub_result.get("tx_hash"),
        "reason": pub_result.get("reason"),
    }


@router.get("/signals")
async def get_signals(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    published_only: bool = Query(False),
):
    """
    Otto's signal history with win rate from local DB.
    """
    pool = await get_pool()

    conditions = ["1=1"]
    params: list[Any] = []
    if published_only:
        conditions.append("published = TRUE")

    where = " AND ".join(conditions)
    idx = 1
    rows = await pool.fetch(
        f"SELECT * FROM bankr_signals WHERE {where} ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}",
        *params, limit, offset,
    )

    # Single query for all stats (avoids 3 round-trips)
    stats_row = await pool.fetchrow(
        """
        SELECT
            COUNT(*) as total_signals,
            COUNT(*) FILTER (WHERE published = TRUE) as published,
            COUNT(*) FILTER (WHERE win IS NOT NULL) as closed,
            COUNT(*) FILTER (WHERE win = TRUE) as wins,
            COUNT(*) FILTER (WHERE win = FALSE) as losses,
            COUNT(*) FILTER (WHERE win IS NULL AND closed_at IS NULL) as open,
            AVG(pnl_pct) FILTER (WHERE pnl_pct IS NOT NULL) as avg_pnl
        FROM bankr_signals
        """
    )

    closed = stats_row["closed"] or 0
    wins = stats_row["wins"] or 0
    win_rate = round(wins / closed, 3) if closed > 0 else None

    return {
        "signals": [dict(r) for r in rows],
        "stats": {
            "total_signals": stats_row["total_signals"],
            "published": stats_row["published"],
            "open": stats_row["open"],
            "closed": closed,
            "wins": wins,
            "losses": stats_row["losses"],
            "win_rate": win_rate,
            "avg_pnl_pct": round(float(stats_row["avg_pnl"]), 2) if stats_row["avg_pnl"] else None,
        },
    }


@router.post("/launch")
async def launch_token(req: LaunchRequest):
    """
    Launch a token via BANKR (Doppler on Base / Raydium LaunchLab on Solana).
    These jobs are slow — returns job_id if timed out.
    """
    if not settings.bankr_enabled:
        return _disabled_response({"request": req.model_dump()})

    prompt = compose_launch_prompt(
        token_name=req.token_name,
        token_symbol=req.token_symbol,
        supply=req.supply,
        platform=req.platform,
        description=req.description,
        chain=req.chain,
    )
    logger.info("Token launch prompt: %s", prompt)

    client = BankrClient.from_settings()
    pool = await get_pool()

    try:
        result = await client.execute(prompt, req.thread_id)
        trade_id = await _save_trade(pool, prompt, result, req.chain)

        if result["timed_out"] and result.get("job_id"):
            await _save_job(pool, result["job_id"], "launch", prompt, trade_id)

        return {
            "trade_id": trade_id,
            "prompt": prompt,
            "token_name": req.token_name,
            "token_symbol": req.token_symbol,
            "platform": req.platform,
            "job_id": result.get("job_id"),
            "status": result["status"],
            "result": result.get("result"),
            "error": result.get("error"),
            "timed_out": result.get("timed_out", False),
            "note": "Token launch tracked via /bankr/jobs/{job_id}" if result.get("timed_out") else None,
        }
    except BankrError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Poll a BANKR job by ID. Checks local DB first, then live BANKR API.
    """
    pool = await get_pool()

    # Check local DB first
    row = await pool.fetchrow(
        "SELECT * FROM bankr_jobs WHERE job_id = $1",
        job_id,
    )

    local_state = dict(row) if row else None

    # If already completed/failed in DB, return that
    if local_state and local_state["status"] in ("completed", "failed", "cancelled"):
        return {"source": "db", "job": local_state}

    # If BANKR enabled, fetch live status
    if settings.bankr_enabled and settings.bankr_api_key:
        try:
            client = BankrClient.from_settings()
            live_job = await client.get_job(job_id)
            status = live_job.get("status", "").lower()

            # Update DB if we have a local record
            if local_state:
                await pool.execute(
                    "UPDATE bankr_jobs SET status=$1, result=$2::jsonb, poll_count=poll_count+1, updated_at=NOW() WHERE job_id=$3",
                    status,
                    json.dumps(live_job),
                    job_id,
                )

            return {"source": "live", "job_id": job_id, "status": status, "result": live_job}
        except BankrError as e:
            if local_state:
                return {"source": "db", "job": local_state, "live_error": str(e)}
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if local_state:
        return {"source": "db", "job": local_state}

    raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

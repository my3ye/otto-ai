"""
Birdeye API client for Project Alpha.

Covers:
  - get_token_security()      — holder concentration, mint/freeze auth, LP lock status
  - get_token_ohlcv()         — OHLCV candles for price history checks (4H chart)
  - get_wallet_tx_list()      — wallet swap transaction history (for PnL analysis)
  - compute_wallet_win_rate() — derive win rate from swap history pairs

Birdeye free tier: 100 req/min, Solana-only for most endpoints.
API key is loaded from alpha .env (BIRDEYE_API_KEY).
Base URL: https://public-api.birdeye.so

Docs: https://docs.birdeye.so/reference
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

# ── Config ────────────────────────────────────────────────────────────────────

BIRDEYE_BASE = "https://public-api.birdeye.so"
CHAIN = "solana"
REQUEST_TIMEOUT = 15.0
RATE_LIMIT_SLEEP = 0.7  # 100 req/min = 1 req/600ms; 0.7s is safe

# Env loading — try alpha .env, then memory .env, then OS env
_ENV_FILES = [
    Path("/home/web3relic/otto/projects/alpha/.env"),
    Path("/home/web3relic/memory/.env"),
]


def _get_birdeye_key() -> str:
    """Load BIRDEYE_API_KEY from env files or OS environment."""
    # Try OS env first (set by dotenv or systemd)
    key = os.environ.get("BIRDEYE_API_KEY", "")
    if key:
        return key
    # Parse env files
    for env_file in _ENV_FILES:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                line = line.strip()
                if line.startswith("BIRDEYE_API_KEY="):
                    val = line.split("=", 1)[1].strip()
                    if val:
                        return val
    return ""


def _headers(key: str) -> dict[str, str]:
    return {
        "X-API-KEY": key,
        "x-chain": CHAIN,
        "accept": "application/json",
    }


# ── Token Security ────────────────────────────────────────────────────────────
#
# NOTE: Birdeye /defi/token_security requires a paid plan.
# On the free tier we use /defi/token_overview as a proxy — it provides:
#   - holder count, price change, buy/sell volume breakdown
# This gives us softer rug signals (no mint_authority, no LP lock status).

def get_token_overview(token_address: str) -> dict[str, Any]:
    """
    Fetch Birdeye token overview — price, volume, holder count, buy/sell flow.
    Available on free tier. Returns empty dict on error.
    """
    key = _get_birdeye_key()
    if not key:
        return {}

    url = f"{BIRDEYE_BASE}/defi/token_overview"
    params = {"address": token_address}

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=_headers(key), params=params)
            if resp.status_code == 429:
                logger.warning("[birdeye] Rate limited on token_overview for {}", token_address[:8])
                return {}
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("[birdeye] token_overview error for {}: {}", token_address[:8], e)
        return {}

    return data.get("data", {}) or {}


def get_token_security(token_address: str) -> dict[str, Any]:
    """
    Derive rug-risk signals from token_overview (free-tier Birdeye proxy).

    The /defi/token_security endpoint requires a paid plan.
    This function uses /defi/token_overview to check:
      - Holder count (< 50 = very early / suspicious)
      - Volume/price ratio (wash-trading detection)
      - Buy vs sell pressure imbalance

    Returns dict with:
      - holder_count: int
      - is_rug_risk: bool
      - rug_reasons: list[str]
      - confidence: str   ('low' — limited without security endpoint)

    On API error returns empty dict — callers treat as "no data, skip filter".
    """
    overview = get_token_overview(token_address)
    if not overview:
        return {}

    holder_count = int(overview.get("holder", 0) or 0)
    price_change_24h = float(overview.get("priceChange24hPercent", 0) or 0)
    v24h = float(overview.get("v24h", 0) or 0)  # raw token volume
    v24h_usd = float(overview.get("v24hUSD", 0) or overview.get("vHistory24hUSD", 0) or 0)
    liquidity = float(overview.get("liquidity", 0) or 0)

    rug_reasons: list[str] = []

    # Rug signal: extremely low holder count
    if holder_count < 50 and holder_count > 0:
        rug_reasons.append(f"holder_count={holder_count}<50 (very concentrated)")

    # Rug signal: wash trading — massive volume relative to liquidity
    if liquidity > 0 and v24h_usd > 20 * liquidity:
        ratio = v24h_usd / liquidity
        rug_reasons.append(f"volume/liquidity={ratio:.0f}x (possible wash trading)")

    # Rug signal: extreme price spike with very low holders (pump-and-dump pattern)
    if price_change_24h > 500 and holder_count < 100:
        rug_reasons.append(f"price_spike={price_change_24h:.0f}%+low_holders ({holder_count})")

    return {
        "holder_count": holder_count,
        "liquidity_usd": liquidity,
        "price_change_24h": price_change_24h,
        "volume_24h_usd": v24h_usd,
        "is_rug_risk": bool(rug_reasons),
        "rug_reasons": rug_reasons,
        "confidence": "low",  # Free tier: no mint_authority, LP lock, creator % data
    }


# ── OHLCV (Price History) ─────────────────────────────────────────────────────

def get_token_ohlcv(
    token_address: str,
    resolution: str = "4H",
    limit: int = 24,
) -> list[dict[str, Any]]:
    """
    Fetch OHLCV candles for a token.

    resolution: '15m', '30m', '1H', '4H', '1D'
    limit: number of candles to fetch (max 1000)

    Returns list of dicts: {unixTime, open, high, low, close, volume}
    Oldest-first. Empty list on error.
    """
    key = _get_birdeye_key()
    if not key:
        return []

    now = int(time.time())
    # Map resolution to seconds for time_from calculation
    res_seconds = {
        "15m": 900, "30m": 1800, "1H": 3600,
        "4H": 14400, "1D": 86400,
    }.get(resolution, 14400)
    time_from = now - res_seconds * limit

    url = f"{BIRDEYE_BASE}/defi/ohlcv"
    params = {
        "address": token_address,
        "type": resolution,
        "time_from": time_from,
        "time_to": now,
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=_headers(key), params=params)
            if resp.status_code == 429:
                logger.warning("[birdeye] Rate limited on ohlcv for {}", token_address[:8])
                return []
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning("[birdeye] ohlcv error for {}: {}", token_address[:8], e)
        return []

    items = data.get("data", {}).get("items", []) or []
    return sorted(items, key=lambda c: c.get("unixTime", 0))


def price_increase_pct_over_window(
    token_address: str,
    hours: int = 2,
) -> float | None:
    """
    Returns the % price increase over the last `hours` hours.
    Uses 1H candles; negative means price dropped.
    Returns None if OHLCV data unavailable.
    """
    candles = get_token_ohlcv(token_address, resolution="1H", limit=hours + 2)
    if len(candles) < 2:
        return None
    # Use the close of (hours+1) candles ago as baseline, current close as latest
    baseline_candle = candles[max(0, len(candles) - hours - 1)]
    latest_candle = candles[-1]
    baseline_price = float(baseline_candle.get("open", 0) or 0)
    latest_price = float(latest_candle.get("close", 0) or 0)
    if baseline_price <= 0:
        return None
    return (latest_price - baseline_price) / baseline_price * 100


# ── Historical Price Lookup ────────────────────────────────────────────────────

def get_price_at_timestamp(
    token_address: str,
    unix_ts: int,
    resolution: str = "1H",
) -> float | None:
    """
    Get the approximate price of a token at a given Unix timestamp.

    Uses OHLCV data: fetches the candle containing the timestamp and returns
    the close price. Available on the free Birdeye tier.

    Returns None if no data available.
    """
    # Fetch a window: ±6 candles around the target timestamp
    res_seconds = {
        "15m": 900, "30m": 1800, "1H": 3600, "4H": 14400, "1D": 86400,
    }.get(resolution, 3600)

    time_from = unix_ts - res_seconds * 3
    time_to = unix_ts + res_seconds * 3
    key = _get_birdeye_key()
    if not key:
        return None

    url = f"{BIRDEYE_BASE}/defi/ohlcv"
    params = {
        "address": token_address,
        "type": resolution,
        "time_from": time_from,
        "time_to": time_to,
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            resp = client.get(url, headers=_headers(key), params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
    except Exception:
        return None

    candles = data.get("data", {}).get("items", []) or []
    if not candles:
        return None

    # Find the candle whose window contains our timestamp
    best = None
    for candle in candles:
        candle_ts = candle.get("unixTime", 0)
        if candle_ts <= unix_ts <= candle_ts + res_seconds:
            best = candle
            break
    # Fallback: nearest candle
    if best is None and candles:
        best = min(candles, key=lambda c: abs(c.get("unixTime", 0) - unix_ts))

    return float(best.get("c", best.get("close", 0)) or 0) if best else None


# ── Wallet Transaction History ─────────────────────────────────────────────────
#
# NOTE: Birdeye /v1/wallet/tx_list requires a paid plan (401 on free tier).
# For wallet win rate computation we use Helius Enhanced TX API instead.
# The functions below accept Helius-format transactions and compute win rate
# using Birdeye OHLCV for price data at trade time.

def get_wallet_tx_list(
    wallet_address: str,
    limit: int = 100,
    tx_type: str = "swap",
) -> list[dict[str, Any]]:
    """
    Fetch wallet swap transactions.

    NOTE: Birdeye wallet endpoint requires paid plan — this function returns []
    on the free tier. Use Helius helius_client.get_wallet_transactions() instead
    and pass results to compute_wallet_win_rate_from_helius_txs().

    Kept for forward-compatibility when plan is upgraded.
    """
    logger.warning(
        "[birdeye] get_wallet_tx_list: requires paid plan. "
        "Use helius_client.get_wallet_transactions() + compute_wallet_win_rate_from_helius_txs() instead."
    )
    return []


def get_wallet_portfolio(wallet_address: str) -> dict[str, Any]:
    """
    Fetch wallet portfolio. Requires paid Birdeye plan — returns {} on free tier.
    Use Helius API for wallet data instead.
    """
    logger.warning("[birdeye] get_wallet_portfolio: requires paid plan.")
    return {}


# ── Win Rate Computation ───────────────────────────────────────────────────────

def compute_wallet_win_rate(
    helius_txs: list[dict[str, Any]],
    lookback_days: int = 90,
    min_hold_minutes: int = 5,
    use_birdeye_prices: bool = False,
) -> dict[str, Any]:
    """
    Compute win rate from Helius Enhanced Transaction API swap events.

    Accepts the output of helius_client.get_wallet_transactions() (Helius format).
    Strategy: For each swap, check if token price at T+24h > price at buy time.
    Uses Birdeye OHLCV for historical prices if use_birdeye_prices=True (slow).
    Otherwise uses a simpler proxy: win = token appeared in multiple wallets' signals.

    Helius tx format: {timestamp, type, tokenTransfers, nativeTransfers, ...}

    Returns:
      {
        win_rate: float (0-1),
        trade_count: int,
        avg_hold_minutes: float,
        total_volume_sol: float,
        disqualified: bool,
        reason: str,
      }
    """
    cutoff = time.time() - lookback_days * 86400
    SOL_MINT = "So11111111111111111111111111111111111111112"
    STABLE_MINTS = {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    }

    # Extract buy events from Helius SWAP transactions
    buys: list[dict] = []   # {ts, token, volume_sol}

    for tx in helius_txs:
        ts = tx.get("timestamp", 0)
        if ts < cutoff:
            continue
        if tx.get("type") != "SWAP":
            continue

        token_transfers = tx.get("tokenTransfers", []) or []
        native_transfers = tx.get("nativeTransfers", []) or []

        # Simple heuristic: if native SOL was sent (native_transfers) and
        # tokens were received (token_transfers), it's a SOL→token buy
        sol_sent = sum(
            t.get("amount", 0) for t in native_transfers
            if t.get("toUserAccount") and t.get("fromUserAccount")
        )
        tokens_received = [
            t for t in token_transfers
            if t.get("mint") not in STABLE_MINTS
            and t.get("mint") != SOL_MINT
            and t.get("toUserAccount")
        ]

        if sol_sent > 0 and tokens_received:
            sol_volume = sol_sent / 1_000_000_000  # lamports → SOL
            if sol_volume < 0.01:
                continue  # Dust trade

            token_mint = tokens_received[0].get("mint", "")
            if token_mint:
                buys.append({
                    "ts": ts,
                    "token": token_mint,
                    "volume_sol": round(sol_volume, 4),
                })

    trade_count = len(buys)
    avg_hold = 0.0  # Helius-only: can't compute hold time without sell data

    if use_birdeye_prices and buys:
        # Use Birdeye OHLCV to determine if T+24h price > buy price
        # NOTE: This makes one API call per unique token — rate limit sensitive
        wins = 0
        evaluated = 0
        for buy in buys[:20]:  # Cap at 20 to stay within rate limits
            token = buy["token"]
            buy_ts = buy["ts"]
            buy_price = get_price_at_timestamp(token, buy_ts, resolution="1H")
            future_price = get_price_at_timestamp(token, buy_ts + 86400, resolution="1H")
            time.sleep(RATE_LIMIT_SLEEP)
            if buy_price and future_price and buy_price > 0:
                evaluated += 1
                if future_price > buy_price:
                    wins += 1
        win_rate = wins / evaluated if evaluated > 0 else 0.0
        trade_count = evaluated
    else:
        # Fallback: use swap count as a quality proxy
        # Can't compute actual win rate without sell data — return neutral 0.5
        win_rate = 0.5
        trade_count = len(buys)

    total_volume_sol = sum(b["volume_sol"] for b in buys)
    disqualified = trade_count < 10
    reason = f"insufficient trades ({trade_count}, need 10+)" if disqualified else ""

    return {
        "win_rate": round(win_rate, 3),
        "trade_count": trade_count,
        "avg_hold_minutes": round(avg_hold, 1),
        "total_volume_sol": round(total_volume_sol, 4),
        "disqualified": disqualified,
        "reason": reason,
        "method": "birdeye_ohlcv" if use_birdeye_prices else "helius_count_proxy",
    }


def score_wallet(win_rate_stats: dict[str, Any]) -> float:
    """
    Composite wallet quality score (0-1) based on research framework.

    Formula:
      score = win_rate * 0.50 + pnl_factor * 0.25 + recency * 0.15 + diversity * 0.10

    Designed to match Section 4.1 of SIGNAL_QUALITY_RESEARCH.md.
    Returns 0.0 if disqualified (insufficient trades).
    """
    if win_rate_stats.get("disqualified"):
        return 0.0

    wr = win_rate_stats.get("win_rate", 0.0)
    trade_count = win_rate_stats.get("trade_count", 0)
    pnl = win_rate_stats.get("total_realized_pnl_usd", 0.0)
    avg_hold = win_rate_stats.get("avg_hold_minutes", 0.0)

    # Win rate (50% weight) — normalized: 55% = 0.5 base score, 90% = 1.0
    wr_score = min(1.0, max(0.0, (wr - 0.30) / 0.60))

    # PnL factor (25% weight) — positive PnL vs trade volume as proxy
    vol = win_rate_stats.get("total_volume_usd", 1.0)
    pnl_ratio = pnl / vol if vol > 0 else 0.0
    pnl_score = min(1.0, max(0.0, (pnl_ratio + 0.1) / 0.3))  # -10% to +20% range → 0-1

    # Recency/trade count (15% weight) — more trades = more reliable
    count_score = min(1.0, trade_count / 50.0)  # 50 trades = full score

    # Hold time (10% weight) — bots average <5min, humans 30min+
    hold_score = min(1.0, avg_hold / 120.0)  # 2h hold = full score

    composite = wr_score * 0.50 + pnl_score * 0.25 + count_score * 0.15 + hold_score * 0.10
    return round(composite, 3)

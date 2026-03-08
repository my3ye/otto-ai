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


def compute_wallet_win_rate_from_pairs(
    wallet_address: str,
    helius_txs: list[dict[str, Any]],
    lookback_days: int = 90,
    min_sol_per_trade: float = 0.01,
) -> dict[str, Any]:
    """
    Compute win rate by tracking buy/sell pairs per token from Helius tx history.

    This replaces the broken proxy (0.5 for all) and OHLCV approaches (fails for
    recent/delisted tokens). Uses actual realized PnL from completed trade cycles.

    Key design decisions:
    - Only processes transactions where feePayer == wallet_address (wallet initiated trade).
      This correctly excludes LP position wallets (SM_11/13/17/18) which are passive.
    - Tracks wSOL (wrapped SOL) as currency: modern DEX swaps use wSOL not native SOL.
      wSOL transfers give the real cost/revenue of each trade.
    - FIFO cost basis matching for buy→sell pairs of the same token.
    - Token→token rollover: when wallet swaps A→B, B inherits A's cost basis.
    - Open positions = bought but not sold within the lookback window (excluded from WR).

    Returns:
      win_rate: float [0-1]
      completed_trades: int  — buy+sell pairs matched
      wins: int
      losses: int
      open_positions: int    — tokens held, not yet sold
      realized_pnl_sol: float  — total realized PnL in wSOL/SOL equivalent
      avg_hold_minutes: float
      trade_count: int         — alias for completed_trades (score_wallet compat)
      total_realized_pnl_usd: float  — alias for realized_pnl_sol (proxy, not USD)
      total_volume_sol: float  — total SOL/wSOL spent across all tracked buys
      total_volume_usd: float  — alias for total_volume_sol (proxy, not USD)
      disqualified: bool       — True if completed_trades < 5
      reason: str
      method: str = "helius_pair_tracking"
    """
    from collections import defaultdict, deque

    MIN_COMPLETED_TRADES = 5

    WSOL_MINT = "So11111111111111111111111111111111111111112"  # Wrapped SOL
    STABLE_MINTS = {
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
        "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT alt
    }
    CURRENCY_MINTS = STABLE_MINTS | {WSOL_MINT}  # Not traded assets — used as currency

    cutoff = time.time() - lookback_days * 86400

    # ── Filter: only process txs wallet INITIATED (feePayer = wallet) ─────────
    # This correctly excludes LP position wallets where other wallets trigger swaps
    # against the LP — the LP appears in tokenTransfers but didn't initiate the tx.
    sorted_txs = sorted(
        [tx for tx in helius_txs
         if tx.get("timestamp", 0) >= cutoff
         and tx.get("type") == "SWAP"
         and tx.get("feePayer") == wallet_address],
        key=lambda x: x.get("timestamp", 0),
    )

    # holdings[token_mint] = deque of {"buy_ts": int, "sol_cost": float, "token_amount": float}
    # sol_cost is the wSOL/SOL basis (possibly inherited through token→token rollovers)
    holdings: dict[str, deque] = defaultdict(deque)

    completed_trades: list[dict] = []
    total_buy_sol: float = 0.0  # Track total SOL/wSOL spent on buys

    for tx in sorted_txs:
        ts = tx.get("timestamp", 0)
        account_data = tx.get("accountData") or []
        token_transfers = tx.get("tokenTransfers") or []

        # ── Step 1: Get wallet's native SOL change (fallback for non-wSOL swaps) ─
        sol_delta_lamports = 0
        for acc in account_data:
            if acc.get("account") == wallet_address:
                sol_delta_lamports = acc.get("nativeBalanceChange", 0) or 0
                break
        native_sol_delta = sol_delta_lamports / 1_000_000_000

        # ── Step 2: Track wSOL and non-stable token flows for this wallet ────────
        wsol_recv: float = 0.0   # wSOL received by wallet (from sells)
        wsol_sent: float = 0.0   # wSOL sent by wallet (for buys)
        tokens_received: dict[str, float] = {}   # non-currency tokens received
        tokens_sent: dict[str, float] = {}       # non-currency tokens sent

        for xfer in token_transfers:
            mint = xfer.get("mint", "")
            if not mint:
                continue
            amount = float(xfer.get("tokenAmount", 0) or 0)
            if amount <= 0:
                continue

            if mint == WSOL_MINT:
                if xfer.get("toUserAccount") == wallet_address:
                    wsol_recv += amount
                if xfer.get("fromUserAccount") == wallet_address:
                    wsol_sent += amount
            elif mint not in STABLE_MINTS:
                if xfer.get("toUserAccount") == wallet_address:
                    tokens_received[mint] = tokens_received.get(mint, 0) + amount
                if xfer.get("fromUserAccount") == wallet_address:
                    tokens_sent[mint] = tokens_sent.get(mint, 0) + amount

        # ── Step 3: Compute net SOL proxy (wSOL is primary; native SOL is fallback) ─
        # Net wSOL flow: positive = received, negative = spent
        net_wsol = wsol_recv - wsol_sent
        # Use wSOL as primary currency indicator; native SOL as secondary for DEXes
        # that unwrap SOL directly (less common with modern DEXes)
        sol_proxy_spent = wsol_sent if wsol_sent > 0.001 else max(0.0, -native_sol_delta)
        sol_proxy_recv = wsol_recv if wsol_recv > 0.001 else max(0.0, native_sol_delta)

        # ── Step 4: Classify transaction ──────────────────────────────────────────
        #
        # JIT LP detection: if for ANY token, the sent and received amounts are
        # nearly identical (within 0.5%), this tx is a JIT liquidity provision
        # event, not a directional trade. Skip these entirely.
        jit_lp_tx = any(
            mint in tokens_sent and tokens_sent[mint] > 0 and
            abs(tokens_received.get(mint, 0) - tokens_sent[mint]) / tokens_sent[mint] < 0.005
            for mint in tokens_received
        )
        if jit_lp_tx:
            continue  # JIT LP tx: wallet added/removed liquidity atomically

        is_buy = sol_proxy_spent > min_sol_per_trade and bool(tokens_received)
        is_sell = sol_proxy_recv > 0.001 and bool(tokens_sent)
        # Token→token: no meaningful wSOL/SOL change but both tokens moved
        is_token_swap = (
            bool(tokens_received) and bool(tokens_sent)
            and not is_buy and not is_sell
            and abs(net_wsol) < 0.001
            and abs(native_sol_delta) < 0.001
        )

        if is_buy and tokens_received:
            # wSOL/SOL → Token BUY
            # Distribute cost evenly if multiple tokens received (rare)
            num_tokens = len(tokens_received)
            sol_per_token = sol_proxy_spent / num_tokens
            total_buy_sol += sol_proxy_spent

            for mint, amount in tokens_received.items():
                holdings[mint].append({
                    "buy_ts": ts,
                    "sol_cost": sol_per_token,
                    "token_amount": amount,
                })

        elif is_sell and tokens_sent:
            # Token → wSOL/SOL SELL: FIFO match against prior buys
            num_tokens = len(tokens_sent)
            sol_per_token = sol_proxy_recv / num_tokens

            for mint, amount in tokens_sent.items():
                if not holdings[mint]:
                    continue  # No tracked buy → skip (pre-lookback purchase)

                sol_received_for_this = sol_per_token
                sol_basis = 0.0
                remaining_to_sell = amount
                earliest_buy_ts = ts  # fallback

                while remaining_to_sell > 1e-9 and holdings[mint]:
                    oldest = holdings[mint][0]

                    if oldest["token_amount"] <= remaining_to_sell + 1e-9:
                        # Consume entire buy lot
                        sol_basis += oldest["sol_cost"]
                        remaining_to_sell -= oldest["token_amount"]
                        earliest_buy_ts = oldest["buy_ts"]
                        holdings[mint].popleft()
                    else:
                        # Partial consume: split the lot proportionally
                        fraction = remaining_to_sell / oldest["token_amount"]
                        portion_cost = oldest["sol_cost"] * fraction
                        sol_basis += portion_cost
                        earliest_buy_ts = oldest["buy_ts"]
                        # Update lot in place
                        oldest["sol_cost"] -= portion_cost
                        oldest["token_amount"] -= remaining_to_sell
                        remaining_to_sell = 0

                if sol_basis > 0:
                    pnl_sol = sol_received_for_this - sol_basis
                    hold_minutes = (ts - earliest_buy_ts) / 60 if earliest_buy_ts else 0

                    completed_trades.append({
                        "token": mint,
                        "buy_ts": earliest_buy_ts,
                        "sell_ts": ts,
                        "sol_spent": round(sol_basis, 6),
                        "sol_received": round(sol_received_for_this, 6),
                        "pnl_sol": round(pnl_sol, 6),
                        "hold_minutes": round(hold_minutes, 1),
                        "is_win": pnl_sol > 0,
                    })

        elif is_token_swap:
            # Token → Token SWAP: transfer cost basis from sold token to bought token
            # Handles Jupiter routes where SOL→A→B→SOL happens across multiple txs
            for sent_mint, sent_amount in tokens_sent.items():
                if not holdings[sent_mint]:
                    continue

                # Extract cost basis from sent token (consume FIFO lots)
                extracted_basis = 0.0
                remaining = sent_amount

                while remaining > 1e-9 and holdings[sent_mint]:
                    oldest = holdings[sent_mint][0]
                    if oldest["token_amount"] <= remaining + 1e-9:
                        extracted_basis += oldest["sol_cost"]
                        remaining -= oldest["token_amount"]
                        holdings[sent_mint].popleft()
                    else:
                        fraction = remaining / oldest["token_amount"]
                        portion = oldest["sol_cost"] * fraction
                        extracted_basis += portion
                        oldest["sol_cost"] -= portion
                        oldest["token_amount"] -= remaining
                        remaining = 0

                if extracted_basis > 0:
                    # Transfer basis to received tokens (split evenly if multiple)
                    num_received = len(tokens_received)
                    basis_per_received = extracted_basis / num_received if num_received > 0 else 0

                    for recv_mint, recv_amount in tokens_received.items():
                        if recv_mint in CURRENCY_MINTS:
                            continue
                        holdings[recv_mint].append({
                            "buy_ts": ts,
                            "sol_cost": basis_per_received,
                            "token_amount": recv_amount,
                        })

    # ── Compute open positions ────────────────────────────────────────────────
    open_positions = sum(
        1 for lots in holdings.values()
        for lot in lots
        if lot.get("sol_cost", 0) > 0
    )

    # ── Aggregate results ─────────────────────────────────────────────────────
    wins = sum(1 for t in completed_trades if t["is_win"])
    losses = len(completed_trades) - wins
    total_pnl_sol = sum(t["pnl_sol"] for t in completed_trades)
    avg_hold = (
        sum(t["hold_minutes"] for t in completed_trades) / len(completed_trades)
        if completed_trades else 0.0
    )

    n = len(completed_trades)
    win_rate = wins / n if n > 0 else 0.0
    disqualified = n < MIN_COMPLETED_TRADES
    reason = ""
    if disqualified:
        reason = f"insufficient completed trades ({n}, need {MIN_COMPLETED_TRADES}+)"

    return {
        "win_rate": round(win_rate, 3),
        "completed_trades": n,
        "wins": wins,
        "losses": losses,
        "open_positions": open_positions,
        "realized_pnl_sol": round(total_pnl_sol, 4),
        "avg_hold_minutes": round(avg_hold, 1),
        # Compat aliases for score_wallet()
        "trade_count": n,
        "total_realized_pnl_usd": round(total_pnl_sol, 4),  # SOL as proxy (directionally correct)
        "total_volume_sol": round(total_buy_sol, 4),
        "total_volume_usd": round(total_buy_sol, 4),         # SOL as proxy
        "disqualified": disqualified,
        "reason": reason,
        "method": "helius_pair_tracking",
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

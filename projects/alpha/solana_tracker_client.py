"""
solana_tracker_client.py — Solana Tracker API Client (rate-guarded)

Paid tier: 10,000 req/month ($1/month). Use sparingly.
Base URL: https://data.solanatracker.io
Auth: x-api-key header

RATE-LIMIT GUARDS (per Mev directive):
  - Fallback-first: only call ST when no other source can answer
  - Monthly request counter persisted to disk, hard cap at 9,500
  - Warnings logged at 80% budget (7,600 requests)
  - Graceful rejection with informative error when cap is hit

Key endpoint: GET /pnl/{wallet}
Returns: win_rate, realized_pnl, trade_count, avg_hold_time

Usage:
    from solana_tracker_client import get_wallet_pnl, score_wallet_st, budget_status
    stats = get_wallet_pnl("WalletAddressHere")
    score = score_wallet_st("WalletAddressHere")
    remaining = budget_status()  # check remaining requests
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SOLANA_TRACKER_API_KEY: str = os.environ.get("SOLANA_TRACKER_API_KEY", "")
BASE_URL = "https://data.solanatracker.io"
RATE_LIMIT_SLEEP = 0.12  # 10 RPS max → 100ms between calls; 120ms to be safe

# Budget constants — Mev pays $1/month for 10K requests. Leave 500 buffer.
MONTHLY_HARD_CAP = 9_500
MONTHLY_WARN_THRESHOLD = 7_600  # 80% of cap → start logging warnings

# Persisted usage counter (simple JSON file, no DB dependency)
_USAGE_FILE = Path(__file__).parent / ".solana_tracker_usage.json"

logger = logging.getLogger("solana_tracker")


# ---------------------------------------------------------------------------
# Budget tracking — persisted monthly counter
# ---------------------------------------------------------------------------
def _current_month() -> str:
    """Return YYYY-MM in UTC for consistent month boundaries."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _load_usage() -> dict:
    """Load usage counter from disk. Auto-resets on new month."""
    default = {"month": _current_month(), "count": 0}
    if not _USAGE_FILE.exists():
        return default
    try:
        data = json.loads(_USAGE_FILE.read_text())
        # Auto-reset if we've rolled into a new month
        if data.get("month") != _current_month():
            logger.info("[ST] New month detected — resetting usage counter from %d", data.get("count", 0))
            return default
        return data
    except (json.JSONDecodeError, KeyError):
        return default


def _save_usage(data: dict) -> None:
    """Persist usage counter atomically (write-then-rename)."""
    tmp = _USAGE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.rename(_USAGE_FILE)


def _increment_usage() -> int:
    """Increment the monthly counter. Returns new count."""
    data = _load_usage()
    data["count"] = data.get("count", 0) + 1
    data["month"] = _current_month()
    _save_usage(data)
    return data["count"]


def _check_budget() -> tuple[bool, int, str]:
    """
    Check if we can make another request.
    Returns (allowed, current_count, message).
    """
    data = _load_usage()
    count = data.get("count", 0)

    if count >= MONTHLY_HARD_CAP:
        msg = (
            f"[ST] BLOCKED: Monthly budget exhausted ({count}/{MONTHLY_HARD_CAP}). "
            f"Resets on the 1st of next month. Use DexScreener or Helius instead."
        )
        return False, count, msg

    if count >= MONTHLY_WARN_THRESHOLD:
        pct = count / MONTHLY_HARD_CAP * 100
        msg = f"[ST] WARNING: {pct:.0f}% of monthly budget used ({count}/{MONTHLY_HARD_CAP})"
        logger.warning(msg)
        print(msg)

    return True, count, ""


def budget_status() -> dict:
    """
    Public helper to check budget without making a request.
    Returns dict with month, used, remaining, cap, pct_used.
    """
    data = _load_usage()
    count = data.get("count", 0)
    return {
        "month": data.get("month", _current_month()),
        "used": count,
        "remaining": max(0, MONTHLY_HARD_CAP - count),
        "cap": MONTHLY_HARD_CAP,
        "pct_used": round(count / MONTHLY_HARD_CAP * 100, 1),
        "blocked": count >= MONTHLY_HARD_CAP,
    }


# ---------------------------------------------------------------------------
# Fallback-first pattern
# ---------------------------------------------------------------------------
class SolanaTrackerBudgetExhausted(Exception):
    """Raised when monthly request cap is hit. Caller should use alternative source."""
    pass


def require_budget(func):
    """
    Decorator that gates every ST API call behind the budget check.
    Raises SolanaTrackerBudgetExhausted if cap is reached.
    """
    def wrapper(*args, **kwargs):
        allowed, count, msg = _check_budget()
        if not allowed:
            raise SolanaTrackerBudgetExhausted(msg)
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def _headers() -> dict:
    key = SOLANA_TRACKER_API_KEY or os.environ.get("SOLANA_TRACKER_API_KEY", "")
    if not key:
        raise ValueError(
            "SOLANA_TRACKER_API_KEY not set. "
            "Add key to ~/memory/.env"
        )
    return {"x-api-key": key}


# ---------------------------------------------------------------------------
# Core API calls (budget-gated)
# ---------------------------------------------------------------------------
@require_budget
def get_wallet_pnl(wallet: str, timeout: float = 15.0) -> Optional[dict]:
    """
    Fetch wallet PnL stats from Solana Tracker.

    IMPORTANT: This costs 1 request from a 10K/month budget.
    Prefer DexScreener (free, unlimited) or Helius for data they can provide.
    Only use this for wallet-level PnL/win-rate data that other sources lack.

    Returns dict with keys:
        win_rate        float  (0.0-1.0)  fraction of trades that were profitable
        realized_pnl    float  USD realized profit/loss
        trade_count     int    total completed trades
        avg_hold_time   float  average hold time in minutes (None if unavailable)
        raw             dict   full API response

    Returns None on HTTP error (404, rate limit, etc).
    Raises SolanaTrackerBudgetExhausted if monthly cap hit.
    """
    url = f"{BASE_URL}/pnl/{wallet}"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=_headers())

        # Count this request regardless of response status
        new_count = _increment_usage()
        if new_count % 100 == 0:
            status = budget_status()
            logger.info("[ST] Budget checkpoint: %d/%d used (%.0f%%)",
                        status["used"], status["cap"], status["pct_used"])

        if resp.status_code == 429:
            print(f"  [ST] Rate limited for {wallet[:12]}... sleeping 5s")
            time.sleep(5)
            return None

        if resp.status_code == 404:
            return None

        resp.raise_for_status()
        data = resp.json()

    except httpx.HTTPStatusError as e:
        print(f"  [ST] HTTP error for {wallet[:12]}: {e.response.status_code}")
        return None
    except SolanaTrackerBudgetExhausted:
        raise  # Don't swallow budget errors
    except Exception as e:
        print(f"  [ST] Error for {wallet[:12]}: {e}")
        return None

    # Normalize response fields
    # API shape: { "winRate": 0.72, "realizedPnl": 1234.56, "tradesCount": 87,
    #              "avgHoldingTime": 3600, ... }
    win_rate = (
        data.get("winRate")
        or data.get("win_rate")
        or data.get("winrate")
        or 0.0
    )
    realized_pnl = (
        data.get("realizedPnl")
        or data.get("realized_pnl")
        or data.get("pnl")
        or 0.0
    )
    trade_count = int(
        data.get("tradesCount")
        or data.get("trades_count")
        or data.get("tradeCount")
        or data.get("trade_count")
        or 0
    )
    avg_hold = (
        data.get("avgHoldingTime")
        or data.get("avg_holding_time")
        or data.get("avgHoldTime")
        or None
    )
    avg_hold_minutes = float(avg_hold) / 60.0 if avg_hold else None

    return {
        "win_rate": float(win_rate),
        "realized_pnl": float(realized_pnl),
        "trade_count": trade_count,
        "avg_hold_minutes": avg_hold_minutes,
        "raw": data,
    }


def score_wallet_st(
    wallet: str,
    min_trade_count: int = 30,
    min_hold_minutes: float = 5.0,
) -> Optional[dict]:
    """
    Score a wallet using Solana Tracker PnL data.
    Returns scoring dict, or None if data unavailable.
    Raises SolanaTrackerBudgetExhausted if monthly cap hit.

    Scoring mirrors birdeye_requalification.py thresholds:
        MIN_WIN_RATE_KEEP = 0.55
        MIN_WIN_RATE_ADD  = 0.65
        MIN_TRADE_COUNT   = 30
        MIN_AVG_HOLD_MINUTES = 5.0
    """
    stats = get_wallet_pnl(wallet)  # budget check happens inside
    time.sleep(RATE_LIMIT_SLEEP)

    if stats is None:
        return None

    win_rate = stats["win_rate"]
    trade_count = stats["trade_count"]
    avg_hold = stats["avg_hold_minutes"]

    is_bot = avg_hold is not None and avg_hold < min_hold_minutes
    insufficient_data = trade_count < min_trade_count

    return {
        "wallet": wallet,
        "win_rate": win_rate,
        "realized_pnl": stats["realized_pnl"],
        "trade_count": trade_count,
        "avg_hold_minutes": avg_hold,
        "is_bot": is_bot,
        "insufficient_data": insufficient_data,
        "qualifies_keep": win_rate >= 0.55 and not is_bot and not insufficient_data,
        "qualifies_add":  win_rate >= 0.65 and not is_bot and not insufficient_data,
    }


def batch_score_wallets(
    wallets: list[str],
    min_trade_count: int = 30,
    min_hold_minutes: float = 5.0,
    verbose: bool = True,
) -> list[dict]:
    """
    Score a list of wallets. Rate-limited to 10 RPS.
    Stops early if budget is exhausted (logs warning, returns partial results).
    """
    results = []
    for i, wallet in enumerate(wallets):
        if verbose:
            print(f"  [{i+1}/{len(wallets)}] Scoring {wallet[:16]}...")
        try:
            score = score_wallet_st(wallet, min_trade_count, min_hold_minutes)
        except SolanaTrackerBudgetExhausted as e:
            print(f"  [ST] Budget exhausted after {i} wallets: {e}")
            break
        if score:
            results.append(score)
            if verbose:
                wr = score["win_rate"]
                tc = score["trade_count"]
                q = "KEEP" if score["qualifies_keep"] else ("ADD" if score["qualifies_add"] else "DROP")
                print(f"    -> WR={wr:.1%} trades={tc} [{q}]")
        else:
            if verbose:
                print(f"    -> No data")
    return results


def test_connection() -> bool:
    """Quick connectivity test. Costs 1 request from budget."""
    TEST_WALLET = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"  # Raydium AMM
    try:
        result = get_wallet_pnl(TEST_WALLET, timeout=10.0)
        return True
    except (ValueError, SolanaTrackerBudgetExhausted):
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if not SOLANA_TRACKER_API_KEY:
        print("ERROR: SOLANA_TRACKER_API_KEY not set in environment.")
        print("  Add to ~/memory/.env and source it")
        sys.exit(1)

    # Always show budget status first
    status = budget_status()
    print(f"Budget: {status['used']}/{status['cap']} used ({status['pct_used']}%), "
          f"{status['remaining']} remaining")
    if status["blocked"]:
        print("BLOCKED: Monthly budget exhausted. Use DexScreener/Helius instead.")
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--status":
        # Just show budget, already printed above
        sys.exit(0)

    if len(sys.argv) > 1:
        wallet = sys.argv[1]
        print(f"Scoring wallet: {wallet}")
        try:
            score = score_wallet_st(wallet)
            if score:
                print(json.dumps(score, indent=2))
            else:
                print("No data returned.")
        except SolanaTrackerBudgetExhausted as e:
            print(f"BLOCKED: {e}")
            sys.exit(1)
    else:
        print("Testing connection...")
        ok = test_connection()
        print(f"Connection: {'OK' if ok else 'FAILED'}")
        if ok:
            print(f"API key: {SOLANA_TRACKER_API_KEY[:8]}...")

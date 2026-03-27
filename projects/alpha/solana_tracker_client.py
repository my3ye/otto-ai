"""
solana_tracker_client.py — Solana Tracker API Client

Free tier: 500K credits/month, 10 RPS
Base URL: https://data.solanatracker.io
Auth: x-api-key header

Key endpoint: GET /pnl/{wallet}
Returns: win_rate, realized_pnl, trade_count, avg_hold_time
Replaces Birdeye wallet scoring (which requires paid plan for wallet endpoints).

Usage:
    from solana_tracker_client import get_wallet_pnl, score_wallet_st
    stats = get_wallet_pnl("WalletAddressHere")
    score = score_wallet_st("WalletAddressHere")
"""

from __future__ import annotations

import os
import time
from typing import Optional

import httpx
from dotenv import load_dotenv

load_dotenv()

SOLANA_TRACKER_API_KEY: str = os.environ.get("SOLANA_TRACKER_API_KEY", "")
BASE_URL = "https://data.solanatracker.io"
RATE_LIMIT_SLEEP = 0.12  # 10 RPS max → 100ms between calls; 120ms to be safe


def _headers() -> dict:
    key = SOLANA_TRACKER_API_KEY or os.environ.get("SOLANA_TRACKER_API_KEY", "")
    if not key:
        raise ValueError(
            "SOLANA_TRACKER_API_KEY not set. "
            "Register free at data.solanatracker.io, then add key to ~/memory/.env"
        )
    return {"x-api-key": key}


def get_wallet_pnl(wallet: str, timeout: float = 15.0) -> Optional[dict]:
    """
    Fetch wallet PnL stats from Solana Tracker.

    Returns dict with keys:
        win_rate        float  (0.0–1.0)  fraction of trades that were profitable
        realized_pnl    float  USD realized profit/loss
        trade_count     int    total completed trades
        avg_hold_time   float  average hold time in seconds (None if unavailable)
        raw             dict   full API response

    Returns None on error.
    """
    url = f"{BASE_URL}/pnl/{wallet}"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, headers=_headers())

        if resp.status_code == 429:
            print(f"  [ST] Rate limited for {wallet[:12]}... sleeping 5s")
            time.sleep(5)
            return None

        if resp.status_code == 404:
            # Wallet not found / no trading history
            return None

        resp.raise_for_status()
        data = resp.json()

    except httpx.HTTPStatusError as e:
        print(f"  [ST] HTTP error for {wallet[:12]}: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"  [ST] Error for {wallet[:12]}: {e}")
        return None

    # Normalize response fields
    # Solana Tracker PnL response shape (based on API docs):
    # { "winRate": 0.72, "realizedPnl": 1234.56, "tradesCount": 87,
    #   "avgHoldingTime": 3600, ... }
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

    Scoring mirrors birdeye_requalification.py thresholds:
        MIN_WIN_RATE_KEEP = 0.55
        MIN_WIN_RATE_ADD  = 0.65
        MIN_TRADE_COUNT   = 30
        MIN_AVG_HOLD_MINUTES = 5.0
    """
    stats = get_wallet_pnl(wallet)
    time.sleep(RATE_LIMIT_SLEEP)

    if stats is None:
        return None

    win_rate = stats["win_rate"]
    trade_count = stats["trade_count"]
    avg_hold = stats["avg_hold_minutes"]

    # Reject bots: <5min avg hold time
    is_bot = avg_hold is not None and avg_hold < min_hold_minutes
    # Reject thin sample: <30 trades
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
    Returns list of score dicts (None results excluded).
    """
    results = []
    for i, wallet in enumerate(wallets):
        if verbose:
            print(f"  [{i+1}/{len(wallets)}] Scoring {wallet[:16]}...")
        score = score_wallet_st(wallet, min_trade_count, min_hold_minutes)
        if score:
            results.append(score)
            if verbose:
                wr = score["win_rate"]
                tc = score["trade_count"]
                q = "KEEP" if score["qualifies_keep"] else ("ADD" if score["qualifies_add"] else "DROP")
                print(f"    → WR={wr:.1%} trades={tc} [{q}]")
        else:
            if verbose:
                print(f"    → No data")
    return results


def test_connection() -> bool:
    """Quick connectivity test. Returns True if API key is valid."""
    # Use a known active Solana wallet for the test
    TEST_WALLET = "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1"  # Raydium AMM
    try:
        result = get_wallet_pnl(TEST_WALLET, timeout=10.0)
        # 404 = wallet not found but API key is valid
        # None only means error if exception was thrown
        return True
    except ValueError:
        # Missing API key
        return False
    except Exception:
        return False


if __name__ == "__main__":
    import sys

    if not SOLANA_TRACKER_API_KEY:
        print("ERROR: SOLANA_TRACKER_API_KEY not set in environment.")
        print("  Register free at https://data.solanatracker.io")
        print("  Then: echo 'SOLANA_TRACKER_API_KEY=<key>' >> ~/memory/.env")
        sys.exit(1)

    if len(sys.argv) > 1:
        wallet = sys.argv[1]
        print(f"Scoring wallet: {wallet}")
        score = score_wallet_st(wallet)
        if score:
            import json
            print(json.dumps(score, indent=2))
        else:
            print("No data returned.")
    else:
        print("Testing connection...")
        ok = test_connection()
        print(f"Connection: {'OK' if ok else 'FAILED'}")
        if ok:
            print(f"API key: {SOLANA_TRACKER_API_KEY[:8]}...")

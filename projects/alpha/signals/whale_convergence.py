"""
SM_12: Whale Wallet Convergence (Enhanced)

Enhanced convergence strategy using all 15 discovered wallets.
Signals when 2+ wallets buy the same token within a 60-minute window (vs 30min before).
Extended window should increase signal frequency ~2x.
Also adds minimum buy size filter ($100+) to reduce noise.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from collections import defaultdict, Counter
from typing import Optional

SIGNAL_NAME = "SM_12_whale_convergence"
SIGNALS_PATH = os.path.join(os.path.dirname(__file__), '..', 'signals.jsonl')
WINDOW_MINUTES = 30       # Tightened back to 30min (60min was too wide — stale signals)
# Week 1 fix: raised from $100 → $500. $100 buys are bots/dust — not conviction trades.
# Backtest showed wrong wallet pool (SM_1/2/4/7 = bots) was the primary 30% WR cause.
# Raising the floor filters the smallest bot trades even from non-noisy wallets.
MIN_BUY_USD = 500         # Raised from $100 — require real conviction (not bot dust)
MIN_WALLETS = 4           # Raised from 3 — every trade had wallet_count=3 (no discriminating power)
# BUG FIX 6: Only look at signals from the last N hours — prevents stale signals from
# generating fresh convergence alerts every run (was causing same token to appear 112x)
# NOTE: Exit logic is now TP/SL-based (TP1=+10%, TP2=+25%, TP3=+50%, SL=-15%) in
# signal_publisher.py. This lookback controls data freshness for detection only.
SIGNAL_LOOKBACK_HOURS = 2

# BUG FIX 5: Noisy wallets — SM_1 (254 trades, all SELL/UNKNOWN) and
# SM_2 (700 trades, all SELL/UNKNOWN). Zero buys → pollute convergence signals.
# Analysis 2026-02-23: SM_4, SM_7, SM_10 also noisy — 0% WR across every signal.
NOISY_WALLETS = {"SM_1", "SM_2", "SM_4", "SM_7", "SM_10"}

# Stablecoins, base tokens, and large-cap tokens — never convergence signals
# Large-caps (BTC, ETH, SOL wrappers, major DeFi) cannot hit +25% TP in 4h window
BLOCKED_TOKENS = {
    # Stablecoins
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",  # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd",  # USDT alt
    "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB",   # USD1 (World Liberty) — primary
    "USD1ttGY1N17NEEHLmELZmFE4A7d5nSqeAV3f3BBRDB",  # USD1 (alt address) — BUG FIX 7
    "USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA",   # USDS (Drift)
    "USDH1SM1ojwWUga67PGrgFWUHibbjqMvuMaDkRJTgkX",   # USDH (Hubble)
    "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo",  # PYUSD (PayPal)
    "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT",  # UXD
    "Fm9rHUTF5v3hwMLbStjZXqNBBoZyGriQaFM6sTFz3K8A",  # USDD
    "AZsHEMXd36Bj1EMNXhowJajpUXzrKcK57wW4ZGXVa7yR",  # BUSD (Wormhole)
    "JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD",   # USD3/JUSD stablecoin — BUG FIX 7
    # Base/native tokens
    "So11111111111111111111111111111111111111112",     # SOL (wrapped)
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "7dHbWXmci3dT8UFYWYZweBLXgycu7Y3iL6trKn1Y7ARj",  # stSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",  # jitoSOL
    # Large-cap wrapped assets — TP+25% in 4h is unrealistic
    "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",   # cbBTC (Coinbase BTC)
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E",  # wBTC
    "2FPyTwcZLUgr5Th81bnrK3vGTDYddPTFJGe85tHFdSK3",  # wETH
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs",  # wETH alt
    # Major DeFi protocol tokens — stable, high liquidity, won't hit 25% in 4h
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",  # RAY (Raydium)
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",   # JUP (Jupiter)
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",   # ORCA
    "METvsvVRapdjFy6HZnpbfFd7WNJiMp1sT1Nz1rSAtFS",   # MET (Meteora)
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK (high-liq, won't 25% fast)
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # WIF
    "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4",  # Unknown DeFi, price ~$3.7 (too stable for 20% TP)
}

# Label→address mapping from wallets.json
WALLETS_PATH = os.path.join(os.path.dirname(__file__), '..', 'wallets.json')


def load_wallet_labels() -> dict:
    """Returns address→label mapping."""
    try:
        with open(WALLETS_PATH) as f:
            data = json.load(f)
        wallets = data.get("wallets", [])
        return {w["address"]: w["label"] for w in wallets}
    except Exception:
        return {}


def load_buy_signals() -> list[dict]:
    """
    Load MEDIUM/HIGH wallet buy signals from signals.jsonl.
    BUG FIX 6: Only loads signals within the last SIGNAL_LOOKBACK_HOURS (4h) to
    prevent stale signals from triggering fresh convergence detections every run.
    """
    records = []
    cutoff_ts = time.time() - SIGNAL_LOOKBACK_HOURS * 3600
    with open(SIGNALS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue

            # Must have token, wallet, signal
            token = r.get("token", "")
            if not token or len(token) < 20:
                continue
            if token in BLOCKED_TOKENS:
                continue
            if r.get("signal") not in ("MEDIUM", "HIGH"):
                continue

            wallet = r.get("wallet", "")
            if not wallet or wallet in ("CONVERGENCE", "MULTI"):
                continue
            # BUG FIX 5: Exclude noisy wallets (all SELL/UNKNOWN, zero buys)
            if wallet in NOISY_WALLETS:
                continue

            ts_str = r.get("timestamp", "")
            try:
                ts_str = ts_str.replace("Z", "+00:00")
                dt = datetime.fromisoformat(ts_str)
                ts = int(dt.timestamp())
            except Exception:
                continue

            # BUG FIX 6: Skip stale signals beyond lookback window
            if ts < cutoff_ts:
                continue

            # Week 1 fix: enforce MIN_BUY_USD filter (was defined but never applied!)
            # $100 buys are bots/dust — filter before convergence detection.
            amount_usd = float(r.get("amount_usd", 0) or 0)
            if amount_usd < MIN_BUY_USD:
                continue

            records.append({
                "ts": ts,
                "timestamp": ts_str,
                "token": token,
                "wallet": wallet,
                "amount_usd": amount_usd,
                "signal": r.get("signal"),
                # fee_payer: stored by live_watcher since Week 1 fix — used for coordinator detection
                "fee_payer": r.get("fee_payer", ""),
            })

    return sorted(records, key=lambda r: r["ts"])


def detect_convergence(records: list[dict]) -> list[dict]:
    """
    Sliding window convergence detection.
    Returns signals where MIN_WALLETS+ buy same token within WINDOW_MINUTES.
    """
    # Group by token
    token_buys: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        token_buys[r["token"]].append(r)

    signals = []
    seen_windows = set()  # Deduplicate overlapping windows

    for token, buys in token_buys.items():
        if len(buys) < MIN_WALLETS:
            continue

        buys_sorted = sorted(buys, key=lambda b: b["ts"])
        for i in range(len(buys_sorted)):
            window_start = buys_sorted[i]["ts"]
            window_end = window_start + (WINDOW_MINUTES * 60)

            window_buys = [
                b for b in buys_sorted[i:]
                if b["ts"] <= window_end
            ]

            # Deduplicate by wallet within window
            unique_wallets = {}
            for b in window_buys:
                wallet = b["wallet"]
                if wallet not in unique_wallets:
                    unique_wallets[wallet] = b

            if len(unique_wallets) < MIN_WALLETS:
                continue

            # --- Fee-payer cluster check (+8-12% WR) ---
            # If 3+ converging wallets share the same feePayer, it's a coordinated
            # insider pump (one coordinator paying fees for multiple sub-accounts).
            # Organic convergence = each wallet is its own feePayer (distinct addresses).
            # Only applies if fee_payer data is present (live_watcher stores it).
            fee_payers = [b.get("fee_payer", "") for b in unique_wallets.values()
                          if b.get("fee_payer")]
            if len(fee_payers) >= 3:
                most_common_fp, fp_count = Counter(fee_payers).most_common(1)[0]
                if fp_count >= 3 and most_common_fp:
                    # Coordinated: skip this convergence signal
                    continue

            # Deduplicate convergence events at same token+approx_time
            dedup_key = (token, window_start // 3600)  # Same hour
            if dedup_key in seen_windows:
                continue
            seen_windows.add(dedup_key)

            total_usd = sum(b["amount_usd"] for b in unique_wallets.values())
            signal_ts = max(b["ts"] for b in unique_wallets.values())

            signals.append({
                "signal_name": SIGNAL_NAME,
                "token": token,
                "signal_ts": signal_ts,
                "signal_time": datetime.fromtimestamp(signal_ts, tz=timezone.utc).isoformat(),
                "wallet_count": len(unique_wallets),
                "wallets": list(unique_wallets.keys()),
                "total_buy_usd": total_usd,
                "window_minutes": WINDOW_MINUTES,
                # MIN_WALLETS=3 baseline; ULTRA requires 4+ wallets for extra conviction
                "confidence": "ULTRA" if len(unique_wallets) >= 4 else "HIGH",
            })

    return sorted(signals, key=lambda s: s["signal_ts"])


def get_backtest_signals() -> list[dict]:
    """Backtest entry point."""
    records = load_buy_signals()
    print(f"[SM_12] Loaded {len(records)} buy signals from signals.jsonl")
    signals = detect_convergence(records)
    print(f"[SM_12] Detected {len(signals)} convergence events (window={WINDOW_MINUTES}min)")
    return signals


if __name__ == "__main__":
    signals = get_backtest_signals()
    print(f"\nSM_12 Whale Convergence signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  {s['signal_time']} | wallets={s['wallet_count']} | ${s['total_buy_usd']:.0f} | {s['confidence']}")

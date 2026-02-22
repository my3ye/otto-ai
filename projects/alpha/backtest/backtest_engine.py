"""
Backtesting engine for Solana copy trading convergence strategy.

Strategy: When 2+ tracked smart money wallets buy the same token
within 30 minutes (convergence signal), simulate entering a position.
Track P&L at T+1h, T+4h, T+24h.

Assumptions:
- Entry at close price of the candle containing the signal timestamp
- 0.3% slippage on entry (DEX swap slippage + fees)
- 0.3% slippage on exit
- $100 USDC per position (fixed sizing for analysis)
- No stop-loss in base simulation (analyzed separately)
"""

import json
import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from data_fetcher import get_prices_at_offsets, get_token_info_dexscreener, BASE_TOKENS
from signal_parser import extract_convergence_signals, extract_medium_signals
from metrics import summarize_trades, calculate_returns

SLIPPAGE = 0.003  # 0.3% per side
POSITION_SIZE_USDC = 100.0
OFFSETS_HOURS = [0, 1, 4, 24]

# Tokens known to not be useful signals (major/stable assets)
SKIP_TOKENS = BASE_TOKENS | {
    "swap",  # malformed signal
}


def apply_slippage(price: float, side: str = "buy") -> float:
    """Apply slippage to a price."""
    if side == "buy":
        return price * (1 + SLIPPAGE)
    return price * (1 - SLIPPAGE)


def run_convergence_backtest(
    min_wallets: int = 2,
    rate_limit_sleep: float = 12.0,
) -> dict:
    """
    Main convergence copy-trading backtest.
    Returns full results dict with trades and metrics.
    """
    print(f"\n{'='*60}")
    print("STRATEGY: Convergence Copy Trading")
    print(f"Entry: Signal when {min_wallets}+ wallets buy same token in 30min")
    print(f"Position: ${POSITION_SIZE_USDC} USDC per trade, {SLIPPAGE*100:.1f}% slippage/side")
    print("="*60)

    signals = extract_convergence_signals(min_wallets=min_wallets)
    print(f"\nFound {len(signals)} convergence signals")

    trades = []
    token_info_cache = {}

    for i, sig in enumerate(signals):
        token = sig["token"]

        if token in SKIP_TOKENS:
            print(f"  [{i+1}] SKIP {token[:20]} (base/skip token)")
            continue

        print(f"\n  [{i+1}] Signal: {sig['signal_time']}")
        print(f"       Token: {token[:20]}...")
        print(f"       Wallets: {sig['wallet_count']}")

        # Get token info
        if token not in token_info_cache:
            info = get_token_info_dexscreener(token)
            token_info_cache[token] = info
        else:
            info = token_info_cache[token]

        symbol = info.get("symbol", "?")
        print(f"       Symbol: {symbol}")

        # Fetch prices at signal time + offsets
        prices = get_prices_at_offsets(token, sig["signal_ts"], offsets_hours=OFFSETS_HOURS)

        entry_price_raw = prices.get(0)
        if not entry_price_raw:
            print(f"       SKIP: no price data at signal time")
            trades.append({
                "signal_time": sig["signal_time"],
                "token": token,
                "symbol": symbol,
                "wallet_count": sig["wallet_count"],
                "entry_price": None,
                "return_pct_1h": None,
                "return_pct_4h": None,
                "return_pct_24h": None,
                "note": "no price data",
            })
            time.sleep(rate_limit_sleep)
            continue

        entry_price = apply_slippage(entry_price_raw, "buy")

        # Calculate returns at each horizon
        trade = {
            "signal_time": sig["signal_time"],
            "token": token,
            "symbol": symbol,
            "wallet_count": sig["wallet_count"],
            "wallets": sig["wallets"],
            "entry_price": entry_price,
            "entry_price_raw": entry_price_raw,
            "liquidity_usd": info.get("liquidity_usd"),
        }

        for horizon_hours in [1, 4, 24]:
            exit_price_raw = prices.get(horizon_hours)
            if exit_price_raw:
                exit_price = apply_slippage(exit_price_raw, "sell")
                ret = calculate_returns(entry_price, exit_price)
                trade[f"return_pct_{horizon_hours}h"] = ret
                trade[f"exit_price_{horizon_hours}h"] = exit_price_raw
                print(f"       T+{horizon_hours}h: ${exit_price_raw:.8f} → {ret:+.2f}%")
            else:
                trade[f"return_pct_{horizon_hours}h"] = None
                trade[f"exit_price_{horizon_hours}h"] = None
                print(f"       T+{horizon_hours}h: no data")

        trades.append(trade)
        time.sleep(rate_limit_sleep)

    # Calculate metrics
    metrics = summarize_trades(trades)

    return {
        "strategy": "convergence_copy_trading",
        "config": {
            "min_wallets": min_wallets,
            "slippage_pct": SLIPPAGE * 100,
            "position_size_usdc": POSITION_SIZE_USDC,
        },
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "trades": trades,
        "metrics": metrics,
    }


def run_single_wallet_backtest(
    wallet_label: str = None,
    rate_limit_sleep: float = 12.0,
) -> dict:
    """
    Single wallet copy-trading backtest.
    Simulates copying every MEDIUM signal from a specific wallet.
    """
    signals = extract_medium_signals()

    if wallet_label:
        signals = [s for s in signals if wallet_label in s.get("wallet", "")]
        print(f"\nFiltered to wallet {wallet_label}: {len(signals)} signals")
    else:
        print(f"\nAll medium signals: {len(signals)}")

    trades = []
    token_info_cache = {}

    for i, sig in enumerate(signals):
        token = sig["token"]
        if token in SKIP_TOKENS or len(token) < 20:
            continue

        if token not in token_info_cache:
            info = get_token_info_dexscreener(token)
            token_info_cache[token] = info
        else:
            info = token_info_cache[token]

        symbol = info.get("symbol", "?")
        prices = get_prices_at_offsets(token, sig["signal_ts"], offsets_hours=OFFSETS_HOURS)
        entry_price_raw = prices.get(0)

        if not entry_price_raw:
            trades.append({
                "signal_time": sig["signal_time"],
                "token": token,
                "symbol": symbol,
                "wallet": sig["wallet"],
                "entry_price": None,
                "return_pct_1h": None,
                "return_pct_4h": None,
                "return_pct_24h": None,
                "note": "no price data",
            })
            time.sleep(rate_limit_sleep)
            continue

        entry_price = apply_slippage(entry_price_raw, "buy")
        trade = {
            "signal_time": sig["signal_time"],
            "token": token,
            "symbol": symbol,
            "wallet": sig["wallet"],
            "entry_price": entry_price,
            "entry_price_raw": entry_price_raw,
        }

        for horizon_hours in [1, 4, 24]:
            exit_price_raw = prices.get(horizon_hours)
            if exit_price_raw:
                exit_price = apply_slippage(exit_price_raw, "sell")
                ret = calculate_returns(entry_price, exit_price)
                trade[f"return_pct_{horizon_hours}h"] = ret
                trade[f"exit_price_{horizon_hours}h"] = exit_price_raw
            else:
                trade[f"return_pct_{horizon_hours}h"] = None
                trade[f"exit_price_{horizon_hours}h"] = None

        trades.append(trade)
        time.sleep(rate_limit_sleep)

    metrics = summarize_trades(trades)
    return {
        "strategy": "single_wallet_copy",
        "wallet_filter": wallet_label,
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
        "trades": trades,
        "metrics": metrics,
    }


if __name__ == "__main__":
    # Test with convergence strategy
    result = run_convergence_backtest(min_wallets=2)
    out_path = os.path.join(os.path.dirname(__file__), "results", "convergence_backtest.json")
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to {out_path}")
    print(f"\nMetrics summary:")
    print(json.dumps(result["metrics"], indent=2))

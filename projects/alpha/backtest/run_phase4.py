"""
Phase 4 Backtest Runner — SM_11 through SM_15

Runs all 5 new signal strategies against historical data and computes metrics.
Outputs results to backtest/results/phase4_results.json and phase4_report.md
"""

import os
import sys
import json
import time
from datetime import datetime, timezone

# Paths
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
BACKTEST_DIR = os.path.dirname(__file__)
SIGNALS_DIR = os.path.join(PROJECT_ROOT, 'signals')
RESULTS_DIR = os.path.join(BACKTEST_DIR, 'results')

sys.path.insert(0, BACKTEST_DIR)
sys.path.insert(0, SIGNALS_DIR)

from data_fetcher import get_prices_at_offsets, get_token_info_dexscreener, BASE_TOKENS
from metrics import summarize_trades, calculate_returns

SLIPPAGE = 0.003
POSITION_SIZE_USDC = 100.0
OFFSETS_HOURS = [0, 1, 4, 24]
SLEEP = 12.0  # seconds between GeckoTerminal API calls (429 guard)


def apply_slippage(price: float, side: str = "buy") -> float:
    if side == "buy":
        return price * (1 + SLIPPAGE)
    return price * (1 - SLIPPAGE)


def backtest_signals(signals: list[dict], strategy_name: str) -> dict:
    """Run backtest on a list of signal dicts."""
    print(f"\n{'='*55}")
    print(f"Strategy: {strategy_name}")
    print(f"Signals: {len(signals)}")
    print(f"{'='*55}")

    if not signals:
        return {
            "strategy": strategy_name,
            "signals": 0,
            "trades": [],
            "metrics": {"error": "no signals"},
        }

    trades = []
    token_info_cache = {}

    for i, sig in enumerate(signals):
        token = sig.get("token")
        if not token or token in BASE_TOKENS:
            continue

        signal_ts = sig.get("signal_ts")
        if not signal_ts:
            continue

        # Token info
        if token not in token_info_cache:
            info = get_token_info_dexscreener(token)
            token_info_cache[token] = info
        else:
            info = token_info_cache[token]

        symbol = info.get("symbol", "?")
        print(f"\n  [{i+1}/{len(signals)}] {strategy_name} | {token[:16]}... ({symbol})")

        # Fetch prices
        prices = get_prices_at_offsets(token, signal_ts, offsets_hours=OFFSETS_HOURS)
        entry_price_raw = prices.get(0)

        trade = {
            "strategy": strategy_name,
            "signal_time": sig.get("signal_time"),
            "token": token,
            "symbol": symbol,
            "confidence": sig.get("confidence", "MEDIUM"),
            "entry_price": None,
            "signal_meta": {
                k: v for k, v in sig.items()
                if k not in ("token", "signal_ts", "signal_time")
            },
        }

        if not entry_price_raw:
            trade["note"] = "no price data"
            for h in [1, 4, 24]:
                trade[f"return_pct_{h}h"] = None
            trades.append(trade)
            time.sleep(SLEEP)
            continue

        entry_price = apply_slippage(entry_price_raw, "buy")
        trade["entry_price"] = entry_price
        trade["entry_price_raw"] = entry_price_raw

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

        trades.append(trade)
        time.sleep(SLEEP)

    metrics = summarize_trades(trades)
    return {
        "strategy": strategy_name,
        "signals": len(signals),
        "tradeable": len([t for t in trades if t.get("entry_price")]),
        "trades": trades,
        "metrics": metrics,
        "run_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def run_all():
    """Run Phase 4 backtest for all 5 strategies."""
    results = {}

    # ── SM_11: Volume Anomaly ──────────────────────────────────────────
    try:
        from volume_anomaly import get_backtest_signals_from_known_tokens
        print("\n[Phase4] Running SM_11: Volume Anomaly...")
        signals = get_backtest_signals_from_known_tokens()
        results["SM_11"] = backtest_signals(signals, "SM_11_volume_anomaly")
    except Exception as e:
        print(f"[Phase4] SM_11 error: {e}")
        results["SM_11"] = {"strategy": "SM_11_volume_anomaly", "error": str(e)}

    # ── SM_12: Whale Convergence Enhanced ─────────────────────────────
    try:
        from whale_convergence import get_backtest_signals
        print("\n[Phase4] Running SM_12: Whale Convergence (60min window)...")
        signals = get_backtest_signals()
        results["SM_12"] = backtest_signals(signals, "SM_12_whale_convergence")
    except Exception as e:
        print(f"[Phase4] SM_12 error: {e}")
        results["SM_12"] = {"strategy": "SM_12_whale_convergence", "error": str(e)}

    # ── SM_13: Momentum Divergence ────────────────────────────────────
    try:
        from momentum_divergence import get_backtest_signals
        print("\n[Phase4] Running SM_13: Momentum Divergence...")
        signals = get_backtest_signals()
        results["SM_13"] = backtest_signals(signals, "SM_13_momentum_divergence")
    except Exception as e:
        print(f"[Phase4] SM_13 error: {e}")
        results["SM_13"] = {"strategy": "SM_13_momentum_divergence", "error": str(e)}

    # ── SM_14: Cross-DEX Divergence ───────────────────────────────────
    try:
        from cross_dex_divergence import get_backtest_signals
        print("\n[Phase4] Running SM_14: Cross-DEX Divergence...")
        signals = get_backtest_signals()
        results["SM_14"] = backtest_signals(signals, "SM_14_cross_dex_divergence")
    except Exception as e:
        print(f"[Phase4] SM_14 error: {e}")
        results["SM_14"] = {"strategy": "SM_14_cross_dex_divergence", "error": str(e)}

    # ── SM_15: Sentiment Proxy ────────────────────────────────────────
    try:
        from sentiment_proxy import get_backtest_signals
        print("\n[Phase4] Running SM_15: Sentiment Proxy...")
        signals = get_backtest_signals()
        results["SM_15"] = backtest_signals(signals, "SM_15_sentiment_proxy")
    except Exception as e:
        print(f"[Phase4] SM_15 error: {e}")
        results["SM_15"] = {"strategy": "SM_15_sentiment_proxy", "error": str(e)}

    return results


def generate_report(results: dict) -> str:
    """Generate markdown report from phase 4 results."""
    lines = [
        "# Project Alpha — Phase 4 Backtest Results (SM_11–SM_15)",
        f"\n**Generated:** {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "**Hold horizon:** T+4h  \n**Slippage:** 0.3% per side  \n**Position size:** $100 USDC\n",
        "---\n",
        "## Summary Table\n",
        "| Strategy | Signals | Tradeable | Win Rate | Avg Return | Sharpe | Max DD |",
        "|----------|---------|-----------|----------|------------|--------|--------|",
    ]

    for name, r in results.items():
        if "error" in r and "metrics" not in r:
            lines.append(f"| {name} | ERROR | - | - | - | - | - |")
            continue

        m = r.get("metrics", {})
        h4 = m.get("horizon_4h", {})
        if isinstance(h4, dict) and h4.get("count", 0) > 0:
            wr = f"{h4['win_rate']:.0%}"
            avg = f"{h4['avg_return_pct']:+.2f}%"
            sharpe = f"{h4['sharpe_ratio']:.3f}" if h4.get("sharpe_ratio") else "N/A"
            maxdd = f"{h4['max_drawdown_pct']:.2f}%"
            tradeable = r.get("tradeable", 0)
        else:
            wr = avg = sharpe = maxdd = "N/A"
            tradeable = r.get("tradeable", 0)

        lines.append(
            f"| {name} ({r.get('strategy','').split('_',2)[-1][:20]}) "
            f"| {r.get('signals',0)} | {tradeable} | {wr} | {avg} | {sharpe} | {maxdd} |"
        )

    lines.append("\n---\n")
    lines.append("## Per-Strategy Detail\n")

    for name, r in results.items():
        lines.append(f"### {name}: {r.get('strategy', name)}\n")

        if "error" in r and "metrics" not in r:
            lines.append(f"**ERROR:** {r['error']}\n")
            continue

        m = r.get("metrics", {})
        for horizon, label in [("horizon_1h", "T+1h"), ("horizon_4h", "T+4h"), ("horizon_24h", "T+24h")]:
            h = m.get(horizon, {})
            if isinstance(h, dict) and h.get("count", 0) > 0:
                sharpe_val = h.get("sharpe_ratio")
                sharpe_str = f"{sharpe_val:.3f}" if isinstance(sharpe_val, float) else "N/A"
                lines.append(
                    f"- **{label}:** {h['count']} trades | "
                    f"WR={h['win_rate']:.0%} | avg={h['avg_return_pct']:+.2f}% | "
                    f"Sharpe={sharpe_str}"
                )

        lines.append("")

    lines.append("---\n")
    lines.append("## Go-Live Assessment\n")
    lines.append("| Criterion | Status | Notes |")
    lines.append("|-----------|--------|-------|")
    lines.append("| SM_11 Volume Anomaly | ⚠️ Needs data | Requires 7d+ OHLCV per token |")
    lines.append("| SM_12 Whale Convergence | ⚠️ Testing | Extended 60min window — needs 2wk paper run |")
    lines.append("| SM_13 Momentum Divergence | ⚠️ Needs data | RSI needs OHLCV history |")
    lines.append("| SM_14 Cross-DEX Divergence | ✅ Ready | Can run live, executes on cheaper DEX |")
    lines.append("| SM_15 Sentiment Proxy | ✅ Ready | F&G + SOL momentum — market-level signal |")
    lines.append("| Paper trading | ✅ Built | paper_trader.py — run with --daemon |")
    lines.append("| Execution bot | ❌ Not built | Jupiter buy/sell logic needed |")
    lines.append("| Stop-loss | ✅ In paper trader | 15% stop |")

    lines.append("\n## Recommendations\n")
    lines.append(
        "1. **SM_12 + SM_14 composite**: Signal when whale convergence AND cross-DEX divergence align — highest conviction.\n"
        "2. **SM_15 market filter**: Only trade during F&G < 30 + SOL recovery — reduces false positives in bear markets.\n"
        "3. **SM_11 volume spike** on SM_8 meme_coins wallet buys: layer volume spike confirmation on top of copy signal.\n"
        "4. **Paper trading**: Start `python3 paper_trader.py --daemon` via systemd timer (every 60min).\n"
        "5. **Data gap**: 2-day signal window is too short for statistical validation. Need 2–4 weeks.\n"
        "6. **Next**: Build Jupiter execution bot for SM_14 arb (deterministic, fastest path to profit).\n"
    )

    return "\n".join(lines)


if __name__ == "__main__":
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"\n{'='*60}")
    print("PROJECT ALPHA — PHASE 4 BACKTEST")
    print(f"Started: {datetime.now(tz=timezone.utc).isoformat()}")
    print(f"{'='*60}")

    results = run_all()

    # Save JSON
    json_path = os.path.join(RESULTS_DIR, "phase4_results.json")
    # Strip trades for summary (trades list can be large)
    summary = {k: {**v, "trades": len(v.get("trades", []))} for k, v in results.items()}
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {json_path}")

    # Save report
    report = generate_report(results)
    report_path = os.path.join(RESULTS_DIR, "phase4_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"Report saved: {report_path}")

    # Print report to stdout
    print("\n" + "="*60)
    print(report)

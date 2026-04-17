"""
Main entry point for Alpha backtesting.
Runs all strategies and saves consolidated results.

Usage:
    python3 run_backtest.py [--strategy convergence|single|all] [--wallet SM_8]
"""

import sys
import os
import json
import argparse
from datetime import datetime, timezone

# Add backtest dir to path
sys.path.insert(0, os.path.dirname(__file__))

from backtest_engine import run_convergence_backtest, run_single_wallet_backtest
from signal_parser import extract_convergence_signals, extract_medium_signals

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def print_summary(result: dict) -> None:
    """Print human-readable summary of backtest results."""
    print(f"\n{'='*60}")
    print(f"RESULTS: {result['strategy']}")
    if result.get('wallet_filter'):
        print(f"Wallet: {result['wallet_filter']}")
    print("="*60)

    metrics = result.get("metrics", {})
    total = metrics.get("total_signals", 0)
    with_data = metrics.get("signals_with_price_data", 0)
    print(f"Total signals: {total} | With price data: {with_data}")

    for label in ["1h", "4h", "24h"]:
        h = metrics.get(f"horizon_{label}")
        if not h or h.get("count", 0) == 0:
            print(f"\n  T+{label}: no data")
            continue

        wr = h.get("win_rate", 0)
        avg = h.get("avg_return_pct", 0)
        sharpe = h.get("sharpe_ratio")
        mdd = h.get("max_drawdown_pct", 0)
        pf = h.get("profit_factor")

        print(f"\n  T+{label} ({h['count']} trades):")
        print(f"    Win rate:      {wr:.1%}  ({h['wins']}W/{h['losses']}L)")
        print(f"    Avg return:    {avg:+.2f}%")
        print(f"    Median return: {h.get('median_return_pct', 0):+.2f}%")
        print(f"    Best/Worst:    {h.get('max_return_pct', 0):+.2f}% / {h.get('min_return_pct', 0):+.2f}%")
        print(f"    Sharpe ratio:  {sharpe:.3f}" if sharpe else f"    Sharpe ratio:  N/A")
        print(f"    Max drawdown:  {mdd:.2f}%")
        print(f"    Profit factor: {pf:.2f}" if pf else f"    Profit factor: N/A")

    print()


def main():
    parser = argparse.ArgumentParser(description="Alpha Backtesting")
    parser.add_argument("--strategy", choices=["convergence", "single", "all"], default="convergence")
    parser.add_argument("--wallet", type=str, default=None, help="Wallet label filter for single strategy")
    parser.add_argument("--min-wallets", type=int, default=2, help="Min wallets for convergence")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_results = []

    if args.strategy in ("convergence", "all"):
        print("\nRunning CONVERGENCE backtest...")
        result = run_convergence_backtest(min_wallets=args.min_wallets)
        out = os.path.join(RESULTS_DIR, "convergence_backtest.json")
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved: {out}")
        print_summary(result)
        all_results.append(result)

    if args.strategy in ("single", "all"):
        print("\nRunning SINGLE WALLET backtest (SM_8 — meme hunter)...")
        result = run_single_wallet_backtest(wallet_label=args.wallet or "SM_8")
        out = os.path.join(RESULTS_DIR, "single_wallet_backtest.json")
        with open(out, "w") as f:
            json.dump(result, f, indent=2)
        print(f"Saved: {out}")
        print_summary(result)
        all_results.append(result)

    # Consolidated summary
    if len(all_results) > 1:
        summary = {
            "run_at": datetime.now(tz=timezone.utc).isoformat(),
            "strategies_run": [r["strategy"] for r in all_results],
            "results": {r["strategy"]: r["metrics"] for r in all_results},
        }
        out = os.path.join(RESULTS_DIR, "summary.json")
        with open(out, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nConsolidated summary saved: {out}")

    print("\nDone.")


if __name__ == "__main__":
    main()

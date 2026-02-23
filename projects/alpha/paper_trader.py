"""
Alpha Paper Trading Framework

Simulates live trade execution without real funds.
Logs would-be trades to ~/otto/projects/alpha/paper_trades.jsonl and
to a PostgreSQL table (paper_trades) via the Memory API.

Usage:
  python3 paper_trader.py --run-once   # Single scan cycle
  python3 paper_trader.py --daemon     # Continuous loop (60s intervals)
  python3 paper_trader.py --report     # P&L report on open/closed positions
  python3 paper_trader.py --close-all  # Mark all open positions as closed at current price

Configuration:
  POSITION_SIZE_USDC = $50 per signal (conservative paper trading)
  STOP_LOSS_PCT = 8% (tighter: cut losses fast)
  TAKE_PROFIT_PCT = 20% (achievable for meme tokens in 2h)
  HOLD_HORIZON_HOURS = 2 (meme pumps resolve in 15-60min)
"""

import os
import sys
import json
import time
import argparse
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backtest'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'signals'))

from data_fetcher import (
    get_solana_pool_for_token,
    fetch_ohlcv_geckoterminal,
    get_token_info_dexscreener,
    BASE_TOKENS,
)

# ── Config ──────────────────────────────────────────────────────────────────
POSITION_SIZE_USDC = 50.0
SLIPPAGE = 0.003        # 0.3% per side
STOP_LOSS_PCT = 0.06    # -6% (tightened from 8% — meme dumps are sharp, exit sooner)
TAKE_PROFIT_PCT = 0.20  # +20% (achievable for meme tokens in 2h window)
HOLD_HORIZON_HOURS = 2  # 2h (meme pumps resolve in 15-60min; 4h was riding the dump)

# Token tier config: meme/small-cap only for paper trading
# Large-cap tokens (BTC wraps, major DeFi protocols) are stable — +25% in 4h is unrealistic
# Tokens priced above this threshold are classified as large-cap and skipped
LARGE_CAP_PRICE_THRESHOLD = 50.0      # Skip tokens priced >$50 (cbBTC, wrapped BTC, etc.)
HIGH_LIQUIDITY_THRESHOLD = 20_000_000  # Skip tokens with >$20M liquidity (too stable)

PAPER_TRADES_PATH = os.path.join(os.path.dirname(__file__), "paper_trades.jsonl")
MEMORY_API = "http://localhost:8100"

# ── Signal-timestamp dedup (daemon mode) ─────────────────────────────────────
# FIX: was an in-memory dict that was wiped on every restart, allowing the same signal
# event to reopen a position after a restart. Now file-backed for cross-restart persistence.
_SIGNAL_TS_DEDUP_HOURS = 4.0  # Matches hold horizon + buffer
_PROCESSED_SIGNALS_PATH = os.path.join(os.path.dirname(__file__), "processed_signals.jsonl")


def _load_processed_signals() -> dict[str, float]:
    """Load processed signal keys from disk into an in-memory dict."""
    result: dict[str, float] = {}
    if not os.path.exists(_PROCESSED_SIGNALS_PATH):
        return result
    cutoff = time.time() - _SIGNAL_TS_DEDUP_HOURS * 3600
    try:
        with open(_PROCESSED_SIGNALS_PATH) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    key, ts = rec.get("key"), rec.get("ts")
                    if key and ts and ts >= cutoff:
                        result[key] = ts
                except Exception:
                    pass
    except OSError:
        pass
    return result


def _append_processed_signal(key: str, ts: float):
    """Append a processed signal to the persistent log."""
    try:
        with open(_PROCESSED_SIGNALS_PATH, "a") as f:
            f.write(json.dumps({"key": key, "ts": ts}) + "\n")
    except OSError:
        pass


# In-memory cache — hydrated from disk on first access
_PROCESSED_SIGNALS: dict[str, float] = {}
_PROCESSED_SIGNALS_LOADED = False


# ── Persistence ─────────────────────────────────────────────────────────────

def load_paper_trades() -> list[dict]:
    """Load all paper trades from the JSONL log."""
    trades = []
    if not os.path.exists(PAPER_TRADES_PATH):
        return trades
    with open(PAPER_TRADES_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    trades.append(json.loads(line))
                except Exception:
                    pass
    return trades


def save_paper_trade(trade: dict):
    """Append a trade to the JSONL log."""
    with open(PAPER_TRADES_PATH, "a") as f:
        f.write(json.dumps(trade) + "\n")


def update_paper_trade(trade_id: str, updates: dict):
    """Update an existing trade by rewriting the JSONL file."""
    trades = load_paper_trades()
    with open(PAPER_TRADES_PATH, "w") as f:
        for t in trades:
            if t.get("trade_id") == trade_id:
                t.update(updates)
            f.write(json.dumps(t) + "\n")


def log_to_memory(trade: dict, event_type: str = "paper_trade"):
    """Log trade event to Otto's episodic memory."""
    try:
        payload = {
            "event_type": event_type,
            "content": json.dumps(trade),
            "importance": 5,
            "metadata": {"source": "paper_trader", "signal": trade.get("signal_name")},
        }
        httpx.post(f"{MEMORY_API}/episodic/events", json=payload, timeout=5)
    except Exception:
        pass  # Non-critical


# ── Price fetching ───────────────────────────────────────────────────────────

def get_current_price(token_address: str) -> Optional[float]:
    """Get current token price from DexScreener."""
    try:
        info = get_token_info_dexscreener(token_address)
        price_str = info.get("price_usd") or info.get("priceUsd")
        if price_str:
            return float(price_str)

        # Fallback: GeckoTerminal OHLCV latest candle
        pool = get_solana_pool_for_token(token_address)
        if pool:
            candles = fetch_ohlcv_geckoterminal(pool, timeframe="minute", limit=5)
            if candles:
                return candles[-1].get("close")
    except Exception as e:
        print(f"  [price] Error for {token_address[:12]}: {e}")
    return None


# ── Trade lifecycle ──────────────────────────────────────────────────────────

def is_recently_traded(token: str, minutes: int = 5) -> bool:
    """
    Check if a trade for this token is currently open or was opened in last N minutes.

    BUG FIX: Now also blocks any currently OPEN position for this token (regardless
    of age). The old 5-minute window was too short — positions hold for 2h, then the
    same token could be re-entered immediately. Callers pass minutes=HOLD_HORIZON_HOURS*60
    to cover the full hold window.
    """
    trades = load_paper_trades()
    cutoff_ts = int((datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)).timestamp())
    for t in trades:
        if t.get("token") != token:
            continue
        # Always block if currently open (regardless of when it was opened)
        if t.get("status") == "open":
            return True
        # Block if opened within the dedup window (handles concurrent scan races)
        if t.get("opened_ts", 0) >= cutoff_ts:
            return True
    return False


def _signal_key(signal: dict) -> str:
    """Build a dedup key from signal token + event timestamp bucket."""
    token = signal.get("token", "")
    # ts_bucket from live_watcher (5-min rounded epoch) is ideal.
    # For SM_11-SM_15 signals without ts_bucket, round current time to nearest hour
    # so re-runs within the same hour are collapsed but the key rotates out naturally.
    ts = signal.get("ts_bucket") or signal.get("ts") or 0
    if not ts:
        ts = int(time.time() // 3600) * 3600  # nearest hour
    sig_name = signal.get("signal_name", signal.get("signal", ""))
    return f"{token}:{ts}:{sig_name}"


def is_signal_processed(signal: dict) -> bool:
    """Return True if we have already opened a trade for this signal event."""
    global _PROCESSED_SIGNALS, _PROCESSED_SIGNALS_LOADED
    if not _PROCESSED_SIGNALS_LOADED:
        _PROCESSED_SIGNALS = _load_processed_signals()
        _PROCESSED_SIGNALS_LOADED = True

    now = time.time()
    cutoff = now - _SIGNAL_TS_DEDUP_HOURS * 3600
    # Prune expired entries from in-memory cache
    expired = [k for k, added in _PROCESSED_SIGNALS.items() if added < cutoff]
    for k in expired:
        del _PROCESSED_SIGNALS[k]
    return _signal_key(signal) in _PROCESSED_SIGNALS


def mark_signal_processed(signal: dict):
    """Record that we acted on this signal event — persisted to disk."""
    global _PROCESSED_SIGNALS, _PROCESSED_SIGNALS_LOADED
    if not _PROCESSED_SIGNALS_LOADED:
        _PROCESSED_SIGNALS = _load_processed_signals()
        _PROCESSED_SIGNALS_LOADED = True

    key = _signal_key(signal)
    ts = time.time()
    _PROCESSED_SIGNALS[key] = ts
    _append_processed_signal(key, ts)


def open_position(signal: dict) -> Optional[dict]:
    """
    Simulate opening a position on a signal.
    Returns the paper trade record, or None if price unavailable.
    """
    token = signal.get("token")
    if not token or token in BASE_TOKENS:
        return None

    # Dedup fix: skip if same token is currently open OR was traded in last HOLD_HORIZON_HOURS
    # BUG FIX: 5-minute window was too short — positions run 2h, same token was re-entered
    if is_recently_traded(token, minutes=int(HOLD_HORIZON_HOURS * 60)):
        print(f"  [paper] Skipping {token[:12]}: already open or traded in last {HOLD_HORIZON_HOURS}h (dedup)")
        return None

    # Signal-ts dedup: same underlying event (ts_bucket) should never reopen after close.
    # Without this, SM_11-SM_15 lookback windows return the same buy events every 60s cycle,
    # allowing re-entry as soon as the 2h token dedup window expires.
    if is_signal_processed(signal):
        print(f"  [paper] Skipping {token[:12]}: signal event already processed (ts dedup)")
        return None

    entry_price_raw = signal.get("entry_price") or get_current_price(token)
    if not entry_price_raw or entry_price_raw <= 0:
        print(f"  [paper] Cannot open {token[:12]}: no price")
        return None

    # Price-based stablecoin safety filter — skip anything pegged to ~$1
    if 0.90 <= entry_price_raw <= 1.10:
        print(f"  [paper] Skipping {token[:12]}: price ${entry_price_raw:.4f} looks like a stablecoin")
        return None

    # Large-cap filter — tokens >$50 are BTC/ETH wrappers or major DeFi assets
    # These cannot realistically hit +25% TP in 4h window
    if entry_price_raw > LARGE_CAP_PRICE_THRESHOLD:
        print(f"  [paper] Skipping {token[:12]}: price ${entry_price_raw:.2f} > ${LARGE_CAP_PRICE_THRESHOLD} (large-cap, low volatility)")
        return None

    # Liquidity filter from signal metadata — skip over-liquid tokens (too stable)
    liq = signal.get("liquidity_usd") or 0
    if liq and liq > HIGH_LIQUIDITY_THRESHOLD:
        print(f"  [paper] Skipping {token[:12]}: liquidity ${liq:,.0f} > ${HIGH_LIQUIDITY_THRESHOLD:,.0f} (too stable for 25% TP)")
        return None

    entry_price = entry_price_raw * (1 + SLIPPAGE)
    units = POSITION_SIZE_USDC / entry_price
    now = datetime.now(tz=timezone.utc)
    trade_id = f"PT_{int(now.timestamp())}_{token[:8]}"

    trade = {
        "trade_id": trade_id,
        "signal_name": signal.get("signal_name", "unknown"),
        "token": token,
        "opened_at": now.isoformat(),
        "opened_ts": int(now.timestamp()),
        "entry_price": entry_price,
        "entry_price_raw": entry_price_raw,
        "units": units,
        "position_size_usdc": POSITION_SIZE_USDC,
        "stop_loss_price": entry_price * (1 - STOP_LOSS_PCT),
        "take_profit_price": entry_price * (1 + TAKE_PROFIT_PCT),
        "close_at_ts": int((now + timedelta(hours=HOLD_HORIZON_HOURS)).timestamp()),
        "status": "open",
        "exit_reason": None,
        "exit_price": None,
        "closed_at": None,
        "pnl_usdc": None,
        "pnl_pct": None,
        "signal_meta": {
            k: v for k, v in signal.items()
            if k not in ("token",)
        },
    }

    save_paper_trade(trade)
    mark_signal_processed(signal)  # Prevent this signal event from reopening after position closes
    log_to_memory(trade, "paper_trade_open")
    print(
        f"  [paper] OPENED {trade_id} | {token[:16]} | "
        f"entry=${entry_price:.8f} | size=${POSITION_SIZE_USDC}"
    )
    return trade


def close_position(trade: dict, current_price: float, reason: str) -> dict:
    """Simulate closing a position."""
    exit_price = current_price * (1 - SLIPPAGE)
    pnl_pct = (exit_price - trade["entry_price"]) / trade["entry_price"] * 100
    pnl_usdc = pnl_pct / 100 * POSITION_SIZE_USDC

    now = datetime.now(tz=timezone.utc)
    updates = {
        "status": "closed",
        "exit_reason": reason,
        "exit_price": exit_price,
        "closed_at": now.isoformat(),
        "pnl_usdc": round(pnl_usdc, 4),
        "pnl_pct": round(pnl_pct, 4),
    }

    update_paper_trade(trade["trade_id"], updates)
    closed_trade = {**trade, **updates}
    log_to_memory(closed_trade, "paper_trade_close")

    emoji = "✓" if pnl_usdc >= 0 else "✗"
    print(
        f"  [paper] {emoji} CLOSED {trade['trade_id']} | "
        f"exit=${exit_price:.8f} | P&L: {pnl_pct:+.2f}% (${pnl_usdc:+.2f}) | {reason}"
    )
    return closed_trade


def monitor_open_positions():
    """Check all open positions — apply stop/take-profit/time exits."""
    trades = load_paper_trades()
    open_trades = [t for t in trades if t.get("status") == "open"]

    if not open_trades:
        print("[paper] No open positions.")
        return

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    print(f"[paper] Monitoring {len(open_trades)} open positions...")

    for trade in open_trades:
        token = trade["token"]

        # BUG FIX 3: Retry price fetch 3x with 2s backoff to avoid 0% P&L false entries
        current_price = None
        for attempt in range(3):
            current_price = get_current_price(token)
            if current_price:
                break
            if attempt < 2:
                time.sleep(2)

        if not current_price:
            print(f"  [paper] Cannot price {token[:12]} after 3 attempts — skipping close")
            continue

        # Stop loss
        if current_price <= trade["stop_loss_price"]:
            close_position(trade, current_price, "stop_loss")
            continue

        # Take profit
        if current_price >= trade["take_profit_price"]:
            close_position(trade, current_price, "take_profit")
            continue

        # Time expiry
        if now_ts >= trade["close_at_ts"]:
            close_position(trade, current_price, f"time_exit_{HOLD_HORIZON_HOURS}h")
            continue

        # Still open — log current unrealized P&L
        unr_pct = (current_price - trade["entry_price"]) / trade["entry_price"] * 100
        hours_open = (now_ts - trade["opened_ts"]) / 3600
        print(
            f"  [paper] OPEN {trade['trade_id'][:20]} | "
            f"cur=${current_price:.8f} | unr={unr_pct:+.2f}% | "
            f"{hours_open:.1f}h open"
        )
        time.sleep(0.3)


# ── Reporting ────────────────────────────────────────────────────────────────

def generate_report() -> dict:
    """Generate P&L report on all paper trades."""
    trades = load_paper_trades()
    closed = [t for t in trades if t.get("status") == "closed"]
    open_t = [t for t in trades if t.get("status") == "open"]

    print(f"\n{'='*60}")
    print("PAPER TRADING P&L REPORT")
    print(f"Generated: {datetime.now(tz=timezone.utc).isoformat()}")
    print(f"{'='*60}")
    print(f"Total trades: {len(trades)} ({len(open_t)} open, {len(closed)} closed)")

    if not closed:
        print("No closed trades yet.")
        return {"total": len(trades), "open": len(open_t), "closed": 0}

    pnls = [t["pnl_pct"] for t in closed if t.get("pnl_pct") is not None]
    pnl_usdc = [t["pnl_usdc"] for t in closed if t.get("pnl_usdc") is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    total_pnl_usdc = sum(pnl_usdc)
    avg_pnl_pct = sum(pnls) / len(pnls) if pnls else 0
    win_rate = len(wins) / len(pnls) if pnls else 0

    # Sharpe ratio (using per-trade returns)
    sharpe = None
    if len(pnls) >= 2:
        import math
        mean = avg_pnl_pct
        variance = sum((p - mean) ** 2 for p in pnls) / (len(pnls) - 1)
        if variance > 0:
            sharpe = mean / math.sqrt(variance)

    # By signal
    by_signal: dict[str, list[float]] = {}
    for t in closed:
        sig = t.get("signal_name", "unknown")
        if sig not in by_signal:
            by_signal[sig] = []
        if t.get("pnl_pct") is not None:
            by_signal[sig].append(t["pnl_pct"])

    # Exit reasons
    by_exit: dict[str, int] = {}
    for t in closed:
        reason = t.get("exit_reason", "unknown")
        by_exit[reason] = by_exit.get(reason, 0) + 1

    print(f"\n── Overall ─────────────────────────────")
    print(f"Win rate:        {win_rate:.1%} ({len(wins)}W / {len(losses)}L)")
    print(f"Avg return:      {avg_pnl_pct:+.2f}%")
    print(f"Total P&L:       ${total_pnl_usdc:+.2f} USDC")
    print(f"Sharpe ratio:    {sharpe:.3f}" if sharpe else "Sharpe ratio:    N/A")

    print(f"\n── By Signal ───────────────────────────")
    for sig, returns in sorted(by_signal.items()):
        avg = sum(returns) / len(returns) if returns else 0
        w = len([r for r in returns if r > 0])
        print(f"  {sig:30s} | {len(returns)} trades | avg {avg:+.2f}% | {w}/{len(returns)} wins")

    print(f"\n── Exit Reasons ────────────────────────")
    for reason, count in sorted(by_exit.items()):
        print(f"  {reason:20s}: {count}")

    print(f"\n── Recent Closed Trades ────────────────")
    for t in sorted(closed, key=lambda x: x.get("closed_at", ""))[-10:]:
        print(
            f"  {t.get('closed_at','')[:16]} | {t.get('signal_name','')[:20]:20s} | "
            f"{t.get('pnl_pct', 0):+6.2f}% | {t.get('exit_reason','')}"
        )

    return {
        "total": len(trades),
        "open": len(open_t),
        "closed": len(closed),
        "win_rate": win_rate,
        "avg_return_pct": avg_pnl_pct,
        "total_pnl_usdc": total_pnl_usdc,
        "sharpe": sharpe,
        "by_signal": {s: {"count": len(r), "avg_pct": sum(r)/len(r) if r else 0} for s, r in by_signal.items()},
    }


# ── Scanner integration ──────────────────────────────────────────────────────

def run_signal_scan():
    """Run all SM_11-SM_15 signal generators and open positions on new signals."""
    print(f"\n[paper] Signal scan @ {datetime.now(tz=timezone.utc).isoformat()}")

    # Load existing open positions to avoid re-opening same token
    open_trades = [t for t in load_paper_trades() if t.get("status") == "open"]
    open_tokens = {t["token"] for t in open_trades}

    all_signals = []

    # SM_11: Volume anomaly
    try:
        from volume_anomaly import get_backtest_signals_from_known_tokens
        sigs = get_backtest_signals_from_known_tokens()
        all_signals.extend(sigs)
        print(f"  [SM_11] {len(sigs)} volume anomaly signals")
    except Exception as e:
        print(f"  [SM_11] Error: {e}")

    # SM_12: Whale convergence
    try:
        from whale_convergence import get_backtest_signals
        sigs = get_backtest_signals()
        all_signals.extend(sigs)
        print(f"  [SM_12] {len(sigs)} whale convergence signals")
    except Exception as e:
        print(f"  [SM_12] Error: {e}")

    # SM_13: Momentum divergence
    try:
        from momentum_divergence import get_backtest_signals
        sigs = get_backtest_signals()
        all_signals.extend(sigs)
        print(f"  [SM_13] {len(sigs)} momentum divergence signals")
    except Exception as e:
        print(f"  [SM_13] Error: {e}")

    # SM_14: Cross-DEX divergence
    try:
        from cross_dex_divergence import get_backtest_signals
        sigs = get_backtest_signals()
        all_signals.extend(sigs)
        print(f"  [SM_14] {len(sigs)} cross-DEX divergence signals")
    except Exception as e:
        print(f"  [SM_14] Error: {e}")

    # SM_15: Sentiment proxy
    try:
        from sentiment_proxy import get_backtest_signals
        sigs = get_backtest_signals()
        all_signals.extend(sigs)
        print(f"  [SM_15] {len(sigs)} sentiment signals")
    except Exception as e:
        print(f"  [SM_15] Error: {e}")

    # Filter: HIGH or ULTRA confidence only (MIN_WALLETS=3+), new tokens
    high_confidence = [
        s for s in all_signals
        if s.get("confidence") in ("HIGH", "ULTRA") and s.get("token") not in open_tokens
    ]
    print(f"\n[paper] {len(high_confidence)} HIGH/ULTRA-confidence new signals → opening positions")

    opened = 0
    for sig in high_confidence[:5]:  # Max 5 new positions per cycle
        if sig["token"] in open_tokens:
            continue  # Already opened this token in this cycle
        trade = open_position(sig)
        if trade:
            open_tokens.add(sig["token"])
            opened += 1

    print(f"[paper] Opened {opened} paper positions.")
    return opened


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Alpha Paper Trader")
    parser.add_argument("--run-once", action="store_true", help="Single scan + monitor cycle")
    parser.add_argument("--daemon", action="store_true", help="Continuous loop (60s)")
    parser.add_argument("--monitor", action="store_true", help="Monitor open positions")
    parser.add_argument("--report", action="store_true", help="Generate P&L report")
    parser.add_argument("--close-all", action="store_true", help="Force-close all open positions")
    args = parser.parse_args()

    if args.report:
        generate_report()
        return

    if args.monitor:
        monitor_open_positions()
        return

    if args.close_all:
        trades = load_paper_trades()
        open_trades = [t for t in trades if t.get("status") == "open"]
        print(f"Force-closing {len(open_trades)} positions...")
        for trade in open_trades:
            price = get_current_price(trade["token"])
            if price:
                close_position(trade, price, "manual_close")
            else:
                print(f"  Cannot price {trade['token'][:12]}")
        return

    if args.run_once:
        monitor_open_positions()
        run_signal_scan()
        generate_report()
        return

    if args.daemon:
        print("[paper] Starting daemon mode (60s interval)...")
        while True:
            monitor_open_positions()
            run_signal_scan()
            print(f"[paper] Sleeping 60s...")
            time.sleep(60)
        return

    # Default: run once
    monitor_open_positions()
    run_signal_scan()
    generate_report()


if __name__ == "__main__":
    main()

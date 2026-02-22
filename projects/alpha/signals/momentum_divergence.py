"""
SM_13: Momentum Divergence (RSI vs Price)

Signal: RSI oversold (< 35) while price has been falling for 3+ candles,
then price makes a higher low (reversal setup). Classic RSI divergence.

Bullish divergence: price makes lower low, RSI makes higher low → likely reversal up.
Also signals simple RSI < 30 oversold conditions on tokens with volume > $10k.

Uses GeckoTerminal OHLCV.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backtest'))

import time
import json
from datetime import datetime, timezone
from data_fetcher import get_solana_pool_for_token, fetch_ohlcv_geckoterminal, BASE_TOKENS

SIGNAL_NAME = "SM_13_momentum_divergence"
RSI_PERIOD = 14
RSI_OVERSOLD = 35
RSI_OVERBOUGHT = 65
MIN_VOLUME_USD = 10000


def calculate_rsi(closes: list[float], period: int = RSI_PERIOD) -> list[float]:
    """Calculate RSI for a series of closing prices."""
    if len(closes) < period + 1:
        return []

    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    rsi_values = []
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        if avg_loss == 0:
            rsi_values.append(100.0)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    return rsi_values


def detect_bullish_divergence(candles: list[dict]) -> list[dict]:
    """
    Detect RSI bullish divergence and simple oversold conditions.
    Signals:
      1. RSI < RSI_OVERSOLD (simple oversold)
      2. Price lower low + RSI higher low (divergence)
    """
    if len(candles) < RSI_PERIOD + 5:
        return []

    closes = [c.get("close", 0) for c in candles]
    volumes = [c.get("volume", 0) for c in candles]
    rsi_values = calculate_rsi(closes)

    if not rsi_values:
        return []

    # Align RSI with candles (RSI starts at index RSI_PERIOD)
    offset = len(closes) - len(rsi_values)
    signals = []
    seen_ts = set()

    for i in range(2, len(rsi_values)):
        candle_idx = i + offset
        candle = candles[candle_idx]
        rsi = rsi_values[i]
        volume = volumes[candle_idx]

        if volume < MIN_VOLUME_USD:
            continue

        ts = candle.get("timestamp", 0)

        # Signal type 1: Simple RSI oversold
        if rsi < RSI_OVERSOLD and ts not in seen_ts:
            seen_ts.add(ts)
            signals.append({
                "signal_name": SIGNAL_NAME,
                "signal_type": "rsi_oversold",
                "signal_ts": ts,
                "signal_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "rsi": round(rsi, 2),
                "close_price": closes[candle_idx],
                "volume_usd": volume,
                "confidence": "HIGH" if rsi < 25 else "MEDIUM",
            })
            continue

        # Signal type 2: Bullish divergence (price lower low, RSI higher low)
        prev_rsi = rsi_values[i - 1]
        prev_prev_rsi = rsi_values[i - 2]
        prev_close = closes[candle_idx - 1]
        prev_prev_close = closes[candle_idx - 2]

        # Price: lower low (close[i] < close[i-1] < close[i-2])
        # RSI: higher low (rsi[i] > rsi[i-1] but rsi[i] < rsi[i-2])
        price_lower_low = closes[candle_idx] < prev_close < prev_prev_close
        rsi_higher_low = rsi > prev_rsi and prev_rsi < prev_prev_rsi

        if price_lower_low and rsi_higher_low and ts not in seen_ts:
            seen_ts.add(ts)
            signals.append({
                "signal_name": SIGNAL_NAME,
                "signal_type": "bullish_divergence",
                "signal_ts": ts,
                "signal_time": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
                "rsi": round(rsi, 2),
                "close_price": closes[candle_idx],
                "volume_usd": volume,
                "confidence": "HIGH" if rsi < RSI_OVERSOLD else "MEDIUM",
            })

    return signals


def get_backtest_signals(token_addresses: list[str] = None, sleep: float = 12.0) -> list[dict]:  # 429 guard: 12s between GeckoTerminal calls
    """Backtest entry point: scan known tokens for momentum divergence."""
    if token_addresses is None:
        signals_path = os.path.join(os.path.dirname(__file__), '..', 'signals.jsonl')
        token_addresses = set()
        with open(signals_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    t = r.get("token", "")
                    if t and len(t) > 20 and t not in BASE_TOKENS:
                        token_addresses.add(t)
                except Exception:
                    pass
        token_addresses = list(token_addresses)

    all_signals = []
    print(f"[SM_13] Scanning {len(token_addresses)} tokens for momentum divergence...")

    for token in token_addresses:
        pool = get_solana_pool_for_token(token)
        if not pool:
            continue
        candles = fetch_ohlcv_geckoterminal(pool, timeframe="hour", limit=168)
        if not candles:
            continue
        sigs = detect_bullish_divergence(candles)
        for s in sigs:
            s["token"] = token
        all_signals.extend(sigs)
        time.sleep(sleep)

    return all_signals


if __name__ == "__main__":
    signals = get_backtest_signals()
    print(f"\nSM_13 Momentum Divergence signals: {len(signals)}")
    for s in signals[:5]:
        print(f"  {s['signal_time']} | type={s['signal_type']} | RSI={s['rsi']} | conf={s['confidence']}")

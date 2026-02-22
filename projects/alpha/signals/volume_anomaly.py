"""
SM_11: Volume Anomaly Detection

Signals when a token's trading volume spikes >3x its rolling 24h average.
Uses GeckoTerminal OHLCV data.
Strategy: Volume spike often precedes price movement — enter early on the spike,
exit at T+4h before the volume fade.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backtest'))

import httpx
import time
from datetime import datetime, timezone
from typing import Optional
from data_fetcher import get_solana_pool_for_token, fetch_ohlcv_geckoterminal, BASE_TOKENS

SIGNAL_NAME = "SM_11_volume_anomaly"
VOLUME_SPIKE_THRESHOLD = 3.0   # Signal when vol > 3x rolling avg
ROLLING_WINDOW_HOURS = 24
MIN_VOLUME_USD = 5000           # Ignore micro-cap noise


def detect_volume_anomaly(token_address: str, candles: list[dict]) -> list[dict]:
    """
    Scan OHLCV candles for volume anomaly events.
    Returns list of signal dicts with the candle timestamp where spike occurred.
    """
    if len(candles) < ROLLING_WINDOW_HOURS + 1:
        return []

    signals = []
    for i in range(ROLLING_WINDOW_HOURS, len(candles)):
        current = candles[i]
        window = candles[i - ROLLING_WINDOW_HOURS:i]
        avg_volume = sum(c.get("volume", 0) for c in window) / len(window)

        if avg_volume < MIN_VOLUME_USD:
            continue

        current_vol = current.get("volume", 0)
        if current_vol >= avg_volume * VOLUME_SPIKE_THRESHOLD:
            ratio = current_vol / avg_volume
            signals.append({
                "signal_name": SIGNAL_NAME,
                "token": token_address,
                "signal_ts": current.get("timestamp"),
                "signal_time": datetime.fromtimestamp(
                    current.get("timestamp", 0), tz=timezone.utc
                ).isoformat(),
                "volume_usd": current_vol,
                "avg_volume_usd": avg_volume,
                "volume_ratio": ratio,
                "close_price": current.get("close"),
                "confidence": "HIGH" if ratio > 5.0 else "MEDIUM",
            })

    return signals


def scan_tokens_for_volume_anomalies(
    token_addresses: list[str],
    sleep: float = 12.0,  # 429 guard: 12s between GeckoTerminal calls
) -> list[dict]:
    """Scan a list of tokens for volume anomaly signals."""
    all_signals = []

    for token in token_addresses:
        if token in BASE_TOKENS:
            continue
        pool = get_solana_pool_for_token(token)
        if not pool:
            continue
        candles = fetch_ohlcv_geckoterminal(pool, timeframe="hour", limit=168)  # 7 days
        if not candles:
            continue
        sigs = detect_volume_anomaly(token, candles)
        all_signals.extend(sigs)
        time.sleep(sleep)

    return all_signals


def get_backtest_signals_from_known_tokens() -> list[dict]:
    """
    Backtest entry point: scan tokens already in signals.jsonl for volume anomalies.
    Returns signals compatible with the backtest engine format.
    """
    import json
    signals_path = os.path.join(os.path.dirname(__file__), '..', 'signals.jsonl')
    tokens = set()
    with open(signals_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                t = r.get("token", "")
                if t and len(t) > 20 and t not in BASE_TOKENS:
                    tokens.add(t)
            except Exception:
                pass

    print(f"[SM_11] Scanning {len(tokens)} known tokens for volume anomalies...")
    return scan_tokens_for_volume_anomalies(list(tokens))


if __name__ == "__main__":
    signals = get_backtest_signals_from_known_tokens()
    print(f"\nSM_11 Volume Anomaly signals found: {len(signals)}")
    for s in signals[:5]:
        print(f"  {s['signal_time']} | ratio={s['volume_ratio']:.1f}x | conf={s['confidence']}")

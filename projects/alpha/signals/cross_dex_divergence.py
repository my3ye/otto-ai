"""
SM_14: Cross-DEX Price Divergence

Signal: Same token trades at >2% price difference across Solana DEXes
(e.g., Raydium vs Orca vs Meteora). This creates an arbitrage-like opportunity —
price tends to converge, and the cheaper side often pumps toward the pricier side.

Uses DexScreener pairs data to find multi-pool tokens.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backtest'))

import httpx
import time
import json
from datetime import datetime, timezone
from data_fetcher import DEXSCREENER_BASE, BASE_TOKENS

SIGNAL_NAME = "SM_14_cross_dex_divergence"
MIN_DIVERGENCE_PCT = 2.0    # Minimum price difference to signal
MAX_DIVERGENCE_PCT = 50.0   # Anything > 50% is likely stale price / denomination error
MIN_LIQUIDITY_USD = 5000    # Ignore illiquid pools
MIN_POOL_COUNT = 2          # Need at least 2 pools

# Preferred Solana DEXes (excluding low-quality aggregators)
PREFERRED_DEXES = {
    "raydium", "orca", "meteora", "openbook", "lifinity",
    "aldrin", "saber", "mercurial", "pump_fun"
}


def get_token_pools(token_address: str, timeout: int = 10) -> list[dict]:
    """Fetch all Solana pools for a token from DexScreener."""
    try:
        url = f"{DEXSCREENER_BASE}/latest/dex/tokens/{token_address}"
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()

        pairs = data.get("pairs") or []
        sol_pairs = [
            p for p in pairs
            if p.get("chainId") == "solana"
            and (p.get("liquidity", {}).get("usd") or 0) >= MIN_LIQUIDITY_USD
        ]
        return sol_pairs

    except Exception as e:
        print(f"  [DexScreener] Error for {token_address[:12]}: {e}")
        return []


def detect_divergence(token_address: str, pools: list[dict]) -> list[dict]:
    """
    Find price divergence across pools for a single token.
    Returns signal dict if divergence > MIN_DIVERGENCE_PCT.
    """
    if len(pools) < MIN_POOL_COUNT:
        return []

    # Extract prices from each pool
    priced_pools = []
    for p in pools:
        price_str = p.get("priceUsd") or p.get("priceNative")
        try:
            price = float(price_str) if price_str else None
        except (TypeError, ValueError):
            price = None

        if price and price > 0:
            dex_id = p.get("dexId", "unknown").lower()
            priced_pools.append({
                "dex": dex_id,
                "pair": p.get("pairAddress", ""),
                "price": price,
                "liquidity_usd": (p.get("liquidity") or {}).get("usd", 0),
                "volume_24h": (p.get("volume") or {}).get("h24", 0),
            })

    if len(priced_pools) < MIN_POOL_COUNT:
        return []

    prices = [p["price"] for p in priced_pools]
    min_price = min(prices)
    max_price = max(prices)

    if min_price <= 0:
        return []

    divergence_pct = (max_price - min_price) / min_price * 100

    if divergence_pct < MIN_DIVERGENCE_PCT:
        return []

    # Reject likely stale/denominator errors
    if divergence_pct > MAX_DIVERGENCE_PCT:
        return []

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    low_pool = min(priced_pools, key=lambda p: p["price"])
    high_pool = max(priced_pools, key=lambda p: p["price"])

    # Reject same-DEX signals (price difference likely denomination artifact)
    if low_pool["dex"] == high_pool["dex"]:
        return []

    return [{
        "signal_name": SIGNAL_NAME,
        "token": token_address,
        "signal_ts": now_ts,
        "signal_time": datetime.fromtimestamp(now_ts, tz=timezone.utc).isoformat(),
        "divergence_pct": round(divergence_pct, 2),
        "low_dex": low_pool["dex"],
        "low_price": low_pool["price"],
        "high_dex": high_pool["dex"],
        "high_price": high_pool["price"],
        "pool_count": len(priced_pools),
        "confidence": "HIGH" if divergence_pct > 5.0 else "MEDIUM",
        "entry_dex": low_pool["dex"],  # Buy on cheaper side
        "entry_price": low_pool["price"],
    }]


def get_backtest_signals(sleep: float = 0.5) -> list[dict]:
    """Backtest entry point: scan known tokens for cross-DEX divergence."""
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

    all_signals = []
    print(f"[SM_14] Scanning {len(tokens)} tokens for cross-DEX divergence...")

    for token in tokens:
        pools = get_token_pools(token)
        sigs = detect_divergence(token, pools)
        all_signals.extend(sigs)
        time.sleep(sleep)

    return all_signals


if __name__ == "__main__":
    signals = get_backtest_signals()
    print(f"\nSM_14 Cross-DEX Divergence signals: {len(signals)}")
    for s in signals[:5]:
        print(
            f"  {s['signal_time']} | {s['low_dex']}→{s['high_dex']} "
            f"| {s['divergence_pct']:.1f}% | {s['confidence']}"
        )

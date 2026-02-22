"""
Data fetcher for Alpha backtesting.
Sources:
  - GeckoTerminal API (free, no key): OHLCV for Solana DEX pools
  - DexScreener API (free, no key): Pool discovery by token address
  - Jupiter Price API: spot prices for well-known tokens
"""

import httpx
import time
import json
import random
import os
from datetime import datetime, timezone
from typing import Optional

DEXSCREENER_BASE = "https://api.dexscreener.com"
GECKOTERMINAL_BASE = "https://api.geckoterminal.com/api/v2"
JUPITER_PRICE_BASE = "https://api.jup.ag/price/v2"

# ── GeckoTerminal rate limiting ───────────────────────────────────────────────
# Free tier: ~30 req/min → 1 req/2s to be safe
GECKO_MIN_INTERVAL = 2.0        # seconds between calls
GECKO_CACHE_TTL = 60            # seconds to cache responses on disk
_last_gecko_call: float = 0.0   # module-level timestamp of last call

# Disk cache path (persists across subprocess restarts)
_GECKO_DISK_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".gecko_cache.json")
_gecko_disk_cache: dict = {}    # loaded on first use


def _load_gecko_disk_cache() -> None:
    """Load the on-disk OHLCV cache into memory (called once per process)."""
    global _gecko_disk_cache
    try:
        if os.path.exists(_GECKO_DISK_CACHE_PATH):
            with open(_GECKO_DISK_CACHE_PATH) as f:
                _gecko_disk_cache = json.load(f)
    except Exception:
        _gecko_disk_cache = {}


def _save_gecko_disk_cache() -> None:
    """Persist current disk cache to JSON file."""
    try:
        # Prune expired entries before saving
        now = time.time()
        pruned = {k: v for k, v in _gecko_disk_cache.items()
                  if v.get("expires_at", 0) > now}
        _gecko_disk_cache.clear()
        _gecko_disk_cache.update(pruned)
        with open(_GECKO_DISK_CACHE_PATH, "w") as f:
            json.dump(_gecko_disk_cache, f)
    except Exception:
        pass


def _gecko_rate_limit() -> None:
    """Enforce minimum interval between GeckoTerminal API calls."""
    global _last_gecko_call
    elapsed = time.time() - _last_gecko_call
    if elapsed < GECKO_MIN_INTERVAL:
        time.sleep(GECKO_MIN_INTERVAL - elapsed)
    _last_gecko_call = time.time()

# Base tokens to exclude from trading signals (not alpha signals)
# These are stablecoins, wrapped assets, major protocol tokens, or large-caps
# that cannot realistically move +20% in a 2-4h window.
BASE_TOKENS = {
    # ── Native / Wrapped ─────────────────────────────────────────────────────
    "So11111111111111111111111111111111111111112",    # Wrapped SOL
    "7vfCXTUXx5WJV5JADk17DUJ4ksgau7utNKj4b963voxs", # ETH (Wormhole)
    "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",  # cbBTC (Coinbase BTC on Solana)
    # ── Liquid Staking Tokens ────────────────────────────────────────────────
    "mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",  # mSOL
    "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn", # jitoSOL
    "bSo13r4TkiE4KumL71LsHTPpL2euBYLFx6h9HP3piy1",  # bSOL
    "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",  # JTO (Jito governance)
    # ── Stablecoins ──────────────────────────────────────────────────────────
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", # USDC
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB", # USDT
    "Es9vMFrzaCERmKkovDkRs3zqhEYnhEhFdRgEaYNTbEUd", # USDT alt
    "USD1ttGY1N17NEEHLmELoaybftRBUSErhqYiQzvEmuB",  # USD1 (World Liberty) — primary
    "USD1ttGY1N17NEEHLmELZmFE4A7d5nSqeAV3f3BBRDB",  # USD1 (alt address) — BUG FIX
    "USDSwr9ApdHk5bvJKMjzff41FfuX8bSxdKcR81vTwcA",  # USDS (Drift)
    "USDH1SM1ojwWUga67PGrgFWUHibbjqMvuMaDkRJTgkX",  # USDH (Hubble)
    "2b1kV6DkPAnxd5ixfnxCpjxmKwqjjaYmCZfHsFu24GXo", # PYUSD (PayPal)
    "7kbnvuGBxxj8AG9qp8Scn56muWGaRaFqxg1FsRp3PaFT", # UXD
    "Fm9rHUTF5v3hwMLbStjZXqNBBoZyGriQaFM6sTFz3K8A", # USDD
    "AZsHEMXd36Bj1EMNXhowJajpUXzrKcK57wW4ZGXVa7yR", # BUSD (Wormhole)
    "JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD",  # USD3/JUSD (stablecoin variant)
    # ── Major Protocol / Large-Cap Tokens ────────────────────────────────────
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", # BONK (major meme, not a copy signal)
    "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R", # RAY (Raydium governance)
    "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",  # JUP (Jupiter governance/routing)
    "orcaEKTdK7LKz57vaAYr624Dp4QuCcrKQhAVmFnvBbQ",  # ORCA (Orca DEX router)
    "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",  # ORCA alt address
    "METvsvVRapdj9cFLzq4Tr43xK4tAjQfwX76z3n6mWQL",  # MET (Meteora, large-cap DeFi)
    "27G8MtK7VtTcCHkpASjSDdkWWYfoqT6ggEuKidVJidD4", # large-cap DeFi token (identified in audit)
}

# Cache for pool lookups (avoids repeated API calls — in-memory only, fast)
_pool_cache: dict[str, Optional[str]] = {}
_ohlcv_cache: dict[str, list] = {}  # in-memory shortcut cache (per-process)


def get_solana_pool_for_token(token_address: str, timeout: int = 10) -> Optional[str]:
    """Find the best Solana DEX pool address for a token via DexScreener."""
    if token_address in _pool_cache:
        return _pool_cache[token_address]

    try:
        url = f"{DEXSCREENER_BASE}/latest/dex/tokens/{token_address}"
        with httpx.Client(timeout=timeout) as client:
            r = client.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()

        pairs = data.get("pairs") or []
        # Filter to Solana pairs only, sort by liquidity
        sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if not sol_pairs:
            _pool_cache[token_address] = None
            return None

        # Prefer highest liquidity pair
        sol_pairs.sort(key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0, reverse=True)
        pool_addr = sol_pairs[0].get("pairAddress")
        _pool_cache[token_address] = pool_addr
        return pool_addr

    except Exception as e:
        print(f"  [DexScreener] Error for {token_address[:12]}: {e}")
        _pool_cache[token_address] = None
        return None


def fetch_ohlcv_geckoterminal(
    pool_address: str,
    timeframe: str = "hour",  # "minute", "hour", "day"
    limit: int = 100,
    before_timestamp: Optional[int] = None,
    timeout: int = 15,
) -> list[dict]:
    """
    Fetch OHLCV from GeckoTerminal for a Solana pool.
    Returns list of candles: [{timestamp, open, high, low, close, volume}, ...]

    Rate limiting:
    - Enforces GECKO_MIN_INTERVAL (2s) between calls to stay under 30 req/min
    - 60s disk cache shared across subprocess restarts
    - Exponential backoff with jitter on 429: 15→30→60s + random 0-5s jitter
    - Returns [] gracefully after 4 failed attempts
    """
    cache_key = f"{pool_address}:{timeframe}:{limit}:{before_timestamp}"

    # 1. In-memory cache (fast path — same process)
    if cache_key in _ohlcv_cache:
        return _ohlcv_cache[cache_key]

    # 2. Disk cache (persists across subprocess restarts)
    if not _gecko_disk_cache:
        _load_gecko_disk_cache()
    entry = _gecko_disk_cache.get(cache_key)
    if entry and entry.get("expires_at", 0) > time.time():
        candles = entry["candles"]
        _ohlcv_cache[cache_key] = candles  # warm in-memory cache too
        return candles

    url = f"{GECKOTERMINAL_BASE}/networks/solana/pools/{pool_address}/ohlcv/{timeframe}"
    params = {"limit": limit}
    if before_timestamp:
        params["before_timestamp"] = before_timestamp

    backoff = 15
    for attempt in range(4):
        try:
            # Rate limit: enforce minimum interval before each call
            _gecko_rate_limit()

            with httpx.Client(timeout=timeout) as client:
                r = client.get(url, params=params, headers={"Accept": "application/json"})
                if r.status_code == 429:
                    if attempt < 3:
                        jitter = random.uniform(0, 5)
                        sleep_time = backoff + jitter
                        print(f"  [GeckoTerminal] 429 rate limit — sleeping {sleep_time:.1f}s (attempt {attempt+1}/4)")
                        time.sleep(sleep_time)
                        backoff = min(backoff * 2, 60)
                        continue
                    print(f"  [GeckoTerminal] 429 rate limit — giving up after 4 attempts for {pool_address[:12]}")
                    return []
                r.raise_for_status()
                data = r.json()

            candles_raw = data.get("data", {}).get("attributes", {}).get("ohlcv_list", [])
            candles = []
            for c in candles_raw:
                # GeckoTerminal format: [timestamp, open, high, low, close, volume]
                if len(c) >= 6:
                    candles.append({
                        "timestamp": c[0],
                        "open": float(c[1]),
                        "high": float(c[2]),
                        "low": float(c[3]),
                        "close": float(c[4]),
                        "volume_usd": float(c[5]),
                    })

            candles.sort(key=lambda c: c["timestamp"])

            # Cache in memory and on disk
            _ohlcv_cache[cache_key] = candles
            _gecko_disk_cache[cache_key] = {
                "candles": candles,
                "expires_at": time.time() + GECKO_CACHE_TTL,
            }
            _save_gecko_disk_cache()
            return candles

        except Exception as e:
            if attempt < 3:
                jitter = random.uniform(0, 5)
                sleep_time = backoff + jitter
                print(f"  [GeckoTerminal] Error (attempt {attempt+1}/4) for {pool_address[:12]}: {e} — retrying in {sleep_time:.1f}s")
                time.sleep(sleep_time)
                backoff = min(backoff * 2, 60)
            else:
                print(f"  [GeckoTerminal] Error for pool {pool_address[:12]}: {e}")
                return []
    return []


def get_price_at_timestamp(
    token_address: str,
    target_ts: int,
    tolerance_seconds: int = 3600,
) -> Optional[float]:
    """
    Get token price (USD) at a specific Unix timestamp.
    Uses GeckoTerminal hourly OHLCV via DexScreener pool discovery.
    Returns close price of the candle nearest to target_ts, or None.
    """
    pool = get_solana_pool_for_token(token_address)
    if not pool:
        return None

    # Fetch ~100 hourly candles starting from just before target
    # Request with before_timestamp slightly ahead so we include target
    before_ts = target_ts + 3600 * 5
    candles = fetch_ohlcv_geckoterminal(pool, timeframe="hour", limit=100, before_timestamp=before_ts)

    if not candles:
        return None

    # Find candle closest to target_ts
    best = None
    best_diff = float("inf")
    for c in candles:
        diff = abs(c["timestamp"] - target_ts)
        if diff < best_diff:
            best_diff = diff
            best = c

    if best and best_diff <= tolerance_seconds:
        return best["close"]

    return None


def get_prices_at_offsets(
    token_address: str,
    signal_ts: int,
    offsets_hours: list[int] = [0, 1, 4, 24],
) -> dict[int, Optional[float]]:
    """
    Get prices at multiple time offsets after signal.
    Returns {offset_hours: price_usd}
    """
    pool = get_solana_pool_for_token(token_address)
    if not pool:
        return {h: None for h in offsets_hours}

    # Fetch enough candles to cover 24h forward from signal
    max_offset = max(offsets_hours)
    before_ts = signal_ts + (max_offset + 4) * 3600
    candles = fetch_ohlcv_geckoterminal(pool, timeframe="hour", limit=max_offset + 10, before_timestamp=before_ts)

    results = {}
    for offset in offsets_hours:
        target_ts = signal_ts + offset * 3600
        best = None
        best_diff = float("inf")
        for c in candles:
            diff = abs(c["timestamp"] - target_ts)
            if diff < best_diff:
                best_diff = diff
                best = c
        if best and best_diff <= 3600 * 2:
            results[offset] = best["close"]
        else:
            results[offset] = None

    return results


def get_token_info_dexscreener(token_address: str) -> dict:
    """Get basic token info from DexScreener."""
    try:
        url = f"{DEXSCREENER_BASE}/latest/dex/tokens/{token_address}"
        with httpx.Client(timeout=10) as client:
            r = client.get(url, headers={"Accept": "application/json"})
            r.raise_for_status()
            data = r.json()
        pairs = data.get("pairs") or []
        sol_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        if sol_pairs:
            sol_pairs.sort(key=lambda p: p.get("liquidity", {}).get("usd", 0) or 0, reverse=True)
            best = sol_pairs[0]
            return {
                "symbol": best.get("baseToken", {}).get("symbol", "?"),
                "name": best.get("baseToken", {}).get("name", "?"),
                "price_usd": float(best.get("priceUsd") or 0),
                "liquidity_usd": best.get("liquidity", {}).get("usd", 0),
                "volume_24h": best.get("volume", {}).get("h24", 0),
                "pair_address": best.get("pairAddress"),
            }
    except Exception as e:
        pass
    return {}


if __name__ == "__main__":
    # Quick test
    print("Testing data fetcher...")
    test_token = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK
    info = get_token_info_dexscreener(test_token)
    print(f"Token info: {json.dumps(info, indent=2)}")
    pool = get_solana_pool_for_token(test_token)
    print(f"Pool: {pool}")
    if pool:
        candles = fetch_ohlcv_geckoterminal(pool, timeframe="hour", limit=5)
        print(f"Latest candles ({len(candles)}):")
        for c in candles[-3:]:
            ts = datetime.fromtimestamp(c["timestamp"], tz=timezone.utc)
            print(f"  {ts.isoformat()} close=${c['close']:.8f}")

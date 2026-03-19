"""Price Feed — CoinGecko (primary) + Birdeye (Solana) price data.

Free-tier CoinGecko: 50 req/min, no key required for basic calls.
Birdeye: Solana-native token prices (BIRDEYE_API_KEY optional for higher limits).
"""

import logging
from dataclasses import dataclass
from typing import Optional
import httpx

from ..config import settings

log = logging.getLogger("otto.crypto.price_feed")

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
BIRDEYE_BASE = "https://public-api.birdeye.so"

# Symbol → CoinGecko ID mapping for top tokens
COINGECKO_IDS: dict[str, str] = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "USDC": "usd-coin",
    "USDT": "tether",
    "MATIC": "matic-network",
    "POL": "matic-network",   # Polygon rebranded
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "AAVE": "aave",
    "CRV": "curve-dao-token",
    "MKR": "maker",
    "COMP": "compound-governance-token",
    "ARB": "arbitrum",
    "OP": "optimism",
    "BASE": "base-protocol",
    "CBBTC": "coinbase-wrapped-btc",
    "WETH": "ethereum",        # Wrapped ETH = ETH price
    "WBTC": "bitcoin",         # Wrapped BTC = BTC price
    "stETH": "staked-ether",
    "cbETH": "coinbase-wrapped-staked-eth",
    "DOGE": "dogecoin",
    "SHIB": "shiba-inu",
    "PEPE": "pepe",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "POPCAT": "popcat",
    "TRUMP": "official-trump",
}


@dataclass
class PriceData:
    symbol: str
    price_usd: float
    change_24h: Optional[float] = None    # percentage
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    source: str = "coingecko"


async def get_price(symbol: str, chain: Optional[str] = None) -> Optional[PriceData]:
    """Get current USD price for a token symbol.

    Args:
        symbol: Token symbol (e.g. "ETH", "SOL", "USDC")
        chain: Optional chain hint — if "solana", tries Birdeye first

    Returns:
        PriceData or None if token not found
    """
    symbol_upper = symbol.upper()

    # For Solana-native tokens (not in CoinGecko mapping), try Birdeye
    if chain == "solana" and symbol_upper not in COINGECKO_IDS and settings.birdeye_api_key:
        price = await _birdeye_price(symbol_upper)
        if price:
            return price

    # Default: CoinGecko
    cg_id = COINGECKO_IDS.get(symbol_upper, symbol.lower())
    return await _coingecko_price(symbol_upper, cg_id)


async def get_prices(symbols: list[str]) -> dict[str, PriceData]:
    """Batch price lookup for multiple symbols.

    Args:
        symbols: List of token symbols

    Returns:
        Dict mapping symbol → PriceData (missing = not found)
    """
    if not symbols:
        return {}

    # Build CoinGecko ID list
    cg_ids = []
    id_to_symbol: dict[str, str] = {}
    for sym in symbols:
        sym_upper = sym.upper()
        cg_id = COINGECKO_IDS.get(sym_upper, sym.lower())
        cg_ids.append(cg_id)
        id_to_symbol[cg_id] = sym_upper

    headers = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(set(cg_ids)),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        result: dict[str, PriceData] = {}
        for cg_id, cg_sym in id_to_symbol.items():
            if cg_id in data:
                d = data[cg_id]
                result[cg_sym] = PriceData(
                    symbol=cg_sym,
                    price_usd=d.get("usd", 0.0),
                    change_24h=d.get("usd_24h_change"),
                    market_cap=d.get("usd_market_cap"),
                    volume_24h=d.get("usd_24h_vol"),
                    source="coingecko",
                )
        return result

    except Exception as e:
        log.warning(f"Batch price fetch failed: {e}")
        return {}


async def _coingecko_price(symbol: str, cg_id: str) -> Optional[PriceData]:
    """Fetch single token price from CoinGecko."""
    headers = {}
    if settings.coingecko_api_key:
        headers["x-cg-demo-api-key"] = settings.coingecko_api_key

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": cg_id,
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                    "include_24hr_vol": "true",
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        if cg_id not in data:
            log.debug(f"CoinGecko: no data for {cg_id} ({symbol})")
            return None

        d = data[cg_id]
        return PriceData(
            symbol=symbol,
            price_usd=d.get("usd", 0.0),
            change_24h=d.get("usd_24h_change"),
            market_cap=d.get("usd_market_cap"),
            volume_24h=d.get("usd_24h_vol"),
            source="coingecko",
        )

    except Exception as e:
        log.warning(f"CoinGecko price fetch failed for {symbol}: {e}")
        return None


async def _birdeye_price(symbol: str) -> Optional[PriceData]:
    """Fetch Solana token price from Birdeye (requires API key or public endpoint)."""
    if not settings.birdeye_api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Birdeye symbol search
            resp = await client.get(
                f"{BIRDEYE_BASE}/defi/token_list",
                params={"sort_by": "v24hUSD", "sort_type": "desc", "offset": 0, "limit": 10,
                        "search_keyword": symbol},
                headers={"X-API-KEY": settings.birdeye_api_key, "x-chain": "solana"},
            )
            resp.raise_for_status()
            data = resp.json()

        tokens = data.get("data", {}).get("tokens", [])
        for token in tokens:
            if token.get("symbol", "").upper() == symbol:
                return PriceData(
                    symbol=symbol,
                    price_usd=token.get("price", 0.0),
                    change_24h=token.get("priceChange24h"),
                    volume_24h=token.get("v24hUSD"),
                    source="birdeye",
                )

        return None

    except Exception as e:
        log.warning(f"Birdeye price fetch failed for {symbol}: {e}")
        return None

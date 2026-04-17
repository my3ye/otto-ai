"""
Helius API client for Project Alpha.
Covers:
  - get_wallet_transactions()  — enhanced transaction history via DAS API
  - get_token_price()          — token price via Helius price oracle endpoint

Uses helius_rotator to cycle through keys when monthly quota is hit.
"""

from __future__ import annotations

import httpx
from loguru import logger
from typing import Any

from helius_rotator import (
    get_helius_key,
    mark_key_exhausted,
    is_quota_exhaustion,
    HELIUS_API_BASE,
)


async def get_wallet_transactions(
    address: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """
    Fetch recent parsed transactions for a wallet address using the
    Helius Enhanced Transactions API.

    Docs: https://docs.helius.dev/solana-apis/enhanced-transactions-api
    Returns a list of enriched transaction objects (may be empty list if
    all keys are exhausted or address has no transactions).

    Rotates keys automatically on monthly quota exhaustion.
    """
    # Try up to len(all keys) times — once per available key
    for _attempt in range(4):
        key = get_helius_key()
        if not key:
            logger.warning("All Helius keys exhausted — returning empty for {}", address[:8])
            return []

        url = f"{HELIUS_API_BASE}/addresses/{address}/transactions"
        params = {
            "api-key": key,
            "limit": limit,
            "type": "SWAP",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 429:
                    body = resp.text
                    if is_quota_exhaustion(body):
                        logger.warning(
                            "Helius key {}... monthly quota exhausted — rotating to next key",
                            key[:8],
                        )
                        mark_key_exhausted(key)
                        continue  # retry with next key
                    else:
                        # Transient rate limit — don't burn key, just bail
                        logger.warning("Helius rate limited (transient) for {}", address[:8])
                        return []
                resp.raise_for_status()
                data = resp.json()
                logger.debug("Fetched {} transactions for {}", len(data), address[:8])
                return data if isinstance(data, list) else []
        except httpx.HTTPStatusError as e:
            logger.error(
                "Helius API error for {}: {} {}",
                address[:8],
                e.response.status_code,
                e.response.text[:200],
            )
            return []
        except Exception as e:
            logger.error("Failed to fetch transactions for {}: {}", address[:8], e)
            return []

    logger.error("All Helius key rotation attempts exhausted for {}", address[:8])
    return []


async def get_token_price(mint_address: str) -> float | None:
    """
    Fetch the current USD price of a token by its mint address.
    Uses the Helius DAS getAsset endpoint combined with price feed data.

    Falls back to None if unavailable.
    """
    for _attempt in range(4):
        key = get_helius_key()
        if not key:
            logger.warning("All Helius keys exhausted — cannot fetch price for {}", mint_address[:8])
            return None

        url = "https://api.helius.xyz/v1/prices"
        params = {"api-key": key}
        payload = {"mints": [mint_address]}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, params=params, json=payload)
                if resp.status_code == 429:
                    body = resp.text
                    if is_quota_exhaustion(body):
                        logger.warning(
                            "Helius key {}... monthly quota exhausted on price API — rotating",
                            key[:8],
                        )
                        mark_key_exhausted(key)
                        continue
                    else:
                        logger.warning("Helius price API rate limited (transient) for {}", mint_address[:8])
                        return None
                resp.raise_for_status()
                data = resp.json()
                items = data.get("data", [])
                if items:
                    price = items[0].get("price")
                    logger.debug("Price for {}: ${}", mint_address[:8], price)
                    return float(price) if price is not None else None
                return None
        except httpx.HTTPStatusError as e:
            logger.warning("Price API error for {}: {}", mint_address[:8], e.response.status_code)
            return None
        except Exception as e:
            logger.error("Failed to fetch price for {}: {}", mint_address[:8], e)
            return None

    return None

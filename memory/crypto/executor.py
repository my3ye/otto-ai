"""Trade Executor — 0x Swap API quote + CDP AgentKit execution.

Phase 2 feature — execution is disabled until CRYPTO_EXECUTION_ENABLED=true.
Phase 1: provides quote-only (dry-run) functionality.
"""

import logging
from dataclasses import dataclass
from typing import Optional
import httpx

from ..config import settings
from .nlparser import TradeIntent

log = logging.getLogger("otto.crypto.executor")

ZEROX_SWAP_URL = f"{settings.zerox_api_url}/swap/v1/quote"

# Token contract addresses on Base (needed for 0x quote)
BASE_TOKEN_ADDRESSES: dict[str, str] = {
    "ETH": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",   # Native ETH sentinel
    "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "WETH": "0x4200000000000000000000000000000000000006",
    "cbETH": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22",
    "cbBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",
    "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    "DAI": "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
}


@dataclass
class SwapQuote:
    """Quote from 0x Swap API."""
    token_in: str
    token_out: str
    amount_in: str          # in token units (wei-like)
    amount_out: str         # in token units (wei-like)
    price: float            # effective price
    gas_estimate: int
    to: str                 # contract to call
    calldata: str           # encoded call data
    value: str              # ETH value to send
    chain: str
    slippage_bps: int = 50  # 0.5% default
    source: str = "0x"


@dataclass
class TxResult:
    """Result of a submitted transaction."""
    tx_hash: Optional[str]
    status: str             # pending | completed | failed
    error: Optional[str] = None
    gas_used: Optional[int] = None


async def get_quote(intent: TradeIntent) -> Optional[SwapQuote]:
    """Get a swap quote from 0x API without executing.

    Args:
        intent: Parsed TradeIntent

    Returns:
        SwapQuote or None if quote fails
    """
    if intent.chain not in ("base", "eth", "polygon"):
        log.warning(f"Chain {intent.chain} not supported by 0x executor yet")
        return None

    if intent.chain == "base":
        token_map = BASE_TOKEN_ADDRESSES
    else:
        # Phase 2: add ETH and Polygon mappings
        log.warning(f"Token address map not yet configured for {intent.chain}")
        return None

    token_in = intent.token_in or "USDC"
    token_out = intent.token_out or "ETH"

    sell_token = token_map.get(token_in.upper(), token_in)
    buy_token = token_map.get(token_out.upper(), token_out)

    # Amount: convert USD to token units is complex — Phase 1 stub
    # TODO Phase 2: use price feed to convert USD → token amount
    if not intent.amount_token and not intent.amount_usd:
        log.warning("No amount specified for quote")
        return None

    headers = {}
    if settings.zerox_api_key:
        headers["0x-api-key"] = settings.zerox_api_key

    # For Phase 1, return a placeholder quote structure
    # Phase 2 will make the actual 0x API call
    log.info(f"Quote requested: {token_in} → {token_out} on {intent.chain} [Phase 2 — execution not yet implemented]")
    return None


async def execute_swap(quote: SwapQuote, dry_run: bool = True) -> TxResult:
    """Execute a swap using CDP AgentKit.

    Args:
        quote: SwapQuote from get_quote()
        dry_run: If True, simulate only — no actual broadcast

    Returns:
        TxResult
    """
    if not settings.crypto_execution_enabled:
        return TxResult(
            tx_hash=None,
            status="failed",
            error="CRYPTO_EXECUTION_ENABLED is false — set to true to enable trading",
        )

    if dry_run:
        return TxResult(
            tx_hash=None,
            status="pending",
            error="dry_run=True — simulation only",
        )

    # Phase 2: CDP AgentKit execution
    log.info("Trade execution via CDP AgentKit — Phase 2 feature, not yet implemented")
    return TxResult(
        tx_hash=None,
        status="failed",
        error="Trade execution not yet implemented (Phase 2)",
    )

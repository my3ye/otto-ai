"""Portfolio — Multi-chain balance and PnL aggregation.

EVM chains (Base, ETH, Polygon): Alchemy API for native + token balances.
Solana: Birdeye portfolio or Helius.
Hyperliquid: reuses existing trading.py logic.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional
import httpx

from ..config import settings
from .price_feed import get_price, PriceData

log = logging.getLogger("otto.crypto.portfolio")

ALCHEMY_ENDPOINTS: dict[str, str] = {
    "base": f"https://base-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}" if settings.alchemy_api_key else "",
    "eth": f"https://eth-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}" if settings.alchemy_api_key else "",
    "polygon": f"https://polygon-mainnet.g.alchemy.com/v2/{settings.alchemy_api_key}" if settings.alchemy_api_key else "",
}

HL_INFO_URL = "https://api.hyperliquid.xyz/info"


@dataclass
class TokenBalance:
    symbol: str
    amount: float
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None
    contract_address: Optional[str] = None


@dataclass
class ChainPortfolio:
    chain: str
    wallet_address: str
    native_balance: TokenBalance
    token_balances: list[TokenBalance] = field(default_factory=list)
    total_value_usd: float = 0.0
    error: Optional[str] = None


@dataclass
class PortfolioSummary:
    chains: list[ChainPortfolio] = field(default_factory=list)
    total_value_usd: float = 0.0
    hyperliquid_equity: float = 0.0
    error: Optional[str] = None


async def get_evm_balances(wallet_address: str, chain: str = "base") -> ChainPortfolio:
    """Fetch EVM token balances for a wallet using Alchemy.

    Args:
        wallet_address: 0x... EVM wallet address
        chain: "base" | "eth" | "polygon"

    Returns:
        ChainPortfolio with native + token balances
    """
    rpc_url = ALCHEMY_ENDPOINTS.get(chain, "")
    if not rpc_url or not settings.alchemy_api_key:
        # Return empty portfolio if no Alchemy key configured
        native_symbol = {"base": "ETH", "eth": "ETH", "polygon": "POL"}.get(chain, "ETH")
        return ChainPortfolio(
            chain=chain,
            wallet_address=wallet_address,
            native_balance=TokenBalance(symbol=native_symbol, amount=0.0),
            error="ALCHEMY_API_KEY not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch native ETH balance
            eth_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0", "method": "eth_getBalance",
                "params": [wallet_address, "latest"], "id": 1,
            })
            eth_resp.raise_for_status()
            eth_data = eth_resp.json()
            native_wei = int(eth_data.get("result", "0x0"), 16)
            native_amount = native_wei / 1e18

            # Fetch ERC-20 token balances
            token_resp = await client.post(rpc_url, json={
                "jsonrpc": "2.0", "method": "alchemy_getTokenBalances",
                "params": [wallet_address, "erc20"],
                "id": 2,
            })
            token_resp.raise_for_status()
            token_data = token_resp.json()

        # Get ETH price for value calculation
        native_symbol = {"base": "ETH", "eth": "ETH", "polygon": "POL"}.get(chain, "ETH")
        native_price = await get_price(native_symbol, chain)
        native_value = native_amount * (native_price.price_usd if native_price else 0.0)

        native_bal = TokenBalance(
            symbol=native_symbol,
            amount=native_amount,
            price_usd=native_price.price_usd if native_price else None,
            value_usd=native_value,
        )

        # Parse ERC-20 tokens with non-zero balances
        token_balances: list[TokenBalance] = []
        raw_tokens = token_data.get("result", {}).get("tokenBalances", [])

        # Fetch token metadata for non-zero balances (batch, max 10)
        non_zero = [t for t in raw_tokens if t.get("tokenBalance") != "0x" and
                    int(t.get("tokenBalance", "0x0"), 16) > 0][:10]

        for tok in non_zero:
            amount_raw = int(tok.get("tokenBalance", "0x0"), 16)
            # Default to 18 decimals — metadata lookup would be more precise
            # but we skip for simplicity (Phase 1 — show approximate values)
            amount = amount_raw / 1e18
            if amount > 0.000001:  # skip dust
                token_balances.append(TokenBalance(
                    symbol="ERC20",  # symbol resolution requires additional call
                    amount=amount,
                    contract_address=tok.get("contractAddress"),
                ))

        total_value = native_value + sum(t.value_usd or 0.0 for t in token_balances)

        return ChainPortfolio(
            chain=chain,
            wallet_address=wallet_address,
            native_balance=native_bal,
            token_balances=token_balances,
            total_value_usd=total_value,
        )

    except Exception as e:
        log.warning(f"EVM balance fetch failed for {wallet_address} on {chain}: {e}")
        native_symbol = {"base": "ETH", "eth": "ETH", "polygon": "POL"}.get(chain, "ETH")
        return ChainPortfolio(
            chain=chain,
            wallet_address=wallet_address,
            native_balance=TokenBalance(symbol=native_symbol, amount=0.0),
            error=str(e),
        )


async def get_hyperliquid_equity() -> float:
    """Get Hyperliquid account equity for the trading wallet.

    Returns total equity in USD, or 0.0 on error.
    """
    wallet = settings.otto_trading_wallet_address or settings.otto_wallet_address
    if not wallet:
        return 0.0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(HL_INFO_URL, json={
                "type": "clearinghouseState",
                "user": wallet,
            })
            resp.raise_for_status()
            data = resp.json()

        equity = float(data.get("marginSummary", {}).get("accountValue", 0.0))
        return equity
    except Exception as e:
        log.warning(f"Hyperliquid equity fetch failed: {e}")
        return 0.0


async def get_portfolio_summary(chains: list[str] = None) -> PortfolioSummary:
    """Aggregate portfolio across all configured chains.

    Args:
        chains: List of chains to query. Defaults to ["base", "eth"] if Alchemy configured.

    Returns:
        PortfolioSummary with per-chain breakdown + totals
    """
    if chains is None:
        chains = ["base", "eth"] if settings.alchemy_api_key else []

    wallet = settings.otto_wallet_address
    if not wallet:
        return PortfolioSummary(error="OTTO_WALLET_ADDRESS not configured")

    chain_portfolios: list[ChainPortfolio] = []
    for chain in chains:
        cp = await get_evm_balances(wallet, chain)
        chain_portfolios.append(cp)

    hl_equity = await get_hyperliquid_equity()
    total_evm = sum(cp.total_value_usd for cp in chain_portfolios)
    total_value = total_evm + hl_equity

    return PortfolioSummary(
        chains=chain_portfolios,
        total_value_usd=total_value,
        hyperliquid_equity=hl_equity,
    )

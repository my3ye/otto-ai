"""NL Parser — Natural Language → Structured TradeIntent using Claude/LLM.

We ARE the LLM. This module extracts structured trade intents from natural
language commands like "buy $200 of ETH on Base" without any external NL API.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional

from ..llm import llm_chat, extract_json

log = logging.getLogger("otto.crypto.nlparser")

# Supported chains and actions
SUPPORTED_CHAINS = {"base", "eth", "polygon", "solana", "hyperliquid", "bsc", "avalanche",
                    "arbitrum", "optimism"}
SUPPORTED_ACTIONS = {"swap", "buy", "sell", "bridge", "limit_buy", "limit_sell", "stop_loss",
                     "dca", "take_profit", "launch", "koink_launch", "portfolio", "price", "signal"}


@dataclass
class TradeIntent:
    """Structured representation of a parsed trade command."""
    action: str                          # swap | buy | sell | bridge | limit_buy | stop_loss | dca | koink_launch | ...
    token_in: Optional[str] = None       # token to spend (e.g. "USDC")
    token_out: Optional[str] = None      # token to receive (e.g. "ETH")
    amount_usd: Optional[float] = None   # USD value of the trade
    amount_token: Optional[float] = None # raw token amount (alternative to USD)
    chain: str = "base"                  # target chain
    conditions: Optional[dict] = None    # for conditional orders: {trigger_price, trigger_type, ...}
    koink_params: Optional[dict] = None  # for koink_launch: {name, symbol, anti_whale_cap_pct, ...}
    raw_text: str = ""                   # original NL input
    confidence: float = 1.0             # parser confidence (0.0-1.0)
    missing_fields: list = None         # fields that were unclear/missing
    is_query: bool = False              # True = info request (price, portfolio), no execution needed

    def __post_init__(self):
        if self.missing_fields is None:
            self.missing_fields = []

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def is_valid_for_execution(self) -> tuple[bool, str]:
        """Check if this intent has all required fields for execution.

        Returns:
            (is_valid, reason_if_invalid)
        """
        if self.action not in SUPPORTED_ACTIONS:
            return False, f"Unknown action: {self.action}"

        if self.action in ("buy", "swap", "sell"):
            if not self.token_out and not self.token_in:
                return False, "No token specified"
            if not self.amount_usd and not self.amount_token:
                return False, "No amount specified"
            if self.confidence < 0.7:
                return False, f"Low confidence parse ({self.confidence:.0%}) — please rephrase"

        if self.action in ("limit_buy", "limit_sell", "stop_loss"):
            conditions = self.conditions or {}
            if not conditions.get("trigger_price"):
                return False, "No trigger price specified for conditional order"

        return True, ""


_PARSE_SYSTEM = """You are a crypto trade intent parser. Extract structured trading intent from natural language.

Return ONLY valid JSON with these fields:
{
  "action": "buy|sell|swap|bridge|limit_buy|limit_sell|stop_loss|dca|take_profit|price|portfolio|signal|koink_launch",
  "token_in": "symbol of token to spend (null if buying with USD/stablecoin)",
  "token_out": "symbol of token to receive",
  "amount_usd": float USD amount or null,
  "amount_token": float token amount or null,
  "chain": "base|eth|polygon|solana|hyperliquid|bsc|avalanche|arbitrum|optimism (default: base)",
  "conditions": {
    "trigger_price": float or null,
    "trigger_type": "above|below or null",
    "dca_interval_hours": int or null,
    "dca_runs": int or null
  },
  "koink_params": {
    "name": "token name or null",
    "symbol": "token symbol or null",
    "anti_whale_cap_pct": float or null,
    "sell_tax_initial_bps": int or null,
    "treasury_pct": float or null,
    "dhm_months": int or null,
    "total_supply": float or null
  },
  "confidence": float 0.0-1.0,
  "missing_fields": ["list of unclear or missing required fields"],
  "is_query": bool (true if this is asking for info, not a trade)
}

Rules:
- "buy $200 of ETH" → action=buy, token_out=ETH, amount_usd=200
- "swap 0.5 ETH for USDC" → action=swap, token_in=ETH, token_out=USDC, amount_token=0.5
- "sell all my SOL" → action=sell, token_in=SOL, missing_fields=["amount"]
- "set a limit buy for BTC at $90000" → action=limit_buy, token_out=BTC, conditions={trigger_price:90000, trigger_type:below}
- "DCA $100 into ETH weekly" → action=dca, token_out=ETH, amount_usd=100, conditions={dca_interval_hours:168}
- "what's the price of SOL?" → action=price, token_out=SOL, is_query=true
- "show my portfolio" → action=portfolio, is_query=true
- "launch a KOINK token called PiPi on Base" → action=koink_launch, chain=base, koink_params={name:"PiPi", symbol:"PIPI"}
- "create a $KOINK Standard meme coin FROG on Arbitrum with 2% anti-whale" → action=koink_launch, chain=arbitrum, koink_params={name:"FROG", symbol:"FROG", anti_whale_cap_pct:2.0}
- "deploy KOINK token DOGE2 on Solana, 12-month diamond hands, 20% treasury" → action=koink_launch, chain=solana, koink_params={name:"DOGE2", symbol:"DOGE2", dhm_months:12, treasury_pct:20.0}
- If chain not mentioned, default to "base"
- For koink_launch: populate koink_params with any mentioned parameters; missing required fields go in missing_fields
- Use null for unknown/missing fields — never guess amounts
"""


async def parse(text: str) -> TradeIntent:
    """Parse a natural language trading command into a structured TradeIntent.

    Args:
        text: Natural language input (e.g. "buy $200 of ETH on Base")

    Returns:
        TradeIntent with confidence score and missing_fields list
    """
    messages = [{"role": "user", "content": text}]

    try:
        response = await llm_chat(
            messages=messages,
            system_instruction=_PARSE_SYSTEM,
            max_tokens=500,
            temperature=0.0,
        )

        data = extract_json(response)
        if not data:
            log.warning(f"NL parser: could not extract JSON from response: {response[:200]}")
            return _fallback_intent(text, "LLM returned non-JSON response")

        return TradeIntent(
            action=data.get("action", "unknown"),
            token_in=data.get("token_in"),
            token_out=data.get("token_out"),
            amount_usd=_to_float(data.get("amount_usd")),
            amount_token=_to_float(data.get("amount_token")),
            chain=data.get("chain", "base"),
            conditions=data.get("conditions") or {},
            koink_params=data.get("koink_params") or None,
            raw_text=text,
            confidence=_to_float(data.get("confidence"), default=0.5),
            missing_fields=data.get("missing_fields") or [],
            is_query=bool(data.get("is_query", False)),
        )

    except Exception as e:
        log.error(f"NL parser error: {e}")
        return _fallback_intent(text, str(e))


def _fallback_intent(text: str, reason: str) -> TradeIntent:
    """Return a low-confidence fallback intent when parsing fails."""
    log.warning(f"NL parser fallback triggered. Reason: {reason}. Input: {text[:100]!r}")
    return TradeIntent(
        action="unknown",
        raw_text=text,
        confidence=0.0,
        missing_fields=["parse_failed"],
        is_query=False,
    )


def _to_float(value, default: float = None) -> Optional[float]:
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

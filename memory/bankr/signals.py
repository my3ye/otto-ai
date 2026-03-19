"""
BANKR Signals integration.

Publishes Otto's whale-convergence / alpha signals to bankrsignals.com
with on-chain TX-hash proof. This is a revenue path — verified signals
build reputation and subscriber base.

Endpoint pattern (bankrsignals.com API):
  POST /signals  → {"signalId": "...", "txHash": "..."}
  GET  /signals  → paginated signal history

Feature-flagged behind BANKR_SIGNALS_ENABLED.
"""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class BankrSignals:
    """
    Publishes and retrieves signals on bankrsignals.com.
    """

    def __init__(
        self,
        api_key: str,
        signals_url: str = "https://api.bankrsignals.com",
        enabled: bool = False,
    ):
        self.api_key = api_key
        self.signals_url = signals_url.rstrip("/")
        self.enabled = enabled

    @classmethod
    def from_settings(cls) -> "BankrSignals":
        from ..config import settings
        return cls(
            api_key=settings.bankr_api_key,
            signals_url=settings.bankr_signals_url,
            enabled=settings.bankr_signals_enabled,
        )

    def _headers(self) -> dict:
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def publish(
        self,
        token: str,
        direction: str,           # "long" | "short" | "neutral"
        chain: Optional[str],
        confidence: float,
        entry_price: Optional[float],
        target_price: Optional[float],
        stop_price: Optional[float],
        signal_type: str = "whale_convergence",
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Publish a signal to bankrsignals.com.

        Returns {"signalId": ..., "txHash": ..., "published": True} on success.
        Returns {"published": False, "reason": ...} when disabled or on error.
        """
        if not self.enabled:
            return {"published": False, "reason": "BANKR_SIGNALS_ENABLED=false"}
        if not self.api_key:
            return {"published": False, "reason": "BANKR_API_KEY not configured"}

        payload: dict[str, Any] = {
            "token": token,
            "direction": direction,
            "confidence": confidence,
            "signalType": signal_type,
        }
        if chain:
            payload["chain"] = chain
        if entry_price is not None:
            payload["entryPrice"] = entry_price
        if target_price is not None:
            payload["targetPrice"] = target_price
        if stop_price is not None:
            payload["stopPrice"] = stop_price
        if metadata:
            payload["metadata"] = metadata

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.signals_url}/signals",
                    json=payload,
                    headers=self._headers(),
                )
                if resp.status_code >= 400:
                    logger.warning("bankrsignals publish error %s: %s", resp.status_code, resp.text[:200])
                    return {"published": False, "reason": f"HTTP {resp.status_code}"}

                data = resp.json()
                return {
                    "published": True,
                    "signal_id": data.get("signalId") or data.get("id"),
                    "tx_hash": data.get("txHash"),
                    "raw": data,
                }
        except httpx.RequestError as e:
            logger.error("bankrsignals unreachable: %s", e)
            return {"published": False, "reason": f"Connection error: {e}"}

    async def get_history(self, limit: int = 50, offset: int = 0) -> dict:
        """Fetch Otto's published signal history from bankrsignals.com."""
        if not self.enabled:
            return {"signals": [], "reason": "BANKR_SIGNALS_ENABLED=false"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.signals_url}/signals",
                    params={"limit": limit, "offset": offset},
                    headers=self._headers(),
                )
                if resp.status_code >= 400:
                    return {"signals": [], "error": f"HTTP {resp.status_code}"}
                return resp.json()
        except httpx.RequestError as e:
            return {"signals": [], "error": str(e)}

    async def close_signal(
        self,
        signal_id: str,
        exit_price: float,
        win: bool,
        pnl_pct: float,
    ) -> dict:
        """Mark a signal as closed with outcome."""
        if not self.enabled:
            return {"updated": False, "reason": "signals disabled"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.patch(
                    f"{self.signals_url}/signals/{signal_id}",
                    json={"exitPrice": exit_price, "win": win, "pnlPct": pnl_pct, "status": "closed"},
                    headers=self._headers(),
                )
                return {"updated": resp.status_code < 400}
        except httpx.RequestError as e:
            return {"updated": False, "error": str(e)}

"""WalletAdapter — abstract signing interface for OWS + Koink + ONEON.

Phase 0: NullWalletAdapter raises NotImplementedError (no signing needed yet).
Phase 1: OWSWalletAdapter will plug in here, implementing the same interface.

Usage:
    from .wallet_adapter import get_wallet_adapter

    adapter = get_wallet_adapter()
    signed = await adapter.sign_transaction(tx_payload)

This is the seam that prevents deep coupling to any specific wallet signing
infrastructure. When OWS Phase 1 ships (~$3-8K), only this module changes.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

log = logging.getLogger("otto.wallet_adapter")


class WalletAdapter(ABC):
    """Abstract signing interface. All signing flows go through this."""

    @abstractmethod
    async def sign_transaction(self, tx_payload: dict[str, Any]) -> dict[str, Any]:
        """Sign a transaction payload. Returns signed payload dict."""
        ...

    @abstractmethod
    async def get_address(self) -> str:
        """Return the public address for this wallet."""
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """Return health/status info for this adapter."""
        ...


class NullWalletAdapter(WalletAdapter):
    """Phase 0 stub — raises NotImplementedError on any signing call.

    This is intentional: signing is not needed in Phase 0. The adapter
    exists as an interface contract, not a functional implementation.
    """

    async def sign_transaction(self, tx_payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "WalletAdapter: signing not available in Phase 0. "
            "OWS Phase 1 implementation required before contract deployment."
        )

    async def get_address(self) -> str:
        raise NotImplementedError(
            "WalletAdapter: no deploy wallet configured in Phase 0."
        )

    async def health(self) -> dict[str, Any]:
        return {
            "phase": "0",
            "status": "stub",
            "signing_available": False,
            "note": "NullWalletAdapter — OWS Phase 1 required for signing.",
        }


# Module-level singleton — swap this out in Phase 1
_adapter: WalletAdapter = NullWalletAdapter()


def get_wallet_adapter() -> WalletAdapter:
    """Return the active WalletAdapter instance."""
    return _adapter


def set_wallet_adapter(adapter: WalletAdapter) -> None:
    """Replace the active adapter (Phase 1 OWS setup)."""
    global _adapter
    log.info(f"WalletAdapter set to: {type(adapter).__name__}")
    _adapter = adapter

"""ONEON DID utilities — Phase 0 stubs.

Phase 0: DID construction is string-based (no resolution, no signing).
Phase 2: Will hook into ONEON People Chain (Polkadot-based) for real DID resolution.
"""

import logging
from typing import Optional

log = logging.getLogger("otto.oneon.did")


def construct_did(
    handle: str,
    chain: str = "none",
    address: Optional[str] = None,
) -> str:
    """Build a did:oneon DID string.

    Phase 0: Returns a well-formed DID string. No on-chain registration yet.
    Format: did:oneon:<handle>:<chain>:<address>
            did:oneon:<handle>:none (if no address yet)
    """
    handle_clean = handle.lstrip("@").lower()
    if address:
        return f"did:oneon:{handle_clean}:{chain}:{address}"
    return f"did:oneon:{handle_clean}:{chain}"


def parse_did(did: str) -> dict:
    """Parse a did:oneon string into its components."""
    parts = did.split(":")
    if len(parts) < 3 or parts[0] != "did" or parts[1] != "oneon":
        raise ValueError(f"Invalid did:oneon format: {did}")
    result = {
        "method": "oneon",
        "handle": parts[2] if len(parts) > 2 else None,
        "chain": parts[3] if len(parts) > 3 else "none",
        "address": parts[4] if len(parts) > 4 else None,
        "raw": did,
    }
    return result


def did_document_stub(handle: str, did: str) -> dict:
    """Return a Phase 0 DID document stub.

    Phase 2: This will be a real W3C DID Document fetched from ONEON People Chain.
    """
    return {
        "@context": ["https://www.w3.org/ns/did/v1"],
        "id": did,
        "verificationMethod": [],   # Empty in Phase 0
        "authentication": [],       # Empty in Phase 0
        "note": (
            f"Phase 0 stub for {handle}. "
            "Real DID Document requires ONEON People Chain (Phase 2)."
        ),
    }

"""ONEON Identity Network integration module.

Feature-flagged via settings.oneon_enabled.

Phase 0: DB/API only — identity registry, governance proposals, DID stubs.
Phase 1: OWS custodial vault, on-chain DID anchoring.
Phase 2: Self-sovereign, Polkadot People Chain.
"""

from .spec import ONEON_SPEC, ONEON_TIERS, DID_METHOD

from .identity import (
    register_identity,
    get_identity,
    get_identity_by_handle,
    list_identities,
    upgrade_tier,
    get_identity_stats,
)

from .governance import (
    create_proposal,
    get_proposal,
    list_proposals,
    update_proposal_status,
    cast_vote,
    get_votes,
)

from .did import (
    construct_did,
    parse_did,
    did_document_stub,
)

__all__ = [
    # Spec
    "ONEON_SPEC",
    "ONEON_TIERS",
    "DID_METHOD",
    # Identity
    "register_identity",
    "get_identity",
    "get_identity_by_handle",
    "list_identities",
    "upgrade_tier",
    "get_identity_stats",
    # Governance
    "create_proposal",
    "get_proposal",
    "list_proposals",
    "update_proposal_status",
    "cast_vote",
    "get_votes",
    # DID
    "construct_did",
    "parse_did",
    "did_document_stub",
]

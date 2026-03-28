"""ONEON Identity Network integration module.

Feature-flagged via settings.oneon_enabled.

Phase 0: DB/API only — identity registry, governance proposals, DID stubs.
Phase 1A: Invisible signup, magic link auth, session keys, credentials, action queueing.
Phase 1B: Smart contracts, on-chain deployment, bundler integration.
Phase 2: Self-sovereign, mesh network.
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

from .auth import (
    send_magic_link,
    verify_magic_link,
    create_session_token,
    verify_session_token,
    invalidate_session,
)

from .invisible import (
    compute_smart_account_address,
    create_session_key,
    get_active_session_key,
    revoke_session_key,
    execute_action,
    get_actions,
)

from .credentials import (
    issue_credential,
    list_achievements,
    list_raw_credentials,
    revoke_credential,
    get_credential,
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
    # Auth (Phase 1A)
    "send_magic_link",
    "verify_magic_link",
    "create_session_token",
    "verify_session_token",
    "invalidate_session",
    # Invisible Layer (Phase 1A)
    "compute_smart_account_address",
    "create_session_key",
    "get_active_session_key",
    "revoke_session_key",
    "execute_action",
    "get_actions",
    # Credentials (Phase 1A)
    "issue_credential",
    "list_achievements",
    "list_raw_credentials",
    "revoke_credential",
    "get_credential",
]

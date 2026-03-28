"""ONEON Identity Network API routes (/oneon/*).

All endpoints guarded by the oneon_enabled feature flag.

Phase 0: Identity registry, governance proposals, DID stubs.
Phase 1A: Invisible signup, magic link auth, actions, credentials.

Routes:
    GET  /oneon/status                           — feature flags, phase info, stats
    GET  /oneon/spec                             — machine-readable ONEON spec
    POST /oneon/signup                           — invisible signup (handle + email)
    POST /oneon/auth/magic-link                  — verify magic link token
    POST /oneon/identities                       — register identity (Phase 0 compat)
    GET  /oneon/identities                       — list identities
    GET  /oneon/identities/{identity_id}         — single identity
    GET  /oneon/identities/by-handle/{handle}    — lookup by @handle
    POST /oneon/identities/{identity_id}/upgrade — tier upgrade
    GET  /oneon/identities/{identity_id}/achievements — user-friendly credentials
    GET  /oneon/identities/{identity_id}/credentials  — raw W3C VCs (Tier 2+)
    GET  /oneon/identities/{identity_id}/actions      — action history
    POST /oneon/actions/vote                     — invisible vote action
    POST /oneon/actions/post                     — invisible post action
    POST /oneon/credentials/issue                — issue credential/achievement
    POST /oneon/governance/proposals             — create proposal
    GET  /oneon/governance/proposals             — list proposals
    GET  /oneon/governance/proposals/{proposal_id} — single proposal + votes
    POST /oneon/governance/proposals/{proposal_id}/vote — cast vote
    PUT  /oneon/governance/proposals/{proposal_id}/status — update status (admin)
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..oneon import (
    ONEON_SPEC,
    # Identity
    register_identity,
    get_identity,
    get_identity_by_handle,
    list_identities,
    upgrade_tier,
    get_identity_stats,
    # Auth
    send_magic_link,
    verify_magic_link,
    # Invisible layer
    create_session_key,
    execute_action,
    get_actions,
    # Credentials
    issue_credential,
    list_achievements,
    list_raw_credentials,
    # Governance
    create_proposal,
    get_proposal,
    list_proposals,
    update_proposal_status,
    cast_vote,
    get_votes,
    # DID
    did_document_stub,
)
from ..oneon.invisible import _decrypt_key  # noqa: for dev introspection

log = logging.getLogger("otto.routes.oneon")

router = APIRouter(prefix="/oneon", tags=["oneon"])


def _require_enabled():
    if not settings.oneon_enabled:
        raise HTTPException(
            status_code=503,
            detail="ONEON integration is disabled. Set ONEON_ENABLED=true to enable.",
        )


def _require_admin():
    """Placeholder admin auth guard — replace with real session-based auth.

    Phase 1A provides session tokens via magic link. Full Depends() guard
    should check Authorization header → verify_session_token().
    """
    raise HTTPException(
        status_code=501,
        detail="Admin endpoints require auth. Use /oneon/signup + /oneon/auth/magic-link first.",
    )


# ─── Request Models ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    """Invisible signup — handle + email, nothing else."""
    handle: str = Field(..., min_length=2, max_length=32)
    email: str = Field(..., min_length=5, max_length=254)
    display_name: Optional[str] = None


class MagicLinkVerifyRequest(BaseModel):
    """Verify a magic link token from email."""
    token: str


class RegisterIdentityRequest(BaseModel):
    """Phase 0 identity registration (backwards compatible)."""
    handle: str
    display_name: Optional[str] = None
    wallet_address: Optional[str] = None
    chain: str = "none"
    metadata: Optional[dict] = None


class UpgradeTierRequest(BaseModel):
    new_tier: str
    ows_vault_ref: Optional[str] = None
    wallet_address: Optional[str] = None


class ActionRequest(BaseModel):
    """Execute an invisible action."""
    identity_id: UUID
    payload: dict = Field(default_factory=dict)


class VoteActionRequest(ActionRequest):
    """Invisible vote on a governance proposal."""
    proposal_id: UUID
    vote: str  # for | against | abstain


class PostActionRequest(ActionRequest):
    """Invisible post/content creation."""
    content: str = Field(..., max_length=10000)
    channel: Optional[str] = None


class IssueCredentialRequest(BaseModel):
    """Issue a credential/achievement."""
    subject_id: UUID
    credential_type: str
    claims: Optional[dict] = None
    issuer_id: Optional[UUID] = None
    badge_name: Optional[str] = None
    badge_description: Optional[str] = None


class CreateProposalRequest(BaseModel):
    proposer_id: UUID
    title: str = Field(..., max_length=200)
    body: str = Field(..., max_length=10000)
    proposal_type: str = "general"
    quorum_required: int = 10
    voting_ends_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class CastVoteRequest(BaseModel):
    voter_id: UUID
    vote: str  # for | against | abstain
    weight: int = Field(default=1, ge=1, le=1)


class UpdateStatusRequest(BaseModel):
    status: str


# ─── Invisible Onboarding ────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(req: SignupRequest):
    """Invisible signup — user provides handle + email, gets an identity.

    Under the hood: creates identity at custodial tier, derives smart account
    address, sends magic link email for verification.
    """
    _require_enabled()
    try:
        identity = await register_identity(
            handle=req.handle,
            display_name=req.display_name,
            email=req.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Send magic link for email verification
    magic_link_info = None
    try:
        magic_link_info = await send_magic_link(
            identity_id=str(identity["id"]),
            email=req.email,
        )
    except Exception as e:
        log.warning(f"Magic link send failed (identity created, auth pending): {e}")

    # Create initial session key for invisible signing
    try:
        await create_session_key(str(identity["id"]))
    except Exception as e:
        log.warning(f"Session key creation failed (non-fatal): {e}")

    # Issue "Pioneer" credential
    try:
        from ..oneon import issue_credential as _issue_cred
        await _issue_cred(
            subject_id=str(identity["id"]),
            credential_type="first_identity",
        )
    except Exception as e:
        log.warning(f"Pioneer credential failed (non-fatal): {e}")

    return {
        "identity_id": str(identity["id"]),
        "handle": identity["handle"],
        "tier": identity["tier"],
        "smart_account_address": identity.get("smart_account_address"),
        "did": identity.get("did"),
        "email_verification_sent": magic_link_info is not None,
        "message": "Check your email to verify your identity.",
    }


@router.post("/auth/magic-link")
async def verify_magic_link_route(req: MagicLinkVerifyRequest):
    """Verify a magic link token from email.

    Returns session token for authenticated API access.
    """
    _require_enabled()
    result = await verify_magic_link(req.token)
    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired magic link. Request a new one.",
        )

    # Issue "Verified" credential on first email verification
    try:
        from ..oneon import issue_credential as _issue_cred
        await _issue_cred(
            subject_id=result["identity_id"],
            credential_type="email_verified",
        )
    except Exception as e:
        log.warning(f"Verified credential failed (non-fatal): {e}")

    return result


# ─── Invisible Actions ───────────────────────────────────────────────────────

@router.post("/actions/vote")
async def action_vote(req: VoteActionRequest):
    """Cast an invisible governance vote.

    Tier 1: auto-signed, gas sponsored. User sees "Vote recorded".
    Requires email verification.
    """
    _require_enabled()
    try:
        action = await execute_action(
            identity_id=str(req.identity_id),
            action_type="vote",
            payload={
                "proposal_id": str(req.proposal_id),
                "vote": req.vote,
                **(req.payload or {}),
            },
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "action_id": str(action["id"]),
        "status": action["status"],
        "message": "Vote recorded.",
    }


@router.post("/actions/post")
async def action_post(req: PostActionRequest):
    """Create an invisible post/content.

    Content is hashed and signed. Chain anchoring in Phase 1B.
    Requires email verification.
    """
    _require_enabled()
    import hashlib
    content_hash = hashlib.sha256(req.content.encode()).hexdigest()

    try:
        action = await execute_action(
            identity_id=str(req.identity_id),
            action_type="post",
            payload={
                "content": req.content,
                "content_hash": content_hash,
                "channel": req.channel,
            },
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "action_id": str(action["id"]),
        "content_hash": content_hash,
        "status": action["status"],
        "message": "Post created.",
    }


# ─── Credentials / Achievements ─────────────────────────────────────────────

@router.post("/credentials/issue", status_code=201)
async def issue_credential_route(req: IssueCredentialRequest):
    """Issue a credential (achievement) to an identity."""
    _require_enabled()
    try:
        credential = await issue_credential(
            subject_id=str(req.subject_id),
            credential_type=req.credential_type,
            claims=req.claims,
            issuer_id=str(req.issuer_id) if req.issuer_id else None,
            badge_name=req.badge_name,
            badge_description=req.badge_description,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return credential


@router.get("/identities/{identity_id}/achievements")
async def get_achievements_route(identity_id: UUID):
    """List achievements (user-friendly credential view).

    Tier 1 users see badges: name, description, earned date.
    No VC jargon.
    """
    _require_enabled()
    identity = await get_identity(str(identity_id))
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return await list_achievements(str(identity_id))


@router.get("/identities/{identity_id}/credentials")
async def get_credentials_route(identity_id: UUID):
    """List raw W3C Verifiable Credentials (Tier 2+ export).

    Returns full VC JWTs for portable identity.
    """
    _require_enabled()
    identity = await get_identity(str(identity_id))
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return await list_raw_credentials(str(identity_id))


@router.get("/identities/{identity_id}/actions")
async def get_actions_route(
    identity_id: UUID,
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List actions for an identity."""
    _require_enabled()
    identity = await get_identity(str(identity_id))
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return await get_actions(str(identity_id), status=status, limit=limit)


# ─── Phase 0 Identity CRUD (backwards compatible) ───────────────────────────

@router.post("/identities", status_code=201)
async def register_identity_route(req: RegisterIdentityRequest):
    """Register a new ONEON identity (Phase 0 compat).

    For invisible signup, use POST /oneon/signup instead.
    """
    _require_enabled()
    try:
        identity = await register_identity(
            handle=req.handle,
            display_name=req.display_name,
            wallet_address=req.wallet_address,
            chain=req.chain,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return identity


@router.get("/status")
async def get_oneon_status():
    """ONEON feature flags, phase info, and aggregate stats."""
    stats = {}
    if settings.oneon_enabled:
        try:
            stats = await get_identity_stats()
        except Exception:
            stats = {"error": "stats unavailable"}
    return {
        "enabled": settings.oneon_enabled,
        "phase": "1A",
        "phase_description": (
            "Invisible Web3 layer — signup, auth, actions, credentials. "
            "Smart contracts and chain integration in Phase 1B."
        ),
        "features": {
            "identity_registry": True,
            "invisible_signup": True,
            "magic_link_auth": True,
            "session_keys": True,
            "invisible_actions": True,
            "credentials_achievements": True,
            "governance_proposals": True,
            "did_stubs": True,
            "smart_contracts": False,      # Phase 1B
            "on_chain_actions": False,     # Phase 1B
            "xmtp_messaging": False,       # Phase 1C
            "passkey_auth": False,         # Phase 1C
            "self_sovereign": False,       # Phase 2
        },
        "stats": stats,
    }


@router.get("/spec")
async def get_oneon_spec():
    """Machine-readable ONEON specification."""
    return ONEON_SPEC


@router.get("/identities")
async def list_identities_route(
    tier: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List ONEON identities with optional tier filter."""
    _require_enabled()
    try:
        return await list_identities(tier=tier, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/identities/by-handle/{handle}")
async def get_identity_by_handle_route(handle: str):
    """Look up an ONEON identity by @handle."""
    _require_enabled()
    identity = await get_identity_by_handle(handle)
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity not found: @{handle}")
    did_doc = did_document_stub(identity["handle"], identity["did"] or "")
    return {**identity, "did_document": did_doc}


@router.get("/identities/{identity_id}")
async def get_identity_route(identity_id: UUID):
    """Fetch a single ONEON identity with DID document stub."""
    _require_enabled()
    identity = await get_identity(str(identity_id))
    if not identity:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    did_doc = did_document_stub(identity["handle"], identity["did"] or "")
    return {**identity, "did_document": did_doc}


@router.post("/identities/{identity_id}/upgrade")
async def upgrade_tier_route(identity_id: UUID, req: UpgradeTierRequest):
    """Request a tier upgrade for an ONEON identity."""
    _require_enabled()
    try:
        updated = await upgrade_tier(
            identity_id=str(identity_id),
            new_tier=req.new_tier,
            ows_vault_ref=req.ows_vault_ref,
            wallet_address=req.wallet_address,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Identity not found: {identity_id}")
    return updated


# ─── Governance ──────────────────────────────────────────────────────────────

@router.post("/governance/proposals", status_code=201)
async def create_proposal_route(req: CreateProposalRequest):
    """Create a new governance proposal."""
    _require_enabled()
    try:
        proposal = await create_proposal(
            proposer_id=str(req.proposer_id),
            title=req.title,
            body=req.body,
            proposal_type=req.proposal_type,
            quorum_required=req.quorum_required,
            voting_ends_at=req.voting_ends_at,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return proposal


@router.get("/governance/proposals")
async def list_proposals_route(
    status: Optional[str] = Query(None),
    proposal_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List governance proposals with optional filters."""
    _require_enabled()
    return await list_proposals(
        status=status, proposal_type=proposal_type,
        limit=limit, offset=offset,
    )


@router.get("/governance/proposals/{proposal_id}")
async def get_proposal_route(proposal_id: UUID):
    """Fetch a single proposal with its votes."""
    _require_enabled()
    proposal = await get_proposal(str(proposal_id))
    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    votes = await get_votes(str(proposal_id))
    return {**proposal, "votes": votes}


@router.post("/governance/proposals/{proposal_id}/vote")
async def cast_vote_route(proposal_id: UUID, req: CastVoteRequest):
    """Cast a vote on an open governance proposal."""
    _require_enabled()
    try:
        vote = await cast_vote(
            proposal_id=str(proposal_id),
            voter_id=str(req.voter_id),
            vote=req.vote,
            weight=req.weight,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return vote


@router.put("/governance/proposals/{proposal_id}/status")
async def update_proposal_status_route(proposal_id: UUID, req: UpdateStatusRequest):
    """Update a proposal's status (admin endpoint)."""
    _require_admin()
    _require_enabled()
    try:
        updated = await update_proposal_status(str(proposal_id), req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {proposal_id}")
    return updated

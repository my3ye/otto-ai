"""ONEON Identity Network API routes (/oneon/*).

All endpoints guarded by the oneon_enabled feature flag.
Phase 0: DB/API only — no OWS signing, no on-chain DID resolution.

Routes:
    GET  /oneon/status                         — feature flags, phase info, stats
    GET  /oneon/spec                           — machine-readable ONEON spec
    POST /oneon/identities                     — register a new identity
    GET  /oneon/identities                     — list identities (filterable by tier)
    GET  /oneon/identities/{identity_id}       — single identity with DID document stub
    GET  /oneon/identities/by-handle/{handle}  — lookup by @handle
    POST /oneon/identities/{identity_id}/upgrade — tier upgrade request
    POST /oneon/governance/proposals           — create a governance proposal
    GET  /oneon/governance/proposals           — list proposals
    GET  /oneon/governance/proposals/{proposal_id} — single proposal + votes
    POST /oneon/governance/proposals/{proposal_id}/vote — cast a vote
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
    register_identity,
    get_identity,
    get_identity_by_handle,
    list_identities,
    upgrade_tier,
    get_identity_stats,
    create_proposal,
    get_proposal,
    list_proposals,
    update_proposal_status,
    cast_vote,
    get_votes,
    did_document_stub,
)

log = logging.getLogger("otto.routes.oneon")

router = APIRouter(prefix="/oneon", tags=["oneon"])


def _require_enabled():
    if not settings.oneon_enabled:
        raise HTTPException(
            status_code=503,
            detail="ONEON integration is disabled. Set ONEON_ENABLED=true to enable.",
        )


def _require_admin():
    """Placeholder admin auth guard. Phase 1: wire in real token/session check.
    Currently raises 501 to make the absence of auth explicit rather than silent.
    Replace with a proper dependency (e.g. OAuth2 bearer) before enabling ONEON.
    """
    raise HTTPException(
        status_code=501,
        detail="Admin endpoints require auth. Phase 1: implement _require_admin() before enabling ONEON.",
    )


# ─── Request Models ────────────────────────────────────────────────────────────

class RegisterIdentityRequest(BaseModel):
    handle: str
    display_name: Optional[str] = None
    wallet_address: Optional[str] = None
    chain: str = "none"
    metadata: Optional[dict] = None


class UpgradeTierRequest(BaseModel):
    new_tier: str
    ows_vault_ref: Optional[str] = None
    wallet_address: Optional[str] = None


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
    vote: str    # for | against | abstain
    weight: int = Field(default=1, ge=1, le=100)


class UpdateStatusRequest(BaseModel):
    status: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

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
        "phase": "0",
        "phase_description": ONEON_SPEC["phase_description"],
        "features": {
            "identity_registry": True,
            "governance_proposals": True,
            "did_stubs": True,
            "ows_vault": False,          # Phase 1
            "on_chain_did": False,       # Phase 2
            "self_sovereign": False,     # Phase 2
        },
        "stats": stats,
    }


@router.get("/spec")
async def get_oneon_spec():
    """Machine-readable ONEON specification."""
    return ONEON_SPEC


@router.post("/identities", status_code=201)
async def register_identity_route(req: RegisterIdentityRequest):
    """Register a new ONEON identity at 'waitlist' tier."""
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
    """Request a tier upgrade for an ONEON identity.

    Phase 0: Only waitlist → custodial is practically meaningful.
    Phase 1: OWS vault ref required for custodial.
    """
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
    return await list_proposals(status=status, proposal_type=proposal_type, limit=limit, offset=offset)


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

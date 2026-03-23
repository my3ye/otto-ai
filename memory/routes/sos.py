"""SOS Systems API routes (/sos/*).

All endpoints guarded by the sos_enabled feature flag.
Phase 0: Learner registry, contribution tracking, case management.

Routes:
    GET  /sos/status                              — feature flags, stats
    POST /sos/learners                            — register a learner
    GET  /sos/learners                            — list learners
    GET  /sos/learners/{learner_id}               — single learner
    GET  /sos/learners/by-handle/{handle}         — lookup by handle
    POST /sos/learners/{learner_id}/contribution  — award a contribution + XP
    POST /sos/cases                               — open a case
    GET  /sos/cases                               — list cases (sorted by urgency)
    GET  /sos/cases/{case_id}                     — single case
    PUT  /sos/cases/{case_id}/status              — update case status
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..sos import (
    register_learner,
    get_learner,
    get_learner_by_handle,
    list_learners,
    award_contribution,
    get_learner_stats,
    TIER_XP_THRESHOLDS,
    create_case,
    get_case,
    list_cases,
    update_case_status,
    get_case_stats,
)

log = logging.getLogger("otto.routes.sos")

router = APIRouter(prefix="/sos", tags=["sos"])


def _require_enabled():
    if not settings.sos_enabled:
        raise HTTPException(
            status_code=503,
            detail="SOS Systems integration is disabled. Set SOS_ENABLED=true to enable.",
        )


# ─── Request Models ────────────────────────────────────────────────────────────

class RegisterLearnerRequest(BaseModel):
    handle: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    origin_type: str = "general"
    oneon_id: Optional[UUID] = None
    tusita_location: Optional[UUID] = None
    metadata: Optional[dict] = None


class AwardContributionRequest(BaseModel):
    contribution_type: str
    title: str
    description: Optional[str] = None
    xp_awarded: int = 0
    reviewer_id: Optional[UUID] = None
    metadata: Optional[dict] = None


class CreateCaseRequest(BaseModel):
    requester_name: str = Field(..., max_length=200)
    description: str = Field(..., max_length=5000)
    case_type: str = "general"
    urgency: str = "standard"
    requester_email: Optional[str] = None
    location: Optional[str] = None
    tusita_ref: Optional[UUID] = None
    metadata: Optional[dict] = None


class UpdateCaseStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    tusita_ref: Optional[UUID] = None
    learner_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_sos_status():
    """SOS Systems feature flags and aggregate stats."""
    learner_stats: dict = {}
    case_stats: dict = {}
    if settings.sos_enabled:
        try:
            learner_stats = await get_learner_stats()
            case_stats = await get_case_stats()
        except Exception:
            learner_stats = {"error": "unavailable"}
            case_stats = {"error": "unavailable"}
    return {
        "enabled": settings.sos_enabled,
        "phase": "0",
        "phase_description": (
            "Learner registry, contribution tracking, case management. "
            "No merit scoring engine or tier advancement automation yet."
        ),
        "features": {
            "learner_registry": True,
            "contribution_tracking": True,
            "case_management": True,
            "merit_engine": False,        # Phase 2
            "auto_tier_advancement": False,  # Phase 2 (manual XP awards only)
            "mesh_network": False,        # Phase 3
        },
        "tier_thresholds": TIER_XP_THRESHOLDS,
        "learner_stats": learner_stats,
        "case_stats": case_stats,
    }


@router.post("/learners", status_code=201)
async def register_learner_route(req: RegisterLearnerRequest):
    """Register a new SOS learner at 'seed' tier."""
    _require_enabled()
    try:
        learner = await register_learner(
            handle=req.handle,
            display_name=req.display_name,
            email=req.email,
            origin_type=req.origin_type,
            oneon_id=str(req.oneon_id) if req.oneon_id else None,
            tusita_location=str(req.tusita_location) if req.tusita_location else None,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return learner


@router.get("/learners")
async def list_learners_route(
    tier: Optional[str] = Query(None),
    origin_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List SOS learners ranked by XP, with optional tier/origin filters."""
    _require_enabled()
    return await list_learners(tier=tier, origin_type=origin_type, limit=limit, offset=offset)


@router.get("/learners/by-handle/{handle}")
async def get_learner_by_handle_route(handle: str):
    """Look up a learner by @handle."""
    _require_enabled()
    learner = await get_learner_by_handle(handle)
    if not learner:
        raise HTTPException(status_code=404, detail=f"Learner not found: @{handle}")
    return learner


@router.get("/learners/{learner_id}")
async def get_learner_route(learner_id: UUID):
    """Fetch a single SOS learner."""
    _require_enabled()
    learner = await get_learner(str(learner_id))
    if not learner:
        raise HTTPException(status_code=404, detail=f"Learner not found: {learner_id}")
    return learner


@router.post("/learners/{learner_id}/contribution")
async def award_contribution_route(learner_id: UUID, req: AwardContributionRequest):
    """Award a contribution and XP to a learner. Advances tier if threshold crossed."""
    _require_enabled()
    try:
        result = await award_contribution(
            learner_id=str(learner_id),
            contribution_type=req.contribution_type,
            title=req.title,
            description=req.description,
            xp_awarded=req.xp_awarded,
            reviewer_id=str(req.reviewer_id) if req.reviewer_id else None,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.post("/cases", status_code=201)
async def create_case_route(req: CreateCaseRequest):
    """Open a new SOS case (refuge, displacement, or general)."""
    _require_enabled()
    try:
        case = await create_case(
            requester_name=req.requester_name,
            description=req.description,
            case_type=req.case_type,
            urgency=req.urgency,
            requester_email=req.requester_email,
            location=req.location,
            tusita_ref=str(req.tusita_ref) if req.tusita_ref else None,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return case


@router.get("/cases")
async def list_cases_route(
    status: Optional[str] = Query(None),
    case_type: Optional[str] = Query(None),
    urgency: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List SOS cases sorted by urgency (critical first)."""
    _require_enabled()
    return await list_cases(status=status, case_type=case_type, urgency=urgency, limit=limit, offset=offset)


@router.get("/cases/{case_id}")
async def get_case_route(case_id: UUID):
    """Fetch a single SOS case."""
    _require_enabled()
    case = await get_case(str(case_id))
    if not case:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    return case


@router.put("/cases/{case_id}/status")
async def update_case_status_route(case_id: UUID, req: UpdateCaseStatusRequest):
    """Update a case's status and optional resolution details."""
    _require_enabled()
    try:
        updated = await update_case_status(
            case_id=str(case_id),
            status=req.status,
            notes=req.notes,
            tusita_ref=str(req.tusita_ref) if req.tusita_ref else None,
            learner_id=str(req.learner_id) if req.learner_id else None,
            assigned_to=str(req.assigned_to) if req.assigned_to else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Case not found: {case_id}")
    return updated

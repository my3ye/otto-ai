"""Tusita community locations and bookings API routes (/tusita/*).

All endpoints guarded by the tusita_enabled feature flag.
Phase 0: Location registry + booking management.

Routes:
    GET  /tusita/status                        — feature flags, stats
    POST /tusita/locations                     — register a location
    GET  /tusita/locations                     — list locations
    GET  /tusita/locations/{location_id}       — single location with booking count
    GET  /tusita/locations/by-slug/{slug}      — lookup by slug
    PUT  /tusita/locations/{location_id}/status — update location status
    POST /tusita/locations/{location_id}/revenue — record revenue
    POST /tusita/bookings                      — create a booking
    GET  /tusita/bookings                      — list bookings
    GET  /tusita/bookings/{booking_id}         — single booking
    PUT  /tusita/bookings/{booking_id}/status  — update booking status
"""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..config import settings
from ..tusita import (
    create_location,
    get_location,
    get_location_by_slug,
    list_locations,
    update_location_status,
    record_revenue,
    get_location_stats,
    create_booking,
    get_booking,
    list_bookings,
    update_booking_status,
)

log = logging.getLogger("otto.routes.tusita")

router = APIRouter(prefix="/tusita", tags=["tusita"])


def _require_enabled():
    if not settings.tusita_enabled:
        raise HTTPException(
            status_code=503,
            detail="Tusita integration is disabled. Set TUSITA_ENABLED=true to enable.",
        )


# ─── Request Models ────────────────────────────────────────────────────────────

class CreateLocationRequest(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    coordinates: Optional[dict] = None
    dome_type: str = "community"
    capacity: int = 0
    metadata: Optional[dict] = None


class UpdateStatusRequest(BaseModel):
    status: str


class RecordRevenueRequest(BaseModel):
    amount: float


class CreateBookingRequest(BaseModel):
    location_id: UUID
    guest_name: str
    check_in: date
    check_out: date
    booking_type: str = "visitor"
    guest_email: Optional[str] = None
    guest_handle: Optional[str] = None
    party_size: int = 1
    total_amount: Optional[float] = None
    currency: str = "USD"
    notes: Optional[str] = None
    metadata: Optional[dict] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def get_tusita_status():
    """Tusita feature flags and aggregate stats."""
    stats = {}
    if settings.tusita_enabled:
        try:
            stats = await get_location_stats()
        except Exception:
            stats = {"error": "stats unavailable"}
    return {
        "enabled": settings.tusita_enabled,
        "phase": "0",
        "phase_description": (
            "Location registry + booking management. "
            "No availability engine or payment processing yet."
        ),
        "features": {
            "location_registry": True,
            "booking_management": True,
            "revenue_tracking": True,
            "availability_engine": False,   # Phase 2
            "payment_processing": False,    # Phase 2
        },
        "stats": stats,
    }


@router.post("/locations", status_code=201)
async def create_location_route(req: CreateLocationRequest):
    """Register a new Tusita location (dome or community site)."""
    _require_enabled()
    try:
        location = await create_location(
            name=req.name,
            slug=req.slug,
            description=req.description,
            country=req.country,
            region=req.region,
            coordinates=req.coordinates,
            dome_type=req.dome_type,
            capacity=req.capacity,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return location


@router.get("/locations")
async def list_locations_route(
    status: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    dome_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List Tusita locations with optional filters."""
    _require_enabled()
    return await list_locations(status=status, country=country, dome_type=dome_type, limit=limit)


@router.get("/locations/by-slug/{slug}")
async def get_location_by_slug_route(slug: str):
    """Look up a Tusita location by slug."""
    _require_enabled()
    location = await get_location_by_slug(slug)
    if not location:
        raise HTTPException(status_code=404, detail=f"Location not found: {slug}")
    return location


@router.get("/locations/{location_id}")
async def get_location_route(location_id: UUID):
    """Fetch a single Tusita location."""
    _require_enabled()
    location = await get_location(str(location_id))
    if not location:
        raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")
    return location


@router.put("/locations/{location_id}/status")
async def update_location_status_route(location_id: UUID, req: UpdateStatusRequest):
    """Update a location's operational status."""
    _require_enabled()
    try:
        updated = await update_location_status(str(location_id), req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")
    return updated


@router.post("/locations/{location_id}/revenue")
async def record_revenue_route(location_id: UUID, req: RecordRevenueRequest):
    """Record revenue for a location (adds to year-to-date total)."""
    _require_enabled()
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    updated = await record_revenue(str(location_id), req.amount)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Location not found: {location_id}")
    return updated


@router.post("/bookings", status_code=201)
async def create_booking_route(req: CreateBookingRequest):
    """Create a new Tusita booking."""
    _require_enabled()
    try:
        booking = await create_booking(
            location_id=str(req.location_id),
            guest_name=req.guest_name,
            check_in=req.check_in,
            check_out=req.check_out,
            booking_type=req.booking_type,
            guest_email=req.guest_email,
            guest_handle=req.guest_handle,
            party_size=req.party_size,
            total_amount=req.total_amount,
            currency=req.currency,
            notes=req.notes,
            metadata=req.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return booking


@router.get("/bookings")
async def list_bookings_route(
    location_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    booking_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """List bookings with optional filters."""
    _require_enabled()
    return await list_bookings(
        location_id=str(location_id) if location_id else None,
        status=status,
        booking_type=booking_type,
        limit=limit,
    )


@router.get("/bookings/{booking_id}")
async def get_booking_route(booking_id: UUID):
    """Fetch a single Tusita booking."""
    _require_enabled()
    booking = await get_booking(str(booking_id))
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking not found: {booking_id}")
    return booking


@router.put("/bookings/{booking_id}/status")
async def update_booking_status_route(booking_id: UUID, req: UpdateStatusRequest):
    """Update a booking's status (confirm, cancel, complete)."""
    _require_enabled()
    try:
        updated = await update_booking_status(str(booking_id), req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail=f"Booking not found: {booking_id}")
    return updated

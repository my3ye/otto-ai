"""Tusita Bookings CRUD — guest and resident booking management."""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.tusita.bookings")

VALID_STATUSES = ("pending", "confirmed", "cancelled", "completed")
VALID_TYPES = ("visitor", "resident", "retreat", "volunteer")


async def create_booking(
    location_id: str,
    guest_name: str,
    check_in: date,
    check_out: date,
    booking_type: str = "visitor",
    guest_email: Optional[str] = None,
    guest_handle: Optional[str] = None,
    party_size: int = 1,
    total_amount: Optional[float] = None,
    currency: str = "USD",
    notes: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a new Tusita booking."""
    if booking_type not in VALID_TYPES:
        raise ValueError(f"Invalid booking_type: {booking_type}")
    if check_out <= check_in:
        raise ValueError("check_out must be after check_in")
    if party_size < 1:
        raise ValueError("party_size must be at least 1")

    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO tusita_bookings
            (location_id, guest_name, guest_email, guest_handle,
             check_in, check_out, party_size, booking_type,
             status, total_amount, currency, notes, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', $9, $10, $11, $12)
        RETURNING *
    """, UUID(location_id), guest_name, guest_email,
        guest_handle.lstrip("@").lower() if guest_handle else None,
        check_in, check_out, party_size, booking_type,
        total_amount, currency, notes, metadata or {})

    log.info(f"Tusita booking created: {row['id']} at {location_id}")
    return dict(row)


async def get_booking(booking_id: str) -> Optional[dict]:
    """Fetch a booking by UUID, with location info."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        SELECT b.*, l.name as location_name, l.slug as location_slug
        FROM tusita_bookings b
        JOIN tusita_locations l ON l.id = b.location_id
        WHERE b.id = $1
    """, UUID(booking_id))
    return dict(row) if row else None


async def list_bookings(
    location_id: Optional[str] = None,
    status: Optional[str] = None,
    booking_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List bookings with optional filters."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if location_id:
        args.append(UUID(location_id))
        conditions.append(f"b.location_id = ${len(args)}")
    if status:
        args.append(status)
        conditions.append(f"b.status = ${len(args)}")
    if booking_type:
        args.append(booking_type)
        conditions.append(f"b.booking_type = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.append(limit)

    rows = await pool.fetch(f"""
        SELECT b.*, l.name as location_name, l.slug as location_slug
        FROM tusita_bookings b
        JOIN tusita_locations l ON l.id = b.location_id
        {where}
        ORDER BY b.check_in ASC, b.created_at DESC
        LIMIT ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def update_booking_status(
    booking_id: str,
    status: str,
) -> Optional[dict]:
    """Update a booking's status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    pool = await get_pool()
    row = await pool.fetchrow("""
        UPDATE tusita_bookings
        SET status = $2, updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """, UUID(booking_id), status)
    return dict(row) if row else None

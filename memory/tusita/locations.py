"""Tusita Location CRUD — dome registry and revenue tracking."""

import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.tusita.locations")

VALID_STATUSES = ("planned", "construction", "operational", "closed")
VALID_DOME_TYPES = ("community", "meditation", "worship", "visitor_center", "accommodation")


async def create_location(
    name: str,
    slug: str,
    description: Optional[str] = None,
    country: Optional[str] = None,
    region: Optional[str] = None,
    coordinates: Optional[dict] = None,
    dome_type: str = "community",
    capacity: int = 0,
    metadata: Optional[dict] = None,
) -> dict:
    """Register a new Tusita location (dome/community site)."""
    if dome_type not in VALID_DOME_TYPES:
        raise ValueError(f"Invalid dome_type: {dome_type}")

    pool = await get_pool()
    try:
        row = await pool.fetchrow("""
            INSERT INTO tusita_locations
                (name, slug, description, country, region, coordinates,
                 dome_type, capacity, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, name, slug.lower(), description, country, region,
            coordinates or {}, dome_type, capacity, metadata or {})
    except Exception as e:
        if "unique" in str(e).lower():
            raise ValueError(f"Location slug already exists: {slug}")
        raise

    log.info(f"Tusita location created: {row['id']} ({name})")
    return dict(row)


async def get_location(location_id: str) -> Optional[dict]:
    """Fetch a location by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM tusita_locations WHERE id = $1",
        UUID(location_id),
    )
    return dict(row) if row else None


async def get_location_by_slug(slug: str) -> Optional[dict]:
    """Fetch a location by slug."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM tusita_locations WHERE slug = $1",
        slug.lower(),
    )
    return dict(row) if row else None


async def list_locations(
    status: Optional[str] = None,
    country: Optional[str] = None,
    dome_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List Tusita locations with optional filters."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if status:
        args.append(status)
        conditions.append(f"status = ${len(args)}")
    if country:
        args.append(country)
        conditions.append(f"country = ${len(args)}")
    if dome_type:
        args.append(dome_type)
        conditions.append(f"dome_type = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.append(limit)

    rows = await pool.fetch(f"""
        SELECT l.*,
            (SELECT COUNT(*) FROM tusita_bookings b
             WHERE b.location_id = l.id AND b.status != 'cancelled') as active_bookings
        FROM tusita_locations l
        {where}
        ORDER BY l.created_at DESC
        LIMIT ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def update_location_status(
    location_id: str,
    status: str,
    opened_at: Optional[str] = None,
) -> Optional[dict]:
    """Update location status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    pool = await get_pool()
    row = await pool.fetchrow("""
        UPDATE tusita_locations
        SET status = $2,
            updated_at = NOW(),
            opened_at = CASE WHEN $2 = 'operational' AND opened_at IS NULL THEN NOW() ELSE opened_at END
        WHERE id = $1
        RETURNING *
    """, UUID(location_id), status)
    return dict(row) if row else None


async def record_revenue(location_id: str, amount: float) -> Optional[dict]:
    """Add to location's cumulative revenue total."""
    pool = await get_pool()
    row = await pool.fetchrow("""
        UPDATE tusita_locations
        SET revenue_total = revenue_total + $2, updated_at = NOW()
        WHERE id = $1
        RETURNING *
    """, UUID(location_id), amount)
    return dict(row) if row else None


async def get_location_stats() -> dict:
    """Aggregate statistics across all Tusita locations."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT status, COUNT(*) as count, SUM(capacity) as total_capacity,
               SUM(revenue_total) as total_revenue
        FROM tusita_locations
        GROUP BY status
    """)
    return {
        "by_status": {
            r["status"]: {
                "count": r["count"],
                "capacity": r["total_capacity"] or 0,
                "revenue_total": float(r["total_revenue"] or 0),
            }
            for r in rows
        }
    }

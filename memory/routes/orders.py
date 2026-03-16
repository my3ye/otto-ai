"""
WebAssist Orders API — manual payment flow.
POST /orders — client submits order
GET /orders — admin lists all orders
GET /orders/{id} — single order detail
PATCH /orders/{id}/status — admin confirms/cancels payment
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

from ..db import get_pool

router = APIRouter(prefix="/orders", tags=["orders"])


# ── Pydantic models ──────────────────────────────────────────────────────────


class OrderCreate(BaseModel):
    client_name: str
    client_email: str
    business_name: str
    requirements: Optional[str] = None
    amount_usd: float = 499.00
    currency: str = "USD"
    payment_method: Optional[str] = None  # bank | wise | crypto | pending


class OrderStatusUpdate(BaseModel):
    payment_status: str  # pending | confirmed | cancelled
    payment_method: Optional[str] = None
    admin_notes: Optional[str] = None
    confirmed_by: Optional[str] = "admin"


# ── Helpers ──────────────────────────────────────────────────────────────────


def _row_to_dict(row) -> dict:
    d = dict(row)
    # Serialize UUIDs and datetimes
    for k, v in d.items():
        if isinstance(v, UUID):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


# ── Routes ───────────────────────────────────────────────────────────────────


@router.post("")
async def create_order(body: OrderCreate):
    """Client submits an order. Returns the created order with id."""
    pool = await get_pool()

    row = await pool.fetchrow(
        """
        INSERT INTO webassist_orders
            (client_name, client_email, business_name, requirements,
             amount_usd, currency, payment_method)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        body.client_name,
        body.client_email,
        body.business_name,
        body.requirements,
        body.amount_usd,
        body.currency,
        body.payment_method or "pending",
    )
    return _row_to_dict(row)


@router.get("")
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by payment_status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Admin: list all orders, optionally filtered by status."""
    pool = await get_pool()

    where_clauses = []
    params = []
    idx = 1

    if status:
        where_clauses.append(f"payment_status = ${idx}")
        params.append(status)
        idx += 1

    where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    rows = await pool.fetch(
        f"""
        SELECT * FROM webassist_orders
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        limit,
        offset,
    )

    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM webassist_orders {where_sql}",
        *params,
    )

    # Stats
    stats_rows = await pool.fetch(
        """
        SELECT payment_status, COUNT(*) as count, SUM(amount_usd) as total_usd
        FROM webassist_orders
        GROUP BY payment_status
        """
    )
    stats = {r["payment_status"]: {"count": r["count"], "total_usd": float(r["total_usd"] or 0)} for r in stats_rows}

    return {
        "orders": [_row_to_dict(r) for r in rows],
        "total": total,
        "offset": offset,
        "limit": limit,
        "stats": stats,
    }


@router.get("/{order_id}")
async def get_order(order_id: str):
    """Get a single order by ID."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT * FROM webassist_orders WHERE id = $1",
        order_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return _row_to_dict(row)


@router.patch("/{order_id}/status")
async def update_order_status(order_id: str, body: OrderStatusUpdate):
    """Admin confirms or cancels a payment."""
    valid_statuses = {"pending", "confirmed", "cancelled"}
    if body.payment_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    pool = await get_pool()

    confirmed_at = datetime.now(timezone.utc) if body.payment_status == "confirmed" else None

    row = await pool.fetchrow(
        """
        UPDATE webassist_orders SET
            payment_status = $1,
            payment_method  = COALESCE($2, payment_method),
            admin_notes     = COALESCE($3, admin_notes),
            confirmed_by    = CASE WHEN $1 = 'confirmed' THEN $4 ELSE confirmed_by END,
            confirmed_at    = CASE WHEN $1 = 'confirmed' THEN $5 ELSE confirmed_at END,
            updated_at      = NOW()
        WHERE id = $6
        RETURNING *
        """,
        body.payment_status,
        body.payment_method,
        body.admin_notes,
        body.confirmed_by,
        confirmed_at,
        order_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Order not found")
    return _row_to_dict(row)

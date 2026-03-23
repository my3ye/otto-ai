"""SOS Systems Case Management — refuge/displacement case tracking."""

import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.sos.cases")

VALID_STATUSES = ("open", "in_review", "matched", "resolved", "closed")
VALID_TYPES = ("general", "war_zone", "homelessness", "underprivileged")
VALID_URGENCY = ("standard", "urgent", "critical")


async def create_case(
    requester_name: str,
    description: str,
    case_type: str = "general",
    urgency: str = "standard",
    requester_email: Optional[str] = None,
    location: Optional[str] = None,
    tusita_ref: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Open a new SOS case."""
    if case_type not in VALID_TYPES:
        raise ValueError(f"Invalid case_type: {case_type}")
    if urgency not in VALID_URGENCY:
        raise ValueError(f"Invalid urgency: {urgency}")

    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO sos_cases
            (case_type, requester_name, requester_email, location,
             description, urgency, status, tusita_ref, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, 'open', $7, $8)
        RETURNING *
    """, case_type, requester_name, requester_email, location,
        description, urgency,
        UUID(tusita_ref) if tusita_ref else None,
        metadata or {})

    log.info(f"SOS case created: {row['id']} (type={case_type}, urgency={urgency})")
    return dict(row)


async def get_case(case_id: str) -> Optional[dict]:
    """Fetch a case by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sos_cases WHERE id = $1",
        UUID(case_id),
    )
    return dict(row) if row else None


async def list_cases(
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    urgency: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List SOS cases with optional filters."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if status:
        args.append(status)
        conditions.append(f"c.status = ${len(args)}")
    if case_type:
        args.append(case_type)
        conditions.append(f"c.case_type = ${len(args)}")
    if urgency:
        args.append(urgency)
        conditions.append(f"c.urgency = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.append(limit)
    args.append(offset)

    rows = await pool.fetch(f"""
        SELECT c.*,
            l.handle as learner_handle,
            a.handle as handler_handle
        FROM sos_cases c
        LEFT JOIN sos_learners l ON l.id = c.learner_id
        LEFT JOIN sos_learners a ON a.id = c.assigned_to
        {where}
        ORDER BY
            CASE c.urgency WHEN 'critical' THEN 1 WHEN 'urgent' THEN 2 ELSE 3 END ASC,
            c.created_at DESC
        LIMIT ${len(args) - 1}
        OFFSET ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def update_case_status(
    case_id: str,
    status: str,
    notes: Optional[str] = None,
    tusita_ref: Optional[str] = None,
    learner_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
) -> Optional[dict]:
    """Update a case's status and optionally set resolution details."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    pool = await get_pool()
    updates = ["status = $2", "updated_at = NOW()"]
    args: list = [UUID(case_id), status]

    if notes is not None:
        args.append(notes)
        updates.append(f"notes = ${len(args)}")
    if tusita_ref is not None:
        args.append(UUID(tusita_ref))
        updates.append(f"tusita_ref = ${len(args)}")
    if learner_id is not None:
        args.append(UUID(learner_id))
        updates.append(f"learner_id = ${len(args)}")
    if assigned_to is not None:
        args.append(UUID(assigned_to))
        updates.append(f"assigned_to = ${len(args)}")
    if status in ("resolved", "closed"):
        updates.append("resolved_at = COALESCE(resolved_at, NOW())")

    set_clause = ", ".join(updates)
    row = await pool.fetchrow(f"""
        UPDATE sos_cases SET {set_clause}
        WHERE id = $1
        RETURNING *
    """, *args)
    if row:
        log.info(f"SOS case {case_id} updated to status: {status}")
    return dict(row) if row else None


async def get_case_stats() -> dict:
    """Aggregate stats for SOS cases."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT status, urgency, COUNT(*) as count
        FROM sos_cases
        GROUP BY status, urgency
    """)
    total = await pool.fetchval("SELECT COUNT(*) FROM sos_cases")
    return {
        "total": total,
        "breakdown": [{"status": r["status"], "urgency": r["urgency"], "count": r["count"]} for r in rows],
    }

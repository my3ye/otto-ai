"""Unified Content Calendar — scheduling layer over the content table.

Each slot = one publishing action on one platform on one date.
One content item can have multiple slots (article on Paragraph + tweet about it).
"""

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_pool

log = logging.getLogger("otto.calendar")
router = APIRouter(prefix="/content-calendar", tags=["content-calendar"])

# ── Pydantic Models ─────────────────────────────────────────────


class SlotCreate(BaseModel):
    content_id: str
    slot_date: str  # YYYY-MM-DD
    platform: str = "paragraph"
    action: str = "publish"
    slot_position: Optional[int] = None
    pinned: bool = False
    notes: Optional[str] = None


class SlotUpdate(BaseModel):
    slot_date: Optional[str] = None
    platform: Optional[str] = None
    action: Optional[str] = None
    status: Optional[str] = None
    slot_position: Optional[int] = None
    pinned: Optional[bool] = None
    notes: Optional[str] = None


class SlotPostMark(BaseModel):
    posted_by: str = "mev"


class ReorderRequest(BaseModel):
    slot_ids: List[str]


class GenerateRequest(BaseModel):
    date_from: str
    date_to: str
    strategy: str = "balanced"  # Only "balanced" is implemented currently


# ── Helpers ─────────────────────────────────────────────────────


SLOT_QUERY = """
SELECT
    cs.id, cs.content_id, cs.slot_date, cs.slot_position,
    cs.platform, cs.action, cs.status, cs.posted_at, cs.posted_by,
    cs.notes, cs.pinned, cs.created_at, cs.updated_at,
    c.title, c.content_type, c.status AS content_status,
    c.project_id, c.character, c.tags,
    LEFT(c.body, 200) AS body_preview
FROM calendar_slots cs
JOIN content c ON c.id = cs.content_id
WHERE c.archived = FALSE
"""


def _row_to_slot(row) -> dict:
    return {
        "id": str(row["id"]),
        "content_id": str(row["content_id"]),
        "slot_date": row["slot_date"].isoformat(),
        "slot_position": row["slot_position"],
        "platform": row["platform"],
        "action": row["action"],
        "status": row["status"],
        "posted_at": row["posted_at"].isoformat() if row["posted_at"] else None,
        "posted_by": row["posted_by"],
        "notes": row["notes"],
        "pinned": row["pinned"],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "content": {
            "id": str(row["content_id"]),
            "title": row["title"],
            "content_type": row["content_type"],
            "status": row["content_status"],
            "project_id": row["project_id"],
            "character": row["character"],
            "tags": row["tags"] or [],
            "body_preview": row["body_preview"] or "",
        },
    }


# ── Endpoints ───────────────────────────────────────────────────


@router.get("/slots")
async def list_slots(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    """List calendar slots with optional date range, platform, status filters."""
    pool = await get_pool()
    conditions = []
    params = []
    idx = 1

    try:
        if date_from:
            conditions.append(f"cs.slot_date >= ${idx}")
            params.append(date.fromisoformat(date_from))
            idx += 1
        if date_to:
            conditions.append(f"cs.slot_date <= ${idx}")
            params.append(date.fromisoformat(date_to))
            idx += 1
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format — use YYYY-MM-DD")
    if platform:
        platforms = [p.strip() for p in platform.split(",")]
        conditions.append(f"cs.platform = ANY(${idx}::text[])")
        params.append(platforms)
        idx += 1
    if status:
        statuses = [s.strip() for s in status.split(",")]
        conditions.append(f"cs.status = ANY(${idx}::text[])")
        params.append(statuses)
        idx += 1

    where = ""
    if conditions:
        where = " AND " + " AND ".join(conditions)

    query = (
        SLOT_QUERY
        + where
        + " ORDER BY cs.slot_date ASC, cs.pinned DESC, cs.slot_position ASC"
    )
    rows = await pool.fetch(query, *params)
    return {"slots": [_row_to_slot(r) for r in rows], "count": len(rows)}


@router.get("/today")
async def get_today():
    """Get today's slots + pinned queue, priority-ordered."""
    pool = await get_pool()
    today = date.today()

    query = (
        SLOT_QUERY
        + " AND (cs.slot_date = $1 OR cs.pinned = TRUE)"
        + " ORDER BY cs.pinned DESC, "
        + "CASE WHEN c.status = 'ready' THEN 0 "
        + "WHEN c.status = 'published' THEN 1 "
        + "ELSE 2 END, "
        + "cs.slot_position ASC"
    )
    rows = await pool.fetch(query, today)
    slots = [_row_to_slot(r) for r in rows]

    pinned = [s for s in slots if s["pinned"]]
    scheduled = [s for s in slots if not s["pinned"]]

    stats = {
        "total": len(slots),
        "ready": sum(1 for s in slots if s["status"] == "ready"),
        "posted": sum(1 for s in slots if s["status"] == "posted"),
        "queued": sum(1 for s in slots if s["status"] == "queued"),
    }

    return {
        "date": today.isoformat(),
        "pinned": pinned,
        "scheduled": scheduled,
        "stats": stats,
    }


@router.get("/queue")
async def get_queue(days: int = Query(7, ge=1, le=90)):
    """Get the next N days of scheduled slots, priority-ordered per day."""
    pool = await get_pool()
    today = date.today()
    end_date = today + timedelta(days=days)

    query = (
        SLOT_QUERY
        + " AND cs.slot_date >= $1 AND cs.slot_date <= $2"
        + " ORDER BY cs.slot_date ASC, cs.pinned DESC, cs.slot_position ASC"
    )
    rows = await pool.fetch(query, today, end_date)

    # Group by date, include empty-day markers
    by_date: dict[str, list] = defaultdict(list)
    for r in rows:
        by_date[r["slot_date"].isoformat()].append(_row_to_slot(r))

    result = []
    current = today
    while current <= end_date:
        ds = current.isoformat()
        result.append({
            "date": ds,
            "slots": by_date.get(ds, []),
            "count": len(by_date.get(ds, [])),
        })
        current += timedelta(days=1)

    return {"days": result, "total_slots": len(rows)}


@router.get("/stats")
async def get_stats(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Coverage stats — days with slots, gaps, posts per project."""
    pool = await get_pool()

    conditions = []
    params = []
    idx = 1
    try:
        if date_from:
            conditions.append(f"cs.slot_date >= ${idx}")
            params.append(date.fromisoformat(date_from))
            idx += 1
        if date_to:
            conditions.append(f"cs.slot_date <= ${idx}")
            params.append(date.fromisoformat(date_to))
            idx += 1
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format — use YYYY-MM-DD")

    where = ""
    if conditions:
        where = " AND " + " AND ".join(conditions)

    # Counts per date
    q1 = f"""
    SELECT cs.slot_date,
           COUNT(*) as total,
           SUM(CASE WHEN cs.status = 'posted' THEN 1 ELSE 0 END) as posted,
           SUM(CASE WHEN cs.status = 'ready' THEN 1 ELSE 0 END) as ready,
           SUM(CASE WHEN cs.status = 'queued' THEN 1 ELSE 0 END) as queued
    FROM calendar_slots cs
    JOIN content c ON c.id = cs.content_id
    WHERE c.archived = FALSE {where}
    GROUP BY cs.slot_date ORDER BY cs.slot_date
    """
    rows = await pool.fetch(q1, *params)

    dates = {}
    for r in rows:
        dates[r["slot_date"].isoformat()] = {
            "total": r["total"],
            "posted": r["posted"],
            "ready": r["ready"],
            "queued": r["queued"],
        }

    # Coverage calculation
    if dates:
        all_dates = sorted(dates.keys())
        first = date.fromisoformat(all_dates[0])
        last = date.fromisoformat(all_dates[-1])
        total_days = (last - first).days + 1
        days_with_slots = len(dates)

        gap_days = []
        current = first
        while current <= last:
            if current.isoformat() not in dates:
                gap_days.append(current.isoformat())
            current += timedelta(days=1)
    else:
        total_days = 0
        days_with_slots = 0
        gap_days = []

    # Per-project counts
    q2 = f"""
    SELECT c.project_id, COUNT(*) as count
    FROM calendar_slots cs
    JOIN content c ON c.id = cs.content_id
    WHERE c.archived = FALSE {where}
    GROUP BY c.project_id ORDER BY count DESC
    """
    proj_rows = await pool.fetch(q2, *params)
    by_project = {r["project_id"] or "unassigned": r["count"] for r in proj_rows}

    # Per-platform counts
    q3 = f"""
    SELECT cs.platform, COUNT(*) as count
    FROM calendar_slots cs
    JOIN content c ON c.id = cs.content_id
    WHERE c.archived = FALSE {where}
    GROUP BY cs.platform ORDER BY count DESC
    """
    plat_rows = await pool.fetch(q3, *params)
    by_platform = {r["platform"]: r["count"] for r in plat_rows}

    return {
        "dates": dates,
        "coverage": {
            "days_with_slots": days_with_slots,
            "total_days": total_days,
            "gap_days": gap_days[:30],  # Limit for response size
        },
        "by_project": by_project,
        "by_platform": by_platform,
    }


@router.post("/slots")
async def create_slot(body: SlotCreate):
    """Create a calendar slot for a content item."""
    pool = await get_pool()

    # Validate inputs
    try:
        content_uuid = UUID(body.content_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid content_id — must be a UUID")
    try:
        slot_date_obj = date.fromisoformat(body.slot_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid slot_date — use YYYY-MM-DD")

    # Verify content exists
    content = await pool.fetchrow(
        "SELECT id FROM content WHERE id = $1 AND archived = FALSE",
        content_uuid,
    )
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    # Use transaction to prevent TOCTOU race on auto-position
    async with pool.acquire() as conn:
        async with conn.transaction():
            position = body.slot_position
            if position is None:
                row = await conn.fetchrow(
                    "SELECT COALESCE(MAX(slot_position), -1) + 1 AS next_pos "
                    "FROM calendar_slots WHERE slot_date = $1 FOR UPDATE",
                    slot_date_obj,
                )
                position = row["next_pos"]

            try:
                slot_id = await conn.fetchval(
                    """INSERT INTO calendar_slots
                       (content_id, slot_date, slot_position, platform, action, pinned, notes)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)
                       RETURNING id""",
                    content_uuid,
                    slot_date_obj,
                    position,
                    body.platform,
                    body.action,
                    body.pinned,
                    body.notes,
                )
            except Exception as e:
                if "unique" in str(e).lower():
                    raise HTTPException(
                        status_code=409,
                        detail="Slot already exists for this content/date/platform",
                    )
                raise

    # Return created slot with content join
    row = await pool.fetchrow(SLOT_QUERY + " AND cs.id = $1", slot_id)
    return _row_to_slot(row)


@router.put("/slots/{slot_id}")
async def update_slot(slot_id: UUID, body: SlotUpdate):
    """Update a calendar slot (partial update)."""
    pool = await get_pool()

    updates = []
    params = []
    idx = 1

    for field in ["slot_date", "platform", "action", "status", "slot_position", "pinned", "notes"]:
        val = getattr(body, field, None)
        if val is not None:
            updates.append(f"{field} = ${idx}")
            if field == "slot_date":
                try:
                    params.append(date.fromisoformat(val))
                except ValueError:
                    raise HTTPException(status_code=422, detail="Invalid slot_date — use YYYY-MM-DD")
            else:
                params.append(val)
            idx += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    params.append(slot_id)
    query = f"UPDATE calendar_slots SET {', '.join(updates)} WHERE id = ${idx} RETURNING id"

    result = await pool.fetchval(query, *params)
    if not result:
        raise HTTPException(status_code=404, detail="Slot not found")

    row = await pool.fetchrow(SLOT_QUERY + " AND cs.id = $1", slot_id)
    return _row_to_slot(row)


@router.delete("/slots/{slot_id}")
async def delete_slot(slot_id: UUID):
    """Remove a calendar slot (doesn't touch the content item)."""
    pool = await get_pool()
    result = await pool.execute(
        "DELETE FROM calendar_slots WHERE id = $1", slot_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Slot not found")
    return {"ok": True}


@router.post("/slots/{slot_id}/post")
async def mark_posted(slot_id: UUID, body: SlotPostMark = SlotPostMark()):
    """Mark a slot as posted."""
    pool = await get_pool()
    result = await pool.fetchval(
        """UPDATE calendar_slots
           SET status = 'posted', posted_at = NOW(), posted_by = $2
           WHERE id = $1 RETURNING id""",
        slot_id,
        body.posted_by,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Slot not found")

    row = await pool.fetchrow(SLOT_QUERY + " AND cs.id = $1", slot_id)
    return _row_to_slot(row)


@router.post("/slots/reorder")
async def reorder_slots(body: ReorderRequest):
    """Reorder slots within a day by array position."""
    pool = await get_pool()
    if not body.slot_ids:
        raise HTTPException(status_code=400, detail="slot_ids required")

    async with pool.acquire() as conn:
        async with conn.transaction():
            for i, sid in enumerate(body.slot_ids):
                await conn.execute(
                    "UPDATE calendar_slots SET slot_position = $1 WHERE id = $2",
                    i,
                    UUID(sid),
                )
    return {"ok": True, "count": len(body.slot_ids)}


@router.post("/generate")
async def generate_schedule(body: GenerateRequest, commit: bool = Query(False)):
    """Auto-generate slots for unscheduled content. Returns preview unless commit=true."""
    pool = await get_pool()

    try:
        date_from = date.fromisoformat(body.date_from)
        date_to = date.fromisoformat(body.date_to)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format — use YYYY-MM-DD")

    # Get unscheduled content (not in any calendar slot)
    rows = await pool.fetch("""
        SELECT c.id, c.title, c.content_type, c.project_id, c.status, c.tags
        FROM content c
        WHERE c.archived = FALSE
          AND c.status IN ('ready', 'draft')
          AND c.id NOT IN (SELECT content_id FROM calendar_slots)
        ORDER BY
          CASE WHEN c.status = 'ready' THEN 0 ELSE 1 END,
          c.created_at ASC
    """)

    if not rows:
        return {"preview": [], "total": 0, "message": "No unscheduled content to assign"}

    # Simple balanced strategy: round-robin across dates
    # Articles on weekdays, social on any day
    articles = [r for r in rows if r["content_type"] == "article"]
    social = [r for r in rows if r["content_type"] == "social_post"]
    other = [r for r in rows if r["content_type"] not in ("article", "social_post")]

    preview = []
    current = date_from
    article_idx = 0
    social_idx = 0
    other_idx = 0

    while current <= date_to:
        is_weekday = current.weekday() < 5

        # 1 article per weekday
        if is_weekday and article_idx < len(articles):
            art = articles[article_idx]
            preview.append({
                "content_id": str(art["id"]),
                "title": art["title"],
                "content_type": art["content_type"],
                "slot_date": current.isoformat(),
                "platform": "paragraph",
                "action": "publish",
            })
            article_idx += 1

        # 1-2 social posts per day
        if social_idx < len(social):
            sp = social[social_idx]
            preview.append({
                "content_id": str(sp["id"]),
                "title": sp["title"],
                "content_type": sp["content_type"],
                "slot_date": current.isoformat(),
                "platform": "x",
                "action": "publish",
            })
            social_idx += 1

        # Other content on weekdays
        if is_weekday and other_idx < len(other):
            ot = other[other_idx]
            preview.append({
                "content_id": str(ot["id"]),
                "title": ot["title"],
                "content_type": ot["content_type"],
                "slot_date": current.isoformat(),
                "platform": "paragraph",
                "action": "publish",
            })
            other_idx += 1

        current += timedelta(days=1)

    if commit and preview:
        async with pool.acquire() as conn:
            async with conn.transaction():
                for i, item in enumerate(preview):
                    # Auto-position
                    sd = date.fromisoformat(item["slot_date"])
                    pos_row = await conn.fetchrow(
                        "SELECT COALESCE(MAX(slot_position), -1) + 1 AS p "
                        "FROM calendar_slots WHERE slot_date = $1",
                        sd,
                    )
                    try:
                        await conn.execute(
                            """INSERT INTO calendar_slots
                               (content_id, slot_date, slot_position, platform, action)
                               VALUES ($1, $2, $3, $4, $5)
                               ON CONFLICT DO NOTHING""",
                            UUID(item["content_id"]),
                            sd,
                            pos_row["p"],
                            item["platform"],
                            item["action"],
                        )
                    except Exception:
                        pass  # Skip conflicts

    return {
        "preview": preview,
        "total": len(preview),
        "committed": commit,
        "message": f"{'Committed' if commit else 'Preview'}: {len(preview)} slots",
    }

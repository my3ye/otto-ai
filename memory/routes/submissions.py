"""
Submissions API routes — unified view of landing page form submissions.

Reads from the projects DB (port 5433) which stores:
- waitlist_entries: waitlist signups from landing pages
- project_contacts: contact form submissions
"""

import logging
from typing import Optional

import asyncpg
from fastapi import APIRouter, Query

logger = logging.getLogger("otto.routes.submissions")

router = APIRouter(prefix="/submissions", tags=["submissions"])

# ── Projects DB connection ────────────────────────────────────────────────────

PROJECTS_DB_DSN = "postgresql://projects:projects_pass@localhost:5433/projects"
_projects_pool: asyncpg.Pool | None = None


async def _get_projects_pool() -> asyncpg.Pool:
    global _projects_pool
    if _projects_pool is None or _projects_pool._closed:
        _projects_pool = await asyncpg.create_pool(PROJECTS_DB_DSN, min_size=1, max_size=3)
    return _projects_pool


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_submissions(
    source: Optional[str] = Query(None, description="Filter by project slug"),
    type: Optional[str] = Query(None, description="Filter by type: waitlist or contact"),
    search: Optional[str] = Query(None, description="Search name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List all submissions across waitlist entries and contact forms."""
    pool = await _get_projects_pool()

    # Build unified query combining both tables
    parts = []
    params: list = []

    # Waitlist entries
    if type is None or type == "waitlist":
        wl_conditions = ["TRUE"]
        if source:
            params.append(source)
            wl_conditions.append(f"w.project_slug = ${len(params)}")
        if search:
            params.append(f"%{search}%")
            idx = len(params)
            wl_conditions.append(f"(w.name ILIKE ${idx} OR w.email ILIKE ${idx})")

        wl_where = " AND ".join(wl_conditions)
        parts.append(f"""
            SELECT
                w.id::text,
                w.email,
                COALESCE(w.name, '') as name,
                '' as message,
                w.project_slug as source,
                'waitlist' as submission_type,
                w.source as form_source,
                w.created_at
            FROM waitlist_entries w
            WHERE {wl_where}
        """)

    # Contact submissions
    if type is None or type == "contact":
        ct_conditions = ["TRUE"]
        if source:
            params.append(source)
            ct_conditions.append(f"c.project_slug = ${len(params)}")
        if search:
            params.append(f"%{search}%")
            idx = len(params)
            ct_conditions.append(f"(c.name ILIKE ${idx} OR c.email ILIKE ${idx})")

        ct_where = " AND ".join(ct_conditions)
        parts.append(f"""
            SELECT
                c.id::text,
                c.email,
                COALESCE(c.name, '') as name,
                COALESCE(c.message, '') as message,
                c.project_slug as source,
                'contact' as submission_type,
                c.contact_type as form_source,
                c.created_at
            FROM project_contacts c
            WHERE {ct_where}
        """)

    if not parts:
        return {"total": 0, "submissions": [], "offset": offset, "limit": limit}

    union_query = " UNION ALL ".join(parts)

    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({union_query}) sub"
    total = await pool.fetchval(count_query, *params)

    # Get paginated results
    data_query = f"""
        SELECT * FROM ({union_query}) sub
        ORDER BY created_at DESC
        LIMIT {limit} OFFSET {offset}
    """
    rows = await pool.fetch(data_query, *params)

    return {
        "total": total,
        "submissions": [dict(r) for r in rows],
        "offset": offset,
        "limit": limit,
    }


@router.get("/stats")
async def submission_stats():
    """Summary statistics for all submissions."""
    pool = await _get_projects_pool()

    # Waitlist counts by project
    wl_by_project = await pool.fetch("""
        SELECT project_slug, COUNT(*) as count
        FROM waitlist_entries
        GROUP BY project_slug
        ORDER BY count DESC
    """)

    # Contact counts by project
    ct_by_project = await pool.fetch("""
        SELECT project_slug, COUNT(*) as count
        FROM project_contacts
        GROUP BY project_slug
        ORDER BY count DESC
    """)

    # Totals
    wl_total = await pool.fetchval("SELECT COUNT(*) FROM waitlist_entries")
    ct_total = await pool.fetchval("SELECT COUNT(*) FROM project_contacts")

    # Recent (last 7 days)
    recent_wl = await pool.fetchval(
        "SELECT COUNT(*) FROM waitlist_entries WHERE created_at > NOW() - INTERVAL '7 days'"
    )
    recent_ct = await pool.fetchval(
        "SELECT COUNT(*) FROM project_contacts WHERE created_at > NOW() - INTERVAL '7 days'"
    )

    # Available projects
    projects = await pool.fetch("SELECT slug, name, status FROM projects ORDER BY name")

    return {
        "total": wl_total + ct_total,
        "waitlist_total": wl_total,
        "contacts_total": ct_total,
        "recent_7d": recent_wl + recent_ct,
        "waitlist_by_project": [dict(r) for r in wl_by_project],
        "contacts_by_project": [dict(r) for r in ct_by_project],
        "projects": [dict(r) for r in projects],
    }


@router.get("/projects")
async def list_projects():
    """List available projects for filtering."""
    pool = await _get_projects_pool()
    rows = await pool.fetch("SELECT slug, name, status, waitlist_open FROM projects ORDER BY name")
    return [dict(r) for r in rows]

"""
Landing Pages API — CRUD for generated landing page entities.
Workflow orchestration is separate; this table tracks the product lifecycle.

Research endpoints (standalone — also called by workflow steps):
  POST /landing-pages/research/business      → research_business()
  POST /landing-pages/research/competitors   → research_competitors()
"""

import json
import re
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_pool
from ..models import (
    LandingPageCreate,
    LandingPageOut,
    LandingPageListItem,
    LandingPageStatusUpdate,
    LandingPageDataUpdate,
)
from ..services.landing_page.research import research_business, research_competitors

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])

VALID_STATUSES = {
    "pending", "researching", "designing", "generating",
    "review", "published", "archived",
}


def _slugify(name: str) -> str:
    """Convert business name to URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:60] or "landing-page"


async def _ensure_unique_slug(pool, slug: str) -> str:
    """Append -2, -3, etc. if slug already exists."""
    base = slug
    suffix = 1
    while True:
        exists = await pool.fetchval(
            "SELECT 1 FROM landing_pages WHERE slug = $1", slug
        )
        if not exists:
            return slug
        suffix += 1
        slug = f"{base}-{suffix}"


def _parse_row(row) -> dict:
    """Convert asyncpg Record to dict, parsing JSONB string fields."""
    d = dict(row)
    for field in ("research_data", "competitor_data", "design_decisions"):
        if field in d and isinstance(d[field], str):
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field] = {}
    return d


def _row_to_out(row) -> LandingPageOut:
    return LandingPageOut(**_parse_row(row))


def _row_to_list_item(row) -> LandingPageListItem:
    return LandingPageListItem(**dict(row))


# ── Research request models ───────────────────────────────────────────────────

class ResearchBusinessRequest(BaseModel):
    business_name: str
    business_url: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    # If provided, update landing_pages.research_data and set status=researching
    landing_page_id: Optional[str] = None


class ResearchCompetitorsRequest(BaseModel):
    business_name: str
    target_audience: Optional[str] = None
    description: Optional[str] = None
    # industry hint — pass from business research result if available
    industry: Optional[str] = None
    # If provided, update landing_pages.competitor_data
    landing_page_id: Optional[str] = None


# ── Research endpoints ────────────────────────────────────────────────────────

@router.post("/research/business")
async def api_research_business(body: ResearchBusinessRequest):
    """
    Research a business for landing page creation.

    Uses DuckDuckGo search + BeautifulSoup scraping to gather:
    - Value proposition, tagline, products/services
    - Tone of voice, pricing tier, brand colors
    - Social presence, reviews/press mentions

    Returns structured JSON. Optionally persists to landing_pages.research_data
    if landing_page_id is provided.
    """
    pool = await get_pool()

    if body.landing_page_id:
        exists = await pool.fetchval(
            "SELECT 1 FROM landing_pages WHERE id = $1::uuid", body.landing_page_id
        )
        if not exists:
            raise HTTPException(404, "Landing page not found")
        # Mark as researching
        await pool.execute(
            "UPDATE landing_pages SET status = 'researching', updated_at = now() "
            "WHERE id = $1::uuid AND status = 'pending'",
            body.landing_page_id,
        )

    data = await research_business(
        business_name=body.business_name,
        business_url=body.business_url,
        description=body.description,
        target_audience=body.target_audience,
        landing_page_id=body.landing_page_id,
        db_pool=pool if body.landing_page_id else None,
    )

    return {"success": True, "data": data}


@router.post("/research/competitors")
async def api_research_competitors(body: ResearchCompetitorsRequest):
    """
    Research competitors for landing page positioning.

    Uses DuckDuckGo search + BeautifulSoup scraping to find 3-5 competitors,
    then extracts:
    - Visual style, messaging strategy, CTA approach
    - Strengths and weaknesses
    - Market trends, positioning gaps, recommended angles

    Returns structured JSON. Optionally persists to landing_pages.competitor_data
    if landing_page_id is provided.
    """
    pool = await get_pool()

    if body.landing_page_id:
        exists = await pool.fetchval(
            "SELECT 1 FROM landing_pages WHERE id = $1::uuid", body.landing_page_id
        )
        if not exists:
            raise HTTPException(404, "Landing page not found")

    data = await research_competitors(
        business_name=body.business_name,
        target_audience=body.target_audience,
        description=body.description,
        industry=body.industry,
        landing_page_id=body.landing_page_id,
        db_pool=pool if body.landing_page_id else None,
    )

    return {"success": True, "data": data}


# ── POST /landing-pages/generate ─────────────────────────────────

@router.post("/generate", status_code=201)
async def generate_landing_page(body: LandingPageCreate):
    """Create a landing page record. Workflow start is handled externally."""
    pool = await get_pool()
    slug = _slugify(body.business_name)
    slug = await _ensure_unique_slug(pool, slug)

    row = await pool.fetchrow(
        """
        INSERT INTO landing_pages (slug, business_name, business_url, description, target_audience)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *
        """,
        slug, body.business_name, body.business_url,
        body.description, body.target_audience,
    )
    return _row_to_out(row)


# ── GET /landing-pages ───────────────────────────────────────────

@router.get("")
async def list_landing_pages(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            """
            SELECT id, slug, business_name, status, preview_url, created_at, updated_at
            FROM landing_pages
            WHERE status = $1
            ORDER BY created_at DESC
            LIMIT $2 OFFSET $3
            """,
            status, limit, offset,
        )
        count = await pool.fetchval(
            "SELECT COUNT(*) FROM landing_pages WHERE status = $1", status
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, slug, business_name, status, preview_url, created_at, updated_at
            FROM landing_pages
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            limit, offset,
        )
        count = await pool.fetchval("SELECT COUNT(*) FROM landing_pages")

    return {
        "count": count,
        "landing_pages": [_row_to_list_item(r) for r in rows],
    }


# ── GET /landing-pages/{id} ─────────────────────────────────────

@router.get("/{page_id}")
async def get_landing_page(page_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM landing_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(404, "Landing page not found")
    return _row_to_out(row)


# ── GET /landing-pages/{id}/status ───────────────────────────────

@router.get("/{page_id}/status")
async def get_landing_page_status(page_id: UUID):
    """Lightweight status check for polling."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT lp.id, lp.status, lp.preview_url, lp.workflow_instance_id,
               lp.created_at, lp.updated_at
        FROM landing_pages lp
        WHERE lp.id = $1
        """,
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    result = {
        "id": row["id"],
        "status": row["status"],
        "preview_url": row["preview_url"],
        "workflow_instance_id": row["workflow_instance_id"],
    }

    # If linked to a workflow, try to get step progress
    if row["workflow_instance_id"]:
        wf_row = await pool.fetchrow(
            """
            SELECT current_step, status as wf_status
            FROM workflow_instances
            WHERE id = $1
            """,
            row["workflow_instance_id"],
        )
        if wf_row:
            step_names = {
                0: "Business Research",
                1: "Market & Competitor Scan",
                2: "Design Synthesis",
                3: "HTML Generation",
                4: "Deploy & Notify",
            }
            step = wf_row["current_step"] or 0
            result["current_step"] = step
            result["total_steps"] = 5
            result["step_name"] = step_names.get(step, f"Step {step}")

    return result


# ── PATCH /landing-pages/{id}/status ─────────────────────────────

@router.patch("/{page_id}/status")
async def update_landing_page_status(page_id: UUID, body: LandingPageStatusUpdate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

    pool = await get_pool()

    # Build dynamic SET clause
    sets = ["status = $2"]
    params = [page_id, body.status]
    idx = 3

    if body.preview_url is not None:
        sets.append(f"preview_url = ${idx}")
        params.append(body.preview_url)
        idx += 1

    if body.error_text is not None:
        sets.append(f"error_text = ${idx}")
        params.append(body.error_text)
        idx += 1

    row = await pool.fetchrow(
        f"UPDATE landing_pages SET {', '.join(sets)} WHERE id = $1 RETURNING *",
        *params,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")
    return _row_to_out(row)


# ── PATCH /landing-pages/{id}/data ───────────────────────────────

@router.patch("/{page_id}/data")
async def update_landing_page_data(page_id: UUID, body: LandingPageDataUpdate):
    """Update research/competitor/design JSONB fields (called by workflow steps)."""
    pool = await get_pool()

    sets = []
    params = [page_id]
    idx = 2

    if body.research_data is not None:
        sets.append(f"research_data = ${ idx}")
        params.append(body.research_data)
        idx += 1

    if body.competitor_data is not None:
        sets.append(f"competitor_data = ${idx}")
        params.append(body.competitor_data)
        idx += 1

    if body.design_decisions is not None:
        sets.append(f"design_decisions = ${idx}")
        params.append(body.design_decisions)
        idx += 1

    if not sets:
        raise HTTPException(400, "No data fields provided")

    row = await pool.fetchrow(
        f"UPDATE landing_pages SET {', '.join(sets)} WHERE id = $1 RETURNING *",
        *params,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")
    return _row_to_out(row)


# ── PATCH /landing-pages/{id}/workflow ───────────────────────────

@router.patch("/{page_id}/workflow")
async def link_workflow(page_id: UUID, workflow_instance_id: UUID = Query(...)):
    """Link a workflow instance to a landing page record."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        UPDATE landing_pages
        SET workflow_instance_id = $2
        WHERE id = $1
        RETURNING *
        """,
        page_id, workflow_instance_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")
    return _row_to_out(row)


# ── DELETE /landing-pages/{id} ───────────────────────────────────

@router.delete("/{page_id}")
async def archive_landing_page(page_id: UUID):
    """Soft-delete: set status to archived."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        UPDATE landing_pages SET status = 'archived'
        WHERE id = $1 AND status != 'archived'
        RETURNING id, slug, status
        """,
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found or already archived")
    return {"id": row["id"], "slug": row["slug"], "status": "archived"}


# ── POST /landing-pages/{id}/generate ────────────────────────────

@router.post("/{page_id}/generate")
async def generate_landing_page_html(page_id: UUID):
    """Generate the HTML file for a landing page from stored design_decisions, research_data, copy.

    Reads design_decisions, competitor_data (for copy), and research_data from the DB.
    Calls generate_and_save() which builds the HTML and saves to /var/www/webassist/{id}/index.html.
    Updates html_path and preview_url. Sets status='review'.

    Returns: {"html_path": str, "preview_url": str, "size_bytes": int, "status": "review"}
    """
    import sys
    sys.path.insert(0, "/home/web3relic/otto")
    from ..services.landing_page.generator import generate_and_save

    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT id, research_data, competitor_data, design_decisions, status FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    research_data = dict(row["research_data"] or {})
    competitor_data = dict(row["competitor_data"] or {})
    design_decisions = dict(row["design_decisions"] or {})

    # copy_data lives inside design_decisions if stored there, else try competitor_data
    copy_data = design_decisions.pop("_copy_data", None) or competitor_data.get("_copy_data") or {}

    if not design_decisions:
        raise HTTPException(422, "design_decisions is empty — run design synthesis first")

    # Merge copy from research if not separately stored
    if not copy_data:
        copy_data = research_data.get("_copy_data", {})

    try:
        await pool.execute(
            "UPDATE landing_pages SET status = 'generating' WHERE id = $1",
            page_id,
        )
        result = await generate_and_save(
            page_id=page_id,
            design_decisions=design_decisions,
            copy_data=copy_data,
            research_data=research_data,
            pool=pool,
        )
        return result
    except Exception as exc:
        await pool.execute(
            "UPDATE landing_pages SET status = 'review', error_text = $2 WHERE id = $1",
            page_id, str(exc)[:500],
        )
        logger.exception(f"HTML generation failed for {page_id}")
        raise HTTPException(500, f"HTML generation failed: {exc}")

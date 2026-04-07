"""
Landing Pages API — generate landing pages via Claude Code agent.

POST /landing-pages/generate → creates record, spawns agent that reads
prompts.md and writes HTML. Poll GET /landing-pages/{id}/status for progress.
"""

import json
import logging
import re
import sys
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_pool

if "/home/web3relic/otto" not in sys.path:
    sys.path.insert(0, "/home/web3relic/otto")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])

VALID_STATUSES = {"pending", "generating", "review", "published", "archived", "failed"}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:60] or "landing-page"


async def _ensure_unique_slug(pool, slug: str) -> str:
    base = slug
    suffix = 1
    while True:
        exists = await pool.fetchval("SELECT 1 FROM landing_pages WHERE slug = $1", slug)
        if not exists:
            return slug
        suffix += 1
        slug = f"{base}-{suffix}"


# ── Background Pipeline ────────────────────────────────────────────────────

async def _run_pipeline(page_id: UUID, business_name: str, business_url: str,
                        description: str, target_audience: str):
    """Spawn Claude Code agent to generate the landing page."""
    pool = await get_pool()
    start = time.time()

    try:
        await pool.execute(
            "UPDATE landing_pages SET status = 'generating', updated_at = now() WHERE id = $1",
            page_id,
        )

        from services.landing_page.agent_generator import generate_with_agent

        result = await generate_with_agent(
            page_id=page_id,
            business_name=business_name,
            business_url=business_url,
            description=description,
            target_audience=target_audience,
            pool=pool,
        )

        logger.info("[pipeline:%s] Done in %.1fs — %s", page_id, time.time() - start,
                     result.get("preview_url"))

    except Exception as exc:
        logger.exception("[pipeline:%s] Failed: %s", page_id, exc)
        await pool.execute(
            "UPDATE landing_pages SET status = 'failed', error_text = $2, updated_at = now() WHERE id = $1",
            page_id, str(exc)[:1000],
        )


# ── Request/Response Models ────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    target_audience: Optional[str] = Field(None, max_length=500)
    project_id: Optional[str] = Field(None, max_length=100)
    api_key: Optional[str] = Field(None, exclude=True)


class WizardCompleteRequest(BaseModel):
    """Payload from WebAssist wizard submission."""
    project_id: str = Field(..., min_length=1, max_length=100)
    name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = Field(None, max_length=300)
    company: str = Field(..., min_length=1, max_length=200)
    industry: Optional[str] = Field(None, max_length=200)
    websiteType: Optional[str] = Field(None, max_length=100)
    websitePurpose: Optional[str] = Field(None, max_length=1000)
    designStyle: Optional[str] = Field(None, max_length=100)
    features: Optional[list[str]] = None
    pagesNeeded: Optional[list[str]] = None


class GenerateResponse(BaseModel):
    id: UUID
    slug: str
    status: str
    preview_url: Optional[str] = None
    status_url: str


# ── POST /landing-pages/generate ───────────────────────────────────────────

@router.post("/generate", status_code=202, response_model=GenerateResponse)
async def generate_landing_page(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Generate a landing page. Returns immediately; poll status_url for progress."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        provided_key = x_api_key or body.api_key
        if not provided_key or provided_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    pool = await get_pool()

    slug = _slugify(body.business_name)
    slug = await _ensure_unique_slug(pool, slug)

    row = await pool.fetchrow(
        """INSERT INTO landing_pages (slug, business_name, business_url, description,
                                     target_audience, project_id, status, created_by)
           VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'api')
           RETURNING id, slug, status, preview_url""",
        slug, body.business_name, body.business_url,
        body.description, body.target_audience, body.project_id,
    )

    page_id = row["id"]

    background_tasks.add_task(
        _run_pipeline,
        page_id=page_id,
        business_name=body.business_name,
        business_url=body.business_url or "",
        description=body.description or "",
        target_audience=body.target_audience or "",
    )

    logger.info("Started generation for %s (id=%s)", body.business_name, page_id)

    return GenerateResponse(
        id=page_id,
        slug=slug,
        status="pending",
        preview_url=None,
        status_url=f"/landing-pages/{page_id}/status",
    )


# ── GET /landing-pages ─────────────────────────────────────────────────────

@router.get("")
async def list_landing_pages(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    pool = await get_pool()
    if status:
        rows = await pool.fetch(
            """SELECT id, slug, business_name, status, preview_url, project_id,
                      created_at, updated_at
               FROM landing_pages WHERE status = $1
               ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
            status, limit, offset,
        )
        count = await pool.fetchval("SELECT COUNT(*) FROM landing_pages WHERE status = $1", status)
    else:
        rows = await pool.fetch(
            """SELECT id, slug, business_name, status, preview_url, project_id,
                      created_at, updated_at
               FROM landing_pages ORDER BY created_at DESC LIMIT $1 OFFSET $2""",
            limit, offset,
        )
        count = await pool.fetchval("SELECT COUNT(*) FROM landing_pages")

    return {
        "count": count,
        "landing_pages": [dict(r) for r in rows],
    }


# ── GET /landing-pages/{id} ────────────────────────────────────────────────

@router.get("/{page_id}")
async def get_landing_page(page_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM landing_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(404, "Landing page not found")
    return dict(row)


# ── GET /landing-pages/{id}/status ──────────────────────────────────────────

@router.get("/{page_id}/status")
async def get_landing_page_status(page_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, preview_url, error_text, created_at, updated_at FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    progress = {"pending": 0, "generating": 50, "review": 100, "published": 100, "archived": 100, "failed": 0}

    return {
        "id": row["id"],
        "status": row["status"],
        "progress_percent": progress.get(row["status"], 0),
        "preview_url": row["preview_url"],
        "error_text": row["error_text"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


# ── PATCH /landing-pages/{id}/status ────────────────────────────────────────

@router.patch("/{page_id}/status")
async def update_landing_page_status(page_id: UUID, status: str = Query(...)):
    if status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE landing_pages SET status = $2, updated_at = now() WHERE id = $1 RETURNING id, status",
        page_id, status,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")
    return dict(row)


# ── DELETE /landing-pages/{id} ──────────────────────────────────────────────

@router.delete("/{page_id}")
async def archive_landing_page(page_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE landing_pages SET status = 'archived' WHERE id = $1 AND status != 'archived' RETURNING id, slug, status",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found or already archived")
    return dict(row)


# ── GET /landing-pages/by-project/{project_id} ────────────────────────────────

@router.get("/by-project/{project_id}")
async def get_landing_page_by_project(
    project_id: str,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Lookup landing page by WebAssist project ID. Returns the most recent one."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, slug, business_name, status, preview_url, error_text,
                  created_at, updated_at
           FROM landing_pages
           WHERE project_id = $1 AND status != 'archived'
           ORDER BY created_at DESC LIMIT 1""",
        project_id,
    )
    if not row:
        raise HTTPException(404, "No landing page for this project")

    progress = {"pending": 0, "generating": 50, "review": 100, "published": 100, "failed": 0}
    result = dict(row)
    result["progress_percent"] = progress.get(row["status"], 0)
    return result


# ── POST /landing-pages/webhook/wizard-complete ──────────────────────────────

@router.post("/webhook/wizard-complete", status_code=202)
async def webhook_wizard_complete(
    body: WizardCompleteRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Receive WebAssist wizard submission and auto-generate a landing page."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    # Map wizard data to landing page fields
    business_name = body.company
    description_parts = []
    if body.industry:
        description_parts.append(f"Industry: {body.industry}")
    if body.websitePurpose:
        description_parts.append(f"Purpose: {body.websitePurpose}")
    if body.features:
        description_parts.append(f"Features: {', '.join(body.features)}")
    if body.pagesNeeded:
        description_parts.append(f"Pages: {', '.join(body.pagesNeeded)}")
    if body.designStyle:
        description_parts.append(f"Design style: {body.designStyle}")
    description = ". ".join(description_parts) if description_parts else None

    target_audience = None
    if body.websiteType:
        type_map = {
            "business": "Business customers and potential clients",
            "ecommerce": "Online shoppers",
            "portfolio": "Potential employers and collaborators",
            "blog": "Readers and subscribers",
            "nonprofit": "Donors, volunteers, and community members",
            "education": "Students and learners",
        }
        target_audience = type_map.get(body.websiteType, f"{body.websiteType} audience")

    pool = await get_pool()

    slug = _slugify(business_name)
    slug = await _ensure_unique_slug(pool, slug)

    # Wrap check + insert in a transaction to prevent TOCTOU race (double-click)
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchval(
                "SELECT id FROM landing_pages WHERE project_id = $1 AND status != 'archived' LIMIT 1",
                body.project_id,
            )
            if existing:
                return {
                    "id": existing,
                    "status": "already_exists",
                    "status_url": f"/landing-pages/{existing}/status",
                }

            row = await conn.fetchrow(
                """INSERT INTO landing_pages (slug, business_name, description,
                                             target_audience, project_id, status, created_by)
                   VALUES ($1, $2, $3, $4, $5, 'pending', 'webassist')
                   RETURNING id, slug, status""",
                slug, business_name, description, target_audience, body.project_id,
            )

    page_id = row["id"]

    background_tasks.add_task(
        _run_pipeline,
        page_id=page_id,
        business_name=business_name,
        business_url="",
        description=description or "",
        target_audience=target_audience or "",
    )

    logger.info("Wizard-triggered generation for %s (project=%s, page=%s)",
                business_name, body.project_id, page_id)

    return {
        "id": page_id,
        "status": "pending",
        "status_url": f"/landing-pages/{page_id}/status",
    }


# ── POST /landing-pages/{id}/regenerate ─────────────────────────────────────

@router.post("/{page_id}/regenerate")
async def regenerate_landing_page(page_id: UUID, background_tasks: BackgroundTasks):
    """Re-generate HTML for an existing landing page."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, business_name, business_url, description, target_audience FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    background_tasks.add_task(
        _run_pipeline,
        page_id=page_id,
        business_name=row["business_name"],
        business_url=row["business_url"] or "",
        description=row["description"] or "",
        target_audience=row["target_audience"] or "",
    )

    return {"id": page_id, "status": "regenerating"}

"""
Landing Pages API — dual-generator landing page pipeline.

POST /landing-pages/generate → creates record, runs both Claude + Gemini
generators concurrently. Poll GET /landing-pages/{id}/status for progress.
Pick a variant via POST /landing-pages/{id}/select, then publish.
"""

import asyncio
import json
import logging
import re
import shutil
import sys
import time
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_pool

if "/home/web3relic/otto" not in sys.path:
    sys.path.insert(0, "/home/web3relic/otto")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])

VALID_STATUSES = {"pending", "researching", "generating", "review", "published", "archived", "failed"}


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


# ── Supabase Project Sync ─────────────────────────────────────────────────

async def _sync_project_stage(project_id: str | None, stage: str, progress: int):
    """Update the WebAssist Supabase project stage/progress if project_id is set."""
    if not project_id:
        return
    try:
        import httpx
        url = settings.webassist_supabase_url
        key = settings.webassist_supabase_service_key
        if not url or not key:
            return
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            await client.patch(
                f"{url}/rest/v1/projects?id=eq.{project_id}",
                headers=headers,
                json={"current_stage": stage, "overall_progress": progress, "stage_progress": progress},
            )
        logger.info("[sync:%s] Project stage → %s (%d%%)", project_id, stage, progress)
    except Exception as exc:
        logger.warning("[sync:%s] Failed to update project: %s", project_id, exc)


# ── Background Pipeline ────────────────────────────────────────────────────

async def _run_pipeline(page_id: UUID, business_name: str, business_url: str,
                        description: str, target_audience: str,
                        project_id: str | None = None,
                        skip_research: bool = False,
                        existing_website_url: str | None = None,
                        google_business_url: str | None = None,
                        uploaded_files: list[dict] | None = None):
    """Run dual-generator pipeline: research → generate (Claude + Gemini) → review."""
    pool = await get_pool()
    start = time.time()

    try:
        # ── Phase 1: Research ──────────────────────────────────────
        if not skip_research:
            await pool.execute(
                "UPDATE landing_pages SET status = 'researching', updated_at = now() WHERE id = $1",
                page_id,
            )
            await _sync_project_stage(project_id, "research", 10)

            research_data = {
                "business_name": business_name,
                "business_url": business_url or None,
                "existing_website_url": existing_website_url or None,
                "google_business_url": google_business_url or None,
                "description": description or None,
                "target_audience": target_audience or None,
                "uploaded_files": [
                    {"name": f["name"], "type": f["type"], "size": f["size"], "category": f["category"], "url": f["url"]}
                    for f in (uploaded_files or [])
                ] if uploaded_files else None,
            }
            await pool.execute(
                "UPDATE landing_pages SET research_data = $2, updated_at = now() WHERE id = $1",
                page_id, json.dumps(research_data),
            )

        # ── Phase 2: Dual generation ──────────────────────────────
        await pool.execute(
            "UPDATE landing_pages SET status = 'generating', updated_at = now() WHERE id = $1",
            page_id,
        )
        await _sync_project_stage(project_id, "development", 30)

        from services.landing_page.agent_generator import generate_with_agent
        from services.landing_page.gemini_generator import generate_with_gemini

        # Run both generators concurrently, each in its own subdirectory
        claude_task = generate_with_agent(
            page_id=page_id,
            business_name=business_name,
            business_url=business_url,
            description=description,
            target_audience=target_audience,
            output_subdir="claude",
        )
        gemini_task = generate_with_gemini(
            page_id=page_id,
            business_name=business_name,
            business_url=business_url,
            description=description,
            target_audience=target_audience,
            output_subdir="gemini",
        )

        results = await asyncio.gather(claude_task, gemini_task, return_exceptions=True)
        claude_result, gemini_result = results

        # Build generations JSONB
        generations = {}
        any_success = False

        if isinstance(claude_result, dict):
            generations["claude"] = {
                "status": "done",
                "preview_url": claude_result["preview_url"],
                "html_path": claude_result["html_path"],
                "file_size": claude_result["file_size"],
                "error_text": None,
            }
            any_success = True
        else:
            err = str(claude_result)[:500] if claude_result else "Unknown error"
            generations["claude"] = {"status": "failed", "error_text": err, "preview_url": None, "html_path": None}
            logger.warning("[pipeline:%s] Claude failed: %s", page_id, err)

        if isinstance(gemini_result, dict):
            generations["gemini"] = {
                "status": "done",
                "preview_url": gemini_result["preview_url"],
                "html_path": gemini_result["html_path"],
                "file_size": gemini_result["file_size"],
                "error_text": None,
            }
            any_success = True
        else:
            err = str(gemini_result)[:500] if gemini_result else "Unknown error"
            generations["gemini"] = {"status": "failed", "error_text": err, "preview_url": None, "html_path": None}
            logger.warning("[pipeline:%s] Gemini failed: %s", page_id, err)

        # ── Phase 3: Store results ────────────────────────────────
        if any_success:
            # Use first successful preview_url as the primary
            primary_url = (generations.get("claude") or generations.get("gemini") or {}).get("preview_url")
            if not primary_url and "gemini" in generations:
                primary_url = generations["gemini"].get("preview_url")

            await pool.execute(
                """UPDATE landing_pages
                   SET status = 'review', generations = $2, preview_url = $3,
                       error_text = NULL, updated_at = now()
                   WHERE id = $1""",
                page_id, json.dumps(generations), primary_url,
            )
            await _sync_project_stage(project_id, "client_preview", 80)
        else:
            combined_err = "; ".join(
                f"{k}: {v.get('error_text', '?')}" for k, v in generations.items()
            )[:1000]
            await pool.execute(
                """UPDATE landing_pages
                   SET status = 'failed', generations = $2, error_text = $3, updated_at = now()
                   WHERE id = $1""",
                page_id, json.dumps(generations), combined_err,
            )
            await _sync_project_stage(project_id, "development", 0)

        logger.info("[pipeline:%s] Done in %.1fs — claude=%s, gemini=%s",
                    page_id, time.time() - start,
                    generations.get("claude", {}).get("status"),
                    generations.get("gemini", {}).get("status"))

    except Exception as exc:
        logger.exception("[pipeline:%s] Failed: %s", page_id, exc)
        await pool.execute(
            "UPDATE landing_pages SET status = 'failed', error_text = $2, updated_at = now() WHERE id = $1",
            page_id, str(exc)[:1000],
        )
        await _sync_project_stage(project_id, "development", 0)


# ── Request/Response Models ────────────────────────────────────────────────

class UploadedFileModel(BaseModel):
    name: str
    type: str
    size: int
    category: str
    url: str  # public URL from Supabase Storage


class GenerateRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    target_audience: Optional[str] = Field(None, max_length=500)
    project_id: Optional[str] = Field(None, max_length=100)
    # Structured fields (same as wizard — used to compose description if provided)
    industry: Optional[str] = Field(None, max_length=200)
    website_type: Optional[str] = Field(None, max_length=100)
    website_purpose: Optional[str] = Field(None, max_length=1000)
    design_style: Optional[str] = Field(None, max_length=100)
    features: Optional[list[str]] = None
    pages_needed: Optional[list[str]] = None
    # Content assets
    existing_website_url: Optional[str] = Field(None, max_length=500)
    google_business_url: Optional[str] = Field(None, max_length=500)
    uploaded_files: Optional[list[UploadedFileModel]] = None
    skip_research: bool = Field(False, description="Skip research phase and go straight to generation")
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
    existing_website_url: Optional[str] = Field(None, max_length=500)
    google_business_url: Optional[str] = Field(None, max_length=500)
    uploaded_files: Optional[list[UploadedFileModel]] = None


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

    # Compose description from structured fields if no free-text description given
    description = body.description
    if not description and any([body.industry, body.website_purpose, body.features, body.pages_needed, body.design_style]):
        parts = []
        if body.industry:
            parts.append(f"Industry: {body.industry}")
        if body.website_purpose:
            parts.append(f"Purpose: {body.website_purpose}")
        if body.features:
            parts.append(f"Features: {', '.join(body.features)}")
        if body.pages_needed:
            parts.append(f"Pages: {', '.join(body.pages_needed)}")
        if body.design_style:
            parts.append(f"Design style: {body.design_style}")
        description = ". ".join(parts)

    # Compose target_audience from website_type if not given
    target_audience = body.target_audience
    if not target_audience and body.website_type:
        type_map = {
            "business": "Business customers and potential clients",
            "ecommerce": "Online shoppers",
            "portfolio": "Potential employers and collaborators",
            "blog": "Readers and subscribers",
            "nonprofit": "Donors, volunteers, and community members",
            "education": "Students and learners",
        }
        target_audience = type_map.get(body.website_type, f"{body.website_type} audience")

    pool = await get_pool()

    slug = _slugify(body.business_name)
    slug = await _ensure_unique_slug(pool, slug)

    row = await pool.fetchrow(
        """INSERT INTO landing_pages (slug, business_name, business_url, description,
                                     target_audience, project_id, status, created_by)
           VALUES ($1, $2, $3, $4, $5, $6, 'pending', 'api')
           RETURNING id, slug, status, preview_url""",
        slug, body.business_name, body.business_url,
        description, target_audience, body.project_id,
    )

    page_id = row["id"]

    background_tasks.add_task(
        _run_pipeline,
        page_id=page_id,
        business_name=body.business_name,
        business_url=body.business_url or "",
        description=description or "",
        target_audience=target_audience or "",
        project_id=body.project_id,
        skip_research=body.skip_research,
        existing_website_url=body.existing_website_url,
        google_business_url=body.google_business_url,
        uploaded_files=[f.model_dump() for f in body.uploaded_files] if body.uploaded_files else None,
    )

    logger.info("Started dual generation for %s (id=%s, skip_research=%s)", body.business_name, page_id, body.skip_research)

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
        "SELECT id, status, preview_url, error_text, generations, created_at, updated_at FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    progress = {
        "pending": 0, "researching": 15, "generating": 50,
        "review": 100, "published": 100, "archived": 100, "failed": 0,
    }

    gens = row["generations"]
    if isinstance(gens, str):
        gens = json.loads(gens)

    return {
        "id": row["id"],
        "status": row["status"],
        "progress_percent": progress.get(row["status"], 0),
        "preview_url": row["preview_url"],
        "error_text": row["error_text"],
        "generations": gens or {},
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
                  generations, created_at, updated_at
           FROM landing_pages
           WHERE project_id = $1 AND status != 'archived'
           ORDER BY created_at DESC LIMIT 1""",
        project_id,
    )
    if not row:
        raise HTTPException(404, "No landing page for this project")

    progress = {
        "pending": 0, "researching": 15, "generating": 50,
        "review": 100, "published": 100, "failed": 0,
    }
    result = dict(row)
    result["progress_percent"] = progress.get(row["status"], 0)
    gens = result.get("generations")
    if isinstance(gens, str):
        result["generations"] = json.loads(gens)
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
        business_url=body.existing_website_url or "",
        description=description or "",
        target_audience=target_audience or "",
        project_id=body.project_id,
        existing_website_url=body.existing_website_url,
        google_business_url=body.google_business_url,
        uploaded_files=[f.model_dump() for f in body.uploaded_files] if body.uploaded_files else None,
    )

    logger.info("Wizard-triggered dual generation for %s (project=%s, page=%s)",
                business_name, body.project_id, page_id)

    return {
        "id": page_id,
        "status": "pending",
        "status_url": f"/landing-pages/{page_id}/status",
    }


# ── POST /landing-pages/{id}/regenerate ─────────────────────────────────────

@router.post("/{page_id}/regenerate")
async def regenerate_landing_page(
    page_id: UUID,
    background_tasks: BackgroundTasks,
):
    """Re-generate HTML for an existing landing page (both Claude + Gemini)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, business_name, business_url, description, target_audience, project_id FROM landing_pages WHERE id = $1",
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
        project_id=row["project_id"],
    )

    return {"id": page_id, "status": "regenerating"}


# ── POST /landing-pages/{id}/select ───────────────────────────────────────

class SelectRequest(BaseModel):
    generator: str = Field(..., description="Which variant to publish: 'claude' or 'gemini'")


@router.post("/{page_id}/select")
async def select_variant(page_id: UUID, body: SelectRequest):
    """Select a generator variant (claude/gemini) as the final version and publish."""
    if body.generator not in ("claude", "gemini"):
        raise HTTPException(400, "generator must be 'claude' or 'gemini'")

    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, generations, project_id FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    gens = row["generations"]
    if isinstance(gens, str):
        gens = json.loads(gens)

    variant = gens.get(body.generator)
    if not variant or variant.get("status") != "done":
        raise HTTPException(400, f"{body.generator} variant not available or failed")

    # Copy selected variant to the root directory as the canonical version
    from pathlib import Path
    src_html = Path(variant["html_path"])
    root_dir = src_html.parent.parent  # {page_id}/claude/ → {page_id}/
    dest_html = root_dir / "index.html"
    shutil.copy2(str(src_html), str(dest_html))

    preview_url = f"https://webassist.otto.lk/{page_id}"

    await pool.execute(
        """UPDATE landing_pages
           SET status = 'published', html_path = $2, preview_url = $3,
               error_text = NULL, updated_at = now()
           WHERE id = $1""",
        page_id, str(dest_html), preview_url,
    )

    await _sync_project_stage(row["project_id"], "delivered", 100)

    logger.info("[select:%s] Published %s variant → %s", page_id, body.generator, preview_url)

    return {"id": page_id, "status": "published", "selected": body.generator, "preview_url": preview_url}


# ── POST /landing-pages/upload ────────────────────────────────────────────

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    category: str = Form("content"),
):
    """Upload a file to Supabase Storage and return metadata with public URL.

    Used by OMS to upload files for landing page generation.
    """
    url = settings.webassist_supabase_url
    key = settings.webassist_supabase_service_key
    if not url or not key:
        raise HTTPException(503, "Supabase Storage not configured")

    if category not in ("logo", "brand", "content"):
        raise HTTPException(400, "category must be logo, brand, or content")

    MAX_SIZE = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(400, f"File exceeds 5 MB limit ({len(content)} bytes)")

    import httpx

    bucket = "wizard-uploads"
    storage_path = f"oms/{category}/{int(time.time())}-{file.filename}"
    content_type = file.content_type or "application/octet-stream"

    # Upload via Supabase Storage REST API
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{url}/storage/v1/object/{bucket}/{storage_path}",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": content_type,
            },
            content=content,
        )

    if resp.status_code not in (200, 201):
        logger.error("[upload] Supabase Storage error: %s %s", resp.status_code, resp.text)
        raise HTTPException(502, f"Storage upload failed: {resp.text[:200]}")

    public_url = f"{url}/storage/v1/object/public/{bucket}/{storage_path}"

    return {
        "name": file.filename,
        "type": content_type,
        "size": len(content),
        "category": category,
        "storagePath": storage_path,
        "url": public_url,
    }

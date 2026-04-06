"""
Landing Pages API — Sellable endpoint for automated landing page generation.

The primary endpoint is POST /landing-pages/generate which orchestrates the full
async pipeline: business research → competitor analysis → design synthesis →
copy generation → HTML build. Clients poll GET /landing-pages/{id}/status for
progress.

Auth: X-API-Key header (or api_key body field). Configurable via
LANDING_PAGE_API_KEY env var. Empty key = open access (dev mode).

Pipeline stages & status progression:
  pending → researching → designing → generating → review
  Any stage failure → status stays at that stage with error_text set.
"""

import asyncio
import json
import logging
import re
import sys
import time
import traceback
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..db import get_pool
from ..models import (
    LandingPageCreate,
    LandingPageOut,
    LandingPageListItem,
    LandingPageStatusUpdate,
    LandingPageDataUpdate,
)
from ..services.landing_page.research import research_business, research_competitors

# Ensure Otto services are importable (used by design + agent_generator modules)
if "/home/web3relic/otto" not in sys.path:
    sys.path.insert(0, "/home/web3relic/otto")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])

VALID_STATUSES = {
    "pending", "researching", "designing", "generating",
    "review", "published", "archived",
}


# ── Auth Dependency ──────────────────────────────────────────────────────────

async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    API key authentication for landing page endpoints.

    Checks X-API-Key header against LANDING_PAGE_API_KEY env var.
    If LANDING_PAGE_API_KEY is empty (dev mode), all requests pass.
    """
    configured_key = settings.landing_page_api_key
    if not configured_key:
        # Dev mode — no auth required
        return None
    if not x_api_key or x_api_key != configured_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Provide X-API-Key header.",
        )
    return x_api_key


# ── Helpers ──────────────────────────────────────────────────────────────────

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


async def _update_status(pool, page_id: UUID, status: str, error_text: str = None):
    """Update landing page status (and optionally error_text) in DB."""
    if error_text:
        await pool.execute(
            "UPDATE landing_pages SET status = $2, error_text = $3, updated_at = now() "
            "WHERE id = $1",
            page_id, status, error_text[:1000],
        )
    else:
        await pool.execute(
            "UPDATE landing_pages SET status = $2, error_text = NULL, updated_at = now() "
            "WHERE id = $1",
            page_id, status,
        )


# ── Background Pipeline ─────────────────────────────────────────────────────

async def _run_pipeline(page_id: UUID, business_name: str, business_url: str,
                        description: str, target_audience: str):
    """
    Full landing page generation pipeline. Runs as a background task.

    Steps:
      1. Research business (scraping + DDG search)
      2. Research competitors (DDG search + profiling)
      3. Design synthesis (LLM-driven design decisions from catalog)
      4. Copy generation (LLM-driven section copy)
      5. HTML generation + file save

    Each step updates the landing_pages row with its output and status.
    Failures at any step store error_text and halt the pipeline.
    """
    pool = await get_pool()
    start = time.time()

    try:
        # ── Step 1: Business Research ────────────────────────────────
        logger.info("[pipeline:%s] Step 1: Business research", page_id)
        await _update_status(pool, page_id, "researching")

        research_data = await research_business(
            business_name=business_name,
            business_url=business_url,
            description=description,
            target_audience=target_audience,
            landing_page_id=str(page_id),
            db_pool=pool,
        )

        # Persist research_data to DB (research_business may have done this,
        # but ensure it's there)
        await pool.execute(
            "UPDATE landing_pages SET research_data = $2::jsonb, updated_at = now() "
            "WHERE id = $1",
            page_id, json.dumps(research_data),
        )

        logger.info("[pipeline:%s] Step 1 complete (%.1fs)", page_id, time.time() - start)

    except Exception as exc:
        logger.exception("[pipeline:%s] Step 1 failed: %s", page_id, exc)
        await _update_status(pool, page_id, "researching",
                             f"Business research failed: {exc}")
        return

    try:
        # ── Step 2: Competitor Research ──────────────────────────────
        step2_start = time.time()
        logger.info("[pipeline:%s] Step 2: Competitor research", page_id)

        industry = research_data.get("industry", None)
        competitor_data = await research_competitors(
            business_name=business_name,
            target_audience=target_audience,
            description=description,
            industry=industry,
            landing_page_id=str(page_id),
            db_pool=pool,
        )

        await pool.execute(
            "UPDATE landing_pages SET competitor_data = $2::jsonb, updated_at = now() "
            "WHERE id = $1",
            page_id, json.dumps(competitor_data),
        )

        logger.info("[pipeline:%s] Step 2 complete (%.1fs)", page_id, time.time() - step2_start)

    except Exception as exc:
        logger.exception("[pipeline:%s] Step 2 failed: %s", page_id, exc)
        await _update_status(pool, page_id, "researching",
                             f"Competitor research failed: {exc}")
        return

    try:
        # ── Step 3: Design Selection ────────────────────────────────
        step3_start = time.time()
        logger.info("[pipeline:%s] Step 3: Design selection", page_id)
        await _update_status(pool, page_id, "designing")

        from services.landing_page.design import design_synthesizer

        # LLM picks the best design from the prompts.md catalog
        design_decisions = await design_synthesizer(
            research_data=research_data,
            competitor_data=competitor_data,
        )

        # Persist design decisions to DB
        await pool.execute(
            "UPDATE landing_pages SET design_decisions = $2::jsonb, updated_at = now() "
            "WHERE id = $1",
            page_id, json.dumps(design_decisions),
        )

        logger.info("[pipeline:%s] Step 3 complete (%.1fs) — design=%s",
                     page_id, time.time() - step3_start,
                     design_decisions.get("selected_design_id", "?"))

    except Exception as exc:
        logger.exception("[pipeline:%s] Step 3 failed: %s", page_id, exc)
        await _update_status(pool, page_id, "designing",
                             f"Design synthesis failed: {exc}")
        return

    try:
        # ── Step 4: Agent-Driven HTML Generation ─────────────────────
        step4_start = time.time()
        logger.info("[pipeline:%s] Step 4: Agent HTML generation", page_id)
        await _update_status(pool, page_id, "generating")

        from services.landing_page.agent_generator import generate_with_agent

        result = await generate_with_agent(
            page_id=page_id,
            design_decisions=design_decisions,
            research_data=research_data,
            competitor_data=competitor_data,
            pool=pool,
        )

        # generate_with_agent sets status='review', html_path, and preview_url
        total_time = time.time() - start
        logger.info(
            "[pipeline:%s] Pipeline complete in %.1fs — preview: %s",
            page_id, total_time, result.get("preview_url"),
        )

    except Exception as exc:
        # Fallback: try the old template generator
        logger.warning("[pipeline:%s] Agent failed (%s), falling back to template generator",
                       page_id, exc)
        try:
            from services.landing_page.design import copy_generator
            from services.landing_page.generator import generate_and_save

            copy_data = await copy_generator(
                business_data=research_data,
                design_decisions=design_decisions,
            )
            result = await generate_and_save(
                page_id=page_id,
                design_decisions=design_decisions,
                copy_data=copy_data,
                research_data=research_data,
                pool=pool,
            )
            total_time = time.time() - start
            logger.info(
                "[pipeline:%s] Fallback complete in %.1fs — preview: %s",
                page_id, total_time, result.get("preview_url"),
            )
        except Exception as fallback_exc:
            logger.exception("[pipeline:%s] Fallback also failed: %s", page_id, fallback_exc)
            await _update_status(pool, page_id, "generating",
                                 f"HTML generation failed (agent: {exc}, fallback: {fallback_exc})")
            return


# ── Request/Response Models ──────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    """
    Request body for POST /landing-pages/generate.

    Args:
        business_name:   Name of the business (required)
        business_url:    Homepage URL — used for scraping brand info
        description:     What the business does (helps when URL unavailable)
        target_audience: Who the landing page targets
        api_key:         Alternative to X-API-Key header (convenience for form clients)
    """
    business_name: str = Field(..., min_length=1, max_length=200,
                               description="Business name")
    business_url: Optional[str] = Field(None, max_length=500,
                                        description="Business homepage URL")
    description: Optional[str] = Field(None, max_length=2000,
                                       description="What the business does")
    target_audience: Optional[str] = Field(None, max_length=500,
                                           description="Target audience description")
    api_key: Optional[str] = Field(None, exclude=True,
                                   description="API key (alternative to X-API-Key header)")


class GenerateResponse(BaseModel):
    """Response from POST /landing-pages/generate."""
    id: UUID
    slug: str
    status: str
    preview_url: Optional[str] = None
    estimated_time_seconds: int = Field(
        default=120,
        description="Estimated time to completion in seconds",
    )
    status_url: str = Field(
        description="Poll this URL for status updates",
    )


class ResearchBusinessRequest(BaseModel):
    business_name: str
    business_url: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    landing_page_id: Optional[str] = None


class ResearchCompetitorsRequest(BaseModel):
    business_name: str
    target_audience: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    landing_page_id: Optional[str] = None


# ── POST /landing-pages/generate ─────────────────────────────────────────────

@router.post("/generate", status_code=202, response_model=GenerateResponse)
async def generate_landing_page(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Generate a complete landing page for a business.

    Creates a landing page record and starts the async generation pipeline:
      1. **Research** — scrapes business website + DDG search for brand info
      2. **Competitors** — finds 3-5 competitors, analyzes visual + messaging
      3. **Design** — selects design template, fonts, colors, section layout
      4. **Copy** — generates all section headlines, body text, CTAs
      5. **Build** — renders a self-contained HTML file with inline CSS

    **Authentication:**
      - Header: `X-API-Key: <your-key>`
      - Body field: `api_key: "<your-key>"`
      - Dev mode: if no key is configured server-side, all requests pass

    **Polling:**
      Use the returned `status_url` to check progress. Status values:
      `pending` → `researching` → `designing` → `generating` → `review`

    **Returns:** 202 Accepted with job metadata. The `preview_url` field
    populates once generation completes (status=review).
    """
    # Auth: check header OR body field
    configured_key = settings.landing_page_api_key
    if configured_key:
        provided_key = x_api_key or body.api_key
        if not provided_key or provided_key != configured_key:
            raise HTTPException(
                status_code=401,
                detail="Invalid or missing API key. Provide X-API-Key header or api_key body field.",
            )

    pool = await get_pool()

    # Create the landing page record
    slug = _slugify(body.business_name)
    slug = await _ensure_unique_slug(pool, slug)

    row = await pool.fetchrow(
        """
        INSERT INTO landing_pages (slug, business_name, business_url, description,
                                   target_audience, status, created_by)
        VALUES ($1, $2, $3, $4, $5, 'pending', 'api')
        RETURNING id, slug, status, preview_url
        """,
        slug, body.business_name, body.business_url,
        body.description, body.target_audience,
    )

    page_id = row["id"]

    # Start the async pipeline
    background_tasks.add_task(
        _run_pipeline,
        page_id=page_id,
        business_name=body.business_name,
        business_url=body.business_url or "",
        description=body.description or "",
        target_audience=body.target_audience or "",
    )

    logger.info("Pipeline started for %s (id=%s)", body.business_name, page_id)

    return GenerateResponse(
        id=page_id,
        slug=slug,
        status="pending",
        preview_url=None,
        estimated_time_seconds=120,
        status_url=f"/landing-pages/{page_id}/status",
    )


# ── Research Endpoints (standalone — also called by workflow steps) ───────────

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


# ── GET /landing-pages ───────────────────────────────────────────────────────

@router.get("")
async def list_landing_pages(
    status: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all landing pages with optional status filter."""
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


# ── GET /landing-pages/{id} ─────────────────────────────────────────────────

@router.get("/{page_id}")
async def get_landing_page(page_id: UUID):
    """
    Get full landing page record including all research data, design decisions,
    and generated HTML path.
    """
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM landing_pages WHERE id = $1", page_id)
    if not row:
        raise HTTPException(404, "Landing page not found")
    return _row_to_out(row)


# ── GET /landing-pages/{id}/status ───────────────────────────────────────────

@router.get("/{page_id}/status")
async def get_landing_page_status(page_id: UUID):
    """
    Lightweight status polling endpoint.

    Returns current pipeline stage, progress indicator, and preview_url
    (populated once generation completes). Poll every 5-10 seconds.

    Status progression: pending → researching → designing → generating → review

    If error_text is non-null, the pipeline failed at the current stage.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT lp.id, lp.status, lp.preview_url, lp.error_text,
               lp.workflow_instance_id, lp.created_at, lp.updated_at
        FROM landing_pages lp
        WHERE lp.id = $1
        """,
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    # Map status to progress percentage
    progress_map = {
        "pending": 0,
        "researching": 25,
        "designing": 50,
        "generating": 75,
        "review": 100,
        "published": 100,
        "archived": 100,
    }

    result = {
        "id": row["id"],
        "status": row["status"],
        "progress_percent": progress_map.get(row["status"], 0),
        "preview_url": row["preview_url"],
        "error_text": row["error_text"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }

    # If linked to a workflow, enrich with step progress
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


# ── PATCH /landing-pages/{id}/status ─────────────────────────────────────────

@router.patch("/{page_id}/status")
async def update_landing_page_status(page_id: UUID, body: LandingPageStatusUpdate):
    """Update landing page status (admin/workflow use)."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {VALID_STATUSES}")

    pool = await get_pool()
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


# ── PATCH /landing-pages/{id}/data ───────────────────────────────────────────

@router.patch("/{page_id}/data")
async def update_landing_page_data(page_id: UUID, body: LandingPageDataUpdate):
    """Update research/competitor/design JSONB fields (called by workflow steps)."""
    pool = await get_pool()
    sets = []
    params = [page_id]
    idx = 2

    if body.research_data is not None:
        sets.append(f"research_data = ${idx}")
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


# ── PATCH /landing-pages/{id}/workflow ───────────────────────────────────────

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


# ── DELETE /landing-pages/{id} ───────────────────────────────────────────────

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


# ── POST /landing-pages/{id}/generate (re-generate HTML from stored data) ───

@router.post("/{page_id}/generate")
async def generate_landing_page_html(page_id: UUID, _key=Depends(verify_api_key)):
    """
    Re-generate HTML for an existing landing page using the agent pipeline.

    Uses stored design_decisions and research data. Falls back to template
    generator if the agent fails.

    Requires design_decisions to be populated (run design synthesis first).
    """
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT id, research_data, competitor_data, design_decisions, status "
        "FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    parsed = _parse_row(row)
    research_data = parsed.get("research_data") or {}
    competitor_data = parsed.get("competitor_data") or {}
    design_decisions = parsed.get("design_decisions") or {}

    if not design_decisions:
        raise HTTPException(422, "design_decisions is empty — run design synthesis first")

    try:
        await pool.execute(
            "UPDATE landing_pages SET status = 'generating' WHERE id = $1",
            page_id,
        )

        # Try agent-driven generation first
        from services.landing_page.agent_generator import generate_with_agent

        result = await generate_with_agent(
            page_id=page_id,
            design_decisions=design_decisions,
            research_data=research_data,
            competitor_data=competitor_data,
            pool=pool,
        )
        return result

    except Exception as agent_exc:
        logger.warning("Agent failed for %s (%s), trying template fallback", page_id, agent_exc)

        # Fallback to old template generator
        try:
            from services.landing_page.design import copy_generator
            from services.landing_page.generator import generate_and_save

            copy_data = await copy_generator(
                business_data=research_data,
                design_decisions=design_decisions,
            )
            result = await generate_and_save(
                page_id=page_id,
                design_decisions=design_decisions,
                copy_data=copy_data,
                research_data=research_data,
                pool=pool,
            )
            return result
        except Exception as fallback_exc:
            await pool.execute(
                "UPDATE landing_pages SET status = 'review', error_text = $2 WHERE id = $1",
                page_id, f"Agent: {agent_exc}; Fallback: {fallback_exc}"[:500],
            )
            logger.exception("Both agent and fallback failed for %s", page_id)
            raise HTTPException(500, f"HTML generation failed: {fallback_exc}")

"""
Landing Pages API — multi-phase landing page pipeline.

Phase 1 (parallel): Template generation (Claude+Gemini) + Website scraping + Competitor research
Phase 2: Copy synthesis from scraped content + competitor data
Phase 3: Manual template selection (from OMS)
Phase 4: Enrich selected template with synthesized copy
Phase 4.5: QA pass
Phase 5: Client preview → Publish

POST /landing-pages/generate → starts pipeline
POST /landing-pages/{id}/select → selects template, triggers enrichment
POST /landing-pages/{id}/publish → final publish after client preview
GET /landing-pages/{id}/status → poll progress
POST /landing-pages/sync → upsert from external standalone instances
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

VALID_STATUSES = {
    "pending", "phase1", "synthesizing", "design_review", "template_review",
    "enriching", "qa", "client_preview", "published", "archived", "failed",
    # Legacy (existing rows)
    "researching", "designing", "generating", "review",
}


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
                        uploaded_files: list[dict] | None = None,
                        competitors: list[str] | None = None):
    """Multi-phase pipeline: research → synthesis → design options → design_review (stops here).

    Phase 1: Track B (scrape) + Track C (competitors) in parallel
    Phase 2: Copy synthesis
    Phase 3: Generate 3 design.md options
    Then sets status='design_review' and exits. Admin selects design via API,
    which triggers _run_template_generation() → template_review → enrichment.
    """
    pool = await get_pool()
    start = time.time()

    try:
        # ── Store research data ───────────────────────────────────
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
            "competitors": competitors or [],
        }
        await pool.execute(
            "UPDATE landing_pages SET status = 'phase1', research_data = $2, updated_at = now() WHERE id = $1",
            page_id, json.dumps(research_data),
        )
        await _sync_project_stage(project_id, "initial_review", 10)

        # ── Phase 1: Two parallel tracks (scrape + competitors) ───
        from services.landing_page.scraper import scrape_website
        from services.landing_page.design import synthesize_copy

        # Track B: Website scraping (if URL provided)
        scrape_url = existing_website_url or business_url
        scrape_task = asyncio.create_task(
            scrape_website(scrape_url) if scrape_url else _empty_scrape()
        )

        # Track C: Competitor research (lightweight LLM call)
        competitor_task = asyncio.create_task(
            _run_competitor_research(business_name, description, target_audience, competitors or [])
        )

        scrape_result, competitor_result = await asyncio.gather(
            scrape_task, competitor_task, return_exceptions=True
        )

        scraped = scrape_result if isinstance(scrape_result, dict) else {"error": str(scrape_result)[:500]}
        comp_data = competitor_result if isinstance(competitor_result, dict) else {"error": str(competitor_result)[:500]}

        await pool.execute(
            """UPDATE landing_pages SET scraped_content = $2, competitor_data = $3, updated_at = now()
               WHERE id = $1""",
            page_id, json.dumps(scraped), json.dumps(comp_data),
        )
        await _sync_project_stage(project_id, "research", 30)

        # ── Phase 2: Copy synthesis ───────────────────────────────
        await pool.execute(
            "UPDATE landing_pages SET status = 'synthesizing', updated_at = now() WHERE id = $1",
            page_id,
        )
        await _sync_project_stage(project_id, "content_collection", 40)

        try:
            copy_data = await synthesize_copy(research_data, scraped, comp_data)
        except Exception as exc:
            logger.warning("[pipeline:%s] Synthesis failed, using fallback: %s", page_id, exc)
            copy_data = {"_fallback": True, "headline": business_name}

        await pool.execute(
            "UPDATE landing_pages SET synthesized_copy = $2, updated_at = now() WHERE id = $1",
            page_id, json.dumps(copy_data),
        )
        await _sync_project_stage(project_id, "content_collection", 50)

        # ── Phase 3: Generate 3 design.md options ─────────────────
        from services.landing_page.design_generator import generate_all_design_options

        design_result = await generate_all_design_options(
            page_id=page_id,
            research_data=research_data,
            scraped_content=scraped,
            competitor_data=comp_data,
            synthesized_copy=copy_data,
        )

        any_design = any(
            v.get("status") == "done" for v in design_result.values()
        )

        if any_design:
            await pool.execute(
                """UPDATE landing_pages
                   SET status = 'design_review', design_options = $2,
                       error_text = NULL, updated_at = now()
                   WHERE id = $1""",
                page_id, json.dumps(design_result),
            )
            await _sync_project_stage(project_id, "design_review", 55)
        else:
            combined_err = "; ".join(
                f"{k}: {v.get('error', '?')}" for k, v in design_result.items()
            )[:1000]
            await pool.execute(
                """UPDATE landing_pages
                   SET status = 'failed', design_options = $2, error_text = $3, updated_at = now()
                   WHERE id = $1""",
                page_id, json.dumps(design_result), combined_err,
            )
            await _sync_project_stage(project_id, "development", 0)

        logger.info("[pipeline:%s] Research + synthesis + designs done in %.1fs — designs=%s, copy=%s",
                    page_id, time.time() - start,
                    {k: v.get("status") for k, v in design_result.items()},
                    "ok" if not copy_data.get("_fallback") else "fallback")

    except Exception as exc:
        logger.exception("[pipeline:%s] Failed: %s", page_id, exc)
        await pool.execute(
            "UPDATE landing_pages SET status = 'failed', error_text = $2, updated_at = now() WHERE id = $1",
            page_id, str(exc)[:1000],
        )
        await _sync_project_stage(project_id, "development", 0)


async def _run_template_generation(page_id: UUID):
    """Background task: generate templates using selected design.md, then set template_review."""
    pool = await get_pool()

    try:
        row = await pool.fetchrow(
            """SELECT id, business_name, business_url, description, target_audience,
                      project_id, selected_design, design_options
               FROM landing_pages WHERE id = $1""",
            page_id,
        )
        if not row:
            return

        selected = row["selected_design"]
        options = row["design_options"]
        if isinstance(options, str):
            options = json.loads(options)

        design_file = options.get(selected, {}).get("file_path")
        if not design_file:
            raise RuntimeError(f"No file path for selected design '{selected}'")

        from pathlib import Path
        design_md = Path(design_file).read_text(encoding="utf-8")

        business_name = row["business_name"]
        project_id = row["project_id"]

        await pool.execute(
            "UPDATE landing_pages SET status = 'phase1', updated_at = now() WHERE id = $1",
            page_id,
        )
        await _sync_project_stage(project_id, "development", 60)

        generations = await _run_templates(
            page_id, business_name, row["business_url"] or "",
            row["description"] or "", row["target_audience"] or "",
            design_md=design_md,
        )

        any_success = any(v.get("status") == "done" for v in generations.values())

        if any_success:
            primary_url = None
            for gen in ("claude", "gemini"):
                v = generations.get(gen, {})
                if v.get("status") == "done" and v.get("preview_url"):
                    primary_url = v["preview_url"]
                    break

            await pool.execute(
                """UPDATE landing_pages
                   SET status = 'template_review', generations = $2, preview_url = $3,
                       error_text = NULL, updated_at = now()
                   WHERE id = $1""",
                page_id, json.dumps(generations), primary_url,
            )
            await _sync_project_stage(project_id, "review", 70)
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

        logger.info("[template-gen:%s] Templates done — claude=%s, gemini=%s",
                    page_id,
                    generations.get("claude", {}).get("status"),
                    generations.get("gemini", {}).get("status"))

    except Exception as exc:
        logger.exception("[template-gen:%s] Failed: %s", page_id, exc)
        await pool.execute(
            "UPDATE landing_pages SET status = 'failed', error_text = $2, updated_at = now() WHERE id = $1",
            page_id, str(exc)[:1000],
        )


async def _run_templates(page_id, business_name, business_url, description, target_audience, design_md=""):
    """Run Claude + Gemini template generation in parallel, optionally guided by design.md."""
    from services.landing_page.agent_generator import generate_with_agent
    from services.landing_page.gemini_generator import generate_with_gemini

    claude_task = generate_with_agent(
        page_id=page_id, business_name=business_name, business_url=business_url,
        description=description, target_audience=target_audience, output_subdir="claude",
        design_md=design_md,
    )
    gemini_task = generate_with_gemini(
        page_id=page_id, business_name=business_name, business_url=business_url,
        description=description, target_audience=target_audience, output_subdir="gemini",
        design_md=design_md,
    )

    results = await asyncio.gather(claude_task, gemini_task, return_exceptions=True)
    claude_result, gemini_result = results

    generations = {}
    for name, result in [("claude", claude_result), ("gemini", gemini_result)]:
        if isinstance(result, dict):
            generations[name] = {
                "status": "done",
                "preview_url": result["preview_url"],
                "html_path": result["html_path"],
                "file_size": result["file_size"],
                "error_text": None,
            }
        else:
            err = str(result)[:500] if result else "Unknown error"
            generations[name] = {"status": "failed", "error_text": err, "preview_url": None, "html_path": None}
            logger.warning("[templates:%s] %s failed: %s", page_id, name, err)

    return generations


async def _claude_json(prompt: str, label: str = "claude-json", timeout: int = 120) -> dict | None:
    """Run a short Claude CLI call and extract JSON from the response."""
    import os

    cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print", "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "1",
        "--max-budget-usd", "0.50",
        "--output-format", "json",
        "-p", prompt,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/web3relic/otto",
            env={**os.environ, "HOME": "/home/web3relic"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = stdout.decode(errors="replace")

        if not text.strip():
            logger.warning("[%s] Empty response", label)
            return None

        from memory.llm import extract_json
        result = extract_json(text)
        if result:
            logger.info("[%s] Got JSON (%d keys)", label, len(result))
        else:
            logger.warning("[%s] Could not extract JSON from response (%d chars)", label, len(text))
        return result

    except asyncio.TimeoutError:
        logger.warning("[%s] Timed out after %ds", label, timeout)
        return None
    except Exception as exc:
        logger.warning("[%s] Failed: %s", label, exc)
        return None


async def _run_competitor_research(business_name: str, description: str, target_audience: str,
                                   known_competitors: list[str] | None = None) -> dict:
    """Track C: competitor research via Claude CLI."""
    known_section = ""
    if known_competitors:
        known_section = f"\nKNOWN COMPETITORS (provided by the client): {', '.join(known_competitors)}\nAnalyze these specifically and find 1-2 additional competitors.\n"

    prompt = f"""You are a market research analyst. Be specific and concise.

Analyze the competitive landscape for this business:

Business: {business_name}
Description: {description}
Target audience: {target_audience}
{known_section}
Return a JSON object:
{{
    "competitors": [
        {{"name": "Competitor Name", "positioning": "their key value prop", "visual_style": "their website aesthetic"}}
    ],
    "positioning_gaps": ["gap 1", "gap 2"],
    "recommended_angles": ["angle 1", "angle 2"]
}}

List 3-5 competitors (include any known ones above), 2-3 positioning gaps, and 2-3 recommended angles.
Return ONLY valid JSON, no markdown fences."""

    result = await _claude_json(prompt, label="competitor-research")
    if result:
        return result
    return {"competitors": [], "positioning_gaps": [], "recommended_angles": []}


async def _empty_scrape() -> dict:
    """Return empty scrape result when no URL is provided."""
    return {"home": None, "pages": [], "nav_links": [], "error": "No URL provided"}


async def _run_enrichment(page_id: UUID):
    """Background task: enrich selected template with synthesized copy, run QA, set client_preview."""
    pool = await get_pool()

    try:
        row = await pool.fetchrow(
            """SELECT id, business_name, business_url, description, target_audience,
                      project_id, generations, synthesized_copy, selected_template
               FROM landing_pages WHERE id = $1""",
            page_id,
        )
        if not row:
            return

        business_name = row["business_name"]
        project_id = row["project_id"]
        selected = row["selected_template"]
        gens = row["generations"]
        if isinstance(gens, str):
            gens = json.loads(gens)
        copy_data = row["synthesized_copy"]
        if isinstance(copy_data, str):
            copy_data = json.loads(copy_data)

        variant = gens.get(selected, {})
        template_html = variant.get("html_path")
        if not template_html:
            raise RuntimeError(f"No HTML path for selected template '{selected}'")

        # ── Phase 4: Enrichment ───────────────────────────────────
        await pool.execute(
            "UPDATE landing_pages SET status = 'enriching', updated_at = now() WHERE id = $1",
            page_id,
        )
        await _sync_project_stage(project_id, "development", 70)

        from services.landing_page.agent_generator import enrich_template

        enrich_result = await enrich_template(
            page_id=page_id,
            template_html_path=template_html,
            copy_json=copy_data,
            business_name=business_name,
        )

        # ── Phase 4.5: QA pass ────────────────────────────────────
        await pool.execute(
            "UPDATE landing_pages SET status = 'qa', updated_at = now() WHERE id = $1",
            page_id,
        )
        await _sync_project_stage(project_id, "quality_assurance", 85)

        from services.landing_page.agent_generator import _build_qa_prompt, _run_agent
        import os

        qa_prompt = _build_qa_prompt(page_id, business_name)
        qa_cmd = [
            "/home/web3relic/.local/bin/claude",
            "--print", "--dangerously-skip-permissions",
            "--model", "claude-sonnet-4-6",
            "--max-turns", "8", "--max-budget-usd", "1",
            "-p", qa_prompt,
        ]
        env = {**os.environ, "HOME": "/home/web3relic"}
        await _run_agent(qa_cmd, page_id, "qa", env, timeout=300)

        # ── Phase 5: Client preview ───────────────────────────────
        preview_url = f"https://webassist.otto.lk/{page_id}"
        await pool.execute(
            """UPDATE landing_pages
               SET status = 'client_preview', html_path = $2, preview_url = $3,
                   error_text = NULL, updated_at = now()
               WHERE id = $1""",
            page_id, enrich_result["html_path"], preview_url,
        )
        await _sync_project_stage(project_id, "client_preview", 90)

        logger.info("[enrich:%s] Complete → client_preview at %s", page_id, preview_url)

    except Exception as exc:
        logger.exception("[enrich:%s] Failed: %s", page_id, exc)
        await pool.execute(
            "UPDATE landing_pages SET status = 'failed', error_text = $2, updated_at = now() WHERE id = $1",
            page_id, str(exc)[:1000],
        )
        project_id = (await pool.fetchval("SELECT project_id FROM landing_pages WHERE id = $1", page_id))
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
    businessDescription: Optional[str] = Field(None, max_length=2000)
    websiteType: Optional[str] = Field(None, max_length=100)
    websitePurpose: Optional[str] = Field(None, max_length=1000)
    designStyle: Optional[str] = Field(None, max_length=100)
    features: Optional[list[str]] = None
    pagesNeeded: Optional[list[str]] = None
    competitors: Optional[list[str]] = None
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
        "SELECT id, status, preview_url, error_text, generations, selected_template, created_at, updated_at FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    progress = {
        "pending": 0,
        "phase1": 20, "synthesizing": 35, "design_review": 50,
        "template_review": 65, "enriching": 75, "qa": 85, "client_preview": 95,
        "published": 100, "archived": 100, "failed": 0,
        # Legacy
        "researching": 15, "designing": 30, "generating": 50, "review": 100,
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
        "selected_template": row["selected_template"] if "selected_template" in row.keys() else None,
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
        "pending": 0, "phase1": 20, "synthesizing": 35, "design_review": 50, "template_review": 65,
        "enriching": 70, "qa": 85, "client_preview": 95,
        "published": 100, "archived": 100, "failed": 0,
        "researching": 15, "generating": 50, "review": 100,
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
    # Use the client's own business description as primary, supplement with structured fields
    description = body.businessDescription or ""
    structured_parts = []
    if body.industry:
        structured_parts.append(f"Industry: {body.industry}")
    if body.websitePurpose:
        structured_parts.append(f"Purpose: {body.websitePurpose}")
    if body.features:
        structured_parts.append(f"Features: {', '.join(body.features)}")
    if body.pagesNeeded:
        structured_parts.append(f"Pages: {', '.join(body.pagesNeeded)}")
    if body.designStyle:
        structured_parts.append(f"Design style: {body.designStyle}")
    if structured_parts:
        supplement = ". ".join(structured_parts)
        description = f"{description}\n{supplement}" if description else supplement

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
        competitors=body.competitors,
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


# ── Design Review Endpoints ──────────────────────────────────────────────

DESIGNS_DIR = "/var/www/webassist"


@router.get("/{page_id}/designs")
async def list_design_options(page_id: UUID):
    """List all 3 design.md options with their content."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT design_options, selected_design FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    options = row["design_options"]
    if isinstance(options, str):
        options = json.loads(options)

    from pathlib import Path
    result = {}
    for key, meta in options.items():
        entry = {**meta}
        file_path = meta.get("file_path")
        if file_path and Path(file_path).exists():
            entry["content"] = Path(file_path).read_text(encoding="utf-8")
        else:
            entry["content"] = None
        result[key] = entry

    return {
        "options": result,
        "selected_design": row["selected_design"],
    }


@router.get("/{page_id}/designs/{option}")
async def read_design_option(page_id: UUID, option: str):
    """Read a single design.md option content."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT design_options FROM landing_pages WHERE id = $1", page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    options = row["design_options"]
    if isinstance(options, str):
        options = json.loads(options)

    meta = options.get(option)
    if not meta:
        raise HTTPException(404, f"Design option '{option}' not found")

    from pathlib import Path
    file_path = meta.get("file_path")
    if not file_path or not Path(file_path).exists():
        raise HTTPException(404, f"Design file not found on disk")

    content = Path(file_path).read_text(encoding="utf-8")
    return {"option": option, "content": content, **meta}


class SaveDesignRequest(BaseModel):
    content: str


@router.put("/{page_id}/designs/{option}")
async def save_design_option(page_id: UUID, option: str, body: SaveDesignRequest):
    """Save edited design.md content back to disk."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT design_options FROM landing_pages WHERE id = $1", page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    options = row["design_options"]
    if isinstance(options, str):
        options = json.loads(options)

    meta = options.get(option)
    if not meta:
        raise HTTPException(404, f"Design option '{option}' not found")

    from pathlib import Path
    file_path = meta.get("file_path")
    if not file_path:
        raise HTTPException(404, "No file path for this option")

    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(file_path).write_text(body.content, encoding="utf-8")

    logger.info("[save-design:%s] Saved %s (%d bytes)", page_id, option, len(body.content))
    return {"option": option, "size": len(body.content)}


class SelectDesignRequest(BaseModel):
    option: str = Field(..., description="Which design to select: 'option_1', 'option_2', or 'option_3'")


@router.post("/{page_id}/select-design")
async def select_design(
    page_id: UUID,
    body: SelectDesignRequest,
    background_tasks: BackgroundTasks,
):
    """Select a design.md option and trigger template generation (Claude + Gemini)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, design_options, project_id FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    options = row["design_options"]
    if isinstance(options, str):
        options = json.loads(options)

    meta = options.get(body.option)
    if not meta or meta.get("status") != "done":
        raise HTTPException(400, f"Design option '{body.option}' not available or failed")

    await pool.execute(
        """UPDATE landing_pages
           SET selected_design = $2, updated_at = now()
           WHERE id = $1""",
        page_id, body.option,
    )

    background_tasks.add_task(_run_template_generation, page_id)

    logger.info("[select-design:%s] Design '%s' selected, template generation queued", page_id, body.option)

    return {"id": str(page_id), "status": "generating", "selected_design": body.option}


# ── POST /landing-pages/{id}/select ───────────────────────────────────────

class SelectRequest(BaseModel):
    generator: str = Field(..., description="Which template to select: 'claude' or 'gemini'")


@router.post("/{page_id}/select")
async def select_template(
    page_id: UUID,
    body: SelectRequest,
    background_tasks: BackgroundTasks,
):
    """Select a design template (claude/gemini) and trigger enrichment with synthesized copy."""
    if body.generator not in ("claude", "gemini"):
        raise HTTPException(400, "generator must be 'claude' or 'gemini'")

    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, generations, project_id FROM landing_pages WHERE id = $1",
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

    # Store selection and trigger enrichment
    await pool.execute(
        """UPDATE landing_pages
           SET selected_template = $2, status = 'enriching', updated_at = now()
           WHERE id = $1""",
        page_id, body.generator,
    )

    background_tasks.add_task(_run_enrichment, page_id)

    logger.info("[select:%s] Template '%s' selected, enrichment queued", page_id, body.generator)

    return {"id": page_id, "status": "enriching", "selected": body.generator}


# ── POST /landing-pages/{id}/publish ──────────────────────────────────────

@router.post("/{page_id}/publish")
async def publish_landing_page(page_id: UUID):
    """Final publish after client preview. Makes the page live."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, status, html_path, project_id FROM landing_pages WHERE id = $1",
        page_id,
    )
    if not row:
        raise HTTPException(404, "Landing page not found")

    if row["status"] not in ("client_preview", "review"):
        raise HTTPException(400, f"Cannot publish from status '{row['status']}'. Must be in client_preview.")

    preview_url = f"https://webassist.otto.lk/{page_id}"

    await pool.execute(
        """UPDATE landing_pages
           SET status = 'published', preview_url = $2, error_text = NULL, updated_at = now()
           WHERE id = $1""",
        page_id, preview_url,
    )

    await _sync_project_stage(row["project_id"], "delivered", 100)

    logger.info("[publish:%s] Published → %s", page_id, preview_url)

    return {"id": page_id, "status": "published", "preview_url": preview_url}


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


# ── POST /landing-pages/sync ────────────────────────────────────────────────

class SyncPayload(BaseModel):
    """Full landing page state from an external standalone instance."""
    id: UUID
    slug: str
    business_name: str
    status: str
    business_url: Optional[str] = None
    description: Optional[str] = None
    target_audience: Optional[str] = None
    project_id: Optional[str] = None
    research_data: Optional[dict] = None
    competitor_data: Optional[dict] = None
    scraped_content: Optional[dict] = None
    synthesized_copy: Optional[dict] = None
    design_decisions: Optional[dict] = None
    design_options: Optional[dict] = None
    selected_design: Optional[str] = None
    generations: Optional[dict] = None
    selected_template: Optional[str] = None
    html_path: Optional[str] = None
    preview_url: Optional[str] = None
    error_text: Optional[str] = None
    source_instance: Optional[str] = None


@router.post("/sync")
async def sync_landing_page(
    body: SyncPayload,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Upsert a landing page from an external standalone instance.

    Called by the standalone sync module after every phase transition.
    Inserts if the page ID doesn't exist, updates if it does.
    """
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    if body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {body.status}")

    pool = await get_pool()

    existing = await pool.fetchval("SELECT 1 FROM landing_pages WHERE id = $1", body.id)

    if existing:
        await pool.execute(
            """UPDATE landing_pages
               SET status = $2,
                   business_name = $3, business_url = $4, description = $5,
                   target_audience = $6, project_id = $7,
                   research_data = COALESCE($8, research_data),
                   competitor_data = COALESCE($9, competitor_data),
                   scraped_content = COALESCE($10, scraped_content),
                   synthesized_copy = COALESCE($11, synthesized_copy),
                   design_decisions = COALESCE($12, design_decisions),
                   design_options = COALESCE($13, design_options),
                   selected_design = COALESCE($14, selected_design),
                   generations = COALESCE($15, generations),
                   selected_template = COALESCE($16, selected_template),
                   html_path = COALESCE($17, html_path),
                   preview_url = COALESCE($18, preview_url),
                   error_text = $19,
                   updated_at = now()
               WHERE id = $1""",
            body.id, body.status,
            body.business_name, body.business_url, body.description,
            body.target_audience, body.project_id,
            json.dumps(body.research_data) if body.research_data else None,
            json.dumps(body.competitor_data) if body.competitor_data else None,
            json.dumps(body.scraped_content) if body.scraped_content else None,
            json.dumps(body.synthesized_copy) if body.synthesized_copy else None,
            json.dumps(body.design_decisions) if body.design_decisions else None,
            json.dumps(body.design_options) if body.design_options else None,
            body.selected_design,
            json.dumps(body.generations) if body.generations else None,
            body.selected_template,
            body.html_path, body.preview_url, body.error_text,
        )
        action = "updated"
    else:
        slug = await _ensure_unique_slug(pool, body.slug)
        await pool.execute(
            """INSERT INTO landing_pages
               (id, slug, business_name, business_url, description, target_audience,
                project_id, status, research_data, competitor_data, scraped_content,
                synthesized_copy, design_decisions, design_options, selected_design,
                generations, selected_template,
                html_path, preview_url, error_text, created_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)""",
            body.id, slug, body.business_name, body.business_url, body.description,
            body.target_audience, body.project_id, body.status,
            json.dumps(body.research_data or {}),
            json.dumps(body.competitor_data or {}),
            json.dumps(body.scraped_content or {}),
            json.dumps(body.synthesized_copy or {}),
            json.dumps(body.design_decisions or {}),
            json.dumps(body.design_options or {}),
            body.selected_design,
            json.dumps(body.generations or {}),
            body.selected_template,
            body.html_path, body.preview_url, body.error_text,
            f"external:{body.source_instance or 'standalone'}",
        )
        action = "created"

    logger.info("[sync:%s] %s (status=%s, source=%s)", body.id, action, body.status, body.source_instance)

    return {"id": str(body.id), "action": action, "status": body.status}


# ── POST /landing-pages/{id}/upload-html ─────────────────────────────────

WEBASSIST_DIR = "/var/www/webassist"

class UploadHtmlRequest(BaseModel):
    content: str = Field(..., description="Full HTML content")
    subdir: Optional[str] = Field(None, description="Subdirectory (e.g. 'claude', 'gemini')")


@router.post("/{page_id}/upload-html")
async def upload_html(
    page_id: UUID,
    body: UploadHtmlRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Accept generated HTML from a remote worker and write to /var/www/webassist/{id}/.

    Used by standalone distribution workers that generate HTML locally
    and need to push it to Otto for serving.
    """
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    pool = await get_pool()
    exists = await pool.fetchval("SELECT 1 FROM landing_pages WHERE id = $1", page_id)
    if not exists:
        raise HTTPException(404, "Landing page not found")

    import os
    from pathlib import Path

    if body.subdir:
        page_dir = Path(WEBASSIST_DIR) / str(page_id) / body.subdir
    else:
        page_dir = Path(WEBASSIST_DIR) / str(page_id)

    page_dir.mkdir(parents=True, exist_ok=True)
    html_file = page_dir / "index.html"
    html_file.write_text(body.content, encoding="utf-8")

    html_path = str(html_file)
    preview_url = f"https://webassist.otto.lk/{page_id}"
    if body.subdir:
        preview_url = f"{preview_url}/{body.subdir}"

    # Update DB with file path
    await pool.execute(
        """UPDATE landing_pages SET html_path = $2, preview_url = $3, updated_at = now()
           WHERE id = $1""",
        page_id, html_path, preview_url,
    )

    size = len(body.content.encode("utf-8"))
    logger.info("[upload-html:%s] Wrote %d bytes to %s", page_id, size, html_path)

    return {
        "html_path": html_path,
        "preview_url": preview_url,
        "size": size,
    }


# ── GET /landing-pages/{id}/html ─────────────────────────────────────────

@router.get("/{page_id}/html")
async def read_html(
    page_id: UUID,
    subdir: Optional[str] = Query(None, description="Subdirectory (claude/gemini)"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Read generated HTML content for editing."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    from pathlib import Path

    if subdir:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / subdir / "index.html"
    else:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / "index.html"

    if not html_file.exists():
        raise HTTPException(404, f"HTML file not found: {html_file}")

    content = html_file.read_text(encoding="utf-8")

    return {
        "content": content,
        "path": str(html_file),
        "size": len(content.encode("utf-8")),
    }


# ── PUT /landing-pages/{id}/html ─────────────────────────────────────────

class SaveHtmlRequest(BaseModel):
    content: str
    subdir: Optional[str] = None


@router.put("/{page_id}/html")
async def save_html(
    page_id: UUID,
    body: SaveHtmlRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """Save edited HTML content (from frontend editor)."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    from pathlib import Path

    if body.subdir:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / body.subdir / "index.html"
    else:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / "index.html"

    if not html_file.parent.exists():
        html_file.parent.mkdir(parents=True, exist_ok=True)

    html_file.write_text(body.content, encoding="utf-8")
    size = len(body.content.encode("utf-8"))

    logger.info("[save-html:%s] Saved %d bytes to %s", page_id, size, html_file)

    return {"path": str(html_file), "size": size}


# ── POST /landing-pages/{id}/ai-edit ─────────────────────────────────────

class AiEditRequest(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=2000)
    subdir: Optional[str] = None


@router.post("/{page_id}/ai-edit")
async def ai_edit_html(
    page_id: UUID,
    body: AiEditRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """AI-powered HTML editing — sends current HTML + instruction to LLM, returns modified HTML."""
    configured_key = settings.landing_page_api_key
    if configured_key:
        if not x_api_key or x_api_key != configured_key:
            raise HTTPException(401, "Invalid or missing API key.")

    from pathlib import Path

    if body.subdir:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / body.subdir / "index.html"
    else:
        html_file = Path(WEBASSIST_DIR) / str(page_id) / "index.html"

    if not html_file.exists():
        raise HTTPException(404, f"HTML file not found: {html_file}")

    content = html_file.read_text(encoding="utf-8")

    if not settings.gemini_api_key:
        raise HTTPException(503, "AI editing requires GEMINI_API_KEY to be configured")

    import google.generativeai as genai
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""You are an expert web developer editing a landing page HTML file.

FILE: {html_file.name}
INSTRUCTION: {body.instruction}

CURRENT CONTENT:
```html
{content}
```

RULES:
- Return the COMPLETE modified file content (not a diff)
- Only make changes relevant to the instruction
- Preserve existing style, structure, and formatting
- Return valid HTML

Respond with a JSON object:
{{"explanation": "brief description of changes", "modified_content": "the full updated HTML"}}"""

    try:
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: model.generate_content(prompt)
        )
        text = response.text

        from ..llm import extract_json
        result = extract_json(text)
        if not result or "modified_content" not in result:
            raise HTTPException(502, "AI did not return valid modified content")

        return {
            "explanation": result.get("explanation", ""),
            "modified_content": result["modified_content"],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("[ai-edit:%s] Failed: %s", page_id, exc)
        raise HTTPException(502, f"AI edit failed: {str(exc)[:200]}")

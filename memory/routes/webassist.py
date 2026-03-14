"""
WebAssist Admin API routes — Supabase data proxy for the OMS admin panel.
Exposes leads (wizard_completions), projects, and stats from the WebAssist Supabase instance.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import httpx

from ..config import settings

router = APIRouter(prefix="/webassist", tags=["webassist"])

SUPABASE_URL = settings.webassist_supabase_url
SUPABASE_KEY = settings.webassist_supabase_service_key


def _headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


async def _supabase_get(path: str, params: dict | None = None) -> list | dict:
    if not _configured():
        raise HTTPException(503, "WebAssist Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, headers=_headers(), params=params)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Supabase error: {resp.text}")
    return resp.json()


async def _supabase_patch(path: str, body: dict) -> dict:
    if not _configured():
        raise HTTPException(503, "WebAssist Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(url, headers=_headers(), json=body)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Supabase error: {resp.text}")
    return resp.json()


# ── Stats ──────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def webassist_stats():
    """Dashboard stats: lead count, project count, stage breakdown."""
    if not _configured():
        return {
            "configured": False,
            "leads": {"total": 0, "this_week": 0},
            "projects": {"total": 0, "active": 0, "completed": 0, "pending_payment": 0},
        }

    leads_task = _supabase_get("wizard_completions", {
        "select": "id,created_at,completion_status",
    })
    projects_task = _supabase_get("projects", {
        "select": "id,status,payment_status,current_stage,created_at",
    })

    import asyncio
    leads_raw, projects_raw = await asyncio.gather(leads_task, projects_task, return_exceptions=True)

    leads = leads_raw if isinstance(leads_raw, list) else []
    projects = projects_raw if isinstance(projects_raw, list) else []

    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    leads_this_week = sum(
        1 for l in leads
        if l.get("created_at") and datetime.fromisoformat(l["created_at"].replace("Z", "+00:00")) > week_ago
    )

    stage_breakdown: dict[str, int] = {}
    for p in projects:
        stage = p.get("current_stage", "unknown")
        stage_breakdown[stage] = stage_breakdown.get(stage, 0) + 1

    return {
        "configured": True,
        "leads": {
            "total": len(leads),
            "this_week": leads_this_week,
        },
        "projects": {
            "total": len(projects),
            "active": sum(1 for p in projects if p.get("status") == "active"),
            "completed": sum(1 for p in projects if p.get("status") == "completed"),
            "pending_payment": sum(1 for p in projects if p.get("payment_status") == "pending"),
            "stage_breakdown": stage_breakdown,
        },
    }


# ── Leads (wizard_completions) ─────────────────────────────────────────────────

@router.get("/leads")
async def list_leads(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """List wizard completion leads, newest first."""
    params: dict = {
        "select": "id,created_at,name,email,company,industry,website_type,budget,timeline,rush_delivery,completion_status",
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if status:
        params["completion_status"] = f"eq.{status}"
    if search:
        # Search by name or email using ILIKE
        params["or"] = f"(name.ilike.*{search}*,email.ilike.*{search}*,company.ilike.*{search}*)"

    return await _supabase_get("wizard_completions", params)


@router.get("/leads/{lead_id}")
async def get_lead(lead_id: str):
    """Get full details of a single lead."""
    results = await _supabase_get("wizard_completions", {
        "select": "*",
        "id": f"eq.{lead_id}",
        "limit": "1",
    })
    if not results:
        raise HTTPException(404, "Lead not found")
    return results[0]


# ── Projects ───────────────────────────────────────────────────────────────────

@router.get("/projects")
async def list_projects(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    stage: Optional[str] = None,
):
    """List projects, newest first."""
    params: dict = {
        "select": "id,created_at,project_number,client_name,client_email,company_name,current_stage,overall_progress,stage_progress,status,payment_status,is_rush_delivery,started_at,expected_completion_at",
        "order": "created_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if status:
        params["status"] = f"eq.{status}"
    if stage:
        params["current_stage"] = f"eq.{stage}"

    return await _supabase_get("projects", params)


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get full project details including stages."""
    import asyncio
    project_task = _supabase_get("projects", {
        "select": "*",
        "id": f"eq.{project_id}",
        "limit": "1",
    })
    stages_task = _supabase_get("project_stages", {
        "select": "*",
        "project_id": f"eq.{project_id}",
        "order": "stage_order.asc",
    })
    updates_task = _supabase_get("project_updates", {
        "select": "id,created_at,update_type,title,message,is_visible_to_client",
        "project_id": f"eq.{project_id}",
        "order": "created_at.desc",
        "limit": "20",
    })
    project_raw, stages_raw, updates_raw = await asyncio.gather(
        project_task, stages_task, updates_task, return_exceptions=True
    )
    if not project_raw or not isinstance(project_raw, list):
        raise HTTPException(404, "Project not found")
    project = project_raw[0]
    project["stages"] = stages_raw if isinstance(stages_raw, list) else []
    project["updates"] = updates_raw if isinstance(updates_raw, list) else []
    return project


@router.patch("/projects/{project_id}")
async def update_project(project_id: str, body: dict):
    """Update project fields (status, assigned_to, etc.)."""
    allowed = {"status", "current_stage", "overall_progress", "stage_progress", "assigned_to"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(400, "No valid fields to update")
    return await _supabase_patch(f"projects?id=eq.{project_id}", update)

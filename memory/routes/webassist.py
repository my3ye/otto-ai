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


async def _supabase_get_safe(path: str, params: dict | None = None) -> list:
    """Like _supabase_get but returns [] instead of raising on error (e.g. schema not applied)."""
    try:
        result = await _supabase_get(path, params)
        return result if isinstance(result, list) else []
    except HTTPException:
        return []


async def _supabase_patch(path: str, body: dict) -> dict:
    if not _configured():
        raise HTTPException(503, "WebAssist Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(url, headers=_headers(), json=body)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Supabase error: {resp.text}")
    return resp.json()


async def _supabase_post(path: str, body: dict) -> dict:
    if not _configured():
        raise HTTPException(503, "WebAssist Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=_headers(), json=body)
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Supabase error: {resp.text}")
    result = resp.json()
    return result[0] if isinstance(result, list) and result else result


async def _supabase_delete(path: str) -> None:
    if not _configured():
        raise HTTPException(503, "WebAssist Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.delete(url, headers=_headers())
    if resp.status_code >= 400:
        raise HTTPException(resp.status_code, f"Supabase error: {resp.text}")


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
    schema_ready = isinstance(leads_raw, list) and isinstance(projects_raw, list)

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
        "schema_ready": schema_ready,
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

    return await _supabase_get_safe("wizard_completions", params)


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

    return await _supabase_get_safe("projects", params)


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


# ── CRM Leads ─────────────────────────────────────────────────────────────────

VALID_PIPELINE_STAGES = ("new", "qualified", "proposal_sent", "project_active", "in_review", "delivered", "maintenance", "lost")
VALID_PACKAGE_TIERS = ("starter", "growth", "enterprise")

CRM_SELECT = "id,created_at,updated_at,stage_changed_at,wizard_completion_id,name,email,company,industry,website_type,budget,timeline,rush_delivery,pipeline_stage,package_tier,assigned_to,internal_notes,lost_reason,project_id"


@router.get("/crm/leads")
async def list_crm_leads(
    stage: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List CRM leads. Filter by stage or search name/email/company."""
    params: dict = {
        "select": CRM_SELECT,
        "order": "stage_changed_at.desc",
        "limit": str(limit),
        "offset": str(offset),
    }
    if stage and stage in VALID_PIPELINE_STAGES:
        params["pipeline_stage"] = f"eq.{stage}"
    if search:
        params["or"] = f"(name.ilike.*{search}*,email.ilike.*{search}*,company.ilike.*{search}*)"
    return await _supabase_get_safe("crm_leads", params)


@router.get("/crm/leads/{lead_id}")
async def get_crm_lead(lead_id: str):
    """Get a single CRM lead with notes and comms."""
    import asyncio
    lead_task = _supabase_get("crm_leads", {"select": CRM_SELECT, "id": f"eq.{lead_id}", "limit": "1"})
    notes_task = _supabase_get("lead_notes", {
        "select": "id,created_at,author,content,note_type",
        "lead_id": f"eq.{lead_id}",
        "order": "created_at.desc",
        "limit": "50",
    })
    comms_task = _supabase_get("lead_comms", {
        "select": "id,created_at,direction,channel,subject,content,author",
        "lead_id": f"eq.{lead_id}",
        "order": "created_at.desc",
        "limit": "50",
    })
    lead_raw, notes_raw, comms_raw = await asyncio.gather(
        lead_task, notes_task, comms_task, return_exceptions=True
    )
    if not lead_raw or not isinstance(lead_raw, list):
        raise HTTPException(404, "CRM lead not found")
    lead = lead_raw[0]
    lead["notes"] = notes_raw if isinstance(notes_raw, list) else []
    lead["comms"] = comms_raw if isinstance(comms_raw, list) else []
    return lead


@router.post("/crm/leads")
async def create_crm_lead(body: dict):
    """Manually create a CRM lead."""
    required = {"name", "email"}
    if not required.issubset(body.keys()):
        raise HTTPException(400, "name and email are required")
    allowed = {"name", "email", "company", "industry", "website_type", "budget", "timeline",
               "rush_delivery", "pipeline_stage", "package_tier", "assigned_to", "internal_notes",
               "wizard_completion_id"}
    data = {k: v for k, v in body.items() if k in allowed}
    if "pipeline_stage" in data and data["pipeline_stage"] not in VALID_PIPELINE_STAGES:
        raise HTTPException(400, f"Invalid pipeline_stage")
    if "package_tier" in data and data["package_tier"] not in VALID_PACKAGE_TIERS:
        raise HTTPException(400, f"Invalid package_tier")
    return await _supabase_post("crm_leads", data)


@router.patch("/crm/leads/{lead_id}")
async def update_crm_lead(lead_id: str, body: dict):
    """Update CRM lead fields."""
    allowed = {"pipeline_stage", "package_tier", "assigned_to", "internal_notes", "lost_reason", "project_id"}
    update = {k: v for k, v in body.items() if k in allowed}
    if not update:
        raise HTTPException(400, "No valid fields to update")
    if "pipeline_stage" in update:
        if update["pipeline_stage"] not in VALID_PIPELINE_STAGES:
            raise HTTPException(400, "Invalid pipeline_stage")
        from datetime import datetime, timezone
        update["stage_changed_at"] = datetime.now(timezone.utc).isoformat()
        update["updated_at"] = update["stage_changed_at"]
    return await _supabase_patch(f"crm_leads?id=eq.{lead_id}", update)


# ── CRM Notes ─────────────────────────────────────────────────────────────────

@router.post("/crm/leads/{lead_id}/notes")
async def add_lead_note(lead_id: str, body: dict):
    """Add a note/activity to a CRM lead."""
    if not body.get("content"):
        raise HTTPException(400, "content is required")
    valid_types = ("note", "call", "email", "meeting", "whatsapp", "system", "stage_change")
    data = {
        "lead_id": lead_id,
        "content": body["content"],
        "author": body.get("author", "Mev"),
        "note_type": body.get("note_type", "note") if body.get("note_type") in valid_types else "note",
    }
    return await _supabase_post("lead_notes", data)


@router.delete("/crm/leads/{lead_id}/notes/{note_id}")
async def delete_lead_note(lead_id: str, note_id: str):
    """Delete a note from a CRM lead."""
    await _supabase_delete(f"lead_notes?id=eq.{note_id}&lead_id=eq.{lead_id}")
    return {"deleted": True}


# ── CRM Comms ─────────────────────────────────────────────────────────────────

@router.post("/crm/leads/{lead_id}/comms")
async def add_lead_comm(lead_id: str, body: dict):
    """Log a communication for a CRM lead."""
    required = {"direction", "channel", "content"}
    if not required.issubset(body.keys()):
        raise HTTPException(400, "direction, channel, and content are required")
    data = {
        "lead_id": lead_id,
        "direction": body["direction"],
        "channel": body["channel"],
        "content": body["content"],
        "subject": body.get("subject"),
        "author": body.get("author", "Mev"),
    }
    return await _supabase_post("lead_comms", data)


# ── CRM Stats ─────────────────────────────────────────────────────────────────

@router.get("/crm/stats")
async def crm_stats():
    """Pipeline stats: count by stage."""
    leads = await _supabase_get_safe("crm_leads", {
        "select": "pipeline_stage,package_tier",
        "limit": "1000",
    })
    stage_counts: dict[str, int] = {}
    tier_counts: dict[str, int] = {}
    for lead in leads:
        s = lead.get("pipeline_stage", "new")
        stage_counts[s] = stage_counts.get(s, 0) + 1
        t = lead.get("package_tier")
        if t:
            tier_counts[t] = tier_counts.get(t, 0) + 1
    return {
        "total": len(leads),
        "by_stage": stage_counts,
        "by_tier": tier_counts,
    }

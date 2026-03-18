"""
Security Vulnerability Intelligence API routes.
Endpoints for querying, filtering, and managing the vulnerability database.
"""
import asyncio
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from ..db import get_pool

router = APIRouter()
log = logging.getLogger("security")


# ─── Models ──────────────────────────────────────────────────────────────────

class VulnUpdateModel(BaseModel):
    mitigation_status: Optional[str] = None
    mitigation_notes: Optional[str] = None
    guardrails: Optional[dict] = None


# ─── Query Endpoints ──────────────────────────────────────────────────────────

@router.get("/security/vulns")
async def list_vulns(
    vertical: Optional[str] = Query(None, description="blockchain|ai|vm_infra|web|mobile|network|robotics|cross_cutting"),
    severity: Optional[str] = Query(None, description="CRITICAL|HIGH|MEDIUM|LOW|INFO"),
    source: Optional[str] = Query(None, description="nvd|defihacklabs|atlas|manual"),
    otto_system: Optional[str] = Query(None, description="Filter by affected Otto system"),
    mitigation_status: Optional[str] = Query(None, description="unreviewed|not_applicable|planned|in_progress|mitigated"),
    q: Optional[str] = Query(None, description="Full-text search"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """
    List vulnerabilities with optional filters.
    Results sorted by severity (CRITICAL first) then published_at desc.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []
        idx = 1

        if vertical:
            conditions.append(f"vertical = ${idx}")
            params.append(vertical)
            idx += 1
        if severity:
            conditions.append(f"severity = ${idx}")
            params.append(severity)
            idx += 1
        if source:
            conditions.append(f"source = ${idx}")
            params.append(source)
            idx += 1
        if mitigation_status:
            conditions.append(f"mitigation_status = ${idx}")
            params.append(mitigation_status)
            idx += 1
        if otto_system:
            conditions.append(f"${idx} = ANY(affected_otto_systems)")
            params.append(otto_system)
            idx += 1
        if q:
            conditions.append(
                f"to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')) @@ plainto_tsquery('english', ${idx})"
            )
            params.append(q)
            idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        severity_order = "CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END"

        rows = await conn.fetch(f"""
            SELECT
                id, title, cve_id, external_id, vertical, category, severity, cvss_score,
                source, source_url, description, affected_products, affected_otto_systems,
                financial_loss_usd, guardrails, mitigation_status, mitigation_notes,
                published_at, fetched_at, updated_at
            FROM vulnerability_intelligence
            {where}
            ORDER BY {severity_order}, published_at DESC NULLS LAST
            LIMIT ${idx} OFFSET ${idx+1}
        """, *params, limit, offset)

        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM vulnerability_intelligence {where}",
            *params
        )

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": [dict(r) for r in rows],
        }


@router.get("/security/vulns/{vuln_id}")
async def get_vuln(vuln_id: str):
    """Get a single vulnerability by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM vulnerability_intelligence WHERE id = $1",
            vuln_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Vulnerability not found")
        return dict(row)


@router.get("/security/stats")
async def get_stats():
    """Vulnerability database statistics — counts by vertical and severity."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        by_vertical = await conn.fetch("""
            SELECT vertical, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE severity = 'CRITICAL') as critical,
                   COUNT(*) FILTER (WHERE severity = 'HIGH') as high,
                   COUNT(*) FILTER (WHERE severity = 'MEDIUM') as medium,
                   COUNT(*) FILTER (WHERE severity = 'LOW') as low
            FROM vulnerability_intelligence
            GROUP BY vertical
            ORDER BY total DESC
        """)

        by_mitigation = await conn.fetch("""
            SELECT mitigation_status, COUNT(*) as cnt
            FROM vulnerability_intelligence
            GROUP BY mitigation_status
            ORDER BY cnt DESC
        """)

        otto_exposure = await conn.fetch("""
            SELECT unnest(affected_otto_systems) as otto_system, COUNT(*) as vuln_count
            FROM vulnerability_intelligence
            WHERE cardinality(affected_otto_systems) > 0
            GROUP BY 1
            ORDER BY vuln_count DESC
            LIMIT 15
        """)

        recent_critical = await conn.fetch("""
            SELECT title, vertical, source, published_at, cvss_score
            FROM vulnerability_intelligence
            WHERE severity IN ('CRITICAL', 'HIGH')
            ORDER BY fetched_at DESC
            LIMIT 10
        """)

        last_sync = await conn.fetch("""
            SELECT source, started_at, records_new, records_updated, status
            FROM vuln_sync_log
            ORDER BY started_at DESC
            LIMIT 10
        """)

        total = await conn.fetchval("SELECT COUNT(*) FROM vulnerability_intelligence")
        unreviewed = await conn.fetchval(
            "SELECT COUNT(*) FROM vulnerability_intelligence WHERE mitigation_status = 'unreviewed'"
        )

        return {
            "total_vulnerabilities": total,
            "unreviewed_count": unreviewed,
            "by_vertical": [dict(r) for r in by_vertical],
            "by_mitigation_status": [dict(r) for r in by_mitigation],
            "otto_system_exposure": [dict(r) for r in otto_exposure],
            "recent_critical_high": [dict(r) for r in recent_critical],
            "last_syncs": [dict(r) for r in last_sync],
        }


@router.get("/security/otto-exposure")
async def get_otto_exposure(otto_system: Optional[str] = None):
    """
    Get vulnerabilities mapped to specific Otto/MY3YE systems.
    If otto_system is specified, return only vulns for that system.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        if otto_system:
            rows = await conn.fetch("""
                SELECT id, title, vertical, severity, cvss_score, category,
                       source, source_url, description, guardrails, mitigation_status,
                       published_at
                FROM vulnerability_intelligence
                WHERE $1 = ANY(affected_otto_systems)
                ORDER BY
                    CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                    cvss_score DESC NULLS LAST
            """, otto_system)
            return {"otto_system": otto_system, "vulnerabilities": [dict(r) for r in rows]}

        # Return summary for all Otto systems
        rows = await conn.fetch("""
            SELECT
                sm.otto_system,
                sm.description,
                sm.criticality as system_criticality,
                COUNT(v.id) as total_vulns,
                COUNT(v.id) FILTER (WHERE v.severity = 'CRITICAL') as critical,
                COUNT(v.id) FILTER (WHERE v.severity = 'HIGH') as high,
                COUNT(v.id) FILTER (WHERE v.mitigation_status = 'unreviewed') as unreviewed
            FROM vuln_system_map sm
            LEFT JOIN vulnerability_intelligence v ON sm.otto_system = ANY(v.affected_otto_systems)
            GROUP BY sm.otto_system, sm.description, sm.criticality
            ORDER BY critical DESC, high DESC
        """)
        return {"systems": [dict(r) for r in rows]}


@router.patch("/security/vulns/{vuln_id}")
async def update_vuln(vuln_id: str, update: VulnUpdateModel):
    """Update mitigation status and notes for a vulnerability."""
    valid_statuses = ("unreviewed", "not_applicable", "planned", "in_progress", "mitigated")
    if update.mitigation_status and update.mitigation_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose: {valid_statuses}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM vulnerability_intelligence WHERE id = $1", vuln_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Vulnerability not found")

        sets = []
        params = [vuln_id]
        idx = 2
        if update.mitigation_status:
            sets.append(f"mitigation_status = ${idx}")
            params.append(update.mitigation_status)
            idx += 1
        if update.mitigation_notes is not None:
            sets.append(f"mitigation_notes = ${idx}")
            params.append(update.mitigation_notes)
            idx += 1
        if update.guardrails is not None:
            sets.append(f"guardrails = ${idx}")
            params.append(json.dumps(update.guardrails))
            idx += 1

        if not sets:
            raise HTTPException(status_code=400, detail="Nothing to update")

        sets.append("updated_at = NOW()")
        await conn.execute(
            f"UPDATE vulnerability_intelligence SET {', '.join(sets)} WHERE id = $1",
            *params
        )

        updated = await conn.fetchrow(
            "SELECT id, title, mitigation_status, mitigation_notes, updated_at FROM vulnerability_intelligence WHERE id = $1",
            vuln_id
        )
        return dict(updated)


# ─── Sync Endpoints ──────────────────────────────────────────────────────────

@router.post("/security/sync")
async def trigger_sync(
    sources: Optional[list[str]] = None,
    days_back: int = Query(7, description="How many days back to fetch CVEs from NVD"),
    background: bool = Query(True, description="Run sync in background (non-blocking)")
):
    """
    Trigger a vulnerability database sync.
    sources: list of ['nvd', 'defihacklabs', 'ai_atlas', 'blockchain_curated']
             or omit for all sources.
    """
    all_sources = ["nvd", "defihacklabs", "ai_atlas", "blockchain_curated"]
    if sources:
        invalid = [s for s in sources if s not in all_sources]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Unknown sources: {invalid}. Valid: {all_sources}")
    else:
        sources = all_sources

    if background:
        # Spawn a background process to run the sync
        env = os.environ.copy()
        script = f"""
import asyncio, sys
sys.path.insert(0, '/home/web3relic/otto')
from memory.security.vuln_collector import run_sync
result = asyncio.run(run_sync(sources={sources!r}, days_back={days_back}))
print(result)
"""
        subprocess.Popen(
            [sys.executable, "-c", script],
            stdout=open("/tmp/vuln_sync.log", "w"),
            stderr=subprocess.STDOUT,
        )
        return {
            "status": "started",
            "sources": sources,
            "days_back": days_back,
            "log": "/tmp/vuln_sync.log",
        }
    else:
        # Run synchronously (blocking)
        sys.path.insert(0, '/home/web3relic/otto')
        from memory.security.vuln_collector import run_sync
        result = await run_sync(sources=sources, days_back=days_back)
        return {"status": "complete", "result": result}


@router.get("/security/sync/status")
async def sync_status():
    """Get recent sync log entries."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT source, started_at, completed_at, records_fetched, records_new,
                   records_updated, status, error
            FROM vuln_sync_log
            ORDER BY started_at DESC
            LIMIT 20
        """)
        return {"sync_log": [dict(r) for r in rows]}


@router.get("/security/system-map")
async def get_system_map():
    """Get the Otto/MY3YE system map used for vulnerability cross-mapping."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM vuln_system_map ORDER BY criticality, otto_system")
        return {"systems": [dict(r) for r in rows]}


@router.get("/security/audits")
async def get_audit_history(limit: int = Query(10, le=50)):
    """
    Get recent security audit runs from episodic memory.
    Queries episodic_events WHERE event_type = 'security_audit', ordered newest first.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, content, event_type, importance, metadata, created_at
            FROM episodic_events
            WHERE event_type = 'security_audit'
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

        audits = []
        for r in rows:
            row_dict = dict(r)
            meta = row_dict.get("metadata")
            if isinstance(meta, str):
                try:
                    row_dict["metadata"] = json.loads(meta)
                except Exception:
                    row_dict["metadata"] = {}
            audits.append(row_dict)

        return {
            "total": len(audits),
            "audits": audits,
        }

"""
Leads API routes — Web Assist lead database stats and queries.
"""

from fastapi import APIRouter, HTTPException
from ..db import get_pool

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/stats")
async def lead_stats():
    """Summary stats for the Web Assist lead database."""
    pool = await get_pool()

    # Overall counts by lead type
    by_type = await pool.fetch("""
        SELECT lead_type, COUNT(*) as count, ROUND(AVG(lead_score)::numeric, 1) as avg_score
        FROM web_assist_leads
        WHERE business_status = 'OPERATIONAL' OR business_status IS NULL
        GROUP BY lead_type
        ORDER BY count DESC
    """)

    # Top cities
    top_cities = await pool.fetch("""
        SELECT city, COUNT(*) as count
        FROM web_assist_leads
        WHERE city IS NOT NULL
        GROUP BY city
        ORDER BY count DESC
        LIMIT 10
    """)

    # Outreach status breakdown
    outreach = await pool.fetch("""
        SELECT outreach_status, COUNT(*) as count
        FROM web_assist_leads
        GROUP BY outreach_status
        ORDER BY count DESC
    """)

    # Top scoring leads (score >= 70, not yet contacted)
    top_leads = await pool.fetch("""
        SELECT name, city, phone, website, lead_score, lead_type, lead_notes, google_maps_url
        FROM web_assist_leads
        WHERE lead_score >= 70
          AND outreach_status = 'new'
          AND (business_status = 'OPERATIONAL' OR business_status IS NULL)
        ORDER BY lead_score DESC
        LIMIT 20
    """)

    # Last scrape run
    last_run = await pool.fetchrow("""
        SELECT started_at, finished_at, status, leads_found, leads_new, leads_updated
        FROM lead_scrape_runs
        ORDER BY started_at DESC
        LIMIT 1
    """)

    # Total counts
    total = await pool.fetchval("SELECT COUNT(*) FROM web_assist_leads")
    operational = await pool.fetchval(
        "SELECT COUNT(*) FROM web_assist_leads WHERE business_status = 'OPERATIONAL'"
    )

    return {
        "total_leads": total,
        "operational": operational,
        "by_type": [dict(r) for r in by_type],
        "top_cities": [dict(r) for r in top_cities],
        "outreach_status": [dict(r) for r in outreach],
        "top_leads": [dict(r) for r in top_leads],
        "last_scrape_run": dict(last_run) if last_run else None,
    }


@router.get("/top")
async def top_leads(limit: int = 50, lead_type: str = None):
    """Get top-scoring leads, optionally filtered by type."""
    pool = await get_pool()

    if lead_type and lead_type not in ("no_website", "revamp_candidate", "strong_web_presence"):
        raise HTTPException(status_code=400, detail="Invalid lead_type")

    query = """
        SELECT name, city, address, phone, website, lead_score, lead_type,
               lead_notes, google_maps_url, outreach_status, scraped_at
        FROM web_assist_leads
        WHERE outreach_status = 'new'
          AND (business_status = 'OPERATIONAL' OR business_status IS NULL)
    """
    params = []
    if lead_type:
        query += " AND lead_type = $1"
        params.append(lead_type)

    query += f" ORDER BY lead_score DESC LIMIT {min(limit, 200)}"

    rows = await pool.fetch(query, *params)
    return {"leads": [dict(r) for r in rows], "count": len(rows)}

"""
Leads API routes — Web Assist lead database stats and queries.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
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


@router.get("/dashboard", response_class=HTMLResponse)
async def leads_dashboard():
    """Web Assist leads dashboard — visual overview for Mev."""
    pool = await get_pool()

    by_type = await pool.fetch("""
        SELECT lead_type, COUNT(*) as count, ROUND(AVG(lead_score)::numeric, 1) as avg_score
        FROM web_assist_leads
        WHERE business_status = 'OPERATIONAL' OR business_status IS NULL
        GROUP BY lead_type ORDER BY count DESC
    """)

    top_cities = await pool.fetch("""
        SELECT city, COUNT(*) as count FROM web_assist_leads
        WHERE city IS NOT NULL GROUP BY city ORDER BY count DESC LIMIT 8
    """)

    top_leads = await pool.fetch("""
        SELECT name, city, phone, website, lead_score, lead_type, lead_notes, google_maps_url
        FROM web_assist_leads
        WHERE lead_score >= 70 AND outreach_status = 'new'
          AND (business_status = 'OPERATIONAL' OR business_status IS NULL)
        ORDER BY lead_score DESC LIMIT 50
    """)

    last_run = await pool.fetchrow("""
        SELECT started_at, status, leads_found, leads_new FROM lead_scrape_runs
        ORDER BY started_at DESC LIMIT 1
    """)

    total = await pool.fetchval("SELECT COUNT(*) FROM web_assist_leads")

    # Build type cards
    type_colors = {
        "no_website": ("#10b981", "No Website"),
        "revamp_candidate": ("#f59e0b", "Revamp Candidate"),
        "strong_web_presence": ("#6b7280", "Strong Web Presence"),
    }
    type_cards = ""
    for row in by_type:
        lt = row["lead_type"]
        color, label = type_colors.get(lt, ("#6b7280", lt))
        type_cards += f"""
        <div class="card">
            <div class="card-label" style="color:{color}">{label}</div>
            <div class="card-value">{row['count']}</div>
            <div class="card-sub">avg score {row['avg_score']}</div>
        </div>"""

    # Build city bars
    max_city = max((r["count"] for r in top_cities), default=1)
    city_bars = ""
    for row in top_cities:
        pct = int(row["count"] / max_city * 100)
        city_bars += f"""
        <div class="bar-row">
            <span class="bar-label">{row['city']}</span>
            <div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>
            <span class="bar-count">{row['count']}</span>
        </div>"""

    # Build leads table
    lead_rows = ""
    for row in top_leads:
        lt = row["lead_type"]
        badge_color = {"no_website": "#10b981", "revamp_candidate": "#f59e0b"}.get(lt, "#6b7280")
        badge_label = {"no_website": "No Site", "revamp_candidate": "Revamp"}.get(lt, "Strong")
        website_col = f'<a href="{row["website"]}" target="_blank">{row["website"][:30]}...</a>' if row["website"] else '<span style="color:#6b7280">—</span>'
        maps_link = f'<a href="{row["google_maps_url"]}" target="_blank">📍</a>' if row["google_maps_url"] else ""
        lead_rows += f"""
        <tr>
            <td>{row['name']}</td>
            <td>{row['city'] or '—'}</td>
            <td>{row['phone'] or '—'}</td>
            <td>{website_col}</td>
            <td><span class="badge" style="background:{badge_color}">{badge_label}</span></td>
            <td class="score">{row['lead_score']}</td>
            <td>{maps_link}</td>
        </tr>"""

    last_run_str = "Never"
    if last_run:
        ts = last_run["started_at"].strftime("%Y-%m-%d %H:%M UTC")
        last_run_str = f"{ts} · {last_run['leads_new']} new"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Web Assist — Lead Database</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }}
  .header h1 {{ font-size: 1.4rem; font-weight: 700; color: #f1f5f9; }}
  .header .subtitle {{ font-size: 0.85rem; color: #94a3b8; margin-top: 2px; }}
  .logo {{ width: 36px; height: 36px; background: linear-gradient(135deg, #6366f1, #8b5cf6); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}
  .stats-row {{ display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; min-width: 180px; }}
  .card-label {{ font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }}
  .card-value {{ font-size: 2rem; font-weight: 700; color: #f1f5f9; line-height: 1; }}
  .card-sub {{ font-size: 0.8rem; color: #64748b; margin-top: 4px; }}
  .total-card {{ background: linear-gradient(135deg, #1e3a5f, #1e293b); border-color: #3b82f6; }}
  .total-card .card-value {{ color: #60a5fa; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .panel {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px 24px; }}
  .panel h3 {{ font-size: 0.9rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 16px; }}
  .bar-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }}
  .bar-label {{ font-size: 0.85rem; color: #cbd5e1; min-width: 100px; }}
  .bar-track {{ flex: 1; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); border-radius: 4px; }}
  .bar-count {{ font-size: 0.8rem; color: #64748b; min-width: 30px; text-align: right; }}
  .scrape-info {{ font-size: 0.8rem; color: #64748b; }}
  .table-wrap {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
  .table-header {{ padding: 16px 24px; border-bottom: 1px solid #334155; display: flex; align-items: center; justify-content: space-between; }}
  .table-header h3 {{ font-size: 0.9rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; padding: 12px 16px; text-align: left; border-bottom: 1px solid #334155; }}
  td {{ padding: 12px 16px; font-size: 0.85rem; border-bottom: 1px solid #1e293b; color: #cbd5e1; vertical-align: middle; }}
  tr:hover td {{ background: #263148; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 600; color: white; }}
  .score {{ font-weight: 700; color: #f1f5f9; }}
  a {{ color: #60a5fa; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .refresh {{ font-size: 0.75rem; color: #475569; }}
</style>
</head>
<body>
<div class="header">
  <div class="logo">W</div>
  <div>
    <h1>Web Assist — Lead Database</h1>
    <div class="subtitle">Sri Lanka · {total} total leads · Last scrape: {last_run_str}</div>
  </div>
</div>
<div class="container">
  <div class="stats-row">
    <div class="card total-card">
      <div class="card-label" style="color:#60a5fa">Total Leads</div>
      <div class="card-value">{total}</div>
      <div class="card-sub">in database</div>
    </div>
    {type_cards}
  </div>
  <div class="grid">
    <div class="panel">
      <h3>Leads by City</h3>
      {city_bars}
    </div>
    <div class="panel">
      <h3>Pipeline Status</h3>
      <div style="font-size:0.9rem; color:#cbd5e1; line-height:2;">
        🟢 All {total} leads are <strong>new</strong> — outreach not yet started<br>
        📋 Top priority: 119 businesses with <strong>no website</strong><br>
        🔄 Revamp candidates: 46 with <strong>outdated sites</strong><br>
        🔁 Scraper runs <strong>hourly</strong> via systemd<br>
        <br>
        <span class="scrape-info">Last run: {last_run_str}</span>
      </div>
    </div>
  </div>
  <div class="table-wrap">
    <div class="table-header">
      <h3>Top Priority Leads (score ≥ 70)</h3>
      <div><span class="refresh">Auto-refresh: reload page</span> &nbsp; <a href="/leads/export/csv?lead_type=no_website&min_score=70" style="color:#22d3ee;font-size:0.8rem;text-decoration:none;border:1px solid #22d3ee;padding:4px 10px;border-radius:4px;">Export CSV (no-website)</a> &nbsp; <a href="/leads/export/csv?lead_type=revamp_candidate&min_score=0" style="color:#a78bfa;font-size:0.8rem;text-decoration:none;border:1px solid #a78bfa;padding:4px 10px;border-radius:4px;">Export CSV (revamp)</a></div>
    </div>
    <table>
      <thead>
        <tr>
          <th>Business</th><th>City</th><th>Phone</th><th>Website</th><th>Type</th><th>Score</th><th>Map</th>
        </tr>
      </thead>
      <tbody>
        {lead_rows}
      </tbody>
    </table>
  </div>
</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/export/csv")
async def export_leads_csv(
    lead_type: str = None,
    min_score: int = 0,
    outreach_status: str = "new",
    limit: int = 500,
):
    """Export leads as CSV — ready for outreach campaigns."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    pool = await get_pool()

    query = """
        SELECT name, city, address, phone, website, lead_score, lead_type,
               lead_notes, google_maps_url, outreach_status, scraped_at
        FROM web_assist_leads
        WHERE lead_score >= $1
    """
    params = [min_score]

    if lead_type:
        if lead_type not in ("no_website", "revamp_candidate", "strong_web_presence"):
            raise HTTPException(status_code=400, detail="Invalid lead_type")
        params.append(lead_type)
        query += f" AND lead_type = ${len(params)}"

    if outreach_status:
        params.append(outreach_status)
        query += f" AND outreach_status = ${len(params)}"

    query += f" ORDER BY lead_score DESC LIMIT {min(limit, 1000)}"

    rows = await pool.fetch(query, *params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "City", "Address", "Phone", "Website",
        "Score", "Lead Type", "Notes", "Google Maps URL",
        "Outreach Status", "Scraped At"
    ])
    for row in rows:
        writer.writerow([
            row["name"], row["city"], row["address"] or "", row["phone"] or "",
            row["website"] or "", row["lead_score"], row["lead_type"],
            row["lead_notes"] or "", row["google_maps_url"] or "",
            row["outreach_status"], row["scraped_at"]
        ])

    output.seek(0)
    filename = f"web_assist_leads_{lead_type or 'all'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/{lead_id}/outreach")
async def update_outreach_status(lead_id: str, body: dict):
    """Update outreach status for a lead (new → contacted → responded → converted)."""
    pool = await get_pool()

    valid_statuses = ("new", "contacted", "responded", "not_interested", "converted", "invalid")
    status = body.get("status")
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    notes = body.get("notes", "")
    result = await pool.execute(
        """
        UPDATE web_assist_leads
        SET outreach_status = $1,
            lead_notes = CASE WHEN $2 != '' THEN lead_notes || E'\n' || $2 ELSE lead_notes END
        WHERE place_id = $3
        """,
        status, notes, lead_id
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"ok": True, "place_id": lead_id, "status": status}

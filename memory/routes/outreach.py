"""
Outreach Queue API routes — manage AI-generated outreach messages for Web Assist leads.
Mev reviews and approves messages before they're sent.
"""

import asyncio
import logging
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from ..db import get_pool

# Minimum seconds between outreach messages to avoid WhatsApp spam detection
SEND_DELAY_SECONDS = 60

log = logging.getLogger("otto.routes.outreach")

# Athena's WebAssist WhatsApp service (port 3002)
ATHENA_WHATSAPP_URL = "http://localhost:3002"

router = APIRouter(prefix="/outreach", tags=["outreach"])


class ApprovalBody(BaseModel):
    action: str  # "approve" | "reject"
    rejection_reason: str = ""


@router.get("/queue")
async def get_queue(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    lead_type: str = "",
    search: str = "",
):
    """Get outreach messages in queue, filtered by status, lead_type, and search."""
    valid = ("pending", "approved", "rejected", "sent", "failed")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"status must be one of: {valid}")

    pool = await get_pool()

    # Build dynamic WHERE clause
    conditions = ["status = $1"]
    params: list = [status]

    if lead_type:
        params.append(lead_type)
        conditions.append(f"lead_type = ${len(params)}")

    if search:
        params.append(f"%{search}%")
        conditions.append(f"(business_name ILIKE ${len(params)} OR city ILIKE ${len(params)} OR message_body ILIKE ${len(params)})")

    where = " AND ".join(conditions)

    # Count total matching rows
    total = await pool.fetchval(f"SELECT COUNT(*) FROM outreach_queue WHERE {where}", *params)

    # Fetch page
    params_page = params + [limit, offset]
    rows = await pool.fetch(f"""
        SELECT id, business_name, city, phone, website, lead_type, lead_score,
               channel, message_body, status, created_at, approved_at, sent_at
        FROM outreach_queue
        WHERE {where}
        ORDER BY (message_body = 'Web Assist service inquiry') ASC, lead_score DESC NULLS LAST, created_at DESC
        LIMIT ${len(params_page) - 1} OFFSET ${len(params_page)}
    """, *params_page)

    return {
        "status": status,
        "total": total,
        "count": len(rows),
        "messages": [dict(r) for r in rows],
    }


@router.get("/stats")
async def outreach_stats():
    """Stats for the outreach queue."""
    pool = await get_pool()

    by_status = await pool.fetch("""
        SELECT status, COUNT(*) as count
        FROM outreach_queue
        GROUP BY status ORDER BY count DESC
    """)

    by_type = await pool.fetch("""
        SELECT lead_type, status, COUNT(*) as count
        FROM outreach_queue
        GROUP BY lead_type, status ORDER BY lead_type, count DESC
    """)

    return {
        "by_status": [dict(r) for r in by_status],
        "by_type": [dict(r) for r in by_type],
    }


@router.post("/queue/{message_id}/approve")
async def approve_message(message_id: str, body: ApprovalBody):
    """Approve or reject an outreach message."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT id, status FROM outreach_queue WHERE id = $1", message_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    if row["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Message is already '{row['status']}'")

    if body.action == "approve":
        await pool.execute("""
            UPDATE outreach_queue
            SET status = 'approved', approved_at = NOW()
            WHERE id = $1
        """, message_id)
        return {"ok": True, "action": "approved", "id": message_id}

    elif body.action == "reject":
        await pool.execute("""
            UPDATE outreach_queue
            SET status = 'rejected', rejection_reason = $2
            WHERE id = $1
        """, message_id, body.rejection_reason)
        return {"ok": True, "action": "rejected", "id": message_id}

    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")


@router.post("/queue/{message_id}/mark-sent")
async def mark_sent(message_id: str):
    """Mark an approved message as sent (DB only — no actual WhatsApp call)."""
    pool = await get_pool()
    result = await pool.execute("""
        UPDATE outreach_queue
        SET status = 'sent', sent_at = NOW()
        WHERE id = $1 AND status = 'approved'
    """, message_id)
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Message not found or not in approved state")
    return {"ok": True, "id": message_id, "status": "sent"}


@router.post("/queue/{message_id}/send")
async def send_message(message_id: str):
    """Send a single approved message via Athena's WhatsApp (port 3002)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT id, phone, message_body, status FROM outreach_queue WHERE id = $1",
        message_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Message not found")
    if row["status"] not in ("approved", "failed"):
        raise HTTPException(status_code=400, detail=f"Message is '{row['status']}' — only approved/failed can be sent")
    if not row["phone"]:
        raise HTTPException(status_code=400, detail="No phone number on this message")

    # Format JID
    clean_phone = row["phone"].replace("+", "").replace(" ", "").replace("-", "")
    jid = f"{clean_phone}@s.whatsapp.net"

    # Send via Athena (port 3002 — WebAssist line, not Otto's 3001)
    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            resp = await http.post(
                f"{ATHENA_WHATSAPP_URL}/send",
                json={"jid": jid, "message": row["message_body"]},
            )
            if resp.status_code != 200:
                # Mark as failed
                await pool.execute(
                    "UPDATE outreach_queue SET status = 'failed' WHERE id = $1",
                    message_id,
                )
                raise HTTPException(
                    status_code=502,
                    detail=f"Athena WhatsApp returned {resp.status_code}: {resp.text[:200]}",
                )
    except HTTPException:
        raise
    except Exception as e:
        await pool.execute(
            "UPDATE outreach_queue SET status = 'failed' WHERE id = $1",
            message_id,
        )
        raise HTTPException(status_code=503, detail=f"Athena WhatsApp unreachable: {e}")

    # Mark as sent
    await pool.execute(
        "UPDATE outreach_queue SET status = 'sent', sent_at = NOW() WHERE id = $1",
        message_id,
    )
    # Update lead status
    await pool.execute(
        """UPDATE web_assist_leads SET outreach_status = 'contacted', outreach_at = NOW()
           WHERE id = (SELECT lead_id FROM outreach_queue WHERE id = $1)""",
        message_id,
    )
    log.info(f"Outreach sent via Athena: msg={message_id} jid={jid}")
    return {"ok": True, "id": message_id, "status": "sent", "jid": jid}


@router.post("/queue/send-approved")
async def send_all_approved(limit: int = 50):
    """Send all approved outreach messages via Athena's WhatsApp (port 3002).
    Returns summary of sent/failed counts.
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, phone, message_body FROM outreach_queue
           WHERE status = 'approved' AND phone IS NOT NULL
           ORDER BY lead_score DESC NULLS LAST
           LIMIT $1""",
        limit,
    )
    if not rows:
        return {"ok": True, "sent": 0, "failed": 0, "detail": "No approved messages to send"}

    sent_ids = []
    failed_ids = []

    async with httpx.AsyncClient(timeout=15.0) as http:
        for i, row in enumerate(rows):
            clean_phone = row["phone"].replace("+", "").replace(" ", "").replace("-", "")
            jid = f"{clean_phone}@s.whatsapp.net"
            try:
                resp = await http.post(
                    f"{ATHENA_WHATSAPP_URL}/send",
                    json={"jid": jid, "message": row["message_body"]},
                )
                if resp.status_code == 200:
                    await pool.execute(
                        "UPDATE outreach_queue SET status = 'sent', sent_at = NOW() WHERE id = $1",
                        row["id"],
                    )
                    await pool.execute(
                        """UPDATE web_assist_leads SET outreach_status = 'contacted', outreach_at = NOW()
                           WHERE id = (SELECT lead_id FROM outreach_queue WHERE id = $1)""",
                        row["id"],
                    )
                    sent_ids.append(str(row["id"]))
                    log.info(f"Outreach sent: msg={row['id']} jid={jid}")
                else:
                    await pool.execute(
                        "UPDATE outreach_queue SET status = 'failed' WHERE id = $1",
                        row["id"],
                    )
                    failed_ids.append(str(row["id"]))
                    log.warning(f"Outreach send failed: msg={row['id']} status={resp.status_code}")
            except Exception as e:
                await pool.execute(
                    "UPDATE outreach_queue SET status = 'failed' WHERE id = $1",
                    row["id"],
                )
                failed_ids.append(str(row["id"]))
                log.error(f"Outreach send error: msg={row['id']} error={e}")

            # Throttle: max 1 message per minute to avoid WhatsApp spam detection
            if i < len(rows) - 1:
                log.info(f"Throttling: waiting {SEND_DELAY_SECONDS}s before next message ({i+1}/{len(rows)} sent)")
                await asyncio.sleep(SEND_DELAY_SECONDS)

    return {
        "ok": True,
        "sent": len(sent_ids),
        "failed": len(failed_ids),
        "sent_ids": sent_ids,
        "failed_ids": failed_ids,
    }


@router.get("/dashboard", response_class=HTMLResponse)
async def outreach_dashboard():
    """Outreach queue dashboard — review and approve messages."""
    pool = await get_pool()

    pending = await pool.fetch("""
        SELECT id, business_name, city, phone, website, lead_type, lead_score,
               channel, message_body, created_at
        FROM outreach_queue
        WHERE status = 'pending'
        ORDER BY lead_score DESC, created_at DESC
        LIMIT 100
    """)

    stats = await pool.fetch("""
        SELECT status, COUNT(*) as count FROM outreach_queue GROUP BY status
    """)
    stats_dict = {r["status"]: r["count"] for r in stats}

    total_pending = stats_dict.get("pending", 0)
    total_approved = stats_dict.get("approved", 0)
    total_sent = stats_dict.get("sent", 0)
    total_rejected = stats_dict.get("rejected", 0)

    rows_html = ""
    for row in pending:
        lt = row["lead_type"]
        badge_color = {"no_website": "#10b981", "revamp_candidate": "#f59e0b"}.get(lt, "#6b7280")
        badge_label = {"no_website": "No Site", "revamp_candidate": "Revamp"}.get(lt, lt)
        msg = row["message_body"].replace('"', '&quot;').replace('\n', '<br>')
        phone = row["phone"] or "—"
        wa_link = f"https://wa.me/{row['phone'].replace('+','').replace(' ','')}" if row["phone"] else "#"

        rows_html += f"""
        <div class="card" id="card-{row['id']}">
          <div class="card-header">
            <div>
              <strong>{row['business_name']}</strong>
              <span class="badge" style="background:{badge_color}">{badge_label}</span>
              <span class="score">Score: {row['lead_score']}</span>
            </div>
            <div class="meta">{row['city'] or '—'} · {phone}</div>
          </div>
          <div class="message">{msg}</div>
          <div class="actions">
            <a href="{wa_link}" target="_blank" class="btn btn-wa">Open WhatsApp</a>
            <button class="btn btn-approve" onclick="updateStatus('{row['id']}', 'approve')">Approve</button>
            <button class="btn btn-reject" onclick="updateStatus('{row['id']}', 'reject')">Reject</button>
          </div>
        </div>"""

    if not rows_html:
        rows_html = '<div style="padding:40px;text-align:center;color:#64748b;">No pending messages. Run the generator to create some.</div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Web Assist — Outreach Queue</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; }}
  .header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }}
  .header h1 {{ font-size: 1.4rem; font-weight: 700; color: #f1f5f9; }}
  .logo {{ width: 36px; height: 36px; background: linear-gradient(135deg, #10b981, #6366f1); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 1rem; }}
  .stats-bar {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 12px 32px; display: flex; gap: 24px; font-size: 0.85rem; }}
  .stat {{ color: #94a3b8; }}
  .stat strong {{ color: #f1f5f9; }}
  .container {{ max-width: 860px; margin: 0 auto; padding: 24px 32px; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin-bottom: 16px; }}
  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }}
  .card-header strong {{ font-size: 1rem; color: #f1f5f9; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 0.7rem; font-weight: 600; color: white; margin-left: 8px; }}
  .score {{ font-size: 0.8rem; color: #64748b; margin-left: 8px; }}
  .meta {{ font-size: 0.8rem; color: #64748b; }}
  .message {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 14px 16px; font-size: 0.9rem; line-height: 1.6; color: #cbd5e1; margin-bottom: 14px; white-space: pre-wrap; }}
  .actions {{ display: flex; gap: 10px; flex-wrap: wrap; }}
  .btn {{ padding: 8px 16px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: none; text-decoration: none; display: inline-block; }}
  .btn-approve {{ background: #10b981; color: white; }}
  .btn-approve:hover {{ background: #059669; }}
  .btn-reject {{ background: #334155; color: #94a3b8; }}
  .btn-reject:hover {{ background: #ef4444; color: white; }}
  .btn-wa {{ background: #25d366; color: white; }}
  .btn-wa:hover {{ background: #128c7e; }}
  .removed {{ opacity: 0.3; transition: opacity 0.3s; }}
</style>
</head>
<body>
<div class="header">
  <div class="logo">W</div>
  <div>
    <h1>Web Assist — Outreach Queue</h1>
    <div style="font-size:0.85rem;color:#94a3b8;margin-top:2px;">Review AI-generated messages before sending</div>
  </div>
</div>
<div class="stats-bar">
  <div class="stat">Pending: <strong>{total_pending}</strong></div>
  <div class="stat">Approved: <strong>{total_approved}</strong></div>
  <div class="stat">Sent: <strong>{total_sent}</strong></div>
  <div class="stat">Rejected: <strong>{total_rejected}</strong></div>
  <div class="stat" style="margin-left:auto"><a href="/leads/dashboard" style="color:#60a5fa;font-size:0.8rem;">← Lead Database</a></div>
</div>
<div class="container">
  {rows_html}
</div>
<script>
async function updateStatus(id, action) {{
  const card = document.getElementById('card-' + id);
  const reason = action === 'reject' ? (prompt('Rejection reason (optional):') || '') : '';

  try {{
    const r = await fetch('/outreach/queue/' + id + '/approve', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ action, rejection_reason: reason }})
    }});
    if (r.ok) {{
      card.classList.add('removed');
      setTimeout(() => card.remove(), 400);
    }} else {{
      alert('Error: ' + (await r.json()).detail);
    }}
  }} catch(e) {{
    alert('Network error: ' + e);
  }}
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)

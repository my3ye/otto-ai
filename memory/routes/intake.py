"""
WebAssist Intake API — receives form submissions from the client intake form.
Stores leads in web_assist_leads and notifies via WhatsApp.
"""

import subprocess
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..db import get_pool

router = APIRouter(prefix="/intake", tags=["intake"])


class IntakeSubmission(BaseModel):
    business_name: str
    contact_name: str
    phone: str
    city: Optional[str] = None
    need: Optional[str] = None          # new-website | revamp | landing | ecommerce
    budget: Optional[str] = None        # under-25k | 25k-50k | 50k-100k | over-100k | unsure
    description: Optional[str] = None
    existing_url: Optional[str] = None
    inspiration: Optional[str] = None
    submitted_at: Optional[str] = None
    source: Optional[str] = "intake-form"


@router.post("")
async def receive_intake(data: IntakeSubmission):
    """Receive a WebAssist intake form submission."""
    pool = await get_pool()

    # Map need to lead_type
    lead_type_map = {
        "new-website": "no_website",
        "revamp": "revamp_candidate",
        "landing": "no_website",
        "ecommerce": "no_website",
    }
    lead_type = lead_type_map.get(data.need or "", "unknown")

    # Upsert into web_assist_leads (by phone as unique identifier)
    row = await pool.fetchrow("""
        INSERT INTO web_assist_leads (
            place_id, name, phone, city, country,
            lead_type, lead_notes, outreach_status, search_query
        )
        VALUES (
            $1, $2, $3, $4, 'LK',
            $5, $6, 'intake', 'intake-form'
        )
        ON CONFLICT DO NOTHING
        RETURNING id
    """,
        f"intake-{data.phone.replace(' ', '').replace('+', '')}",
        data.business_name,
        data.phone,
        data.city,
        lead_type,
        f"Contact: {data.contact_name}. Need: {data.need}. Budget: {data.budget}. {data.description or ''}".strip()
    )

    lead_id = str(row["id"]) if row else "duplicate"

    # Notify Mev via WhatsApp
    budget_map = {
        "under-25k": "< 25k",
        "25k-50k": "25k–50k",
        "50k-100k": "50k–100k",
        "over-100k": "> 100k",
        "unsure": "TBD",
    }
    budget_str = budget_map.get(data.budget or "", data.budget or "N/A")

    need_map = {
        "new-website": "New Website",
        "revamp": "Redesign",
        "landing": "Landing Page",
        "ecommerce": "Online Store",
    }
    need_str = need_map.get(data.need or "", data.need or "N/A")

    msg = (
        f"📥 *New WebAssist Intake!*\n\n"
        f"*{data.business_name}* — {data.city or 'SL'}\n"
        f"Contact: {data.contact_name} · {data.phone}\n"
        f"Need: {need_str} · Budget: {budget_str} LKR\n"
        f"{('Desc: ' + data.description[:120] + '...') if data.description else ''}"
    )

    try:
        subprocess.run(
            ["/home/web3relic/otto/tools/whatsapp_send.sh", msg],
            timeout=10, check=False, capture_output=True
        )
    except Exception:
        pass

    return {"status": "received", "lead_id": lead_id}

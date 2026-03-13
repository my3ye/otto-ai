"""
Notify API — webhook for external services to trigger WhatsApp notifications.
Protected by a bearer token (OTTO_WEBHOOK_SECRET env var).
Used by WebAssist (Vercel) to notify Mev when a wizard lead submits.
"""

import os
import subprocess
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/notify", tags=["notify"])

WEBHOOK_SECRET = os.environ.get("OTTO_WEBHOOK_SECRET", "")


def _verify_token(request: Request) -> None:
    """Verify bearer token from Authorization header."""
    if not WEBHOOK_SECRET:
        return  # No secret configured — skip auth (dev mode)
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer ") or auth[7:] != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")


class WizardLeadPayload(BaseModel):
    name: str
    email: str
    company: str
    websiteType: Optional[str] = None
    budget: Optional[str] = None
    timeline: Optional[str] = None
    rushDelivery: Optional[bool] = False
    projectNumber: Optional[str] = None


@router.post("/wizard-lead")
async def wizard_lead_notification(payload: WizardLeadPayload, request: Request):
    """
    Notify Mev via WhatsApp when a WebAssist wizard lead is submitted.
    Called fire-and-forget from the Vercel wizard submit route.
    """
    _verify_token(request)

    rush = "Yes ⚡" if payload.rushDelivery else "No"
    project_line = f"\nProject #: {payload.projectNumber}" if payload.projectNumber else ""

    msg = (
        f"🔔 *New WebAssist Lead!*{project_line}\n\n"
        f"*Name:* {payload.name}\n"
        f"*Email:* {payload.email}\n"
        f"*Company:* {payload.company}\n"
        f"*Type:* {payload.websiteType or 'N/A'}\n"
        f"*Budget:* {payload.budget or 'N/A'}\n"
        f"*Timeline:* {payload.timeline or 'N/A'}\n"
        f"*Rush:* {rush}"
    )

    try:
        subprocess.run(
            ["/home/web3relic/otto/tools/whatsapp_send.sh", msg],
            timeout=10,
            check=False,
            capture_output=True,
        )
    except Exception as e:
        # Don't fail the request if WhatsApp send fails
        return {"status": "notified", "whatsapp": "failed", "error": str(e)}

    return {"status": "notified", "whatsapp": "sent"}

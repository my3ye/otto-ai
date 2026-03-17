"""
Email API routes — POST /email/send, GET /email/inbox, GET /email/status

Otto can send and receive email via otto@otto.lk using Google Workspace (or
any SMTP/IMAP provider).  Credentials live in ~/memory/.env:
  OTTO_EMAIL_ADDRESS   — otto@otto.lk
  OTTO_EMAIL_PASSWORD  — Google Workspace App Password
  OTTO_SMTP_HOST       — smtp.gmail.com  (default)
  OTTO_IMAP_HOST       — imap.gmail.com  (default)
"""

import sys
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List

logger = logging.getLogger("otto.email.routes")

# Import service from interfaces/ directory
import importlib.util, os
_svc_path = os.path.expanduser("~/interfaces/email/email_service.py")
_spec = importlib.util.spec_from_file_location("email_service", _svc_path)
_mod  = importlib.util.module_from_spec(_spec)
try:
    _spec.loader.exec_module(_mod)
    email_service = _mod
    _EMAIL_OK = True
except Exception as _e:
    logger.warning(f"email_service import failed: {_e}")
    email_service = None
    _EMAIL_OK = False

router = APIRouter(prefix="/email", tags=["email"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class SendRequest(BaseModel):
    to: str | List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    reply_to: Optional[str] = None
    from_name: str = "Otto"


class InboxRequest(BaseModel):
    folder: str = "INBOX"
    limit: int = 20
    unread_only: bool = True
    mark_seen: bool = False


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/status")
async def email_status():
    """Check email connectivity (SMTP + IMAP health)."""
    if not _EMAIL_OK or email_service is None:
        return {"ok": False, "error": "email_service module not loaded", "configured": False}
    result = email_service.check_connectivity()
    result["configured"] = bool(os.environ.get("OTTO_EMAIL_PASSWORD"))
    return result


@router.post("/send")
async def send_email(req: SendRequest):
    """
    Send an email from otto@otto.lk.

    Body:
        to: email address or list of addresses
        subject: email subject
        body: plain text body
        html_body: optional HTML version
        reply_to: optional reply-to address
        from_name: display name (default: Otto)
    """
    if not _EMAIL_OK or email_service is None:
        raise HTTPException(503, "Email service not available")

    result = email_service.send_email(
        to=req.to,
        subject=req.subject,
        body=req.body,
        html_body=req.html_body,
        reply_to=req.reply_to,
        from_name=req.from_name,
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Send failed"))
    return result


@router.post("/inbox")
async def fetch_inbox(req: InboxRequest):
    """
    Fetch emails from IMAP inbox.

    Returns list of emails with: id, subject, from, to, date, body, message_id
    """
    if not _EMAIL_OK or email_service is None:
        raise HTTPException(503, "Email service not available")

    result = email_service.fetch_inbox(
        folder=req.folder,
        limit=req.limit,
        unread_only=req.unread_only,
        mark_seen=req.mark_seen,
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Inbox fetch failed"))
    return result


@router.get("/inbox")
async def fetch_inbox_get(folder: str = "INBOX", limit: int = 10, unread_only: bool = True):
    """Shorthand GET for fetching unread inbox (no request body needed)."""
    if not _EMAIL_OK or email_service is None:
        raise HTTPException(503, "Email service not available")

    result = email_service.fetch_inbox(folder=folder, limit=limit, unread_only=unread_only)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Inbox fetch failed"))
    return result

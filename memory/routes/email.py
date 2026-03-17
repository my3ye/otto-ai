"""
Email API routes — Full inbox management + email-based authentication

Otto can send and receive email via otto@otto.lk using Google Workspace (or
any SMTP/IMAP provider).  Credentials live in ~/memory/.env:
  OTTO_EMAIL_ADDRESS   — otto@otto.lk
  OTTO_EMAIL_PASSWORD  — Google Workspace App Password
  OTTO_SMTP_HOST       — smtp.gmail.com  (default)
  OTTO_IMAP_HOST       — imap.gmail.com  (default)

Endpoints:
  GET  /email/status            — SMTP + IMAP health
  POST /email/send              — Send email
  GET  /email/inbox             — Fetch inbox (query params)
  POST /email/inbox             — Fetch inbox (request body)
  GET  /email/inbox/{uid}       — Fetch single email by UID
  POST /email/reply             — Reply to an email (threaded)
  POST /email/inbox/{uid}/read  — Mark as read
  POST /email/inbox/{uid}/unread — Mark as unread
  DELETE /email/inbox/{uid}     — Delete email
  GET  /email/search            — Search inbox
  GET  /email/threads           — Inbox grouped by thread
  GET  /email/folders           — List IMAP folders
  POST /email/auth/request      — Request magic link / OTP
  POST /email/auth/verify       — Verify OTP token → returns session
  GET  /email/auth/pending      — List pending OTP sessions (OMS monitoring)
  DELETE /email/auth/pending/{email} — Revoke a pending OTP session
"""

import logging
import os
import secrets
import importlib.util
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

logger = logging.getLogger("otto.email.routes")

# ── Load email service module ─────────────────────────────────────────────────

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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _svc():
    """Raise 503 if service is not loaded."""
    if not _EMAIL_OK or email_service is None:
        raise HTTPException(503, "Email service not available")
    return email_service


# ── Schemas ───────────────────────────────────────────────────────────────────

class SendRequest(BaseModel):
    to: str | List[str]
    subject: str
    body: str
    html_body: Optional[str] = None
    reply_to: Optional[str] = None
    from_name: str = "Otto"
    in_reply_to: Optional[str] = None   # Message-ID header for threading
    references: Optional[str] = None    # References header chain


class ReplyRequest(BaseModel):
    uid: str                             # UID of message being replied to
    folder: str = "INBOX"
    body: str
    html_body: Optional[str] = None
    from_name: str = "Otto"
    reply_all: bool = False


class InboxRequest(BaseModel):
    folder: str = "INBOX"
    limit: int = 20
    unread_only: bool = True
    mark_seen: bool = False
    include_html: bool = False


class AuthRequestBody(BaseModel):
    email: str
    purpose: str = "login"              # login, verify, reset


class AuthVerifyBody(BaseModel):
    email: str
    token: str


# ── In-memory OTP store (replace with DB for production) ─────────────────────
# Stores: email → {"token": ..., "expires": datetime, "purpose": ...}
_otp_store: dict = {}

OTP_EXPIRY_MINUTES = 15


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/status")
async def email_status():
    """Check email connectivity (SMTP + IMAP health)."""
    svc = _svc()
    result = svc.check_connectivity()
    result["configured"] = bool(os.environ.get("OTTO_EMAIL_PASSWORD"))
    return result


# ── Send ──────────────────────────────────────────────────────────────────────

@router.post("/send")
async def send_email(req: SendRequest):
    """
    Send an email from otto@otto.lk.

    Use `in_reply_to` (Message-ID) + `references` to thread a reply manually.
    For replying to an existing inbox message by UID, use POST /email/reply instead.
    """
    svc = _svc()
    result = svc.send_email(
        to=req.to,
        subject=req.subject,
        body=req.body,
        html_body=req.html_body,
        reply_to=req.reply_to,
        from_name=req.from_name,
        in_reply_to=req.in_reply_to,
        references=req.references,
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Send failed"))
    return result


@router.post("/reply")
async def reply_to_email(req: ReplyRequest):
    """
    Reply to an existing email message (by IMAP UID).

    Automatically fetches the original message to build correct threading headers.
    Prefixes subject with "Re:" if not already present.
    """
    svc = _svc()

    # Fetch original message for threading headers
    fetch_result = svc.fetch_email_by_id(req.uid, folder=req.folder, include_html=False)
    if not fetch_result.get("ok"):
        raise HTTPException(404, detail=f"Original email {req.uid} not found: {fetch_result.get('error')}")

    original = fetch_result["email"]

    # Build subject
    orig_subject = original.get("subject", "")
    if not orig_subject.lower().startswith("re:"):
        subject = f"Re: {orig_subject}"
    else:
        subject = orig_subject

    # Determine recipient(s)
    to_addr = original.get("from", "")
    if req.reply_all:
        to_addr = [original.get("from", ""), original.get("to", "")]
        cc = original.get("cc", "")

    result = svc.send_email(
        to=to_addr,
        subject=subject,
        body=req.body,
        html_body=req.html_body,
        from_name=req.from_name,
        in_reply_to=original.get("message_id", ""),
        references=original.get("references", ""),
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Reply failed"))
    return result


# ── Inbox ─────────────────────────────────────────────────────────────────────

@router.get("/inbox")
async def fetch_inbox_get(
    folder: str = "INBOX",
    limit: int = 20,
    unread_only: bool = False,
    include_html: bool = False,
):
    """Fetch inbox messages (GET shorthand)."""
    svc = _svc()
    result = svc.fetch_inbox(
        folder=folder,
        limit=limit,
        unread_only=unread_only,
        include_html=include_html,
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Inbox fetch failed"))
    return result


@router.post("/inbox")
async def fetch_inbox_post(req: InboxRequest):
    """Fetch inbox messages (POST with full options)."""
    svc = _svc()
    result = svc.fetch_inbox(
        folder=req.folder,
        limit=req.limit,
        unread_only=req.unread_only,
        mark_seen=req.mark_seen,
        include_html=req.include_html,
    )
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Inbox fetch failed"))
    return result


@router.get("/inbox/{uid}")
async def fetch_email(uid: str, folder: str = "INBOX", include_html: bool = True):
    """Fetch a single email by IMAP UID. Marks it as read."""
    svc = _svc()
    result = svc.fetch_email_by_id(uid, folder=folder, include_html=include_html)
    if not result.get("ok"):
        raise HTTPException(404, detail=result.get("error", "Email not found"))
    return result


@router.post("/inbox/{uid}/read")
async def mark_read(uid: str, folder: str = "INBOX"):
    """Mark email as read (\\Seen)."""
    svc = _svc()
    result = svc.mark_email(uid, "\\Seen", add=True, folder=folder)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Mark read failed"))
    return result


@router.post("/inbox/{uid}/unread")
async def mark_unread(uid: str, folder: str = "INBOX"):
    """Mark email as unread (remove \\Seen)."""
    svc = _svc()
    result = svc.mark_email(uid, "\\Seen", add=False, folder=folder)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Mark unread failed"))
    return result


@router.post("/inbox/{uid}/flag")
async def flag_email(uid: str, folder: str = "INBOX"):
    """Star/flag an email (\\Flagged)."""
    svc = _svc()
    result = svc.mark_email(uid, "\\Flagged", add=True, folder=folder)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Flag failed"))
    return result


@router.delete("/inbox/{uid}")
async def delete_email(uid: str, folder: str = "INBOX"):
    """Delete an email (mark Deleted + expunge)."""
    svc = _svc()
    result = svc.delete_email(uid, folder=folder)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Delete failed"))
    return result


# ── Search ────────────────────────────────────────────────────────────────────

@router.get("/search")
async def search_inbox(
    q: str,
    folder: str = "INBOX",
    limit: int = 20,
):
    """Search inbox by subject, sender, or body text."""
    svc = _svc()
    if not q or len(q) < 2:
        raise HTTPException(400, detail="Query must be at least 2 characters")
    result = svc.search_inbox(query=q, folder=folder, limit=limit)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Search failed"))
    return result


# ── Threads ───────────────────────────────────────────────────────────────────

@router.get("/threads")
async def get_threads(
    folder: str = "INBOX",
    limit: int = 20,
    unread_only: bool = False,
):
    """
    Fetch inbox grouped into conversation threads.

    Threads are grouped by subject (normalised) and In-Reply-To headers.
    Returns threads sorted by most recent message.
    """
    svc = _svc()
    result = svc.get_threads(folder=folder, limit=limit, unread_only=unread_only)
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Thread fetch failed"))
    return result


# ── Folders ───────────────────────────────────────────────────────────────────

@router.get("/folders")
async def list_folders():
    """List available IMAP folders/mailboxes."""
    svc = _svc()
    result = svc.list_folders()
    if not result.get("ok"):
        raise HTTPException(500, detail=result.get("error", "Folder list failed"))
    return result


# ── Email-Based Authentication ────────────────────────────────────────────────

@router.post("/auth/request")
async def request_auth_token(req: AuthRequestBody):
    """
    Request an email OTP / magic link for authentication.

    Generates a 6-digit OTP valid for 15 minutes and sends it to the
    provided email address. Used to authenticate users without passwords.

    Use cases:
      - User login to WebAssist / OMS via email
      - Email address verification
      - Password reset flow
    """
    svc = _svc()

    # Generate OTP
    token = str(secrets.randbelow(900000) + 100000)  # 6-digit
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    _otp_store[req.email] = {
        "token"  : token,
        "expires": expires,
        "purpose": req.purpose,
    }

    # Send OTP email
    subject_map = {
        "login" : "Your Otto login code",
        "verify": "Verify your email address",
        "reset" : "Your password reset code",
    }
    subject = subject_map.get(req.purpose, "Your Otto verification code")

    body = f"""Your Otto verification code is:

  {token}

This code expires in {OTP_EXPIRY_MINUTES} minutes.

If you didn't request this, you can safely ignore this email.

— Otto"""

    html_body = f"""<div style="font-family: monospace; max-width: 480px; margin: 40px auto; padding: 32px; background: #0a0a0a; color: #e2e2e2; border: 1px solid #2a2a2a; border-radius: 8px;">
  <h2 style="color: #00ff88; font-size: 18px; margin: 0 0 24px;">Otto — Verification Code</h2>
  <p style="color: #999; margin: 0 0 16px;">Your {req.purpose} code:</p>
  <div style="font-size: 36px; letter-spacing: 12px; color: #00ff88; margin: 24px 0; padding: 16px; background: #111; border-radius: 4px; text-align: center;">{token}</div>
  <p style="color: #666; font-size: 12px; margin: 24px 0 0;">Expires in {OTP_EXPIRY_MINUTES} minutes. If you didn't request this, ignore this email.</p>
</div>"""

    result = svc.send_email(
        to=req.email,
        subject=subject,
        body=body,
        html_body=html_body,
        from_name="Otto",
    )

    if not result.get("ok"):
        # Don't leak internal errors — but log them
        logger.error(f"OTP send failed for {req.email}: {result.get('error')}")
        raise HTTPException(500, detail="Failed to send verification email")

    return {
        "ok"     : True,
        "message": f"Verification code sent to {req.email}",
        "expires": expires.isoformat(),
    }


@router.post("/auth/verify")
async def verify_auth_token(req: AuthVerifyBody):
    """
    Verify an email OTP.

    Returns a session token on success that can be used for subsequent API auth.
    Token is single-use and deleted on verification.
    """
    stored = _otp_store.get(req.email)

    if not stored:
        raise HTTPException(401, detail="No pending verification for this email")

    if datetime.now(timezone.utc) > stored["expires"]:
        del _otp_store[req.email]
        raise HTTPException(401, detail="Verification code expired")

    if stored["token"] != req.token:
        raise HTTPException(401, detail="Invalid verification code")

    # Consume the token
    purpose = stored.pop("purpose", "login")
    del _otp_store[req.email]

    # Generate a simple session token (production: use JWT or store in DB)
    session_token = secrets.token_urlsafe(32)

    return {
        "ok"           : True,
        "email"        : req.email,
        "purpose"      : purpose,
        "session_token": session_token,
        "verified_at"  : datetime.now(timezone.utc).isoformat(),
    }


@router.get("/auth/pending")
async def list_pending_auth():
    """
    List pending (unverified) OTP sessions.

    Returns all active OTP sessions that have been requested but not yet
    verified. Tokens are not exposed — only metadata for monitoring.
    Expired sessions are purged automatically on retrieval.
    """
    now = datetime.now(timezone.utc)
    # Purge expired
    expired = [email for email, data in _otp_store.items() if now > data["expires"]]
    for email in expired:
        del _otp_store[email]

    sessions = [
        {
            "email"  : email,
            "purpose": data["purpose"],
            "expires": data["expires"].isoformat(),
            "expires_in_seconds": max(0, int((data["expires"] - now).total_seconds())),
        }
        for email, data in _otp_store.items()
    ]
    return {"ok": True, "sessions": sessions, "count": len(sessions)}


@router.delete("/auth/pending/{email_addr}")
async def revoke_pending_auth(email_addr: str):
    """
    Revoke (delete) a pending OTP session.

    Allows OMS admins to invalidate an outstanding OTP before it expires.
    """
    if email_addr not in _otp_store:
        raise HTTPException(404, detail="No pending session for this email")
    del _otp_store[email_addr]
    return {"ok": True, "revoked": email_addr}

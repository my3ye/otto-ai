"""
Otto Email Service — Zoho Mail SMTP + IMAP.

Connects to Zoho Mail for sending (SMTP) and receiving (IMAP).

Zoho server stack:
  - SMTP: smtppro.zoho.com:465 (SSL) or :587 (TLS)
  - IMAP: imappro.zoho.com:993 (SSL)
  Account: admin@otto.lk

Supports:
  - SMTP send via Zoho (port 465 / SSL)
  - IMAP receive via Zoho (port 993 / SSL)
  - Reply with proper In-Reply-To / References threading
  - Mark messages read/unread, delete (trash), search
  - Thread grouping by conversation
  - List available folders/mailboxes
  - User authentication via email OTP

Configuration (from ~/memory/.env):
  OTTO_EMAIL_ADDRESS   — admin@otto.lk
  OTTO_EMAIL_PASSWORD  — Zoho account password
  OTTO_SMTP_HOST       — smtppro.zoho.com
  OTTO_SMTP_PORT       — 465 (SSL)
  OTTO_IMAP_HOST       — imappro.zoho.com
  OTTO_IMAP_PORT       — 993 (SSL)
"""

import os
import re
import ssl
import smtplib
import imaplib
import email as email_lib
import logging
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime
from typing import Optional

logger = logging.getLogger("otto.email")

# ── Config ───────────────────────────────────────────────────────────────────
# Load from ~/memory/.env if vars aren't already in environment

def _load_env():
    """Load email vars from .env if not already set."""
    env_file = os.path.expanduser("~/memory/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key, val = key.strip(), val.strip()
                if key.startswith("OTTO_EMAIL") or key.startswith("OTTO_SMTP") or key.startswith("OTTO_IMAP"):
                    os.environ.setdefault(key, val)

_load_env()

# Defaults point to Zoho Mail
OTTO_EMAIL   = os.environ.get("OTTO_EMAIL_ADDRESS", "admin@otto.lk")
EMAIL_PASS   = os.environ.get("OTTO_EMAIL_PASSWORD", "")
# Zoho SMTP (SSL on 465)
SMTP_HOST    = os.environ.get("OTTO_SMTP_HOST", "smtppro.zoho.com")
SMTP_PORT    = int(os.environ.get("OTTO_SMTP_PORT", "465"))
# Zoho IMAP (SSL on 993)
IMAP_HOST    = os.environ.get("OTTO_IMAP_HOST", "imappro.zoho.com")
IMAP_PORT    = int(os.environ.get("OTTO_IMAP_PORT", "993"))

# OTP store for user email authentication (in-memory, 15-min TTL)
_otp_store: dict = {}


def _ssl_context() -> ssl.SSLContext:
    """Standard SSL context for Zoho (proper certificate verification)."""
    return ssl.create_default_context()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _decode_header_value(value: str) -> str:
    """Decode encoded email header (e.g. =?utf-8?q?...?=)."""
    if not value:
        return ""
    parts = decode_header(value)
    decoded = []
    for chunk, charset in parts:
        if isinstance(chunk, bytes):
            decoded.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(chunk)
    return "".join(decoded)


def _extract_body(msg) -> tuple[str, str]:
    """Extract (plain_text, html) body from email message."""
    plain, html = "", ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    plain = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            elif ct == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            ct = msg.get_content_type()
            body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            if ct == "text/html":
                html = body
            else:
                plain = body
    return plain, html


def _build_email_dict(uid, msg, include_html: bool = False) -> dict:
    """Build a standardised email dict from IMAP message."""
    plain, html = _extract_body(msg)
    uid_str = uid.decode() if isinstance(uid, bytes) else str(uid)

    return {
        "id"          : uid_str,
        "message_id"  : msg.get("Message-ID", ""),
        "subject"     : _decode_header_value(msg.get("Subject", "(no subject)")),
        "from"        : _decode_header_value(msg.get("From", "")),
        "to"          : _decode_header_value(msg.get("To", "")),
        "cc"          : _decode_header_value(msg.get("Cc", "")),
        "date"        : msg.get("Date", ""),
        "body"        : plain[:3000],
        "html"        : html[:5000] if include_html else bool(html),
        "in_reply_to" : msg.get("In-Reply-To", ""),
        "references"  : msg.get("References", ""),
    }


def _imap_connect():
    """Return authenticated Zoho IMAP4_SSL connection."""
    mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_ssl_context())
    mail.login(OTTO_EMAIL, EMAIL_PASS)
    return mail


# ── Send ─────────────────────────────────────────────────────────────────────

def send_email(
    to,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    from_name: str = "Otto",
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
) -> dict:
    """
    Send an email via Zoho SMTP (SSL on port 465).

    Args:
        in_reply_to: Message-ID of the email being replied to (for threading)
        references:  Existing References header from original email

    Returns:
        {"ok": True, "message_id": "..."} on success
        {"ok": False, "error": "..."} on failure
    """
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    recipients = [to] if isinstance(to, str) else to

    # Build MIME message
    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEText(body, "plain")

    msg["From"]    = f"{from_name} <{OTTO_EMAIL}>"
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = subject
    msg["Date"]    = email_lib.utils.formatdate(localtime=True)
    if reply_to:
        msg["Reply-To"] = reply_to

    # Threading headers
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references + " " + in_reply_to
        else:
            msg["References"] = in_reply_to

    domain = OTTO_EMAIL.split("@")[1] if "@" in OTTO_EMAIL else "otto.lk"
    msg["Message-ID"] = email_lib.utils.make_msgid(domain=domain)
    message_id = msg["Message-ID"]

    try:
        # Zoho uses SMTP_SSL on port 465 (direct SSL, not STARTTLS)
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=_ssl_context(), timeout=30) as smtp:
                smtp.login(OTTO_EMAIL, EMAIL_PASS)
                smtp.sendmail(OTTO_EMAIL, recipients, msg.as_string())
        else:
            # Fallback: STARTTLS on port 587
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls(context=_ssl_context())
                smtp.ehlo()
                smtp.login(OTTO_EMAIL, EMAIL_PASS)
                smtp.sendmail(OTTO_EMAIL, recipients, msg.as_string())

        logger.info(f"Email sent to {recipients} — subject: {subject!r}")
        return {"ok": True, "message_id": message_id}
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP auth failed: {e}")
        return {"ok": False, "error": f"Authentication failed: {e}"}
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return {"ok": False, "error": str(e)}


# ── Receive ──────────────────────────────────────────────────────────────────

def fetch_inbox(
    folder: str = "INBOX",
    limit: int = 20,
    unread_only: bool = True,
    mark_seen: bool = False,
    include_html: bool = False,
) -> dict:
    """
    Fetch emails from IMAP inbox.

    Returns:
        {"ok": True, "emails": [...], "count": N, "folder": folder}
    """
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        mail.select(folder)

        search_crit = "UNSEEN" if unread_only else "ALL"
        _, msg_ids = mail.search(None, search_crit)

        ids = msg_ids[0].split()
        ids = ids[-limit:][::-1]

        emails = []
        for uid in ids:
            _, msg_data = mail.fetch(uid, "(RFC822 FLAGS)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            entry = _build_email_dict(uid, msg, include_html=include_html)
            flags_data = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
            entry["unread"] = "\\Seen" not in flags_data
            emails.append(entry)

            if mark_seen:
                mail.store(uid, "+FLAGS", "\\Seen")

        mail.logout()
        return {"ok": True, "emails": emails, "count": len(emails), "folder": folder}
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error: {e}")
        return {"ok": False, "error": f"IMAP error: {e}"}
    except Exception as e:
        logger.error(f"Inbox fetch failed: {e}")
        return {"ok": False, "error": str(e)}


def fetch_email_by_id(uid: str, folder: str = "INBOX", include_html: bool = True) -> dict:
    """Fetch a single email by UID and mark it as read."""
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        mail.select(folder)
        _, msg_data = mail.fetch(uid.encode(), "(RFC822 FLAGS)")
        if not msg_data or msg_data[0] is None:
            mail.logout()
            return {"ok": False, "error": f"Email {uid} not found"}

        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)
        entry = _build_email_dict(uid.encode(), msg, include_html=include_html)
        flags_data = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
        entry["unread"] = "\\Seen" not in flags_data

        mail.store(uid.encode(), "+FLAGS", "\\Seen")
        mail.logout()
        return {"ok": True, "email": entry}
    except Exception as e:
        logger.error(f"Fetch email {uid} failed: {e}")
        return {"ok": False, "error": str(e)}


def mark_email(uid: str, flag: str, add: bool = True, folder: str = "INBOX") -> dict:
    """
    Set or unset IMAP flag on a message.

    flag: "\\Seen", "\\Flagged", "\\Deleted"
    add: True to set, False to unset
    """
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        mail.select(folder)
        op = "+FLAGS" if add else "-FLAGS"
        mail.store(uid.encode(), op, flag)
        mail.logout()
        return {"ok": True, "uid": uid, "flag": flag, "added": add}
    except Exception as e:
        logger.error(f"Mark email {uid} failed: {e}")
        return {"ok": False, "error": str(e)}


def delete_email(uid: str, folder: str = "INBOX", expunge: bool = True) -> dict:
    """Delete an email (mark Deleted + expunge)."""
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        mail.select(folder)
        mail.store(uid.encode(), "+FLAGS", "\\Deleted")
        if expunge:
            mail.expunge()
        mail.logout()
        return {"ok": True, "uid": uid, "deleted": True}
    except Exception as e:
        logger.error(f"Delete email {uid} failed: {e}")
        return {"ok": False, "error": str(e)}


def search_inbox(query: str, folder: str = "INBOX", limit: int = 20) -> dict:
    """Search inbox — matches subject, from, or body text."""
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        mail.select(folder)

        try:
            search_str = f'(OR SUBJECT "{query}" FROM "{query}")'
            _, msg_ids = mail.search(None, search_str)
        except Exception:
            _, msg_ids = mail.search(None, f'TEXT "{query}"')

        ids = msg_ids[0].split()
        ids = ids[-limit:][::-1]

        emails = []
        for uid in ids:
            _, msg_data = mail.fetch(uid, "(RFC822 FLAGS)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)
            entry = _build_email_dict(uid, msg)
            flags_data = msg_data[0][0].decode() if isinstance(msg_data[0][0], bytes) else str(msg_data[0][0])
            entry["unread"] = "\\Seen" not in flags_data
            emails.append(entry)

        mail.logout()
        return {"ok": True, "emails": emails, "count": len(emails), "query": query}
    except Exception as e:
        logger.error(f"Search inbox failed: {e}")
        return {"ok": False, "error": str(e)}


def list_folders() -> dict:
    """List all IMAP folders/mailboxes."""
    if not EMAIL_PASS:
        return {"ok": False, "error": "OTTO_EMAIL_PASSWORD not configured"}

    try:
        mail = _imap_connect()
        _, folder_list = mail.list()
        mail.logout()

        folders = []
        for item in folder_list:
            if item:
                decoded = item.decode()
                # Zoho uses "/" as delimiter
                parts = decoded.split(' "/" ')
                if len(parts) < 2:
                    parts = decoded.split(' "." ')
                if len(parts) >= 2:
                    name = parts[-1].strip().strip('"')
                    folders.append(name)
        return {"ok": True, "folders": folders}
    except Exception as e:
        logger.error(f"List folders failed: {e}")
        return {"ok": False, "error": str(e)}


def get_threads(folder: str = "INBOX", limit: int = 20, unread_only: bool = False) -> dict:
    """
    Fetch emails and group by conversation thread.

    Returns threads sorted by most recent activity.
    """
    result = fetch_inbox(folder=folder, limit=limit * 3, unread_only=unread_only)
    if not result.get("ok"):
        return result

    emails = result["emails"]

    threads: dict = {}
    msg_id_to_thread: dict = {}

    def normalise_subject(s: str) -> str:
        return re.sub(r"^(re|fwd|fw):\s*", "", s.lower().strip(), flags=re.IGNORECASE)

    for em in emails:
        base_subj = normalise_subject(em.get("subject", ""))
        reply_to_id = em.get("in_reply_to", "").strip()

        thread_key = None
        if reply_to_id and reply_to_id in msg_id_to_thread:
            thread_key = msg_id_to_thread[reply_to_id]
        elif base_subj in threads:
            thread_key = base_subj
        else:
            thread_key = base_subj or em.get("message_id", em["id"])

        if thread_key not in threads:
            threads[thread_key] = []
        threads[thread_key].append(em)

        if em.get("message_id"):
            msg_id_to_thread[em["message_id"]] = thread_key

    thread_list = []
    for key, messages in threads.items():
        messages.sort(key=lambda m: m.get("date", ""), reverse=True)
        latest = messages[0]
        thread_list.append({
            "thread_key"    : key,
            "subject"       : latest.get("subject", "(no subject)"),
            "participants"  : list({m.get("from", "") for m in messages}),
            "message_count" : len(messages),
            "latest_date"   : latest.get("date", ""),
            "unread_count"  : sum(1 for m in messages if m.get("unread")),
            "messages"      : messages,
        })

    thread_list.sort(key=lambda t: t.get("latest_date", ""), reverse=True)
    thread_list = thread_list[:limit]

    return {"ok": True, "threads": thread_list, "count": len(thread_list), "folder": folder}


def check_connectivity() -> dict:
    """Verify SMTP and IMAP credentials work (without sending)."""
    results = {"smtp": False, "imap": False, "address": OTTO_EMAIL}

    if not EMAIL_PASS:
        results["error"] = "OTTO_EMAIL_PASSWORD not set"
        return results

    # Test SMTP
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=_ssl_context(), timeout=10) as smtp:
                smtp.login(OTTO_EMAIL, EMAIL_PASS)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls(context=_ssl_context())
                smtp.ehlo()
                smtp.login(OTTO_EMAIL, EMAIL_PASS)
        results["smtp"] = True
    except Exception as e:
        results["smtp_error"] = str(e)

    # Test IMAP
    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_ssl_context())
        mail.login(OTTO_EMAIL, EMAIL_PASS)
        mail.logout()
        results["imap"] = True
    except Exception as e:
        results["imap_error"] = str(e)

    return results


# ── User Auth via Email OTP ───────────────────────────────────────────────────

def send_otp(email_address: str) -> dict:
    """
    Send a 6-digit OTP to authenticate a user via their email address.
    OTP expires in 15 minutes.
    """
    otp = "".join(random.choices(string.digits, k=6))
    expiry = datetime.utcnow().timestamp() + 900  # 15 min
    _otp_store[email_address] = {"otp": otp, "expiry": expiry}

    body = f"""Your Otto verification code is: {otp}

This code expires in 15 minutes. Do not share it with anyone.

— Otto (admin@otto.lk)"""

    result = send_email(
        to=email_address,
        subject="Your Otto verification code",
        body=body,
        from_name="Otto Auth",
    )
    if result.get("ok"):
        return {"ok": True, "message": f"OTP sent to {email_address}"}
    return {"ok": False, "error": result.get("error", "send failed")}


def verify_otp(email_address: str, otp: str) -> dict:
    """Verify an OTP. Returns {"ok": True, "email": email} on success."""
    entry = _otp_store.get(email_address)
    if not entry:
        return {"ok": False, "error": "No OTP requested for this address"}
    if datetime.utcnow().timestamp() > entry["expiry"]:
        del _otp_store[email_address]
        return {"ok": False, "error": "OTP expired — request a new one"}
    if entry["otp"] != otp:
        return {"ok": False, "error": "Invalid OTP"}
    del _otp_store[email_address]
    return {"ok": True, "email": email_address}

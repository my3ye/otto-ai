#!/usr/bin/env python3
"""
IMAP IDLE Email Listener — Real-time email intake for Otto.

Maintains a persistent IMAP connection to Zoho using IDLE command.
When new mail arrives, fetches it immediately, normalizes to a
GatewayMessage, and POSTs to /gateway/incoming. If Otto replies,
sends the response via SMTP.

Runs as systemd service: otto-email-listener

Architecture mirrors the WhatsApp adapter:
  New email → normalize → POST /gateway/incoming → deliver reply via SMTP
"""

import os
import sys
import ssl
import time
import json
import email as email_lib
import imaplib
import smtplib
import logging
import signal
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────────

def _load_env():
    env_file = os.path.expanduser("~/memory/.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

_load_env()

IMAP_HOST = os.environ.get("OTTO_IMAP_HOST", "imappro.zoho.com")
IMAP_PORT = int(os.environ.get("OTTO_IMAP_PORT", "993"))
SMTP_HOST = os.environ.get("OTTO_SMTP_HOST", "smtppro.zoho.com")
SMTP_PORT = int(os.environ.get("OTTO_SMTP_PORT", "465"))
EMAIL_ADDR = os.environ.get("OTTO_EMAIL_ADDRESS", "admin@otto.lk")
EMAIL_PASS = os.environ.get("OTTO_EMAIL_PASSWORD", "")
GATEWAY_URL = os.environ.get("OTTO_GATEWAY_URL", "http://localhost:8100/gateway/incoming")

# IDLE timeout: re-issue IDLE every 25 min (Zoho drops at ~29 min)
IDLE_TIMEOUT = 25 * 60

# Reconnect delay on failure
RECONNECT_DELAY = 10
MAX_RECONNECT_DELAY = 300

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("otto.email.idle")

_running = True


def _signal_handler(sig, frame):
    global _running
    log.info("Shutdown signal received")
    _running = False


signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)


# ── Helpers ─────────────────────────────────────────────────────────────

def _ssl_ctx():
    return ssl.create_default_context()


def _decode_hdr(value: str) -> str:
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


def _extract_address(raw: str) -> str:
    """Extract bare email address from 'Name <addr>' format."""
    import re
    m = re.search(r'<(.+?)>', raw)
    return m.group(1).strip() if m else raw.strip()


def _extract_body(msg) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        # Fallback: try HTML
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
    return ""


def _send_reply(to: str, subject: str, body: str,
                in_reply_to: str = "", references: str = ""):
    """Send a reply via Zoho SMTP."""
    msg = MIMEText(body, "plain")
    msg["From"] = f"Otto <{EMAIL_ADDR}>"
    msg["To"] = to
    msg["Subject"] = subject if subject.lower().startswith("re:") else f"Re: {subject}"
    msg["Date"] = email_lib.utils.formatdate(localtime=True)
    msg["Message-ID"] = email_lib.utils.make_msgid(domain="otto.lk")
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = f"{references} {in_reply_to}".strip() if references else in_reply_to

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=_ssl_ctx(), timeout=30) as smtp:
            smtp.login(EMAIL_ADDR, EMAIL_PASS)
            smtp.sendmail(EMAIL_ADDR, [to], msg.as_string())
        log.info("Reply sent to %s — %s", to, subject)
    except Exception as e:
        log.error("Failed to send reply to %s: %s", to, e)


# ── Gateway Integration ─────────────────────────────────────────────────

def _post_to_gateway(sender_addr: str, sender_name: str, subject: str,
                     body: str, message_id: str, uid: str) -> dict | None:
    """POST normalized email to gateway, return response or None."""
    payload = {
        "channel": "email",
        "sender_id": sender_addr,
        "sender_name": sender_name or sender_addr.split("@")[0],
        "content": f"[Email] Subject: {subject}\n\n{body[:3000]}",
        "message_id": uid,
        "metadata": {
            "from_email": sender_addr,
            "subject": subject,
            "message_id": message_id,
            "imap_uid": uid,
        },
    }

    try:
        resp = requests.post(GATEWAY_URL, json=payload, timeout=120)
        if resp.status_code == 200:
            data = resp.json()
            log.info("Gateway response for UID %s: status=%s, len=%d",
                     uid, data.get("metadata", {}).get("status", "?"),
                     len(data.get("content", "")))
            return data
        else:
            log.warning("Gateway returned %d for UID %s: %s",
                        resp.status_code, uid, resp.text[:200])
    except requests.Timeout:
        log.warning("Gateway timeout for UID %s", uid)
    except Exception as e:
        log.error("Gateway POST failed for UID %s: %s", uid, e)

    return None


# ── IMAP IDLE Loop ──────────────────────────────────────────────────────

def _get_existing_uids(mail: imaplib.IMAP4_SSL) -> set:
    """Get all current UIDs in INBOX to avoid processing old mail on startup."""
    mail.select("INBOX")
    _, data = mail.uid("search", None, "ALL")
    if data[0]:
        return set(data[0].split())
    return set()


def _process_new_email(mail: imaplib.IMAP4_SSL, uid: bytes):
    """Fetch a single email by UID and route through gateway."""
    try:
        _, msg_data = mail.uid("fetch", uid, "(RFC822)")
        if not msg_data or msg_data[0] is None:
            log.warning("Could not fetch UID %s", uid)
            return

        raw = msg_data[0][1]
        msg = email_lib.message_from_bytes(raw)

        from_raw = _decode_hdr(msg.get("From", ""))
        sender_addr = _extract_address(from_raw)
        sender_name = from_raw.split("<")[0].strip().strip('"') if "<" in from_raw else ""
        subject = _decode_hdr(msg.get("Subject", "(no subject)"))
        body = _extract_body(msg)
        message_id = msg.get("Message-ID", "")
        references = msg.get("References", "")

        # Skip automated/system emails
        if sender_addr.lower() in ("noreply@zoho.com", "welcome@zoho.com", "notification@zoho.com"):
            log.debug("Skipping automated email from %s", sender_addr)
            return

        log.info("New email from %s — %s", sender_addr, subject)

        # Route through gateway
        response = _post_to_gateway(
            sender_addr=sender_addr,
            sender_name=sender_name,
            subject=subject,
            body=body,
            message_id=message_id,
            uid=uid.decode(),
        )

        # Send reply if gateway provided one
        if response and response.get("content"):
            status = response.get("metadata", {}).get("status", "")
            if status != "ignored":
                _send_reply(
                    to=sender_addr,
                    subject=subject,
                    body=response["content"],
                    in_reply_to=message_id,
                    references=references,
                )

    except Exception as e:
        log.error("Error processing UID %s: %s", uid, e, exc_info=True)


def run_idle_loop():
    """Main IDLE loop — connect, get baseline, then IDLE for new mail."""
    reconnect_delay = RECONNECT_DELAY

    while _running:
        mail = None
        try:
            log.info("Connecting to %s:%d as %s", IMAP_HOST, IMAP_PORT, EMAIL_ADDR)
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, ssl_context=_ssl_ctx())
            mail.login(EMAIL_ADDR, EMAIL_PASS)
            log.info("IMAP login successful")

            # Get existing UIDs so we only process NEW mail
            known_uids = _get_existing_uids(mail)
            log.info("Baseline: %d existing messages in INBOX", len(known_uids))

            reconnect_delay = RECONNECT_DELAY  # Reset on success

            while _running:
                # Enter IDLE mode
                mail.select("INBOX")
                tag = mail._new_tag().decode()
                mail.send(f"{tag} IDLE\r\n".encode())

                # Read the continuation response (+ idling)
                resp = mail.readline().decode()
                if "+" not in resp:
                    log.warning("IDLE not accepted: %s", resp.strip())
                    break

                log.debug("IDLE active, waiting for notifications...")

                # Wait for server notification or timeout
                idle_start = time.time()
                got_mail = False

                while _running and (time.time() - idle_start) < IDLE_TIMEOUT:
                    # Non-blocking read with 30s socket timeout
                    mail.socket().settimeout(30)
                    try:
                        line = mail.readline().decode()
                        if not line:
                            log.warning("IMAP connection dropped")
                            break
                        if "EXISTS" in line:
                            log.info("New mail notification: %s", line.strip())
                            got_mail = True
                            break
                        # Other untagged responses (EXPUNGE, etc.) — continue waiting
                    except (TimeoutError, OSError):
                        # Socket timeout — just re-loop (heartbeat)
                        continue

                # Exit IDLE
                try:
                    mail.send(b"DONE\r\n")
                    # Read the tagged response
                    mail.readline()
                except Exception:
                    pass

                if not _running:
                    break

                if got_mail:
                    # Check for new UIDs
                    mail.select("INBOX")
                    _, data = mail.uid("search", None, "ALL")
                    if data[0]:
                        current_uids = set(data[0].split())
                        new_uids = current_uids - known_uids
                        for uid in sorted(new_uids):
                            _process_new_email(mail, uid)
                        known_uids = current_uids

        except imaplib.IMAP4.abort as e:
            log.warning("IMAP connection aborted: %s", e)
        except Exception as e:
            log.error("IMAP IDLE error: %s", e, exc_info=True)
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

        if _running:
            log.info("Reconnecting in %ds...", reconnect_delay)
            time.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, MAX_RECONNECT_DELAY)


# ── Main ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not EMAIL_PASS:
        log.error("OTTO_EMAIL_PASSWORD not set. Cannot start IDLE listener.")
        sys.exit(1)

    log.info("Starting IMAP IDLE listener for %s", EMAIL_ADDR)
    run_idle_loop()
    log.info("IMAP IDLE listener stopped")

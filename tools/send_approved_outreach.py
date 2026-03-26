#!/usr/bin/env python3
"""
Send all approved outreach messages from the queue.
Handles multiline message bodies correctly (unlike the shell version).

Usage:
    python3 send_approved_outreach.py [--dry-run] [--delay N]
"""

import sys
import os
import json
import time
import subprocess
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone

# DB access via docker exec
DB_CONTAINER = "memory-postgres-1"
DB_USER = "otto"
DB_NAME = "memory"
WHATSAPP_URL = "http://localhost:3002"  # Athena's WebAssist WhatsApp (not Otto's Ottolabs 3001)
DELAY_SECONDS = 5  # between messages (reduced for task execution)

LOG_FORMAT = "%(asctime)s [outreach_sender] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("outreach_sender")


def db_query_json(query):
    """Run a psql query that returns JSON array result."""
    result = subprocess.run(
        ["docker", "exec", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
         "-t", "-A", "-c", query],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"DB error: {result.stderr}")
    return result.stdout.strip()


def fetch_approved_messages():
    """Fetch all approved, unsent outreach messages using JSON output to handle newlines."""
    query = """
    SELECT json_agg(row_to_json(t)) FROM (
        SELECT id, business_name, city, phone, channel, message_body, approved_at
        FROM outreach_queue
        WHERE status = 'approved' AND sent_at IS NULL AND phone IS NOT NULL
        ORDER BY lead_score DESC NULLS LAST
    ) t;
    """
    output = db_query_json(query)
    if not output or output.lower() == "null":
        return []
    return json.loads(output)


def format_phone_jid(phone: str) -> str:
    """Convert international phone to WhatsApp JID."""
    # Strip +, spaces, dashes, parens
    clean = phone.replace("+", "").replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    return f"{clean}@s.whatsapp.net"


def send_whatsapp(jid: str, message: str) -> bool:
    """Send message via local WhatsApp HTTP service."""
    payload = json.dumps({"jid": jid, "message": message})
    try:
        result = subprocess.run(
            ["curl", "-sf", "-X", "POST", f"{WHATSAPP_URL}/send",
             "-H", "Content-Type: application/json",
             "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return True
        log.error(f"curl failed: {result.stdout} {result.stderr}")
        return False
    except Exception as e:
        log.error(f"Send exception: {e}")
        return False


def mark_sent(msg_id: str) -> bool:
    """Mark message as sent via Memory API."""
    try:
        result = subprocess.run(
            ["curl", "-sf", "-X", "POST",
             f"http://localhost:8100/outreach/queue/{msg_id}/mark-sent"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        log.error(f"mark-sent error: {e}")
        return False


def mark_failed(msg_id: str):
    """Mark message as failed in DB."""
    db_query_json(f"UPDATE outreach_queue SET status='failed' WHERE id='{msg_id}';")


def update_lead_contacted(msg_id: str):
    """Update the lead's outreach_status to 'contacted'."""
    db_query_json(f"""
        UPDATE web_assist_leads
        SET outreach_status='contacted', outreach_at=NOW()
        WHERE id=(SELECT lead_id FROM outreach_queue WHERE id='{msg_id}');
    """)


def log_to_episodic(msg_id: str, business_name: str, phone: str, sent: bool):
    """Log the send event to episodic memory."""
    status = "sent" if sent else "failed"
    content = f"Outreach {status}: {business_name} ({phone}) — msg_id={msg_id}"
    try:
        payload = json.dumps({
            "content": content,
            "event_type": "outreach_send",
            "importance": 0.7,
            "metadata": {"msg_id": msg_id, "business": business_name, "phone": phone, "status": status}
        })
        subprocess.run(
            ["curl", "-sf", "-X", "POST", "http://localhost:8100/episodic/events",
             "-H", "Content-Type: application/json", "-d", payload],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        pass  # episodic logging is best-effort


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print without sending")
    parser.add_argument("--delay", type=int, default=DELAY_SECONDS, help="Seconds between sends")
    args = parser.parse_args()

    log.info("Fetching approved outreach messages...")
    messages = fetch_approved_messages()

    if not messages:
        log.info("No approved messages found.")
        print("RESULT: 0 messages sent — queue empty.")
        return

    log.info(f"Found {len(messages)} approved message(s) to send.")

    sent_list = []
    failed_list = []

    for i, msg in enumerate(messages, 1):
        msg_id = msg["id"]
        business_name = msg["business_name"]
        city = msg.get("city", "")
        phone = msg["phone"]
        channel = msg.get("channel", "whatsapp")
        message_body = msg["message_body"]
        approved_at = msg.get("approved_at", "")

        jid = format_phone_jid(phone)

        log.info(f"[{i}/{len(messages)}] {business_name} ({city}) → {phone} [{channel}]")
        log.info(f"  JID: {jid}")
        log.info(f"  Message preview: {message_body[:80]}...")

        if args.dry_run:
            log.info("  DRY RUN — skipping send")
            sent_list.append({"business": business_name, "phone": phone, "jid": jid, "dry_run": True})
            continue

        if channel == "whatsapp":
            success = send_whatsapp(jid, message_body)
        else:
            log.warning(f"  Unknown channel '{channel}' — skipping")
            continue

        if success:
            log.info(f"  ✓ Sent successfully")
            mark_sent(msg_id)
            update_lead_contacted(msg_id)
            log_to_episodic(msg_id, business_name, phone, sent=True)
            sent_list.append({
                "business": business_name,
                "phone": phone,
                "city": city,
                "jid": jid,
                "sent_at": datetime.now(timezone.utc).isoformat()
            })
        else:
            log.error(f"  ✗ Send failed")
            mark_failed(msg_id)
            log_to_episodic(msg_id, business_name, phone, sent=False)
            failed_list.append({"business": business_name, "phone": phone})

        # Polite delay between messages
        if i < len(messages) and not args.dry_run:
            log.info(f"  Waiting {args.delay}s before next message...")
            time.sleep(args.delay)

    # Summary
    log.info(f"Done. Sent: {len(sent_list)}, Failed: {len(failed_list)}")
    print("\n=== OUTREACH SEND SUMMARY ===")
    print(f"Total approved: {len(messages)}")
    print(f"Sent: {len(sent_list)}")
    print(f"Failed: {len(failed_list)}")
    if sent_list:
        print("\nSent to:")
        for s in sent_list:
            print(f"  ✓ {s['business']} ({s.get('city','')}) — {s['phone']}")
    if failed_list:
        print("\nFailed:")
        for f in failed_list:
            print(f"  ✗ {f['business']} — {f['phone']}")


if __name__ == "__main__":
    main()

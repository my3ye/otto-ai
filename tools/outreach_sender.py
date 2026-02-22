#!/usr/bin/env python3
"""
Web Assist Outreach Sender
Sends personalized WhatsApp messages to no-website leads in the DB.

Usage:
    python3 outreach_sender.py --dry-run --limit 5
    python3 outreach_sender.py --limit 10         # sends and marks as contacted
    python3 outreach_sender.py --lead-type revamp --limit 5

Flags:
    --dry-run          Print messages without sending (default: True)
    --limit N          Max number of leads to process (default: 10)
    --lead-type TYPE   Filter by lead_type: no_website | revamp (default: no_website)
    --delay N          Seconds between sends in live mode (default: 5)
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from dotenv import dotenv_values

import psycopg2
import psycopg2.extras

# --- Config ---

ENV_PATH = Path.home() / "memory" / ".env"
WHATSAPP_SEND = "/home/web3relic/otto/tools/whatsapp_send.sh"

LOG_FORMAT = "%(asctime)s [outreach_sender] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("outreach_sender")

# --- Message templates ---

# Template A — No Website (Primary)
TEMPLATE_A1 = (
    "Hi {business_name}! 👋 {rating} stars and {reviews} reviews in {city} — clearly you're doing something right. "
    "But without a website, you're invisible to anyone searching online. "
    "Web Assist builds modern, affordable websites for Sri Lankan businesses — fast. "
    "Want a free mockup to see what yours could look like?"
)

TEMPLATE_A2 = (
    "Hi {business_name}! 👋 I came across your business in {city} and noticed you don't have a website yet. "
    "These days, customers Google everything before they visit — you could be missing a lot. "
    "Web Assist helps Sri Lankan businesses get online quickly and affordably. "
    "Want to see a free mockup of what your site could look like?"
)

TEMPLATE_A3 = (
    "Hi {business_name}! Your business is great in person — but hard to find online. "
    "Web Assist builds fast, affordable websites for Sri Lankan SMBs. "
    "Free mockup, no strings. Interested?"
)

# Template B — Revamp Candidate (Secondary)
TEMPLATE_B1 = (
    "Hi {business_name}! 👋 Saw you're active on Facebook — great start. "
    "But a proper website builds way more trust and gets you found on Google. "
    "Web Assist builds modern sites for Sri Lankan businesses, fast and affordable. "
    "Want to see a free mockup of what yours could look like?"
)

TEMPLATE_B2 = (
    "Hi {business_name}! 👋 I noticed your website could use a refresh. "
    "A modern site works like a 24/7 salesperson — building trust, answering questions, and bringing in new customers. "
    "Web Assist does full website revamps for Sri Lankan businesses at a fixed price. "
    "Want to see what's possible with a free mockup?"
)

TEMPLATE_B3 = (
    "Hi {business_name}! Your current web presence isn't doing justice to what you've built. "
    "Web Assist does modern website revamps for Sri Lankan businesses — fixed price, fast turnaround. "
    "Free mockup to see what's possible?"
)

# Template C — General Fallback
TEMPLATE_C1 = (
    "Hi {business_name}! 👋 We're Web Assist, a local web development service helping Sri Lankan businesses "
    "grow online with modern, affordable websites. "
    "Would you be open to a quick chat? We can offer a free mockup — no commitment needed."
)

TEMPLATE_C2 = (
    "Hi {business_name}! 👋 We're Web Assist — helping {city} businesses get a professional web presence "
    "quickly and affordably. Whether you need a first website or a refresh, we handle everything. "
    "Want to see a free mockup?"
)


def load_env():
    """Load DB credentials from ~/memory/.env"""
    if not ENV_PATH.exists():
        log.error(f"Env file not found: {ENV_PATH}")
        sys.exit(1)
    return dotenv_values(ENV_PATH)


def get_db_conn(env: dict):
    """Connect to PostgreSQL."""
    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env.get("POSTGRES_USER", "otto"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "memory"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )


def fetch_leads(conn, lead_type: str, limit: int) -> list:
    """Fetch leads with outreach_status=new, sorted by lead_score DESC."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, phone, city, lead_type, lead_score, outreach_status,
                   rating, user_ratings_total, lead_notes
            FROM web_assist_leads
            WHERE outreach_status = 'new'
              AND lead_type = %s
              AND phone IS NOT NULL
              AND phone <> ''
            ORDER BY lead_score DESC
            LIMIT %s
            """,
            (lead_type, limit),
        )
        return cur.fetchall()


def build_message(lead: dict) -> tuple:
    """Generate a personalized outreach message.

    Returns:
        (message, template_variant) — template_variant for A/B tracking.
    """
    business_name = lead["name"] or "there"
    city = lead.get("city") or "Sri Lanka"
    rating = lead.get("rating")
    reviews = lead.get("user_ratings_total") or 0
    lead_type = lead["lead_type"]

    if lead_type in ("no_website", "no-website"):
        if rating and rating >= 4.0 and reviews >= 10:
            return (
                TEMPLATE_A1.format(
                    business_name=business_name, city=city,
                    rating=rating, reviews=reviews,
                ),
                "A1",
            )
        else:
            return (
                TEMPLATE_A2.format(business_name=business_name, city=city),
                "A2",
            )

    elif lead_type == "revamp_candidate":
        notes = lead.get("lead_notes", "") or ""
        if "facebook.com" in notes.lower() or "instagram.com" in notes.lower():
            return (
                TEMPLATE_B1.format(business_name=business_name, city=city),
                "B1",
            )
        else:
            return (
                TEMPLATE_B2.format(business_name=business_name, city=city),
                "B2",
            )

    else:
        if city and city != "Sri Lanka":
            return (
                TEMPLATE_C2.format(business_name=business_name, city=city),
                "C2",
            )
        return (
            TEMPLATE_C1.format(business_name=business_name, city=city),
            "C1",
        )


def normalize_phone(phone: str) -> str:
    """Normalize a Sri Lankan phone number to international format."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        return phone
    if phone.startswith("00"):
        return "+" + phone[2:]
    if phone.startswith("0"):
        return "+94" + phone[1:]
    # Assume already in 94XXXXXXXXX format
    if phone.startswith("94"):
        return "+" + phone
    return phone


def send_whatsapp(phone: str, message: str) -> bool:
    """Call whatsapp_send.sh to send a message. Returns True on success."""
    try:
        result = subprocess.run(
            [WHATSAPP_SEND, phone, message],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True
        log.error(f"whatsapp_send.sh failed (code {result.returncode}): {result.stderr}")
        return False
    except subprocess.TimeoutExpired:
        log.error(f"whatsapp_send.sh timed out for {phone}")
        return False
    except Exception as e:
        log.error(f"whatsapp_send.sh error: {e}")
        return False


def mark_contacted(conn, lead_id: str):
    """Update outreach_status to 'contacted' and set outreach_at."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE web_assist_leads
            SET outreach_status = 'contacted',
                outreach_at = NOW()
            WHERE id = %s
            """,
            (lead_id,),
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Web Assist Outreach Sender")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Print messages without sending (default: True)",
    )
    parser.add_argument(
        "--send",
        action="store_true",
        default=False,
        help="Actually send messages (disables dry-run)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max leads to process (default: 10)",
    )
    parser.add_argument(
        "--lead-type",
        type=str,
        default="no_website",
        choices=["no_website", "revamp_candidate"],
        help="Lead type to target (default: no_website)",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=5,
        help="Seconds between sends in live mode (default: 5)",
    )
    args = parser.parse_args()

    # --send overrides default dry-run=True
    dry_run = not args.send

    env = load_env()
    conn = get_db_conn(env)

    try:
        leads = fetch_leads(conn, args.lead_type, args.limit)
        total = len(leads)

        if total == 0:
            log.info(f"No {args.lead_type} leads with outreach_status=new and phone found.")
            return

        mode = "DRY RUN" if dry_run else "LIVE SEND"
        log.info(f"[{mode}] Processing {total} leads (type={args.lead_type}, limit={args.limit})")
        print(f"\n{'='*60}")
        print(f"  Mode: {mode}")
        print(f"  Lead type: {args.lead_type}")
        print(f"  Leads to process: {total}")
        print(f"{'='*60}\n")

        sent = 0
        failed = 0

        for i, lead in enumerate(leads, 1):
            message, template_variant = build_message(lead)
            phone_raw = lead["phone"]
            phone = normalize_phone(phone_raw)

            print(f"[{i}/{total}] {lead['name']}")
            print(f"  Phone (raw): {phone_raw}")
            print(f"  Phone (normalized): {phone}")
            print(f"  City: {lead.get('city', 'N/A')}")
            print(f"  Score: {lead.get('lead_score', 0)}")
            print(f"  Rating: {lead.get('rating', 'N/A')} ({lead.get('user_ratings_total', 0)} reviews)")
            print(f"  Template: {template_variant}")
            print(f"  Message:")
            print(f"    {message}")
            print()

            if not dry_run:
                success = send_whatsapp(phone, message)
                if success:
                    mark_contacted(conn, str(lead["id"]))
                    sent += 1
                    log.info(f"  Sent to {lead['name']} ({phone})")
                else:
                    failed += 1
                    log.warning(f"  Failed: {lead['name']} ({phone})")

                if i < total:
                    time.sleep(args.delay)

        print(f"\n{'='*60}")
        if dry_run:
            print(f"  DRY RUN complete. {total} messages would be sent.")
            print(f"  Run with --send to actually deliver messages.")
        else:
            print(f"  LIVE SEND complete. Sent: {sent} | Failed: {failed}")
        print(f"{'='*60}\n")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

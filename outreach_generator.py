#!/usr/bin/env python3
"""
Web Assist Outreach Generator
Reads top leads from the DB, generates personalized WhatsApp messages via Gemini,
queues them for Mev's approval before sending.
"""

import asyncio
import json
import os
import sys
import httpx
import asyncpg
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/home/web3relic/memory/.env")

_pg_user = os.getenv("POSTGRES_USER", "otto")
_pg_pass = os.getenv("POSTGRES_PASSWORD", "")
_pg_db = os.getenv("POSTGRES_DB", "memory")
_pg_host = os.getenv("POSTGRES_HOST", "localhost")
_pg_port = os.getenv("POSTGRES_PORT", "5432")
DB_DSN = f"postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

BATCH_SIZE = int(sys.argv[1]) if len(sys.argv) > 1 else 10


SYSTEM_PROMPT = """You are a business development assistant for Web Assist, an AI-powered web design service in Sri Lanka.

Web Assist helps local businesses build their online presence with modern, affordable websites.
- New websites: from LKR 25,000 (approx $80 USD)
- Website revamps: from LKR 15,000 (approx $50 USD)
- Fast turnaround: 5-7 business days
- Mobile-first, professional design

Write a SHORT, friendly WhatsApp message (3-4 sentences max) to a local Sri Lankan business.
The message should:
- Be in English (with optional Sinhala greeting if appropriate)
- Sound human and warm, not robotic or salesy
- Mention the specific business by name
- Reference their actual situation (no website / outdated website)
- Offer a specific, low-commitment next step (free consultation / free mockup)
- Never be pushy or spammy
- Be under 200 words

Return ONLY the message text, nothing else."""


async def generate_message(client: httpx.AsyncClient, lead: dict) -> str | None:
    lead_type = lead["lead_type"]
    name = lead["name"]
    city = lead.get("city") or "Sri Lanka"
    rating = lead.get("rating")
    reviews = lead.get("user_ratings_total")

    if lead_type == "no_website":
        situation = f"{name} in {city} doesn't have a website yet"
        pitch = "help them get online and reach more customers"
    else:  # revamp_candidate
        situation = f"{name} in {city} has an older website that could use a refresh"
        pitch = "help modernize their online presence"

    context = ""
    if rating and reviews:
        context = f"They have a {rating} star rating with {reviews} reviews on Google — clearly a well-regarded business."

    prompt = f"""Business: {name}
Location: {city}, Sri Lanka
Situation: {situation}
Context: {context}
Goal: {pitch}

Write the WhatsApp outreach message."""

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},
    }

    try:
        r = await client.post(GEMINI_URL, json=payload, timeout=20)
        r.raise_for_status()
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"  [error] Gemini failed for {name}: {e}")
        return None


async def main():
    print(f"[outreach-generator] Starting — batch size: {BATCH_SIZE}")
    print(f"[outreach-generator] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    conn = await asyncpg.connect(DB_DSN)

    # Fetch top leads not yet in the outreach queue
    leads = await conn.fetch("""
        SELECT l.id, l.place_id, l.name, l.city, l.phone, l.website,
               l.lead_type, l.lead_score, l.lead_notes,
               l.rating, l.user_ratings_total
        FROM web_assist_leads l
        WHERE l.lead_type IN ('no_website', 'revamp_candidate')
          AND l.outreach_status = 'new'
          AND l.phone IS NOT NULL AND l.phone != ''
          AND NOT EXISTS (
              SELECT 1 FROM outreach_queue q
              WHERE q.lead_id = l.id AND q.channel = 'whatsapp'
                AND q.status IN ('pending', 'approved', 'sent')
          )
        ORDER BY l.lead_score DESC, l.user_ratings_total DESC NULLS LAST
        LIMIT $1
    """, BATCH_SIZE)

    print(f"[outreach-generator] Found {len(leads)} leads to generate messages for")

    if not leads:
        print("[outreach-generator] No new leads to process. All top leads already queued.")
        await conn.close()
        return

    generated = 0
    failed = 0

    async with httpx.AsyncClient() as client:
        for lead in leads:
            lead = dict(lead)
            print(f"  Generating for: {lead['name']} ({lead['city']}) — score {lead['lead_score']}")

            message = await generate_message(client, lead)
            if not message:
                failed += 1
                continue

            await conn.execute("""
                INSERT INTO outreach_queue
                    (lead_id, place_id, business_name, city, phone, website,
                     lead_type, lead_score, channel, message_body, status)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'whatsapp', $9, 'pending')
                ON CONFLICT (lead_id, channel) WHERE status IN ('pending', 'approved') DO NOTHING
            """,
                lead["id"], lead["place_id"], lead["name"], lead.get("city"),
                lead.get("phone"), lead.get("website"),
                lead["lead_type"], lead["lead_score"], message
            )

            generated += 1
            print(f"    -> Queued: {message[:80]}...")
            await asyncio.sleep(0.3)  # rate limit

    print(f"\n[outreach-generator] Done. Generated: {generated}, Failed: {failed}")
    print(f"[outreach-generator] View queue: GET http://localhost:8100/outreach/queue")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

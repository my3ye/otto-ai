#!/usr/bin/env python3
"""
Batch-stage leads into outreach_queue with pre-generated messages.
Supports both SL (--country=LK) and AU (--country=AU, default).
"""

import sys
import argparse
from pathlib import Path
from dotenv import dotenv_values
import psycopg2
import psycopg2.extras

ENV_PATH = Path.home() / "memory" / ".env"

# --- SL Templates ---

SL_TEMPLATE_A1 = (
    "Hi {business_name}! 👋 {rating} stars and {reviews} reviews in {city} — clearly you're doing something right. "
    "But without a website, you're invisible to anyone searching online. "
    "Web Assist builds modern, affordable websites for Sri Lankan businesses — fast. "
    "Want a free mockup to see what yours could look like?"
)

SL_TEMPLATE_A2 = (
    "Hi {business_name}! 👋 I came across your business in {city} and noticed you don't have a website yet. "
    "These days, customers Google everything before they visit — you could be missing a lot. "
    "Web Assist helps Sri Lankan businesses get online quickly and affordably. "
    "Want to see a free mockup of what your site could look like?"
)

# --- AU Templates ---

AU_TEMPLATE_A1 = (
    "Hi {business_name}! 👋 {rating} stars with {reviews} reviews in {city} — solid reputation.\n\n"
    "One thing holding you back: no website. When someone Googles your type of business in {city}, you don't show up.\n\n"
    "We build modern, AI-assisted websites for Aussie businesses, fast and without the agency price tag.\n\n"
    "Happy to put together a free mockup so you can see what it'd look like. Want to take a look?"
)

AU_TEMPLATE_A2 = (
    "Hi {business_name}! 👋 Came across your business in {city} — looks like you don't have a website yet.\n\n"
    "In Australia, most people Google before they visit anywhere new. Without a site, you're handing those customers to competitors who do.\n\n"
    "We build clean, professional websites for small businesses — AI-assisted, quick to launch.\n\n"
    "Want a free mockup to see what yours could look like?"
)

AU_TEMPLATE_A3 = (
    "Hi {business_name}! 👋 Noticed your website in {city} — has the look of something built a few years back.\n\n"
    "An outdated site can quietly hurt you: slow load times, no mobile view, and Google tends to rank it lower.\n\n"
    "We refresh and rebuild business websites using AI-assisted tools — faster and more affordable than going back to a traditional agency.\n\n"
    "Happy to show you a free mockup of what a modern version could look like. Interested?"
)


def build_message_sl(lead: dict) -> tuple:
    business_name = lead["name"] or "there"
    city = lead.get("city") or "Sri Lanka"
    rating = lead.get("rating")
    reviews = lead.get("user_ratings_total") or 0

    if rating and float(rating) >= 4.0 and int(reviews) >= 10:
        return (
            SL_TEMPLATE_A1.format(
                business_name=business_name,
                city=city,
                rating=rating,
                reviews=reviews,
            ),
            "A1",
        )
    else:
        return (
            SL_TEMPLATE_A2.format(business_name=business_name, city=city),
            "A2",
        )


def build_message_au(lead: dict) -> tuple:
    business_name = lead["name"] or "there"
    city = lead.get("city") or "your area"
    rating = lead.get("rating")
    reviews = lead.get("user_ratings_total") or 0
    lead_type = lead.get("lead_type") or ""

    if lead_type == "revamp_candidate":
        return (
            AU_TEMPLATE_A3.format(business_name=business_name, city=city),
            "A3",
        )
    elif rating and float(rating) >= 4.0 and int(reviews) >= 10:
        return (
            AU_TEMPLATE_A1.format(
                business_name=business_name,
                city=city,
                rating=rating,
                reviews=reviews,
            ),
            "A1",
        )
    else:
        return (
            AU_TEMPLATE_A2.format(business_name=business_name, city=city),
            "A2",
        )


def main():
    parser = argparse.ArgumentParser(description="Stage leads into outreach queue.")
    parser.add_argument(
        "--country",
        default="AU",
        help="Country code to stage leads for (default: AU). Use LK for Sri Lanka.",
    )
    args = parser.parse_args()
    country = args.country.upper()

    env = dotenv_values(ENV_PATH)
    conn = psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        user=env.get("POSTGRES_USER", "otto"),
        password=env.get("POSTGRES_PASSWORD", ""),
        dbname=env.get("POSTGRES_DB", "memory"),
        cursor_factory=psycopg2.extras.RealDictCursor,
    )

    try:
        with conn.cursor() as cur:
            if country == "LK":
                # SL: only no_website leads
                cur.execute("""
                    SELECT wl.id, wl.name, wl.phone, wl.city, wl.lead_type,
                           wl.lead_score, wl.rating, wl.user_ratings_total,
                           wl.place_id, wl.website
                    FROM web_assist_leads wl
                    WHERE wl.country = 'LK'
                      AND wl.lead_type = 'no_website'
                      AND wl.phone IS NOT NULL
                      AND wl.phone <> ''
                      AND NOT EXISTS (
                        SELECT 1 FROM outreach_queue oq
                        WHERE oq.lead_id = wl.id
                        AND oq.status IN ('pending','approved')
                      )
                    ORDER BY wl.lead_score DESC NULLS LAST
                """)
            else:
                # AU (or other): no_website + revamp_candidate leads
                cur.execute("""
                    SELECT wl.id, wl.name, wl.phone, wl.city, wl.lead_type,
                           wl.lead_score, wl.rating, wl.user_ratings_total,
                           wl.place_id, wl.website
                    FROM web_assist_leads wl
                    WHERE wl.country = %s
                      AND wl.lead_type IN ('no_website', 'revamp_candidate')
                      AND wl.phone IS NOT NULL
                      AND wl.phone <> ''
                      AND NOT EXISTS (
                        SELECT 1 FROM outreach_queue oq
                        WHERE oq.lead_id = wl.id
                        AND oq.status IN ('pending','approved')
                      )
                    ORDER BY wl.lead_score DESC NULLS LAST
                """, (country,))
            leads = cur.fetchall()

        print(f"[{country}] Fetched {len(leads)} eligible leads to stage.")

        if not leads:
            print("Nothing to do.")
            return

        # Build batch insert rows
        rows = []
        template_counts = {}

        for lead in leads:
            if country == "LK":
                message, variant = build_message_sl(lead)
            else:
                message, variant = build_message_au(lead)

            template_counts[variant] = template_counts.get(variant, 0) + 1
            rows.append((
                str(lead["id"]),
                lead["place_id"] or "",
                lead["name"] or "Unknown",
                lead.get("city"),
                lead.get("phone"),
                lead.get("website"),
                lead.get("lead_type") or "no_website",
                lead.get("lead_score"),
                "whatsapp",
                message,
                "pending",
                f"stage_outreach_queue.py:{country}:{variant}",
            ))

        # Batch insert with ON CONFLICT DO NOTHING
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM outreach_queue")
            count_before = cur.fetchone()["count"]

            psycopg2.extras.execute_values(
                cur,
                """
                INSERT INTO outreach_queue
                    (lead_id, place_id, business_name, city, phone, website,
                     lead_type, lead_score, channel, message_body, status, generated_by)
                VALUES %s
                ON CONFLICT DO NOTHING
                """,
                rows,
                template="(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                page_size=200,
            )
            cur.execute("SELECT COUNT(*) FROM outreach_queue")
            count_after = cur.fetchone()["count"]
            inserted = count_after - count_before

        conn.commit()

        print(f"Inserted: {inserted} rows (skipped duplicates if any)")
        dist_parts = ", ".join(f"{k}={v}" for k, v in sorted(template_counts.items()))
        print(f"Template distribution: {dist_parts}")

        # Final queue count
        with conn.cursor() as cur:
            cur.execute("SELECT status, COUNT(*) FROM outreach_queue GROUP BY status ORDER BY status")
            rows_status = cur.fetchall()
        print("\nOutreach queue totals:")
        for row in rows_status:
            print(f"  {row['status']}: {row['count']}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

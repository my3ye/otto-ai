#!/usr/bin/env python3
"""
Web Assist Lead Scraper
Scrapes potential web design/development clients using Google Places API.
Currently targeting Dubai/UAE (pivoted from Australia 2026-02-21 per Mev directive).
Runs hourly via systemd timer (otto-lead-scraper.timer).

Usage:
    python3 lead_scraper.py [--dry-run] [--query "custom query"] [--max-pages N]
"""

import os
import sys
import json
import time
import argparse
import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
import asyncpg

# --- Config ---

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PLACES_API_KEY = os.environ.get("PLACES_API_KEY", GEMINI_API_KEY)  # falls back to Gemini key if same project

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "otto")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "memory")

PLACES_API_BASE = "https://places.googleapis.com/v1"
PLACES_LEGACY_BASE = "https://maps.googleapis.com/maps/api/place"

LOG_FORMAT = "%(asctime)s [lead_scraper] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("lead_scraper")

# --- Dubai/UAE search queries ---
# Pivoted from Australia 2026-02-21 per Mev directive.
# Target: SMBs in Dubai and UAE cities likely to need websites.
# UAE is heavily service-oriented — hospitality, retail, real estate, F&B dominate.
UAE_QUERIES = [
    # === Dubai — Food & Beverage ===
    "restaurants in Deira Dubai",
    "restaurants in Bur Dubai",
    "restaurants in Jumeirah Dubai",
    "restaurants in Business Bay Dubai",
    "restaurants in Downtown Dubai",
    "restaurants in Dubai Marina",
    "restaurants in JLT Dubai",
    "restaurants in Al Quoz Dubai",
    "cafes in Dubai Marina",
    "cafes in Jumeirah Dubai",
    "cafes in Downtown Dubai",
    "cafes in Business Bay Dubai",
    "cafes in JLT Dubai",
    "cafes in Deira Dubai",
    "bakeries in Dubai",
    "juice bars in Dubai",
    "dessert shops in Dubai",
    "Indian restaurants in Dubai",
    "Pakistani restaurants in Dubai",
    "Lebanese restaurants in Dubai",
    # === Dubai — Beauty & Wellness ===
    "beauty salons in Dubai",
    "beauty salons in Deira Dubai",
    "beauty salons in Jumeirah Dubai",
    "beauty salons in Al Barsha Dubai",
    "nail salons in Dubai",
    "nail salons in Jumeirah Dubai",
    "barber shops in Dubai",
    "barber shops in Deira Dubai",
    "spas in Dubai",
    "spas in Jumeirah Dubai",
    "massage centers in Dubai",
    "yoga studios in Dubai",
    "pilates studios in Dubai",
    "gyms in Dubai",
    "gyms in Dubai Marina",
    "gyms in Al Barsha Dubai",
    "fitness centers in Deira Dubai",
    # === Dubai — Medical & Health ===
    "dental clinics in Dubai",
    "dental clinics in Deira Dubai",
    "dental clinics in Jumeirah Dubai",
    "physiotherapy clinics in Dubai",
    "medical clinics in Dubai",
    "medical clinics in Deira Dubai",
    "opticians in Dubai",
    "pharmacies in Dubai",
    # === Dubai — Professional Services ===
    "accounting firms in Dubai",
    "auditing firms in Dubai",
    "legal consultants in Dubai",
    "business setup consultants in Dubai",
    "PRO services in Dubai",
    "HR consultants in Dubai",
    "marketing agencies in Dubai",
    "event management companies in Dubai",
    "photography studios in Dubai",
    "videography services in Dubai",
    "interior design firms in Dubai",
    "architecture firms in Dubai",
    # === Dubai — Real Estate & Property ===
    "real estate agents in Dubai",
    "real estate agents in Downtown Dubai",
    "property management companies in Dubai",
    "real estate brokers in Dubai Marina",
    "real estate brokers in Business Bay Dubai",
    # === Dubai — Retail & Boutiques ===
    "boutique clothing stores in Dubai",
    "jewellery shops in Dubai",
    "jewellery shops in Deira Dubai",
    "gift shops in Dubai",
    "flower shops in Dubai",
    "pet shops in Dubai",
    "electronics shops in Dubai",
    "tailoring shops in Dubai",
    "tailoring shops in Deira Dubai",
    # === Dubai — Hospitality & Tourism ===
    "hotels in Dubai",
    "hotels in Deira Dubai",
    "hotel apartments in Dubai",
    "guesthouses in Dubai",
    "travel agencies in Dubai",
    "tourism companies in Dubai",
    "tour operators in Dubai",
    "desert safari companies in Dubai",
    "yacht rental in Dubai",
    # === Dubai — Auto & Trades ===
    "car repair shops in Dubai",
    "auto service centers in Dubai",
    "car wash services in Dubai",
    "cleaning services in Dubai",
    "pest control services in Dubai",
    "painting services in Dubai",
    "AC maintenance in Dubai",
    "AC repair services in Dubai",
    "furniture shops in Dubai",
    "home maintenance services in Dubai",
    # === Dubai — Food Delivery & Catering ===
    "catering companies in Dubai",
    "cloud kitchens in Dubai",
    "food trucks in Dubai",
    # === Abu Dhabi ===
    "restaurants in Abu Dhabi",
    "cafes in Abu Dhabi",
    "beauty salons in Abu Dhabi",
    "dental clinics in Abu Dhabi",
    "gyms in Abu Dhabi",
    "real estate agents in Abu Dhabi",
    "hotels in Abu Dhabi",
    "cleaning services in Abu Dhabi",
    "medical clinics in Abu Dhabi",
    "event management companies in Abu Dhabi",
    "interior design firms in Abu Dhabi",
    "accounting firms in Abu Dhabi",
    "legal consultants in Abu Dhabi",
    "tailoring shops in Abu Dhabi",
    "travel agencies in Abu Dhabi",
    # === Sharjah ===
    "restaurants in Sharjah",
    "cafes in Sharjah",
    "beauty salons in Sharjah",
    "dental clinics in Sharjah",
    "gyms in Sharjah",
    "real estate agents in Sharjah",
    "cleaning services in Sharjah",
    "tailoring shops in Sharjah",
    "medical clinics in Sharjah",
    "car repair shops in Sharjah",
    # === Ajman ===
    "restaurants in Ajman",
    "cafes in Ajman",
    "beauty salons in Ajman",
    "dental clinics in Ajman",
    "real estate agents in Ajman",
    "cleaning services in Ajman",
    # === Ras Al Khaimah ===
    "restaurants in Ras Al Khaimah",
    "cafes in Ras Al Khaimah",
    "hotels in Ras Al Khaimah",
    "real estate agents in Ras Al Khaimah",
    "beauty salons in Ras Al Khaimah",
    # === Fujairah ===
    "restaurants in Fujairah",
    "cafes in Fujairah",
    "hotels in Fujairah",
    "beauty salons in Fujairah",
    # === Umm Al Quwain ===
    "restaurants in Umm Al Quwain",
    "cafes in Umm Al Quwain",
]


# Weak web presence indicators — these businesses have a site but need a revamp
WEAK_WEB_INDICATORS = [
    "facebook.com", "facebook.com/", "fb.com",
    "instagram.com",
    "wix.com",
    "blogspot.com",
    "weebly.com",
    "wordpress.com",       # .com = hosted/free (not self-hosted)
    "squarespace.com",
    "sites.google.com",
    "linktr.ee",
    "linkinbio",
]



# Places API v1 returns priceLevel as a string enum, not an int
PRICE_LEVEL_MAP = {
    "PRICE_LEVEL_FREE": 0,
    "PRICE_LEVEL_INEXPENSIVE": 1,
    "PRICE_LEVEL_MODERATE": 2,
    "PRICE_LEVEL_EXPENSIVE": 3,
    "PRICE_LEVEL_VERY_EXPENSIVE": 4,
}

def classify_lead_type(website: str) -> str:
    """Classify a lead as no_website, revamp_candidate, or strong_web_presence."""
    if not website:
        return "no_website"
    w = website.lower()
    if any(indicator in w for indicator in WEAK_WEB_INDICATORS):
        return "revamp_candidate"
    return "strong_web_presence"


def compute_lead_score(place: dict) -> tuple[int, str, str]:
    """
    Score a lead from 0-100 based on signals.
    Higher = better prospect for Web Assist.
    Returns (score, notes, lead_type).

    Lead types:
      no_website        — needs a site built from scratch (highest priority)
      revamp_candidate  — has a weak/social/free-hosted presence, needs upgrade
      strong_web_presence — likely has a proper site, lower priority
    """
    score = 0
    notes = []

    website = place.get("websiteUri") or place.get("website", "")
    lead_type = classify_lead_type(website)

    if lead_type == "no_website":
        score += 40
        notes.append("No website — prime new-build prospect")
    elif lead_type == "revamp_candidate":
        score += 30
        notes.append(f"Weak web presence ({website}) — revamp opportunity")
    else:
        # Has a real website — lower base, still worth tracking
        score += 5

    # Rating signals (sweet spot: 3.5-4.7 = established, active, room to grow)
    rating = place.get("rating") or 0
    if 3.5 <= rating <= 4.7:
        score += 15
        notes.append(f"Good rating {rating} — established business")
    elif rating > 4.7:
        score += 8
        notes.append(f"Excellent rating {rating}")

    # Volume of reviews = real business activity
    reviews = place.get("userRatingCount") or place.get("userRatingsTotal") or place.get("user_ratings_total") or 0
    if reviews > 50:
        score += 15
        notes.append(f"{reviews} reviews — active business")
    elif reviews > 10:
        score += 8

    # Business is open (OPERATIONAL)
    if place.get("businessStatus") == "OPERATIONAL":
        score += 10

    # Price level 1-2 = SMB range (our sweet spot)
    _raw_price = place.get("priceLevel") or place.get("price_level") or 0
    if isinstance(_raw_price, str):
        price = PRICE_LEVEL_MAP.get(_raw_price, 0)
    else:
        price = _raw_price or 0
    if price in [1, 2]:
        score += 5
        notes.append("SMB price range")

    return min(score, 100), "; ".join(notes) if notes else None, lead_type


async def get_db_conn() -> asyncpg.Connection:
    return await asyncpg.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        database=POSTGRES_DB,
    )


async def upsert_lead(conn: asyncpg.Connection, place: dict, query: str) -> str:
    """Insert or update a lead. Returns 'new', 'updated', or 'skipped'."""

    place_id = place.get("id") or place.get("place_id")
    if not place_id:
        return "skipped"

    # Extract fields (handles both new Places API v1 and legacy format)
    name = (place.get("displayName") or {}).get("text") or place.get("name", "")
    address = place.get("formattedAddress") or place.get("formatted_address", "")
    phone = place.get("internationalPhoneNumber") or place.get("international_phone_number", "")
    website = place.get("websiteUri") or place.get("website", "")
    maps_url = place.get("googleMapsUri") or place.get("url", "")
    business_status = place.get("businessStatus") or place.get("business_status", "")
    types = place.get("types", [])
    rating = place.get("rating")
    user_ratings = place.get("userRatingCount") or place.get("userRatingsTotal") or place.get("user_ratings_total")
    _raw_price = place.get("priceLevel") or place.get("price_level")
    if isinstance(_raw_price, str):
        price_level = PRICE_LEVEL_MAP.get(_raw_price)
    else:
        price_level = _raw_price

    location = place.get("location") or (place.get("geometry") or {}).get("location", {})
    lat = location.get("latitude") or location.get("lat")
    lng = location.get("longitude") or location.get("lng")

    score, notes, lead_type = compute_lead_score(place)

    # Determine city from address
    # UAE address format: "Street, District/Area, City/Emirate, United Arab Emirates"
    # e.g. "Shop 12, Al Fahidi St, Bur Dubai, Dubai, United Arab Emirates" -> city = "Dubai"
    UAE_SKIP = {"united arab emirates", "uae", "u.a.e."}
    UAE_EMIRATES = {"dubai", "abu dhabi", "sharjah", "ajman", "ras al khaimah", "fujairah", "umm al quwain"}
    city = None
    if address:
        parts = [p.strip() for p in address.split(",")]
        # Work backwards: skip "United Arab Emirates", find the emirate name
        for part in reversed(parts):
            clean = part.strip()
            if not clean or clean.lower() in UAE_SKIP:
                continue
            # Direct emirate match
            if clean.lower() in UAE_EMIRATES:
                city = clean
                break
            # Partial match (e.g. "Dubai - JBR" or "Dubai Marina")
            for emirate in UAE_EMIRATES:
                if emirate in clean.lower():
                    city = emirate.title()
                    break
            if city:
                break
        # Fallback: second-to-last non-UAE part
        if not city and len(parts) >= 2:
            for part in reversed(parts):
                clean = part.strip()
                if clean and clean.lower() not in UAE_SKIP:
                    city = clean
                    break

    existing = await conn.fetchrow(
        "SELECT id FROM web_assist_leads WHERE place_id = $1", place_id
    )

    if existing:
        await conn.execute("""
            UPDATE web_assist_leads SET
                name = $2,
                types = $3,
                business_status = $4,
                address = $5,
                phone = $6,
                website = $7,
                google_maps_url = $8,
                city = $9,
                latitude = $10,
                longitude = $11,
                rating = $12,
                user_ratings_total = $13,
                price_level = $14,
                lead_score = $15,
                lead_notes = $16,
                lead_type = $17,
                updated_at = NOW()
            WHERE place_id = $1
        """, place_id, name, types, business_status, address, phone, website,
            maps_url, city, lat, lng, rating, user_ratings, price_level, score, notes,
            lead_type)
        return "updated"
    else:
        await conn.execute("""
            INSERT INTO web_assist_leads (
                place_id, name, types, business_status, address, phone, website,
                google_maps_url, city, country, latitude, longitude,
                rating, user_ratings_total, price_level, lead_score, lead_notes, search_query,
                lead_type
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'AE',$10,$11,$12,$13,$14,$15,$16,$17,$18)
        """, place_id, name, types, business_status, address, phone, website,
            maps_url, city, lat, lng, rating, user_ratings, price_level, score, notes, query,
            lead_type)
        return "new"


async def search_places_v1(client: httpx.AsyncClient, query: str, page_token: str = None) -> dict:
    """Google Places API v1 (new) text search."""
    body = {"textQuery": query, "maxResultCount": 20, "locationBias": {
        "rectangle": {
            "low": {"latitude": 22.6, "longitude": 51.5},
            "high": {"latitude": 26.1, "longitude": 56.4}
        }
    }}
    if page_token:
        body["pageToken"] = page_token

    resp = await client.post(
        f"{PLACES_API_BASE}/places:searchText",
        json=body,
        headers={
            "X-Goog-Api-Key": PLACES_API_KEY,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.websiteUri,places.internationalPhoneNumber,"
                "places.businessStatus,places.types,places.rating,"
                "places.userRatingCount,places.priceLevel,"
                "places.googleMapsUri,places.location"
            ),
            "nextPageToken": ""
        },
        timeout=30,
    )
    return resp.json()


async def search_places_legacy(client: httpx.AsyncClient, query: str, page_token: str = None) -> dict:
    """Google Places API legacy text search (fallback)."""
    params = {
        "query": query,
        "key": PLACES_API_KEY,
        "region": "ae",
    }
    if page_token:
        params["pagetoken"] = page_token

    resp = await client.get(
        f"{PLACES_LEGACY_BASE}/textsearch/json",
        params=params,
        timeout=30,
    )
    return resp.json()


async def run_scrape(dry_run: bool = False, specific_query: str = None, max_pages: int = 2):
    """Main scrape loop."""
    log.info("Starting lead scrape run")

    conn = await get_db_conn()

    # Start run log
    run_id = None
    if not dry_run:
        run_id = await conn.fetchval(
            "INSERT INTO lead_scrape_runs DEFAULT VALUES RETURNING id"
        )

    queries = [specific_query] if specific_query else UAE_QUERIES
    total_found = total_new = total_updated = 0

    async with httpx.AsyncClient() as client:
        for query in queries:
            log.info(f"Searching: {query}")
            page_token = None
            pages_done = 0

            while pages_done < max_pages:
                try:
                    # Try new API first, fall back to legacy
                    result = await search_places_v1(client, query, page_token)

                    if "error" in result:
                        err_code = result["error"].get("code")
                        err_reason = (result["error"].get("details") or [{}])[0].get("reason", "")

                        if err_code == 403 and "API_KEY_SERVICE_BLOCKED" in err_reason:
                            log.warning("Places API v1 blocked — trying legacy API")
                            result = await search_places_legacy(client, query, page_token)

                            if result.get("status") == "REQUEST_DENIED":
                                log.error(
                                    "Both Places API endpoints blocked. "
                                    "Enable 'Places API' in Google Cloud Console for the API key project. "
                                    "Current key: ...%s", PLACES_API_KEY[-6:]
                                )
                                if not dry_run and run_id:
                                    await conn.execute(
                                        "UPDATE lead_scrape_runs SET status='failed', "
                                        "finished_at=NOW(), error_message=$2 WHERE id=$1",
                                        run_id,
                                        "Places API not enabled for this API key. "
                                        "Enable 'Places API' in GCP Console."
                                    )
                                await conn.close()
                                return False

                            places = result.get("results", [])
                            next_page = result.get("next_page_token")
                        else:
                            log.error(f"API error: {result['error']}")
                            break
                    else:
                        places = result.get("places", [])
                        next_page = result.get("nextPageToken")

                    log.info(f"  Got {len(places)} places (page {pages_done+1})")
                    total_found += len(places)

                    if not dry_run:
                        for place in places:
                            outcome = await upsert_lead(conn, place, query)
                            if outcome == "new":
                                total_new += 1
                            elif outcome == "updated":
                                total_updated += 1
                    else:
                        for place in places[:3]:
                            name = (place.get("displayName") or {}).get("text") or place.get("name", "?")
                            website = place.get("websiteUri") or place.get("website", "none")
                            score, notes, lead_type = compute_lead_score(place)
                            log.info(f"  [DRY RUN] {name} | website={website} | score={score}")

                    pages_done += 1
                    if not next_page:
                        break

                    page_token = next_page
                    # Places API requires 2s delay between paginated requests
                    time.sleep(2)

                except httpx.TimeoutException:
                    log.error(f"Timeout on query: {query}")
                    break
                except Exception as e:
                    log.error(f"Error on query '{query}': {e}")
                    break

            # Rate limiting — be a good citizen
            time.sleep(1)

    log.info(
        f"Scrape complete: {total_found} found, {total_new} new, {total_updated} updated"
    )

    if not dry_run and run_id:
        await conn.execute("""
            UPDATE lead_scrape_runs SET
                status = 'completed',
                finished_at = NOW(),
                queries_run = $2,
                leads_found = $3,
                leads_new = $4,
                leads_updated = $5
            WHERE id = $1
        """, run_id, len(queries), total_found, total_new, total_updated)

    await conn.close()
    return True


def main():
    parser = argparse.ArgumentParser(description="Web Assist Lead Scraper")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--query", help="Run a single query instead of all")
    parser.add_argument("--max-pages", type=int, default=2, help="Max pages per query (default 2)")
    args = parser.parse_args()

    # Load env from ~/memory/.env if running directly
    env_path = os.path.expanduser("~/memory/.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

    # Re-read after loading env
    global PLACES_API_KEY, POSTGRES_PASSWORD, POSTGRES_DB
    PLACES_API_KEY = os.environ.get("PLACES_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.environ.get("POSTGRES_DB", "memory")

    if not PLACES_API_KEY:
        log.error("No API key found. Set PLACES_API_KEY or GEMINI_API_KEY.")
        sys.exit(1)

    success = asyncio.run(run_scrape(
        dry_run=args.dry_run,
        specific_query=args.query,
        max_pages=args.max_pages,
    ))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

"""Location detection and regional pricing for Athena.

Priority order:
1. WhatsApp phone number country prefix (+94=LK, +971=AE, +61=AU, +1=US)
2. Outreach data: web_assist_leads.country (via outreach_id → outreach_queue → leads)
3. Default: Global $499 USD

Usage:
    result = await detect_prospect_location(pool, jid, outreach_id)
    pricing_block = build_pricing_context(result)
"""

import logging
import re

log = logging.getLogger("otto.gateway.location_pricing")

# ──────────────────────────────────────────────────────────────
# Pricing table
# ──────────────────────────────────────────────────────────────

REGIONAL_PRICING = {
    "LK": {
        "name": "Sri Lanka",
        "flag": "🇱🇰",
        "price": "LKR 49,000",
        "currency": "LKR",
        "amount": 49000,
        "rush": "LKR 80,000",
    },
    "US": {
        "name": "USA",
        "flag": "🇺🇸",
        "price": "$3,499 USD",
        "currency": "USD",
        "amount": 3499,
        "rush": "$3,999 USD",
    },
    "AE": {
        "name": "UAE",
        "flag": "🇦🇪",
        "price": "AED 7,000",
        "currency": "AED",
        "amount": 7000,
        "rush": "AED 8,800",
    },
    "AU": {
        "name": "Australia",
        "flag": "🇦🇺",
        "price": "A$3,499 AUD",
        "currency": "AUD",
        "amount": 3499,
        "rush": "A$3,999 AUD",
    },
    "CA": {
        "name": "Canada",
        "flag": "🇨🇦",
        "price": "$499 USD",  # Canada uses Global pricing
        "currency": "USD",
        "amount": 499,
        "rush": "$999 USD",
    },
}

GLOBAL_PRICING = {
    "name": "Global",
    "flag": "🌍",
    "price": "$499 USD",
    "currency": "USD",
    "amount": 499,
    "rush": "$999 USD",
}

# ──────────────────────────────────────────────────────────────
# Phone prefix → country code
# Ordered longest-first so +971 matches before +97
# ──────────────────────────────────────────────────────────────

PHONE_PREFIX_MAP = [
    ("971", "AE"),  # UAE
    ("94",  "LK"),  # Sri Lanka
    ("61",  "AU"),  # Australia
    ("1",   "US"),  # USA (Canada +1 also hits here; corrected by outreach data if available)
]


def extract_phone_digits(jid_or_phone: str) -> str:
    """Strip WhatsApp JID suffix and leading + to get raw digit string."""
    # e.g. "94743768830@s.whatsapp.net" → "94743768830"
    raw = jid_or_phone.split("@")[0]
    return re.sub(r"[^0-9]", "", raw)


def detect_country_from_phone(jid_or_phone: str) -> tuple[str | None, str]:
    """
    Parse WhatsApp JID or phone number to detect ISO country code.
    Returns (country_code, matched_prefix) or (None, "").
    """
    digits = extract_phone_digits(jid_or_phone)
    if not digits:
        return None, ""

    for prefix, country in PHONE_PREFIX_MAP:
        if digits.startswith(prefix) and len(digits) > len(prefix) + 3:
            return country, prefix

    return None, ""


async def detect_country_from_outreach(pool, outreach_id: str) -> str | None:
    """
    Look up the ISO country code for this prospect via:
    outreach_id → outreach_queue.lead_id → web_assist_leads.country

    Returns ISO 2-letter code (e.g. "AU", "LK") or None.
    """
    if not outreach_id:
        return None
    try:
        row = await pool.fetchrow(
            """SELECT l.country
               FROM outreach_queue oq
               JOIN web_assist_leads l ON l.id = oq.lead_id
               WHERE oq.id = $1
               LIMIT 1""",
            outreach_id,
        )
        if row and row["country"]:
            return row["country"].upper()
    except Exception as e:
        log.debug(f"Outreach country lookup failed: {e}")
    return None


async def detect_prospect_location(
    pool,
    jid: str,
    outreach_id=None,
    cached_country: str | None = None,
) -> dict:
    """
    Full location detection pipeline.
    Returns a dict with: country, source, pricing (from REGIONAL_PRICING or GLOBAL_PRICING).

    cached_country: if already stored on the prospect row, skip re-detection.
    """
    # 1. Use cached value if available
    if cached_country:
        pricing = REGIONAL_PRICING.get(cached_country, GLOBAL_PRICING)
        return {
            "country": cached_country,
            "source": "cached",
            "pricing": pricing,
        }

    # 2. Phone prefix detection (primary)
    country, prefix = detect_country_from_phone(jid)
    if country:
        pricing = REGIONAL_PRICING.get(country, GLOBAL_PRICING)
        log.info(f"Location detected from phone prefix +{prefix}: {country}")
        return {
            "country": country,
            "source": "phone",
            "pricing": pricing,
        }

    # 3. Outreach / lead data fallback
    if outreach_id:
        outreach_country = await detect_country_from_outreach(pool, str(outreach_id))
        if outreach_country:
            pricing = REGIONAL_PRICING.get(outreach_country, GLOBAL_PRICING)
            log.info(f"Location detected from outreach data: {outreach_country}")
            return {
                "country": outreach_country,
                "source": "outreach",
                "pricing": pricing,
            }

    # 4. Default: Global
    log.info(f"Location unknown for {jid} — defaulting to Global pricing")
    return {
        "country": None,
        "source": "default",
        "pricing": GLOBAL_PRICING,
    }


async def save_detected_country(pool, prospect_id: str, country: str | None, source: str):
    """Cache the detected country on the prospect row to avoid re-detection."""
    try:
        await pool.execute(
            """UPDATE athena_prospects
               SET detected_country = $1, pricing_source = $2, updated_at = NOW()
               WHERE id = $3""",
            country,
            source,
            prospect_id,
        )
    except Exception as e:
        log.debug(f"Failed to cache detected country: {e}")


def build_pricing_context(location_result: dict) -> str:
    """
    Build a short pricing context block to inject into Athena's system prompt.
    This tells Athena exactly what price to quote and why.
    """
    pricing = location_result["pricing"]
    country = location_result.get("country")
    source = location_result.get("source", "default")

    flag = pricing.get("flag", "🌍")
    name = pricing.get("name", "Global")
    price = pricing.get("price", "$499 USD")
    rush = pricing.get("rush", "$999 USD")

    if source == "phone":
        detection_note = f"Detected from WhatsApp country code."
    elif source == "outreach":
        detection_note = f"Detected from outreach/lead data."
    elif source == "cached":
        detection_note = f"Previously detected and cached."
    else:
        detection_note = f"Location unknown — using Global default."

    return (
        f"\n\n## This Prospect's Pricing\n"
        f"Location: {flag} {name} ({detection_note})\n"
        f"Standard price: **{price}**\n"
        f"Rush delivery (24h): {rush}\n"
        f"Always quote in local currency ({pricing.get('currency', 'USD')}). "
        f"Do NOT convert to USD unless the prospect asks. "
        f"If they claim a different location, use that region's price instead.\n"
    )

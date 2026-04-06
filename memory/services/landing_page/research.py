"""Landing Page Research Service

Two core research functions for the landing page generation workflow:

  research_business(business_name, business_url, description, ...)
      → Profiles the business: value prop, tagline, products, tone, social proof.

  research_competitors(business_name, target_audience, description, ...)
      → Finds top 3-5 competitors, extracts positioning gaps and angles.

Both return structured JSON dicts and optionally persist to the landing_pages table
via research_data / competitor_data JSONB columns.

Web research strategy:
  1. DuckDuckGo text search (no API key required, free)
  2. requests + BeautifulSoup for page scraping (structured extraction)
  3. Graceful degradation — if scraping fails, return best-effort partial data
"""

import asyncio
import json
import logging
import re
import time
from typing import Optional
from urllib.parse import urlparse, urljoin

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("otto.landing_page.research")

# ── Constants ──────────────────────────────────────────────────────────────────

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_SCRAPE_TIMEOUT = 12  # seconds per URL
_SEARCH_TIMEOUT = 10  # seconds for DDG search
_MAX_TEXT_LEN = 3000  # max scraped text chars per page


# ── Helpers ────────────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]


def _clean_text(text: str, max_len: int = _MAX_TEXT_LEN) -> str:
    """Strip excess whitespace, truncate."""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned[:max_len]


def _extract_meta(soup: BeautifulSoup) -> dict:
    """Extract common meta tags from a page."""
    result: dict = {}

    # Title
    if soup.title:
        result["title"] = soup.title.string.strip() if soup.title.string else ""

    # Description
    for attr in ("description", "og:description", "twitter:description"):
        tag = soup.find("meta", attrs={"name": attr}) or soup.find(
            "meta", attrs={"property": attr}
        )
        if tag and tag.get("content"):
            result["meta_description"] = tag["content"].strip()
            break

    # OG title / site name
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        result["og_title"] = og_title["content"].strip()

    og_site = soup.find("meta", attrs={"property": "og:site_name"})
    if og_site and og_site.get("content"):
        result["og_site_name"] = og_site["content"].strip()

    # Twitter handle
    tw_site = soup.find("meta", attrs={"name": "twitter:site"})
    if tw_site and tw_site.get("content"):
        result["twitter_handle"] = tw_site["content"].strip()

    return result


def _extract_brand_colors(soup: BeautifulSoup) -> list[str]:
    """Extract hex color codes mentioned in inline styles or CSS variables."""
    hex_pattern = re.compile(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
    colors: set[str] = set()

    for tag in soup.find_all(style=True):
        found = hex_pattern.findall(tag.get("style", ""))
        for c in found:
            colors.add(f"#{c.upper()}")

    for style_tag in soup.find_all("style"):
        if style_tag.string:
            found = hex_pattern.findall(style_tag.string)
            for c in found:
                colors.add(f"#{c.upper()}")

    # Filter out near-black/near-white as those are likely text/bg defaults
    filtered = [
        c for c in colors
        if c not in {"#FFFFFF", "#000000", "#FFF", "#000", "#FFFFFE"}
    ]
    return filtered[:8]


def _extract_hero_copy(soup: BeautifulSoup) -> dict:
    """Try to extract hero/above-fold copy: h1, h2, and lead paragraph."""
    result: dict = {}

    h1 = soup.find("h1")
    if h1:
        result["h1"] = _clean_text(h1.get_text(), 200)

    h2 = soup.find("h2")
    if h2:
        result["h2"] = _clean_text(h2.get_text(), 200)

    # First paragraph of substantial length
    for p in soup.find_all("p"):
        text = _clean_text(p.get_text(), 500)
        if len(text) > 60:
            result["lead_paragraph"] = text
            break

    return result


async def _fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return a BeautifulSoup object, or None on failure."""
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=_SCRAPE_TIMEOUT,
            follow_redirects=True,
            verify=False,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
    except Exception as exc:
        log.debug("Failed to fetch %s: %s", url, exc)
        return None


async def _ddg_search(query: str, max_results: int = 5) -> list[dict]:
    """Run a DuckDuckGo text search, return list of {title, href, body} dicts."""
    try:
        from duckduckgo_search import DDGS

        def _sync_search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))

        results = await asyncio.get_event_loop().run_in_executor(None, _sync_search)
        return results or []
    except Exception as exc:
        log.warning("DDG search failed for %r: %s", query, exc)
        return []


def _detect_tone_from_copy(text: str) -> str:
    """Heuristic: infer tone of voice from web copy."""
    text_lower = text.lower()

    formal_signals = ["leverage", "solutions", "enterprise", "optimize", "scalable",
                      "roi", "strategic", "mission-critical", "stakeholder"]
    casual_signals = ["hey", "awesome", "love", "excited", "easy", "simple",
                      "just", "amazing", "super", "cool"]
    playful_signals = ["!", "fun", "game", "play", "delight", "wink", "oops", "woops"]
    technical_signals = ["api", "sdk", "integration", "deploy", "config", "open source",
                         "documentation", "github", "cli", "terminal"]

    scores = {
        "formal": sum(1 for w in formal_signals if w in text_lower),
        "casual": sum(1 for w in casual_signals if w in text_lower),
        "playful": sum(1 for w in playful_signals if w in text_lower),
        "technical": sum(1 for w in technical_signals if w in text_lower),
    }
    dominant = max(scores, key=scores.get)  # type: ignore[arg-type]
    return dominant if scores[dominant] > 0 else "professional"


def _detect_pricing_tier(text: str) -> str:
    """Heuristic pricing tier from page copy."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["luxury", "premium", "exclusive", "bespoke", "boutique"]):
        return "premium"
    if any(w in text_lower for w in ["affordable", "cheap", "low cost", "budget", "free"]):
        return "budget"
    if any(w in text_lower for w in ["enterprise", "custom pricing", "contact sales"]):
        return "enterprise"
    return "mid"


# ── Public Research Functions ──────────────────────────────────────────────────


async def research_business(
    business_name: str,
    business_url: Optional[str] = None,
    description: Optional[str] = None,
    target_audience: Optional[str] = None,
    *,
    landing_page_id: Optional[str] = None,
    db_pool=None,
) -> dict:
    """
    Research a business for landing page creation.

    Gathers: industry, tagline, value proposition, products/services,
    tone of voice, pricing tier, brand colors, social presence, reviews.

    Args:
        business_name: Name of the business
        business_url:  Homepage URL (optional but recommended)
        description:   User-provided description to seed search
        target_audience: Who the business serves
        landing_page_id: If provided, update landing_pages.research_data in DB
        db_pool: asyncpg connection pool (required if landing_page_id provided)

    Returns:
        Structured dict with business profile.
    """
    log.info("Researching business: %s (url=%s)", business_name, business_url)
    result: dict = {
        "business_name": business_name,
        "business_url": business_url or "",
        "description_provided": description or "",
        "industry": "",
        "tagline": "",
        "value_proposition": "",
        "products_services": [],
        "pricing_tier": "mid",
        "brand_colors": [],
        "tone_of_voice": "professional",
        "target_audience": target_audience or "",
        "differentiator": "",
        "social_presence": {},
        "notable_reviews_or_press": [],
        "existing_site_assessment": "none",
        "raw_notes": "",
        "_sources": [],
    }

    raw_notes: list[str] = []

    # ── Step 1: Scrape the business website (if URL provided) ──────────────────
    if business_url:
        soup = await _fetch_page(business_url)
        if soup:
            result["existing_site_assessment"] = "basic"
            meta = _extract_meta(soup)
            hero = _extract_hero_copy(soup)
            colors = _extract_brand_colors(soup)

            # Tagline: og_title or h1 tends to be shortest
            result["tagline"] = (
                hero.get("h1") or meta.get("og_title") or meta.get("title") or ""
            )
            result["value_proposition"] = (
                meta.get("meta_description") or hero.get("lead_paragraph") or ""
            )
            result["brand_colors"] = colors
            result["_sources"].append(business_url)

            # Full page text for analysis
            page_text = _clean_text(soup.get_text(), _MAX_TEXT_LEN)
            result["tone_of_voice"] = _detect_tone_from_copy(page_text)
            result["pricing_tier"] = _detect_pricing_tier(page_text)

            # Site quality assessment
            nav = soup.find("nav")
            footer = soup.find("footer")
            scripts = soup.find_all("script", src=True)
            if len(scripts) > 3 and nav and footer:
                result["existing_site_assessment"] = "professional"
            elif nav or footer:
                result["existing_site_assessment"] = "decent"

            # Extract services/products from nav links or section headings
            services: list[str] = []
            for link in soup.find_all("a", href=True):
                href = link["href"].lower()
                text = link.get_text().strip()
                if any(k in href for k in ["/service", "/product", "/solution", "/offering"]):
                    if text and len(text) < 60:
                        services.append(text)
            for heading in soup.find_all(["h2", "h3"]):
                h_text = heading.get_text().strip()
                if 5 < len(h_text) < 80:
                    services.append(h_text)
            result["products_services"] = list(dict.fromkeys(services))[:8]

            # Social links
            social_patterns = {
                "twitter": r"twitter\.com/([^/?\"']+)",
                "linkedin": r"linkedin\.com/(?:company|in)/([^/?\"']+)",
                "instagram": r"instagram\.com/([^/?\"']+)",
                "facebook": r"facebook\.com/([^/?\"']+)",
                "youtube": r"youtube\.com/(?:channel|c|@)([^/?\"']+)",
            }
            html_str = str(soup)
            for platform, pattern in social_patterns.items():
                m = re.search(pattern, html_str, re.IGNORECASE)
                if m:
                    handle = m.group(1).rstrip("/")
                    result["social_presence"][platform] = handle

            raw_notes.append(f"Scraped {business_url}: title={meta.get('title','?')}")
        else:
            raw_notes.append(f"Could not fetch {business_url}")

    # ── Step 2: DDG search for business info ───────────────────────────────────
    search_queries = [
        f"{business_name} company overview what do they do",
        f"{business_name} reviews customers testimonials",
    ]
    if description:
        search_queries.insert(0, f'"{business_name}" {description[:60]}')

    for query in search_queries[:2]:
        results = await _ddg_search(query, max_results=4)
        for r in results:
            body = r.get("body", "")
            href = r.get("href", "")
            title = r.get("title", "")

            if not result["industry"] and body:
                # Simple industry detection
                industry_keywords = {
                    "restaurant": ["restaurant", "food", "dining", "cafe", "bistro"],
                    "e-commerce": ["shop", "store", "buy", "cart", "product"],
                    "saas": ["software", "platform", "app", "subscription", "saas"],
                    "consulting": ["consulting", "advisory", "strategy", "services"],
                    "agency": ["agency", "design", "marketing", "creative"],
                    "real estate": ["property", "real estate", "rent", "lease"],
                    "healthcare": ["health", "medical", "clinic", "wellness"],
                    "education": ["education", "course", "learn", "training"],
                    "finance": ["finance", "investment", "banking", "insurance"],
                }
                for ind, kws in industry_keywords.items():
                    if any(kw in body.lower() for kw in kws):
                        result["industry"] = ind
                        break

            if not result["value_proposition"] and body and len(body) > 50:
                result["value_proposition"] = body[:300]

            # Press mentions
            if any(k in href for k in ["techcrunch", "forbes", "bbc", "reuters",
                                        "guardian", "bloomberg", "wsj"]):
                result["notable_reviews_or_press"].append(f"{title} — {href}")

            result["_sources"].append(href)

        await asyncio.sleep(0.5)  # gentle rate limiting

    # ── Step 3: Review/rating search ──────────────────────────────────────────
    review_results = await _ddg_search(
        f"{business_name} customer reviews rating trustpilot g2 yelp", max_results=3
    )
    for r in review_results:
        href = r.get("href", "")
        title = r.get("title", "")
        if any(site in href for site in ["trustpilot", "g2.com", "yelp", "glassdoor",
                                          "capterra", "tripadvisor"]):
            snippet = r.get("body", "")[:120]
            result["notable_reviews_or_press"].append(f"{title}: {snippet} [{href}]")

    # ── Finalize ───────────────────────────────────────────────────────────────
    # Ensure user-provided fields survive even when scraping returns nothing
    if description and not result.get("value_proposition"):
        result["value_proposition"] = description
    if target_audience and not result.get("target_audience"):
        result["target_audience"] = target_audience

    if not result["industry"] and description:
        result["industry"] = "business"
    if not result["differentiator"] and result["value_proposition"]:
        # Best-effort: extract differentiator from value prop
        vp = result["value_proposition"]
        if "unlike" in vp.lower():
            idx = vp.lower().index("unlike")
            result["differentiator"] = vp[idx:idx+150]
        elif "first" in vp.lower():
            result["differentiator"] = "Positioning claims to be first/only in category"

    result["raw_notes"] = "\n".join(raw_notes)

    # ── Persist to DB if requested ─────────────────────────────────────────────
    if landing_page_id and db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE landing_pages
                    SET research_data = $1::jsonb,
                        status = CASE WHEN status = 'researching' THEN 'researching' ELSE status END,
                        updated_at = now()
                    WHERE id = $2
                    """,
                    json.dumps(result),
                    landing_page_id,
                )
            log.info("Saved research_data for landing_page %s", landing_page_id)
        except Exception as exc:
            log.error("Failed to persist research_data: %s", exc)

    return result


async def research_competitors(
    business_name: str,
    target_audience: Optional[str] = None,
    description: Optional[str] = None,
    industry: Optional[str] = None,
    *,
    landing_page_id: Optional[str] = None,
    db_pool=None,
) -> dict:
    """
    Research competitors for a business to inform landing page positioning.

    Finds top 3-5 competitors, extracts: visual style, messaging strategy,
    CTA approach, strengths, weaknesses, positioning gaps to exploit.

    Args:
        business_name:   Name of the business we're building for
        target_audience: Who the business serves
        description:     User-provided business description
        industry:        Optional industry hint (if already from research_business)
        landing_page_id: If provided, update landing_pages.competitor_data in DB
        db_pool: asyncpg connection pool (required if landing_page_id provided)

    Returns:
        Structured dict with competitor profiles and positioning gaps.
    """
    log.info("Researching competitors for: %s", business_name)

    result: dict = {
        "business_name": business_name,
        "competitors": [],
        "market_trends": [],
        "positioning_gaps": [],
        "recommended_angles": [],
        "visual_direction_notes": "",
        "messaging_direction_notes": "",
        "_sources": [],
    }

    # ── Step 1: Find competitors via DDG search ────────────────────────────────
    context = description or ""
    industry_hint = industry or ""
    audience_hint = target_audience or ""

    search_queries = [
        f"{business_name} alternatives competitors similar {industry_hint}".strip(),
        f"best {industry_hint} {audience_hint} companies like {business_name}".strip(),
        f"top {industry_hint} services competitors {business_name}".strip(),
    ]

    competitor_urls: list[dict] = []  # [{name, url, snippet}]

    for query in search_queries[:2]:
        ddg_results = await _ddg_search(query, max_results=5)
        for r in ddg_results:
            href = r.get("href", "")
            title = r.get("title", "")
            body = r.get("body", "")

            # Skip the business itself, review sites, social media
            skip_domains = [
                "reddit", "quora", "youtube", "twitter", "facebook",
                "linkedin", "yelp", "trustpilot", "glassdoor", "wikipedia",
                _slugify(business_name),
            ]
            parsed = urlparse(href)
            domain = parsed.netloc.replace("www.", "")

            if any(skip in domain.lower() for skip in skip_domains):
                continue
            if not href.startswith("http"):
                continue

            # Avoid duplicates
            existing_domains = [urlparse(c["url"]).netloc for c in competitor_urls]
            if domain not in existing_domains:
                competitor_urls.append({
                    "name": title.split(" - ")[0].split(" | ")[0].strip()[:80],
                    "url": href,
                    "snippet": body[:200],
                })
                result["_sources"].append(href)

            if len(competitor_urls) >= 6:
                break

        await asyncio.sleep(0.5)

    # ── Step 2: Scrape each competitor's homepage ──────────────────────────────
    competitor_profiles: list[dict] = []

    async def _profile_competitor(comp: dict) -> Optional[dict]:
        url = comp["url"]
        # Only use root domain to get homepage
        parsed = urlparse(url)
        homepage = f"{parsed.scheme}://{parsed.netloc}"

        soup = await _fetch_page(homepage)
        profile: dict = {
            "name": comp["name"],
            "url": homepage,
            "visual_style": "unknown",
            "messaging_strategy": "",
            "cta_approach": "",
            "headline": "",
            "value_prop": comp["snippet"],
            "strengths": [],
            "weaknesses": [],
            "brand_colors": [],
        }

        if not soup:
            # Use snippet from DDG as fallback
            profile["messaging_strategy"] = comp["snippet"]
            return profile

        meta = _extract_meta(soup)
        hero = _extract_hero_copy(soup)
        colors = _extract_brand_colors(soup)
        page_text = _clean_text(soup.get_text(), _MAX_TEXT_LEN)

        profile["headline"] = (
            hero.get("h1") or meta.get("og_title") or meta.get("title") or comp["name"]
        )
        profile["value_prop"] = (
            meta.get("meta_description") or hero.get("lead_paragraph") or comp["snippet"]
        )
        profile["brand_colors"] = colors

        # Detect visual style heuristics
        html_str = str(soup)
        if any(x in html_str.lower() for x in ["tailwind", "material", "bootstrap"]):
            profile["visual_style"] = "framework-based"
        elif len(colors) > 5:
            profile["visual_style"] = "colorful/branded"
        elif all(c in ["#FFFFFF", "#000000", "#F5F5F5"] for c in colors[:3]):
            profile["visual_style"] = "minimal/monochrome"
        else:
            profile["visual_style"] = "standard"

        # CTA detection
        cta_buttons: list[str] = []
        for btn in soup.find_all(["button", "a"], class_=re.compile(r"btn|cta|button", re.I)):
            text = btn.get_text().strip()
            if 2 < len(text) < 50:
                cta_buttons.append(text)
        if cta_buttons:
            profile["cta_approach"] = ", ".join(dict.fromkeys(cta_buttons)[:4])

        # Messaging strategy from tone
        tone = _detect_tone_from_copy(page_text)
        profile["messaging_strategy"] = f"{tone} tone — {profile['value_prop'][:150]}"

        # Strengths & weaknesses (heuristic)
        if len(page_text) > 1500:
            profile["strengths"].append("Comprehensive content / detailed messaging")
        if not cta_buttons:
            profile["weaknesses"].append("Unclear CTA — no prominent call-to-action found")
        if not colors:
            profile["weaknesses"].append("Weak visual identity — no distinctive brand colors")
        if meta.get("meta_description"):
            profile["strengths"].append("Strong SEO meta description present")
        else:
            profile["weaknesses"].append("Missing meta description (SEO gap)")

        return profile

    # Run all competitor scrapes concurrently (max 5)
    tasks = [_profile_competitor(c) for c in competitor_urls[:5]]
    profiles = await asyncio.gather(*tasks, return_exceptions=True)

    for p in profiles:
        if isinstance(p, dict):
            competitor_profiles.append(p)

    result["competitors"] = competitor_profiles

    # ── Step 3: Market trends search ──────────────────────────────────────────
    trends_query = f"{industry_hint or business_name} industry website design trends 2025 2026"
    trend_results = await _ddg_search(trends_query, max_results=3)
    trends: list[str] = []
    for r in trend_results:
        body = r.get("body", "")
        if body and len(body) > 40:
            trends.append(body[:150])
    result["market_trends"] = trends[:3]

    # ── Step 4: Synthesize positioning gaps ────────────────────────────────────
    gaps: list[str] = []
    recommended: list[str] = []

    all_ctas = [c.get("cta_approach", "") for c in competitor_profiles if c.get("cta_approach")]
    all_tones = [
        c.get("messaging_strategy", "").split(" tone")[0]
        for c in competitor_profiles
        if c.get("messaging_strategy")
    ]
    all_colors = [c for comp in competitor_profiles for c in comp.get("brand_colors", [])]

    # Identify overused CTA language
    cta_text = " ".join(all_ctas).lower()
    if cta_text.count("get started") > 1:
        gaps.append("'Get Started' CTA is overused — differentiate with specific, outcome-oriented CTA")
    if cta_text.count("learn more") > 1:
        gaps.append("'Learn More' CTAs dominant — replace with value-forward CTAs")

    # Tone gap
    tone_counter: dict = {}
    for t in all_tones:
        tone_counter[t] = tone_counter.get(t, 0) + 1
    dominant_tone = max(tone_counter, key=tone_counter.get) if tone_counter else None
    if dominant_tone == "formal":
        gaps.append("Market is formal/corporate — casual/human tone is a differentiator")
        recommended.append("Use conversational, first-person language to stand out from formal competitors")
    elif dominant_tone == "casual":
        gaps.append("Market is casual — authority/expertise tone can differentiate premium positioning")
        recommended.append("Lead with expertise signals (credentials, results, case studies)")

    # Color gap
    if len(set(all_colors)) < 5:
        gaps.append("Competitors have weak or similar visual identities — strong brand color system differentiates")
        recommended.append("Invest in distinctive brand colors and visual identity system")

    # Generic recommendations
    recommended.extend([
        "Lead with concrete outcomes/results rather than feature lists",
        "Use social proof (testimonials, case studies) above the fold",
        "Add trust signals (logos, certifications, stats) in the first viewport",
    ])

    # Visual direction summary
    styles = [c.get("visual_style") for c in competitor_profiles if c.get("visual_style")]
    if styles:
        from collections import Counter
        style_counts = Counter(styles)
        most_common = style_counts.most_common(1)[0][0]
        result["visual_direction_notes"] = (
            f"Most competitors use {most_common} visual style. "
            "Consider contrasting approach for differentiation."
        )

    # Messaging direction summary
    if competitor_profiles:
        first = competitor_profiles[0]
        result["messaging_direction_notes"] = (
            f"Top competitor ({first.get('name','?')}) focuses on: "
            f"{first.get('value_prop','')[:120]}. "
            "Identify what they don't say and lead with that."
        )

    result["positioning_gaps"] = gaps
    result["recommended_angles"] = recommended

    # ── Persist to DB if requested ─────────────────────────────────────────────
    if landing_page_id and db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE landing_pages
                    SET competitor_data = $1::jsonb,
                        updated_at = now()
                    WHERE id = $2
                    """,
                    json.dumps(result),
                    landing_page_id,
                )
            log.info("Saved competitor_data for landing_page %s", landing_page_id)
        except Exception as exc:
            log.error("Failed to persist competitor_data: %s", exc)

    return result

"""Design synthesis engine for landing page generation.

Provides:
    design_synthesizer(research_data, competitor_data) → design_decisions dict
    copy_generator(business_data, design_decisions) → section_copy dict

Uses prompts.md catalog + LLM to make informed design and copy decisions.
"""

import json
import logging
import sys
from typing import Any

# Ensure otto root is importable
sys.path.insert(0, "/home/web3relic/otto")

from memory.llm import llm_chat, extract_json
from services.landing_page.design_catalog import (
    get_catalog,
    get_catalog_summaries,
    get_design_by_id,
    BANNED_FONTS,
)

log = logging.getLogger("otto.design")


# ---------- Design Decisions Schema ----------

DESIGN_DECISIONS_SCHEMA = {
    "selected_design_id": "DESIGN_XX (from catalog)",
    "design_name": "short descriptive name",
    "fonts": {
        "heading": {"family": "Font Name", "weight": 700, "style": "normal"},
        "body": {"family": "Font Name", "weight": 400, "style": "normal"},
        "accent": {"family": "Font Name (optional mono/display)", "weight": 500, "style": "normal"},
    },
    "colors": {
        "primary": "#hex (brand/accent)",
        "secondary": "#hex",
        "accent": "#hex (CTA/highlight)",
        "background": "#hex (page bg)",
        "text": "#hex (main text)",
        "muted": "#hex (secondary text)",
    },
    "ui_style": "one of: minimal|brutalist|editorial|glassmorphic|luxury|technical|bold|soft-organic|futuristic|cinematic",
    "color_mode": "light|dark",
    "sections": [
        {"type": "hero|features|social_proof|cta|pricing|faq|testimonials|about|how_it_works|problem_solution|portfolio|footer",
         "name": "Section display name",
         "layout": "centered|split|grid|bento|staggered|asymmetric",
         "notes": "specific implementation notes"},
    ],
    "imagery_style": "description of image treatment",
    "copy_tone": "description of writing voice",
    "animations": {
        "style": "smooth|snappy|weighted|minimal",
        "easing": "cubic-bezier values or keyword",
        "duration": "default duration",
        "scroll_reveal": True,
    },
    "special_components": ["list of signature components to build"],
    "rationale": "2-3 sentences explaining why this design fits the business",
}

SECTION_COPY_SCHEMA = {
    "headline": "primary hero headline",
    "subheadline": "supporting hero text",
    "cta_primary": {"text": "CTA button text", "action": "url or action"},
    "cta_secondary": {"text": "secondary CTA text", "action": "url or action"},
    "sections": [
        {
            "type": "section type",
            "heading": "section heading",
            "subheading": "section subheading",
            "body": "section body text or null",
            "items": [
                {"title": "item title", "description": "item description", "icon_hint": "suggested icon"}
            ],
        }
    ],
    "social_proof": {
        "headline": "social proof heading",
        "testimonials": [
            {"quote": "testimonial text", "author": "name", "role": "title/company"}
        ],
        "stats": [
            {"value": "100+", "label": "metric label"}
        ],
    },
    "footer": {
        "tagline": "footer tagline",
        "cta": "footer CTA text",
    },
    "meta": {
        "page_title": "SEO title (50-60 chars)",
        "meta_description": "SEO description (150-160 chars)",
        "og_title": "social share title",
        "og_description": "social share description",
    },
}


# ---------- Core Functions ----------


async def design_synthesizer(
    research_data: dict[str, Any],
    competitor_data: dict[str, Any],
) -> dict[str, Any]:
    """Synthesize design decisions from research + competitor data using prompts.md catalog.

    Args:
        research_data: Business research from Step 0 (name, industry, brand colors, etc.)
        competitor_data: Market/competitor analysis from Step 1

    Returns:
        Structured design_decisions dict matching DESIGN_DECISIONS_SCHEMA.
    """
    catalog_summary = get_catalog_summaries()
    catalog = get_catalog()

    # Build the industry/business context
    business_name = research_data.get("business_name", "Unknown Business")
    industry = research_data.get("industry", "general")
    pricing_tier = research_data.get("pricing_tier", "mid")
    tone = research_data.get("tone_of_voice", "professional")
    existing_colors = research_data.get("brand_colors", [])
    target_audience = research_data.get("target_audience", "general audience")
    differentiator = research_data.get("differentiator", "")

    # Competitor visual directions
    competitor_styles = []
    for comp in competitor_data.get("competitors", []):
        if isinstance(comp, dict):
            competitor_styles.append(
                f"- {comp.get('name', '?')}: {comp.get('visual_style', 'unknown')}"
            )
    competitor_visual = "\n".join(competitor_styles) if competitor_styles else "No competitor data available"

    positioning_gaps = competitor_data.get("positioning_gaps", [])
    recommended_angles = competitor_data.get("recommended_angles", [])

    system_prompt = f"""You are an expert web designer selecting a design system for a landing page.

You have a catalog of {len(catalog)} proven design systems. Your job is to select the BEST one
for this business and customize it. Consider:

1. INDUSTRY FIT — A law firm needs authority (technical/editorial), a wellness brand needs warmth (soft-organic)
2. AUDIENCE MATCH — Gen Z prefers bold/futuristic, professionals prefer minimal/editorial
3. COMPETITOR DIFFERENTIATION — If competitors all use dark themes, consider light. Stand out.
4. BRAND ALIGNMENT — Respect existing brand colors if strong, otherwise propose fresh palette
5. PRICING TIER — Premium businesses need luxury aesthetics, budget businesses need clean/clear

BANNED FONTS (never select these): {', '.join(BANNED_FONTS)}

DESIGN CATALOG:
{catalog_summary}
"""

    user_prompt = f"""Select and customize a design system for this landing page:

BUSINESS: {business_name}
INDUSTRY: {industry}
PRICING TIER: {pricing_tier}
TONE: {tone}
EXISTING BRAND COLORS: {json.dumps(existing_colors)}
TARGET AUDIENCE: {target_audience}
DIFFERENTIATOR: {differentiator}

COMPETITOR VISUAL STYLES:
{competitor_visual}

POSITIONING GAPS: {json.dumps(positioning_gaps)}
RECOMMENDED ANGLES: {json.dumps(recommended_angles)}
VISUAL DIRECTION NOTES: {competitor_data.get('visual_direction_notes', 'none')}
MESSAGING DIRECTION NOTES: {competitor_data.get('messaging_direction_notes', 'none')}

Return a JSON object with these exact keys:
{{
    "selected_design_id": "DESIGN_XX",
    "design_name": "short name for this customized design",
    "fonts": {{
        "heading": {{"family": "Font Name", "weight": 700, "style": "normal"}},
        "body": {{"family": "Font Name", "weight": 400, "style": "normal"}},
        "accent": {{"family": "Font Name", "weight": 500, "style": "normal"}}
    }},
    "colors": {{
        "primary": "#hex",
        "secondary": "#hex",
        "accent": "#hex",
        "background": "#hex",
        "text": "#hex",
        "muted": "#hex"
    }},
    "ui_style": "category",
    "color_mode": "light|dark",
    "sections": [
        {{"type": "hero", "name": "Hero", "layout": "layout_type", "notes": "specifics"}},
        ... (6-10 sections in recommended order)
    ],
    "imagery_style": "description",
    "copy_tone": "description of writing voice",
    "animations": {{
        "style": "smooth|snappy|weighted|minimal",
        "easing": "cubic-bezier(x,y,z,w)",
        "duration": "Xms",
        "scroll_reveal": true
    }},
    "special_components": ["list of 2-4 signature components"],
    "rationale": "2-3 sentences explaining why this design fits"
}}

IMPORTANT:
- Do NOT use banned fonts
- If existing brand colors are strong, incorporate them into the palette
- Select 6-10 sections appropriate for this business type
- Ensure the design DIFFERENTIATES from competitors
- Return ONLY valid JSON, no markdown fences"""

    response = await llm_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system_instruction=system_prompt,
        max_tokens=2000,
        temperature=0.3,
    )

    decisions = extract_json(response)

    if not decisions:
        log.error("LLM failed to return valid design decisions JSON")
        return _fallback_design(research_data)

    # Post-process: validate and enrich
    decisions = _validate_decisions(decisions, research_data)

    # Enrich with raw spec from selected design
    selected_id = decisions.get("selected_design_id", "")
    selected_design = get_design_by_id(selected_id)
    if selected_design:
        decisions["_source_spec"] = selected_design.get("raw_spec", "")
        decisions["_source_sections"] = selected_design.get("sections", [])
        decisions["_source_components"] = selected_design.get("special_components", [])
        decisions["_source_notes"] = selected_design.get("special_notes", "")

    log.info(
        f"Design synthesized for {business_name}: {decisions.get('design_name', '?')} "
        f"(base: {selected_id}, style: {decisions.get('ui_style', '?')})"
    )

    return decisions


async def copy_generator(
    business_data: dict[str, Any],
    design_decisions: dict[str, Any],
) -> dict[str, Any]:
    """Generate all section copy for the landing page.

    Args:
        business_data: Combined research data (from Step 0)
        design_decisions: Output from design_synthesizer

    Returns:
        Structured copy dict with headline, sections, CTAs, meta tags, etc.
    """
    business_name = business_data.get("business_name", "Unknown Business")
    industry = business_data.get("industry", "general")
    value_prop = business_data.get("value_proposition", "")
    products = business_data.get("products_services", [])
    differentiator = business_data.get("differentiator", "")
    target_audience = business_data.get("target_audience", "general audience")
    tagline = business_data.get("tagline", "")
    reviews = business_data.get("notable_reviews_or_press", [])

    copy_tone = design_decisions.get("copy_tone", "professional")
    sections = design_decisions.get("sections", [])
    ui_style = design_decisions.get("ui_style", "modern")

    # Build section list for the LLM
    section_list = []
    for s in sections:
        if isinstance(s, dict):
            section_list.append(f"- {s.get('type', 'unknown')}: {s.get('name', '')} ({s.get('layout', '')})")
        else:
            section_list.append(f"- {s}")
    sections_str = "\n".join(section_list) if section_list else "hero, features, social_proof, cta"

    system_prompt = f"""You are an expert landing page copywriter. Write compelling, conversion-optimized copy
for a landing page. Your writing voice must match: {copy_tone}

Guidelines:
- Headlines should be punchy, specific, and benefit-driven (not generic)
- Subheadlines should expand on the headline with a supporting detail
- Feature descriptions should focus on BENEFITS, not just features
- CTAs should be action-oriented and specific (not just "Learn More")
- Social proof should feel authentic and specific
- Avoid cliches: "revolutionize", "cutting-edge", "world-class", "synergy"
- Match the UI style: {ui_style} — e.g., brutalist copy is direct/raw, luxury is refined
- Keep headline under 10 words, subheadline under 25 words
- SEO meta description: 150-160 chars, include primary keyword naturally"""

    user_prompt = f"""Write all copy for the {business_name} landing page.

BUSINESS: {business_name}
INDUSTRY: {industry}
VALUE PROPOSITION: {value_prop}
PRODUCTS/SERVICES: {json.dumps(products)}
DIFFERENTIATOR: {differentiator}
TARGET AUDIENCE: {target_audience}
EXISTING TAGLINE: {tagline}
REVIEWS/PRESS: {json.dumps(reviews[:3]) if reviews else "none"}

SECTIONS TO WRITE COPY FOR:
{sections_str}

Return a JSON object:
{{
    "headline": "primary hero headline (max 10 words)",
    "subheadline": "supporting text (max 25 words)",
    "cta_primary": {{"text": "button text", "action": "#signup or url"}},
    "cta_secondary": {{"text": "secondary link text", "action": "#learn-more"}},
    "sections": [
        {{
            "type": "section_type",
            "heading": "section heading",
            "subheading": "optional subheading or null",
            "body": "body text if applicable or null",
            "items": [
                {{"title": "item title", "description": "1-2 sentence description", "icon_hint": "suggested icon name"}}
            ]
        }}
    ],
    "social_proof": {{
        "headline": "social proof section heading",
        "testimonials": [
            {{"quote": "testimonial text (2-3 sentences)", "author": "First L.", "role": "Title, Company"}}
        ],
        "stats": [
            {{"value": "100+", "label": "metric name"}}
        ]
    }},
    "footer": {{
        "tagline": "short footer tagline",
        "cta": "footer CTA text"
    }},
    "meta": {{
        "page_title": "SEO title (50-60 chars)",
        "meta_description": "SEO meta description (150-160 chars)",
        "og_title": "social share title",
        "og_description": "social share description (under 100 chars)"
    }}
}}

Write copy for EVERY section listed above. Each section needs heading + items or body.
Return ONLY valid JSON, no markdown fences."""

    response = await llm_chat(
        messages=[{"role": "user", "content": user_prompt}],
        system_instruction=system_prompt,
        max_tokens=3000,
        temperature=0.5,
    )

    copy_data = extract_json(response)

    if not copy_data:
        log.error("LLM failed to return valid copy JSON")
        return _fallback_copy(business_data)

    # Post-process: ensure all required fields exist
    copy_data = _validate_copy(copy_data, business_data)

    log.info(
        f"Copy generated for {business_name}: "
        f"{len(copy_data.get('sections', []))} sections, "
        f"{len(copy_data.get('social_proof', {}).get('testimonials', []))} testimonials"
    )

    return copy_data


# ---------- Validation Helpers ----------


def _validate_decisions(decisions: dict, research: dict) -> dict:
    """Validate and patch design decisions."""
    # Ensure required keys exist
    defaults = {
        "selected_design_id": "DESIGN_06",
        "design_name": "Custom Design",
        "ui_style": "modern",
        "color_mode": "light",
        "imagery_style": "minimal photography",
        "copy_tone": "professional",
        "rationale": "Default selection",
    }
    for key, default in defaults.items():
        if key not in decisions:
            decisions[key] = default

    # Validate fonts structure
    if "fonts" not in decisions or not isinstance(decisions["fonts"], dict):
        decisions["fonts"] = {
            "heading": {"family": "Clash Display", "weight": 700, "style": "normal"},
            "body": {"family": "Satoshi", "weight": 400, "style": "normal"},
            "accent": {"family": "JetBrains Mono", "weight": 500, "style": "normal"},
        }
    else:
        # Check for banned fonts
        for role, spec in decisions["fonts"].items():
            if isinstance(spec, dict) and spec.get("family") in BANNED_FONTS:
                log.warning(f"Banned font {spec['family']} in {role}, replacing")
                spec["family"] = "Satoshi" if role == "body" else "Clash Display"

    # Validate colors structure
    if "colors" not in decisions or not isinstance(decisions["colors"], dict):
        decisions["colors"] = {
            "primary": "#1e1e1e",
            "secondary": "#f2f2f2",
            "accent": "#DB4A2B",
            "background": "#ffffff",
            "text": "#1e1e1e",
            "muted": "#7a7a7a",
        }

    # Validate sections is a list
    if "sections" not in decisions or not isinstance(decisions["sections"], list):
        decisions["sections"] = [
            {"type": "hero", "name": "Hero", "layout": "centered", "notes": ""},
            {"type": "features", "name": "Features", "layout": "grid", "notes": ""},
            {"type": "social_proof", "name": "Social Proof", "layout": "cards", "notes": ""},
            {"type": "cta", "name": "Call to Action", "layout": "centered", "notes": ""},
        ]

    # Validate animations
    if "animations" not in decisions or not isinstance(decisions["animations"], dict):
        decisions["animations"] = {
            "style": "smooth",
            "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
            "duration": "800ms",
            "scroll_reveal": True,
        }

    # Validate special_components is a list
    if "special_components" not in decisions or not isinstance(decisions["special_components"], list):
        decisions["special_components"] = []

    return decisions


def _validate_copy(copy_data: dict, business_data: dict) -> dict:
    """Validate and patch copy data."""
    name = business_data.get("business_name", "Our Business")

    if "headline" not in copy_data:
        copy_data["headline"] = f"Welcome to {name}"
    if "subheadline" not in copy_data:
        copy_data["subheadline"] = business_data.get("value_proposition", "Discover what we offer.")
    if "cta_primary" not in copy_data:
        copy_data["cta_primary"] = {"text": "Get Started", "action": "#signup"}
    if "cta_secondary" not in copy_data:
        copy_data["cta_secondary"] = {"text": "Learn More", "action": "#features"}
    if "sections" not in copy_data:
        copy_data["sections"] = []
    if "social_proof" not in copy_data:
        copy_data["social_proof"] = {"headline": "Trusted by many", "testimonials": [], "stats": []}
    if "footer" not in copy_data:
        copy_data["footer"] = {"tagline": name, "cta": "Get in touch"}
    if "meta" not in copy_data:
        copy_data["meta"] = {
            "page_title": f"{name} — Official Website",
            "meta_description": business_data.get("value_proposition", f"Discover {name}")[:160],
            "og_title": name,
            "og_description": business_data.get("value_proposition", f"Discover {name}")[:100],
        }

    return copy_data


def _fallback_design(research: dict) -> dict:
    """Return a safe fallback design when LLM fails."""
    return {
        "selected_design_id": "DESIGN_06",
        "design_name": "Clean SaaS Default",
        "fonts": {
            "heading": {"family": "Clash Display", "weight": 700, "style": "normal"},
            "body": {"family": "Satoshi", "weight": 400, "style": "normal"},
            "accent": {"family": "JetBrains Mono", "weight": 500, "style": "normal"},
        },
        "colors": {
            "primary": "#171e19",
            "secondary": "#f8f9fa",
            "accent": "#ffe17c",
            "background": "#ffffff",
            "text": "#171e19",
            "muted": "#6b7280",
        },
        "ui_style": "minimal",
        "color_mode": "light",
        "sections": [
            {"type": "hero", "name": "Hero", "layout": "centered", "notes": "Full viewport centered headline"},
            {"type": "social_proof", "name": "Trusted By", "layout": "logo-grid", "notes": "Logo bar"},
            {"type": "features", "name": "Features", "layout": "grid", "notes": "3-column feature grid"},
            {"type": "how_it_works", "name": "How It Works", "layout": "steps", "notes": "3-step process"},
            {"type": "testimonials", "name": "Testimonials", "layout": "cards", "notes": "Review cards"},
            {"type": "cta", "name": "Get Started", "layout": "centered", "notes": "Final conversion section"},
        ],
        "imagery_style": "clean photography with subtle hover effects",
        "copy_tone": "clear-confident",
        "animations": {
            "style": "smooth",
            "easing": "cubic-bezier(0.16, 1, 0.3, 1)",
            "duration": "800ms",
            "scroll_reveal": True,
        },
        "special_components": ["highlight-bar", "gradient-cta"],
        "rationale": "Fallback design — LLM was unable to make a selection. Using clean SaaS default.",
        "_fallback": True,
    }


def _fallback_copy(business_data: dict) -> dict:
    """Return safe fallback copy when LLM fails."""
    name = business_data.get("business_name", "Our Business")
    return {
        "headline": f"Welcome to {name}",
        "subheadline": business_data.get("value_proposition", "Discover what makes us different."),
        "cta_primary": {"text": "Get Started", "action": "#signup"},
        "cta_secondary": {"text": "Learn More", "action": "#features"},
        "sections": [],
        "social_proof": {"headline": "Trusted by our customers", "testimonials": [], "stats": []},
        "footer": {"tagline": name, "cta": "Get in touch"},
        "meta": {
            "page_title": f"{name} — Official Website",
            "meta_description": f"Discover {name} — {business_data.get('value_proposition', 'your trusted partner')}."[:160],
            "og_title": name,
            "og_description": f"Discover {name}"[:100],
        },
        "_fallback": True,
    }


# ---------- Copy Synthesis (Multi-Phase Pipeline) ----------


async def synthesize_copy(
    research_data: dict,
    scraped_content: dict,
    competitor_data: dict,
) -> dict:
    """Synthesize landing page copy from scraped website + competitor research + wizard data.

    Phase 2 of the multi-phase pipeline. Uses the business's own words (from scraping)
    and competitive positioning to produce conversion-optimized copy.

    Returns:
        Structured copy dict matching SECTION_COPY_SCHEMA.
    """
    business_name = research_data.get("business_name", "Unknown Business")
    description = research_data.get("description", "")
    target_audience = research_data.get("target_audience", "general audience")
    business_url = research_data.get("business_url", "")

    # Build scraped content context
    scraped_context = ""
    home = scraped_content.get("home")
    if home:
        scraped_context += f"HOME PAGE TITLE: {home.get('title', 'N/A')}\n"
        scraped_context += f"META DESCRIPTION: {home.get('meta_description', 'N/A')}\n"
        for h in home.get("headings", [])[:15]:
            scraped_context += f"  {h['level'].upper()}: {h['text']}\n"
        scraped_context += f"BODY TEXT:\n{home.get('body_text', '')[:2000]}\n\n"
        for t in home.get("testimonials", [])[:5]:
            scraped_context += f"TESTIMONIAL: {t['quote'][:300]}\n"

    for page in scraped_content.get("pages", [])[:4]:
        scraped_context += f"\nPAGE: {page.get('url', 'unknown')}\n"
        scraped_context += f"TITLE: {page.get('title', 'N/A')}\n"
        for h in page.get("headings", [])[:8]:
            scraped_context += f"  {h['level'].upper()}: {h['text']}\n"
        scraped_context += f"BODY: {page.get('body_text', '')[:1000]}\n"

    # Build competitor context
    competitor_context = ""
    competitors = competitor_data.get("competitors", [])
    if competitors:
        for comp in competitors[:5]:
            if isinstance(comp, dict):
                competitor_context += f"- {comp.get('name', '?')}: {comp.get('positioning', comp.get('visual_style', ''))}\n"
    positioning_gaps = competitor_data.get("positioning_gaps", [])
    if positioning_gaps:
        competitor_context += f"POSITIONING GAPS: {', '.join(str(g) for g in positioning_gaps[:5])}\n"

    system_prompt = f"""You are an expert landing page copywriter writing copy for {business_name}.

Synthesize the business's existing content (from their current website) with competitive
intelligence to produce sharp, conversion-optimized landing page copy.

RULES:
- Use the business's OWN language and terminology where possible
- Headlines: under 8 words, zero jargon, one sharp truth
- Subheadlines: expand the benefit, max 25 words
- CTAs: action-oriented, specific to THIS business (never "Learn More")
- Stats/metrics: use real numbers from scraped content, or plausible specific numbers
- Testimonials: use real ones from scraped content if available, or write realistic ones
- Position against competitors — highlight what makes this business different
- No cliches: "revolutionize", "cutting-edge", "world-class", "synergy", "leverage"
- SEO meta description: 150-160 chars with primary keyword"""

    user_prompt = f"""Write all copy for the {business_name} landing page.

BUSINESS INFO (from wizard):
- Name: {business_name}
- URL: {business_url}
- Description: {description}
- Target audience: {target_audience}

EXISTING WEBSITE CONTENT (scraped):
{scraped_context if scraped_context else "No existing website content available."}

COMPETITOR LANDSCAPE:
{competitor_context if competitor_context else "No competitor data available."}

Return a JSON object:
{{
    "headline": "primary hero headline (max 8 words)",
    "subheadline": "supporting text (max 25 words)",
    "cta_primary": {{"text": "button text", "action": "#signup or url"}},
    "cta_secondary": {{"text": "secondary link text", "action": "#learn-more"}},
    "sections": [
        {{
            "type": "section_type (features|social_proof|how_it_works|pricing|about|testimonials|faq|cta)",
            "heading": "section heading",
            "subheading": "optional subheading or null",
            "body": "body text if applicable or null",
            "items": [
                {{"title": "item title", "description": "1-2 sentence description", "icon_hint": "suggested icon"}}
            ]
        }}
    ],
    "social_proof": {{
        "headline": "social proof section heading",
        "testimonials": [
            {{"quote": "testimonial text (2-3 sentences)", "author": "First L.", "role": "Title, Company"}}
        ],
        "stats": [
            {{"value": "100+", "label": "metric name"}}
        ]
    }},
    "footer": {{
        "tagline": "short footer tagline",
        "cta": "footer CTA text"
    }},
    "meta": {{
        "page_title": "SEO title (50-60 chars)",
        "meta_description": "SEO meta description (150-160 chars)",
        "og_title": "social share title",
        "og_description": "social share description (under 100 chars)"
    }}
}}

Include at least 4 sections. Write copy for EVERY section. Return ONLY valid JSON, no markdown fences."""

    # Use Claude CLI directly (llm_chat backends are unreliable)
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    copy_data = await _claude_json_call(full_prompt, label="copy-synthesis")

    if not copy_data:
        log.error("Copy synthesis failed for %s — using fallback", business_name)
        return _fallback_copy(research_data)

    copy_data = _validate_copy(copy_data, research_data)

    log.info(
        "Copy synthesized for %s: %d sections, %d testimonials",
        business_name,
        len(copy_data.get("sections", [])),
        len(copy_data.get("social_proof", {}).get("testimonials", [])),
    )

    return copy_data


async def _claude_json_call(prompt: str, label: str = "claude-json", timeout: int = 120) -> dict | None:
    """Run a short Claude CLI call and extract JSON from the response."""
    import asyncio
    import os

    cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print", "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "1",
        "--max-budget-usd", "0.50",
        "--output-format", "json",
        "-p", prompt,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/web3relic/otto",
            env={**os.environ, "HOME": "/home/web3relic"},
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = stdout.decode(errors="replace")

        if not text.strip():
            log.warning("[%s] Empty response", label)
            return None

        result = extract_json(text)
        if result:
            log.info("[%s] Got JSON (%d keys)", label, len(result))
        else:
            log.warning("[%s] Could not extract JSON (%d chars)", label, len(text))
        return result

    except asyncio.TimeoutError:
        log.warning("[%s] Timed out after %ds", label, timeout)
        return None
    except Exception as exc:
        log.warning("[%s] Failed: %s", label, exc)
        return None

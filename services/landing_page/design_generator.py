"""Generate 3 distinct design.md options for a landing page.

Each option is a complete design system document (~300 lines of rich markdown) with:
1. Visual Theme & Atmosphere
2. Color Palette & Roles
3. Typography Rules
4. Component Stylings
5. Layout Principles
6. Depth & Elevation
7. Do's and Don'ts
8. Responsive Behavior
9. Agent Prompt Guide

Uses Claude CLI to generate each option with a different style direction,
producing maximally diverse creative directions for agent-based HTML generation.
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from uuid import UUID

log = logging.getLogger("otto.design_generator")

WEBASSIST_DIR = Path(os.getenv("WEBASSIST_DIR", "/var/www/webassist"))
CLAUDE_CLI = os.getenv("CLAUDE_CLI_PATH", "/home/web3relic/.local/bin/claude")

# ── Style Directions ──────────────────────────────────────────────────────

STYLE_DIRECTIONS = [
    {
        "name": "bold-modern",
        "label": "Bold Modern",
        "guidance": (
            "Geometric precision, high-contrast color blocks, decisive typography. "
            "Think oversized sans-serif headlines, sharp edges, confident whitespace. "
            "Brutalist-adjacent but polished. The page should feel like it was designed "
            "by someone who builds skyscrapers."
        ),
        "moods": [
            "architectural confidence",
            "editorial punch",
            "kinetic type",
            "stark contrasts",
            "grid tension",
        ],
    },
    {
        "name": "warm-organic",
        "label": "Warm Organic",
        "guidance": (
            "Natural textures, soft rounded shapes, inviting color warmth. "
            "Think earthy tones, generous padding, friendly serif accents. "
            "The page should feel like a conversation over coffee -- approachable, "
            "genuine, and unhurried. Subtle grain or paper-like qualities welcome."
        ),
        "moods": [
            "handcrafted feel",
            "earthy palette",
            "soft gradients",
            "rounded corners",
            "comfortable reading rhythm",
        ],
    },
    {
        "name": "dark-cinematic",
        "label": "Dark Cinematic",
        "guidance": (
            "Immersive dark backgrounds, dramatic lighting effects, premium feel. "
            "Think film noir meets luxury tech. Deep blacks with selective glow, "
            "glass/blur effects, and typography that emerges from shadow. "
            "The page should feel like stepping into a private screening room."
        ),
        "moods": [
            "dramatic reveal",
            "selective illumination",
            "velvet depth",
            "glass morphism",
            "premium restraint",
        ],
    },
]

# ── Section Template ──────────────────────────────────────────────────────

SECTION_TEMPLATE = """## 1. Visual Theme & Atmosphere

[2-3 paragraphs describing the overall visual philosophy. Not just "what" but "why" —
explain the emotional logic behind the design choices. Describe how the page should FEEL
to navigate. Reference specific design movements or real-world analogies.

Include a "Key Characteristics" bullet list (8-10 items) summarizing the concrete
visual decisions: font choices, color rhythm, component shapes, spacing philosophy,
animation approach, imagery treatment.]

**Key Characteristics:**
- [specific font families with optical sizing notes]
- [color rhythm: how backgrounds alternate or flow]
- [accent color strategy: how many, where they appear]
- [imagery treatment: photography style, backgrounds, cropping]
- [headline treatment: weight, tracking, line-height feel]
- [layout philosophy: centered, asymmetric, grid, etc.]
- [CTA shape and style: pill, sharp, ghost, etc.]
- [whitespace philosophy: generous, compressed, cinematic, etc.]

## 2. Color Palette & Roles

### Primary
- **[Name]** (`#hex`): [where and why this color is used]
- **[Name]** (`#hex`): [where and why]
- **[Name]** (`#hex`): [where and why]

### Interactive
- **[Name]** (`#hex`): [CTA backgrounds, focus rings, etc.]
- **[Name]** (`#hex`): [inline links, secondary interactive]
- **[Name]** (`#hex`): [dark-background variant if applicable]

### Text
- **[Name]** (`#hex` or `rgba()`): [primary body text]
- **[Name]** (`#hex` or `rgba()`): [secondary/muted text]
- **[Name]** (`#hex` or `rgba()`): [tertiary/disabled text]

### Surface & Variants
- **[Name]** (`#hex`): [card backgrounds, elevated surfaces]
- **[Name]** (`#hex`): [alternate section backgrounds]
- **[Name]** (`#hex`): [subtle surface variations]

### Shadows
- **[Name]** (`rgba() Xpx Ypx Zpx Wpx`): [shadow usage and philosophy]

## 3. Typography Rules

### Font Family
- **Display**: `[Font Name]`, with fallbacks: `[fallback stack]`
- **Body**: `[Font Name]`, with fallbacks: `[fallback stack]`
- **Accent/Mono** (if applicable): `[Font Name]`, with fallbacks: `[fallback stack]`

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Section Heading | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Card Title | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Sub-heading | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Body | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Body Emphasis | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Button | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Link | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Caption | [font] | [size] | [weight] | [lh] | [ls] | [usage] |
| Micro | [font] | [size] | [weight] | [lh] | [ls] | [usage] |

### Principles
- [3-4 bullet points on typography philosophy: sizing strategy, weight usage, tracking patterns, line-height range]

## 4. Component Stylings

### Buttons

**Primary CTA**
- Background: `#hex`
- Text: `#hex`
- Padding: [values]
- Radius: [values]
- Border: [values]
- Font: [font, size, weight]
- Hover: [behavior]
- Active: [behavior]
- Focus: [behavior]
- Use: [when to use this button]

**Secondary CTA**
- [same structure as above]

**Ghost / Outline**
- [same structure]

### Cards & Containers
- Background: [values for light and dark variants]
- Border: [values]
- Radius: [values]
- Shadow: [values]
- Hover: [behavior]

### Navigation
- Background: [value + any blur/glass effects]
- Height: [value]
- Text: [color, size, weight]
- Active: [state]
- Mobile: [collapse behavior]

### Image Treatment
- [3-4 bullet points on how images are handled: backgrounds, cropping, overlays, borders]

### Distinctive Components
[2-4 signature components unique to this design, each with detailed specs]

## 5. Layout Principles

### Spacing System
- Base unit: [value]
- Scale: [list of values]

### Grid & Container
- Max content width: [value]
- Hero: [layout description]
- Content sections: [column/layout description]
- [any special grid notes]

### Whitespace Philosophy
- [3 bullet points on whitespace approach]

### Border Radius Scale
- Micro: [value and usage]
- Standard: [value and usage]
- Large: [value and usage]
- Full/Pill: [value and usage]

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | [treatment] | [use] |
| Subtle (Level 1) | [treatment] | [use] |
| Elevated (Level 2) | [treatment] | [use] |
| Overlay (Level 3) | [treatment] | [use] |
| Focus | [treatment] | [use] |

**Shadow Philosophy**: [1-2 sentences on how depth/shadow is used in this design]

### Decorative Depth
- [2-3 bullet points on non-shadow depth techniques: color contrast, blur, gradients, borders]

## 7. Do's and Don'ts

### Do
- [8-10 specific, actionable rules for maintaining this design system]

### Don't
- [8-10 specific anti-patterns to avoid]

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Mobile | [range] | [changes] |
| Tablet | [range] | [changes] |
| Desktop | [range] | [changes] |
| Large Desktop | [range] | [changes] |

### Touch Targets
- [2-3 bullet points on minimum touch sizes]

### Collapsing Strategy
- [4-6 bullet points on how elements adapt across breakpoints]

### Image Behavior
- [3-4 bullet points on responsive image handling]

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: [hex]
- Page background: [hex]
- Heading text: [hex]
- Body text: [hex or rgba]
- Link color: [hex]
- Focus ring: [hex]
- Card shadow: [full shadow value]

### Example Component Prompts
- "[full prompt for creating the hero section with exact values]"
- "[full prompt for creating a feature card with exact values]"
- "[full prompt for creating the navigation with exact values]"
- "[full prompt for creating an alternating section layout]"
- "[full prompt for creating a CTA button]"

### Iteration Guide
1. [7-8 numbered rules that an agent should follow when iterating on this design]
"""


# ── Core Functions ────────────────────────────────────────────────────────


def _build_design_prompt(
    style_direction: dict,
    business_data: dict,
    scraped_content: dict,
    competitor_data: dict,
    synthesized_copy: dict,
    catalog_summaries: str,
) -> str:
    """Build the full prompt for generating one design.md document."""
    business_name = business_data.get("business_name", "Unknown Business")
    industry = business_data.get("industry", "general")
    description = business_data.get("description", "")
    target_audience = business_data.get("target_audience", "general audience")
    pricing_tier = business_data.get("pricing_tier", "mid")
    brand_colors = business_data.get("brand_colors", [])

    # -- Scraped content summary --
    scraped_summary_parts = []
    home = scraped_content.get("home") if scraped_content else None
    if home:
        if home.get("title"):
            scraped_summary_parts.append(f"Site title: {home['title']}")
        headings = home.get("headings", [])
        if headings:
            heading_texts = [f"{h.get('level', 'h2').upper()}: {h.get('text', '')}" for h in headings[:10]]
            scraped_summary_parts.append("Key headings:\n  " + "\n  ".join(heading_texts))
        if home.get("meta_description"):
            scraped_summary_parts.append(f"Meta description: {home['meta_description']}")
        body = home.get("body_text", "")
        if body:
            scraped_summary_parts.append(f"Body excerpt: {body[:800]}")
    pages = scraped_content.get("pages", []) if scraped_content else []
    for page in pages[:3]:
        if page.get("title"):
            scraped_summary_parts.append(f"Subpage: {page['title']}")
    scraped_summary = "\n".join(scraped_summary_parts) if scraped_summary_parts else "No existing website content scraped."

    # -- Competitor visual styles --
    competitor_parts = []
    competitors = competitor_data.get("competitors", []) if competitor_data else []
    for comp in competitors[:5]:
        if isinstance(comp, dict):
            name = comp.get("name", "?")
            style = comp.get("visual_style", comp.get("positioning", "unknown"))
            competitor_parts.append(f"- {name}: {style}")
    competitor_summary = "\n".join(competitor_parts) if competitor_parts else "No competitor visual data."

    # -- Synthesized copy headlines --
    copy_hints = []
    if synthesized_copy:
        if synthesized_copy.get("headline"):
            copy_hints.append(f"Hero headline: {synthesized_copy['headline']}")
        if synthesized_copy.get("subheadline"):
            copy_hints.append(f"Subheadline: {synthesized_copy['subheadline']}")
        cta = synthesized_copy.get("cta_primary", {})
        if isinstance(cta, dict) and cta.get("text"):
            copy_hints.append(f"Primary CTA: {cta['text']}")
        sections = synthesized_copy.get("sections", [])
        for sec in sections[:6]:
            if isinstance(sec, dict) and sec.get("heading"):
                copy_hints.append(f"Section: {sec.get('type', '?')} -- \"{sec['heading']}\"")
    copy_summary = "\n".join(copy_hints) if copy_hints else "No synthesized copy available yet."

    # -- Style direction --
    direction_name = style_direction["name"]
    direction_label = style_direction["label"]
    direction_guidance = style_direction["guidance"]
    direction_moods = ", ".join(style_direction.get("moods", []))

    # -- Brand color hints --
    brand_color_note = ""
    if brand_colors:
        brand_color_note = (
            f"\nEXISTING BRAND COLORS: {', '.join(str(c) for c in brand_colors)}\n"
            "Incorporate these into the palette where they fit naturally. They do not need to be "
            "the dominant colors, but they should be present (e.g., as accent or CTA color)."
        )

    prompt = f"""You are an expert web designer creating a comprehensive design system document (design.md) for a landing page.

BUSINESS CONTEXT:
- Business: {business_name}
- Industry: {industry}
- Description: {description}
- Target Audience: {target_audience}
- Pricing Tier: {pricing_tier}{brand_color_note}

EXISTING WEBSITE CONTENT (scraped):
{scraped_summary}

COMPETITOR VISUAL LANDSCAPE:
{competitor_summary}

COPY THAT THE DESIGN MUST COMPLEMENT:
{copy_summary}

DESIGN CATALOG (for inspiration -- borrow techniques, don't copy wholesale):
{catalog_summaries}

STYLE DIRECTION: {direction_label}
{direction_guidance}
Mood keywords: {direction_moods}

YOUR TASK:
Generate a COMPLETE design system document in markdown. This document will be used by an AI coding agent
to build the actual HTML/CSS landing page, so every value must be specific and implementable.

REQUIREMENTS:
- The document must have ALL 9 sections listed in the template below
- Every color must be a specific hex code or rgba() value
- Every font must be a specific Google Fonts family (NOT: Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, Space Grotesk -- these are banned)
- Every size must be a specific pixel/rem value
- The "Agent Prompt Guide" section must include 5 ready-to-use prompts with exact CSS values
- The design must feel distinctly "{direction_name}" -- it should be unmistakable which style direction this is
- The design must be appropriate for the business and industry
- The design must work well with the copy headlines listed above
- Write rich, opinionated prose in sections 1, 5, and 6 -- not just specs, but design philosophy
- Target approximately 300 lines of content

Start the document with a first-level heading: # [Creative Design Name]
Follow the heading with a one-paragraph summary of the design direction.

SECTION TEMPLATE (follow this structure exactly):
{SECTION_TEMPLATE}

OUTPUT: Write the complete design.md document now. Output ONLY the markdown content -- no code fences, no preamble, no "Here is the document" intro. Start directly with the # heading."""

    return prompt


async def generate_design_option(
    option_index: int,
    style_direction: dict,
    business_data: dict,
    scraped_content: dict,
    competitor_data: dict,
    synthesized_copy: dict,
    catalog_summaries: str,
) -> str:
    """Generate one design.md document via Claude CLI.

    Args:
        option_index: 0, 1, or 2 (for logging).
        style_direction: One entry from STYLE_DIRECTIONS.
        business_data: Research data about the business.
        scraped_content: Scraped website content dict.
        competitor_data: Competitor analysis dict.
        synthesized_copy: Synthesized copy dict (headlines, CTAs, sections).
        catalog_summaries: Text summary of available design systems from the catalog.

    Returns:
        The raw markdown text of the generated design.md.

    Raises:
        RuntimeError: If generation fails completely.
    """
    label = style_direction["name"]
    business_name = business_data.get("business_name", "Unknown")

    prompt = _build_design_prompt(
        style_direction=style_direction,
        business_data=business_data,
        scraped_content=scraped_content,
        competitor_data=competitor_data,
        synthesized_copy=synthesized_copy,
        catalog_summaries=catalog_summaries,
    )

    cmd = [
        CLAUDE_CLI,
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "1",
        "--max-budget-usd", "1",
        "-p", prompt,
    ]

    env = {**os.environ, "HOME": "/home/web3relic"}

    log.info(
        "[design:%d:%s] Generating design option for '%s'",
        option_index + 1, label, business_name,
    )

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/web3relic/otto",
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
    except asyncio.TimeoutError:
        log.error("[design:%d:%s] Timed out after 300s", option_index + 1, label)
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        raise RuntimeError(f"Design option {option_index + 1} ({label}) timed out")
    except Exception as exc:
        log.error("[design:%d:%s] Subprocess error: %s", option_index + 1, label, exc)
        raise RuntimeError(f"Design option {option_index + 1} ({label}) failed: {exc}")

    text = stdout.decode(errors="replace").strip()

    if proc.returncode != 0:
        err_text = stderr.decode(errors="replace")[-500:]
        log.warning(
            "[design:%d:%s] Non-zero exit (%d): %s",
            option_index + 1, label, proc.returncode, err_text,
        )

    if not text:
        raise RuntimeError(f"Design option {option_index + 1} ({label}) returned empty output")

    # Claude CLI with --output-format json wraps the result; we don't use that flag,
    # so stdout is raw text. Strip any accidental markdown fences the LLM may have added.
    text = _strip_outer_fences(text)

    # Validate: must contain at least the 9 section headings
    required_sections = [
        "Visual Theme",
        "Color Palette",
        "Typography",
        "Component Styling",
        "Layout Principle",
        "Depth",
        "Do's and Don'ts",
        "Responsive",
        "Agent Prompt Guide",
    ]
    missing = [s for s in required_sections if s.lower() not in text.lower()]
    if len(missing) > 3:
        log.warning(
            "[design:%d:%s] Missing %d sections: %s (keeping output anyway)",
            option_index + 1, label, len(missing), ", ".join(missing),
        )

    line_count = text.count("\n") + 1
    log.info(
        "[design:%d:%s] Generated %d lines, %d chars",
        option_index + 1, label, line_count, len(text),
    )

    return text


async def generate_all_design_options(
    page_id: UUID,
    research_data: dict,
    scraped_content: dict,
    competitor_data: dict,
    synthesized_copy: dict,
) -> dict:
    """Generate all 3 design options in parallel.

    Writes each to {WEBASSIST_DIR}/{page_id}/designs/option-{1,2,3}.md.
    Returns metadata dict for each option.

    Args:
        page_id: UUID for the landing page project.
        research_data: Business research data (from wizard / Step 0).
        scraped_content: Scraped website content dict.
        competitor_data: Competitor analysis dict.
        synthesized_copy: Synthesized copy dict from copy_generator.

    Returns:
        {
            "option_1": {"status": "done"|"failed", "file_path": str, "label": str, "summary": str, "error": str|None},
            "option_2": {...},
            "option_3": {...},
        }
    """
    # Import catalog summaries
    from services.landing_page.design_catalog import get_catalog_summaries

    catalog_summaries = get_catalog_summaries()

    designs_dir = WEBASSIST_DIR / str(page_id) / "designs"
    designs_dir.mkdir(parents=True, exist_ok=True)

    # Launch all 3 in parallel
    tasks = []
    for i, direction in enumerate(STYLE_DIRECTIONS):
        tasks.append(
            _safe_generate(
                option_index=i,
                style_direction=direction,
                business_data=research_data,
                scraped_content=scraped_content,
                competitor_data=competitor_data,
                synthesized_copy=synthesized_copy,
                catalog_summaries=catalog_summaries,
            )
        )

    results = await asyncio.gather(*tasks)

    # Write results and build metadata
    metadata = {}
    for i, (content, error) in enumerate(results):
        option_key = f"option_{i + 1}"
        direction = STYLE_DIRECTIONS[i]
        file_path = designs_dir / f"option-{i + 1}.md"

        if content:
            file_path.write_text(content, encoding="utf-8")
            label = _extract_label(content) or direction["label"]
            summary = _extract_summary(content)

            metadata[option_key] = {
                "status": "done",
                "file_path": str(file_path),
                "label": label,
                "summary": summary,
                "style_direction": direction["name"],
                "line_count": content.count("\n") + 1,
                "error": None,
            }
            log.info(
                "[design:%d] Wrote %s (%d bytes) -- %s",
                i + 1, file_path, len(content), label,
            )
        else:
            metadata[option_key] = {
                "status": "failed",
                "file_path": str(file_path),
                "label": direction["label"],
                "summary": "",
                "style_direction": direction["name"],
                "line_count": 0,
                "error": error or "Unknown failure",
            }
            log.error("[design:%d] Failed: %s", i + 1, error)

    succeeded = sum(1 for v in metadata.values() if v["status"] == "done")
    log.info(
        "[design] Completed %d/3 design options for page %s",
        succeeded, page_id,
    )

    return metadata


# ── Helpers ───────────────────────────────────────────────────────────────


async def _safe_generate(
    option_index: int,
    style_direction: dict,
    business_data: dict,
    scraped_content: dict,
    competitor_data: dict,
    synthesized_copy: dict,
    catalog_summaries: str,
) -> tuple[str | None, str | None]:
    """Wrapper that catches exceptions so one failure doesn't kill the gather.

    Returns:
        (content, None) on success, (None, error_message) on failure.
    """
    try:
        content = await generate_design_option(
            option_index=option_index,
            style_direction=style_direction,
            business_data=business_data,
            scraped_content=scraped_content,
            competitor_data=competitor_data,
            synthesized_copy=synthesized_copy,
            catalog_summaries=catalog_summaries,
        )
        return (content, None)
    except Exception as exc:
        return (None, str(exc))


def _strip_outer_fences(text: str) -> str:
    """Remove wrapping ```markdown ... ``` fences if the LLM added them."""
    stripped = text.strip()
    # Check for opening fence
    if stripped.startswith("```"):
        # Remove first line (```markdown or ```)
        first_newline = stripped.find("\n")
        if first_newline == -1:
            return stripped
        stripped = stripped[first_newline + 1:]
        # Remove closing fence
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()
            stripped = stripped[: stripped.rfind("```")].rstrip()
    return stripped


def _extract_label(markdown: str) -> str:
    """Extract the design name from the first # heading.

    E.g., "# Obsidian Prism" -> "Obsidian Prism"
    """
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if match:
        label = match.group(1).strip()
        # Strip any trailing markdown formatting artifacts
        label = re.sub(r"\s*[—\-]\s*Design System.*$", "", label, flags=re.IGNORECASE)
        return label[:80]  # Reasonable max length
    return ""


def _extract_summary(markdown: str) -> str:
    """Extract a 2-3 sentence summary from the first paragraph after the # heading.

    Looks for the first non-heading, non-empty paragraph.
    """
    lines = markdown.split("\n")
    in_first_paragraph = False
    paragraph_lines = []

    for line in lines:
        stripped = line.strip()

        # Skip the heading itself
        if stripped.startswith("# "):
            in_first_paragraph = True
            continue

        # Skip empty lines before the first paragraph
        if in_first_paragraph and not stripped:
            if paragraph_lines:
                # End of first paragraph
                break
            continue

        # Skip sub-headings
        if stripped.startswith("##"):
            if paragraph_lines:
                break
            continue

        # Collect paragraph lines
        if in_first_paragraph and stripped:
            paragraph_lines.append(stripped)

    if not paragraph_lines:
        return ""

    full_text = " ".join(paragraph_lines)

    # Truncate to ~2-3 sentences (roughly 300 chars)
    if len(full_text) > 300:
        # Find a sentence boundary near 300 chars
        for end_char in [".", "!", "?"]:
            idx = full_text.find(end_char, 200)
            if 200 < idx < 400:
                return full_text[: idx + 1]
        return full_text[:300].rsplit(" ", 1)[0] + "..."

    return full_text

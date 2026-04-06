"""Parse /mnt/media/prompts.md into a structured catalog of design systems.

Each design system is extracted as a dict with:
- id, summary, style_description, fonts, colors, layout_type
- sections, special_components, special_notes, raw_spec
"""

import re
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("otto.design_catalog")

PROMPTS_PATH = Path("/mnt/media/prompts.md")

# Banned fonts from the architecture doc
BANNED_FONTS = {
    "Inter", "Roboto", "Arial", "Open Sans",
    "Lato", "Montserrat", "Poppins", "Space Grotesk",
}


def _extract_fonts(text: str) -> list[str]:
    """Extract font family names from design text."""
    # Known font families that appear in prompts.md
    KNOWN_FONTS = {
        "Clash Display", "Clash Grotesk", "Satoshi", "General Sans",
        "Anton", "Plus Jakarta Sans", "League Spartan", "JetBrains Mono",
        "Geist Mono", "DM Serif Display", "Playfair Display", "Outfit",
        "Reenie Beanie", "Aileron", "Inter Tight", "Lora", "ZTNature",
    }
    # First pass: find known fonts
    found = []
    seen = set()
    for font in KNOWN_FONTS:
        if font in text and font not in seen:
            found.append(font)
            seen.add(font)
    # Second pass: catch quoted font names not in known set
    quoted = re.findall(r"['\"]([A-Z][A-Za-z\s]+?)['\"]", text)
    # Filter: must look like a font name (2+ words or known pattern)
    NON_FONT_WORDS = {
        "Echo Stack", "Read More", "View Case", "Quick View",
        "Raw", "New", "Most Popular", "Join Digest", "Get Access",
        "Enter", "Free Access", "Super Travel", "Season",
    }
    for f in quoted:
        f = f.strip()
        if (f not in seen and f not in NON_FONT_WORDS
                and len(f) < 25 and " " in f
                and not f.startswith("http")
                and any(c.isupper() for c in f[1:])):
            seen.add(f)
            found.append(f)
    return found


def _extract_colors(text: str) -> dict[str, str]:
    """Extract hex color codes with their context labels."""
    colors = {}
    # Match patterns like "Background: #f2f2f2" or "#171e19 (charcoal)"
    hex_pattern = re.findall(
        r'(?:(\w[\w\s/]*?)[:=]\s*)?`?(#[0-9A-Fa-f]{6})\b`?(?:\s*\(([^)]+)\))?',
        text
    )
    idx = 0
    for label, hex_val, paren_label in hex_pattern:
        raw = (label or paren_label or "").strip().lower()
        # Clean up the key
        key = re.sub(r'[^a-z0-9_ ]', '', raw).strip().replace(" ", "_")
        if not key or key in colors:
            # Use semantic name based on position
            role_names = ["background", "primary_text", "accent", "secondary",
                          "muted", "border", "highlight"]
            key = role_names[idx] if idx < len(role_names) else f"color_{idx}"
            idx += 1
        if hex_val:
            colors[key] = hex_val
    return colors


def _extract_sections(text: str) -> list[str]:
    """Extract section names from ## headings under Layout & Structure."""
    layout_match = re.search(
        r'# Layout & Structure\n(.*?)(?=\n# (?!#)|$)',
        text, re.DOTALL
    )
    if not layout_match:
        return []
    layout_text = layout_match.group(1)
    sections = re.findall(r'^## (.+)$', layout_text, re.MULTILINE)
    return sections


def _extract_special_components(text: str) -> list[str]:
    """Extract special component names."""
    comps_match = re.search(
        r'# Special Components\n(.*?)(?=\n# (?!#)|$)',
        text, re.DOTALL
    )
    if not comps_match:
        return []
    return re.findall(r'^## (.+)$', comps_match.group(1), re.MULTILINE)


def _extract_special_notes(text: str) -> str:
    """Extract special notes section."""
    notes_match = re.search(
        r'# Special Notes\n(.+?)(?=\nDESIGN \d|$)',
        text, re.DOTALL
    )
    return notes_match.group(1).strip() if notes_match else ""


def _classify_style(summary: str, style_text: str) -> str:
    """Classify the design into a UI style category."""
    combined = (summary + " " + style_text).lower()
    if "brutalist" in combined or "brutal" in combined:
        if "luxury" in combined or "fashion" in combined:
            return "luxury-brutalist"
        if "lite" in combined or "saas" in combined:
            return "brutalist-lite"
        return "brutalist"
    if "minimal" in combined and ("dark" in combined or "obsidian" in combined):
        return "dark-minimal"
    if "minimal" in combined:
        return "minimal"
    if "editorial" in combined:
        return "editorial"
    if "glass" in combined or "glassmorphism" in combined:
        return "glassmorphic"
    if "wellness" in combined or "soft" in combined or "pastel" in combined:
        return "soft-organic"
    if "neon" in combined or "cyber" in combined or "futuristic" in combined:
        return "futuristic"
    if "luxury" in combined or "premium" in combined:
        return "luxury"
    if "corporate" in combined or "technical" in combined:
        return "technical"
    if "cinematic" in combined:
        return "cinematic"
    if "playful" in combined or "bold" in combined:
        return "bold"
    return "modern"


def _classify_tone(summary: str, style_text: str) -> str:
    """Infer recommended copy tone from the design aesthetic."""
    combined = (summary + " " + style_text).lower()
    if "luxury" in combined or "premium" in combined or "fashion" in combined:
        return "refined-authoritative"
    if "brutalist" in combined or "aggressive" in combined or "raw" in combined:
        return "bold-direct"
    if "wellness" in combined or "soft" in combined or "organic" in combined:
        return "warm-conversational"
    if "technical" in combined or "architectural" in combined:
        return "precise-technical"
    if "cinematic" in combined or "editorial" in combined:
        return "narrative-dramatic"
    if "neon" in combined or "velocity" in combined or "kinetic" in combined:
        return "urgent-energetic"
    if "saas" in combined or "modern" in combined:
        return "clear-confident"
    return "professional"


def _classify_color_mode(colors: dict[str, str]) -> str:
    """Classify as light-mode, dark-mode, or mixed."""
    bg_keys = [k for k in colors if "background" in k or "bg" in k or "base" in k]
    if bg_keys:
        bg = colors[bg_keys[0]].lower()
        r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "dark" if luminance < 0.3 else "light"
    return "light"


def parse_prompts_file(path: Optional[Path] = None) -> list[dict]:
    """Parse prompts.md into a list of structured design system dicts."""
    path = path or PROMPTS_PATH
    if not path.exists():
        log.error(f"Prompts file not found: {path}")
        return []

    content = path.read_text(encoding="utf-8")

    # Split by DESIGN headers
    blocks = re.split(r'\n(?=DESIGN \d+)', content)
    catalog = []

    for block in blocks:
        # Extract design ID
        id_match = re.match(r'DESIGN (\d+)', block)
        if not id_match:
            continue

        design_id = f"DESIGN_{id_match.group(1).zfill(2)}"

        # Skip designs that are raw HTML (DESIGN 16 has embedded HTML)
        if "<!DOCTYPE html>" in block[:2000]:
            # Still extract summary if available
            pass

        # Extract summary
        summary_match = re.search(r'# Summary\n\n(.+?)(?=\n#)', block, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        # Extract style description
        style_match = re.search(r'# Style\n\n(.+?)(?=\n## Spec|\n# )', block, re.DOTALL)
        style_desc = style_match.group(1).strip() if style_match else ""

        # Extract spec section
        spec_match = re.search(r'## Spec\n\n(.+?)(?=\n# )', block, re.DOTALL)
        raw_spec = spec_match.group(1).strip() if spec_match else ""

        # Parse structured data
        fonts = _extract_fonts(block)
        colors = _extract_colors(raw_spec or block[:3000])
        sections = _extract_sections(block)
        components = _extract_special_components(block)
        notes = _extract_special_notes(block)

        # Classifications
        ui_style = _classify_style(summary, style_desc)
        copy_tone = _classify_tone(summary, style_desc)
        color_mode = _classify_color_mode(colors)

        catalog.append({
            "id": design_id,
            "summary": summary,
            "style_description": style_desc,
            "ui_style": ui_style,
            "color_mode": color_mode,
            "copy_tone": copy_tone,
            "fonts": fonts,
            "colors": colors,
            "sections": sections,
            "special_components": components,
            "special_notes": notes,
            "raw_spec": raw_spec[:2000],  # Truncate for LLM context
        })

    log.info(f"Parsed {len(catalog)} design systems from {path}")
    return catalog


# Module-level cache
_catalog_cache: list[dict] | None = None


def get_catalog() -> list[dict]:
    """Get the parsed design catalog (cached)."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = parse_prompts_file()
    return _catalog_cache


def get_catalog_summaries() -> str:
    """Build a condensed catalog summary for LLM context."""
    catalog = get_catalog()
    lines = []
    for d in catalog:
        fonts_str = ", ".join(d["fonts"][:3]) if d["fonts"] else "unspecified"
        top_colors = list(d["colors"].values())[:4]
        colors_str = " ".join(top_colors) if top_colors else "unspecified"
        lines.append(
            f"- {d['id']}: {d['summary'][:120]}... "
            f"| Style: {d['ui_style']} | Mode: {d['color_mode']} "
            f"| Fonts: {fonts_str} | Colors: {colors_str} "
            f"| Sections: {', '.join(d['sections'][:5])}"
        )
    return "\n".join(lines)


def get_design_by_id(design_id: str) -> dict | None:
    """Retrieve a specific design system by ID."""
    for d in get_catalog():
        if d["id"] == design_id:
            return d
    return None

"""HTML Generation Engine for Landing Pages.

generateHTML(design_decisions, copy, research_data, page_id) → complete HTML string

Produces a self-contained, single-file HTML landing page:
- Inline all CSS (no external deps except Google Fonts CDN)
- Uses exact fonts/colors/sections from design_decisions
- Renders all sections: hero, features, social_proof, testimonials, cta, pricing, faq, etc.
- Mobile responsive via inline CSS media queries
- Includes meta tags, OG tags
- Inserts business name, copy, CTAs from copy object
- Saves to /var/www/webassist/{id}/index.html
- Updates landing_pages DB record with html_path and preview_url
"""

import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any
from uuid import UUID

log = logging.getLogger("otto.generator")

WEBASSIST_DIR = Path("/var/www/webassist")
BASE_URL = "https://webassist.otto.lk"


# ── Font URL builder ──────────────────────────────────────────────────────────

GOOGLE_FONT_ALIASES = {
    "Satoshi": "DM+Sans",
    "Clash Display": "Space+Grotesk",
    "Plus Jakarta Sans": "Plus+Jakarta+Sans",
    "Cabinet Grotesk": "Space+Grotesk",
    "Neue Montreal": "DM+Sans",
    "Geist": "DM+Sans",
    "General Sans": "DM+Sans",
    "Swear Display": "Playfair+Display",
    "Editorial New": "Playfair+Display",
    "PP Mondwest": "Bebas+Neue",
    "Boska": "Libre+Baskerville",
    "Syne": "Syne",
    "Instrument Serif": "Instrument+Serif",
    "Shrikhand": "Shrikhand",
    "Fraunces": "Fraunces",
    "Bebas Neue": "Bebas+Neue",
    "Barlow": "Barlow",
    "DM Sans": "DM+Sans",
    "DM Serif Display": "DM+Serif+Display",
    "Space Grotesk": "Space+Grotesk",
    "Space Mono": "Space+Mono",
    "JetBrains Mono": "JetBrains+Mono",
    "Manrope": "Manrope",
    "Bricolage Grotesque": "Bricolage+Grotesque",
    "Libre Baskerville": "Libre+Baskerville",
    "Playfair Display": "Playfair+Display",
    "Cormorant Garamond": "Cormorant+Garamond",
    "Outfit": "Outfit",
    "Oxanium": "Oxanium",
    "Rajdhani": "Rajdhani",
    "IBM Plex Mono": "IBM+Plex+Mono",
    "Fira Code": "Fira+Code",
    "Cardo": "Cardo",
}


def _google_font_name(family: str) -> str:
    """Map custom font name to closest Google Fonts equivalent."""
    return GOOGLE_FONT_ALIASES.get(family, family.replace(" ", "+"))


def _build_google_fonts_url(fonts: dict) -> str:
    """Build a Google Fonts import URL for all font families."""
    seen = set()
    families = []
    for spec in fonts.values():
        if not isinstance(spec, dict):
            continue
        family = spec.get("family", "")
        gf = _google_font_name(family)
        if gf and gf not in seen:
            seen.add(gf)
            weights = "300;400;500;600;700;800"
            families.append(f"family={gf}:ital,wght@0,{weights};1,400")
    if not families:
        families = ["family=DM+Sans:ital,wght@0,300;400;500;600;700;800;1,400"]
    query = "&".join(families)
    return f"https://fonts.googleapis.com/css2?{query}&display=swap"


def _css_font_family(spec: dict) -> str:
    """Convert font spec to CSS font-family value."""
    family = spec.get("family", "DM Sans")
    gf = _google_font_name(family)
    gf_display = gf.replace("+", " ")
    # Return original name first (may match), then Google Fonts name, then fallback
    if family != gf_display:
        return f"'{family}', '{gf_display}', sans-serif"
    return f"'{family}', sans-serif"


# ── UI Style → CSS variables ───────────────────────────────────────────────────

def _build_css_variables(design: dict, copy_data: dict) -> str:
    """Build CSS custom properties from design decisions."""
    colors = design.get("colors", {})
    fonts = design.get("fonts", {})
    animations = design.get("animations", {})
    ui_style = design.get("ui_style", "minimal")
    color_mode = design.get("color_mode", "light")

    primary = colors.get("primary", "#1a1a2e")
    secondary = colors.get("secondary", "#f0f0f0")
    accent = colors.get("accent", "#e94560")
    background = colors.get("background", "#ffffff")
    text_color = colors.get("text", "#1a1a1e")
    muted = colors.get("muted", "#6b7280")

    heading_font = _css_font_family(fonts.get("heading", {"family": "Space Grotesk"}))
    body_font = _css_font_family(fonts.get("body", {"family": "DM Sans"}))
    accent_font = _css_font_family(fonts.get("accent", fonts.get("body", {"family": "DM Sans"})))

    duration = animations.get("duration", "800ms")
    easing = animations.get("easing", "cubic-bezier(0.16, 1, 0.3, 1)")

    # Derive secondary text from background for contrast
    bg_is_dark = color_mode == "dark"
    surface = _darken_or_lighten(background, 0.04, bg_is_dark)
    surface2 = _darken_or_lighten(background, 0.08, bg_is_dark)
    border = _darken_or_lighten(background, 0.12, bg_is_dark)

    # Style-specific overrides
    style_vars = _get_style_vars(ui_style, colors)

    return f"""
:root {{
    --primary: {primary};
    --secondary: {secondary};
    --accent: {accent};
    --bg: {background};
    --surface: {surface};
    --surface2: {surface2};
    --text: {text_color};
    --muted: {muted};
    --border: {border};
    --font-heading: {heading_font};
    --font-body: {body_font};
    --font-accent: {accent_font};
    --duration: {duration};
    --ease: {easing};
    --radius: {style_vars['radius']};
    --radius-sm: {style_vars['radius_sm']};
    --border-width: {style_vars['border_width']};
    --shadow: {style_vars['shadow']};
    --shadow-hover: {style_vars['shadow_hover']};
    --section-gap: 6rem;
    --container-max: 1200px;
}}"""


def _get_style_vars(ui_style: str, colors: dict) -> dict:
    """Return style-specific CSS variable values."""
    accent = colors.get("accent", "#e94560")
    styles = {
        "minimal": {
            "radius": "8px", "radius_sm": "4px", "border_width": "1px",
            "shadow": "0 1px 3px rgba(0,0,0,0.08)", "shadow_hover": "0 8px 30px rgba(0,0,0,0.12)",
        },
        "brutalist": {
            "radius": "0px", "radius_sm": "0px", "border_width": "2px",
            "shadow": "4px 4px 0 var(--primary)", "shadow_hover": "6px 6px 0 var(--primary)",
        },
        "editorial": {
            "radius": "2px", "radius_sm": "1px", "border_width": "1px",
            "shadow": "none", "shadow_hover": "none",
        },
        "glassmorphic": {
            "radius": "16px", "radius_sm": "8px", "border_width": "1px",
            "shadow": "0 8px 32px rgba(0,0,0,0.1)", "shadow_hover": "0 16px 48px rgba(0,0,0,0.15)",
        },
        "luxury": {
            "radius": "0px", "radius_sm": "0px", "border_width": "1px",
            "shadow": "0 4px 20px rgba(0,0,0,0.15)", "shadow_hover": "0 12px 40px rgba(0,0,0,0.2)",
        },
        "technical": {
            "radius": "4px", "radius_sm": "2px", "border_width": "1px",
            "shadow": "0 0 0 1px rgba(255,255,255,0.1)", "shadow_hover": f"0 0 0 2px {accent}",
        },
        "bold": {
            "radius": "12px", "radius_sm": "6px", "border_width": "2px",
            "shadow": "0 4px 20px rgba(0,0,0,0.15)", "shadow_hover": "0 8px 40px rgba(0,0,0,0.25)",
        },
        "soft-organic": {
            "radius": "24px", "radius_sm": "12px", "border_width": "1px",
            "shadow": "0 4px 24px rgba(0,0,0,0.06)", "shadow_hover": "0 12px 48px rgba(0,0,0,0.1)",
        },
        "futuristic": {
            "radius": "4px", "radius_sm": "2px", "border_width": "1px",
            "shadow": f"0 0 20px rgba(0,0,0,0.3), 0 0 40px {accent}22", "shadow_hover": f"0 0 30px rgba(0,0,0,0.4), 0 0 60px {accent}33",
        },
        "cinematic": {
            "radius": "0px", "radius_sm": "0px", "border_width": "0px",
            "shadow": "0 8px 40px rgba(0,0,0,0.4)", "shadow_hover": "0 16px 60px rgba(0,0,0,0.5)",
        },
    }
    return styles.get(ui_style, styles["minimal"])


def _darken_or_lighten(hex_color: str, amount: float, make_darker: bool) -> str:
    """Adjust hex color brightness slightly."""
    try:
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        if make_darker:
            # Darken
            r = max(0, int(r * (1 - amount)))
            g = max(0, int(g * (1 - amount)))
            b = max(0, int(b * (1 - amount)))
        else:
            # Check if color is already dark, if so lighten; if light, darken slightly
            luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            if luminance > 0.5:
                # Light bg: make surface slightly darker
                r = max(0, int(r - (amount * 255)))
                g = max(0, int(g - (amount * 255)))
                b = max(0, int(b - (amount * 255)))
            else:
                # Dark bg: make surface slightly lighter
                r = min(255, int(r + (amount * 255)))
                g = min(255, int(g + (amount * 255)))
                b = min(255, int(b + (amount * 255)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color if hex_color.startswith("#") else f"#{hex_color}"


# ── Base CSS ───────────────────────────────────────────────────────────────────

def _build_base_css(design: dict) -> str:
    """Build base/reset CSS."""
    ui_style = design.get("ui_style", "minimal")
    color_mode = design.get("color_mode", "light")

    # Style-specific body treatments
    body_extras = ""
    if ui_style == "glassmorphic":
        body_extras = "background-attachment: fixed;"
    elif ui_style == "cinematic":
        body_extras = "background-color: var(--bg); letter-spacing: 0.02em;"

    # Scrollbar styling
    scrollbar = """
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 3px; }""" if ui_style != "brutalist" else ""

    return f"""
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

html {{
    scroll-behavior: smooth;
    font-size: 16px;
    -webkit-text-size-adjust: 100%;
}}

body {{
    font-family: var(--font-body);
    background-color: var(--bg);
    color: var(--text);
    line-height: 1.6;
    overflow-x: hidden;
    {body_extras}
}}

img {{ max-width: 100%; height: auto; display: block; }}
a {{ color: inherit; text-decoration: none; }}
ul, ol {{ list-style: none; }}

.container {{
    width: 100%;
    max-width: var(--container-max);
    margin: 0 auto;
    padding: 0 2rem;
}}

section {{
    padding: var(--section-gap) 0;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: var(--font-heading);
    line-height: 1.15;
    font-weight: 700;
}}

.section-label {{
    font-family: var(--font-accent);
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 1rem;
    display: block;
}}

.section-heading {{
    font-size: clamp(1.75rem, 3vw, 2.5rem);
    font-weight: 700;
    margin-bottom: 1rem;
    color: var(--text);
}}

.section-subheading {{
    font-size: 1.125rem;
    color: var(--muted);
    max-width: 600px;
    line-height: 1.7;
}}

/* Buttons */
.btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.875rem 1.75rem;
    border-radius: var(--radius);
    font-family: var(--font-body);
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    border: var(--border-width) solid transparent;
    transition: all 0.2s ease;
    white-space: nowrap;
    text-decoration: none;
}}

.btn-primary {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
}}
.btn-primary:hover {{
    opacity: 0.9;
    transform: translateY(-1px);
    box-shadow: var(--shadow-hover);
}}

.btn-secondary {{
    background: transparent;
    color: var(--text);
    border-color: var(--border);
}}
.btn-secondary:hover {{
    border-color: var(--primary);
    background: var(--surface);
}}

/* Scroll reveal */
.reveal {{
    opacity: 0;
    transform: translateY(24px);
    transition: opacity var(--duration) var(--ease), transform var(--duration) var(--ease);
}}
.reveal.visible {{
    opacity: 1;
    transform: translateY(0);
}}
.reveal-delay-1 {{ transition-delay: 100ms; }}
.reveal-delay-2 {{ transition-delay: 200ms; }}
.reveal-delay-3 {{ transition-delay: 300ms; }}
.reveal-delay-4 {{ transition-delay: 400ms; }}

{scrollbar}

/* Mobile responsive */
@media (max-width: 768px) {{
    :root {{
        --section-gap: 4rem;
    }}
    .container {{
        padding: 0 1.25rem;
    }}
    .btn {{
        padding: 0.75rem 1.5rem;
        font-size: 0.875rem;
    }}
    .section-heading {{
        font-size: clamp(1.5rem, 5vw, 2rem);
    }}
}}"""


# ── Style-specific CSS ─────────────────────────────────────────────────────────

def _build_style_css(design: dict) -> str:
    """Build UI-style-specific CSS enhancements."""
    ui_style = design.get("ui_style", "minimal")
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")
    primary = colors.get("primary", "#1a1a2e")
    color_mode = design.get("color_mode", "light")

    if ui_style == "brutalist":
        return f"""
/* Brutalist overrides */
.btn-primary {{
    background: var(--primary);
    color: var(--bg);
    border: var(--border-width) solid var(--primary);
    box-shadow: 4px 4px 0 var(--accent);
    transition: box-shadow 0.1s ease, transform 0.1s ease;
}}
.btn-primary:hover {{
    box-shadow: 6px 6px 0 var(--accent);
    transform: translate(-2px, -2px);
    opacity: 1;
}}
.btn-secondary {{
    border: var(--border-width) solid var(--primary);
    box-shadow: 3px 3px 0 var(--primary);
}}
.btn-secondary:hover {{
    box-shadow: 4px 4px 0 var(--primary);
    transform: translate(-1px, -1px);
    background: var(--surface);
}}
.card {{
    border: 2px solid var(--primary);
    box-shadow: 4px 4px 0 var(--primary);
}}
.card:hover {{
    box-shadow: 6px 6px 0 var(--accent);
    transform: translate(-2px, -2px);
}}"""

    elif ui_style == "glassmorphic":
        return f"""
/* Glassmorphic overrides */
.card {{
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(255,255,255,0.15);
    box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}}
.card:hover {{
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.25);
    box-shadow: 0 16px 48px rgba(0,0,0,0.2);
    transform: translateY(-4px);
}}
nav {{
    background: rgba(255,255,255,0.08) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
}}"""

    elif ui_style == "luxury":
        return f"""
/* Luxury overrides */
body {{ letter-spacing: 0.01em; }}
h1, h2, h3, h4 {{ font-weight: 300; letter-spacing: -0.02em; }}
.section-label {{ letter-spacing: 0.3em; font-weight: 400; }}
.btn-primary {{
    background: var(--primary);
    color: var(--bg);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-size: 0.8125rem;
    padding: 1rem 2.5rem;
}}
.btn-primary:hover {{
    background: var(--accent);
    transform: none;
    opacity: 1;
}}
.card {{
    border: 1px solid var(--border);
    background: var(--surface);
}}
hr, .divider {{
    border: none;
    border-top: 1px solid var(--border);
    margin: 2rem 0;
}}"""

    elif ui_style == "futuristic":
        return f"""
/* Futuristic overrides */
.btn-primary {{
    background: transparent;
    color: var(--accent);
    border: 1px solid var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.8125rem;
    position: relative;
    overflow: hidden;
}}
.btn-primary::before {{
    content: '';
    position: absolute;
    inset: 0;
    background: var(--accent);
    transform: scaleX(0);
    transform-origin: left;
    transition: transform 0.3s var(--ease);
    z-index: -1;
}}
.btn-primary:hover::before {{ transform: scaleX(1); }}
.btn-primary:hover {{ color: var(--bg); opacity: 1; transform: none; }}
.card {{
    border: 1px solid rgba(255,255,255,0.1);
    background: rgba(255,255,255,0.03);
    position: relative;
    overflow: hidden;
}}
.card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}}
.card:hover::before {{ opacity: 1; }}
.card:hover {{ border-color: rgba(255,255,255,0.2); }}"""

    elif ui_style == "soft-organic":
        return f"""
/* Soft-organic overrides */
.card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 24px;
    transition: transform 0.3s var(--ease), box-shadow 0.3s var(--ease);
}}
.card:hover {{
    transform: translateY(-6px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.08);
}}
.btn-primary {{
    border-radius: 100px;
}}
.btn-secondary {{
    border-radius: 100px;
}}
h1, h2, h3 {{ font-weight: 600; }}"""

    elif ui_style == "editorial":
        return f"""
/* Editorial overrides */
body {{ font-size: 1.0625rem; }}
h1, h2, h3 {{ font-weight: 400; letter-spacing: -0.03em; }}
h1 {{ font-style: italic; }}
.section-label {{ font-style: normal; color: var(--muted); font-size: 0.6875rem; }}
.btn-primary {{
    background: var(--primary);
    color: var(--bg);
    border-radius: 2px;
    font-weight: 500;
    letter-spacing: 0.05em;
}}
.card {{
    border-top: 1px solid var(--border);
    border-radius: 0;
    padding: 2rem 0;
}}"""

    elif ui_style == "technical":
        return f"""
/* Technical overrides */
body {{ font-size: 0.9375rem; }}
.card {{
    background: var(--surface);
    border: 1px solid var(--border);
    font-family: var(--font-accent);
    font-size: 0.875rem;
}}
.section-label {{ font-family: var(--font-accent); color: var(--accent); }}
.btn-primary {{
    font-family: var(--font-accent);
    font-size: 0.875rem;
    letter-spacing: 0.05em;
}}
.stat-value {{ font-family: var(--font-accent); }}"""

    else:
        return ""


# ── Nav ───────────────────────────────────────────────────────────────────────

def _build_nav(design: dict, copy_data: dict, business_name: str) -> str:
    cta_text = copy_data.get("cta_primary", {}).get("text", "Get Started")
    cta_action = copy_data.get("cta_primary", {}).get("action", "#")
    logo_text = business_name[:20]
    ui_style = design.get("ui_style", "minimal")
    colors = design.get("colors", {})
    bg = colors.get("background", "#ffffff")
    primary = colors.get("primary", "#1a1a2e")
    color_mode = design.get("color_mode", "light")

    nav_bg = "rgba(255,255,255,0.92)" if color_mode == "light" else f"rgba(0,0,0,0.88)"
    text_on_nav = primary

    if ui_style == "brutalist":
        return f"""
<nav id="nav" style="position:fixed;top:0;left:0;right:0;z-index:100;padding:1rem 2rem;background:var(--bg);border-bottom:2px solid var(--primary);display:flex;align-items:center;justify-content:space-between;">
  <div style="font-family:var(--font-heading);font-size:1.25rem;font-weight:800;color:var(--primary);letter-spacing:-0.02em;">{logo_text}</div>
  <a href="{cta_action}" class="btn btn-primary">{cta_text}</a>
</nav>"""
    else:
        return f"""
<nav id="nav" style="position:fixed;top:0;left:0;right:0;z-index:100;padding:1rem 2rem;background:{nav_bg};backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;transition:all 0.3s ease;">
  <div style="font-family:var(--font-heading);font-size:1.25rem;font-weight:700;color:var(--primary);">{logo_text}</div>
  <a href="{cta_action}" class="btn btn-primary" style="padding:0.625rem 1.25rem;font-size:0.875rem;">{cta_text}</a>
</nav>"""


# ── Section renderers ──────────────────────────────────────────────────────────

def _render_hero(section_config: dict, copy_data: dict, design: dict) -> str:
    layout = section_config.get("layout", "centered")
    headline = copy_data.get("headline", "Welcome")
    subheadline = copy_data.get("subheadline", "")
    cta_primary = copy_data.get("cta_primary", {"text": "Get Started", "action": "#"})
    cta_secondary = copy_data.get("cta_secondary", {"text": "Learn More", "action": "#features"})
    colors = design.get("colors", {})
    ui_style = design.get("ui_style", "minimal")
    color_mode = design.get("color_mode", "light")
    primary = colors.get("primary", "#1a1a2e")
    accent = colors.get("accent", "#e94560")
    bg = colors.get("background", "#ffffff")

    # Hero background treatment
    if ui_style == "futuristic":
        hero_bg = f"background:radial-gradient(ellipse at 60% 50%, {accent}22 0%, transparent 60%), var(--bg);"
        dot_pattern = f"background-image:radial-gradient(circle, {primary}22 1px, transparent 1px);background-size:32px 32px;"
    elif ui_style == "glassmorphic":
        hero_bg = f"background:linear-gradient(135deg, {primary} 0%, {accent}88 100%);"
        dot_pattern = ""
    elif ui_style == "brutalist":
        hero_bg = f"background:var(--bg);"
        dot_pattern = ""
    elif ui_style == "editorial":
        hero_bg = f"background:var(--bg);"
        dot_pattern = ""
    elif ui_style == "cinematic":
        hero_bg = f"background:linear-gradient(180deg, {primary} 0%, #000 100%);"
        dot_pattern = ""
    elif ui_style == "luxury":
        hero_bg = f"background:var(--bg);"
        dot_pattern = f"background-image:repeating-linear-gradient(0deg, {primary}08, {primary}08 1px, transparent 1px, transparent 40px), repeating-linear-gradient(90deg, {primary}08, {primary}08 1px, transparent 1px, transparent 40px);"
    else:
        hero_bg = f"background:var(--bg);"
        dot_pattern = ""

    hero_text_color = "color:#fff;" if ui_style in ("glassmorphic", "cinematic") else ""
    subtext_color = "color:rgba(255,255,255,0.75);" if ui_style in ("glassmorphic", "cinematic") else "color:var(--muted);"

    if layout == "split":
        return f"""
<section id="hero" style="min-height:100vh;display:flex;align-items:center;padding-top:5rem;{hero_bg}position:relative;overflow:hidden;">
  {'<div style="position:absolute;inset:0;' + dot_pattern + 'pointer-events:none;opacity:0.6;"></div>' if dot_pattern else ''}
  <div class="container">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:4rem;align-items:center;">
      <div class="reveal">
        <span class="section-label" style="{hero_text_color.replace('color:#fff;','color:var(--accent);') if not hero_text_color else 'color:rgba(255,255,255,0.6);letter-spacing:0.15em;font-size:0.75rem;'}">Welcome</span>
        <h1 style="font-size:clamp(2.5rem,5vw,4rem);margin-bottom:1.5rem;{hero_text_color}">{headline}</h1>
        <p style="font-size:1.125rem;margin-bottom:2.5rem;max-width:520px;line-height:1.75;{subtext_color}">{subheadline}</p>
        <div style="display:flex;gap:1rem;flex-wrap:wrap;">
          <a href="{cta_primary.get('action','#')}" class="btn btn-primary">{cta_primary.get('text','Get Started')}</a>
          <a href="{cta_secondary.get('action','#features')}" class="btn btn-secondary" {'style="color:#fff;border-color:rgba(255,255,255,0.3);"' if hero_text_color else ''}>{cta_secondary.get('text','Learn More')}</a>
        </div>
      </div>
      <div class="reveal reveal-delay-2" style="position:relative;">
        <div style="width:100%;aspect-ratio:4/3;background:linear-gradient(135deg,{accent}22,{primary}11);border-radius:var(--radius);display:flex;align-items:center;justify-content:center;border:1px solid var(--border);">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="80" height="80" rx="16" fill="{accent}" opacity="0.15"/>
            <path d="M40 20L56 44H24L40 20Z" fill="{accent}" opacity="0.6"/>
            <circle cx="40" cy="54" r="10" fill="{accent}" opacity="0.4"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</section>"""
    else:  # centered (default)
        return f"""
<section id="hero" style="min-height:100vh;display:flex;align-items:center;justify-content:center;text-align:center;padding-top:5rem;{hero_bg}position:relative;overflow:hidden;">
  {'<div style="position:absolute;inset:0;' + dot_pattern + 'pointer-events:none;opacity:0.5;"></div>' if dot_pattern else ''}
  <div class="container" style="position:relative;z-index:1;">
    <div class="reveal">
      <span class="section-label" style="{'color:rgba(255,255,255,0.6);' if hero_text_color else ''}">Built for results</span>
      <h1 style="font-size:clamp(2.75rem,6vw,5rem);margin-bottom:1.5rem;{hero_text_color}max-width:900px;margin-left:auto;margin-right:auto;">{headline}</h1>
      <p style="font-size:1.125rem;margin-bottom:2.5rem;max-width:560px;margin-left:auto;margin-right:auto;line-height:1.75;{subtext_color}">{subheadline}</p>
      <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
        <a href="{cta_primary.get('action','#')}" class="btn btn-primary">{cta_primary.get('text','Get Started')} →</a>
        <a href="{cta_secondary.get('action','#features')}" class="btn btn-secondary" {'style="color:#fff;border-color:rgba(255,255,255,0.3);"' if hero_text_color else ''}>{cta_secondary.get('text','Learn More')}</a>
      </div>
    </div>
  </div>
</section>"""


def _render_features(section_config: dict, section_copy: dict, design: dict) -> str:
    layout = section_config.get("layout", "grid")
    heading = section_copy.get("heading", "Features")
    subheading = section_copy.get("subheading", "")
    items = section_copy.get("items", [])
    ui_style = design.get("ui_style", "minimal")
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")

    # Icon SVGs for common hint types
    icons = {
        "star": f'<svg width="24" height="24" fill="{accent}" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
        "check": f'<svg width="24" height="24" fill="none" stroke="{accent}" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>',
        "bolt": f'<svg width="24" height="24" fill="{accent}" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>',
        "shield": f'<svg width="24" height="24" fill="none" stroke="{accent}" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
        "chart": f'<svg width="24" height="24" fill="none" stroke="{accent}" stroke-width="2" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
        "default": f'<svg width="24" height="24" fill="none" stroke="{accent}" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4l3 3"/></svg>',
    }

    def get_icon(hint: str) -> str:
        hint_lower = (hint or "").lower()
        for key in icons:
            if key in hint_lower:
                return icons[key]
        return icons["default"]

    # Build feature items
    if not items:
        items = [
            {"title": "Fast & Reliable", "description": "Built for performance from day one.", "icon_hint": "bolt"},
            {"title": "Secure by Default", "description": "Enterprise-grade security baked in.", "icon_hint": "shield"},
            {"title": "Data-Driven", "description": "Make decisions backed by real insights.", "icon_hint": "chart"},
        ]

    cols = 3 if len(items) >= 3 else len(items)

    if layout in ("bento",):
        # Bento grid layout
        cards_html = ""
        for i, item in enumerate(items[:6]):
            span = "grid-column: span 2;" if i == 0 else ""
            cards_html += f"""
      <div class="card reveal reveal-delay-{min(i+1,4)}" style="{span}padding:2rem;border-radius:var(--radius);background:var(--surface);border:var(--border-width) solid var(--border);transition:transform 0.3s var(--ease),box-shadow 0.3s var(--ease);">
        <div style="margin-bottom:1.25rem;width:48px;height:48px;border-radius:var(--radius-sm);background:{accent}18;display:flex;align-items:center;justify-content:center;">
          {get_icon(item.get('icon_hint',''))}
        </div>
        <h3 style="font-size:1.125rem;margin-bottom:0.5rem;">{item.get('title','Feature')}</h3>
        <p style="font-size:0.9375rem;color:var(--muted);line-height:1.65;">{item.get('description','')}</p>
      </div>"""
        return f"""
<section id="features" style="background:var(--surface2);padding:var(--section-gap) 0;">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3rem;">
      <span class="section-label">Features</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading" style="margin:0 auto;">{subheading}</p>' if subheading else ''}
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:1.5rem;">
      {cards_html}
    </div>
  </div>
</section>"""
    else:
        # Standard grid
        cards_html = ""
        for i, item in enumerate(items[:6]):
            cards_html += f"""
      <div class="card reveal reveal-delay-{min(i+1,4)}" style="padding:2rem;border-radius:var(--radius);background:var(--surface);border:var(--border-width) solid var(--border);transition:transform 0.3s var(--ease),box-shadow 0.3s var(--ease);">
        <div style="margin-bottom:1.25rem;width:48px;height:48px;border-radius:var(--radius-sm);background:{accent}18;display:flex;align-items:center;justify-content:center;">
          {get_icon(item.get('icon_hint',''))}
        </div>
        <h3 style="font-size:1.125rem;margin-bottom:0.5rem;font-family:var(--font-heading);">{item.get('title','Feature')}</h3>
        <p style="font-size:0.9375rem;color:var(--muted);line-height:1.65;">{item.get('description','')}</p>
      </div>"""

        grid_cols = f"repeat({min(cols,3)},1fr)"
        return f"""
<section id="features">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">Features</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading" style="margin:0 auto;">{subheading}</p>' if subheading else ''}
    </div>
    <div style="display:grid;grid-template-columns:{grid_cols};gap:1.5rem;">
      {cards_html}
    </div>
  </div>
</section>"""


def _render_social_proof(section_config: dict, copy_data: dict, design: dict) -> str:
    """Logo bar / stats strip."""
    social_proof = copy_data.get("social_proof", {})
    stats = social_proof.get("stats", [])
    headline = social_proof.get("headline", "Trusted by growing businesses")
    colors = design.get("colors", {})
    primary = colors.get("primary", "#1a1a2e")
    muted = colors.get("muted", "#6b7280")
    ui_style = design.get("ui_style", "minimal")

    if not stats:
        stats = [
            {"value": "500+", "label": "Clients Served"},
            {"value": "98%", "label": "Satisfaction Rate"},
            {"value": "5★", "label": "Average Rating"},
            {"value": "3x", "label": "Average ROI"},
        ]

    stats_html = ""
    for i, stat in enumerate(stats[:5]):
        stats_html += f"""
      <div class="reveal reveal-delay-{i+1}" style="text-align:center;padding:2rem 1rem;">
        <div class="stat-value" style="font-family:var(--font-heading);font-size:clamp(2.5rem,5vw,3.5rem);font-weight:800;color:var(--primary);line-height:1;">{stat.get('value','—')}</div>
        <div style="font-size:0.875rem;color:var(--muted);margin-top:0.5rem;letter-spacing:0.05em;">{stat.get('label','')}</div>
      </div>"""

    divider_style = "border-bottom:2px solid var(--primary);" if ui_style == "brutalist" else "border-bottom:1px solid var(--border);"

    return f"""
<section id="social-proof" style="padding:3rem 0;{divider_style}border-top:1px solid var(--border);">
  <div class="container">
    <p class="reveal" style="text-align:center;font-size:0.875rem;color:var(--muted);letter-spacing:0.08em;text-transform:uppercase;margin-bottom:2rem;">{headline}</p>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0;border-left:1px solid var(--border);">
      {stats_html}
    </div>
  </div>
</section>"""


def _render_how_it_works(section_config: dict, section_copy: dict, design: dict) -> str:
    heading = section_copy.get("heading", "How It Works")
    subheading = section_copy.get("subheading", "")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")
    primary = colors.get("primary", "#1a1a2e")

    if not items:
        items = [
            {"title": "Share Your Goals", "description": "Tell us about your business and what you want to achieve.", "icon_hint": "chat"},
            {"title": "We Get to Work", "description": "Our team crafts a tailored solution just for you.", "icon_hint": "bolt"},
            {"title": "See Results", "description": "Watch your business grow with measurable outcomes.", "icon_hint": "chart"},
        ]

    steps_html = ""
    for i, item in enumerate(items[:5]):
        num = i + 1
        steps_html += f"""
      <div class="reveal reveal-delay-{min(num,4)}" style="display:flex;gap:1.5rem;align-items:flex-start;">
        <div style="flex-shrink:0;width:48px;height:48px;border-radius:50%;background:var(--accent);color:#fff;display:flex;align-items:center;justify-content:center;font-family:var(--font-heading);font-weight:800;font-size:1.125rem;">{num}</div>
        <div style="padding-top:0.5rem;">
          <h3 style="font-size:1.125rem;margin-bottom:0.5rem;font-family:var(--font-heading);">{item.get('title','Step')}</h3>
          <p style="color:var(--muted);line-height:1.65;">{item.get('description','')}</p>
        </div>
      </div>"""

    return f"""
<section id="how-it-works" style="background:var(--surface2);">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">Process</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading" style="margin:0 auto;">{subheading}</p>' if subheading else ''}
    </div>
    <div style="display:grid;grid-template-columns:1fr;gap:2.5rem;max-width:600px;margin:0 auto;">
      {steps_html}
    </div>
  </div>
</section>"""


def _render_testimonials(section_config: dict, copy_data: dict, design: dict) -> str:
    social_proof = copy_data.get("social_proof", {})
    testimonials = social_proof.get("testimonials", [])
    heading = social_proof.get("headline", "What Our Clients Say")
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")
    ui_style = design.get("ui_style", "minimal")

    if not testimonials:
        testimonials = [
            {"quote": "Working with this team completely transformed how we approach our business. The results exceeded every expectation.", "author": "Alex M.", "role": "CEO, Acme Corp"},
            {"quote": "The attention to detail and strategic thinking they bring is unmatched. Highly recommend.", "author": "Sarah K.", "role": "Marketing Director"},
            {"quote": "We saw 3x growth in the first quarter alone. This was the best investment we made.", "author": "James L.", "role": "Founder"},
        ]

    cards_html = ""
    for i, t in enumerate(testimonials[:4]):
        cards_html += f"""
      <div class="card reveal reveal-delay-{min(i+1,4)}" style="padding:2rem;border-radius:var(--radius);background:var(--surface);border:var(--border-width) solid var(--border);">
        <div style="color:{accent};font-size:1.5rem;margin-bottom:1rem;line-height:1;">"</div>
        <p style="font-size:0.9375rem;line-height:1.75;color:var(--text);margin-bottom:1.5rem;font-style:italic;">{t.get('quote','')}</p>
        <div style="display:flex;align-items:center;gap:0.75rem;">
          <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,{accent}44,{accent}88);display:flex;align-items:center;justify-content:center;font-family:var(--font-heading);font-weight:700;font-size:0.875rem;color:#fff;">{t.get('author','A')[0]}</div>
          <div>
            <div style="font-weight:600;font-size:0.875rem;">{t.get('author','')}</div>
            <div style="font-size:0.8125rem;color:var(--muted);">{t.get('role','')}</div>
          </div>
        </div>
      </div>"""

    cols = min(len(testimonials), 3)
    return f"""
<section id="testimonials" style="background:var(--surface2);">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">Testimonials</span>
      <h2 class="section-heading">{heading}</h2>
    </div>
    <div style="display:grid;grid-template-columns:repeat({cols},1fr);gap:1.5rem;">
      {cards_html}
    </div>
  </div>
</section>"""


def _render_cta(section_config: dict, copy_data: dict, design: dict) -> str:
    cta_primary = copy_data.get("cta_primary", {"text": "Get Started", "action": "#"})
    cta_secondary = copy_data.get("cta_secondary", {"text": "Learn More", "action": "#"})
    headline = copy_data.get("headline", "Ready to get started?")
    colors = design.get("colors", {})
    primary = colors.get("primary", "#1a1a2e")
    accent = colors.get("accent", "#e94560")
    bg = colors.get("background", "#ffffff")
    ui_style = design.get("ui_style", "minimal")

    # Find a CTA section copy if it exists
    for sec in copy_data.get("sections", []):
        if sec.get("type") in ("cta", "call_to_action"):
            headline = sec.get("heading", headline)
            break

    if ui_style in ("glassmorphic", "futuristic", "technical", "cinematic"):
        cta_bg = f"background:linear-gradient(135deg,{primary} 0%,{accent}cc 100%);"
        text_style = "color:#fff;"
        sub_style = "color:rgba(255,255,255,0.75);"
        btn_style = "background:#fff;color:var(--primary);border-color:#fff;"
        btn_hover = ""
    elif ui_style == "luxury":
        cta_bg = f"background:var(--primary);"
        text_style = "color:var(--bg);"
        sub_style = "color:rgba(255,255,255,0.6);"
        btn_style = "background:var(--accent);color:#fff;border-color:var(--accent);"
        btn_hover = ""
    elif ui_style == "brutalist":
        cta_bg = f"background:var(--accent);"
        text_style = "color:#fff;"
        sub_style = "color:rgba(255,255,255,0.8);"
        btn_style = "background:#fff;color:var(--accent);border:2px solid #fff;box-shadow:4px 4px 0 var(--primary);"
        btn_hover = ""
    else:
        cta_bg = f"background:linear-gradient(135deg,{primary}ee 0%,{accent}cc 100%);"
        text_style = "color:#fff;"
        sub_style = "color:rgba(255,255,255,0.75);"
        btn_style = "background:#fff;color:var(--primary);border-color:#fff;"
        btn_hover = ""

    subheadline = copy_data.get("subheadline", "")
    cta_subtext = f"<p class='reveal reveal-delay-2' style='font-size:1.0625rem;margin-bottom:2rem;{sub_style}'>{subheadline[:120] if subheadline else 'Join hundreds of satisfied customers today.'}</p>"

    return f"""
<section id="cta" class="reveal" style="{cta_bg}border-radius:var(--radius);margin:var(--section-gap) auto;max-width:calc(var(--container-max) - 4rem);padding:5rem 3rem;text-align:center;position:relative;overflow:hidden;">
  <div style="position:relative;z-index:1;">
    <h2 class="reveal" style="font-size:clamp(2rem,4vw,3rem);margin-bottom:1rem;{text_style}">{headline}</h2>
    {cta_subtext}
    <div class="reveal reveal-delay-3" style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;">
      <a href="{cta_primary.get('action','#')}" class="btn" style="{btn_style}padding:1rem 2.5rem;font-size:1rem;">{cta_primary.get('text','Get Started')}</a>
      <a href="{cta_secondary.get('action','#')}" class="btn" style="background:transparent;color:#fff;border-color:rgba(255,255,255,0.4);padding:1rem 2.5rem;">{cta_secondary.get('text','Learn More')}</a>
    </div>
  </div>
</section>"""


def _render_about(section_config: dict, section_copy: dict, design: dict, business_name: str) -> str:
    heading = section_copy.get("heading", f"About {business_name}")
    body = section_copy.get("body", "")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")

    items_html = ""
    for item in items[:4]:
        items_html += f"""
        <div style="display:flex;gap:0.75rem;align-items:flex-start;margin-bottom:1rem;">
          <div style="flex-shrink:0;width:20px;height:20px;border-radius:50%;background:{accent};display:flex;align-items:center;justify-content:center;margin-top:2px;">
            <svg width="10" height="10" fill="none" stroke="#fff" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
          </div>
          <div>
            <strong style="font-size:0.9375rem;">{item.get('title','')}</strong>
            <p style="font-size:0.875rem;color:var(--muted);margin-top:0.25rem;">{item.get('description','')}</p>
          </div>
        </div>"""

    return f"""
<section id="about">
  <div class="container">
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:5rem;align-items:center;">
      <div class="reveal">
        <span class="section-label">About Us</span>
        <h2 class="section-heading">{heading}</h2>
        {f'<p style="color:var(--muted);line-height:1.75;margin-bottom:2rem;">{body}</p>' if body else ''}
        {items_html}
      </div>
      <div class="reveal reveal-delay-2">
        <div style="aspect-ratio:1;background:linear-gradient(135deg,{accent}18,{accent}08);border-radius:var(--radius);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="80" height="80" rx="16" fill="{accent}" opacity="0.1"/>
            <circle cx="40" cy="32" r="14" fill="{accent}" opacity="0.3"/>
            <path d="M16 64c0-13.3 10.7-24 24-24s24 10.7 24 24" fill="{accent}" opacity="0.2"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</section>"""


def _render_pricing(section_config: dict, section_copy: dict, design: dict, copy_data: dict) -> str:
    heading = section_copy.get("heading", "Simple, Transparent Pricing")
    subheading = section_copy.get("subheading", "")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")
    primary = colors.get("primary", "#1a1a2e")
    cta_text = copy_data.get("cta_primary", {}).get("text", "Get Started")

    if not items:
        items = [
            {"title": "Starter", "description": "Perfect for getting started. Essential features to launch your presence.", "icon_hint": "star"},
            {"title": "Professional", "description": "Everything you need to grow. Advanced features for serious businesses.", "icon_hint": "bolt"},
            {"title": "Enterprise", "description": "Custom solutions for large organizations with dedicated support.", "icon_hint": "shield"},
        ]

    cards_html = ""
    for i, item in enumerate(items[:3]):
        is_featured = i == 1 or len(items) == 1
        feat_style = f"background:var(--primary);color:#fff;border-color:var(--primary);transform:scale(1.02);" if is_featured else ""
        text_muted = "color:rgba(255,255,255,0.7);" if is_featured else "color:var(--muted);"
        feat_label = f'<div style="font-size:0.75rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{accent};background:{accent}22;padding:0.25rem 0.75rem;border-radius:100px;display:inline-block;margin-bottom:1rem;">Most Popular</div>' if is_featured else ""

        cards_html += f"""
      <div class="card reveal reveal-delay-{i+1}" style="padding:2.5rem;border-radius:var(--radius);border:var(--border-width) solid var(--border);{feat_style}transition:transform 0.3s var(--ease),box-shadow 0.3s var(--ease);">
        {feat_label}
        <h3 style="font-size:1.375rem;margin-bottom:0.5rem;font-family:var(--font-heading);">{item.get('title','Plan')}</h3>
        <p style="font-size:0.9375rem;line-height:1.65;margin-bottom:2rem;{text_muted}">{item.get('description','')}</p>
        <a href="#" class="btn {'btn-primary' if not is_featured else ''}" style="{'background:#fff;color:var(--primary);border-color:#fff;width:100%;justify-content:center;' if is_featured else 'width:100%;justify-content:center;'}">{cta_text}</a>
      </div>"""

    return f"""
<section id="pricing">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">Pricing</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading" style="margin:0 auto;">{subheading}</p>' if subheading else ''}
    </div>
    <div style="display:grid;grid-template-columns:repeat({min(len(items),3)},1fr);gap:1.5rem;align-items:center;">
      {cards_html}
    </div>
  </div>
</section>"""


def _render_faq(section_config: dict, section_copy: dict, design: dict) -> str:
    heading = section_copy.get("heading", "Frequently Asked Questions")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")

    if not items:
        items = [
            {"title": "How does it work?", "description": "Simply sign up, share your requirements, and we handle the rest."},
            {"title": "What is included?", "description": "Everything you need to get started, with no hidden fees or surprises."},
            {"title": "Can I get a refund?", "description": "We offer a 30-day satisfaction guarantee. No questions asked."},
            {"title": "Do you offer support?", "description": "Yes, our team is available 7 days a week via email and live chat."},
        ]

    items_html = ""
    for i, item in enumerate(items[:8]):
        items_html += f"""
      <details class="reveal reveal-delay-{min(i+1,4)}" style="border-bottom:var(--border-width) solid var(--border);padding:1.5rem 0;" open="{'' if i > 0 else 'true'}">
        <summary style="font-size:1rem;font-weight:600;cursor:pointer;list-style:none;display:flex;justify-content:space-between;align-items:center;user-select:none;">
          {item.get('title','Question')}
          <svg width="18" height="18" fill="none" stroke="{accent}" stroke-width="2" viewBox="0 0 24 24" style="flex-shrink:0;transition:transform 0.3s;"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>
        </summary>
        <p style="font-size:0.9375rem;color:var(--muted);line-height:1.7;margin-top:1rem;">{item.get('description','')}</p>
      </details>"""

    return f"""
<section id="faq" style="background:var(--surface2);">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">FAQ</span>
      <h2 class="section-heading">{heading}</h2>
    </div>
    <div style="max-width:720px;margin:0 auto;">
      {items_html}
    </div>
  </div>
</section>"""


def _render_problem_solution(section_config: dict, section_copy: dict, design: dict) -> str:
    heading = section_copy.get("heading", "The Problem We Solve")
    body = section_copy.get("body", "")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")
    primary = colors.get("primary", "#1a1a2e")

    half = len(items) // 2
    problems = items[:half] if half > 0 else items[:2]
    solutions = items[half:] if half > 0 else items[2:]

    def make_list(lst, color, label):
        html = f'<h3 style="font-size:1rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:{color};margin-bottom:1.5rem;">{label}</h3>'
        for item in lst:
            html += f'<div style="display:flex;gap:0.75rem;margin-bottom:1rem;"><span style="color:{color};font-size:1.25rem;line-height:1;">{"✕" if label == "BEFORE" else "✓"}</span><div><strong style="font-size:0.9375rem;">{item.get("title","")}</strong><p style="font-size:0.875rem;color:var(--muted);margin-top:0.25rem;">{item.get("description","")}</p></div></div>'
        return html

    before_html = make_list(problems or [{"title": "Wasted time on manual tasks", "description": "Hours lost on repetitive work that should be automated."}, {"title": "Scattered tools and data", "description": "No single source of truth, leading to costly mistakes."}], "#ef4444", "BEFORE")
    after_html = make_list(solutions or [{"title": "Automated workflows", "description": "Save hours every week with intelligent automation."}, {"title": "Unified dashboard", "description": "Everything in one place, always up to date."}], "#22c55e", "AFTER")

    return f"""
<section id="problem-solution">
  <div class="container">
    <div class="reveal" style="text-align:center;margin-bottom:3.5rem;">
      <span class="section-label">The Shift</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading" style="margin:0 auto;">{body[:200] if body else ""}</p>' if body else ''}
    </div>
    <div style="display:grid;grid-template-columns:1fr auto 1fr;gap:2rem;align-items:start;">
      <div class="reveal" style="background:rgba(239,68,68,0.04);border:1px solid rgba(239,68,68,0.12);border-radius:var(--radius);padding:2.5rem;">
        {before_html}
      </div>
      <div style="display:flex;align-items:center;padding-top:4rem;">
        <div style="width:48px;height:48px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;">
          <svg width="20" height="20" fill="#fff" viewBox="0 0 24 24"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
        </div>
      </div>
      <div class="reveal reveal-delay-2" style="background:rgba(34,197,94,0.04);border:1px solid rgba(34,197,94,0.12);border-radius:var(--radius);padding:2.5rem;">
        {after_html}
      </div>
    </div>
  </div>
</section>"""


def _render_footer(copy_data: dict, design: dict, business_name: str) -> str:
    footer = copy_data.get("footer", {})
    tagline = footer.get("tagline", business_name)
    cta = footer.get("cta", "Get in touch")
    cta_primary = copy_data.get("cta_primary", {"text": "Get Started", "action": "#"})
    colors = design.get("colors", {})
    primary = colors.get("primary", "#1a1a2e")
    bg = colors.get("background", "#ffffff")
    ui_style = design.get("ui_style", "minimal")
    color_mode = design.get("color_mode", "light")

    footer_bg = primary if color_mode == "light" else "#080808"
    footer_text = "#f9f9f9"
    footer_muted = "rgba(249,249,249,0.55)"

    if ui_style == "brutalist":
        return f"""
<footer style="background:{footer_bg};color:{footer_text};padding:3rem 0;border-top:2px solid var(--accent);">
  <div class="container">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:2rem;flex-wrap:wrap;">
      <div>
        <div style="font-family:var(--font-heading);font-size:1.375rem;font-weight:800;margin-bottom:0.5rem;">{business_name}</div>
        <p style="font-size:0.875rem;color:{footer_muted};">{tagline}</p>
      </div>
      <a href="{cta_primary.get('action','#')}" class="btn" style="background:var(--accent);color:#fff;border-color:var(--accent);box-shadow:4px 4px 0 #fff;">{cta}</a>
    </div>
    <div style="margin-top:2rem;padding-top:2rem;border-top:1px solid rgba(255,255,255,0.1);font-size:0.8125rem;color:{footer_muted};">
      © {_get_year()} {business_name}. All rights reserved.
    </div>
  </div>
</footer>"""
    else:
        return f"""
<footer style="background:{footer_bg};color:{footer_text};padding:5rem 0 3rem;">
  <div class="container">
    <div style="display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:4rem;margin-bottom:4rem;">
      <div>
        <div style="font-family:var(--font-heading);font-size:1.5rem;font-weight:700;margin-bottom:1rem;">{business_name}</div>
        <p style="font-size:0.9375rem;color:{footer_muted};line-height:1.7;max-width:280px;">{tagline}</p>
      </div>
      <div>
        <h4 style="font-size:0.8125rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{footer_muted};margin-bottom:1.25rem;">Company</h4>
        <ul style="display:flex;flex-direction:column;gap:0.75rem;">
          <li><a href="#about" style="font-size:0.9375rem;color:{footer_text};opacity:0.7;transition:opacity 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">About</a></li>
          <li><a href="#features" style="font-size:0.9375rem;color:{footer_text};opacity:0.7;transition:opacity 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">Features</a></li>
          <li><a href="#testimonials" style="font-size:0.9375rem;color:{footer_text};opacity:0.7;transition:opacity 0.2s;" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'">Testimonials</a></li>
        </ul>
      </div>
      <div>
        <h4 style="font-size:0.8125rem;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{footer_muted};margin-bottom:1.25rem;">Get Started</h4>
        <a href="{cta_primary.get('action','#')}" class="btn btn-primary" style="margin-bottom:1rem;display:inline-flex;">{cta}</a>
      </div>
    </div>
    <div style="padding-top:2rem;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;">
      <span style="font-size:0.8125rem;color:{footer_muted};">© {_get_year()} {business_name}. All rights reserved.</span>
    </div>
  </div>
</footer>"""


def _get_year() -> int:
    import datetime
    return datetime.date.today().year


# ── Section dispatcher ─────────────────────────────────────────────────────────

def _render_section(section_config: dict, copy_data: dict, design: dict, business_name: str) -> str:
    section_type = section_config.get("type", "")

    # Find matching copy section
    section_copy = {}
    for cs in copy_data.get("sections", []):
        if isinstance(cs, dict) and cs.get("type") == section_type:
            section_copy = cs
            break
    # Fallback: match by loose keyword
    if not section_copy:
        for cs in copy_data.get("sections", []):
            if isinstance(cs, dict) and section_type in cs.get("type", "").lower():
                section_copy = cs
                break

    if section_type == "hero":
        return _render_hero(section_config, copy_data, design)
    elif section_type == "features":
        return _render_features(section_config, section_copy, design)
    elif section_type == "social_proof":
        return _render_social_proof(section_config, copy_data, design)
    elif section_type in ("testimonials", "reviews"):
        return _render_testimonials(section_config, copy_data, design)
    elif section_type == "how_it_works":
        return _render_how_it_works(section_config, section_copy, design)
    elif section_type in ("cta", "call_to_action"):
        return _render_cta(section_config, copy_data, design)
    elif section_type == "about":
        return _render_about(section_config, section_copy, design, business_name)
    elif section_type == "pricing":
        return _render_pricing(section_config, section_copy, design, copy_data)
    elif section_type == "faq":
        return _render_faq(section_config, section_copy, design)
    elif section_type == "problem_solution":
        return _render_problem_solution(section_config, section_copy, design)
    elif section_type == "footer":
        return _render_footer(copy_data, design, business_name)
    else:
        # Generic section fallback
        return _render_generic_section(section_config, section_copy, design)


def _render_generic_section(section_config: dict, section_copy: dict, design: dict) -> str:
    """Fallback for unknown section types."""
    heading = section_copy.get("heading", section_config.get("name", "Section"))
    subheading = section_copy.get("subheading", "")
    body = section_copy.get("body", "")
    items = section_copy.get("items", [])
    colors = design.get("colors", {})
    accent = colors.get("accent", "#e94560")

    items_html = ""
    for item in items[:6]:
        items_html += f"""
      <div class="card reveal" style="padding:1.5rem;border-radius:var(--radius);background:var(--surface);border:var(--border-width) solid var(--border);">
        <h3 style="font-size:1rem;margin-bottom:0.5rem;">{item.get('title','')}</h3>
        <p style="font-size:0.875rem;color:var(--muted);">{item.get('description','')}</p>
      </div>"""

    return f"""
<section>
  <div class="container">
    <div class="reveal" style="{'text-align:center;' if not items else ''}margin-bottom:{'3rem' if items else '0'};">
      <span class="section-label">{section_config.get('type','').replace('_',' ').title()}</span>
      <h2 class="section-heading">{heading}</h2>
      {f'<p class="section-subheading">{subheading}</p>' if subheading else ''}
      {f'<p style="color:var(--muted);line-height:1.75;margin-top:1rem;">{body}</p>' if body else ''}
    </div>
    {f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1.5rem;">{items_html}</div>' if items else ''}
  </div>
</section>"""


# ── JavaScript ─────────────────────────────────────────────────────────────────

def _build_js(design: dict) -> str:
    animations = design.get("animations", {})
    scroll_reveal = animations.get("scroll_reveal", True)

    scroll_js = """
// Scroll reveal
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.classList.add('visible');
        }
    });
}, { threshold: 0.1, rootMargin: '0px 0px -60px 0px' });
document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
""" if scroll_reveal else ""

    return f"""
<script>
document.addEventListener('DOMContentLoaded', function() {{
{scroll_js}
    // Nav scroll effect
    const nav = document.getElementById('nav');
    if (nav) {{
        window.addEventListener('scroll', function() {{
            if (window.scrollY > 50) {{
                nav.style.background = 'rgba(255,255,255,0.97)';
                nav.style.boxShadow = '0 1px 20px rgba(0,0,0,0.08)';
            }} else {{
                nav.style.background = '';
                nav.style.boxShadow = '';
            }}
        }}, {{ passive: true }});
    }}

    // FAQ accordion icon rotation
    document.querySelectorAll('details').forEach(details => {{
        const icon = details.querySelector('svg');
        details.addEventListener('toggle', function() {{
            if (icon) icon.style.transform = this.open ? 'rotate(180deg)' : '';
        }});
    }});
}});
</script>"""


# ── Main HTML assembler ────────────────────────────────────────────────────────

def generate_html(
    design_decisions: dict[str, Any],
    copy_data: dict[str, Any],
    research_data: dict[str, Any],
) -> str:
    """Build a complete, self-contained HTML landing page.

    Args:
        design_decisions: Output from design_synthesizer — fonts, colors, sections, ui_style, etc.
        copy_data: Output from copy_generator — headline, subheadline, CTAs, sections, social_proof, meta
        research_data: Business research data — business_name, industry, etc.

    Returns:
        Complete HTML string (single self-contained file).
    """
    business_name = research_data.get("business_name") or design_decisions.get("business_name", "Your Business")
    meta = copy_data.get("meta", {})
    page_title = meta.get("page_title") or f"{business_name} — Official Website"
    meta_description = meta.get("meta_description") or f"Discover {business_name}."
    og_title = meta.get("og_title") or page_title
    og_description = meta.get("og_description") or meta_description

    business_url = research_data.get("business_url") or "#"
    og_image = ""  # No image generation in this step

    fonts = design_decisions.get("fonts", {})
    google_fonts_url = _build_google_fonts_url(fonts)
    colors = design_decisions.get("colors", {})
    bg = colors.get("background", "#ffffff")

    css_vars = _build_css_variables(design_decisions, copy_data)
    base_css = _build_base_css(design_decisions)
    style_css = _build_style_css(design_decisions)

    nav_html = _build_nav(design_decisions, copy_data, business_name)

    # Render sections
    sections_config = design_decisions.get("sections", [])
    if not sections_config:
        sections_config = [
            {"type": "hero", "name": "Hero", "layout": "centered"},
            {"type": "social_proof", "name": "Social Proof", "layout": "stats"},
            {"type": "features", "name": "Features", "layout": "grid"},
            {"type": "testimonials", "name": "Testimonials", "layout": "cards"},
            {"type": "cta", "name": "CTA", "layout": "centered"},
        ]

    sections_html = ""
    has_footer = any(s.get("type") == "footer" for s in sections_config)
    for sec in sections_config:
        if not isinstance(sec, dict):
            continue
        sections_html += _render_section(sec, copy_data, design_decisions, business_name)

    if not has_footer:
        sections_html += _render_footer(copy_data, design_decisions, business_name)

    js_html = _build_js(design_decisions)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape(page_title)}</title>
  <meta name="description" content="{_escape(meta_description)}">
  <!-- OG / Social -->
  <meta property="og:type" content="website">
  <meta property="og:title" content="{_escape(og_title)}">
  <meta property="og:description" content="{_escape(og_description)}">
  <meta property="og:url" content="{_escape(business_url)}">
  {'<meta property="og:image" content="' + _escape(og_image) + '">' if og_image else ''}
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_escape(og_title)}">
  <meta name="twitter:description" content="{_escape(og_description)}">
  <!-- Canonical -->
  <link rel="canonical" href="{_escape(business_url)}">
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{google_fonts_url}" rel="stylesheet">
  <style>
{css_vars}
{base_css}
{style_css}

/* ── Mobile responsive overrides ── */
@media (max-width: 900px) {{
  #hero > .container > div[style*="grid-template-columns:1fr 1fr"] {{
    grid-template-columns: 1fr !important;
  }}
  #about .container > div[style*="grid-template-columns:1fr 1fr"] {{
    grid-template-columns: 1fr !important;
  }}
  #problem-solution .container > div[style*="grid-template-columns:1fr auto 1fr"] {{
    grid-template-columns: 1fr !important;
  }}
  footer .container > div[style*="grid-template-columns"] {{
    grid-template-columns: 1fr !important;
  }}
}}

@media (max-width: 768px) {{
  #features .container > div[style*="grid-template-columns"] {{
    grid-template-columns: 1fr !important;
  }}
  #testimonials .container > div[style*="grid-template-columns"] {{
    grid-template-columns: 1fr !important;
  }}
  #pricing .container > div[style*="grid-template-columns"] {{
    grid-template-columns: 1fr !important;
  }}
  #cta {{
    margin-left: 1rem !important;
    margin-right: 1rem !important;
    padding: 3rem 1.5rem !important;
  }}
}}
  </style>
</head>
<body style="background-color:{bg};">

{nav_html}

<main>
{sections_html}
</main>

{js_html}

</body>
</html>"""

    return html


def _escape(s: str) -> str:
    """Escape HTML special chars for use in attribute values."""
    return (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


# ── File persistence + DB update ───────────────────────────────────────────────

async def save_html_and_update_db(
    page_id: str | UUID,
    html: str,
    pool=None,
) -> tuple[str, str]:
    """Save HTML to disk and update landing_pages record.

    Args:
        page_id: UUID of the landing page record
        html: Complete HTML string
        pool: Optional asyncpg pool (if not provided, uses get_pool())

    Returns:
        (html_path, preview_url) tuple
    """
    import sys
    sys.path.insert(0, "/home/web3relic/otto")

    page_id_str = str(page_id)

    # Save file
    page_dir = WEBASSIST_DIR / page_id_str
    page_dir.mkdir(parents=True, exist_ok=True)
    html_file = page_dir / "index.html"
    html_file.write_text(html, encoding="utf-8")
    html_path = str(html_file)
    preview_url = f"{BASE_URL}/{page_id_str}"

    log.info(f"HTML saved: {html_path} ({len(html):,} bytes)")

    # Update DB
    if pool is None:
        from memory.db import get_pool
        pool = await get_pool()

    await pool.execute(
        """
        UPDATE landing_pages
        SET html_path = $1, preview_url = $2, status = 'review', updated_at = NOW()
        WHERE id = $3::uuid
        """,
        html_path,
        preview_url,
        page_id_str,
    )

    log.info(f"DB updated: landing_pages[{page_id_str}] → status=review, preview_url={preview_url}")
    return html_path, preview_url


async def generate_and_save(
    page_id: str | UUID,
    design_decisions: dict[str, Any],
    copy_data: dict[str, Any],
    research_data: dict[str, Any],
    pool=None,
) -> dict[str, Any]:
    """Full pipeline: generate HTML, save file, update DB.

    Args:
        page_id: UUID of landing_pages record
        design_decisions: From design_synthesizer()
        copy_data: From copy_generator()
        research_data: Business research dict
        pool: Optional asyncpg pool

    Returns:
        {"html_path": str, "preview_url": str, "size_bytes": int, "status": "review"}
    """
    log.info(f"Starting HTML generation for page {page_id}")

    html = generate_html(design_decisions, copy_data, research_data)
    html_path, preview_url = await save_html_and_update_db(page_id, html, pool)

    return {
        "html_path": html_path,
        "preview_url": preview_url,
        "size_bytes": len(html.encode("utf-8")),
        "status": "review",
    }

"""Landing page generation via Claude Code CLI.

The creative direction lives in system_prompt.md (injected via
--append-system-prompt-file). The user prompt is just the business brief
and output path. A separate QA pass validates the result.
"""

import asyncio
import logging
import os
from pathlib import Path
from uuid import UUID

log = logging.getLogger("otto.agent_generator")

WEBASSIST_DIR = Path("/var/www/webassist")
BASE_URL = "https://webassist.otto.lk"
SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"


def _build_prompt(
    page_id: UUID,
    business_name: str,
    business_url: str,
    description: str,
    target_audience: str,
    output_subdir: str = "",
    design_md: str = "",
) -> str:
    base = WEBASSIST_DIR / str(page_id)
    output_dir = base / output_subdir if output_subdir else base
    output_path = output_dir / "index.html"
    preview_url = f"{BASE_URL}/{page_id}/{output_subdir}" if output_subdir else f"{BASE_URL}/{page_id}"

    design_section = ""
    if design_md:
        design_section = f"""
## DESIGN SYSTEM (MANDATORY — follow this exactly)

{design_md}

You MUST follow the design system above. Use the exact colors, fonts, spacing,
component styles, and layout principles specified. This is your creative brief —
do NOT deviate from these specifications. The design system IS your sensory DNA,
style direction, and visual identity. Skip Steps A-E of the system prompt and
go straight to building based on this design system.
"""

    return f"""Build a landing page for "{business_name}".
{design_section}
## BUSINESS INFO
- Name: {business_name}
- URL: {business_url or 'N/A'}
- Description: {description or 'N/A'}
- Target audience: {target_audience or 'N/A'}

## INSTRUCTIONS
{'''Follow your system prompt end-to-end. Run through sensory translation, style fitness,
experiential design, and signature moment. Generate 2-3 concept proposals internally,
pick the strongest one yourself, and build it — do NOT wait for user input.''' if not design_md else '''The design system above is your complete creative direction. Implement it faithfully.
Focus on translating the design system into pixel-perfect HTML/CSS.'''}

## COPY RULES
- Hero headline: punchy, specific, benefit-driven, max 10 words. NOT "Welcome to {business_name}".
- Subheadline: expand the benefit, max 25 words.
- CTAs: action-oriented and specific to THIS business. NOT generic "Learn More" or "Get Started".
- Stats/metrics: always include specific plausible numbers (e.g. "500+ Clients", "98% Satisfaction").
- Write real testimonials with names and roles.
- No "Lorem ipsum", no "Coming soon", no empty placeholder text anywhere.

## OUTPUT
- Canonical URL: {preview_url}
{f'- Primary CTA links to: {business_url}' if business_url else '- Primary CTA links to: #contact'}
- Output path: {output_path}
- First run: mkdir -p {output_dir}
- Write the file, then verify it exists and is larger than 5KB.
"""


def _build_qa_prompt(page_id: UUID, business_name: str, output_subdir: str = "") -> str:
    base = WEBASSIST_DIR / str(page_id)
    html_path = (base / output_subdir / "index.html") if output_subdir else (base / "index.html")

    return f"""You are doing a QA review of a generated landing page for "{business_name}".

Read the HTML file at {html_path} and check ALL of the following:

## FUNCTIONAL CHECKS
1. The file is a valid, complete HTML document (<!DOCTYPE html>, <html>, <head>, <body>)
2. Has <meta name="viewport" content="width=device-width, initial-scale=1.0">
3. Has <title> tag with the business name
4. Has <meta name="description"> with real content
5. Has Open Graph tags (og:title, og:description, og:url)
6. Google Fonts are loaded via <link> tags (check the href contains fonts.googleapis.com)
7. All CSS is inline in <style> tags (no external stylesheet links)
8. All JS is inline in <script> tags (no external script src)

## RESPONSIVE CHECKS
9. Has at least 2 @media queries for different breakpoints
10. No fixed pixel widths on containers that would break on mobile (look for width: 1200px etc without max-width)
11. Font sizes use responsive units or have media query overrides for mobile

## CONTENT CHECKS
12. No "Lorem ipsum" or placeholder text anywhere
13. No "Coming soon" or empty sections
14. No empty <h1>, <h2>, <h3> tags
15. No sections with heading "None" or "undefined"
16. Stats/metrics sections have actual numbers (not empty)
17. Navigation has real anchor links that match section IDs
18. Footer has actual content (company name, links, copyright)

## DESIGN QUALITY CHECKS
19. Not using banned fonts: Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, Space Grotesk (check the Google Fonts link AND the CSS font-family declarations)
20. Has scroll-triggered animations (IntersectionObserver or similar)
21. Has a skip-to-content accessibility link
22. Has prefers-reduced-motion media query
23. Color palette is consistent (not mixing random colors)

## FIX ANY ISSUES
If you find problems, fix them directly in the file using the Edit tool.
After fixing, verify the file is still valid HTML and larger than 10KB.

Report what you found and what you fixed (if anything). Be brief.
"""


async def _run_agent(cmd: list, page_id: UUID, label: str, env: dict, timeout: int) -> tuple:
    """Run a Claude Code CLI subprocess and return (stdout, stderr, exit_code)."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/web3relic/otto",
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        log.info("[%s:%s] Exited code=%s", label, page_id, proc.returncode)
        if proc.returncode != 0:
            log.warning("[%s:%s] stderr: %s", label, page_id, stderr[-2000:].decode(errors="replace"))
        return stdout, stderr, proc.returncode

    except asyncio.TimeoutError:
        log.warning("[%s:%s] Timed out after %ds", label, page_id, timeout)
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        await asyncio.sleep(3)
        return b"", b"", -1

    except Exception as exc:
        log.exception("[%s:%s] Failed: %s", label, page_id, exc)
        raise RuntimeError(f"{label} failed: {exc}")


async def generate_with_agent(
    page_id: UUID,
    business_name: str,
    business_url: str = "",
    description: str = "",
    target_audience: str = "",
    pool=None,
    output_subdir: str = "",
    design_md: str = "",
) -> dict:
    """Generate a landing page by spawning a Claude Code session, then QA it."""
    base_dir = WEBASSIST_DIR / str(page_id)
    output_dir = base_dir / output_subdir if output_subdir else base_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"

    env = {**os.environ, "HOME": "/home/web3relic"}

    # ── Generation pass ─────────────────────────────────────────────
    prompt = _build_prompt(page_id, business_name, business_url, description, target_audience, output_subdir, design_md=design_md)

    gen_cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "20",
        "--max-budget-usd", "3",
        "--append-system-prompt-file", str(SYSTEM_PROMPT_PATH),
        "-p", prompt,
    ]

    log.info("[gen:%s] Starting generation for '%s' (subdir=%s)", page_id, business_name, output_subdir or "root")
    await _run_agent(gen_cmd, page_id, "gen", env, timeout=1500)

    # Verify generation output
    if not html_path.exists():
        raise RuntimeError("Agent did not create HTML file")

    file_size = html_path.stat().st_size
    if file_size < 10 * 1024:
        raise RuntimeError(f"HTML too small ({file_size} bytes, min 10KB)")

    log.info("[gen:%s] Generated %d bytes, starting QA", page_id, file_size)

    # ── QA pass ─────────────────────────────────────────────────────
    qa_prompt = _build_qa_prompt(page_id, business_name, output_subdir)

    qa_cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "8",
        "--max-budget-usd", "1",
        "-p", qa_prompt,
    ]

    log.info("[qa:%s] Starting QA review", page_id)
    await _run_agent(qa_cmd, page_id, "qa", env, timeout=300)

    # Final verification after QA
    if not html_path.exists():
        raise RuntimeError("HTML file missing after QA")

    file_size = html_path.stat().st_size
    if file_size < 10 * 1024:
        raise RuntimeError(f"HTML too small after QA ({file_size} bytes)")

    preview_url = f"{BASE_URL}/{page_id}/{output_subdir}" if output_subdir else f"{BASE_URL}/{page_id}"

    log.info("[done:%s] %s (%d bytes) → %s", page_id, html_path, file_size, preview_url)

    return {"html_path": str(html_path), "preview_url": preview_url, "file_size": file_size}


# ── Enrichment ──────────────────────────────────────────────────────────

def _build_enrich_prompt(
    template_html_path: str,
    copy_json: dict,
    business_name: str,
    output_path: str,
) -> str:
    import json as _json
    return f"""You are enriching a landing page template with real copy for "{business_name}".

## TEMPLATE
Read the HTML file at {template_html_path}. This is a design template with placeholder/generic copy.
The visual design (CSS, layout, colors, fonts, animations, JavaScript) is FINAL — do NOT change it.

## COPY DATA
Replace ALL text content (headlines, subheadlines, paragraphs, CTAs, testimonials, stats,
footer text, meta tags) with the real copy below:

```json
{_json.dumps(copy_json, indent=2)}
```

## RULES
- Do NOT modify any CSS, layout, colors, fonts, or JavaScript
- Do NOT add or remove HTML sections — only replace text within existing elements
- Replace the <title>, <meta description>, Open Graph, and Twitter Card tags with the meta copy
- Replace hero headline, subheadline, and CTA button text
- Replace feature titles and descriptions
- Replace testimonial quotes, author names, and roles
- Replace stat values and labels
- Replace footer tagline and CTA
- If the template has more sections than the copy data, keep the section but write appropriate copy
- If the copy data has sections the template doesn't have, skip them

## OUTPUT
Write the enriched file to: {output_path}
First run: mkdir -p {str(Path(output_path).parent)}
Verify the file exists and is larger than 5KB after writing.
"""


async def enrich_template(
    page_id: UUID,
    template_html_path: str,
    copy_json: dict,
    business_name: str,
) -> dict:
    """Enrich a design template with synthesized copy using Claude Code CLI."""
    output_dir = WEBASSIST_DIR / str(page_id)
    output_path = output_dir / "index.html"
    output_dir.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "HOME": "/home/web3relic"}

    prompt = _build_enrich_prompt(template_html_path, copy_json, business_name, str(output_path))

    cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "10",
        "--max-budget-usd", "1.5",
        "-p", prompt,
    ]

    log.info("[enrich:%s] Starting enrichment for '%s'", page_id, business_name)
    await _run_agent(cmd, page_id, "enrich", env, timeout=600)

    if not output_path.exists():
        raise RuntimeError("Enrichment did not create output file")

    file_size = output_path.stat().st_size
    if file_size < 5 * 1024:
        raise RuntimeError(f"Enriched HTML too small ({file_size} bytes, min 5KB)")

    preview_url = f"{BASE_URL}/{page_id}"
    log.info("[enrich:%s] Enriched %d bytes → %s", page_id, file_size, preview_url)

    return {"html_path": str(output_path), "preview_url": preview_url, "file_size": file_size}

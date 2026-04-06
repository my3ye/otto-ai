"""Landing page generation via Claude Code CLI.

Simple approach: give the agent the business info, point it at prompts.md,
let it read the design system and generate the HTML. Then run a QA pass
to verify quality and fix issues.
"""

import asyncio
import logging
import os
from pathlib import Path
from uuid import UUID

log = logging.getLogger("otto.agent_generator")

WEBASSIST_DIR = Path("/var/www/webassist")
BASE_URL = "https://webassist.otto.lk"
PROMPTS_PATH = Path("/mnt/media/prompts.md")


def _build_prompt(
    page_id: UUID,
    business_name: str,
    business_url: str,
    description: str,
    target_audience: str,
) -> str:
    output_dir = WEBASSIST_DIR / str(page_id)
    output_path = output_dir / "index.html"
    preview_url = f"{BASE_URL}/{page_id}"

    return f"""You are building a production landing page for "{business_name}".

## STEP 1: Read the design system

Read the file at {PROMPTS_PATH}. It contains 33 proven design systems, each starting
with a line like "DESIGN 01", "DESIGN 02", etc. Each design block contains:

- **Summary** — one-line description of the aesthetic
- **Style** — fonts, colors, gradients, effects, animation curves
- **Spec** — exact CSS values: hex colors, font weights, tracking, line-height, border-radius, transitions
- **Layout & Structure** — section-by-section breakdown: Navigation, Hero, content sections, Footer
- **Special Components** — signature UI elements unique to that design (echo stacks, shiny borders, glassmorphic cards, etc.)
- **Special Notes** — DOs and DON'Ts for that specific design

## STEP 2: Pick the best design

Choose the ONE design that best fits this business. Consider:

- **Industry fit** — a law firm needs authority (editorial/technical), a wellness brand needs warmth (soft-organic), a tech startup needs energy (brutalist/futuristic)
- **Audience match** — Gen Z prefers bold/futuristic, corporate professionals prefer minimal/editorial
- **Tone** — premium businesses need luxury aesthetics, approachable brands need clean/friendly
- **Differentiation** — avoid the most common/generic-looking designs

## STEP 3: Build the page

Follow the chosen design's spec EXACTLY. This means:

- Use the EXACT fonts specified (family, weight, tracking, line-height). Never substitute with Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, or Space Grotesk.
- Use the EXACT color palette (hex values for background, text, accent, muted). Don't default to generic blue/white.
- Implement EVERY section described in the Layout & Structure (Navigation, Hero, content sections, Footer) using the EXACT layout specified (if it says asymmetric grid, build an asymmetric grid — don't fall back to centered stacks).
- Build ALL special components described for that design (echo stacks, pill showcases, gradient blobs, shiny borders, etc.). These are what make each design unique.
- Use the EXACT animation values (easing curves, durations, transforms) — not generic ease-in-out.
- Navigation sections describe the sticky nav bar. Implement as a proper <nav> element, not as body content cards.

## BUSINESS INFO
- Name: {business_name}
- URL: {business_url or 'N/A'}
- Description: {description or 'N/A'}
- Target audience: {target_audience or 'N/A'}

## COPY RULES
- Hero headline: punchy, specific, benefit-driven, max 10 words. NOT "Welcome to {business_name}".
- Subheadline: expand the benefit, max 25 words.
- CTAs: action-oriented and specific to THIS business. NOT generic "Learn More" or "Get Started".
- For stats/metrics/counters: always include specific plausible numbers (e.g. "500+ Clients", "98% Satisfaction", "10+ Years"). Never leave empty.
- Write real testimonials with names and roles if none exist in research data.
- No "Lorem ipsum", no "Coming soon", no empty placeholder text anywhere.

## OUTPUT REQUIREMENTS
- Single self-contained HTML file — ALL CSS in <style>, ALL JS in <script>
- Google Fonts loaded via <link> — no other external dependencies
- Mobile-first responsive: 375px → 768px → 1440px breakpoints
- IntersectionObserver for scroll-triggered animations
- Full SEO: <title>, <meta description>, Open Graph, Twitter Card tags
- Accessibility: skip-to-content link, :focus-visible states, prefers-reduced-motion
- No placeholder images — use CSS gradients, geometric shapes, or SVG patterns
- Canonical URL: {preview_url}
{f'- Primary CTA links to: {business_url}' if business_url else '- Primary CTA links to: #contact'}

## WRITE THE FILE
Output path: {output_path}
First run: mkdir -p {output_dir}
Use the Write tool to create the file, then verify it exists and is larger than 5KB.
"""


def _build_qa_prompt(page_id: UUID, business_name: str) -> str:
    html_path = WEBASSIST_DIR / str(page_id) / "index.html"

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
) -> dict:
    """Generate a landing page by spawning a Claude Code session, then QA it."""
    output_dir = WEBASSIST_DIR / str(page_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"

    env = {**os.environ, "HOME": "/home/web3relic"}

    # ── Generation pass ─────────────────────────────────────────────
    prompt = _build_prompt(page_id, business_name, business_url, description, target_audience)

    gen_cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "12",
        "--max-budget-usd", "3",
        "-p", prompt,
    ]

    log.info("[gen:%s] Starting generation for '%s'", page_id, business_name)
    await _run_agent(gen_cmd, page_id, "gen", env, timeout=1500)

    # Verify generation output
    if not html_path.exists():
        raise RuntimeError("Agent did not create HTML file")

    file_size = html_path.stat().st_size
    if file_size < 10 * 1024:
        raise RuntimeError(f"HTML too small ({file_size} bytes, min 10KB)")

    log.info("[gen:%s] Generated %d bytes, starting QA", page_id, file_size)

    # ── QA pass ─────────────────────────────────────────────────────
    qa_prompt = _build_qa_prompt(page_id, business_name)

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

    preview_url = f"{BASE_URL}/{page_id}"

    if pool:
        await pool.execute(
            """UPDATE landing_pages
               SET html_path = $2, preview_url = $3, status = 'review',
                   error_text = NULL, updated_at = now()
               WHERE id = $1""",
            page_id, str(html_path), preview_url,
        )

    log.info("[done:%s] %s (%d bytes) → %s", page_id, html_path, file_size, preview_url)

    return {"html_path": str(html_path), "preview_url": preview_url, "file_size": file_size}

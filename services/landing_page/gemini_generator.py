"""Landing page generation via Gemini CLI.

Mirror of agent_generator.py but uses `gemini` CLI with
gemini-3.1-pro-preview model. Creative direction injected via
GEMINI_SYSTEM_MD env var pointing to system_prompt.md.
"""

import asyncio
import logging
import os
from pathlib import Path
from uuid import UUID

log = logging.getLogger("otto.gemini_generator")

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
    """Run a Gemini CLI subprocess and return (stdout, stderr, exit_code)."""
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


async def generate_with_gemini(
    page_id: UUID,
    business_name: str,
    business_url: str = "",
    description: str = "",
    target_audience: str = "",
    pool=None,
    output_subdir: str = "",
    design_md: str = "",
) -> dict:
    """Generate a landing page by spawning a Gemini CLI session, then QA it."""
    base_dir = WEBASSIST_DIR / str(page_id)
    output_dir = base_dir / output_subdir if output_subdir else base_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"

    env = {
        **os.environ,
        "HOME": "/home/web3relic",
        "GEMINI_SYSTEM_MD": str(SYSTEM_PROMPT_PATH),
    }

    # ── Generation pass ─────────────────────────────────────────────
    prompt = _build_prompt(page_id, business_name, business_url, description, target_audience, output_subdir, design_md=design_md)

    gen_cmd = [
        "/usr/bin/gemini",
        "-y",
        "-m", "gemini-3.1-pro-preview",
        "--include-directories", "/var/www/webassist",
        "-p", prompt,
    ]

    log.info("[gemini-gen:%s] Starting generation for '%s' (subdir=%s)", page_id, business_name, output_subdir or "root")
    await _run_agent(gen_cmd, page_id, "gemini-gen", env, timeout=1500)

    # Verify generation output (Gemini produces leaner HTML than Claude)
    if not html_path.exists():
        raise RuntimeError("Gemini agent did not create HTML file")

    file_size = html_path.stat().st_size
    if file_size < 3 * 1024:
        raise RuntimeError(f"HTML too small ({file_size} bytes, min 3KB)")

    log.info("[gemini-gen:%s] Generated %d bytes, starting QA", page_id, file_size)

    # ── QA pass ────────────────────────────────────────────────────
    qa_prompt = _build_qa_prompt(page_id, business_name, output_subdir)

    qa_cmd = [
        "/usr/bin/gemini",
        "-y",
        "-m", "gemini-3.1-pro-preview",
        "--include-directories", "/var/www/webassist",
        "-p", qa_prompt,
    ]

    log.info("[gemini-qa:%s] Starting QA review", page_id)
    await _run_agent(qa_cmd, page_id, "gemini-qa", env, timeout=300)

    # Final verification after QA
    if not html_path.exists():
        raise RuntimeError("HTML file missing after QA")

    file_size = html_path.stat().st_size
    if file_size < 3 * 1024:
        raise RuntimeError(f"HTML too small after QA ({file_size} bytes, min 3KB)")

    preview_url = f"{BASE_URL}/{page_id}/{output_subdir}" if output_subdir else f"{BASE_URL}/{page_id}"

    log.info("[gemini-done:%s] %s (%d bytes) → %s", page_id, html_path, file_size, preview_url)

    return {"html_path": str(html_path), "preview_url": preview_url, "file_size": file_size}

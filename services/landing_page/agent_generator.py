"""Agent-driven HTML generation for landing pages.

Replaces the template-based generator.py with a Claude Code CLI agent that:
1. Receives the full design spec from prompts.md for the selected design
2. Gets all research + competitor data as context
3. Generates complete, bespoke HTML using the design system's methodology
4. Writes HTML directly to /var/www/webassist/{id}/index.html

The agent runs as a subprocess with fresh context, ensuring no accumulated
pollution from prior generations.

Fallback: If the agent fails (timeout, rate limit, etc.), the caller should
fall back to the old template generator (generator.py).
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from uuid import UUID

log = logging.getLogger("otto.agent_generator")

WEBASSIST_DIR = Path("/var/www/webassist")
BASE_URL = "https://webassist.otto.lk"
PROMPTS_PATH = Path("/mnt/media/prompts.md")

# Cache the full prompts.md text to avoid re-reading for each generation
_prompts_cache: str | None = None


def _get_prompts_text() -> str:
    """Read and cache prompts.md content."""
    global _prompts_cache
    if _prompts_cache is None:
        _prompts_cache = PROMPTS_PATH.read_text()
    return _prompts_cache


def _extract_design_spec(design_id: str) -> str:
    """Extract the full spec for a specific design from prompts.md.

    Each design starts with 'DESIGN XX' on its own line and ends before the
    next 'DESIGN XX' line or EOF.

    Args:
        design_id: e.g. "DESIGN_06" or "DESIGN 06"

    Returns:
        Full text of the design spec, or empty string if not found.
    """
    text = _get_prompts_text()

    # Normalize: "DESIGN_06" -> "DESIGN 06"
    normalized = design_id.replace("_", " ")

    # Find the design block: starts at 'DESIGN XX' line, ends before next 'DESIGN XX'
    pattern = rf'^({re.escape(normalized)}\n.*?)(?=^DESIGN \d|\Z)'
    match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Try without zero-padding: "DESIGN 6" -> "DESIGN 06"
    # Also try with zero-pad if given without
    num_match = re.search(r'\d+', design_id)
    if num_match:
        num = int(num_match.group())
        for fmt in [f"DESIGN {num:02d}", f"DESIGN {num}"]:
            pattern = rf'^({re.escape(fmt)}\n.*?)(?=^DESIGN \d|\Z)'
            match = re.search(pattern, text, re.DOTALL | re.MULTILINE)
            if match:
                return match.group(1).strip()

    log.warning("Could not find design spec for %s", design_id)
    return ""


def _build_agent_prompt(
    page_id: UUID,
    design_spec: str,
    design_decisions: dict,
    research_data: dict,
    competitor_data: dict,
) -> str:
    """Build the prompt for the Claude Code CLI agent.

    The prompt gives the agent everything it needs to generate a complete
    landing page: design spec, business context, and strict requirements.
    """
    output_dir = WEBASSIST_DIR / str(page_id)
    output_path = output_dir / "index.html"
    preview_url = f"{BASE_URL}/{page_id}"

    business_name = research_data.get("business_name", "Business")
    business_url = research_data.get("business_url", "")

    return f"""You are building a production landing page for "{business_name}".

## YOUR TASK
Write a complete, self-contained HTML file to: {output_path}
First create the directory: mkdir -p {output_dir}

## DESIGN SYSTEM (from prompts.md — follow this EXACTLY)
{design_spec}

## DESIGN DECISIONS (customized for this business)
{json.dumps(design_decisions, indent=2)}

## BUSINESS RESEARCH
{json.dumps(research_data, indent=2)}

## COMPETITOR ANALYSIS
{json.dumps(competitor_data, indent=2)}

## HARD REQUIREMENTS
1. Single self-contained HTML file — ALL CSS in <style> tags, ALL JS in <script> tags
2. Google Fonts loaded via <link> tag — NO other external dependencies
3. Follow the design spec PRECISELY — use the exact fonts, colors, layout structures, special components, and animations described above
4. Mobile-first responsive design: 375px → 768px → 1440px breakpoints
5. Implement EVERY special component from the design spec (echo stacks, pill showcases, gradient blobs, etc.)
6. NO generic centered vertical stack layouts — use the asymmetric grids, offset content, editorial layouts from the spec
7. IntersectionObserver for scroll-triggered entrance animations
8. Full SEO: <title>, <meta description>, Open Graph tags, Twitter Card tags
9. Accessibility: skip-to-content link, :focus-visible states, prefers-reduced-motion media query
10. Canonical URL: {preview_url}
11. OG URL: {preview_url}
12. OG image: use a CSS gradient or pattern as placeholder (no external image URLs)
{f'13. Link the primary CTA to: {business_url}' if business_url else '13. Primary CTA links to #contact'}

## COPY GUIDELINES
- Hero headline: punchy, specific, benefit-driven, max 10 words (NOT "Welcome to {business_name}")
- Subheadline: expand the benefit, max 25 words
- CTAs: action-oriented and specific to THIS business (NOT generic "Learn More" or "Get Started")
- Section headings: concrete, not filler
- If research data has real testimonials/reviews, use them verbatim
- If not, write 2-3 plausible testimonials that match the business type and industry
- Match tone to business: {research_data.get('tone_of_voice', 'professional')}
- Write real body copy for every section — no "Lorem ipsum" or "Coming soon" or empty placeholders

## ANTI-SLOP CHECKLIST (verify BEFORE writing the file)
- [ ] No banned fonts: Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, Space Grotesk
- [ ] No centered-everything layout — the design spec has specific layouts, USE THEM
- [ ] At least one grid-breaking asymmetric element
- [ ] Signature moment / special component from the spec is implemented
- [ ] Color palette matches the design decisions above (not generic blue/white)
- [ ] Animations use the spec's easing curve (check the Spec section), not generic ease-in-out
- [ ] No placeholder images — use CSS gradients, geometric shapes, or patterns instead
- [ ] No "Lorem ipsum" anywhere
- [ ] Footer has real content, not just "© 2024"
- [ ] Navigation is functional with smooth-scroll anchor links
- [ ] All sections from design_decisions.sections are present

Write the complete HTML file now. Use the Write tool to create the file at {output_path}.
After writing, verify the file exists and is larger than 5KB using Bash.
"""


async def generate_with_agent(
    page_id: UUID,
    design_decisions: dict,
    research_data: dict,
    competitor_data: dict,
    pool=None,
) -> dict:
    """Generate landing page HTML using Claude Code CLI agent.

    Spawns a fresh Claude Code session with the full design spec + research
    context. The agent writes HTML directly to /var/www/webassist/{id}/index.html.

    Args:
        page_id: Landing page UUID
        design_decisions: From design_synthesizer() — includes selected_design_id
        research_data: Business research dict
        competitor_data: Competitor analysis dict
        pool: Optional asyncpg pool for DB updates

    Returns:
        Dict with preview_url, html_path, file_size on success.

    Raises:
        RuntimeError: If agent fails, times out, or produces bad output.
    """
    # Extract the full design spec for the selected design
    design_id = design_decisions.get("selected_design_id", "DESIGN 06")
    design_spec = _extract_design_spec(design_id)

    if not design_spec:
        log.warning("No spec found for %s, trying DESIGN 01", design_id)
        design_spec = _extract_design_spec("DESIGN 01")

    if not design_spec:
        raise RuntimeError(f"Could not extract any design spec from {PROMPTS_PATH}")

    # Build the prompt
    prompt = _build_agent_prompt(
        page_id=page_id,
        design_spec=design_spec,
        design_decisions=design_decisions,
        research_data=research_data,
        competitor_data=competitor_data,
    )

    # Ensure output directory exists
    output_dir = WEBASSIST_DIR / str(page_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Invoke Claude Code CLI as subprocess
    cmd = [
        "claude",
        "--model", "claude-sonnet-4-20250514",
        "-p", prompt,
        "--max-turns", "5",
        "--allowedTools", "Write,Read,Bash",
        "--output-format", "text",
    ]

    log.info("[agent:%s] Starting agent (design=%s, spec=%d chars)",
             page_id, design_id, len(design_spec))

    env = {**os.environ, "CLAUDE_CODE_MAX_COST_DOLLARS": "2"}

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd="/home/web3relic/otto",
            env=env,
        )

        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=180,  # 3 minutes max
        )

        exit_code = proc.returncode
        stdout_text = stdout.decode("utf-8", errors="replace")[-500:] if stdout else ""
        log.info("[agent:%s] Agent exited code=%s, stdout_tail=%d chars",
                 page_id, exit_code, len(stdout_text))

    except asyncio.TimeoutError:
        log.error("[agent:%s] Agent timed out after 180s", page_id)
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        raise RuntimeError("Agent timed out after 180 seconds")

    except Exception as exc:
        log.exception("[agent:%s] Agent invocation failed: %s", page_id, exc)
        raise RuntimeError(f"Agent invocation failed: {exc}")

    # Verify the HTML file was written
    html_path = output_dir / "index.html"
    if not html_path.exists():
        stderr_text = stderr.decode("utf-8", errors="replace")[-500:] if stderr else ""
        log.error("[agent:%s] HTML not created. exit=%s stderr=%s",
                  page_id, exit_code, stderr_text)
        raise RuntimeError(
            f"Agent did not create HTML file. Exit code: {exit_code}. "
            f"stderr: {stderr_text[:200]}"
        )

    file_size = html_path.stat().st_size
    if file_size < 1024:
        log.warning("[agent:%s] HTML too small: %d bytes", page_id, file_size)
        raise RuntimeError(f"Generated HTML too small ({file_size} bytes) — likely incomplete")

    preview_url = f"{BASE_URL}/{page_id}"

    # Update DB if pool provided
    if pool:
        await pool.execute(
            """UPDATE landing_pages
               SET html_path = $2, preview_url = $3, status = 'review',
                   error_text = NULL, updated_at = now()
               WHERE id = $1""",
            page_id,
            str(html_path),
            preview_url,
        )

    log.info("[agent:%s] HTML generated: %s (%d bytes) → %s",
             page_id, html_path, file_size, preview_url)

    return {
        "html_path": str(html_path),
        "preview_url": preview_url,
        "file_size": file_size,
    }

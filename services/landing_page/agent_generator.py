"""Landing page generation via Claude Code CLI.

Simple approach: give the agent the business info, point it at prompts.md,
let it read the design system and generate the HTML. One step, no pipeline.
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

Read the design system file at {PROMPTS_PATH} — it contains 35 proven design systems.
Pick the ONE that best fits this business and follow its spec exactly.

## BUSINESS INFO
- Name: {business_name}
- URL: {business_url or 'N/A'}
- Description: {description or 'N/A'}
- Target audience: {target_audience or 'N/A'}

## OUTPUT
Write a single self-contained HTML file to: {output_path}
First create the directory: mkdir -p {output_dir}

Canonical URL: {preview_url}
{f'Primary CTA links to: {business_url}' if business_url else 'Primary CTA links to: #contact'}
"""


async def generate_with_agent(
    page_id: UUID,
    business_name: str,
    business_url: str = "",
    description: str = "",
    target_audience: str = "",
    pool=None,
) -> dict:
    """Generate a landing page by spawning a Claude Code session.

    The agent reads prompts.md, picks a design, and writes the HTML.
    """
    output_dir = WEBASSIST_DIR / str(page_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "index.html"

    prompt = _build_prompt(page_id, business_name, business_url, description, target_audience)

    cmd = [
        "/home/web3relic/.local/bin/claude",
        "--print",
        "--dangerously-skip-permissions",
        "--model", "claude-sonnet-4-6",
        "--max-turns", "12",
        "--max-budget-usd", "3",
        "-p", prompt,
    ]

    log.info("[agent:%s] Starting generation for '%s'", page_id, business_name)

    env = {**os.environ, "HOME": "/home/web3relic"}

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
            timeout=1500,
        )

        exit_code = proc.returncode
        log.info("[agent:%s] Agent exited code=%s", page_id, exit_code)

    except asyncio.TimeoutError:
        log.warning("[agent:%s] Agent timed out after 1500s", page_id)
        try:
            proc.kill()
            await proc.wait()
        except Exception:
            pass
        await asyncio.sleep(3)
        if not (html_path.exists() and html_path.stat().st_size >= 10 * 1024):
            raise RuntimeError("Agent timed out after 1500 seconds")

    except Exception as exc:
        log.exception("[agent:%s] Agent invocation failed: %s", page_id, exc)
        raise RuntimeError(f"Agent invocation failed: {exc}")

    # Verify output
    if not html_path.exists():
        stderr_text = stderr.decode("utf-8", errors="replace")[-500:] if stderr else ""
        raise RuntimeError(f"Agent did not create HTML. exit={exit_code} stderr={stderr_text[:200]}")

    file_size = html_path.stat().st_size
    if file_size < 10 * 1024:
        raise RuntimeError(f"HTML too small ({file_size} bytes, min 10KB)")

    preview_url = f"{BASE_URL}/{page_id}"

    if pool:
        await pool.execute(
            """UPDATE landing_pages
               SET html_path = $2, preview_url = $3, status = 'review',
                   error_text = NULL, updated_at = now()
               WHERE id = $1""",
            page_id, str(html_path), preview_url,
        )

    log.info("[agent:%s] Done: %s (%d bytes) → %s", page_id, html_path, file_size, preview_url)

    return {"html_path": str(html_path), "preview_url": preview_url, "file_size": file_size}

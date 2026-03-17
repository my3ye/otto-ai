#!/usr/bin/env python3
"""
X Auto-Scheduler — Posts due scheduled Social Calendar entries to X.

Runs every 15 minutes via systemd timer (otto-x-scheduler.timer).
Reads posts with status=scheduled and scheduled_at <= now(), posts via twikit,
marks as posted.

Character → X account mapping:
  my3ye / maitrieye → @maitrieye
  otto / ottoassist  → @OttoAssist
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Paths ─────────────────────────────────────────────────────────────────────
BROADCAST_DIR = Path(__file__).parent
CONFIGS_DIR = BROADCAST_DIR / "configs"
LOG_DIR = Path("/home/web3relic/otto/logs")
LOG_FILE = LOG_DIR / "x_scheduler.log"

# ── Constants ──────────────────────────────────────────────────────────────────
MEMORY_API = "http://localhost:8100"
CHAR_LIMIT = 280

# Map social calendar character to X handle (case-insensitive key lookup)
CHARACTER_TO_HANDLE: dict[str, str] = {
    "my3ye": "maitrieye",
    "maitrieye": "maitrieye",
    "otto": "OttoAssist",
    "ottoassist": "OttoAssist",
    "pipi": "maitrieye",      # PiPi posts via MY3YE account for now
    "koink": "maitrieye",
}

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [x_scheduler] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger("x_scheduler")


# ── Config helpers ─────────────────────────────────────────────────────────────

def load_x_account(handle: str) -> dict | None:
    """Load X account config for the given handle from platforms.json."""
    config_path = CONFIGS_DIR / "platforms.json"
    try:
        config = json.loads(config_path.read_text())
        accounts = config.get("platforms", {}).get("x", {}).get("accounts", [])
        for acc in accounts:
            if acc.get("handle", "").lower() == handle.lower():
                return acc
    except Exception as e:
        log.error(f"Failed to load X config: {e}")
    return None


# ── Social Calendar API ────────────────────────────────────────────────────────

async def get_due_posts() -> list[dict]:
    """Fetch social calendar posts that are due (scheduled_at <= now, status=scheduled, platform=x)."""
    now = datetime.now(timezone.utc)
    due = []

    async with httpx.AsyncClient(timeout=10) as client:
        # Fetch all scheduled posts (no character filter — pick up any character targeting X)
        r = await client.get(
            f"{MEMORY_API}/social-calendar",
            params={"status": "scheduled", "limit": 100},
        )
        r.raise_for_status()
        posts = r.json().get("posts", [])

    for post in posts:
        # Must have a scheduled time
        scheduled_at_str = post.get("scheduled_at")
        if not scheduled_at_str:
            continue

        # Must be due
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
            # Ensure timezone-aware for comparison
            if scheduled_at.tzinfo is None:
                scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        except ValueError:
            log.warning(f"Bad scheduled_at format for post {post.get('id')}: {scheduled_at_str}")
            continue

        if scheduled_at > now:
            continue

        # Must target X platform (empty platforms list = post to all, including X)
        platforms = [p.lower() for p in (post.get("platforms") or [])]
        if platforms and "x" not in platforms:
            continue

        due.append(post)

    return due


async def mark_posted(post_id: str, url: str | None = None) -> None:
    notes = f"Posted at {datetime.now(timezone.utc).isoformat()}"
    if url:
        notes += f" → {url}"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.patch(
            f"{MEMORY_API}/social-calendar/{post_id}",
            json={"status": "posted", "notes": notes},
        )
    log.info(f"Marked post {post_id} as posted")


async def mark_failed(post_id: str, error: str) -> None:
    existing_notes = ""  # We'll just append
    notes = f"SCHEDULER FAILED at {datetime.now(timezone.utc).isoformat()}: {error[:300]}"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.patch(
            f"{MEMORY_API}/social-calendar/{post_id}",
            json={"notes": notes},
        )
    log.warning(f"Marked post {post_id} as failed: {error[:100]}")


# ── X Posting ──────────────────────────────────────────────────────────────────

async def post_to_x(post: dict) -> tuple[bool, str | None]:
    """
    Post a social calendar entry to X.
    Returns (success, url_or_None).
    """
    # Import the adapter (lazy to avoid import errors if twikit not present)
    try:
        sys.path.insert(0, str(BROADCAST_DIR.parent))
        from broadcast.adapters.x import XAdapter
    except ImportError as e:
        log.error(f"Could not import XAdapter: {e}")
        return False, None

    character = post.get("character", "my3ye").lower().replace(" ", "")
    handle = CHARACTER_TO_HANDLE.get(character, "maitrieye")

    account = load_x_account(handle)
    if not account:
        log.error(f"No X account configured for handle '{handle}' (character: {character})")
        return False, None

    content = post.get("content", "").strip()
    if not content:
        log.error(f"Post {post['id']} has no content, skipping")
        return False, None

    # Truncate to X character limit
    text = content[:CHAR_LIMIT]

    log.info(f"Posting to @{handle}: {text[:80]}...")

    adapter = XAdapter()
    try:
        result = await adapter.post_single_account(text, account)
        if result.success:
            log.info(f"✓ Posted @{handle} → {result.url or 'posted'}")
            return True, result.url
        else:
            log.error(f"✗ Failed @{handle}: {result.error}")
            return False, result.error
    except Exception as e:
        log.error(f"Exception posting to X: {e}")
        return False, str(e)


# ── Main ──────────────────────────────────────────────────────────────────────

async def run() -> None:
    log.info("X scheduler starting...")

    try:
        due = await get_due_posts()
    except Exception as e:
        log.error(f"Failed to fetch due posts: {e}")
        return

    if not due:
        log.info("No posts due. Done.")
        return

    log.info(f"Found {len(due)} due post(s).")

    for post in due:
        pid = post["id"]
        char = post.get("character", "?")
        title = post.get("title", "untitled")
        log.info(f"Processing [{char}] '{title}' (id={pid})")

        success, result = await post_to_x(post)

        if success:
            url = result if isinstance(result, str) and result.startswith("http") else None
            await mark_posted(pid, url)
        else:
            error = result or "unknown error"
            await mark_failed(pid, error)

        # Brief delay between posts to avoid rate limits
        await asyncio.sleep(3)

    log.info("X scheduler done.")


if __name__ == "__main__":
    asyncio.run(run())

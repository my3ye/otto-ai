"""Articles route — manage content created by Otto for MY3YE ecosystem.

Status workflow: draft → ready → approved → posted
Mev must approve (set status=approved) before publishing.
Provides CRUD + status transitions + one-click broadcast publish.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..db import get_pool

# Make broadcast module importable
_BROADCAST_PATH = Path("/home/web3relic/otto/projects/broadcast")
if str(_BROADCAST_PATH.parent) not in sys.path:
    sys.path.insert(0, str(_BROADCAST_PATH.parent))

log = logging.getLogger("otto.articles")

router = APIRouter(prefix="/articles", tags=["articles"])

# ── Schema ─────────────────────────────────────────────────────────────────

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title       TEXT NOT NULL DEFAULT 'Untitled',
    status      TEXT NOT NULL DEFAULT 'draft',
    content     TEXT NOT NULL DEFAULT '',
    platform    TEXT,
    ecosystem_project TEXT,
    tags        TEXT[] DEFAULT '{}',
    publish_date DATE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
"""

VALID_STATUSES = {"draft", "ready", "approved", "posted"}

# Ordered progression — status can only move forward
STATUS_ORDER = ["draft", "ready", "approved", "posted"]

PLATFORMS = [
    "paragraph", "mirror", "medium", "substack", "x",
    "bluesky", "farcaster", "devto", "hashnode",
    "telegram", "discord", "mastodon", "other",
]


# ── Pydantic models ────────────────────────────────────────────────────────

class ArticleCreate(BaseModel):
    title: str = "Untitled"
    content: str = ""
    platform: Optional[str] = None
    ecosystem_project: Optional[str] = None
    tags: list[str] = []
    publish_date: Optional[str] = None  # ISO date string


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    platform: Optional[str] = None
    ecosystem_project: Optional[str] = None
    tags: Optional[list[str]] = None
    publish_date: Optional[str] = None


class ArticleOut(BaseModel):
    id: str
    title: str
    status: str
    content: str
    platform: Optional[str]
    ecosystem_project: Optional[str]
    tags: list[str]
    publish_date: Optional[str]
    created_at: str
    updated_at: str


def _row_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "status": row["status"],
        "content": row["content"],
        "platform": row["platform"],
        "ecosystem_project": row["ecosystem_project"],
        "tags": list(row["tags"] or []),
        "publish_date": str(row["publish_date"]) if row["publish_date"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


async def _ensure_table(pool):
    await pool.execute(CREATE_TABLE_SQL)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
async def list_articles(status: Optional[str] = None):
    """List all articles, optionally filtered by status."""
    pool = await get_pool()
    await _ensure_table(pool)

    if status:
        rows = await pool.fetch(
            "SELECT * FROM articles WHERE status = $1 ORDER BY updated_at DESC",
            status,
        )
    else:
        rows = await pool.fetch(
            "SELECT * FROM articles ORDER BY updated_at DESC"
        )

    articles = [_row_to_dict(r) for r in rows]
    counts = {"draft": 0, "ready": 0, "posted": 0}
    for a in articles:
        if a["status"] in counts:
            counts[a["status"]] += 1

    return {"articles": articles, "counts": counts, "total": len(articles)}


@router.post("", status_code=201)
async def create_article(body: ArticleCreate):
    """Create a new article (default status: draft)."""
    pool = await get_pool()
    await _ensure_table(pool)

    if body.platform and body.platform not in PLATFORMS:
        raise HTTPException(400, f"Invalid platform. Must be one of: {PLATFORMS}")

    row = await pool.fetchrow(
        """INSERT INTO articles (title, content, platform, ecosystem_project, tags, publish_date)
           VALUES ($1, $2, $3, $4, $5, $6::DATE)
           RETURNING *""",
        body.title,
        body.content,
        body.platform,
        body.ecosystem_project,
        body.tags,
        body.publish_date,
    )

    return _row_to_dict(row)


@router.get("/{article_id}")
async def get_article(article_id: str):
    """Get a single article by ID."""
    pool = await get_pool()
    await _ensure_table(pool)

    row = await pool.fetchrow(
        "SELECT * FROM articles WHERE id = $1",
        article_id,
    )
    if not row:
        raise HTTPException(404, f"Article {article_id} not found")

    return _row_to_dict(row)


@router.patch("/{article_id}")
async def update_article(article_id: str, body: ArticleUpdate):
    """Update article fields (partial update)."""
    pool = await get_pool()
    await _ensure_table(pool)

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {list(VALID_STATUSES)}")

    if body.platform and body.platform not in PLATFORMS:
        raise HTTPException(400, f"Invalid platform. Must be one of: {PLATFORMS}")

    # Build SET clause dynamically
    updates = {}
    if body.title is not None:
        updates["title"] = body.title
    if body.content is not None:
        updates["content"] = body.content
    if body.status is not None:
        updates["status"] = body.status
    if body.platform is not None:
        updates["platform"] = body.platform
    if body.ecosystem_project is not None:
        updates["ecosystem_project"] = body.ecosystem_project
    if body.tags is not None:
        updates["tags"] = body.tags
    if body.publish_date is not None:
        updates["publish_date"] = body.publish_date

    if not updates:
        # Nothing to update — just return current
        row = await pool.fetchrow("SELECT * FROM articles WHERE id = $1", article_id)
        if not row:
            raise HTTPException(404, f"Article {article_id} not found")
        return _row_to_dict(row)

    set_parts = []
    values = []
    idx = 1
    for key, val in updates.items():
        if key == "publish_date":
            set_parts.append(f"{key} = ${idx}::DATE")
        else:
            set_parts.append(f"{key} = ${idx}")
        values.append(val)
        idx += 1

    set_parts.append(f"updated_at = ${idx}")
    values.append(datetime.now(timezone.utc))
    idx += 1
    values.append(article_id)

    row = await pool.fetchrow(
        f"UPDATE articles SET {', '.join(set_parts)} WHERE id = ${idx} RETURNING *",
        *values,
    )
    if not row:
        raise HTTPException(404, f"Article {article_id} not found")

    return _row_to_dict(row)


@router.post("/{article_id}/status")
async def update_status(article_id: str, status: str):
    """Transition article status: draft → ready → approved → posted."""
    pool = await get_pool()
    await _ensure_table(pool)

    if status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status. Must be one of: {list(VALID_STATUSES)}")

    row = await pool.fetchrow(
        "UPDATE articles SET status = $1, updated_at = now() WHERE id = $2 RETURNING *",
        status,
        article_id,
    )
    if not row:
        raise HTTPException(404, f"Article {article_id} not found")

    return _row_to_dict(row)


class PublishRequest(BaseModel):
    platforms: Optional[list[str]] = None   # None = all enabled platforms


@router.post("/{article_id}/publish")
async def publish_article(article_id: str, req: PublishRequest = PublishRequest()):
    """Broadcast an approved article to configured platforms.

    Article must be in 'approved' status. After successful broadcast,
    status advances to 'posted'. Returns per-platform results.
    """
    pool = await get_pool()
    await _ensure_table(pool)

    row = await pool.fetchrow("SELECT * FROM articles WHERE id = $1", article_id)
    if not row:
        raise HTTPException(404, f"Article {article_id} not found")

    article = _row_to_dict(row)
    if article["status"] != "approved":
        raise HTTPException(
            400,
            f"Article must be in 'approved' status to publish. Current status: {article['status']}. "
            "Mev must approve the article before it can be broadcast."
        )

    try:
        from broadcast.broadcast import BroadcastEngine
        from broadcast.models import BroadcastMessage
    except ImportError as e:
        raise HTTPException(500, f"Broadcast module not available: {e}")

    # Build message from article — format as article for long-form platforms
    tags = article.get("tags") or []
    if article.get("ecosystem_project"):
        tags = [article["ecosystem_project"]] + [t for t in tags if t != article["ecosystem_project"]]

    msg = BroadcastMessage(
        content=article["content"],
        format="article",
        title=article["title"],
        tags=tags,
    )

    try:
        engine = BroadcastEngine()
        record = await engine.send(msg, platforms=req.platforms)
    except Exception as e:
        log.exception("Broadcast failed for article %s", article_id)
        raise HTTPException(500, str(e))

    # Mark as posted if at least one platform succeeded
    if record.platforms_succeeded > 0:
        await pool.execute(
            "UPDATE articles SET status = 'posted', updated_at = now() WHERE id = $1",
            article_id,
        )

    from dataclasses import asdict
    return {
        "article_id": article_id,
        "broadcast": asdict(record),
        "status_updated": record.platforms_succeeded > 0,
    }


@router.delete("/{article_id}", status_code=204)
async def delete_article(article_id: str):
    """Permanently delete an article."""
    pool = await get_pool()
    await _ensure_table(pool)

    result = await pool.execute(
        "DELETE FROM articles WHERE id = $1",
        article_id,
    )
    if result == "DELETE 0":
        raise HTTPException(404, f"Article {article_id} not found")


# ── File sync ──────────────────────────────────────────────────────────────

ARTICLES_DIR = Path(os.path.expanduser("~/otto/projects/articles"))

# Filename-to-metadata hints (ecosystem project + tags)
_FILE_META: dict[str, dict] = {
    "pipi_intro.md":         {"ecosystem_project": "pipi", "platform": "paragraph", "tags": ["pipi", "intro"]},
    "pipi_three_lives.md":   {"ecosystem_project": "pipi", "platform": "paragraph", "tags": ["pipi", "mythology"]},
    "pipi_why_the_pig.md":   {"ecosystem_project": "pipi", "platform": "paragraph", "tags": ["pipi", "cultural"]},
    "pipi_the_frequency.md": {"ecosystem_project": "pipi", "platform": "paragraph", "tags": ["pipi", "philosophy"]},
    "koink_intro.md":        {"ecosystem_project": "koink", "platform": "paragraph", "tags": ["koink", "intro"]},
    "505_systems_intro.md":  {"ecosystem_project": "sos-systems", "platform": "paragraph", "tags": ["sos-systems", "intro"]},
}


@router.post("/sync-from-files", status_code=200)
async def sync_from_files():
    """Scan ~/otto/projects/articles/*.md and import any files not already in the DB.

    Matches by title derived from filename. Idempotent — skips files whose title
    already exists in the DB. Returns a summary of imported vs skipped files.
    """
    pool = await get_pool()
    await _ensure_table(pool)

    if not ARTICLES_DIR.exists():
        return {"imported": 0, "skipped": 0, "files": []}

    # Build set of existing titles for dedup
    existing_titles = {
        r["title"]
        for r in await pool.fetch("SELECT title FROM articles")
    }

    imported = []
    skipped = []

    for md_file in sorted(ARTICLES_DIR.glob("*.md")):
        content = md_file.read_text().strip()
        filename = md_file.name

        # Derive title: use first H1 heading, fall back to filename
        title = filename.replace(".md", "").replace("_", " ").title()
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                title = stripped[2:].strip()
                break

        if title in existing_titles:
            skipped.append(filename)
            continue

        meta = _FILE_META.get(filename, {})
        row = await pool.fetchrow(
            """INSERT INTO articles (title, content, platform, ecosystem_project, tags)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING id, title, status""",
            title,
            content,
            meta.get("platform"),
            meta.get("ecosystem_project"),
            meta.get("tags", []),
        )
        imported.append({"id": str(row["id"]), "title": row["title"], "file": filename})
        existing_titles.add(title)
        log.info("Imported article from file: %s → %s", filename, row["id"])

    return {
        "imported": len(imported),
        "skipped": len(skipped),
        "files": imported,
        "skipped_files": skipped,
    }

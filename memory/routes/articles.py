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

CREATE_VERSIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_versions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    article_id      UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL,
    title           TEXT NOT NULL DEFAULT '',
    content         TEXT NOT NULL DEFAULT '',
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_article_versions_article_version
    ON article_versions(article_id, version_number);
CREATE INDEX IF NOT EXISTS idx_article_versions_article_created
    ON article_versions(article_id, created_at DESC);
"""

MAX_VERSIONS_PER_ARTICLE = 50

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
    await pool.execute(CREATE_VERSIONS_TABLE_SQL)


def _version_row_to_dict(row) -> dict:
    return {
        "id": str(row["id"]),
        "article_id": str(row["article_id"]),
        "version_number": row["version_number"],
        "title": row["title"],
        "content": row["content"],
        "note": row["note"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


async def _snapshot(pool, article_id: str, title: str, content: str, note: str | None = None):
    """Save a snapshot of the current article state before overwriting."""
    # Get next version number
    row = await pool.fetchrow(
        "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_ver FROM article_versions WHERE article_id = $1",
        article_id,
    )
    next_ver = row["next_ver"]

    await pool.execute(
        """INSERT INTO article_versions (article_id, version_number, title, content, note)
           VALUES ($1, $2, $3, $4, $5)""",
        article_id, next_ver, title, content, note,
    )

    # Prune oldest versions if over limit
    await pool.execute(
        """DELETE FROM article_versions
           WHERE article_id = $1
             AND version_number NOT IN (
               SELECT version_number FROM article_versions
               WHERE article_id = $1
               ORDER BY version_number DESC
               LIMIT $2
             )""",
        article_id, MAX_VERSIONS_PER_ARTICLE,
    )


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
    counts = {"draft": 0, "ready": 0, "approved": 0, "posted": 0}
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

    # Auto-snapshot current state before writing (only if content or title is changing)
    if "content" in updates or "title" in updates:
        current = await pool.fetchrow("SELECT title, content FROM articles WHERE id = $1", article_id)
        if current:
            await _snapshot(pool, article_id, current["title"], current["content"])

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


class SnapshotCreate(BaseModel):
    note: Optional[str] = None  # optional human label e.g. "Pre-publish draft"


@router.get("/{article_id}/versions")
async def list_versions(article_id: str):
    """List all saved versions for an article, newest first."""
    pool = await get_pool()
    await _ensure_table(pool)

    rows = await pool.fetch(
        """SELECT id, article_id, version_number, title,
                  LEFT(content, 200) AS content_preview,
                  note, created_at
           FROM article_versions
           WHERE article_id = $1
           ORDER BY version_number DESC""",
        article_id,
    )
    versions = []
    for r in rows:
        versions.append({
            "id": str(r["id"]),
            "article_id": str(r["article_id"]),
            "version_number": r["version_number"],
            "title": r["title"],
            "content_preview": r["content_preview"],
            "note": r["note"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        })
    return {"versions": versions, "total": len(versions)}


@router.get("/{article_id}/versions/{version_id}")
async def get_version(article_id: str, version_id: str):
    """Get full content of a specific version."""
    pool = await get_pool()
    await _ensure_table(pool)

    row = await pool.fetchrow(
        "SELECT * FROM article_versions WHERE id = $1 AND article_id = $2",
        version_id, article_id,
    )
    if not row:
        raise HTTPException(404, f"Version {version_id} not found for article {article_id}")
    return _version_row_to_dict(row)


@router.post("/{article_id}/versions", status_code=201)
async def create_snapshot(article_id: str, body: SnapshotCreate = SnapshotCreate()):
    """Manually snapshot the current article state with an optional note."""
    pool = await get_pool()
    await _ensure_table(pool)

    current = await pool.fetchrow("SELECT * FROM articles WHERE id = $1", article_id)
    if not current:
        raise HTTPException(404, f"Article {article_id} not found")

    await _snapshot(pool, article_id, current["title"], current["content"], note=body.note)

    # Return the newly created version
    row = await pool.fetchrow(
        """SELECT * FROM article_versions WHERE article_id = $1
           ORDER BY version_number DESC LIMIT 1""",
        article_id,
    )
    return _version_row_to_dict(row)


@router.post("/{article_id}/versions/{version_id}/restore")
async def restore_version(article_id: str, version_id: str):
    """Restore article to a previous version. Auto-snapshots current state first."""
    pool = await get_pool()
    await _ensure_table(pool)

    version = await pool.fetchrow(
        "SELECT * FROM article_versions WHERE id = $1 AND article_id = $2",
        version_id, article_id,
    )
    if not version:
        raise HTTPException(404, f"Version {version_id} not found for article {article_id}")

    # Snapshot current state before restoring
    current = await pool.fetchrow("SELECT title, content FROM articles WHERE id = $1", article_id)
    if not current:
        raise HTTPException(404, f"Article {article_id} not found")

    await _snapshot(
        pool, article_id, current["title"], current["content"],
        note=f"Auto-saved before restoring v{version['version_number']}",
    )

    # Restore
    row = await pool.fetchrow(
        """UPDATE articles SET title = $1, content = $2, updated_at = now()
           WHERE id = $3 RETURNING *""",
        version["title"], version["content"], article_id,
    )
    return {
        "article": _row_to_dict(row),
        "restored_from_version": version["version_number"],
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

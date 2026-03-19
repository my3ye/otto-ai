"""Unified Content API — single system for all content types.

Replaces fragmented articles, social_calendar_posts, and project_content tables
with one model featuring granular versioning, content relationships, and
type-specific metadata via JSONB.

Content types: article, social_post, landing_copy, roadmap, plan, note, research
"""

import difflib
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool

log = logging.getLogger("otto.content")
router = APIRouter(prefix="/content", tags=["content"])

MAX_VERSIONS = 100

VALID_TYPES = {
    "article", "social_post", "landing_copy",
    "roadmap", "plan", "note", "research",
}

VALID_LINK_TYPES = {
    "promotes", "extends", "references",
    "derived_from", "section_of", "variant_of",
}

# ── Pydantic Models ─────────────────────────────────────────────


class ContentCreate(BaseModel):
    content_type: str
    project_id: Optional[str] = None
    character: Optional[str] = None
    title: str = "Untitled"
    body: str = ""
    metadata: dict = {}
    status: str = "draft"
    scheduled_at: Optional[str] = None
    tags: List[str] = []
    parent_id: Optional[str] = None
    sort_order: int = 0
    created_by: str = "mev"


class ContentUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    content_type: Optional[str] = None
    project_id: Optional[str] = None
    character: Optional[str] = None
    metadata: Optional[dict] = None
    status: Optional[str] = None
    scheduled_at: Optional[str] = None
    published_at: Optional[str] = None
    tags: Optional[List[str]] = None
    parent_id: Optional[str] = None
    sort_order: Optional[int] = None
    archived: Optional[bool] = None
    change_note: Optional[str] = None
    changed_by: str = "mev"


class LinkCreate(BaseModel):
    target_id: str
    link_type: str
    metadata: dict = {}


# ── Helpers ─────────────────────────────────────────────────────


def _parse_jsonb(val):
    """Normalize JSONB that asyncpg may return as str or dict."""
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return {}
    return val if val is not None else {}


def _row_to_dict(row) -> dict:
    d = dict(row)
    for k in ("scheduled_at", "published_at", "created_at", "updated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    d["id"] = str(d["id"])
    if d.get("parent_id"):
        d["parent_id"] = str(d["parent_id"])
    d["metadata"] = _parse_jsonb(d.get("metadata"))
    return d


def _version_to_dict(row) -> dict:
    d = dict(row)
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    d["id"] = str(d["id"])
    d["content_id"] = str(d["content_id"])
    d["metadata"] = _parse_jsonb(d.get("metadata"))
    return d


def _detect_changes(existing: dict, updates: dict) -> list[str]:
    """Return list of field names that actually changed."""
    changed = []
    for field, new_val in updates.items():
        if field in ("change_note", "changed_by"):
            continue
        old_val = existing.get(field)
        if old_val != new_val:
            changed.append(field)
    return changed


def _parse_ts(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, f"Invalid datetime format: {s}")


# Version-worthy fields — changes to these trigger a snapshot
_VERSIONABLE = {"title", "body", "metadata", "status", "tags"}


async def _snapshot(conn, content_id: str, row, changed_fields: list[str],
                    change_note: str | None, changed_by: str):
    """Snapshot current state before applying changes."""
    version = row["version"]
    meta = row["metadata"]
    if isinstance(meta, dict):
        meta = json.dumps(meta)

    await conn.execute(
        """INSERT INTO content_versions
           (content_id, version, title, body, metadata, status, tags,
            changed_fields, change_note, changed_by)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8, $9, $10)
           ON CONFLICT (content_id, version) DO NOTHING""",
        content_id, version, row["title"], row["body"], meta,
        row["status"], list(row["tags"] or []),
        changed_fields, change_note, changed_by,
    )

    # Prune oldest versions beyond limit
    await conn.execute(
        """DELETE FROM content_versions
           WHERE content_id = $1 AND version NOT IN (
               SELECT version FROM content_versions
               WHERE content_id = $1
               ORDER BY version DESC LIMIT $2
           )""",
        content_id, MAX_VERSIONS,
    )


# ── CRUD ────────────────────────────────────────────────────────


@router.get("")
async def list_content(
    type: Optional[str] = Query(None, description="Filter by content_type"),
    project: Optional[str] = Query(None, description="Filter by project_id"),
    character: Optional[str] = Query(None, description="Filter by character"),
    status: Optional[str] = Query(None, description="Filter by status"),
    parent_id: Optional[str] = Query(None, description="Filter by parent_id"),
    tag: Optional[str] = Query(None, description="Filter by tag (items containing this tag)"),
    search: Optional[str] = Query(None, description="Search title (case-insensitive)"),
    metadata_filter: Optional[str] = Query(None, description="JSON for JSONB containment filter"),
    include_archived: bool = Query(False, description="Include archived items"),
    sort: str = Query("updated_at", description="Sort field"),
    order: str = Query("desc", description="Sort order: asc or desc"),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List content with flexible filtering."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params: list = []
        idx = 1

        if not include_archived:
            conditions.append("archived = FALSE")

        if type:
            conditions.append(f"content_type = ${idx}")
            params.append(type)
            idx += 1

        if project:
            conditions.append(f"project_id = ${idx}")
            params.append(project)
            idx += 1

        if character:
            conditions.append(f"character = ${idx}")
            params.append(character)
            idx += 1

        if status:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        if parent_id:
            conditions.append(f"parent_id = ${idx}")
            params.append(parent_id)
            idx += 1

        if tag:
            conditions.append(f"${idx} = ANY(tags)")
            params.append(tag)
            idx += 1

        if search:
            conditions.append(f"title ILIKE ${idx}")
            params.append(f"%{search}%")
            idx += 1

        if metadata_filter:
            try:
                json.loads(metadata_filter)  # validate
            except json.JSONDecodeError:
                raise HTTPException(400, "metadata_filter must be valid JSON")
            conditions.append(f"metadata @> ${idx}::jsonb")
            params.append(metadata_filter)
            idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Validate sort field
        valid_sorts = {"created_at", "updated_at", "scheduled_at", "title", "sort_order", "version"}
        if sort not in valid_sorts:
            sort = "updated_at"
        sort_dir = "ASC" if order.lower() == "asc" else "DESC"

        # Count
        count_params = params.copy()
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM content {where}", *count_params
        )

        # Fetch
        params.extend([limit, offset])
        rows = await conn.fetch(
            f"""SELECT * FROM content {where}
                ORDER BY {sort} {sort_dir} NULLS LAST, created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}""",
            *params,
        )

        return {
            "items": [_row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.post("", status_code=201)
async def create_content(body: ContentCreate):
    """Create a new content item."""
    if body.content_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid content_type. Must be one of: {sorted(VALID_TYPES)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        scheduled = _parse_ts(body.scheduled_at)
        meta = json.dumps(body.metadata)

        row = await conn.fetchrow(
            """INSERT INTO content
               (content_type, project_id, character, title, body, metadata,
                status, scheduled_at, tags, parent_id, sort_order, created_by)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11, $12)
               RETURNING *""",
            body.content_type, body.project_id, body.character,
            body.title, body.body, meta,
            body.status, scheduled, body.tags,
            body.parent_id, body.sort_order, body.created_by,
        )
        log.info("Created %s content: %s (%s)", body.content_type, row["id"], body.title)
        return _row_to_dict(row)


@router.get("/types")
async def content_type_stats():
    """Get content type summary with counts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT content_type, status, COUNT(*) as count
               FROM content WHERE archived = FALSE
               GROUP BY content_type, status
               ORDER BY content_type, status"""
        )

        # Aggregate into nested structure
        types: dict = {}
        for r in rows:
            ct = r["content_type"]
            if ct not in types:
                types[ct] = {"total": 0, "by_status": {}}
            types[ct]["total"] += r["count"]
            types[ct]["by_status"][r["status"]] = r["count"]

        return {"types": types}


@router.get("/{content_id}")
async def get_content(content_id: str):
    """Get a single content item with link counts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM content WHERE id = $1", content_id
        )
        if not row:
            raise HTTPException(404, "Content not found")

        result = _row_to_dict(row)

        # Add link counts
        link_count = await conn.fetchval(
            """SELECT COUNT(*) FROM content_links
               WHERE source_id = $1 OR target_id = $1""",
            content_id,
        )
        version_count = await conn.fetchval(
            "SELECT COUNT(*) FROM content_versions WHERE content_id = $1",
            content_id,
        )
        result["link_count"] = link_count
        result["version_count"] = version_count

        return result


@router.patch("/{content_id}")
async def update_content(content_id: str, body: ContentUpdate):
    """Update content with auto-versioning.

    Automatically snapshots the current state before applying changes
    when versionable fields (title, body, metadata, status, tags) change.
    """
    if body.content_type and body.content_type not in VALID_TYPES:
        raise HTTPException(400, f"Invalid content_type. Must be one of: {sorted(VALID_TYPES)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM content WHERE id = $1", content_id
        )
        if not existing:
            raise HTTPException(404, "Content not found")

        # Build update dict
        updates: dict = {}
        if body.title is not None:
            updates["title"] = body.title
        if body.body is not None:
            updates["body"] = body.body
        if body.content_type is not None:
            updates["content_type"] = body.content_type
        if body.project_id is not None:
            updates["project_id"] = body.project_id
        if body.character is not None:
            updates["character"] = body.character
        if body.metadata is not None:
            updates["metadata"] = json.dumps(body.metadata)
        if body.status is not None:
            updates["status"] = body.status
        if body.scheduled_at is not None:
            updates["scheduled_at"] = _parse_ts(body.scheduled_at)
        if body.published_at is not None:
            updates["published_at"] = _parse_ts(body.published_at)
        if body.tags is not None:
            updates["tags"] = body.tags
        if body.parent_id is not None:
            updates["parent_id"] = body.parent_id
        if body.sort_order is not None:
            updates["sort_order"] = body.sort_order
        if body.archived is not None:
            updates["archived"] = body.archived

        if not updates:
            return _row_to_dict(existing)

        # Detect which fields actually changed
        existing_dict = dict(existing)
        # Normalize metadata for comparison
        if "metadata" in updates:
            existing_meta = json.dumps(existing_dict.get("metadata") or {})
            if updates["metadata"] == existing_meta:
                del updates["metadata"]

        changed = _detect_changes(existing_dict, updates)
        versionable_changed = set(changed) & _VERSIONABLE

        # Auto-snapshot if versionable fields changed
        if versionable_changed:
            await _snapshot(
                conn, content_id, existing,
                list(versionable_changed),
                body.change_note, body.changed_by,
            )
            updates["version"] = existing["version"] + 1

        # Build and execute UPDATE
        set_parts = []
        values = [content_id]
        pidx = 2
        for key, val in updates.items():
            if key == "metadata":
                set_parts.append(f"{key} = ${pidx}::jsonb")
            else:
                set_parts.append(f"{key} = ${pidx}")
            values.append(val)
            pidx += 1

        row = await conn.fetchrow(
            f"UPDATE content SET {', '.join(set_parts)} WHERE id = $1 RETURNING *",
            *values,
        )
        return _row_to_dict(row)


@router.delete("/{content_id}")
async def archive_content(content_id: str, hard: bool = Query(False)):
    """Soft-archive content (or hard-delete if hard=true)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if hard:
            result = await conn.execute(
                "DELETE FROM content WHERE id = $1", content_id
            )
            if result == "DELETE 0":
                raise HTTPException(404, "Content not found")
            return {"ok": True, "deleted": content_id}
        else:
            row = await conn.fetchrow(
                "UPDATE content SET archived = TRUE WHERE id = $1 RETURNING id",
                content_id,
            )
            if not row:
                raise HTTPException(404, "Content not found")
            return {"ok": True, "archived": content_id}


# ── Versioning ──────────────────────────────────────────────────


@router.get("/{content_id}/versions")
async def list_versions(content_id: str):
    """List all versions for a content item, newest first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verify content exists
        exists = await conn.fetchval(
            "SELECT 1 FROM content WHERE id = $1", content_id
        )
        if not exists:
            raise HTTPException(404, "Content not found")

        rows = await conn.fetch(
            """SELECT id, content_id, version, title,
                      LEFT(body, 200) AS body_preview,
                      status, tags, changed_fields, change_note, changed_by, created_at
               FROM content_versions
               WHERE content_id = $1
               ORDER BY version DESC""",
            content_id,
        )
        versions = []
        for r in rows:
            d = dict(r)
            d["id"] = str(d["id"])
            d["content_id"] = str(d["content_id"])
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            versions.append(d)

        return {"versions": versions, "total": len(versions)}


@router.get("/{content_id}/versions/{version}")
async def get_version(content_id: str, version: int):
    """Get full content of a specific version."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM content_versions WHERE content_id = $1 AND version = $2",
            content_id, version,
        )
        if not row:
            raise HTTPException(404, f"Version {version} not found")
        return _version_to_dict(row)


@router.post("/{content_id}/restore/{version}")
async def restore_version(content_id: str, version: int):
    """Restore content to a previous version. Auto-snapshots current state first."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get the version to restore
        ver = await conn.fetchrow(
            "SELECT * FROM content_versions WHERE content_id = $1 AND version = $2",
            content_id, version,
        )
        if not ver:
            raise HTTPException(404, f"Version {version} not found")

        # Get current state
        current = await conn.fetchrow(
            "SELECT * FROM content WHERE id = $1", content_id
        )
        if not current:
            raise HTTPException(404, "Content not found")

        # Snapshot current state before restoring
        await _snapshot(
            conn, content_id, current,
            ["restore"],
            f"Auto-saved before restoring v{version}",
            "mev",
        )

        new_version = current["version"] + 1
        meta = ver["metadata"]
        if isinstance(meta, dict):
            meta = json.dumps(meta)

        row = await conn.fetchrow(
            """UPDATE content
               SET title = $2, body = $3, metadata = $4::jsonb,
                   status = $5, tags = $6, version = $7
               WHERE id = $1 RETURNING *""",
            content_id, ver["title"], ver["body"], meta,
            ver["status"], list(ver["tags"] or []), new_version,
        )

        return {
            "content": _row_to_dict(row),
            "restored_from_version": version,
        }


@router.get("/{content_id}/diff")
async def diff_versions(
    content_id: str,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
):
    """Compare two versions and return field-level diffs."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        ver1 = await conn.fetchrow(
            "SELECT * FROM content_versions WHERE content_id = $1 AND version = $2",
            content_id, v1,
        )
        ver2 = await conn.fetchrow(
            "SELECT * FROM content_versions WHERE content_id = $1 AND version = $2",
            content_id, v2,
        )

        # Allow comparing with current version (use version from content table)
        current = await conn.fetchrow(
            "SELECT * FROM content WHERE id = $1", content_id
        )
        if not current:
            raise HTTPException(404, "Content not found")

        if not ver1 and v1 == current["version"]:
            ver1 = current
        if not ver2 and v2 == current["version"]:
            ver2 = current

        if not ver1:
            raise HTTPException(404, f"Version {v1} not found")
        if not ver2:
            raise HTTPException(404, f"Version {v2} not found")

        changes = {}

        # Compare text fields
        for field in ("title", "status"):
            old = ver1.get(field) or ""
            new = ver2.get(field) or ""
            if old != new:
                changes[field] = {"old": old, "new": new}

        # Body diff with unified diff
        old_body = ver1.get("body") or ""
        new_body = ver2.get("body") or ""
        if old_body != new_body:
            diff_lines = list(difflib.unified_diff(
                old_body.splitlines(keepends=True),
                new_body.splitlines(keepends=True),
                fromfile=f"v{v1}", tofile=f"v{v2}",
            ))
            changes["body"] = {
                "old_length": len(old_body),
                "new_length": len(new_body),
                "diff": "".join(diff_lines),
            }

        # Tags diff
        old_tags = list(ver1.get("tags") or [])
        new_tags = list(ver2.get("tags") or [])
        if old_tags != new_tags:
            changes["tags"] = {
                "added": [t for t in new_tags if t not in old_tags],
                "removed": [t for t in old_tags if t not in new_tags],
            }

        # Metadata diff
        old_meta = ver1.get("metadata") or {}
        new_meta = ver2.get("metadata") or {}
        if old_meta != new_meta:
            changes["metadata"] = {"old": old_meta, "new": new_meta}

        return {
            "content_id": content_id,
            "v1": v1,
            "v2": v2,
            "changes": changes,
            "fields_changed": list(changes.keys()),
        }


# ── Content Links ───────────────────────────────────────────────


@router.get("/{content_id}/links")
async def list_links(content_id: str):
    """Get all content linked to/from this item."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Outgoing links (this content → other)
        outgoing = await conn.fetch(
            """SELECT cl.*, c.title as target_title, c.content_type as target_type,
                      c.status as target_status
               FROM content_links cl
               JOIN content c ON c.id = cl.target_id
               WHERE cl.source_id = $1
               ORDER BY cl.created_at DESC""",
            content_id,
        )

        # Incoming links (other → this content)
        incoming = await conn.fetch(
            """SELECT cl.*, c.title as source_title, c.content_type as source_type,
                      c.status as source_status
               FROM content_links cl
               JOIN content c ON c.id = cl.source_id
               WHERE cl.target_id = $1
               ORDER BY cl.created_at DESC""",
            content_id,
        )

        def _link_to_dict(r):
            d = dict(r)
            for k in ("id", "source_id", "target_id"):
                if d.get(k):
                    d[k] = str(d[k])
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            return d

        return {
            "outgoing": [_link_to_dict(r) for r in outgoing],
            "incoming": [_link_to_dict(r) for r in incoming],
        }


@router.post("/{content_id}/links", status_code=201)
async def create_link(content_id: str, body: LinkCreate):
    """Create a relationship between two content items."""
    if body.link_type not in VALID_LINK_TYPES:
        raise HTTPException(400, f"Invalid link_type. Must be one of: {sorted(VALID_LINK_TYPES)}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verify both exist
        source = await conn.fetchval("SELECT 1 FROM content WHERE id = $1", content_id)
        target = await conn.fetchval("SELECT 1 FROM content WHERE id = $1", body.target_id)
        if not source:
            raise HTTPException(404, "Source content not found")
        if not target:
            raise HTTPException(404, "Target content not found")
        if content_id == body.target_id:
            raise HTTPException(400, "Cannot link content to itself")

        try:
            row = await conn.fetchrow(
                """INSERT INTO content_links (source_id, target_id, link_type, metadata)
                   VALUES ($1, $2, $3, $4::jsonb)
                   RETURNING *""",
                content_id, body.target_id, body.link_type,
                json.dumps(body.metadata),
            )
        except Exception as e:
            if "unique" in str(e).lower():
                raise HTTPException(409, "This link already exists")
            raise

        d = dict(row)
        for k in ("id", "source_id", "target_id"):
            d[k] = str(d[k])
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        return d


@router.delete("/links/{link_id}")
async def delete_link(link_id: str):
    """Delete a content link."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM content_links WHERE id = $1", link_id
        )
        if result == "DELETE 0":
            raise HTTPException(404, "Link not found")
        return {"ok": True, "deleted": link_id}


# ── Data Migration ──────────────────────────────────────────────


@router.post("/migrate-legacy", status_code=200)
async def migrate_legacy_data():
    """One-time migration from articles, social_calendar_posts, project_content.

    Idempotent — skips items whose IDs already exist in the content table.
    """
    pool = await get_pool()
    stats = {"articles": 0, "article_versions": 0, "social_posts": 0, "project_content": 0, "skipped": 0}

    async with pool.acquire() as conn:
        # Get existing content IDs to skip duplicates
        existing_ids = {
            str(r["id"])
            for r in await conn.fetch("SELECT id FROM content")
        }

        # ── 1. Migrate articles ────────────────────────────────
        try:
            articles = await conn.fetch("SELECT * FROM articles ORDER BY created_at")
        except Exception:
            articles = []
            log.info("No articles table found, skipping")

        for a in articles:
            aid = str(a["id"])
            if aid in existing_ids:
                stats["skipped"] += 1
                continue

            meta = {}
            if a.get("platform"):
                meta["platform"] = a["platform"]
            if a.get("publish_date"):
                meta["publish_date"] = str(a["publish_date"])

            published_at = None
            if a["status"] == "posted":
                published_at = a.get("updated_at")

            await conn.execute(
                """INSERT INTO content
                   (id, content_type, project_id, title, body, metadata, status,
                    published_at, tags, version, created_by, created_at, updated_at)
                   VALUES ($1, 'article', $2, $3, $4, $5::jsonb, $6,
                           $7, $8, $9, 'mev', $10, $11)""",
                a["id"], a.get("ecosystem_project"),
                a["title"], a["content"], json.dumps(meta),
                a["status"], published_at,
                list(a.get("tags") or []),
                1,  # will update after migrating versions
                a["created_at"], a["updated_at"],
            )
            stats["articles"] += 1

            # Migrate versions for this article
            try:
                versions = await conn.fetch(
                    """SELECT * FROM article_versions
                       WHERE article_id = $1 ORDER BY version_number""",
                    a["id"],
                )
            except Exception:
                versions = []

            max_ver = 0
            for v in versions:
                await conn.execute(
                    """INSERT INTO content_versions
                       (content_id, version, title, body, change_note, created_at)
                       VALUES ($1, $2, $3, $4, $5, $6)
                       ON CONFLICT (content_id, version) DO NOTHING""",
                    a["id"], v["version_number"],
                    v["title"], v["content"], v.get("note"),
                    v["created_at"],
                )
                stats["article_versions"] += 1
                max_ver = max(max_ver, v["version_number"])

            # Update version counter to max + 1
            if max_ver > 0:
                await conn.execute(
                    "UPDATE content SET version = $1 WHERE id = $2",
                    max_ver + 1, a["id"],
                )

        # ── 2. Migrate social_calendar_posts ────────────────────
        try:
            posts = await conn.fetch("SELECT * FROM social_calendar_posts ORDER BY created_at")
        except Exception:
            posts = []
            log.info("No social_calendar_posts table found, skipping")

        for p in posts:
            pid = str(p["id"])
            if pid in existing_ids:
                stats["skipped"] += 1
                continue

            meta = {}
            if p.get("platforms"):
                meta["platforms"] = list(p["platforms"])
            if p.get("post_type"):
                meta["post_type"] = p["post_type"]
            if p.get("notes"):
                meta["notes"] = p["notes"]

            published_at = None
            if p["status"] == "posted":
                published_at = p.get("updated_at")

            await conn.execute(
                """INSERT INTO content
                   (id, content_type, character, title, body, metadata, status,
                    scheduled_at, published_at, tags, created_by, created_at, updated_at)
                   VALUES ($1, 'social_post', $2, $3, $4, $5::jsonb, $6,
                           $7, $8, $9, 'mev', $10, $11)""",
                p["id"], p.get("character"),
                p.get("title", "Untitled"), p.get("content", ""),
                json.dumps(meta), p["status"],
                p.get("scheduled_at"), published_at,
                list(p.get("tags") or []),
                p["created_at"], p["updated_at"],
            )
            stats["social_posts"] += 1

        # ── 3. Migrate project_content ──────────────────────────
        try:
            pc_rows = await conn.fetch(
                "SELECT *, type::TEXT as type_text FROM project_content ORDER BY created_at"
            )
        except Exception:
            pc_rows = []
            log.info("No project_content table found, skipping")

        for pc in pc_rows:
            pcid = str(pc["id"])
            if pcid in existing_ids:
                stats["skipped"] += 1
                continue

            content_type = pc["type_text"]  # roadmap, article, plan, note, research

            await conn.execute(
                """INSERT INTO content
                   (id, content_type, project_id, title, body, metadata,
                    archived, created_by, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb,
                           $7, 'mev', $8, $9)""",
                pc["id"], content_type, pc["project_id"],
                pc["title"], pc["content"],
                json.dumps(pc.get("metadata") or {}),
                pc["archived"],
                pc["created_at"], pc["updated_at"],
            )
            stats["project_content"] += 1

    log.info("Legacy migration complete: %s", stats)
    return {"ok": True, "stats": stats}

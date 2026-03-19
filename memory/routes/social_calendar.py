"""Social Calendar route — manage scheduled posts, launches, countdowns, and meme drops
per ecosystem character (PiPi, Koink, Otto, etc.).

Status workflow: draft → scheduled → posted | cancelled
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from ..db import get_pool

log = logging.getLogger("otto.social_calendar")

router = APIRouter(prefix="/social-calendar", tags=["social_calendar"])

# ── Pydantic models ─────────────────────────────────────────────────────────

class CreatePost(BaseModel):
    character: str = "pipi"
    title: str = "Untitled"
    content: str = ""
    platforms: List[str] = []
    post_type: str = "post"
    scheduled_at: Optional[str] = None
    status: str = "draft"
    notes: Optional[str] = None
    tags: List[str] = []

class UpdatePost(BaseModel):
    character: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    platforms: Optional[List[str]] = None
    post_type: Optional[str] = None
    scheduled_at: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_dict(row) -> dict:
    d = dict(row)
    for k in ("scheduled_at", "created_at", "updated_at"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d

# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("")
async def list_posts(
    character: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0),
):
    """List social calendar posts, optionally filtered by character and/or status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = ["deleted_at IS NULL"] if False else []
        params: list = []

        where_parts = []
        if character:
            params.append(character)
            where_parts.append(f"character = ${len(params)}")
        if status:
            params.append(status)
            where_parts.append(f"status = ${len(params)}")

        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

        params_count = params.copy()
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM social_calendar_posts {where_clause}",
            *params_count,
        )

        params.extend([limit, offset])
        rows = await conn.fetch(
            f"""SELECT * FROM social_calendar_posts
                {where_clause}
                ORDER BY COALESCE(scheduled_at, created_at) ASC, created_at ASC
                LIMIT ${len(params)-1} OFFSET ${len(params)}""",
            *params,
        )
        return {
            "posts": [_row_to_dict(r) for r in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }


@router.get("/characters")
async def list_characters():
    """List all unique characters that have posts."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT character, COUNT(*) as post_count FROM social_calendar_posts GROUP BY character ORDER BY character"
        )
        return {"characters": [dict(r) for r in rows]}


@router.get("/{post_id}")
async def get_post(post_id: str):
    """Get a single post by ID."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM social_calendar_posts WHERE id = $1", post_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Post not found")
        return _row_to_dict(row)


@router.post("", status_code=201)
async def create_post(body: CreatePost):
    """Create a new social calendar post."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        scheduled_at = None
        if body.scheduled_at:
            try:
                scheduled_at = datetime.fromisoformat(body.scheduled_at.replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid scheduled_at format")

        row = await conn.fetchrow(
            """INSERT INTO social_calendar_posts
               (character, title, content, platforms, post_type, scheduled_at, status, notes, tags)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            body.character,
            body.title,
            body.content,
            body.platforms,
            body.post_type,
            scheduled_at,
            body.status,
            body.notes,
            body.tags,
        )
        log.info("Created social calendar post %s for %s", row["id"], body.character)
        return _row_to_dict(row)


@router.patch("/{post_id}")
async def update_post(post_id: str, body: UpdatePost):
    """Update a social calendar post."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM social_calendar_posts WHERE id = $1", post_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Post not found")

        updates: dict = {}
        if body.character is not None:
            updates["character"] = body.character
        if body.title is not None:
            updates["title"] = body.title
        if body.content is not None:
            updates["content"] = body.content
        if body.platforms is not None:
            updates["platforms"] = body.platforms
        if body.post_type is not None:
            updates["post_type"] = body.post_type
        if body.scheduled_at is not None:
            try:
                updates["scheduled_at"] = datetime.fromisoformat(
                    body.scheduled_at.replace("Z", "+00:00")
                )
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid scheduled_at format")
        if body.status is not None:
            updates["status"] = body.status
        if body.notes is not None:
            updates["notes"] = body.notes
        if body.tags is not None:
            updates["tags"] = body.tags

        if not updates:
            return _row_to_dict(existing)

        updates["updated_at"] = datetime.now(timezone.utc)

        set_parts = [f"{k} = ${i+2}" for i, k in enumerate(updates.keys())]
        values = list(updates.values())

        row = await conn.fetchrow(
            f"UPDATE social_calendar_posts SET {', '.join(set_parts)} WHERE id = $1 RETURNING *",
            post_id, *values,
        )
        return _row_to_dict(row)


@router.delete("/{post_id}", status_code=204)
async def delete_post(post_id: str):
    """Delete a social calendar post."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM social_calendar_posts WHERE id = $1", post_id
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Post not found")

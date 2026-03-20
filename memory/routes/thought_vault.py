"""
Thought Vault API routes.

Dedicated storage for Mev's voice notes and long-form thought dumps.
Auto-capture via Phase 5 hook in ric.py; also supports manual creation.

Endpoints:
  POST   /thought-vault/entries           Create entry (manual)
  GET    /thought-vault/entries           List entries (filter: source, tags, date range)
  GET    /thought-vault/entries/{id}      Single entry detail
  PUT    /thought-vault/entries/{id}      Update tags, cleaned_content, importance
  DELETE /thought-vault/entries/{id}      Soft delete
  POST   /thought-vault/synthesize        Run LLM synthesis → creates synthesis record
  GET    /thought-vault/synthesis         List synthesis records
  GET    /thought-vault/stats             Counts by source, top themes, unprocessed count
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_pool
from ..llm import llm_chat, extract_json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/thought-vault", tags=["thought-vault"])


# ── Pydantic Models ───────────────────────────────────────────────────────────

class EntryCreate(BaseModel):
    raw_content: str
    cleaned_content: Optional[str] = None
    source: str = "manual"
    source_message_id: Optional[str] = None
    importance: int = 5
    tags: List[str] = []


class EntryUpdate(BaseModel):
    cleaned_content: Optional[str] = None
    importance: Optional[int] = None
    tags: Optional[List[str]] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_entry(row) -> dict:
    return {
        "id": str(row["id"]),
        "source": row["source"],
        "source_message_id": row["source_message_id"],
        "raw_content": row["raw_content"],
        "cleaned_content": row["cleaned_content"],
        "importance": row["importance"],
        "tags": list(row["tags"]) if row["tags"] else [],
        "themes": list(row["themes"]) if row["themes"] else [],
        "synthesis_id": str(row["synthesis_id"]) if row["synthesis_id"] else None,
        "processed": row["processed"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _row_to_synthesis(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "summary": row["summary"],
        "themes": list(row["themes"]) if row["themes"] else [],
        "entry_ids": [str(x) for x in row["entry_ids"]] if row["entry_ids"] else [],
        "entry_count": row["entry_count"],
        "model": row["model"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


# ── CRUD: Entries ─────────────────────────────────────────────────────────────

@router.post("/entries", status_code=201)
async def create_entry(body: EntryCreate):
    """Create a thought vault entry."""
    if not body.raw_content.strip():
        raise HTTPException(status_code=400, detail="raw_content is required")
    if not (1 <= body.importance <= 10):
        raise HTTPException(status_code=400, detail="importance must be 1-10")

    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO thought_vault
               (source, source_message_id, raw_content, cleaned_content, importance, tags)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT (source_message_id) DO NOTHING
           RETURNING *""",
        body.source,
        body.source_message_id,
        body.raw_content,
        body.cleaned_content,
        body.importance,
        body.tags,
    )
    if row is None:
        # Duplicate source_message_id — silently return existing
        existing = await pool.fetchrow(
            "SELECT * FROM thought_vault WHERE source_message_id = $1",
            body.source_message_id,
        )
        return _row_to_entry(existing)
    return _row_to_entry(row)


@router.get("/entries")
async def list_entries(
    source: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    processed: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List thought vault entries with optional filters."""
    pool = await get_pool()

    conditions = ["deleted_at IS NULL"]
    params: list = []

    if source:
        params.append(source)
        conditions.append(f"source = ${len(params)}")
    if tag:
        params.append(tag)
        conditions.append(f"$%d = ANY(tags)" % len(params))
    if processed is not None:
        params.append(processed)
        conditions.append(f"processed = ${len(params)}")

    where = " AND ".join(conditions)
    params.extend([limit, offset])

    rows = await pool.fetch(
        f"""SELECT * FROM thought_vault
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${len(params) - 1} OFFSET ${len(params)}""",
        *params,
    )

    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM thought_vault WHERE {where}",
        *params[:-2],
    )

    return {
        "entries": [_row_to_entry(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    """Get single entry detail."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM thought_vault WHERE id = $1 AND deleted_at IS NULL",
        entry_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    return _row_to_entry(row)


@router.put("/entries/{entry_id}")
async def update_entry(entry_id: str, body: EntryUpdate):
    """Update tags, cleaned_content, or importance."""
    pool = await get_pool()
    existing = await pool.fetchrow(
        "SELECT * FROM thought_vault WHERE id = $1 AND deleted_at IS NULL", entry_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Entry not found")

    cleaned = body.cleaned_content if body.cleaned_content is not None else existing["cleaned_content"]
    importance = body.importance if body.importance is not None else existing["importance"]
    tags = body.tags if body.tags is not None else list(existing["tags"])

    if not (1 <= importance <= 10):
        raise HTTPException(status_code=400, detail="importance must be 1-10")

    row = await pool.fetchrow(
        """UPDATE thought_vault
           SET cleaned_content = $1, importance = $2, tags = $3, updated_at = NOW()
           WHERE id = $4
           RETURNING *""",
        cleaned, importance, tags, entry_id,
    )
    return _row_to_entry(row)


@router.delete("/entries/{entry_id}", status_code=204)
async def delete_entry(entry_id: str):
    """Soft delete a thought vault entry."""
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE thought_vault SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL",
        entry_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Entry not found")


# ── Synthesis ─────────────────────────────────────────────────────────────────

@router.post("/synthesize", status_code=201)
async def run_synthesis(limit: int = Query(20, ge=1, le=50)):
    """Run LLM synthesis on unprocessed entries.

    Loads up to `limit` unprocessed entries, asks the LLM to group them by
    theme and write a synthesis summary, then creates a thought_synthesis record
    and marks the entries as processed.
    """
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT * FROM thought_vault
           WHERE processed = FALSE AND deleted_at IS NULL
           ORDER BY created_at ASC
           LIMIT $1""",
        limit,
    )

    if not rows:
        return {"message": "No unprocessed entries found", "synthesis": None}

    # Build numbered entry list for LLM
    entries_text = "\n\n".join(
        f"[{i+1}] (id={row['id']}, source={row['source']}, "
        f"importance={row['importance']}, created={row['created_at'].strftime('%Y-%m-%d')})\n"
        + (row["cleaned_content"] or row["raw_content"])
        for i, row in enumerate(rows)
    )

    prompt = f"""You are reading {len(rows)} thought-dump entries from Mev — voice notes and long-form reflections.

Your job:
1. Identify 2-5 recurring themes across these entries.
2. Write a clear synthesis title (≤10 words).
3. Write a synthesis summary (3-7 paragraphs) capturing the key ideas, tensions, and insights.
4. For each entry, extract 1-3 theme labels (short, lowercase, e.g. "education", "community", "consciousness").

Return ONLY valid JSON:
{{
  "title": "...",
  "summary": "...",
  "themes": ["theme1", "theme2", ...],
  "entry_themes": {{
    "<entry_id>": ["theme1", "theme2"]
  }}
}}

--- ENTRIES ---
{entries_text}
"""

    response = await llm_chat(
        messages=[{"role": "user", "content": prompt}],
        system_instruction="You synthesize raw thought-dumps into structured insights. Be precise and insightful.",
        max_tokens=2000,
        temperature=0.3,
    )

    parsed = extract_json(response)
    if not parsed:
        raise HTTPException(status_code=500, detail="LLM synthesis failed to return valid JSON")

    title = parsed.get("title", "Thought Synthesis")
    summary = parsed.get("summary", response)
    themes = parsed.get("themes", [])
    entry_themes = parsed.get("entry_themes", {})

    entry_ids = [str(r["id"]) for r in rows]

    # Create synthesis record
    synthesis = await pool.fetchrow(
        """INSERT INTO thought_synthesis
               (title, summary, themes, entry_ids, entry_count)
           VALUES ($1, $2, $3, $4::uuid[], $5)
           RETURNING *""",
        title,
        summary,
        themes,
        entry_ids,
        len(entry_ids),
    )

    # Mark entries as processed and update themes + synthesis_id
    async with pool.acquire() as conn:
        async with conn.transaction():
            for row in rows:
                row_id = str(row["id"])
                entry_theme_list = entry_themes.get(row_id, [])
                await conn.execute(
                    """UPDATE thought_vault
                       SET processed = TRUE,
                           synthesis_id = $1,
                           themes = $2,
                           updated_at = NOW()
                       WHERE id = $3""",
                    synthesis["id"],
                    entry_theme_list,
                    row["id"],
                )

    logger.info(f"Thought Vault synthesis created: {title} ({len(entry_ids)} entries)")
    return {
        "message": f"Synthesis complete: {len(entry_ids)} entries processed",
        "synthesis": _row_to_synthesis(synthesis),
    }


@router.get("/synthesis")
async def list_synthesis(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List synthesis records."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT * FROM thought_synthesis
           WHERE deleted_at IS NULL
           ORDER BY created_at DESC
           LIMIT $1 OFFSET $2""",
        limit, offset,
    )
    total = await pool.fetchval(
        "SELECT COUNT(*) FROM thought_synthesis WHERE deleted_at IS NULL"
    )
    return {
        "synthesis": [_row_to_synthesis(r) for r in rows],
        "total": total,
    }


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Counts by source, top themes, unprocessed count."""
    pool = await get_pool()

    total = await pool.fetchval(
        "SELECT COUNT(*) FROM thought_vault WHERE deleted_at IS NULL"
    )
    unprocessed = await pool.fetchval(
        "SELECT COUNT(*) FROM thought_vault WHERE processed = FALSE AND deleted_at IS NULL"
    )
    synthesis_count = await pool.fetchval(
        "SELECT COUNT(*) FROM thought_synthesis WHERE deleted_at IS NULL"
    )

    by_source = await pool.fetch(
        """SELECT source, COUNT(*) as count
           FROM thought_vault
           WHERE deleted_at IS NULL
           GROUP BY source
           ORDER BY count DESC""",
    )

    # Top themes from entries
    top_themes = await pool.fetch(
        """SELECT unnest(themes) as theme, COUNT(*) as count
           FROM thought_vault
           WHERE deleted_at IS NULL AND array_length(themes, 1) > 0
           GROUP BY theme
           ORDER BY count DESC
           LIMIT 10""",
    )

    return {
        "total": total,
        "unprocessed": unprocessed,
        "synthesis_count": synthesis_count,
        "by_source": [{"source": r["source"], "count": r["count"]} for r in by_source],
        "top_themes": [{"theme": r["theme"], "count": r["count"]} for r in top_themes],
    }

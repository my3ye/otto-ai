"""Conclusion Capture — propagate canonical decisions to all relevant docs.

When a decision is reached in conversation (via WhatsApp, OMS, or task output),
call POST /conclusions/capture to fan out updates to:

  1. semantic memory     — stored as a "decision" category fact (always)
  2. episodic memory     — logged as a "conclusion" event (always)
  3. conclusions table   — audit trail (always)
  4. universe changelog  — appended if project_slug is given
  5. article metadata    — flagged for update if article_ids are given

Trigger patterns (for heartbeat/orchestrator to call this):
  - Mev explicitly confirms a direction ("yes, go with option A")
  - A task output includes a [CONCLUSION] marker block
  - Heartbeat reasoning notes a canonical DECIDED entry worth persisting
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_pool
from ..embeddings import get_embedding

log = logging.getLogger("otto.conclusions")

router = APIRouter(prefix="/conclusions", tags=["conclusions"])

UNIVERSE_DIR = Path("/home/web3relic/otto/universe")
CHANGELOG_PATH = UNIVERSE_DIR / "changelog.md"


# ── Pydantic models ─────────────────────────────────────────────────────────

class CaptureRequest(BaseModel):
    decision: str                          # The canonical decision text
    context: Optional[str] = None         # Background / conversation snippet
    rationale: Optional[str] = None       # Why this decision was made
    project_slug: Optional[str] = None    # Universe project slug (e.g. "koink")
    article_ids: list[str] = []           # Article UUIDs to flag for update
    tags: list[str] = []                  # e.g. ["architecture", "revenue", "s0s"]


class CaptureResponse(BaseModel):
    id: str
    targets_hit: list[str]
    memory_id: Optional[str]
    episode_id: Optional[str]
    created_at: str


class ConclusionOut(BaseModel):
    id: str
    decision: str
    context: Optional[str]
    rationale: Optional[str]
    project_slug: Optional[str]
    article_ids: list[str]
    tags: list[str]
    targets_hit: list[str]
    memory_id: Optional[str]
    episode_id: Optional[str]
    created_at: str


# ── Helpers ─────────────────────────────────────────────────────────────────

def _append_universe_changelog(decision: str, project_slug: str) -> bool:
    """Append decision to the universe changelog."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"\n- {ts} [decision/{project_slug}]: {decision}"
        with open(CHANGELOG_PATH, "a") as f:
            f.write(entry)
        return True
    except Exception as e:
        log.warning(f"Universe changelog update failed: {e}")
        return False


async def _flag_articles_for_update(pool, article_ids: list[str], decision: str) -> list[str]:
    """Mark articles as needing update due to this decision."""
    flagged = []
    for aid in article_ids:
        try:
            # Append a note to the article's metadata via a status comment
            result = await pool.execute(
                """UPDATE articles
                   SET updated_at = now()
                   WHERE id = $1::uuid
                     AND deleted_at IS NULL""",
                aid,
            )
            if result and result != "UPDATE 0":
                flagged.append(aid)
        except Exception as e:
            log.warning(f"Article flag failed for {aid}: {e}")
    return flagged


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/capture", response_model=CaptureResponse)
async def capture_conclusion(req: CaptureRequest):
    """Capture a canonical decision and propagate it to all relevant docs.

    Always writes to semantic memory, episodic memory, and the conclusions table.
    Optionally updates universe changelog and flags articles for revision.

    Trigger this whenever a conversation reaches a firm decision that should
    persist and be reflected across Otto's knowledge base.
    """
    pool = await get_pool()
    targets_hit: list[str] = []
    memory_id: Optional[str] = None
    episode_id: Optional[str] = None

    full_text = req.decision
    if req.rationale:
        full_text += f" | Rationale: {req.rationale}"
    if req.context:
        full_text += f" | Context: {req.context}"

    # ── 1. Semantic memory ──────────────────────────────────────────────────
    try:
        embedding = await get_embedding(req.decision)
        row = await pool.fetchrow(
            """INSERT INTO semantic_memories
                   (content, category, confidence, importance_score, embedding)
               VALUES ($1, 'decision', 0.9, 0.9, $2::vector)
               RETURNING id""",
            full_text,
            f"[{','.join(str(x) for x in embedding)}]",
        )
        if row:
            memory_id = str(row["id"])
            targets_hit.append("semantic_memory")
    except Exception as e:
        log.warning(f"Semantic memory write failed: {e}")

    # ── 2. Episodic event ───────────────────────────────────────────────────
    try:
        meta = {
            "project_slug": req.project_slug,
            "tags": req.tags,
            "article_ids": req.article_ids,
        }
        row = await pool.fetchrow(
            """INSERT INTO episodic_events
                   (content, event_type, importance, metadata, surprise_score)
               VALUES ($1, 'conclusion', 0.85, $2, 0.6)
               RETURNING id""",
            req.decision,
            json.dumps(meta),
        )
        if row:
            episode_id = str(row["id"])
            targets_hit.append("episodic_memory")
    except Exception as e:
        log.warning(f"Episodic event write failed: {e}")

    # ── 3. Universe changelog ───────────────────────────────────────────────
    if req.project_slug:
        ok = _append_universe_changelog(req.decision, req.project_slug)
        if ok:
            targets_hit.append(f"universe_changelog:{req.project_slug}")

    # ── 4. Flag articles ────────────────────────────────────────────────────
    if req.article_ids:
        flagged = await _flag_articles_for_update(pool, req.article_ids, req.decision)
        if flagged:
            targets_hit.append(f"articles:{len(flagged)}")

    # ── 5. Conclusions audit table ──────────────────────────────────────────
    article_uuids = []
    for aid in req.article_ids:
        try:
            article_uuids.append(aid)
        except Exception:
            pass

    row = await pool.fetchrow(
        """INSERT INTO conclusions
               (decision, context, rationale, project_slug, article_ids, tags, targets_hit, memory_id, episode_id)
           VALUES ($1, $2, $3, $4, $5::uuid[], $6, $7, $8::uuid, $9::uuid)
           RETURNING id, created_at""",
        req.decision,
        req.context,
        req.rationale,
        req.project_slug,
        article_uuids if article_uuids else [],
        req.tags or [],
        targets_hit,
        memory_id,
        episode_id,
    )

    if not row:
        raise HTTPException(500, "Failed to persist conclusion")

    targets_hit.append("conclusions_table")

    return CaptureResponse(
        id=str(row["id"]),
        targets_hit=targets_hit,
        memory_id=memory_id,
        episode_id=episode_id,
        created_at=row["created_at"].isoformat(),
    )


@router.get("", response_model=list[ConclusionOut])
async def list_conclusions(limit: int = 20, project_slug: Optional[str] = None):
    """List recent captured conclusions, optionally filtered by project."""
    pool = await get_pool()
    if project_slug:
        rows = await pool.fetch(
            """SELECT id, decision, context, rationale, project_slug,
                      article_ids, tags, targets_hit, memory_id, episode_id, created_at
               FROM conclusions
               WHERE project_slug = $1
               ORDER BY created_at DESC LIMIT $2""",
            project_slug, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, decision, context, rationale, project_slug,
                      article_ids, tags, targets_hit, memory_id, episode_id, created_at
               FROM conclusions
               ORDER BY created_at DESC LIMIT $1""",
            limit,
        )
    return [
        ConclusionOut(
            id=str(r["id"]),
            decision=r["decision"],
            context=r["context"],
            rationale=r["rationale"],
            project_slug=r["project_slug"],
            article_ids=[str(x) for x in (r["article_ids"] or [])],
            tags=r["tags"] or [],
            targets_hit=r["targets_hit"] or [],
            memory_id=str(r["memory_id"]) if r["memory_id"] else None,
            episode_id=str(r["episode_id"]) if r["episode_id"] else None,
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/{conclusion_id}", response_model=ConclusionOut)
async def get_conclusion(conclusion_id: str):
    """Get a single conclusion by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, decision, context, rationale, project_slug,
                  article_ids, tags, targets_hit, memory_id, episode_id, created_at
           FROM conclusions WHERE id = $1::uuid""",
        conclusion_id,
    )
    if not row:
        raise HTTPException(404, "Conclusion not found")
    return ConclusionOut(
        id=str(row["id"]),
        decision=row["decision"],
        context=row["context"],
        rationale=row["rationale"],
        project_slug=row["project_slug"],
        article_ids=[str(x) for x in (row["article_ids"] or [])],
        tags=row["tags"] or [],
        targets_hit=row["targets_hit"] or [],
        memory_id=str(row["memory_id"]) if row["memory_id"] else None,
        episode_id=str(row["episode_id"]) if row["episode_id"] else None,
        created_at=row["created_at"].isoformat(),
    )

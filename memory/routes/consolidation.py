"""
Memory consolidation system.

POST /memory/consolidate — run full consolidation (called by reflection heartbeat).

Three operations:
1. Semantic dedup: find near-duplicate semantic memories (cosine > 0.92) and
   archive the weaker copy.
2. Episodic summarization: events older than 7 days get grouped into daily
   summaries via Gemini Flash, originals are marked consolidated.
3. Stale detection: old memories with temporal language + low relevance get
   flagged or archived.

Audit trail: each run logs a consolidation_audit episodic event with counts.
"""

import asyncio
import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings
from ..db import get_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["consolidation"])

# Temporal language patterns that suggest a memory may contain outdated info.
_STALE_PATTERNS = re.compile(
    r"\b(currently|right now|as of today|this week|this month|"
    r"at present|at this time|ongoing|in progress|pending|active|"
    r"running|queued|latest|just yesterday|today)\b",
    re.IGNORECASE,
)

# Cosine similarity threshold for duplicate detection.
_DEDUP_THRESHOLD = 0.92


class ConsolidationResult(BaseModel):
    dupes_found: int
    dupes_archived: int
    events_summarized: int
    summaries_created: int
    stale_flagged: int
    stale_archived: int
    ran_at: datetime


# ── Gemini Flash helper ───────────────────────────────────────────────────────

def _get_gemini_model():
    import google.generativeai as genai  # lazy import
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config={"temperature": 0.1},
    )


async def _gemini_summarize(events_text: str) -> str | None:
    """Summarize a batch of episodic events into 2-3 sentences."""
    prompt = (
        "You are an AI memory assistant. Summarize the following episodic events "
        "into 2-3 sentences capturing key facts, decisions, and outcomes. "
        "Be concrete and omit trivial details.\n\n"
        f"Events:\n{events_text}\n\n"
        "Return only the summary text (no JSON, no headers)."
    )
    try:
        model = _get_gemini_model()
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        return text if text else None
    except Exception as e:
        logger.warning(f"Gemini summarization failed: {e}")
        return None


# ── 1. Semantic dedup ─────────────────────────────────────────────────────────

async def run_semantic_dedup() -> tuple[int, int]:
    """
    Find near-duplicate semantic memories (cosine similarity > 0.92) and
    archive the weaker copy (lower confidence; ties broken by newer = archive).

    Uses HNSW index via a nearest-neighbor lookup per memory.

    Returns (dupes_found, dupes_archived).
    """
    pool = await get_pool()

    # Fetch all non-archived memories with their halfvec embeddings as text.
    # We cast halfvec to text so we can pass it back as a query vector.
    all_rows = await pool.fetch(
        """SELECT id, content, confidence, category,
                  embedding_hv::text AS embedding_str
           FROM semantic_memories
           WHERE archived = FALSE AND embedding_hv IS NOT NULL
           ORDER BY created_at ASC"""
    )

    if len(all_rows) < 2:
        return 0, 0

    to_archive: set = set()   # IDs to archive at the end
    seen_pairs: set = set()   # (min_id_str, max_id_str) — avoid double-counting
    dupes_found = 0

    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")

        for row in all_rows:
            rid = row["id"]

            # If we've already decided this memory is going away, skip.
            if rid in to_archive:
                continue

            # Find nearest neighbor using HNSW index.
            similar = await conn.fetchrow(
                """SELECT id, confidence, created_at,
                          1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                   FROM semantic_memories
                   WHERE id != $2
                     AND archived = FALSE
                     AND embedding_hv IS NOT NULL
                   ORDER BY embedding_hv <=> $1::halfvec(1536)
                   LIMIT 1""",
                row["embedding_str"], rid,
            )

            if not similar:
                continue

            sim = float(similar["similarity"])
            if sim < _DEDUP_THRESHOLD:
                continue

            other_id = similar["id"]

            # Deduplicate pair processing (A→B and B→A are the same pair).
            pair_key = (min(str(rid), str(other_id)), max(str(rid), str(other_id)))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            dupes_found += 1

            # Archive the weaker copy. Tie-break: archive the newer one.
            if float(row["confidence"]) >= float(similar["confidence"]):
                to_archive.add(other_id)
                logger.debug(
                    f"Dedup: archive {other_id} (sim={sim:.3f}, kept={rid})"
                )
            else:
                to_archive.add(rid)
                logger.debug(
                    f"Dedup: archive {rid} (sim={sim:.3f}, kept={other_id})"
                )

        if to_archive:
            await conn.execute(
                """UPDATE semantic_memories
                   SET archived = TRUE, updated_at = NOW()
                   WHERE id = ANY($1::uuid[])""",
                list(to_archive),
            )

    dupes_archived = len(to_archive)
    logger.info(
        f"Semantic dedup: {dupes_found} pairs found, {dupes_archived} archived"
    )
    return dupes_found, dupes_archived


# ── 2. Episodic summarization ─────────────────────────────────────────────────

async def run_episodic_summarization() -> tuple[int, int]:
    """
    Summarize unconsolidated episodic events older than 7 days.

    Groups events by UTC date, generates a 2-3 sentence summary per day via
    Gemini Flash, inserts a new summary event, marks originals consolidated.

    Returns (events_summarized, summaries_created).
    """
    if not settings.gemini_api_key:
        logger.warning("Episodic summarization skipped: no Gemini API key")
        return 0, 0

    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, session_id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE consolidated = FALSE
             AND created_at < NOW() - INTERVAL '7 days'
           ORDER BY created_at ASC
           LIMIT 500"""
    )

    if not rows:
        return 0, 0

    # Group by UTC date (YYYY-MM-DD).
    day_groups: dict[str, list] = {}
    for row in rows:
        day_key = row["created_at"].strftime("%Y-%m-%d")
        day_groups.setdefault(day_key, []).append(dict(row))

    events_summarized = 0
    summaries_created = 0

    for day, events in day_groups.items():
        lines = [
            f"[{e['event_type']}|imp={e['importance']}] {e['content'][:300]}"
            for e in events
        ]
        events_text = f"Date: {day}\n" + "\n".join(lines)

        summary = await _gemini_summarize(events_text)
        if not summary:
            logger.warning(f"Summarization returned empty for {day}, skipping")
            continue

        summary_content = f"[Daily summary {day}] {summary}"
        meta = json.dumps({
            "source": "episodic_summarization",
            "original_count": len(events),
            "date": day,
        })

        # Insert compressed summary event (pre-marked as consolidated).
        await pool.execute(
            """INSERT INTO episodic_events
                   (content, event_type, importance, consolidated, metadata)
               VALUES ($1, 'summary', 6, TRUE, $2::jsonb)""",
            summary_content, meta,
        )

        # Mark originals as consolidated and store summary text in their row.
        event_ids = [e["id"] for e in events]
        await pool.execute(
            """UPDATE episodic_events
               SET consolidated = TRUE, summary = $1
               WHERE id = ANY($2::uuid[])""",
            summary, event_ids,
        )

        events_summarized += len(events)
        summaries_created += 1
        logger.info(
            f"Episodic summarization: {len(events)} events from {day} → 1 summary"
        )

    return events_summarized, summaries_created


# ── 3. Stale memory detection ─────────────────────────────────────────────────

async def run_stale_detection() -> tuple[int, int]:
    """
    Detect semantic memories likely containing outdated information.

    Criteria:
    - Older than 14 days
    - relevance_score < 0.6
    - Contains temporal/status language (currently, running, pending, etc.)
    - Not in protected categories (identity, infrastructure)

    Action:
    - relevance_score < 0.3 → archive immediately
    - relevance_score 0.3–0.6 → reduce confidence to min(conf, 0.3) + decay relevance

    Returns (stale_flagged, stale_archived).
    """
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, content, confidence, relevance_score
           FROM semantic_memories
           WHERE archived = FALSE
             AND created_at < NOW() - INTERVAL '14 days'
             AND relevance_score < 0.6
             AND category NOT IN ('identity', 'infrastructure')
           ORDER BY relevance_score ASC
           LIMIT 200"""
    )

    if not rows:
        return 0, 0

    flag_ids: list = []    # reduce confidence + decay
    archive_ids: list = [] # archive immediately

    for row in rows:
        if not _STALE_PATTERNS.search(row["content"]):
            continue
        if float(row["relevance_score"]) < 0.3:
            archive_ids.append(row["id"])
        else:
            flag_ids.append(row["id"])

    if flag_ids:
        await pool.execute(
            """UPDATE semantic_memories
               SET confidence = LEAST(confidence, 0.3),
                   relevance_score = relevance_score * 0.8,
                   updated_at = NOW()
               WHERE id = ANY($1::uuid[])""",
            flag_ids,
        )
        logger.info(f"Stale detection: {len(flag_ids)} flagged (confidence reduced)")

    if archive_ids:
        await pool.execute(
            """UPDATE semantic_memories
               SET archived = TRUE, updated_at = NOW()
               WHERE id = ANY($1::uuid[])""",
            archive_ids,
        )
        logger.info(
            f"Stale detection: {len(archive_ids)} archived (very low relevance)"
        )

    return len(flag_ids), len(archive_ids)


# ── Audit log ─────────────────────────────────────────────────────────────────

async def _log_consolidation_audit(result: ConsolidationResult) -> None:
    """Log this consolidation run as an episodic event for audit trail."""
    pool = await get_pool()
    summary = (
        f"Memory consolidation: "
        f"dedup {result.dupes_archived}/{result.dupes_found} archived, "
        f"episodic {result.events_summarized}→{result.summaries_created} summaries, "
        f"stale {result.stale_flagged} flagged/{result.stale_archived} archived"
    )
    meta = json.dumps({
        "source": "memory_consolidation",
        "dupes_found": result.dupes_found,
        "dupes_archived": result.dupes_archived,
        "events_summarized": result.events_summarized,
        "summaries_created": result.summaries_created,
        "stale_flagged": result.stale_flagged,
        "stale_archived": result.stale_archived,
    })
    await pool.execute(
        """INSERT INTO episodic_events
               (content, event_type, importance, consolidated, metadata)
           VALUES ($1, 'consolidation_audit', 4, TRUE, $2::jsonb)""",
        summary, meta,
    )


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/consolidate", response_model=ConsolidationResult)
async def run_consolidation():
    """
    Run the full memory consolidation pipeline:
    1. Semantic dedup — archive near-duplicate semantic memories (cosine > 0.92)
    2. Episodic summarization — compress old events (>7 days) into daily summaries
    3. Stale detection — flag/archive outdated temporal-language memories

    Called by the reflection heartbeat at :30. Also callable manually.
    """
    dupes_found, dupes_archived = await run_semantic_dedup()
    events_summarized, summaries_created = await run_episodic_summarization()
    stale_flagged, stale_archived = await run_stale_detection()

    result = ConsolidationResult(
        dupes_found=dupes_found,
        dupes_archived=dupes_archived,
        events_summarized=events_summarized,
        summaries_created=summaries_created,
        stale_flagged=stale_flagged,
        stale_archived=stale_archived,
        ran_at=datetime.now(timezone.utc),
    )

    await _log_consolidation_audit(result)

    logger.info(
        f"Consolidation complete: dedup={dupes_archived}, "
        f"summarized={events_summarized}, stale_archived={stale_archived}"
    )
    return result

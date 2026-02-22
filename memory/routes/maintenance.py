"""
Memory maintenance: nightly decay + episodic consolidation.

POST /memory/maintenance — run decay and consolidation immediately.
Also called by the APScheduler nightly job (02:00 LKT = 20:30 UTC).
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["maintenance"])


class MaintenanceResult(BaseModel):
    decay_updated: int
    archived: int
    events_consolidated: int
    facts_stored: int
    scratch_consolidated: bool
    ran_at: datetime


class SalienceDecayResult(BaseModel):
    updated: int
    ran_at: datetime


class EvolveResult(BaseModel):
    decay_updated: int
    archived: int
    scratch_consolidated: bool
    short_horizon_compressed: int
    short_horizon_facts: int
    events_consolidated: int
    facts_stored: int
    dupes_archived: int
    critique_refined: int
    reme_evolved: int  # ReMe: memories confidence-boosted or accelerated-decayed
    ttl_expired: int   # AgeMem: memories hard-deleted due to expired TTL
    ran_at: datetime


# ── Gemini Flash helper ────────────────────────────────────────────────────────

def _get_gemini_model():
    import google.generativeai as genai  # lazy import to avoid startup errors
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config={"temperature": 0.1},
    )


async def _gemini_extract_facts(events_text: str) -> list[dict]:
    """Call Gemini Flash to extract permanent facts from episodic events.

    Returns list of {content, category, confidence} dicts. Empty list on failure.
    """
    prompt = (
        "You are an AI memory assistant. Extract permanent facts from these episodic events "
        "that are worth storing in long-term memory.\n\n"
        f"Events:\n{events_text}\n\n"
        "Return a JSON array (only the array, no markdown) of 0-5 facts. "
        "Each object: {\"content\": \"<1-2 sentence fact>\", "
        "\"category\": \"<one of: infrastructure, brand, mission, goal, decision, observation, "
        "market_research, research, pipeline_status>\", \"confidence\": <0.5-1.0>}. "
        "Skip trivial, obvious, or duplicate facts. Return [] if nothing is worth storing."
    )
    try:
        model = _get_gemini_model()
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        facts = json.loads(text)
        if not isinstance(facts, list):
            return []
        return facts
    except Exception as e:
        logger.warning(f"Gemini extraction failed: {e}")
        return []


# ── Decay ──────────────────────────────────────────────────────────────────────

async def run_decay() -> tuple[int, int]:
    """Apply relevance decay and archive low-score memories.

    Returns (decay_updated, archived).
    """
    pool = await get_pool()

    # Decay: relevance_score *= 0.99 for non-identity/infrastructure facts
    # not retrieved in 7+ days
    decay_result = await pool.execute(
        """UPDATE semantic_memories
           SET relevance_score = GREATEST(0.1, relevance_score * 0.99),
               updated_at = NOW()
           WHERE (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '7 days')
             AND category NOT IN ('identity', 'infrastructure')
             AND archived = FALSE"""
    )
    decay_updated = int(decay_result.split()[-1])

    # Archive: very low score facts that aren't identity/infrastructure
    archive_result = await pool.execute(
        """UPDATE semantic_memories
           SET archived = TRUE,
               updated_at = NOW()
           WHERE relevance_score < 0.3
             AND utility_score < 0.3
             AND archived = FALSE
             AND category NOT IN ('identity', 'infrastructure')"""
    )
    archived = int(archive_result.split()[-1])

    logger.info(f"Decay: {decay_updated} updated, {archived} archived")
    return decay_updated, archived


# ── Consolidation ──────────────────────────────────────────────────────────────

async def run_consolidation() -> tuple[int, int]:
    """Consolidate unconsolidated episodic events into semantic memories.

    Groups events by session, calls Gemini Flash to extract facts,
    deduplicates via cosine similarity (> 0.92 = skip), stores new facts.

    Returns (events_consolidated, facts_stored).
    """
    if not settings.gemini_api_key:
        logger.warning("Consolidation skipped: no Gemini API key configured")
        return 0, 0

    pool = await get_pool()

    # Pull unconsolidated events (max 200 to keep prompt manageable)
    rows = await pool.fetch(
        """SELECT id, session_id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE consolidated = FALSE
           ORDER BY created_at ASC
           LIMIT 200"""
    )
    if not rows:
        return 0, 0

    # Group by session
    sessions: dict[str, list] = {}
    for row in rows:
        sid = str(row["session_id"]) if row["session_id"] else "no_session"
        sessions.setdefault(sid, []).append(dict(row))

    events_consolidated = 0
    facts_stored = 0

    for sid, events in sessions.items():
        # Build a compact text block for Gemini
        lines = [
            f"[{e['event_type']}] importance={e['importance']}: {e['content'][:400]}"
            for e in events
        ]
        events_text = "\n".join(lines)

        # Extract facts
        facts = await _gemini_extract_facts(events_text)

        for fact in facts[:5]:
            content = str(fact.get("content", "")).strip()
            category = str(fact.get("category", "observation"))
            confidence = float(fact.get("confidence", 0.7))
            confidence = max(0.5, min(1.0, confidence))

            if not content or len(content) < 10:
                continue

            try:
                # Get embedding for dedup check
                embedding = await get_embedding(content)
                embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

                async with pool.acquire() as conn:
                    # Check for near-duplicate (cosine similarity > 0.92)
                    await conn.execute("SET hnsw.iterative_scan = relaxed_order")
                    similar = await conn.fetchrow(
                        """SELECT 1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                           FROM semantic_memories
                           WHERE embedding_hv IS NOT NULL AND archived = FALSE
                           ORDER BY embedding_hv <=> $1::halfvec(1536)
                           LIMIT 1""",
                        embedding_str,
                    )

                    if similar and float(similar["similarity"]) > 0.92:
                        logger.debug(f"Dedup skip (sim={similar['similarity']:.3f}): {content[:60]}")
                        continue

                    # Insert new fact
                    await conn.execute(
                        """INSERT INTO semantic_memories
                               (content, category, confidence, source, embedding, embedding_hv, metadata)
                           VALUES ($1, $2, $3, 'consolidation', $4::vector, $4::halfvec(1536), '{}')""",
                        content, category, confidence, embedding_str,
                    )
                    facts_stored += 1
                    logger.info(f"Stored fact [{category}]: {content[:80]}")

            except Exception as e:
                logger.warning(f"Failed to store fact: {e}")

        # Mark events as consolidated
        event_ids = [e["id"] for e in events]
        await pool.execute(
            "UPDATE episodic_events SET consolidated = TRUE WHERE id = ANY($1::uuid[])",
            event_ids,
        )
        events_consolidated += len(events)

    logger.info(f"Consolidation: {events_consolidated} events, {facts_stored} new facts")
    return events_consolidated, facts_stored


# ── Scratch consolidation ──────────────────────────────────────────────────────

async def consolidate_scratch() -> bool:
    """If working memory scratch slot has content, flush it to episodic events.

    Clears scratch after storing. Returns True if content was flushed.
    """
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT content FROM core_memory WHERE slot = 'scratch'"
    )
    if not row or not row["content"].strip():
        return False

    scratch = row["content"].strip()
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance, metadata)
           VALUES ($1, 'observation', 5, '{"source": "scratch_consolidation"}'::jsonb)""",
        f"[scratch] {scratch}",
    )
    await pool.execute(
        "UPDATE core_memory SET content = '', updated_at = NOW() WHERE slot = 'scratch'"
    )
    logger.info(f"Scratch flushed to episodic ({len(scratch)} chars)")
    return True


# ── Maintenance endpoint ───────────────────────────────────────────────────────

@router.post("/maintenance", response_model=MaintenanceResult)
async def run_maintenance():
    """Run full memory maintenance cycle:
    1. Relevance decay on stale semantic memories
    2. Archive very-low-score memories
    3. Consolidate scratch slot → episodic events
    4. Consolidate episodic events → semantic facts (via Gemini Flash)
    """
    decay_updated, archived = await run_decay()
    scratch_consolidated = await consolidate_scratch()
    events_consolidated, facts_stored = await run_consolidation()

    return MaintenanceResult(
        decay_updated=decay_updated,
        archived=archived,
        events_consolidated=events_consolidated,
        facts_stored=facts_stored,
        scratch_consolidated=scratch_consolidated,
        ran_at=datetime.now(timezone.utc),
    )


async def run_maintenance_job():
    """Background job entrypoint — called by APScheduler. Logs result."""
    try:
        result = await run_maintenance()
        logger.info(
            f"Nightly maintenance complete: decay={result.decay_updated}, "
            f"archived={result.archived}, consolidated={result.events_consolidated}, "
            f"new_facts={result.facts_stored}"
        )
    except Exception as e:
        logger.error(f"Nightly maintenance failed: {e}", exc_info=True)


# ── BMAM: Salience Decay ──────────────────────────────────────────────────────

@router.post("/salience-decay", response_model=SalienceDecayResult)
async def run_salience_decay():
    """BMAM: decay salience scores for memories not accessed in 3+ days.

    Implements the forgetting curve from BMAM (arxiv 2601.20465):
    - For each eligible memory, applies: salience *= 0.95 ^ days_since_last_access
    - Eligibility: not archived, not deleted, last_retrieved_at (or created_at) < 3 days ago
    - Floor: 0.05 (memories are never fully forgotten, just deprioritized)

    Call from the reflection heartbeat to keep salience scores current.
    """
    pool = await get_pool()

    result = await pool.execute(
        """UPDATE semantic_memories
           SET salience_score = GREATEST(
               0.05,
               salience_score * POWER(
                   0.95,
                   GREATEST(
                       0.0,
                       EXTRACT(EPOCH FROM (
                           NOW() - COALESCE(last_retrieved_at, created_at)
                       )) / 86400.0 - 3.0
                   )
               )
           ),
           updated_at = NOW()
           WHERE archived = FALSE
             AND deleted_at IS NULL
             AND COALESCE(last_retrieved_at, created_at) < NOW() - INTERVAL '3 days'"""
    )
    updated = int(result.split()[-1])
    logger.info(f"BMAM salience decay: {updated} memories updated")

    return SalienceDecayResult(updated=updated, ran_at=datetime.now(timezone.utc))


# ── Short-horizon episodic compression ────────────────────────────────────────

async def run_short_horizon_compression() -> tuple[int, int]:
    """Compress low-importance episodic events older than 48 hours into semantic memories.

    Targets events with importance < 5 that haven't been consolidated yet.
    Uses Gemini Flash to extract permanent facts; deduplicates via cosine > 0.92.
    Marks originals as consolidated after extraction.

    Returns (events_compressed, facts_stored).
    """
    if not settings.gemini_api_key:
        logger.warning("Short-horizon compression skipped: no Gemini API key")
        return 0, 0

    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE consolidated = FALSE
             AND importance < 5
             AND created_at < NOW() - INTERVAL '48 hours'
           ORDER BY created_at ASC
           LIMIT 300"""
    )

    if not rows:
        return 0, 0

    lines = [
        f"[{e['event_type']}|imp={e['importance']}] {e['content'][:300]}"
        for e in rows
    ]
    events_text = "\n".join(lines)

    facts = await _gemini_extract_facts(events_text)
    facts_stored = 0

    for fact in facts[:8]:
        content = str(fact.get("content", "")).strip()
        category = str(fact.get("category", "observation"))
        confidence = float(fact.get("confidence", 0.7))
        confidence = max(0.5, min(1.0, confidence))

        if not content or len(content) < 10:
            continue

        try:
            embedding = await get_embedding(content)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            async with pool.acquire() as conn:
                await conn.execute("SET hnsw.iterative_scan = relaxed_order")
                similar = await conn.fetchrow(
                    """SELECT 1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                       FROM semantic_memories
                       WHERE embedding_hv IS NOT NULL AND archived = FALSE AND deleted_at IS NULL
                       ORDER BY embedding_hv <=> $1::halfvec(1536)
                       LIMIT 1""",
                    embedding_str,
                )

                if similar and float(similar["similarity"]) > 0.92:
                    logger.debug(f"Short-horizon dedup skip (sim={similar['similarity']:.3f}): {content[:60]}")
                    continue

                await conn.execute(
                    """INSERT INTO semantic_memories
                           (content, category, confidence, source, embedding, embedding_hv, metadata)
                       VALUES ($1, $2, $3, 'short_horizon_compression', $4::vector, $4::halfvec(1536), '{}')""",
                    content, category, confidence, embedding_str,
                )
                facts_stored += 1
                logger.info(f"Short-horizon fact [{category}]: {content[:80]}")

        except Exception as e:
            logger.warning(f"Short-horizon compression fact failed: {e}")

    event_ids = [e["id"] for e in rows]
    await pool.execute(
        "UPDATE episodic_events SET consolidated = TRUE WHERE id = ANY($1::uuid[])",
        event_ids,
    )

    logger.info(f"Short-horizon compression: {len(rows)} events → {facts_stored} facts")
    return len(rows), facts_stored


# ── Critique-driven memory refinement ────────────────────────────────────────

async def _gemini_critique_memories(memories: list[dict]) -> list[dict]:
    """Use Gemini Flash to critique low-quality memories.

    From CRITIC (Gou et al. ICLR 2024) + Reflection-Tuning: ground evaluation in
    structured scoring rather than subjective judgement.

    Returns list of {id, accuracy, relevance, utility, action, reason} dicts.
    action: 'archive' | 'boost' | 'keep'
    """
    prompt = (
        "You are an AI memory curator. Critique these stored memories for quality.\n\n"
        "For each memory, score on 3 dimensions (1-5 each):\n"
        "- ACCURACY: Is this still likely true and not outdated? "
        "(5=definitely true/current, 1=likely stale/wrong)\n"
        "- RELEVANCE: Is this relevant to an AI agent building systems? "
        "(5=highly relevant, 1=trivial noise)\n"
        "- UTILITY: Would recalling this improve future decisions? "
        "(5=very useful, 1=useless)\n\n"
        "Memories to evaluate:\n"
    )
    for m in memories:
        prompt += f"\nID={m['id']}: {m['content'][:250]}\n"

    prompt += (
        "\n\nReturn a JSON array (only the array, no markdown). Each object:\n"
        '{"id": "<uuid>", "accuracy": <1-5>, "relevance": <1-5>, "utility": <1-5>, '
        '"action": "<archive|boost|keep>", "reason": "<one sentence>"}\n'
        "action=archive if any score is 1 OR average < 2.0. "
        "action=boost if all scores >= 4. "
        "action=keep otherwise."
    )
    try:
        model = _get_gemini_model()
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text)
        if not isinstance(result, list):
            return []
        return result
    except Exception as e:
        logger.warning(f"Memory critique failed: {e}")
        return []


async def run_critique_refinement() -> int:
    """Critique low-quality memories and refine scores.

    Implements critique-driven memory refinement from Self-Refine and Reflection-Tuning:
    - Fetch memories with low relevance not recently retrieved
    - Critique via Gemini Flash (accuracy, relevance, utility scored 1-5)
    - Fast-track archiving for genuinely stale/wrong memories
    - Boost score for memories that are actually valuable but under-retrieved

    Returns number of memories refined (archived or boosted).
    """
    if not settings.gemini_api_key:
        logger.warning("Critique refinement skipped: no Gemini API key")
        return 0

    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, content, category, relevance_score, confidence
           FROM semantic_memories
           WHERE archived = FALSE
             AND deleted_at IS NULL
             AND category NOT IN ('identity', 'infrastructure')
             AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '3 days')
             AND relevance_score < 0.6
           ORDER BY relevance_score ASC
           LIMIT 20"""
    )

    if not rows:
        return 0

    memories = [dict(r) for r in rows]
    critiques = await _gemini_critique_memories(memories)

    refined = 0
    for critique in critiques:
        mem_id = critique.get("id")
        action = critique.get("action", "keep")

        if not mem_id:
            continue

        try:
            if action == "archive":
                await pool.execute(
                    "UPDATE semantic_memories SET archived = TRUE, updated_at = NOW() "
                    "WHERE id = $1::uuid",
                    mem_id,
                )
                refined += 1
                logger.info(
                    f"Critique-archived {mem_id[:8]}: {critique.get('reason', '')}"
                )
            elif action == "boost":
                await pool.execute(
                    """UPDATE semantic_memories
                       SET relevance_score = LEAST(1.0, relevance_score + 0.1),
                           updated_at = NOW()
                       WHERE id = $1::uuid""",
                    mem_id,
                )
                refined += 1
                logger.info(
                    f"Critique-boosted {mem_id[:8]}: {critique.get('reason', '')}"
                )
        except Exception as e:
            logger.warning(f"Failed to apply critique to {mem_id}: {e}")

    logger.info(
        f"Critique refinement: {refined}/{len(memories)} memories refined "
        f"(archive+boost)"
    )
    return refined


# ── ReMe: Retrieval-enhanced Memory Evolution ────────────────────────────────

async def run_reme() -> int:
    """ReMe: use retrieval frequency as a bidirectional evolution signal.

    Two operations:
    1. Boost confidence for frequently-retrieved memories that are under-confident.
       Rationale: if a memory is retrieved ≥5 times it's evidently useful — trust it more.
       Effect: confidence += 0.05 (capped at 0.9).

    2. Accelerate relevance decay for zero-retrieval old memories.
       Rationale: a memory never recalled after 14 days is probably noise — speed decay.
       Effect: relevance_score *= 0.95 (instead of the standard 0.99).

    Returns total memories evolved (boosted + accelerated-decay).
    """
    pool = await get_pool()

    # 1. Confidence boost for frequently-retrieved but under-confident memories
    boost_result = await pool.execute(
        """UPDATE semantic_memories
           SET confidence = LEAST(0.9, confidence + 0.05),
               updated_at = NOW()
           WHERE retrieval_count >= 5
             AND confidence < 0.8
             AND archived = FALSE
             AND deleted_at IS NULL"""
    )
    boosted = int(boost_result.split()[-1])

    # 2. Accelerated decay for zero-retrieval old memories (non-identity/infrastructure)
    accel_decay_result = await pool.execute(
        """UPDATE semantic_memories
           SET relevance_score = GREATEST(0.05, relevance_score * 0.95),
               updated_at = NOW()
           WHERE retrieval_count = 0
             AND created_at < NOW() - INTERVAL '14 days'
             AND archived = FALSE
             AND deleted_at IS NULL
             AND category NOT IN ('identity', 'infrastructure')"""
    )
    decayed = int(accel_decay_result.split()[-1])

    logger.info(
        f"ReMe evolution: {boosted} memories confidence-boosted (retrieval_count>=5), "
        f"{decayed} memories accelerated-decayed (zero-retrieval >14d)"
    )
    return boosted + decayed


# ── AgeMem: TTL enforcement ───────────────────────────────────────────────────

async def run_ttl_enforcement() -> int:
    """Hard-delete semantic memories whose TTL has expired.

    A memory expires when: ttl_days IS NOT NULL AND created_at + ttl_days < NOW().
    These are truly deleted (not soft-deleted) since TTL implies intentional transience.

    Returns count of deleted memories.
    """
    pool = await get_pool()
    result = await pool.execute(
        """DELETE FROM semantic_memories
           WHERE ttl_days IS NOT NULL
             AND deleted_at IS NULL
             AND created_at + (ttl_days || ' days')::interval < NOW()"""
    )
    expired = int(result.split()[-1])
    if expired:
        logger.info(f"AgeMem TTL: hard-deleted {expired} expired memories")
    return expired


# ── Memory evolution endpoint ─────────────────────────────────────────────────

@router.post("/evolve", response_model=EvolveResult)
async def run_evolve():
    """Full memory evolution cycle (for reflection heartbeat):
    1. Relevance decay on stale semantic memories + archive very-low-score
    2. Flush scratch slot → episodic events
    3. Compress low-importance events older than 48h → semantic memories
    4. Full episodic → semantic consolidation (remaining unconsolidated events)
    5. Semantic dedup — archive near-duplicate memories (cosine > 0.92)
    6. Critique-driven refinement — score low-quality memories and archive/boost
    7. ReMe — retrieval-enhanced evolution: boost frequently-retrieved, decay zero-retrieval
    8. AgeMem TTL — hard-delete expired TTL memories
    """
    from .consolidation import run_semantic_dedup  # avoid circular import at module level

    decay_updated, archived = await run_decay()
    scratch_consolidated = await consolidate_scratch()
    short_horizon_compressed, short_horizon_facts = await run_short_horizon_compression()
    events_consolidated, facts_stored = await run_consolidation()
    _dupes_found, dupes_archived = await run_semantic_dedup()
    critique_refined = await run_critique_refinement()
    reme_evolved = await run_reme()
    ttl_expired = await run_ttl_enforcement()

    logger.info(
        f"Memory evolution: decay={decay_updated}, archived={archived}, "
        f"short_horizon={short_horizon_compressed}→{short_horizon_facts} facts, "
        f"consolidated={events_consolidated}→{facts_stored} facts, "
        f"dupes_archived={dupes_archived}, critique_refined={critique_refined}, "
        f"reme_evolved={reme_evolved}, ttl_expired={ttl_expired}"
    )

    return EvolveResult(
        decay_updated=decay_updated,
        archived=archived,
        scratch_consolidated=scratch_consolidated,
        short_horizon_compressed=short_horizon_compressed,
        short_horizon_facts=short_horizon_facts,
        events_consolidated=events_consolidated,
        facts_stored=facts_stored,
        dupes_archived=dupes_archived,
        critique_refined=critique_refined,
        reme_evolved=reme_evolved,
        ttl_expired=ttl_expired,
        ran_at=datetime.now(timezone.utc),
    )

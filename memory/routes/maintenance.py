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

import numpy as np

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding, invalidate_svc_cache
from ..llm import llm_chat, extract_json_array

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
    sure_replayed: int = 0  # SuRe: lessons stored from surprise replay
    ran_at: datetime


# ── LLM helper ────────────────────────────────────────────────────────────────


async def _gemini_extract_facts(events_text: str) -> list[dict]:
    """Extract permanent facts from episodic events with ProMem verification.

    ProMem (arXiv:2601.04463): After initial extraction, generates self-questions
    about the source text and checks whether extracted facts answer them. Gaps
    trigger a targeted re-extraction pass, improving recall by ~15-25%.

    Returns list of {content, category, confidence} dicts. Empty list on failure.
    """
    # ── Phase 1: Initial extraction (same as before) ──
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
        text = await llm_chat([{"role": "user", "content": prompt}], max_tokens=500, temperature=0.1)
        facts = extract_json_array(text) or []
    except Exception as e:
        logger.warning(f"LLM extraction failed: {e}")
        return []

    # ── Phase 2: ProMem self-questioning verification ──
    # Only run if we got facts AND the source text is substantial enough
    if not facts or len(events_text) < 100:
        return facts

    try:
        facts_summary = "\n".join(f"- {f.get('content', '')}" for f in facts)
        verify_prompt = (
            "Given these source events and the facts already extracted from them, "
            "generate 2-3 verification questions that test whether the extraction "
            "captured all important information.\n\n"
            f"Source events:\n{events_text}\n\n"
            f"Extracted facts:\n{facts_summary}\n\n"
            "For each question, check if the extracted facts answer it. "
            "Return a JSON array (no markdown) of objects: "
            "{\"question\": \"...\", \"answered\": true/false, "
            "\"missing_fact\": \"<1-2 sentence fact to fill the gap, or null if answered>\", "
            "\"category\": \"<category if missing_fact>\", \"confidence\": <0.5-1.0 if missing>}. "
            "Only flag genuinely important gaps — not trivia."
        )
        verify_text = await llm_chat(
            [{"role": "user", "content": verify_prompt}],
            max_tokens=400, temperature=0.1,
        )
        gaps = extract_json_array(verify_text) or []

        # Collect unanswered gaps with valid missing facts
        new_facts = []
        for gap in gaps:
            if not gap.get("answered", True) and gap.get("missing_fact"):
                missing = str(gap["missing_fact"]).strip()
                if len(missing) >= 10:
                    new_facts.append({
                        "content": missing,
                        "category": str(gap.get("category", "observation")),
                        "confidence": float(gap.get("confidence", 0.65)),
                    })

        if new_facts:
            logger.info(f"ProMem: filled {len(new_facts)} gap(s) via self-questioning")
            facts.extend(new_facts[:3])  # Cap at 3 gap-fills per batch

    except Exception as e:
        logger.warning(f"ProMem verification failed (non-fatal): {e}")

    return facts


# ── Decay (legacy fixed-rate) ──────────────────────────────────────────────────
# NOTE: This is the legacy fixed-rate decay path. The newer category-aware adaptive
# decay is available at POST /memory/adaptive-decay (see _run_adaptive_decay_logic).
# This function is still called by the nightly evolve job for backward compatibility.

async def run_decay() -> tuple[int, int]:
    """Apply relevance decay and archive low-score memories (legacy fixed-rate).

    Returns (decay_updated, archived).
    """
    pool = await get_pool()

    # Legacy: relevance_score *= 0.99 for non-identity/infrastructure facts
    # not retrieved in 7+ days (see /memory/adaptive-decay for category-aware version)
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
    if not settings.kimi_api_key:
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

        # Filter reflection meta-noise: transient metrics, cycle status reports
        # Root cause of evolve noise (9 cycles of symptom treatment, ~40+ wasted facts)
        _NOISE_CATS = {"pipeline_status", "self_critique_metrics"}
        _NOISE_MARKERS = [
            "self-critique", "mars dual reflection", "adversarial check",
            "currently idle", "system is currently idle",
            "no tasks have been created", "0 tasks created",
            "system health metrics", "glove system is clean",
            # Phase 2: catch reflection meta-noise (cycle 129 fix)
            "reflection cycle", "heartbeat cycle", "noise filter",
            "deferral debt", "idle-inflated", "evolve noise",
            "confirmed the alignment", "wasted fact extraction",
            "mars sweep", "preflect sweep", "tame evaluator",
            # Phase 3: catch alpha heartbeat transient operational noise (cycle 130 fix)
            "nudge threshold", "nudge mev", "helius keys",
            "live watcher", "paper trader", "medium signals",
            "high signals", "sync pulse", "positions are currently",
            "signals in the last", "keys have been exhausted",
            # Phase 4: catch reflection self-metric reporting noise (cycle 131 fix)
            "rl2f metric", "idle inflation", "reasoning accuracy",
            "proposals related to", "recent critiques",
            "blockers resolved", "mission aligned",
            # Phase 5: catch evolve self-referential meta-noise (cycle 133 fix)
            "facts stored", "noise pattern", "surface new noise",
            "verification confirmed", "phase 4 verification",
        ]
        facts = [
            f for f in facts
            if f.get("category") not in _NOISE_CATS
            and not any(m in str(f.get("content", "")).lower() for m in _NOISE_MARKERS)
        ]

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

        # AgentOS: trigger maintenance sync pulse
        try:
            from ..kernel.sync import run_sync_pulse
            await run_sync_pulse(trigger="maintenance")
            logger.info("AgentOS maintenance sync pulse completed")
        except Exception as e:
            logger.debug(f"AgentOS sync pulse skipped: {e}")

    except Exception as e:
        logger.error(f"Nightly maintenance failed: {e}", exc_info=True)


async def run_evolve_job():
    """Full memory evolution job — called by APScheduler (02:00 LKT).

    Runs the complete evolve cycle: decay, scratch flush, short-horizon compression,
    episodic consolidation, semantic dedup, critique refinement, ReMe, AgeMem TTL,
    SuRe surprise replay. Replaces run_maintenance_job for nightly scheduling.
    """
    try:
        from .consolidation import run_semantic_dedup
        decay_updated, archived = await run_decay()
        scratch_consolidated = await consolidate_scratch()
        short_horizon_compressed, short_horizon_facts = await run_short_horizon_compression()
        events_consolidated, facts_stored = await run_consolidation()
        _dupes_found, dupes_archived = await run_semantic_dedup()
        critique_refined = await run_critique_refinement()
        reme_evolved = await run_reme()
        ttl_expired = await run_ttl_enforcement()
        await run_sure_retroactive_scoring()
        sure_replayed = await run_sure_replay()
        logger.info(
            f"Nightly evolve complete: decay={decay_updated}, archived={archived}, "
            f"short_horizon={short_horizon_compressed}->{short_horizon_facts} facts, "
            f"consolidated={events_consolidated}->{facts_stored} facts, "
            f"dupes_archived={dupes_archived}, critique_refined={critique_refined}, "
            f"reme_evolved={reme_evolved}, ttl_expired={ttl_expired}, "
            f"sure_replayed={sure_replayed}"
        )
    except Exception as e:
        logger.error(f"Nightly evolve failed: {e}", exc_info=True)


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


# ── AgeMem RL-inspired adaptive decay ─────────────────────────────────────────

# Category-specific decay rates (learned from Otto's usage patterns)
# Lower = slower decay = more important categories
_CATEGORY_DECAY = {
    "identity": 0.0,          # Never decay identity
    "infrastructure": 0.0,    # Never decay infrastructure
    "directive": 0.005,       # Very slow — directives are critical
    "mission": 0.005,         # Very slow — mission context
    "decision": 0.01,         # Slow — decisions matter
    "credential": 0.0,        # Never decay credentials
    "capability": 0.01,       # Slow — capabilities are reference
    "project": 0.015,         # Moderate — project context evolves
    "learning": 0.02,         # Moderate — learnings age
    "research": 0.02,         # Moderate — research findings age
    "observation": 0.03,      # Faster — observations are transient
    "system": 0.025,          # Moderate — system state changes
    "relationship": 0.01,     # Slow — relationships are stable
}
_DEFAULT_DECAY = 0.02  # For unknown categories


async def _run_adaptive_decay_logic() -> dict:
    """Core adaptive decay logic — callable from endpoint and from evolve.

    Returns dict with total_updated, category_breakdown, ran_at.
    """
    pool = await get_pool()

    # Collect all distinct categories from DB to handle unknown ones too
    cat_rows = await pool.fetch(
        """SELECT DISTINCT category FROM semantic_memories
           WHERE archived = FALSE AND deleted_at IS NULL"""
    )
    all_categories = {}
    for r in cat_rows:
        cat = r["category"]
        if cat:
            all_categories[cat] = _CATEGORY_DECAY.get(cat, _DEFAULT_DECAY)

    total_updated = 0
    category_stats = {}

    for category, base_rate in all_categories.items():
        if base_rate == 0.0:
            continue  # Skip protected categories

        # Retrieval-adjusted decay:
        # - High retrieval (>10): decay at 0.5x base rate (frequently used = valuable)
        # - Medium retrieval (3-10): decay at base rate
        # - Low retrieval (0-2): decay at 1.5x base rate (rarely used = less valuable)
        # - Zero retrieval + >14 days old: decay at 2x base rate (accelerated cleanup)

        # High retrieval — slow decay
        result = await pool.execute(
            """UPDATE semantic_memories
               SET relevance_score = GREATEST(0.1, relevance_score * (1.0 - $1)),
                   salience_score = GREATEST(0.05, salience_score * (1.0 - $1)),
                   updated_at = NOW()
               WHERE category = $2
                 AND archived = FALSE AND deleted_at IS NULL
                 AND retrieval_count > 10
                 AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '7 days')""",
            base_rate * 0.5, category,
        )
        high_ret = int(result.split()[-1])

        # Medium retrieval — base decay
        result = await pool.execute(
            """UPDATE semantic_memories
               SET relevance_score = GREATEST(0.1, relevance_score * (1.0 - $1)),
                   salience_score = GREATEST(0.05, salience_score * (1.0 - $1)),
                   updated_at = NOW()
               WHERE category = $2
                 AND archived = FALSE AND deleted_at IS NULL
                 AND retrieval_count BETWEEN 3 AND 10
                 AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '7 days')""",
            base_rate, category,
        )
        med_ret = int(result.split()[-1])

        # Low retrieval — accelerated decay
        result = await pool.execute(
            """UPDATE semantic_memories
               SET relevance_score = GREATEST(0.1, relevance_score * (1.0 - $1)),
                   salience_score = GREATEST(0.05, salience_score * (1.0 - $1)),
                   updated_at = NOW()
               WHERE category = $2
                 AND archived = FALSE AND deleted_at IS NULL
                 AND retrieval_count < 3
                 AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '7 days')""",
            base_rate * 1.5, category,
        )
        low_ret = int(result.split()[-1])

        # Zero retrieval + old — aggressive decay
        result = await pool.execute(
            """UPDATE semantic_memories
               SET relevance_score = GREATEST(0.1, relevance_score * (1.0 - $1)),
                   salience_score = GREATEST(0.05, salience_score * (1.0 - $1)),
                   updated_at = NOW()
               WHERE category = $2
                 AND archived = FALSE AND deleted_at IS NULL
                 AND (retrieval_count IS NULL OR retrieval_count = 0)
                 AND created_at < NOW() - INTERVAL '14 days'""",
            base_rate * 2.0, category,
        )
        zero_old = int(result.split()[-1])

        cat_total = high_ret + med_ret + low_ret + zero_old
        total_updated += cat_total
        if cat_total > 0:
            category_stats[category] = {
                "high_retrieval": high_ret, "medium": med_ret,
                "low": low_ret, "zero_old": zero_old,
            }

    logger.info(f"AgeMem adaptive decay: {total_updated} memories updated across {len(category_stats)} categories")

    return {
        "total_updated": total_updated,
        "category_breakdown": category_stats,
        "ran_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/adaptive-decay")
async def run_adaptive_decay():
    """AgeMem RL-inspired adaptive decay: decay rate varies by category and retrieval pattern.

    Instead of fixed 0.99/0.95 rates, uses learned rates based on:
    - Category importance weights (identity=0, directive=0.005, research=0.02, observation=0.03)
    - Retrieval frequency: frequently retrieved memories decay slower
    - Age: very old memories with zero retrieval get accelerated decay

    This replaces the fixed FadeMem decay with a category-aware policy.
    """
    result = await _run_adaptive_decay_logic()
    return result


# ── Short-horizon episodic compression ────────────────────────────────────────

async def run_short_horizon_compression() -> tuple[int, int]:
    """Compress low-importance episodic events older than 48 hours into semantic memories.

    Targets events with importance < 5 that haven't been consolidated yet.
    Uses Gemini Flash to extract permanent facts; deduplicates via cosine > 0.92.
    Marks originals as consolidated after extraction.

    Returns (events_compressed, facts_stored).
    """
    if not settings.kimi_api_key:
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

    # Filter reflection meta-noise (same filter as consolidation path)
    _NOISE_CATS = {"pipeline_status", "self_critique_metrics"}
    _NOISE_MARKERS = [
        "self-critique", "mars dual reflection", "adversarial check",
        "currently idle", "system is currently idle",
        "no tasks have been created", "0 tasks created",
        "system health metrics", "glove system is clean",
        # Phase 2: catch reflection meta-noise (cycle 129 fix)
        "reflection cycle", "heartbeat cycle", "noise filter",
        "deferral debt", "idle-inflated", "evolve noise",
        "confirmed the alignment", "wasted fact extraction",
        "mars sweep", "preflect sweep", "tame evaluator",
        # Phase 3: catch alpha heartbeat transient operational noise (cycle 130 fix)
        "nudge threshold", "nudge mev", "helius keys",
        "live watcher", "paper trader", "medium signals",
        "high signals", "sync pulse", "positions are currently",
        "signals in the last", "keys have been exhausted",
        # Phase 4: catch reflection self-metric reporting noise (cycle 131 fix)
        "rl2f metric", "idle inflation", "reasoning accuracy",
        "proposals related to", "recent critiques",
        "blockers resolved", "mission aligned",
        # Phase 5: catch evolve self-referential meta-noise (cycle 133 fix)
        "facts stored", "noise pattern", "surface new noise",
        "verification confirmed", "phase 4 verification",
    ]
    facts = [
        f for f in facts
        if f.get("category") not in _NOISE_CATS
        and not any(m in str(f.get("content", "")).lower() for m in _NOISE_MARKERS)
    ]

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
        text = await llm_chat([{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.1)
        result = extract_json_array(text)
        return result if result else []
    except Exception as e:
        logger.warning(f"Memory critique failed: {e}")
        return []


async def run_critique_refinement() -> int:
    """Critique low-quality memories and refine scores.

    Implements critique-driven memory refinement from Self-Refine and Reflection-Tuning:
    - Fetch memories with low relevance not recently retrieved
    - Critique via LLM (accuracy, relevance, utility scored 1-5)
    - Fast-track archiving for genuinely stale/wrong memories
    - Boost score for memories that are actually valuable but under-retrieved

    Returns number of memories refined (archived or boosted).
    """
    if not settings.kimi_api_key:
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


# ── SuRe: Surprise-based Replay ──────────────────────────────────────────────


async def _gemini_extract_sure_lessons(events_text: str) -> list[dict]:
    """Extract learnable lessons from surprising episodic events via Gemini Flash.

    SuRe principle: high-surprise events carry the most learning signal because
    they expose gaps between expectation and reality. Extract what went wrong and
    what can be done differently.

    Returns list of {content, category, confidence} dicts.
    """
    prompt = (
        "You are an AI self-improvement assistant. The following events were SURPRISING — "
        "they deviated significantly from expectations or resulted in errors.\n\n"
        f"Events:\n{events_text}\n\n"
        "Extract 1-4 concrete lessons from these surprises that an AI agent should remember. "
        "Focus on: root causes of failures, corrected mental models, actionable principles.\n"
        "Return a JSON array (only the array, no markdown). Each object:\n"
        '{"content": "<1-2 sentence lesson>", '
        '"category": "<one of: task_execution, memory_ops, alpha_trading, outreach, general, pipeline_status, research>", '
        '"confidence": <0.6-0.9>}\n'
        "Skip trivial observations. Return [] if no real lessons apply."
    )
    try:
        text = await llm_chat([{"role": "user", "content": prompt}], max_tokens=500, temperature=0.1)
        lessons = extract_json_array(text)
        return lessons if lessons else []
    except Exception as e:
        logger.warning(f"SuRe lesson extraction failed: {e}")
        return []


async def run_sure_replay(top_n: int = 20, threshold: float = 0.7) -> int:
    """SuRe: Surprise-based Replay for memory consolidation.

    Fetches the top-N most surprising unprocessed episodic events (surprise_score >= threshold),
    extracts learnable lessons via LLM, stores them as semantic memories,
    and marks the events as replayed.

    Returns: number of lessons stored.
    """
    if not settings.kimi_api_key:
        logger.warning("SuRe replay skipped: no LLM API key")
        return 0

    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, content, event_type, importance, surprise_score, created_at
           FROM episodic_events
           WHERE surprise_replayed = FALSE
             AND surprise_score >= $1
           ORDER BY surprise_score DESC
           LIMIT $2""",
        threshold, top_n,
    )

    if not rows:
        logger.info("SuRe replay: no high-surprise events to process")
        return 0

    lines = [
        f"[{e['event_type']}|surprise={e['surprise_score']:.2f}|imp={e['importance']}] "
        f"{e['content'][:300]}"
        for e in rows
    ]
    events_text = "\n".join(lines)

    lessons = await _gemini_extract_sure_lessons(events_text)
    lessons_stored = 0

    for lesson in lessons[:4]:
        content = str(lesson.get("content", "")).strip()
        category = str(lesson.get("category", "general"))
        confidence = float(lesson.get("confidence", 0.75))
        confidence = max(0.6, min(0.9, confidence))

        if not content or len(content) < 15:
            continue

        try:
            from ..embeddings import get_embedding  # lazy to avoid circular at module level
            embedding = await get_embedding(content)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

            async with pool.acquire() as conn:
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
                    logger.debug(f"SuRe dedup skip (sim={similar['similarity']:.3f}): {content[:60]}")
                    continue

                await conn.execute(
                    """INSERT INTO semantic_memories
                           (content, category, confidence, source, embedding, embedding_hv, metadata)
                       VALUES ($1, $2, $3, 'sure_replay', $4::vector, $4::halfvec(1536),
                               '{"source": "sure_replay"}'::jsonb)""",
                    content, category, confidence, embedding_str,
                )
                lessons_stored += 1
                logger.info(f"SuRe lesson stored [{category}]: {content[:80]}")

        except Exception as e:
            logger.warning(f"SuRe: failed to store lesson: {e}")

    # Mark all fetched events as replayed regardless of lesson count
    event_ids = [e["id"] for e in rows]
    await pool.execute(
        "UPDATE episodic_events SET surprise_replayed = TRUE WHERE id = ANY($1::uuid[])",
        event_ids,
    )

    logger.info(
        f"SuRe replay: {len(rows)} high-surprise events processed → {lessons_stored} lessons stored"
    )
    return lessons_stored


# ── SuRe: Retroactive surprise scoring from reasoning chain ──────────────────


async def run_sure_retroactive_scoring() -> int:
    """Back-fill surprise scores on episodic events correlated with reasoning misses.

    The reasoning_chain table tracks expected vs actual outcomes. When outcome_match='miss',
    the events from that cycle were more surprising than average — elevate their score.

    Returns: count of events updated.
    """
    pool = await get_pool()

    # Find reasoning entries where the outcome was a miss (cycle_ts from the last 7 days)
    miss_rows = await pool.fetch(
        """SELECT cycle_ts
           FROM reasoning_chain
           WHERE outcome_match = 'miss'
             AND cycle_ts > NOW() - INTERVAL '7 days'"""
    )

    if not miss_rows:
        return 0

    updated_total = 0
    for entry in miss_rows:
        cycle_ts = entry["cycle_ts"]
        # Events within ±30 minutes of a missed reasoning cycle carry higher surprise
        result = await pool.execute(
            """UPDATE episodic_events
               SET surprise_score = GREATEST(surprise_score, 0.8)
               WHERE created_at BETWEEN $1::timestamptz - INTERVAL '30 minutes'
                                      AND $1::timestamptz + INTERVAL '30 minutes'
                 AND surprise_score < 0.8
                 AND surprise_replayed = FALSE""",
            cycle_ts,
        )
        count = int(result.split()[-1])
        updated_total += count

    if updated_total:
        logger.info(f"SuRe retroactive scoring: elevated {updated_total} events near reasoning misses")
    return updated_total


# ── Memory evolution endpoint ─────────────────────────────────────────────────

@router.get("/surprise-queue")
async def get_surprise_queue(limit: int = 20, threshold: float = 0.7):
    """SuRe: Return top-N most surprising unprocessed episodic events.

    These are candidates for surprise replay — events where Otto's actual
    experience diverged significantly from expectations. Callers can use
    this to understand what surprised Otto most recently and trigger replay.

    Query params:
    - limit: max events to return (default 20)
    - threshold: minimum surprise_score to include (default 0.7)
    """
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, content, event_type, importance, surprise_score, created_at
           FROM episodic_events
           WHERE surprise_replayed = FALSE
             AND surprise_score >= $1
           ORDER BY surprise_score DESC
           LIMIT $2""",
        threshold, limit,
    )
    return [dict(r) for r in rows]


@router.post("/evolve", response_model=EvolveResult)
async def run_evolve():
    """Full memory evolution cycle (for reflection heartbeat):
    1. Relevance decay on stale semantic memories + archive very-low-score (legacy)
    1b. AgeMem adaptive decay — category-aware, retrieval-adjusted decay
    2. Flush scratch slot → episodic events
    3. Compress low-importance events older than 48h → semantic memories
    4. Full episodic → semantic consolidation (remaining unconsolidated events)
    5. Semantic dedup — archive near-duplicate memories (cosine > 0.92)
    6. Critique-driven refinement — score low-quality memories and archive/boost
    7. ReMe — retrieval-enhanced evolution: boost frequently-retrieved, decay zero-retrieval
    8. AgeMem TTL — hard-delete expired TTL memories
    9. SuRe — surprise-based replay: elevate + extract lessons from surprising events
    """
    from .consolidation import run_semantic_dedup  # avoid circular import at module level

    decay_updated, archived = await run_decay()

    # AgeMem adaptive decay: category-aware, retrieval-adjusted (runs alongside legacy)
    try:
        adaptive_result = await _run_adaptive_decay_logic()
        logger.info(f"Evolve: adaptive decay updated {adaptive_result['total_updated']} memories")
    except Exception as e:
        logger.warning(f"Adaptive decay in evolve failed (non-fatal): {e}")

    scratch_consolidated = await consolidate_scratch()
    short_horizon_compressed, short_horizon_facts = await run_short_horizon_compression()
    events_consolidated, facts_stored = await run_consolidation()
    _dupes_found, dupes_archived = await run_semantic_dedup()
    critique_refined = await run_critique_refinement()
    reme_evolved = await run_reme()
    ttl_expired = await run_ttl_enforcement()
    # SuRe: retroactive scoring then replay
    await run_sure_retroactive_scoring()
    sure_replayed = await run_sure_replay()

    logger.info(
        f"Memory evolution: decay={decay_updated}, archived={archived}, "
        f"short_horizon={short_horizon_compressed}→{short_horizon_facts} facts, "
        f"consolidated={events_consolidated}→{facts_stored} facts, "
        f"dupes_archived={dupes_archived}, critique_refined={critique_refined}, "
        f"reme_evolved={reme_evolved}, ttl_expired={ttl_expired}, "
        f"sure_replayed={sure_replayed}"
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
        sure_replayed=sure_replayed,
        ran_at=datetime.now(timezone.utc),
    )


# ── Agent Drift Detection (arXiv 2601.04170) ─────────────────────────────────

# Constitutional directives extracted from CONSTITUTION.md + priorities
# Keyed by directive_id for alignment scoring
_CONSTITUTIONAL_DIRECTIVES = [
    {
        "id": "goal_model_building",
        "type": "GOAL",
        "priority": "P1",
        "description": "Build Otto's own continuously learning model — fine-tuning pipeline, training data collection, LoRA/QLoRA. Focus on scaffolding excellence.",
        "keywords": ["model", "training", "fine-tun", "lora", "rlhf", "rl2f", "scaffold", "memory", "pipeline"],
    },
    {
        "id": "goal_self_improvement",
        "type": "GOAL",
        "priority": "P2",
        "description": "Research and implement findings that make Otto genuinely smarter — better decisions, better anticipation, better output.",
        "keywords": ["research", "implement", "improve", "paper", "algorithm", "capability", "sweep"],
    },
    {
        "id": "goal_alpha_trading",
        "type": "GOAL",
        "priority": "P3",
        "description": "Crypto trading — fix signal pipeline, paper trader, move toward live trading.",
        "keywords": ["alpha", "trading", "signal", "crypto", "wallet", "solana", "paper_trader", "backtest"],
    },
    {
        "id": "goal_memory_evolution",
        "type": "GOAL",
        "priority": "P4",
        "description": "Better memory, better reasoning, better autonomy. Build in otto-core repo.",
        "keywords": ["memory", "episodic", "semantic", "graph", "context", "retrieval", "embedding"],
    },
    {
        "id": "identity_autonomy",
        "type": "IDENTITY",
        "priority": "P10",
        "description": "Otto operates with full autonomy over otto-machine. Acts freely, boldly, and proactively.",
        "keywords": ["autonomy", "proactive", "self-direct", "initiative"],
    },
    {
        "id": "identity_partnership",
        "type": "IDENTITY",
        "priority": "P10",
        "description": "Otto is Mev's partner, not a tool or butler. Pushes back when something is wrong, respectfully but firmly.",
        "keywords": ["partner", "mev", "collaborat", "respect", "disagree"],
    },
    {
        "id": "identity_no_harm",
        "type": "IDENTITY",
        "priority": "P10",
        "description": "Never expose private information, never take irreversible actions without approval, never send messages to anyone other than Mev.",
        "keywords": ["private", "irreversible", "approve", "credential", "secret"],
    },
    {
        "id": "capability_heartbeat",
        "type": "CAPABILITY",
        "priority": "P8",
        "description": "Dual heartbeat rhythm (orchestrator + reflection) must run each hour. Tasks complete and are reviewed. Memory evolves.",
        "keywords": ["heartbeat", "reflection", "orchestrator", "task", "queue", "review", "complet"],
    },
    {
        "id": "capability_memory_ops",
        "type": "CAPABILITY",
        "priority": "P4",
        "description": "Memory API endpoints functional. Embeddings, consolidation, and retrieval working correctly.",
        "keywords": ["memory", "api", "endpoint", "embedding", "search", "retriev"],
    },
]


class DriftCheckResult(BaseModel):
    overall_drift: float
    per_directive: list[dict]
    flags: list[dict]
    tasks_analyzed: int
    checked_at: datetime


async def _gemini_score_drift(tasks: list[dict], directives: list[dict]) -> list[dict]:
    """Use Gemini Flash to score task alignment against constitutional directives.

    Returns list of {directive_id, directive_type, score, reasoning, flagged} dicts.
    score 0.0 = complete drift, 1.0 = perfect alignment.
    """
    # Build compact task summary
    task_lines = []
    for t in tasks:
        output_snippet = (t.get("output") or "")[:300]
        task_lines.append(
            f"- [{t.get('priority','?')}] {t.get('title','?')}: {output_snippet}"
        )
    tasks_text = "\n".join(task_lines) if task_lines else "(no tasks)"

    # Build directive descriptions
    dir_lines = [
        f"{d['id']} [{d['type']}|{d['priority']}]: {d['description']}"
        for d in directives
    ]
    dirs_text = "\n".join(dir_lines)

    prompt = (
        "You are evaluating an AI agent (Otto) for constitutional drift — deviations from its "
        "core mission and identity.\n\n"
        "RECENT TASKS COMPLETED:\n"
        f"{tasks_text}\n\n"
        "CONSTITUTIONAL DIRECTIVES:\n"
        f"{dirs_text}\n\n"
        "For each directive, score the alignment of the recent tasks on a 0.0-1.0 scale:\n"
        "- 1.0: tasks clearly serve this directive\n"
        "- 0.7: tasks partially serve this directive\n"
        "- 0.5: tasks are neutral — neither aligned nor misaligned\n"
        "- 0.3: tasks slightly neglect or contradict this directive\n"
        "- 0.0: tasks directly contradict or completely ignore this directive\n\n"
        "DRIFT TYPES:\n"
        "- GOAL drift: tasks not advancing stated mission priorities\n"
        "- IDENTITY drift: behavior/language deviating from Otto's core identity\n"
        "- CAPABILITY drift: key capabilities degrading or not being exercised\n\n"
        "Return a JSON array (only the array, no markdown). Each object:\n"
        '{"directive_id": "<id>", "directive_type": "<GOAL|IDENTITY|CAPABILITY>", '
        '"score": <0.0-1.0>, "reasoning": "<one sentence>", "flagged": <true if score < 0.5>}\n'
        "Be objective. If tasks don't touch a directive at all, score 0.5 (neutral)."
    )

    try:
        text = await llm_chat([{"role": "user", "content": prompt}], max_tokens=1000, temperature=0.1)
        result = extract_json_array(text)
        return result if result else []
    except Exception as e:
        logger.warning(f"Drift scoring failed: {e}")
        return []


@router.post("/drift-check", response_model=DriftCheckResult)
async def run_drift_check(task_limit: int = 5):
    """Agent Drift detection — constitutional alignment check.

    Implements ASI metric framework (arXiv 2601.04170) with 3 drift types:
    - GOAL DRIFT: are tasks aligned with Mev priorities (P1-P10)?
    - IDENTITY DRIFT: does behavior match personality.md / CONSTITUTION.md?
    - CAPABILITY DRIFT: are key capabilities working or degrading?

    Process:
    1. Fetch last N completed tasks
    2. Score each constitutional directive on 0-1 alignment scale via LLM
    3. Flag directives scoring below 0.5
    4. Store result in drift_history for trend analysis
    5. Return overall drift score + per-directive breakdown + flagged violations
    """
    if not settings.kimi_api_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Drift check requires LLM API key")

    pool = await get_pool()

    # 1. Fetch recent completed tasks
    task_rows = await pool.fetch(
        """SELECT id, title, output, priority, created_at, status, cli
           FROM tasks
           WHERE status = 'completed'
           ORDER BY completed_at DESC
           LIMIT $1""",
        task_limit,
    )
    tasks = [dict(r) for r in task_rows]

    if not tasks:
        # No tasks to analyze — return neutral score
        return DriftCheckResult(
            overall_drift=0.0,
            per_directive=[
                {
                    "directive_id": d["id"],
                    "directive_type": d["type"],
                    "priority": d["priority"],
                    "score": 0.5,
                    "reasoning": "No completed tasks to analyze",
                    "flagged": False,
                }
                for d in _CONSTITUTIONAL_DIRECTIVES
            ],
            flags=[],
            tasks_analyzed=0,
            checked_at=datetime.now(timezone.utc),
        )

    # 2. Score alignment via Gemini
    scores = await _gemini_score_drift(tasks, _CONSTITUTIONAL_DIRECTIVES)

    # 3. Build per-directive results, filling in any directives Gemini missed
    scored_ids = {s.get("directive_id") for s in scores}
    per_directive = []

    for directive in _CONSTITUTIONAL_DIRECTIVES:
        match = next((s for s in scores if s.get("directive_id") == directive["id"]), None)
        if match:
            score_val = float(match.get("score", 0.5))
            score_val = max(0.0, min(1.0, score_val))
            per_directive.append({
                "directive_id": directive["id"],
                "directive_type": directive["type"],
                "priority": directive["priority"],
                "score": score_val,
                "reasoning": str(match.get("reasoning", "")),
                "flagged": score_val < 0.5,
            })
        else:
            # Gemini didn't score this directive — neutral
            per_directive.append({
                "directive_id": directive["id"],
                "directive_type": directive["type"],
                "priority": directive["priority"],
                "score": 0.5,
                "reasoning": "Not evaluated (directive not scored)",
                "flagged": False,
            })

    # 4. Compute overall drift (1.0 - mean alignment score)
    if per_directive:
        mean_alignment = sum(d["score"] for d in per_directive) / len(per_directive)
        overall_drift = round(1.0 - mean_alignment, 4)
    else:
        overall_drift = 0.0

    # 5. Collect flags
    flags = [
        {
            "directive_id": d["directive_id"],
            "directive_type": d["directive_type"],
            "priority": d["priority"],
            "score": d["score"],
            "reasoning": d["reasoning"],
        }
        for d in per_directive
        if d["flagged"]
    ]

    # 6. Store in drift_history
    task_ids = [r["id"] for r in task_rows]
    try:
        await pool.execute(
            """INSERT INTO drift_history (overall_drift, per_directive, flags, task_ids, metadata)
               VALUES ($1, $2::jsonb, $3::jsonb, $4, $5::jsonb)""",
            overall_drift,
            json.dumps(per_directive),
            json.dumps(flags),
            task_ids,
            json.dumps({"tasks_analyzed": len(tasks), "task_limit": task_limit}),
        )
        logger.info(
            f"Drift check: overall_drift={overall_drift:.3f}, "
            f"{len(flags)} flag(s) across {len(tasks)} tasks"
        )
    except Exception as e:
        # Table may not exist yet — log but don't fail the response
        logger.warning(f"Drift history insert failed (migration pending?): {e}")

    return DriftCheckResult(
        overall_drift=overall_drift,
        per_directive=per_directive,
        flags=flags,
        tasks_analyzed=len(tasks),
        checked_at=datetime.now(timezone.utc),
    )


@router.get("/drift-history")
async def get_drift_history(limit: int = 10):
    """Return recent drift check results for trend analysis.

    Shows whether Otto's constitutional alignment is improving or degrading over time.
    """
    pool = await get_pool()
    try:
        rows = await pool.fetch(
            """SELECT id, checked_at, overall_drift, per_directive, flags, task_ids
               FROM drift_history
               ORDER BY checked_at DESC
               LIMIT $1""",
            limit,
        )
        return [dict(r) for r in rows]
    except Exception as e:
        logger.warning(f"Drift history query failed: {e}")
        return []


# ── SVC: Singular Value Calibration ─────────────────────────────────────────


class SVCFitResult(BaseModel):
    vectors_sampled: int
    top_k: int
    components_path: str
    mean_norm: float
    explained_variance_ratio: list[float]
    ran_at: datetime


@router.post("/svc/fit", response_model=SVCFitResult)
async def fit_svc_components(sample_size: int = 5000):
    """Compute and save SVC principal components from stored embeddings.

    Samples up to `sample_size` embeddings from semantic_memories, computes the
    corpus mean and top-k PCA directions via SVD, then saves them to the path
    configured in settings.svc_components_path.

    These components are used by get_embedding() to calibrate query embeddings
    at inference time, reducing anisotropy and improving semantic retrieval.

    Safe to call repeatedly — just overwrites the components file and invalidates
    the in-memory cache so the new components are picked up immediately.
    """
    pool = await get_pool()

    # Fetch raw float4[] embeddings from DB (pgvector stores as float4[])
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT embedding::text
               FROM semantic_memories
               WHERE embedding IS NOT NULL
                 AND deleted_at IS NULL
                 AND archived = FALSE
               ORDER BY RANDOM()
               LIMIT $1""",
            sample_size,
        )

    if len(rows) < 10:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=f"Not enough embeddings to fit SVC: found {len(rows)}, need at least 10",
        )

    # Parse pgvector text format "[f1,f2,...,fn]" into float arrays
    vectors = []
    for row in rows:
        raw = row["embedding"]
        try:
            floats = [float(x) for x in raw.strip("[]").split(",")]
            if len(floats) == 1536:
                vectors.append(floats)
        except Exception:
            continue

    if len(vectors) < 10:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse embeddings — only {len(vectors)} valid vectors",
        )

    logger.info(f"SVC fit: using {len(vectors)} embedding vectors (requested {sample_size})")

    # Convert to numpy matrix — shape (N, 1536)
    matrix = np.array(vectors, dtype=np.float32)

    # Step 1: Compute corpus mean
    mean_vec = matrix.mean(axis=0)

    # Step 2: Center the matrix
    centered = matrix - mean_vec

    # Step 3: SVD to find principal directions
    # We only need the top-k right singular vectors (V^T rows)
    # Use truncated SVD via np.linalg.svd with full_matrices=False for efficiency
    top_k = settings.svc_top_k
    try:
        # For large N, full SVD is expensive — use randomized SVD trick via numpy
        # np.linalg.svd returns U (N,K), S (K,), Vt (K,D) with full_matrices=False
        _, singular_values, Vt = np.linalg.svd(centered, full_matrices=False)
    except np.linalg.LinAlgError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"SVD computation failed: {e}")

    # principal_components: shape (top_k, 1536) — top-k rows of Vt
    principal_components = Vt[:top_k].astype(np.float32)

    # Normalize each component to unit length (should already be, but ensure it)
    for i in range(top_k):
        norm = np.linalg.norm(principal_components[i])
        if norm > 1e-8:
            principal_components[i] /= norm

    # Compute explained variance ratio for diagnostics
    total_variance = float(np.sum(singular_values ** 2))
    evr = [
        float(singular_values[i] ** 2 / total_variance)
        for i in range(min(top_k, len(singular_values)))
    ]

    # Save to .npz file
    import os
    components_path = settings.svc_components_path
    os.makedirs(os.path.dirname(components_path), exist_ok=True)
    np.savez(components_path, mean=mean_vec, components=principal_components)

    # Invalidate in-memory cache so new components are used immediately
    invalidate_svc_cache()

    logger.info(
        f"SVC fit complete: {len(vectors)} vectors, top_k={top_k}, "
        f"EVR={[f'{x:.4f}' for x in evr]}, saved to {components_path}"
    )

    return SVCFitResult(
        vectors_sampled=len(vectors),
        top_k=top_k,
        components_path=components_path,
        mean_norm=float(np.linalg.norm(mean_vec)),
        explained_variance_ratio=evr,
        ran_at=datetime.now(timezone.utc),
    )


# ── GLOVE: Memory-Environment Realignment (arXiv:2601.19249) ─────────────────
# Active probing to detect when stored memories diverge from current reality.
# Instead of passively trusting retrieved memories, GLOVE verifies them against
# live system state. Stale or wrong memories get flagged for update/archival.


class GLOVEResult(BaseModel):
    memories_probed: int
    mismatches_found: int
    memories_flagged: list[dict]  # [{id, content_preview, issue, action}]
    ran_at: datetime


@router.post("/verify-alignment", response_model=GLOVEResult)
async def verify_alignment(
    category: str | None = None,
    limit: int = 20,
    min_importance: float = 0.5,
):
    """GLOVE: Probe high-importance memories against current system state.

    For each memory, ask: "Is this still true?" using lightweight LLM verification.
    Memories that fail verification get their salience decayed and flagged.

    Called by reflection heartbeat after MARS sweep.
    """
    pool = await get_pool()

    # Fetch high-importance memories that haven't been verified recently
    cat_filter = "AND category = $3" if category else ""
    params: list = [min_importance, limit]
    if category:
        params.append(category)

    rows = await pool.fetch(
        f"""SELECT id, content, category, confidence, importance_score,
                   salience_score, created_at, updated_at
            FROM semantic_memories
            WHERE archived = FALSE AND deleted_at IS NULL
              AND importance_score >= $1
              {cat_filter}
            ORDER BY importance_score DESC, salience_score DESC
            LIMIT $2""",
        *params,
    )

    if not rows:
        return GLOVEResult(
            memories_probed=0, mismatches_found=0,
            memories_flagged=[], ran_at=datetime.now(timezone.utc),
        )

    # Build a batch verification prompt
    memory_texts = []
    for i, r in enumerate(rows):
        memory_texts.append(f"{i+1}. [{r['category']}] {r['content'][:200]}")

    verification_prompt = (
        "You are a memory verification system for Otto, a persistent AI agent that runs "
        "24/7 on a Linux VM. Otto has long-term memory storing facts, lessons, directives, "
        "and infrastructure state. Your job is to flag memories that are FACTUALLY WRONG — "
        "not merely old.\n\n"
        "CRITICAL RULES — memories that should ALMOST ALWAYS be marked 'valid':\n"
        "- Historical lessons/fixes (e.g. 'bug X was fixed on date Y') — these are RECORDS, "
        "they don't become stale. The fix happened. The lesson is permanent.\n"
        "- Directives from Mev (the human admin) — these remain valid until EXPLICITLY revoked. "
        "Age alone does NOT invalidate a directive.\n"
        "- Architectural decisions — these persist until explicitly changed.\n"
        "- Identity/ecosystem facts — these are foundational and rarely change.\n"
        "- Infrastructure configs/settings — these are stable unless there's evidence of change.\n\n"
        "Only flag as 'stale' when:\n"
        "- The memory states a CURRENT status that is likely no longer true (e.g. 'service X is down' "
        "from 2 weeks ago — it's probably been fixed)\n"
        "- The memory contains a FACTUAL ERROR you can identify from the content itself\n"
        "- The memory references temporary state (credentials expiring, time-limited offers)\n\n"
        "When in doubt, mark as 'valid'. False positives (flagging valid memories) cause more "
        "harm than false negatives (missing stale ones).\n\n"
        "Memories to verify:\n" + "\n".join(memory_texts) + "\n\n"
        "Return a JSON array with one entry per memory. Each entry:\n"
        '{\"index\": <1-based>, \"status\": \"valid\"|\"stale\"|\"uncertain\", '
        '\"reason\": \"<brief reason>\"}\n'
        "Be CONSERVATIVE — most memories should be 'valid'. Only flag clear staleness. "
        "Return [] if all memories look valid. Return ONLY the JSON array."
    )

    try:
        text = await llm_chat(
            [{"role": "user", "content": verification_prompt}],
            max_tokens=800, temperature=0.1,
        )
        assessments = extract_json_array(text) or []
    except Exception as e:
        logger.warning(f"GLOVE verification LLM call failed: {e}")
        return GLOVEResult(
            memories_probed=len(rows), mismatches_found=0,
            memories_flagged=[], ran_at=datetime.now(timezone.utc),
        )

    # Process assessments — flag stale/uncertain memories
    flagged = []
    for assessment in assessments:
        idx = assessment.get("index", 0) - 1
        status = assessment.get("status", "valid")
        reason = assessment.get("reason", "")

        if status not in ("stale", "uncertain") or idx < 0 or idx >= len(rows):
            continue

        row = rows[idx]
        memory_id = row["id"]

        if status == "stale":
            # Gentle decay for stale — flag for reflection review
            # Avoid aggressive decay to prevent mass-archival from false positives
            await pool.execute(
                """UPDATE semantic_memories
                   SET salience_score = GREATEST(0.0, salience_score - 0.05),
                       confidence = GREATEST(0.0, confidence - 0.05)
                   WHERE id = $1""",
                memory_id,
            )
            action = "flagged stale (salience -0.05, confidence -0.05)"
        else:  # uncertain
            # No auto-decay for uncertain — just flag for review
            action = "flagged uncertain (no auto-decay)"

        flagged.append({
            "id": str(memory_id),
            "content_preview": row["content"][:100],
            "category": row["category"],
            "issue": f"{status}: {reason}",
            "action": action,
        })

    return GLOVEResult(
        memories_probed=len(rows),
        mismatches_found=len(flagged),
        memories_flagged=flagged,
        ran_at=datetime.now(timezone.utc),
    )

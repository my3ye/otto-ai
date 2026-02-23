import asyncio
import itertools
import json
import logging
import math
import time
from uuid import UUID

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import (
    SemanticMemoryCreate,
    SemanticMemoryOut,
    SemanticSearchQuery,
    SemanticForgetRequest,
    SemanticForgetResponse,
    SemanticUpdateRequest,
    SemanticSummarizeRequest,
    SemanticSummarizeResponse,
    SemanticMergeRequest,
    SemanticMergeResponse,
    DuplicateGroup,
    NoteLink,
    LinkMemoryResponse,
    ARAGSearchRequest,
    ARAGResult,
    ARAGSearchResponse,
)

# ── HyMem: Dual-granularity retrieval helpers ──────────────────────


class QueryComplexityClassifier:
    """HyMem query complexity classifier.
    
    Simple heuristic: short queries (few words) use summary tier,
    long/complex queries use detailed tier.
    
    Thresholds:
    - <= complexity_threshold words: summary tier (fast, lightweight)
    - > complexity_threshold words OR contains complex operators: detailed tier
    """
    
    # Complex query indicators (regex-like patterns)
    COMPLEX_INDICATORS = [
        " and ", " or ", " but ", " however ", " although ",
        " compared ", " difference ", " between ", " relationship ",
        " why ", " how ", " explain ", " analyze ", " compare ",
    ]
    
    def __init__(self, threshold: int = 8):
        self.threshold = threshold
    
    def classify(self, query: str) -> tuple[str, float]:
        """Classify query complexity. Returns (tier, confidence).
        
        Tier: 'summary' for simple queries, 'detailed' for complex queries.
        """
        query_lower = query.lower().strip()
        word_count = len(query_lower.split())
        
        # Check for complex query indicators
        has_complex_indicators = any(
            indicator in query_lower 
            for indicator in self.COMPLEX_INDICATORS
        )
        
        # Check for question marks (seeking explanation)
        is_question = "?" in query or query_lower.startswith(("what", "why", "how", "when", "where", "who"))
        
        # Check for conjunctions (multiple concepts)
        has_conjunctions = any(word in query_lower for word in [" and ", " or ", " vs ", " versus "])
        
        # Scoring
        complexity_score = 0.0
        if word_count > self.threshold:
            complexity_score += 0.4
        if has_complex_indicators:
            complexity_score += 0.3
        if is_question and word_count > 5:
            complexity_score += 0.2
        if has_conjunctions:
            complexity_score += 0.1
        
        # Determine tier
        if complexity_score >= 0.5 or word_count > self.threshold:
            return "detailed", min(1.0, complexity_score + 0.3)
        return "summary", min(1.0, 1.0 - complexity_score + 0.3)


class SummaryGenerator:
    """Generate concise summaries for HyMem dual-granularity storage."""
    
    MAX_SUMMARY_LENGTH = 200  # characters
    
    @classmethod
    def generate(cls, content: str, category: str = "general") -> str:
        """Generate a concise summary of the content.
        
        Uses simple heuristics for fast generation at write time.
        Falls back to Gemini Flash if content is complex.
        """
        content = content.strip()
        
        # If already short, use as-is (no summary needed)
        if len(content) <= cls.MAX_SUMMARY_LENGTH:
            return content
        
        # Try sentence-based extraction first (faster than API call)
        sentences = content.replace("! ", ". ").replace("? ", ". ").split(". ")
        
        # Extract key sentence(s) up to max length
        summary_parts = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            # Prioritize first sentence (often contains main point)
            if not summary_parts:
                summary_parts.append(sentence)
                current_length = len(sentence)
            elif current_length + len(sentence) + 2 <= cls.MAX_SUMMARY_LENGTH:
                summary_parts.append(sentence)
                current_length += len(sentence) + 2
            else:
                break
        
        summary = ". ".join(summary_parts)
        if not summary.endswith("."):
            summary += "."
        
        return summary[:cls.MAX_SUMMARY_LENGTH]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/semantic", tags=["semantic"])


# ── AgeMem: Importance scoring ─────────────────────────────────────

# Category weights per AgeMem spec (arxiv 2601.01885)
_CATEGORY_WEIGHTS: dict[str, float] = {
    "identity": 1.0,
    "directive": 0.95,
    "infrastructure": 0.9,
    "project_alpha": 0.85,
    "brand": 0.85,
    "mission": 0.85,
    "research": 0.8,
    "self_improvement": 0.8,
    "principle": 0.8,
    "goal": 0.75,
    "decision": 0.75,
    "procedure": 0.7,
    "outreach": 0.65,
    "task": 0.65,
    "event": 0.6,
    "observation": 0.55,
    "general": 0.5,
}

_DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # cosine similarity above which we suppress a duplicate


async def _compute_importance(
    pool,
    category: str,
    embedding_str: str,
    is_active_task: bool = False,
    override: float | None = None,
) -> tuple[float, str | None]:
    """Compute AgeMem importance score for a new memory.

    Returns (importance_score, existing_id_if_duplicate_or_None).
    If a near-duplicate exists (cosine > 0.85), returns the existing memory ID
    so the caller can skip insertion and return the existing row.
    """
    if override is not None:
        return min(1.0, max(0.0, override)), None

    # Category weight (base)
    base = _CATEGORY_WEIGHTS.get(category.lower(), 0.5)

    # Recency / active task boost
    if is_active_task:
        base = min(1.0, base + 0.1)

    # Duplicate check: if a very similar memory already exists, return its ID
    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        dup = await conn.fetchrow(
            """SELECT id, 1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity,
                      importance_score
               FROM semantic_memories
               WHERE embedding_hv IS NOT NULL
                 AND deleted_at IS NULL
                 AND archived = FALSE
               ORDER BY embedding_hv <=> $1::halfvec(1536)
               LIMIT 1""",
            embedding_str,
        )

    if dup and float(dup["similarity"]) >= _DUPLICATE_SIMILARITY_THRESHOLD:
        existing_importance = float(dup["importance_score"]) if dup["importance_score"] is not None else 0.5
        # Keep the higher importance, don't duplicate
        merged_importance = max(existing_importance, base)
        return merged_importance, str(dup["id"])

    return base, None


# ── Gemini Flash helper ────────────────────────────────────────────

async def _gemini_summarize(memories_text: str, category: str) -> str:
    """Use Gemini Flash to merge multiple memories into a single summary."""
    if not settings.gemini_api_key:
        # Fallback: simple concatenation
        return f"[summarized] {memories_text[:500]}"

    import google.generativeai as genai  # lazy import
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        "gemini-2.0-flash",
        generation_config={"temperature": 0.1},
    )
    prompt = (
        "You are an AI memory assistant. Merge these related memories into a single, "
        "concise factual statement (1-3 sentences). Preserve all key information. "
        "Do not add new information. Return only the merged statement, no preamble.\n\n"
        f"Category: {category}\n\nMemories to merge:\n{memories_text}"
    )
    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        return response.text.strip()
    except Exception as e:
        logger.warning(f"Gemini summarize failed: {e}")
        # Fallback: concatenate with separator
        return " | ".join(
            line.lstrip("- ").strip()
            for line in memories_text.split("\n")
            if line.strip()
        )[:800]


# ── A-Mem: Associative linking helpers ────────────────────────────

_AMEM_LINK_THRESHOLD = 0.70  # cosine similarity threshold for auto-linking
_AMEM_TOP_K = 3              # max links to create per new memory


async def _amem_create_links(pool, new_id, embedding_str: str) -> int:
    """Find top-K similar existing memories and create bidirectional note_links.
    Returns number of link pairs created."""
    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        candidates = await conn.fetch(
            """SELECT id, 1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
               FROM semantic_memories
               WHERE id != $2
                 AND embedding_hv IS NOT NULL
                 AND deleted_at IS NULL
                 AND archived = FALSE
               ORDER BY embedding_hv <=> $1::halfvec(1536)
               LIMIT $3""",
            embedding_str, new_id, _AMEM_TOP_K * 5,  # oversample before threshold filter
        )

    above_threshold = [
        r for r in candidates
        if float(r["similarity"]) >= _AMEM_LINK_THRESHOLD
    ][:_AMEM_TOP_K]

    if not above_threshold:
        return 0

    links_created = 0
    async with pool.acquire() as conn:
        for r in above_threshold:
            existing_id = r["id"]
            strength = float(r["similarity"])
            # Insert A→B and B→A (bidirectional), skip on conflict
            await conn.execute(
                """INSERT INTO note_links (source_id, target_id, link_strength)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (source_id, target_id) DO NOTHING""",
                new_id, existing_id, strength,
            )
            await conn.execute(
                """INSERT INTO note_links (source_id, target_id, link_strength)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (source_id, target_id) DO NOTHING""",
                existing_id, new_id, strength,
            )
            links_created += 1

    return links_created


# ── BMAM: Salience-aware scoring ──────────────────────────────────
# Implements: BMAM (arxiv 2601.20465) — brain-inspired multi-agent memory framework.
# Salience formula: 0.3*recency + 0.2*frequency + 0.3*importance + 0.2*goal_relevance
# Search ranking: 0.6*cosine_similarity + 0.4*salience_score

_GOAL_EMBEDDING_CACHE: dict = {"content": None, "embedding": None, "ts": 0.0}
_GOAL_CACHE_TTL_S = 300  # refresh goal embedding at most every 5 minutes


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two raw embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


async def _get_goal_embedding(pool) -> list[float] | None:
    """Return embedding for the active_mission working-memory slot.

    Cached for up to 5 minutes to avoid redundant OpenAI calls.
    """
    global _GOAL_EMBEDDING_CACHE
    now = time.monotonic()
    cached = _GOAL_EMBEDDING_CACHE

    if cached["embedding"] is not None and (now - cached["ts"]) < _GOAL_CACHE_TTL_S:
        return cached["embedding"]

    try:
        row = await pool.fetchrow(
            "SELECT content FROM core_memory WHERE slot = 'active_mission' LIMIT 1"
        )
        if not row or not row["content"].strip():
            return None

        content = row["content"].strip()
        if content == cached["content"]:
            # Content unchanged — just refresh the timestamp
            _GOAL_EMBEDDING_CACHE = {**cached, "ts": now}
            return cached["embedding"]

        embedding = await get_embedding(content[:1000])
        _GOAL_EMBEDDING_CACHE = {"content": content, "embedding": embedding, "ts": now}
        return embedding
    except Exception as e:
        logger.warning(f"BMAM: goal embedding fetch failed (non-fatal): {e}")
        return None


async def _compute_salience(
    pool,
    importance: float,
    memory_embedding: list[float],
) -> float:
    """Compute BMAM salience score for a newly stored memory.

    Formula: salience = 0.3*recency + 0.2*frequency + 0.3*importance + 0.2*goal_relevance
    At creation: recency=1.0, frequency=0.0 (never retrieved yet).
    """
    recency = 1.0      # max for freshly created memories
    frequency = 0.0    # retrieval_count = 0 at creation

    goal_embedding = await _get_goal_embedding(pool)
    if goal_embedding and memory_embedding:
        goal_relevance = _cosine_similarity(memory_embedding, goal_embedding)
    else:
        goal_relevance = 0.5  # neutral when goal unavailable

    salience = (
        0.3 * recency
        + 0.2 * frequency
        + 0.3 * importance
        + 0.2 * goal_relevance
    )
    return max(0.05, min(1.0, salience))


def _bmam_score(r) -> float:
    """BMAM salience-blended search ranking.

    final_rank = 0.6 * cosine_similarity + 0.4 * salience_score
    Replaces the pure AgeMem importance-weighted formula for /semantic/search.
    """
    similarity = float(r["similarity"])
    salience = float(r["salience_score"]) if r.get("salience_score") is not None else 0.5
    return 0.6 * similarity + 0.4 * salience


# ── Core endpoints ─────────────────────────────────────────────────

@router.post("/remember", response_model=SemanticMemoryOut)
async def remember(req: SemanticMemoryCreate):
    embedding = await get_embedding(req.content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()

    # AgeMem: compute importance score and check for near-duplicates
    importance, duplicate_id = await _compute_importance(
        pool, req.category, embedding_str, override=req.importance_score
    )

    if duplicate_id is not None:
        # Near-duplicate exists — update its importance to the max, return existing
        logger.info(
            f"AgeMem: near-duplicate detected (cosine > {_DUPLICATE_SIMILARITY_THRESHOLD}), "
            f"returning existing memory {duplicate_id} with importance={importance:.3f}"
        )
        row = await pool.fetchrow(
            """UPDATE semantic_memories
               SET importance_score = GREATEST(importance_score, $1)
               WHERE id = $2
               RETURNING id, content, category, confidence, source, created_at, importance_score, summary_content""",
            importance, duplicate_id,
        )
        return SemanticMemoryOut(**{**dict(row), "importance_score": importance, "tier_used": None})

    # BMAM: compute salience score before insert
    salience = await _compute_salience(pool, importance, embedding)

    # HyMem: Generate summary for dual-granularity storage
    summary_content = SummaryGenerator.generate(req.content, req.category)
    summary_embedding_str = None
    
    # Only generate summary embedding if summary differs from content
    if summary_content != req.content:
        summary_embedding = await get_embedding(summary_content)
        summary_embedding_str = "[" + ",".join(str(x) for x in summary_embedding) + "]"

    row = await pool.fetchrow(
        """INSERT INTO semantic_memories
               (content, category, confidence, source, embedding, embedding_hv, metadata,
                importance_score, ttl_days, salience_score,
                summary_content, summary_embedding, summary_embedding_hv)
           VALUES ($1, $2, $3, $4, $5::text::vector, $5::text::halfvec(1536), $6, $7, $8, $9, $10,
                   CASE WHEN ($11::text) IS NOT NULL THEN ($11::text)::vector ELSE NULL END,
                   CASE WHEN ($11::text) IS NOT NULL THEN ($11::text)::halfvec(1536) ELSE NULL END)
           RETURNING id, content, category, confidence, source, created_at, importance_score, summary_content""",
        req.content, req.category, req.confidence, req.source,
        embedding_str, req.metadata, importance, req.ttl_days, salience,
        summary_content, summary_embedding_str,
    )
    logger.info(
        f"AgeMem+BMAM+HyMem: stored memory {row['id']} category={req.category} "
        f"importance={importance:.3f} salience={salience:.3f} summary_len={len(summary_content)}"
    )

    # A-Mem: auto-link new memory to similar existing memories
    new_id = row["id"]
    try:
        n_links = await _amem_create_links(pool, new_id, embedding_str)
        if n_links:
            logger.info(f"A-Mem: created {n_links} bidirectional links for memory {new_id}")
    except Exception as e:
        logger.warning(f"A-Mem linking failed (non-fatal): {e}")

    return SemanticMemoryOut(**dict(row))


def _importance_weighted_score(r) -> float:
    """AgeMem importance-weighted ranking formula.
    final_score = 0.7 * cosine_similarity + 0.2 * importance_score + 0.1 * recency_factor
    recency_factor = 1.0 / (1.0 + days_since_creation / 30)
    """
    from datetime import datetime as _dt, timezone as _tz
    similarity = float(r["similarity"])
    importance = float(r["importance_score"]) if r["importance_score"] is not None else 0.5
    created_at = r["created_at"]
    now = _dt.now(_tz.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=_tz.utc)
    days_old = max(0.0, (now - created_at).total_seconds() / 86400)
    recency = 1.0 / (1.0 + days_old / 30)
    return 0.7 * similarity + 0.2 * importance + 0.1 * recency


@router.post("/search", response_model=list[SemanticMemoryOut])
async def search(req: SemanticSearchQuery):
    """HyMem dual-granularity semantic search.
    
    Automatically selects tier based on query complexity:
    - Summary tier: fast, lightweight retrieval for simple queries
    - Detailed tier: full semantic search for complex queries
    """
    pool = await get_pool()
    
    # HyMem: classify query complexity to select appropriate tier
    classifier = QueryComplexityClassifier(threshold=req.complexity_threshold)
    recommended_tier, confidence = classifier.classify(req.query)
    
    # Use forced tier if specified, otherwise use classifier recommendation
    tier = req.force_tier or recommended_tier
    
    logger.info(f"HyMem: query='{req.query[:50]}...' tier={tier} (confidence={confidence:.2f}, forced={req.force_tier is not None})")

    # Perform dual-tier search
    results = await _hymem_search(pool, req, tier)
    
    # Tag results with tier used
    for r in results:
        r.tier_used = tier
    
    return results


async def _hymem_search(
    pool,
    req: SemanticSearchQuery,
    tier: str
) -> list[SemanticMemoryOut]:
    """Internal HyMem dual-granularity search implementation."""

    # Embed query first — embedding is always $1 to avoid param index shifting
    query_embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # Build dynamic WHERE clause — exclude archived and soft-deleted
    conditions = ["archived = FALSE", "deleted_at IS NULL"]
    params: list = [embedding_str]  # $1 = embedding (fixed)
    idx = 2  # next free param index

    if req.min_confidence > 0:
        conditions.append(f"confidence >= ${idx}")
        params.append(req.min_confidence)
        idx += 1

    if req.category:
        conditions.append(f"category = ${idx}")
        params.append(req.category)
        idx += 1

    where = " AND ".join(conditions)
    fetch_limit = req.limit * 3
    params.append(fetch_limit)
    # idx now points to fetch_limit's position in params

    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")

        if tier == "summary":
            # HyMem Summary Tier: fast retrieval using summary embeddings
            # Falls back to detailed tier if no summary embeddings available

            # Try summary tier first (only rows with summary embeddings)
            rows = await conn.fetch(
                f"""SELECT id, content, category, confidence, source, created_at,
                           utility_score, relevance_score, importance_score, salience_score,
                           summary_content,
                           1 - (summary_embedding_hv <=> $1::halfvec(1536)) AS similarity
                    FROM semantic_memories
                    WHERE summary_embedding_hv IS NOT NULL AND {where}
                    ORDER BY summary_embedding_hv <=> $1::halfvec(1536)
                    LIMIT ${idx}""",
                *params,
            )

            # If summary tier returns too few results, fall back to detailed
            if len(rows) < req.limit:
                logger.info(f"HyMem: summary tier returned {len(rows)} results, falling back to detailed tier")
                rows = await conn.fetch(
                    f"""SELECT id, content, category, confidence, source, created_at,
                               utility_score, relevance_score, importance_score, salience_score,
                               summary_content,
                               1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                        FROM semantic_memories
                        WHERE embedding_hv IS NOT NULL AND {where}
                        ORDER BY embedding_hv <=> $1::halfvec(1536)
                        LIMIT ${idx}""",
                    *params,
                )
        else:
            # HyMem Detailed Tier: full semantic search on content embeddings
            rows = await conn.fetch(
                f"""SELECT id, content, category, confidence, source, created_at,
                           utility_score, relevance_score, importance_score, salience_score,
                           summary_content,
                           1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                    FROM semantic_memories
                    WHERE embedding_hv IS NOT NULL AND {where}
                    ORDER BY embedding_hv <=> $1::halfvec(1536)
                    LIMIT ${idx}""",
                *params,
            )

        # Phase 2: re-rank by BMAM salience-blended score
        ranked = sorted(rows, key=_bmam_score, reverse=True)[: req.limit]

        # ReMe + AgeMem + BMAM + HyMem: update retrieval stats
        ids = [r["id"] for r in ranked]
        if ids:
            if tier == "summary":
                await conn.execute(
                    """UPDATE semantic_memories
                       SET last_retrieved_at = NOW(),
                           summary_retrieval_count = summary_retrieval_count + 1,
                           utility_score = LEAST(1.0, utility_score + 0.1 * (1.0 - utility_score)),
                           relevance_score = LEAST(1.0, relevance_score + 0.05 * (1.0 - relevance_score)),
                           salience_score = LEAST(1.0, salience_score + 0.05 * (1.0 - salience_score)),
                           retrieval_count = retrieval_count + 1
                       WHERE id = ANY($1::uuid[])""",
                    ids,
                )
            else:
                await conn.execute(
                    """UPDATE semantic_memories
                       SET last_retrieved_at = NOW(),
                           utility_score = LEAST(1.0, utility_score + 0.1 * (1.0 - utility_score)),
                           relevance_score = LEAST(1.0, relevance_score + 0.05 * (1.0 - relevance_score)),
                           salience_score = LEAST(1.0, salience_score + 0.05 * (1.0 - salience_score)),
                           retrieval_count = retrieval_count + 1
                       WHERE id = ANY($1::uuid[])""",
                    ids,
                )

        primary = [
            SemanticMemoryOut(**{
                **dict(r),
                "score": _bmam_score(r),
                "importance_score": float(r["importance_score"]) if r["importance_score"] is not None else 0.5,
            })
            for r in ranked
        ]

    # A-Mem: expand with 1-hop linked context
    try:
        primary_ids = [r.id for r in primary]
        linked = await _amem_expand_links(pool, primary_ids)
        if linked:
            logger.info(f"A-Mem: {len(linked)} linked memories surfaced for query '{req.query[:60]}'")
    except Exception as e:
        logger.warning(f"A-Mem link expansion failed (non-fatal): {e}")

    return primary


async def _amem_expand_links(pool, memory_ids: list) -> list[SemanticMemoryOut]:
    """Fetch 1-hop neighbours from note_links for a list of memory IDs.
    Returns deduplicated linked memories (excluding the primary results themselves)."""
    if not memory_ids:
        return []

    async with pool.acquire() as conn:
        linked_rows = await conn.fetch(
            """SELECT DISTINCT ON (sm.id)
                      sm.id, sm.content, sm.category, sm.confidence,
                      sm.source, sm.created_at
               FROM note_links nl
               JOIN semantic_memories sm ON sm.id = nl.target_id
               WHERE nl.source_id = ANY($1::uuid[])
                 AND nl.target_id != ALL($1::uuid[])
                 AND sm.deleted_at IS NULL
                 AND sm.archived = FALSE
               ORDER BY sm.id, nl.link_strength DESC
               LIMIT 20""",
            memory_ids,
        )

    return [SemanticMemoryOut(**dict(r)) for r in linked_rows]


@router.post("/search/linked")
async def search_with_links(req: SemanticSearchQuery) -> dict:
    """Search with A-Mem associative expansion. Returns primary results AND
    1-hop linked context as a separate field. Does not modify primary result format."""
    query_embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    pool = await get_pool()

    conditions = ["archived = FALSE", "deleted_at IS NULL"]
    params: list = [embedding_str]
    idx = 2

    if req.min_confidence > 0:
        conditions.append(f"confidence >= ${idx}")
        params.append(req.min_confidence)
        idx += 1

    if req.category:
        conditions.append(f"category = ${idx}")
        params.append(req.category)
        idx += 1

    where = " AND ".join(conditions)
    fetch_limit = req.limit * 3
    params.append(fetch_limit)

    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       utility_score, relevance_score, importance_score, salience_score,
                       1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                FROM semantic_memories
                WHERE embedding_hv IS NOT NULL AND {where}
                ORDER BY embedding_hv <=> $1::halfvec(1536)
                LIMIT ${idx}""",
            *params,
        )

    ranked = sorted(rows, key=_bmam_score, reverse=True)[: req.limit]
    primary = [
        SemanticMemoryOut(**{
            **dict(r),
            "score": _bmam_score(r),
            "importance_score": float(r["importance_score"]) if r["importance_score"] is not None else 0.5,
        })
        for r in ranked
    ]

    primary_ids = [r.id for r in primary]
    linked = await _amem_expand_links(pool, primary_ids)

    return {
        "results": [m.model_dump() for m in primary],
        "linked_context": [m.model_dump() for m in linked],
        "linked_count": len(linked),
    }


# ── A-RAG: Hierarchical Retrieval Interface ───────────────────────
# Implements: arxiv 2602.03442 — 3 retrieval strategies run in parallel,
# merged by memory ID, ranked by weighted combination of per-strategy scores.


async def arag_search_internal(
    pool,
    query: str,
    limit: int = 10,
    min_confidence: float = 0.0,
    category: str | None = None,
    min_importance: float | None = None,
    date_after=None,
    date_before=None,
    semantic_weight: float = 0.5,
    keyword_weight: float = 0.3,
    structured_weight: float = 0.2,
) -> dict:
    """A-RAG hierarchical retrieval — 3 strategies in parallel, merged + ranked.

    Strategies:
      1. semantic    — pgvector cosine similarity (broad meaning-based recall)
      2. keyword     — pg_trgm word_similarity (exact/partial term matching)
      3. structured  — SQL metadata filtering (importance_score, date, category)

    Scoring: arag_score = semantic_weight * s_sem + keyword_weight * s_kw + structured_weight * s_str
    Returns a dict with keys: results, strategies_used, total_candidates,
    semantic_count, keyword_count, structured_count.
    """

    # ── Strategy 1: Semantic (pgvector halfvec cosine) ────────────────────
    async def _semantic():
        try:
            query_embedding = await get_embedding(query)
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            conditions = ["archived = FALSE", "deleted_at IS NULL", "embedding_hv IS NOT NULL"]
            params: list = [embedding_str]
            idx = 2
            if min_confidence > 0:
                conditions.append(f"confidence >= ${idx}")
                params.append(min_confidence)
                idx += 1
            if category:
                conditions.append(f"category = ${idx}")
                params.append(category)
                idx += 1
            where = " AND ".join(conditions)
            params.append(limit * 3)
            async with pool.acquire() as conn:
                await conn.execute("SET hnsw.iterative_scan = relaxed_order")
                rows = await conn.fetch(
                    f"""SELECT id, content, category, confidence, source, created_at,
                               importance_score,
                               1 - (embedding_hv <=> $1::halfvec(1536)) AS score
                        FROM semantic_memories
                        WHERE {where}
                        ORDER BY embedding_hv <=> $1::halfvec(1536)
                        LIMIT ${idx}""",
                    *params,
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"A-RAG semantic strategy failed: {e}")
            return []

    # ── Strategy 2: Keyword (pg_trgm word_similarity) ─────────────────────
    async def _keyword():
        try:
            conditions = ["archived = FALSE", "deleted_at IS NULL"]
            # Trigram match OR substring match (ILIKE fallback for short queries)
            conditions.append("(word_similarity($1, content) > 0.1 OR content ILIKE '%' || $1 || '%')")
            params: list = [query]
            idx = 2
            if min_confidence > 0:
                conditions.append(f"confidence >= ${idx}")
                params.append(min_confidence)
                idx += 1
            if category:
                conditions.append(f"category = ${idx}")
                params.append(category)
                idx += 1
            where = " AND ".join(conditions)
            params.append(limit * 3)
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""SELECT id, content, category, confidence, source, created_at,
                               importance_score,
                               GREATEST(
                                   word_similarity($1, content),
                                   CASE WHEN content ILIKE '%' || $1 || '%' THEN 0.4 ELSE 0.0 END
                               ) AS score
                        FROM semantic_memories
                        WHERE {where}
                        ORDER BY score DESC
                        LIMIT ${idx}""",
                    *params,
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"A-RAG keyword strategy failed (pg_trgm may not be installed): {e}")
            return []

    # ── Strategy 3: Structured (SQL metadata filtering) ───────────────────
    async def _structured():
        try:
            conditions = ["archived = FALSE", "deleted_at IS NULL"]
            params: list = []
            idx = 1
            if min_confidence > 0:
                conditions.append(f"confidence >= ${idx}")
                params.append(min_confidence)
                idx += 1
            if category:
                conditions.append(f"category = ${idx}")
                params.append(category)
                idx += 1
            if min_importance is not None:
                conditions.append(f"importance_score >= ${idx}")
                params.append(min_importance)
                idx += 1
            if date_after is not None:
                conditions.append(f"created_at >= ${idx}")
                params.append(date_after)
                idx += 1
            if date_before is not None:
                conditions.append(f"created_at <= ${idx}")
                params.append(date_before)
                idx += 1
            where = " AND ".join(conditions)
            params.append(limit * 3)
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    f"""SELECT id, content, category, confidence, source, created_at,
                               importance_score,
                               COALESCE(importance_score, 0.5) AS score
                        FROM semantic_memories
                        WHERE {where}
                        ORDER BY importance_score DESC NULLS LAST, created_at DESC
                        LIMIT ${idx}""",
                    *params,
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"A-RAG structured strategy failed: {e}")
            return []

    # ── Run all 3 strategies in parallel ─────────────────────────────────
    semantic_results, keyword_results, structured_results = await asyncio.gather(
        _semantic(), _keyword(), _structured()
    )

    # ── Normalize scores within each strategy to [0, 1] ──────────────────
    def _normalize(results: list[dict]) -> list[dict]:
        if not results:
            return results
        max_score = max(float(r["score"]) for r in results)
        if max_score <= 0:
            return results
        for r in results:
            r["score"] = float(r["score"]) / max_score
        return results

    semantic_results = _normalize(semantic_results)
    keyword_results = _normalize(keyword_results)
    structured_results = _normalize(structured_results)

    # ── Merge results by memory ID ────────────────────────────────────────
    merged: dict[str, dict] = {}

    def _upsert(row: dict, sem: float = 0.0, kw: float = 0.0, st: float = 0.0, strategy: str = "") -> None:
        rid = str(row["id"])
        if rid not in merged:
            merged[rid] = {
                "id": row["id"],
                "content": row["content"],
                "category": row["category"],
                "confidence": float(row["confidence"]),
                "source": row.get("source"),
                "created_at": row["created_at"],
                "importance_score": float(row["importance_score"]) if row.get("importance_score") is not None else 0.5,
                "semantic_score": 0.0,
                "keyword_score": 0.0,
                "structured_score": 0.0,
                "retrieval_strategies": [],
            }
        entry = merged[rid]
        if sem > 0:
            entry["semantic_score"] = max(entry["semantic_score"], sem)
        if kw > 0:
            entry["keyword_score"] = max(entry["keyword_score"], kw)
        if st > 0:
            entry["structured_score"] = max(entry["structured_score"], st)
        if strategy and strategy not in entry["retrieval_strategies"]:
            entry["retrieval_strategies"].append(strategy)

    for r in semantic_results:
        _upsert(r, sem=r["score"], strategy="semantic")
    for r in keyword_results:
        _upsert(r, kw=r["score"], strategy="keyword")
    for r in structured_results:
        _upsert(r, st=r["score"], strategy="structured")

    # ── Compute combined A-RAG score and sort ─────────────────────────────
    for entry in merged.values():
        entry["arag_score"] = (
            semantic_weight * entry["semantic_score"]
            + keyword_weight * entry["keyword_score"]
            + structured_weight * entry["structured_score"]
        )

    final = sorted(merged.values(), key=lambda x: x["arag_score"], reverse=True)[:limit]

    # ReMe: update retrieval stats for surfaced memories
    if final:
        ids = [entry["id"] for entry in final]
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """UPDATE semantic_memories
                       SET last_retrieved_at = NOW(),
                           relevance_score = LEAST(1.0, relevance_score + 0.05 * (1.0 - relevance_score)),
                           retrieval_count = retrieval_count + 1
                       WHERE id = ANY($1::uuid[])""",
                    ids,
                )
        except Exception as e:
            logger.warning(f"A-RAG ReMe update failed (non-fatal): {e}")

    return {
        "results": final,
        "strategies_used": ["semantic", "keyword", "structured"],
        "total_candidates": len(merged),
        "semantic_count": len(semantic_results),
        "keyword_count": len(keyword_results),
        "structured_count": len(structured_results),
    }


@router.post("/arag_search", response_model=ARAGSearchResponse)
async def arag_search(req: ARAGSearchRequest):
    """A-RAG hierarchical retrieval: 3 strategies in parallel, merged + ranked.

    Runs semantic (pgvector), keyword (pg_trgm), and structured (SQL) retrieval
    simultaneously, deduplicates by memory ID, and returns a unified ranked list.

    Ranking formula: arag_score = 0.5*semantic + 0.3*keyword + 0.2*structured
    (weights are configurable via request body).
    """
    pool = await get_pool()
    result = await arag_search_internal(
        pool=pool,
        query=req.query,
        limit=req.limit,
        min_confidence=req.min_confidence,
        category=req.category,
        min_importance=req.min_importance,
        date_after=req.date_after,
        date_before=req.date_before,
        semantic_weight=req.semantic_weight,
        keyword_weight=req.keyword_weight,
        structured_weight=req.structured_weight,
    )
    return ARAGSearchResponse(
        results=[ARAGResult(**r) for r in result["results"]],
        query=req.query,
        strategies_used=result["strategies_used"],
        total_candidates=result["total_candidates"],
        semantic_count=result["semantic_count"],
        keyword_count=result["keyword_count"],
        structured_count=result["structured_count"],
    )


# ── HyMem: briefing search (exported) ─────────────────────────────

async def hymem_briefing_facts(
    pool,
    query: str,
    limit: int = 20,
    min_confidence: float = 0.7,
    top_k_detailed: int = 5,
    excluded_categories: tuple = (),
) -> list[dict]:
    """HyMem hybrid search optimised for context briefings.

    Returns top_k_detailed results with full content (detailed tier),
    plus remaining results with summary_content only (summary tier breadth).
    Falls back to arag_search_internal if needed.
    """
    query_embedding = await get_embedding(query)
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    conditions = ["archived = FALSE", "deleted_at IS NULL", "embedding_hv IS NOT NULL"]
    params: list = [embedding_str]
    idx = 2

    if min_confidence > 0:
        conditions.append(f"confidence >= ${idx}")
        params.append(min_confidence)
        idx += 1

    where = " AND ".join(conditions)
    params.append(limit * 3)

    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       importance_score, salience_score, utility_score, relevance_score,
                       summary_content,
                       1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                FROM semantic_memories
                WHERE {where}
                ORDER BY embedding_hv <=> $1::halfvec(1536)
                LIMIT ${idx}""",
            *params,
        )

    ranked = sorted(rows, key=_bmam_score, reverse=True)[:limit]

    results = []
    for i, r in enumerate(ranked):
        cat = r["category"]
        if cat in excluded_categories:
            continue
        # Detailed tier for top-k, summary tier for breadth
        use_summary = i >= top_k_detailed and r["summary_content"]
        results.append({
            "id": r["id"],
            "content": r["content"],
            "summary_content": r["summary_content"],
            "category": cat,
            "confidence": float(r["confidence"]),
            "importance_score": float(r["importance_score"]) if r["importance_score"] is not None else 0.5,
            "display_content": r["summary_content"] if use_summary else r["content"],
            "tier": "summary" if use_summary else "detailed",
        })

    return results


# ── AgeMem: explicit memory management ────────────────────────────

@router.post("/forget", response_model=SemanticForgetResponse)
async def forget(req: SemanticForgetRequest):
    """Soft-delete memories by ID or by semantic similarity to a query."""
    pool = await get_pool()

    if req.memory_id is not None:
        result = await pool.execute(
            "UPDATE semantic_memories SET deleted_at = NOW() WHERE id = $1 AND deleted_at IS NULL",
            req.memory_id,
        )
        affected = int(result.split()[-1])
        return SemanticForgetResponse(affected=affected)

    if req.query:
        query_embedding = await get_embedding(req.query)
        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        async with pool.acquire() as conn:
            await conn.execute("SET hnsw.iterative_scan = relaxed_order")
            rows = await conn.fetch(
                """SELECT id, 1 - (embedding_hv <=> $1::halfvec(1536)) AS similarity
                   FROM semantic_memories
                   WHERE embedding_hv IS NOT NULL AND deleted_at IS NULL
                   ORDER BY embedding_hv <=> $1::halfvec(1536)
                   LIMIT 100""",
                embedding_str,
            )

        ids_to_delete = [r["id"] for r in rows if float(r["similarity"]) >= req.threshold]
        if not ids_to_delete:
            return SemanticForgetResponse(affected=0)

        result = await pool.execute(
            "UPDATE semantic_memories SET deleted_at = NOW() WHERE id = ANY($1::uuid[])",
            ids_to_delete,
        )
        affected = int(result.split()[-1])
        return SemanticForgetResponse(affected=affected)

    raise HTTPException(status_code=400, detail="Provide either memory_id or query+threshold")


@router.put("/update", response_model=SemanticMemoryOut)
async def update_memory(req: SemanticUpdateRequest):
    """Update memory content and re-embed. Optionally change category."""
    embedding = await get_embedding(req.content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()

    if req.category is not None:
        row = await pool.fetchrow(
            """UPDATE semantic_memories
               SET content = $1, category = $2,
                   embedding = $3::vector, embedding_hv = $3::halfvec(1536),
                   updated_at = NOW()
               WHERE id = $4 AND deleted_at IS NULL
               RETURNING id, content, category, confidence, source, created_at""",
            req.content, req.category, embedding_str, req.memory_id,
        )
    else:
        row = await pool.fetchrow(
            """UPDATE semantic_memories
               SET content = $1,
                   embedding = $2::vector, embedding_hv = $2::halfvec(1536),
                   updated_at = NOW()
               WHERE id = $3 AND deleted_at IS NULL
               RETURNING id, content, category, confidence, source, created_at""",
            req.content, embedding_str, req.memory_id,
        )

    if not row:
        raise HTTPException(status_code=404, detail="Memory not found or already deleted")

    return SemanticMemoryOut(**dict(row))


@router.post("/summarize", response_model=SemanticSummarizeResponse)
async def summarize_memories(req: SemanticSummarizeRequest):
    """Merge multiple memories into one summary via Gemini Flash, soft-delete originals."""
    pool = await get_pool()

    if req.memory_ids:
        rows = await pool.fetch(
            """SELECT id, content, category, confidence, source, created_at
               FROM semantic_memories
               WHERE id = ANY($1::uuid[]) AND deleted_at IS NULL""",
            req.memory_ids,
        )
    elif req.category is not None:
        query = (
            "SELECT id, content, category, confidence, source, created_at "
            "FROM semantic_memories WHERE deleted_at IS NULL AND archived = FALSE AND category = $1"
        )
        params: list = [req.category]
        if req.older_than_days:
            query += f" AND created_at < NOW() - INTERVAL '{int(req.older_than_days)} days'"
        query += " ORDER BY created_at ASC LIMIT 50"
        rows = await pool.fetch(query, *params)
    else:
        raise HTTPException(status_code=400, detail="Provide either memory_ids or category")

    if not rows:
        raise HTTPException(status_code=404, detail="No memories found to summarize")
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 memories to summarize")

    # Determine dominant category
    categories = [r["category"] for r in rows]
    summary_category = max(set(categories), key=categories.count)
    avg_confidence = sum(float(r["confidence"]) for r in rows) / len(rows)

    content_lines = [f"- [{r['category']}] {r['content']}" for r in rows]
    memories_text = "\n".join(content_lines)
    summary_content = await _gemini_summarize(memories_text, summary_category)

    embedding = await get_embedding(summary_content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    source_ids = json.dumps([str(r["id"]) for r in rows])

    new_row = await pool.fetchrow(
        """INSERT INTO semantic_memories
               (content, category, confidence, source, embedding, embedding_hv, metadata)
           VALUES ($1, $2, $3, 'summarize_endpoint', $4::vector, $4::halfvec(1536),
                   jsonb_build_object('summarized_from', $5::jsonb))
           RETURNING id, content, category, confidence, source, created_at""",
        summary_content, summary_category, avg_confidence, embedding_str, source_ids,
    )

    # Soft-delete originals
    ids = [r["id"] for r in rows]
    await pool.execute(
        "UPDATE semantic_memories SET deleted_at = NOW() WHERE id = ANY($1::uuid[])",
        ids,
    )

    return SemanticSummarizeResponse(
        summary_memory=SemanticMemoryOut(**dict(new_row)),
        originals_deleted=len(ids),
    )


@router.get("/links/{memory_id}", response_model=list[NoteLink])
async def get_memory_links(memory_id: UUID):
    """Return outgoing note_links for a given memory (bidirectionality is stored explicitly,
    so querying source_id gives all associations without duplicates)."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT nl.id, nl.source_id, nl.target_id, nl.link_strength, nl.created_at,
                  sm.content AS linked_content, sm.category AS linked_category
           FROM note_links nl
           JOIN semantic_memories sm ON sm.id = nl.target_id
           WHERE nl.source_id = $1
           ORDER BY nl.link_strength DESC""",
        memory_id,
    )
    if not rows:
        return []
    return [NoteLink(**dict(r)) for r in rows]


@router.post("/merge-duplicates", response_model=SemanticMergeResponse)
async def merge_duplicates(req: SemanticMergeRequest):
    """Find near-duplicate memories and optionally merge them (soft-delete all but best)."""
    pool = await get_pool()

    # Build self-join to find duplicate pairs
    cat_clause = "AND a.category = $2 AND b.category = $2" if req.category else ""
    threshold_param = 2 if req.category else 1
    params: list = [req.threshold]
    if req.category:
        params = [req.threshold, req.category]

    pairs_query = f"""
        SELECT a.id AS id1, a.content AS content1, a.confidence AS conf1,
               b.id AS id2, b.content AS content2, b.confidence AS conf2,
               1 - (a.embedding_hv <=> b.embedding_hv) AS similarity
        FROM semantic_memories a
        JOIN semantic_memories b ON a.id < b.id
        WHERE a.deleted_at IS NULL AND a.archived = FALSE AND a.embedding_hv IS NOT NULL
          AND b.deleted_at IS NULL AND b.archived = FALSE AND b.embedding_hv IS NOT NULL
          {cat_clause}
          AND 1 - (a.embedding_hv <=> b.embedding_hv) > ${threshold_param}
        ORDER BY similarity DESC
        LIMIT 500
    """

    pairs = await pool.fetch(pairs_query, *params)
    if not pairs:
        return SemanticMergeResponse(groups_found=0, groups=[], merged=0)

    # Union-find clustering
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if x not in parent:
            parent[x] = x
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: str, y: str) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    pair_sims: dict[tuple, float] = {}
    for pair in pairs:
        id1, id2 = str(pair["id1"]), str(pair["id2"])
        union(id1, id2)
        key = (min(id1, id2), max(id1, id2))
        pair_sims[key] = float(pair["similarity"])

    # Group by root
    groups_map: dict[str, list[str]] = {}
    for id_str in parent:
        root = find(id_str)
        groups_map.setdefault(root, []).append(id_str)

    # Fetch full data for all involved memories
    all_ids = list(parent.keys())
    mem_rows = await pool.fetch(
        "SELECT id::text, content, category, confidence FROM semantic_memories WHERE id = ANY($1::uuid[])",
        all_ids,
    )
    row_map = {r["id"]: dict(r) for r in mem_rows}

    groups: list[DuplicateGroup] = []
    for root, ids in groups_map.items():
        if len(ids) < 2:
            continue
        combos = list(itertools.combinations(ids, 2))
        sims = [pair_sims.get((min(a, b), max(a, b)), req.threshold) for a, b in combos]
        max_sim = max(sims) if sims else req.threshold
        groups.append(DuplicateGroup(
            ids=[UUID(i) for i in ids],
            contents=[row_map[i]["content"] for i in ids if i in row_map],
            max_similarity=max_sim,
        ))

    # Sort groups by similarity descending
    groups.sort(key=lambda g: g.max_similarity, reverse=True)

    merged = 0
    if not req.dry_run:
        for group in groups:
            group_data = [row_map[str(i)] for i in group.ids if str(i) in row_map]
            if not group_data:
                continue
            # Keep highest-confidence memory; soft-delete the rest
            best = max(group_data, key=lambda r: float(r["confidence"]))
            to_delete = [UUID(r["id"]) for r in group_data if r["id"] != best["id"]]
            if to_delete:
                await pool.execute(
                    "UPDATE semantic_memories SET deleted_at = NOW() WHERE id = ANY($1::uuid[])",
                    to_delete,
                )
                merged += len(to_delete)

    return SemanticMergeResponse(
        groups_found=len(groups),
        groups=groups,
        merged=merged,
    )

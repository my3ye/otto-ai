import asyncio
import itertools
import json
import logging
import math
import time
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding, get_embedding_provider, emb_col, emb_cast, emb_summary_col
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
    SimpleMemSearchResponse,
)
from ..simplemem import compress_for_context
from ..llm import llm_chat

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
# Canonical category set — validated on /remember. Any caller must use one of these.
# Mapped from legacy: market_research→research, self_improvement→capability,
# alpha/brand/characters/product/project_context/own_model/webassist→project,
# pipeline_status/working_memory/reasoning_chain→system, architecture→infrastructure,
# narrative/general→observation, procedure/implementation→capability, goal→mission.
CANONICAL_CATEGORIES: frozenset[str] = frozenset({
    "identity",      # Otto's identity, persona, who Otto is
    "directive",     # Commands/instructions from Mev
    "mission",       # Goals, objectives, purpose (inc. former 'goal')
    "decision",      # Decisions made by Otto or Mev
    "infrastructure",# System architecture, deployment (inc. former 'architecture')
    "project",       # All brand/product projects (alpha, characters, brand, etc.)
    "research",      # Papers, findings, market research
    "capability",    # Otto's skills, procedures, implementations (inc. 'self_improvement')
    "system",        # Internal system state, pipeline status, memory state
    "observation",   # General observations, narrative, facts (inc. 'general')
    "learning",      # Lessons learned, reflections (future use)
    "relationship",  # Relationships between entities (future use)
})

_CATEGORY_WEIGHTS: dict[str, float] = {
    "identity": 1.0,
    "directive": 0.95,
    "infrastructure": 0.9,
    "mission": 0.85,
    "research": 0.8,
    "capability": 0.8,
    "decision": 0.75,
    "project": 0.75,
    "learning": 0.7,
    "system": 0.65,
    "relationship": 0.6,
    "observation": 0.55,
}

_DUPLICATE_SIMILARITY_THRESHOLD = 0.85  # cosine similarity above which we suppress a duplicate


async def _compute_importance(
    pool,
    category: str,
    embedding_str: str,
    is_active_task: bool = False,
    override: float | None = None,
    content: str | None = None,
) -> tuple[float, str | None]:
    """Compute AgeMem importance score for a new memory.

    Returns (importance_score, existing_id_if_duplicate_or_None).
    If a near-duplicate exists (cosine > 0.85), returns the existing memory ID
    so the caller can skip insertion and return the existing row.

    Cross-provider dedup: if the cosine check finds no duplicate (because the
    other embedding column is NULL), falls back to pg_trgm text similarity on
    the content field (threshold 0.85) to catch duplicates stored by a
    different embedding provider.
    """
    if override is not None:
        return min(1.0, max(0.0, override)), None

    # Category weight (base)
    base = _CATEGORY_WEIGHTS.get(category.lower(), 0.5)

    # Recency / active task boost
    if is_active_task:
        base = min(1.0, base + 0.1)

    # Duplicate check: if a very similar memory already exists, return its ID
    col = emb_col()
    cast = emb_cast("$1")
    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        dup = await conn.fetchrow(
            f"""SELECT id, 1 - ({col} <=> {cast}) AS similarity,
                      importance_score
               FROM semantic_memories
               WHERE {col} IS NOT NULL
                 AND deleted_at IS NULL
                 AND archived = FALSE
               ORDER BY {col} <=> {cast}
               LIMIT 1""",
            embedding_str,
        )

    if dup and float(dup["similarity"]) >= _DUPLICATE_SIMILARITY_THRESHOLD:
        existing_importance = float(dup["importance_score"]) if dup["importance_score"] is not None else 0.5
        # Keep the higher importance, don't duplicate
        merged_importance = max(existing_importance, base)
        return merged_importance, str(dup["id"])

    # Cross-provider fallback: check text similarity via pg_trgm
    # This catches duplicates stored by a different embedding provider
    # (e.g. content stored with OpenAI won't have embedding_local, and vice versa)
    if content:
        _TEXT_SIMILARITY_THRESHOLD = 0.85
        async with pool.acquire() as conn:
            text_dup = await conn.fetchrow(
                """SELECT id, similarity(content, $1) AS sim,
                          importance_score
                   FROM semantic_memories
                   WHERE deleted_at IS NULL
                     AND archived = FALSE
                     AND similarity(content, $1) >= $2
                   ORDER BY similarity(content, $1) DESC
                   LIMIT 1""",
                content,
                _TEXT_SIMILARITY_THRESHOLD,
            )
        if text_dup:
            existing_importance = float(text_dup["importance_score"]) if text_dup["importance_score"] is not None else 0.5
            merged_importance = max(existing_importance, base)
            logger.info(
                f"AgeMem: cross-provider text duplicate detected "
                f"(trigram sim={float(text_dup['sim']):.3f}), "
                f"returning existing memory {text_dup['id']}"
            )
            return merged_importance, str(text_dup["id"])

    return base, None


# ── Gemini Flash helper ────────────────────────────────────────────

async def _gemini_summarize(memories_text: str, category: str) -> str:
    """Use LLM to merge multiple memories into a single summary."""
    if not settings.kimi_api_key:
        return f"[summarized] {memories_text[:500]}"

    prompt = (
        "You are an AI memory assistant. Merge these related memories into a single, "
        "concise factual statement (1-3 sentences). Preserve all key information. "
        "Do not add new information. Return only the merged statement, no preamble.\n\n"
        f"Category: {category}\n\nMemories to merge:\n{memories_text}"
    )
    try:
        response = await llm_chat([{"role": "user", "content": prompt}], max_tokens=300, temperature=0.1)
        return response or f"[summarized] {memories_text[:500]}"
    except Exception as e:
        logger.warning(f"LLM summarize failed: {e}")
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
    col = emb_col()
    cast = emb_cast("$1")
    async with pool.acquire() as conn:
        await conn.execute("SET hnsw.iterative_scan = relaxed_order")
        candidates = await conn.fetch(
            f"""SELECT id, 1 - ({col} <=> {cast}) AS similarity
               FROM semantic_memories
               WHERE id != $2
                 AND {col} IS NOT NULL
                 AND deleted_at IS NULL
                 AND archived = FALSE
               ORDER BY {col} <=> {cast}
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


_AMEM_UPDATE_THRESHOLD = 0.80  # higher bar for cross-link updates


async def _amem_update_related(pool, new_memory_id: str, new_content: str, new_embedding: list[float]) -> int:
    """A-MEM cross-linking: update existing linked memories when new context arrives.

    When a new memory is stored that's strongly linked (similarity > 0.80) to existing memories,
    boost the related memories' salience and retrieval priority. This implements the
    "memory evolution" pattern from A-MEM — memories don't just link, they strengthen each other.

    Returns count of memories updated.
    """
    embedding_str = "[" + ",".join(str(x) for x in new_embedding) + "]"
    col = emb_col()
    cast = emb_cast("$2")

    # Find strongly related existing memories
    rows = await pool.fetch(
        f"""SELECT id, content, salience_score, retrieval_count
           FROM semantic_memories
           WHERE id != $1
             AND archived IS NOT TRUE AND deleted_at IS NULL
             AND {col} IS NOT NULL
           ORDER BY ({col} <=> {cast}) ASC
           LIMIT 5""",
        new_memory_id, embedding_str,
    )

    updated = 0
    cast1 = emb_cast("$1")
    for row in rows:
        # Compute actual similarity
        sim = await pool.fetchval(
            f"SELECT 1 - ({col} <=> {cast1}) FROM semantic_memories WHERE id = $2",
            embedding_str, row["id"],
        )
        if sim and sim > _AMEM_UPDATE_THRESHOLD:
            # Boost salience (capped at 1.0) — related memories become more important
            new_salience = min(1.0, (row["salience_score"] or 0.5) + 0.05)
            await pool.execute(
                """UPDATE semantic_memories
                   SET salience_score = $2, updated_at = NOW()
                   WHERE id = $1""",
                row["id"], new_salience,
            )
            updated += 1

    return updated


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
    """BMAM + ReMe blended search ranking.

    final_rank = 0.55 * cosine_similarity + 0.30 * salience_score + 0.15 * reme_signal
    Integrates three signals:
    - Semantic similarity (cosine distance from pgvector)
    - BMAM salience (recency + frequency + importance + goal relevance)
    - ReMe retrieval frequency (frequently retrieved = proven useful)
    """
    similarity = float(r["similarity"])
    salience = float(r["salience_score"]) if r.get("salience_score") is not None else 0.5
    # ReMe signal: log-scale retrieval count, capped at 1.0
    retrieval_count = int(r["retrieval_count"]) if r.get("retrieval_count") is not None else 0
    import math
    reme_signal = min(1.0, math.log1p(retrieval_count) / 3.0)  # ~20 retrievals = 1.0
    return 0.55 * similarity + 0.30 * salience + 0.15 * reme_signal


# ── Core endpoints ─────────────────────────────────────────────────

@router.post("/remember", response_model=SemanticMemoryOut)
async def remember(req: SemanticMemoryCreate):
    # Category validation — normalize to canonical set
    cat = req.category.lower().strip() if req.category else "observation"
    if cat not in CANONICAL_CATEGORIES:
        # Auto-map legacy/unknown categories to closest canonical
        _legacy_map = {
            "general": "observation", "market_research": "research",
            "self_improvement": "capability", "alpha": "project",
            "characters": "project", "brand": "project", "product": "project",
            "project_context": "project", "own_model": "project", "webassist": "project",
            "pipeline_status": "system", "working_memory": "system",
            "reasoning_chain": "system", "architecture": "infrastructure",
            "narrative": "observation", "implementation": "capability",
            "procedure": "capability", "goal": "mission",
            "principle": "capability", "task": "system", "event": "observation",
            "outreach": "project", "project_alpha": "project",
        }
        mapped = _legacy_map.get(cat, "observation")
        logger.warning(f"category '{cat}' not canonical — mapped to '{mapped}'")
        cat = mapped
    # Mutate the request category field for downstream use
    req = req.model_copy(update={"category": cat})

    # Generate embedding — gracefully degrade if all providers unavailable
    embedding = None
    embedding_str = None
    embedding_provider = None
    _embedding_failed = False
    try:
        embedding = await get_embedding(req.content)
        embedding_provider = get_embedding_provider()
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    except Exception as e:
        _embedding_failed = True
        logger.warning(f"Embedding generation failed (storing without vector): {e}")

    pool = await get_pool()

    # AgeMem: compute importance score and check for near-duplicates
    # (requires embedding — skip dedup check if embedding unavailable)
    importance = req.importance_score if req.importance_score is not None else 0.5
    duplicate_id = None
    if embedding_str is not None:
        importance, duplicate_id = await _compute_importance(
            pool, req.category, embedding_str, override=req.importance_score,
            content=req.content,
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

    # BMAM: compute salience score before insert (requires embedding — use default if unavailable)
    salience = 0.5
    if embedding is not None:
        salience = await _compute_salience(pool, importance, embedding)

    # HyMem: Generate summary for dual-granularity storage
    summary_content = SummaryGenerator.generate(req.content, req.category)
    summary_embedding_str = None

    # Only generate summary embedding if summary differs from content AND embedding API is working
    summary_embedding_provider = None
    if summary_content != req.content and not _embedding_failed:
        try:
            summary_embedding = await get_embedding(summary_content)
            summary_embedding_provider = get_embedding_provider()
            summary_embedding_str = "[" + ",".join(str(x) for x in summary_embedding) + "]"
        except Exception as e:
            logger.warning(f"Summary embedding failed (non-fatal): {e}")

    # Build INSERT with provider-aware column selection
    openai_emb = embedding_str if embedding_provider == "openai" else None
    local_emb = embedding_str if embedding_provider == "local" else None
    openai_sum_emb = summary_embedding_str if summary_embedding_provider == "openai" else None
    local_sum_emb = summary_embedding_str if summary_embedding_provider == "local" else None

    row = await pool.fetchrow(
        """INSERT INTO semantic_memories
               (content, category, confidence, source,
                embedding, embedding_hv, embedding_local,
                metadata, importance_score, ttl_days, salience_score,
                summary_content, summary_embedding, summary_embedding_hv, summary_embedding_local,
                embedding_provider)
           VALUES ($1, $2, $3, $4,
                   CASE WHEN ($5::text) IS NOT NULL THEN ($5::text)::vector ELSE NULL END,
                   CASE WHEN ($5::text) IS NOT NULL THEN ($5::text)::halfvec(1536) ELSE NULL END,
                   CASE WHEN ($12::text) IS NOT NULL THEN ($12::text)::halfvec(384) ELSE NULL END,
                   $6, $7, $8, $9, $10,
                   CASE WHEN ($11::text) IS NOT NULL THEN ($11::text)::vector ELSE NULL END,
                   CASE WHEN ($11::text) IS NOT NULL THEN ($11::text)::halfvec(1536) ELSE NULL END,
                   CASE WHEN ($13::text) IS NOT NULL THEN ($13::text)::halfvec(384) ELSE NULL END,
                   $14)
           RETURNING id, content, category, confidence, source, created_at, importance_score, summary_content""",
        req.content, req.category, req.confidence, req.source,
        openai_emb, req.metadata, importance, req.ttl_days, salience,
        summary_content, openai_sum_emb, local_emb, local_sum_emb,
        embedding_provider,
    )
    if _embedding_failed:
        logger.warning(
            f"Stored memory {row['id']} WITHOUT embedding (category={req.category}) — "
            f"record saved for text-based lookup, vector search unavailable until embeddings restored"
        )
    else:
        logger.info(
            f"AgeMem+BMAM+HyMem: stored memory {row['id']} category={req.category} "
            f"importance={importance:.3f} salience={salience:.3f} summary_len={len(summary_content)}"
        )

    # A-Mem: auto-link new memory to similar existing memories (requires embedding)
    new_id = row["id"]
    if embedding_str is not None:
        try:
            n_links = await _amem_create_links(pool, new_id, embedding_str)
            if n_links:
                logger.info(f"A-Mem: created {n_links} bidirectional links for memory {new_id}")
        except Exception as e:
            logger.warning(f"A-Mem linking failed (non-fatal): {e}")

        # A-MEM cross-linking: boost salience of strongly related existing memories
        try:
            n_updated = await _amem_update_related(pool, new_id, req.content, embedding)
            if n_updated:
                logger.info(f"A-MEM cross-link: boosted {n_updated} related memories for {new_id}")
        except Exception as e:
            logger.warning(f"A-MEM cross-link update failed (non-fatal): {e}")

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


async def _bm25_search(
    pool,
    query: str,
    limit: int = 30,
    min_confidence: float = 0.0,
    category: str | None = None,
) -> list[dict]:
    """BM25 full-text search using PostgreSQL tsvector + ts_rank.

    Uses plainto_tsquery for full-text matching with ts_rank scoring,
    plus pg_trgm similarity as fallback for fuzzy/partial matches.
    OmniMem paper (arXiv 2604.01007v1): BM25 set-union with pgvector improves recall 30-50%.
    """
    conditions = ["archived = FALSE", "deleted_at IS NULL"]
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
    params.append(limit)

    async with pool.acquire() as conn:
        # Strategy 1: Full-text search with ts_rank (highest quality matches)
        fts_rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       utility_score, relevance_score, importance_score, salience_score,
                       retrieval_count, summary_content,
                       ts_rank(content_tsv, plainto_tsquery('english', $1)) AS bm25_score
                FROM semantic_memories
                WHERE content_tsv @@ plainto_tsquery('english', $1) AND {where}
                ORDER BY bm25_score DESC
                LIMIT ${idx}""",
            *params,
        )

        # Strategy 2: pg_trgm fuzzy fallback (catches misspellings, partial terms)
        trgm_rows = await conn.fetch(
            f"""SELECT id, content, category, confidence, source, created_at,
                       utility_score, relevance_score, importance_score, salience_score,
                       retrieval_count, summary_content,
                       word_similarity($1, content) AS bm25_score
                FROM semantic_memories
                WHERE word_similarity($1, content) > 0.15 AND {where}
                ORDER BY bm25_score DESC
                LIMIT ${idx}""",
            *params,
        )

    # Merge: FTS results first (higher quality), then trgm additions
    seen = set()
    results = []
    for row in fts_rows:
        rid = str(row["id"])
        if rid not in seen:
            seen.add(rid)
            results.append(dict(row))
    for row in trgm_rows:
        rid = str(row["id"])
        if rid not in seen:
            seen.add(rid)
            results.append(dict(row))

    return results[:limit]


@router.post("/search")
async def search(
    req: SemanticSearchQuery,
    compress: bool = Query(default=False, description="Apply SimpleMem 3-stage compression (dedup+summarize+rank). Returns SimpleMemSearchResponse when True."),
):
    """HyMem dual-granularity semantic search with optional BM25 hybrid (OmniMem).

    Automatically selects tier based on query complexity:
    - Summary tier: fast, lightweight retrieval for simple queries
    - Detailed tier: full semantic search for complex queries

    When hybrid=true (default), also runs BM25 full-text search and merges results
    via set-union (OmniMem paper finding: +30-50% recall improvement).

    Optional ?compress=true applies SimpleMem 3-stage compression (arXiv 2601.02553):
    returns a SimpleMemSearchResponse with original_count, compressed_count, and
    char reduction metadata alongside the compressed result list.
    """
    pool = await get_pool()

    # HyMem: classify query complexity to select appropriate tier
    classifier = QueryComplexityClassifier(threshold=req.complexity_threshold)
    recommended_tier, confidence = classifier.classify(req.query)

    # Use forced tier if specified, otherwise use classifier recommendation
    tier = req.force_tier or recommended_tier

    logger.info(f"HyMem: query='{req.query[:50]}...' tier={tier} hybrid={req.hybrid} (confidence={confidence:.2f})")

    if req.hybrid:
        # Run pgvector semantic + BM25 full-text in parallel, merge via set-union
        # return_exceptions=True so OpenAI quota errors don't crash BM25
        gather_results = await asyncio.gather(
            _hymem_search(pool, req, tier),
            _bm25_search(pool, req.query, limit=req.limit * 2,
                         min_confidence=req.min_confidence, category=req.category),
            return_exceptions=True,
        )
        vector_results = gather_results[0] if not isinstance(gather_results[0], BaseException) else []
        bm25_results = gather_results[1] if not isinstance(gather_results[1], BaseException) else []
        if isinstance(gather_results[0], BaseException):
            logger.warning(f"BM25 hybrid: pgvector failed ({gather_results[0]}), using BM25 only")
        if isinstance(gather_results[1], BaseException):
            logger.warning(f"BM25 hybrid: BM25 failed ({gather_results[1]}), using pgvector only")

        # Set-union merge: combine unique results from both strategies
        seen_ids = set()
        merged = []

        # Vector results come first (primary ranking)
        for r in vector_results:
            rid = str(r.id)
            if rid not in seen_ids:
                seen_ids.add(rid)
                r.tier_used = tier
                r.retrieval_strategies = ["semantic"]
                merged.append(r)

        # Add BM25-only results (not already in vector results)
        for bm25_row in bm25_results:
            rid = str(bm25_row["id"])
            if rid not in seen_ids:
                seen_ids.add(rid)
                r_out = SemanticMemoryOut(
                    id=bm25_row["id"],
                    content=bm25_row["content"],
                    category=bm25_row["category"],
                    confidence=float(bm25_row["confidence"]),
                    source=bm25_row.get("source"),
                    created_at=bm25_row["created_at"],
                    score=float(bm25_row.get("bm25_score", 0.0)),
                    importance_score=float(bm25_row["importance_score"]) if bm25_row.get("importance_score") is not None else 0.5,
                )
                r_out.tier_used = "bm25"
                r_out.retrieval_strategies = ["bm25"]
                merged.append(r_out)
            else:
                # Tag existing result as found by both strategies
                for m in merged:
                    if str(m.id) == rid and hasattr(m, 'retrieval_strategies'):
                        if "bm25" not in m.retrieval_strategies:
                            m.retrieval_strategies.append("bm25")
                        break

        results = merged[:req.limit]
        logger.info(f"BM25 hybrid: {len(vector_results)} vector + {len(bm25_results)} bm25 → {len(results)} merged (set-union)")
    else:
        # Pure pgvector search (legacy behavior)
        results = await _hymem_search(pool, req, tier)
        for r in results:
            r.tier_used = tier

    if not compress:
        return results

    # ── SimpleMem compression ─────────────────────────────────────────────────
    compressed, orig_chars, comp_chars = compress_for_context(
        results,
        top_k=req.limit,
        dedup_threshold=0.82,
    )
    return SimpleMemSearchResponse(
        results=compressed,
        original_count=len(results),
        compressed_count=len(compressed),
        original_chars=orig_chars,
        compressed_chars=comp_chars,
        reduction_pct=round(100.0 * (1 - comp_chars / orig_chars), 1) if orig_chars > 0 else 0.0,
    )


async def _hymem_search(
    pool,
    req: SemanticSearchQuery,
    tier: str
) -> list[SemanticMemoryOut]:
    """Internal HyMem dual-granularity search implementation."""

    # Embed query first — embedding is always $1 to avoid param index shifting
    try:
        query_embedding = await get_embedding(req.query)
    except Exception as e:
        logger.warning(f"HyMem search: embedding failed, returning empty vector results: {e}")
        return []
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    col = emb_col()
    cast = emb_cast("$1")
    sum_col = emb_summary_col()
    sum_cast = emb_cast("$1")  # same cast, different column

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
                           retrieval_count, summary_content,
                           1 - ({sum_col} <=> {sum_cast}) AS similarity
                    FROM semantic_memories
                    WHERE {sum_col} IS NOT NULL AND {where}
                    ORDER BY {sum_col} <=> {sum_cast}
                    LIMIT ${idx}""",
                *params,
            )

            # If summary tier returns too few results, fall back to detailed
            if len(rows) < req.limit:
                logger.info(f"HyMem: summary tier returned {len(rows)} results, falling back to detailed tier")
                rows = await conn.fetch(
                    f"""SELECT id, content, category, confidence, source, created_at,
                               utility_score, relevance_score, importance_score, salience_score,
                               retrieval_count, summary_content,
                               1 - ({col} <=> {cast}) AS similarity
                        FROM semantic_memories
                        WHERE {col} IS NOT NULL AND {where}
                        ORDER BY {col} <=> {cast}
                        LIMIT ${idx}""",
                    *params,
                )
        else:
            # HyMem Detailed Tier: full semantic search on content embeddings
            rows = await conn.fetch(
                f"""SELECT id, content, category, confidence, source, created_at,
                           utility_score, relevance_score, importance_score, salience_score,
                           summary_content,
                           1 - ({col} <=> {cast}) AS similarity
                    FROM semantic_memories
                    WHERE {col} IS NOT NULL AND {where}
                    ORDER BY {col} <=> {cast}
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
    try:
        query_embedding = await get_embedding(req.query)
    except Exception as e:
        logger.warning(f"search/linked: embedding failed, returning empty: {e}")
        return {"results": [], "linked": [], "warning": "Embedding API unavailable"}
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    col = emb_col()
    cast = emb_cast("$1")

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
                       1 - ({col} <=> {cast}) AS similarity
                FROM semantic_memories
                WHERE {col} IS NOT NULL AND {where}
                ORDER BY {col} <=> {cast}
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
    semantic_weight: float = 0.4,
    keyword_weight: float = 0.2,
    bm25_weight: float = 0.25,
    structured_weight: float = 0.15,
) -> dict:
    """A-RAG hierarchical retrieval — 4 strategies in parallel, merged + ranked.

    Strategies:
      1. semantic    — pgvector cosine similarity (broad meaning-based recall)
      2. keyword     — pg_trgm word_similarity (exact/partial term matching)
      3. bm25        — PostgreSQL full-text search with ts_rank (OmniMem paper)
      4. structured  — SQL metadata filtering (importance_score, date, category)

    Scoring: arag_score = weighted sum of all strategy scores
    Returns a dict with keys: results, strategies_used, total_candidates,
    semantic_count, keyword_count, bm25_count, structured_count.
    """

    # ── Strategy 1: Semantic (pgvector halfvec cosine) ────────────────────
    async def _semantic():
        try:
            query_embedding = await get_embedding(query)
            embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            col = emb_col()
            cast = emb_cast("$1")
            conditions = ["archived = FALSE", "deleted_at IS NULL", f"{col} IS NOT NULL"]
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
                               1 - ({col} <=> {cast}) AS score
                        FROM semantic_memories
                        WHERE {where}
                        ORDER BY {col} <=> {cast}
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

    # ── Strategy 4: BM25 full-text search (OmniMem paper) ──────────────
    async def _bm25():
        try:
            conditions = ["archived = FALSE", "deleted_at IS NULL"]
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
                               ts_rank(content_tsv, plainto_tsquery('english', $1)) AS score
                        FROM semantic_memories
                        WHERE content_tsv @@ plainto_tsquery('english', $1) AND {where}
                        ORDER BY score DESC
                        LIMIT ${idx}""",
                    *params,
                )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"A-RAG BM25 strategy failed: {e}")
            return []

    # ── Run all 4 strategies in parallel ─────────────────────────────────
    semantic_results, keyword_results, bm25_results, structured_results = await asyncio.gather(
        _semantic(), _keyword(), _bm25(), _structured()
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
    bm25_results = _normalize(bm25_results)
    structured_results = _normalize(structured_results)

    # ── Merge results by memory ID ────────────────────────────────────────
    merged: dict[str, dict] = {}

    def _upsert(row: dict, sem: float = 0.0, kw: float = 0.0, bm: float = 0.0, st: float = 0.0, strategy: str = "") -> None:
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
                "bm25_score": 0.0,
                "structured_score": 0.0,
                "retrieval_strategies": [],
            }
        entry = merged[rid]
        if sem > 0:
            entry["semantic_score"] = max(entry["semantic_score"], sem)
        if kw > 0:
            entry["keyword_score"] = max(entry["keyword_score"], kw)
        if bm > 0:
            entry["bm25_score"] = max(entry["bm25_score"], bm)
        if st > 0:
            entry["structured_score"] = max(entry["structured_score"], st)
        if strategy and strategy not in entry["retrieval_strategies"]:
            entry["retrieval_strategies"].append(strategy)

    for r in semantic_results:
        _upsert(r, sem=r["score"], strategy="semantic")
    for r in keyword_results:
        _upsert(r, kw=r["score"], strategy="keyword")
    for r in bm25_results:
        _upsert(r, bm=r["score"], strategy="bm25")
    for r in structured_results:
        _upsert(r, st=r["score"], strategy="structured")

    # ── Compute combined A-RAG score and sort ─────────────────────────────
    for entry in merged.values():
        entry["arag_score"] = (
            semantic_weight * entry["semantic_score"]
            + keyword_weight * entry["keyword_score"]
            + bm25_weight * entry["bm25_score"]
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
        "strategies_used": ["semantic", "keyword", "bm25", "structured"],
        "total_candidates": len(merged),
        "semantic_count": len(semantic_results),
        "keyword_count": len(keyword_results),
        "bm25_count": len(bm25_results),
        "structured_count": len(structured_results),
    }


@router.post("/arag_search", response_model=ARAGSearchResponse)
async def arag_search(req: ARAGSearchRequest):
    """A-RAG hierarchical retrieval: 4 strategies in parallel, merged + ranked.

    Runs semantic (pgvector), keyword (pg_trgm), BM25 (full-text), and structured (SQL)
    retrieval simultaneously, deduplicates by memory ID, and returns a unified ranked list.

    Ranking formula: arag_score = weighted sum of all strategy scores (configurable).
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
        bm25_weight=req.bm25_weight,
        structured_weight=req.structured_weight,
    )
    return ARAGSearchResponse(
        results=[ARAGResult(**r) for r in result["results"]],
        query=req.query,
        strategies_used=result["strategies_used"],
        total_candidates=result["total_candidates"],
        semantic_count=result["semantic_count"],
        keyword_count=result["keyword_count"],
        bm25_count=result.get("bm25_count", 0),
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
    col = emb_col()
    cast = emb_cast("$1")

    conditions = ["archived = FALSE", "deleted_at IS NULL", f"{col} IS NOT NULL"]
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
                       retrieval_count, summary_content,
                       1 - ({col} <=> {cast}) AS similarity
                FROM semantic_memories
                WHERE {where}
                ORDER BY {col} <=> {cast}
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
        col = emb_col()
        cast = emb_cast("$1")

        async with pool.acquire() as conn:
            await conn.execute("SET hnsw.iterative_scan = relaxed_order")
            rows = await conn.fetch(
                f"""SELECT id, 1 - ({col} <=> {cast}) AS similarity
                   FROM semantic_memories
                   WHERE {col} IS NOT NULL AND deleted_at IS NULL
                   ORDER BY {col} <=> {cast}
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
    provider = get_embedding_provider()
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    pool = await get_pool()

    # Provider-aware column updates
    if provider == "openai":
        emb_set = "embedding = $EMB::vector, embedding_hv = $EMB::halfvec(1536), embedding_provider = 'openai'"
    else:
        emb_set = "embedding_local = $EMB::halfvec(384), embedding_provider = 'local'"

    if req.category is not None:
        sql = f"""UPDATE semantic_memories
               SET content = $1, category = $2,
                   {emb_set.replace('$EMB', '$3')},
                   updated_at = NOW()
               WHERE id = $4 AND deleted_at IS NULL
               RETURNING id, content, category, confidence, source, created_at"""
        row = await pool.fetchrow(sql, req.content, req.category, embedding_str, req.memory_id)
    else:
        sql = f"""UPDATE semantic_memories
               SET content = $1,
                   {emb_set.replace('$EMB', '$2')},
                   updated_at = NOW()
               WHERE id = $3 AND deleted_at IS NULL
               RETURNING id, content, category, confidence, source, created_at"""
        row = await pool.fetchrow(sql, req.content, embedding_str, req.memory_id)

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
    provider = get_embedding_provider()
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    source_ids = json.dumps([str(r["id"]) for r in rows])

    if provider == "openai":
        new_row = await pool.fetchrow(
            """INSERT INTO semantic_memories
                   (content, category, confidence, source, embedding, embedding_hv,
                    embedding_provider, metadata)
               VALUES ($1, $2, $3, 'summarize_endpoint', $4::vector, $4::halfvec(1536),
                       'openai', jsonb_build_object('summarized_from', $5::jsonb))
               RETURNING id, content, category, confidence, source, created_at""",
            summary_content, summary_category, avg_confidence, embedding_str, source_ids,
        )
    else:
        new_row = await pool.fetchrow(
            """INSERT INTO semantic_memories
                   (content, category, confidence, source, embedding_local,
                    embedding_provider, metadata)
               VALUES ($1, $2, $3, 'summarize_endpoint', $4::halfvec(384),
                       'local', jsonb_build_object('summarized_from', $5::jsonb))
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


# ── Local Embedding Backfill ────────────────────────────────────────
# Embeds memories that have NULL embeddings (both OpenAI and local)
# using the local sentence-transformer model.

@router.post("/backfill-local")
async def backfill_local_embeddings(limit: int = 100):
    """Backfill memories with NULL embeddings using local sentence-transformer model.

    Targets memories where BOTH embedding_hv and embedding_local are NULL.
    Uses local model directly (not get_embedding) to avoid OpenAI attempt overhead.
    """
    from ..embeddings import _local_embed

    if not settings.local_embedding_enabled:
        raise HTTPException(status_code=400, detail="Local embedding is disabled (LOCAL_EMBEDDING_ENABLED=false)")

    pool = await get_pool()

    # Find memories with no embeddings at all
    rows = await pool.fetch(
        """SELECT id, content
           FROM semantic_memories
           WHERE embedding_hv IS NULL
             AND embedding_local IS NULL
             AND deleted_at IS NULL
             AND archived = FALSE
           ORDER BY created_at DESC
           LIMIT $1""",
        limit,
    )

    if not rows:
        return {"backfilled": 0, "message": "No memories with null embeddings found"}

    backfilled = 0
    errors = 0
    for row in rows:
        try:
            content = row["content"]
            if not content or not content.strip():
                continue
            embedding = _local_embed(content[:1000])
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await pool.execute(
                """UPDATE semantic_memories
                   SET embedding_local = $1::halfvec(384),
                       embedding_provider = COALESCE(embedding_provider, 'local')
                   WHERE id = $2""",
                embedding_str, row["id"],
            )
            backfilled += 1
        except Exception as e:
            logger.warning(f"Backfill failed for memory {row['id']}: {e}")
            errors += 1

    return {
        "backfilled": backfilled,
        "errors": errors,
        "remaining": len(rows) - backfilled - errors,
        "message": f"Backfilled {backfilled} memories with local embeddings (384-dim)",
    }

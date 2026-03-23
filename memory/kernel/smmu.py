"""Semantic Memory Management Unit (S-MMU) — L1/L2/L3 paging.

Reference: arXiv 2602.20934v1 §4 (Memory Management)

Three-level memory hierarchy:
- L1: Active context slices (in-memory, token-budgeted, fast)
- L2: Warm storage (pgvector semantic_memories + semantic_slices)
- L3: Cold storage (Neo4j graph, archived memories)

Integrates existing Otto features:
- HyMem dual-granularity retrieval for L2 search
- ARAG blended retrieval for relevance scoring
- FadeMem importance decay for eviction scoring
- Context builder tier logic for always-resident content
"""

import logging
from uuid import UUID

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding

log = logging.getLogger("otto.kernel.smmu")


class SMMU:
    """Semantic Memory Management Unit.

    Manages the 3-level memory hierarchy and handles paging
    between levels based on relevance and importance.

    Each agent gets its own SMMU instance with independent L1 state.
    """

    def __init__(self, agent_id: str = "otto"):
        self.agent_id = agent_id
        # L1 state (in-memory cache)
        self.l1_slice_ids: list[UUID] = []
        self.l1_token_count: int = 0
        self.l1_context_text: str = ""
        self.always_resident_text: str = ""
        self.interrupts_since_sync: int = 0

    async def save_state(self, trigger: str = "manual") -> UUID | None:
        """Save current L1 state as a cognitive snapshot."""
        if not self.l1_slice_ids and self.l1_token_count == 0:
            return None

        from .state import CognitiveState
        state = CognitiveState(
            l1_slice_ids=list(self.l1_slice_ids),
            l1_token_count=self.l1_token_count,
            drift_value=0.0,
            interrupts_since_sync=self.interrupts_since_sync,
            trigger=trigger,
            extra={"agent_id": self.agent_id},
        )
        pool = await get_pool()
        return await state.save(pool, agent_id=self.agent_id)

    async def load_for_message(self, message: str, channel: str = "whatsapp") -> str:
        """Load context for processing an admin message.

        This is the primary S-MMU path for conversational messages:
        1. Load always-resident slices (purpose, priorities, identity, directives)
        2. Find relevant L2 slices by embedding similarity
        3. Page in top slices until L1 capacity reached
        4. Load recent conversation history
        5. Assemble into context string
        6. Apply position bias mitigation (primacy+recency anchor at end)

        Returns assembled context text.
        """
        pool = await get_pool()
        capacity = settings.l1_capacity_tokens
        lines: list[str] = []
        used = 0
        # Track top-relevance content for position bias anchor (reset per message)
        self._top_relevance_anchor: str = ""

        def _estimate_tokens(text: str) -> int:
            return len(text) // 4

        def _add(text: str) -> bool:
            nonlocal used
            cost = _estimate_tokens(text)
            if used + cost > capacity:
                return False
            lines.append(text)
            used += cost
            return True

        # ── Always-resident: Purpose + Priorities + Directives + Working Memory ──
        # These map to protected core_memory slots — always in L1 (~2000 tokens)
        await self._load_always_resident(pool, _add)

        # ── Dynamic: Message-relevant slices from L2 ──
        # First check if we have semantic slices built
        slice_count = await pool.fetchval("SELECT COUNT(*) FROM semantic_slices")

        if slice_count > 0:
            # Use CID slices: find most relevant by centroid similarity
            await self._load_relevant_slices(pool, message, _add, capacity - used)
        else:
            # No slices yet: fall back to existing context builder approach
            await self._load_legacy_context(pool, message, channel, _add, capacity - used)

        # ── Recent memories (chronologically newest, regardless of similarity) ──
        await self._load_recent_memories(pool, _add)

        # ── Conversation history is now loaded as proper multi-turn messages
        # in ric.py instead of flat text here. This prevents the goldfish problem
        # where Otto can't connect short replies to what it just asked. ──

        # ── Pending questions ──
        await self._load_pending_questions(pool, _add)

        # ── Position bias mitigation (arXiv 2501 "lost in middle" — 30% degradation) ──
        # The most relevant dynamic content is anchored at the END as well as in the middle.
        # This exploits primacy+recency: facts at start AND end are better recalled than middle.
        if self._top_relevance_anchor:
            _add("")
            _add("[Otto] Key context anchor (most relevant retrieved memory):")
            _add(f"  {self._top_relevance_anchor}")
            _add("")

        # Update L1 tracking
        self.l1_token_count = used
        self.l1_context_text = "\n".join(lines)
        self.always_resident_text = "\n".join(lines[:20])  # First 20 lines are always-resident

        # Safety valve: compress if context exceeds threshold
        if self.l1_token_count > settings.context_compression_threshold:
            try:
                from ..context_builder import compress_context_text
                compressed, orig_tokens, new_tokens = compress_context_text(
                    self.l1_context_text, settings.context_max_tokens
                )
                log.info(
                    f"S-MMU context compression: {orig_tokens} → {new_tokens} tokens "
                    f"(threshold={settings.context_compression_threshold})"
                )
                self.l1_context_text = compressed
                self.l1_token_count = new_tokens
            except Exception as e:
                log.warning(f"S-MMU context compression failed (using uncompressed): {e}")

        return self.l1_context_text

    async def _load_always_resident(self, pool, _add) -> None:
        """Load always-resident L1 content: purpose, priorities, directives, working memory."""
        # Purpose
        try:
            row = await pool.fetchrow("SELECT content FROM core_memory WHERE slot = 'purpose'")
            if row and row["content"]:
                _add("=" * 60)
                _add("[Otto] PURPOSE (immutable — only Admin can change this):")
                _add(f"  {row['content']}")
                _add("=" * 60)
                _add("")
        except Exception:
            pass

        # Priorities
        try:
            row = await pool.fetchrow("SELECT content FROM core_memory WHERE slot = 'priorities'")
            if row and row["content"]:
                _add("[Otto] PRIORITIES (from Mev, ranked):")
                for line in row["content"].split("\n"):
                    if line.strip():
                        _add(f"  {line.strip()}")
                _add("")
        except Exception:
            pass

        # Active directives
        try:
            rows = await pool.fetch(
                """SELECT directive, priority, category FROM mission_directives
                   WHERE status = 'active' ORDER BY priority DESC LIMIT 10"""
            )
            if rows:
                _add("[Otto] Active Directives from Mev:")
                for r in rows:
                    _add(f"  [P{r['priority']}] [{r['category'].upper()}] {r['directive']}")
                _add("")
        except Exception:
            pass

        # Working memory (other core_memory slots)
        try:
            rows = await pool.fetch(
                "SELECT slot, content FROM core_memory "
                "WHERE content != '' AND slot NOT IN ('purpose', 'priorities') "
                "ORDER BY priority DESC, updated_at DESC NULLS LAST"
            )
            if rows:
                _add("[Otto] Working Memory:")
                for r in rows:
                    _add(f"  [{r['slot']}] {r['content'][:250]}")
                _add("")
        except Exception:
            pass

        # Identity facts
        try:
            rows = await pool.fetch(
                """SELECT content FROM semantic_memories
                   WHERE category = 'identity' AND confidence >= 0.8
                     AND archived IS NOT TRUE AND deleted_at IS NULL
                   ORDER BY confidence DESC LIMIT 20"""
            )
            if rows:
                _add("[Otto] Identity:")
                for r in rows:
                    _add(f"  - {r['content']}")
                _add("")
        except Exception:
            pass

    async def _load_relevant_slices(
        self, pool, message: str, _add, remaining_tokens: int
    ) -> None:
        """Load relevant L2 slices by centroid similarity to message embedding."""
        try:
            msg_embedding = await get_embedding(message)
            embedding_str = "[" + ",".join(str(x) for x in msg_embedding) + "]"

            # Find top slices by centroid similarity + importance + recency
            rows = await pool.fetch(
                """SELECT s.id, s.label, s.memory_ids, s.token_count, s.category,
                          p.importance_score, p.access_count,
                          1 - (s.centroid <=> $1::vector(1536)) AS similarity
                   FROM semantic_slices s
                   JOIN semantic_page_table p ON p.slice_id = s.id
                   WHERE s.centroid IS NOT NULL
                   ORDER BY (0.4 * (1 - (s.centroid <=> $1::vector(1536)))
                           + 0.25 * COALESCE(p.importance_score, 0.5)
                           + 0.15 * LEAST(p.access_count::float / 100.0, 1.0)
                           + 0.2 * GREATEST(0, 1.0 - EXTRACT(EPOCH FROM NOW() - s.updated_at) / 2592000.0)
                           ) DESC
                   LIMIT 10""",
                embedding_str,
            )

            if not rows:
                return

            loaded_tokens = 0
            loaded_ids = []

            # Minimum similarity floor — skip semantically unrelated slices that
            # only rank high due to access_count or importance_score (context-rot guard)
            SIMILARITY_THRESHOLD = 0.7

            for r in rows:
                if r["similarity"] < SIMILARITY_THRESHOLD:
                    log.debug(
                        f"S-MMU skipping low-similarity slice '{r['label']}' "
                        f"({r['similarity']:.3f} < {SIMILARITY_THRESHOLD})"
                    )
                    continue
                if loaded_tokens + r["token_count"] > remaining_tokens:
                    continue

                # Load actual memories in this slice
                memory_ids = r["memory_ids"]
                if not memory_ids:
                    continue

                memories = await pool.fetch(
                    """SELECT content, category FROM semantic_memories
                       WHERE id = ANY($1) AND archived IS NOT TRUE AND deleted_at IS NULL
                       ORDER BY confidence DESC""",
                    memory_ids,
                )

                if memories:
                    _add(f"[Otto] {r['label']}:")
                    for m in memories:
                        _add(f"  [{m['category']}] {m['content'][:300]}")
                    _add("")

                    loaded_tokens += r["token_count"]
                    loaded_ids.append(r["id"])

                    # Capture top-relevance content for position bias anchor (first slice only)
                    if not self._top_relevance_anchor and memories:
                        top_items = [m["content"][:180] for m in memories[:2]]
                        self._top_relevance_anchor = f"[{r['label']}] " + " | ".join(top_items)

                    # Update access tracking
                    await pool.execute(
                        """UPDATE semantic_page_table
                           SET last_accessed_at = NOW(), access_count = access_count + 1,
                               level = 'L1', loaded_at = NOW()
                           WHERE slice_id = $1""",
                        r["id"],
                    )

            self.l1_slice_ids = loaded_ids
            log.info(f"S-MMU loaded {len(loaded_ids)} slices ({loaded_tokens} tokens)")

        except Exception as e:
            log.warning(f"Slice loading failed, using legacy fallback: {e}")
            await self._load_legacy_context(pool, message, "whatsapp", _add, remaining_tokens)

    async def _load_legacy_context(
        self, pool, message: str, channel: str, _add, remaining_tokens: int
    ) -> None:
        """Fallback: use existing HyMem/ARAG retrieval when slices aren't built yet."""
        try:
            from ..routes.semantic import hymem_briefing_facts
            facts = await hymem_briefing_facts(
                pool=pool,
                query=message or "Otto mission priorities active work",
                limit=15,
                min_confidence=0.6,
                top_k_detailed=5,
                excluded_categories=("identity",),
            )
            if facts:
                _add("[Otto] Relevant context:")
                for f in facts:
                    display = f["display_content"][:300]
                    _add(f"  [{f['category']}] {display}")
                _add("")
                # Capture top-relevance for position bias anchor
                if not self._top_relevance_anchor and facts:
                    top = facts[0]
                    self._top_relevance_anchor = f"[{top['category']}] {top['display_content'][:200]}"
        except Exception as e:
            log.warning(f"Legacy context fallback failed: {e}")

        # Mission & goals
        try:
            rows = await pool.fetch(
                """SELECT content FROM semantic_memories
                   WHERE category IN ('mission', 'goal', 'decision') AND confidence >= 0.7
                     AND archived IS NOT TRUE AND deleted_at IS NULL
                   ORDER BY confidence DESC, created_at DESC LIMIT 10"""
            )
            if rows:
                _add("[Otto] Mission & Goals:")
                for r in rows:
                    _add(f"  - {r['content']}")
                _add("")
        except Exception:
            pass

    async def _load_recent_memories(self, pool, _add) -> None:
        """Load the most recently created/updated memories regardless of similarity.

        Ensures Otto can answer 'what's recent?' or 'what did we just add?'
        by always surfacing the chronologically newest memories.
        """
        try:
            rows = await pool.fetch(
                """SELECT content, category, created_at
                   FROM semantic_memories
                   WHERE archived IS NOT TRUE AND deleted_at IS NULL
                     AND category NOT IN ('identity')
                   ORDER BY created_at DESC LIMIT 8"""
            )
            if rows:
                _add("[Otto] Recent memories (newest first):")
                for r in rows:
                    age = r["created_at"].strftime("%Y-%m-%d")
                    _add(f"  [{r['category']}] ({age}) {r['content'][:250]}")
                _add("")
        except Exception:
            pass

    async def _load_conversation_history(self, pool, channel: str, _add) -> None:
        """Load recent conversation messages for continuity."""
        try:
            rows = await pool.fetch(
                """SELECT direction, content, push_name, created_at
                   FROM whatsapp_messages
                   WHERE channel = $1
                   ORDER BY created_at DESC LIMIT 20""",
                channel,
            )
            if rows:
                _add("[Otto] Recent conversation:")
                for r in reversed(rows):
                    name = r["push_name"] or ("Mev" if r["direction"] == "incoming" else "Otto")
                    _add(f"  {name}: {r['content'][:400]}")
                _add("")
        except Exception:
            pass

    async def _load_pending_questions(self, pool, _add) -> None:
        """Load unresolved pending questions."""
        try:
            rows = await pool.fetch(
                """SELECT question, intent FROM pending_questions
                   WHERE resolved_at IS NULL
                   ORDER BY asked_at DESC LIMIT 5"""
            )
            if rows:
                _add("[Otto] Pending questions (awaiting Mev):")
                for r in rows:
                    _add(f"  [{r['intent'].upper()}] {r['question']}")
                _add("")
        except Exception:
            pass

    async def load_for_agent_context(self, role: str) -> str:
        """Load simpler context for non-conversational agents (heartbeat, reflection, task_worker).

        Loads:
        1. Always-resident content (purpose, priorities, directives)
        2. Agent role description
        3. Recent agent activity
        """
        pool = await get_pool()

        # Get agent-specific L1 capacity
        agent_capacity = settings.l1_capacity_tokens
        try:
            from .agents import get_agent
            agent = get_agent(self.agent_id)
            if agent:
                agent_capacity = agent.config.l1_capacity
        except Exception:
            pass

        lines: list[str] = []
        used = 0

        def _estimate_tokens(text: str) -> int:
            return len(text) // 4

        def _add(text: str) -> bool:
            nonlocal used
            cost = _estimate_tokens(text)
            if used + cost > agent_capacity:
                return False
            lines.append(text)
            used += cost
            return True

        # Always-resident
        await self._load_always_resident(pool, _add)

        # Agent role
        _add(f"[Agent] Role: {role}")
        _add("")

        # Recent activity for this agent
        try:
            rows = await pool.fetch(
                """SELECT event_type, details, created_at
                   FROM agent_activity_log
                   WHERE agent_id = $1
                   ORDER BY created_at DESC LIMIT 5""",
                self.agent_id,
            )
            if rows:
                _add(f"[Agent] Recent activity ({self.agent_id}):")
                for r in rows:
                    _add(f"  [{r['event_type']}] {r['created_at'].isoformat()[:19]}")
                _add("")
        except Exception:
            pass

        self.l1_token_count = used
        self.l1_context_text = "\n".join(lines)
        self.always_resident_text = "\n".join(lines[:20])
        return self.l1_context_text

    async def evict_least_important(self, count: int = 3) -> int:
        """Evict least-important slices from L1 back to L2.

        eviction_score = (1 - importance) * time_since_access_normalized
        Higher score = evict first. Always-resident slices exempt.
        """
        pool = await get_pool()
        rows = await pool.fetch(
            """SELECT slice_id, importance_score, last_accessed_at
               FROM semantic_page_table
               WHERE level = 'L1'
               ORDER BY importance_score ASC, last_accessed_at ASC
               LIMIT $1""",
            count,
        )

        evicted = 0
        for r in rows:
            await pool.execute(
                """UPDATE semantic_page_table
                   SET level = 'L2', evicted_at = NOW()
                   WHERE slice_id = $1""",
                r["slice_id"],
            )
            if r["slice_id"] in self.l1_slice_ids:
                self.l1_slice_ids.remove(r["slice_id"])
            evicted += 1

        log.info(f"S-MMU evicted {evicted} slices from L1")
        return evicted


# ── Per-Agent Registry ───────────────────────────────────────────────────────

_smmu_instances: dict[str, SMMU] = {}


def get_smmu(agent_id: str = "otto") -> SMMU:
    """Get the S-MMU instance for an agent. Creates one if needed."""
    if agent_id not in _smmu_instances:
        _smmu_instances[agent_id] = SMMU(agent_id=agent_id)
    return _smmu_instances[agent_id]

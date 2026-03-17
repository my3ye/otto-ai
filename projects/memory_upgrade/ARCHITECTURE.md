# Otto Memory Architecture — MemGPT-Style Hierarchical Design

**Version:** 0.1
**Date:** 2026-02-19
**Status:** Draft — approved for implementation

---

## 1. Research Synthesis

### MemGPT / Letta (2023–2025)
OS-like virtual context management for LLMs. Key insight: treat the LLM context window like an OS manages RAM — actively page memory in and out. Three operational zones:
- **Main context**: what the model can currently see (~4k tokens, now much larger)
- **Core memory**: always-in-context scratchpad (persona + key facts, editable by model via tool calls)
- **External memory**: archival DB + recall memory (conversation history), both searchable via tool-call functions

The agent uses explicit memory functions: `core_memory_replace`, `archival_memory_insert`, `archival_memory_search`. This gives the model agency over its own memory — it decides what to remember permanently.

### Mem0 (2024–2025, arxiv 2504.19413, 29K GitHub stars)
Focuses on **deduplication and decay** in a structured fact store:
- Extracts memory-worthy facts from conversation via LLM
- Conflict resolution: newer contradicting facts invalidate older ones (update rather than append)
- Utility scoring + recency bias guide retrieval
- Result: a curated, non-redundant fact store that grows without bloat

### MIRIX (arxiv 2507.07957)
6-tier memory taxonomy: **Working → Episodic → Semantic → Procedural → Associative → Archival**. Key contributions:
- Hierarchical consolidation: episodic events are promoted to semantic memory when they accumulate
- Associative tier: links between memories (what leads to what)
- Archival is the cold store for rarely-accessed but permanent facts

### Bayesian Continual Learning
- **Catastrophic forgetting prevention**: new learning shouldn't overwrite old knowledge
- **Relevance decay**: memories naturally lose relevance over time unless reinforced
- **EMA utility updates**: utility_score = utility + 0.1 * (1 - utility) on retrieval (already partially implemented in Otto's semantic search)

---

## 2. Current Otto Memory System — Inventory

### Infrastructure
| Layer | Technology | Port | Status |
|---|---|---|---|
| Structured + Vector | PostgreSQL 17 + pgvector | 5432 | ✅ Healthy |
| Knowledge Graph | Neo4j 5.26.2 | 7474/7687 | ✅ Healthy |
| Graph API | Graphiti | 8000 | ✅ Healthy |
| Legacy Vector | Qdrant | 6333 | ❌ Unhealthy, unused |

### Database Schema (PostgreSQL)
| Table | Purpose | Key Fields |
|---|---|---|
| `sessions` | Session lifecycle | started_at, ended_at, summary, key_decisions |
| `episodic_events` | Raw event log | content, event_type, importance(1-10), consolidated, summary |
| `semantic_memories` | Long-term facts | content, category, confidence, embedding, utility_score, relevance_score, archived |
| `procedures` | Skill library | name, steps, success_count, failure_count |
| `pending_questions` | Cross-brain comms | question, intent, direction, resolved_at |
| `tasks` | Async task queue | title, prompt, status, pid, output |

### Already Implemented (Good News)
- ✅ Episodic memory with importance scoring and session linking
- ✅ Semantic memory with pgvector halfvec (HNSW index), utility_score, relevance_score, archived flag
- ✅ EMA utility updates on retrieval (semantic.py:72-80)
- ✅ Two-phase retrieval: HNSW → rerank by combined score (semantic.py:66-70)
- ✅ Procedural memory with outcome tracking
- ✅ Graphiti knowledge graph for relational/temporal facts
- ✅ Token-budgeted context injection with 8 priority tiers (context.py)
- ✅ `consolidated` flag on episodic_events (migration 009)
- ✅ `relevance_score` column exists on semantic_memories

### Gaps (What Needs Building)
- ❌ No **working memory** as a distinct controllable zone (core memory in MemGPT terms)
- ❌ No **consolidation loop**: `consolidated=False` events never actually get consolidated
- ❌ No **relevance decay**: `relevance_score` exists but no decay function runs
- ❌ No **deduplication**: semantic_memories accumulates duplicates (Mem0 gap)
- ❌ Stale `vector` column alongside `halfvec` — ~50% wasted index storage
- ❌ No **memory summarization**: episodic events are not promoted to semantic
- ❌ Context injection doesn't include working memory / core memory block

---

## 3. Target Architecture: 3-Tier Hierarchical Memory

```
┌─────────────────────────────────────────────────────────────┐
│  TIER 1: WORKING MEMORY  (in-prompt, ~1-2k tokens)         │
│  • Core identity block (always present)                      │
│  • Active session context                                    │
│  • Current task state                                        │
│  • Dynamic notes Otto can update during session              │
│  Backed by: core_memory table (PostgreSQL)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ session end / importance threshold
┌──────────────────────▼──────────────────────────────────────┐
│  TIER 2: EPISODIC MEMORY  (recent buffer, 1-7 days)        │
│  • Raw event log (observations, decisions, actions)          │
│  • Linked to sessions                                        │
│  • Consolidated flag marks what's been promoted              │
│  Backed by: episodic_events table                            │
└──────────────────────┬──────────────────────────────────────┘
                       │ consolidation (LLM-assisted, nightly)
┌──────────────────────▼──────────────────────────────────────┐
│  TIER 3: ARCHIVAL MEMORY  (long-term, searchable)          │
│  • Semantic facts (pgvector, utility+relevance scored)       │
│  • Knowledge graph (Graphiti: relationships, decisions)      │
│  • Procedures library (skill steps + outcome history)        │
│  Backed by: semantic_memories + Neo4j/Graphiti + procedures  │
└─────────────────────────────────────────────────────────────┘
```

### Tier 1: Working Memory

**What it is:** A small, always-in-context block of critical state that Otto (the LLM) can explicitly read and update. Inspired by MemGPT's "core memory."

**Schema** (new table):
```sql
CREATE TABLE core_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slot TEXT NOT NULL UNIQUE,     -- 'persona', 'active_mission', 'current_focus', 'scratch'
    content TEXT NOT NULL,
    max_tokens INTEGER DEFAULT 200,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Slots:**
- `persona`: Otto's identity summary (~200 tokens, rarely changes)
- `active_mission`: Current top priority task or goal (~150 tokens)
- `current_focus`: What Otto is working on right now (~100 tokens)
- `scratch`: Ephemeral notes for current session (~200 tokens)

**API endpoints:**
- `GET /working/memory` — return all slots as a flat string (for context injection)
- `PUT /working/memory/{slot}` — update a slot (called by Otto during session)
- `POST /working/memory/{slot}/append` — append to a slot

**Context injection**: Working memory is injected at the start of context, before episodic/semantic.

### Tier 2: Episodic Memory (Existing + Consolidation Loop)

**What it is:** The raw event journal. Short-lived buffer for recent experiences. Already exists — needs a consolidation loop.

**Consolidation trigger:** After session end OR when `consolidated=False` events > 50 per category.

**Consolidation process:**
1. Pull all `consolidated=False` events grouped by session
2. For each session group, call LLM (Gemini Flash via Gemini API — cheap) to generate:
   - A 1-2 sentence summary of key events
   - Extracted facts worth storing permanently (with category + confidence)
3. Insert extracted facts into `semantic_memories`
4. Insert graph-worthy relationships into Graphiti
5. Mark events as `consolidated=True`, store summary in `episodic_events.summary`

**API endpoints to add:**
- `POST /episodic/consolidate` — trigger consolidation for unconsolidated events
- `GET /episodic/unconsolidated` — list events pending consolidation

### Tier 3: Archival Memory (Existing + Dedup + Decay)

**What it is:** The permanent, searchable long-term store. Already exists — needs dedup and decay.

**Deduplication (Mem0 pattern):**
When inserting a new semantic memory, before insert:
1. Vector search for top-3 similar existing memories (cosine similarity > 0.92)
2. If match found: LLM decides to UPDATE (merge/replace) or INSERT (genuinely new)
3. On update: bump confidence, update content to merge facts, preserve embedding

**Relevance Decay:**
Run nightly (via systemd timer) on semantic_memories:
```sql
UPDATE semantic_memories
SET relevance_score = GREATEST(0.1, relevance_score * 0.99)
WHERE last_retrieved_at < NOW() - INTERVAL '7 days'
  AND category NOT IN ('identity', 'infrastructure')
  AND archived = FALSE;
```
Category exceptions: identity and infrastructure facts don't decay.

**Cleanup:**
```sql
UPDATE semantic_memories
SET archived = TRUE
WHERE relevance_score < 0.3 AND utility_score < 0.3 AND archived = FALSE
  AND category NOT IN ('identity', 'infrastructure');
```

**Fix stale vector column:**
- Migration 011: `ALTER TABLE semantic_memories DROP COLUMN IF EXISTS vector;`

---

## 4. Gap Analysis: Current vs Target

| Feature | Current State | Target State | Priority |
|---|---|---|---|
| Working memory / core memory | ❌ None | ✅ core_memory table + API | High |
| Context injection includes working memory | ❌ No | ✅ Tier 0 in injection | High |
| Consolidation loop | ❌ Flag exists, no process | ✅ Nightly consolidation job | High |
| Deduplication on insert | ❌ None | ✅ Similarity check + LLM merge | Medium |
| Relevance decay | ❌ Column exists, no decay | ✅ Nightly decay job | Medium |
| Old vector column removed | ❌ Still present | ✅ Migration 011 drops it | Low |
| Memory summarization | ❌ None | ✅ Episodic → semantic promotion | High |
| Qdrant removed | ❌ Still running unhealthy | ✅ Remove from compose | Low |

---

## 5. Phased Implementation Plan

### Phase 1: Working Memory (Tier 1) — Week 1
**Effort:** ~2-3 hours. Foundational.

1. **Migration 011**: Create `core_memory` table + seed default slots
2. **routes/working.py**: Add `GET /working/memory`, `PUT /working/memory/{slot}`
3. **context.py injection update**: Inject core_memory as Tier 0 (before identity)
4. **api.py**: Register new working memory router
5. **Test**: Verify `GET /context/inject` includes working memory block

### Phase 2: Maintenance Jobs — Week 1
**Effort:** ~2 hours. Fills in gaps with existing data.

1. **Migration 011 continued**: Drop old `vector` column from semantic_memories
2. **scripts/memory_decay.py**: Nightly relevance decay + archive pruning
3. **scripts/memory_consolidate.py**: Episodic → semantic consolidation (Gemini Flash)
4. **systemd timer**: `otto-memory-maintenance.timer` running nightly at 03:00 LKT
5. **POST /episodic/consolidate**: On-demand consolidation endpoint

### Phase 3: Deduplication on Insert — Week 2
**Effort:** ~3 hours. Quality improvement.

1. **Update routes/semantic.py `/remember`**: Pre-insert similarity check
2. **Merge logic**: If cosine > 0.92 → call Gemini Flash to merge or confirm distinct
3. **New field**: `merged_from UUID[]` on semantic_memories for audit trail
4. **Test**: Verify duplicate facts are merged rather than duplicated

### Phase 4: Otto Self-Memory Control — Week 2-3
**Effort:** ~3 hours. MemGPT-style agency.

1. **Tool definitions**: Expose memory management as Claude tool-callable endpoints
2. **Heartbeat integration**: Heartbeat can call `/working/memory/current_focus` to set task context
3. **Session end**: Auto-update `active_mission` based on task outcomes
4. **Documentation**: Update CLAUDE.md with memory management protocol

### Phase 5: Qdrant Removal + Cleanup — Week 3
**Effort:** ~1 hour.

1. Remove Qdrant from `~/memory/docker-compose.yml`
2. Remove any Qdrant references from codebase (verify none exist)
3. Update infrastructure fact in memory

---

## 6. Key Design Decisions

1. **Use Gemini Flash for consolidation** (not Claude): consolidation is cheap extraction work. Gemini Flash via existing API key. Cost ~$0.001/session consolidated.

2. **Don't replace Graphiti — extend it**: Graphiti handles relational/temporal knowledge. pgvector handles semantic similarity search. They're complementary.

3. **Working memory is small and deliberate**: Max 1000 tokens total across all slots. The value is not in what's stored but in what's always available without search.

4. **Dedup threshold 0.92**: Conservative. Below that, facts are probably distinct enough to keep. This prevents over-merging.

5. **Decay exceptions for identity/infrastructure**: These facts should be permanent. Decay only applies to project-specific, market, and general knowledge.

6. **Consolidation via LLM, not rules**: Rule-based summarization creates brittle summaries. An LLM extracts genuinely memorable facts. The quality/cost tradeoff favors this.

---

## 8. ONEON Memory Capsules — External Application of This Architecture

Otto's internal memory system is the proof-of-concept for ONEON Memory Capsules — the personal intelligence layer every ONEON participant will have.

**How they map:**

| Otto Internal | ONEON Memory Capsule |
|---|---|
| Tier 1 (Working Memory) | Active session context — dynamically injected per interaction |
| Tier 2 (Episodic Memory) | Personal event history — private by default |
| Tier 3 Semantic (pgvector) | Long-term knowledge — the compounding intelligence layer |
| Tier 3 Graph (Graphiti) | Relationship/decision history — governance weight source |
| Relevance decay | Capsule freshness scoring — stale context earns less |
| Deduplication | Capsule quality enforcement — no bloat, only real knowledge |

**Key differences from Otto's internal system:**
- Capsules are encrypted on-chain (not on Otto's Postgres instance)
- Capsule layers can be selectively shared for $KOIN compensation
- LLM output quality is directly tied to capsule depth (better capsule = better answers)
- Quality validators rate capsule utility — quality determines earnings

**What this means for implementation:**
Otto's memory architecture (this doc) should be treated as the **reference implementation**. When building ONEON Memory Capsules, start here. The 3-tier hierarchy, deduplication logic, relevance decay, and consolidation patterns all transfer directly — but wrapped in client-side encryption and on-chain access control.

---

## 7. Success Metrics

- Context injection consistently < 10k tokens while containing actionable state
- Zero duplicate semantic facts in `identity` and `infrastructure` categories
- Consolidation runs nightly; `consolidated=False` count stays < 50
- Working memory slots updated at session end by Otto
- `relevance_score` distribution: 60% of non-identity facts have score > 0.6 (showing active retrieval drives scores up while stale facts decay)

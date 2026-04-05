---
name: OmniMem Research — arXiv 2604.01007v1
description: Lifelong multimodal agent memory discovered via autonomous research pipeline. Key Otto gaps: BM25 hybrid search, pyramid retrieval, prompt constraint positioning.
type: project
---

## Paper
**OmniMem: Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory**  
Jiaqi Liu et al. | April 1, 2026 | github.com/aiming-lab/OmniMem  
DB Research Note ID: 22efbf05 | Episodic ID: 687bfb45  
Full summary: `/home/web3relic/otto/research/papers/2604_01007v1_summary.md`

## Key Architecture (OmniMem)

- **MAU** = Multimodal Atomic Unit: `{summary, embedding, cold_pointer, timestamp, modality, links}`
- **Pyramid Retrieval**: 3 levels under token budget (L1: summary ~10 tokens → L2: full text if sim>0.4 → L3: raw greedy fill)
- **Hybrid Dense+Sparse**: FAISS vector + BM25 keyword, merged via **set-union** (not score fusion)
- **KG augmentation**: 7 entity types, h-hop neighborhood expansion with distance-decay scoring

## Key Finding
Bug fixes (+175%), architectural changes (+44%), and prompt engineering (+188%) each **individually beat cumulative hyperparameter tuning**. Autonomous pipeline (50 experiments, 72h) discovered all of this without human intervention.

## Otto Gaps (Priority Order)

**P1 — BM25 hybrid search** (1-2 days): Otto has pure pgvector, no sparse/keyword retrieval. Add pg_trgm/tsvector BM25 alongside vector search with set-union merge. Expected: +30-50% recall for keyword-heavy queries.

**P2 — Pyramid retrieval in S-MMU** (3-5 days): S-MMU loads full content flat. 3-level pyramid under token budget would reduce context rot significantly.

**P3 — Prompt constraint positioning** (1 day, zero code): Move format constraints BEFORE task descriptions in all agent prompts. Found +188% improvement in structured output tasks.

**P4 — Pre-ingestion dedup** (1 day): Current 0.96 dedup is post-store. Pre-ingestion check at 0.85-0.9 threshold would prevent noisy memories entering the store.

**P5 — Verify Graphiti h-hop wired** (audit): Otto has Neo4j + Graphiti but unclear if h-hop neighborhood expansion is used during retrieval. Check graphiti search calls.

## What NOT to Do
- AutoResearchClaw pipeline: already evaluated (March 2026), rejected — too complex, 23 stages, OpenAI-dependent, paper-generation focus. OmniMem's *framing* of discovery types is useful; the pipeline itself is not.

**Why:** P1 and P2 are the highest-leverage improvements with bounded scope. P3 is zero-cost and should be batched with next prompt audit cycle.  
**How to apply:** When Mev asks about memory retrieval improvements, lead with BM25 hybrid + pyramid retrieval as the concrete next steps. Do not re-research — implement.

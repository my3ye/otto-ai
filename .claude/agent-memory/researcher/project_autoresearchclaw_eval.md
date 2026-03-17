---
name: AutoResearchClaw Tool Evaluation
description: Comparative analysis of AutoResearchClaw vs Otto's current research stack — crawl quality, synthesis quality, dependency cost, fit assessment
type: project
---

## Verdict: Do NOT adopt as-is. Extract the crawl pattern instead.

**Why:** AutoResearchClaw is an end-to-end academic paper generator (idea → LaTeX paper). Otto's research tasks are about finding implementation signal, competitive intelligence, and domain understanding — not writing papers. The full 23-stage pipeline is architectural overkill.

**How to apply:** When evaluating any research tool, check whether its OUTPUT format matches what Otto actually needs. A paper generator != a research assistant.

---

## What AutoResearchClaw Is

- **3,683 stars**, actively maintained (updated 2026-03-17)
- 23-stage pipeline in 8 phases: scoping → literature discovery → synthesis → experiment design → execution → analysis → paper writing → finalization
- Generates complete LaTeX papers with experiments, figures, citations
- Claude Code skill integration via `.claude/skills/researchclaw/SKILL.md`

## Crawl Layer (Stages 3-6) — The Valuable Part

- Sources: **OpenAlex + Semantic Scholar + arXiv** with query expansion, deduplication, circuit breaker + graceful degradation
- Screens papers by relevance threshold (min 4.0 quality score)
- 4-layer citation verification: arXiv ID → CrossRef DOI → Semantic Scholar title → LLM relevance
- **This is categorically better than Otto's current WebFetch/WebSearch ad-hoc pattern**

## Synthesis Layer — Multi-Agent Debate

- Clusters findings to identify research gaps
- Multi-agent debate for hypothesis generation
- Multi-perspective peer review
- Quality is good but output is academic paper format — mismatched to Otto's needs

## Otto's Current Research Stack

| Component | Purpose | Location |
|---|---|---|
| A-RAG (arxiv 2602.03442) | Internal memory retrieval — 3 strategies parallel (semantic/keyword/structured) | semantic.py `/arag_search` |
| Research triage | Paper scoring pipeline (composite score → implement/skip) | research.py |
| Gemini sweep pattern | Once/day domain research sweep via Gemini CLI large-context | heartbeat.md |
| WebFetch/WebSearch | Ad-hoc web research | Task-level tool calls |

## Comparative Assessment

| Dimension | AutoResearchClaw | Otto Current Stack |
|---|---|---|
| Crawl sources | OpenAlex + Semantic Scholar + arXiv (multi-source, query expansion) | WebFetch/WebSearch (ad-hoc, single-call) |
| Search quality | **Significantly better** | Basic |
| Synthesis | Multi-agent debate (academic quality) | Single LLM pass |
| Output format | LaTeX academic paper | Research notes in DB |
| LLM requirement | OpenAI API key required | Claude (already have) |
| Overhead | 23 stages, hours per run | 10-30 min task |
| Fit: persona critique | **Poor** — social/cultural research, not arxiv | Better fit |
| Fit: general research | **Partial** — crawl layer only | Adequate |

## Where It Slots

- **Persona critique pipeline**: POOR FIT. Persona critique needs social, cultural, community intelligence — not ML papers from arXiv. No meaningful overlap.
- **General research tasks (implementation discovery)**: PARTIAL FIT. The literature discovery layer (stages 3-6) is genuinely valuable. The rest (experiment execution, paper writing) is irrelevant overhead.

## Dependency Costs

- Requires OpenAI API key (adds $/month cost — Otto uses Anthropic)
- Complex system: 23 stages, 1,284 tests, optional Docker — significant maintenance surface
- Not cleanly extractable: crawl layer is tightly coupled to 23-stage pipeline architecture

## Actionable Recommendation

**Build a targeted `LitSearch` tool natively:**
1. Query OpenAlex API (free, no auth key) and Semantic Scholar API (free tier)
2. Implement query expansion (add synonyms/related terms)
3. Deduplicate by DOI/arxiv_id
4. Return ranked paper list with abstracts → feed into existing research triage at `/research/papers`

This gives Otto the best part of AutoResearchClaw (multi-source literature discovery) without irrelevant overhead and without requiring OpenAI API costs.

**Research notes stored in DB:** Memory ID `da77499a-fcd1-452b-86ce-2932136f07aa`

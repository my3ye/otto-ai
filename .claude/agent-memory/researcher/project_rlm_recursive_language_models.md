---
name: RLM Recursive Language Models Research
description: Analysis of arXiv 2512.24601 — Recursive Language Models — and applicability to Otto's architecture
type: project
---

# Recursive Language Models (arXiv 2512.24601)

**Authors:** Alex L. Zhang, Tim Kraska, Omar Khattab
**Published:** Dec 31 2025 (v2: Jan 28 2026)
**Code:** github.com/alexzhang13/rlm
**DB Memory IDs:** 32b72975 (paper analysis), 7d1128f9 (Otto applicability)

## Core Concept

RLMs treat long prompts as **external environment** — model never loads full prompt into context. Instead:
1. Model receives only **metadata** (length, prefix, access functions) — a symbolic handle
2. Model writes **code in a REPL** that can recursively invoke itself on prompt slices
3. Outputs stored in REPL variables (unbounded, not autoregressive)
4. Loop repeats until model sets `Final` variable

Handles inputs **100x beyond context window** at comparable median cost to base models.

## Three Key Innovations

1. **Symbolic handle to input** — only metadata, prevents context pollution
2. **Unbounded output generation** — REPL variable storage, not raw token generation
3. **Symbolic recursion** — REPL code can call LLM on transformed slices, O(|P|) or O(|P|²) work

## Performance Results

| Task | RLM(GPT-5) | RLM(Qwen3-Coder) | RLM-Qwen3-8B (fine-tuned) |
|------|-----------|-----------------|--------------------------|
| BrowseComp+ (1K docs) | 91.3% | 44.7% | 14.0% |
| OOLONG | 56.5% | 48.0% | 32.0% |
| OOLONG-Pairs | 58.0% | 23.1% | 5.2% |

- RLM(GPT-5) outperforms base GPT-5 by up to 28.4%
- RLM-Qwen3-8B: 28.3% median improvement from only ~1K SFT samples

## Training Recipe (if ever needed)

- 750 LongBenchPro tasks with RLM(Qwen3-Coder-480B) trajectories
- Filter zero-score + single-turn → ~1K cleaned samples
- 300 steps, batch 64, 48 H100 hours (Prime RL library)
- Each root iteration = distinct SFT sample

## Emergent Behaviors (no explicit training)

- Context filtering (regex + model priors to narrow search)
- Intelligent chunking (by newlines, keywords, semantic boundaries)
- Variable stitching (store sub-call results, combine for unbounded output)

## Applicability to Otto

### Priority 1: S-MMU Symbolic Handle Pattern (HIGH IMPACT, no model training)
Current S-MMU loads full memory slice content into context (L2/L3 paging). RLM pattern: load only metadata headers (title, category, salience, first 50 chars) → model requests full content on demand. Directly addresses lost-in-the-middle problem.

### Priority 2: Long Document Processing (HIGH IMPACT)
WhatsApp document handler (sovereign_charter.docx use case): instead of chunking the whole doc upfront, give Otto metadata + access functions, let it recursively query the slices it needs. Eliminates manual chunking logic.

### Priority 3: REPL-Based Task Decomposition (MEDIUM IMPACT)
Heartbeat orchestrator could use RLM-style code execution to programmatically decompose complex tasks — write code that calls sub-agents on specific slices of the problem. More structured than current free-form task creation.

### Priority 4: Inference-Time Scaling for Hard Tasks (MEDIUM IMPACT)
For complex multi-step analysis (signal backtests, long research), apply RLM recursive self-calls to scale compute to task complexity. Complements existing LATS tree search.

**Why:** RLM's key insight maps directly to Otto's context engineering gaps identified in the 2026 context engineering research. Specifically addresses the "lost in the middle" problem and S-MMU loading inefficiency.
**How to apply:** Start with S-MMU lazy-loading (no model training required). Test on long document processing use case before broader rollout.

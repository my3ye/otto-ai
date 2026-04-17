# Architecture: Research-Superior Patterns Implementation

**Date:** 2026-04-17 | **Author:** Architect agent (Opus)  
**Inputs:** Research synthesis (25+ papers), codebase audit (95 migrations, 400+ endpoints), code-verified gap analysis (12 gaps)  
**Scope:** All patterns where peer-reviewed research is definitively superior to Otto's current implementation

---

## Problem

Otto implements 13/25+ research recommendations at production quality. But 12 verified gaps exist where research papers describe approaches that are measurably better than what Otto does today. The critical issue is **measurement failure** — GAP-01 and GAP-02 mean Otto cannot accurately assess its own performance, so all 5 learning loops (RL2F/JitRL/AutoEvolve/MARS/PreFlect) operate on noisy signals.

**Why now:** AutoEvolve has been frozen at generation 7 with 0 experiments for 30 days. RL2F accuracy has plateaued at 0.72 for 9 cycles. These are compounding — every hour Otto runs without fixing this, it learns less.

---

## Approach: 4-Phase Implementation

Each phase is independently deployable. Later phases benefit from earlier ones but don't strictly require them.

### Phase 1: Fix Active Degradation (3 tasks, ~8h, ~$2)

Fix the learning system measurement failures so Otto can accurately assess itself.

### Phase 2: Improve Context Quality (4 tasks, ~10h, ~$3)

Better memory retrieval = better agent performance across every task.

### Phase 3: Expand Learning Surface (3 tasks, ~10h, ~$2.50)

More signal sources for learning = faster improvement compounding.

### Phase 4: Observability + Future (3 tasks, ~10h, ~$3)

Long-term capabilities for production maturity.

---

## Phase 1: Fix Active Degradation

### IMPL-01: RL2F Idle-Cycle Tagging

**Research:** Constraint-injection (2026-03-23), OMNIFLOW (2603.15797)  
**Problem:** RL2F accuracy at 0.72 is inflated. ~30-40% of heartbeat cycles are idle (queue_depth=0, nothing dispatched). Predicting "do nothing" on an idle cycle is trivially correct but counts toward accuracy.  
**Verified state:** `heartbeat.md` line 881 already sets `idle_cycle` metadata on reasoning chain entries. But `rl2f.py` does NOT filter by this field when computing accuracy. The data is tagged; the queries ignore it.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/routes/rl2f.py` | Add `idle_cycle: Optional[bool]` field to RL2F feedback creation. Update accuracy queries to compute `active_accuracy` (excluding idle cycles) alongside `total_accuracy`. Add `GET /rl2f/active-accuracy` endpoint. | ~33-50, ~70-90 |
| `memory/models.py` | Add `idle_cycle: Optional[bool] = None` to `RL2FFeedbackCreate` model | Model section |
| `.claude/agents/heartbeat.md` | In RL2F write step: explicitly pass `idle_cycle: true/false` based on whether any tasks were dispatched or Mev messages processed this cycle | RL2F section (~line 881) |

**Migration:** None — `idle_cycle` can be stored in existing `metadata` JSONB column on `rl2f_feedback` table. Query via `metadata->>'idle_cycle'`.

**Verification:** After 10 heartbeat cycles, compare `total_accuracy` vs `active_accuracy`. If delta > 5pp, the fix is working.

---

### IMPL-02: Stagnation Detection + Auto-Pivot

**Research:** CORAL (2604.01658) — 5 consecutive non-improving evals → forced strategy pivot  
**Problem:** AutoEvolve frozen at gen=7, 0 experiments, 30 days. `cycles_since_improvement: 9` in meta_memory.json. The stagnation is detected (reflection.md has DEGRADED classification) but the pivot action never fires effectively.  
**Verified state:** `reflection.md` already has Step 0.5 cycle classifier that marks DEGRADED when `cycles_since_improvement >= 3`. Step 7c branches to AutoEvolve on IDLE/DEGRADED. But meta_memory shows it's not working — likely because budget exhaustion prevents the AutoEvolve experiment from actually running, or the hypothesis generation doesn't produce actionable experiments.

**Root cause (verified):** `meta_memory.json` causal hypothesis h001 says "AutoEvolve never fires because Step 7c budget gate prevents it." The forward_plan "Move AutoEvolve to Step 1 on IDLE/DEGRADED" is marked `status: done`. So the prompt was fixed, but AutoEvolve still isn't running. The issue is likely that the `/autoevolve/insights` endpoint generates hypotheses but the reflection agent doesn't create an actual experiment task from them.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/routes/autoevolve.py` | Add `POST /autoevolve/stagnation-check` endpoint: reads meta_memory.json, if `cycles_since_improvement >= 5`, returns forced pivot recommendation with specific action (rotate RL2F features, force experiment, change strategy). Add `POST /autoevolve/force-experiment` that creates an experiment directly from a hypothesis without waiting for reflection cycle. | New endpoints |
| `.claude/agents/reflection.md` | In Step 7c: after generating hypothesis, ALWAYS create an experiment task if stagnation count > 5. Remove budget-check gate that blocks experiment creation during DEGRADED cycles (the experiment IS the fix for degradation). | Step 7c |
| `meta_memory.json` | Add `stagnation_pivots` array tracking when pivots occurred and what changed. Add `auto_pivot_enabled: true` flag. | New fields |

**Migration:** None.

**Verification:** After next reflection cycle in DEGRADED state, an actual AutoEvolve experiment should be created. Check `/autoevolve/experiments?status=proposed` returns non-empty.

---

### IMPL-03: VISTA Structured Failure Labels

**Research:** VISTA (2603.18388) — hypothesis-driven prompt optimization, 28% improvement over open-loop retry  
**Problem:** When QA rejects a task and triggers retry, the rejection reason is injected as raw text. The retrying agent gets "QA said no because X" but not a structured diagnosis of what went wrong and what to do differently.  
**Verified state:** `task_runner.sh` lines 1249-1289 build failure-mode-specific context blocks. For `qa_rejected` mode, it injects the QA output as text. No structured parsing into `{failure_type, hypothesis, corrective_action}`.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `task_runner.sh` | In the `qa_rejected` retry path (~line 1265): before injecting QA output as context, call a new API endpoint to parse it into structured failure labels. Inject the structured label instead of (or alongside) raw text. | ~1265-1280 |
| `memory/routes/tasks.py` | Add `POST /tasks/parse-failure` endpoint: takes `{qa_output: str, task_title: str, task_prompt_excerpt: str}`, returns `{failure_type: str, root_cause: str, hypothesis: str, corrective_action: str}`. Uses Kimi Flash (cheapest) with a tight prompt. | New endpoint |
| `memory/routes/rl2f.py` | Extend `task_retry_feedback` to store structured failure labels alongside raw feedback. Add `failure_type` and `hypothesis` columns to enable per-type retry success analysis. | ~195-250 |

**Migration:** Add `failure_type VARCHAR(50)` and `failure_hypothesis TEXT` columns to `task_retry_feedback` table. One ALTER TABLE, no data migration needed.

**Failure types (initial taxonomy):**
- `scope_creep` — agent did more than asked
- `quality_insufficient` — output exists but doesn't meet standards
- `incomplete` — agent stopped before finishing
- `wrong_approach` — correct scope but wrong method
- `format_violation` — output format doesn't match requirements
- `timeout_related` — ran out of time/budget
- `dependency_missing` — needed something that wasn't available

**Verification:** After 5 QA-rejected retries, check that structured labels are stored and that retry prompts contain corrective actions. Compare retry success rate with/without structured feedback via `/rl2f/retry-metrics`.

---

## Phase 2: Improve Context Quality

### IMPL-04: Pyramid Retrieval + Symbolic Handles in S-MMU

**Research:** OmniMem (2604.01007) pyramid retrieval + RLM (2512.24601) symbolic handles  
**Problem:** S-MMU loads full memory content for all qualifying slices, truncated to 300 chars. This wastes context tokens on low-value expansions and causes "lost in the middle" degradation on large memory sets.  
**Verified state:** `smmu.py` line 282 truncates to 300 chars. No summary column exists on semantic_slices. Token budget check at line 264-265 only measures whether the truncated content fits.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/migrations/096_pyramid_retrieval.sql` | Add `summary VARCHAR(100)` column to `semantic_slices` table. Add `summary_embedding vector(1536)` for summary-level similarity matching. Backfill summaries from existing content (first sentence or LLM-generated). | New migration |
| `memory/kernel/smmu.py` | Rewrite `_load_relevant_slices()` to 3-level pyramid: **L1 Handle** (load summary + metadata for ALL candidates, ~10 tokens each), **L2 Expand** (load full text for top-K by similarity where sim > 0.4), **L3 Greedy Fill** (fill remaining token budget with next-best summaries). Replace 300-char truncation with structured expansion. | ~222-316 |
| `memory/kernel/smmu.py` | Add `request_expansion(slice_id)` method for on-demand content loading (symbolic handle pattern). | New method |
| `memory/routes/semantic.py` | In `_create_slice()`: generate summary via first-sentence extraction (no LLM call, fast). For slices with complex content, use LLM summarization in background. | Slice creation path |

**Token budget math:**
- Current: 10 slices × ~50 tokens each (300 chars) = ~500 tokens for memory context
- Pyramid L1: 30 candidates × ~10 tokens (summary) = ~300 tokens for screening
- Pyramid L2: Top 5 expanded × ~200 tokens = ~1000 tokens for detail
- Pyramid L3: Remaining budget (~700 tokens) for greedy fill
- Net: Same token spend, 3x more candidates screened, better precision

**Migration backfill strategy:** Run async job to generate summaries for existing ~200 active slices. Use first-sentence extraction (regex, no LLM cost). Takes ~30 seconds.

**Verification:** Compare context quality before/after via manual inspection of 5 heartbeat L1 snapshots. Measure: more relevant memories loaded per token spent.

---

### IMPL-05: Wire meta_memory.json into Reflection Decisions

**Research:** HyperAgents (2603.19461) — cross-session causal learning  
**Problem:** meta_memory.json exists and is populated, but reflection agent reads it without acting on specific fields.  
**Verified state:** File has `causal_hypotheses` (1 entry, untested), `forward_plans` (1 done), `rl2f_trend` (stagnation visible). Reflection reads it but the connection between "what meta_memory says" and "what reflection does" is loose.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/reflection.md` | Add explicit decision tree after Step 0.5: IF `causal_hypotheses` has untested entries → design test for highest-priority hypothesis. IF `forward_plans` has pending items → execute next pending plan. IF `cross_session_patterns` shows recurring failure → escalate to Mev. | After Step 0.5 |
| `meta_memory.json` | Add `cross_session_patterns: []` array (currently missing). Add `last_acted_on: timestamp` per hypothesis/plan to prevent re-processing. | Schema extension |

**Migration:** None (file-based).

**Verification:** Next reflection cycle should either test hypothesis h001 or execute a forward plan. Check reflection log for "acting on meta_memory" entries.

---

### IMPL-06: PG-CoT Constraint Gate (Prompt Experiment)

**Research:** OMNIFLOW (2603.15797) — constraint verification at each reasoning step  
**Problem:** Heartbeat dispatches tasks without systematic constraint verification beyond budget floor.  
**Verified state:** Budget gate (Gate A) and Directive gate (Gate B) exist. But no formal constraint checklist at the REFLECT→DECIDE transition that also tags idle vs active.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/heartbeat.md` | Add explicit constraint gate between OBSERVE and ACT phases: `## Constraint Gate (BEFORE any task dispatch): (1) budget_remaining > $0.10? (2) proposed work aligns with P1-P10 active directives? (3) not rate-limited? (4) Tag this cycle as idle_cycle=true if no tasks dispatched AND no Mev messages processed.` | Between OBSERVE and ACT |

**Migration:** None (prompt-only change).

**Verification:** Run as prompt experiment for 1 week (20+ cycles). Compare idle-tagged vs active-tagged accuracy in RL2F. If no measurable difference, revert.

---

### IMPL-07: A-MEM Relationship Types (Upgrade)

**Research:** A-MEM (2502.12110) — NeurIPS 2025  
**Problem:** `_amem_update_related()` boosts salience but doesn't record relationship type.  
**Verified state:** Function finds top-5 memories with sim > 0.80, boosts salience_score by +0.05. `_amem_create_links()` creates bidirectional links. Neither records extends/contradicts/refines.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/routes/semantic.py` | In `_amem_create_links()`: classify relationship type using heuristic (not LLM — too expensive per-write). Heuristic: sim > 0.95 = `extends`, same category + different content = `refines`, explicit negation keywords = `contradicts`. Store as `relationship_type` in link record. | ~627-650 |
| `memory/migrations/096_pyramid_retrieval.sql` | Add `relationship_type VARCHAR(20) DEFAULT 'related'` to memory link table (if exists) or to a new `memory_links` table. | Combined with IMPL-04 migration |

**Verification:** After 20 memory writes, check that relationship types are being assigned. Query: `SELECT relationship_type, COUNT(*) FROM memory_links GROUP BY 1`.

---

## Phase 3: Expand Learning Surface

### IMPL-08: Cross-Task Exemplar Leaderboard

**Research:** CORAL (2604.01658) — 17% improvement rate from cross-agent parentage  
**Problem:** 291+ completed tasks, zero cross-pollination. New agents start from scratch every time.  
**Verified state:** No exemplar endpoint exists in tasks.py.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/routes/tasks.py` | Add `GET /tasks/exemplars` endpoint: query params `category` (agent_type or keyword), `limit` (default 3). Returns top tasks by quality score (SOFAI-LM average) with: task_id, title, output_excerpt (500 chars), agent_type, quality_score. Filter: status=completed, qa_status=approved, output length > 200 chars. | New endpoint |
| `task_runner.sh` | In prompt assembly (~line 14 context blocks): if agent_type matches a category with exemplars, call `/tasks/exemplars?category={agent_type}&limit=3` and inject as `## Reference: Top Prior Outputs` section. Cap at 1500 tokens total. | ~After semantic memory injection |

**Guard against copying:** Inject with explicit instruction: "These are reference outputs for quality calibration. Do NOT copy structure or content — use them only to understand expected quality level and approach patterns."

**Migration:** None (queries existing data).

**Verification:** After 10 tasks with exemplar injection, compare SOFAI-LM scores vs 10 without. Track via RL2F.

---

### IMPL-09: Partial-Success Skill Extraction

**Research:** Trace2Skill (2603.25158) — skill distillation from trajectories including failures  
**Problem:** `_extract_skill_from_task()` only fires on exit_code==0. Failed tasks with useful partial outputs are discarded.  
**Verified state:** Line 1397 checks `task.get('exit_code') == 0`. Hard gate.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/routes/tasks.py` | Relax gate at line ~1397: fire skill extraction if EITHER (a) exit_code==0, OR (b) exit_code!=0 AND output length > 500 chars AND task was not a timeout (timeout_seconds not exceeded). For case (b), use modified extraction prompt: "Extract anti-patterns and partial successes from this failed task." Tag extracted procedures with `source: partial_success` in metadata for trust differentiation (start at 0.30 instead of 0.50). | ~1397-1420 |

**Migration:** None (procedures table already has metadata JSONB).

**Verification:** After next batch of failed tasks, check if new procedures appear with `source: partial_success` tag. Compare trust convergence rate vs normal procedures.

---

### IMPL-10: Worktree Isolation in Task Runner

**Research:** CORAL (2604.01658) — isolated execution environments  
**Problem:** task_runner.sh executes in main working tree. Concurrent tasks can collide on git state.  
**Verified state:** qa_runner.sh already implements worktree pattern. task_runner.sh does not.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `task_runner.sh` | For tasks with `working_directory` pointing to otto repo: create git worktree before CLI spawn, execute in worktree, merge changes back on success, cleanup worktree on exit. Mirror qa_runner.sh pattern. Only for otto-repo tasks — external repo tasks already have separate working dirs. | ~Before CLI spawn, after cleanup |

**Guard:** Only activate for tasks that modify files (agent_type in: coder, debugger, frontend-developer, backend-architect). Read-only agents (researcher, reviewer) don't need isolation.

**Migration:** None.

**Verification:** Run 2 concurrent coder tasks. Verify no git conflicts or dirty-state warnings in task logs.

---

## Phase 4: Observability + Future

### IMPL-11: Caller Profiler

**Research:** STEM Agent (2603.22359) — tool usage pattern tracking  
**Problem:** 22 agent types, no visibility into tool usage patterns.

**Changes:**

| File | Change | Lines |
|------|--------|-------|
| `memory/migrations/097_caller_profiler.sql` | New `agent_tool_usage` table: id, agent_type, tool_name, invocation_count, success_count, avg_latency_ms, last_used, session_id. Aggregated per agent_type + tool_name. | New migration |
| `memory/routes/agents.py` | Add `POST /agents/tool-usage` (log invocation), `GET /agents/tool-usage/profile?agent_type=X` (retrieve profile), `GET /agents/tool-usage/anomalies` (detect unusual patterns). | New endpoints |
| `task_runner.sh` | After task completion, parse Claude CLI output for tool invocations (grep for tool call patterns) and POST to `/agents/tool-usage`. | Post-completion |

**Migration:** New table, no existing data needed.

### IMPL-12: Cross-Encoder Reranking

**Research:** OmniMem, TrustGraph consensus  
**Conditional:** Only implement if pyramid retrieval (IMPL-04) proves insufficient after 1 week.

**Changes:** Add `ms-marco-MiniLM-L-6-v2` (80MB) cross-encoder as reranking pass in `_load_relevant_slices()` after top-10 candidates identified. **RAM constraint:** +300MB on 16GB system.

**Decision gate:** Measure pyramid retrieval context quality for 1 week. If agent SOFAI-LM scores don't improve by >2pp, implement reranking.

### IMPL-13: Context Cores (Domain-Versioned Knowledge)

**Research:** TrustGraph  
**Future:** Most valuable when project portfolio grows beyond current scope.

**Changes:** New `context_cores` table, CRUD API, integration with S-MMU L2 loading. Deferred until post-Phase 3.

---

## Key Decisions

| Decision | Chosen | Alternative | Rationale |
|----------|--------|-------------|-----------|
| **Idle-cycle tag storage** | Existing `metadata` JSONB column | New boolean column | No migration needed, JSONB query perf is fine at current scale (~500 RL2F entries) |
| **Failure label generation** | Kimi Flash LLM call | Regex/heuristic | Failure types are nuanced (scope_creep vs wrong_approach). LLM classification at $0.001/call is worth the accuracy. Kimi Flash is cheapest. |
| **Pyramid retrieval summary** | First-sentence extraction (regex) | LLM-generated summaries | Zero cost, instant, good enough for 10-token handles. LLM summarization available as async upgrade path. |
| **Cross-task exemplars** | Top 3 by SOFAI-LM score | Random sampling | Quality signal already exists (SOFAI-LM scores from metacognitive check). Use it. |
| **Partial-success trust** | Start at 0.30 (vs 0.50 for success) | Same trust as success | Partial-success patterns are less reliable. Lower initial trust lets the convergence mechanism validate them. |
| **Worktree scope** | Only coder/debugger/frontend/backend agents | All tasks | Read-only agents (researcher, reviewer) don't modify files. Worktree overhead (git operations) not worth it for them. |
| **Relationship type classification** | Heuristic (sim threshold + keyword) | LLM per-write | LLM call per memory write is too expensive at current write volume. Heuristic captures 80% of value. |
| **Stagnation pivot implementation** | Force-experiment endpoint | Prompt-only fix | Prompt-only already failed (meta_memory shows done but ineffective). Need a code-level endpoint that reflection can call reliably. |

---

## Dependencies & Ordering

```
IMPL-01 (RL2F idle tagging)     ──────────────────────→ IMPL-06 (PG-CoT gate, uses idle tag)
                                                          │
IMPL-02 (Stagnation detection)  → IMPL-05 (meta_memory)  │
                                                          │
IMPL-03 (VISTA failure labels)  ──────────────────────────┘
                                   (all Phase 1 independent of each other)

IMPL-04 (Pyramid retrieval)     → IMPL-12 (Cross-encoder, only if IMPL-04 insufficient)
  └── includes IMPL-07 (A-MEM types, shares migration)

IMPL-08 (Exemplar leaderboard)  — independent
IMPL-09 (Partial skill extract) — independent  
IMPL-10 (Worktree isolation)    — independent

IMPL-11 (Caller profiler)      — independent
IMPL-13 (Context cores)        — deferred
```

**Critical path:** IMPL-01 → IMPL-06 (idle tagging enables constraint gate experiment)  
**Highest value:** IMPL-04 (every agent benefits from better context)  
**Quickest win:** IMPL-06 (prompt-only, 1h, measurable in 1 week)

---

## Migration Plan

Only 2 migrations needed across all 13 implementations:

| Migration | Tables | Phase |
|-----------|--------|-------|
| `096_pyramid_retrieval.sql` | ALTER `semantic_slices` ADD `summary`, ALTER memory link table ADD `relationship_type` | Phase 2 |
| `097_caller_profiler.sql` | CREATE `agent_tool_usage` | Phase 4 |

Phase 1 and Phase 3 require NO migrations — all storage uses existing JSONB columns or file-based state.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Pyramid retrieval degrades context quality | HIGH | Keep current 300-char truncation as fallback. A/B test via feature flag in smmu.py. |
| Structured failure labels add latency to retry path | LOW | Kimi Flash call is <1s. Retry already takes 60s+. Negligible. |
| Cross-task exemplars cause agents to copy rather than innovate | MEDIUM | Anti-copying instruction in prompt. Monitor output diversity. |
| Stagnation force-experiment creates bad experiments | MEDIUM | AutoEvolve already has evaluation + rollback. Forced experiments are evaluated same as voluntary ones. |
| Worktree isolation slows task startup | LOW | git worktree create is <1s. Only applies to 4 agent types. |
| Summary generation is too lossy | MEDIUM | Start with first-sentence extraction. If inadequate, add LLM summarization as async background job. |

---

## Estimated Total Cost

| Phase | Tasks | Agent Hours | Agent Cost | Timeline |
|-------|-------|-------------|------------|----------|
| Phase 1 | 3 | 8h | ~$2.00 | Immediate (this session) |
| Phase 2 | 4 | 10h | ~$3.00 | Next 48h |
| Phase 3 | 3 | 10h | ~$2.50 | This week |
| Phase 4 | 3 | 10h | ~$3.00 | Next week |
| **Total** | **13** | **~38h** | **~$10.50** | **~7 days** |

---

## Implementation Task Specifications

### For Workflow Steps 1-4

**Step 1 (Phase 1 — Fix Degradation):**
- Task 1A: IMPL-01 (RL2F idle tagging) — modify rl2f.py, models.py, heartbeat.md
- Task 1B: IMPL-02 (Stagnation pivot) — modify autoevolve.py, reflection.md, meta_memory.json
- Task 1C: IMPL-03 (VISTA failure labels) — modify task_runner.sh, add endpoint in tasks.py, migration for task_retry_feedback columns

**Step 2 (Phase 2 — Context Quality):**
- Task 2A: IMPL-04+07 (Pyramid retrieval + A-MEM types) — migration 096, rewrite smmu.py, modify semantic.py
- Task 2B: IMPL-05 (meta_memory wiring) — modify reflection.md, extend meta_memory.json
- Task 2C: IMPL-06 (PG-CoT constraint gate) — modify heartbeat.md (prompt-only)

**Step 3 (Phase 3 — Learning Surface):**
- Task 3A: IMPL-08 (Cross-task exemplars) — new endpoint in tasks.py, modify task_runner.sh
- Task 3B: IMPL-09 (Partial skill extraction) — modify tasks.py gate logic
- Task 3C: IMPL-10 (Worktree isolation) — modify task_runner.sh

**Step 4 (Phase 4 — Observability):**
- Task 4A: IMPL-11 (Caller profiler) — migration 097, new endpoints, task_runner.sh logging
- Task 4B: IMPL-12 (Cross-encoder) — conditional on Phase 2 results
- Task 4C: IMPL-13 (Context cores) — deferred

---

*Architecture complete. 13 implementations across 4 phases. 2 migrations. ~38h estimated effort. Critical path: IMPL-01 (idle tagging) unlocks reliable metrics for everything else.*

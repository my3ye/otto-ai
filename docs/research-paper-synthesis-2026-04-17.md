# Otto Research Paper Learnings — Synthesis Document
**Generated:** 2026-04-17 | **Status:** Complete | **Papers:** 25+ | **Task:** Gap Analysis Ready

---

## Overview

This document synthesizes all research paper learnings stored in Otto's memory system as of 2026-04-17. Sources: semantic memory API, research notes DB (114 notes), research papers table (11 papers), researcher agent memory files. Organized for downstream gap analysis.

**Papers by Status:**
- **Implemented:** AgentOS (2602.20934), HyMem (2604.01401), RL2F (2501.07215), MARS (2501.09150), JitRL (2410.05047)
- **Scored / Pending Implementation:** Externalization (2604.08224), Harness (2604.11535)
- **Queued (implement status):** A-MEM (2502.12110), AgeMem (2601.01885), Sybil Detection (2505.09313), Pump.fun Graduation (2602.14860)
- **Analyzed (not in papers table):** CORAL (2604.01658), OmniMem (2604.01007), HiClaw, TrustGraph, VISTA (2603.18388), HyperAgents (2603.19461), STEM (2603.22359), Trace2Skill (2603.25158), OMNIFLOW (2603.15797), RLM (2512.24601), A2A Protocol, Context Rot (Chroma)

---

## SECTION 1: Core Concepts

### 1.1 Externalization Progression (arXiv 2604.08224)
The dominant framework for understanding modern LLM agents: capability moves from weights → context → harness.

- **Weights layer (2022+):** Capability in model parameters. Fast inference, hard to update/audit.
- **Context layer (2023+):** ReAct, Tree-of-Thoughts, RAG. Converts recall to recognition problem. Ephemeral (session amnesia), finite window.
- **Harness layer (2024+):** AutoGen, MetaGPT, SWE-agent, LangGraph, Otto. External infrastructure governs what agents do, remember, and know. Key insight: self-evolving harnesses = next frontier.
- **4 Externalization Dimensions:** (1) Memory externalizes state across time. (2) Skills externalize procedural expertise. (3) Protocols externalize interaction structure. (4) Harness engineering coordinates all three into governed execution.

### 1.2 Harness Engineering Anatomy (arXiv 2604.11535 — Definition 1)
5 mandatory components of a production-grade agent harness:
1. **Project specification** — auto-loaded into every agent session (CLAUDE.md equivalent)
2. **Tools** — what the agent may invoke
3. **Knowledge base** — progressively disclosed, NOT all at once
4. **Automation skills** — executable checklists composing the above three into pipelines
5. **Advisor skills** — human control handles for irreducible decisions

**Delegation Spectrum (4 responsibilities that cannot be automated):**
1. Selecting which problems to pursue
2. Deciding when output quality is sufficient
3. Managing external stakeholder relationships
4. Ethical judgment under genuine uncertainty

### 1.3 AgentOS — Cognitive Operating System (arXiv 2602.20934) [IMPLEMENTED]
Core architecture Otto runs on. Key concepts:
- **Single Reasoning Kernel** with IVT priority queue + RIC cycle (Save→Load→Process→Align→Post)
- **S-MMU** — hierarchical memory paging: L1 (12K token cap, always-resident + dynamic slices), L2 (episodic), L3 (semantic)
- **Drift Detection** — measured every 5 interrupts; sync trigger at Δψ > 0.3
- **Cognitive Sync Pulses** — periodic alignment across memory layers
- **Peripherals** — pluggable adapters for WhatsApp, web, scheduler

### 1.4 Context Rot (Chroma Research 2026)
LLMs degrade reliably as input length grows, even on simple tasks, despite near-perfect NIAH benchmarks:
- **Needle-Question Similarity Effect:** Lower semantic similarity between Q and stored fact → steeper degradation with longer context
- **Distractor Effect:** Individual distractors have non-uniform impact amplified by length; Claude = lower hallucination, GPT = more confident but incorrect
- **Key finding:** "Shuffled haystacks outperform structured text" — random ordering beats structured ordering in long contexts
- **Critical threshold:** Context < 50% full = safe; beyond 50%, decay accelerates non-linearly
- **Positional bias:** Beginning and end of context = highest recall (RoPE positional encoding decay)

### 1.5 CORAL Multi-Agent Evolution (arXiv 2604.01658)
Multi-agent autonomous evolution framework (MIT/NUS/Stanford/Meta/Amazon/Microsoft):
- **Architecture:** 6 modules (Config, Agent System, Grader Hierarchy, Workspace, Hub/shared-mem, Core Types)
- **3-trigger heartbeat:** Per-iteration reflection, every-10-eval consolidation, stagnation pivot after 5 consecutive non-improving evals
- **Shared memory model:** `.coral/public/` filesystem — attempts (commit hash keyed), notes (markdown), skills (executable)
- **Key metrics:** SOTA on 10/13 tasks; 3-10x faster convergence vs OpenEvolve/ShinkaEvolve; cross-agent parentage = 36% of attempts, 17% improvement rate vs 9% overall; knowledge access deprivation = 55% performance drop on kernel engineering

### 1.6 HyperAgents — Self-Referential Self-Modification (arXiv 2603.19461)
Self-referential agent architecture (FAIR/Meta + UBC + Edinburgh + NYU):
- **Core claim:** Task agent + meta agent as single editable program. Meta agent rewrites itself. Eliminates DGM requirement that coding skill = self-modification skill.
- **Two phases:** (1) Metacognitive self-modification (parent generates modified self-variants). (2) Empirical evaluation (variants added to archive).
- **Key results:** DGM-H 0.710 vs DGM-custom 0.590 vs initial 0.0 on paper review; IMO math transfer DGM-H = 0.630 vs all others = 0.0
- **Critical insight:** Start with deliberately minimal agent — capability accumulates through modification cycles, not initial design.

### 1.7 Recursive Language Models (arXiv 2512.24601)
RLMs treat long prompts as external environment — model never loads full prompt into context:
- **3 innovations:** (1) Symbolic handle to input (only metadata, not content). (2) Unbounded output via REPL variable storage. (3) Symbolic recursion — REPL code calls LLM on transformed slices.
- **Performance:** RLM(GPT-5) outperforms base GPT-5 by 28.4% on BrowseComp+; handles inputs 100x beyond context window at comparable median cost.
- **Emergent behaviors (no explicit training):** Context filtering, intelligent chunking, variable stitching.
- **Training recipe (if needed):** ~1K SFT samples (750 LongBenchPro tasks), 300 steps, 48 H100 hours.

---

## SECTION 2: Architectural Recommendations

### 2.1 Memory Architecture

**Hierarchical memory is correct; gaps are in retrieval and evolution:**

From **OmniMem (arXiv 2604.01007):**
- MAU structure: `{summary, embedding, cold_pointer, timestamp, modality, links}`
- **Pyramid retrieval:** 3 levels under token budget (L1: summary ~10 tokens → L2: full text if sim>0.4 → L3: raw greedy fill)
- **Hybrid dense+sparse:** FAISS vector + BM25 keyword, merged via **set-union** (not score fusion). Expected: +30-50% recall on keyword-heavy queries.
- **KG augmentation:** 7 entity types, h-hop neighborhood expansion with distance-decay scoring
- **Critical finding:** Bug fixes (+175%), architectural changes (+44%), prompt engineering (+188%) each individually beat cumulative hyperparameter tuning. Architecture > tuning.

From **A-MEM (arXiv 2502.12110):**
- Zettelkasten-inspired atomic notes with cross-links and keyword tags
- **Living memory:** New memories trigger updates to related historical memories (cross-linking via LLM). Otto is currently append-only — this is a confirmed gap.
- Works across 6 LLM backbones. Published NeurIPS 2025.

From **AgeMem (arXiv 2601.01885):**
- Unified LTM+STM: memory operations (store/retrieve/update/summarize/discard) exposed as **tool actions** the agent invokes
- Agent autonomously decides what to remember via RL (GRPO algorithm)
- Outperforms baselines on 5 long-horizon benchmarks
- **Key insight:** Memory management should be LEARNED, not rule-based.

From **RLM (arXiv 2512.24601):**
- S-MMU should use symbolic handle pattern: load only metadata headers (title, category, salience, first 50 chars) → model requests full content on demand
- Directly addresses "lost in the middle" problem for L2/L3 paging

From **TrustGraph:**
- **Context Cores:** Portable versioned knowledge bundles per domain. Schema: `context_cores(id, domain, version, ontology_json, provenance_json, retrieval_policies_json, promoted_at)`.
- 3 RAG modes: DocumentRAG (vector chunks), GraphRAG (entity traversal), OntologyRAG (SPARQL schema-enforced)
- Otto already has the stack (Neo4j + pgvector + A-RAG); missing the versioning/bundling layer.

### 2.2 Self-Improvement Architecture

From **VISTA (arXiv 2603.18388):**
- Black-box reflective prompt optimization via hypothesis-driven exploration
- **Novel contribution:** Labeled diagnosis BEFORE rewriting. Identifies WHY prompts fail before fixing.
- **Decoupled agent roles:** Diagnosis agent ≠ rewriting agent (prevents role conflation)
- **Structured failure labels:** `{failure_type, hypothesis}` extracted from rejection reasons
- Application: Parse `qa_rejection_reason` → structured labels → inject into retry prompts (task_retry_feedback already has the field)

From **CORAL (arXiv 2604.01658):**
- **Stagnation detection:** After 5 consecutive non-improving evals → forced strategy pivot (Otto missing this)
- **Cross-task leaderboard:** Agents inspect best prior attempts before starting. Otto tasks run in isolation — zero cross-task visibility (confirmed absent by grep)
- **Per-agent memory:** Per-agent `.claude/agent-memory/` = CORAL architecture match (confirmed)
- **Worktree isolation:** Present in qa_runner.sh but NOT in task_runner.sh main path (partial match)

From **HyperAgents (arXiv 2603.19461):**
- `meta_memory.json` for cross-session causal learning continuity. Fields: `causal_hypotheses` (what changes produced improvements), `best_cycle_analysis` (which reflection cycles worked), `cross_session_patterns`.
- Store in S-MMU episodic substrate (smmu.py already supports this)

From **OMNIFLOW (arXiv 2603.15797):**
- **PG-CoT (Physics-Guided Chain-of-Thought):** Constraint verification at EACH reasoning step, not just preamble
- Transferable as experiment: add 1 constraint checkpoint at REFLECT→DECIDE transition in heartbeat.md
- **CRITICAL CAVEAT:** PG-CoT proven with hard physics constraints; Otto constraints are soft (mission alignment, budget). Treat as pilot, not proven improvement.

From **STEM Agent (arXiv 2603.22359):**
- **Caller Profiler** — tracks who (which agent/user) calls which tools, with what patterns. Enables routing optimization. Full gap in Otto (0 equivalent).
- **Skills Maturation** — skill templates auto-crystallize from successful task traces. Otto creates manually only.
- **Self-Adaptation** — failure-triggered reconfiguration. Otto: RL2F/JitRL exist but cross-session only, not in-task.
- **Memory sub-linear growth:** episodic pruning + semantic dedup + pattern extraction → growth bounded logarithmically.

### 2.3 Multi-Agent Architecture

From **HiClaw (Alibaba):**
- Manager Agent (chief of staff) coordinates stateless Worker Agents via Matrix rooms
- All comms visible in Matrix rooms — fully human-intervenable
- **Gateway pattern:** Higress AI Gateway for LLM proxy + MCP server + credential management
- Otto structural match: DAG plans = Manager dispatch ✓, gateway classifier = routing ✓, workflows = execution engine ✓

From **A2A Protocol (Google, v1.0, 2026-03-12):**
- Transport: JSON-RPC 2.0/HTTP(S), SSE streaming, webhook push
- Discovery: Agent Card at `/.well-known/agent.json` (identity, skills, endpoint, auth)
- Task lifecycle: `working → input-required → completed/failed/canceled/rejected`
- 150+ orgs adopted. Linux Foundation, Apache 2.0. **IMPLEMENTED** in Otto (`memory/routes/a2a.py`)

From **Trace2Skill (arXiv 2603.25158):**
- **3-stage pipeline:** Trajectory Generation → Parallel Patch Proposal → Conflict-Free Consolidation
- **Two evolution modes:** Deepening (refine existing) vs Creation (build from scratch)
- **20x faster** than sequential with better quality via parallel sub-agent analysis
- **Cross-model transfer:** Skills authored by smaller models improve larger ones
- **Otto parallel:** `_extract_skill_from_task()` in tasks.py (~line 1346) = primitive equivalent. Uses Kimi primary + Claude Haiku fallback. Fires on exit_code==0 only — failed tasks with useful partial outputs never generate skills (confirmed gap).

### 2.4 Context Engineering Architecture

Consensus 4-strategy framework (Anthropic/LangChain):
1. **Write** — persist outside context window (scratchpads, memory stores)
2. **Select** — retrieve only relevant information per step (RAG, embedding search)
3. **Compress** — summarize/trim when context grows large (auto-compact at 95%)
4. **Isolate** — split tasks across sub-agents with focused context windows

**Otto alignment with 2026 consensus:**
- L1/L2/L3 S-MMU hierarchy = matches hierarchical memory ✓
- Semantic slices with centroid-similarity = matches Select strategy ✓
- Auto-compact safety valve = matches Compress strategy ✓
- Sub-agents (heartbeat/reflection/task workers) = matches Isolate strategy ✓
- Always-resident slots = matches "position critical info at start" ✓
- CAT protocol (workspace handoff) = matches multi-agent context sharing ✓

---

## SECTION 3: Implementation Patterns

### 3.1 Implemented in Otto (Reference)

| System | Paper | File | Status |
|--------|-------|------|--------|
| AgentOS Kernel | 2602.20934 | `memory/kernel/reasoning_kernel.py` | LIVE |
| IVT Priority Queue | 2602.20934 | `memory/kernel/ivt.py` | LIVE |
| RIC Cycle | 2602.20934 | `memory/kernel/ric.py` | LIVE |
| S-MMU Paging | 2602.20934 | `memory/kernel/smmu.py` | LIVE |
| Drift Detection | 2602.20934 | `memory/kernel/drift.py` | LIVE |
| HyMem Dual-Granularity | 2604.01401 | `memory/routes/` | LIVE |
| RL2F 2-Layer Feedback | 2501.07215 | `memory/routes/rl2f.py` | LIVE |
| MARS Adversarial Reflection | 2501.09150 | Reflection heartbeat | LIVE |
| JitRL Experience Replay | 2410.05047 | `memory/routes/routing.py` | LIVE |
| A-RAG 3-Strategy Search | — | Memory retrieval pipeline | LIVE |
| A2A Protocol | Google v1.0 | `memory/routes/a2a.py` | LIVE |
| BM25 Hybrid Search | OmniMem | pg_trgm/tsvector | DEPLOYED (cycle 532) |
| Skill Extraction | Trace2Skill | `memory/routes/tasks.py:1346` | PARTIAL |

### 3.2 VISTA Hypothesis Loop (Priority P1, ~$3 cost)
**Pattern:** Parse rejection reasons into structured failure labels before retry.

```python
# In task_runner.sh / task retry path:
# 1. Extract structured label from qa_rejection_reason
failure_label = {
    "failure_type": "scope_creep|quality|incomplete|...",
    "hypothesis": "agent did X when it should have done Y because Z"
}
# 2. Inject into retry task prompt (task_retry_feedback already exists)
# 3. Score improvement via RL2F after retry
```
**File:** `task_runner.sh` retry path + `task_retry_feedback` field
**Source:** VISTA (arXiv 2603.18388), validated 8/10

### 3.3 CORAL Stagnation Detection (Priority P1)
**Pattern:** Count consecutive non-improving evals → force strategy pivot at threshold 5.

```python
# In autoevolve.py or reflection.md:
# Current: RL2F logs failures, no counter
# Target: consecutive_non_improving_evals counter
# At threshold 5: trigger pivot (change agent type, change approach, escalate)
# Grep-verified gap: stagnation|consecutive.*fail → 0 hits in otto/memory/
```
**File:** `autoevolve.py` or `reflection.md`
**Source:** CORAL (arXiv 2604.01658), grep-verified absent

### 3.4 Cross-Task Leaderboard (Priority P2)
**Pattern:** Top-N completed task outputs accessible to new agents before starting.

```bash
# New API endpoint:
GET /tasks/top-outputs?category=X&limit=5
# Returns: task_id, title, output_excerpt, quality_score, agent_type
# Pattern: new agent calls this to inspect best prior work before starting
```
**File:** `memory/routes/tasks.py` — new endpoint
**Source:** CORAL (arXiv 2604.01658), grep-verified absent

### 3.5 OmniMem Pyramid Retrieval (Priority P2)
**Pattern:** 3-level retrieval under token budget constraint.

```python
# In smmu.py / S-MMU retrieval:
# L1: load summary (~10 tokens) for all candidate memories
# If sim > 0.4: load full text (L2)
# If token budget remains: greedy fill (L3)
# Current: flat load of all matching slices — token wasteful
```
**File:** `memory/kernel/smmu.py`
**Source:** OmniMem (arXiv 2604.01007), validated

### 3.6 HyperAgents meta_memory.json (Priority P2)
**Pattern:** Cross-session causal learning log appended to S-MMU episodic store.

```json
{
  "causal_hypotheses": [
    {"change": "added budget gate to heartbeat", "effect": "+23% on-budget completion", "cycle": 14}
  ],
  "best_cycle_analysis": {"cycle": 12, "why": "clear task scope, explicit constraints"},
  "cross_session_patterns": ["budget gate prevents runaway tasks", "RL2F idle tagging needed"]
}
```
**File:** New file `~/otto/meta_memory.json`, loaded into S-MMU episodic
**Source:** HyperAgents (arXiv 2603.19461), validated action

### 3.7 A-MEM Living Memory (Priority P3)
**Pattern:** On every new memory write, trigger cross-link update to related existing memories.

```python
# In semantic/remember endpoint:
# 1. Find top-K related existing memories (sim > threshold)
# 2. Append cross-link: {"related_to": new_id, "relationship": "extends|contradicts|refines"}
# 3. Update existing memory's links field (NOT content — preserve original)
# Current: append-only, no cross-linking
```
**File:** `memory/routes/semantic.py`
**Source:** A-MEM (arXiv 2502.12110), NeurIPS 2025

### 3.8 RL2F Idle-Cycle Tagging (Priority P1)
**Pattern:** Tag predictions as idle vs active at write time; score separately.

```python
# In rl2f.py / heartbeat RL2F write:
# Add: idle_cycle: True if queue_depth == 0 and no tasks dispatched
# Score: active_cycle_accuracy separately (30-40% of entries are idle = trivially correct)
# Root cause of 36% accuracy / 12-cycle RL2F decline
```
**File:** `memory/routes/rl2f.py` + `heartbeat.md`
**Source:** Constraint-injection research (2026-03-23), OMNIFLOW validation

### 3.9 S-MMU Symbolic Handle (Priority P2)
**Pattern:** Load only metadata headers into L1; fetch full content on demand.

```python
# Current: S-MMU loads full slice content for all L2/L3 candidates
# Target: load {title, category, salience, first_50_chars} as handle
# Agent requests full content via explicit tool call if needed
# Prevents "lost in middle" on large memory sets
```
**File:** `memory/kernel/smmu.py`
**Source:** RLM (arXiv 2512.24601), validated high-impact

### 3.10 PG-CoT Constraint Gate (Priority P2 — EXPERIMENTAL)
**Pattern:** Single constraint checkpoint at REFLECT→DECIDE in heartbeat OODA loop.

```markdown
# In heartbeat.md, at REFLECT→DECIDE transition:
## Constraint Gate
Before dispatching any task or action:
- [ ] budget_remaining > $0.10 (binary abort if false)
- [ ] proposed task aligns with active P1-P10 directives (soft check)
- [ ] not rate-limited (binary abort if true)
Tag prediction as idle_cycle vs active_cycle BEFORE RL2F write.
```
**File:** `.claude/agents/heartbeat.md`
**Source:** OMNIFLOW (2603.15797) + Constraint-injection (2026-03-23); treat as experiment

### 3.11 Trace2Skill Enhancement (Priority P2)
**Pattern:** Extend `_extract_skill_from_task()` to generate skills from PARTIAL successes.

```python
# Current: skills generated only on exit_code==0
# Gap: failed tasks with useful partial outputs never generate skills
# Fix: add partial_success detection (exit_code!=0 but output_quality > threshold)
# Also: run Trace2Skill's Error Analyst + Success Analyst in parallel (not sequentially)
```
**File:** `memory/routes/tasks.py:~1346`
**Source:** Trace2Skill (arXiv 2603.25158), CORAL (2604.01658)

---

## SECTION 4: Specific Techniques

### 4.1 Memory Retrieval Techniques

**BM25 + Vector Set-Union (OmniMem — DEPLOYED)**
- Implementation: pg_trgm/tsvector (BM25) alongside pgvector (dense), merged via set-union (not score fusion)
- Status: DEPLOYED as of cycle 532
- Expected gain: +30-50% recall for keyword-heavy queries

**Dual-Granularity Retrieval (HyMem — IMPLEMENTED)**
- Fine-grained fact retrieval + coarse-grained context retrieval combined
- Enables precise access at multiple abstraction levels
- Active in Otto's memory retrieval pipeline

**BMAM+ReMe Blended Ranking (implemented)**
- Blended multi-source ranking with recency-weighted merge

**h-hop Neighborhood Expansion (TrustGraph)**
- For Neo4j/Graphiti: query entity neighbors at h hops with distance-decay scoring
- Status: Graphiti used but h-hop wiring status unverified (audit needed)

**Two-Stage Retrieval with Cross-Encoder Reranking**
- Broad recall → cross-encoder reranking → strategic ordering (top evidence at start AND end)
- Otto has broad recall; missing the cross-encoder reranking stage

### 4.2 Self-Improvement Techniques

**Adversarial Reflection (MARS — IMPLEMENTED)**
- Two critic agents challenge each other to surface blind spots
- Active in reflection heartbeat

**Experience Replay RL (JitRL — IMPLEMENTED)**
- RL applied at inference time using recent trajectory data
- Wired to routing.py for task routing decisions

**2-Layer Feedback Learning (RL2F — IMPLEMENTED)**
- Layer 1: immediate reward on task outcome
- Layer 2: long-term trajectory quality assessment
- Currently at ~60% accuracy (recovering); needs idle-cycle tagging fix

**Hypothesis-Driven Prompt Optimization (VISTA)**
- Diagnosis agent labels failure type + hypothesis
- Rewriting agent takes labeled failure as input
- Current Otto: open-loop (rejection logged but not fed back structurally)

**CORAL 3-Trigger Heartbeat**
- Per-iteration micro-reflection → every-10 macro-consolidation → stagnation pivot
- Otto has dual heartbeat; missing stagnation pivot counter

**DGM-H Self-Modification (HyperAgents)**
- `autoevolve.py` already implements sandboxed variant modification (partial match)
- Gap: no `meta_memory.json` cross-session causal log
- Constraint: self-modification still requires Mev approval (constitutional)

### 4.3 Agent Skill Techniques

**Trace2Skill 3-Stage Pipeline**
- Stage 1: Trajectory generation (agent executes diverse examples)
- Stage 2: Parallel patch proposal (20-agent fleet analyzes trajectories simultaneously)
- Stage 3: Conflict-free consolidation (hierarchical inductive reasoning merges patches)
- Deepening vs Creation modes for skill evolution

**STEM Agent Caller Profiler**
- Tracks which agent/user calls which tools with what patterns
- Enables routing optimization and anomaly detection
- Full gap in Otto (0 equivalent, highest novelty)

**Progressive Tool Disclosure**
- Tool RAG: semantically retrieve relevant tools from registry based on current task
- 3x improvement in tool selection accuracy vs full listing
- Otto currently loads all tools simultaneously — confirmed gap

**Skill Disclosure on Demand**
- Per 2604.08224: skills should be loaded on demand, not all upfront
- Each skill: instructions + demos + references
- Otto's skills system partially implements this

### 4.4 Blockchain-Specific Techniques

**Sybil Detection via Subgraph Analysis (arXiv 2505.09313 — implement pending)**
- Subgraph LightGBM model. Precision 0.9428, F1 0.9303, AUC 0.9806
- Deposit address clustering as primary feature
- Application: SOS governance wallet cap (3 wallets per person)

**Pump.fun Graduation Dynamics (arXiv 2602.14860 — implement pending)**
- 655,770 tokens analyzed. 0.63% graduation rate. Graduation at ~85 SOL.
- Liquidity velocity (SOL per trade) = strongest graduation predictor
- Application: Koink.fun pre-graduation signal generation

**Dormant Token Decay (design research)**
- Decay governance weight, never balance
- 5-year half-life for contributors, 18-month for circulating
- Prevents stale governance capture

### 4.5 ZK-Specific Techniques

**zkLogin Pattern for Dynamic Keys (validated HIGH)**
- Address = H(stable_identity_inputs + salt) — never changes
- Signing key = ephemeral pair embedded in ZK-certified nonce
- For zkPresence/ONEON: replace OAuth JWT with biometric+passphrase
- Combined master_secret = HKDF(FuzzyExtract(bio) || Argon2(passphrase, salt))

**Fuzzy Extractors for Biometric ZK (CCS 2025)**
- 105-bit iris entropy, 92% TAR (true acceptance rate)
- Production-viable as of CCS 2025 publication

**PLONK > Groth16 for Dynamic Key Rotation**
- Universal setup (no per-circuit ceremony)
- SP1 Hypercube supports PLONK

**Post-Quantum Migration Frame**
- DPC algorithm: PQ-safe (pure math, no crypto ops)
- Address binding (DPCRegistry mapping(address => DPCScore)): ECDSA-dependent, NOT PQ-safe
- Migration: keep algorithm, replace binding with ML-DSA-65
- Q-Day timeline: 2027-2030 (accelerated in 2026)

---

## SECTION 5: Gap Analysis Summary

### 5.1 Confirmed Otto Gaps (Code-Verified Absent)

| Gap | Source Paper | Priority | Effort | Impact |
|-----|-------------|---------|--------|--------|
| Stagnation detection counter | CORAL (2604.01658) | P1 | 2h | HIGH — prevents RL2F spiral |
| Cross-task leaderboard | CORAL (2604.01658) | P2 | 4h | HIGH — 17% improvement rate |
| RL2F idle-cycle tagging | Constraint-injection | P1 | 2h | HIGH — fixes 36% accuracy |
| VISTA hypothesis loop | VISTA (2603.18388) | P1 | 3h | HIGH — closes RL2F open loop |
| A-MEM living memory | A-MEM (2502.12110) | P3 | 8h | MED — evolving memory |
| Pyramid retrieval in S-MMU | OmniMem (2604.01007) | P2 | 5h | HIGH — reduces context rot |
| S-MMU symbolic handles | RLM (2512.24601) | P2 | 4h | HIGH — LIM prevention |
| meta_memory.json causal log | HyperAgents (2603.19461) | P2 | 2h | MED — cross-session learning |
| Caller Profiler | STEM (2603.22359) | P3 | 1w | HIGH (novelty) — routing insight |
| Tool RAG (progressive disclosure) | 2604.08224 | P3 | 1w | MED — 3x tool selection acc |
| Partial-success skill extraction | Trace2Skill (2603.25158) | P2 | 3h | MED — more skills from fails |
| PG-CoT budget gate | OMNIFLOW (2603.15797) | P2 | 1h | MED — experiment only |
| h-hop graph wiring audit | TrustGraph | P2 | 2h | MED — verify existing |
| Context Cores domain bundles | TrustGraph | P3 | 5h | MED — versioned knowledge |
| Worktree isolation in task_runner | CORAL (2604.01658) | P2 | 3h | MED — cleaner isolation |

### 5.2 Otto Architectural Strengths (Confirmed Moats)

| Strength | vs Competition | Source Validation |
|----------|---------------|-------------------|
| 6-layer memory stack | ★★★★★ (avg ★★) | AI harness landscape 2026 |
| Self-improvement loop (RL2F+MARS+AutoEvolve) | Unique — no framework has all | AI orchestration benchmark |
| DAG task plans + auto-employment | Unique in open source | HiClaw comparison |
| Dual heartbeat (mission + reflection) | Novel operational discipline | — |
| Per-agent MEMORY.md | Matches CORAL best practice | CORAL (2604.01658) |
| Budget discipline + QA gate | Unique operational constraint | — |

### 5.3 Prioritized Implementation Queue (Top 5)

1. **RL2F Idle-Cycle Tagging** — 2h, P1, fixes immediate accuracy decline
2. **CORAL Stagnation Counter** — 2h, P1, prevents infinite loops
3. **VISTA Hypothesis Loop** — 3h, P1, closes RL2F feedback gap
4. **Pyramid Retrieval in S-MMU** — 5h, P2, reduces context rot for all agents
5. **S-MMU Symbolic Handles** — 4h, P2, prevents LIM on large memory sets

---

## Source Index

| Paper ID | Title | Status | Key Insight |
|----------|-------|--------|-------------|
| 2602.20934 | AgentOS | IMPLEMENTED | Core kernel + IVT + S-MMU |
| 2604.01401 | HyMem | IMPLEMENTED | Dual-granularity retrieval |
| 2501.07215 | RL2F | IMPLEMENTED | 2-layer feedback |
| 2501.09150 | MARS | IMPLEMENTED | Adversarial reflection |
| 2410.05047 | JitRL | IMPLEMENTED | Experience replay |
| 2604.08224 | Externalization Review | SCORED (9 relevance) | Weights→Context→Harness framework |
| 2604.11535 | Harness Engineering | SCORED (6 relevance) | 5-component harness anatomy |
| 2502.12110 | A-MEM | QUEUE | Living memory cross-linking |
| 2601.01885 | AgeMem | QUEUE | RL-driven memory management |
| 2505.09313 | Sybil Detection | QUEUE | Subgraph LightGBM, 0.94 precision |
| 2602.14860 | Pump.fun Graduation | QUEUE | Liquidity velocity predictor |
| 2604.01658 | CORAL | ANALYZED | Stagnation pivot, cross-task leaderboard |
| 2604.01007 | OmniMem | ANALYZED | Pyramid retrieval, BM25 hybrid |
| 2603.18388 | VISTA | ANALYZED | Hypothesis-driven prompt optimization |
| 2603.19461 | HyperAgents | ANALYZED | Self-referential modification, meta_memory |
| 2603.22359 | STEM Agent | ANALYZED | 5-layer extensible architecture, Caller Profiler |
| 2603.25158 | Trace2Skill | ANALYZED | Parallel skill distillation from trajectories |
| 2603.15797 | OMNIFLOW | ANALYZED | PG-CoT constraint injection (experimental) |
| 2512.24601 | RLM | ANALYZED | Symbolic handles, 100x context scaling |
| HiClaw | Alibaba multi-agent OS | ANALYZED | Manager/Worker pattern, Matrix rooms |
| TrustGraph | Context graph platform | ANALYZED | Context Cores, 3 RAG modes |
| A2A v1.0 | Google Agent protocol | IMPLEMENTED | JSON-RPC agent cards |
| Context Rot | Chroma 2026 | ANALYZED | 50% threshold, positional decay |
| Context Engineering | Anthropic/LangChain | ANALYZED | Write/Select/Compress/Isolate |

---

*Synthesis complete. 25+ papers across implemented, queued, and analyzed states. Ready for gap analysis pass.*

# STEM Agent vs Otto Architecture — Gap & Alignment Analysis

**Date**: 2026-03-28
**Source**: arXiv 2603.22359 (Alfred Shen, Aaron Shen)
**STEM**: Self-Adapting, Tool-Enabled, Extensible, Multi-Protocol

---

## 1. Primitive-by-Primitive Mapping

### P1: Protocol Gateway (5 protocols: A2A, AG-UI, A2UI, UCP, AP2)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Unified gateway, protocol-agnostic routing, fallback degradation | `/gateway/incoming` in `kernel/ric.py` — 2 channels (WhatsApp, Web) |
| **Status** | — | **PARTIAL MATCH** |

**Otto already has**: Unified routing via RIC (Reasoning Interrupt Cycle) that processes all channels through the same cognitive path. Protocol-agnostic at the kernel level — WhatsApp and Web messages both become `Interrupt` objects.

**Gap**: Only 2 input channels implemented. A2A (agent-to-agent) is the critical missing piece — Otto's task_runner spawns agents but they can't communicate with each other mid-execution. AG-UI, UCP, AP2 are lower priority for current use cases.

**Recommendation**: **P5 — LOW PRIORITY**. Otto's 2-channel gateway is sufficient for current needs. A2A would matter when multi-agent collaboration scales, but plan DAGs already provide sequential coordination. Revisit when cross-agent real-time messaging becomes a bottleneck.

---

### P2: Tool Management (MCP Externalization + Dynamic Discovery)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | All capabilities via MCP; runtime discovery + introspection + composition + versioning | Static `SKILL_REGISTRY` list in `skills.py`; semantic search over registry for Tool RAG |
| **Status** | — | **FULL GAP** |

**Otto already has**: Tool RAG in `skills.py` — semantic matching against skill descriptions to return relevant tools per task. This is *better* than dumping all tools, but the registry is manually maintained and skills can't compose.

**Gap**: No MCP server, no dynamic tool discovery, no runtime composition. Adding a new skill requires editing `skills.py`. Tools can't discover or call each other.

**STEM superiority**: Dynamic composition is genuinely powerful — complex tasks auto-assembling multi-tool chains. MCP externalization would also enable cross-system interop.

**Recommendation**: **P6 — MEDIUM-TERM**. Current static registry works for 21 agents. MCP becomes valuable when: (a) external tools need to plug in, (b) agent count exceeds manual curation, or (c) Otto needs to interop with other MCP-aware systems. Not blocking any current priority.

---

### P3: Caller Profiler (20+ behavioral dimensions)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Continuous tracking of 20+ user behavioral dimensions; adapts tool selection, communication style, task decomposition per user | None |
| **Status** | — | **FULL GAP** |

**Otto already has**: Nothing equivalent. `personality.md` defines Otto's voice statically. Mev's preferences are stored as scattered semantic memories, not structured behavioral profiles.

**Gap**: Zero structured user profiling. Otto doesn't track Mev's preferred response length, time-of-day patterns, task category preferences, communication register, or which agent types Mev requests most.

**STEM superiority**: This is the highest-novelty primitive. A profiler would reduce clarification loops and improve task decomposition accuracy — directly impacting RL2F scores.

**Recommendation**: **P3 — HIGH PRIORITY**. Implement a lightweight Caller Profiler for Mev:
- Track 5-8 dimensions: preferred response length, task categories requested, agent types selected, time-of-day activity, communication register (terse/detailed), approval rate by task type
- Store as structured JSON in semantic memory (category: `caller_profile`)
- Update on every WhatsApp interaction and task review
- Inject summary into heartbeat context briefing
- **Implementation**: ~$3-5 task, modify `kernel/ric.py` POST phase to extract dims, add `/profiler` route for storage/retrieval
- **Expected impact**: Fewer Mev clarification loops, better task scoping, RL2F improvement

---

### P4: Skills Maturation (pattern → crystallization → reusable skill)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Auto-detects recurring interaction patterns; promotes them through maturation lifecycle to reusable skills (biological pluripotency metaphor) | Manual workflow template creation; AutoEvolve mutates existing templates |
| **Status** | — | **PARTIAL — strong foundation but no auto-crystallization** |

**Otto already has**:
- Workflow templates with fitness scoring and evolutionary optimization (`routes/workflows.py`)
- AutoEvolve: reflection-driven hypothesis → experiment → keep/discard loop (`routes/autoevolve.py`)
- RL2F + JitRL for cross-session learning
- These are *better* than nothing — Otto can optimize existing workflows — but can't *create new ones from patterns*

**Gap**: No detection of recurring ad-hoc task patterns that should become workflows. If Mev asks for the same type of task 5 times, each one is dispatched independently. No "this pattern has matured — propose a template" trigger.

**STEM superiority**: Auto-crystallization is the highest compound-leverage item. It means Otto's capability library grows automatically with use.

**Recommendation**: **P2 — HIGH PRIORITY**. Add pattern detection to reflection agent:
- Query completed tasks for recurring `agent_type + prompt structure` combos (3+ occurrences)
- When detected, propose workflow template crystallization (flag to Mev for approval)
- Reflection already monitors workflow fitness — extend it to monitor task recurrence
- **Implementation**: ~$3 task, add query to `reflection.md` step + `/workflows/propose` endpoint
- **Expected impact**: Compounds Otto capability without manual authoring; directly addresses plateau

---

### P5: Self-Adaptation (in-task tool reconfiguration on failure)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Evaluates performance mid-task → reconfigures tool selections → adjusts parameters on failure → learns from failure patterns; monitors token budget/compute | RL2F (cross-session teacher feedback), JitRL (experience-based policy optimization), AutoEvolve (self-modification experiments) |
| **Status** | — | **PARTIAL — strong cross-session, weak in-task** |

**Otto already has**:
- **RL2F** (`routes/rl2f.py`): 2-layer feedback — heartbeat-level teacher critiques + task-level retry chains. Stores structured feedback for future tasks.
- **JitRL** (`routes/jitrl.py`): Training-free test-time optimization. Stores (state, action, reward) tuples, retrieves similar past states at inference, computes advantage scores.
- **AutoEvolve** (`routes/autoevolve.py`): Reflection proposes mutations to system files, tracks outcomes over N cycles.
- These are arguably *more sophisticated* than STEM's in-task adaptation for long-horizon learning.

**Gap**: No *in-task* adaptation. When a task_runner hits a failure, it exits. No retry-with-different-agent, no parameter adjustment, no fallback tool selection during execution. RL2F feedback only applies to the *next* task, not the current one.

**STEM superiority**: In-task reconfiguration catches failures before they propagate. Combined with Otto's cross-session learning, this would create both fast (in-task) and slow (cross-session) adaptation loops.

**Recommendation**: **P4 — MEDIUM PRIORITY**. Add failure-branch adaptation to `task_runner.sh`:
- On non-zero exit, log failure pattern to semantic memory (agent_type, error class, task category)
- For known failure classes (timeout, budget exhaustion, API error), retry with: alternate agent, increased timeout, reduced scope
- Keep cross-session learning (RL2F/JitRL) as-is — they're strong
- **Implementation**: ~$3-5 task, modify `task_runner.sh` exit handler
- **Expected impact**: Reduces zombie task rate, improves RL2F recovery (currently 32%, declining)

---

### P6: Agent Communication (pub-sub async, protocol-agnostic)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Pub-sub async patterns; message serialization across heterogeneous agents; protocol-agnostic routing; state sync across distributed networks | Sequential task execution via plan DAGs; output flows between workflow steps via template variables |
| **Status** | — | **PARTIAL — sequential, not async** |

**Otto already has**:
- Plan DAGs (`routes/task_plans.py`): Dependency-based execution with output injection between tasks
- Workflow step chaining: `{prev_output}` and `{step_N_output}` template variables
- These handle the coordination use case but are strictly sequential

**Gap**: No real-time async agent-to-agent communication. Agents can't publish events that other agents subscribe to during execution.

**Recommendation**: **P7 — LOW PRIORITY**. Current DAG + workflow chaining handles all production use cases. Async pub-sub would only matter for large-scale multi-agent swarms, which isn't the current architecture direction.

---

### P7: Memory Subsystem (sub-linear growth)

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Episodic pruning + semantic deduplication + pattern extraction → sub-linear growth under sustained interaction | Salience decay, episodic consolidation (event → narrative), semantic dedup (0.96 threshold), FadeMem, HyMem (dual-granularity retrieval) |
| **Status** | — | **STRONG MATCH** |

**Otto already has**:
- **Salience decay**: Automatic relevance score decay over time
- **Episodic consolidation**: Events grouped into narratives; empty narratives archived
- **Semantic dedup**: 0.96 cosine threshold prevents duplicate memories
- **FadeMem**: Memory lifecycle management
- **HyMem**: Dual-granularity retrieval (course + fine)
- **Maintenance endpoints**: `/memory/maintenance`, `/memory/salience-decay`, `/memory/consolidate`
- 205 active memories from 558+ total (effective pruning demonstrated)

**Gap**: Not benchmarked for sub-linearity. Growth rate may be sub-linear in practice (205 active from months of operation) but this hasn't been measured formally.

**Recommendation**: **P8 — MONITOR ONLY**. Otto's memory subsystem is mature and working. Add a simple growth rate metric to maintenance (count active memories over time, verify sub-linear trend) but don't rebuild anything.

---

### P8: Dynamic Tool Composition

| Aspect | STEM | Otto |
|---|---|---|
| **Architecture** | Complex tasks auto-assemble multi-tool chains at runtime based on capability introspection | Static agent selection via classifier; plan decomposition via LLM |
| **Status** | — | **PARTIAL — LLM-mediated, not introspection-based** |

**Otto already has**:
- Plan classifier that decomposes complex instructions into multi-task DAGs
- Dispatch classifier that selects agents per task
- These achieve similar *outcomes* but via LLM reasoning, not tool capability introspection

**Gap**: No formal capability introspection. The LLM selects tools based on skill descriptions, not structured capability declarations.

**Recommendation**: **P7 — LOW PRIORITY**. LLM-mediated selection works well enough at current scale. Structured introspection becomes valuable with 50+ tools or when non-LLM routing is needed for speed.

---

## 2. Architectural Conflicts

| Conflict | Details | Severity |
|---|---|---|
| MCP adoption vs static registry | Migrating to MCP would require rewriting skill discovery, agent dispatching, and potentially the workflow engine | **LOW** — can be incremental; MCP server can wrap existing registry |
| In-task adaptation vs clean exit model | `task_runner.sh` uses `set -euo pipefail` + clean exit. In-task retry adds complexity to an already sensitive script | **MEDIUM** — implement carefully with trap handlers |
| Pub-sub vs DAG model | Async pub-sub fundamentally different from sequential DAGs. Can coexist but adds conceptual overhead | **LOW** — not recommended for current phase |

---

## 3. Prioritized Recommendations

| Priority | Primitive | Action | Effort | Impact | Dependencies |
|---|---|---|---|---|---|
| **P2** | Skills Maturation | Add pattern detection to reflection + `/workflows/propose` endpoint | ~$3-5 | Compounds capability automatically | None |
| **P3** | Caller Profiler | Build 5-8 dim profiler for Mev; inject into context | ~$3-5 | Reduces clarification, improves RL2F | None |
| **P4** | Self-Adaptation | Add failure-branch retry logic to `task_runner.sh` | ~$3-5 | Reduces zombie tasks, aids RL2F recovery | None |
| **P5** | Protocol Gateway | A2A channel for agent-to-agent (future) | ~$5-10 | Enables real-time multi-agent collaboration | Scale need |
| **P6** | MCP Externalization | Wrap skill registry as MCP server | ~$5-8 | External interop, dynamic discovery | External demand |
| **P7** | Dynamic Composition | Structured capability declarations on agents | ~$2-3 | Better routing accuracy | High agent count |
| **P7** | Agent Communication | Pub-sub event bus (future) | ~$8-12 | Async multi-agent swarms | Architecture shift |
| **P8** | Memory Growth | Add sub-linearity metric to maintenance | ~$1 | Validates existing design | None |

---

## 4. Where Otto Is Already Ahead of STEM

1. **Cross-session learning**: RL2F + JitRL + AutoEvolve is a more sophisticated learning stack than STEM's in-task adaptation alone. STEM adapts within tasks; Otto learns across sessions and self-modifies its own agent prompts.

2. **Cognitive architecture**: S-MMU (L1/L2/L3 paging), IVT (priority queue), RIC (5-phase processing), drift detection — Otto has a full cognitive operating system. STEM's architecture is modular but doesn't describe this level of cognitive infrastructure.

3. **Workflow evolution**: AutoEvolve + workflow fitness scoring + evolutionary mutations is more mature than STEM's skills maturation (which is primarily pattern → template promotion, not fitness-driven optimization).

4. **Memory management**: HyMem dual-granularity retrieval, MARS dual adversarial reflection, A-RAG 3-strategy search — Otto's memory retrieval is more sophisticated than STEM's consolidation-focused approach.

---

## 5. Key Takeaway

**STEM's highest-value contribution to Otto is conceptual, not architectural.** Otto's existing systems are more mature in most areas. The three actionable gaps are:

1. **Caller Profiler** — genuinely novel, zero equivalent in Otto
2. **Skills Maturation trigger** — Otto has the infrastructure (workflows, AutoEvolve) but lacks the pattern-detection trigger
3. **In-task failure adaptation** — complementary to Otto's cross-session learning

All three can be implemented independently, incrementally, without architectural overhaul. Total estimated implementation: ~$9-15 across 3 tasks.

**License gate**: Do NOT copy any code from `alfredcs/stem-agent`. Re-implement concepts independently.

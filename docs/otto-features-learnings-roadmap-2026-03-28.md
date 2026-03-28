# Otto: Features, Learnings & Improvement Roadmap
*Generated: 2026-03-28 | Source: System manifest v1.0 + codebase analysis + operational logs*

---

## 1. Full Feature Inventory

### 1.1 Cognitive Core (AgentOS Kernel)

| Feature | File | Status | Notes |
|---|---|---|---|
| Interrupt-driven reasoning loop | `kernel/reasoning_kernel.py` | ✅ Live | All inputs are interrupts; no polling |
| Priority interrupt queue (IVT) | `kernel/ivt.py` | ✅ Live | Admin messages always highest priority |
| Save→Load→Process→Align→Post (RIC) | `kernel/ric.py` (1063 lines) | ✅ Live | Core cognitive cycle |
| L1/L2/L3 memory paging (S-MMU) | `kernel/smmu.py` (524 lines) | ✅ Live | L1=12k tokens always-resident; L2=dynamic slice retrieval |
| Semantic slice segmentation (CID) | `kernel/slicing.py` | ✅ Live | Content-addressable slice inventory |
| Cognitive drift detection (Δψ) | `kernel/drift.py` | ✅ Live | Measures every 5 interrupts; sync at Δψ>0.3 |
| Cognitive Sync Pulses | `kernel/sync.py` | ✅ Live | Multi-agent sync every 2h |
| LLM output perception/validation | `kernel/perception.py` | ✅ Live | Post-process hook chain |
| Multi-LLM provider backend | `kernel/provider.py` | ✅ Live | 3 types: claude_code_stream, openai_compatible, claude_cli |
| 9-hook post-process pipeline | `kernel/ric.py` | ✅ Live | episodic log, persist, graphiti, pending match, directive extract, reactive dispatch, drift, thought vault, cross-brain |

### 1.2 Memory Layer

| Feature | File/Endpoint | Status | Notes |
|---|---|---|---|
| Semantic memory (pgvector) | `routes/semantic.py` (1450 lines) | ✅ Live | 205+ active memories |
| HyMem dual-granularity retrieval | `semantic.py` | ✅ Live | Full content + pre-computed summaries |
| A-RAG 3-strategy retrieval | `semantic.py` | ✅ Live | Semantic + keyword + graph, merged re-ranked |
| A-MEM memory graph (Zettelkasten) | `semantic.py` | ✅ Live | Auto-links new memories to related ones |
| BMAM blended ranking | `semantic.py` | ✅ Live | Similarity + recency + importance + goal-align |
| SVC bias removal | `semantic.py` | ✅ Live | Removes top-3 bias directions from query embeddings |
| FadeMem salience decay | `routes/maintenance.py` (1731 lines) | ✅ Live | Time-weighted decay; 2400+ processed per cycle |
| SimpleMem 3-stage compression | `routes/consolidation.py` (387 lines) | ✅ Live | Dedup→summarize→rank+trim |
| Episodic event log | `routes/episodic.py` | ✅ Live | 323+ events; salience-scored |
| Episodic→narrative consolidation | `routes/maintenance.py` | ✅ Live | 7-day window; LLM summarisation |
| Procedural memory | `routes/procedural.py` | ✅ Live | Trust scores via exponential smoothing; 16 procedures |
| Working memory slots | `routes/working.py` | ✅ Live | Fast PUT /working/memory/{slot} key-value state |
| Knowledge graph (Neo4j+Graphiti) | Docker: graphiti on :8000 | ✅ Live | Temporal entity extraction, G2CP typed nodes |
| Cross-brain message graph | `kernel/agents.py` | ✅ Live | Persisted messages shared across heartbeat agents |
| Agent-to-agent (A2A) channels | `routes/a2a.py` | ✅ Live | In-process DB-backed; not protocol-level |
| Thought Vault | `routes/thought_vault.py` | ✅ Live | Captured ideas from kernel post-process hook |
| Context briefing aggregation | `routes/context.py` (613 lines) | ✅ Live | Multi-source assembly for session injection |
| Per-agent MEMORY.md files | `.claude/agent-memory/*/` | ✅ Live | 10+ agents maintain persistent topic files |

### 1.3 Learning & Self-Improvement

| Feature | File | Status | Notes |
|---|---|---|---|
| RL2F Layer 1 (heartbeat critiques) | `routes/rl2f.py` (413 lines) | ✅ Live | Per-cycle teacher feedback; 20/50 matched (40%) |
| RL2F Layer 2 (QA rejection chain) | `routes/rl2f.py` | ✅ Live | QA reject→structured feedback→retry→outcome signal |
| JiTRL experience replay | `routes/jitrl.py` (335 lines) | ✅ Live | kNN similarity→advantage computation→ranked hints at task creation |
| AutoEvolve experiment loop | `routes/autoevolve.py` (507 lines) | ✅ Live | Gen 3. Hypothesis→mutation→N-cycle eval→keep/discard |
| MARS dual-adversarial reflection | `kernel/ric.py` + reflection agent | ✅ Live | Initial→critic→synthesis per reflection cycle |
| Reasoning chain (WHY/DECIDED/EXPECTED/ACTUAL) | `routes/reasoning.py` (536 lines) | ✅ Live | Outcome matching drives RL2F L2 lesson extraction |
| Failure-branch adaptation (STEM-inspired) | `routes/failure_branch.py` | ✅ Live | Detect failure signals→root cause→correction→retest |
| Learned principles store | `routes/principles.py` | ✅ Live | Trust-scored behavioral rules extracted from RL2F misses |
| Evaluation benchmarking | `routes/eval.py` (427 lines) | ✅ Live | Benchmark-gated self-modification evaluation |
| Workflow auto-eval + evolution | `routes/workflows.py` (2242 lines) | ✅ Live | Every 3 runs: fitness scoring + template mutation |
| Self-critique (ACCURACY/COMPLETENESS/GOAL_ALIGN/BIAS) | reflection agent | ✅ Live | Per reflection cycle; scored 1–5 |

### 1.4 Task Execution Engine

| Feature | File | Status | Notes |
|---|---|---|---|
| Task queue + lifecycle | `routes/tasks.py` (1826 lines) | ✅ Live | 1255 completed, 119 failed total |
| Detached task runner (CLI) | `task_runner.sh` | ✅ Live | claude/gemini/kimi CLI; budget + preflight + trap EXIT |
| Continuous task dispatcher | `otto-task-dispatcher.service` | ✅ Live | Polls queue; auto-launches ready tasks |
| Max concurrent limit | `routes/tasks.py` | ✅ Live | 5 total: claude=3, gemini=1, kimi=1 |
| QA runner (Gemini review) | `qa_runner.sh` | ✅ Live | Post-task Gemini review; approve/reject → RL2F feedback |
| LATS-style preflect | `routes/tasks.py` | ✅ Live | Pre-decision brief surfaces lessons before task starts |
| JiTRL hint injection | `routes/tasks.py` | ✅ Live | Relevant past experiences injected at task creation |
| Artifact path storage (HiClaw) | `routes/tasks.py` | ✅ Live | Large outputs (>2KB) written to file; path stored in DB |
| Hindsight analysis | `routes/tasks.py` | ✅ Live | Post-completion lesson extraction |
| Task stop via SIGTERM | `routes/tasks.py` + gateway | ✅ Live | WhatsApp "stop task" → SIGTERM → process kill |
| DAG task orchestration (plans) | `routes/task_plans.py` (836 lines) | ✅ Live | Dependency edges; parallel/sequential/hybrid topologies |
| Agent auto-employment | `routes/task_plans.py` | ✅ Live | Activates agents from agency-agents/ (138 available) |
| Dependency output injection | `routes/task_plans.py` | ✅ Live | Prev task output flows to dependents as template vars |
| Multi-agent workflow pipelines | `routes/workflows.py` (2242 lines) | ✅ Live | Template-based; 5 steps; sequential with gate support |
| Workflow gate system | `routes/workflows.py` | ✅ Live | human_approval, code_review, security_audit checkpoints |
| Workflow evolution (mutation) | `routes/workflows.py` | ✅ Live | Template fitness tracking + mutation history |
| Wink stall monitor | `heartbeat.sh` | ✅ Live | Detects 5+ min stalled tasks; alerts |

### 1.5 Heartbeat Agents (Autonomous Loops)

| Agent | File | Schedule | Status |
|---|---|---|---|
| Orchestrator heartbeat | `agents/heartbeat.md` | Hourly :00 | ✅ Live |
| Reflection heartbeat | `agents/reflection.md` | Hourly :30 | ✅ Live |
| Alpha trading heartbeat | `agents/alpha_heartbeat.md` | Every 2h | ✅ Live |
| Crypto signal publisher | `otto-signals.timer` | Every 15m | ✅ Live |
| Alpha market watcher | `otto-alpha-watcher.timer` | Every 5m | ✅ Live |
| Research pipeline | `otto-research-pipeline.timer` | Every 3h | ✅ Live |
| Security audit | `otto-security-audit.timer` | Every 3 days | ✅ Live |
| Vuln sync | `otto-vuln-sync.timer` | Every 6h | ✅ Live |
| Memory maintenance | `otto-maintenance.timer` | 02:00 + 14:00 | ✅ Live |
| Weekly self-improvement | `otto-weekly-improve.timer` | Weekly | ✅ Live |
| X/Twitter scheduler | `otto-x-scheduler.timer` | Every 15m | ✅ Live |
| Service health monitor | `service-monitor.timer` | Periodic | ✅ Live |

### 1.6 Specialist Agents (21 Active)

Orchestrator, Reflection, Alpha, Researcher, Research-Synthesizer, Architect, Coder, Reviewer, Debugger, Content-Creator, Memory-Curator, Outbound-Strategist, Growth-Hacker, Social-Media-Strategist, Twitter-Engager, Landing-Page, Security-Audit, Reality-Checker, Solidity-Smart-Contract-Engineer, Blockchain-Security-Auditor, Sprint-Prioritizer.

Plus **138 catalogued** in `agency-agents/` available for auto-employment.

### 1.7 Communication Interfaces

| Interface | Stack | Status | Notes |
|---|---|---|---|
| WhatsApp primary | Baileys :3001 → Memory API | ✅ Live | Primary Mev channel (Ottolabs account) |
| WhatsApp Athena | Baileys :3002 → Athena handler | ✅ Live | Separate channel for Athena agent |
| Email (admin@otto.lk) | Zoho SMTP :465 / IMAP :993 | ✅ Live | IDLE listener; send/reply/search via API |
| OMS (mev.otto.lk) | Next.js + `/api/*` routes | ✅ Live | 52 pages; task/workflow/memory dashboard |

### 1.8 Domain Modules

| Domain | Module | Status | Notes |
|---|---|---|---|
| WebAssist | `routes/webassist.py` (398 lines) | ✅ Live at webassist.ink | CRM, leads, orders, projects |
| Koink.fun | `routes/koink.py` (575 lines) | ✅ API ready | DHM tokenomics, treasury, launch tracking |
| ONEON | `routes/oneon.py` (575 lines) | ✅ API ready | DID, credentials, governance |
| Tusita | `routes/tusita.py` | ✅ API ready | Bookings, retreats, locations |
| SOS Systems | `routes/sos.py` | ✅ API ready | Cases, learner mgmt, aid distribution |
| Crypto/Alpha | `routes/crypto.py` (530 lines) | ✅ Live | Signals, portfolio, NLP trade parsing |
| Bankr.bot | `routes/bankr.py` (642 lines) | ✅ Live | Trading via Bankr Agent API |
| Universe Registry | `universe/` YAML | ✅ Live | 15 projects + 3 personas; LLM conversational edit |

### 1.9 Database (80 Migrations, 35+ Tables)

Core tables: sessions, semantic_memories (pgvector), episodic_events, procedural_memories, tasks, task_retry_feedback, task_plans, workflow_templates, workflow_instances, workflow_gates, workflow_evolution_experiments, autoevolve_experiments, rl2f_feedback, jitrl_experiences, reasoning_entries, principles, conclusions, interrupts, agents, semantic_slices, cognitive_states, cross_brain_messages, cross_brain_graph, leads, outreach_queue, contacts, live_systems, secrets_vault, thought_vault, failure_branch_adaptations, a2a_messages, koink_*, oneon_*, tusita_*, sos_*.

---

## 2. Key Engineering Learnings

### 2.1 Memory System

**What we learned building the memory layer:**

1. **Dual-column archival is a footgun.** The DB has both `archived` (boolean) and `deleted_at` (timestamp). Different routes used different columns. This caused 31 "ghost records" — visible to some queries, invisible to others. Rule established: always filter `archived = FALSE AND deleted_at IS NULL` together.

2. **Compound decay kills memories fast.** Reflection agent was applying 0.95x manual decay on top of AutoEvolve's 0.99x per cycle. Within days, 558 memories dropped to 44 active. Fix: reflection.md now has an explicit "no manual decay" guard. Decay is maintenance-only.

3. **Memory dedup threshold matters.** At cosine threshold 0.92, too many memories collapsed — including distinct events. At 0.96, dedup is healthier. The threshold is now 0.96 in consolidation.py.

4. **Episode truncation breaks context continuity.** Episodic events were stored at 200 chars. Kernel was loading 6 messages at 200 chars. This caused "goldfish memory" — Otto forgot directives Mev gave hours earlier. Fixed: episodes at 500 chars, 20 conversation messages at 400 chars each.

5. **Conversation→directive gap.** When Mev gives a new direction via WhatsApp, the kernel processes and responds — but does not automatically extract the directive into semantic memory or working memory. This gap caused 26 stagnation flags. Short-term fix: manual extraction. Systemic fix not yet implemented.

### 2.2 Task Execution

**What we learned running 1374 tasks (1255 completed + 119 failed):**

1. **Zombie tasks are the primary failure mode.** Tasks with no PID entry (coordinator tasks, workflow step coordinators) run indefinitely in DB with no live process. Root cause: `set -euo pipefail` without a `trap EXIT` handler means unguarded command failures silently exit without marking the task failed. Rule: always include trap EXIT that POSTs failed status to completion API.

2. **Budget exhaustion before completion is the secondary failure mode.** Complex bash script tasks (qa_runner.sh, heartbeat.sh modifications) need $2+ and 30+ turns. $1/25 turns causes exhaustion mid-completion. QA rightfully rejects these. Budget calibration is still imprecise.

3. **Rate limit false positives lost 60% of heartbeat cycles.** The `grep -i "rate.limit"` pattern matched the heartbeat's own status output "Rate limit | expired" — causing cycles to be skipped even when no real limit existed. Fixed: specific patterns only (HTTP 429, RateLimitError, exact error strings).

4. **QA prompt truncation caused false rejections.** `PROMPT_EXCERPT="${PROMPT:0:800}"` in qa_runner.sh hid P3 sections from the Gemini reviewer. Gemini flagged P3 cleanup as "unauthorized scope" because it wasn't visible. Fixed: raised to 2000 chars.

5. **QA is blind to `/mnt/media/projects/`** (external repos). qa_runner.sh detects no file changes for tasks modifying external repos, auto-approves with "No file changes detected." Verification must be manual for external repo tasks.

6. **Task output field is unreliable.** Tasks can report errors while having completed the work, or report success while having failed. Always verify by checking the actual codebase (file timestamps, DB records, endpoint responses).

7. **git preflight SIGPIPE on large repos.** 1040+ dirty files caused `git status | head` to produce exit 141 (SIGPIPE) — falsely failing the git preflight check. Fixed in task_runner.sh line 403.

8. **Working directory classifier error.** When task plans are created from WhatsApp instructions, the plan classifier sometimes assigns the wrong `working_directory` to individual tasks. Fixed by procedure: always verify working_directory per plan item.

### 2.3 Heartbeat Rhythms

1. **Timers can die silently.** All timers stopped in late Feb 2026 and went unnoticed for 6 days. Fix: each heartbeat now checks sibling timers at the start of every cycle. Self-healing loop.

2. **Idle periods inflate learning metrics.** RL2F accuracy improved from 32% to 40% partly during a long idle period where all predictions were trivially correct ("queue stays empty"). True validation requires active workload. RL2F score needs an `idle_cycle` tag to separate idle predictions from real ones.

3. **Message fatigue is real.** Otto was sending Mev messages every heartbeat even when there was nothing new. Rule established: never send a message unless there's something new since the last check-in. Currently respecting >42h silence window without messaging.

### 2.4 Architectural Evolution (What Was Rearchitected)

| What Changed | From | To | Why |
|---|---|---|---|
| Task dispatch | Single-dispatch only | Plan classifier first → falls back to single-dispatch | Multi-step instructions created a single task instead of a DAG |
| Task coordination | Direct API calls | DAG task plans with dependency injection | No way to chain specialist agents on complex work |
| Multi-agent pipelines | Ad-hoc task sequences | Workflow engine with templates, gates, evolution | No reusable pipeline abstraction existed |
| Workflow-plan integration | Separate | Workflow-backed plan items advance the DAG on completion | Hybrid orchestration was impossible |
| Kernel routing | Keyword matching | Plan classifier → single-dispatch → stop classifier | Classifier missed action requests, couldn't detect workflows |
| Content generation | Inline in kernel response | content-creator agent dispatched via workflow | Otto was writing articles inline instead of using specialist agents |
| Skill registry | Manual sync | Registered in `routes/skills.py` | Skill registry was perpetually out of sync with agent files |
| WhatsApp message window | 6 msgs at 200 chars | 20 msgs at 400 chars | Goldfish memory: directives forgotten mid-conversation |
| Episodic event storage | 200 char truncation | 500 char storage | Context loss for longer event descriptions |

### 2.5 What Worked Well (No Changes Needed)

1. **FastAPI + asyncpg on :8100** — Single entrypoint, zero restarts in weeks, extensible via route files. This architecture scales cleanly.

2. **Dual heartbeat rhythm (orchestrator :00 + reflection :30)** — Separating mission execution from self-improvement prevents reflection from stealing execution budget. Clean separation of concerns.

3. **Detached Claude Code CLI sessions for tasks** — Fully isolated, killable, budget-capped. Spawning sub-agents as separate processes (not API calls) avoids context pollution.

4. **Systemd for everything** — All persistent services and timers are systemd units. Survives reboots, logs to journald, easy monitoring.

5. **pgvector + Neo4j layered approach** — Fast vector search in Postgres for semantic memories; temporal knowledge graph in Neo4j for relationships. Each does what it's best at.

6. **RL2F Layer 2 (QA rejection chain)** — Structured feedback from QA failures flowing back into retry context significantly improved task completion rates for repeated patterns.

7. **MARS adversarial reflection** — Adversarial critic catches assumptions that self-critique misses. Multiple times it caught inflated metrics or unverified claims that would have propagated as bad data.

8. **AutoEvolve experiment loop** — Gen 3 active. State Delta patch improved RL2F 28%→40% (+12pp). The keep/discard discipline prevents degradation accumulating.

9. **Per-agent MEMORY.md persistence** — Specialist agents accumulate domain knowledge across sessions. The researcher, coder, reviewer, and reflection agents are meaningfully more effective with their memory files.

10. **Universe Registry + natural language edit** — Treating ecosystem projects as a YAML registry with LLM conversational edit proved more maintainable than hardcoded config.

---

## 3. Failure Modes Observed in Logs

### 3.1 Task Failure Taxonomy (from 119 failed tasks)

| Failure Mode | Frequency | Root Cause | Status |
|---|---|---|---|
| **Zombie task** (no PID, coordinator killed after timeout) | High | Missing `trap EXIT` in task_runner.sh for coordinator-type tasks | Mitigated — heartbeat kills zombies; root cause partially fixed |
| **Rate limit exhaustion** (`You've hit your limit`) | High | Claude API daily limit hit during heavy burst periods | Mitigated — rate limit detection + holding posture |
| **Process died** (`set -e triggered`) | Medium | Unguarded command failures in complex bash tasks | Partially fixed — `set -euo pipefail` + trap EXIT added |
| **Budget exhaustion** (no output, short run time) | Medium | $1 budget too low for complex multi-file tasks | Ongoing — budget calibration is imprecise |
| **Workflow step false failure** (step marked failed despite task exit 0) | Low | Workflow coordinator zombie; step output not captured before kill | Procedure documented: retry via `/workflows/instances/{id}/approve` |
| **QA false rejection** (truncated prompt) | Fixed | Prompt excerpt limited to 800 chars, hiding task scope | Fixed: raised to 2000 chars |
| **SIGPIPE in git preflight** | Fixed | `git status | head` produces exit 141 on large repos | Fixed: line 403 task_runner.sh |

### 3.2 Memory Failure Modes

| Failure Mode | Frequency | Root Cause | Status |
|---|---|---|---|
| **Mass-archival** (558→44 memories in hours) | Occurred twice | Compound decay: manual 0.95x on top of automatic 0.99x | Fixed: reflection.md "no manual decay" guard |
| **Ghost records** (visible to some queries, not others) | Occurred once | archived/deleted_at desync during mass-restoration | Fixed: always use both columns in WHERE clause |
| **Empty TraceMem narratives** | Persistent | LLM returns empty for certain episode groupings | Low priority, ongoing (33 archived empty narratives) |
| **Wink monitor false positives** | Persistent (ongoing) | 90s stall threshold triggers on I/O-heavy tasks that are fine | Mitigated: threshold tunable; noise accepted |
| **Goldfish memory** | Fixed | Episodic truncation + short conversation window | Fixed: kernel/ric.py + kernel/smmu.py |

### 3.3 Infrastructure Failure Modes

| Failure Mode | Frequency | Root Cause | Status |
|---|---|---|---|
| **Timer outage** (6 days unnoticed) | Occurred once | No self-healing for timer failures | Fixed: heartbeat checks sibling timers |
| **Rate limit false positive** (60% cycles skipped) | Occurred, weeks long | grep -i "rate.limit" matched own status output | Fixed: specific error patterns only |
| **CDP wallet_secret format error** | Occurred once | Ed25519 bytes used instead of DER PKCS8 EC P-256 | Fixed: documented in auto-memory |
| **ip-api.com HTTPS 403** | Occurred once | Free tier blocks HTTPS | Fixed: switched to api.country.is |

---

## 4. What Worked vs. What Was Rearchitected

### Worked First Time, Never Changed

- FastAPI route structure (`routes/` per domain)
- PostgreSQL + pgvector for semantic memories
- Docker Compose for memory infrastructure (postgres, neo4j, graphiti)
- Systemd service + timer pattern
- Baileys-based WhatsApp bridge
- Session hook pattern (start/stop via scripts)
- `task_runner.sh` core spawn loop (budget + CLI)
- Dual heartbeat rhythm concept (execution vs reflection)
- MARS adversarial reflection architecture
- HyMem dual-granularity retrieval design
- A-RAG 3-strategy retrieval

### Rearchitected Once (Got It Right Second Time)

- **Task dispatch** → added plan classifier layer on top
- **Workflow engine** → created from scratch after task sequences proved unscalable
- **Content generation** → moved from inline kernel response to specialist agent dispatch
- **Skill registry** → made explicit in skills.py after repeated sync bugs
- **Episodic truncation** → fixed after goldfish memory incident
- **Rate limit detection** → narrowed grep pattern after false positive incident
- **QA prompt excerpt** → raised from 800 to 2000 chars after false rejection

### Still Being Refined (Ongoing)

- RL2F accuracy (40%, target: 70%+ on active workload)
- AutoEvolve (Gen 3, validation needs active workload)
- Task budget calibration (imprecise, trial-and-error per task type)
- Wink stall detection threshold (noise vs utility tradeoff)
- Workflow coordinator zombie prevention
- Directive auto-extraction from WhatsApp conversations

---

## 5. Prioritised Improvement Backlog

### Short-Term (Next 1–4 Cycles, High Confidence × High Impact)

| # | Item | Impact | Effort | Source |
|---|---|---|---|---|
| S1 | **A2A Protocol** — Add Agent Card endpoint + A2A handshake to task_plans.py and gateway. Enables plan tasks to communicate directly instead of DB polling. Aligns with Google ADK, STEM arXiv 2603.22359 | Very High | Medium | Synthesis task |
| S2 | **STEM Caller Profiler** — Implement 5–8 dimension tracker for Mev preferences (tone, depth, domain, urgency). Full gap in current STEM implementation | High | Medium | Known gaps, STEM gap analysis |
| S3 | **RL2F idle_cycle tagging** — Tag predictions made during idle periods separately. Current 40% accuracy partially inflated by trivial idle-period predictions | Medium | Low | Reflection + MARS |
| S4 | **Directive auto-extraction** — After kernel responds to Mev message, run lightweight classifier to detect new directives; auto-store to semantic memory + working memory | High | Low | Goldfish memory incident |
| S5 | **HiClaw GAP-3** — Heartbeat sometimes creates tasks directly for multi-step work, bypassing plan system. Add plan-classifier check to heartbeat.md at task creation step | Medium | Low | HiClaw gap analysis |

### Medium-Term (1–3 Weeks, Validated Architecture Needed)

| # | Item | Impact | Effort | Source |
|---|---|---|---|---|
| M1 | **MCP Server Layer** — Wrap `/semantic`, `/tasks`, `/workflows` routes as MCP resources in `memory/mcp_server.py`. Positions Otto as infrastructure others build on; enables all MCP-compatible agents to access Otto's memory | Very High | High | Synthesis task; all Tier-1 frameworks ship MCP in 2026 |
| M2 | **DGM-H Reflection Unfreeze** — reflection.md proposes its own diff to a staging path; heartbeat applies if RL2F score improves. Removes hard ceiling on self-improvement speed (ref: github.com/facebookresearch/HyperAgents, CC BY 4.0) | Very High | Medium | Synthesis task; HyperAgents arXiv 2603.19461 |
| M3 | **S-MMU near-miss threshold** — Apply similarity_threshold=0.7 to L2 slice injection. Currently all slices above any threshold are injected. Near-miss filtering would reduce context noise | Medium | Low | Known gaps (P5 deferred) |
| M4 | **VISTA structured failure categorization** — Categorize task failures into typed buckets (budget, zombie, rate-limit, QA, etc.); inject category + correction hypothesis into retry prompt | High | Medium | Known gaps |
| M5 | **S-MMU injection ordering** — Relevant slices must be placed at context START, not middle. Current implementation may inject slices mid-context causing position bias degradation (arXiv context-rot research) | Medium | Medium | Context Rot memory |
| M6 | **OTel observability** — Add OpenTelemetry trace/span pipeline to task execution and workflow engine. Required for debugging multi-agent workflows at scale; currently log-file only | Medium | High | Synthesis task; industry standard |

### Long-Term (Strategic, 1–3 Months)

| # | Item | Impact | Effort | Source |
|---|---|---|---|---|
| L1 | **AOP Governance Layer** — Agent Operations Platform pattern: policy enforcement, audit trails per agent role, role-based capability restriction. Mirrors CrewAI AOP architecture | High | Very High | Synthesis task |
| L2 | **Multi-LLM expansion** — Extend provider.py beyond Claude-primary. Add Bedrock, Ollama, Gemini via openai_compatible adapter. Reduces cost + single-provider risk | Medium | Medium | Synthesis task; resilience |
| L3 | **Deriver Pattern (Honcho)** — Async background processor that builds Mev-specific representations from interaction history. Store→Reason→Retrieve flow; Working Representation per entity (not global context inject) | High | High | Honcho evaluation memory |
| L4 | **TrustGraph Context Cores** — Package domain knowledge (WebAssist, SOS, Koink protocols) into versioned portable bundles importable by any heartbeat/task agent. Solves context drift | Medium | Medium | TrustGraph memory |
| L5 | **RLM Recursive Document Processing** — Give Otto doc metadata + access functions; let it recursively query slices it needs. Eliminates upfront full-doc ingestion for large docs | Medium | Medium | RLM arXiv 2512.24601 memory |
| L6 | **STEM Dynamic Tool Composition** — Runtime tool composition from modular primitives. Currently tools are static per agent | Medium | Very High | STEM gap analysis |
| L7 | **STEM MCP Externalization** — Expose Otto's agent capabilities as MCP tools accessible from external clients | High | High | STEM gap analysis |
| L8 | **AgentOS Multi-tenant** — Extend kernel to serve multiple users (not just Mev). Required for WebAssist agents and any multi-user product | Very High | Very High | Pre-launch architecture; future revenue |

---

## 6. vs. State-of-the-Art Harnesses (2026 Competitive Context)

*Source: Research synthesis task (Step 1, 2026-03-28), 44 data points across 6 source types.*

### Otto's Defensible Advantages

| Advantage | Detail | What External Frameworks Have |
|---|---|---|
| Memory stack depth | HyMem + S-MMU + pgvector + Neo4j + A-RAG simultaneously | None (LangGraph, CrewAI, AutoGen, OpenAI SDK, Google ADK have none of this together) |
| RL2F feedback learning | 2-layer: heartbeat critiques + QA rejection chains | Absent from all surveyed frameworks |
| MARS adversarial reflection | Dual critic per reflection cycle; catches inflated conclusions | Absent from all surveyed frameworks |
| DAG task orchestration | Dependency injection, topology detection, agent auto-employment | LangGraph closest (graph-based); no auto-employment |
| Self-improvement experiment loop | AutoEvolve Gen 3; keep/discard discipline | Not in any external framework |
| Dual heartbeat rhythm | Execution vs self-improvement cleanly separated | Not a standard pattern |

### Otto's Confirmed Gaps

| Gap | Severity | What Has It |
|---|---|---|
| **A2A protocol** (code-confirmed absent) | Critical | Google ADK native; STEM identifies as #1 gap |
| **MCP support** (code-confirmed absent) | Critical | LangGraph (partial), ADK, Strands, Mastra all native in 2026 |
| **Self-rewriting reflection** (reflection.md is static file) | High | DGM-H (HyperAgents arXiv 2603.19461) shows 20pp improvement |
| **OpenTelemetry** (logs only) | Medium | All Tier-1 frameworks ship native OTel in 2026 |
| **Multi-LLM breadth** (3 provider types, Claude-primary) | Low | OpenAI SDK: 100+ LLMs; ADK model-agnostic |

---

*This document is a merge target for the main Otto architecture document. Sections are self-contained.*
*Task: Document Otto features, learnings, and improvement roadmap | Agent: memory-curator | 2026-03-28*

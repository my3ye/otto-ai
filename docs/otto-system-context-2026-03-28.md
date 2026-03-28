# Otto System Context: Architecture, Benchmarks & Current State

**Generated:** 2026-03-28
**Purpose:** Structured baseline for roadmap planning and competitive positioning
**Source:** Live DB queries + codebase analysis + memory synthesis + existing arch docs

---

## 1. System Overview

Otto is a persistent, autonomous AI operating system built on AgentOS (arXiv 2602.20934v1). It runs on a GCP VM (4 vCPU, 16GB RAM, Debian 12) and operates as both Mev's digital COO and the operational intelligence layer for the MY3YE ecosystem (15+ projects).

**Core design axioms:**
- Interrupt-driven (not poll-driven) — everything enters as a typed interrupt through a single kernel
- Memory as first-class infrastructure — explicit L1/L2/L3 hierarchy, maintenance cycles, decay
- Composable over monolithic — 80+ focused route modules, Markdown agent prompts, template-based workflows
- Research-informed, not research-driven — 24+ papers implemented as practical systems

---

## 2. Infrastructure State (Live, 2026-03-28)

### 2.1 Compute
| Resource | Total | Used | Available | Notes |
|---|---|---|---|---|
| Boot disk (`/`) | 68GB | 28GB (43%) | 38GB | Healthy |
| Media disk (`/mnt/media`) | 97GB | 12GB (13%) | 81GB | Healthy |
| RAM | 16GB | 5.1GB used | ~10GB available | No swap |
| CPU | 4 vCPU | — | — | Debian 12 |

### 2.2 Services & Uptime
| Service | Status | Uptime | Notes |
|---|---|---|---|
| Memory API (FastAPI :8100) | ✅ Healthy | — | Primary API; systemd: otto-memory |
| PostgreSQL 17 + pgvector | ✅ Healthy | 4 weeks | Docker: memory-postgres-1 |
| Neo4j 5.26.2 | ✅ Healthy | 4 weeks | Docker: memory-neo4j-1 |
| Graphiti (Temporal KG) | ✅ Healthy | 7 days | Docker: memory-graphiti-1 |
| WhatsApp (Baileys :3001) | ✅ Live | — | Primary Mev channel |
| OMS (mev.otto.lk) | ✅ Live | — | Next.js on Vercel |
| WebAssist (webassist.ink) | ✅ Live | — | P1 product; payment-blocked |

### 2.3 Timer Health (All 11 Running)
| Timer | Schedule | Last Run | Status |
|---|---|---|---|
| otto-heartbeat | Hourly :00 | 34min ago | ✅ Active |
| otto-reflection | Hourly :30 | 4min ago | ✅ Active |
| otto-alpha-watcher | Every 5m | 3min ago | ✅ Active |
| otto-signals | Every 15m | 4min ago | ✅ Active |
| otto-x-scheduler | Every 15m | 14min ago | ✅ Active |
| otto-alpha-heartbeat | Every 2h | 1h 33min ago | ✅ Active |
| otto-research-pipeline | Every 3h | 2h 33min ago | ✅ Active |
| otto-vuln-sync | Every 6h | 4h 39min ago | ✅ Active |
| otto-maintenance | 02:00 + 14:00 | 3h 33min ago | ✅ Active |
| otto-security-audit | Every 3 days | 9h ago | ✅ Active |
| otto-weekly-improve | Weekly | 6 days ago | ✅ Active |

**Self-healing:** Each heartbeat checks sibling timers. No silent outage risk since Feb 2026 fix.

---

## 3. Task Execution Metrics

### 3.1 All-Time Totals
| Metric | Value |
|---|---|
| Total completed | 1,259 |
| Total failed | 119 |
| Total cancelled | 14 |
| Failure rate (all-time) | ~8.6% |

### 3.2 Last 7 Days
| Status | Count |
|---|---|
| Completed | 606 |
| Failed | 71 |
| Cancelled | 9 |
| Pending | 8 |
| Running | 2 |

**7-day failure rate:** 71/606 = **11.7%** (elevated vs all-time; includes idle-period burst activity)

### 3.3 QA Stats (Last 7 Days, Completed Tasks)
| QA Status | Count | % |
|---|---|---|
| Approved | 503 | 83% |
| Rejected | 1 | 0.2% |
| No QA (null) | 56 | 9% |

**QA approval rate: 83%.** The 9% null QA are tasks that completed without triggering Gemini review (e.g., external repo tasks, coordinator tasks).

### 3.4 Max Concurrent Limits
| CLI | Limit | Currently Running |
|---|---|---|
| claude | 3 | 2 |
| gemini | 1 | 0 |
| kimi | 1 | 0 |

---

## 4. Learning & Self-Improvement Benchmarks

### 4.1 RL2F (Reinforcement Learning from Feedback)
| Metric | Value | Notes |
|---|---|---|
| Accuracy (50-cycle window) | **40%** | Matched predictions; stable trend |
| Partial match rate | 58% | Close but not exact |
| Miss rate | 2% | Hard failures |
| Prior accuracy | 38% | Trend: slight upward |
| Target | 70%+ | Requires active workload validation |

**Caveat:** Current 40% includes idle periods where all predictions are trivially correct. True active-workload accuracy needs `idle_cycle` tagging to separate. Gen 3 State Delta patch improved from 28% baseline.

### 4.2 Reasoning Chain (Last 7 Days)
| Outcome | Count | % |
|---|---|---|
| Matched | 21 | 28% |
| Partial | 38 | 50% |
| Pending | 15 | 20% |
| Miss | 2 | 3% |

**7-day match rate: 28% full + 50% partial = 78% "not a miss"**

### 4.3 AutoEvolve Experiment History
| Gen | Experiment | Outcome | Metric Delta |
|---|---|---|---|
| Gen 1 | Procedure trust threshold 0.55→0.40 | KEEP | +6pp (56%→62%) |
| Gen 1 | Test placeholder | DISCARD | — |
| Gen 2 | RL2F table bug fix (wrong table read) | KEEP | Prerequisite fix; metric: 0.30→0.22 (correct) |
| Gen 3 | State Delta patch in heartbeat.md | KEEP | +12pp (28%→40%) |

**Current generation: 3.** Next experiment deferred pending active workload.

### 4.4 Workflow Template Fitness
| Template | Fitness Score | Notes |
|---|---|---|
| content-publishing-pipeline | 0.83 | Best performer |
| feature-development | 0.82 | — |
| social-content-pipeline | 0.80 | — |
| research-pipeline | 0.78 | — |
| product-sprint-pipeline | None (new) | Insufficient runs |
| grant-application-pipeline | None (new) | Insufficient runs |

**Workflow instance summary:** 113 total instances, 103 completed (91%), 1 failed.

### 4.5 Procedural Memory
| Metric | Value |
|---|---|
| Total procedures | 16 |
| Top trust score | 0.9996 (debug_memory_api) |
| Trust range | 0.35–1.00 |
| Average confidence (principles) | 0.84 |
| Total principles | 36 |

### 4.6 Memory System
| Metric | Value |
|---|---|
| Semantic memories (active) | ~3,788 |
| Semantic memories (total incl. archived) | 3,829 |
| Episodic events | 5,181 |
| Avg relevance score | 0.42 |

---

## 5. WebAssist Product Benchmarks

**Status:** Live at webassist.ink. Payment blocked on Stripe keys (Mev-owned).

### Lighthouse Audit (2026-03-09, Homepage)
| Metric | Score/Value | Target | Status |
|---|---|---|---|
| Performance | 72/100 | 90+ | ⚠️ Needs work |
| Accessibility | 54/100 | 90+ | ❌ Critical |
| SEO | 82/100 | 90+ | ⚠️ Good |
| Best Practices | 96/100 | 90+ | ✅ Good |
| LCP | 4.85s | <2.5s | ❌ Critical |
| CLS | 0.000 | <0.1 | ✅ Excellent |
| FCP | 1.05s | <1.8s | ✅ Good |
| TBT | 400ms | <200ms | ⚠️ Moderate |

**Root cause of LCP (fixed):** Hero h1 had `opacity: 0` → browser waited for JS hydration. Fix applied (dynamic import, removed Framer Motion above-fold). Latest scores not yet re-audited.

---

## 6. Architecture Subsystem Inventory

### 6.1 AgentOS Kernel (15 modules, 3,900+ lines)
| Module | Lines | Function |
|---|---|---|
| `ric.py` | 1,063 | Core processing: IVT→S-MMU→LLM→8 hooks |
| `smmu.py` | 524 | L1/L2/L3 memory paging; HyMem/A-RAG retrieval |
| `provider.py` | 597 | Multi-LLM backends (Claude, Gemini, Kimi) |
| `sync.py` | 311 | Cognitive Sync Pulses on drift |
| `ivt.py` | 300 | Priority interrupt queue (PostgreSQL-backed) |
| `slicing.py` | 295 | CID-based semantic segmentation |
| `drift.py` | 164 | Δψ drift detection every 5 interrupts |
| Others | ~550 | perception, scheduler, agents, state, types, masking, hooks |

**Interrupt priority order:** admin_message(10) > sync_drift(8) > perception_error(9) > task_event(7) > heartbeat(5) > maintenance(3)

### 6.2 Memory Layer (Multi-Tier)
| Layer | Technology | Purpose | L1 Capacity |
|---|---|---|---|
| L1 (always-resident) | In-process | Identity, priorities, directives | 12,000 tokens |
| L2 (dynamic) | pgvector semantic search | Task-relevant slices injected per interrupt | Variable |
| L3 (cold) | Full PostgreSQL + Neo4j | All memories, graph nodes | Unlimited |
| Knowledge Graph | Neo4j + Graphiti | Temporal entity extraction, relationships | Unlimited |

**Retrieval strategy (A-RAG):** Semantic (pgvector cosine) + keyword (pg_trgm) + graph (Graphiti) → merged + BMAM re-ranked (similarity + recency + importance + goal-alignment).

### 6.3 Task Execution Engine
| Layer | Component | Capability |
|---|---|---|
| Single tasks | task_runner.sh + tasks.py | Claude/Gemini/Kimi CLI; budget-capped; trap EXIT; QA |
| DAG plans | task_plans.py (836 lines) | Dependency edges; auto-employment; output injection |
| Workflows | workflows.py (2,242 lines) | Template chains; gates; fitness scoring; evolution |
| Dispatcher | otto-task-dispatcher.service | Polls queue; auto-launches ready tasks |

### 6.4 Specialist Agents (21 Active + 138 Available)
**Active:** Orchestrator, Reflection, Alpha, Researcher, Research-Synthesizer, Architect, Coder, Reviewer, Debugger, Content-Creator, Memory-Curator, Outbound-Strategist, Growth-Hacker, Social-Media-Strategist, Twitter-Engager, Landing-Page, Security-Audit, Reality-Checker, Solidity-Smart-Contract-Engineer, Blockchain-Security-Auditor, Sprint-Prioritizer

**Pooled (auto-employment):** 138 agents in `agency-agents/`

### 6.5 Database (86 Migrations, 35+ Tables)
Key tables: `tasks`, `task_plans`, `workflow_templates`, `workflow_instances`, `workflow_gates`, `semantic_memories`, `episodic_events`, `procedural_memories`, `reasoning_chain`, `rl2f_feedback`, `jitrl_experiences`, `autoevolve_experiments`, `autoevolve_generation`, `principles`, `a2a_messages`, `thought_vault`, `failure_branch_adaptations`, `interrupts`, `cognitive_states`, `semantic_slices` + domain tables (koink_*, oneon_*, tusita_*, sos_*)

---

## 7. Known Gaps & Weaknesses

### 7.1 Critical Gaps (Code-Confirmed Absent)

| Gap | Severity | Impact | What Has It |
|---|---|---|---|
| **A2A Protocol** — agents can't communicate mid-execution; DB polling only | Critical | Multi-agent coordination limited | Google ADK native; STEM P1 |
| **MCP Server Layer** — no external tool discovery or composition | Critical | External tools can't plug in | LangGraph, ADK, Strands, Mastra all ship native MCP 2026 |
| **Caller Profiler (Mev)** — zero structured user behavioral profiling | High | Clarification loops; imprecise task scoping | STEM P3; Honcho Deriver |
| **Self-rewriting reflection** — reflection.md is a static file | High | Hard ceiling on self-improvement speed | HyperAgents arXiv 2603.19461 (DGM-H) |

### 7.2 Partial Gaps (Implemented but Incomplete)

| Gap | Current State | Missing Piece |
|---|---|---|
| **RL2F idle tagging** | 40% accuracy (partially inflated by idle periods) | `idle_cycle` boolean flag; separate active vs idle metric |
| **Directive auto-extraction** | Manual extraction; kernel responds but doesn't auto-store | Lightweight post-hook classifier in ric.py |
| **S-MMU injection ordering** | Unknown if context-start placement is enforced | Position bias fix: relevant slices must inject at START |
| **S-MMU near-miss filtering** | All slices above threshold injected | `similarity_threshold=0.70` filter for near-miss slices |
| **HiClaw GAP-3** | Heartbeat sometimes bypasses plan system | Plan-classifier check in heartbeat.md at task creation step |
| **VISTA failure categorization** | Smart retry exists but failure types are unstructured | Categorize into typed buckets; inject category into retry prompt |
| **OTel observability** | Log-file only (journald) | OpenTelemetry trace/span pipeline for workflows |

### 7.3 Operational Debt (Accepted but Not Fixed)

| Debt Item | Frequency | Priority |
|---|---|---|
| Wink false positives (90s threshold too sensitive for I/O-heavy tasks) | Persistent (~16 alerts/day) | Low — noise accepted |
| Empty TraceMem narratives (LLM returns empty on certain episode groups) | Persistent (33 archived) | Low |
| QA blind to `/mnt/media/projects/` (auto-approves external repo tasks) | Persistent | Medium |
| Budget calibration imprecise (trial-and-error per task type) | Persistent | Medium |
| Directive-to-memory gap (WhatsApp directives not auto-extracted) | Persistent | High |

---

## 8. Performance Baselines (Measurable KPIs)

| KPI | Current | Target | Status |
|---|---|---|---|
| RL2F accuracy (50-cycle window) | 40% | 70% (active workload) | 🟡 Improving |
| Task failure rate (7-day) | 11.7% | <5% | 🔴 Elevated |
| Task failure rate (all-time) | 8.6% | <5% | 🟡 Above target |
| QA approval rate (7-day) | 83% | 95%+ | 🟡 Acceptable |
| Workflow completion rate | 91% (103/113) | 95%+ | 🟡 Acceptable |
| WebAssist LCP | 4.85s | <2.5s | 🔴 Critical (fix applied) |
| WebAssist Accessibility | 54/100 | 90+ | 🔴 Critical |
| Timer self-healing | 100% (all 11 healthy) | 100% | ✅ Green |
| Memory API uptime | 100% (DB healthy) | 99.9% | ✅ Green |
| AutoEvolve Gen | 3 | — | ✅ Active |
| Active principles confidence | 0.84 avg | 0.80+ | ✅ Green |
| Reasoning match rate (7d) | 28% full, 78% non-miss | 50%+ full | 🟡 Improving |

---

## 9. Competitive Position (vs. 2026 AI Harnesses)

### Otto's Defensible Moat
1. **Memory stack depth** — HyMem + S-MMU + pgvector + Neo4j + A-RAG simultaneously. No external framework (LangGraph, CrewAI, AutoGen, OpenAI SDK, Google ADK) has this combination.
2. **RL2F 2-layer learning** — Heartbeat critiques + QA rejection chains. Absent from all surveyed frameworks.
3. **MARS adversarial reflection** — Dual critic per reflection cycle. Absent from all surveyed frameworks.
4. **DAG task orchestration with auto-employment** — LangGraph is closest (graph-based) but lacks auto-employment and dependency injection.
5. **Self-improvement experiment loop (AutoEvolve)** — Gen 3, with keep/discard discipline. Not in any external framework.
6. **Dual heartbeat rhythm** — Execution vs self-improvement cleanly separated. Not a standard pattern.
7. **Interrupt-driven unified cognitive path** — All inputs (WhatsApp, web, scheduled) through one cognitive processing pipeline.

### Critical Gaps vs. External Frameworks
1. **A2A protocol** — Google ADK ships this natively. Otto agents can't coordinate mid-execution.
2. **MCP support** — Industry standard in 2026 (LangGraph partial, ADK, Strands, Mastra all native). Otto has no MCP server.
3. **Self-rewriting agents** — DGM-H pattern (HyperAgents, arXiv 2603.19461) shows 20pp improvement when reflection can propose its own diff.
4. **OpenTelemetry** — All Tier-1 frameworks ship native OTel for multi-agent debugging. Otto is logs-only.
5. **Multi-LLM breadth** — OpenAI SDK supports 100+ LLMs; ADK is model-agnostic. Otto is Claude-primary with 3 provider types.

---

## 10. Priority Improvement Actions (Ranked by Impact × Effort)

| Priority | Item | Impact | Effort | Source |
|---|---|---|---|---|
| **P1** | RL2F idle_cycle tagging | Medium | Low (~$1) | MARS reflection |
| **P2** | Directive auto-extraction (ric.py post-hook) | High | Low (~$2) | Recurring gap |
| **P3** | Caller Profiler for Mev (5-8 dimensions) | High | Medium (~$5) | STEM gap analysis |
| **P4** | HiClaw GAP-3 (heartbeat plan bypass fix) | Medium | Low (~$1) | HiClaw gap analysis |
| **P5** | S-MMU near-miss threshold (0.70 filter) | Medium | Low (~$1) | Constraint injection research |
| **P6** | VISTA failure categorization (retry typed buckets) | High | Medium (~$4) | Known gaps |
| **P7** | S-MMU injection ordering fix (context START) | Medium | Medium (~$3) | Context rot research |
| **P8** | A2A Protocol (Agent Card + handshake) | Very High | Medium (~$6) | STEM, ADK comparison |
| **P9** | DGM-H Reflection Unfreeze (reflection self-diff) | Very High | Medium (~$5) | HyperAgents arXiv 2603.19461 |
| **P10** | MCP Server Layer (wrap routes as resources) | Very High | High (~$10) | Industry standard 2026 |

---

## 11. Key Reference Documents

| Document | Path | Date |
|---|---|---|
| System Architecture (full) | `~/otto/docs/otto-system-architecture-2026-03-28.md` | 2026-03-28 |
| Features, Learnings & Roadmap | `~/otto/docs/otto-features-learnings-roadmap-2026-03-28.md` | 2026-03-28 |
| System Manifest (JSON) | `~/otto/docs/otto-system-manifest-2026-03-28.json` | 2026-03-28 |
| STEM Gap Analysis | `~/otto/docs/stem-agent-gap-analysis-2026-03-28.md` | 2026-03-28 |
| HiClaw Gap Analysis | `~/otto/docs/hiclaw-otto-gap-analysis-2026-03-24.md` | 2026-03-24 |
| HiClaw Sprint Backlog | `~/otto/docs/hiclaw-sprint-backlog-2026-03-24.md` | 2026-03-24 |
| HiClaw Artifact Architecture | `~/otto/docs/hiclaw-artifact-path-architecture-2026-03-24.md` | 2026-03-24 |
| Pre-launch Architecture | `~/otto/docs/prelaunch-architecture-2026-03-19.md` | 2026-03-19 |

---

*Generated by researcher agent | Task: Gather system architecture, benchmarks, and current state context | 2026-03-28*

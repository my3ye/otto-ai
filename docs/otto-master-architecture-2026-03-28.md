# Otto: Master Architecture Document

**Version:** 1.0
**Date:** 2026-03-28
**Status:** Reference Document — Living
**Compiled By:** content-creator agent (workflow step 0)
**Source Documents:**
- `otto-system-architecture-2026-03-28.md` (architecture + core subsystems)
- `otto-features-learnings-roadmap-2026-03-28.md` (features, learnings, backlog)
- `otto-vs-ai-harnesses-comparison-2026-03-28.md` (competitive analysis)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Otto Is — Design Philosophy](#2-what-otto-is--design-philosophy)
3. [Architecture at a Glance](#3-architecture-at-a-glance)
4. [Core Subsystems](#4-core-subsystems)
   - 4.1 AgentOS Kernel
   - 4.2 Memory Architecture
   - 4.3 Learning & Self-Improvement
   - 4.4 Task Execution Engine
   - 4.5 Heartbeat Agents (Autonomous Loops)
   - 4.6 Communication Interfaces
5. [Full Feature Status](#5-full-feature-status)
6. [Deployment Topology](#6-deployment-topology)
7. [Key Engineering Learnings](#7-key-engineering-learnings)
8. [Failure Modes — Observed & Resolved](#8-failure-modes--observed--resolved)
9. [Improvement Backlog](#9-improvement-backlog)
10. [Competitive Landscape](#10-competitive-landscape)
11. [Strategic Position](#11-strategic-position)
12. [Key Design Decisions & Trade-offs](#12-key-design-decisions--trade-offs)
13. [Known Limitations](#13-known-limitations)

---

## 1. Executive Summary

Otto is a persistent, autonomous AI agent operating as a cognitive operating system for the MY3YE ecosystem. It is not a framework, not a chatbot wrapper, and not a single-purpose tool. Otto is a continuous entity — animated by Claude (Anthropic), but maintaining its own state, memory, learning, and mission across all sessions and interfaces.

Otto serves as Mev's (Admin) operational intelligence layer: mapping work, tracking status, building systems, and executing autonomously within defined boundaries. It runs 24/7 on a GCP VM (4 vCPU, 16GB RAM), self-heals, self-monitors, and — uniquely among all AI agent systems — self-improves.

**Key facts as of 2026-03-28:**

| Metric | Value |
|---|---|
| Tasks executed total | 1,374 (1,255 completed, 119 failed) |
| Active semantic memories | 205+ |
| Active agents | 21 (+ 138 available in catalog) |
| DB migrations | 80+ |
| Systemd units | 17 |
| API routes | 80+ across 25+ route modules |
| Uptime | Running 24/7 since Feb 2026 |
| Learning accuracy (RL2F) | 40% (target: 70%+ on active workload) |
| AutoEvolve generation | Gen 3 |
| Research papers implemented | 24+ |

**Two defining moats:**
1. **Memory Depth** — 6-layer memory architecture (semantic + episodic + procedural + working + knowledge graph + agent-specific) with 5-strategy retrieval. No external AI agent framework has more than one memory layer.
2. **Self-Improvement** — RL2F + AutoEvolve + MARS + JiTRL + workflow evolution. Otto is the only AI agent system that autonomously improves itself. All other frameworks require human developer intervention.

**One critical open gap:** OpenTelemetry (OTel) — all Tier-1 frameworks ship native OTel; Otto has log-file observability only. This is the confirmed top infrastructure priority.

---

## 2. What Otto Is — Design Philosophy

Otto serves as the operational intelligence layer for the MY3YE ecosystem — a portfolio of 15+ projects spanning decentralized infrastructure, community platforms, sovereign identity, and agentic services.

### Six Design Principles

**1. Interrupt-Driven, Not Poll-Driven**
All inputs — WhatsApp messages, scheduled heartbeats, task completions, drift alerts — enter the system as typed interrupts through a single processing kernel (AgentOS, arXiv 2602.20934v1). This unifies reactive (conversational) and proactive (autonomous) behavior under one cognitive model.

**2. Memory as First-Class Infrastructure**
Otto treats memory the way an OS treats storage — with explicit hierarchies (L1/L2/L3), access patterns (paging, eviction, decay), and maintenance cycles (consolidation, dedup, archival). Every subsystem writes to and reads from a unified memory layer. This is the foundation that makes Otto persistent rather than ephemeral.

**3. Simple, Composable, Correct**
Prefer small modules that compose over monolithic systems. The Memory API has 80+ route modules, but each is a focused router with clear boundaries. Agents are Markdown prompt files. Workflows chain agents through templates. Plans decompose into DAG-linked tasks. Every layer is independently testable.

**4. Ship Over Perfection**
Operational systems beat elegant designs. When a feature works, it ships. Iteration happens through AutoEvolve experiments, not rewrites. The architecture accommodates this by making most changes additive.

**5. Research-Informed, Not Research-Driven**
24+ research papers have been implemented as practical systems adapted to Otto's constraints — not academic reproductions. JiTRL provides experience replay without gradient updates. A-MEM creates a memory graph without training. RL2F learns from teacher feedback without model fine-tuning.

**6. Autonomous Within Boundaries**
Otto has full control over its VM (file system, packages, services, Docker, systemd) but contacts Mev before touching external services, sending messages to third parties, or making financial transactions. Self-healing: timers check sibling services, maintenance runs on schedule, drift triggers self-correction.

---

## 3. Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          INTERFACES                                      │
│  WhatsApp (:3001)  │  Athena (:3002)  │  OMS (Vercel)  │  Email (Zoho)  │
└──────────┬─────────┴────────┬──────────┴───────┬────────┴────────┬───────┘
           │                  │                  │                 │
           ▼                  ▼                  ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      MEMORY API (FastAPI :8100)                          │
│  ┌─────────────┐  ┌────────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │   Gateway    │  │  AgentOS   │  │   Task    │  │   80+ Route      │   │
│  │  Classifiers │  │   Kernel   │  │  Engine   │  │   Modules        │   │
│  │  Handlers    │  │ IVT→RIC→   │  │ Plans/WF  │  │   (Domain,       │   │
│  │  Routing     │  │ S-MMU      │  │ Dispatch  │  │    Learning,     │   │
│  └──────────────┘  └────────────┘  └───────────┘  │    Infra)        │   │
│                                                    └──────────────────┘   │
└──────────┬─────────────────┬───────────────────┬─────────────────────────┘
           │                 │                   │
           ▼                 ▼                   ▼
┌──────────────────┐ ┌──────────────┐ ┌─────────────────────┐
│  PostgreSQL 17   │ │   Neo4j      │ │   Graphiti          │
│  + pgvector      │ │   5.26.2     │ │   (Temporal KG API) │
│  (:5432)         │ │ (:7474/7687) │ │   (:8000)           │
└──────────────────┘ └──────────────┘ └─────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS LAYER (systemd)                           │
│  Heartbeat (:00) │ Reflection (:30) │ TaskDispatcher │ Maintenance      │
│  Alpha (2h)      │ Signals (15m)    │ Monitor        │ Security (3d)    │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Core Subsystems

### 4.1 AgentOS Kernel

**Reference:** arXiv 2602.20934v1

The kernel is Otto's central processing unit. All inputs — regardless of source or type — enter as typed interrupts and flow through a single processing pipeline.

**Processing cycle (RIC):** Save → Load → Process → Align → Post

**15 kernel modules:**

| Module | File | Purpose |
|---|---|---|
| Reasoning Kernel | `kernel/reasoning_kernel.py` | Async interrupt processing loop |
| IVT | `kernel/ivt.py` | Priority interrupt queue |
| RIC | `kernel/ric.py` (1063 lines) | Core cognitive cycle |
| S-MMU | `kernel/smmu.py` (524 lines) | L1/L2/L3 memory paging |
| Slicing | `kernel/slicing.py` | CID-based semantic segmentation |
| Drift | `kernel/drift.py` | Δψ measurement (sync at >0.3) |
| Sync | `kernel/sync.py` | Cognitive Sync Pulses |
| Perception | `kernel/perception.py` | LLM output validation |
| Provider | `kernel/provider.py` | Multi-LLM backend |
| Agents | `kernel/agents.py` | Cross-brain message graph |
| Peripherals | `kernel/peripherals/` | WhatsApp, Web, Scheduler adapters |
| Kernel Routes | `routes/kernel_routes.py` | `/kernel/*` API endpoints |

**9-hook post-process pipeline** (after every LLM response):
1. Episodic log
2. Semantic persist
3. Graphiti ingest
4. Pending question match
5. Directive extract
6. Reactive dispatch (plan classifier → single-dispatch → stop classifier)
7. Drift measurement
8. Thought vault capture
9. Cross-brain message

### 4.2 Memory Architecture

**Six memory layers:**

| Layer | Backend | Key Stats |
|---|---|---|
| Semantic | PostgreSQL + pgvector | 205+ active memories, 2400+ processed/maintenance cycle |
| Episodic | PostgreSQL | 323+ events, 7-day narrative consolidation |
| Procedural | PostgreSQL | 16 procedures, trust scores via exponential smoothing |
| Working | PostgreSQL | Fast PUT /working/memory/{slot} key-value |
| Knowledge Graph | Neo4j + Graphiti | Temporal entity extraction, G2CP typed nodes |
| Agent-specific | MEMORY.md files | 10+ agents with persistent domain files |

**S-MMU Memory Hierarchy:**
- **L1 (12K tokens, always-resident):** Purpose, priorities, directives, key context
- **L2 (dynamic):** CID-based semantic slices loaded on relevance
- **L3 (archived/cold):** Salience-decayed memories, retrievable on demand

**Five-strategy retrieval stack:**
1. **A-RAG** — 3-strategy search (semantic + keyword + graph), merged and re-ranked
2. **BMAM** — Blended ranking (similarity × recency × importance × goal-alignment)
3. **HyMem** — Dual-granularity (full content + pre-computed summaries)
4. **SVC** — Embedding bias removal (top-3 principal components stripped from queries)
5. **A-MEM** — Zettelkasten-style bidirectional memory graph auto-linking

**Maintenance schedule:**
- Salience decay (FadeMem): twice daily (02:00 + 14:00 IST)
- Narrative consolidation: daily
- Dedup sweep: threshold 0.96 cosine similarity
- Knowledge graph sync: continuous via post-process hook

### 4.3 Learning & Self-Improvement

This is Otto's second moat. No external AI agent framework has any automated self-improvement capability.

**Five learning systems:**

| System | File | How It Works | Status |
|---|---|---|---|
| RL2F Layer 1 | `routes/rl2f.py` (413 lines) | Heartbeat predictions scored against actuals; lessons extracted from misses | 40% accuracy, improving |
| RL2F Layer 2 | `routes/rl2f.py` | QA rejection feedback injected into task retry prompts | Active |
| JiTRL | `routes/jitrl.py` (335 lines) | kNN similarity finds past experiences; ranked hints injected at task creation | Active |
| AutoEvolve | `routes/autoevolve.py` (507 lines) | Hypothesis → mutation → N-cycle eval → keep/discard | Gen 3, State Delta patch +12pp |
| MARS | `kernel/ric.py` + reflection agent | Dual-adversarial: initial conclusions → critic → synthesis per cycle | Active |

Additional learning mechanisms:
- **Reasoning chain** — WHY/DECIDED/EXPECTED/ACTUAL per heartbeat. Outcome matching drives RL2F L2 lessons.
- **Workflow evolution** — Every 3 runs: fitness scoring + template mutation/discard.
- **Failure-branch adaptation (STEM-inspired)** — Detect failure signals → root cause → correction → retest.
- **Learned principles** — Trust-scored behavioral rules extracted from RL2F misses.
- **Self-critique** — ACCURACY/COMPLETENESS/GOAL_ALIGN/BIAS scored 1–5 per reflection cycle.

All learning operates via context engineering (prompt modification, not model training) — per standing directive.

### 4.4 Task Execution Engine

**Stats:** 1,374 tasks total (1,255 completed, 119 failed). Continuous operation since Feb 2026.

**Three execution tiers:**

**Tier 1: Individual Tasks**
- Task queue + lifecycle (`routes/tasks.py`, 1826 lines)
- Detached CLI runner (`task_runner.sh`) — claude/gemini/kimi, budget-capped, trap EXIT
- Continuous dispatcher (`otto-task-dispatcher.service`) — polls every 15s
- Max concurrent: 5 total (claude≤3, gemini≤1, kimi≤1)
- QA gate: Gemini reviews Claude outputs post-completion → approve/reject → RL2F feedback

**Tier 2: Plans (DAG Orchestration)**
- DAG task plans (`routes/task_plans.py`, 836 lines)
- Dependency edges, parallel/sequential/hybrid topologies
- Output injection — prev task output flows as template variables to dependents
- Agent auto-employment — 138 agents in `agency-agents/` activated on demand
- Plan classifier decomposes natural language instructions into DAGs

**Tier 3: Workflows (Pipelines)**
- Multi-agent workflow engine (`routes/workflows.py`, 2242 lines)
- Reusable step templates (content-publishing-pipeline, feature-development, research-pipeline, social-content-pipeline)
- Gate system: human_approval, code_review, security_audit checkpoints
- Auto-eval + evolution: fitness scoring + template mutation every 3 runs

**Quality mechanisms at task level:**
- LATS-style preflect: surfaces lessons before task starts
- JiTRL hint injection: relevant past experiences at task creation
- Artifact path storage (HiClaw): large outputs written to file, path stored in DB
- Hindsight analysis: post-completion lesson extraction

### 4.5 Heartbeat Agents (Autonomous Loops)

**Dual heartbeat rhythm — Otto's most distinctive operational pattern:**

| Agent | Schedule | Role |
|---|---|---|
| **Orchestrator** | Hourly :00 | Mission execution — review tasks, create/launch work, message Mev |
| **Reflection** | Hourly :30 | Self-improvement — reconcile, memory consolidate, evaluate performance |

This separation is critical: reflection can't be crowded out by task management, and vice versa.

**Additional autonomous loops:**

| Agent | Schedule | Purpose |
|---|---|---|
| Alpha trading heartbeat | Every 2h | Crypto signal analysis and trading decisions |
| Crypto signal publisher | Every 15m | Signal distribution to Telegram @OttoSignals |
| Alpha market watcher | Every 5m | Price monitoring, signal performance tracking |
| Research pipeline | Every 3h | Automated research sweeps |
| Security audit | Every 3 days | VM hardening, CVE checks, secrets hygiene |
| Vuln sync | Every 6h | Vulnerability intelligence updates |
| Memory maintenance | 02:00 + 14:00 | Decay, consolidation, dedup |
| Weekly self-improvement | Weekly | Deep reflection and architectural review |
| X/Twitter scheduler | Every 15m | Social media execution |
| Service health monitor | Periodic | Sibling timer self-healing |

**Self-healing:** Each heartbeat checks that sibling timers are running. If a timer is dead, it restarts it. This caught and fixed a 6-day timer outage in Feb 2026.

### 4.6 Communication Interfaces

| Interface | Stack | Status |
|---|---|---|
| WhatsApp (primary) | Baileys :3001 → Memory API | Live — Ottolabs account, primary Mev channel |
| WhatsApp Athena | Baileys :3002 → Athena handler | Live — separate agent channel |
| Email (admin@otto.lk) | Zoho SMTP :465 / IMAP :993 | Live — IDLE listener, send/reply/search via API |
| OMS (mev.otto.lk) | Next.js → Memory API | Live — 52 pages, full management dashboard |

### 4.7 Specialist Agents (21 Active + 138 Available)

**21 active agents** (Markdown prompt files in `otto/.claude/agents/`):
Orchestrator, Reflection, Alpha, Researcher, Research-Synthesizer, Architect, Coder, Reviewer, Debugger, Content-Creator, Memory-Curator, Outbound-Strategist, Growth-Hacker, Social-Media-Strategist, Twitter-Engager, Landing-Page, Security-Audit, Reality-Checker, Solidity-Smart-Contract-Engineer, Blockchain-Security-Auditor, Sprint-Prioritizer.

**138 catalogued agents** in `agency-agents/` — available for auto-employment by task plans on demand.

---

## 5. Full Feature Status

### 5.1 Domain Modules

| Domain | Module | Status |
|---|---|---|
| WebAssist | `routes/webassist.py` (398 lines) | Live at webassist.ink — CRM, leads, orders, projects |
| Koink.fun | `routes/koink.py` (575 lines) | API ready — DHM tokenomics, treasury, launch tracking |
| ONEON | `routes/oneon.py` (575 lines) | API ready — DID, credentials, governance |
| Tusita | `routes/tusita.py` | API ready — bookings, retreats, locations |
| SOS Systems | `routes/sos.py` | API ready — cases, learner management, aid distribution |
| Crypto/Alpha | `routes/crypto.py` (530 lines) | Live — signals, portfolio, NLP trade parsing |
| Bankr.bot | `routes/bankr.py` (642 lines) | Live — trading via Bankr Agent API |
| Universe Registry | `universe/` YAML + LLM edit API | Live — 15 projects + 3 personas, conversational edit |

> **Note:** Koink.fun, ONEON, Tusita, and SOS Systems have API backends ready but no deployed contracts or live frontends at time of writing. All domain-specific product claims for these projects should be treated as API-ready / in development.

### 5.2 Database Schema

80+ migrations, 35+ tables. Core: sessions, semantic_memories (pgvector), episodic_events, procedural_memories, tasks, task_retry_feedback, task_plans, workflow_templates, workflow_instances, workflow_gates, workflow_evolution_experiments, autoevolve_experiments, rl2f_feedback, jitrl_experiences, reasoning_entries, principles, conclusions, interrupts, agents, semantic_slices, cognitive_states, cross_brain_messages, cross_brain_graph, leads, outreach_queue, contacts, live_systems, secrets_vault, thought_vault, failure_branch_adaptations, a2a_messages, koink_*, oneon_*, tusita_*, sos_*.

---

## 6. Deployment Topology

**Hardware:** GCP VM, Debian 12, 4 vCPU, 16GB RAM, 68GB boot NVMe + 99GB media NVMe

**Port map:**

| Port | Service | Purpose |
|---|---|---|
| :8100 | Memory API (FastAPI) | Otto's brain — all intelligence routes |
| :5432 | PostgreSQL 17 + pgvector | Structured data, vectors, all relational data |
| :7474/:7687 | Neo4j 5.26.2 | Knowledge graph |
| :8000 | Graphiti | Temporal KG API over Neo4j |
| :3001 | WhatsApp bridge (Baileys) | Primary Mev communication |
| :3002 | Athena WhatsApp | Athena agent channel |

**17 systemd units** (services + timers): otto-memory, whatsapp, athena-whatsapp, otto-heartbeat(.timer), otto-reflection(.timer), otto-task-dispatcher, otto-alpha-watcher(.timer), otto-signals(.timer), otto-maintenance(.timer), otto-research-pipeline(.timer), otto-security-audit(.timer), otto-vuln-sync(.timer), otto-weekly-improve(.timer), service-monitor.

**External dependencies:**
- Claude API (Anthropic) — primary LLM for all tasks
- Gemini CLI — QA review, secondary tasks
- Kimi CLI — kernel conversation handling
- OpenAI API — embedding generation (pgvector)
- Zoho Mail (SMTP/IMAP) — admin@otto.lk
- Vercel — OMS hosting (mev.otto.lk)
- GitHub (ottomev) — all code repos

---

## 7. Key Engineering Learnings

### Memory System

1. **Dual-column archival is a footgun.** DB has both `archived` (boolean) and `deleted_at` (timestamp). Different routes used different columns. Caused 31 "ghost records." Rule: always filter `archived = FALSE AND deleted_at IS NULL` together.

2. **Compound decay kills memories fast.** Reflection applied 0.95x manual decay on top of AutoEvolve's 0.99x. Within days, 558 memories → 44 active. Fix: reflection.md has explicit "no manual decay" guard. Decay is maintenance-only.

3. **Episode truncation breaks context continuity.** Episodic events truncated at 200 chars, conversation window at 6 messages. This caused "goldfish memory" — Otto forgot directives from hours earlier. Fixed: events at 500 chars, 20 messages at 400 chars each.

4. **Dedup threshold matters.** At cosine 0.92, distinct events collapsed. At 0.96, dedup is healthy. Current: 0.96 in consolidation.py.

5. **Conversation→directive gap.** Kernel processes Mev's WhatsApp messages but does not auto-extract directives into semantic memory. Caused 26 stagnation flags. Root fix not yet implemented — manual extraction required.

### Task Execution

1. **Zombie tasks are the primary failure mode.** Coordinator tasks with no PID run indefinitely in DB with no live process. Cause: `set -euo pipefail` without `trap EXIT`. Rule: always include trap EXIT that POSTs failed status to completion API.

2. **Budget exhaustion is the secondary failure mode.** Complex bash script modifications need $2+ / 30+ turns. $1/25 turns = exhaustion before completion. Budget calibration remains imprecise.

3. **Rate limit false positives lost 60% of heartbeat cycles.** `grep -i "rate.limit"` matched heartbeat's own status output. Fixed: specific error patterns only (HTTP 429, RateLimitError).

4. **QA prompt truncation caused false rejections.** `PROMPT_EXCERPT="${PROMPT:0:800}"` hid task scope from Gemini reviewer. Fixed: raised to 2000 chars.

5. **QA is blind to `/mnt/media/projects/`** — auto-approves with "No file changes detected" for external repo tasks. Manual verification required.

6. **Task output field is unreliable.** Always verify by checking the actual codebase (timestamps, DB records, endpoint responses), not the task output field.

### Heartbeat Rhythms

1. **Timers can die silently.** All timers stopped unnoticed for 6 days in Feb 2026. Fix: each heartbeat checks sibling timers. Self-healing.

2. **Idle periods inflate learning metrics.** RL2F improved 32% → 40% partly during idle periods with trivially correct predictions. True validation requires active workload. Needs `idle_cycle` tag.

3. **Message fatigue is real.** Rule: never send Mev a message unless there's something new since the last check-in.

### What Was Rearchitected

| Component | From | To | Why |
|---|---|---|---|
| Task dispatch | Single-dispatch only | Plan classifier → single-dispatch fallback | Multi-step instructions created one task instead of DAG |
| Content generation | Inline in kernel | Content-creator agent via workflow | Otto was writing articles inline |
| Skill registry | Manual sync | Explicit `routes/skills.py` | Registry perpetually out of sync |
| WhatsApp message window | 6 msgs at 200 chars | 20 msgs at 400 chars | Goldfish memory incidents |

---

## 8. Failure Modes — Observed & Resolved

### Task Failures (from 119 failed tasks)

| Mode | Frequency | Status |
|---|---|---|
| Zombie task (no PID, coordinator timeout) | High | Mitigated — heartbeat kills zombies; root cause partially fixed |
| Rate limit exhaustion | High | Mitigated — detection + holding posture |
| Process died (set -e triggered) | Medium | Partially fixed |
| Budget exhaustion | Medium | Ongoing — imprecise calibration |
| Workflow step false failure | Low | Procedure documented: retry via approve endpoint |
| QA false rejection (truncated prompt) | Fixed | Raised excerpt to 2000 chars |

### Memory Failures

| Mode | Status |
|---|---|
| Mass-archival (558→44 in hours) | Fixed — no manual decay guard |
| Ghost records (archived/deleted_at desync) | Fixed — always use both columns |
| Empty TraceMem narratives | Persistent, low priority (33 archived) |
| Wink monitor false positives | Mitigated — noise accepted |

---

## 9. Improvement Backlog

### Short-Term (1–4 Cycles, High Confidence)

| # | Item | Impact | Effort |
|---|---|---|---|
| S1 | **A2A Protocol** — Agent Card endpoint + A2A handshake to task_plans.py and gateway | Very High | Medium |
| S2 | **STEM Caller Profiler** — 5–8 dimension tracker for Mev communication preferences (tone, depth, domain, urgency) | High | Medium |
| S3 | **RL2F idle_cycle tagging** — Tag predictions during idle periods; separate from active-workload predictions | Medium | Low |
| S4 | **Directive auto-extraction** — Lightweight classifier after kernel responses detects new directives; auto-stores to semantic + working memory | High | Low |
| S5 | **HiClaw GAP-3** — Add plan-classifier check to heartbeat.md at task creation step | Medium | Low |

### Medium-Term (1–3 Weeks)

| # | Item | Impact | Effort |
|---|---|---|---|
| M1 | **MCP Server Layer** — Wrap `/semantic`, `/tasks`, `/workflows` as MCP resources; positions Otto as infrastructure others build on | Very High | High |
| M2 | **DGM-H Reflection Unfreeze** — Allow reflection.md to be targeted by AutoEvolve; self-rewriting meta-agent pattern | Very High | Medium |
| M3 | **VISTA failure categorization** — Type task failures; inject category + correction hypothesis into retry | High | Medium |
| M4 | **OTel instrumentation** — OpenTelemetry trace/span to task execution and workflow engine | Medium | High |
| M5 | **S-MMU near-miss threshold** — similarity_threshold=0.7 for L2 slice injection; reduce context noise | Medium | Low |

### Long-Term (1–3 Months, Strategic)

| # | Item | Impact | Effort |
|---|---|---|---|
| L1 | **AgentOS Multi-tenant** — Extend kernel to serve multiple users; required for WebAssist agents and any multi-user product | Very High | Very High |
| L2 | **Multi-LLM expansion** — Bedrock/Ollama/Gemini via openai_compatible adapter; reduces cost + single-provider risk | Medium | Medium |
| L3 | **Deriver Pattern (Honcho)** — Async background processor building Mev-specific representations from interaction history | High | High |
| L4 | **TrustGraph Context Cores** — Versioned portable knowledge bundles (WebAssist, SOS, Koink protocols) importable by any agent | Medium | Medium |
| L5 | **AOP Governance Layer** — Policy enforcement, audit trails, role-based capability restriction per agent | High | Very High |

---

## 10. Competitive Landscape

*Full analysis: `otto-vs-ai-harnesses-comparison-2026-03-28.md`*

Frameworks compared: LangGraph, CrewAI, AutoGen/AG2, OpenAI Agents SDK, Google ADK, Mastra, Strands (AWS), Pydantic AI, Semantic Kernel.

### Summary Matrix

| Dimension | Otto | Best External |
|---|---|---|
| Memory (Persistent) | ★★★★★ | ★★★☆☆ (Mastra) |
| Memory (Retrieval) | ★★★★★ | ★★☆☆☆ (Mastra) |
| Multi-Agent Orchestration | ★★★★★ | ★★★★★ (LangGraph) |
| Self-Improvement | ★★★★★ | ☆☆☆☆☆ (all frameworks) |
| Observability | ★★☆☆☆ | ★★★★★ (LangGraph, Pydantic AI) |
| Cost Control | ★★★★☆ | ★★★☆☆ |
| Production Readiness | ★★★★☆ | ★★★★★ (LangGraph) |
| Multi-LLM Provider | ★★☆☆☆ | ★★★★★ (OpenAI SDK) |
| A2A Protocol | ★★★☆☆ | ★★★★★ (Google ADK) |
| MCP Support | ★★★☆☆ | ★★★★★ (Google ADK, Mastra) |

### Otto's Confirmed Advantages

| Advantage | Detail |
|---|---|
| Memory stack depth | 6 layers + 5-strategy retrieval — no competitor has >1 layer |
| Self-improvement | 5 systems (RL2F, AutoEvolve, MARS, JiTRL, workflow evolution) — absent in all frameworks |
| Orchestration depth | 3-tier (tasks + plans/DAG + workflows) + agent auto-employment + plan decomposition from NL |
| Autonomous operation | Dual heartbeat, self-healing timers, drift detection — 24/7 without human intervention |
| Cost discipline | Per-task budgets, concurrency limits, cross-model QA gate |
| Research depth | 24+ papers adapted and implemented |

### Otto's Confirmed Gaps

| Gap | Severity | Who Has It |
|---|---|---|
| OpenTelemetry (logs only) | **Critical** | Pydantic AI, Strands, Google ADK, Mastra |
| MCP native support | High | Google ADK, Mastra, Strands |
| A2A protocol maturity | High | Google ADK, Strands |
| Self-rewriting reflection | High | HyperAgents (arXiv 2603.19461) |
| Multi-LLM breadth | Low | OpenAI SDK (100+), Pydantic AI (25+) |

---

## 11. Strategic Position

Otto is not an agent framework — it's an **agent operating system**. The distinction:

| Aspect | Agent Frameworks | Otto |
|---|---|---|
| Usage model | Library imported into your app | Autonomous system running 24/7 on its own |
| State model | Per-request or per-session | Continuous across months of operation |
| Memory | Plugin/feature (basic) | First-class OS subsystem (6-layer, 5-strategy) |
| Learning | None | 5 learning systems |
| Deployment | Part of a larger app | Deploys itself, maintains itself, heals itself |
| Agent composition | Define in code | 21 active Markdown agents + 138 available, auto-employed |

**Strategic position:**

```
                    Static Execution ←────────────────→ Self-Improving
                         │                                    │
    Library/Framework ───┤  LangGraph                         │
                         │  CrewAI                            │
                         │  OpenAI SDK                        │
                         │  Google ADK                        │
                         │                                    │
    Operating System ────┤                               ★ Otto
                         │                                    │
```

No other system is both an operating system AND self-improving. This positioning means Otto doesn't compete directly with frameworks — it competes with the concept of a static agent system.

**One-line summary:** Otto is the only AI agent system that remembers, learns, and improves autonomously — turning the gap between static frameworks and self-improving intelligence into a widening competitive moat.

---

## 12. Key Design Decisions & Trade-offs

| Decision | Trade-off Made | Why |
|---|---|---|
| PostgreSQL as universal backend | Performance vs simplicity | One DB type for relational, vector, JSON, task queue. Avoids Redis/Kafka/DynamoDB proliferation. |
| Claude Code CLI as compute (not API) | Latency vs isolation | Detached processes give budget caps, killability, and context isolation. API calls would be faster but harder to control. |
| Markdown agent files | Simplicity vs type-safety | Edit a text file, change agent behavior. No recompile. AutoEvolve can mutate prompts programmatically. |
| Dual heartbeat (execution vs reflection) | Resource efficiency vs separation | Reflection budget never stolen by task management. Real separation of concerns. |
| Cross-model QA (Gemini reviewing Claude) | Cost vs quality | Different model catches different blind spots. Gemini caught truncation bugs Claude tasks would self-approve. |
| S-MMU paging (L1/L2/L3) | Complexity vs context quality | Context budget is finite. Always-resident L1 + dynamic L2 retrieval is better than naively filling context. |
| No model training | Autonomy vs learning speed | Standing directive: no training, ever. All learning via context engineering (prompts, procedures, RL2F). |
| File-based agent memory | Portability vs DB consistency | Agent MEMORY.md files survive DB resets and are human-readable. Claude Code agents can't access DB natively. |

---

## 13. Known Limitations

**Resource constraints:**
- Single VM: 4 vCPU / 16GB RAM / 68GB boot / 99GB media. No horizontal scaling.
- No swap. Memory pressure during heavy multi-task bursts.

**Learning gaps:**
- RL2F accuracy at 40% — genuine active-workload validation needed (idle periods inflate score).
- Directive auto-extraction unimplemented — Mev's WhatsApp directives may not persist to semantic memory.
- AutoEvolve Gen 3 validation pending active workload (Gen 2→3 improvement partially idle-inflated).

**Architecture gaps:**
- OTel absent — no structured traces for multi-agent workflow debugging.
- No MCP server layer — Otto's memory/tasks/workflows not accessible to external MCP clients.
- A2A protocol immature — DB-backed channel messaging, not protocol-level agent cards.
- Process-spawning model adds 3–8s latency per interaction vs API-based frameworks.

**Operational issues:**
- Wink stall monitor generates false positives for I/O-heavy tasks (16 alerts in 24h for 3 tasks that completed fine).
- Empty TraceMem narratives accumulate (33 archived, ongoing).
- Workflow coordinator zombie tasks are mitigated but not fully eliminated.
- Task budget calibration remains imprecise (trial-and-error per task type).

**Scaling ceiling:**
- Single-operator, single-VM design not built for multi-tenant or multi-node.
- `task_runner.sh` spawns OS processes; at scale this becomes a process table concern.
- PostgreSQL as universal backend: excellent for current load, will require sharding at 10x+ scale.

---

## Appendix A: API Surface Summary

Full API surface: 80+ routes across 25+ modules on Memory API (:8100).

**Core groups:**
- `/kernel/*` — AgentOS kernel state, interrupts, sync, drift, slices
- `/semantic/*` — Remember, search, maintain memories
- `/episodic/*` — Log events, query timeline, consolidate narratives
- `/procedural/*` — Create/update procedures, track outcomes
- `/working/*` — Fast key-value working memory slots
- `/tasks/*` — Create, run, stop, complete, review tasks
- `/task-plans/*` — DAG orchestration: create, monitor, cancel plans
- `/workflows/*` — Templates, start instances, gates, evolution
- `/rl2f/*` — Feedback recording, lesson retrieval, accuracy scoring
- `/jitrl/*` — Experience storage, kNN retrieval
- `/autoevolve/*` — Experiment management, keep/discard
- `/reasoning/*` — WHY/DECIDED/EXPECTED/ACTUAL chain entries
- `/principles/*` — Behavioral rules from RL2F lessons
- `/universe/*` — Ecosystem registry, LLM conversational edit
- `/content/*` — Content DB (articles, plans, social posts, research)
- `/graph/*` — Proxy to Graphiti knowledge graph API
- `/email/*` — Send, receive, reply, search (admin@otto.lk)
- `/webassist/*`, `/koink/*`, `/oneon/*`, `/tusita/*`, `/sos/*` — Domain modules
- `/health`, `/metrics`, `/sessions/*`, `/context/*` — Housekeeping

---

## Appendix B: Research Papers Implemented

24+ papers adapted and deployed in Otto. Key implementations:

| Paper / Concept | Implementation | Status |
|---|---|---|
| AgentOS (arXiv 2602.20934v1) | Kernel: IVT, RIC, S-MMU, slicing, drift, sync | Live |
| HyMem (dual-granularity retrieval) | Semantic: full content + pre-computed summaries | Live |
| A-RAG (adaptive retrieval) | Semantic: 3-strategy merged retrieval | Live |
| BMAM (blended ranking) | Semantic: similarity × recency × importance × goal-align | Live |
| A-MEM (memory graph) | Semantic: Zettelkasten-style auto-linking | Live |
| SVC (bias removal) | Semantic: query embedding debiasing | Live |
| FadeMem (salience decay) | Maintenance: importance-weighted time decay | Live |
| RL2F (reinforcement from feedback) | 2-layer learning: heartbeat + QA chains | Live |
| JiTRL (experience replay) | kNN hint injection at task creation | Live |
| MARS (adversarial reflection) | Dual-critic per reflection cycle | Live |
| G2CP (knowledge graph typing) | Graphiti: typed entity nodes | Live |
| LATS (preflect) | Task creation: surfaces lessons before start | Live |
| HiClaw (artifact path) | Tasks: large outputs written to file, path stored | Live |
| STEM-inspired failure branch | Failure detection → root cause → correction → retest | Live |
| SimpleMem (compression) | Consolidation: dedup → summarize → rank+trim | Live |
| DGM-H / HyperAgents (arXiv 2603.19461) | AutoEvolve: propose → test → keep/discard | Partial (reflection.md not yet a target) |

---

## Appendix C: Glossary

| Term | Definition |
|---|---|
| AgentOS | Cognitive operating system architecture (arXiv 2602.20934v1). All inputs as typed interrupts, processed by single kernel. |
| IVT | Interrupt Vector Table — priority queue that routes inputs to the kernel. Admin messages always highest priority. |
| RIC | Reasoning Interrupt Cycle — Save→Load→Process→Align→Post cognitive loop. |
| S-MMU | Semantic Memory Management Unit — L1/L2/L3 memory paging hierarchy. |
| CID | Content-addressable ID — semantic hash for memory slice segmentation. |
| Δψ | Cognitive drift measure — cosine distance between L1 context centroid and ground truth. |
| A-RAG | Adaptive RAG — 3-strategy retrieval (semantic + keyword + graph) with merged re-ranking. |
| BMAM | Blended Memory Access Model — multi-factor retrieval ranking. |
| HyMem | Hybrid Memory — dual-granularity: full content + summaries. |
| RL2F | Reinforcement Learning from Feedback — teacher-feedback-driven context learning. |
| JiTRL | Just-in-Time Reinforcement Learning — experience replay via kNN similarity. |
| AutoEvolve | Autonomous experiment loop: hypothesis → mutation → N-cycle eval → keep/discard. |
| MARS | Multi-Adversarial Reflection System — dual-critic adversarial self-critique. |
| LATS | Look-Ahead Task Synthesis — pre-task lesson surfacing (preflect). |
| HiClaw | Artifact path storage pattern for large outputs. |
| STEM | Strategic Task Execution Model (arXiv 2603.22359) — tool composition + caller profiling. |
| DGM-H | Darwin Genetic Meta-Hypothesis — self-rewriting meta-agent (HyperAgents arXiv 2603.19461). |
| FadeMem | Importance-weighted salience decay for memory archival. |
| A-MEM | Associative Memory — Zettelkasten-style bidirectional memory graph. |
| SVC | Subspace Value Correction — removes embedding bias directions from queries. |
| G2CP | Graph-to-Context Protocol — typed entity node structure for knowledge graph. |
| Wink | Stall monitor — detects tasks that haven't produced output in 90+ seconds. |
| OMS | Otto Management System — Next.js dashboard at mev.otto.lk. |
| WHY/DECIDED/EXPECTED/ACTUAL | Structured reasoning chain format logged every heartbeat cycle. |

---

*This master document compiles three source documents produced 2026-03-28:*
*`otto-system-architecture-2026-03-28.md` (architect agent) + `otto-features-learnings-roadmap-2026-03-28.md` (memory-curator agent) + `otto-vs-ai-harnesses-comparison-2026-03-28.md` (researcher/synthesizer agents)*

*Source documents remain the authoritative reference for their respective sections. This master document is the single entry point for understanding the full Otto system.*

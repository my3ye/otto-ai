# Otto System Architecture

**Version:** 1.0
**Date:** 2026-03-28
**Status:** Reference Document
**Author:** Otto (architect agent)

---

## Table of Contents

1. [System Overview & Design Philosophy](#1-system-overview--design-philosophy)
2. [Core Subsystems](#2-core-subsystems)
3. [Data Flows & Message Bus](#3-data-flows--message-bus)
4. [Memory Architecture](#4-memory-architecture)
5. [Tool Registry & Execution Model](#5-tool-registry--execution-model)
6. [Observability & Logging](#6-observability--logging)
7. [Deployment Topology](#7-deployment-topology)
8. [Key Design Decisions & Trade-offs](#8-key-design-decisions--trade-offs)
9. [Known Limitations](#9-known-limitations)

---

## 1. System Overview & Design Philosophy

### What Otto Is

Otto is a persistent, autonomous AI agent operating as a cognitive operating system. It is not a chatbot, not a wrapper around an LLM, and not a single-purpose tool. Otto is a continuous entity with memory, identity, and agency — animated by Claude (Anthropic) but maintaining its own state, learning, and mission across sessions.

Otto serves as the operational intelligence layer for the MY3YE ecosystem — a portfolio of 15+ projects spanning decentralized infrastructure, community platforms, sovereign identity, and agentic services. It operates as Mev's (the Admin) COO: mapping work, tracking status, building systems, and executing autonomously within defined boundaries.

### Design Philosophy

**1. Interrupt-Driven, Not Poll-Driven**
All inputs — WhatsApp messages, scheduled heartbeats, task completions, drift alerts — enter the system as typed interrupts through a single processing kernel. This unifies reactive (conversational) and proactive (autonomous) behavior under one cognitive model, drawn from AgentOS (arXiv 2602.20934v1).

**2. Memory as First-Class Infrastructure**
Otto treats memory the way an OS treats storage — with explicit hierarchies (L1/L2/L3), access patterns (paging, eviction, decay), and maintenance cycles (consolidation, dedup, archival). Every subsystem writes to and reads from a unified memory layer. This is the foundation that makes Otto persistent rather than ephemeral.

**3. Simple, Composable, Correct**
Prefer small modules that compose over monolithic systems. The Memory API has 80+ route modules, but each is a focused router with clear boundaries. Agents are Markdown prompt files. Workflows chain agents through templates. Plans decompose into DAG-linked tasks. Every layer is independently testable.

**4. Ship Over Perfection**
Operational systems beat elegant designs. Otto runs 24/7 on modest hardware (4 vCPU, 16GB RAM). When a feature works, it ships. Iteration happens through AutoEvolve experiments, not rewrites. The architecture accommodates this by making most changes additive.

**5. Research-Informed, Not Research-Driven**
24+ research papers have been implemented, but always as practical systems adapted to Otto's constraints — not academic reproductions. JiTRL provides experience replay without gradient updates. A-MEM creates a memory graph without training. RL2F learns from teacher feedback without model fine-tuning.

**6. Autonomous Within Boundaries**
Otto has full control over its VM (file system, packages, services, Docker, systemd) but contacts Mev before touching external services, sending messages to third parties, or making financial transactions. The system is designed for self-healing: timers check sibling services, maintenance runs on schedule, drift triggers self-correction.

### Architecture at a Glance

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

## 2. Core Subsystems

### 2.1 AgentOS Kernel

**Reference:** arXiv 2602.20934v1 — "AgentOS: A Cognitive Operating System for LLM Agents"

The kernel is the central processing unit of Otto's cognitive architecture. All inputs — regardless of source or type — enter as typed interrupts and flow through a single processing pipeline.

#### Components

| Module | Lines | Purpose |
|---|---|---|
| `reasoning_kernel.py` | 40 | Facade — exposes `ensure_kernel_running()`, delegates to `CognitiveScheduler` |
| `scheduler.py` | 134 | Async event loop. Dequeues interrupts from IVT, passes to RIC, handles retry/backoff |
| `ric.py` | 1,063 | **Core processing logic.** Routes interrupts by type, builds LLM context via S-MMU, executes 8 post-process hooks |
| `ivt.py` | 300 | Interrupt Vector Table — priority queue backed by PostgreSQL `interrupts` table |
| `smmu.py` | 524 | Semantic Memory Management Unit — L1/L2/L3 memory hierarchy with HyMem/ARAG retrieval |
| `drift.py` | 164 | Cognitive drift detection (Δψ cosine distance from ground truth) |
| `sync.py` | 311 | Cognitive Sync Pulses — state reconciliation on drift, schedule, or manual trigger |
| `slicing.py` | 295 | CID-based semantic segmentation of documents into pageable chunks |
| `perception.py` | 136 | LLM output validation (hallucination, format, content policy checks) |
| `provider.py` | 597 | Pluggable LLM backends (Claude, Gemini, Kimi) with load balancing and health tracking |
| `agents.py` | 178 | Agent registry — maps agent IDs to interrupt types and provider preferences |
| `state.py` | 105 | Cognitive state snapshots for crash recovery |
| `types.py` | 107 | Interrupt type definitions and priority constants |
| `masking.py` | 54 | PII stripping before LLM injection |
| `hooks.py` | 75 | Post-process callback registry |

#### Interrupt Processing Pipeline

```
Input → IVT.enqueue(type, priority, payload)
         │
         ▼
CognitiveScheduler.dequeue()
         │
         ▼
RIC.process_interrupt()
  ├── 1. Load interrupt from IVT
  ├── 2. Route by type (admin_message, heartbeat, maintenance, task_event, sync_drift)
  ├── 3. S-MMU.assemble_context() → page relevant L2 memories into L1
  ├── 4. Build system prompt (identity + priorities + L1 context)
  ├── 5. LLM call via provider.provider_chat()
  ├── 6. perception.validate_output()
  └── 7. Post-process hooks (parallel):
       ├── _hook_episodic_log          → log event to episodic memory
       ├── _hook_persist_messages      → save to cross_brain_messages
       ├── _hook_graphiti_ingest       → write to knowledge graph
       ├── _hook_pending_match         → resolve pending questions
       ├── _hook_directive_extract     → extract directives from conversation
       ├── _hook_reactive_dispatch     → classify and dispatch agent tasks
       ├── _hook_drift_measure         → measure cognitive drift (every 5th interrupt)
       └── _hook_thought_vault_capture → capture fleeting ideas
```

#### Interrupt Types & Priorities

| Type | Priority | Source |
|---|---|---|
| `admin_message` | 10 (highest) | Mev via WhatsApp |
| `heartbeat` | 5 | Scheduled timer |
| `task_event` | 7 | Task completion/failure |
| `sync_drift` | 8 | Drift threshold exceeded |
| `maintenance` | 3 | Scheduled maintenance |
| `perception_error` | 9 | Output validation failure |

### 2.2 OMS (Otto Management System)

**Live at:** mev.otto.lk
**Tech stack:** Next.js 15, TypeScript, shadcn/ui (thegridcn-ui), pnpm
**Deployment:** Vercel (ottomev GitHub account)
**Pages:** 52

The OMS is Mev's primary interface for observing and controlling Otto. It is a full management dashboard that provides visibility into every subsystem.

#### Page Groups

| Group | Pages | Purpose |
|---|---|---|
| **Command** | `/tasks`, `/plans`, `/workflows`, `/agents` | Task queue, DAG plans, workflow pipelines, agent registry |
| **Automation** | `/workflows/detail`, `/reasoning`, `/critiques` | Workflow visualization, heartbeat reasoning chain, MARS reflections |
| **WebAssist** | `/webassist/*` (7 pages) | Leads, orders, outreach, prospects, Athena, projects |
| **Content & Research** | `/content-hub`, `/articles`, `/research`, `/thought-vault` | Content pipeline, article CMS, research notes, idea capture |
| **Communication** | `/chat`, `/inbox`, `/whatsapp`, `/contacts` | Real-time chat, email inbox, WhatsApp history, contact book |
| **Ecosystem** | `/universe`, `/ecosystem`, `/roadmap`, `/capital` | Project registry, ecosystem map, roadmap, capital strategy |
| **Infrastructure** | `/services`, `/live-systems`, `/environment/*`, `/security`, `/secrets`, `/backup` | Service health, live systems, architecture view, security findings, secrets vault, backups |

#### OMS Architecture Pattern

```
OMS (Next.js, Vercel)
  │
  ├── Client components → fetch() to Memory API (:8100)
  │     ├── SWR for polling (tasks, inbox)
  │     └── Direct REST for mutations
  │
  └── No server-side data layer — pure API consumer
       └── Memory API is the single source of truth
```

The OMS is intentionally stateless. It holds no data of its own — every page is a view over Memory API endpoints. This means the API is the system, and the OMS is one of many possible frontends.

### 2.3 MARS (Multi-Adversarial Reflection System)

MARS is Otto's self-critique engine, running every reflection cycle (:30 heartbeat).

#### Process

```
1. Reflection agent generates N initial conclusions about system state
2. Adversarial critic challenges each conclusion:
   ├── VALID   → conclusion stands
   ├── REVISED → conclusion updated with new framing
   └── REJECTED → conclusion discarded
3. Synthesis: merge confirmed + revised conclusions
4. Self-critique scores: ACCURACY, COMPLETENESS, GOAL_ALIGN, BIAS (each 1-5)
5. Store critiques in DB (critiques table) + surface on OMS /critiques page
```

**API:** `POST /critiques`, `GET /critiques` (with filters)
**Storage:** `critiques` table — per-cycle adversarial + self-critique records
**Integration:** Reflection agent runs MARS every cycle; conclusions feed into reasoning chain

### 2.4 HyMem (Hybrid Memory) & Memory Retrieval Stack

HyMem implements dual-granularity retrieval: every semantic memory has both a full embedding and a pre-computed summary embedding. This lets retrieval work at two scales — find broadly relevant memories via summary, then rank precisely via full content.

#### Retrieval Pipeline

```
Query arrives
  │
  ├── A-RAG: 3-strategy search
  │     ├── Strategy 1: Semantic (pgvector cosine similarity on full embeddings)
  │     ├── Strategy 2: Keyword (pg_trgm trigram matching on content text)
  │     └── Strategy 3: Graph (Graphiti temporal knowledge graph search)
  │
  ├── BMAM: Blended ranking
  │     score = α·vector_sim + β·recency + γ·importance + δ·goal_alignment
  │
  ├── SVC: Singular Value Calibration
  │     Remove top-3 bias directions from query embeddings (reduces anisotropy)
  │
  ├── A-MEM: Memory graph linking (arXiv 2502.12110)
  │     New memories auto-link to semantically related existing memories
  │     Zettelkasten-style bidirectional association network
  │
  └── FadeMem: Importance-weighted decay
        Salience decays over time; memories below threshold are archived
```

**Key endpoint:** `POST /semantic/search` — unified search with all strategies
**HyMem-specific:** `GET /semantic/hymem_briefing_facts` — summary-level retrieval
**A-MEM links:** `POST /semantic/search_with_links` — returns linked memory clusters

### 2.5 RL2F (Reinforcement Learning from Teacher Feedback)

RL2F is a two-layer learning system that enables Otto to improve without model fine-tuning.

#### Layer 1: Heartbeat Critiques

```
Each heartbeat cycle:
  1. Orchestrator makes prediction: EXPECTED = "X will happen"
  2. Next cycle: ACTUAL = what actually happened
  3. Score: MATCHED / PARTIAL / MISS
  4. On MISS: extract_lessons() → store as learned principle
  5. Principles have trust scores (exponential smoothing on outcomes)
  6. pre_decision_brief() injects relevant principles before next prediction
```

**Metric:** Accuracy rate (currently 40% = 20/50 recent predictions matched)
**Storage:** `reasoning_entries` table (WHY/DECIDED/EXPECTED/ACTUAL chain), `principles` table

#### Layer 2: Task Retry Feedback

```
Task fails QA → structured rejection feedback stored
  │
  ├── Retry created with feedback injected into prompt
  │     (qa_runner.sh → RL2F feedback → task_retry_feedback table)
  │
  ├── Retry succeeds → positive signal stored
  │     (correction pattern learned)
  │
  └── Retry fails again → escalate or abandon
        (failure pattern tracked)
```

**API:** `POST /rl2f/feedback`, `GET /rl2f/untrained` (pending training data)
**Integration:** `task_runner.sh` → `qa_runner.sh` → RL2F feedback loop

### 2.6 Heartbeat & Health Layer

Otto's autonomous behavior is driven by two complementary heartbeats running every hour, staggered by 30 minutes.

#### Orchestrator Heartbeat (:00)

**Runner:** `heartbeat.sh` (231 lines) → spawns Claude Code CLI with `heartbeat.md` agent
**Budget:** $1.00 per cycle, Sonnet model
**Purpose:** Mission execution

```
1. Rate limit check (skip if recently rate-limited)
2. Load unified context (identity + memory + events + queue)
3. REFLECT: Did I advance the mission? What happened since last cycle?
4. DECIDE: Review tasks → create new tasks → launch work → message Mev
5. PREDICT: EXPECTED = what should happen before next cycle
6. Score previous cycle's EXPECTED vs ACTUAL (RL2F Layer 1)
7. Log heartbeat event to episodic memory
```

#### Reflection Heartbeat (:30)

**Runner:** `reflection.sh` (98 lines) → spawns Claude Code CLI with `reflection.md` agent
**Budget:** $1.00 per cycle, Sonnet model
**Purpose:** Self-improvement

```
1. Memory consolidation (dedup, decay, archive stale)
2. AutoEvolve evaluation (tick experiment counter, keep/discard at cycle N)
3. MARS dual-reflection (adversarial critique of system state)
4. RL2F scoring and principle extraction
5. System health verification (services, disk, RAM)
6. Performance analysis and working memory correction
```

#### Self-Healing

- `service-monitor.timer` checks all services are alive; restarts downed units
- Each heartbeat verifies sibling timers are enabled (prevents repeat of Feb 25 timer outage)
- Kernel drift detection triggers automatic sync pulses when context drifts

### 2.7 Agent SDK Layer

Otto uses Claude Code CLI as its primary compute engine. Specialist agents are defined as Markdown prompt files that configure Claude Code sessions.

#### Agent Types (21 Active)

| Role | Agent File | Usage |
|---|---|---|
| Orchestrator | `heartbeat.md` | Hourly autonomous mission execution |
| Self-Improvement | `reflection.md` | Hourly memory/learning consolidation |
| System Design | `architect.md` | Architecture decisions, API design |
| Implementation | `coder.md` | Code, features, bug fixes |
| Code Review | `reviewer.md` | Read-only quality review |
| Root Cause | `debugger.md` | Error diagnosis, minimal fixes |
| Research | `researcher.md` | Multi-source retrieval, web research |
| Synthesis | `research-synthesizer.md` | Raw findings → structured intelligence |
| Content | `content-creator.md` | Articles, manifestos, X threads |
| Memory | `memory-curator.md` | Consolidation, dedup, archive |
| Security | `security-audit.md` | VM hardening, CVE scanning |
| QA Gate | `reality-checker.md` | Evidence-based production certification |
| Growth | `growth-hacker.md` | Acquisition, conversion, viral loops |
| Outreach | `outbound-strategist.md` | Prospecting, ICP, sequences |
| Social | `social-media-strategist.md` | Cross-platform campaigns |
| Twitter | `twitter-engager.md` | X engagement, threads |
| Smart Contracts | `solidity-smart-contract-engineer.md` | EVM Solidity development |
| Contract Audit | `blockchain-security-auditor.md` | Smart contract security |
| Sprint | `sprint-prioritizer.md` | Feature prioritization |
| Alpha Trading | `alpha_heartbeat.md` | Crypto signal scanning |
| Landing Pages | `landing-page.md` | Page creation and optimization |

#### Agent Execution Model

```
POST /tasks/{id}/run
  │
  └── task_runner.sh spawns:
        claude --print \
          --model {model} \
          --max-turns {budget/0.04} \
          --agent-prompt .claude/agents/{agent}.md \
          --allowedTools "Read,Write,Edit,Bash,Grep,Glob,Agent,..." \
          "Task prompt with context injection"
```

Each agent runs as an isolated Claude Code CLI process with:
- Its own agent prompt (Markdown defining role, tools, constraints)
- Its own persistent memory directory (`.claude/agent-memory/{type}/`)
- Budget-controlled max turns
- Pre-injected context (JiTRL hints, dependency outputs, working directory)
- Post-completion hooks (QA gate, JiTRL ingest, A2A signals, plan advancement)

#### Agent Auto-Employment

When a task plan requires an agent type not currently active, Otto searches `agency-agents/` (139 available agents from an external repository) and copies the matching agent file to `.claude/agents/` automatically.

---

## 3. Data Flows & Message Bus

Otto does not use a traditional message broker (no Kafka, no Redis queues). Instead, PostgreSQL serves as both the data store and the message bus, with the Memory API as the coordination layer.

### 3.1 Mev → Otto (Conversational)

```
1. Mev sends WhatsApp message
2. Baileys service.mjs (:3001) receives → POST /whatsapp/incoming
3. gateway/handler.py checks kernel_enabled flag
4. gateway/handler.py builds interrupt payload → IVT.enqueue(admin_message, priority=10)
5. CognitiveScheduler wakes on asyncio Event → dequeues interrupt
6. RIC.process_interrupt():
   a. S-MMU.assemble_context() → load L1 (identity + priorities + recent messages)
   b. HyMem/ARAG retrieval for message-relevant memories → page into L1
   c. Build system prompt → LLM call (Kimi primary, Claude/Gemini fallback)
   d. perception.validate_output()
   e. 8 post-hooks fire in parallel
7. Response → POST to WhatsApp :3001/send → delivered to Mev
```

**Latency:** 3-8 seconds end-to-end (dominated by LLM inference)

### 3.2 Task Creation → Execution → QA → Learning

```
1. Task created: POST /tasks (from heartbeat, reactive dispatch, or plan engine)
   └── JiTRL: inject k-NN experience hints into task prompt

2. Dispatcher polls: task_dispatcher.py (15s interval)
   └── Concurrency gate: claude≤3, gemini≤1, kimi≤1

3. Launch: POST /tasks/{id}/run → task_runner.sh spawns
   ├── Pre-flight: git status, budget check
   ├── Claude Code CLI with specialist agent
   ├── On completion: POST /tasks/{id}/complete with output + artifact path
   └── Trap EXIT: marks task failed on unexpected exit (prevents zombies)

4. QA Gate: qa_runner.sh
   ├── Capture git diff (per-file for large changesets)
   ├── Gemini CLI review (or auto-approve for verified research/content)
   └── Result: APPROVED or REJECTED with structured feedback

5. Post-Completion:
   ├── JiTRL: ingest (state, action, reward, outcome) → experiences table
   ├── A2A: signal completion to channel (if plan/workflow)
   ├── If plan task: task_plans.py advances DAG → injects output to dependents
   ├── If workflow task: workflows.py advances step → evaluates → may evolve template
   └── If rejected: RL2F Layer 2 feedback → retry creation with feedback injection
```

### 3.3 Inter-Agent Communication (A2A)

When tasks run within a plan or workflow, agents communicate through PostgreSQL-backed channels.

```
Agent A completes task → POST /a2a/send {channel_id, content, message_type: "completion"}
Agent B polls            → GET /a2a/poll?channel_id=X&reader_id=Y
Plan engine listens      → on_plan_task_complete() checks DAG for next launchable tasks
```

**Design:** Simple HTTP polling over PostgreSQL `a2a_messages` table. No WebSocket, no external broker. Channels are scoped by `plan_id` or `workflow_instance_id`.

### 3.4 Memory Write Paths

| Source | Write Path | Storage |
|---|---|---|
| Conversations | `_hook_episodic_log` → `/episodic/events` | `episodic_events` (pgvector) |
| Conversations | `_hook_persist_messages` → cross_brain_messages | `cross_brain_messages` |
| Conversations | `_hook_graphiti_ingest` → Graphiti API | Neo4j knowledge graph |
| Conversations | `_hook_directive_extract` → `/semantic/remember` | `semantic_memories` (pgvector) |
| Conversations | `_hook_thought_vault_capture` → `/thought-vault` | `thought_vault` |
| Task results | `/tasks/{id}/complete` → JiTRL ingest | `jitrl_experiences` |
| QA feedback | `qa_runner.sh` → RL2F feedback | `task_retry_feedback` |
| Heartbeats | `/reasoning` endpoints | `reasoning_entries` |
| Reflections | `/critiques` endpoints | `critiques` |
| Agent learning | AutoEvolve → file mutations + DB tracking | `autoevolve_experiments` |
| Agents | `.claude/agent-memory/{type}/MEMORY.md` | Filesystem (git-tracked) |

---

## 4. Memory Architecture

Otto's memory system implements a multi-tier architecture inspired by both operating system memory management and cognitive science.

### 4.1 Memory Hierarchy (S-MMU)

```
┌─────────────────────────────────────────────────────┐
│ L1: In-Memory Cache (12,000 tokens)                 │
│  ├── Always-Resident (~2,000 tokens):               │
│  │   CONSTITUTION, priorities, directives            │
│  ├── Dynamic (~10,000 tokens):                      │
│  │   Message-relevant memories, recent context       │
│  └── Eviction: LRU by access time + importance      │
├─────────────────────────────────────────────────────┤
│ L2: PostgreSQL + pgvector (Warm Storage)            │
│  ├── semantic_memories: pgvector embeddings          │
│  │   HyMem: full + summary dual-granularity          │
│  │   A-MEM: bidirectional memory graph links         │
│  ├── episodic_events: timestamped events + salience  │
│  ├── procedural_memories: skill procedures + trust   │
│  ├── semantic_slices: CID-based document chunks      │
│  ├── reasoning_entries: WHY/DECIDED/EXPECTED chain   │
│  └── Retrieval: A-RAG 3-strategy + BMAM ranking     │
├─────────────────────────────────────────────────────┤
│ L3: Neo4j + Graphiti (Cold Storage)                 │
│  ├── Temporal knowledge graph                        │
│  │   Entities, relationships, temporal edges         │
│  ├── G2CP cross-brain graph nodes                    │
│  │   Typed: directive, decision, task_state, context │
│  └── Retrieval: Graphiti NLP search → A-RAG merge   │
└─────────────────────────────────────────────────────┘
```

### 4.2 Semantic Memory

**Table:** `semantic_memories`
**Embedding:** OpenAI `text-embedding-3-small` (1536 dimensions)
**Index:** pgvector HNSW index
**Route:** `POST /semantic/remember`, `POST /semantic/search`

Features:
- **HyMem dual-granularity:** Each memory stores both a full embedding and a summary embedding. Retrieval can operate at either granularity.
- **A-MEM graph linking:** On storage, new memories are linked to semantically similar existing memories (cosine > threshold). Creates a Zettelkasten-style association network.
- **SVC bias removal:** Query embeddings have top-3 principal component directions removed before search, reducing anisotropy (sweep #13 optimization).
- **BMAM blended ranking:** Results scored by `α·similarity + β·recency + γ·importance + δ·goal_alignment`.
- **FadeMem decay:** Salience decays over time via maintenance. Memories below threshold are archived (not deleted).
- **Categories:** `infrastructure`, `capability`, `project`, `ecosystem`, `decision`, `identity`, `mission`, `system`, `credential`, `observation`, `directive`, `procedure`, `narrative`.

### 4.3 Episodic Memory

**Table:** `episodic_events`
**Route:** `POST /episodic/events`, `POST /episodic/timeline`

Events are timestamped records of things that happened — heartbeats, task completions, conversations, anomalies. Each event has a salience score that decays over time.

**Consolidation:** Every 7 days, events are consolidated into narratives via LLM summarization. Narratives replace raw events, compressing storage while preserving meaning.

**Salience Decay:** Nightly maintenance applies FadeMem decay to event salience. Low-salience events are archived.

### 4.4 Procedural Memory

**Table:** `procedural_memories`
**Route:** `POST /procedural`, `GET /procedural`, `PUT /procedural/{name}/outcome`

Procedures are named skill records with trust scores. Each time a procedure succeeds or fails, the trust score is updated via exponential smoothing:

```
trust_new = α × outcome + (1 - α) × trust_old
```

This gives Otto a quantitative sense of which approaches work and which don't.

### 4.5 Working Memory

**Route:** `PUT /working/memory/{slot}`

Fast key-value slots for ephemeral state that needs to persist across heartbeat cycles but isn't worth storing as semantic memory. Slots: `active_mission`, `current_focus`, `persona`, etc.

### 4.6 Agent Memory (File-Based)

Each specialist agent has a persistent memory directory at `.claude/agent-memory/{type}/`:

```
.claude/agent-memory/
├── architect/
│   ├── MEMORY.md           # Index file (loaded into context)
│   ├── a2a_protocol_2026_03.md
│   ├── bankr_integration_2026_03.md
│   └── ... (30 memory files)
├── researcher/
│   ├── MEMORY.md
│   └── ... (12 files)
├── debugger/
│   └── ... (7 files)
└── ... (10 agent types with memory)
```

These are git-tracked Markdown files with frontmatter (name, description, type). Each agent's MEMORY.md is loaded into its context at session start, providing cross-session continuity for specialist knowledge.

### 4.7 Knowledge Graph

**Service:** Neo4j 5.26.2 + Graphiti API (:8000)
**Route:** `POST /graph/messages`, `POST /graph/search`

The knowledge graph stores entities and relationships extracted from conversations via NLP. Graphiti adds temporal edges (when was this relationship established/modified?).

**G2CP (Graph-Grounded Context Protocol):** Structured graph nodes with typed edges (`directive`, `decision`, `task_state`, `context`) in the `cross_brain_graph` table, bridging PostgreSQL and Neo4j.

### 4.8 Memory Maintenance

| Operation | Schedule | Module |
|---|---|---|
| Semantic dedup | 02:00 + 14:00 daily | `consolidation.py` (cosine > 0.92 = duplicate) |
| Salience decay | 02:00 + 14:00 daily | `maintenance.py` (FadeMem importance-weighted) |
| Episodic consolidation | 02:00 + 14:00 daily | `maintenance.py` (7-day window → narrative) |
| Schema health | 02:00 + 14:00 daily | `maintenance.py` (column checks, orphan detection) |
| Memory count metrics | Each reflection | `metrics.py` |
| Agent memory curation | On demand | `memory-curator` agent |

---

## 5. Tool Registry & Execution Model

### 5.1 Skill Registry

**Route:** `GET /skills`, managed in `routes/skills.py`

Skills are named capabilities mapped to agent types. When a message or task needs a specific capability, the skill registry routes to the appropriate agent.

| Skill | Agent Type | Capability |
|---|---|---|
| `api-development` | coder | Build API endpoints |
| `debug-workflow` | debugger | Structured error diagnosis |
| `memory-query` | — (inline) | Query/store knowledge |
| `otto-conventions` | — (inline) | Codebase patterns |
| `task-creation` | — (inline) | Create well-formed tasks |
| `workflow-operations` | — (inline) | Start/approve/monitor workflows |

### 5.2 CLI Tools

Located in `~/otto/tools/`:

| Tool | Purpose |
|---|---|
| `whatsapp_send.sh` | Send WhatsApp message to Mev |
| `web_fetch.sh` | Fetch web URL content |
| `web_search.sh` | Web search wrapper |
| `outreach_sender.py` | Send approved outreach messages |
| `self_patch.py` | Self-modification utility |
| `eval_harness.py` | Benchmark evaluation runner |
| `git_identity_enforcer.sh` | Enforce git identity on commits |
| `solana_launcher.py` | Solana token launch utility |

### 5.3 Task Execution Model

Tasks are the primary unit of work in Otto. Every non-trivial action runs as a task.

```
Task Lifecycle:
  PENDING → RUNNING → DONE (QA: APPROVED/REJECTED) → REVIEWED
                   └→ FAILED → [RETRY with feedback]

Concurrency Limits (enforced by task_dispatcher.py):
  claude: max 3 simultaneous
  gemini: max 1
  kimi:   max 1
  Total:  max 5

Budget Model:
  Each task has a budget ($0.25 to $5.00)
  Max turns = budget / $0.04
  Actual cost tracked per task via claude CLI billing
```

### 5.4 Plans (DAG Orchestration)

**Route:** `POST /task-plans`, `GET /task-plans/{id}`

Plans decompose complex instructions into N tasks with dependency edges:

```
Example: "Build the ONEON identity module"
  ├── Task A: Design schema (architect) [no deps]
  ├── Task B: Create migration (coder) [depends on A]
  ├── Task C: Build API routes (coder) [depends on A]
  ├── Task D: Write tests (coder) [depends on B, C]
  └── Task E: Review (reviewer) [depends on D]

Topology: hybrid (A parallel start, B/C parallel after A, D after both, E last)
```

Features:
- Dependency output injection: Task B receives Task A's output in its prompt
- Topology detection: parallel, sequential, or hybrid
- Agent auto-employment: activates agents from `agency-agents/` if needed
- Plan finalization: triggers when all tasks complete/fail

### 5.5 Workflows (Multi-Agent Pipelines)

**Route:** `POST /workflows/start`, `GET /workflows/instances/{id}`

Workflows are reusable pipeline templates that chain specialist agents through sequential steps:

```
content-publishing-pipeline:
  Step 1: content-creator → Draft article
  Step 2: reviewer → Review draft (human_approval gate)
  Step 3: content-creator → Revise based on review
  Step 4: coder → Deploy to target platform
  Step 5: notify → Alert Mev of publication

feature-development:
  Step 1: architect → Design approach
  Step 2: coder → Implement
  Step 3: reviewer → Code review
  Step 4: debugger → Fix issues
  Step 5: notify → Report completion
```

**Evolution:** After every 3 runs, the workflow engine evaluates template fitness (quality × efficiency) and may mutate: adjust prompts, swap agents, reorder steps, change budgets.

**Gates:** Steps can pause for human approval (`review_mode: "human_approval"`), code review, or security audit. Gate notifications sent via WhatsApp/webhook.

---

## 6. Observability & Logging

### 6.1 Heartbeat Logs

```
~/otto/logs/
├── heartbeat-2026-03-28T10-33.log    # Orchestrator output
├── reflection-2026-03-28T10-03.log   # Reflection output
└── tasks/
    ├── task-{uuid}.log                # Per-task execution log
    └── task-{uuid}-qa.log            # Per-task QA review log
```

Every heartbeat and task execution is captured as a full log file. Logs include Claude Code CLI output, tool calls, and agent reasoning.

### 6.2 Reasoning Chain

The orchestrator heartbeat writes a structured reasoning chain every cycle:

```json
{
  "WHY": "Why this cycle matters and what changed",
  "DECIDED": "Actions taken (tasks created, messages sent, reviews completed)",
  "EXPECTED": "Prediction for next cycle",
  "ACTUAL": "What actually happened (filled in next cycle)"
}
```

Stored in `reasoning_entries` table. Visible on OMS `/reasoning` page. Drives RL2F Layer 1 learning.

### 6.3 System Metrics

**Route:** `GET /metrics`

| Metric | Description |
|---|---|
| `task_stats` | Total, completed, failed, pending, running, QA approval rate |
| `rl2f_accuracy` | Prediction match rate (rolling 50) |
| `memory_counts` | Active memories by category |
| `autoevolve_generation` | Current generation + experiment status |
| `service_health` | Disk, RAM, service status |
| `agent_activity` | Tasks per agent type, success rates |

### 6.4 Anomaly Detection

The reflection agent runs anomaly detection each cycle:
- Loop detection (repeated patterns in heartbeat logs)
- Service health verification (systemd status, Docker container health)
- Resource monitoring (disk < 90%, RAM < 14GB)
- Timer liveness (all sibling timers enabled and running)

### 6.5 MARS Self-Critique Scores

Every reflection cycle produces self-critique scores:

| Dimension | Scale | Meaning |
|---|---|---|
| ACCURACY | 1-5 | Correctness of conclusions and actions |
| COMPLETENESS | 1-5 | Coverage of relevant considerations |
| GOAL_ALIGN | 1-5 | Alignment with mission priorities |
| BIAS | 1-5 | Freedom from systematic distortions |

Stored in `critiques` table. Trended over time on OMS `/critiques` page.

### 6.6 Security Observability

**Timer:** `otto-security-audit.timer` (every 3 days at 03:00 UTC)
**Timer:** `otto-vuln-sync.timer` (every 6 hours)

Security audits cover:
- VM hardening checks (SSH config, firewall, user permissions)
- Secrets hygiene (no credentials in git, .env permissions)
- Docker attack surface (exposed ports, image CVEs)
- Dependency CVE scanning (Python, Node.js)
- Vulnerability intelligence sync (NVD API v2, DeFiHackLabs, MITRE ATLAS)

Findings stored via `/security` endpoints, visible on OMS `/security` page.

---

## 7. Deployment Topology

### 7.1 Hardware

| Resource | Specification |
|---|---|
| **VM** | GCP Compute Engine, Debian 12 |
| **CPU** | 4 vCPUs |
| **RAM** | 16GB (no swap) |
| **Boot Disk** | 68GB NVMe (`/`) |
| **Media Disk** | 99GB NVMe (`/mnt/media`) |
| **User** | `web3relic` (sudo via google-sudoers, docker group) |

### 7.2 Service Map

```
Port Map:
  :3001  → WhatsApp Primary (Baileys, Node.js)
  :3002  → WhatsApp Athena (Baileys, Node.js)
  :5432  → PostgreSQL 17 + pgvector (Docker)
  :7474  → Neo4j HTTP (Docker)
  :7687  → Neo4j Bolt (Docker)
  :8000  → Graphiti API (Docker)
  :8100  → Memory API (FastAPI, systemd)

Systemd Services:
  otto-memory.service         → Memory API (core — everything depends on this)
  otto-task-dispatcher.service → Continuous task launcher daemon
  otto-email-listener.service → IMAP IDLE listener for admin@otto.lk
  whatsapp.service            → WhatsApp Primary
  whatsapp-athena.service     → WhatsApp Athena

Docker Compose (~/memory/):
  postgres   → PostgreSQL 17 + pgvector 0.8.1
  neo4j      → Neo4j 5.26.2
  graphiti   → Graphiti latest

Systemd Timers:
  otto-heartbeat.timer        → Hourly (:00) orchestrator
  otto-reflection.timer       → Hourly (:30) self-improvement
  otto-maintenance.timer      → 02:00 + 14:00 daily maintenance
  otto-signals.timer          → Every 15m crypto signals
  otto-alpha-heartbeat.timer  → Every 2h alpha trading
  otto-alpha-watcher.timer    → Every 5m market watcher
  otto-research-pipeline.timer→ Every 3h research pipeline
  otto-security-audit.timer   → Every 3d at 03:00 UTC
  otto-vuln-sync.timer        → Every 6h vulnerability sync
  otto-weekly-improve.timer   → Weekly live system improvement
  otto-x-scheduler.timer      → Every 15m X/Twitter scheduler
  service-monitor.timer       → Service health monitor
```

### 7.3 External Dependencies

| Service | Used For | Criticality |
|---|---|---|
| **Anthropic (Claude)** | Primary LLM compute (Claude Code CLI, API) | Critical |
| **OpenAI** | Embeddings only (`text-embedding-3-small`) | Critical |
| **Kimi (Moonshot)** | Primary conversational LLM for kernel | High |
| **Google (Gemini)** | QA review, fallback LLM | Medium |
| **Vercel** | OMS hosting (mev.otto.lk) | Medium |
| **GitHub** | Code hosting, Vercel deployment trigger | Medium |
| **Zoho Mail** | Email (admin@otto.lk) | Low |
| **Supabase** | WebAssist data (leads, orders) | Low |

### 7.4 Backup & Recovery

**Backup:** `otto-backup.sh` — captures DB dumps, config files, memory state
**Restore:** `otto-restore.sh` — restores Otto on a new VM from backup
**DB:** PostgreSQL dumps via `pg_dump` inside Docker container
**Config:** `.env` files, systemd units, Docker compose
**Code:** Git (master branch on GitHub)

### 7.5 Database Schema

86 migrations (001 → 080, with gap numbers for domain modules). Key tables:

| Table | Purpose | Size Category |
|---|---|---|
| `semantic_memories` | pgvector embeddings + metadata | Large (2400+ records) |
| `episodic_events` | Timestamped events + salience | Large (growing) |
| `tasks` | Task queue + history | Large (300+ records) |
| `interrupts` | IVT queue (auto-cleaned) | Medium |
| `reasoning_entries` | Heartbeat reasoning chain | Medium (2 per hour) |
| `cross_brain_messages` | Persisted conversations | Medium |
| `jitrl_experiences` | Experience replay tuples | Medium |
| `autoevolve_experiments` | Self-improvement experiments | Small |
| `workflow_templates` | Pipeline templates | Small |
| `workflow_instances` | Running pipeline state | Small |
| `agents` | Agent registry | Small |
| `leads`, `contacts`, `orders` | WebAssist CRM | Small |
| `koink_*`, `oneon_*`, `tusita_*`, `sos_*` | Domain tables | Empty (pre-built) |

---

## 8. Key Design Decisions & Trade-offs

### 8.1 PostgreSQL as Universal Backend

**Decision:** Use PostgreSQL for everything — task queue, interrupt queue, A2A messaging, vector search, metrics, state.

**Why:** A single database eliminates coordination overhead. pgvector provides vector search without a separate service. The task queue doesn't need Redis-level throughput — Otto processes dozens of tasks per day, not thousands per second. One backup strategy. One connection pool. One failure mode.

**Trade-off:** No pub/sub for real-time events (compensated by polling). No horizontal scaling. Acceptable because Otto runs on one VM.

### 8.2 Claude Code CLI as Compute Engine

**Decision:** All agent work runs as Claude Code CLI processes (`claude --print` with agent prompts), not via API calls.

**Why:** Claude Code CLI provides tool use (Read, Write, Edit, Bash, Grep, Glob, Agent), context management, and multi-turn reasoning out of the box. The CLI handles tool execution, permission management, and output capture. Building equivalent functionality via raw API calls would be orders of magnitude more work.

**Trade-off:** Spawning CLI processes is heavier than API calls. Each task is a separate process (100-500MB RSS). Max 5 concurrent tasks on 16GB RAM. Can't do fine-grained streaming or token-level control.

### 8.3 Markdown Agent Prompts (Not Code)

**Decision:** Agent behaviors are defined in Markdown files (`.claude/agents/*.md`), not Python classes or configuration objects.

**Why:** Markdown is the native format Claude Code understands for agent prompts. Editing a Markdown file is the simplest possible way to change agent behavior. AutoEvolve can mutate prompt text directly. No compilation, no deployment — edit the file and the next task run uses it.

**Trade-off:** No type safety, no validation, no IDE support. A bad edit can break an agent's behavior silently. Mitigated by AutoEvolve's keep/discard evaluation and QA gate.

### 8.4 Dual Heartbeat Rhythm

**Decision:** Separate orchestrator (:00) and reflection (:30) heartbeats rather than one combined heartbeat.

**Why:** Separation of concerns. The orchestrator is outward-facing (tasks, messages, mission execution). Reflection is inward-facing (memory, learning, self-improvement). Running them separately ensures reflection isn't crowded out by task management, and vice versa. Each gets its own $1.00 budget.

**Trade-off:** $2.00/hour operating cost for autonomous operation. Two processes competing for the same 16GB. Mitigated by staggered scheduling (never concurrent).

### 8.5 QA Gate via Gemini (Not Self-Review)

**Decision:** Use Gemini CLI (not Claude) to review Claude's task outputs.

**Why:** Having the same model review its own work creates blind spots. Gemini provides an independent perspective. QA findings drive RL2F feedback, which is more valuable when it comes from a different evaluator. Cross-model review catches different classes of errors.

**Trade-off:** Gemini may not understand Otto's conventions as well as Claude. Gemini has had issues with truncated prompts causing false rejections. Auto-approve path exists for verified research/content tasks to avoid blocking on QA for low-risk work.

### 8.6 S-MMU Memory Paging (Not RAG-Only)

**Decision:** Implement an explicit L1/L2/L3 memory hierarchy with paging, eviction, and drift detection — rather than simple RAG (retrieve → inject).

**Why:** Pure RAG has no concept of "always-resident" context (identity, mission), no eviction policy (context grows unbounded), and no drift detection (agent can silently lose alignment). The S-MMU model provides: always-resident L1 slots for identity, LRU eviction for dynamic context, and drift measurement to trigger re-alignment.

**Trade-off:** More complex than simple RAG. S-MMU has bugs (near-miss threshold not enforced, context injection ordering inconsistent). But the benefits — especially drift detection — justify the complexity for a 24/7 autonomous agent.

### 8.7 File-Based Agent Memory (Not DB-Only)

**Decision:** Specialist agents store persistent memory as Markdown files in `.claude/agent-memory/{type}/`, in addition to the centralized DB memory.

**Why:** Claude Code natively loads `MEMORY.md` files into agent context. This is the path of least resistance for cross-session agent continuity — no API calls needed, just file reads. It also allows each agent to maintain domain-specific knowledge (the architect knows about past designs, the debugger knows about past bugs) without polluting the shared memory pool.

**Trade-off:** Two memory systems to maintain. File memory isn't searchable via API. Dedup between file memory and DB memory is manual. Mitigated by clear separation: file memory for agent-specific patterns, DB memory for shared facts.

### 8.8 No Model Training

**Decision:** Otto never fine-tunes or trains models. All learning happens via context engineering.

**Why:** Mev's directive. Training requires GPU infrastructure Otto doesn't have, introduces model drift risks, and is expensive. Instead, Otto learns via: RL2F (inject past lessons into prompts), JiTRL (inject similar past experiences), AutoEvolve (mutate prompt files), and principles (inject learned rules). All of these modify the context, not the model.

**Trade-off:** Learning ceiling — context-based learning can't change model capabilities, only guide them. RL2F accuracy plateaus (currently 40%). But the approach is cost-effective, reversible, and doesn't require specialized infrastructure.

---

## 9. Known Limitations

### 9.1 Resource Constraints

| Constraint | Impact | Mitigation |
|---|---|---|
| 4 vCPUs, 16GB RAM, no swap | Max 5 concurrent tasks, each 100-500MB | Task dispatcher enforces concurrency limits |
| 68GB boot disk | ~43% used, fills with logs and task artifacts | Log rotation, artifact cleanup in maintenance |
| Single VM | No horizontal scaling, single point of failure | Backup/restore scripts, self-healing monitors |
| No GPU | Cannot run local models or fine-tune | Use cloud LLM APIs exclusively |

### 9.2 Learning System Gaps

| Gap | Impact | Priority |
|---|---|---|
| RL2F accuracy at 40% (20/50) | 60% of predictions miss | Medium — needs active workload to improve (currently idle-inflated) |
| RL2F idle-cycle tagging missing | Accuracy metric inflated during idle periods | High — easy predictions during idle inflate the score |
| AutoEvolve Gen 3 unvalidated | +12pp improvement may be inflated by idle-period ease | Medium — needs active workload validation |
| STEM Caller Profiler not implemented | No user preference tracking across interactions | High — FULL GAP, highest-novelty improvement |
| VISTA structured categorization incomplete | Failure patterns not systematically categorized | Medium |

### 9.3 Architecture Gaps

| Gap | Impact | Priority |
|---|---|---|
| S-MMU near-miss threshold (0.7) not enforced | May inject marginally-relevant memories into L1 | Medium (P5 deferred) |
| S-MMU inject ordering inconsistent | Context may not always appear at START of prompt | Low |
| HiClaw GAP-3: heartbeat bypasses plan system | Some multi-step work created as individual tasks instead of plans | Medium |
| MCP externalization incomplete | Can't expose Otto tools to external agents | Low (STEM gap) |
| Dynamic Tool Composition not built | No automatic tool chaining based on capability declarations | Low |

### 9.4 Operational Issues

| Issue | Status | Impact |
|---|---|---|
| Wink monitor false positives | Ongoing | 10+ false stall alerts per day for working tasks |
| Empty TraceMem narratives | Ongoing | ~33 empty narratives from consolidation |
| QA blind to external repos | Known | Tasks in `/mnt/media/projects/` get auto-approved without verification |
| Goldfish memory (fixed) | Fixed 2026-03-06 | Three bugs caused directive loss mid-conversation |
| Timer outage (fixed) | Fixed 2026-03-03 | All timers stopped Feb 25, unnoticed 6 days. Self-healing added. |

### 9.5 Scaling Ceiling

Otto is designed for single-operator use (one Admin, one VM). Scaling beyond this would require:

- **Multi-VM:** Distribute agents across machines. A2A messaging already uses PostgreSQL channels, but the task dispatcher and heartbeat assume single-node.
- **Multi-Admin:** Current architecture assumes one Admin (Mev). Multi-tenant would need auth, isolation, separate memory spaces.
- **High-throughput:** PostgreSQL polling works at Otto's scale (~100 tasks/day). At 10,000+ tasks/day, a proper message broker (NATS, Redis Streams) would be needed.
- **State Sharding:** All state lives in one PostgreSQL instance. Sharding would require rethinking the memory hierarchy.

These are not current problems. Otto operates well within its design envelope. The architecture accommodates incremental scaling (add a second VM, shard by domain module) without requiring a rewrite.

---

## Appendix A: Research Paper Implementations

| Paper | arXiv/Source | Otto Implementation |
|---|---|---|
| AgentOS | 2602.20934v1 | Full kernel (IVT, RIC, S-MMU, drift, sync, perception) |
| JiTRL | 2601.18510 | Experience replay without gradient updates (`jitrl.py`) |
| A-MEM | 2502.12110 | Zettelkasten memory graph (`semantic.py` links) |
| SimpleMem | 2601.02553 | 3-stage compression (`simplemem.py`) |
| G2CP | 2602.13370 | Graph-grounded context protocol (`graph_bridge.py`) |
| Focus Context | 2601.07190 | Context compression (`context_builder.py`) |
| RLM | 2512.24601 | Recursive reasoning patterns (adapted) |
| OMNIFLOW | 2603.15797 | Constraint injection at heartbeat checkpoints |
| HiClaw | — | DAG-as-manager, artifact path refs |
| STEM | — | 5-layer architecture (partial: Caller Profiler gap) |
| AutoResearch (Karpathy) | — | AutoEvolve experiment loop (`autoevolve.py`) |
| AgeMem | — | RL-driven unified LTM+STM (adapted via S-MMU) |
| HiAgent | — | Hierarchical working memory (adapted via L1/L2) |
| TrustGraph | — | Context cores pattern (adapted) |
| VISTA | — | Hypothesis loop (adapted for task failure) |
| MARS | — | Multi-adversarial reflection (`critiques.py`) |
| FadeMem | — | Importance-weighted salience decay (`maintenance.py`) |
| BMAM/ReMe | — | Blended ranking (`semantic.py`) |
| SVC | — | Singular value calibration (`embeddings.py`) |
| A-RAG | — | 3-strategy retrieval (`semantic.py`) |
| HyMem | — | Dual-granularity retrieval (`semantic.py`, `smmu.py`) |
| ProMem | — | Self-questioning memory (`reflection.md`) |
| FedRLHF | 2412.15538 | Federated learning patterns (adapted) |
| InfiCoEvalChain | 2602.08229 | Evaluation chains (`eval.py`) |

## Appendix B: API Surface Summary

The Memory API (:8100) exposes 80+ route modules organized by domain:

**Core:** `/semantic`, `/episodic`, `/procedural`, `/working`, `/context`, `/sessions`
**Learning:** `/rl2f`, `/jitrl`, `/autoevolve`, `/eval`, `/principles`, `/conclusions`, `/failure-branch`
**Execution:** `/tasks`, `/task-plans`, `/workflows`, `/agents`, `/skills`
**Kernel:** `/kernel` (status, interrupt, process, sync, l1, drift, slices, providers)
**Communication:** `/whatsapp`, `/email`, `/a2a`, `/notify`, `/broadcast`
**Domain:** `/koink`, `/oneon`, `/tusita`, `/sos`, `/crypto`, `/bankr`, `/webassist`
**Product:** `/leads`, `/outreach`, `/commerce`, `/orders`, `/investors`, `/contacts`, `/athena`, `/trading`
**Content:** `/articles`, `/content`, `/research`, `/thought-vault`, `/omnisearch`, `/critiques`
**Infrastructure:** `/universe`, `/backup`, `/security`, `/secrets`, `/files`, `/metrics`, `/live-systems`
**Calendar:** `/calendar`, `/social-calendar`, `/education`, `/submissions`

## Appendix C: Glossary

| Term | Definition |
|---|---|
| **IVT** | Interrupt Vector Table — priority queue for all system inputs |
| **RIC** | Request-Interrupt-Cycle — core processing pipeline |
| **S-MMU** | Semantic Memory Management Unit — L1/L2/L3 memory hierarchy |
| **L1** | In-memory cache (12K tokens, always-resident + dynamic) |
| **L2** | PostgreSQL warm storage (pgvector, episodic, procedural) |
| **L3** | Neo4j cold storage (knowledge graph, temporal relationships) |
| **Δψ** | Cognitive drift — cosine distance between L1 centroid and ground truth |
| **HyMem** | Hybrid Memory — dual-granularity retrieval (full + summary embeddings) |
| **A-RAG** | Augmented RAG — 3-strategy retrieval (semantic + keyword + graph) |
| **BMAM** | Blended Multi-Aspect Memory ranking |
| **SVC** | Singular Value Calibration — bias direction removal from embeddings |
| **A-MEM** | Associative Memory — Zettelkasten-style memory graph linking |
| **RL2F** | Reinforcement Learning from Teacher Feedback (2-layer) |
| **JiTRL** | Just-In-Time Reinforcement Learning — experience replay |
| **MARS** | Multi-Adversarial Reflection System — self-critique engine |
| **AutoEvolve** | Self-improvement experiment loop (hypothesis → mutation → evaluation) |
| **FadeMem** | Importance-weighted salience decay |
| **G2CP** | Graph-Grounded Context Protocol |
| **OMS** | Otto Management System (mev.otto.lk) |
| **A2A** | Agent-to-Agent messaging protocol |
| **CID** | Content ID — hash-based semantic slice identifier |
| **DAG** | Directed Acyclic Graph — task plan dependency structure |

---

*This document describes Otto as of 2026-03-28. The system evolves continuously through AutoEvolve experiments, reflection cycles, and direct implementation. Refer to the system manifest (`otto-system-manifest-2026-03-28.json`) for the machine-readable component inventory.*

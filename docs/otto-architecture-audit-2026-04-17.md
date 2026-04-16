# Otto Architecture Audit — 2026-04-17

## Executive Summary

Otto is a **sovereign autonomous intelligence system** built on a cognitive kernel architecture (AgentOS, arXiv 2602.20934v1). It combines a 5-phase Reasoning Interrupt Cycle (RIC), 3-level semantic memory hierarchy (S-MMU), 5 self-improvement learning systems, DAG-based task orchestration, and multi-agent workflow pipelines — all served through a single FastAPI process on port 8100.

**Scale**: 95 DB migrations, 62 mounted routers (~400+ endpoints), 22 specialist agents, 14+ systemd units, ~15K lines of Python + 1.5K lines of bash orchestration.

---

## 1. Architecture Overview

```
                    +------------------+
                    |   Mev (Admin)    |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        WhatsApp:3001  OMS (web-next)  Email (Zoho)
        Athena:3002    mev.otto.lk     admin@otto.lk
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    |  Gateway Layer   |
                    |  (classifiers,   |
                    |   persistence,   |
                    |   routing)       |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  AgentOS Kernel  |
                    |  IVT -> RIC ->   |
                    |  S-MMU -> LLM    |
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
        +-----v----+  +-----v-----+  +-----v------+
        | Task      |  | Workflow  |  | Learning   |
        | Queue     |  | Engine   |  | Systems    |
        | (DAG)     |  | (pipes)  |  | (5 loops)  |
        +-----------+  +----------+  +------------+
              |              |              |
              +--------------+--------------+
                             |
              +--------------+--------------+
              |              |              |
        PostgreSQL     Neo4j/Graphiti    MCP Server
        + pgvector     Knowledge Graph   (SSE :8100)
        :5432          :7474/:7687
```

---

## 2. Core Components Inventory

### 2.1 Memory API (FastAPI on :8100)

**Entry**: `memory/api.py`  
**Framework**: FastAPI + APScheduler + SlowAPI (rate limiting)  
**Startup**: asyncpg pool init, kernel provider loading, agent registry, Phase 5 hooks, nightly maintenance scheduler, OTel instrumentation (optional)

**62 Mounted Routers** (grouped by domain):

| Domain | Routers | Endpoint Count | Key Routes |
|--------|---------|---------------|------------|
| **Memory** | sessions, episodic, semantic, procedural, context, working, maintenance, consolidation, omnisearch | ~45 | `/semantic/remember`, `/semantic/arag_search`, `/context/briefing` |
| **Knowledge Graph** | graph, graph_nodes | ~8 | `/graph/messages`, `/graph/search`, `/graph/nodes` |
| **Kernel** | kernel_routes, gateway_router | ~25 | `/kernel/status`, `/kernel/interrupt`, `/gateway/incoming` |
| **Tasks** | tasks, task_plans, plans, workspace | ~38 | `/tasks`, `/task-plans`, `/tasks/route`, `/tasks/hindsight` |
| **Workflows** | workflows | ~24 | `/workflows/start`, `/workflows/{id}/gate/resolve` |
| **Learning** | rl2f, jitrl, autoevolve, principles, eval, reasoning, failure_branch | ~55 | `/rl2f/`, `/jitrl/optimize`, `/autoevolve/insights` |
| **Communication** | whatsapp, email, notify, broadcast, a2a, a2a_standard | ~35 | `/whatsapp/incoming`, `/email/send`, `/a2a/send` |
| **Content** | articles, content, critiques, social_calendar, calendar_routes, landing_pages | ~55 | `/content`, `/articles`, `/landing-pages` |
| **Business** | webassist, leads, outreach, orders, contacts, services, investors | ~50 | `/webassist`, `/leads`, `/outreach` |
| **Ecosystem** | universe, koink, oneon, tusita, sos, submissions, thought_vault, athena | ~80 | `/universe`, `/oneon`, `/koink` |
| **Operations** | metrics, agents, skills, files, backup, security, secrets, live_systems, education | ~60 | `/agents/activity`, `/secrets`, `/backup` |
| **Crypto** | bankr, crypto, commerce, virtuals, trading | ~40 | `/crypto/parse`, `/bankr/trade` |

**Total**: ~400+ HTTP endpoints

### 2.2 Pydantic Models (`memory/models.py`)

**Core Memory**: SessionStart/End/Out, EpisodicEventCreate/Out, SemanticMemoryCreate/Out, ProcedureCreate/Out, ContextBriefing  
**Kernel**: InterruptCreate/Out, SemanticSlice, CognitiveSnapshotOut, KernelStatusOut, ProviderConfigOut  
**Tasks**: TaskCreate/Out, DecomposeRequest, HandoffRequest, MevTaskUpdate, TaskRunResponse  
**Planning**: TaskPlanRequest/Response, ApproachCandidate, ExecutionStrategy, PlanCacheStore/Match  
**Evaluation**: HeartbeatMetricCreate/Out, ReasoningEntryCreate/Out, PreflectResult/Out  
**Learning**: RL2FFeedbackCreate/Out, TaskRetryFeedbackCreate/Out, JitRLExperienceCreate/Out, JitRLOptimizeRequest/Response  
**Search**: ARAGSearchRequest/Response, SemanticForgetRequest, SemanticMergeRequest, SimpleMemSearchResponse  
**Collaboration**: DecisionProposalCreate/Out, CrossBrainNote  

### 2.3 Configuration (`memory/config.py`)

**Settings (Pydantic BaseSettings, loads from ~/memory/.env)**:

| Category | Key Settings |
|----------|-------------|
| **PostgreSQL** | user, password, db, host, port, DSN |
| **Embeddings** | openai_api_key, local_embedding_enabled (all-MiniLM-L6-v2, 384-dim), SVC calibration |
| **Kernel** | kernel_enabled, l1_capacity_tokens (12K), drift_threshold (0.3), sync_interval_minutes (60) |
| **LLM Providers** | Kimi (primary), Claude CLI (fallback), Gemini (secondary) |
| **Crypto** | Hyperliquid wallets, Alchemy, 0x, CoinGecko, Birdeye APIs |
| **Feature Gates** | koink_enabled, oneon_enabled, tusita_enabled, sos_enabled (all False) |
| **External** | Graphiti URL, WhatsApp gateway, Neo4j, Supabase |
| **Security** | web_auth_token, investor_password, vault_master_key (Fernet), mcp_token |
| **OTel** | otel_enabled, service_name, export_endpoint, trace_retention_days (30) |
| **Gates** | gate_whatsapp_enabled, gate_webhook_urls, gate_webhook_secret |

### 2.4 Embeddings (`memory/embeddings.py`)

- **Primary**: OpenAI text-embedding-3-small (1536-dim)
- **Fallback**: sentence-transformers all-MiniLM-L6-v2 (384-dim, local)
- **SVC**: Singular Value Calibration — removes top-k PCA directions to reduce anisotropy (fitted offline, 1hr cache)
- **Dual column**: `embedding_hv` (1536) + `embedding_local` (384) — `emb_col()` returns correct one based on active provider

---

## 3. AgentOS Kernel

### 3.1 File Map

| File | Role |
|------|------|
| `kernel/reasoning_kernel.py` | Kernel lifecycle API (start/stop/ensure) |
| `kernel/scheduler.py` | CognitiveScheduler — main interrupt dispatch loop |
| `kernel/ivt.py` | Interrupt Vector Table — priority queue (atomic SQL dequeue) |
| `kernel/ric.py` | 5-phase RIC: SAVE -> LOAD -> PROCESS -> ALIGN -> POST |
| `kernel/smmu.py` | 3-level memory pager (L1/L2/L3) |
| `kernel/slicing.py` | CID-based semantic boundary detection |
| `kernel/drift.py` | Cognitive drift detection (1 - cosine(L1, ground_truth)) |
| `kernel/sync.py` | Cognitive Sync Pulse (importance recalc, consolidation) |
| `kernel/perception.py` | LLM output validation + correction |
| `kernel/provider.py` | Pluggable LLM backend registry (Kimi, Claude CLI) |
| `kernel/types.py` | InterruptType enum (10 signals), Priority |
| `kernel/state.py` | CognitiveState snapshot serialization |
| `kernel/agents.py` | Multi-agent registry + routing |
| `kernel/masking.py` | Interrupt deferral during critical sections |
| `kernel/hooks.py` | Event listener registry (concurrent, fault-isolated) |

### 3.2 Message Processing Pipeline

```
Message In -> Gateway (classify channel, admin check)
  |
  v
IVT Enqueue (priority from InterruptType, auto-route to agent)
  |
  v
CognitiveScheduler (asyncio.Event wait, atomic dequeue)
  |
  v
RIC Phase 1: SAVE (snapshot L1 -> cognitive_snapshots)
  |
  v
RIC Phase 2: LOAD (S-MMU paging)
  - Always-resident: purpose, priorities, directives, identity (~2K tokens)
  - Dynamic slices: similarity-ranked by centroid (weighted: 0.4 sim + 0.25 importance + 0.15 access + 0.2 recency)
  - Threshold floor: skip slices below 0.7 similarity
  - Position bias: anchor top slice at END
  - Token budget: fill L1 capacity (12K tokens)
  |
  v
RIC Phase 3: PROCESS (LLM call)
  - Load 17-msg WhatsApp history
  - Extract confirmed facts (pattern-match, no LLM)
  - Build system prompt (context + facts + channel voice)
  - Inject document text if attached (<8K chars)
  - provider_chat() with priority-based fallback
  |
  v
RIC Phase 4: ALIGN (perception validation)
  - Check: empty, code fence, role confusion, privacy leak
  - Correct via LLM (1 retry max)
  |
  v
IVT Complete -> Response Delivered
  |
  v
Phase 5: POST-PROCESSING (async, non-blocking)
  Group 1 (concurrent):
    - Episodic event log
    - Persist messages + compute embeddings
    - Graphiti knowledge graph ingest
    - Pending question matching
    - Decision proposal matching
  Group 2 (after Group 1):
    - Lesson extraction (detect Mev corrections)
    - Directive extraction (detect Mev directives)
    - Reactive dispatch (classify -> task/plan/workflow/stop)
    - Drift measurement
    - Thought Vault capture
```

### 3.3 Interrupt Types

| Signal | Priority | Trigger |
|--------|----------|---------|
| SIG_MSG_ADMIN | 2 | Message from Mev |
| SIG_PERCEPTION_ERR | 1 | LLM output failed alignment |
| SIG_DIRECTIVE | 2 | Mev directive detected |
| SIG_CONTEXT_FULL | 3 | L1 capacity reached |
| SIG_SYNC_DRIFT | 3 | Drift > threshold |
| SIG_TASK_FAILED | 3 | Task errored |
| SIG_TASK_COMPLETE | 4 | Task finished |
| SIG_PROPOSAL_RESOLVED | 4 | Mev resolved decision |
| SIG_HEARTBEAT | 5 | Hourly orchestrator |
| SIG_MAINTENANCE | 7 | Nightly maintenance |

### 3.4 Gateway Layer

| File | Role |
|------|------|
| `gateway/handler.py` | Core message router (admin/athena/contact) |
| `gateway/routes.py` | `/gateway/incoming`, `/gateway/ws`, `/gateway/health` |
| `gateway/classifiers.py` | LLM-based dispatch, plan, stop, lesson, directive classifiers |
| `gateway/persistence.py` | Store messages + embeddings, graph ingest, resolve pending |
| `gateway/contact_handler.py` | Non-admin WhatsApp routing |
| `gateway/athena_handler.py` | Separate LLM line (no tools, no kernel) |

### 3.5 Peripherals

| Peripheral | Source | Purpose |
|-----------|--------|---------|
| WhatsApp | `peripherals/whatsapp.py` | WhatsApp -> IVT interrupt |
| Web | `peripherals/web.py` | WebSocket -> IVT interrupt |
| Scheduler | `peripherals/scheduler.py` | Task completion/failure -> interrupt |

---

## 4. Task Orchestration

### 4.1 Three-Tier Execution Model

```
Tier 1: Single Task
  task_runner.sh -> Claude CLI -> output -> QA -> complete

Tier 2: Task Plan (DAG)
  Instruction -> classify_for_plan() -> decompose -> N tasks with edges
  -> DAG executor runs tasks as dependencies clear
  -> plan finalizes when all tasks complete

Tier 3: Workflow (Multi-Agent Pipeline)
  Template -> instance -> step 1 (agent A) -> step 2 (agent B) -> ...
  -> output pipes between steps via {prev_output}
  -> gates (human/DAO approval) between steps
  -> auto-eval scores completed workflows
```

### 4.2 Task Runner (`task_runner.sh`, 1507 lines)

**37-step execution pipeline**:

1. Init + logging
2. Fetch task spec from API
3. Decomposition gate (block if needs decomposition)
4. Tool RAG (auto-select specialist agent)
5. Progressive loading (priority -> effort level)
6. AdaptOrch routing (strategy, model, budget, timeout overrides)
7. RL2F feedback injection (if retry)
8. Chain-of-Hindsight (past successes/failures)
9. Procedure memory lookup (trust >= 0.40)
10. Semantic memory enrichment (A-RAG search)
11. Git preflight (branch, commits, dirty files)
12. Progress file recovery (resume from previous attempt)
13. A2A channel detection (peer messaging)
14. Full prompt assembly (all context blocks)
15. CLI spawning (claude/gemini/kimi with flags)
16. Timeout wrapper + Wink monitor
17. Output capture + exit code handling
18. Rate limit detection
19. Artifact path refs (HiClaw GAP-2: >2KB -> file + summary)
20. NEEDS_MEV_INPUT extraction -> decision proposals
21. SOFAI-LM metacognitive self-check (Gemini Flash scores 1-10)
22. Auto-restart Memory API if memory/*.py modified
23. Task completion report to API
24. JitRL experience ingestion
25. Procedure outcome recording
26. QA runner launch
27. Smart inline retry (up to 2 retries, mode-specific: timeout/error/empty/qa_rejected)
28. Progress file cleanup
29. APC plan cache
30. WhatsApp completion notification
31. Kernel completion report

**CLI Backends**: claude (primary), gemini (experimental), kimi (experimental)  
**Key Flags**: `--print --dangerously-skip-permissions --model {M} --fallback-model {F} --max-turns {T} --max-budget-usd {B} --effort {E} --no-session-persistence`

### 4.3 Task Dispatcher (`task_dispatcher.py`, 240 lines)

- **Stateless polling**: 15-second interval
- **Queries**: `/tasks/queue/status` + `/tasks?status=pending&limit=20`
- **Concurrency**: Respects per-CLI capacity (claude=3, gemini=1, kimi=1)
- **Rate limit awareness**: Checks `/kernel/providers/rate-limited` + sentinel file
- **Backoff**: 30s per CLI type on 429
- **Graceful shutdown**: SIGTERM/SIGINT handler

### 4.4 Task Plans (`memory/routes/task_plans.py`)

- **Plan creation**: POST `/task-plans` with items + dependency edges
- **Topology detection**: parallel / sequential / hybrid from edge structure
- **DAG executor**: Atomic claim (pending -> running), dependency verification before launch
- **Agent auto-employment**: Copy specialist agents from agency-agents/ on demand
- **Workflow spawning**: Plan items with `workflow_template` create workflow instances
- **Completion cascade**: Each task completion -> `execute_plan()` -> find newly unblocked tasks

### 4.5 Workflow Engine (`memory/routes/workflows.py`)

- **Templates**: Reusable step definitions with agent_type, prompt_template, review_mode
- **Step execution**: Creates task per step, pipes output via `{prev_output}` / `{step_N_output}`
- **Gates**: Pre/post-step approval gates (human or DAO), timeout + escalation
- **Failure modes**: retry_once, pause, skip, fail_workflow
- **Auto-eval**: Post-workflow evaluator scores fitness dimensions
- **Evolution**: Template mutation based on fitness scores (every 3 runs)

---

## 5. Dual Heartbeat Rhythm

### 5.1 Orchestrator (`heartbeat.sh`, hourly at :00)

1. Concurrency lock + self-healing (check sibling timers)
2. Rate limit check
3. Unified context fetch (`/kernel/context?role=orchestrator`)
4. Run Claude CLI with `--agent heartbeat --model opus`
5. Public site health checks (6 domains, alert after 2 failures)
6. Auto-repair scan (detect repeat error patterns)
7. Unified post-processing (lessons, drift)
8. Log cleanup (7-day retention)

**Agent role**: Mission execution — review tasks, process Mev input, create/launch tasks, communicate with Mev. ReflAct framework. Budget gate ($0.10 floor).

### 5.2 Reflection (`reflection.sh`, hourly at :30)

1. Concurrency lock + rate limit check
2. Run Claude CLI with `--agent reflection --model opus`
3. Log cleanup

**Agent role**: Self-improvement — reconcile state, consolidate memory, review agent performance, audit mission alignment, create improvement tasks. MARS adversarial synthesis.

### 5.3 Other Scheduled Agents

| Timer | Schedule | Agent | Purpose |
|-------|----------|-------|---------|
| otto-strategy | Daily 05:00 IST | strategist | Strategic planning + task dispatch |
| otto-alpha-heartbeat | Every 2h | alpha_heartbeat | Solana smart money scanner |
| otto-alpha-watcher | Every 5m | - | Live alpha signal watcher |
| otto-research-pipeline | Every 3h | - | Multi-stage research |
| otto-security-audit | Every 3d at 03:00 | security-audit | VM hardening, CVE scan |
| otto-vuln-sync | Every 6h | - | Vulnerability intel sync |
| otto-signals | Every 15m | - | Signal publishing |
| otto-maintenance | 02:00 + 14:00 | - | Memory maintenance |
| otto-weekly-improve | Sunday 03:00 | - | Weekly self-improvement |
| otto-dns-healer | Every 1h | - | DNS auto-healing |

---

## 6. Learning Systems (5 Feedback Loops)

### 6.1 RL2F — Reinforcement Learning from Teacher Feedback

**Location**: `memory/routes/rl2f.py`  
**Tables**: `rl2f_feedback`, `task_retry_feedback`

**Layer 1 (Heartbeat-level)**: Mev feedback on Otto's cycle decisions. Abhidharma mental factors (sati/amoha). Outcome tracking: matched/partial/miss. Training pipeline extraction.

**Layer 2 (Task-level)**: QA rejection -> structured feedback -> retry prompt injection. Metrics: retry success rate with vs without feedback.

### 6.2 JitRL — Just-In-Time Reinforcement Learning

**Location**: `memory/routes/jitrl.py`  
**Paper**: arXiv:2601.18510

**Mechanism**: Non-parametric experience buffer. At inference: embed context -> retrieve k similar past states -> compute advantage per action_type -> KL-constrained policy weight. Returns ranked action recommendations. No gradient updates needed.

### 6.3 AutoEvolve — Self-Improvement Experiments

**Location**: `memory/routes/autoevolve.py`  
**Inspired by**: karpathy/autoresearch

**Mechanism**: Hypothesis-driven changes to system files (agent prompts, thresholds, budgets). Track metric_before/metric_after over evaluation cycles. Keep/discard/rollback decisions. Generation counter tracks evolution depth.

### 6.4 MARS Principles — Rule Extraction & Confidence

**Location**: `memory/routes/principles.py`

**Mechanism**: Extracted from outcomes, applied to new tasks. Confidence: +0.05 on application, -0.10 on violation. Top 5 active principles injected into task context.

### 6.5 PreFlect — Prospective Failure Prediction

**Location**: `memory/routes/tasks.py` (lines 1468+)  
**Paper**: arXiv:2602.07187

**Mechanism**: Match upcoming task against failure pattern database (4 patterns from 11 historical failures). Risk score 0-1. Suggest modifications (increase timeout, split task, etc.). Gate high-risk tasks before execution.

---

## 7. Storage Architecture

### 7.1 PostgreSQL + pgvector (:5432)

**95 migrations** covering:

| Migration Range | Domain |
|----------------|--------|
| 001-009 | Core memory, vector search, hierarchical memory |
| 010-015 | Task queue, core memory, procedures |
| 016-025 | MARS principles, agent tuning, education, note links, cross-brain graph |
| 026-035 | RL2F, JitRL, HyMem |
| 036-045 | Task routing, LATS planning, AgentOS kernel |
| 046-060 | AutoEvolve, workflows, lead tracking |
| 061-075 | Onchain tasks, thought vault, workflow gates, reflection versions |
| 076-095 | Diff versioning, A2A messaging, BM25 hybrid search, local embeddings, landing pages |

**Key Tables**: `semantic_memories`, `episodic_events`, `tasks`, `interrupt_queue`, `workflow_templates`, `workflow_instances`, `rl2f_feedback`, `jitrl_experience`, `autoevolve_experiments`, `principles`, `whatsapp_messages`, `core_memory`, `semantic_slices`, `semantic_page_table`, `cognitive_snapshots`, `kernel_drift_log`, `a2a_messages`

### 7.2 Neo4j + Graphiti (:7474/:7687/:8000)

- Temporal knowledge graph
- Ingested from: conversations, episodic consolidation, semantic memories
- Searched via: `/graph/search` (Graphiti API proxy)
- Memory limit: 2GB Neo4j + 1.5GB Graphiti

### 7.3 Docker Compose Stack

| Service | Image | Port | Memory |
|---------|-------|------|--------|
| postgres | pgvector/pgvector:pg17 | :5432 | 1GB |
| neo4j | neo4j:5.26.2 | :7474/:7687 | 2GB |
| graphiti | zepai/graphiti:latest | :8000 | 1.5GB |

**Total Docker memory**: ~4.5GB of 16GB available

---

## 8. Interface Layer

### 8.1 WhatsApp (Main — :3001)

- **Library**: Baileys (Node.js WhatsApp client)
- **Flow**: Incoming msg -> dedup (5-min window) -> parse type -> transcribe audio (Deepgram nova-2) -> save documents -> POST `/gateway/incoming` -> receive reply -> send back
- **Features**: Multi-type support (text, document, image, video, audio, sticker, contact, location), 30-min idle auto-reconnect, health endpoint

### 8.2 WhatsApp (Athena — :3002)

- **Separate account**: +94743768830
- **Differences**: QR management for OMS, no audio transcription, account="athena" metadata routing
- **Routing**: Gateway detects `metadata.account="athena"` -> athena_handler (pure LLM, no kernel)

### 8.3 OMS Web Interface (mev.otto.lk)

- **Framework**: Next.js 16.1.1, React 19, shadcn/ui, Tailwind CSS 4
- **Pages**: WhatsApp QR, WebAssist (leads/prospects/orders/landing-pages/pipeline), Research, Editor, Secrets, Files, Settings, Context History
- **API connection**: Hooks + lib connecting to localhost:8100
- **Static export**: Built to `out/` directory

### 8.4 Email (admin@otto.lk via Zoho)

- **SMTP**: smtppro.zoho.com:465 (SSL)
- **IMAP**: imappro.zoho.com:993 (SSL)
- **16 endpoints**: send, inbox, reply, search, threads, folders, auth (magic link + OTP)

---

## 9. Authentication & Security

| Mechanism | Scope | Implementation |
|-----------|-------|----------------|
| **Rate limiting** | All endpoints | SlowAPI 120 req/min per IP |
| **Investor auth** | `/investors/*` | HMAC-SHA256 token, 24h TTL |
| **Email OTP** | `/email/auth/*` | Single-use tokens, 24h lifetime |
| **MCP bearer** | `/mcp/*` | X-MCP-Token header (dev: open) |
| **Secrets vault** | `/secrets/*` | Fernet AES-256 encryption + audit log |
| **WebSocket auth** | `/gateway/ws` | Bearer token in connection params |
| **Network isolation** | All ports | Bound to 127.0.0.1 (Docker, services) |
| **No API key auth** | Most endpoints | Relies on private deployment |

---

## 10. MCP Server

- **Transport**: SSE at `/mcp/sse` (in-process, no new port)
- **15 tools**: 5 memory, 4 tasks, 2 communication, 2 system, 2 content
- **4 resources**: context briefing, constitution, personality, queue state
- **3 prompt templates**: research_task, content_pipeline, bug_report
- **Auth**: Bearer token middleware (constant-time comparison)

---

## 11. Key Architectural Patterns

### 11.1 Interrupt-Driven Processing
All work enters via IVT (10 signal types). Atomic SQL dequeue (`FOR UPDATE SKIP LOCKED`) prevents lost interrupts. Priority-based ordering ensures Mev messages (P2) preempt background tasks (P7).

### 11.2 Token-Budgeted Context
S-MMU L1 has fixed 12K token capacity. Weighted scoring (0.4 similarity + 0.25 importance + 0.15 access + 0.2 recency) determines what's paged in. Similarity threshold (0.7) prevents context rot. Position bias mitigation anchors best slice at end.

### 11.3 Progressive Context Loading
Task priority maps to effort level (low/medium/high). Low-effort tasks skip semantic enrichment, procedures, hindsight. High-effort tasks get full context injection. Prevents budget waste on simple tasks.

### 11.4 Reactive Dispatch
Phase 5 post-processing classifies Mev's messages for implicit actions. Single messages can create tasks, plans (DAG), or workflows. Dedup guard prevents duplicate tasks (similarity > 0.4 within 2h).

### 11.5 Self-Improvement Loops
Five independent feedback mechanisms operate at different timescales:
- **RL2F**: Per-heartbeat + per-task feedback (hours)
- **JitRL**: Non-parametric advantage estimation (minutes)
- **AutoEvolve**: Hypothesis-driven experiments (days)
- **MARS Principles**: Rule extraction + confidence (weeks)
- **PreFlect**: Failure pattern matching (pre-task)

### 11.6 Fault Isolation
Phase 5 hooks wrapped in try/except (one failing hook doesn't break others). Provider fallback chain (Kimi -> Claude CLI). Smart inline retry (up to 2 retries with mode-specific context). Progress files survive task timeouts.

### 11.7 DAG Orchestration
Task plans decompose instructions into dependency graphs. Atomic claim prevents double-launch. Agent auto-employment activates specialists on demand from 139-agent pool. Workflow steps pipe output between agents.

---

## 12. Resource Profile

| Resource | Allocation | Usage |
|----------|-----------|-------|
| **CPU** | 4 vCPUs | Shared: API, Docker, CLI agents |
| **RAM** | 16GB (no swap) | Docker: ~4.5GB, API: ~500MB, CLI agents: variable |
| **Boot disk** | 68GB NVMe | ~30% used |
| **Media disk** | 99GB NVMe | ~3% used |
| **Concurrent tasks** | Max 5 (claude=3, gemini=1, kimi=1) | Dispatcher-managed |
| **Heartbeat cost** | ~$2/day (opus x2/hour) | Budget-gated |
| **Task cost** | Variable ($0.10 - $5.00) | AdaptOrch-optimized |

---

## 13. Data Flow Diagram

```
Mev Input                               Scheduled Triggers
(WhatsApp/Web/Email)                    (systemd timers)
       |                                       |
       v                                       v
  Gateway Router                      Heartbeat/Reflection
  (classify, persist)                 (context fetch, plan)
       |                                       |
       v                                       v
  IVT Enqueue                          Task Creation
  (priority queue)                     (via API)
       |                                       |
       v                                       v
  RIC Processing                      Task Dispatcher
  (SAVE->LOAD->PROCESS->ALIGN)        (15s poll, launch)
       |                                       |
       v                                       v
  Response Delivery                   Task Runner
  (WhatsApp/WebSocket)                (37-step pipeline)
       |                                       |
       v                                       v
  Phase 5 Post-Processing             CLI Agent Execution
  (10 async hooks)                    (claude/gemini/kimi)
       |                                       |
       +----> Task/Plan/Workflow               |
       |      Creation (reactive)              |
       |                                       v
       +----> Learning System             QA + Retry
       |      Ingestion                   (qa_runner.sh)
       |      (RL2F, JitRL)                    |
       |                                       v
       +----> Memory Persistence          Completion Report
              (semantic + graph)          (API + WhatsApp + JitRL)
```

---

## 14. Notable Design Decisions

| Decision | Choice | Alternative Considered | Rationale |
|----------|--------|----------------------|-----------|
| **Single process** | All routes in one FastAPI app | Microservices | Simplicity on 4 vCPU, shared DB pool |
| **Interrupt-driven** | IVT with priority queue | Polling/webhook | OS-inspired, deterministic ordering |
| **Dual embeddings** | OpenAI (1536) + local (384) | OpenAI only | Fallback when API down, cost saving |
| **Provider fallback** | Kimi primary, Claude CLI fallback | Single provider | Reliability + cost optimization |
| **Task runner in bash** | 1507-line shell script | Python | Direct CLI invocation, process control |
| **S-MMU token budget** | Fixed 12K tokens | Dynamic | Predictable latency, prevents runaway |
| **Phase 5 async** | Background hooks after response | Blocking | Response latency < 3s target |
| **DAG over linear** | Task plans with dependency edges | Simple sequential | Parallel execution, branch + merge |
| **5 learning systems** | Independent loops at different timescales | Single RL loop | Diverse signal sources, multi-horizon |

---

## 15. Identified Patterns & Conventions

1. **Route files are self-contained**: Each route file handles its own DB queries, no shared ORM layer
2. **Semantic memory as universal store**: Most systems log to `semantic_memories` with category tags
3. **WhatsApp as primary notification**: All systems use `whatsapp_send.sh` for alerts
4. **Feature gating via config**: `koink_enabled`, `sos_enabled` etc. in settings
5. **Episodic logging for observability**: Key events logged to `episodic_events` table
6. **Procedure trust scores**: Approach memory with convergent trust (success +0.05, failure -0.10)
7. **Decision proposals for escalation**: NEEDS_MEV_INPUT markers extracted from task output
8. **Artifact path refs**: Large outputs (>2KB) written to filesystem, replaced with `[ARTIFACT: path]`
9. **Progress file recovery**: `.otto-progress-{id}.md` files survive task timeouts for retry

---

*Audit performed 2026-04-17 by architect agent. Covers full Otto codebase at /home/web3relic/otto/.*

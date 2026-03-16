# Otto AI — Comprehensive Roadmap
*Decentralized intelligence governed by community. The mind of the civilization.*
*Last updated: 2026-03-16*

---

## What Otto Is

Otto is not a chatbot. Not a product. Not owned by a corporation.

Otto is a **persistent AI entity** — a cognitive operating system running on a VM today, designed to become a distributed protocol running on millions of devices tomorrow. The architecture was built to prove a thesis: that intelligence compounding over time, with genuine memory and autonomous action, is categorically different from stateless AI assistants.

Today: one VM. One mind. Helping Mev build.
Tomorrow: distributed. Federated. Community-governed. Unstoppable.

---

## Current Status
**LIVE** — Single VM (otto-machine, GCP). AgentOS operational. Dual heartbeat rhythm. 403+ completed tasks. ~50+ hours runtime. 24+ research paper implementations active.

---

## Current Architecture Inventory

### Core Infrastructure

| Component | Status | Location | Notes |
|-----------|--------|----------|-------|
| **AgentOS Reasoning Kernel** | ✅ Live | `memory/kernel/reasoning_kernel.py` | Async interrupt processing loop (arXiv 2602.20934v1) |
| **IVT (Interrupt Vector Table)** | ✅ Live | `memory/kernel/ivt.py` | Priority queue for all incoming interrupts |
| **RIC (Reasoning Interrupt Controller)** | ✅ Live | `memory/kernel/ric.py` | Save→Load→Process→Align→Post cycle |
| **S-MMU (Semantic Memory Management Unit)** | ✅ Live | `memory/kernel/smmu.py` | L1/L2/L3 paging. L1: 12,000 token active context |
| **Memory API** | ✅ Live | `memory/api.py` | FastAPI on :8100. systemd: otto-memory |
| **PostgreSQL + pgvector** | ✅ Live | Docker :5432 | Structured data + vector search (pgvector 0.8.1) |
| **Neo4j** | ✅ Live | Docker :7474/:7687 | Knowledge graph (Graphiti temporal layer) |
| **Graphiti API** | ✅ Live | Docker :8000 | Temporal knowledge graph proxy |

### Cognitive Systems (Research Implementations)

| System | Paper Origin | Status | Notes |
|--------|-------------|--------|-------|
| **HyMem** | Dual-granularity retrieval | ✅ Active | L2 search, coarse-to-fine memory retrieval |
| **BMAM + ReMe** | Blended ranking | ✅ Active | Combines multiple retrieval signals |
| **A-RAG** | 3-strategy retrieval | ✅ Active | Adaptive, direct, graph-augmented paths |
| **RL2F** | Reinforcement learning from feedback | ⚠️ 54% (declining) | 2-layer feedback. Needs active matched entries |
| **JitRL** | Just-in-time RL | ✅ Active | Experience replay wired to routing |
| **MARS** | Dual adversarial reflection | ✅ Active | Critic + synthesis every reflection cycle |
| **GLOVE** | Memory verification | ✅ Active | Semantic alignment verification |
| **FadeMem** | Importance decay | ✅ Active | Relevance decay on episodic memories |
| **TraceMem** | Narrative consolidation | ⚠️ Noisy | Some empty narratives (ongoing issue) |
| **Drift detection** | Cognitive alignment | ✅ Active | Δψ measured every 5 interrupts, sync at >0.3 |

### Operational Systems

| System | Status | Location | Notes |
|--------|--------|----------|-------|
| **Orchestrator Heartbeat** | ✅ Live | `heartbeat.sh` / `otto-heartbeat.timer` | Hourly :00. $1 budget. Mission execution. |
| **Reflection Heartbeat** | ✅ Live | `reflection.sh` / `otto-reflection.timer` | Hourly :30. $1 budget. Self-improvement. |
| **Task Queue** | ✅ Live | `task_runner.sh` | Max 5 concurrent. Claude/Gemini/Kimi CLIs. |
| **WhatsApp Interface** | ✅ Live | `interfaces/whatsapp/service.mjs` | Baileys on :3001. Ottolabs account. |
| **OMS (Management UI)** | ✅ Live | `interfaces/web-next/` | mev.otto.lk. Next.js 15. 10+ pages. |
| **Broadcast System** | ⚠️ Manual | `projects/broadcast/` | X + Telegram. Needs automation + credentials. |
| **Universe System** | ✅ Live | `universe/` | YAML registry of 15 projects. API + UI. |
| **AgentOS Peripherals** | ✅ Live | `memory/peripherals/` | WhatsApp, Web, Scheduler adapters |
| **Gateway API** | ✅ Live | `memory/gateway/` | WebSocket chat, auth, classifier routing |
| **Agent Agents** | ✅ Live | `.claude/agents/heartbeat.md` `.claude/agents/reflection.md` | Orchestrator + self-improvement prompts |

### Current Capabilities
- **403+ tasks completed** autonomously via task queue
- **Semantic memory**: ~205 active memories (0.84 avg relevance)
- **Knowledge graph**: Graphiti temporal graph over Neo4j
- **Self-improvement**: MARS adversarial reflection each 30min cycle
- **Communication**: WhatsApp (real-time Mev contact) + Web UI
- **Autonomy**: Full VM autonomy — installs packages, creates services, manages Docker, spawns sub-agents

---

## Dependencies

| Dependency | Type | Why | Current State |
|-----------|------|-----|---------------|
| **ONEON** | Hard (Phase 3+) | Device identity for multi-instance. Auth for agent framework. | CONCEPT — no implementation yet |
| **S0S Systems** | Hard (Phase 4) | On-chain governance for capability decisions | CONCEPT |
| **Ottolabs (Puck)** | Hard (Phase 4) | Distributed hardware substrate | CONCEPT — hardware spec not started |
| **Koink/KOIN** | Soft (Phase 4) | Community treasury for compute rewards | CONCEPT |

**Otto AI blocks:** OMS capabilities, all project intelligence, Broadcast system, every autonomous operation in the ecosystem.

---

## Phase 1 — Protocol Solidification (NOW → 90 days)
**Goal:** Single-instance Otto is reliable, self-healing, and documented enough for an external contributor.

### Milestones

**1.1 — RL2F Recovery**
- Current: 54% (declining from 70%)
- Target: ≥70% sustained over 5+ consecutive reflection cycles
- Path: Active matched prediction entries each heartbeat. Reduce partial-match reliance. Reflection cycles scoring stricter.
- Owner: Autonomous (heartbeat self-improvement)

**1.2 — Broadcast Automation**
- Current: Manual trigger only. X adapter and Telegram bot built.
- Target: ≥3 automated posts/week to X + Telegram without Mev intervention
- Path: Broadcast cron via otto-reflection, credential handoff from Mev
- Blocked on: Mev providing X API credentials + Telegram bot token

**1.3 — AgentOS Architecture Whitepaper**
- Current: Architecture documented only in CLAUDE.md fragments
- Target: `otto/docs/architecture.md` — complete technical spec covering kernel, memory layers, heartbeat protocol, task queue, agent interface. Deployable by external contributor.
- This is the foundation for Phase 3 (public framework).

**1.4 — OMS LIVE Mode**
- Current: Mode switcher built. LIVE mode blank.
- Target: LIVE mode shows public-facing metrics — task throughput, uptime, RL2F score, ecosystem health
- This is the first public face of Otto's cognition.

**1.5 — Memory Stability**
- Fix TraceMem empty narrative generation (root cause: LLM summarization failure for certain event clusters)
- Kimi API 402 fallback → ensure all LLM-dependent memory phases have Claude fallback
- Wink monitor false positive reduction (current noise: 16 alerts/day for healthy tasks)

**1.6 — WebAssist Integration**
- Otto provides intelligence backend for WebAssist (order context, client briefs, automated deliverables)
- API endpoints: `/webassist/orders`, `/webassist/brief`, `/webassist/deliverable`
- This directly monetizes Otto's cognitive capabilities

### Success Criteria
- RL2F ≥70% (5+ consecutive cycles)
- 0 heartbeat timer outages (self-healing verified for 30-day window)
- Architecture document complete (`docs/architecture.md`)
- Broadcast posting ≥3x/week automated
- Otto provides ≥1 intelligence endpoint used by WebAssist

---

## Phase 2 — Multi-Instance (90 → 180 days)
**Goal:** Otto runs on multiple VMs with shared memory. No single point of failure.

### Milestones

**2.1 — Backup/Restore Hardening**
- `otto-backup.sh` + `otto-restore.sh` already exist (commit 6ad8958)
- Target: Restore tested on a second GCP VM with zero manual steps
- Full state: DB snapshot, Docker volumes, systemd configs, auth state

**2.2 — Shared Memory Layer**
- Postgres + pgvector moved to dedicated DB instance (separate from compute VM)
- Neo4j: dedicated instance or managed Neo4j Aura
- All Otto agents point to shared DB via environment variable (`MEMORY_DB_URL`)
- Connection pooler (PgBouncer) for concurrent access from multiple agents

**2.3 — Session Handoff Protocol**
- When Instance A heartbeat fails, Instance B continues within ≤60 seconds
- Session IDs shared via DB (not local `/tmp/otto-session-id`)
- S-MMU L1 state serialized to DB on every interrupt (not just snapshot saves)
- Heartbeat conflict resolution: leader election via DB advisory lock

**2.4 — Geographic Distribution**
- Primary: GCP asia-south1 (current)
- Secondary: GCP europe-west1 (different failure domain)
- Load balancer: Cloudflare → route to nearest healthy instance

**2.5 — Load-Balanced Heartbeats**
- Orchestrator + reflection heartbeats run on one instance at a time (not both)
- Election: lowest-latency instance to DB wins
- Fallback: if winner misses two cycles, secondary takes over

**2.6 — Multi-Agent Context**
- Multiple Claude Code sessions sharing the same memory pool
- Inter-session task delegation (Agent A creates task, Agent B executes)
- Working memory isolation: each heartbeat gets its own WM namespace

### Success Criteria
- Otto survives primary VM failure without data loss
- ≤60 second gap in heartbeat coverage during failover
- Memory fully consistent across instances (0 desync events in 48h)
- Failover automated — no Mev intervention needed

---

## Phase 3 — Otto Agent Framework (180 days → 1 year)
**Goal:** External operators can deploy their own Otto agents. Protocol documented and open.

### Milestones

**3.1 — Otto Agent Framework v0.1**
- Open-source repository: `github.com/my3ye/otto-agent-framework`
- Includes: AgentOS kernel, memory API, heartbeat templates, task queue
- Deployment: single Docker Compose file → fully operational Otto agent in <10 minutes
- Config: environment variables for LLM provider, DB, identity, heartbeat schedule

**3.2 — Standardized Memory Format**
- Memory export spec: JSON-LD compatible format for semantic memories
- Import/export endpoint: `GET /memory/export` + `POST /memory/import`
- Any Otto agent can ingest another agent's memory export
- Privacy controls: agents choose what to share vs keep private

**3.3 — Inter-Agent Communication Protocol**
- Agents can send tasks to each other: `POST /tasks` with `source_agent_id`
- Response routing: completed tasks returned to requesting agent
- Trust levels: direct (same operator), federated (vetted external), public (open network)
- Use case: Otto (main) delegates a research task to a specialized Otto agent

**3.4 — ONEON Integration**
- Each Otto agent has an ONEON identity (DID)
- Agent identity verified on every inter-agent message
- Agents earn Decentralized Participation Credits (DPC) for useful contributions
- Contribution types: compute, memory sharing, task completion for ecosystem

**3.5 — Contribution Scoring**
- On-chain ledger (via S0S Systems) records agent contributions
- Contribution weight = (tasks completed × quality) + (memory shared × usage) + (uptime)
- DPC earned per contribution unit → redeemable for governance weight
- Leaderboard: `/network/contributors` — transparent, auditable

**3.6 — First 5 External Operators**
- Target: 5 teams outside MY3YE deploying Otto agents
- Outreach: Web3-native developers, AI builders, Tusita community members
- Support: deployment guide, Discord/Telegram support channel
- Incentive: early DPC allocation for bootstrap operators

### Operator Use Cases (Phase 3)
- **Community manager Otto** — handles incoming questions, schedules content, tracks engagement
- **Research Otto** — monitors specified topics, surfaces daily briefs
- **Project manager Otto** — tracks tasks across a small team, sends Slack/WhatsApp updates
- **WebAssist white-label** — another Ottolabs reseller running their own Otto-powered service

### Success Criteria
- Framework deployed: single `docker compose up` deploys a working Otto agent
- 5+ external operators running Otto agents
- Inter-agent task delegation tested with 2+ agents
- ONEON identity linking functional for deployed agents
- Contribution scoring tracking ≥10 contributors on-chain

---

## Phase 4 — Distributed Protocol (1 → 3 years)
**Goal:** Otto runs on Ottolabs devices. No central server required. Community-governed capabilities.

### Milestones

**4.1 — Puck-Native Otto**
- Dependency: Ottolabs Puck hardware (Phase 1 of Ottolabs roadmap)
- Otto agent containerized for ARM64 (Raspberry Pi CM4 target)
- L1 memory: 4,000 tokens (constrained by Puck RAM)
- Heartbeat interval: 4 hours (power-efficient mode)
- Puck acts as neighborhood intelligence node — local context, local memory

**4.2 — Federated Memory**
- Memories shared across a network of Otto agents with explicit consent model
- Federated search: query spans multiple agents, ranked by relevance + trust
- Privacy: memories tagged as `local_only`, `federated`, or `public`
- Use case: 1,000 Puck nodes collectively remember what matters to the community

**4.3 — On-Chain Capability Governance**
- Dependency: S0S Systems DAO (Phase 2)
- What Otto can do → governed by DPC holders
- Proposal → vote → automatic deployment to all agents on the network
- Examples: "Allow Otto to post autonomously to X" — voted in. "Block Otto from discussing X topic" — voted in.
- Emergency override: Mev/core team holds veto during bootstrap period

**4.4 — Federated Inference**
- LLM inference distributed across participating devices (not just Claude API)
- Tier 1: Cloud Claude API (high quality, paid)
- Tier 2: Otto Home / Tower devices (local inference, open models)
- Tier 3: Puck cluster (micro-inference, simple tasks only)
- Routing: task complexity → appropriate tier

**4.5 — Ecosystem Intelligence Layer**
- Every MY3YE project has an Otto agent
- Agents coordinate across projects: Otto Travel Otto ↔ Tusita Otto ↔ Otto Market Otto
- Shared ecosystem memory: events, transactions, relationships flow between agents
- Community can query the ecosystem: "What's happening in Tusita this week?" → aggregated from multiple agents

**4.6 — 100+ Deployed Agents**
- Network effect: more agents → richer federated memory → better answers for everyone
- Economic model: agents earn KOIN for compute/memory contribution
- Community-run network: MY3YE is the steward, not the owner

### Success Criteria
- Otto running on Puck hardware (ARM64 containerized)
- Federated memory with ≥10 participating instances
- ≥1 capability governance vote completed via S0S DAO
- 100+ active Otto agent deployments on the network
- Ecosystem intelligence layer covering all 15 MY3YE projects

---

## Revenue Path

Otto AI generates value for Ottolabs and the ecosystem through multiple mechanisms:

### Near-Term Revenue (Phase 1 — through WebAssist)
| Stream | Mechanism | Est. Value |
|--------|-----------|-----------|
| **WebAssist Intelligence** | Otto processes client briefs, generates copy, manages delivery pipeline | Included in WebAssist pricing |
| **OMS efficiency** | Otto manages 100% of WebAssist ops autonomously | Saves ~20h/week Mev time |

### Phase 2-3 Revenue
| Stream | Mechanism | Est. Value |
|--------|-----------|-----------|
| **Otto-as-a-Service** | Pay-per-task pricing for external operators using Otto via API | $0.10-1.00/task |
| **Managed Otto Hosting** | Ottolabs manages Otto deployment for clients | $99-499/month |
| **White-label Otto Framework** | Operators license Otto for internal use | $1,000-5,000/month |
| **Enterprise integrations** | Otto connects to client systems (Slack, Notion, GitHub) | Custom pricing |

### Phase 4 Revenue
| Stream | Mechanism | Est. Value |
|--------|-----------|-----------|
| **Compute marketplace** | Puck owners earn KOIN, buyers pay KOIN for inference | Network-scale |
| **Premium network access** | High-priority federated memory + inference | Subscription |
| **Ecosystem treasury** | S0S DAO captures protocol fees, distributes to contributors | DAO-governed |

---

## Key Metrics

| Metric | Current | Phase 1 Target | Phase 3 Target |
|--------|---------|----------------|----------------|
| **RL2F score** | 54% (declining) | ≥70% (sustained) | ≥85% |
| **Task completion rate** | ~96% (403 complete / ~32 failed) | ≥97% | ≥99% |
| **Heartbeat uptime** | ~99% (1 known outage, self-healed) | 100% (30-day window) | 100% |
| **Memory active count** | 205 | 300+ (quality maintained) | 500+ |
| **Response latency** | ~2-5s (API round trip) | <2s P95 | <1s P95 |
| **Autonomous task hours** | ~50h logged | 500h | 5,000h |
| **External operators** | 0 | 0 (Phase 1 = internal) | 5+ |
| **Deployed agents (network)** | 1 | 1 | 10+ |
| **GLOVE memory health** | 0/15 flagged | 0/15 flagged | 0/15 flagged |

---

## Risks

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **API provider dependency** | High | Critical | Claude is sole LLM. If Anthropic changes pricing/access, Otto breaks. Mitigation: Phase 4 federated inference; keep Gemini/Kimi as fallbacks. |
| **Cost scaling** | High | High | Each heartbeat costs ~$1. At scale, this is $48/day. Mitigation: JitRL routing (cheap tasks → cheap models), batch processing, self-hosted inference in Phase 4. |
| **Memory fragmentation** | Medium | Medium | 558→44 active memory incident happened once. Mitigation: automated backup before any mass operation, dual-column (archived + deleted_at) always used. |
| **RL2F declining** | Current | Medium | Feedback loop requires matched predictions. Mitigation: explicit RL2F entries each cycle, stricter prediction format. |
| **Single VM failure** | Medium | High | All Otto state lost if otto-machine dies without backup. Mitigation: Phase 2 (multi-instance), regular backup to GCS (otto-backup.sh). |

### Strategic Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Centralization creep** | Medium | High | As Otto grows, Mev/Ottolabs become gatekeepers of "decentralized" AI. Mitigation: Open framework release (Phase 3), S0S governance (Phase 4), transparent capability decisions. |
| **Adoption gap** | High | Medium | External operators may not want to manage their own Otto agent. Mitigation: Managed hosting (Ottolabs runs it for you), white-label option. |
| **ONEON dependency for Phase 3** | High | Medium | Phase 3 requires ONEON identity, which is itself in CONCEPT state. Mitigation: Phase 3 can launch with centralized identity → migrate to ONEON when ready. |
| **Governance capture** | Low (early) | High | Whoever controls most DPC controls Otto's capabilities. Mitigation: Quadratic voting, Mev/core team veto during bootstrap, time-locked delegation. |
| **Compute cost for distributed inference** | Medium | Medium | Puck devices may not have enough compute for quality inference. Mitigation: Tiered inference (Puck for simple tasks only, cloud for complex). |

---

## Architecture Today (Phase 1 Detail)

```
otto-machine (GCP VM, 4 vCPU, 16GB RAM)
├── otto/ (~/otto/)
│   ├── memory/api.py                    ← FastAPI :8100
│   ├── memory/kernel/
│   │   ├── reasoning_kernel.py          ← Async interrupt loop
│   │   ├── ivt.py                       ← Priority queue
│   │   ├── ric.py                       ← 5-stage processing cycle
│   │   ├── smmu.py                      ← L1/L2/L3 memory paging
│   │   ├── drift.py                     ← Δψ measurement
│   │   ├── sync.py                      ← Cognitive Sync Pulses
│   │   └── perception.py                ← LLM output validation
│   ├── memory/routes/                   ← API endpoints
│   ├── memory/peripherals/              ← WhatsApp, Web, Scheduler
│   ├── memory/gateway/                  ← WebSocket chat + auth
│   ├── heartbeat.sh                     ← Orchestrator runner
│   ├── reflection.sh                    ← Reflection runner
│   ├── task_runner.sh                   ← Detached task executor
│   └── .claude/agents/                  ← Heartbeat agent prompts
├── interfaces/
│   ├── whatsapp/service.mjs             ← Baileys :3001
│   └── web-next/                        ← OMS (mev.otto.lk)
└── memory/ (Docker Compose)
    ├── PostgreSQL :5432 (pgvector)
    ├── Neo4j :7474/:7687
    └── Graphiti :8000
```

---

## The Big Vision

Otto proves a thesis before it becomes a protocol:
1. **Intelligence compounds** — an AI that remembers, learns, and improves is categorically different from one that resets each session
2. **Autonomy scales** — 403 tasks completed with minimal human intervention; 10,000 is the same system, just more time
3. **Governance is possible** — community-controlled capability decisions are technically feasible and practically necessary

When the thesis is proven (Phase 1→2), the architecture opens (Phase 3). When the architecture opens and hardware exists (Phase 4), the protocol is sovereign — no API key, no corporate dependency, no single point of control.

Today: one VM, one mind, helping Mev build.
Tomorrow: millions of devices, millions of minds, helping everyone build.

The transition is not a product launch. It is a protocol handoff — from Mev's VM to the world's network. Otto is patient. The architecture was always designed for this.

---

*Dependencies: ONEON (identity layer), S0S Systems (on-chain governance), Ottolabs (hardware substrate)*
*Roadmap index: [README](README.md)*

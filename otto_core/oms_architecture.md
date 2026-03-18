# Otto Management System — Architecture Reference

**Version:** 1.0 (2026-03-18)
**Audience:** Otto, Mev, contributors
**Purpose:** Ground-truth reference for how the OMS works end-to-end.

---

## 1. System Overview

The Otto Management System (OMS) is the control plane for the entire Otto AI stack. It exposes Otto's internal state — memory, tasks, agents, conversations, universe, and infrastructure — via a web UI and a REST API.

```
┌────────────────────────────────────────────────────────────────┐
│                   OMS Web UI (web-next)                        │
│       Next.js 15 static export · mev.otto.lk · :443           │
│   30+ pages: tasks, memory, chat, universe, kernel, etc.       │
└──────────────────────┬─────────────────────────────────────────┘
                       │ HTTPS /api → proxied to :8100
┌──────────────────────▼─────────────────────────────────────────┐
│                  Memory API (otto-memory)                       │
│         FastAPI · :8100 · systemd: otto-memory                 │
│  50+ route modules · asyncpg pool · PostgreSQL + pgvector      │
└──────┬──────────────┬────────────────┬────────────────┬────────┘
       │              │                │                │
  ┌────▼────┐   ┌─────▼────┐   ┌──────▼─────┐  ┌──────▼──────┐
  │ Postgres│   │  Neo4j   │   │  Graphiti  │  │  WhatsApp   │
  │  :5432  │   │  :7687   │   │   :8000    │  │   :3001     │
  │ vectors │   │  graph   │   │  temporal  │  │  Baileys    │
  └─────────┘   └──────────┘   └────────────┘  └─────────────┘
```

---

## 2. OMS Frontend (web-next)

**Location:** `~/interfaces/web-next/`
**Framework:** Next.js 15, static export (`output: "export"`)
**Host:** Vercel, deployed from `ottomev` GitHub account
**Theme:** Tron dark system with 6 theme variants (tron, ares, clu, athena, aphrodite, poseidon)

### Page Inventory

| Route | Purpose |
|---|---|
| `/` | Dashboard — live task queue + system health |
| `/tasks` | Task queue browser — create, review, monitor tasks |
| `/memory` | Semantic memory — search, browse, manage facts |
| `/chat` | Live chat with Otto via WhatsApp kernel |
| `/kernel` | AgentOS kernel status — drift, providers, L1 cache |
| `/universe` | Universe YAML browser — projects, personas, changelog |
| `/whatsapp` | WhatsApp accounts status + connection management |
| `/context-history` | Session + episodic event timeline |
| `/reasoning` | Reasoning chain / MARS reflection history |
| `/education` | Skill tree — cluster browser + XP progress |
| `/inbox` | Pending questions Otto asked Mev |
| `/decisions` | Decision log |
| `/critiques` | Self-critique history |
| `/security` | Security audit findings |
| `/environment` | System health — services, disk, ports |
| `/webassist` | WebAssist order/client management |
| `/trading` | Alpha signal pipeline dashboard |
| `/social-calendar` | Social calendar + scheduled posts |
| `/services` | Ottolabs service catalog |
| `/research` | Research task outputs |
| `/settings` | OMS settings + theme |
| `/files` | File browser |
| `/articles` | Published articles |
| `/contacts` | Contact database |
| `/backup` | Memory backup/restore |
| `/investors` | Investor materials (auth-gated) |
| `/whiteboard` | Free-form planning |

### API Communication Pattern

All API calls go through a `next.config.ts` proxy:
```
/api/* → http://localhost:8100/*
```

Frontend helpers (`src/lib/api.ts`):
- `apiGet<T>(path)` — GET with JSON decode
- `apiPost<T>(path, body)` — POST with JSON body
- `apiPut<T>(path, body)` — PUT with JSON body

Data fetching hook:
```typescript
const { data, loading, error } = useApi<T>({
  fetcher: () => apiGet<T>("/endpoint"),
  interval: 5000,    // polling interval (ms)
  enabled: true,     // conditional fetch
  deps: [dep],       // re-fetch on dep change
})
```

### TypeScript Conventions

- New API types → `src/lib/api-types.ts`
- Pages: `src/app/{name}/page.tsx`, always `"use client"` at top
- UI primitives: shadcn/ui in `src/components/ui/`
- Otto widgets: `DataCard`, `Stat` in `src/components/otto/card`
- Navigation: `src/components/layout/app-sidebar.tsx` — add new pages here
- **React Rule:** ALL hook calls must appear before any conditional `return null`
- Verify: `cd ~/interfaces/web-next && npx tsc --noEmit && npm run build`

---

## 3. Memory API

**Location:** `~/otto/memory/`
**Framework:** FastAPI + asyncpg
**Port:** 8100
**Service:** `systemctl start otto-memory`
**Venv:** `~/otto/memory/.venv/bin/python`

### Storage Backends

| Backend | Port | Purpose |
|---|---|---|
| PostgreSQL 17 + pgvector 0.8.1 | :5432 | Structured data, semantic memories, episodic events, tasks, sessions, embeddings |
| Neo4j 5.26.2 | :7474/:7687 | Knowledge graph — entities, relationships, temporal context |
| Graphiti (latest) | :8000 | Temporal knowledge graph API over Neo4j |

**DB Access (no psql on host):**
```bash
docker exec memory-postgres-1 psql -U otto -d memory
```

### Memory Architecture (HyMem)

Otto's memory is organized into three semantic layers:

```
L1 — Active Context (in-memory, 12,000 token budget)
  ├── Always-resident: purpose, priorities, directives, identity
  └── Dynamic: message-relevant slices (loaded per interrupt)

L2 — Warm Storage (PostgreSQL)
  ├── semantic_memories — facts + pgvector embeddings (active: archived=FALSE AND deleted_at IS NULL)
  ├── episodic_events — timeline, salience-decayed, consolidated to narratives
  ├── semantic_slices — CID-keyed context segments
  └── sessions — conversation sessions with start/end metadata

L3 — Cold Storage (Neo4j + Graphiti)
  └── Knowledge graph — entities, relationships, temporal graphs
```

**Memory Query Pattern (A-RAG, 3-strategy):**
1. Vector similarity search (pgvector cosine)
2. BM25 full-text search (pg_trgm)
3. Graph traversal (Neo4j Cypher)

Results are blended via BMAM+ReMe relevance scoring.

### Core API Routes

| Module | Prefix | Key Endpoints |
|---|---|---|
| `sessions.py` | `/sessions` | start, end, last |
| `episodic.py` | `/episodic` | events (POST), timeline (POST), consolidate |
| `semantic.py` | `/semantic` | remember, search, list, decay |
| `tasks.py` | `/tasks` | CRUD, run, complete, review, qa-update |
| `working.py` | `/working` | working memory slots (GET/PUT) |
| `context.py` | `/context` | briefing, inject (full context aggregation) |
| `pending.py` | `/pending` | ask, open, resolve |
| `kernel_routes.py` | `/kernel` | status, interrupt, process, sync, L1, drift, slices |
| `universe.py` | `/universe` | projects, personas, changelog, LLM edit |
| `whatsapp.py` | `/whatsapp` | incoming, accounts, search |
| `rl2f.py` | `/rl2f` | task feedback, outcome resolution |
| `routing.py` | `/routing` | AdaptOrch task routing |
| `principles.py` | `/principles` | normative + task_execution principles |
| `procedural.py` | `/procedural` | procedure registry + outcome tracking |
| `education.py` | `/education` | skill tree, XP, progress tracking |

---

## 4. AgentOS Kernel (Context Engineering)

**Reference:** arXiv 2602.20934v1
**Location:** `~/otto/memory/kernel/`

The Reasoning Kernel is Otto's central cognitive loop. All messages from WhatsApp, web, and other sources are processed as **interrupts** through a single pipeline.

### Interrupt Lifecycle (RIC — 5 Phases)

```
INTERRUPT → [IVT Queue] → CognitiveScheduler
                              │
                    ┌─────────▼─────────────────────┐
         Phase 1:   │ SAVE — snapshot L1 state       │
         Phase 2:   │ LOAD — S-MMU pages in slices   │
         Phase 3:   │ PROCESS — build prompt → LLM   │
         Phase 4:   │ ALIGN — perception validation  │
         Phase 5:   │ POST — episodic log + drift     │ (async, non-blocking)
                    └───────────────────────────────-┘
```

**Phase 2 (LOAD) detail — S-MMU context assembly:**
1. Always-resident content (purpose, priorities, directives) placed at CONTEXT START
2. Conversation window loaded (20 messages, 400 char each)
3. A-RAG search: 3-strategy retrieval for message-relevant memories
4. Slices assembled into L1 (12,000 token budget)
5. Overflow → evict least-important (FadeMem scoring)

**Phase 3 (PROCESS) detail:**
```
System prompt:
  [identity] + [always-resident L1] + [relevant L1 slices]

User turn:
  [interrupt content] + [conversation context]
```

**Drift Detection:**
- Δψ measured every 5 interrupts
- Δψ > 0.3 → triggers Cognitive Sync Pulse (re-alignment)

### IVT (Interrupt Vector Table)

Priority queue for incoming interrupts. Types:
- `message` — incoming WhatsApp/web message
- `task_update` — task queue event
- `kernel_sync` — scheduled sync pulse
- `heartbeat` — orchestrator heartbeat

### S-MMU (Semantic Memory Management Unit)

Three-level paging: L1 (active context) → L2 (pgvector warm) → L3 (Neo4j cold)

Per-agent instances. Otto's kernel agent ID: `"otto"`.

---

## 5. Agent Infrastructure

### Dual Heartbeat Rhythm

Two complementary agents run on cron timers:

| Agent | Timer | Script | Role | Budget |
|---|---|---|---|---|
| **Orchestrator** | `otto-heartbeat.timer` (hourly :00) | `heartbeat.sh` | Mission execution — review tasks, create/launch tasks, message Mev | $1.00 |
| **Reflection** | `otto-reflection.timer` (hourly :30) | `reflection.sh` | Self-improvement — reconcile blockers, consolidate memory, evaluate performance | $1.00 |

Both agents use: `claude --model claude-sonnet-4-5 --budget $1.00`

### Task Queue

Heavy work (builds, research, implementations) runs as detached Claude Code sessions:

```
Heartbeat creates task → POST /tasks
                     ↓
           POST /tasks/{id}/run
                     ↓
        task_runner.sh {task_id}  (detached, nohup)
                     ↓
      claude subprocess (isolated context)
                     ↓
       POST /tasks/{id}/complete
                     ↓
        qa_runner.sh {task_id}   (QA review)
                     ↓
       POST /tasks/{id}/qa-update
                     ↓
        WhatsApp completion notification → Mev
```

**Task Lifecycle States:**
`pending` → `running` → `completed` / `failed` / `needs_manual_review` → `reviewed`

**Concurrency:** Max 5 concurrent tasks (claude=3, gemini=1, kimi=1)

**Logs:** `~/otto/logs/tasks/{task_id}.log`

### QA Runner

`qa_runner.sh` runs after each task completion:
1. Reads task output + diff
2. Sends to Gemini/Claude for LLM review
3. On APPROVE: sets git identity → stages files → commits → updates DB
4. On REJECT: creates RL2F feedback entry → heartbeat retries with lesson
5. **Git Identity Enforcement:** hard-rejects if repo not in `repo_owners.json`

### Git Identity Map

`~/otto/tools/repo_owners.json`:
```json
{
  "/home/web3relic/otto":              { "name": "my3ye",   "email": "my3ye.otto@gmail.com" },
  "/home/web3relic/interfaces/web-next": { "name": "ottomev", "email": "abraottomev@gmail.com" },
  "/mnt/media/projects/web-assist":    { "name": "ottomev", "email": "abraottomev@gmail.com" },
  "/mnt/media/projects/my3ye-web":     { "name": "PipiAgent","email": "my3ye.otto@gmail.com" },
  "/mnt/media/projects/oneon-web":     { "name": "my3ye",   "email": "my3ye.otto@gmail.com" },
  "/mnt/media/projects/tusita-web":    { "name": "my3ye",   "email": "my3ye.otto@gmail.com" }
}
```

**Enforcer:** `~/otto/tools/git_identity_enforcer.sh {repo_path}`
- Exit 0: identity set successfully
- Exit 1: unknown repo → QA HARD REJECTS (no commits from unmapped repos)
- Exit 2: config error

### AdaptOrch Routing

`routing.py` classifies tasks and assigns execution strategy:

| Strategy | Budget | Timeout | For |
|---|---|---|---|
| `express` | capped | 60s | Lookups, quick checks |
| `research_chunked` | extended | 900s | Research sweeps |
| `full_budget_build` | max | 600s | P8+ build tasks |
| `eval_focused` | standard | 600s | Evaluation tasks |
| `lats_fallback` | standard | standard | Previously-failed tasks |
| `standard` | as-is | as-is | Default |

---

## 6. LLM Routing

**Reference:** `~/otto/memory/kernel/provider.py`

Multiple LLM backends with automatic priority-order fallback:

```
Request → Provider Registry
            │
            ├─ Priority 1: Claude Sonnet (Anthropic API)
            ├─ Priority 2: Gemini Flash (Google AI)
            └─ Priority 3: Claude CLI (local fallback)
```

**Provider config** stored in `llm_providers` DB table (editable via OMS settings).

**llm_chat() helper** — used throughout memory API routes:
```python
from ..llm import llm_chat
response = await llm_chat(
    messages=[...],
    system_instruction="...",
    max_tokens=1000,
    temperature=0.0,
)
```

**RL2F (Reward Learning from Feedback):**
When QA rejects a task → creates feedback entry → routing adjusts strategy for retry.
Outcome: `succeeded` / `failed` → trust score updates via JitRL experience replay.

---

## 7. Communications Layer

### WhatsApp (Primary Channel)

**Service:** `~/interfaces/whatsapp/service.mjs` (Baileys, port :3001)
**Account:** Ottolabs WhatsApp
**Incoming flow:**
```
WhatsApp message
    → Baileys hook → POST /whatsapp/incoming (Memory API)
    → Kernel IVT (if kernel_enabled)
    → RIC pipeline → LLM response
    → POST /send (WhatsApp service :3001)
    → Delivered to Mev
```

**Outbound (tools):**
```bash
~/otto/tools/whatsapp_send.sh "message"   # sends as Ottolabs account
```

**Task Completion Notifications:**
`task_runner.sh` sends WhatsApp notification after every task:
- Success: `✅ {title}\n{one-line summary}`
- Failure: `❌ {title}\n{error reason}`

**Accounts tracked:**
- `otto` — Ottolabs account (main, always connected)
- `athena` — Athena account (secondary, connection managed via OMS)

### Pending Questions

When Otto needs Mev input: `POST /pending/ask` registers the question.
`GET /pending/open` shows unresolved questions.
OMS `/inbox` page displays these.

---

## 8. Universe System

**Location:** `~/otto/universe/`
**Registry:** `~/otto/universe/registry.yaml`
**Projects:** `~/otto/universe/projects/{id}.yaml`
**Personas:** `~/otto/universe/personas/{id}.yaml`
**Changelog:** `~/otto/universe/changelog.md` (append-only)

The Universe system is the canonical source of truth for all MY3YE projects and personas. The OMS `/universe` page provides a browser + natural language edit interface backed by LLM.

After any YAML mutation, `clear_cache()` is called to invalidate the in-memory loader cache.

---

## 9. Security Model

- **Memory API:** runs on :8100 (localhost only, nginx proxy for external)
- **WhatsApp service:** :3001 (localhost only)
- **Credentials:** `~/memory/.env` (chmod 600)
- **Git identity:** enforced per-repo via `repo_owners.json`
- **OMS auth:** investor page is auth-gated (JWT)
- **Vercel deploys:** `ottomev` GitHub account only
- **Secrets rotation:** documented in `~/otto/tools/handle_api_key_rotation.sh`

---

## 10. Deployment

| Repo | GitHub Account | Vercel Project | Domain |
|---|---|---|---|
| web-next (OMS) | ottomev | web-next | mev.otto.lk |
| web-assist | ottomev | web-assist | webassist.ink |
| my3ye-web | PipiAgent | my3ye-web | my3ye.xyz |
| otto-web | ottomev | otto-web | otto.lk |
| oneon-web | my3ye | oneon-web | oneon.ink |
| tusita-web | my3ye | tusita-web | tusita.xyz |

**Deploy flow:**
```bash
cd /path/to/repo
git commit -m "feat: ..."
git push ottomev main   # or: git push origin main
# Vercel auto-deploys on push
```

**Verify commit identity before push:**
```bash
git log -1 --format='%an <%ae>'
```

---

## 11. Observability

| What | How |
|---|---|
| Memory API health | `curl localhost:8100/health` |
| Kernel status | `curl localhost:8100/kernel/status` |
| Task queue | `curl localhost:8100/tasks/queue/status` |
| Heartbeat logs | `ls -t ~/otto/logs/heartbeat-*.log \| head -1 \| xargs cat` |
| Reflection logs | `ls -t ~/otto/logs/reflection-*.log \| head -1 \| xargs cat` |
| Task logs | `cat ~/otto/logs/tasks/{task_id}.log` |
| Service status | `systemctl status otto-memory otto-heartbeat.timer whatsapp` |
| DB access | `docker exec memory-postgres-1 psql -U otto -d memory` |

---

## Key Design Decisions

1. **Single kernel** — all message sources converge to one cognitive path (no forking)
2. **S-MMU placement** — always-resident content at CONTEXT START (not mid-context)
3. **Async POST phase** — Phase 5 never blocks response latency
4. **Hard git enforcement** — unknown repos hard-reject; prevents wrong-account commits
5. **Detached task runner** — heavy work isolated in separate Claude subprocess, not blocking heartbeat
6. **Static export** — OMS UI is a static site; API calls go through Next.js rewrites to localhost:8100
7. **Dual DB filter** — always `archived = FALSE AND deleted_at IS NULL` for semantic memories

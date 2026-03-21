# Otto AI — Public GitHub Repo Architecture
**Date:** 2026-03-22
**Purpose:** EasyA developer entry point + public proof-of-build
**Destination:** github.com/my3ye/otto-ai (public)

---

## Design: Otto AI Public GitHub Repo

### Problem

The EasyA outreach email has a hard blocker: `[[NEEDS_MEV_INPUT: public GitHub repo URL]]`. No public `otto-ai` repo exists. The getting-started README is drafted locally but unpublished. Without a real GitHub URL:
- The email cannot be sent
- The "every line of code open" claim in the article is unverifiable
- Hackathon participants have no entry point

### Approach

Create `my3ye/otto-ai` as a public GitHub repo containing a **curated developer SDK** — the real Memory API infrastructure stripped of internal business routes, with working examples, docker-compose setup, and EasyA hackathon track documentation.

This is NOT a demo or mock. This is the actual infrastructure, curated for public developer use. Developers can run it locally with `docker compose up` and immediately call the same APIs that power the production system at webassist.ink.

### Key Decisions

- **Account: `my3ye`** because: (1) the getting-started README already uses `github.com/my3ye/otto-ai`, (2) `my3ye` is the public-facing MY3YE ecosystem identity (name="MY3YE"), (3) EasyA pitch is from "MY3YE" not "ottomev". Alternative: `ottomev` (rejected — existing pallets use ottomev, but the AI infra belongs to the ecosystem identity, not a personal handle).

- **Repo name: `otto-ai`** because: the getting-started README, the EasyA outreach email, and all pitch materials use this name. Alternative: `otto-core` (rejected — already exists as private repo under my3ye, wrong name for public developer SDK).

- **Curated subset over full codebase** because: 50+ production routes include internal business logic (outreach, athena prospects, crypto, leads, investors, WebAssist internals). Exposing these adds security surface and confusion for hackathon developers who only need memory/tasks/kernel. Alternative: full codebase (rejected — too noisy, exposes internals, harder to understand).

- **docker-compose.yml as primary entry point** because: hackathon participants spin up the stack once and work against live endpoints. No Python environment setup confusion. Same architecture as production.

- **MIT License** because: we want developers to use and fork freely; ecosystem contribution is the goal.

### API / Interface

**What the public repo exposes (curated core routes):**

| Route | Purpose | File |
|-------|---------|------|
| `GET /health` | System health | routes/health.py |
| `POST /sessions/start` | Start a session | routes/sessions.py |
| `POST /sessions/{id}/end` | End a session | routes/sessions.py |
| `POST /semantic/remember` | Store a memory with embedding | routes/semantic.py |
| `POST /semantic/search` | Vector similarity search | routes/semantic.py |
| `POST /semantic/forget` | Archive a memory | routes/semantic.py |
| `POST /episodic/events` | Log an event | routes/episodic.py |
| `POST /episodic/timeline` | Query event timeline | routes/episodic.py |
| `POST /procedural` | Create a procedure | routes/procedural.py |
| `GET /procedural` | List procedures | routes/procedural.py |
| `PUT /procedural/{name}/outcome` | Record outcome | routes/procedural.py |
| `POST /tasks` | Create a task | routes/tasks.py |
| `GET /tasks/{id}` | Get task detail | routes/tasks.py |
| `POST /tasks/{id}/run` | Launch task | routes/tasks.py |
| `GET /tasks/queue/status` | Queue summary | routes/tasks.py |

**What is excluded from public repo (internal business routes):**
webassist, athena, leads, investors, outreach, bankr, crypto, commerce, trading, virtuals, broadcast, contacts, email, whatsapp, arts, articles, bulk, social_calendar, workspace, universe, thought_vault, etc.

### Repo Structure

```
otto-ai/
├── README.md                    # Main getting-started (from EasyA draft)
├── docker-compose.yml           # Full stack: postgres+pgvector+neo4j+graphiti+api
├── .env.example                 # Required env vars, no secrets
├── Makefile                     # make up, down, logs, example
├── LICENSE                      # MIT
├── .gitignore                   # .env, __pycache__, .venv, *.pyc
├── docs/
│   ├── quickstart.md            # 5-minute setup (prerequisites → clone → up → curl)
│   ├── architecture.md          # How it works (memory/tasks/kernel)
│   ├── api-reference.md         # All public endpoints documented
│   └── hackathon-tracks.md      # Three EasyA tracks: SOS / ONEON / Otto AI
├── examples/
│   ├── hello-memory/
│   │   ├── agent.py             # Store + recall memories (10 lines, self-contained)
│   │   └── README.md
│   ├── task-runner/
│   │   ├── example.py           # Create + launch + monitor a task
│   │   └── README.md
│   └── multi-agent/
│       ├── orchestrate.py       # Two agents coordinate via shared memory
│       └── README.md
├── memory/                      # Core Memory API (FastAPI)
│   ├── api.py                   # App entrypoint — only public routes registered
│   ├── config.py                # Settings (env-var based, safe)
│   ├── db.py                    # asyncpg connection pool
│   ├── models.py                # Pydantic models (public subset)
│   ├── embeddings.py            # OpenAI embeddings helper
│   ├── requirements.txt         # fastapi, uvicorn, asyncpg, pgvector, pydantic, openai
│   └── routes/
│       ├── health.py            # GET /health
│       ├── sessions.py          # Session management
│       ├── semantic.py          # Memory store + search
│       ├── episodic.py          # Event logging + timeline
│       ├── procedural.py        # Skill/procedure learning
│       └── tasks.py             # Task queue
├── init-db/
│   └── 000_init.sql             # pgvector extension + tables schema
└── task_runner.sh               # Bash task executor (simplified public version)
```

### Implementation Plan

**Step 1: Create and initialize repo**
1. `gh auth switch --user my3ye`
2. `gh repo create my3ye/otto-ai --public --description "Otto AI — autonomous agent infrastructure for the MY3YE ecosystem"`
3. Clone to `/mnt/media/projects/otto-ai/`
4. Initialize with .gitignore, MIT LICENSE, initial commit

**Step 2: Scaffold core files**
5. Write `docker-compose.yml` — adapt from `~/memory/docker-compose.yml` (postgres+pgvector+neo4j+graphiti), add memory-api service pointing to `./memory/`
6. Write `.env.example` — postgres creds, openai key, graphiti url, no real secrets
7. Write `Makefile` — targets: up, down, logs, reset, example

**Step 3: Copy and curate Memory API**
8. Copy `memory/config.py` → repo (already env-var based, safe as-is)
9. Copy `memory/db.py` → repo (pure asyncpg pool, no secrets)
10. Copy `memory/embeddings.py` → repo (OpenAI embedding helper)
11. Write `memory/api.py` — clean version that registers only the 6 public route files
12. Write `memory/models.py` — subset: Session, SemanticMemory, EpisodicEvent, Procedure, Task
13. Copy and audit `memory/routes/semantic.py` → strip any internal query filters, keep public interface
14. Copy and audit `memory/routes/episodic.py` → same
15. Copy and audit `memory/routes/procedural.py` → same
16. Copy and audit `memory/routes/tasks.py` → strip internal fields, keep core CRUD + run
17. Copy and audit `memory/routes/sessions.py` → keep start/end/last
18. Write `memory/routes/health.py` → simple status check
19. Write `memory/requirements.txt` → minimal deps
20. Write `init-db/000_init.sql` → pgvector + 5 core tables schema

**Step 4: Write docs**
21. Write `docs/quickstart.md` — prerequisites (Docker), clone, `make up`, first curl
22. Write `docs/architecture.md` — 4-layer system diagram (memory/tasks/kernel/agents)
23. Write `docs/api-reference.md` — all 15 public endpoints with curl examples
24. Write `docs/hackathon-tracks.md` — three tracks (SOS Systems / ONEON / Otto AI) from existing EasyA material

**Step 5: Write examples**
25. Write `examples/hello-memory/agent.py` — 30 lines: connect, remember, search, print results
26. Write `examples/hello-memory/README.md`
27. Write `examples/task-runner/example.py` — create task, run, poll, print output
28. Write `examples/task-runner/README.md`
29. Write `examples/multi-agent/orchestrate.py` — agent A stores result, agent B searches and acts
30. Write `examples/multi-agent/README.md`

**Step 6: Finalize README and update EasyA materials**
31. Write `README.md` — the getting-started draft from `projects/easya/getting-started-readme.md`, URL updated to real `github.com/my3ye/otto-ai`
32. Commit and push everything to GitHub
33. Verify repo is public: `gh repo view my3ye/otto-ai --web` or `curl https://github.com/my3ye/otto-ai`
34. Update `projects/easya/getting-started-readme.md` — replace draft URL with real URL
35. Update `projects/easya/outreach-email-v2.md` — replace `[[NEEDS_MEV_INPUT: public GitHub repo URL]]` with `https://github.com/my3ye/otto-ai`

### Risks

- **`task_runner.sh` complexity**: The production runner has complex internal logic (QA, cost tracking, multi-model routing). Public version should be a simplified wrapper that calls any `claude` command. Mitigation: write a new simplified `task_runner.sh` for the public repo that just runs a subprocess and logs output.

- **Init SQL schema drift**: The production DB has 64+ migrations. The public repo needs a clean single-file schema for the 5 core tables. Mitigation: derive from the final migration state, write a clean 000_init.sql.

- **Route interdependencies**: Some routes import from others (tasks.py may import from semantic.py for tagging). Mitigation: audit each copied route for internal imports and either satisfy or stub them.

- **models.py is large** (25KB, 400+ lines): The public repo only needs a subset. Mitigation: extract the 5 core model classes into a clean models.py.

- **git identity for my3ye**: Commits must use `my3ye.otto@gmail.com`. Set `git config user.email my3ye.otto@gmail.com` in the repo before committing.

---

## Constraints

- Repo must be public (required for EasyA outreach)
- No secrets in any committed file (config.py reads from .env, .env in .gitignore)
- README must be developer-facing, not internal (no Mev references, no Otto persona)
- All examples must work with `docker compose up` + the provided `.env.example` values (except API keys)

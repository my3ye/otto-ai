---
name: otto-conventions
description: Otto's codebase conventions, project structure, and development patterns. Auto-loaded when working on Otto's code.
user-invocable: false
---

## Project Structure

| Component | Path | Stack |
|-----------|------|-------|
| Memory API | `~/otto/memory/` | FastAPI, asyncpg, Python 3.11 |
| Kernel | `~/otto/memory/kernel/` | AgentOS reasoning kernel |
| Gateway | `~/otto/memory/gateway/` | Unified message handler |
| Web UI | `~/interfaces/web/` | Vanilla HTML/CSS/JS (no build step) |
| WhatsApp | `~/interfaces/whatsapp/` | Node.js, Baileys |
| Infra | `~/memory/` | Docker Compose (Postgres, Neo4j, Graphiti) |

## Conventions

- **Python**: Type hints on public functions. Use asyncpg for DB, httpx for HTTP.
- **Web**: Vanilla HTML/CSS/JS — no frameworks, no build step. FastAPI serves static files.
- **LLM calls**: Always go through `~/otto/memory/llm.py` (`llm_chat()`) — never call providers directly.
- **Memory**: All memory operations go through the API (:8100), not direct DB access.
- **Services**: systemd for all long-running services. Docker for databases.
- **Secrets**: `~/memory/.env` (chmod 600). Never commit secrets.
- **Git**: Identity is `my3ye / my3ye.otto@gmail.com`. Three GitHub accounts available (ottomev, PipiAgent, my3ye).

## API Route Pattern

```python
# ~/otto/memory/routes/new_routes.py
from fastapi import APIRouter
router = APIRouter(prefix="/new", tags=["new"])

@router.get("/endpoint")
async def get_something():
    ...
```

Register in `api.py`: `app.include_router(new_routes.router)`

## Database Pattern

```python
from db import get_pool
pool = await get_pool()
async with pool.acquire() as conn:
    result = await conn.fetch("SELECT * FROM table WHERE id = $1", some_id)
```

Migrations go in `~/otto/memory/migrations/`. Run with the migration runner.

## Key Gotchas

- No swap on this VM — watch memory usage
- `CLAUDECODE` env var must be unset when spawning child Claude processes
- Kimi needs `User-Agent: claude-code/1.0` header
- `semantic_memories` table uses `archived` (boolean), not `archived_at`
- `whatsapp_messages` has `channel` column (TEXT, default 'whatsapp')
- After modifying memory API code, restart: `sudo systemctl restart otto-memory`

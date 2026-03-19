---
name: api-development
description: Otto Memory API development patterns. Auto-loaded when building new API endpoints or modifying the memory API.
user-invocable: false
---

## Adding a New Endpoint

### 1. Create route file (if new domain)
```python
# ~/otto/memory/routes/new_domain_routes.py
from fastapi import APIRouter, HTTPException
from db import get_pool
from models import SomeModel  # Pydantic models in models.py

router = APIRouter(prefix="/new-domain", tags=["new-domain"])

@router.post("/endpoint")
async def create_thing(request: SomeModel):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            "INSERT INTO things (name, data) VALUES ($1, $2) RETURNING *",
            request.name, request.data
        )
    return dict(result)
```

### 2. Register in api.py
```python
from routes import new_domain_routes
app.include_router(new_domain_routes.router)
```

### 3. Add migration (if schema change)
```sql
-- ~/otto/memory/migrations/NNN_add_things_table.sql
CREATE TABLE IF NOT EXISTS things (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Add Pydantic model
```python
# In models.py
class SomeModel(BaseModel):
    name: str
    data: dict = {}
```

### 5. Restart service
```bash
sudo systemctl restart otto-memory
```

## Patterns

- Use `asyncpg` for all DB access (connection pool via `get_pool()`)
- Return `dict(row)` for single rows, `[dict(r) for r in rows]` for lists
- Use `HTTPException(status_code=404, detail="Not found")` for errors
- JSON fields use `JSONB` column type
- UUIDs for primary keys: `gen_random_uuid()`
- Timestamps: `TIMESTAMPTZ DEFAULT NOW()`
- All routes get their own file in `~/otto/memory/routes/`

## Testing

```bash
# Health check
curl -sf http://localhost:8100/health

# Test your new endpoint
curl -s -X POST http://localhost:8100/new-domain/endpoint \
  -H 'Content-Type: application/json' \
  -d '{"name": "test"}'

# Check service logs
journalctl -u otto-memory -n 30 --no-pager
```

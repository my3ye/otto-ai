# Quickstart

Get Otto AI running locally in 5 minutes.

## Prerequisites

- Docker + Docker Compose v2
- An OpenAI API key (for semantic memory embeddings)

## 1. Clone and configure

```bash
git clone https://github.com/my3ye/otto-ai
cd otto-ai
cp .env.example .env
```

Edit `.env` with your values:

```bash
POSTGRES_USER=otto
POSTGRES_PASSWORD=your-password-here
POSTGRES_DB=memory
OPENAI_API_KEY=sk-...
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password
```

## 2. Start the stack

```bash
docker compose up -d
```

This starts:
- **PostgreSQL + pgvector** (port 5432) — structured data and vector search
- **Neo4j** (port 7474/7687) — temporal knowledge graph
- **Graphiti** (port 8000) — knowledge graph API
- **Memory API** (port 8100) — your agent's memory interface

## 3. Verify

```bash
curl http://localhost:8100/health
```

Expected response:
```json
{"status": "ok", "db": "healthy", "timestamp": "2026-..."}
```

## 4. Store your first memory

```bash
curl -X POST http://localhost:8100/semantic/remember \
  -H 'Content-Type: application/json' \
  -d '{
    "content": "The user prefers concise responses",
    "category": "preference",
    "confidence": 0.9
  }'
```

## 5. Search memories

```bash
curl -X POST http://localhost:8100/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "user communication style", "limit": 5}'
```

## Next steps

- Read the [Architecture guide](architecture.md)
- Browse the [API Reference](api-reference.md)
- Try the [examples](../examples/)
- Check the [EasyA hackathon tracks](hackathon-tracks.md) if you're here for the hackathon

## Performance note: vector search

The semantic memory table uses an IVFFlat index for fast approximate nearest-neighbour search. IVFFlat builds its internal cluster list at index-creation time, but the clusters become accurate only after `ANALYZE` has run on the table. On a fresh install the index is empty, so Postgres will fall back to a sequential scan until you load some memories.

After you've added your first batch of memories (or before running benchmarks), run:

```bash
docker exec -it <postgres-container> psql -U $POSTGRES_USER -d $POSTGRES_DB \
  -c "ANALYZE semantic_memories;"
```

This is a one-time step per data load. Normal inserts re-use the existing clusters without needing another `ANALYZE`.

---

## Troubleshooting

**Services not starting:**
```bash
docker compose logs
```

**Memory API not reachable:**
```bash
docker compose logs memory-api
```

**Database connection errors:**
Make sure `POSTGRES_HOST=postgres` in your environment (it uses the Docker service name, not `localhost`).

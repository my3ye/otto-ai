---
name: memory-query
description: Query and store knowledge in Otto's memory system. Use when needing context from past experiences, decisions, lessons, or stored knowledge.
user-invocable: false
---

## Otto Memory API (localhost:8100)

### Search (read)

**Hybrid search (best for most queries):**
```bash
curl -s -X POST http://localhost:8100/semantic/arag_search \
  -H 'Content-Type: application/json' \
  -d '{"query": "your search query", "limit": 10, "min_confidence": 0.3}'
```

**Vector similarity search:**
```bash
curl -s -X POST http://localhost:8100/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "your search query", "limit": 5}'
```

**Knowledge graph search:**
```bash
curl -s -X POST http://localhost:8100/graph/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "entity or relationship"}'
```

**Episodic timeline:**
```bash
curl -s -X POST http://localhost:8100/episodic/timeline \
  -H 'Content-Type: application/json' \
  -d '{"query": "what happened", "limit": 10}'
```

### Store (write)

**Remember a fact:**
```bash
curl -s -X POST http://localhost:8100/semantic/remember \
  -H 'Content-Type: application/json' \
  -d '{"content": "the fact to remember", "category": "decision|lesson|convention|directive|context"}'
```

**Log an event:**
```bash
curl -s -X POST http://localhost:8100/episodic/events \
  -H 'Content-Type: application/json' \
  -d '{"content": "what happened", "event_type": "task_complete|error|decision|milestone", "importance": 5}'
```

**Store a procedure:**
```bash
curl -s -X POST http://localhost:8100/procedural \
  -H 'Content-Type: application/json' \
  -d '{"name": "procedure-name", "description": "what it does", "steps": ["step 1", "step 2"]}'
```

### Tips

- Always use `arag_search` over basic `search` — it combines 3 retrieval strategies
- Categories matter: use `directive` for Mev's instructions, `lesson` for learned patterns, `convention` for codebase rules
- Importance 1-10: 10 = mission-critical, 5 = normal context, 1 = nice-to-know

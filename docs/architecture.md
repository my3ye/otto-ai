# Architecture

Otto AI is a persistent intelligence infrastructure — not a framework, not a wrapper around an LLM. It is a system of coordinated memory layers and execution primitives that lets agents think across time.

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Your Agent / App                      │
│              (any LLM, any language, any tool)          │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Memory API (:8100)                     │
│              FastAPI — single interface                  │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐  │
│  │ Semantic │  │ Episodic │  │Procedural│  │ Tasks  │  │
│  │ Memory   │  │ Events   │  │ Learning │  │ Queue  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘  │
└───────┼─────────────┼─────────────┼─────────────┼───────┘
        │             │             │             │
        ▼             ▼             └─────────────┘
┌─────────────┐  ┌──────────────┐        │
│ PostgreSQL  │  │    Neo4j     │   task_runner.sh
│ + pgvector  │  │  + Graphiti  │   (subprocess)
│             │  │              │
│ Vector      │  │ Temporal     │
│ Similarity  │  │ Knowledge    │
│ Search      │  │ Graph        │
└─────────────┘  └──────────────┘
```

## Four Memory Layers

### 1. Semantic Memory — "What do I know?"

Stores facts and beliefs as vector embeddings. When you search, you query by *meaning*, not keywords. The system returns the most semantically similar memories.

Built on: PostgreSQL + pgvector. Embeddings: OpenAI text-embedding-3-small (1536 dimensions).

```python
# Store
POST /semantic/remember  {"content": "User is building a DeFi protocol", "confidence": 0.9}

# Recall by meaning
POST /semantic/search  {"query": "what is the user building?", "limit": 5}
```

### 2. Episodic Memory — "What happened?"

Logs events with timestamps. An agent's diary — what it saw, decided, and did. Queryable by session, event type, and importance.

```python
POST /episodic/events  {"content": "User clicked deploy", "event_type": "action", "importance": 0.8}
POST /episodic/timeline  {"event_type": "action", "limit": 20}
```

### 3. Procedural Memory — "How do I do things?"

Named sequences of steps that agents have learned work. Each procedure accumulates a trust score based on success/failure outcomes. High-trust procedures get surfaced first.

```python
POST /procedural  {"name": "deploy_contract", "steps": ["compile", "test", "broadcast"], ...}
PUT  /procedural/deploy_contract/outcome  {"success": true}
```

### 4. Task Queue — "What needs to happen?"

Detached execution — your agent creates tasks, they run asynchronously, and report back. Useful for long-running work that shouldn't block the agent.

```python
POST /tasks  {"title": "Analyze contract", "prompt": "...", "budget_usd": 1.0}
POST /tasks/{id}/run
GET  /tasks/{id}  # poll for completion
```

## Sessions

Sessions provide continuity. Start a session at the beginning of a run, attach events to it, end it with a summary. Later, you can reconstruct what happened.

```python
POST /sessions/start  → session_id
POST /episodic/events  {"session_id": "...", "content": "..."}
POST /sessions/{id}/end  {"summary": "Deployed contract successfully"}
```

## Design Principles

**Persistent by default.** Nothing expires unless you explicitly archive it. Agents should accumulate knowledge, not forget.

**Language agnostic.** The API is HTTP + JSON. Any language, any LLM, any framework can use it.

**Production first.** This same infrastructure runs the MY3YE production system at webassist.ink. It is not a demo.

**Additive.** Each memory layer is independent. You can use only semantic memory if that's all you need. Or combine all four.

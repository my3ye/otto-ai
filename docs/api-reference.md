# API Reference

Base URL: `http://localhost:8100`

All request/response bodies are JSON. All IDs are UUIDs.

---

## Health

### GET /health

System health check.

**Response:**
```json
{
  "status": "ok",
  "db": "healthy",
  "timestamp": "2026-03-22T10:00:00Z"
}
```

---

## Sessions

### POST /sessions/start

Start a new session. Returns a session ID to attach to episodic events.

**Request:**
```json
{
  "agent_id": "my-agent",
  "context": {"task": "analyze contract"}
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "agent_id": "my-agent",
  "started_at": "2026-03-22T10:00:00Z",
  "ended_at": null,
  "summary": null
}
```

---

### POST /sessions/{session_id}/end

End an active session with an optional summary.

**Request:**
```json
{
  "summary": "Analyzed 3 contracts, found 2 issues"
}
```

---

### GET /sessions/last

Get the most recently completed session.

---

## Semantic Memory

### POST /semantic/remember

Store a memory with semantic embedding.

**Request:**
```json
{
  "content": "The user is building a DeFi protocol on Base",
  "category": "context",
  "confidence": 0.9,
  "source": "user_message",
  "metadata": {"session": "abc"}
}
```

**Response:**
```json
{
  "id": "...",
  "content": "The user is building a DeFi protocol on Base",
  "category": "context",
  "confidence": 0.9,
  "source": "user_message",
  "created_at": "2026-03-22T10:00:00Z",
  "relevance": null
}
```

---

### POST /semantic/search

Search memories by semantic similarity.

**Request:**
```json
{
  "query": "what is the user working on?",
  "limit": 5,
  "min_confidence": 0.7,
  "category": "context"
}
```

**Response:** Array of memories, ranked by relevance (cosine similarity). Each includes `relevance` score (0.0–1.0).

---

### POST /semantic/forget/{memory_id}

Archive a memory (excludes it from future searches).

---

## Episodic Events

### POST /episodic/events

Log an event.

**Request:**
```json
{
  "session_id": "550e8400-...",
  "content": "User requested contract deployment to Base",
  "event_type": "action",
  "importance": 0.8,
  "metadata": {"contract": "0x..."}
}
```

**event_type values:** `action`, `decision`, `observation`, `error`, `conversation`, `system`, `general`

**importance:** 0.0 (low) to 1.0 (critical)

---

### POST /episodic/timeline

Query events.

**Request:**
```json
{
  "session_id": "550e8400-...",
  "event_type": "action",
  "min_importance": 0.5,
  "limit": 20
}
```

**Response:** Array of events, newest first.

---

## Procedural Memory

### POST /procedural

Create a procedure.

**Request:**
```json
{
  "name": "deploy_erc20",
  "description": "Deploy a standard ERC20 token contract",
  "steps": [
    "Compile contract with hardhat",
    "Run test suite",
    "Estimate gas",
    "Broadcast to network",
    "Verify on Etherscan"
  ],
  "category": "deployment"
}
```

---

### GET /procedural?category=deployment&limit=10

List procedures, ordered by trust score.

---

### PUT /procedural/{name}/outcome

Record a success or failure. Updates trust score.

**Request:**
```json
{
  "success": true,
  "notes": "Deployed to Base in 12s"
}
```

**Response:**
```json
{
  "name": "deploy_erc20",
  "success": true,
  "trust_score": 0.55,
  "use_count": 1
}
```

---

## Tasks

### POST /tasks

Create a task in the queue.

**Request:**
```json
{
  "title": "Analyze smart contract security",
  "prompt": "Review this contract for common vulnerabilities: [paste code]",
  "priority": 7,
  "budget_usd": 1.0,
  "timeout_seconds": 300,
  "agent_type": "security-engineer",
  "model": "sonnet",
  "created_by": "orchestrator"
}
```

**priority:** 1 (low) to 10 (critical)

---

### GET /tasks/queue/status

Queue summary.

**Response:**
```json
{
  "pending": 2,
  "running": 1,
  "completed_24h": 15,
  "failed_24h": 0
}
```

---

### GET /tasks/{task_id}

Get a single task.

**Response:**
```json
{
  "id": "...",
  "title": "Analyze smart contract",
  "status": "completed",
  "output": "Found 0 critical issues, 2 warnings...",
  "exit_code": 0,
  "created_at": "...",
  "completed_at": "..."
}
```

**status values:** `pending`, `running`, `completed`, `failed`

---

### POST /tasks/{task_id}/run

Launch a pending task. Spawns `task_runner.sh` as a detached subprocess.

**Response:**
```json
{
  "status": "launched",
  "task_id": "...",
  "title": "Analyze smart contract"
}
```

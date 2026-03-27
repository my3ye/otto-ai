# Architecture: A2A (Agent-to-Agent) Protocol

**Date**: 2026-03-28
**Author**: architect agent
**Source**: STEM Agent gap analysis (arXiv 2603.22359) — Gap P1/P6
**Status**: DESIGN — ready for implementation

---

## Problem

Otto's agents (task_runner.sh processes) are **isolated by design**. Each spawns as a detached bash process running a Claude/Gemini CLI session. The only coordination mechanism is:

1. **Plan DAGs** — sequential dependency: Task A completes → output flows to Task B via DB
2. **Workflow step chaining** — output piped via `{prev_output}` template variables
3. **Completion hooks** — `on_plan_task_complete()` advances the DAG

This works for sequential pipelines. It fails when:
- An architect agent needs to **ask** a coder agent a clarifying question mid-execution
- A reviewer agent wants to **request a fix** from the coder without restarting the entire workflow
- Two research agents working in parallel need to **deduplicate** their findings
- A running agent needs to **yield** a partial result for another agent to consume immediately

These are all cases where agents need **real-time, bidirectional, mid-execution communication** — not just "finish and pass output."

### Why Now

Currently low-frequency (agents mostly work alone). But plan DAGs are creating multi-agent workflows where coordination overhead is visible. The 66% partial RL2F rate partly reflects agents working with stale context because they can't query peers.

---

## Approach

**A2A as a lightweight message mailbox built on PostgreSQL + the existing Memory API.** No new infrastructure. No event bus. No pub-sub. Just a table, an API, and a polling convention.

### Why Not Pub-Sub / Redis / WebSockets

| Option | Rejected Because |
|---|---|
| Redis pub-sub | New infrastructure for a low-frequency use case. 4 vCPUs, 16GB RAM — don't add services |
| WebSockets | task_runner.sh is bash. Agents are CLI processes. No WebSocket client available |
| IVT interrupt queue | Already exists but wrong abstraction — IVT is for kernel-level signals, not agent chat |
| File-based (shared dir) | Race conditions, no ordering guarantees, hard to query |

**PostgreSQL polling is the right fit because:**
- Already running, already reliable
- Agents already call the Memory API via curl (task_runner.sh does ~8 API calls per task)
- Polling at 5-10s intervals is fine for agent-to-agent latency
- Full ACID guarantees on message ordering
- Queryable history (debugging, RL2F analysis)

---

## Key Decisions

1. **Mailbox model over pub-sub**: Each agent polls its own mailbox. Simpler, no connection management, works with bash curl. Alternative: event-driven push (rejected — agents are CLI processes, can't receive pushes).

2. **Channel-scoped messages**: Messages belong to a `channel_id` (typically a plan_id or workflow_instance_id). Agents only see messages in their channel. Alternative: global broadcast (rejected — noisy, doesn't scale).

3. **PostgreSQL table over IVT**: IVT is for kernel interrupts (SIG_MSG_ADMIN etc). A2A messages are peer-level, not kernel-level. Mixing them would pollute the interrupt priority queue. Alternative: extend IVT with SIG_A2A type (rejected — different lifecycle, different consumers).

4. **No agent discovery service**: Agents discover peers by querying the channel's participant list (derived from plan tasks or workflow steps). Alternative: registry service (rejected — over-engineering for 3-5 concurrent agents).

5. **Fire-and-forget delivery**: Sender posts message, recipient polls. No delivery guarantee beyond "it's in the DB." If an agent dies before reading, the message persists for the next attempt. Alternative: ack/nack protocol (rejected — complexity for low-frequency use).

---

## Data Model

### Migration: `a2a_messages` table

```sql
-- Migration 077: A2A agent-to-agent messaging
CREATE TABLE IF NOT EXISTS a2a_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID NOT NULL,              -- plan_id, workflow_instance_id, or ad-hoc UUID
    sender_id TEXT NOT NULL,               -- task_id or agent identifier (e.g. "task:abc123" or "heartbeat")
    sender_agent_type TEXT,                -- e.g. "architect", "coder", "reviewer"
    recipient_id TEXT,                     -- NULL = broadcast to channel, or specific "task:xyz789"
    message_type TEXT NOT NULL DEFAULT 'message',  -- message | request | response | artifact | signal
    content TEXT NOT NULL,                 -- the actual message (plain text or JSON)
    metadata JSONB DEFAULT '{}',          -- structured data (e.g. file paths, code snippets)
    in_reply_to UUID REFERENCES a2a_messages(id), -- threading
    read_by TEXT[] DEFAULT '{}',          -- array of task_ids that have read this
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ               -- optional TTL (NULL = permanent within channel lifecycle)
);

-- Indexes for polling pattern
CREATE INDEX idx_a2a_channel ON a2a_messages(channel_id, created_at);
CREATE INDEX idx_a2a_recipient ON a2a_messages(recipient_id, created_at) WHERE recipient_id IS NOT NULL;
CREATE INDEX idx_a2a_unread ON a2a_messages(channel_id, created_at) WHERE array_length(read_by, 1) IS NULL OR array_length(read_by, 1) = 0;
```

**Design notes:**
- `channel_id` is a UUID that groups related agents. For plan tasks, this is the `plan_id`. For workflows, the `workflow_instance_id`. For ad-hoc conversations, a fresh UUID.
- `sender_id` uses a prefixed format: `task:<uuid>` for task agents, `heartbeat` for the orchestrator, `reflection` for the reflection agent.
- `read_by` is an array, not a boolean — supports multi-recipient channels.
- `in_reply_to` enables threading (request→response pairs).
- No foreign keys to `tasks` table — agents outside the task system (heartbeat, reflection) should also participate.

---

## Message Schema

```json
{
    "id": "uuid",
    "channel_id": "uuid (plan_id or workflow_instance_id)",
    "sender_id": "task:abc12345",
    "sender_agent_type": "architect",
    "recipient_id": "task:def67890 | null (broadcast)",
    "message_type": "request",
    "content": "What database engine should the new table use? We have PostgreSQL and could add SQLite for edge cases.",
    "metadata": {
        "context": "designing storage layer",
        "options": ["postgresql", "sqlite"],
        "urgency": "normal"
    },
    "in_reply_to": null,
    "read_by": [],
    "created_at": "2026-03-28T14:30:00Z",
    "expires_at": null
}
```

### Message Types

| Type | Purpose | Example |
|---|---|---|
| `message` | General communication | "FYI: I found 3 API endpoints that need updating" |
| `request` | Expects a `response` | "What error handling pattern should I use here?" |
| `response` | Reply to a `request` (uses `in_reply_to`) | "Use try/except with specific exception types" |
| `artifact` | Shares a file path or structured output | `{"path": "/home/web3relic/otto/logs/tasks/abc/output.md"}` |
| `signal` | Control signal | `{"signal": "yield", "partial_output": "..."}` |

---

## API Endpoints

All under `/a2a` prefix on the Memory API (port 8100).

### POST /a2a/send

Send a message to a channel.

```json
// Request
{
    "channel_id": "uuid",
    "sender_id": "task:abc12345",
    "sender_agent_type": "architect",
    "recipient_id": "task:def67890",  // optional, null = broadcast
    "message_type": "request",
    "content": "Should we add an index on the status column?",
    "metadata": {},
    "in_reply_to": "uuid"  // optional
}

// Response
{
    "id": "uuid",
    "channel_id": "uuid",
    "created_at": "2026-03-28T14:30:00Z"
}
```

### GET /a2a/poll

Poll for new messages in a channel. Primary read path.

```
GET /a2a/poll?channel_id={uuid}&reader_id={task_id}&since={iso_timestamp}&limit=20
```

**Behavior:**
1. Returns messages in `channel_id` where `created_at > since`
2. Filters to messages where `recipient_id IS NULL` (broadcast) OR `recipient_id = reader_id`
3. Automatically appends `reader_id` to `read_by` for returned messages
4. Returns newest-first for immediate relevance

```json
// Response
{
    "messages": [
        {
            "id": "uuid",
            "sender_id": "task:def67890",
            "sender_agent_type": "coder",
            "message_type": "response",
            "content": "Yes, add a B-tree index on status + created_at composite.",
            "in_reply_to": "uuid",
            "created_at": "2026-03-28T14:31:00Z"
        }
    ],
    "count": 1,
    "channel_id": "uuid"
}
```

### GET /a2a/channel/{channel_id}

Full channel state: participants, message count, unread count.

```json
// Response
{
    "channel_id": "uuid",
    "participants": [
        {"id": "task:abc12345", "agent_type": "architect", "last_seen": "2026-03-28T14:30:00Z"},
        {"id": "task:def67890", "agent_type": "coder", "last_seen": "2026-03-28T14:31:00Z"}
    ],
    "total_messages": 12,
    "source_type": "plan",  // plan | workflow | ad-hoc
    "source_id": "uuid"
}
```

### POST /a2a/channel

Create an ad-hoc channel (for agents not in a shared plan/workflow).

```json
// Request
{
    "participants": ["task:abc12345", "heartbeat"],
    "source_type": "ad-hoc",
    "metadata": {"purpose": "coordinate deployment"}
}

// Response
{
    "channel_id": "uuid"
}
```

---

## Agent Discovery

No separate discovery service. Agents find peers through existing structures:

### In Plan DAGs
```
Plan plan_id → tasks WHERE plan_id = X → each task's agent_type
```
When a task starts, it knows its `plan_id` (from task metadata). It can query other tasks in the same plan to find peers.

### In Workflows
```
Workflow instance_id → workflow_steps → running task per step
```
The workflow engine already tracks which task is executing each step. Agents can query this.

### Discovery API (convenience)

```
GET /a2a/peers?channel_id={uuid}
```

Returns:
```json
{
    "peers": [
        {"id": "task:abc12345", "agent_type": "architect", "status": "running", "title": "Design storage layer"},
        {"id": "task:def67890", "agent_type": "coder", "status": "running", "title": "Implement storage module"}
    ]
}
```

Implementation: for plan channels, queries `tasks WHERE plan_id = channel_id AND status = 'running'`. For workflow channels, queries `workflow_steps` joined with their current task.

---

## Handshake Flow

No formal handshake. Channel existence implies communication is open. The protocol is:

```
1. Task starts → task_runner.sh reads plan_id/workflow_instance_id from task metadata
2. If plan_id or workflow_instance_id exists → channel_id = that UUID
3. Agent injects A2A polling into its execution context (via prompt injection)
4. Agent polls /a2a/poll every 30-60s during execution
5. Agent sends messages via /a2a/send when it has questions, artifacts, or signals
6. On task completion → final message posted automatically (signal: "completed")
```

### Join Announcement (Optional)

When a task starts and has a channel_id, the task_runner.sh posts a join announcement:

```json
{
    "channel_id": "<plan_id>",
    "sender_id": "task:<task_id>",
    "sender_agent_type": "architect",
    "message_type": "signal",
    "content": "Agent joined channel",
    "metadata": {"signal": "join", "title": "Design storage layer"}
}
```

This lets other agents in the channel know a new peer is available.

---

## Integration Points

### 1. task_runner.sh — Channel Setup + Prompt Injection

Add ~15 lines after the task fetch block:

```bash
# ── A2A Channel Setup ──────────────────────────────────────────────
PLAN_ID=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('plan_id') or '')" 2>/dev/null || echo "")
WF_INSTANCE=$(echo "$TASK_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('metadata',{}).get('workflow_instance_id',''))" 2>/dev/null || echo "")
A2A_CHANNEL=""

if [ -n "$PLAN_ID" ]; then
    A2A_CHANNEL="$PLAN_ID"
elif [ -n "$WF_INSTANCE" ]; then
    A2A_CHANNEL="$WF_INSTANCE"
fi

A2A_BLOCK=""
if [ -n "$A2A_CHANNEL" ]; then
    # Post join announcement
    curl -sf -X POST "${API}/a2a/send" \
        -H 'Content-Type: application/json' \
        -d "{\"channel_id\":\"${A2A_CHANNEL}\",\"sender_id\":\"task:${TASK_ID}\",\"sender_agent_type\":\"${AGENT_TYPE}\",\"message_type\":\"signal\",\"content\":\"Agent joined\",\"metadata\":{\"signal\":\"join\",\"title\":\"${TITLE}\"}}" \
        >> "$LOG_FILE" 2>&1 || true

    # Fetch recent messages for context
    RECENT_MSGS=$(curl -sf "${API}/a2a/poll?channel_id=${A2A_CHANNEL}&reader_id=task:${TASK_ID}&limit=10" 2>/dev/null || echo "")

    A2A_BLOCK="
## A2A Channel (Agent-to-Agent Communication)
You are in a multi-agent channel. Other agents working on related tasks can communicate with you.

**To send a message to other agents:**
\`\`\`bash
curl -sf -X POST http://localhost:8100/a2a/send -H 'Content-Type: application/json' -d '{\"channel_id\":\"${A2A_CHANNEL}\",\"sender_id\":\"task:${TASK_ID}\",\"message_type\":\"message\",\"content\":\"YOUR MESSAGE\"}'
\`\`\`

**To check for new messages:**
\`\`\`bash
curl -sf 'http://localhost:8100/a2a/poll?channel_id=${A2A_CHANNEL}&reader_id=task:${TASK_ID}&since=LAST_CHECK_TIME&limit=10'
\`\`\`

**Recent channel activity:**
${RECENT_MSGS}
"
fi
```

The `A2A_BLOCK` is appended to the prompt, giving the agent awareness of the channel and the curl commands to interact.

### 2. tasks.py — Completion Announcement

In `complete_task()`, after the existing plan/workflow hooks, post a completion signal:

```python
# A2A: announce completion to channel
channel_id = task_row.get("plan_id") or (task_row.get("metadata") or {}).get("workflow_instance_id")
if channel_id:
    await pool.execute("""
        INSERT INTO a2a_messages (channel_id, sender_id, sender_agent_type, message_type, content, metadata)
        VALUES ($1, $2, $3, 'signal', $4, $5)
    """, channel_id, f"task:{task_id}", task_row.get("agent_type"),
        f"Task completed: {task_row['title']}",
        json.dumps({"signal": "completed", "exit_code": req.exit_code, "output_excerpt": (req.output or "")[:500]}))
```

### 3. task_plans.py — Channel Auto-Creation

When `execute_plan()` launches tasks, it already sets `plan_id` on each task. The channel is implicit — `plan_id` IS the `channel_id`. No explicit channel creation needed for plans.

### 4. workflows.py — Channel Auto-Creation

Same pattern: `workflow_instance_id` IS the `channel_id`. Already stored in task metadata.

### 5. heartbeat.md / reflection.md — Channel Awareness

The heartbeat and reflection agents can participate in channels as `heartbeat` and `reflection` sender IDs. Useful for:
- Heartbeat posting directives to running plan channels
- Reflection posting performance observations to active workflow channels

---

## Lifecycle & Cleanup

Messages inherit the lifecycle of their channel source:

- **Plan channels**: Messages deleted when plan moves to `completed` or `failed` (or after 7 days, whichever is first)
- **Workflow channels**: Messages deleted when workflow instance completes (or after 7 days)
- **Ad-hoc channels**: Expire after 24 hours of no activity

Cleanup runs in the existing maintenance cycle (02:00 + 14:00 daily):

```sql
-- Clean up messages from completed plans (older than 7 days)
DELETE FROM a2a_messages
WHERE channel_id IN (
    SELECT id FROM task_plans WHERE status IN ('completed', 'failed') AND completed_at < now() - INTERVAL '7 days'
)
OR (expires_at IS NOT NULL AND expires_at < now());
```

---

## Implementation Plan

### Phase 1: Foundation (~$3, 1 task)

1. **Migration 077**: Create `a2a_messages` table with indexes
2. **New route file**: `memory/routes/a2a.py` — 4 endpoints (send, poll, channel, peers)
3. **Wire into api.py**: Add router
4. **Test**: Manual curl test — send message, poll it back

Smallest deployable unit. Agents can't use it yet, but the API exists.

### Phase 2: Agent Integration (~$2, 1 task)

1. **task_runner.sh**: Add A2A channel setup + prompt injection block (~15 lines)
2. **tasks.py**: Add completion announcement to `complete_task()`
3. **Test**: Run a 2-task plan, verify agents see each other's messages

This is where agents actually start communicating.

### Phase 3: Intelligence (~$2, future)

1. **A2A-aware routing**: AdaptOrch considers channel activity when routing tasks
2. **Request/response protocol**: Agent blocks on a request, polls for response with timeout
3. **Cleanup in maintenance**: Wire into existing maintenance timer

---

## Risks

| Risk | Mitigation |
|---|---|
| **Polling overhead**: 5 agents polling every 30s = 10 queries/min | Lightweight indexed query. PostgreSQL handles this trivially. Monitor via `/a2a/channel` stats |
| **Prompt bloat**: A2A block + recent messages inflate prompt | Cap at 10 recent messages, 200 chars each. Skip A2A block for low-effort tasks |
| **Agent ignores A2A**: CLI agents may not use the curl commands | Low risk — agents follow injected instructions well. Monitor usage via `read_by` array fill rate |
| **Message storms**: Chatty agents flood channel | Rate limit: max 20 messages per sender per channel per hour. Enforce in `/a2a/send` |
| **Dead letter messages**: Recipient task already completed | No harm — messages persist but are never read. Cleanup handles it |
| **DB growth**: Many messages accumulate | 7-day TTL + maintenance cleanup. Messages are small text rows |

---

## What This Is NOT

- **Not a chat system**: Agents send structured messages for coordination, not conversation
- **Not pub-sub**: No subscriptions, no events, no callbacks. Simple polling
- **Not replacing plan DAGs**: DAGs still handle dependency ordering. A2A adds a communication layer on top
- **Not replacing workflow step chaining**: `{prev_output}` still flows through steps. A2A enables side-channel communication
- **Not an external protocol**: This is internal Otto infrastructure. External A2A (cross-system) is a separate future concern

---

## Estimated Cost

| Phase | Effort | Cost |
|---|---|---|
| Phase 1: Foundation | 1 task, ~30 turns | ~$3 |
| Phase 2: Agent Integration | 1 task, ~25 turns | ~$2 |
| Phase 3: Intelligence | Future, deferred | ~$2 |
| **Total (Phase 1+2)** | **2 tasks** | **~$5** |

---

## Appendix: Comparison with STEM A2A

| Aspect | STEM Agent | Otto A2A |
|---|---|---|
| Transport | Protocol-agnostic gateway | PostgreSQL + HTTP polling |
| Discovery | Registry service | Derived from plan/workflow membership |
| Delivery | Push-based | Poll-based (30-60s) |
| Threading | Conversation IDs | `in_reply_to` UUID references |
| Multi-protocol | A2A + AG-UI + A2UI + UCP + AP2 | A2A only (others not needed yet) |
| Complexity | High (5 protocol adapters) | Low (1 table, 4 endpoints) |

Otto's approach is deliberately simpler. STEM targets heterogeneous multi-system deployments. Otto targets homogeneous agents on a single VM. The design can evolve toward STEM's model if Otto scales to distributed nodes.

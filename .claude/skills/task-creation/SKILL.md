---
name: task-creation
description: Create well-formed tasks in Otto's task queue. Use when delegating work to the task queue system.
user-invocable: false
---

## Task Queue API

### Create a task
```bash
curl -s -X POST http://localhost:8100/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "[P#] Short descriptive title",
    "prompt": "Detailed instructions...",
    "priority": 7,
    "model": "sonnet",
    "cli": "claude",
    "agent_type": "",
    "max_budget_usd": 5.0,
    "timeout_seconds": 3600,
    "created_by": "heartbeat"
  }'
```

### Task sizing

| Type | Model | Budget | Timeout | Agent |
|------|-------|--------|---------|-------|
| Quick lookup | haiku | $0.50 | 300s | — |
| Research | sonnet | $5 | 3600s | researcher |
| Coding (P1-P7) | sonnet | $5-10 | 3600s | coder |
| Coding (P8-P10) | sonnet | $10 | 3600s | coder |
| Heavy reasoning | opus | $15 | 7200s | architect |
| Code review | sonnet | $2 | 600s | reviewer |
| Bug fix | sonnet | $5 | 3600s | debugger |
| Memory maintenance | haiku | $1 | 600s | memory-curator |

### Specialist agents (`agent_type` field)

Set `agent_type` to route the task through a specialist agent:
- `researcher` — papers, APIs, web research
- `coder` — building features, implementing changes
- `reviewer` — code review (read-only)
- `debugger` — root cause analysis and fixes
- `architect` — system design, API design
- `memory-curator` — memory cleanup and consolidation

The task runner loads the agent automatically if the `.md` file exists.

### Queue management
```bash
# Check capacity
curl -sf http://localhost:8100/tasks/queue/status

# Launch a task
curl -sf -X POST http://localhost:8100/tasks/<id>/run

# List pending tasks
curl -sf 'http://localhost:8100/tasks?status=pending&limit=5'
```

### Rules

- Always map tasks to a priority (P1-P10)
- Set `agent_type` when the task matches a specialist
- Minimum $5 budget for Claude tasks (non-trivial work)
- Minimum 3600s timeout for coding tasks
- Don't retry failed tasks blindly — analyze why first

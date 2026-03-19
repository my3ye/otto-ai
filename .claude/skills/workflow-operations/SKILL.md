# Workflow Operations

Use multi-agent workflows for any work that benefits from sequential specialist agents (draft→review→revise→implement).

## Available Templates

| Template | Steps | Variables |
|---|---|---|
| `content-publishing-pipeline` | content-creator → reviewer → content-creator → coder → notify | `content_type`, `topic`, `requirements` |
| `feature-development` | architect → coder → reviewer → debugger → notify | `feature_description`, `requirements` |

## Start a Workflow

```bash
curl -s -X POST http://localhost:8100/workflows/start \
  -H 'Content-Type: application/json' \
  -d '{
    "template_name": "content-publishing-pipeline",
    "name": "Human-readable name for this run",
    "variables": {"content_type": "article", "topic": "SOS Systems", "requirements": "Long-form for Paragraph + X thread"},
    "priority": 7,
    "working_directory": "/home/web3relic/otto"
  }'
```

## Check Workflow Status

```bash
# Dashboard
curl -s http://localhost:8100/workflows/dashboard

# List running instances
curl -s 'http://localhost:8100/workflows/instances?status=running'

# Instance detail (step progress, outputs, eval scores)
curl -s http://localhost:8100/workflows/instances/<id>
```

## Approve/Reject Paused Steps

When a step has `review_mode: "human_approval"`, the workflow pauses. To resume:

```bash
# Approve and advance
curl -s -X POST http://localhost:8100/workflows/instances/<id>/approve \
  -H 'Content-Type: application/json' -d '{"action": "approve"}'

# Reject (stops workflow)
curl -s -X POST http://localhost:8100/workflows/instances/<id>/approve \
  -H 'Content-Type: application/json' -d '{"action": "reject", "reason": "needs X"}'

# Skip step and continue
curl -s -X POST http://localhost:8100/workflows/instances/<id>/approve \
  -H 'Content-Type: application/json' -d '{"action": "skip"}'
```

## Retry / Cancel

```bash
curl -s -X POST http://localhost:8100/workflows/instances/<id>/retry
curl -s -X POST http://localhost:8100/workflows/instances/<id>/cancel
```

## Create a New Template

```bash
curl -s -X POST http://localhost:8100/workflows/templates \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "my-pipeline",
    "description": "What this pipeline does",
    "steps": [
      {"position": 0, "name": "Step Name", "agent_type": "coder", "prompt_template": "Do X with {topic}. Previous output: {prev_output}", "review_mode": "auto", "max_budget_usd": 5.0, "timeout_seconds": 900, "on_failure": "retry_once"},
      {"position": 1, "name": "Notify", "action": "notify", "notify_template": "Done: {workflow_name}"}
    ],
    "tags": ["custom"]
  }'
```

### Prompt Template Variables
- `{prev_output}` — output of the immediately preceding step
- `{step_N_output}` — output of step N specifically (e.g. `{step_0_output}`)
- `{workflow_name}` — instance name
- `{working_directory}` — resolved working directory
- Any key from `variables` dict (e.g. `{topic}`, `{content_type}`)

### Step Options
- `review_mode`: `auto` | `human_approval` | `agent_review`
- `on_failure`: `retry_once` | `pause` | `skip` | `fail_workflow`
- `action: "notify"` — sends WhatsApp notification instead of creating a task

## Evolution & Auto-Eval

Every completed workflow run is auto-evaluated. Every 3 runs, the engine mutates the template to improve fitness.

```bash
# Check evolution history
curl -s http://localhost:8100/workflows/templates/<id>/experiments

# Check fitness over time
curl -s http://localhost:8100/workflows/templates/<id>/fitness

# Manually trigger evolution
curl -s -X POST http://localhost:8100/workflows/templates/<id>/evolve
```

## Available Agents (138 from agency-agents repo)

```bash
# List all available unemployed agents
curl -s http://localhost:8100/workflows/agents/available | python3 -c "
import json,sys
d = json.load(sys.stdin)
for a in d['agents'][:20]:
    status = 'ACTIVE' if a['activated'] else 'available'
    print(f'  [{a[\"category\"]}] {a[\"name\"]} ({status})')
"

# Activate an agent
curl -s -X POST http://localhost:8100/workflows/agents/activate \
  -H 'Content-Type: application/json' \
  -d '{"name": "Agent Name", "source_path": "/mnt/media/projects/agency-agents/category/file.md"}'
```

## When to Use Workflows vs Single Tasks

| Scenario | Use |
|---|---|
| Write an article / landing page / content | `content-publishing-pipeline` workflow |
| Build a feature with code review | `feature-development` workflow |
| Quick fix, config change, research | Single task |
| One-off debug or investigation | Single task |

# Task Runner

Demonstrates the Task Queue: create a task, launch it, poll for completion.

## Run

```bash
# From the otto-ai root directory:
docker compose up -d

cd examples/task-runner
pip install requests
python example.py
```

## What it demonstrates

- `POST /tasks` — create a task with title, prompt, priority, budget
- `POST /tasks/{id}/run` — launch as a detached subprocess
- `GET /tasks/{id}` — poll for completion
- `GET /tasks/queue/status` — queue summary

## How tasks work

1. You create a task (title + prompt + constraints)
2. You launch it — a detached subprocess starts running
3. You poll (or hook, or move on) — the task reports back when done
4. The output is stored in the DB, readable any time

This is how you coordinate multiple agents: each does one thing well,
they communicate through the shared task queue and memory.

## Note on the LLM runner

Tasks run via `task_runner.sh`. If `claude` CLI is not installed,
the task completes immediately with a "not found" message.

To install Claude CLI: https://claude.ai/code

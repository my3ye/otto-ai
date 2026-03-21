# Multi-Agent Coordination

Two agents coordinate through shared memory — no direct communication, no shared process.

## Run

```bash
# From the otto-ai root directory:
docker compose up -d

cd examples/multi-agent
pip install requests
python orchestrate.py
```

## What it demonstrates

- **Sessions** — each agent starts and ends its own session
- **Episodic events** — agents log what they're doing and why
- **Semantic memory as the shared layer** — Agent A stores findings, Agent B searches them

## The pattern

```
Agent A (Researcher)          Agent B (Synthesizer)
         │                              │
         │ POST /semantic/remember      │ POST /semantic/search
         │ (stores findings)            │ (retrieves by meaning)
         │                              │
         └──────── Shared Memory ───────┘
                   (PostgreSQL)
```

Agents don't need to know about each other. They share a memory system.
This scales: 10 agents can all write to and read from the same memory layer.

## Why this matters

Most multi-agent frameworks require agents to run in the same process or communicate via message passing. Otto AI's memory-first approach means:

- Agents can be in different languages, different machines, different timezones
- Any agent can pick up where another left off
- The collaboration history is auditable (episodic log)
- Memory persists even if all agents crash and restart

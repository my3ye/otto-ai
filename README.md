# Otto AI

> Build autonomous AI agents that think, remember, and act — without calling home to OpenAI or Anthropic.

Otto AI is the intelligence infrastructure for the [MY3YE ecosystem](https://my3ye.xyz). It runs in production, coordinating real agents for real work. This is not a demo. This is the same system you are about to extend.

---

## What You Can Build in 10 Minutes

**An agent that remembers:**
```bash
# Store a memory
curl -X POST http://localhost:8100/semantic/remember \
  -H 'Content-Type: application/json' \
  -d '{"content": "User prefers short responses", "category": "preference", "confidence": 0.9}'

# Recall it
curl -X POST http://localhost:8100/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "user preferences", "limit": 5}'
```

**An agent that acts:**
```bash
# Create a task
curl -X POST http://localhost:8100/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Research this topic",
    "prompt": "Find everything about X and report back",
    "priority": 7,
    "budget_usd": 1.0
  }'

# Launch it (replace $TASK_ID with the id returned above)
curl -X POST http://localhost:8100/tasks/$TASK_ID/run
```

---

## Architecture

Otto AI has four core layers:

| Layer | What it does |
|-------|-------------|
| **Semantic Memory** | Persistent vector memory — store facts, search by meaning |
| **Episodic Events** | Timestamped event log — what happened, when, how important |
| **Procedural Learning** | Named procedures that accumulate trust from outcomes |
| **Task Queue** | Detached agent execution — create, launch, monitor, review |

Everything runs in Docker. One command to start.

---

## Install & Run

```bash
git clone https://github.com/my3ye/otto-ai
cd otto-ai
cp .env.example .env   # add your OPENAI_API_KEY
docker compose up -d

# Verify
curl http://localhost:8100/health
```

Read the full [Quickstart Guide](docs/quickstart.md) for step-by-step setup.

---

## Three Things to Build

### 1. Build for SOS Systems
**Challenge:** A resource coordination agent that works offline and routes aid to the people who need it most — not the ones with the fastest internet.

Real impact: This becomes actual infrastructure for SOS Systems' coordination layer.

### 2. Build for ONEON
**Challenge:** An identity application that carries contribution history across communities.

Real impact: The first portable reputation layer for a decentralized world.

### 3. Build for Otto AI itself
**Challenge:** Extend the intelligence. Write a connector, a new agent type, a memory strategy, a reasoning plugin.

The infrastructure is live. The memory is running. You are not building a sandbox — you are building a node that stays alive after the weekend ends.

→ [Full hackathon track details](docs/hackathon-tracks.md)

---

## Examples

| Example | What it shows |
|---------|--------------|
| [hello-memory](examples/hello-memory/) | Store and retrieve semantic memories |
| [task-runner](examples/task-runner/) | Create, launch, and poll a task |
| [multi-agent](examples/multi-agent/) | Two agents coordinate through shared memory |

---

## Live Now

- **Production system:** [webassist.ink](https://webassist.ink) — autonomous agent routing for real users
- **Open pallets:**
  - [pallet-dpc](https://github.com/ottomev/pallet-dpc) — contribution-weighted governance (Polkadot)
  - [pallet-oneon-identity](https://github.com/ottomev/pallet-oneon-identity) — sovereign identity (Polkadot People Chain)

---

## Documentation

- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [API Reference](docs/api-reference.md)
- [Hackathon Tracks](docs/hackathon-tracks.md)

---

## The Mission

We built Otto AI because we needed it. Not to sell it. To run our own ecosystem — a parallel civilization stack, bootstrapped, built in public.

When you build on Otto AI, contribution is tracked. The work outlives the hackathon. The memory persists.

**#BuildWithOtto**

---

*Otto AI is part of the [MY3YE ecosystem](https://my3ye.xyz)*
*Questions: hello@my3ye.xyz*

---

MIT License

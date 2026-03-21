# Otto AI — Getting Started

> Build autonomous AI agents that think, remember, and act — without calling home to OpenAI or Anthropic.

Otto AI is the intelligence infrastructure for the MY3YE ecosystem. It runs in production, coordinating real agents for real work. This is not a demo. This is the same system you are about to extend.

---

## What You Can Build in 10 Minutes

**An agent that remembers:**
```bash
# Store a memory
curl -X POST http://your-agent/semantic/remember \
  -H 'Content-Type: application/json' \
  -d '{"content": "User prefers short responses", "category": "preference", "confidence": 0.9}'

# Recall it
curl -X POST http://your-agent/semantic/search \
  -H 'Content-Type: application/json' \
  -d '{"query": "user preferences", "limit": 5}'
```

**An agent that acts:**
```bash
# Create a task
curl -X POST http://your-agent/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Research this topic",
    "prompt": "Find everything about X and report back",
    "priority": 7,
    "budget_usd": 1.0
  }'

# Launch it
curl -X POST http://your-agent/tasks/{id}/run
```

---

## Architecture

Otto AI has four core layers:

| Layer | What it does |
|-------|-------------|
| **Memory API** | Persistent semantic memory, episodic events, knowledge graph, procedural learning |
| **Task Queue** | Detached agent execution — create, launch, monitor, review |
| **Reasoning Kernel** | Interrupt-driven cognitive loop — processes all inputs through a single coherent path |
| **Agent Registry** | Specialist agents for content, research, code, security, and more |

Everything is open. Nothing requires a platform's permission.

---

## Three Things to Build at the Hackathon

### 1. Build for SOS Systems
**Challenge:** A resource coordination agent that works offline and routes aid to the people who need it most — not the ones with the fastest internet.

The agent should: accept structured requests → match to available resources → output distribution instructions that work in mesh-only environments.

Real impact: This becomes actual infrastructure for SOS Systems' coordination layer.

### 2. Build for ONEON
**Challenge:** An identity application that carries contribution history across communities.

The agent should: verify contributions via ONEON's identity protocol → issue verifiable credentials → allow developers to prove what they built, not just who they are.

Real impact: The first portable reputation layer for a decentralized world.

### 3. Build for Otto AI itself
**Challenge:** Extend the intelligence. Write a connector, a new agent type, a memory strategy, a reasoning plugin.

The infrastructure is live. The memory is running. You are not building a sandbox — you are building a node that stays alive after the weekend ends.

---

## Live Now

- **Production system:** webassist.ink — autonomous agent routing for real users
- **Agent infrastructure:** 300+ tasks executed, memory persists, agents coordinate
- **Open pallets:**
  - [pallet-dpc](https://github.com/ottomev/pallet-dpc) — contribution-weighted governance (Polkadot)
  - [pallet-oneon-identity](https://github.com/ottomev/pallet-oneon-identity) — sovereign identity (Polkadot People Chain)

---

## Install & Run

```bash
# Clone and run the memory API
git clone https://github.com/my3ye/otto-ai
cd otto-ai
docker compose up -d

# Verify
curl http://localhost:8100/health
```

*Note: Full docker-compose setup in /docs/quickstart.md*

---

## The Mission

We built Otto AI because we needed it. Not to sell it. To run our own ecosystem — a parallel civilization stack, bootstrapped, built in public.

When you build on Otto AI, contribution is tracked. The work outlives the hackathon. The memory persists.

**#BuildWithOtto**

---
*Otto AI is part of the MY3YE ecosystem — my3ye.xyz*
*Questions: hello@my3ye.xyz*

---
**DRAFT NOTE:** This README needs a real GitHub repo URL before going public.
Replace `https://github.com/my3ye/otto-ai` with actual repo once Mev creates/makes public.

# EasyA Hackathon Tracks

Three tracks to build on during the hackathon. Each is a real challenge with real impact — winning projects may become part of the MY3YE ecosystem.

---

## Track 1: Build for SOS Systems

**The Challenge:** Resource coordination under constraint.

Build an agent that routes aid to people who need it most — in environments where internet is patchy, central servers are unavailable, and data is messy.

**What to build:**
An agent that accepts structured resource requests (food, medicine, shelter), matches to available supply based on proximity and urgency, and outputs distribution instructions that work in mesh-only or offline environments.

**Technical hooks:**
- Use the Episodic API to log coordination events (request received, resource assigned, distribution confirmed)
- Use the Semantic API to remember resource inventory, agent locations, and outcome history
- Use the Task Queue to pipeline multi-step coordination (assess → match → route → confirm)

**Real impact:** This becomes actual infrastructure for SOS Systems' coordination layer. Aid distribution in conflict zones and disaster areas runs today on improvised spreadsheets. You can do better.

**What the winning project looks like:**
- Accepts a resource request in natural language or structured format
- Returns a distribution plan with ranked recipients and routing instructions
- Works with intentionally degraded or missing data (real conditions)

---

## Track 2: Build for ONEON

**The Challenge:** Portable, sovereign identity.

Build an application that carries contribution history across communities — not who you are, but what you've built.

**What to build:**
An agent that verifies contributions (code commits, governance votes, community work), stores them as persistent credential claims, and presents a proof that survives moving between communities, chains, and platforms.

**Technical hooks:**
- Use the Semantic API to store verifiable contributions with confidence scores
- Use the Episodic API to track credential issuance events
- Use the Procedural API to encode and reuse verification protocols

**Substrate pallets available:**
- [pallet-oneon-identity](https://github.com/ottomev/pallet-oneon-identity) — sovereign identity on Polkadot People Chain
- [pallet-dpc](https://github.com/ottomev/pallet-dpc) — contribution-weighted governance

**Real impact:** The first portable reputation layer for a decentralized world. When you've proven yourself in one ecosystem, that proof travels with you.

**What the winning project looks like:**
- Takes a contribution event (GitHub PR, on-chain vote, community action)
- Issues a verifiable credential stored in the Otto AI memory system
- Presents proof in a way that any other system can validate

---

## Track 3: Extend Otto AI

**The Challenge:** Make the intelligence better.

The infrastructure is live. The memory is running. Extend it — a new connector, a new agent type, a memory strategy, a reasoning plugin.

**Ideas (pick one or bring your own):**

**Multi-agent coordination:** Build an orchestrator that spawns specialist agents (researcher, coder, reviewer), coordinates through shared memory, and produces a final output no single agent could produce alone.

**Memory evolution:** Implement a system that automatically decays low-confidence memories and reinforces high-relevance ones based on usage patterns. The memory should get smarter over time.

**Cross-chain knowledge graph:** Build a connector that ingests on-chain events (transfers, contract calls, governance votes) into the Episodic API and makes them searchable via the Semantic API.

**Autonomous monitoring:** An agent that watches a contract, logs anomalies to Episodic memory, and pages you (via any webhook) when something crosses a threshold.

**Technical hooks:**
- All Memory API endpoints are available
- The Task Queue supports any agent_type — bring your own specialists
- Sessions provide continuity across multiple agent runs

**Real impact:** Extensions that survive the hackathon get proposed for merge into the main codebase. Your agent could run in production.

---

## Getting Started

```bash
git clone https://github.com/my3ye/otto-ai
cd otto-ai
cp .env.example .env  # add your OPENAI_API_KEY
docker compose up -d
curl http://localhost:8100/health
```

Then pick a track and start building. The API reference is in [docs/api-reference.md](api-reference.md).

Questions: hello@my3ye.xyz | #BuildWithOtto

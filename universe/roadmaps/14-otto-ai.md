# Otto AI — Comprehensive Roadmap
*Decentralized intelligence governed by community. The mind of the civilization.*
*Last updated: 2026-03-16*

## Current Status
**LIVE** — Single VM (otto-machine). AgentOS operational. Dual heartbeat. Memory API. Task queue. WhatsApp interface. Management UI.

## Dependencies
- **Hard deps:** ONEON (auth for multi-instance, device identity)
- **Soft deps:** S0S Systems (governance of capability decisions), Ottolabs (distributed hardware)
- **Blocks:** OMS capabilities, all project intelligence, Broadcast system

---

## Phase 1 — Operational Excellence (NOW → 30 days)
**Goal:** Single-instance Otto is reliable, efficient, and well-documented.

### Milestones
1. **RL2F recovery** — RL2F score back to ≥70% (currently 54%, declining). Needs active matched prediction entries.
2. **Reactive dispatch fixed** — Priority-scaled budgets deployed (COMPLETED 7553e0d)
3. **Architecture documented** — AgentOS whitepaper draft: what Otto is, how it works, how to deploy
4. **Broadcast system active** — Posting consistently to X + Telegram (not just manually triggered)
5. **OMS LIVE mode** — Mode switcher implemented; LIVE mode designed for what it will show

### Success Criteria
- RL2F ≥70% (sustained 5+ cycles)
- 0 heartbeat timer outages (self-healing verified)
- Architecture document complete enough for external contributor
- Broadcast posting ≥3x/week automatically

---

## Phase 2 — Multi-Instance (30→90 days)
**Goal:** Otto runs on multiple VMs with shared memory. No single point of failure.

### Milestones
1. **Backup/restore tested** — otto-backup.sh and otto-restore.sh verified on a second VM
2. **Shared memory layer** — Postgres + pgvector shared across instances (connection pooler)
3. **Session handoff protocol** — When Instance A goes down, Instance B continues with full context
4. **Geographic distribution** — Primary: GCP europe/asia. Secondary: different region.
5. **Load-balanced heartbeats** — Multiple heartbeat instances don't conflict

### Success Criteria
- Otto survives primary VM failure without data loss
- Session continuity: ≤60 second gap between instances
- Memory fully consistent across instances
- Recovery from VM failure automated, not requiring Mev intervention

---

## Phase 3 — Otto Agent Framework (90 days → 6 months)
**Goal:** External operators can deploy their own Otto agents. Protocol documented.

### Milestones
1. **Otto Agent Framework v0.1** — Open-source: deploy your own Otto instance
2. **Standardized memory format** — Any Otto agent can read any other Otto agent's memory
3. **Inter-agent communication** — Agents can send tasks to each other
4. **Contribution scoring** — DPC credit for running an Otto node
5. **First external operator** — Someone outside MY3YE deploys an Otto agent
6. **ONEON integration** — Otto agent identity linked to ONEON identity

### Success Criteria
- Framework documented: deployment guide, architecture overview
- 5+ external operators running Otto agents
- Inter-agent task delegation working
- ONEON identity linking functional

---

## Phase 4 — Distributed Protocol (6→18 months)
**Goal:** Otto runs on Ottolabs devices. No central server. Community-governed.

### Milestones
1. **Puck-native Otto** — Otto agent running on Otto Puck hardware
2. **Federated memory** — Memories shared across a network of Otto agents (with consent)
3. **On-chain capability governance** — What Otto can/can't do is voted on by S0S
4. **Community-trained capabilities** — Improvements voted in, deployed across all instances
5. **100+ deployed agents**

### Success Criteria
- Otto running on Puck hardware
- Federated memory with ≥10 participating instances
- At least 1 community governance vote on capability decisions
- 100 active Otto agent deployments

---

## Current Architecture (Phase 1)

| Component | Status | Notes |
|-----------|--------|-------|
| AgentOS Reasoning Kernel | ✅ Live | IVT, RIC, S-MMU all operational |
| Dual heartbeat (orchestrator + reflection) | ✅ Live | Hourly cycles |
| Memory API (FastAPI :8100) | ✅ Live | PostgreSQL + pgvector + Neo4j |
| HyMem (dual-granularity retrieval) | ✅ Live | Semantic search operational |
| MARS (adversarial reflection) | ✅ Live | Dual critic active |
| RL2F (feedback learning) | ⚠️ Declining | 54%, needs active entries |
| WhatsApp interface | ✅ Live | Ottolabs account |
| Task queue | ✅ Live | Max 5 concurrent |
| Broadcast system | ⚠️ Manual | Needs automation |
| OMS (mev.otto.lk) | ✅ Live | 10+ pages |

## The Big Vision
Today: one VM, one mind, helping Mev build.
Tomorrow: millions of devices, millions of minds, helping everyone build.

The transition is a protocol, not a product launch. Otto is proving the architecture works, then opening it to the world.

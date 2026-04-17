---
name: Research Superior Patterns Architecture
description: 13-implementation plan across 4 phases to close research-paper gaps in Otto. IMPL-01 (idle tagging) and IMPL-02 (stagnation pivot) are P0 — fix measurement before adding capability. Only 2 migrations needed (096, 097).
type: project
---

Research-superior patterns architecture designed 2026-04-17. 12 code-verified gaps from 25+ papers.

**Why:** AutoEvolve frozen 30 days (gen=7, 0 experiments). RL2F accuracy inflated at 0.72 (idle cycles counted). Learning loops stagnating.

**How to apply:** Phase 1 (fix degradation) must complete before Phase 2-4 provide value. IMPL-01 (RL2F idle tagging) is the unlock — without it, you can't measure whether other changes help. Key correction from code verification: heartbeat.md already tags idle_cycle in metadata, but rl2f.py doesn't filter by it. The data exists; the queries ignore it.

Stagnation root cause: reflection.md prompt already handles DEGRADED classification, but AutoEvolve budget gate blocks experiment creation even when stagnation is detected. Fix is code-level force-experiment endpoint, not another prompt change.

Full spec at ~/otto/docs/research-superior-patterns-architecture-2026-04-17.md.

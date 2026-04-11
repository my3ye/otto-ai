---
name: CORAL arXiv 2604.01658 Synthesis
description: CORAL multi-agent evolution paper synthesis — 2 structural Otto gaps confirmed (stagnation-pivot, cross-task leaderboard), skill extraction already implemented in tasks.py, ZK routing error documented
type: project
---

## Key Insights

1. CORAL (MIT/NUS/Stanford) = multi-agent evolutionary search framework, NOT a ZK paper. ZK task tag was a routing error — zero ZK content.
2. Otto and CORAL are architecturally isomorphic in 4 of 6 dimensions (worktree isolation, per-agent notes, heartbeat, skill extraction).
3. Skill extraction: IMPLEMENTED in `memory/routes/tasks.py:_extract_skill_from_task` — downgraded from gap claim.
4. Stagnation detection: TRUE GAP — grep `stagnation|consecutive|non.improving` returns only a comment string in autoevolve.py, no counter/pivot logic.
5. Cross-task leaderboard: TRUE GAP — grep `leaderboard|best_attempt|cross.agent` returns zero hits in otto/memory/.
6. CORAL's 36% cross-agent parentage → 17% improvement rate proves shared memory coordination value.

## Recommended Actions
1. Add stagnation counter to RL2F/autoevolve: after 5 consecutive failures on same task type, trigger strategy pivot
2. Add `GET /tasks/top-outputs` endpoint — best completed task outputs queryable by future agents
3. No ZK action needed — task routing error, not a content gap

memory_write_token: 59450ffd-dc77-404d-8a10-3584beefed7a

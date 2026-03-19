---
name: onchain_task_system_2026_03
description: Onchain task system Phase 1 design decisions and implementation status (2026-03-20)
type: project
---

# Onchain Task System Phase 1 — Implemented 2026-03-20

Migration 062 applied. Columns added: upvotes, dependency_score, chain_id, chain_hash, chain_anchored_at.
Priority formula: 0.5*(priority/10) + 0.3*dependency_score + 0.2*(upvotes/(upvotes+10))
Endpoints: POST /tasks/{id}/upvote, POST /tasks/{id}/set-dependency-score.

Why: Mev directive to move tasks on-chain with community voting and bounties.
How to apply: Phase 2 = smart contracts (TaskRegistry + EscrowVault + EvaluationVoting on EVM L2).
Note: Must implement Sybil detection BEFORE opening public voting.

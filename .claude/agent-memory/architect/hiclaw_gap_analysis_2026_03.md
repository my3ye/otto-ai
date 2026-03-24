---
name: hiclaw_gap_analysis_2026_03
description: HiClaw vs Otto gap analysis (2026-03-24). 3 real gaps identified. Full doc location.
type: project
---

Otto already matches HiClaw's core architecture (manager-workers, DAG decomposition, memory hierarchy, workflow chains). Analysis confirmed 3 actionable gaps:

**GAP-1 (LOW risk, medium effort):** Credential isolation — task_runner.sh inherits ANTHROPIC_API_KEY directly. HiClaw uses gateway-token pattern (workers get scoped tokens only). Actual risk is low on single-tenant VM since claude CLI holds keys, not task_runner. Fix: /llm/proxy endpoint in Memory API.

**GAP-2 (HIGH value, ~$2):** Artifact path references — task outputs >2KB should be written to ~/otto/logs/tasks/{id}/output.md with path stored in DB payload, not full text. Prevents DB bloat and context inflation in task chaining. Mirrors HiClaw's MinIO pattern on local FS.

**GAP-3 (PROMPT fix):** Consistency — heartbeat sometimes creates sequential tasks directly (POST /tasks) instead of routing through plan system (POST /task-plans). Single-step: direct is fine. Multi-step: always use task-plans.

**Why:** Full doc at ~/otto/docs/hiclaw-otto-gap-analysis-2026-03-24.md
**How to apply:** When proposing new task orchestration patterns, default to task-plans for multi-step work. When touching task completion flows, consider artifact path pattern for large outputs.

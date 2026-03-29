---
name: DAG executor unmet deps bug
description: Plan tasks launched before dependencies complete — root cause was /tasks/{id}/run endpoint bypassing dependency checks
type: project
---

DAG executor launched tasks before their depends_on tasks completed (plan 9a40a60f, salary contracts, 2026-03-29).

**Root cause:** The `/tasks/{id}/run` endpoint had NO dependency check. The heartbeat agent scanned for pending tasks and called this endpoint directly, bypassing the plan executor's DAG dependency logic entirely. The plan executor's own SQL query was correct.

**Why:** The run endpoint was built before the plan/dependency system existed and never updated to check depends_on.

**How to apply:** When adding new gating logic (dependencies, decomposition, ownership), check ALL code paths that can launch tasks — not just the DAG executor. The run_task endpoint, heartbeat, and any auto-launcher all need the same guards.

**Fix (commit 1254336):**
1. Dependency gate on `run_task()` in tasks.py — returns 409 if unmet deps
2. Transaction wrapping plan+task creation in task_plans.py
3. Pre-launch dep guard in `_launch_task()`
4. Atomic CAS task claiming (prevents double-launches)

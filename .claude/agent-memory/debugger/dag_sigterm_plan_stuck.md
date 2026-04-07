---
name: DAG SIGTERM plan counter fix
description: stop_task() and reconcile_and_fix() bypassed plan/workflow DAG hooks, leaving plans permanently stuck when tasks were killed or zombie-reconciled
type: project
---

Fixed 2026-04-07: Two code paths in tasks.py set task status to 'failed' without firing on_plan_task_complete() or check_workflow_advance():

1. `stop_task()` (manual stop / SIGTERM) — marks task failed, sends SIGTERM, but never notifies the plan DAG
2. `reconcile_and_fix()` (zombie cleanup) — marks zombie/missed-callback tasks as failed/completed but never notifies plan DAG

**Why:** Plans depend on `on_plan_task_complete()` to increment counters, skip dependents of failed tasks, and call `_finalize_plan()`. Without it, plans stay in 'executing' forever with running=0.

**How to apply:** Any new code path that transitions a task to completed/failed/cancelled MUST also fire the same downstream hooks as `complete_task()`: at minimum `on_plan_task_complete()` and `check_workflow_advance()`. Grep for "status = 'failed'" in tasks.py to audit.

---
name: cancelled_task_implementation_review
description: Code review of cancelled_at/cancelled_by column + stop/cancel lifecycle reroute (migration 087, commits 188d9df/2b6a823, 2026-04-11)
type: project
---

NEEDS_CHANGES — 8.5/10. Core design is solid and correct. 1 critical race condition in stop_task running path, 1 cosmetic bug in propagation message, 1 low-severity audit spoofing vector.

**Why:** The stop/cancel lifecycle reroute is a material improvement (stopped≠failed, propagation on cancel), but the stop_task UPDATE for running tasks lacks a status guard — a completing task could be overwritten as cancelled.

**How to apply:** Before merging/deploying into production workflows, fix the WHERE clause in stop_task and the close_output ternary. Low-traffic internal API so risk is tolerable short-term.

Critical: stop_task() running path UPDATE has no status guard (tasks.py ~line 1664): `WHERE id = $1` should be `WHERE id = $1 AND status = 'running'`. Race condition: if task completes between SELECT and UPDATE, the completed row gets overwritten as cancelled.

Warning: close_output ternary in _propagate_completion() (tasks.py ~line 926-930) only has 2 branches for 3 states. When parent_status='failed', message says "all subtasks completed" — factually wrong. Fix: handle 3 states explicitly.

Warning: cancelled_by is an unvalidated query param on POST /cancel (tasks.py ~line 1600). Any caller can pass `?cancelled_by=anything`. Low risk (internal only, not used in control flow) but spoofs audit trail. Fix: validate against enum set or remove the param.

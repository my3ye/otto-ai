# Architecture: Cancelled Column & Stop/End Task Logic Reroute

**Date:** 2026-04-11
**Author:** Architect Agent
**Status:** Design Complete

---

## Design: Task Cancellation Cleanup

### Problem

Three bugs in the task lifecycle:

1. **Stopped tasks masquerade as failed.** When `stop_task()` kills a running task, it sets `status='failed'` with `exit_code=-15`. This conflates intentional cancellation with genuine failures, polluting failure metrics, confusing parent auto-close logic, and making it impossible to distinguish "I stopped this" from "this broke."

2. **`cancel_task()` skips propagation.** Cancelling a pending task does NOT call `_propagate_completion()`, does NOT advance workflows, and does NOT advance plans. If you cancel a child task, the parent may never auto-close because `children_completed` is never incremented.

3. **`stop_task(pending)` also skips propagation.** Same issue — the inline cancel path in `stop_task()` for pending tasks skips all downstream hooks.

4. **No `cancelled_at` timestamp.** There's `completed_at` for success/failure but no timestamp for when a task was cancelled. Can't answer "when was this stopped?"

### Approach

**Minimal, surgical fix — 3 files, 1 migration.**

#### Migration 087: Add `cancelled_at` and `cancelled_by` columns

```sql
ALTER TABLE tasks ADD COLUMN cancelled_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN cancelled_by TEXT;  -- 'admin', 'system', 'workflow', 'plan'
CREATE INDEX idx_tasks_cancelled ON tasks (cancelled_at) WHERE cancelled_at IS NOT NULL;
```

No CHECK constraint change needed — `'cancelled'` is already a valid status value.

#### Route changes (tasks.py)

**A. `cancel_task()` — fix propagation gap**

Current:
```python
# Just sets status='cancelled', returns. No hooks fired.
```

After:
```python
# Sets status='cancelled', cancelled_at=now(), cancelled_by='admin'
# Fires: _propagate_completion(), check_workflow_advance(), on_plan_task_complete()
```

**B. `stop_task()` — reroute running tasks from 'failed' to 'cancelled'**

Current (running tasks):
```python
status = 'failed', exit_code = -15, error = 'Stopped by admin'
```

After:
```python
status = 'cancelled', cancelled_at = now(), cancelled_by = 'admin',
exit_code = -15, error = 'Stopped by admin', pid = NULL
```

Current (pending tasks):
```python
# Inline cancel, no propagation
```

After:
```python
# Delegate to cancel_task() which now handles propagation
```

**C. `_propagate_completion()` — already handles 'cancelled'**

The existing code at line 884 already checks `status in ("completed", "failed", "cancelled")` for counter increments, and line 904 only checks for `'failed'` children when determining parent status. So cancelled children count as "done" and don't poison the parent to 'failed'. No changes needed here.

**D. Parent auto-close status logic — minor fix**

Line 904-908: When determining parent status after all children complete, a parent with all-cancelled children currently evaluates as `all_succeeded=True` (no 'failed' children), closing parent as 'completed'. This is wrong — if all children were cancelled, parent should be 'cancelled' too.

Fix:
```python
any_failed = await pool.fetchval(
    "SELECT COUNT(*) > 0 FROM tasks WHERE parent_id = $1 AND status = 'failed'", parent_id)
all_cancelled = await pool.fetchval(
    "SELECT COUNT(*) = COUNT(*) FILTER (WHERE status = 'cancelled') FROM tasks WHERE parent_id = $1", parent_id)

if all_cancelled:
    parent_status = "cancelled"
elif any_failed:
    parent_status = "failed"
else:
    parent_status = "completed"
```

#### Model changes (models.py)

Add to `TaskOut`:
```python
cancelled_at: datetime | None = None
cancelled_by: str | None = None
```

Add to `TASK_COLUMNS` in tasks.py.

### Key Decisions

- **Reuse 'cancelled' status (not a new 'stopped' status):** The CHECK constraint already includes 'cancelled'. Adding a 6th status would require migrating the constraint and updating every query that checks terminal states. Cancelled + exit_code=-15 distinguishes "stopped running" from "cancelled before start."
  - Alternative rejected: Adding 'stopped' status — too many downstream queries to update.

- **`cancelled_by` as TEXT not FK:** Simple provenance. Values: 'admin' (human), 'system' (timeout/cleanup), 'workflow' (workflow engine), 'plan' (plan cancellation). No need for a foreign key.
  - Alternative rejected: Boolean `manually_cancelled` — less information, same column cost.

- **Fire downstream hooks on cancel:** Cancel is a terminal state. Plans and workflows must know about it or they get stuck forever. The existing `_propagate_completion` already handles 'cancelled' in its counter logic, so we just need to call it.

### API / Interface

No new endpoints. Existing endpoints change behavior:

| Endpoint | Change |
|---|---|
| `POST /tasks/{id}/cancel` | Now sets `cancelled_at`, fires propagation + workflow/plan hooks |
| `POST /tasks/{id}/stop` | Running tasks: status='cancelled' instead of 'failed'. Pending: delegates to `cancel_task()` |
| `GET /tasks/{id}` | Returns new `cancelled_at` and `cancelled_by` fields |
| `GET /tasks` | No filter changes needed — 'cancelled' already queryable |

### Implementation Plan

1. **Migration 087** — Add `cancelled_at`, `cancelled_by` columns + index (~2 min)
2. **Model update** — Add fields to `TaskOut`, add to `TASK_COLUMNS` (~2 min)
3. **Fix `cancel_task()`** — Add timestamp, propagation, workflow/plan hooks (~5 min)
4. **Fix `stop_task()`** — Reroute running to 'cancelled', delegate pending to `cancel_task()` (~5 min)
5. **Fix parent auto-close** — Handle all-cancelled children case (~3 min)
6. **Verify** — Test cancel pending, stop running, parent propagation (~5 min)

Total: ~22 minutes, ~$1-2

### Risks

- **Existing queries filtering `status = 'failed'`:** Some dashboards or reports may count stopped tasks as failures. After this change, those counts will drop. This is correct behavior — stopped tasks were never failures.
  - Mitigation: Grep for `status = 'failed'` and `status='failed'` to verify no logic depends on stopped tasks being 'failed'.

- **task_runner.sh trap handler:** When SIGTERM is received, the trap in task_runner.sh calls `/tasks/{id}/complete` with a failure status. The API's `stop_task()` sets status='cancelled' first, then the trap fires and tries to set status='completed/failed'. The trap's `complete_task()` call may overwrite the 'cancelled' status.
  - Mitigation: Add a guard in `complete_task()` — if task is already 'cancelled', skip the update (task was stopped, don't overwrite).

- **Race between stop_task and task_runner completion:** `complete_task()` currently does NOT check current status — it blindly updates with `WHERE id = $1`. This means the trap handler WILL overwrite 'cancelled' back to 'failed'.
  - Mitigation: Add `AND status NOT IN ('cancelled')` to `complete_task()`'s UPDATE queries. If the task was already cancelled by `stop_task()`, the UPDATE returns no rows — `complete_task()` should return a 200 with no-op (not 404, since the trap handler doesn't check the response).

### Files to Modify

| File | Change |
|---|---|
| `memory/migrations/087_task_cancelled.sql` | New: `cancelled_at`, `cancelled_by` columns + index |
| `memory/models.py` | Add `cancelled_at`, `cancelled_by` to `TaskOut` |
| `memory/routes/tasks.py` | Fix `cancel_task()`, `stop_task()`, `complete_task()`, `_propagate_completion()`, `TASK_COLUMNS` |

No changes needed to: `task_runner.sh`, `models.py TaskCreate`, `qa_runner.sh`, `workflows.py`, `task_plans.py`.

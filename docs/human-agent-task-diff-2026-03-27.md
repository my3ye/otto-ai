# Design: Human vs Agent Task Differentiation

**Date:** 2026-03-27
**Status:** SPEC — ready for implementation

---

## Design: Human vs Agent Task Differentiation

### Problem

The task system treats Mev-owned tasks and Otto-owned tasks identically:

1. **Auto-progression**: Otto's `POST /tasks/{id}/run` spawns a Claude process for any pending task, including Mev's. Heartbeat auto-reviews all completed tasks including Mev's.
2. **Wrong UI shape**: Mev tasks show run buttons, model selectors, budget fields — none of which apply to human work.
3. **No handoff signal**: When Mev marks a task done, Otto has no structured way to detect it and evaluate follow-up actions.

Root cause: `owner` column exists (migration 053, values `otto` | `mev`) but nothing enforces different behavior based on it.

---

### Approach

**Reuse the `owner` column — no new migration needed.**

Status vocabulary stays identical (`pending → running → completed`). Only the *progression mechanism* changes:

| | Otto task | Mev task |
|---|---|---|
| `pending → running` | Otto calls `/run` → spawns process | Mev calls `/mev-update` with `status=in_progress` |
| `running → completed` | `task_runner.sh` calls `/complete` | Mev calls `/mev-update` with `status=done` |
| `completed → reviewed` | Heartbeat calls `/review` | Auto-set to `reviewed=TRUE` on completion (Mev is her own reviewer) |
| Interrupt fired | Yes (SIG_TASK_COMPLETE) | Yes (same mechanism) |
| pid | Set to process PID | Always NULL |

The existing `_count_running()` helper only auto-fails tasks where `pid IS NOT NULL AND process_dead`. A Mev task in `running` status with `pid = NULL` is safe — it won't be auto-failed and won't count toward concurrency limits.

---

### Key Decisions

- **No new migration**: `owner` column already exists. Status enum unchanged. Avoid scope creep.
  Alternative rejected: separate `mev_status` column — adds redundancy and split query logic.

- **Auto-review on Mev completion**: When Mev marks done, set `reviewed = TRUE` immediately. This avoids the heartbeat treating Mev completions as tasks needing Otto's review. Otto's follow-up evaluation is triggered by the kernel interrupt instead.
  Alternative rejected: let heartbeat review mev completions — creates confusing mixed queue and heartbeat has no meaningful review action for "Mev did X".

- **Guard both `/run` AND `/review`**: `/run` guard is the primary blocker. `/review` guard prevents heartbeat from touching mev tasks even if status somehow reaches `completed` before Mev's explicit mark.
  Alternative rejected: guard only at heartbeat prompt level — too soft, bypassed by direct API calls.

- **Single new endpoint `/mev-update`**: Simple status machine with 3 transitions. Rejects invalid transitions. Fires same downstream hooks as agent completion.

---

### API / Interface

#### New endpoint

```
POST /tasks/{task_id}/mev-update
```

Request body (`MevTaskUpdate`):
```json
{
  "status": "in_progress" | "done" | "cancelled",
  "note": "optional string stored in metadata.mev_notes"
}
```

Behavior:
- Validates `owner = 'mev'` (403 if Otto task)
- Status machine:
  - `pending → in_progress` (sets DB status = `running`, pid stays NULL)
  - `pending | in_progress → done` (sets status = `completed`, exit_code = 0, completed_at = now, reviewed = TRUE)
  - `pending | in_progress → cancelled` (sets status = `cancelled`)
  - Any other transition → 409
- On `done`: fires `_fire_task_interrupt(SIG_TASK_COMPLETE)` + `_jitrl_ingest_task()` + `on_plan_task_complete()` + `check_workflow_advance()`
- Appends `{status, note, at}` to `metadata.mev_notes[]`

#### Modified endpoints

`POST /tasks/{id}/run`
→ Add guard: if `owner = 'mev'` → raise 400 `"Mev tasks are manually progressed. Use POST /tasks/{id}/mev-update"`

`POST /tasks/{id}/review`
→ Add guard: if `owner = 'mev'` → raise 400 `"Mev tasks auto-review on completion. Use POST /tasks/{id}/mev-update?status=done"`

---

### Implementation Plan

#### Step 1 — API guards + new endpoint (memory/routes/tasks.py + models.py)

**`memory/models.py`** — add after `HandoffRequest`:
```python
class MevTaskUpdate(BaseModel):
    """Mev manually advances a task she owns."""
    status: str  # 'in_progress' | 'done' | 'cancelled'
    note: str | None = None
```

**`memory/routes/tasks.py`** — 3 changes:

1. In `run_task()` after the row fetch:
```python
if row["owner"] == "mev":
    raise HTTPException(400, "Mev tasks are manually progressed. Use POST /tasks/{id}/mev-update")
```

2. In `mark_reviewed()` after the pool.fetchrow update:
   → Change the WHERE clause to add `AND owner = 'otto'` OR add a pre-check:
```python
# Fetch task first to check owner
task_row = await pool.fetchrow("SELECT owner FROM tasks WHERE id = $1", task_id)
if task_row and task_row["owner"] == "mev":
    raise HTTPException(400, "Mev tasks auto-review on completion. Use /mev-update")
```

3. New route `POST /{task_id}/mev-update`:
```python
@router.post("/{task_id}/mev-update", response_model=TaskOut)
async def mev_update_task(task_id: UUID, req: MevTaskUpdate):
    """Mev manually advances a task she owns through the status machine."""
    pool = await get_pool()
    row = await pool.fetchrow(
        f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = $1", task_id
    )
    if not row:
        raise HTTPException(404, "Task not found")
    if row["owner"] != "mev":
        raise HTTPException(403, "Only Mev-owned tasks can be updated via this endpoint")

    current = row["status"]
    VALID = {
        "in_progress": {"pending"},          # pending → in_progress
        "done":        {"pending", "running"}, # (running = in_progress in DB)
        "cancelled":   {"pending", "running"},
    }
    if req.status not in VALID:
        raise HTTPException(400, f"status must be: {list(VALID.keys())}")
    if current not in VALID[req.status]:
        raise HTTPException(409, f"Cannot move from '{current}' to '{req.status}'")

    # Map friendly names to DB values
    db_status = {"in_progress": "running", "done": "completed", "cancelled": "cancelled"}[req.status]
    is_terminal = req.status in ("done", "cancelled")

    # Update metadata
    existing_meta = dict(row["metadata"]) if row["metadata"] else {}
    notes = existing_meta.get("mev_notes", [])
    notes.append({"status": req.status, "note": req.note, "at": datetime.now(timezone.utc).isoformat()})
    existing_meta["mev_notes"] = notes

    update_row = await pool.fetchrow(
        f"""UPDATE tasks
            SET status = $2,
                completed_at = CASE WHEN $3 THEN now() ELSE completed_at END,
                exit_code    = CASE WHEN $4 THEN 0 ELSE exit_code END,
                reviewed     = CASE WHEN $4 THEN TRUE ELSE reviewed END,
                metadata     = $5, updated_at = now()
            WHERE id = $1
            RETURNING {TASK_COLUMNS}""",
        task_id, db_status, is_terminal, req.status == "done", existing_meta,
    )

    # Fire downstream hooks on completion
    if req.status == "done":
        asyncio.create_task(_fire_task_interrupt(task_id, "completed"))
        asyncio.create_task(_jitrl_ingest_task(task_id))
        from .workflows import check_workflow_advance
        asyncio.create_task(check_workflow_advance(pool, task_id, "completed"))
        from .task_plans import on_plan_task_complete
        asyncio.create_task(on_plan_task_complete(pool, task_id, "completed"))

    log.info(f"Mev updated task {str(task_id)[:8]}: {current} → {db_status}")
    return TaskOut(**dict(update_row))
```

#### Step 2 — Heartbeat guard (heartbeat.md)

Add a rule to the DECIDE/EXECUTE section:

```
TASK OWNERSHIP RULES (critical):
- When launching pending tasks: only launch owner='otto' tasks. Never run owner='mev' tasks.
  Filter: GET /tasks?status=pending&owner=otto
- When reviewing completed tasks: only review owner='otto' tasks.
  Filter: GET /tasks?status=completed&reviewed=false&owner=otto
- Mev tasks appear in your queue view but are Mev's to progress — treat them as context only.
- When a mev task reaches status=completed, it fires a kernel interrupt. If you see SIG_TASK_COMPLETE
  from a mev task, evaluate whether Otto has follow-up work to create.
```

#### Step 3 — OMS UI (tasks/page.tsx)

**KanbanCardInner** action buttons (lines ~366-392):

Replace run button:
```tsx
{task.status === "pending" && task.owner !== "mev" && (!task.requires_decomposition || task.decomposed) && (
  <button onClick={...} ...>run</button>
)}
{task.status === "pending" && task.owner === "mev" && (
  <button onClick={() => onMevUpdate(task.id, "in_progress")} ...>start</button>
)}
```

Replace review button:
```tsx
{task.status === "completed" && !task.reviewed && task.owner !== "mev" && (
  <button onClick={...} ...>done</button>
)}
{task.status === "running" && task.owner === "mev" && (
  <button onClick={() => onMevUpdate(task.id, "done")} ...>done</button>
)}
```

Footer (lines ~340-347): hide model/budget for mev tasks:
```tsx
{task.owner !== "mev" && (
  <span className="flex items-center gap-1">
    <span className="opacity-60">{task.model}</span>
    <span className="text-border/50">·</span>
    <span className="text-emerald-400/60">${task.max_budget_usd}</span>
  </span>
)}
{task.owner === "mev" && (
  <span className="text-amber-400/60 text-[9px]">manual task</span>
)}
```

Add `onMevUpdate` prop to card component; implement via `apiPost(\`/tasks/${id}/mev-update\`, { status })`.

---

### Risks

- **Mev tasks stuck in `running` with no pid**: The `_count_running()` helper won't auto-fail them (safe — pid check guards it). But they won't appear in "alive" count either. Acceptable — they're not consuming compute.
  Mitigation: OMS shows `running` mev tasks clearly as "In Progress" (not "Running process").

- **Heartbeat creates follow-up for Mev completion before Mev-done fires**: The interrupt is async and fires after `/mev-update`. If heartbeat runs within milliseconds of the API call, it may miss the interrupt in that cycle.
  Mitigation: This is fine — heartbeat runs hourly. The task will appear as `completed + reviewed` in the next cycle, and Otto can evaluate then.

- **Plan advancement on Mev task completion**: `on_plan_task_complete()` fires. If a plan has mixed Otto + Mev tasks, a Mev task completing will advance the DAG. This is correct behavior — the plan doesn't care who did the work.

---

### File locations

| File | Change | Priority |
|---|---|---|
| `otto/memory/routes/tasks.py` | Guard `/run`, guard `/review`, add `/mev-update` | P1 — blocks everything |
| `otto/memory/models.py` | Add `MevTaskUpdate` Pydantic model | P1 — needed by route |
| `otto/.claude/agents/heartbeat.md` | Add owner filter rule | P2 — prevents auto-progression |
| `interfaces/web-next/src/app/tasks/page.tsx` | Mev-specific action buttons + footer | P3 — UX polish |

No database migration required. No new tables. Fully backward compatible.

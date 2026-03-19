# Task Hierarchy Architecture
## Hierarchical Subtask Decomposition Design

**Date:** 2026-03-17
**Status:** Architectural recommendation — pending implementation
**Author:** Otto (audit task a55e0230)

---

## 1. Current State

The `tasks` table is **flat**. No parent/child relationships exist. Key facts:

- 31 columns, flat list
- `owner` (otto/mev) just added (f83f01b)
- `metadata` JSONB exists (used for arbitrary KV)
- `status`: pending → running → completed/failed/cancelled
- No decomposition gate — tasks go straight from pending to running
- No auto-close propagation

Mev's requirements:
- Epic → Task → Subtask hierarchy
- Mandatory decomposition before execution
- Bidirectional handoff (Otto ↔ Mev) at any node
- Persistent progressive completion (surviving restarts)
- Parent auto-closes when all children complete

---

## 2. Architecture Decision

### Approach: Self-Referential Adjacency List

Add `parent_id` to the existing `tasks` table. Every row can be an epic, task, or subtask depending on its depth and whether it has children.

**Why not a separate table?**
- All existing infrastructure (task_runner.sh, QA, hindsight, LATS, OMS UI) already works with tasks
- JSONB metadata already stores arbitrary relationships
- Fewer joins, simpler queries
- Recursive CTEs handle tree traversal efficiently in Postgres

---

## 3. Data Model Changes

### SQL Migration

```sql
-- Add hierarchy fields
ALTER TABLE tasks
  ADD COLUMN parent_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
  ADD COLUMN task_type TEXT NOT NULL DEFAULT 'task'
    CHECK (task_type IN ('epic', 'task', 'subtask')),
  ADD COLUMN position INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN requires_decomposition BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN decomposed BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN children_total INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN children_completed INTEGER NOT NULL DEFAULT 0;

-- Index for tree traversal
CREATE INDEX idx_tasks_parent ON tasks(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_tasks_type ON tasks(task_type);
```

### Field Semantics

| Field | Type | Purpose |
|---|---|---|
| `parent_id` | UUID? | Points to parent task. NULL = root node |
| `task_type` | text | epic / task / subtask (max 3 levels) |
| `position` | int | Ordering among siblings (0-indexed) |
| `requires_decomposition` | bool | Must be broken down before any execution |
| `decomposed` | bool | Has been broken into children (gate passed) |
| `children_total` | int | Count of direct children (denormalized, fast) |
| `children_completed` | int | Count of completed/failed children (denormalized) |

---

## 4. Decomposition Gate

### Rule

A task with `requires_decomposition = TRUE` cannot enter `running` status until `decomposed = TRUE`.

### Enforcement (task_runner.sh)

```bash
# Before spawning the Claude process:
TASK_JSON=$(curl -s "http://localhost:8100/tasks/$TASK_ID")
REQ_DECOMP=$(echo "$TASK_JSON" | jq -r '.requires_decomposition')
DECOMPOSED=$(echo "$TASK_JSON" | jq -r '.decomposed')

if [ "$REQ_DECOMP" = "true" ] && [ "$DECOMPOSED" = "false" ]; then
  echo "BLOCKED: Task requires decomposition before execution."
  curl -s -X POST "http://localhost:8100/tasks/$TASK_ID/complete" \
    -H "Content-Type: application/json" \
    -d '{"output": "Blocked — task requires decomposition first.", "exit_code": 1}'
  exit 1
fi
```

### Enforcement (API)

`POST /tasks/{id}/run` returns 409 if:
```python
if task.requires_decomposition and not task.decomposed:
    raise HTTPException(409, "Task requires decomposition before execution")
```

---

## 5. Auto-Close Propagation

When a task completes (via `POST /tasks/{id}/complete`):

```python
async def _propagate_completion(pool, task_id: UUID, status: str):
    """After a task completes/fails, check if parent should auto-close."""
    row = await pool.fetchrow("SELECT parent_id FROM tasks WHERE id = $1", task_id)
    if not row or not row["parent_id"]:
        return  # Root task, no propagation

    parent_id = row["parent_id"]

    # Update denormalized counter
    if status in ("completed", "failed"):
        await pool.execute(
            "UPDATE tasks SET children_completed = children_completed + 1 WHERE id = $1",
            parent_id
        )

    # Check if all children are done
    sibling_stats = await pool.fetchrow(
        """SELECT COUNT(*) as total,
                  COUNT(*) FILTER (WHERE status IN ('completed','failed','cancelled')) as done
           FROM tasks WHERE parent_id = $1""",
        parent_id
    )

    if sibling_stats["total"] == sibling_stats["done"] and sibling_stats["total"] > 0:
        # All children done — auto-close parent
        all_succeeded = await pool.fetchval(
            "SELECT COUNT(*) = 0 FROM tasks WHERE parent_id = $1 AND status = 'failed'",
            parent_id
        )
        parent_status = "completed" if all_succeeded else "failed"
        await pool.execute(
            """UPDATE tasks
               SET status = $1, completed_at = now(),
                   output = 'Auto-closed: all subtasks completed.'
               WHERE id = $2 AND status NOT IN ('completed','failed','cancelled')""",
            parent_status, parent_id
        )
        # Recurse up the tree
        await _propagate_completion(pool, parent_id, parent_status)
```

---

## 6. New API Endpoints

### `POST /tasks/{id}/decompose`
Atomically create children under a parent. Sets `decomposed = TRUE` on parent.

```python
class DecomposeRequest(BaseModel):
    subtasks: list[TaskCreate]  # ordered list of children

# Response: list of created child TaskOut objects
```

### `GET /tasks/{id}/tree`
Return full task tree rooted at `id` (recursive CTE).

```sql
WITH RECURSIVE tree AS (
    SELECT *, 0 as depth FROM tasks WHERE id = $1
    UNION ALL
    SELECT t.*, tree.depth + 1 FROM tasks t
    JOIN tree ON t.parent_id = tree.id
)
SELECT * FROM tree ORDER BY depth, position;
```

Response: nested JSON `{ task, children: [{ task, children: [...] }] }`

### `POST /tasks/{id}/handoff`
Transfer ownership with a note.

```python
class HandoffRequest(BaseModel):
    to: Literal["otto", "mev"]
    note: str  # context for the new owner

# Updates owner field + appends to metadata["handoff_log"]
```

---

## 7. Bidirectional Handoff Pattern

The `owner` field (already exists) drives whose queue a task appears in. Handoff = changing owner.

**Handoff log** in `metadata`:
```json
{
  "handoff_log": [
    {"from": "otto", "to": "mev", "note": "Need approval on budget", "at": "2026-03-17T10:00:00Z"},
    {"from": "mev", "to": "otto", "note": "Approved, go ahead", "at": "2026-03-17T10:05:00Z"}
  ]
}
```

Any node in the tree can be handed off independently. Parent and children can have different owners.

---

## 8. Task Type Transitions

```
                    Mev/Otto creates Epic
                           │
                    (requires_decomposition = TRUE)
                           │
                    Decompose → creates Tasks
                    (decomposed = TRUE on epic)
                           │
                    Tasks may also require decomposition
                    Decompose → creates Subtasks
                           │
                    Subtasks execute (leaf nodes)
                           │
                    Subtasks complete → Tasks auto-close
                    Tasks complete → Epic auto-closes
```

Max depth: **3 levels** (epic → task → subtask). Deeper nesting is unnecessary and adds UI complexity.

---

## 9. OMS UI Changes

### Task List
- Indented tree rows with expand/collapse per parent
- Progress bar on epics/tasks: `children_completed / children_total`
- "Decompose" button on any task with `decomposed = FALSE`
- "Handoff" button on any task with a note field

### Task Detail
- Full tree sidebar showing siblings and parent context
- Decomposition UI: add N subtasks with titles/prompts
- Handoff history (from `metadata.handoff_log`)

---

## 10. Implementation Order

1. **DB migration** — add 6 columns + indexes (5 min)
2. **API: decompose endpoint** — create children atomically (30 min)
3. **API: tree endpoint** — recursive CTE + nested JSON (20 min)
4. **API: auto-close propagation** — hook into complete endpoint (20 min)
5. **API: handoff endpoint** — owner change + log (10 min)
6. **task_runner.sh: decomposition gate** — pre-execution check (10 min)
7. **OMS UI: tree view + decompose dialog** — (2h)
8. **OMS UI: handoff button** — (30 min)

**Total estimate: ~4 hours of implementation**

---

## 11. Backward Compatibility

- All existing tasks have `parent_id = NULL`, `task_type = 'task'`, `requires_decomposition = FALSE`
- All existing API endpoints unchanged
- `requires_decomposition = FALSE` (default) means zero behavior change for existing tasks
- The flat list view in OMS still works — tree view is additive

---

## 12. Key Design Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Tree storage | Adjacency list (parent_id) | Simple, Postgres recursive CTE handles traversal. Nested sets / closure table are overkill for 3 levels. |
| Max depth | 3 (epic→task→subtask) | Mev's request. Deeper = UI nightmare. |
| Auto-close | Yes, on all-children-done | Mev explicitly requested. Fail if any child fails. |
| Decomposition gate | Optional per-task flag | Not all tasks need decomposition. Default FALSE = no change to existing flow. |
| Handoff | Existing owner field + log | Owner already exists. Handoff = owner change + audit trail in metadata. |
| Counter denormalization | children_total, children_completed | Avoid full COUNT query on every status check. Updated atomically in decompose/complete. |

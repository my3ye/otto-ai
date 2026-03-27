---
name: mev_task_separation
description: Human vs agent task differentiation — Mev tasks must not auto-progress; separate status machine and API guards
type: project
---

Mev tasks (`owner='mev'`) must be manually progressed by Mev only. Designed 2026-03-27.

**Why:** Mev complained that tasks assigned to him were auto-moved to review stage by Otto's heartbeat. They also showed the wrong UI (run buttons, model/budget fields).

**How to apply:** All future task system work must respect the owner guard pattern.

Key decisions:
- `owner` column already exists (migration 053) — no new migration
- New `POST /tasks/{id}/mev-update` endpoint with status machine: pending → in_progress → done/cancelled
- Guards in `/run` (400 if owner=mev) and `/review` (400 if owner=mev)
- Mev completions: set `reviewed=TRUE` automatically + fire SIG_TASK_COMPLETE interrupt
- `running` status + null pid is safe — `_count_running()` only auto-fails when pid IS NOT NULL AND dead
- Heartbeat must filter `owner=otto` when auto-launching and auto-reviewing tasks
- OMS UI: hide run/review for mev tasks; show start/done instead; hide model/budget footer

Full design: ~/otto/docs/human-agent-task-diff-2026-03-27.md

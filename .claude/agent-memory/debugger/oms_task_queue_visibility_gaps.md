---
name: oms_task_queue_visibility_gaps
description: OMS task queue shows incomplete data — zombie tasks block plans, "Needs Review" stat filter broken, kanban 100-limit hides older tasks, no plan DAG view
type: project
---

OMS task queue visibility audit (2026-03-28) found 6 gaps causing Mev to not see completed deliverables.

**Why:** Mev reported "I don't see a lot of the above in the OMS" after investor letter, live organism, and 0xAvengers tasks completed.

**How to apply:**
1. Zombie task pattern: tasks marked `running` with NULL pid and no logs = process never spawned. Check `running_alive` vs `running` in queue status.
2. Kanban limit=100 in tasks/page.tsx line 952 pushes older tasks off-screen. Mev-owned tasks are especially affected since there are few of them.
3. "Needs Review" stat click sets `key: "completed"` (line 1278 tasks/page.tsx) — same as "Completed", defeating the purpose. Should filter `reviewed=false`.
4. Task plans have no OMS page — stuck plans are invisible.
5. [WF] workflow step tasks clutter the kanban Review column alongside coordinator tasks.

Full gap report: ~/otto/docs/oms-task-queue-gap-report-2026-03-28.md

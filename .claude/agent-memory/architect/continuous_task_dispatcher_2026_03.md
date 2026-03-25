---
name: continuous_task_dispatcher_design
description: Design for continuous task dispatcher that launches pending tasks immediately (≤15s) without waiting for the hourly heartbeat
type: project
---

Designed a lightweight polling service (`task_dispatcher.py`) as a systemd service (`otto-task-dispatcher.service`) that watches the task queue every 15 seconds and dispatches tasks immediately when slots open.

**Why:** Tasks created between heartbeats (up to 59 minutes) wait idle. Dispatcher closes this gap to ≤15s with zero LLM cost.

**Key decisions:**
- Poll (15s) over LISTEN/NOTIFY (zero-latency but adds DB trigger complexity to 4+ code locations)
- External process over embedded asyncio (independently restartable, observable)
- API concurrency checks are the authoritative lock — dispatcher just calls `/tasks/{id}/run` and handles 409/429 gracefully
- Heartbeat keeps creating/reviewing tasks; dispatcher only launches them (orthogonal roles)
- `in_flight` set is defensive hygiene; real guard is API status check

**Phase 2 options:** `/tasks/queue/next` server-side endpoint, LISTEN/NOTIFY for sub-second latency, batch dispatch per cycle.

**Full design:** ~/otto/docs/continuous-task-dispatcher-architecture-2026-03-25.md

**Why:** Mev asked "how can we ensure tasks get actioned on without waiting for the heartbeat?" — 15s polling is the simplest correct answer.

**How to apply:** When implementing, use the Python pseudocode in the design doc. The systemd unit goes in /etc/systemd/system/. Add otto-task-dispatcher.service to heartbeat.sh self-healing loop.

---
name: Continuous Task Dispatcher Review
description: Review of the continuous task runner (task_dispatcher.py + systemd service), committed 2026-03-25
type: project
---

Review date: 2026-03-25 (task 3dec2e2b)
Verdict: NEEDS_CHANGES — 1 critical (API TOCTOU), 3 warnings

**Confirmed working**: Dispatcher launched 3 tasks at 21:39:20 IST (including the reviewer task itself) immediately after rate limit cleared. Live in production.

**Critical**: TOCTOU race in `/tasks/{id}/run` (tasks.py:~695). SELECT status then UPDATE without a transaction — two simultaneous callers can both pass the `status = 'pending'` check and spawn duplicate runners. Fix: use `UPDATE ... WHERE status = 'pending' RETURNING id` and check affected rows.

**Warnings**:
- `can_run_more` flag doesn't encode per-CLI availability — dispatcher enters `run_dispatch_cycle` even when all available global slots are for an oversubscribed CLI type (e.g., all claude at cap, gemini/kimi slots open but no gemini/kimi pending tasks). Minor polling waste, not a correctness bug.
- Stale rate-limit sentinel: heartbeat writes sentinel but nothing clears it early; dispatcher pauses for full 1h TTL even if limit lifted at 30 min.
- urllib3 version warning spam in task-dispatcher.log (system `requests` package vs urllib3 version mismatch).

**What's good**:
- Batch dispatch fills all available slots per cycle (already Phase 2 behavior)
- Clean SIGTERM shutdown via _sleep_interruptible
- in_flight set with 60s TTL is correct defensive hygiene
- CLI-level 429 backoff (30s per CLI type)
- Heartbeat self-healing integration wired into heartbeat.sh

**Why:** run_task TOCTOU is the only correctness risk. The dispatcher's in_flight set provides partial mitigation but the API itself needs the atomic UPDATE guard.
**How to apply:** When reviewing or implementing task queue changes, always require atomic SELECT+UPDATE on status transitions.

---
name: project_daily_strategy_cron_review
description: Daily strategic prioritization cron job review (2026-03-30, WF Step 2): NEEDS_CHANGES. 1 critical bug (status filter), 3 warnings.
type: project
---

Daily strategy cron job review (2026-03-30, WF Step 2). Files: strategist.md, daily_strategy.sh, otto-strategy.timer, otto-strategy.service, heartbeat.sh.

**VERDICT: NEEDS_CHANGES (1 critical fix required)**

**Critical:**
- `tasks?status=pending,running` in Phase 3 duplicate check returns 0 results always — API uses exact match, not IN clause. Silent failure makes duplicate detection completely broken.

**Warnings:**
- No `--max-budget-usd` flag on claude invocation (consistent with heartbeat.sh pattern, but architecture doc specified $2.00 cap).
- Timer relies on `timedatectl` Asia/Colombo while `/etc/timezone` still says `Etc/UTC` — if reset, timer would fire at 05:00 UTC not 05:00 IST.
- Phase 1 GATHER comments say "last 24h" but queries have no date filter (just limit=20/10).

**Good:** Timer active and next trigger confirmed (05:01 IST). Syntax clean. Lock pattern correct. Rate limit API endpoint verified. Heartbeat self-healing correctly updated on line 29. Parallel with heartbeat.sh pattern is tight.

**Why:** Phase 3 duplicate check is the safeguard against queue flooding. If it silently returns empty, the agent will always think the queue is clear and may create up to 9 tasks regardless of what's already running. Fix: split into two queries (`?status=running` then `?status=pending`).

---
name: project_daily_strategy_cron_review
description: Daily strategic prioritization cron job review (2026-03-30, WF Step 2): NEEDS_CHANGES. 1 critical bug (status filter), 3 warnings.
type: project
---

Daily strategy cron job review — WF Step 2 (2026-03-30) and Step 3 hardening review (2026-03-30).

**STEP 2 VERDICT: NEEDS_CHANGES** — 1 critical (status filter). All 3 warnings fixed in Step 3 (commit 95779ef).

**STEP 3 FINAL VERDICT: APPROVE with 1 recommended warning fix**

All Step 2 critical+warnings were fixed. New findings from hardening review:

**Warning (should fix):**
- `strategist` role NOT in `ROLE_QUERIES` (kernel_routes.py:399) — falls back to literal "strategist" as S-MMU search query. Other roles (orchestrator, reflection) have rich targeted queries. Strategist gets sub-optimal context. Fix: add `"strategist": "strategic priorities mission advancement public readiness system reliability directives WebAssist ONEON"` to ROLE_QUERIES.

**Suggestions:**
- Double API call: lines 30-34 hit `/kernel/providers/rate-limited` twice (once for check, once for remaining_seconds) — could parse from one call.
- Phase 1 fetches 2 recent strategy briefs — should be 5 for rolling-week awareness.
- No episodic event logging at start/end of strategy run (heartbeat and reflection both log events).
- Q2 Public Readiness only checks HTTP 200 — no SEO/og:image/content gap detection.
- Timer has no `TimeZone=Asia/Colombo` directive — relies on system timedatectl. Would fire at wrong time if dpkg-reconfigure tzdata resets to UTC.

**Good:** All Step 2 fixes verified. Split-query duplicate check works (pending=5, running=5 confirmed live). CLI flags valid (--effort, --fallback, --no-session-persistence). Heartbeat self-heals strategy timer (heartbeat.sh:29). kernel/context endpoint works correctly. Service depends on otto-memory. TimeoutStartSec=1200 gives 5-min buffer beyond script's 900s timeout.

**Pattern:** agent prompt roles must have a matching ROLE_QUERIES entry in kernel_routes.py or context quality degrades silently.

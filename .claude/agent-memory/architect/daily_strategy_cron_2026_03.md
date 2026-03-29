---
name: daily_strategy_cron_2026_03
description: Daily strategic cron architecture (2026-03-30). Single strategist agent session, 3 deep-dive analyses (mission/public-ready/core-system), task dispatch, WhatsApp brief. Systemd timer at 05:00 IST.
type: project
---

Daily Strategy Cron designed 2026-03-30 per Mev directive.

**Why:** Mev wants proactive daily strategic planning, not reactive. Three questions answered daily with actionable task dispatch.

**How to apply:** Single Claude session with `strategist` agent, Sonnet model, $2 budget, 900s timeout. Creates 3-9 tasks/day across mission/public/core dimensions. Shell script pattern matches heartbeat.sh exactly. Timer at 05:00 IST (before Mev's day). Self-healing added to heartbeat.sh. Full spec at ~/otto/docs/daily-strategy-cron-architecture-2026-03-30.md.

Key decisions:
- Single session (not 3 parallel) for cross-analysis coherence + 40% cheaper
- Sonnet (not Opus) for budget discipline ($1.50-2/day vs $3-4/day)
- 05:00 IST so Mev wakes to strategic brief
- 9-task daily cap to prevent runaway creation
- `created_by: "daily_strategy"` tag for attribution

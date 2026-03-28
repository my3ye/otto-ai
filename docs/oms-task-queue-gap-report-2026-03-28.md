# OMS Task Queue Visibility Gap Report
**Date**: 2026-03-28
**Trigger**: Mev reported "I don't see a lot of the above in the OMS"
**Auditor**: debugger agent

---

## Executive Summary

39 completed tasks are stuck in "Needs Review" state — they completed successfully (exit_code=0, output present) but were never reviewed by the heartbeat. Additionally, a zombie task is blocking the entire Live Organism plan from completing. The kanban view correctly shows most of these tasks in the "Review" column, but usability issues make them hard to find.

---

## Gap 1: Zombie Task Blocking Live Organism Plan [CRITICAL]

**Task**: `723b6960` — "Generate Vertical Scenario Playbook"
**State**: `status=running`, `pid=NULL`, running for 3600+ seconds (timeout: 900s), zero log files
**Root Cause**: Task was marked `running` with `started_at` set, but no process was ever spawned. No PID, no logs directory. The task_runner never actually executed this task.

**Impact**: The "Otto Live Organism Vision" plan (`d6c13da7`) is stuck in `executing` state. The final synthesis task (`429fffd2` — "Synthesize the Comprehensive Live Organism Vision") depends on ALL 5 other tasks including this zombie, so it remains `pending` indefinitely.

**Plan DAG state**:
| Task | Status | Depends On |
|---|---|---|
| `5e43ed69` Architect the Core Value Loop | completed | — |
| `cac11e4f` Research Real-World Validation Models | completed | — |
| `723b6960` Generate Vertical Scenario Playbook | **ZOMBIE (running, no PID)** | `5e43ed69` |
| `fe34df45` Design On-Chain Architecture | completed | `5e43ed69` |
| `66d31620` Audit On-Chain Architecture | completed | `fe34df45` |
| `429fffd2` Synthesize the Comprehensive Live Organism Vision | **BLOCKED (pending)** | all 5 above |

**Fix needed**: Mark `723b6960` as failed (no process exists), then either re-run it or skip it so the synthesis task can proceed.

---

## Gap 2: 39 Unreviewed Completed Tasks

All 39 tasks completed with `exit_code=0` and have output data, but `reviewed=false`. The heartbeat should have reviewed these during its cycles but hasn't.

### By Category:

**0xAvengers KOL (3 coordinators + 8 WF steps = 11 tasks)**
- `3e8919f0` Create 30-day X posting calendar — output: 3940 bytes, file at `~/otto/docs/0xavengers-30day-calendar-2026-03-28.md`
- `c4ad0c12` Build KOL brand strategy — output: 1303 bytes, file at `~/otto/0xAvengers_strategy.md`
- `23dea044` Research KOL growth tactics — output: 2852 bytes
- 4 WF steps for calendar: `cb31b095`, `003231bb`, `276fa012`, `c48099ee`
- 4 WF steps for KOL research: `3aa0e389`, `cc6d55af`, `15b6192d`, `73b45318`

**Live Organism (4 completed + 1 blocked)**
- `5e43ed69` Architect the Core Value Loop — output: 711 bytes
- `cac11e4f` Research Real-World Validation Models — output: 2853 bytes
- `fe34df45` Design On-Chain Architecture — output: 711 bytes (artifact)
- `66d31620` Audit On-Chain Architecture — output: 1711 bytes
- 5 WF steps for validation research: `ea0fc227`, `d3af020a`, `02851f9e`, `5a7b5922`

**Architecture Document (8 tasks)**
- `e055c329` Audit Otto system components — 1905 bytes
- `90a34c66` Architect system doc — 1887 bytes
- `af775bd3` Write master architecture doc — 9323 bytes
- `b94864c9` Document features & roadmap — 711 bytes
- `d25ee6fc` Competitive comparison — 711 bytes
- `d4c3265c` Review/QA architecture doc — 711 bytes
- `c9ddca6b` Research AI agent harnesses — 3398 bytes
- 4 WF steps: `e5447075`, `60f6c515`, `fc902d3c`, `9a41772a`

**System Improvements (5 tasks)**
- `35facbf8` Build improvement roadmap — 1981 bytes
- `3047d1f5` Gather system context — 1415 bytes
- `9c960f2c` Review deployed fixes — 1978 bytes
- `602948a9` Patch RL2F apply loop — 711 bytes
- `c44eacea` Extend signal expiry — 711 bytes

**Mev-Owned Tasks (4 tasks) — ALSO off-screen in default kanban**
- `7fa95768` Provide Stripe API keys — 1164 bytes
- `708e644a` Register on Gitcoin GG25 — 1224 bytes
- `ebed8ad2` Register Solana Tracker API key — 1311 bytes
- `56397c5b` Submit ENS grant application — 1975 bytes

These 4 Mev-owned tasks are NOT visible in the default "All" kanban view (pushed out by the 100-task limit) but ARE visible when Mev clicks the "Mev" owner tab.

---

## Gap 3: "Needs Review" Stat Click Mismatch [UX BUG]

**Behavior**: The "Needs Review" stat card in the OMS shows count 39. Clicking it sets `statusFilter=completed` — the same filter as clicking "Completed" (1329). This means clicking "Needs Review" shows ALL 1329 completed tasks, not just the 39 unreviewed ones.

**Root Cause**: In `tasks/page.tsx` line 1278:
```js
{ label: "Needs Review", value: queue?.needs_review ?? 0, key: "completed" }
```
The `key` should trigger a `reviewed=false` filter, but the list view API only sends `status` not `reviewed`.

**Fix**: Add a `needs_review` key that passes both `status=completed&reviewed=false` to the API.

---

## Gap 4: Kanban 100-Task Limit

**Behavior**: The kanban fetches 100 tasks total (no pagination). With 2 running + 9 pending + 89 remaining slots for completed/failed tasks, older completed tasks are invisible.

**Current breakdown of 100 visible tasks**:
- 2 running
- 9 pending
- 35 unreviewed completed (in "Review" column)
- 54 reviewed completed (in "Done" column)
- 0 failed (pushed out)

**Impact**: 4 Mev-owned unreviewed tasks and ALL failed tasks (119) are invisible in the default view. The "Done" column shows only the 54 most recent reviewed tasks out of 1290 total.

---

## Gap 5: No Plan/DAG Visibility [STRUCTURAL]

The task_plans system tracks multi-task DAGs (like the Live Organism plan), but there is no OMS page to visualize plan status, task dependencies, or stuck plans.

**Stuck plans currently**:
- `d6c13da7` "Otto Live Organism Vision" — `executing`, 4/6 done, 1 zombie, 1 blocked

**Completed plans** (just for reference):
- `daa85970` "0xAvengers KOL Growth Strategy" — completed
- `9a3e926f` "High-Calibre Investor Letter" — completed

---

## Gap 6: Workflow Steps Clutter Kanban

Of the 35 tasks in the "Review" column, 17 are `[WF]` workflow step tasks. These are implementation details — the coordinator task is what Mev cares about. No filtering exists to hide sub-steps.

---

## Data Location Summary

| Deliverable | Task(s) | Status | Output Location |
|---|---|---|---|
| Investor Letter (full) | `163a7fbb` | completed, reviewed | `~/otto/docs/investor-letter.md` |
| Investor Letter (brief) | `05350394` | completed, reviewed | `~/otto/docs/investor-letter-brief-2026-03-28.md` |
| Investor Letter (sharpened) | `99f772ac` | completed, reviewed | `~/otto/docs/investor-letter-highcalibre.md` |
| Live Organism Architecture | `fe34df45` | completed, **unreviewed** | `logs/tasks/fe34df45.../output.md` |
| Live Organism Audit | `66d31620` | completed, **unreviewed** | DB output field (1711 bytes) |
| Live Organism Synthesis | `429fffd2` | **BLOCKED (pending)** | — |
| 0xAvengers Calendar | `3e8919f0` | completed, **unreviewed** | `~/otto/docs/0xavengers-30day-calendar-2026-03-28.md` |
| 0xAvengers Strategy | `c4ad0c12` | completed, **unreviewed** | `~/otto/0xAvengers_strategy.md` |
| KOL Research | `23dea044` | completed, **unreviewed** | DB output field (2852 bytes) |
| Master Architecture Doc | `af775bd3` | completed, **unreviewed** | `~/otto/docs/` (9323 bytes output) |

---

## Recommended Fixes (Priority Order)

1. **[IMMEDIATE]** Mark zombie task `723b6960` as failed so the Live Organism plan can unblock
2. **[IMMEDIATE]** Batch-review the 39 unreviewed tasks via heartbeat or manual API calls
3. **[SHORT-TERM]** Fix "Needs Review" stat click to filter `reviewed=false` not just `status=completed`
4. **[SHORT-TERM]** Add kanban filter to hide `[WF]` step tasks (show coordinators only)
5. **[MEDIUM-TERM]** Build task plans OMS page showing DAG visualization and stuck plan detection
6. **[MEDIUM-TERM]** Increase kanban limit or add pagination/virtual scrolling for the Done column

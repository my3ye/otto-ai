# Reflection Agent Memory

## System Baselines (updated 2026-04-08 cycle 559)
- **CRITICAL: OpenAI API QUOTA EXCEEDED** since Apr 1 (~32 days). semantic/remember fails. Evolve timeouts. Mev confirmed no funding.
- **CRITICAL: Zoho email DOWN** — trial expired. admin@otto.lk non-functional. Mev confirmed no funding.
- **BM25 HYBRID SEARCH: DEPLOYED & VERIFIED** (cycle 532). Uses PostgreSQL full-text search + pg_trgm. Does NOT need OpenAI.
- **Memory functional**: Evolve timing out (OpenAI quota for embeddings). GLOVE: returned empty this cycle (Kimi may be unavailable). 19 null-embedding memories persist (fix task 227555af unreviewed).
- **Memory stats (cycle 559)**: **1488 active, 16 categories.** Infra: 423, Research: 388, Observation: 224, Project: 159, Directive: 67, Decision: 57, Mission: 55, Capability: 39. 0 text-level duplicates. Natural decay from 1489 (1 memory).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Disk: 47% boot. RAM: 8.7Gi available.
- Queue: 1 running (db10b063 LinkedIn WF), 8 Mev pending, 4 unreviewed completed.
- RL2F accuracy: **active-only 58% w=50** (29/50 matched). meta_memory: **stable** (0.58→0.58), cycles_since_improvement=3. Plateau confirmed 4+ cycles.
- **Anomaly detector false-positive**: Sync pulse 17x/6h matches scheduled cadence — NOT a loop bug.
- **AutoEvolve**: Gen 7. 0 experiments. Deferred until active work resumes.
- **Procedures**: 69 exist, 51 actively used. 18 zero-use procedures are cleanup candidates (age 4c).
- **WF notify step bug**: ALL 8 workflow templates have EMPTY notify step prompts (age 27 cycles).
- **Kernel routing issue (NEW cycle 559)**: Mev said "Don't deploy a task" at 02:57 UTC, kernel responded inline ✓, but follow-up at 03:00 triggered WF task db10b063. "No task" context not carried across messages.
- **Context loss recurring (Apr 7)**: Mev complained "How do you not have context of that, that was just 3 messages before." Goldfish fix (Mar) helped but didn't eliminate.
- **Agent perf**: 100% success across all agent types (last 30 completed tasks).
- **TODO next cycle**: (1) Review 4 unreviewed tasks (priority: 227555af null-embed fix). (2) Investigate kernel routing — "don't deploy" directive not carried across messages. (3) When OpenAI restored: re-embed 19 null-vector memories, run full evolve+dedup. (4) Review 18 zero-use procedures — archive or retire (age 4c). (5) Context loss investigation (recurring Mev complaints).

## Known Gaps (persistent)
- **OpenAI quota exceeded (cycle 479+)**: `insufficient_quota` error, still down as of cycle 499 (Apr 4). Mev confirmed no funding. When restored: run full evolve + dedup cycle.
- **Semantic memory bloat (RESOLVED cycle 480)**: Archived 2,304 floor-relevance memories via DB-level archival. 4,420→2,116 active. No longer critical.
- **Claude Code quota exhaustion (cycle 480)**: All heartbeats/reflections failed Apr 1 13:03 → Apr 3 12:30 (48h). Future risk: if quota is exhausted again, same 24h+ blackout.
- **RL2F accuracy: active-only 58% w=50 (cycle 558)** — plateau confirmed at 58% across 3+ cycles (not window noise). Up from 56% (cycle 556). 78% all-entries confirms idle inflation gap (ALWAYS use `?active_only=true`). AE gen 7. Next improvement likely requires active work (new reasoning entries) or system changes.
- **OpenAI silent degradation (CONFIRMED cycle 482)**: 20 null-embedding memories found. When restored: (1) re-embed, (2) full dedup. GLOVE accuracy unaffected (uses Kimi, not OpenAI).
- **Crashed-at-line-1 failures (cycle 428)**: 5 failures across agents. task_runner.sh issue. Needs debugger investigation. Priority: HIGH (25% failure rate). Not seen recently — may be stale.
- **AutoEvolve template contamination (FIXED cycle 408)**: Always verify after AutoEvolve runs.
- **Self-patch mechanism gap**: heartbeat.md has no step to check/apply pending self-patches. Reflection applies directly as workaround.
- **Plan DAG executor bug (FIXED cycle 447, SIGTERM variant FIXED cycle 551)**: Original DAG execution fixed cycle 447. SIGTERM variant (stop_task/reconcile_and_fix missing hooks) fixed cycle 551 via task 822a11b2. Commit 2a95fce.
- **Trust score EMA divergence (FIXED cycle 551)**: Burst failures during outages caused compound EMA decay (95% success rate → 0.35 trust). Fix: recalibration guard in procedural.py blends toward actual rate when divergence >0.3. 4 procs corrected. Monitor threshold.

## Recurring Patterns
- **Claude Code quota exhaustion kills workflow steps** — step fails with "out of extra usage · resets [time]", coordinator task becomes zombie (no PID, running indefinitely). Principle created: don't retry until after stated reset time.
- System enters idle holds when awaiting Mev. This is correct behavior per budget discipline directive.
- Open proposals typically take 12-48h for Mev response. Nudge threshold: >24h.
- Memory evolve pipeline working. GLOVE working correctly.
- Handoff timestamps from orchestrator/reflection can be days old if system is idle — normal.
- **AutoEvolve mutations can contaminate generic templates** — always verify after AutoEvolve runs.
- **Reflection can and should apply patches directly** when orchestrator doesn't pick them up within 1 cycle.

## Anti-Patterns to Watch
- **Double decay**: NEVER apply manual relevance_score decay on top of evolve endpoint's 0.99x.
- **Stale blockers**: If a blocker appears 2+ cycles without progress, verify via API.
- **Task creation during rate limit**: Respect rate limit alerts. Memory consolidation only.
- **RL2F metric confusion**: ALWAYS use `?active_only=true`. The all-entry metric inflates by idle matches.
- **RL2F idle inflation**: During extended idle holds, RL2F accuracy improves because "idle hold" predictions trivially match. This is NOT real reasoning improvement — must re-baseline when active work resumes.
- **Task timeline assumption**: When checking if a validation task is "redundant," always verify task timestamps against commit dates. A validation that ran BEFORE a fix is NOT the same as validating the fix. Compare task.created_at vs git log dates.
- **Procedure use_count diagnostic bug (RESOLVED cycle 547)**: ProcedureOut model has NO `use_count` field. Usage is tracked via `success_count` + `failure_count`. Checking `use_count` always returns 0. This caused a false 4-cycle carry-forward of "0 uses" alarm.
- **RL2F trend label confusion (RESOLVED cycle 537)**: The API trend label compares 50-entry current window vs prior 50-entry window. "improving" means current > prior + 5pp. It does NOT track cycle-over-cycle changes. For short-term monitoring, use meta_memory.json rl2f_trend.direction (uses 0.02 threshold on consecutive readings). Do NOT re-flag the API label as a bug.

## Priority Context
- P10 WebAssist: LIVE at webassist.ink. Stripe payment flow VALIDATED READY (task b0eaddc5 Apr 5). Only Mev live keys block revenue.
- P9 Management System: LIVE at mev.otto.lk. Push to ottomev/otto-ui COMPLETED.
- P8 Broadcast System: MVP complete, awaiting Mev credentials
- Current emphasis: Ship over perfection, budget discipline. All Mev-blocked.
- **Mev directive (Apr 4)**: No funding for OpenAI/Zoho. OMS repo = ottomev/otto-ui. Stripe confirmed in WebAssist.
- 5 LinkedIn consulting articles in content DB. Awaiting Mev response on whether to publish.

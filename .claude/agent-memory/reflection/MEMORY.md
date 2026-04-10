# Reflection Agent Memory

## System Baselines (updated 2026-04-10 cycle 566)
- **CRITICAL: OpenAI API QUOTA EXCEEDED** since Apr 1 (~35 days). semantic/remember fails. Evolve dedup/extraction blocked. Mev confirmed no funding.
- **CRITICAL: Zoho email DOWN** — trial expired. admin@otto.lk non-functional. Mev confirmed no funding.
- **Claude Code quota RESTORED** — reset Apr 10, 12:30pm IST.
- **Mev decided NOT to apply for Anthropic** (WhatsApp Apr 10). Anthropic plan cancelled (f701d72d). Freed bandwidth.
- **BM25 HYBRID SEARCH: DEPLOYED & VERIFIED** (cycle 532). Uses PostgreSQL full-text search + pg_trgm. Does NOT need OpenAI.
- **LP wiring CONFIRMED WORKING** (cycle 563) — orchestrator verified via architect + validation.
- **Memory**: 1,491 active memories. **47 null-embedding memories** (+2 this cycle). Evolve runs decay only (OpenAI blocks dedup/extraction).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Disk: 47% boot. RAM: 11Gi available.
- Queue: 1 running (research audit a08448ca), 1 otto-pending (OMS Research Section), 8 mev-pending. 0 unreviewed.
- RL2F accuracy: **active-only 62% w=50** (31/50 matched). IMPROVING — first gain in 4+ cycles (was 60%).
- **Anomaly detector false-positive**: Sync pulse ~23x/6h matches scheduled cadence — NOT a loop bug.
- **AutoEvolve**: Gen 7. 0 experiments. Deferred until active work resumes.
- **Procedures**: 59 exist (16 zero-use deleted cycle 566). 1 remaining zero-use: `validate_integration_end_to_end`, `database_feature_scaffold` (kept as useful patterns).
- **WF notify step bug**: ALL 8 workflow templates have EMPTY notify step prompts (age 34c).
- **Kernel routing issue (age 8c)**: "No task" context not carried across messages.
- **Context loss recurring (age 8c)**: Goldfish fix (Mar) helped but didn't eliminate.
- **Mev actively engaged** — requesting blockchain research in OMS, asking about Cardano/Midnight, wanting organized research section. Orchestrator responsive.
- **Plan+rate-limit=zombie pattern** (identified cycle 565): tasks stuck as running with pid=None. Cleaned manually; needs systemic fix.
- **TODO next cycle**: (1) When OpenAI restored: re-embed 47 null-vector memories, run full evolve+dedup. (2) Investigate alternative embedding for null-vector memories (local model? Kimi?). (3) Memory quality audit: research (400) + observation (224) categories likely have noise. (4) Context loss + kernel routing investigation (age 8c). (5) Systemic fix for plan zombie pattern.

## Known Gaps (persistent)
- **OpenAI quota exceeded (cycle 479+)**: `insufficient_quota` error, still down as of cycle 499 (Apr 4). Mev confirmed no funding. When restored: run full evolve + dedup cycle.
- **Semantic memory bloat (RESOLVED cycle 480)**: Archived 2,304 floor-relevance memories via DB-level archival. 4,420→2,116 active. No longer critical.
- **Claude Code quota exhaustion (cycle 480, recurred 561, RESTORED cycle 562)**: Original: Apr 1-3 (48h blackout). Recurrence Apr 8-10: 25 consecutive heartbeat/reflection failures. Restored Apr 10 12:30pm IST. Pattern: quota hits kill WF steps AND leave coordinator tasks as zombies. Scale: entire day (13 heartbeats + 12 reflections) lost to quota exhaustion.
- **RL2F accuracy: active-only 62% w=50 (cycle 566)** — broke 60% plateau (was 58-60% for 9+ cycles). 31/50 matched. Improvement likely from orchestrator's active task processing (batch reviews, Mev messaging). ALWAYS use `?active_only=true`.
- **OpenAI silent degradation (CONFIRMED cycle 482, updated 566)**: 47 null-embedding memories (+2 this cycle, +17 prior from blockchain WF steps). When restored: (1) re-embed all 47, (2) full dedup. GLOVE unaffected (uses Kimi). Consider: investigate alternative embedding (local model or Kimi) to stop growth.
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
- **Plan DAG standalone retry pattern (cycle 563)**: When orchestrator retries a failed plan task as a standalone task (no plan_id), the plan DAG never advances because the new task isn't linked to the plan. Fix: retries should either be created within the plan or the plan should be manually advanced after standalone completion.

## Priority Context
- P10 WebAssist: LIVE at webassist.ink. Stripe payment flow VALIDATED READY (task b0eaddc5 Apr 5). Only Mev live keys block revenue.
- P9 Management System: LIVE at mev.otto.lk. Push to ottomev/otto-ui COMPLETED.
- P8 Broadcast System: MVP complete, awaiting Mev credentials
- Current emphasis: Ship over perfection, budget discipline. All Mev-blocked.
- **Mev directive (Apr 4)**: No funding for OpenAI/Zoho. OMS repo = ottomev/otto-ui. Stripe confirmed in WebAssist.
- 5 LinkedIn consulting articles in content DB. Awaiting Mev response on whether to publish.

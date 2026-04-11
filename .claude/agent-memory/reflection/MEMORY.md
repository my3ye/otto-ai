# Reflection Agent Memory

## System Baselines (updated 2026-04-11 cycle 580)
- **MEV RETURNED** (cycle 579) — Directing Koink.fun ecosystem build ($KOIN, $PENNY, PiPi).
- **PLAN CLEANUP (cycle 580)**: 5 dead plans cancelled (ab7a9849 lore-tokenomics, bf741055 wallet, 1ce164da cohesion, 9156d5d8 ZK ecosystem, 56443b32 Lucky Penny). All rate-limit casualties. Only 847c9b1d (repo init 2/3) remains viable.
- **Queue**: 0 running, ~13 otto-pending, 9 mev-pending. 9 unreviewed completed (Koink.fun research/lore/tokenomics/contracts). 1 zombie cleaned (c8a8f6e7).
- **zkPresence PROJECT FULLY COMPLETE** (cycle 574) — ALL tasks reviewed. All exit=0.
- **EMBEDDING RESILIENCE: COMPLETE** (cycle 570) — ALL memories have local embeddings (all-MiniLM-L6-v2, 384-dim).
- **CRITICAL: Zoho email DOWN** — trial expired. admin@otto.lk non-functional. Mev confirmed no funding.
- **Claude Code quota**: Rate-limited as of cycle 580. Previous full restore Apr 10.
- **Memory**: 1,557+ active. Evolve: 626 decayed, 0 dupes (cycle 580). GLOVE: 0 mismatches.
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Disk: 53% boot. RAM: 11Gi available.
- RL2F accuracy: **active-only 68% w=50** (34/50 matched). Stable. RE-BASELINE POINT from idle→active transition.
- **AutoEvolve**: Gen 7. 0 experiments. STAGNANT — needs attention when rate limit clears.
- **Procedures**: 75 exist.
- **WF notify step bug**: ALL 8 workflow templates have EMPTY notify step prompts (age 48c).
- **Kernel routing issue (age 22c)**: "No task" context not carried across messages.
- **Plan+rate-limit=zombie pattern (age 15c)**: tasks stuck as running with pid=None. Root cause UNPATCHED. 3 instances cleaned across cycles 579-580.
- **Priorities slot STALE** (2+ months): Still says "WebAssist first" but Mev actions show Koink.fun is current priority.
- **TODO next cycle**: (1) Review 9 completed Koink.fun tasks. (2) Re-create high-value cancelled plan items when rate limit clears (ZK ecosystem research, capital strategy). (3) Track RL2F re-baseline. (4) Ask Mev about priorities slot update.

## Known Gaps (persistent)
- **OpenAI quota exceeded (cycle 479+)**: `insufficient_quota` error, still down as of cycle 499 (Apr 4). Mev confirmed no funding. When restored: run full evolve + dedup cycle.
- **Semantic memory bloat (RESOLVED cycle 480)**: Archived 2,304 floor-relevance memories via DB-level archival. 4,420→2,116 active. No longer critical.
- **Claude Code quota exhaustion (cycle 480, recurred 561, RESTORED cycle 562)**: Original: Apr 1-3 (48h blackout). Recurrence Apr 8-10: 25 consecutive heartbeat/reflection failures. Restored Apr 10 12:30pm IST. Pattern: quota hits kill WF steps AND leave coordinator tasks as zombies. Scale: entire day (13 heartbeats + 12 reflections) lost to quota exhaustion.
- **RL2F accuracy: active-only 68% w=50 (cycle 575)** — 68% but CONFIRMED idle inflation (66->68% with 0 active tasks). Re-baseline when active work resumes. ALWAYS use `?active_only=true`.
- **OpenAI silent degradation (RESOLVED cycle 569)**: Was 94 null-embedding memories. LOCAL FALLBACK deployed — all 168 null-embed memories backfilled with local embeddings (all-MiniLM-L6-v2). No longer a blocker. Kimi investigation no longer needed.
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

# Reflection Agent Memory

## System Baselines (updated 2026-04-17 cycle 605)
- **MEV QUIET 13 DAYS** (last msg Apr 4). Orchestrator messaged Mev cycle 604 with paper analysis + Stripe nudge + grant question. Awaiting response.
- **Queue**: 0 running, 2 pending Otto (plan tasks), 5 mev-pending. 6 tasks reviewed this cycle (research-implementation WF). Rate limited — consolidation mode (20th consecutive cycle).
- **Plan "Deep Research Paper Integration"**: EXECUTING — 3/6 done, 0 failed. 2 pending Otto tasks remain. P1 self-improvement work.
- **Zoho email DOWN** — trial expired. ARCHIVED.
- **Claude Code quota**: Rate-limited. Previous full restore Apr 10.
- **Memory**: ~1,690 active. Evolve: 617 decayed, 0 dupes, 0 issues (cycle 605). GLOVE: 0 mismatches (stable).
- **Embeddings**: Local fallback (all-MiniLM-L6-v2) working. OpenAI down. Gemini API key renewal pending (Mev task, 7d+).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Disk: 58% boot. RAM: 10Gi available.
- RL2F accuracy: **active-only 72% w=50** stable. Meta_memory: direction=stable, cycles_since_improvement=10.
- **AutoEvolve**: Gen 7. Experiment f2427591 PROPOSED (carry-forward escalation). h001 CONFIRMED: rate limit override systematically prevents AutoEvolve. 32c stagnant.
- **Alpha**: Helius API keys ALL EXHAUSTED for Apr 2026. Alpha scans blocked.
- **WF notify step bug**: ALL 8 templates have EMPTY notify prompts (age 73c).
- **Kernel routing issue (age 47c)**: "No task" context not carried across messages.
- **Plan+rate-limit=zombie pattern (age 40c)**: tasks stuck as running with pid=None. Root cause UNPATCHED.
- **Priorities slot needs Mev input** (2+ months stale): Says "WebAssist first" but Koink.fun is active focus.
- **3 grant Mev tasks (24d)**: Gitcoin GG25, Solana Foundation, ENS grants — deadlines likely PAST. Orchestrator asked Mev about these.
- **DPC WFs low quality (age 20c)**: Both DPC-related WFs scored poorly (0.42, 0.56).
- **Agent swarm review (age 8c)**: Deferred during rate limit. MUST-DO next non-rate-limited cycle.
- **Deep task output quality review (NEW)**: 6 WF tasks reviewed shallow (exit-code-only). Need output quality verification.
- **TODO next cycle**: (1) Activate AutoEvolve experiment f2427591. (2) Agent swarm review (overdue 8c). (3) Check Mev response. (4) Verify research-implementation WF output quality. (5) If rate limit clears: run remaining plan tasks + implement paper findings.

## Known Gaps (persistent)
- **OpenAI quota exceeded (cycle 479+)**: `insufficient_quota` error, still down as of cycle 499 (Apr 4). Mev confirmed no funding. When restored: run full evolve + dedup cycle.
- **Semantic memory bloat (RESOLVED cycle 480)**: Archived 2,304 floor-relevance memories via DB-level archival. 4,420→2,116 active. No longer critical.
- **Claude Code quota exhaustion (cycle 480, recurred 561, RESTORED cycle 562)**: Original: Apr 1-3 (48h blackout). Recurrence Apr 8-10: 25 consecutive heartbeat/reflection failures. Restored Apr 10 12:30pm IST. Pattern: quota hits kill WF steps AND leave coordinator tasks as zombies. Scale: entire day (13 heartbeats + 12 reflections) lost to quota exhaustion.
- **RL2F accuracy: active-only 72% w=50 (cycle 589)** — improved from 70% (cycle 588), from 68% (cycle 575). MARS assessed as weak signal during idle (low active volume). Re-baseline when active work resumes. ALWAYS use `?active_only=true`.
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
- P10 WebAssist: LIVE at webassist.ink. Stripe payment flow VALIDATED READY. Only Mev live keys block revenue.
- P9 Koink.fun ecosystem: ACTIVE — 6 project chain-fit WFs complete. Pink Paper v6 committed (b7b275a). 4 paused WFs remaining. Tokenomics, Lucky Penny contracts in progress.
- P9 Management System: LIVE at mev.otto.lk.
- P8 Broadcast System: MVP complete, awaiting Mev credentials.
- Current emphasis: Koink.fun ecosystem completion. Budget discipline. Rate-limited.
- **Mev directive (Apr 4)**: No funding for OpenAI/Zoho. OMS repo = ottomev/otto-ui.

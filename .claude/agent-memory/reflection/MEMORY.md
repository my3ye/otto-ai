# Reflection Agent Memory

## System Baselines (updated 2026-04-14 cycle 602)
- **MEV QUIET 10 DAYS** (last msg Apr 4). Koink.fun ecosystem: 6 project WFs COMPLETE. 505.systems /docs live. Pink Paper v6 committed (b7b275a). 4 paused WFs remain.
- **Queue**: 0 running, 7 mev-pending. 2 unreviewed Mev-owned (Zoho + OpenAI — owner=mev, non-reviewable by Otto). Rate limited — consolidation mode (17th+ consecutive cycle).
- **Zoho email DOWN** — trial expired. ARCHIVED. Zoho renewal task is STALE.
- **Claude Code quota**: Rate-limited. Previous full restore Apr 10.
- **Memory**: 1,685 active. Evolve: 596 decayed, 0 dupes, 12 critique-refined (cycle 602). GLOVE: 2nd consecutive success (15 probed, 0 mismatches) — likely recovered, needs 3rd confirmation.
- **Embeddings**: Local fallback (all-MiniLM-L6-v2) working. OpenAI down. Gemini API key renewal pending (Mev task).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Disk: 57% boot. RAM: 9.4Gi available.
- RL2F accuracy: **active-only 72% w=50** stable. Meta_memory: direction=stable, cycles_since_improvement=7.
- **AutoEvolve**: Gen 7. 0 experiments. STAGNANT (age 29c) — FIRST PRIORITY when capacity returns.
- **Agent success**: 100% exit_code on recent tasks (Pink Paper v6 = latest, exit 0).
- **WF notify step bug**: ALL 8 templates have EMPTY notify prompts (age 70c).
- **Kernel routing issue (age 44c)**: "No task" context not carried across messages.
- **Plan+rate-limit=zombie pattern (age 37c)**: tasks stuck as running with pid=None. Root cause UNPATCHED.
- **Priorities slot needs Mev input** (2+ months stale): Says "WebAssist first" but Koink.fun is active focus.
- **3 grant Mev tasks (22d)**: Gitcoin GG25, Solana Foundation, ENS grants — deadlines likely PAST. Escalation-ready: orchestrator should nudge Mev or archive.
- **DPC WFs low quality (age 17c)**: Both DPC-related WFs scored poorly (0.42, 0.56).
- **Sync Pulse frequency (age 18c)**: 15x/6h. Cost review needed — past escalation threshold.
- **GLOVE likely recovered (age 1c)**: 2nd consecutive success (15 probed, 0 mismatches). Needs 3rd confirmation next cycle.
- **Agent swarm review (age 5c)**: Deferred during rate limit. MUST-DO next non-rate-limited cycle.
- **TODO next cycle**: (1) When rate limit clears: AutoEvolve experiment FIRST (29c stagnant). (2) Confirm GLOVE stability (3rd consecutive success?). (3) Agent swarm review (overdue 5c). (4) Grant tasks: nudge Mev or archive. (5) Sync Pulse cost investigation (past escalation threshold).

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

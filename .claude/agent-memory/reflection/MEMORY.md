# Reflection Agent Memory

## System Baselines (updated 2026-03-23 cycle 370)
- Memory: 2405+ active. Evolve healthy (1562 decay, 4 facts, 0 dupes). GLOVE: 0/15 mismatches (clean).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: 42% boot. RAM: 5.0GB/16GB.
- Queue: 0 unreviewed. 0 pending. 0 running. All clean — awaiting Mev direction.
- RL2F accuracy: 38% (19/50) — trend DECLINING (58→...→44→42→40→38%). Self-patch 68eac95a applied but decline continued. Recovery requires active work cycles. AutoEvolve trigger met (RL2F<70%).
- Workflows: 29+ completed. 0 running. Templates: feature-dev v4 (0.82), content-publishing v4 (0.79), social-content v3 (0.68), research-pipeline v3 (0.76). 4 new v1 templates: outbound-sales, smart-contract, grant-application, product-sprint. 6 PENDING experiments awaiting new runs.
- Agents: 100% success rate across all agent types (last 30 tasks).
- Procedures: 15 total, top 3 above 0.95 trust. reactive_analysis_dispatch at 0.96 (188 uses).
- Security: API bound to localhost (127.0.0.1:8100). UFW enabled (22/80/443/3001 allowed). Risk 3/10. api.py source fix verified not needed (no uvicorn.run in source — systemd handles binding).
- **Wink noise FIXED (cycle 346)**: wink_critical at importance 5 (borderline). Noise minimal.

## Known Gaps (persistent)
- **RL2F accuracy: 38% (19/50) DECLINING** — Continued decline (58→...→44→42→40→38%). Self-patch 68eac95a may be insufficient — decline continued post-patch. True test requires active work cycles. If no recovery within 5 active cycles, deeper investigation needed. AutoEvolve trigger met (RL2F<70%, gen 1) — start experiment when rate limit clears. 4th consecutive GOAL_ALIGN=3 cycle.
- **Social-content workflow**: Evolution triggered cycle 368 (v2→v3). Fitness still 0.68, needs a new run to measure. If no improvement after next run, consider structural mutation (merge/remove steps).
- **Orchestrator review gap (cycle 363, RESOLVED cycle 364)**: 6 intermediate workflow steps were unreviewed — orchestrator reviewed them in the following heartbeat cycle. Not recurring.
- **v1 workflow templates untested (cycle 368+)**: 4 templates (outbound-sales, smart-contract, grant-application, product-sprint) with no fitness scores. Track: if untested after 10 more cycles (cycle 380), consider archiving or synthetic test.
- **Researcher agent memory bloat: FIXED (cycle 347)** — Task b5b5ba2b cleaned 454->199 lines (56% reduction). QA approved, committed c45d6d88.
- **Zombie task gap (FIXED cycle 323)**: task_runner.sh had `set -euo pipefail` with NO trap handler. Any unguarded command failure killed the script before the completion callback, creating zombies. 7 total process-died failures. FIX: added `trap cleanup_on_exit EXIT` handler that marks tasks as failed via API on unexpected exit. Secondary fix needed: add `|| true` guards to pre-flight git commands. Stale-task reaper still recommended as defense-in-depth.
- **LLM fallback chain**: Kimi→OpenAI→Claude CLI. Working since cycle 93. Claude CLI fallback untested but non-critical.
- **Agent swarm**: Only `coder` and `researcher` have memory. Tasks don't use agent_type classification. Low priority.
- **Eval baseline**: No eval runs exist. Deferred until active work cycle.
- **Wink monitor false positives (FIXED cycle 346)**: Lowered importance in task_monitor.sh: stall alert 6→3, stall critical 8→5, tool failures 7→5, reasoning loops 7→5. Routine stalls now below MARS sweep threshold. Previous state: 53% of high-importance events were wink noise.

## Recurring Patterns
- System enters idle holds when awaiting Mev. This is correct behavior per budget discipline directive.
- Open proposals typically take 12-48h for Mev response. Nudge threshold: >24h.
- Memory evolve pipeline RESTORED (cycle 93, OpenAI fallback). GLOVE over-flagging FIXED (cycle 94, prompt rewrite). Both working correctly now.
- Handoff timestamps from orchestrator/reflection can be days old if system is idle — normal.

## Anti-Patterns to Watch
- **Double decay**: NEVER apply manual relevance_score decay on top of evolve endpoint's 0.99x. Caused mass-archival incident (558->44 memories, 2026-03-04).
- **Stale blockers**: If a blocker appears 2+ cycles without progress, verify via API. Don't trust working memory blindly.
- **Task creation during rate limit**: System prompt may include rate limit alerts — respect them. Memory consolidation only.
- **Empty TraceMem narratives**: Episodic consolidation sometimes creates empty summaries. Archive when found.
- **Self-patch mechanism gap**: heartbeat.md has no step to check/apply pending self-patches from projects/self_patches/. Direct edits work fine but the staged patch workflow is broken. Low priority.
- **GLOVE false-positive damage (FIXED cycle 94)**: GLOVE's generic verification prompt flagged 80% of memories as "stale" with aggressive -0.3 salience decay. Over 7+ cycles, this eroded 106 memories to near-zero salience. Fix: domain-context prompt + reduced decay (-0.05). LESSON: LLM verification systems need domain context, and auto-decay on unverified flags must be conservative.
- **False observation propagation (FIXED cycle 327)**: "total_uses=null" was reported for ALL 14 procedures across 3+ cycles. Root cause: `total_uses` field doesn't exist in ProcedureOut model — correct fields are `success_count`/`failure_count`. Top 3 procedures had 174/105/24 uses respectively. LESSON: Always verify field names against the actual model before reporting API observations. False alarms propagate indefinitely through persistent memory.

## Priority Context
- P10 SIGNALS REVENUE: Pipeline OPERATIONAL. **Signal quality tier system IMPLEMENTED (cycle 141, task 414f2de4, commit 4417b517)**. Tier 1: SM_10 (83% WR, base 60/100, always publishes). Tier 2: Convergence 4+ wallets (base 10*count, publishes if quality >= 50). Tier 3: Unvetted single wallet (blocked). Bonus scoring: token age, volume spike, repeat convergence. Gate: MIN_PUBLISHER_QUALITY_SCORE=50. Previous: 3 signals published (PUMP, RENDER, PYTH). Daily cap 3/3. Helius rotation (3 keys). Publisher: `~/otto/projects/alpha/signals/signal_publisher.py`. TODO: verify production timers running + SM_10 signals flowing.
- P10 WebAssist: LIVE at webassist.ink. Resend scope FULLY corrected (admin notif removed + lead confirmation removed). Resend reserved for ecosystem/partnership outreach + invoicing ONLY. BLOCKER: Stripe/Wise keys needed from Mev to activate payments.
- P9 Management System: LIVE at mev.otto.lk
- P8 Broadcast System: MVP complete, awaiting Mev credentials
- Current directive emphasis: Ship over perfection, budget discipline, ACTIVE EXECUTION (Mev: GO ACHIEVE)
- **Reactive dispatch working well**: 8 tasks auto-created from Mev WhatsApp messages, 7 completed successfully (1 QA rejected: budget exceeded on multi-track research). Latest: semantic dedup fix (b625a3ad, commit ab33d354). Key lesson from dedup: content-ID based dedup beats text-similarity dedup for LLM-generated messages.
- **Birdeye integration (cycle 88)**: birdeye_client.py (token_overview, OHLCV, price_at_timestamp, win_rate, wallet scoring). birdeye_requalification.py (full Week 2 pipeline). Rug filter in live_watcher.py. Free tier limitation: no /defi/token_security — uses proxy from overview data. Helius for tx history + Birdeye OHLCV for pricing.
- **Wallet pool rebuild (cycle 91)**: wallet_discovery.py built (commit 245cbbc7). 11 qualified directional traders from 75 scored candidates. Avg WR 76.3%, avg PnL +2.42 SOL. Top: KGaphGSWg (95% WR, 19 trades). CAVEAT: MIN_TRADES=5, some top wallets have tiny sample. discovered_traders.json has results. Old pool was 17/18 LP/bot positions. Next: orchestrator shares with Mev + deployment decision.
- **QA external repo blind spot**: Tasks modifying /mnt/media/projects/* get QA auto-approved with "no file changes" — QA can't detect changes outside otto repo. Orchestrator must verify these manually.
- **Brand bibles gap**: Mev asked about brand narratives/character lore research — Otto couldn't find it. Universe system may need brand narrative data populated.

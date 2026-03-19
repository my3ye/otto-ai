# Reflection Agent Memory

## System Baselines (updated 2026-03-19 cycle 338)
- Memory: Evolve healthy (1211 decay, 5 facts, 0 dupes this cycle). GLOVE: 0/15 mismatches (clean, 29+ consecutive cycles).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: ~40% boot. RAM: ~5.7GB/16GB.
- Procedures: 15. Top 3 ACTIVELY USED: reactive_analysis_dispatch trust 0.99 (133 uses), research_and_implement_cycle trust 0.90 (201 uses), create_and_launch_task trust 0.98 (44 uses).
- Queue: 5 unreviewed. 0 pending. 1 running. 583 completed, 45 failed.
- RL2F accuracy: 60% (30/50) FLAT. Trajectory: 56%→62%→64%→62%→60%→60%. AutoEvolve gen-1 KEPT, gen-2 trigger met (RL2F<70%) but deferred (rate limited).
- Workflows: 10 instances completed. Templates: feature-dev v3 (0.82), content-publishing v1 (0.76), social-content v2 (0.68), research-pipeline v1 (no fitness). 1 running (landing page copy).
- Agent performance (last 30 tasks): All 10 agent types at 100% success.

## Known Gaps (persistent)
- **RL2F accuracy: 60% (30/50) FLAT** — trajectory: 56% (cycle 205) → 62% (cycle 323) → 64% (cycle 326) → 62% (cycle 334) → 60% (cycles 335-338). Gen-1 KEPT. API trend field says "improving" but raw count unchanged — don't trust trend when count is static. Orchestrator compliance gap: reported 45% when actual was 60% (principle #9 exists but not followed). AutoEvolve gen-2 trigger met but rate-limited.
- **Zombie task gap (FIXED cycle 323)**: task_runner.sh had `set -euo pipefail` with NO trap handler. Any unguarded command failure killed the script before the completion callback, creating zombies. 7 total process-died failures. FIX: added `trap cleanup_on_exit EXIT` handler that marks tasks as failed via API on unexpected exit. Secondary fix needed: add `|| true` guards to pre-flight git commands. Stale-task reaper still recommended as defense-in-depth.
- **LLM fallback chain**: Kimi→OpenAI→Claude CLI. Working since cycle 93. Claude CLI fallback untested but non-critical.
- **Agent swarm**: Only `coder` and `researcher` have memory. Tasks don't use agent_type classification. Low priority.
- **Eval baseline**: No eval runs exist. Deferred until active work cycle.
- **Wink monitor false positives**: Stall threshold fires on healthy I/O-heavy tasks. Non-critical noise.

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

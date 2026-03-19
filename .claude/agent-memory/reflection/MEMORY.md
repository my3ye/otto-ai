# Reflection Agent Memory

## System Baselines (updated 2026-03-18 cycle 326)
- Memory: Evolve healthy (1095 decay, 4 facts, 0 dupes this cycle). GLOVE: 0/15 mismatches (clean, 27+ consecutive cycles).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: ~40% boot. RAM: ~4.4GB/16GB.
- Procedures: 14. Top 3 ACTIVELY USED: research_and_implement_cycle trust 0.85 (174 uses, 96.6% success), reactive_analysis_dispatch trust 0.75 (105 uses, 94.3%), deploy_webassist_changes trust 0.72 (24 uses, 87.5%). 11 others at trust 0.45-0.50 with 0-1 uses. **Threshold mismatch FIXED cycle 327**: PROC_NAMES tracking was at ≥0.55 while injection at ≥0.40 — 11 procedures could never build trust. Fixed to ≥0.40.
- Queue: 0 unreviewed. 0 pending. 0 running. ~500 completed, 38 failed.
- RL2F accuracy: 64% (32/50) IMPROVING. AutoEvolve gen-1 KEPT.
- Agent memory audit (cycle 326): researcher 427L, coder 81L, reviewer 4L, debugger 6L. architect+memory-curator have no memory files. All agents 100% success in last 30 tasks. Low priority.

## Known Gaps (persistent)
- **RL2F accuracy: 64% (32/50) IMPROVING** — improved from 56% (cycle 205) → 62% (cycle 323) → 64% (cycle 326). Gen-1 KEPT. Trend confirmed by API.
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

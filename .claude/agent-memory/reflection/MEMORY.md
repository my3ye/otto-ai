# Reflection Agent Memory

## System Baselines (updated 2026-03-10 cycle 141)
- Memory: ~387 active. Evolve: decay=80, facts=2. GLOVE: 0 mismatches (clean).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: 33% boot, 3% media. RAM: 4.6GB/16GB.
- Procedures: 10. research_and_implement_cycle trust 0.97 (27/0). reactive_analysis_dispatch trust 0.83. Others 0.50.
- Queue: 0 unreviewed. 0 pending/running. Task 414f2de4 reviewed+approved this cycle.
- RL2F accuracy: 88.0% (44/50). +2 from cycle 140 (43→44). Genuine — matched prediction about Mev's external behavior (responding after 6h silence), not idle state.
- **Self-patch 1b60d774**: SUPERSEDED (cycle 141). Fix was already applied directly to heartbeat.md. Patch file marked superseded.

## Known Gaps (persistent)
- **RL2F accuracy: 88.0% (44/50)** — genuine improvement (+2). Matched external behavior prediction. Coarse metric (2% per match in 50-entry window).
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

## Priority Context
- P10 SIGNALS REVENUE: Pipeline OPERATIONAL. **Signal quality tier system IMPLEMENTED (cycle 141, task 414f2de4, commit 4417b517)**. Tier 1: SM_10 (83% WR, base 60/100, always publishes). Tier 2: Convergence 4+ wallets (base 10*count, publishes if quality >= 50). Tier 3: Unvetted single wallet (blocked). Bonus scoring: token age, volume spike, repeat convergence. Gate: MIN_PUBLISHER_QUALITY_SCORE=50. Previous: 3 signals published (PUMP, RENDER, PYTH). Daily cap 3/3. Helius rotation (3 keys). Publisher: `~/otto/projects/alpha/signals/signal_publisher.py`. TODO: verify production timers running + SM_10 signals flowing.
- P10 WebAssist: LIVE at webassist.ink. Lighthouse: Perf 72, LCP 4.85s (needs fix), A11y 54 (needs fix). Reports at ~/otto/logs/lighthouse/. No /pricing route — pricing is homepage section.
- P9 Management System: LIVE at mev.otto.lk
- P8 Broadcast System: MVP complete, awaiting Mev credentials
- Current directive emphasis: Ship over perfection, budget discipline, idle hold
- **Reactive dispatch working well**: 7 tasks auto-created from Mev WhatsApp messages, 6 completed successfully (1 QA rejected: budget exceeded on multi-track research). Latest: research pipeline timer (b0a81cc6). Principle: iterative research needs $8-10 or split into single-track $5 tasks.
- **Birdeye integration (cycle 88)**: birdeye_client.py (token_overview, OHLCV, price_at_timestamp, win_rate, wallet scoring). birdeye_requalification.py (full Week 2 pipeline). Rug filter in live_watcher.py. Free tier limitation: no /defi/token_security — uses proxy from overview data. Helius for tx history + Birdeye OHLCV for pricing.
- **Wallet pool rebuild (cycle 91)**: wallet_discovery.py built (commit 245cbbc7). 11 qualified directional traders from 75 scored candidates. Avg WR 76.3%, avg PnL +2.42 SOL. Top: KGaphGSWg (95% WR, 19 trades). CAVEAT: MIN_TRADES=5, some top wallets have tiny sample. discovered_traders.json has results. Old pool was 17/18 LP/bot positions. Next: orchestrator shares with Mev + deployment decision.
- **QA external repo blind spot**: Tasks modifying /mnt/media/projects/* get QA auto-approved with "no file changes" — QA can't detect changes outside otto repo. Orchestrator must verify these manually.
- **Brand bibles gap**: Mev asked about brand narratives/character lore research — Otto couldn't find it. Universe system may need brand narrative data populated.

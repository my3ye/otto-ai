# Reflection Agent Memory

## System Baselines (updated 2026-03-28 cycle 431)
- Memory: Evolve healthy (2331 decay, 5 facts, 0 dupes). GLOVE: 0/15 mismatches (clean).
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: 44% boot. RAM: 5.2GB/15GB (up from 4.4 — 3 architect tasks running).
- Queue: 14 unreviewed completed, 3 running (STEM architect tasks), 8 pending (4 otto + 4 Mev-owned).
- **Mev RETURNED ~00:19 IST Mar 28** (after ~42h break). Directed STEM Agent paper extraction + content fixes.
- RL2F accuracy: 32% (16/50) — DECLINING (prior 46%). 44 cycles without improvement. 68% partial, 0% miss.
- **AutoEvolve**: Gen 2, experiment 6435f629 ACTIVE at cycle 3/10 (+4pp vs baseline 28%). State Delta patch on heartbeat.md.
- **STEM Agent gap implementation**: 3 architect tasks running (A2A Protocol, MCP Externalization, Dynamic Tool Composition). 3 implementation + 1 integration test pending.
- **Stuck task**: 1803400a (RL2F research) — no PID after 6h. Flagged for orchestrator.
- **Crashed-at-line-1 pattern**: Still pending debugger task (deferred — rate limited).
- Workflows: Templates: feature-dev v7 (0.82), content-publishing v15 (0.83), social-content v4 (0.80), research-pipeline v7 (0.78). 3 paused WFs.
- Agents: 97% success (29/30 last batch). Researcher 266L, coder 81L, reviewer 54L, architect 27L. All healthy.
- **Wink noise FIXED (cycle 346)**: wink_critical at importance 5 (borderline). Noise minimal.

## Known Gaps (persistent)
- **RL2F accuracy: 32% (16/50) DECLINING** — prior window 46%, current 32% (14pp drop). 44 cycles without improvement. State Delta experiment at cycle 3/10, showing +4pp vs baseline (28%→32%). Key insight: 68% partial rate (34/50) is THE improvement target — 0% miss means predictions are directionally correct but imprecise. Most partials involve predicting Mev behavior timing.
- **Crashed-at-line-1 failures (NEW cycle 428)**: 5 failures across blockchain-security-auditor, reviewer, coder, content-creator. Not agent-specific — task_runner.sh issue. Needs debugger investigation. Priority: HIGH (25% failure rate).
- **AutoEvolve template contamination (FIXED cycle 408)**: content-publishing-pipeline v9 had hardcoded project-specific guard. SYSTEMIC: AutoEvolve needs validation that mutations don't inject project-specific references into generic templates.
- **Annotation WF paused at step 1**: Part of on-chain annotation plan (5/7 done, 2 failed). Needs retry when slots free.
- **v1 workflow templates untested (dormant)**: 4 templates (outbound-sales, smart-contract, grant-application, product-sprint). Accepted as dormant — will be tested when relevant work arrives.
- **Zombie task gap (FIXED cycle 323)**: trap handler added. Secondary fix (|| true guards on git commands) still pending.
- **LLM fallback chain**: Kimi->OpenAI->Claude CLI. Working since cycle 93.
- **Agent swarm**: 6 agents have memory (researcher 266L, coder 81L, reviewer 54L, architect 27L, content-creator 13L, debugger 10L). All healthy.
- **Eval baseline**: No eval runs exist. Deferred until active work cycle.
- **Self-patch mechanism gap**: heartbeat.md has no step to check/apply pending self-patches. Reflection applied patch directly this cycle as workaround.

## Recurring Patterns
- System enters idle holds when awaiting Mev. This is correct behavior per budget discipline directive.
- Open proposals typically take 12-48h for Mev response. Nudge threshold: >24h.
- Memory evolve pipeline RESTORED (cycle 93, OpenAI fallback). GLOVE over-flagging FIXED (cycle 94). Both working correctly.
- Handoff timestamps from orchestrator/reflection can be days old if system is idle — normal.
- **AutoEvolve mutations can contaminate generic templates** — always verify after AutoEvolve runs.
- **Reflection can and should apply patches directly** when orchestrator doesn't pick them up within 1 cycle — proven in cycle 428.

## Anti-Patterns to Watch
- **Double decay**: NEVER apply manual relevance_score decay on top of evolve endpoint's 0.99x.
- **Stale blockers**: If a blocker appears 2+ cycles without progress, verify via API.
- **Task creation during rate limit**: Respect rate limit alerts. Memory consolidation only.
- **Empty TraceMem narratives**: Episodic consolidation sometimes creates empty summaries. Archive when found.
- **False observation propagation**: Always verify field names against the actual model before reporting. False alarms propagate indefinitely through persistent memory.

## Priority Context
- P10 WebAssist: LIVE at webassist.ink. BLOCKER: Stripe/Wise keys needed from Mev.
- P9 Management System: LIVE at mev.otto.lk
- P8 Broadcast System: MVP complete, awaiting Mev credentials
- Current emphasis: Ship over perfection, budget discipline, ACTIVE EXECUTION
- **Directive burst (Mar 27)**: 18+ tasks completed covering governance, annotation contracts, royalty streaming, calendar UI, social campaigns, contributor docs. All done.
- **QA external repo blind spot**: Tasks modifying /mnt/media/projects/* get QA auto-approved. Must verify manually.

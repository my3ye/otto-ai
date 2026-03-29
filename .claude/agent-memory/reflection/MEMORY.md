# Reflection Agent Memory

## System Baselines (updated 2026-03-29 cycle 445)
- Memory: Evolve healthy (2483 decay, 3 facts, 0 dupes). GLOVE: 0/15 clean.
- Services: ALL ACTIVE (otto-memory, heartbeat, reflection). Docker: postgres, neo4j, graphiti.
- Disk: 44% boot. RAM: 4.3GB/15GB. Queue ACTIVE (3 running, 5 pending).
- Queue: 3 running (contributor compensation contracts), 1 Otto-owned pending (Solidity), 4 Mev-owned pending, 1 unreviewed.
- RL2F accuracy: 36% (18/50) — STABLE. 58 cycles without improvement.
- **AutoEvolve**: Gen 4, experiment ac43fbb0 ACTIVE (activated from proposed state in cycle 445 via DB) — tracking RL2F prediction fix.
- Workflows: feature-dev v9 (0.82), content-publishing v17 (0.83), social-content v5 (0.80), research-pipeline v11 (0.79).
- Agents: Researcher 334L, coder 81L, reviewer 76L, architect 34L, content-creator 13L, debugger 12L.
- **API pagination gotcha**: Session hook `/tasks?reviewed=false` returns max 20 — always use `limit=50` to get true count.

## Known Gaps (persistent)
- **RL2F accuracy: 36% (18/50) STABLE** — stalled 57 cycles. ROOT CAUSE IDENTIFIED (cycle 444): All 5/5 recent predictions violate normative principle by including Mev-timing predictions ("IF Mev responds within 6h"). Self-patch applied to heartbeat.md — hard ban on Mev mentions in EXPECTED field. AutoEvolve Gen 4 experiment ac43fbb0 tracking. Expected: accuracy should rise toward 50%+ within 10 cycles IF orchestrator follows the new instruction.
- **Crashed-at-line-1 failures (NEW cycle 428)**: 5 failures across blockchain-security-auditor, reviewer, coder, content-creator. Not agent-specific — task_runner.sh issue. Needs debugger investigation. Priority: HIGH (25% failure rate).
- **AutoEvolve template contamination (FIXED cycle 408)**: content-publishing-pipeline v9 had hardcoded project-specific guard. SYSTEMIC: AutoEvolve needs validation that mutations don't inject project-specific references into generic templates.
- **Annotation WF paused at step 1**: Part of on-chain annotation plan (5/7 done, 2 failed). Needs retry when slots free.
- **v1 workflow templates untested (dormant)**: 4 templates (outbound-sales, smart-contract, grant-application, product-sprint). Accepted as dormant — will be tested when relevant work arrives.
- **Zombie task gap (FIXED cycle 323)**: trap handler added. Secondary fix (|| true guards on git commands) still pending.
- **LLM fallback chain**: Kimi->OpenAI->Claude CLI. Working since cycle 93.
- **Agent swarm**: 6 agents have memory (researcher 266L, coder 81L, reviewer 54L, architect 27L, content-creator 13L, debugger 10L). All healthy.
- **Eval baseline**: No eval runs exist. Deferred until active work cycle.
- **Self-patch mechanism gap**: heartbeat.md has no step to check/apply pending self-patches. Reflection applied patch directly this cycle as workaround.
- **Plan DAG executor bug (NEW cycle 445)**: Tasks in plan 9a40a60f launched with unmet dependencies. Security audit (fba08c82) ran while Solidity contracts (866f1984) were still pending. Reviewer (d6a45578) launched with 2/3 deps unmet, then FAILED. Suspected root cause: race in create_plan_with_tasks() or alternative launch path. Stored as semantic memory + normative principle. Needs P7 debugger task.

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
- **Directive burst (Mar 27-29)**: 50+ tasks completed across governance, annotation, Sri Lanka movement, DPC Dashboard, articles. All done.
- **QA external repo blind spot**: Tasks modifying /mnt/media/projects/* get QA auto-approved. Must verify manually.
- All tasks reviewed+approved (prior to this cycle). Queue now active with salary contract plan.
- **Mev directive (Mar 29)**: Salary contract — 9k/month from treasury reserve, capped, for all contributors. Plan created (5 tasks), executing with DAG issues.

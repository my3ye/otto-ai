---
name: reflection_meta_layer_gap_analysis
description: Frozen meta-layer gaps in reflection.md vs DGM/HyperAgents model — 7 gaps identified, AutoEvolve never executes, RL2F at 30% declining
type: project
---

Reflection meta-layer gap analysis complete (2026-03-24). Full doc: ~/otto/docs/reflection-meta-layer-gap-analysis-2026-03-24.md

**Key finding:** reflection.md is a frozen meta-agent — its growth mechanisms (AutoEvolve Step 7c, self_patch Step 7b) are structurally unreachable in normal operation because budget is consumed by Steps 0–5 before reaching them.

**7 Frozen Assumptions:**
1. Fixed step ordering (always linear 0→8) — no adaptive routing by system state
2. Fixed $1.00 budget — no step-level budget allocation
3. Human-gated self-modification — self_patches staged but rarely auto-applied
4. Text-only meta→domain binding — reflection advises orchestrator, cannot compel
5. No step-level telemetry — reflection can't reason about its own value-per-step
6. AutoEvolve = Generation 1 since 2026-03-18, 0 active experiments ever
7. RL2F at 30% (down from 60%), trend declining, no systemic meta-response

**Why: The DGM Bottleneck (HyperAgents, arXiv:2603.19461)**
The domain agent (heartbeat/orchestrator) has improved via RL2F/MARS/memory. The meta-agent (reflection.md) has not evolved since written. This is exactly the frozen meta-layer pattern HyperAgents identifies as the ceiling on recursive self-improvement.

**Top 3 Interventions:**
1. Move AutoEvolve/self_patch to Step 1 during idle cycles (conditional branch at Step 0)
2. Enable auto-apply of staged patches after 48h with no veto (heartbeat.md change)
3. Add step telemetry: log which steps execute + budget spent per step

**How to apply:** When designing self-improvement changes, treat reflection.md as a frozen DGM bottleneck — even small structural changes to its ordering/budget logic have outsized leverage on Otto's long-term capability growth.

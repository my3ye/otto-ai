---
name: constraint_injection_checkpoints_research
description: Research synthesis on constraint-injection checkpoints for heartbeat.md OODA loop + 3 related improvements (RL2F idle-cycle fix, S-MMU threshold, SSA formatter). Validated 2026-03-23.
type: project
---

# Constraint-Injection Checkpoints Research (2026-03-23)

**Research Note ID**: 3f2c120e-bfae-4d36-a7b7-7685670f2534  
**Semantic Memory IDs**: eae83da8, 98591a29, 6600825b, 69b7712c  
**Sources**: 27 (5 web, 10 memory, 5 graph, 5 code, 2 papers). Validation: PASSED (no contradictions discarded).

## Key Findings

### [RANK 1 — HIGH conf — P7 IMMEDIATE] Constraint-injection gates in heartbeat.md
- Current COLLABORATE CHECK is **post-DECIDE** — not a pre-action abort gate
- Fix (PG-CoT): 3 gates in OODA loop:
  - **Post-WHY**: `if budget_remaining < $0.10 OR rate_limited → abort + log` (binary, no ambiguity)
  - **Post-DECIDE**: verify proposed task aligns with active P1-P10 directives
  - **Post-EXPECTED**: tag prediction as `idle_cycle` vs `active_cycle` before RL2F write
- External consensus: LlamaFirewall, SagaLLM, Task Shield, OMNIFLOW all converge
- File: `otto/.claude/agents/heartbeat.md`
- **Start with binary budget gate. Subjective alignment gate second.**

### [RANK 2 — MEDIUM-HIGH conf — P6] RL2F idle-cycle window fix
- 29/50 window entries = idle predictions (queue=0/0/0) — trivially correct, zero signal
- Root cause of 36% accuracy / 12-cycle decline
- Fix: tag `idle_cycle: true/false` at write time; score `active_cycle_accuracy` separately
- **Independent from Rank 1** — both needed, neither substitutes

### [RANK 3 — MEDIUM conf — P5] S-MMU similarity threshold
- Add `similarity_threshold=0.7` to slice injection in `smmu.py`
- Near-miss slices → L2 (not dropped, not injected to L1)
- File: `otto/memory/kernel/smmu.py`

### [DEFERRED — P6] SSA telemetry formatter
- Convert raw JSON task/health → 3-5 line linguistic summaries before S-MMU injection
- No new urgency signal; carry forward

## Validated Contradictions (accepted, not discarded)
1. PG-CoT domain gap: validated on physics (hard binary), not agent governance (soft). Mitigation: binary gate first.
2. RL2F fix options (exclude idle vs separate scoring) — need 1-2 active cycles to validate which is better.
3. A-MEM memory architecture — relevant long-term, no overlap with this scope.

**Why**: Mev asked to evaluate Honcho by Plastic Labs + what improvements it suggested for Otto's system. This research evaluated constraint-injection (highest-value finding) + 3 related improvements.  
**How to apply**: Next implementation task should target heartbeat.md binary budget gate first. RL2F idle tagging is P6.

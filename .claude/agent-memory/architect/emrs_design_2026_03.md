---
name: emrs_design_2026_03
description: Evolvable Meta-Reflection System (EMRS) design (2026-03-24). 3-component architecture to unfreeze Otto's reflection meta-layer and enable recursive self-improvement.
type: project
---

EMRS designed 2026-03-24 to fix Otto's frozen meta-layer (DGM-H bottleneck diagnosis).

**Why:** reflection.md is a 1220-line doc with AutoEvolve at Step 7c. Budget ($1.00/10min) is exhausted before reaching it. AutoEvolve has been at generation 1 since 2026-03-18 with 0 experiments. RL2F at 30% declining with no systemic response.

**3 Components:**

1. **meta_memory.json** — `~/otto/meta_memory.json`. Cross-session causal learning file. Fields: causal_hypotheses, best_cycle_analysis, forward_plans, rl2f_trend, autoevolve_state. Read at Step 0, write at Step 8. Atomic write (tmp→mv). File-based (not DB) to avoid HTTP overhead in budget-constrained session.

2. **Cycle Classifier (Step 0.5)** — New step inserted after ReflAct block. Classifies cycle as IDLE | DEGRADED | HEALTHY | CRITICAL. IDLE/DEGRADED → jump to AutoEvolve (Step 7c) FIRST. This is the minimal fix that unblocks AutoEvolve immediately (~5 lines added to reflection.md).

3. **Versioned Reflection Manifest** — Migration 075: `reflection_versions` table. Tracks every self-modification: version, content_hash, diff, rl2f_before, rl2f_after, status, auto-rollback trigger. Status machine: pending_veto → active → kept | rolled_back | auto_rolled_back. 48h veto window before auto-apply. Auto-rollback if RL2F drops >15% over 5 cycles.

**Guardrails:** Budget floor (MARS+GLOVE+health always run), 50-line cap per patch, 3 patch queue cap, constitutional lock (personality/identity = Mev approval required), 5-cycle auto-rollback threshold, exploration diversity (G6: next experiment must target different file than last 3).

**Implementation phases:**
- Phase 1 (~$3-4): Step 0.5 + meta_memory.json bootstrap — fixes root cause immediately
- Phase 2 (~$4-5): Migration 075 + version endpoints + self_patch.py integration
- Phase 3 (~$3): OMS visibility tab + WhatsApp patch notifications

**Success metrics:** AutoEvolve generation 2+ (from 1), RL2F stabilized (from 30% declining), meta_memory.json accumulating causal hypotheses.

**Full design at:** `~/otto/docs/evolvable-meta-reflection-architecture-2026-03-24.md`
**Implementation plan at:** `~/otto/docs/emrs-implementation-plan-2026-03-24.md`

**Codebase state (verified 2026-03-24):** reflection.md is 1249 lines. Step 7c at line 1093, Step 0 at line 98. Last migration is 074. autoevolve.py has /experiments+/generation+/insights but NO /versions endpoints. meta_memory.json does NOT exist yet.

**Why:** Root cause is execution order + no causal memory, not missing infrastructure. self_patch.py already exists. The fix is minimal: ~40 lines in reflection.md (Step 0.5) + 1 JSON file.
**How to apply:** Phase 1 is safe to implement autonomously. Phase 2+ should be presented to Mev as a coherent package given it touches live self-modification paths.

**Execution order for impl agent:**
1. Create ~/otto/meta_memory.json (bootstrap)
2. Insert Step 0.5 into reflection.md after line 110
3. Add meta_memory read to reflection Step 0
4. Add meta_memory write to reflection Step 8/handoff
5. Run migration 075
6. Add /versions endpoints to autoevolve.py
7. Add record_version() to self_patch.py
8. Add rollback check to reflection Step 6

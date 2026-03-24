---
name: project_hyperagents_synthesis
description: HyperAgents (arXiv:2603.19461) research pipeline full review (2026-03-24, WF Steps 2+3+adjacent validation). Final verdict: NEEDS_CHANGES. Critical license error (CC BY-NC-SA not CC BY). Implementation mapping corrected. Adjacent work mapped.
type: project
---

HyperAgents research pipeline — full review (2026-03-24):

**Step 2 validation: NEEDS_CHANGES (5.5/10).** Paper facts accurate; Otto mapping critically wrong on 3 counts (see below).

**Step 3 adjacent validation (this task): NEEDS_CHANGES.** One new critical found: license error.

**Why:** Synthesis correctly transcribed all quantitative paper results but critically missed three existing Otto implementations AND misidentified the license.

**How to apply:** When validating research syntheses about Otto self-improvement: (1) grep for autoevolve/rl2f/metrics before accepting "this doesn't exist" claims; (2) check actual GitHub repo license — paper header and GitHub repo can differ.

Critical misses from Step 1 synthesis:
1. autoevolve.py (routes/) implements exactly the DGM-H self-modification loop — already built.
2. RL2F is NOT "binary success/fail" — rich multi-dimensional system (teacher_feedback, root_condition_analysis, mental_factor_scores, outcome_match).
3. metrics.py already has GET /metrics/trends.

New critical from Step 3 (adjacent validation):
4. LICENSE IS CC BY-NC-SA 4.0 — NOT CC BY 4.0. Synthesis stated "fully permissive for implementation and derivatives." FALSE. CC BY-NC-SA prohibits commercial use and requires share-alike on derivatives. GitHub repo confirmed: facebookresearch/HyperAgents badges show CC BY-NC-SA 4.0.

Adjacent work found:
- DGM predecessor: arXiv:2505.22954 (Sakana AI, May 2025) — SWE-bench 20%→50%, Polyglot 14.2%→30.7%. DGM-H directly extends this.
- Gödel Agent: ACL 2025 — theoretical self-referential framework; HyperAgents is empirical instantiation.
- Self-evolving surveys: arXiv:2508.07407 + arXiv:2507.21046 — comprehensive taxonomies of the space.
- ICML 2025 position paper on intrinsic metacognitive learning — directly supports HyperAgents thesis.

HyperAgents advances (not contradicts) prior work. Transfer result (0.630 IMO math) is genuine — explanation for "all others = 0.0": imp@50 measures improvement-over-initial, not raw accuracy. Baselines improve 0% on unseen domain, DGM-H improves 63%.

What remains genuinely valid:
- Paper quantitative results accurately transcribed
- S-MMU substrate mapping legitimate
- Action 3 (meta_memory.json) is genuinely novel recommendation
- Cross-domain transfer architecture claim is plausible and well-ablated

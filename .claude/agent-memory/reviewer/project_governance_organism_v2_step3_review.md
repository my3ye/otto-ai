---
name: Governance Organism v2 Step 3 consistency review
description: Step 3 consistency check of 505 Systems Governance Organism Pink Paper (commit 802a561, all prior fixes applied). MINOR_CHANGES 8.5/10. 2 new criticals found: Dc tier boundary discontinuities; Ec_digital default asymmetry. 4 warnings. All 10 prior criticals/warnings verified fixed.
type: project
---

## Review: 505 Systems Governance Organism Pink Paper — Step 3 Consistency Check
**File:** `/mnt/media/projects/505-systems-web/content/sos-systems-governance-organism-pink-paper.mdx`
**Commit:** 802a561 (after Step 3 coder applied all 10 fixes from Step 2 review)
**Date:** 2026-04-12
**Verdict:** MINOR_CHANGES — 8.5/10

**Why:** All 10 prior fixes verified present. Two new critical formula bugs found that were not in scope of prior passes. Both fixable at formula level with no prose rewrite.

---

## Prior Fixes — All 10 Confirmed Present
1. κ math language corrected (less than a quarter) ✓
2. Lathe labeled "tools class, 5yr depreciation schedule" ✓
3. Force majeure clause in Ec_physical ✓
4. max_beneficiaries defined in Dv_physical ✓
5. Compound Finance 2023 attribution restored (Proposal 289, $24M) ✓
6. Phase 0 counting mechanism parenthetical restored (Snapshot + attestation logs) ✓
7. MAPA Sybil-resistance sentence added ✓
8. Ec_digital reference to Technical Specification added ✓
9. "structurally impossible via contract enforcement" language ✓
10. "single attested labor hour establishes P_gov > 0" minimum threshold ✓

---

## Critical Issues (must fix)

**1. Dc formula has perverse discontinuities at tier boundaries**
`Section IV, Resource Contributions, Dc formula`

Computing Dc at tier boundaries reveals a formula bug that creates incentives to commit *shorter* rather than *longer*:

- 90-day temporary loan: `0.3 × (90/90) = 0.30`
- 91-day medium-term: `0.5 × (91/365) = 0.125`  ← *cliff drop at 91 days*
- 365-day medium-term: `0.5 × (365/365) = 0.50`
- 1-year long-term: `0.7 × (1/5) = 0.14`  ← *cliff drop at 1 year*

A resource contributor committing for 91 days earns Dc=0.125 — less than 42% of the Dc earned by committing for 90 days. A 1-year commitment earns Dc=0.14 — less than 28% of a 365-day medium-term commitment. Any contributor doing the arithmetic will commit exactly 90 days rather than 91+, and will keep rolling medium-term rather than committing long-term. This is the opposite of the intended incentive structure.

**Root cause:** Each tier uses a fraction with the tier's full duration in the denominator. This means the minimum of a higher tier always scores less than the maximum of the lower tier.

**Fix:** The tier boundaries need to produce monotonically increasing Dc values. Options:
- Option A: Use absolute formulas that produce continuous output at boundaries (e.g., remap 91-365 days so 91d→0.31 and 365d→0.5)
- Option B: Change the long-term formula from `0.7 × (years/5)` to `0.5 + (0.2 × (years-1)/4)` so 1 year=0.5, 5 years=0.7
- Option C: Make all tiers share a common normalization denominator

**2. Ec_digital default for non-digital contributors is unspecified**
`Section IV, Digital Contributions, penultimate paragraph`

The document states: "Digital contributors who have made no physical or resource commitments default to Ec_physical = 1.0 and Ec_resource = 1.0 — no penalty for dimensions they have not entered."

The reverse case is not documented: what is Ec_digital for a physical/resource-only contributor who has never committed digital work? Because Ec_total is multiplicative (`Ec_digital × Ec_physical × Ec_resource`), an undefined or zero Ec_digital would nullify the governance weight of every physical worker who has never committed code — precisely the humanitarian deployment population described in Section X.

**Fix:** Add one sentence: "The same default applies symmetrically: contributors who have made no digital commitments default to Ec_digital = 1.0."

---

## Warnings (should fix)

**3. activityMultiplier in GovernanceWeight formula is undefined**
`Section V, Dual-Track Scoring Model`

```
GovernanceWeight = sqrt(P_gov) × activityMultiplier
```

activityMultiplier appears once and is never defined — no formula, no range, no description of what triggers it or how it's computed. Every other variable in the document has explicit definition. A reader cannot verify this formula or implement it. Either define it or remove it until it's specified.

**4. max_expansion undefined in Dv_resource**
`Section IV, Resource Contributions, Dv_resource formula`

```
Dv_resource = Σ(access_expansion × shared_use) / max_expansion
```

max_beneficiaries was correctly defined for Dv_physical in Step 3. The analogous Dv_resource denominator (max_expansion) was not. This is the same gap, one formula lower. Fix: add the same treatment — "max_expansion = total population of the project's registered service area, as declared in the ProjectRegistry at contribution time."

**5. Qp defined as discrete, used as continuous in example**
`Section IV, Physical Labor, Qp definition and Is_physical example`

Qp table shows three discrete values: 0.5 (rework), 1.0 (meets standard), 1.5 (exceptional). The Is_physical worked example uses Qp=1.2, labeled "good quality." 1.2 is not in the table. A spec document must be unambiguous: is Qp discrete (pick from three values) or continuous (0.5–1.5)? Fix: either add "Qp is continuous between these anchor points, assessed by attestation" to the definition, or change the example to Qp=1.0.

**6. No force majeure for resource contributions**
`Section IV, Resource Contributions`

Physical labor gained a force majeure clause (Step 3 fix): suspended commitments without penalty for incapacitation or displacement. Resources have no equivalent. If a contributor's equipment is destroyed in a flood (precisely the humanitarian context described in Section X), Ec_resource goes to 0 immediately — which cascades to Ec_total=0 and P_gov=0, stripping all governance weight including digital contribution history. The design intent from the physical labor section ("Contribution creates gravity. Absence creates drift") should not apply to force majeure resource loss. Fix: add a parallel sentence to the resource section.

---

## What's Good

- **Dc arithmetic is correct within each tier** — the discontinuity is at boundaries, not within tiers
- **Is_physical example math verified correct**: 40 × 2.0 × 1.2 × 1.2 = 115.2 → 0.72 ✓
- **Is_resource lathe example verified correct**: 50000 × 0.8 × 1.0 × 0.4 × 1.0 = 16,000 → Is_resource=1.6 ✓ (tools/5yr, 3yr old, Dp=0.6, 1-Dp=0.4)
- **Tense discipline throughout** — "designed to," "planned for deployment," "is planned" — no legacy present-tense on undeployed contracts. Exceptional consistency.
- **Constitutional capital exclusion is airtight** — the immutable block format, the "Anti-capture, not anti-investor" framing, and the constitutional cannot-modify language are all exactly right
- **Ec multiplicative anti-gaming property is well-explained** — the physics metaphor ("gravity/drift") carries the design intent clearly
- **MAPA Sybil-resistance paragraph** — clean, specific, closes the peer-attestation gaming vector precisely
- **Dual disclaimer structure** — opening spec disclaimer + closing section footer both frame planned architecture without undermining the spec's authority
- **No legacy digital-only assumptions remaining** — Dv_total, Is_total, and Ec_total all explicitly sum/multiply across dimensions; physical workers throughout examples; humanitarian identity section well-integrated

**Why:** All 10 prior fixes were properly verified present. This is now 8.5/10 — up from 8.0/10. The two remaining criticals are formula-level fixes (Dc tier continuity, Ec_digital default sentence) requiring minimal edits. The four warnings are all one-sentence or one-formula fixes.

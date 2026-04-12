---
name: project_governance_organism_v2_review
description: "505 Systems: Governance Organism" v2 (2026-04-12, WF Step 1): MINOR_CHANGES 8.0/10. Adds Physical/Resource/Capital sections. 3 criticals: κ math (23%/33%) unsubstantiated; lathe depreciation 5yr/10yr inconsistency; Ec_physical=0 force majeure gap. 2 prior-fix regressions.
type: project
---

Pink Paper v2: "505 Systems: The Governance Organism" (expanded)
File: /mnt/media/projects/505-systems-web/content/sos-systems-governance-organism-pink-paper.mdx
Content DB ID: 99380ece (updated via PATCH)
Reviewed: 2026-04-12, WF Step 1 (v2 — adds Physical Labor, Resource, Capital sections)
Verdict: MINOR_CHANGES — 8.0/10

## Prior Critical Status
All 3 v1 criticals are FIXED in v2:
- Ec formula undefined inputs ✓ (Ec_physical and Ec_resource now have explicit formulas)
- zkEVM+ML-DSA overclaim ✓ (Phase 2 now says "post-quantum signature support" — no specific algorithm overclaim)
- Pink Paper No. 2 context missing ✓ (cross-reference removed entirely)

## REGRESSION from fd626c0 fixes (must not be lost):
1. **Compound attribution**: fd626c0 fixed to "Compound Finance governance concentration (2023)". v2 reverted to "The Compound governance attack" — year and entity lost. Minor journalist accuracy concern.
2. **Phase 0 counting mechanism**: fd626c0 added "(tracked manually through Snapshot participation and peer attestation logs during Phase 0)". That parenthetical is absent in v2. Closes gap between off-chain mechanics and undeployed ContributionRegistry.

## Critical Issues (must fix before publish):

1. **κ = 0.3 → "23% max capital share" math unsubstantiated** (Section V, dual-track formula)
   "With κ = 0.3, the maximum capital share of any single distribution is 23%" is not derivable from κ alone. The capital share = Σ(C_econ × κ) / Σ(P_gov + C_econ × κ), which depends on the ratio of total C_econ to total P_gov across all contributors. The 23% figure requires explicit assumptions about the distribution of labor vs capital scores in the pool. Same issue with "ceiling is 33%" at κ=0.5. Either derive the figure (include the assumed ratio) or replace with: "Capital's share of any distribution is bounded by the κ coefficient and the per-address 10% cap. At κ=0.3 with balanced participation, capital captures less than a quarter of any distribution."

2. **Lathe depreciation example inconsistency** (Section IV, resource contributions, formula block)
   "$50K lathe, 3 years old (5yr depreciation schedule)" — but the depreciation table above it says "Heavy equipment: linear over 10 years." A $50K lathe is heavy equipment, not a "tool" (≤$5K class). The example uses a 5-year schedule but the spec says 10 years. At 3 years, 10-year linear = Dp=0.3, so (1-Dp)=0.7. The example computation gives 50000×0.8×1.0×0.4×1.0=16,000 — this uses Dp=0.6 implying a 5yr schedule (3/5=0.6). Fix: either label the lathe as a "tool" (but price is inconsistent) or update "(5yr depreciation schedule)" to "(10yr depreciation schedule)" and update Dp from 0.4 to 0.7 and recompute: 50000×0.8×1.0×0.7×1.0=28,000 → Is_resource=2.8.

3. **Ec_physical zeroing creates humanitarian contradiction** (Section IV, Physical Labor, Ec_physical formula)
   Ec_physical = 0.0 when attendance < 0.7 threshold (last 30 days). Combined with multiplicative Ec_total = Ec_digital × Ec_physical × Ec_resource, a contributor who registers physical commitments and is then detained, injured, displaced, or loses connectivity has their ENTIRE governance weight zeroed — including their digital contribution history. Section X explicitly claims the system is designed for "zones of crisis, displacement, disconnection." No grace period, suspension mechanism, or force majeure clause exists. A skeptic will correctly identify this as a design contradiction: the system that claims to include displaced workers is the one mechanism that zeroes governance rights when workers become displaced. Minimum fix: add one sentence — "A contributor may suspend physical commitments without penalty for documented incapacitation or displacement events; governance suspensions are governed by Community Layer proposal."

## Warnings (should fix):

1. **max_beneficiaries undefined** (Section IV, Dv_physical formula)
   `Dv_physical = Σ(B × accessibility_delta) / max_beneficiaries` — max_beneficiaries is never defined. Is it the project's total participant count? The surrounding community population? The infrastructure registry service area? Add: "max_beneficiaries = the total addressable population of the project's service area, set during Phase 0 and updated by oracle annually."

2. **Compound attribution regression** (Section III)
   Reverted from "Compound Finance governance concentration (2023)" to "The Compound governance attack." Restore year and entity name to prevent journalist misattribution.

3. **Phase 0 counting mechanism regression** (Section VIII, Phase 0)
   The parenthetical "(tracked manually through Snapshot participation and peer attestation logs during Phase 0)" was added in fd626c0 and appears absent in v2. Restore it: "the DPC scoring formula has been validated through real use (tracked via Snapshot participation and peer attestation logs) and ratified by the community."

4. **MAPA Sybil-resistance unspecified** (Section IV, Physical Labor, attestation)
   Multi-Party Attestation Protocol is named but anti-Sybil mechanism is not defined. For humanitarian contexts, peer attestation is the primary gaming vector — crews can attest each other without independent verification. Add one sentence: "MAPA requires attesters who are themselves verified contributors with active DPC scores, preventing unverified participants from collectively bootstrapping fraudulent attestation chains."

## Suggestions:
- **Ec_digital formula gap**: Ec_digital is described qualitatively ("contribution streak and frequency") while Ec_physical and Ec_resource now have explicit formulas. Add reference: "Ec_digital computation is specified in the technical specification ratified during Phase 0."
- **"structurally impossible" pre-deployment** (Section V): "written into the architecture to make that outcome structurally impossible" — stronger as "designed to make that outcome structurally impossible via contract enforcement" (the contracts don't exist yet, so "structurally impossible" is a future claim).
- **P_gov > 0 minimum labor**: clarify what minimum verified contribution satisfies P_gov > 0 to unlock capital economic rewards. Even one contribution? One verified commit? One attested labor hour?

## What's Exceptional:
- Physical/capital framing — anti-capture (not anti-investor) is exactly the right framing, credible to crypto-native readers
- Construction worker ≈ developer scoring parity example — proves the design intent in one concrete sentence
- Resource depreciation by asset class — signals genuine thought; land Dp=0 while tools depreciate over 5yr is appropriately specific
- κ hard caps with labor floor guarantee — "constitutional guarantee" language is strong and the specific numbers (67% floor, 10% per-address cap) give skeptics something verifiable to trust
- Multiplicative Ec_total — the anti-gaming property explanation is clean and convincing
- Tense discipline on all new sections — "planned for deployment," "designed to be constitutionally prohibited," "will track" throughout. Best new-section tense discipline in the entire SOS library.
- Token deferral carried through — "The governing body formed in Phase 0 earns the right to set those parameters" is unchanged. Best trust signal in any spec doc.

## Do Not Touch:
- Section III governance failure analysis
- Anti-capture framing in Section V
- Physical labor parity example (construction worker = developer)
- Token deferral paragraph (Section IX)
- "This is not punishment. This is physics." (Ec decay section)
- Closing "We are not asking you to follow. We are asking you to build."
- Dual disclaimer (frontmatter + footer)

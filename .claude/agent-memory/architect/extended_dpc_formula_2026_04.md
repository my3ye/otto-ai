---
name: extended_dpc_formula_2026_04
description: Extended DPC formula for non-digital contributions — physical labor, capital, resources. Dual-track P_gov/P_econ, 8 contribution types, CapitalRegistry contract.
type: project
---

Extended DPC formula architecture complete (2026-04-12). Full doc at ~/otto/docs/extended-dpc-formula-architecture-2026-04-12.md.

**Why:** DPC formula (P = Ec^α × Is^β × max(Dv, ε)^γ) handles digital contributions but lacks formal input functions for physical labor, capital deployment, and resource contributions (land, equipment, facilities). Task to extend the formula while maintaining backward compatibility and constitutional capital exclusion.

**Key decisions:**
- Core formula UNCHANGED — extended the input functions (how Is/Ec/Dv are computed), not the formula itself
- Dual-track: P_gov (governance weight, excludes capital) + P_econ (reward distribution, includes capital via κ coefficient)
- 8 contribution types in uint8 bitmap (added RES on bit 7). CAP tracked in separate CapitalRegistry contract (not in DPC bitmap).
- Ec is MULTIPLICATIVE across dimensions (Ec_digital × Ec_physical × Ec_resource) — broken commitment in any dimension drags down total Ec
- Is and Dv are ADDITIVE across dimensions — impact and accessibility accumulate
- Exponents: α=0.4 (Ec), β=0.35 (Is), γ=0.25 (Dv). Sum to 1.0. Ec highest because sustained contribution is hardest to fake ("Proof of Grit").
- Capital: C_econ = Cd × min(Ct/180)^0.5 × Cf. 180-day tenure cap, sqrt front-loading, function-type multipliers (1.0 operational → 0.1 passive)
- κ (capital reward weight) = 0.3, constitutional max = 0.5. Labor always earns ≥67%.
- Minimum labor requirement: P_gov > 0 to receive any capital rewards. Prevents anonymous capital extraction.
- Phase 1 requires NO contract changes (oracle computes richer scores off-chain). Phase 2 adds CapitalRegistry. Phase 3 adds verification infrastructure.

**How to apply:** When implementing DPC scoring for any vertical, use the extended input functions. Contribution type weights table in Section 1.2. Worked examples in Section 9. All parameters DAO-adjustable within constitutional bounds.

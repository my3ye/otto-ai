# Extended DPC Formula for Non-Digital Contributions
## Sovereign Contribution Scoring Across Physical, Capital, and Resource Dimensions

*Authored by Otto (Architect Agent) | 2026-04-12 | Status: Architecture Complete*
*Prerequisite: Pink Paper v4 (Dv formula), OPRLP contracts, Labor Attestation framework, Core Value Loop*

---

## Design: Extended DPC Formula

### Problem

The current DPC formula `P = Ec^α × Is^β × max(Dv, ε)^γ` was designed for digital-native contributions — code commits, content creation, operational coordination. The 7 contribution types (PHY/MAT/SKL/OPS/EDU/COM/DIG) already sketch the space for physical labor, but:

1. **Physical labor lacks formal input functions.** PHY maps Is=0.7/Ec=0.2/Dv=0.1, but there's no defined method for computing Is from labor hours, skill tiers, or risk premiums. The formula exists but the measurement layer doesn't.

2. **Capital deployment has no scoring model.** Constitutional rule: capital = 0 governance weight (immutable). But capital still needs an economic score for reward distribution. Without a formal model, capital holders either get nothing (unfair) or must be handled ad hoc (ungovernable).

3. **Resource contributions (land, equipment, materials) lack depreciation, utilization, and temporal commitment modeling.** A carpenter who donates a $50K lathe for permanent community use and one who lends it for a weekend both get the same MAT classification.

The formula must extend to handle all three without breaking backward compatibility or violating the constitutional capital exclusion.

### Approach

**Do not change the core formula.** `P = Ec^α × Is^β × max(Dv, ε)^γ` remains canonical. What changes is how Is, Ec, and Dv are *computed* — specifically, the input functions that aggregate contributions across digital, physical, and resource dimensions.

**Dual-track scoring:**
- **Track 1: Governance DPC (P_gov)** — determines voting weight. Excludes capital. Fed into GovernanceWeight.sol.
- **Track 2: Economic DPC (P_econ)** — determines reward distribution. Includes capital. Fed into SplitEngine.sol.

---

## 1. Extended Contribution Taxonomy

### 1.1 Updated Type Registry (8 types)

The existing 7 types are preserved. One new type is added. Capital is tracked separately (not in the DPC bitmap).

| Bit | Code | Category | Description | Status |
|-----|------|----------|-------------|--------|
| 0 | `PHY` | Physical Labor | Construction, assembly, manual work | Existing |
| 1 | `MAT` | Materials | Consumable materials contributed | Existing (refined) |
| 2 | `SKL` | Skilled Trade | Professional expertise applied | Existing |
| 3 | `OPS` | Operations | Coordination, logistics, management | Existing |
| 4 | `EDU` | Education | Teaching, mentoring, training | Existing |
| 5 | `COM` | Community | Dispute resolution, onboarding, care | Existing |
| 6 | `DIG` | Digital | Code, design, content, documentation | Existing |
| 7 | `RES` | Resources | Land, equipment, tools, facilities | **NEW** |
| — | `CAP` | Capital | Financial deployment | **NEW** (separate contract) |

**Why 8 types + separate capital:**
- `uint8` bitmap in DPCRegistry supports exactly 8 bits. All 8 now used.
- CAP is constitutionally excluded from governance DPC, so it doesn't belong in the DPC bitmap.
- RES covers land, equipment, and facilities — subcategorized off-chain but scored on-chain as one type.
- MAT refined to mean *consumable* materials (lumber, concrete, hardware). Durable contributions (lathe, tractor, land) are RES.

### 1.2 Updated DPC Component Weights

Weights updated from Rw→Dv (semantic relabel per April 12 governance change). New RES type added.

```
CONTRIBUTION → DPC COMPONENT MAPPING (v2):

  PHY (Physical Labor):     Is=0.7,  Ec=0.2,  Dv=0.1
  MAT (Materials):           Is=0.8,  Ec=0.1,  Dv=0.1
  SKL (Skilled Trade):       Is=0.5,  Ec=0.2,  Dv=0.3
  OPS (Operations):          Is=0.2,  Ec=0.6,  Dv=0.2
  EDU (Education):           Is=0.3,  Ec=0.3,  Dv=0.4
  COM (Community):           Is=0.1,  Ec=0.3,  Dv=0.6
  DIG (Digital):             Is=0.6,  Ec=0.2,  Dv=0.2
  RES (Resources):           Is=0.6,  Ec=0.2,  Dv=0.2    ← NEW
```

All weights sum to 1.0 per type. DAO-adjustable via governance proposal.

---

## 2. Component Input Functions

The core formula remains:

```
P_gov = Ec_total^α × Is_total^β × max(Dv_total, ε)^γ

Where:
  α = 0.4  (Consistent Energy exponent)
  β = 0.35 (Structural Impact exponent)
  γ = 0.25 (Direction of Value exponent)
  ε = 0.01 (minimum Dv floor to prevent zero-score)
```

Each component aggregates across contribution dimensions:

```
Is_total = Is_digital + Is_physical + Is_resource
Ec_total = Ec_digital × Ec_physical × Ec_resource   ← multiplicative (consistency compounds)
Dv_total = Dv_digital + Dv_physical + Dv_resource
```

**Note:** Ec is multiplicative because consistency must span ALL dimensions. A contributor who codes every day but abandons their physical commitments should not retain full Ec. Is and Dv are additive because structural impact and accessibility expansion accumulate.

### 2.1 Digital Contributions (existing behavior)

Digital contributions are the baseline. Their scoring is already implemented:

```
Is_digital = Σ(artifact_weight_i × complexity_i × adoption_i)
  - artifact_weight: git commits (1.0), PR reviews (0.5), documentation (0.8), 
    design (0.7), deployment (1.2)
  - complexity: lines changed / expected (capped at 3.0)
  - adoption: usage_count / time_since_merge (normalized)

Ec_digital = streak_weeks^0.5 × commit_frequency_30d / expected_frequency
  - streak_weeks: consecutive weeks with ≥1 verified contribution
  - Square root prevents long streaks from dominating

Dv_digital = Σ(user_count_delta_i × access_breadth_i)
  - user_count_delta: how many new users gained access
  - access_breadth: geographic/demographic diversity of new access
```

### 2.2 Physical Labor Contributions

Physical labor introduces three new measurement variables per contribution:

```
PHYSICAL LABOR INPUT VARIABLES:

  Lh  = Verified labor hours (attested via MPAP)
  St  = Skill tier multiplier:
         1.0  Unskilled (general labor, cleaning, carrying)
         1.5  Journeyman (basic trade skills, supervised)
         2.0  Master (independent trade execution)
         2.5  Specialist (licensed/certified, critical systems)
  Qp  = Quality score (0.5–1.5):
         Assessed by peer attestation + site oracle
         0.5 = needs rework, 1.0 = meets standard, 1.5 = exceptional
  Rk  = Risk premium multiplier:
         1.0  Standard (office, indoor, low hazard)
         1.2  Moderate (outdoor, weather exposure, elevation <3m)
         1.5  High (heavy machinery, confined spaces, heights >3m)
         2.0  Hazardous (demolition, chemical exposure, electrical)
```

**Component computation:**

```
Is_physical = Σ(Lh_i × St_i × Qp_i × Rk_i) / normalization_constant
  - normalization_constant = 160 (one full-time month of unskilled labor = 1.0 Is)
  - Example: 40 hours × master (2.0) × good quality (1.2) × moderate risk (1.2) = 115.2
    → Is_physical = 115.2 / 160 = 0.72

Ec_physical = streak(W) × attendance(A)
  - streak(W) = min(W / 52, 1.0)^0.5
    W = consecutive weeks with ≥1 attested physical contribution
  - attendance(A) = attested_days / committed_days (last 30 days)
    Must be ≥ 0.7 to count. Below 0.7 → Ec_physical = 0.
  - Default: 1.0 when no physical commitment exists (no penalty for digital-only)

Dv_physical = Σ(B_i × accessibility_delta_i) / max_beneficiaries
  - B_i = number of beings whose prosperity is expanded by contribution i
  - accessibility_delta_i = binary or graduated measure:
    0.0 = no access change
    0.5 = partial improvement (e.g., road repair improves transit)
    1.0 = new access created (e.g., bridge connects isolated community)
  - max_beneficiaries = normalizing constant, set per project type
  - Machine-verifiable via: before/after satellite imagery, census data,
    infrastructure registry, service availability maps
```

### 2.3 Resource Contributions (Land, Equipment, Facilities)

Resource contributions differ from materials (MAT) because they are durable, temporal, and depreciating.

```
RESOURCE CONTRIBUTION INPUT VARIABLES:

  FMV = Fair market value at contribution time (base unit, e.g., USD)
  U   = Utilization rate (0.0–1.0):
         Measured by oracle (access logs, IoT sensors, peer attestation)
         0.0 = contributed but never used
         0.5 = used half the available time
         1.0 = fully utilized
  Dc  = Duration commitment factor:
         Temporary loan (≤90 days):   0.3 × (days_available / 90)
         Medium-term (91–365 days):   0.5 × (days_available / 365)
         Long-term (1–5 years):       0.7 × (years_committed / 5)
         Permanent donation:          1.0
  Dp  = Depreciation factor (0.0–1.0):
         Land/space:     0.0 (no depreciation — land doesn't wear out)
         Buildings:      linear over 30 years (age / 30)
         Heavy equipment: linear over 10 years (age / 10)
         Tools:          linear over 5 years (age / 5)
         Vehicles:       linear over 7 years (age / 7)
  Mn  = Maintenance factor:
         1.0 = properly maintained (contributor handles upkeep)
         0.7 = shared maintenance (community handles upkeep)
         0.5 = degraded condition (needs repair)
```

**Component computation:**

```
Is_resource = Σ(FMV_j × U_j × Dc_j × (1 - Dp_j) × Mn_j) / normalization_constant
  - normalization_constant = 10000 (contributing a $10K fully-utilized permanent
    resource in good condition = 1.0 Is)
  - Example: $50K lathe, 80% utilized, permanent donation, 3 years old (5yr depreciation),
    well-maintained = 50000 × 0.8 × 1.0 × 0.4 × 1.0 = 16000 → 16000/10000 = 1.6 Is
  - Rescored monthly as utilization and depreciation change

Ec_resource = Π(availability_j × Mn_j) for all active resource commitments
  - availability_j = fraction of committed time the resource was actually available
  - Multiplicative: one unavailable resource drags down the whole factor
  - Default: 1.0 when no resource commitments exist

Dv_resource = Σ(access_expansion_j × shared_use_j) / max_expansion
  - access_expansion_j = number of people who gained capability access
    because of this resource
  - shared_use_j = number of distinct contributors who used the resource / total members
    (rewards resources that serve many, not one)
  - Example: community workshop (access_expansion=50, shared_use=0.3)
    → Dv_resource = (50 × 0.3) / max_expansion
```

---

## 3. Capital Scoring (Governance-Excluded Track)

### 3.1 Constitutional Constraint

```
IMMUTABLE RULE (from CONSTITUTION.md):
  capital_governance_weight = 0.00
  
  Capital deployed NEVER contributes to P_gov.
  Capital deployed NEVER enters Is_total, Ec_total, or Dv_total.
  Capital deployed NEVER influences GovernanceWeight.sol.
  
  This rule is constitutional — cannot be changed by DAO vote,
  governance proposal, or admin action. Only Admin (Mev) can
  modify constitutional rules.
```

### 3.2 Capital Economic Score

Capital earns an economic score (C_econ) used exclusively for reward distribution.

```
CAPITAL INPUT VARIABLES:

  Cd = Capital deployed (normalized to base unit)
  Ct = Capital tenure — days the capital has been at risk
  Cf = Capital function multiplier:
        Operational (working capital for active projects):    1.0
        Infrastructure (building purchase, equipment buy):    0.8
        Liquidity (LP provision, market making):              0.5
        Bridge (short-term loan, credit facility):            0.3
        Passive (treasury deposit, no productive use):        0.1
```

**Formula:**

```
C_econ = Cd × min(Ct / 180, 1.0)^0.5 × Cf

Where:
  - Cd normalized to base unit (e.g., 1 USDC = 1.0)
  - Tenure caps at 180 days (no additional credit for longer deployment;
    prevents "park and forget" capital from accumulating indefinitely)
  - Square root on tenure: front-loaded — capital is most valuable early
    when projects need runway. Year-old capital isn't 2x more valuable
    than 6-month capital.
  - Cf multiplier rewards capital that actively supports production
    over passive parking
```

### 3.3 Capital Hard Caps

```
CAPITAL REWARD CAPS (constitutional):

  1. κ (kappa) = capital reward weight coefficient
     Range: 0.0–0.5 (DAO-adjustable within range)
     Starting value: 0.3
     Constitutional maximum: 0.5
     
  2. Per-address cap: No single address can claim more than 10%
     of total capital rewards in any distribution cycle
     
  3. Minimum labor requirement: To receive ANY capital reward,
     an address must have P_gov > 0 (must have contributed labor).
     Pure capital with zero labor contribution earns nothing.
     This prevents anonymous capital from extracting value.
```

---

## 4. Unified Economic Distribution

### 4.1 Dual-Track Aggregation

```
GOVERNANCE WEIGHT (Track 1 — existing formula):
  P_gov = Ec_total^α × Is_total^β × max(Dv_total, ε)^γ
  
  GovernanceWeight = sqrt(P_gov) × activityMultiplier
  
  Capital contribution: ZERO. Always.


ECONOMIC REWARD SHARE (Track 2 — extended formula):
  P_econ_i = P_gov_i + (C_econ_i × κ)
  
  contributor_reward_i = P_econ_i / Σ(P_econ_j) × reward_pool
  
  Where:
  - P_gov_i = governance DPC score for contributor i
  - C_econ_i = capital economic score for contributor i (0 if no capital)
  - κ = capital reward weight (starting at 0.3, max 0.5)
  - reward_pool = 92% of revenue (per Core Value Loop: 92% contributors / 5% protocol / 3% governance)
```

### 4.2 Maximum Capital Share Analysis

```
With κ = 0.3:
  If a contributor has P_gov = 100 and C_econ = 1000:
  P_econ = 100 + (1000 × 0.3) = 400
  
  Maximum possible capital share of ANY distribution:
  κ / (1 + κ) = 0.3 / 1.3 = 23%
  
  With constitutional max κ = 0.5:
  0.5 / 1.5 = 33%
  
  GUARANTEE: Labor always earns at least 67% of any revenue split.
  This is constitutional.
```

---

## 5. Verification Methods by Contribution Type

### 5.1 Physical Labor (PHY) — MPAP Required

Uses the existing Multi-Party Attestation Protocol from the Labor Attestation framework:
- 2-of-3 quorum: self-report + 2 peer validators OR site oracle
- 48h blind attestation window (anti-collusion)
- GPS/photo evidence hashed to IPFS
- Skill tier set by credential VC or community election
- Risk premium set per project site, not per contribution

### 5.2 Resources (RES) — Oracle + Registry

```
RESOURCE VERIFICATION PROTOCOL:

  1. REGISTRATION
     Contributor registers resource with:
     - Type (land/equipment/facility/vehicle)
     - Fair market value (third-party appraisal or receipt)
     - Commitment type (loan/lease/donation)
     - Duration
     - Location (GPS coordinates)
     
  2. VERIFICATION
     Two independent validators confirm:
     - Resource exists and matches description
     - Contributor has authority to commit it
     - Condition assessment
     - One-time verification (not recurring)
     
  3. ONGOING MONITORING
     Monthly oracle check:
     - Utilization measurement (access logs, IoT, peer report)
     - Condition assessment (maintenance factor update)
     - Availability confirmation
     
  4. DEPRECIATION
     Automatic, based on type:
     - Linear schedule per asset class (see Section 2.3)
     - Overridden by condition assessment if degraded faster
     - Land/space: no depreciation
```

### 5.3 Capital (CAP) — On-Chain Verifiable

```
CAPITAL VERIFICATION PROTOCOL:

  1. DEPLOYMENT
     Capital must be deployed to a registered project address
     or treasury contract. On-chain transaction is the attestation.
     No peer attestation needed — the chain IS the oracle.
     
  2. TENURE
     Measured by: block.timestamp at deposit → block.timestamp at
     withdrawal (or current time if still deployed).
     No human attestation needed — contract tracks automatically.
     
  3. FUNCTION CLASSIFICATION
     Set by the receiving contract's registry entry:
     - Project working capital contracts → Operational (1.0)
     - Asset purchase contracts → Infrastructure (0.8)
     - LP positions → Liquidity (0.5)
     - Bridge/loan contracts → Bridge (0.3)
     - Treasury → Passive (0.1)
     
  4. MINIMUM DEPLOYMENT
     Capital must be deployed for ≥7 days to earn any C_econ.
     Flash loans and short-term parking earn nothing.
```

---

## 6. On-Chain Architecture Changes

### 6.1 DPCRegistry (Minimal Change)

```
EXISTING (unchanged):
  struct DPCScore {
      uint128 rawScore;       // P_gov (governance DPC)
      uint128 peakScore;      // All-time high P_gov
      uint64 lastUpdateTime;
      uint64 lastActiveTime;
      uint8 contributionTypes; // bitmap, now uses all 8 bits
      bool isActive;
  }

CHANGE: contributionTypes bit 7 now assigned to RES.
  Bit 0: PHY, Bit 1: MAT, Bit 2: SKL, Bit 3: OPS,
  Bit 4: EDU, Bit 5: COM, Bit 6: DIG, Bit 7: RES

No struct changes. No function changes. Backward compatible.
The VALIDATOR_ROLE oracle simply includes RES contributions
when computing the P_gov score submitted via updateScore().
```

### 6.2 New Contract: CapitalRegistry

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title CapitalRegistry — Economic score for capital deployment
/// @notice Tracks capital contributions for reward distribution only.
///         NEVER read by GovernanceWeight (constitutional constraint).
contract CapitalRegistry {
    struct CapitalScore {
        uint128 economicScore;   // C_econ
        uint128 totalDeployed;   // Cumulative Cd
        uint64 firstDeployTime;
        uint64 lastDeployTime;
        uint8 functionType;      // Cf classification
        bool hasLabor;           // Must be true to receive rewards
    }
    
    mapping(address => CapitalScore) private _scores;
    
    function updateScore(
        address identity,
        uint128 newScore,
        uint128 deployed,
        uint8 funcType
    ) external onlyRole(VALIDATOR_ROLE);
    
    function getEconomicScore(address identity) 
        external view returns (uint128);
    
    function getScoreDetails(address identity) 
        external view returns (CapitalScore memory);
}
```

### 6.3 SplitEngine Integration

```
EXISTING SplitEngine reads: DPCRegistry.getScore(identity)
EXTENDED SplitEngine reads: DPCRegistry.getScore(identity) 
                          + CapitalRegistry.getEconomicScore(identity) × κ

New function in SplitEngine:
  function getEconomicWeight(address identity) view returns (uint256) {
      uint128 govScore = dpcRegistry.getScore(identity);
      uint128 capScore = capitalRegistry.getEconomicScore(identity);
      return uint256(govScore) + (uint256(capScore) * kappa / SCALE);
  }
```

---

## 7. Backward Compatibility Guarantees

| Component | Change | Impact |
|-----------|--------|--------|
| Core formula | `P = Ec^α × Is^β × max(Dv, ε)^γ` | **No change** |
| DPCScore struct | No field changes | **No change** |
| contributionTypes bitmap | Bit 7 now assigned (was unused) | **Compatible** (popcount still works) |
| GovernanceWeight.sol | No changes needed | **No change** |
| Digital-only contributors | Is_physical=0, Is_resource=0, C_econ=0 | **Reduces to current behavior** |
| Existing PHY/MAT weights | Rw→Dv relabel, values unchanged | **Compatible** |
| DPCMath library | No changes needed | **No change** |
| Lazy decay | Applies to P_gov (includes physical+resource Is/Ec/Dv) | **Compatible** |
| Activity multiplier | Unchanged (30/60/90 day tiers) | **No change** |
| VALIDATOR_ROLE | Same role, richer off-chain computation | **Compatible** |

**New additions only:**
- CapitalRegistry contract (additive, not modifying existing)
- SplitEngine reads from one additional contract
- Off-chain oracle computes richer Is/Ec/Dv inputs

---

## 8. Exponent Rationale

### 8.1 Why α=0.4, β=0.35, γ=0.25

```
P_gov = Ec^0.4 × Is^0.35 × max(Dv, ε)^0.25

DESIGN INTENT:
  α + β + γ = 1.0 (unit-sum constraint for interpretability)
  
  α = 0.4 (Consistent Energy — highest weight)
    WHY: Sustained contribution over time is the hardest thing to fake
    and the most valuable to an organism. "Proof of Grit." A contributor
    who shows up every week for a year is more valuable than one who
    does a single brilliant sprint. This prevents drive-by contributions
    from dominating governance.
    
  β = 0.35 (Structural Impact — second highest)
    WHY: Output matters. But slightly less than consistency because
    impact is easier to game (submit 100 trivial PRs vs. 1 meaningful
    architecture change). The non-linear exponent compresses outliers.
    
  γ = 0.25 (Direction of Value — lowest weight)
    WHY: Dv is the newest component (replacing Rw on April 12, 2026).
    Start with lower weight while measurement methods mature. Unlike
    Is and Ec which have established verification, Dv's "accessibility
    delta" measurement is still early. The ε floor prevents Dv=0 from
    zeroing the entire score. Weight can increase via governance vote
    as measurement confidence grows.
```

### 8.2 Multiplicative vs. Additive

```
WHY P = Ec^α × Is^β × Dv^γ (multiplicative) NOT P = αEc + βIs + γDv (additive):

  Multiplicative means ALL THREE dimensions must be nonzero.
  - Zero consistency = zero score (can't coast on a single big impact)
  - Zero impact = zero score (can't earn by just showing up)
  - Zero value direction = near-zero score (ε prevents hard zero)
  
  This is the anti-gaming property: you cannot dominate by maxing one dimension.
  In the additive form, a contributor could ignore Dv entirely and still
  score 75% by maxing Is and Ec. Multiplicative makes that impossible.
```

---

## 9. Worked Examples

### 9.1 Construction Worker (Physical Labor Primary)

```
Alice: 6 months contributing, builds community center

Physical contributions (monthly average):
  Lh = 160 hours, St = 1.5 (journeyman), Qp = 1.2 (good), Rk = 1.2 (moderate)
  Is_physical = (160 × 1.5 × 1.2 × 1.2) / 160 = 2.16
  
  streak = 26 weeks, attendance = 0.95
  Ec_physical = min(26/52, 1.0)^0.5 × 0.95 = 0.707 × 0.95 = 0.672
  
  Built bridge connecting 200 people to market (accessibility_delta = 1.0)
  Dv_physical = (200 × 1.0) / 500 = 0.4

Digital contributions: none (Is_digital = 0, Dv_digital = 0)
  Ec_digital = 1.0 (default — no digital commitment to miss)

Resource contributions: none

Totals:
  Is_total = 0 + 2.16 + 0 = 2.16
  Ec_total = 1.0 × 0.672 × 1.0 = 0.672
  Dv_total = 0 + 0.4 + 0 = 0.4

P_gov = 0.672^0.4 × 2.16^0.35 × max(0.4, 0.01)^0.25
      = 0.848 × 1.285 × 0.795
      = 0.867

Governance weight = sqrt(0.867) × 1.0 (active) = 0.931
```

### 9.2 Software Developer (Digital Primary, Existing Behavior)

```
Bob: 1 year contributing, builds core infrastructure

Digital contributions:
  Is_digital = 1.8 (high-impact PRs, core architecture)
  Ec_digital = 0.9 (48-week streak, good frequency)
  Dv_digital = 0.5 (tools used by 30+ contributors)

Physical: none, Resource: none

Totals:
  Is_total = 1.8 + 0 + 0 = 1.8
  Ec_total = 0.9 × 1.0 × 1.0 = 0.9  (defaults for missing dimensions)
  Dv_total = 0.5 + 0 + 0 = 0.5

P_gov = 0.9^0.4 × 1.8^0.35 × max(0.5, 0.01)^0.25
      = 0.959 × 1.224 × 0.841
      = 0.987

Governance weight = sqrt(0.987) × 1.0 = 0.993

Note: Alice (physical-primary) and Bob (digital-primary) score
comparably. This is by design — the formula does not privilege
digital over physical labor.
```

### 9.3 Capital Deployer with Labor Requirement

```
Charlie: Deploys $50,000 USDC to project working capital for 120 days.
Also contributes 20 hours/month of OPS (coordination).

Capital:
  Cd = 50000, Ct = 120 days, Cf = 1.0 (operational)
  C_econ = 50000 × min(120/180, 1.0)^0.5 × 1.0
         = 50000 × 0.667^0.5 × 1.0
         = 50000 × 0.816
         = 40,825

Labor (OPS):
  P_gov = (computed via Ec/Is/Dv from OPS contributions)
  P_gov > 0 ← satisfies minimum labor requirement

Economic share:
  P_econ = P_gov + (40825 × 0.3) = P_gov + 12,247.5
  
  Charlie's capital contributes to reward distribution but
  ZERO governance weight. Charlie cannot vote with money.
```

### 9.4 Land Contributor

```
Diana: Donates 2-acre plot for community workshop. No depreciation (land).
Workshop serves 45 members (total community: 120).

Resource:
  FMV = $80,000 (appraised), U = 0.7 (utilized 70%), Dc = 1.0 (permanent),
  Dp = 0.0 (land), Mn = 1.0 (well-maintained)
  
  Is_resource = (80000 × 0.7 × 1.0 × 1.0 × 1.0) / 10000 = 5.6
  Ec_resource = 0.95 (available 95% of the time) × 1.0 (maintained) = 0.95
  Dv_resource = (45 × 0.375) / 100 = 0.169
    (shared_use = 45/120 = 0.375)

Combined with any other contributions Diana makes → P_gov.
```

---

## 10. Parameter Governance

### 10.1 DAO-Adjustable Parameters

| Parameter | Current | Range | Adjustment Method |
|-----------|---------|-------|-------------------|
| α (Ec exponent) | 0.4 | 0.2–0.6 | Governance proposal |
| β (Is exponent) | 0.35 | 0.2–0.5 | Governance proposal |
| γ (Dv exponent) | 0.25 | 0.1–0.4 | Governance proposal |
| κ (capital reward weight) | 0.3 | 0.0–0.5 | Governance proposal |
| ε (Dv floor) | 0.01 | 0.001–0.1 | Governance proposal |
| Contribution type weights | See Section 1.2 | Sum = 1.0 per type | Governance proposal |
| Normalization constants | See Section 2 | Project-specific | Project-level vote |
| Skill tier multipliers | See Section 2.2 | 1.0–3.0 | Governance proposal |
| Risk premium tiers | See Section 2.2 | 1.0–2.5 | Governance proposal |

### 10.2 Constitutional (Immutable) Parameters

| Parameter | Value | Why Immutable |
|-----------|-------|---------------|
| capital_governance_weight | 0.00 | Prevents plutocracy |
| κ maximum | 0.50 | Labor must always earn ≥67% of rewards |
| Minimum labor for capital rewards | P_gov > 0 | Prevents anonymous extraction |
| Per-address capital reward cap | 10% | Prevents capital concentration |
| Multiplicative formula structure | Ec × Is × Dv | Anti-gaming (all dimensions required) |

---

## 11. Migration Path

### 11.1 Phase 1: Off-Chain Scoring (no contract changes)

The VALIDATOR_ROLE oracle already computes scores off-chain and submits to DPCRegistry. Extend the oracle's computation to include:
- Physical labor input functions (Lh × St × Qp × Rk)
- Resource contribution scoring (FMV × U × Dc × (1-Dp) × Mn)
- RES type in bitmap (bit 7)

**No contract changes needed.** The oracle just submits richer scores.

### 11.2 Phase 2: CapitalRegistry Contract

Deploy CapitalRegistry alongside DPCRegistry. Update SplitEngine to read from both. Capital scoring goes on-chain.

### 11.3 Phase 3: Verification Infrastructure

Deploy resource verification protocol (Section 5.2). Integrate IoT/GPS oracles. Enable automated RES utilization tracking.

### 11.4 Phase 4: DPC OS Dashboard Update

Update the DPC OS dashboard to:
- Add RES contribution type with color and descriptions
- Update component labels from Rw→Dv
- Add capital score display (separate from governance)
- Add physical labor input form with skill/risk/quality sliders

---

## 12. Key Decisions

- **Extend inputs, not formula**: Keep `P = Ec^α × Is^β × max(Dv, ε)^γ`. Change how inputs are computed. *Alternative:* add new dimensions (P = f(Is, Ec, Dv, Lh, Rv, Cd)) — rejected because it breaks the multiplicative anti-gaming property and requires contract struct changes.

- **Dual-track scoring**: Separate P_gov and P_econ. *Alternative:* single score with capital discount — rejected because any nonzero capital→governance path violates the constitutional constraint.

- **Ec is multiplicative across dimensions**: Ec_total = Ec_digital × Ec_physical × Ec_resource. *Alternative:* additive — rejected because it allows a contributor to abandon one dimension while maintaining Ec through another, undermining "Proof of Grit."

- **RES as single type (not LND + EQP separate)**: Uses the last available bitmap bit. *Alternative:* upgrade to uint16 — rejected because it breaks IDPCRegistry struct and all downstream consumers. Subcategorize off-chain.

- **Minimum labor requirement for capital rewards**: P_gov > 0. *Alternative:* no requirement (pure capital earns rewards) — rejected because it allows anonymous capital extraction, recreating the investor-captures-value pattern we're eliminating.

- **180-day tenure cap with sqrt**: Prevents "park and forget" capital accumulation. *Alternative:* linear uncapped — rejected because long-idle capital is not more valuable than recently-deployed capital. The project needs runway, not a savings account.

---

## 13. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Physical labor attestation gaming (fake hours) | High | MPAP 2-of-3 quorum, rotating attesters, attestation staking, statistical anomaly detection |
| Resource FMV inflation | Medium | Third-party appraisal requirement for RES > $5K. Below $5K: peer consensus |
| Ec multiplicative penalty too harsh | Medium | Default Ec = 1.0 for dimensions without commitment. Only penalizes broken commitments. |
| Capital function misclassification | Low | Function type set by receiving contract registry, not contributor. Governance can reclassify. |
| Oracle centralization (VALIDATOR_ROLE) | High | Phase 3: decentralized oracle network. Phase 1 accepts centralized oracle as bootstrapping trade-off. |
| Normalization constants differ across projects | Low | Project-level governance sets normalization. Global defaults serve as baseline. |

---

## Appendix A: Variable Reference

```
CORE FORMULA:
  P_gov = Ec_total^α × Is_total^β × max(Dv_total, ε)^γ
  P_econ = P_gov + (C_econ × κ)

EXPONENTS:
  α = 0.4  (Ec weight)
  β = 0.35 (Is weight)
  γ = 0.25 (Dv weight)
  ε = 0.01 (Dv floor)
  κ = 0.3  (capital reward coefficient, max 0.5)

DIGITAL:
  Is_digital = Σ(artifact_weight × complexity × adoption)
  Ec_digital = streak_weeks^0.5 × frequency_ratio
  Dv_digital = Σ(user_count_delta × access_breadth)

PHYSICAL:
  Lh = labor hours
  St = skill tier (1.0/1.5/2.0/2.5)
  Qp = quality (0.5–1.5)
  Rk = risk premium (1.0/1.2/1.5/2.0)
  Is_physical = Σ(Lh × St × Qp × Rk) / 160
  Ec_physical = streak(W) × attendance(A)
  Dv_physical = Σ(B × accessibility_delta) / max_beneficiaries

RESOURCE:
  FMV = fair market value
  U   = utilization (0–1)
  Dc  = duration commitment (0.3–1.0)
  Dp  = depreciation (0–1)
  Mn  = maintenance (0.5–1.0)
  Is_resource = Σ(FMV × U × Dc × (1-Dp) × Mn) / 10000
  Ec_resource = Π(availability × maintenance)
  Dv_resource = Σ(access_expansion × shared_use) / max_expansion

CAPITAL (governance-excluded):
  Cd = capital deployed
  Ct = tenure (days, capped at 180)
  Cf = function multiplier (0.1–1.0)
  C_econ = Cd × min(Ct/180, 1.0)^0.5 × Cf
```

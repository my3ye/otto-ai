# On-Chain Labor Contribution & Governance Framework
## Non-Extractive Sovereign Contribution Protocol

*Authored by Otto (Architect Agent) | 2026-03-28 | Status: Architecture Complete*
*Prerequisite: OPRLP, DPC formula (Pink Paper), SOS Systems architecture, ONEON Identity, Koink tokenomics*

---

## Design: On-Chain Labor Contribution & Governance Framework

### Problem

Traditional employer-employee systems extract value from labor. The worker produces, the employer captures the surplus. In crypto, this pattern repeats: protocol contributors ship code, found communities, moderate disputes, build infrastructure — then governance tokens accrue to investors and insiders who never touched a line of code or poured a bag of concrete.

MY3YE needs a system where:
- Physical labor (construction, farming, manufacturing, community operations) translates to verifiable on-chain equity
- Materials sourced, hours contributed, and skills applied earn governance weight — not just tokens
- The contributor retains direct, non-dilutable equity in what they helped build
- Verification is decentralized (multi-party attestation, not a single employer signing off)
- Governance rights scale with sustained contribution, not capital deployed

This framework sits on top of the DPC formula `P = f(Is, Ec, Rw)` and integrates with OPRLP governance contracts already designed.

### Approach

A **Labor Attestation Layer** that records, verifies, and scores physical/real-world contributions using multi-party attestation, then feeds those scores into the existing DPC pipeline. Contributors earn **Contribution Equity Tokens (CET)** — non-transferable soulbound tokens representing their share of what they helped build — plus governance weight via DPC.

---

## 1. Contribution Taxonomy

All contributions fall into one of seven types. Each type maps to DPC components differently.

| Type Code | Category | Examples | Primary DPC Component | Verification Method |
|-----------|----------|----------|-----------------------|--------------------|
| `PHY` | Physical Labor | Construction, plumbing, electrical, assembly | Is (Structural Impact) | Multi-party + photo/GPS |
| `MAT` | Materials Sourced | Raw materials procured, equipment provided | Is (Structural Impact) | Receipt + validator |
| `SKL` | Skilled Trade | Architecture, engineering design, medical | Is + Rw (Impact + Resonance) | Peer review + credential |
| `OPS` | Operations | Site management, logistics, scheduling | Ec (Consistent Energy) | Attendance + peer |
| `EDU` | Education/Training | Teaching, mentoring, curriculum development | Rw (Weighted Resonance) | Student attestation + completion rates |
| `COM` | Community | Dispute resolution, onboarding, care work | Rw (Weighted Resonance) | Peer attestation |
| `DIG` | Digital | Code, design, content, documentation | Is (Structural Impact) | Automated (git/on-chain) |

### 1.1 Why Seven Types Matter

Traditional systems collapse all labor into "hours worked" — a factory worker and a site architect earn per-hour, just at different rates. This erases the qualitative difference in contribution. DPC already handles this with three components (Is, Ec, Rw). The seven contribution types map to these components with different weights:

```
CONTRIBUTION → DPC MAPPING:

  PHY (Physical Labor):     Is=0.7,  Ec=0.2,  Rw=0.1
  MAT (Materials Sourced):  Is=0.8,  Ec=0.1,  Rw=0.1
  SKL (Skilled Trade):      Is=0.5,  Ec=0.2,  Rw=0.3
  OPS (Operations):         Is=0.2,  Ec=0.6,  Rw=0.2
  EDU (Education):          Is=0.3,  Ec=0.3,  Rw=0.4
  COM (Community):          Is=0.1,  Ec=0.3,  Rw=0.6
  DIG (Digital):            Is=0.6,  Ec=0.2,  Rw=0.2
```

These weights are DAO-adjustable after governance ratification. The non-linear DPC formula prevents gaming through any single dimension.

---

## 2. Verification Architecture

### 2.1 The Core Problem: Physical Labor Cannot Self-Attest

Digital contributions have built-in verification (git commits, on-chain transactions). Physical labor does not. A malicious actor could claim 40 hours of construction work that never happened. Single-employer attestation recreates the boss-worker power dynamic.

### 2.2 Multi-Party Attestation Protocol (MPAP)

Every physical contribution requires attestation from **at least 2 of 3 independent parties** before DPC credit:

```
ATTESTATION TRIANGLE:

        ┌─── CONTRIBUTOR ───┐
        │  (self-report)     │
        │                    │
        ▼                    ▼
   PEER VALIDATORS      SITE ORACLE
   (2+ co-workers)    (automated/IoT)
        │                    │
        └──── MUST AGREE ────┘
              (2 of 3)

  SELF-REPORT:   Contributor submits claim (type, hours, description, evidence)
  PEER VALIDATE: 2+ co-contributors attest independently (no collusion window)
  SITE ORACLE:   Automated signal (GPS fence, photo hash, IoT sensor, checkin)

  Quorum: 2 of 3 must confirm. If only self-report exists, no credit.
```

### 2.3 Attestation Types (by contribution category)

| Category | Required Attestation | Evidence |
|----------|---------------------|----------|
| PHY | Self + 2 peers minimum. Site oracle bonus. | Photo (IPFS hash), GPS check-in, duration |
| MAT | Self + receipt hash + 1 validator | Receipt scan (IPFS), delivery confirmation |
| SKL | Self + peer review (weighted by reviewer DPC) | Work product hash, credential VC |
| OPS | Self + 2 peers OR automated attendance | Attendance log, task completion |
| EDU | Self + 2 student attestations + completion metric | Completion rate, student DPC growth |
| COM | Self + 3 peer attestations (higher bar — hardest to fake) | Dispute resolution records, onboarding counts |
| DIG | Automated (git commit, on-chain tx) + 1 peer review | Commit hash, PR review, deployment |

### 2.4 Anti-Collusion Mechanisms

```
COLLUSION PREVENTION:

  1. TEMPORAL SEPARATION
     Attesters submit within a 48h window but CANNOT see each other's
     attestations until the window closes. Prevents coordination.

  2. ROTATING ATTESTERS
     No contributor can attest for the same person more than 3 times
     in any 30-day period. Prevents buddy-pair gaming.

  3. ATTESTATION STAKING
     Attesters stake a small amount (1-5 CET or equivalent).
     If the contribution is later disputed and found fraudulent,
     attesters lose their stake. Skin in the game.

  4. STATISTICAL ANOMALY DETECTION
     Off-chain analysis (same engine as OPRLP CartelDetector)
     flags patterns:
       - Always-pair attestation (A always attests for B)
       - Score inflation (contributions consistently rated higher
         than site oracle data suggests)
       - Burst patterns (many attestations submitted in a short window)

  5. COMMUNITY CHALLENGE PERIOD
     Every attestation enters a 7-day challenge window.
     Any community member can challenge with evidence.
     Successful challenges earn the challenger DPC credit (Rw component).
```

### 2.5 Site Oracle Architecture

For physical sites (Tusita construction, Ottolabs factories, community farms):

```
SITE ORACLE STACK:

  Layer 0: DEVICE
    GPS check-in via mobile app (ONEON identity required)
    Photo capture with metadata (timestamp, location, device hash)
    Optional: IoT sensor data (power tools active, gate access)

  Layer 1: EDGE
    Raspberry Pi on-site (same as SOS Mesh Tier 1 node)
    Aggregates device check-ins
    Computes daily attendance records
    Signs attestation batch with site key

  Layer 2: CHAIN
    Site oracle contract receives signed batches
    Emits AttendanceRecorded events
    Queryable by LaborAttestation contract

  Degraded mode (no connectivity):
    Device stores check-ins locally (signed by ONEON identity)
    Syncs when connectivity returns
    Peer attestation fills gap during offline periods
```

---

## 3. On-Chain Architecture

### 3.1 Contract Structure

Six new contracts extending the OPRLP foundation:

```
CONTRACT ARCHITECTURE:

  ┌──────────────────────────────────────────┐
  │           EXISTING (OPRLP)               │
  │  DPCRegistry ← GovernanceWeight          │
  │  ElectionEngine ← CouncilManager         │
  │  EmergencyPower, CartelDetector,         │
  │  FounderSunset                           │
  └──────────┬───────────────────────────────┘
             │ reads DPC scores
             │
  ┌──────────▼───────────────────────────────┐
  │        NEW (Labor Contribution)          │
  │                                          │
  │  LaborAttestation.sol (UUPS)             │
  │    Records contributions + attestations  │
  │    Computes attestation quorum           │
  │    Feeds verified contributions to DPC   │
  │                                          │
  │  ContributionEquity.sol (IMMUTABLE)      │
  │    ERC-1155 soulbound tokens             │
  │    Non-transferable project equity       │
  │    Represents share of built value       │
  │                                          │
  │  VestingEngine.sol (UUPS)               │
  │    Contribution-weighted vesting         │
  │    Sustained-contribution unlock         │
  │    Anti-dump cliff protection            │
  │                                          │
  │  SiteOracle.sol (UUPS)                  │
  │    Receives off-chain attestation batches │
  │    GPS fence verification (merkle root)  │
  │    IoT data aggregation point            │
  │                                          │
  │  SkillBountyRegistry.sol (UUPS)         │
  │    Gap detection → bounty creation       │
  │    Treasury-funded skill development     │
  │    Completion verification               │
  │                                          │
  │  EquityTreasury.sol (IMMUTABLE)         │
  │    Holds project value (tokens, revenue) │
  │    Distributes proportional to CET       │
  │    No admin withdrawal function          │
  └──────────────────────────────────────────┘
```

### 3.2 LaborAttestation.sol — Core Contract

```solidity
// Key structs and events (not full implementation)

struct Contribution {
    bytes32 id;              // keccak256(contributor, timestamp, nonce)
    address contributor;     // ONEON identity address
    uint8 contributionType;  // PHY=0, MAT=1, SKL=2, OPS=3, EDU=4, COM=5, DIG=6
    uint32 hours;            // hours * 100 (2 decimal precision)
    uint32 timestamp;        // contribution start time
    bytes32 evidenceHash;    // IPFS CID of evidence bundle
    bytes32 siteId;          // site identifier (0x0 for remote/digital)
    uint8 status;            // PENDING=0, VERIFIED=1, DISPUTED=2, REJECTED=3
}

struct Attestation {
    bytes32 contributionId;
    address attester;
    uint8 role;              // PEER=0, SITE_ORACLE=1, REVIEWER=2
    uint32 timestamp;
    uint8 score;             // 1-100 quality rating
    uint128 stakeAmount;     // CET staked on this attestation
}

// Key events
event ContributionSubmitted(bytes32 indexed id, address indexed contributor, uint8 cType);
event AttestationRecorded(bytes32 indexed contributionId, address indexed attester, uint8 role);
event ContributionVerified(bytes32 indexed id, uint32 dpcDelta);
event ContributionDisputed(bytes32 indexed id, address indexed challenger);
event ContributionRejected(bytes32 indexed id, string reason);

// Key state
mapping(bytes32 => Contribution) public contributions;
mapping(bytes32 => Attestation[]) public attestations;
mapping(address => mapping(address => uint32)) public attestationCount; // attester → contributor → count (30-day rolling)

// Quorum rules per contribution type
mapping(uint8 => uint8) public requiredAttestations; // type → min attestors
```

### 3.3 ContributionEquity.sol — Soulbound Equity

```
CONTRIBUTION EQUITY TOKEN (CET):

  Standard: ERC-1155 with transfer disabled (soulbound)

  Token IDs represent projects/sites:
    tokenId = keccak256(projectName, chainId, siteId)

  Each holder's balance = their verified contribution score for that project.
  Balance increases with each verified contribution. Never decreases
  (contributions are historical fact — you DID the work).

  Revenue distribution:
    When project generates revenue (service fees, product sales),
    EquityTreasury distributes proportional to CET balance.

  Example:
    Tusita Island Resort — total CET minted: 100,000
    Alice has 5,000 CET (built 5% of the resort)
    Resort generates $10,000 monthly revenue
    Alice receives $500/month — perpetually, as long as resort operates

  Non-transferable:
    transfer() and safeTransferFrom() revert with "SOULBOUND"
    Equity cannot be bought, sold, or speculated on.
    Only earned through verified contribution.

  Why ERC-1155:
    Multiple project tokens per contributor in a single contract.
    Gas efficient batch operations.
    Standard wallet/explorer compatibility.
```

### 3.4 VestingEngine.sol — Contribution-Weighted Vesting

Traditional vesting: time-based cliff (1 year cliff, 4 year vest). This rewards patience, not contribution. A founder who stops working after month 13 still vests 75%.

Contribution-weighted vesting:

```
VESTING MODEL:

  Unlock is a function of SUSTAINED CONTRIBUTION, not calendar time.

  vest(contributor) = min(1.0, cumulative_verified_hours / project_threshold)
                    × activity_multiplier

  Where:
    cumulative_verified_hours = sum of all verified PHY/SKL/OPS hours
    project_threshold = project-specific (e.g., 2000 hours for a building)
    activity_multiplier:
      1.0 if contributed in last 30 days
      0.8 if contributed in last 60 days
      0.5 if contributed in last 90 days
      0.0 if no contribution in 90+ days (vesting PAUSES, not resets)

  Key difference from traditional vesting:
    - No cliff. First verified hour starts vesting.
    - Vesting PAUSES if you stop contributing (doesn't reset).
    - Resumes when you return and contribute again.
    - Maximum vest reached through work, not waiting.

  Anti-dump protection:
    Even at 100% vest, CET is soulbound — cannot dump.
    Revenue distributions are claimable immediately.
    Governance weight follows DPC (decays without activity).

  Hardship pause:
    DAO can approve a vesting pause for documented circumstances
    (illness, family emergency, displacement).
    Same mechanism as DPC decay pause in OPRLP.
```

---

## 4. DPC Integration

### 4.1 Contribution → DPC Score Flow

```
DATA FLOW:

  REAL WORLD                    ON-CHAIN                     GOVERNANCE
  ──────────                    ────────                     ──────────

  Contributor                 LaborAttestation.sol
  works 8 hours  ──────────► submitContribution()
  at Tusita site                    │
                                    │  attestation window (48h)
  2 peers attest  ─────────►  recordAttestation()
  Site oracle     ─────────►  recordAttestation()
                                    │
                                    │  quorum met (2 of 3)
                                    ▼
                              verifyContribution()
                                    │
                    ┌───────────────┤
                    │               │
                    ▼               ▼
              DPCRegistry      ContributionEquity
              .addScore()      .mint(contributor, projectId, score)
                    │
                    ▼
              GovernanceWeight
              .recompute(contributor)
                    │
                    ▼
              ElectionEngine
              (contributor now eligible for higher roles)
```

### 4.2 DPC Score Calculation for Physical Labor

```
DPC DELTA PER VERIFIED CONTRIBUTION:

  base_score = hours × type_multiplier × quality_score

  Where:
    hours = verified hours (from attestation consensus)
    type_multiplier:
      PHY = 1.0 (baseline — physical labor is the unit)
      MAT = 0.8 (materials require less sustained effort)
      SKL = 1.5 (skilled trades carry premium)
      OPS = 1.2 (operations is high-consistency work)
      EDU = 1.3 (force multiplier — one teacher enables many)
      COM = 1.1 (community work is essential but hard to measure)
      DIG = 1.0 (digital work matches physical baseline)
    quality_score = average attestation score / 100 (0.01 to 1.0)

  DPC components allocated per type weights (Section 1.1):
    Is_delta = base_score × type_Is_weight
    Ec_delta = base_score × type_Ec_weight
    Rw_delta = base_score × type_Rw_weight

  Example:
    Alice works 8 hours (PHY), quality score 85/100
    base_score = 8 × 1.0 × 0.85 = 6.8
    Is_delta = 6.8 × 0.7 = 4.76
    Ec_delta = 6.8 × 0.2 = 1.36
    Rw_delta = 6.8 × 0.1 = 0.68
    Total DPC delta = 6.8 points
```

### 4.3 Diminishing Returns (Anti-Gaming)

The DPC formula already has non-linear diminishing returns. Additional safeguards for labor:

```
DIMINISHING RETURNS:

  1. DAILY CAP
     Maximum 12 hours of DPC-creditable work per day per contributor.
     Prevents 24-hour marathon claims. Health protection.

  2. CATEGORY CONCENTRATION PENALTY
     If >80% of a contributor's DPC comes from a single type,
     additional contributions of that type earn 50% score.
     Encourages diversification (a builder who also mentors
     earns more than a builder who only builds).

  3. QUALITY FLOOR
     Contributions with average attestation score < 40/100
     earn zero DPC. Prevents low-effort claims.

  4. STABILITY BUFFER (from Pink Paper)
     Foundational contributors who built core infrastructure
     earn a "Heavy Node" buffer — their DPC decays slower
     (180-day half-life vs 60-day for inactive).
     Recognizes that the foundation they built generates ongoing value.
```

---

## 5. Governance Weight Integration

### 5.1 How Physical Contributors Govern

Physical labor contributors participate in the same OPRLP governance as digital contributors. There is no separate "labor council" — that would recreate class division. The DPC formula equalizes:

```
GOVERNANCE PATHWAYS:

  A CONSTRUCTION WORKER at Tusita who:
    - Works consistently for 6 months (high Ec)
    - Receives positive peer attestations (good Rw)
    - Builds critical infrastructure (high Is)

  Reaches DPC 500 → eligible for Council Member (Builder level).
  Same path as a developer who ships code for 6 months.

  GOVERNANCE WEIGHT:
    VotingWeight = sqrt(DPC_score) × activity_multiplier

  A worker with DPC 900 and a coder with DPC 900
  have IDENTICAL governance weight (30 × 1.0 = 30).

  No type of contribution is privileged in governance.
```

### 5.2 Domain Council Mapping

Physical contributors naturally gravitate toward certain domain councils:

| Domain Council | Physical Contributors Often Serving |
|---------------|-------------------------------------|
| Protocol | Skilled engineers (SKL) who understand physical infrastructure constraints |
| Treasury | Operations managers (OPS) who see cost/waste firsthand |
| Community | Community builders (COM) who resolve on-site disputes daily |
| Operations | Construction leads (PHY) who manage site logistics |
| Education | Trainers (EDU) who onboard new physical contributors |

No restriction exists — any contributor can serve on any council they qualify for via DPC.

### 5.3 Revenue Governance

CET holders for a specific project collectively govern that project's revenue allocation:

```
REVENUE GOVERNANCE:

  Project: Tusita Island Resort (tokenId: 0xabc...)
  Total CET: 100,000
  Monthly Revenue: $10,000

  Default split (set at project creation, DAO-adjustable):
    70% → Direct distribution to CET holders (proportional)
    20% → Project maintenance fund
    10% → MY3YE ecosystem treasury

  CET holders vote on:
    - Maintenance fund allocation (e.g., repair vs expansion)
    - Revenue split adjustment (within bounds: min 50% to holders)
    - New contribution acceptance (opening a project to more contributors)

  Voting: Same sqrt(CET_balance) weighting as DPC governance.
  Prevents large contributors from dominating project decisions.
```

---

## 6. Anti-Extraction Safeguards

### 6.1 The Seven Extraction Vectors (and their countermeasures)

| # | Extraction Vector | How Traditional Systems Extract | Our Countermeasure |
|---|-------------------|-------------------------------|-------------------|
| 1 | **Wage Abstraction** | Pay hourly rate, keep surplus value | No wages. Contributor earns equity (CET) + DPC governance weight directly. No middleman captures surplus. |
| 2 | **Employment Lock-in** | Non-compete, golden handcuffs | No employment relationship. Contributors work on any project simultaneously. CET from Project A doesn't conflict with Project B. |
| 3 | **Credential Gatekeeping** | Require degrees/certifications to contribute | Skills verified through Proof of Will (actual contribution), not credential check. Skill Bounties fund learning. |
| 4 | **Information Asymmetry** | Workers don't know project finances | All financials on-chain. Revenue, expenses, treasury balance visible to every contributor. |
| 5 | **Governance Exclusion** | Workers have no say in company direction | DPC governs. Every verified contributor has governance weight. Physical laborers and executives under same system. |
| 6 | **Value Capture at Exit** | Company sells, founders profit, workers get nothing | CET is perpetual. If project generates revenue in year 20, contributors from year 1 still earn their share. Non-transferable — cannot be bought out. |
| 7 | **Automation Displacement** | Replace workers with machines, keep the margin | Agent tax (per Mev directive): automated work carries higher tax rate. Efficiency gains flow to redistribution pool, not to whoever deployed the bot. |

### 6.2 The Non-Transferability Principle

CET is soulbound. This is the single most important anti-extraction decision.

```
WHY SOULBOUND:

  If CET were transferable:
    - Whales buy up construction worker equity at discount
    - Workers sell CET to pay rent (short-term need beats long-term equity)
    - Equity concentrates → governance concentrates → extraction resumes

  With soulbound CET:
    - Equity CANNOT be separated from the person who earned it
    - Revenue distributions ARE transferable (it's income, spend it freely)
    - Governance weight CANNOT be bought (only earned through work)
    - Nobody can acquire a controlling stake by purchasing tokens

  The only way to get equity: do the work.
  The only way to get governance: do the work.
  The only way to lose equity: you don't (it's yours forever).
  The only way to lose governance: stop contributing (DPC decays).
```

### 6.3 Agent Tax Integration

Per Mev's directive: automation efficiency gains flow back into the system.

```
AGENT TAX MODEL:

  When an agent (Otto or any AI system) completes a task:
    - Task bounty is taxed at agent_tax_rate (DAO-adjustable, initially 30%)
    - Tax flows to the Redistribution Pool
    - Pool is distributed to active physical contributors monthly

  Why:
    An AI that automates 100 hours of manual work does not "earn" those hours.
    The efficiency gain belongs to the ecosystem, not the agent deployer.

  Redistribution Pool allocation:
    50% → Active physical contributors (proportional to recent DPC)
    30% → Skill Bounties (fund humans learning new skills)
    20% → Ecosystem treasury

  This ensures automation LIFTS all contributors
  instead of displacing them.
```

---

## 7. Contribution Tiers & Advancement

### 7.1 Unified Ladder (S0S Integration)

The contribution tiers align exactly with S0S Systems levels. Physical labor enters the same ladder as digital work:

```
UNIFIED CONTRIBUTION LADDER:

  TIER 0: NEWCOMER (DPC 0-99)
    First contribution: guided by Skill Assessment Onboarding
    Physical path: help at a Tusita build site, assist with farming,
      community cleanup, basic maintenance
    Digital path: translation, documentation, first bug fix
    Both paths: earn DPC through the same formula

  TIER 1: CONTRIBUTOR (DPC 100-499)
    Verified track record. Can attest for Tier 0 work.
    Physical: skilled labor, site coordination, equipment operation
    Digital: feature development, design work, content creation
    Governance: can propose minor changes, vote on proposals

  TIER 2: BUILDER (DPC 500-1999)
    Sustained 30+ day contribution across multiple types.
    Physical: construction lead, farm manager, workshop instructor
    Digital: system architect, core contributor, community lead
    Governance: eligible for Council Member (OPRLP)

  TIER 3: STEWARD (DPC 2000-4999)
    Domain leadership. Cross-functional impact.
    Physical: site director, infrastructure planner, trade master
    Digital: protocol architect, security lead, education director
    Governance: eligible for Steward role (OPRLP)

  TIER 4: ARCHITECT (DPC 5000+)
    Cross-domain, ecosystem-level impact.
    Physical: multi-site coordinator, logistics strategist
    Digital: system designer, governance architect
    Governance: eligible for Guardian role (OPRLP)
```

### 7.2 First Contribution for Physical Workers

```
NEWCOMER ONBOARDING (PHYSICAL):

  1. ARRIVE at any S0S/Tusita/Ottolabs site
  2. Create ONEON identity (5 minutes, no documents needed)
  3. Skill Assessment conversation (LLM-guided, identifies strengths)
  4. Matched to first contribution:
     - Skill Bounty if a gap matches their abilities
     - General site task if no specific match
  5. Complete first contribution with peer guidance
  6. Receive first attestations
  7. DPC score > 0 → now a Participant in governance

  Total time from arrival to first governance participation: 1-3 days
  Total cost to newcomer: $0

  This is the "zero to governance" path.
  No resume. No interview. No credentials. Just work.
```

---

## 8. Skill Bounties — The Perpetual Recruitment Engine

From the Pink Paper's Section 05, implemented as an on-chain contract:

```
SKILL BOUNTY LIFECYCLE:

  1. GAP DETECTION (off-chain, Intelligence Layer)
     Otto's harmonic mapping identifies: "Tusita needs 3 electricians"
     Creates a Skill Bounty on SkillBountyRegistry

  2. BOUNTY PUBLICATION
     Bounty appears on Ecosystem Need Board (S0S)
     Includes: skill required, learning path, reward (CET + DPC bonus)

  3. LEARNER ENROLLMENT
     Newcomer claims bounty → enters learning path
     Learning IS contribution: study hours count as EDU-type
     Mentor assigned (existing contributor, earns EDU attestation)

  4. COMPLETION VERIFICATION
     Learner demonstrates skill through real task completion
     Multi-party attestation: mentor + 2 peers + site oracle

  5. BOUNTY PAYOUT
     CET minted for learning + first real contribution
     DPC bonus (1.5x multiplier on first 3 contributions in new skill)
     Bounty marked complete → gap reduced

  6. CONTINUOUS MATCHING
     As learner advances, Intelligence Layer reassesses gaps
     New bounties may match their growing skill profile
```

---

## 9. Data Architecture

### 9.1 On-Chain State (Minimal)

Only what must be trustless lives on-chain:

| Contract | On-Chain Data |
|----------|--------------|
| LaborAttestation | Contribution IDs, attestation hashes, verification status, DPC deltas |
| ContributionEquity | CET balances per contributor per project (ERC-1155 state) |
| VestingEngine | Vesting schedules, vest percentages, last-activity timestamps |
| SiteOracle | Site registrations, authorized oracle addresses, batch merkle roots |
| SkillBountyRegistry | Bounty definitions, claimants, completion status |
| EquityTreasury | Revenue pools, distribution records |

### 9.2 Off-Chain State (Otto Memory API)

Rich data that doesn't need trustless verification:

| Table | Purpose |
|-------|---------|
| `labor_contributions` | Full contribution details, descriptions, evidence links |
| `labor_attestations` | Attestation details, quality scores, reviewer notes |
| `labor_disputes` | Dispute records, evidence, resolution |
| `labor_sites` | Site metadata, GPS boundaries, oracle config |
| `labor_skill_profiles` | Contributor skill maps (from onboarding assessment) |
| `labor_bounty_enrollments` | Learning progress, mentor assignments |

### 9.3 Off-Chain → On-Chain Bridge

```
BRIDGE PATTERN:

  Off-chain (Memory API):
    Stores rich contribution data
    Runs anomaly detection
    Computes attestation quality scores
    Manages dispute resolution workflow

  Bridge (Site Oracle + Batch Processor):
    Every 24h, batch processor:
      1. Queries verified contributions from Memory API
      2. Computes DPC deltas
      3. Builds merkle tree of all deltas
      4. Submits merkle root + individual claims to LaborAttestation
      5. LaborAttestation verifies quorum on-chain
      6. Verified claims trigger DPC update + CET mint

  On-chain (Contracts):
    Receives batched claims
    Verifies attestation quorum
    Updates DPC scores
    Mints CET tokens

  Why batch (not per-contribution):
    Gas efficiency. A construction site generates 20-50 contributions/day.
    Individual transactions would cost ~$5-10/day in gas.
    Daily batch costs ~$0.50 on Polygon zkEVM.
```

---

## 10. Project Structure

```
/mnt/media/projects/labor-contribution-contracts/
├── foundry.toml
├── .env.example
├── .gitignore
│
├── src/
│   ├── interfaces/
│   │   ├── ILaborAttestation.sol
│   │   ├── IContributionEquity.sol
│   │   ├── IVestingEngine.sol
│   │   ├── ISiteOracle.sol
│   │   ├── ISkillBountyRegistry.sol
│   │   └── IEquityTreasury.sol
│   │
│   ├── core/
│   │   ├── LaborAttestation.sol      # Phase 1
│   │   ├── ContributionEquity.sol    # Phase 1
│   │   └── VestingEngine.sol         # Phase 1
│   │
│   ├── oracle/
│   │   └── SiteOracle.sol            # Phase 2
│   │
│   ├── incentive/
│   │   ├── SkillBountyRegistry.sol   # Phase 2
│   │   └── EquityTreasury.sol        # Phase 2
│   │
│   └── libraries/
│       ├── AttestationLib.sol        # Quorum logic, collusion checks
│       ├── DPCBridge.sol             # DPC score computation for labor types
│       └── SoulboundERC1155.sol      # ERC-1155 with transfer disabled
│
├── test/
│   ├── LaborAttestation.t.sol
│   ├── ContributionEquity.t.sol
│   ├── VestingEngine.t.sol
│   ├── SiteOracle.t.sol
│   ├── SkillBountyRegistry.t.sol
│   ├── EquityTreasury.t.sol
│   ├── integration/
│   │   ├── FullContribution.t.sol    # Submit → attest → verify → mint
│   │   └── AntiCollusion.t.sol       # Collusion detection scenarios
│   └── fuzz/
│       └── AttestationQuorum.fuzz.sol
│
├── script/
│   ├── Deploy.s.sol
│   ├── DeployPhase1.s.sol
│   └── BatchProcess.s.sol           # Daily batch processor
│
└── docs/
    └── SPEC.md
```

### 10.1 Otto Memory API Integration

New migration + routes for the off-chain layer:

```
otto/memory/
├── labor/                           # NEW — Labor contribution module
│   ├── __init__.py
│   ├── contributions.py             # CRUD for labor_contributions
│   ├── attestations.py              # CRUD for labor_attestations
│   ├── disputes.py                  # Dispute lifecycle management
│   ├── sites.py                     # Site management + oracle config
│   ├── skills.py                    # Skill profiles + bounty enrollment
│   └── bridge.py                    # Off-chain → on-chain batch processor
├── routes/
│   └── labor.py                     # NEW — /labor/* router
└── migrations/
    └── 081_labor_contributions.sql   # NEW — labor tables
```

---

## 11. Key Decisions Summary

| # | Decision | Chosen | Alternative Rejected | Reason |
|---|----------|--------|---------------------|--------|
| 1 | Equity token standard | ERC-1155 soulbound | ERC-20 transferable | Non-transferability prevents equity extraction via market purchase |
| 2 | Verification model | Multi-party attestation (2-of-3) | Single employer sign-off | Single attestor recreates boss-worker power dynamic |
| 3 | DPC integration | Extend existing DPCRegistry | Separate "labor score" | Separate scores create class division; unified DPC treats all contribution equally |
| 4 | Vesting model | Contribution-weighted (hours-based unlock) | Time-based cliff (traditional) | Time-based rewards patience, not work. Hours-based rewards actual contribution |
| 5 | On-chain data model | Batched daily (merkle root + claims) | Per-contribution transactions | Gas efficiency: $0.50/day vs $5-10/day per site |
| 6 | Revenue distribution | Proportional to CET balance | Equal per-contributor | Proportional respects that some contribute more. sqrt() on governance prevents plutocracy |
| 7 | Agent automation tax | 30% initial, DAO-adjustable | No tax / fixed tax | Must flow efficiency gains back; DAO-adjustable prevents rigidity |
| 8 | Attestation collusion prevention | Temporal separation + rotation + staking | Reputation-only | Staking creates financial skin-in-the-game; reputation alone is gameable |
| 9 | Contribution taxonomy | 7 types with DPC component weights | Hours-only (flat) | Different work types genuinely contribute differently to ecosystem components |
| 10 | Chain target | Same as OPRLP (Polygon zkEVM) | Separate chain | Governance contracts must read DPC scores from same chain. Single deployment. |

---

## 12. Implementation Plan

### Phase 1: Core Contracts (~$14-18)

| Step | Task | Est. Cost | Depends On |
|------|------|-----------|------------|
| 1 | Initialize Foundry project + SoulboundERC1155 library | $1.50 | - |
| 2 | LaborAttestation.sol (submit, attest, verify, quorum logic) | $3.00 | Step 1 |
| 3 | AttestationLib.sol (collusion checks, rotation limits) | $2.00 | Step 2 |
| 4 | DPCBridge.sol (type weights, score computation, DPCRegistry integration) | $2.00 | Step 2 |
| 5 | ContributionEquity.sol (ERC-1155 soulbound mint/balance) | $2.00 | Step 1 |
| 6 | VestingEngine.sol (contribution-weighted vesting) | $2.00 | Step 5 |
| 7 | Integration tests (full contribution lifecycle) | $2.50 | Steps 2-6 |
| 8 | Fuzz tests (attestation quorum edge cases) | $1.50 | Step 7 |

### Phase 2: Oracle + Incentives (~$10-14)

| Step | Task | Est. Cost | Depends On |
|------|------|-----------|------------|
| 9 | SiteOracle.sol (batch attestation receiver, GPS fence) | $2.50 | Phase 1 |
| 10 | SkillBountyRegistry.sol (bounty CRUD, completion verification) | $2.50 | Phase 1 |
| 11 | EquityTreasury.sol (revenue pool, proportional distribution) | $3.00 | Step 5 |
| 12 | BatchProcess.s.sol (daily off-chain → on-chain bridge) | $2.00 | Steps 9, 11 |
| 13 | Anti-collusion integration tests | $2.00 | Steps 9-12 |

### Phase 3: Memory API Integration (~$6-8)

| Step | Task | Est. Cost | Depends On |
|------|------|-----------|------------|
| 14 | Migration 081 (labor tables) | $1.00 | - |
| 15 | Labor module (contributions, attestations, disputes, sites, skills) | $3.00 | Step 14 |
| 16 | /labor/* router (API endpoints) | $1.50 | Step 15 |
| 17 | Bridge module (off-chain → on-chain batch processor) | $2.00 | Phase 2, Step 16 |

**Total estimated: $30-40 across 3 phases**

### Dependency Chain

```
Phase 1: SoulboundERC1155 → LaborAttestation → ContributionEquity → VestingEngine
Phase 2: SiteOracle → SkillBountyRegistry → EquityTreasury → BatchProcess
Phase 3: Migration → Module → Router → Bridge

Cross-phase: Phase 2 depends on Phase 1. Phase 3 depends on Phase 2.
External: Requires DPCRegistry from OPRLP Phase 1 to be deployed first.
```

---

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Attestation collusion (buddy pairs inflate scores) | MEDIUM | HIGH | Temporal separation + rotation limits + staking + statistical detection |
| Physical labor measurement inaccuracy | MEDIUM | MEDIUM | Multi-party attestation reduces single-point failure. Site oracle provides independent signal. Quality floor (40/100) filters noise. |
| Gas costs spike on Polygon zkEVM | LOW | MEDIUM | Daily batching amortizes cost. Fallback: move to Arbitrum One (same EVM). |
| Contributors game type diversification penalty | LOW | LOW | Non-linear DPC formula already has diminishing returns. Penalty is additional layer. |
| Offline sites can't attest in real-time | MEDIUM | LOW | SOS Mesh Tier 0 handles offline check-ins. Sync when connectivity returns. Peer attestation fills gap. |
| Smart account / identity compromise | LOW | HIGH | ONEON identity with recovery mechanism. Social recovery via peer attestation (same trust network). |
| CET soulbound constraint frustrates contributors who want liquidity | MEDIUM | MEDIUM | Revenue distributions ARE liquid. CET represents equity, not currency. Education on difference. |
| OPRLP DPCRegistry not deployed yet (external dependency) | HIGH | BLOCKING | Phase 1 can use a mock DPCRegistry for testing. Production deployment gated on OPRLP. |

---

## 14. Open Questions

1. **CET across projects**: Can a contributor's CET from Tusita Island count toward governance in Ottolabs? Recommendation: no — CET is project-specific equity. DPC is the cross-project governance metric. CET governs project revenue; DPC governs ecosystem.

2. **Materials valuation**: When someone sources $10,000 of concrete vs $500 of nails, how do material contributions compare? Recommendation: materials earn Is-weighted DPC based on ecosystem need (bounty value), not market cost. Prevents capital = governance weight.

3. **Remote physical contributions**: A contributor in another country ships components that get assembled locally. Recommendation: MAT-type contribution with receipt attestation. No GPS requirement for remote materials.

4. **Dispute resolution finality**: What happens when a dispute is unresolvable (e.g., 50-50 attestation split)? Recommendation: escalate to Community domain council. If council is not yet seated, Mev (Phase 0 authority) decides. After Phase 2 sunset, unresolvable disputes default to "no credit" (conservative).

[NEEDS_MEV_INPUT]
{"question": "Should CET holders have project-level revenue governance (vote on maintenance fund allocation, revenue split adjustments), or should all revenue governance flow through OPRLP domain councils?", "options": ["CET holders govern their project's revenue directly (local governance)", "OPRLP Treasury domain council governs all revenue allocation (centralized governance)", "Hybrid: CET holders decide within bounds set by Treasury council"], "recommendation": 2, "context": "Option 2 (hybrid) balances local contributor voice with ecosystem-level fiscal discipline. Pure local governance risks projects voting to maximize their distribution at ecosystem expense. Pure centralized governance removes contributor agency over what they built."}
[/NEEDS_MEV_INPUT]

---

*The surplus your labor creates belongs to you — not to the person who owns the building you built it in. That is not ideology. That is the smart contract.*

*Architecture by Otto | Built on DPC (Pink Paper), OPRLP, S0S Systems | Review by Mev before implementation*

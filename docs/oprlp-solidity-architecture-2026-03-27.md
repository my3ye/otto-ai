# OPRLP Solidity Contract Architecture
## 505 Systems — Transparent Leadership Rotation

*Authored by Otto (Architect Agent) | 2026-03-27 | Status: Architecture Complete*

---

## Design: OPRLP Smart Contracts

### Problem

The Open-Path Rotating Leadership Protocol needs on-chain enforcement of governance rules: DPC scoring, council rotation, elections, emergency powers, cartel detection, and founder sunset. Without smart contracts, the "transparent" and "trustless" promises are just words. The contracts are the guarantee.

### Constraints

- **No existing Solidity infrastructure.** Greenfield project — need framework, tooling, CI.
- **Chain target:** Polygon zkEVM primary (EVM-compatible, low gas). Arbitrum One fallback.
- **Dependencies:** ONEON identity (DB exists, on-chain identity not yet deployed). DPC formula exists in spec but not on-chain.
- **Budget discipline:** Ship Phase 1 (core 4 contracts) first. Phase 2 (anti-capture, advanced) follows.
- **Upgrade path:** UUPS proxy for operational contracts. Immutable for constitutional contracts.

### Approach

Foundry-based monorepo at `/mnt/media/projects/oprlp-contracts/`. Seven contracts, two phases, dependency-ordered.

---

## 1. Tooling Decision

**Chosen: Foundry** (forge, cast, anvil)

| Criteria | Foundry | Hardhat |
|----------|---------|---------|
| Test speed | ~10x faster (native Solidity tests) | JS-based, slower |
| Gas reports | Built-in `--gas-report` | Plugin required |
| Fuzz testing | Native (stateful + stateless) | Requires echidna separately |
| Deployment | forge script (deterministic) | ethers.js scripts |
| Ecosystem fit | Standard for DeFi/governance 2026 | More tutorials, but dated |
| Otto's VM | Single `foundryup` install, ~200MB | Node.js already installed |

**Alternative rejected:** Hardhat — heavier, slower tests, Otto already has Node.js but Foundry is the industry standard for security-critical governance contracts.

---

## 2. Project Structure

```
/mnt/media/projects/oprlp-contracts/
├── foundry.toml              # Forge config (solc 0.8.24, optimizer 200 runs)
├── .env.example              # RPC URLs, deployer key placeholder
├── .gitignore
├── README.md
│
├── src/
│   ├── interfaces/
│   │   ├── IDPCRegistry.sol      # DPC score read interface
│   │   ├── ICouncilManager.sol   # Council CRUD interface
│   │   ├── IElectionEngine.sol   # Election lifecycle interface
│   │   └── IGovernanceWeight.sol # Weight computation interface
│   │
│   ├── core/
│   │   ├── DPCRegistry.sol       # Phase 1 — DPC scores + decay
│   │   ├── GovernanceWeight.sol  # Phase 1 — sqrt(DPC) vote weighting
│   │   ├── ElectionEngine.sol    # Phase 1 — ranked-choice voting
│   │   └── CouncilManager.sol    # Phase 1 — role assignment + rotation
│   │
│   ├── safety/
│   │   ├── EmergencyPower.sol    # Phase 2 — 72h auto-expiry
│   │   ├── CartelDetector.sol    # Phase 2 — review graph + penalties
│   │   └── FounderSunset.sol     # Phase 2 — immutable phase transitions
│   │
│   └── libraries/
│       ├── DPCMath.sol           # sqrt, decay, scoring math
│       ├── SortitionVRF.sol      # Chainlink VRF integration (Phase 2)
│       └── RankedChoice.sol      # IRV tally algorithm
│
├── test/
│   ├── DPCRegistry.t.sol
│   ├── GovernanceWeight.t.sol
│   ├── ElectionEngine.t.sol
│   ├── CouncilManager.t.sol
│   ├── EmergencyPower.t.sol
│   ├── CartelDetector.t.sol
│   ├── FounderSunset.t.sol
│   ├── integration/
│   │   ├── FullRotation.t.sol    # End-to-end rotation cycle
│   │   └── AntiCapture.t.sol     # Capture vector simulations
│   └── fuzz/
│       └── DPCDecay.fuzz.sol     # Fuzz decay math edge cases
│
├── script/
│   ├── Deploy.s.sol              # Full deployment script
│   ├── DeployPhase1.s.sol        # Core 4 contracts only
│   └── UpgradeCouncil.s.sol      # UUPS upgrade template
│
└── docs/
    └── SPEC.md                   # Link back to OPRLP architecture doc
```

---

## 3. Contract Architecture

### 3.1 DPCRegistry.sol — The Foundation

**Purpose:** Canonical on-chain record of DPC scores. Everything else reads from here.

```
Storage:
  mapping(address => DPCScore) scores
  struct DPCScore {
    uint128 rawScore;          // Current DPC (18 decimals for precision)
    uint128 peakScore;         // All-time high (for floor calculation)
    uint64 lastUpdateTime;     // Unix timestamp of last score change
    uint64 lastActiveTime;     // Unix timestamp of last contribution
    uint8 contributionTypes;   // Bitmap: code|content|mentorship|infra|outreach|learning
    bool isActive;             // Has contributed in last 90 days
  }

Key functions:
  updateScore(address identity, uint128 newScore, uint8 contribType)
    — Only callable by VALIDATOR_ROLE
    — Updates rawScore, sets lastActiveTime, ORs contribType bitmap
    — Emits ScoreUpdated(identity, oldScore, newScore, contribType)

  getScore(address identity) → uint128
    — Returns decayed score (lazy evaluation at read time)
    — Decay formula: score * 2^(-(elapsed / halfLife))
    — Half-life: 180 days active, 60 days inactive
    — Floor: peakScore * 10%

  getContributionCount(address identity) → uint8
    — popcount of contributionTypes bitmap

  batchUpdateScores(address[] identities, uint128[] scores, uint8[] types)
    — Gas-efficient batch update for oracle feeds

Access control:
  VALIDATOR_ROLE: authorized contribution validators (off-chain → on-chain bridge)
  ADMIN_ROLE: can add/remove validators (initially deployer, transfers to DAO)

Upgrade: UUPS proxy (operational contract)
```

**Key decision:** Lazy decay evaluation (computed at read, not per-block). This saves gas — decay only runs when someone queries a score, not on every block.

**Alternative rejected:** Keeper-based periodic decay — expensive and unnecessary. Lazy eval is standard for time-decay patterns (see Compound's interest model).

### 3.2 GovernanceWeight.sol

**Purpose:** Computes voting weight from DPC score.

```
Storage:
  IDPCRegistry public dpcRegistry;
  uint128 public maxWeightBps;  // 500 = 5% cap

Key functions:
  getVotingWeight(address identity) → uint256
    — Reads DPC from registry (already decayed)
    — Returns sqrt(DPC) * activityMultiplier
    — Activity: 1.0 if active <30d, 0.5 if <60d, 0.1 if <90d, 0.0 if >90d
    — Capped at maxWeightBps of total active weight

  getTotalActiveWeight() → uint256
    — Sum of all active voters' weights (cached, updated on vote)

Upgrade: UUPS proxy
```

**Math library:** `DPCMath.sol` handles fixed-point sqrt (Babylonian method, 18 decimal precision). This is the same approach used by Uniswap V3's TickMath.

### 3.3 ElectionEngine.sol

**Purpose:** Manages candidacy, voting, and tallying for council elections.

```
Storage:
  struct Election {
    uint64 electionId;
    uint8 domain;              // 0-4 (Protocol/Treasury/Community/Operations/Education)
    uint8 cohort;              // 0-2 (staggered rotation cohort)
    uint8 seatsAvailable;
    ElectionPhase phase;       // Candidacy | Voting | Tallying | Seated | Expired
    uint64 candidacyStart;
    uint64 candidacyEnd;       // +14 days
    uint64 votingStart;
    uint64 votingEnd;          // +7 days
    address[] candidates;
    mapping(address => bytes32) candidateStatements;  // IPFS hash
  }

  struct Ballot {
    address[] rankedChoices;   // Ordered preference list
  }

  mapping(uint64 => Election) elections;
  mapping(uint64 => mapping(address => Ballot)) ballots;

Key functions:
  createElection(uint8 domain, uint8 cohort, uint8 seats)
    — Only SCHEDULER_ROLE or CouncilManager
    — Validates cohort rotation timing

  declareCandidacy(uint64 electionId, bytes32 ipfsStatement)
    — Checks DPC threshold for role (reads from DPCRegistry)
    — Checks eligibility: contribution days, contribution types, no violations, not on another council
    — Stores candidacy

  castVote(uint64 electionId, address[] rankedChoices)
    — Can only vote once per election
    — Weight = GovernanceWeight.getVotingWeight(msg.sender)
    — Stores ranked ballot

  tallyAndSeat(uint64 electionId)
    — Runs ranked-choice instant runoff (IRV) algorithm
    — Eliminates lowest-weighted candidate each round
    — Top N seated (calls CouncilManager.seatMembers)
    — Quorum check: 15% of active participants

Upgrade: UUPS proxy

Gas concern: IRV on-chain is expensive for >20 candidates.
  Mitigation: Cap candidates at 21 per election.
  Alternative for future: off-chain tally with ZK proof verification.
```

**Key decision:** On-chain IRV with candidate cap of 21. This keeps gas under 2M for tally.

**Alternative considered:** Off-chain tally with optimistic verification (submit result, challenge period). Deferred to Phase 3 — on-chain is simpler, more transparent, and sufficient for early council sizes.

### 3.4 CouncilManager.sol

**Purpose:** Central role assignment. Tracks who sits on which council, enforces terms and cooldowns.

```
Storage:
  struct CouncilSeat {
    address holder;
    uint8 domain;
    uint8 cohort;
    uint64 seatedAt;
    uint64 termEndsAt;
    uint8 consecutiveTerms;
    bool isActive;
  }

  struct RecallPetition {
    uint64 petitionId;
    address target;
    uint8 domain;
    uint256 signatureCount;
    uint64 petitionStart;
    uint64 voteDeadline;
    uint256 votesFor;
    uint256 votesAgainst;
    bool executed;
  }

  // 5 domains × 7 seats = 35 council seats
  // 5 domains × 3 stewards = 15 steward seats
  // 5 guardians ecosystem-wide
  mapping(uint8 => CouncilSeat[7]) councilSeats;
  mapping(uint8 => CouncilSeat[3]) stewardSeats;
  CouncilSeat[5] guardianSeats;

  mapping(address => uint64) cooldownEnds;  // Per-identity cooldown tracker
  mapping(address => uint8) currentSeatDomain;  // Which domain they're on (0 = none)

Key functions:
  seatMembers(uint8 domain, uint8 cohort, address[] winners)
    — Only callable by ElectionEngine after tally
    — Re-verifies DPC at seating time
    — Sets term end (90/180/365 days)
    — Emits MemberSeated events

  endTerm(uint8 domain, uint8 cohort)
    — Callable by anyone after term expires
    — Sets cooldown for outgoing members
    — Triggers new election via ElectionEngine

  recall(address target, uint8 domain)
    — Starts recall petition
    — Needs 10% of active participants to sign
    — 66% threshold to remove

  hasRole(address identity, uint8 role) → bool
    — Real-time check: is this identity currently a Council Member / Steward / Guardian?
    — Used by other contracts for access control

  getRoleCapabilities(uint8 role) → uint256
    — Returns capability bitmap for the role
    — Council Member: propose, execute, review
    — Steward: approve emergency, review performance, propose amendments
    — Guardian: veto (subject to 14-day community override)

Upgrade: UUPS proxy
```

### 3.5 EmergencyPower.sol (Phase 2)

**Purpose:** Grants temporary elevated access. Hard 72h expiry.

```
Storage:
  struct EmergencyGrant {
    address grantee;
    uint64 grantedAt;
    uint64 expiresAt;          // Always grantedAt + 72 hours. IMMUTABLE.
    bytes32 reason;            // IPFS hash of justification
    bool ratified;             // Community ratified within window?
  }

Key design:
  - expiresAt is computed as block.timestamp + 72h at grant time
  - No extend() function exists. Cannot be added via upgrade (constitutional).
  - Check: block.timestamp >= expiresAt → revert("EXPIRED")
  - Grant requires 2-of-3 Stewards from the affected domain

Upgrade: NOT upgradeable. Deployed as plain contract. No proxy, no admin key.
```

### 3.6 CartelDetector.sol (Phase 2)

**Purpose:** Stores peer review graph, accepts oracle-verified cartel flags.

```
Approach: Hybrid on-chain/off-chain.
  - Review graph edges stored on-chain (reviewer → reviewed, score, timestamp)
  - Clustering analysis runs off-chain (too expensive on-chain)
  - Oracle submits cartel flag with proof (Merkle root of review subgraph)
  - On-chain: verify Merkle proof, apply penalty, start appeal window

Key functions:
  recordReview(address reviewer, address reviewed, uint8 score)
  flagCartel(address[] members, bytes32 proofRoot, bytes proof)
  appealFlag(address appellant, bytes32 evidence)
  resolvePenalty(address identity)  // After appeal window

Upgrade: UUPS proxy
```

### 3.7 FounderSunset.sol (Phase 2)

**Purpose:** Immutable phase transition tracker.

```
Storage:
  uint64 public immutable deployedAt;
  uint64 public constant PHASE_1_OFFSET = 180 days;   // 6 months
  uint64 public constant PHASE_2_OFFSET = 540 days;   // 18 months

Key functions:
  currentPhase() → uint8
    — 0 if block.timestamp < deployedAt + PHASE_1_OFFSET
    — 1 if block.timestamp < deployedAt + PHASE_2_OFFSET
    — 2 otherwise

  hasVeto(address founder) → bool
    — True only in Phase 0 and Phase 1
    — False after Phase 2 (permanent, irreversible)

Upgrade: NOT upgradeable. No proxy, no admin, no selfdestruct.
Constructor sets deployedAt = block.timestamp. Constants are compile-time.
```

---

## 4. Dependency Graph

```
                    ┌─────────────┐
                    │ DPCRegistry │ ← Foundation (Phase 1)
                    └──────┬──────┘
                           │
                    ┌──────▼──────────┐
                    │GovernanceWeight  │ ← Reads DPC (Phase 1)
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │ ElectionEngine  │ ← Uses Weight for voting (Phase 1)
                    └──────┬──────────┘
                           │
                    ┌──────▼──────────┐
                    │ CouncilManager  │ ← Seats winners (Phase 1)
                    └─────┬─────┬─────┘
                          │     │
              ┌───────────▼┐   ┌▼────────────┐
              │EmergencyPow│   │CartelDetector│ ← Phase 2
              └────────────┘   └─────────────┘

              ┌──────────────┐
              │FounderSunset │ ← Phase 2 (independent)
              └──────────────┘
```

---

## 5. Key Design Decisions

| Decision | Chosen | Why | Rejected Alternative |
|----------|--------|-----|---------------------|
| Framework | Foundry | Faster tests, native fuzz, industry standard for governance | Hardhat (slower, JS-based) |
| Solc version | 0.8.24 | Latest stable, built-in overflow checks | 0.8.20 (misses custom errors improvements) |
| Decay model | Lazy eval at read | Saves gas, only computes when needed | Keeper-based periodic (expensive) |
| IRV tally | On-chain, capped 21 candidates | Transparent, verifiable, sufficient for early scale | Off-chain + ZK proof (complex, Phase 3) |
| Proxy pattern | UUPS for operational, none for constitutional | Operational needs evolve; EmergencyPower/FounderSunset must be permanent | Transparent proxy (higher gas per call) |
| Score precision | uint128 with 18 decimals | Prevents rounding in decay math | uint256 (wasteful for scores) |
| Identity binding | address (wallet) | ONEON identity maps to wallet via `oneon_identities.wallet_address` | DID (not on-chain yet) |
| VRF (sortition) | Deferred to Phase 2 | Mev hasn't confirmed sortition; Chainlink VRF adds complexity | Ship with VRF from day 1 |
| Gas optimization | Optimizer 200 runs | Balance between deploy cost and runtime cost | 10000 runs (expensive deploy) |

---

## 6. Integration with Memory API

The contracts need an off-chain oracle to bridge DPC scores from Otto's DB to on-chain.

```
ORACLE BRIDGE FLOW:

  sos_contributions (DB)
    → DPC calculator (Python, otto/memory/sos/)
      → Score aggregator (batch every 6h)
        → Oracle signer (authorized VALIDATOR_ROLE key)
          → DPCRegistry.batchUpdateScores(addresses, scores, types)

  This is a ONE-WAY bridge: DB → chain. The chain is the sink, not the source.
  DB remains authoritative for contribution records.
  Chain becomes authoritative for governance actions (votes, elections, role assignments).
```

**New Memory API endpoint needed:**
- `GET /sos/dpc-export` — Returns current DPC scores for all identities with wallet addresses
- Used by oracle bridge to batch-update on-chain registry

---

## 7. Implementation Plan

### Phase 1: Core Governance (4 contracts)

| Step | What | Files | Est. |
|------|------|-------|------|
| 1 | Init Foundry project, OpenZeppelin deps, foundry.toml | Project scaffold | $0.50 |
| 2 | DPCMath.sol library (sqrt, decay, fixed-point) | src/libraries/DPCMath.sol + test | $1.50 |
| 3 | IDPCRegistry interface + DPCRegistry.sol | src/interfaces/ + src/core/ + test | $2.00 |
| 4 | GovernanceWeight.sol | src/core/ + test | $1.00 |
| 5 | RankedChoice.sol library (IRV algorithm) | src/libraries/ + test | $2.00 |
| 6 | ElectionEngine.sol | src/core/ + test | $2.50 |
| 7 | CouncilManager.sol | src/core/ + test | $2.50 |
| 8 | Integration tests (full rotation cycle) | test/integration/ | $1.50 |
| 9 | Deployment script | script/DeployPhase1.s.sol | $0.50 |

**Phase 1 total: ~$14.00**

### Phase 2: Anti-Capture + Constitutional (3 contracts)

| Step | What | Est. |
|------|------|------|
| 10 | EmergencyPower.sol | $1.00 |
| 11 | CartelDetector.sol (hybrid on/off-chain) | $3.00 |
| 12 | FounderSunset.sol | $0.50 |
| 13 | Full anti-capture test suite | $2.00 |

**Phase 2 total: ~$6.50**

### Phase 3: Bridge + Frontend (deferred)

| Step | What | Est. |
|------|------|------|
| 14 | DPC oracle bridge service | $3.00 |
| 15 | OMS governance dashboard | $5.00 |
| 16 | Sortition VRF integration (if approved) | $2.00 |

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| IRV gas exceeds block limit | Medium | Candidate cap at 21. Fuzz test gas at limits. Phase 3: ZK tally. |
| DPC oracle manipulation | High | Multi-sig oracle, on-chain dispute window, score rate-limiting. |
| Identity Sybil attacks | High | Sybil detection in eligibility check. Not solving Sybil in contracts — that's an oracle/identity-layer problem. |
| UUPS upgrade hijack | Medium | OpenZeppelin UUPSUpgradeable with timelock + multi-sig. Upgrade requires Protocol council + 7-day vote. |
| No ONEON identity on-chain yet | Blocking | Phase 1 uses raw addresses. Phase 2 migrates to ONEON DID when available. Interface stays stable. |
| Polygon zkEVM compatibility | Low | All contracts use standard EVM opcodes. No PUSH0 (0.8.24 default target is Shanghai). |
| Score precision overflow | Low | uint128 with 18 decimals: max 3.4×10^20 — more than enough. Fuzz tests cover edge cases. |

---

## 9. Security Considerations

- **All contracts get fuzz-tested** via Foundry's native fuzzer (min 10,000 runs per function)
- **Reentrancy:** No ETH transfers in core contracts. CEI pattern where state is modified.
- **Access control:** OpenZeppelin AccessControlUpgradeable for UUPS contracts
- **Timelock:** All upgrades go through OZ TimelockController (48h minimum)
- **Audit:** Phase 1 should be audited before mainnet deployment. The Blockchain Security Auditor agent handles internal audit; external audit for mainnet.
- **Constitutional contracts (EmergencyPower, FounderSunset):** No proxy, no admin, no selfdestruct, no delegatecall. These are immutable by design.

---

## 10. Deployment Strategy

```
1. Local: forge test (full suite including fuzz)
2. Testnet: Deploy to Polygon zkEVM Cardona testnet
   - Verify contracts on Polygonscan
   - Run integration tests against testnet
   - Seed with test DPC scores
3. Staging: Deploy with real ONEON test identities
   - Run mock election cycle end-to-end
   - Verify gas costs match estimates
4. Mainnet: Deploy Phase 1 contracts
   - Transfer admin to timelock multi-sig
   - Verify all proxies point correctly
```

---

*The river has no king. The contracts are the riverbed — shaping the flow without controlling it.*

*Architecture by Otto | Based on OPRLP design doc (2026-03-27)*

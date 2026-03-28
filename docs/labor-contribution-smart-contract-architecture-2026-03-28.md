# Smart Contract Architecture: Labor & Contribution Tracking
## Detailed Contract Design, Interface Specs, and Contribution Flows

*Authored by Otto (Solidity Engineer Agent) | 2026-03-28 | Status: Architecture Complete*
*Builds on: On-Chain Labor Contribution & Governance Framework (same date)*

---

## 1. System Overview

Six contracts deployed on Polygon zkEVM, extending the OPRLP foundation. The system translates physical labor into verifiable on-chain equity and governance rights without recreating employer-employee dynamics.

```
DEPLOYMENT TOPOLOGY:

  Polygon zkEVM (L2)
  ├── LaborAttestation.sol      [UUPS Proxy]    Phase 1
  ├── ContributionEquity.sol    [Immutable]     Phase 1
  ├── VestingEngine.sol         [UUPS Proxy]    Phase 1
  ├── SiteOracle.sol            [UUPS Proxy]    Phase 2
  ├── SkillBountyRegistry.sol   [UUPS Proxy]    Phase 2
  └── EquityTreasury.sol        [Immutable]     Phase 3

  External Dependencies:
  ├── OPRLP DPCRegistry         (reads/writes DPC scores)
  ├── OPRLP GovernanceWeight    (recomputes after DPC update)
  └── ONEON Identity            (contributor identity verification)
```

---

## 2. Contract Architecture

### 2.1 LaborAttestation.sol — Core Attestation Engine

**Purpose:** Records contributions, manages attestation quorum, triggers DPC updates and CET minting upon verification.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract LaborAttestation is UUPSUpgradeable, AccessControlUpgradeable {

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    enum ContributionType { PHY, MAT, SKL, OPS, EDU, COM, DIG }
    enum Status { PENDING, VERIFIED, DISPUTED, REJECTED }
    enum AttesterRole { PEER, SITE_ORACLE, REVIEWER }

    struct Contribution {
        bytes32 id;
        address contributor;        // ONEON identity
        ContributionType cType;
        uint32 hours;               // hours × 100 (centihours)
        uint32 startTime;
        uint32 endTime;
        bytes32 evidenceHash;       // IPFS CID
        bytes32 siteId;             // 0x0 for remote/digital
        bytes32 projectId;          // which project this serves
        Status status;
        uint32 dpcDelta;            // computed on verification
        uint32 challengeDeadline;   // timestamp
    }

    struct Attestation {
        address attester;
        AttesterRole role;
        uint32 timestamp;
        uint8 score;                // 1-100 quality
        uint128 stakeAmount;        // CET staked
        bool slashed;
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    // Core storage
    mapping(bytes32 => Contribution) public contributions;
    mapping(bytes32 => Attestation[]) public attestations;

    // Anti-collusion: attester → contributor → count in rolling 30d window
    mapping(address => mapping(address => uint32)) public attestationCount;
    mapping(address => mapping(address => uint32)) public lastAttestationReset;

    // Quorum config per contribution type
    mapping(ContributionType => uint8) public requiredAttestations;

    // Daily cap tracking: contributor → date → hours claimed
    mapping(address => mapping(uint32 => uint32)) public dailyHours;
    uint32 public constant MAX_DAILY_HOURS = 1200; // 12.00 hours

    // Rotating attester limit
    uint8 public constant MAX_ATTESTATIONS_PER_PAIR = 3; // per 30 days
    uint32 public constant CHALLENGE_WINDOW = 7 days;

    // External contracts
    address public dpcRegistry;
    address public contributionEquity;
    address public vestingEngine;
    address public siteOracle;

    // DPC weight mappings (type → [Is, Ec, Rw] × 100)
    mapping(ContributionType => uint16[3]) public dpcWeights;

    // Type multipliers × 100
    mapping(ContributionType => uint16) public typeMultipliers;

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event ContributionSubmitted(
        bytes32 indexed id,
        address indexed contributor,
        ContributionType cType,
        bytes32 indexed projectId,
        uint32 hours
    );
    event AttestationRecorded(
        bytes32 indexed contributionId,
        address indexed attester,
        AttesterRole role,
        uint8 score
    );
    event ContributionVerified(
        bytes32 indexed id,
        address indexed contributor,
        uint32 dpcDelta,
        uint256 cetMinted
    );
    event ContributionDisputed(
        bytes32 indexed id,
        address indexed challenger,
        string reason
    );
    event ContributionRejected(bytes32 indexed id);
    event AttesterSlashed(
        bytes32 indexed contributionId,
        address indexed attester,
        uint128 slashedAmount
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Contributor submits a contribution claim
    /// @param cType Contribution category (PHY, MAT, SKL, etc.)
    /// @param hours Centihours (hours × 100)
    /// @param evidenceHash IPFS CID of evidence bundle
    /// @param siteId Site identifier (0x0 for remote work)
    /// @param projectId Project this contribution serves
    function submitContribution(
        ContributionType cType,
        uint32 hours,
        bytes32 evidenceHash,
        bytes32 siteId,
        bytes32 projectId
    ) external returns (bytes32 contributionId);

    /// @notice Peer or oracle records an attestation
    /// @param contributionId The contribution being attested
    /// @param role Attester role (PEER, SITE_ORACLE, REVIEWER)
    /// @param score Quality rating 1-100
    /// @param stakeAmount CET staked on this attestation
    function recordAttestation(
        bytes32 contributionId,
        AttesterRole role,
        uint8 score,
        uint128 stakeAmount
    ) external;

    /// @notice Checks quorum and finalizes verification
    /// @dev Called automatically when attestation count meets threshold,
    ///      or manually after challenge window expires
    function verifyContribution(bytes32 contributionId) external;

    /// @notice Challenge a contribution during the 7-day window
    /// @param contributionId Contribution to challenge
    /// @param evidenceHash IPFS CID of counter-evidence
    /// @param reason Human-readable reason
    function disputeContribution(
        bytes32 contributionId,
        bytes32 evidenceHash,
        string calldata reason
    ) external;

    /// @notice Batch-submit contributions from off-chain processor
    /// @dev Only callable by authorized batch processor role
    /// @param ids Contribution IDs
    /// @param contributors ONEON addresses
    /// @param types Contribution types
    /// @param hours Centihours array
    /// @param evidenceHashes Evidence CIDs
    /// @param siteId Common site ID for batch
    /// @param projectId Common project ID for batch
    function batchSubmitContributions(
        bytes32[] calldata ids,
        address[] calldata contributors,
        ContributionType[] calldata types,
        uint32[] calldata hours,
        bytes32[] calldata evidenceHashes,
        bytes32 siteId,
        bytes32 projectId
    ) external; // onlyRole(BATCH_PROCESSOR_ROLE)

    // ═══════════════════════════════════════════
    //           INTERNAL LOGIC
    // ═══════════════════════════════════════════

    /// @dev Computes DPC delta from verified contribution
    function _computeDpcDelta(
        ContributionType cType,
        uint32 hours,
        uint8 avgScore,
        address contributor
    ) internal view returns (uint32 delta, uint16[3] memory components);

    /// @dev Enforces rotating attester limits
    function _checkAttesterEligibility(
        address attester,
        address contributor
    ) internal;

    /// @dev Enforces daily hour cap
    function _checkDailyCap(
        address contributor,
        uint32 hours
    ) internal;
}
```

**Key Design Decisions:**
- `UUPS` upgradeable: attestation rules will evolve as the system matures
- `centihours` (hours × 100): avoids floating point, gives 2 decimal precision
- Batch submission: gas efficiency for daily site batches (~$0.50 vs $5-10 individual)
- Challenge window baked into struct: no separate mapping needed

### 2.2 ContributionEquity.sol — Soulbound ERC-1155

**Purpose:** Non-transferable equity tokens. Each token ID = one project. Balance = verified contribution score.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC1155/ERC1155.sol";

contract ContributionEquity is ERC1155 {

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    // Only LaborAttestation can mint
    address public immutable laborAttestation;

    // Project registry
    struct Project {
        string name;
        bytes32 siteId;
        uint256 totalCET;           // total minted for this project
        uint256 createdAt;
        bool active;
    }

    // tokenId → Project
    mapping(uint256 => Project) public projects;

    // tokenId → contributor → first contribution timestamp
    mapping(uint256 => mapping(address => uint256)) public firstContribution;

    // Anti-dilution: early contributor bonus multiplier
    // First 10% of project threshold hours get 1.5x CET
    // Next 20% get 1.2x
    // Remaining get 1.0x
    struct DilutionBracket {
        uint256 thresholdPct;       // percentage of project hours
        uint16 multiplier;          // × 100 (150 = 1.5x)
    }
    DilutionBracket[] public dilutionBrackets;

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event ProjectRegistered(uint256 indexed tokenId, string name, bytes32 siteId);
    event EquityMinted(
        uint256 indexed tokenId,
        address indexed contributor,
        uint256 amount,
        uint256 rawAmount,          // before anti-dilution multiplier
        uint16 bracketMultiplier
    );
    event RevenueDistributed(
        uint256 indexed tokenId,
        uint256 totalAmount,
        uint256 holderShare,
        uint256 maintenanceShare,
        uint256 treasuryShare
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Register a new project (creates a new token ID)
    /// @param name Human-readable project name
    /// @param siteId Associated site ID
    /// @return tokenId The ERC-1155 token ID for this project
    function registerProject(
        string calldata name,
        bytes32 siteId
    ) external returns (uint256 tokenId);

    /// @notice Mint CET for a verified contribution
    /// @dev Only callable by LaborAttestation contract
    /// @param to Contributor address
    /// @param tokenId Project token ID
    /// @param rawAmount Base CET amount (before dilution bracket)
    function mint(
        address to,
        uint256 tokenId,
        uint256 rawAmount
    ) external; // onlyLaborAttestation

    /// @notice Get a contributor's equity percentage in a project
    function equityShare(
        uint256 tokenId,
        address contributor
    ) external view returns (uint256 share, uint256 total);

    /// @notice Get all projects a contributor has equity in
    function contributorProjects(
        address contributor
    ) external view returns (uint256[] memory tokenIds);

    // ═══════════════════════════════════════════
    //          SOULBOUND ENFORCEMENT
    // ═══════════════════════════════════════════

    /// @dev Override: block all transfers (soulbound)
    function safeTransferFrom(
        address, address, uint256, uint256, bytes memory
    ) public pure override {
        revert("SOULBOUND");
    }

    /// @dev Override: block all batch transfers (soulbound)
    function safeBatchTransferFrom(
        address, address, uint256[] memory, uint256[] memory, bytes memory
    ) public pure override {
        revert("SOULBOUND");
    }

    /// @dev Override: block approvals (nothing to approve if no transfers)
    function setApprovalForAll(address, bool) public pure override {
        revert("SOULBOUND");
    }
}
```

**Anti-Dilution Mechanism:**
```
EARLY CONTRIBUTOR PROTECTION:

  Project: Tusita Island Resort
  Total estimated build: 200,000 hours

  Bracket 1 (first 10% = 20,000 hours):
    Contributors get 1.5x CET multiplier
    Alice works 100 hours → receives 150 CET (not 100)

  Bracket 2 (next 20% = 40,000 hours):
    Contributors get 1.2x CET multiplier

  Bracket 3 (remaining 70%):
    Contributors get 1.0x CET multiplier

  Result: Early contributors who took the risk of building
  from scratch earn proportionally more equity. Their CET
  cannot be diluted by later contributors — the multiplier
  is applied at mint time and baked into their balance.

  Why this works:
  - Alice's 150 CET is permanent (soulbound, never decreases)
  - Even as total CET grows, her percentage only dilutes
    naturally through more work being done
  - Her early-risk premium (1.5x) is already captured
  - No vesting cliff needed for early-risk compensation
```

### 2.3 VestingEngine.sol — Contribution-Weighted Vesting

**Purpose:** Revenue distribution rights vest based on sustained contribution, not calendar time.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract VestingEngine is UUPSUpgradeable {

    struct VestingSchedule {
        uint256 tokenId;            // project
        address contributor;
        uint256 totalCET;           // total CET earned
        uint256 vestedCET;          // how much has vested
        uint32 lastContribution;    // timestamp of last verified contribution
        uint32 totalVerifiedHours;  // cumulative verified hours
        uint32 projectThreshold;    // hours needed for full vest
        bool hardshipPause;         // DAO-approved pause
    }

    // contributor → tokenId → schedule
    mapping(address => mapping(uint256 => VestingSchedule)) public schedules;

    // Activity multiplier thresholds
    uint32 public constant ACTIVE_WINDOW = 30 days;
    uint32 public constant WARM_WINDOW = 60 days;
    uint32 public constant COOL_WINDOW = 90 days;

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Update vesting state when new CET is minted
    /// @dev Called by LaborAttestation after verification
    function onContributionVerified(
        address contributor,
        uint256 tokenId,
        uint256 cetAmount,
        uint32 verifiedHours
    ) external; // onlyLaborAttestation

    /// @notice Calculate current vested percentage
    /// @return vestedPct Percentage × 100 (10000 = 100%)
    function vestedPercentage(
        address contributor,
        uint256 tokenId
    ) external view returns (uint256 vestedPct);

    /// @notice DAO approves hardship pause for a contributor
    function approveHardshipPause(
        address contributor,
        uint256 tokenId
    ) external; // onlyRole(DAO_ROLE)

    /// @notice Resume vesting after hardship
    function resumeFromHardship(
        address contributor,
        uint256 tokenId
    ) external; // onlyRole(DAO_ROLE)

    // ═══════════════════════════════════════════
    //           VESTING CALCULATION
    // ═══════════════════════════════════════════

    /// @dev Activity multiplier based on recency of contribution
    /// @return multiplier × 100 (100 = 1.0x, 80 = 0.8x, etc.)
    function _activityMultiplier(
        uint32 lastContribution
    ) internal view returns (uint16 multiplier) {
        if (block.timestamp - lastContribution <= ACTIVE_WINDOW) return 100;
        if (block.timestamp - lastContribution <= WARM_WINDOW) return 80;
        if (block.timestamp - lastContribution <= COOL_WINDOW) return 50;
        return 0; // paused, not reset
    }

    /// @dev Core vesting formula
    /// vest = min(1.0, cumHours / threshold) × activityMultiplier
    function _computeVest(
        VestingSchedule storage s
    ) internal view returns (uint256);
}
```

### 2.4 SiteOracle.sol — Physical Site Bridge

**Purpose:** Receives off-chain attestation batches from edge devices (Raspberry Pi nodes on physical sites).

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract SiteOracle is UUPSUpgradeable {

    struct Site {
        bytes32 siteId;
        string name;
        bytes32 projectId;
        int64 latitude;             // × 1e6
        int64 longitude;            // × 1e6
        uint32 radiusMeters;        // GPS fence radius
        address[] authorizedOracles; // edge device signing keys
        bool active;
    }

    struct AttendanceBatch {
        bytes32 siteId;
        uint32 date;                // YYYYMMDD
        bytes32 merkleRoot;         // root of attendance records
        uint16 workerCount;
        address submittedBy;        // oracle address
        uint32 submittedAt;
    }

    mapping(bytes32 => Site) public sites;
    mapping(bytes32 => AttendanceBatch[]) public batches; // siteId → batches

    event SiteRegistered(bytes32 indexed siteId, string name, bytes32 indexed projectId);
    event AttendanceBatchSubmitted(
        bytes32 indexed siteId,
        uint32 indexed date,
        bytes32 merkleRoot,
        uint16 workerCount
    );
    event OracleAuthorized(bytes32 indexed siteId, address oracle);
    event OracleRevoked(bytes32 indexed siteId, address oracle);

    /// @notice Register a physical site
    function registerSite(
        bytes32 siteId,
        string calldata name,
        bytes32 projectId,
        int64 latitude,
        int64 longitude,
        uint32 radiusMeters
    ) external; // onlyRole(SITE_ADMIN_ROLE)

    /// @notice Submit daily attendance batch from edge device
    /// @param siteId Site identifier
    /// @param date Date as YYYYMMDD
    /// @param merkleRoot Merkle root of individual attendance records
    /// @param workerCount Number of workers in this batch
    /// @param signature Edge device signature over (siteId, date, merkleRoot)
    function submitAttendanceBatch(
        bytes32 siteId,
        uint32 date,
        bytes32 merkleRoot,
        uint16 workerCount,
        bytes calldata signature
    ) external;

    /// @notice Verify a worker was present on a given date
    /// @param siteId Site identifier
    /// @param date Date as YYYYMMDD
    /// @param worker Worker's ONEON address
    /// @param proof Merkle proof of attendance
    function verifyAttendance(
        bytes32 siteId,
        uint32 date,
        address worker,
        bytes32[] calldata proof
    ) external view returns (bool);
}
```

### 2.5 SkillBountyRegistry.sol — Gap-to-Skill Pipeline

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";

contract SkillBountyRegistry is UUPSUpgradeable {

    enum BountyStatus { OPEN, CLAIMED, IN_PROGRESS, COMPLETED, EXPIRED }

    struct SkillBounty {
        bytes32 id;
        bytes32 projectId;
        string skillRequired;       // e.g., "electrician", "plumber"
        uint8 contributionType;     // what type of work this enables
        uint256 cetReward;          // CET bonus on completion
        uint16 dpcBonusMultiplier;  // × 100 (150 = 1.5x on first 3 contributions)
        uint32 deadline;
        BountyStatus status;
        address claimant;
        address mentor;
        uint32 enrolledAt;
        uint32 completedAt;
    }

    mapping(bytes32 => SkillBounty) public bounties;
    bytes32[] public openBountyIds;

    // Redistribution pool funding
    address public equityTreasury;

    event BountyCreated(bytes32 indexed id, bytes32 indexed projectId, string skill);
    event BountyClaimed(bytes32 indexed id, address indexed claimant, address mentor);
    event BountyCompleted(bytes32 indexed id, address indexed claimant, uint256 cetReward);
    event BountyExpired(bytes32 indexed id);

    /// @notice Create a skill bounty (called by Intelligence Layer)
    function createBounty(
        bytes32 projectId,
        string calldata skillRequired,
        uint8 contributionType,
        uint256 cetReward,
        uint16 dpcBonusMultiplier,
        uint32 deadline
    ) external returns (bytes32 bountyId); // onlyRole(BOUNTY_CREATOR_ROLE)

    /// @notice Learner claims a bounty and is matched with a mentor
    function claimBounty(
        bytes32 bountyId,
        address mentor
    ) external;

    /// @notice Mark bounty as completed after skill verification
    /// @dev Requires multi-party attestation (mentor + 2 peers + oracle)
    function completeBounty(
        bytes32 bountyId
    ) external; // onlyRole(ATTESTATION_ENGINE_ROLE)
}
```

### 2.6 EquityTreasury.sol — Revenue Distribution

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract EquityTreasury {

    struct RevenuePool {
        uint256 tokenId;            // project
        uint256 totalDeposited;
        uint256 totalDistributed;
        uint256 maintenanceFund;
        uint256 lastDistribution;
    }

    // Revenue split (DAO-adjustable per project)
    struct RevenueSplit {
        uint16 holderPct;           // default 70% (min 50%)
        uint16 maintenancePct;      // default 20%
        uint16 ecosystemPct;        // default 10%
    }

    address public immutable contributionEquity;
    address public immutable vestingEngine;
    address public ecosystemTreasury;       // MY3YE treasury

    mapping(uint256 => RevenuePool) public pools;
    mapping(uint256 => RevenueSplit) public splits;

    // Agent tax redistribution
    uint16 public agentTaxRate;             // default 3000 (30%)
    struct RedistributionSplit {
        uint16 activeContributorsPct;       // default 50%
        uint16 skillBountiesPct;            // default 30%
        uint16 treasuryPct;                 // default 20%
    }
    RedistributionSplit public redistSplit;

    // Claim tracking: contributor → tokenId → last claimed epoch
    mapping(address => mapping(uint256 => uint256)) public lastClaimed;

    event RevenueDeposited(uint256 indexed tokenId, uint256 amount, address from);
    event RevenueDistributed(uint256 indexed tokenId, uint256 holderTotal);
    event ContributorClaimed(
        uint256 indexed tokenId,
        address indexed contributor,
        uint256 amount
    );
    event AgentTaxCollected(uint256 amount, uint256 toContributors, uint256 toBounties);

    /// @notice Deposit revenue for a project
    function depositRevenue(
        uint256 tokenId
    ) external payable;

    /// @notice Trigger distribution for a project (monthly)
    function distribute(uint256 tokenId) external;

    /// @notice Individual contributor claims their share
    /// @dev Share = (contributor CET / total CET) × vested% × holderPool
    function claim(uint256 tokenId) external;

    /// @notice Deposit agent tax from automated task completion
    function depositAgentTax() external payable;

    /// @notice Update revenue split (DAO governance)
    /// @dev holderPct must be >= 5000 (50%)
    function updateSplit(
        uint256 tokenId,
        uint16 holderPct,
        uint16 maintenancePct,
        uint16 ecosystemPct
    ) external; // onlyRole(DAO_ROLE)

    /// @notice No admin withdrawal — by design
    /// @dev There is intentionally no withdrawAll or emergencyWithdraw
    ///      Revenue only flows out through claim() proportional to CET
}
```

---

## 3. Interface Specifications

### 3.1 ILaborAttestation.sol

```solidity
interface ILaborAttestation {
    function submitContribution(
        uint8 cType, uint32 hours, bytes32 evidenceHash,
        bytes32 siteId, bytes32 projectId
    ) external returns (bytes32);

    function recordAttestation(
        bytes32 contributionId, uint8 role, uint8 score, uint128 stakeAmount
    ) external;

    function verifyContribution(bytes32 contributionId) external;

    function disputeContribution(
        bytes32 contributionId, bytes32 evidenceHash, string calldata reason
    ) external;

    function batchSubmitContributions(
        bytes32[] calldata ids, address[] calldata contributors,
        uint8[] calldata types, uint32[] calldata hours,
        bytes32[] calldata evidenceHashes, bytes32 siteId, bytes32 projectId
    ) external;

    function getContribution(bytes32 id) external view returns (
        address contributor, uint8 cType, uint32 hours, uint8 status,
        uint32 dpcDelta, uint32 challengeDeadline
    );

    function getAttestations(bytes32 contributionId) external view returns (
        address[] memory attesters, uint8[] memory roles,
        uint8[] memory scores, uint32[] memory timestamps
    );

    function contributorStats(address contributor) external view returns (
        uint256 totalContributions, uint256 verified, uint256 disputed,
        uint32 totalHours, uint32 avgScore
    );
}
```

### 3.2 IContributionEquity.sol

```solidity
interface IContributionEquity {
    function registerProject(string calldata name, bytes32 siteId)
        external returns (uint256 tokenId);

    function mint(address to, uint256 tokenId, uint256 rawAmount) external;

    function equityShare(uint256 tokenId, address contributor)
        external view returns (uint256 share, uint256 total);

    function contributorProjects(address contributor)
        external view returns (uint256[] memory tokenIds);

    function projectInfo(uint256 tokenId)
        external view returns (string memory name, uint256 totalCET, bool active);
}
```

### 3.3 IVestingEngine.sol

```solidity
interface IVestingEngine {
    function onContributionVerified(
        address contributor, uint256 tokenId, uint256 cetAmount, uint32 verifiedHours
    ) external;

    function vestedPercentage(address contributor, uint256 tokenId)
        external view returns (uint256 vestedPct);

    function approveHardshipPause(address contributor, uint256 tokenId) external;
    function resumeFromHardship(address contributor, uint256 tokenId) external;

    function scheduleInfo(address contributor, uint256 tokenId)
        external view returns (
            uint256 totalCET, uint256 vestedCET, uint32 lastContribution,
            uint32 totalVerifiedHours, bool hardshipPause
        );
}
```

### 3.4 ISiteOracle.sol

```solidity
interface ISiteOracle {
    function registerSite(
        bytes32 siteId, string calldata name, bytes32 projectId,
        int64 latitude, int64 longitude, uint32 radiusMeters
    ) external;

    function submitAttendanceBatch(
        bytes32 siteId, uint32 date, bytes32 merkleRoot,
        uint16 workerCount, bytes calldata signature
    ) external;

    function verifyAttendance(
        bytes32 siteId, uint32 date, address worker, bytes32[] calldata proof
    ) external view returns (bool);

    function siteInfo(bytes32 siteId)
        external view returns (string memory name, bytes32 projectId, bool active);
}
```

### 3.5 ISkillBountyRegistry.sol

```solidity
interface ISkillBountyRegistry {
    function createBounty(
        bytes32 projectId, string calldata skillRequired, uint8 contributionType,
        uint256 cetReward, uint16 dpcBonusMultiplier, uint32 deadline
    ) external returns (bytes32 bountyId);

    function claimBounty(bytes32 bountyId, address mentor) external;
    function completeBounty(bytes32 bountyId) external;

    function openBounties() external view returns (bytes32[] memory);
    function bountyInfo(bytes32 id) external view returns (
        bytes32 projectId, string memory skill, uint256 cetReward,
        uint8 status, address claimant, address mentor
    );
}
```

### 3.6 IEquityTreasury.sol

```solidity
interface IEquityTreasury {
    function depositRevenue(uint256 tokenId) external payable;
    function distribute(uint256 tokenId) external;
    function claim(uint256 tokenId) external;
    function depositAgentTax() external payable;

    function claimable(uint256 tokenId, address contributor)
        external view returns (uint256 amount);

    function poolInfo(uint256 tokenId)
        external view returns (
            uint256 totalDeposited, uint256 totalDistributed,
            uint256 maintenanceFund, uint256 lastDistribution
        );
}
```

---

## 4. Cross-Contract Interaction Flow

```
CONTRIBUTION LIFECYCLE (on-chain):

  ┌──────────────┐     submitContribution()     ┌──────────────────┐
  │  Contributor  │ ──────────────────────────► │ LaborAttestation │
  │  (ONEON ID)  │                              │                  │
  └──────────────┘                              │  stores PENDING  │
                                                 └────────┬─────────┘
  ┌──────────────┐     recordAttestation()               │
  │  Peer 1      │ ─────────────────────────────────────►│
  │  Peer 2      │ ─────────────────────────────────────►│
  └──────────────┘                                        │
  ┌──────────────┐     recordAttestation(SITE_ORACLE)    │
  │  SiteOracle  │ ─────────────────────────────────────►│
  └──────────────┘                                        │
                                                          │ quorum met (2-of-3)
                                                          ▼
                                                 verifyContribution()
                                                          │
                              ┌────────────────────────────┼──────────────────┐
                              │                            │                  │
                              ▼                            ▼                  ▼
                     ┌─────────────────┐    ┌──────────────────┐   ┌─────────────┐
                     │  DPCRegistry    │    │ ContributionEquity│   │VestingEngine│
                     │  .addScore()    │    │  .mint()          │   │ .onVerified │
                     │                 │    │  (soulbound CET)  │   │             │
                     └────────┬────────┘    └──────────────────┘   └─────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │GovernanceWeight │
                     │  .recompute()   │
                     └─────────────────┘

REVENUE FLOW:

  Project Revenue ──► EquityTreasury.depositRevenue()
                              │
                              ├── 70% → Holder Pool
                              │         └── claim() → (CET share × vested%) per contributor
                              ├── 20% → Maintenance Fund (project-governed)
                              └── 10% → MY3YE Ecosystem Treasury

  Agent Task Bounty ──► EquityTreasury.depositAgentTax()
                              │ (30% of bounty)
                              ├── 50% → Active contributor redistribution
                              ├── 30% → SkillBountyRegistry funding
                              └── 20% → Treasury
```

---

## 5. Multi-Project Contribution Tracking

```
MULTI-PROJECT ARCHITECTURE:

  One contributor can work across multiple projects simultaneously.
  CET is scoped per project (ERC-1155 token IDs).

  Example — Alice contributes to 3 projects:

  Project                 Token ID    Alice's CET    Equity %
  ──────────────────────  ──────────  ─────────────  ────────
  Tusita Island Resort    0xabc...    5,000          5.0%
  Ottolabs Factory #1     0xdef...    2,000          8.0%
  Community Farm          0x123...    800            12.0%

  Alice's DPC is UNIFIED across all projects:
    Total DPC = sum of all verified contributions (any project)
    Governance weight applies system-wide (OPRLP)

  Alice's REVENUE is PER-PROJECT:
    Tusita pays her 5% of holder pool
    Factory pays her 8% of holder pool
    Farm pays her 12% of holder pool

  No double-counting:
    Hours at Tusita don't count toward Factory CET
    But all hours count toward unified DPC score

  Cross-project mobility:
    Alice can stop contributing to Tusita, start at Factory
    Her Tusita CET stays (soulbound, historical fact)
    Her Tusita vesting pauses (activity multiplier decays)
    Her Factory vesting activates (new contributions)
    Her DPC continues accruing from Factory work
```

---

## 6. Plain-English Contribution Flow

### For Non-Crypto Workers: How Your Work Becomes Your Equity

```
╔══════════════════════════════════════════════════════════════╗
║              HOW IT WORKS — PLAIN ENGLISH                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  STEP 1: SHOW UP                                             ║
║  ─────────────────                                           ║
║  Arrive at any build site (Tusita, Ottolabs, community       ║
║  farm). No resume needed. No interview.                      ║
║                                                              ║
║  STEP 2: GET YOUR ID                                         ║
║  ────────────────────                                        ║
║  Create your digital identity on your phone (5 minutes).     ║
║  This is your permanent worker ID — like a passport but      ║
║  you own it, nobody can take it away.                        ║
║                                                              ║
║  STEP 3: DO THE WORK                                         ║
║  ────────────────────                                        ║
║  Build, farm, teach, manage, whatever your skills are.       ║
║  At the end of each day, log what you did in the app.        ║
║  Take a photo if it's physical work.                         ║
║                                                              ║
║  STEP 4: GET VERIFIED                                        ║
║  ─────────────────────                                       ║
║  Two people who worked alongside you confirm:                ║
║  "Yes, Alice was here. Yes, she did this work."              ║
║  The site's check-in system also confirms you were there.    ║
║  No single boss decides — your peers verify.                 ║
║                                                              ║
║  STEP 5: EARN YOUR SHARE                                     ║
║  ─────────────────────────                                   ║
║  Once verified, you receive Equity Points for that project.  ║
║  These points represent YOUR share of what you helped build. ║
║  They can never be taken from you. They can never be sold.   ║
║  They are yours, forever.                                    ║
║                                                              ║
║  STEP 6: GET PAID                                            ║
║  ────────────────                                            ║
║  When the project makes money (hotel revenue, farm sales,    ║
║  factory output), you get your percentage automatically.     ║
║  Built 5% of the resort? You get 5% of the revenue.         ║
║  Every month. For as long as it operates.                    ║
║                                                              ║
║  STEP 7: HAVE A SAY                                          ║
║  ─────────────────                                           ║
║  Your contribution earns you voting rights.                  ║
║  The more you contribute, the more say you have in           ║
║  how the project is run. Same system whether you're          ║
║  a builder, a teacher, or a programmer.                      ║
║                                                              ║
║  THE KEY DIFFERENCE:                                         ║
║  In a normal job, you work and the company keeps the value.  ║
║  Here, you work and YOU keep the value — permanently.        ║
║  Nobody above you captures your surplus.                     ║
║  Nobody can buy your equity out from under you.              ║
║  Nobody can fire you from your own ownership stake.          ║
╚══════════════════════════════════════════════════════════════╝
```

### Worker FAQ

**Q: Do I need to understand crypto?**
A: No. You log your work in an app. You get verified by your peers. You see your equity and earnings in the app. The blockchain part happens behind the scenes — you never need to touch a wallet, send a transaction, or understand gas fees.

**Q: What if I stop working for a while?**
A: Your equity stays. It's yours forever — you built that. Your revenue share might pause if you're inactive for 90+ days, but it resumes the day you come back and do another shift. If you're sick or dealing with a family emergency, the community can approve a pause so nothing changes.

**Q: What if I work on multiple projects?**
A: You earn separate equity in each project. Work on the farm in the morning and the resort in the afternoon — you get equity in both. Your overall governance rights grow from all your work combined.

**Q: How is my work rated?**
A: Your coworkers rate the quality of your contribution (1-100). Higher quality = more equity per hour. The average of your peer ratings determines your score. No single manager decides.

**Q: Can someone with money just buy more equity than me?**
A: No. Equity cannot be bought, sold, or traded. The only way to get it is to do the work. A billionaire and a day laborer earn equity the same way — by contributing.

**Q: What happens if someone lies about their work?**
A: Three safeguards: (1) Two of your peers must independently confirm your work, (2) the site's check-in system verifies your presence, (3) anyone can challenge a claim within 7 days with evidence. Liars lose their stake and get flagged.

---

## 7. Deployment Plan

### Phase 1: Core (Estimated: $15-20 gas)
1. Deploy `ContributionEquity` (immutable)
2. Deploy `LaborAttestation` (UUPS proxy)
3. Deploy `VestingEngine` (UUPS proxy)
4. Wire contracts: LaborAttestation → ContributionEquity, VestingEngine, DPCRegistry
5. Register first project (e.g., "Tusita Island Resort Phase 1")
6. Set quorum rules and DPC weights

### Phase 2: Site Infrastructure ($8-12 gas)
1. Deploy `SiteOracle` (UUPS proxy)
2. Deploy `SkillBountyRegistry` (UUPS proxy)
3. Register first physical site with GPS fence
4. Authorize first edge device (Raspberry Pi oracle)
5. Wire SiteOracle → LaborAttestation

### Phase 3: Revenue ($5-8 gas)
1. Deploy `EquityTreasury` (immutable)
2. Configure revenue splits per project
3. Set agent tax rate (30%)
4. Wire EquityTreasury → ContributionEquity, VestingEngine

### Dependency Chain
```
OPRLP DPCRegistry (must exist)
  └── LaborAttestation
        ├── ContributionEquity
        ├── VestingEngine
        ├── SiteOracle
        └── SkillBountyRegistry
              └── EquityTreasury (depends on all above)
```

---

## 8. Security Considerations

| Risk | Mitigation |
|------|-----------|
| Sybil attacks (fake identities) | ONEON identity required; one identity per person |
| Collusion rings | Rotating attesters, temporal separation, staking, anomaly detection |
| Oracle compromise | Multi-oracle support per site; degraded mode uses peer attestation |
| Front-running attestations | Attestation scores committed as hashes, revealed after window |
| Reentrancy on claims | Checks-effects-interactions pattern; ReentrancyGuard on EquityTreasury |
| Proxy upgrade attacks | UUPS with 48h timelock + multi-sig (Council) on upgrade function |
| Integer overflow on CET | Solidity 0.8+ built-in overflow checks; uint256 for balances |

---

## 9. Gas Optimization Notes

- **Batch processing**: Daily batches reduce individual tx overhead by ~90%
- **Merkle proofs for attendance**: Store root on-chain, verify individually when needed
- **Packed structs**: Contribution struct uses uint32/uint8 where possible (single slot packing)
- **ERC-1155 over ERC-721**: Single contract for all projects, efficient batch operations
- **Polygon zkEVM**: L2 gas costs ~100x cheaper than Ethereum mainnet

---

## 10. Decision Escalated to Mev

[NEEDS_MEV_INPUT]
{"question": "Should CET holders get direct project-level revenue governance (vote on maintenance fund allocation, revenue split adjustments), or should revenue governance flow through OPRLP Treasury council only?", "options": ["Direct: CET holders vote on their project's revenue allocation using sqrt(CET) weighting — more decentralized but adds governance complexity per project", "Council: Revenue governance flows through OPRLP Treasury council (elected via DPC) — simpler but adds a layer between workers and their project's money", "Hybrid: CET holders vote on project-level ops (maintenance, expansion) while OPRLP council handles cross-project allocation and ecosystem treasury — recommended approach"], "recommendation": 2, "context": "The architecture doc recommends hybrid. Direct governance gives workers sovereignty over what they built. Council governance prevents fragmentation. Hybrid gives workers control over their project while keeping ecosystem-level coordination through elected representatives."}
[/NEEDS_MEV_INPUT]

Proceeding with hybrid approach as the default in this architecture.

# On-Chain Architecture: The Live Organism
## Smart Contract & Tokenomics Architecture for the Programmable Otto Loop

*Authored by Otto (Solidity Engineer Agent) | 2026-03-28 | Status: Architecture Complete*
*Builds on: Core Value Loop Architecture, Labor & Contribution Smart Contract Architecture*
*Target chain: Polygon zkEVM (L2) — same as labor contracts*

---

## 1. Contract Topology

Six new contracts compose with the existing OPRLP + Labor Attestation stack to make the Otto Loop fully programmable on-chain.

```
DEPLOYMENT STACK:

  EXISTING (already designed, deployed or deployable):
  ├── DPCRegistry.sol           — DPC score storage
  ├── GovernanceWeight.sol      — sqrt(DPC) × activityMultiplier
  ├── LaborAttestation.sol      — multi-party attestation engine
  ├── ContributionEquity.sol    — soulbound CET (ERC-1155)
  ├── VestingEngine.sol         — contribution-weighted vesting
  ├── SiteOracle.sol            — physical site bridge
  ├── SkillBountyRegistry.sol   — gap-to-skill pipeline
  └── EquityTreasury.sol        — revenue distribution for CET holders

  NEW (Otto Loop On-Chain Layer):
  ├── ContributionRegistry.sol  [UUPS Proxy]   — universal catalog with provenance
  ├── DemandOracle.sol          [UUPS Proxy]   — demand signal aggregation + thresholds
  ├── RevenueRouter.sol         [Immutable*]   — atomic payment splitting
  ├── GovernanceAccrual.sol     [UUPS Proxy]   — non-transferable governance weight
  ├── ReputationNFT.sol         [Immutable]    — soulbound per-vertical reputation
  └── ProductionTrigger.sol     [UUPS Proxy]   — manufacturing partner interface

  * RevenueRouter core split logic is immutable; fee parameters are
    governed by GovernanceAccrual proposals.

  EXTERNAL DEPENDENCIES:
  ├── ONEON Identity             (contributor identity, KYC-optional)
  ├── USDC / KOIN               (settlement tokens)
  └── Chainlink VRF              (randomized audit selection)
```

### Cross-Contract Dependency Graph

```
                    ┌─────────────────────┐
                    │   ONEON Identity     │
                    └──────────┬──────────┘
                               │ (identity verification)
                               ▼
┌──────────────┐    ┌─────────────────────┐    ┌──────────────────┐
│ LaborAttest. │───►│ ContributionRegistry│◄───│   DPCRegistry    │
│ (verify)     │    │ (catalog)           │    │   (score)        │
└──────────────┘    └──────────┬──────────┘    └──────────────────┘
                               │
                    ┌──────────┼──────────────────────┐
                    │          │                       │
                    ▼          ▼                       ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
          │ DemandOracle │  │ReputationNFT │  │ProductionTrigger │
          │ (signals)    │  │ (soulbound)  │  │ (mfg interface)  │
          └──────┬───────┘  └──────────────┘  └──────────────────┘
                 │
                 ▼
          ┌──────────────┐
          │RevenueRouter │──────► USDC/KOIN transfers to all participants
          │ (split)      │
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────────┐
          │GovernanceAccrual │──────► LoopGovernor proposals
          │ (weight)         │
          └──────────────────┘
```

---

## 2. ContributionRegistry.sol — Universal Catalog with Provenance

**Purpose:** Every creative, AI, production, and labor input across all verticals is logged here with full provenance tracing. This is the single source of truth for "who contributed what, derived from what."

**Upgrade pattern:** UUPS — catalog schema will evolve as verticals launch.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract ContributionRegistry is UUPSUpgradeable, AccessControlUpgradeable {

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    enum ContributionType {
        DESIGN,     // 0 — original creative work (furniture, music, UI)
        CODE,       // 1 — software, AI models, production plans
        DATA,       // 2 — training data, memory capsules, annotations
        LABOR,      // 3 — physical work (construction, manufacturing)
        MATERIAL,   // 4 — raw materials, supplies
        CAPITAL,    // 5 — financial investment
        CURATION,   // 6 — discovery, recommendation, taste-making
        OPERATION,  // 7 — logistics, maintenance, hosting
        EDUCATION,  // 8 — teaching, mentoring, curriculum
        COMMUNITY   // 9 — governance participation, community building
    }

    enum CatalogStatus { DRAFT, ACTIVE, SUSPENDED, ARCHIVED }

    struct Entry {
        address contributor;         // ONEON identity
        bytes32 projectId;           // vertical identifier (keccak256 of "otto-market:furniture")
        ContributionType cType;
        bytes32 artifactHash;        // IPFS CID of the submitted work
        uint32 dpcScore;             // current DPC score (updated by DPCRegistry callback)
        CatalogStatus status;
        uint32 submittedAt;
        uint32 activatedAt;          // 0 until verified + activated
        uint32 demandCount;          // total demand events referencing this entry
        uint256 totalRevenue;        // lifetime revenue generated (in settlement token decimals)
        bool isAgent;                // true if contributor is an AI agent (triggers agent tax)
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    // Core catalog
    mapping(bytes32 => Entry) public entries;

    // Provenance: registryId => parent registryIds
    // e.g., a production plan's provenance includes the original design
    mapping(bytes32 => bytes32[]) public provenance;

    // Reverse provenance: registryId => child registryIds (derivatives)
    mapping(bytes32 => bytes32[]) public derivatives;

    // Contributor index: address => list of their registryIds
    mapping(address => bytes32[]) public contributorEntries;

    // Project index: projectId => list of registryIds
    mapping(bytes32 => bytes32[]) public projectEntries;

    // Nonce for deterministic ID generation
    uint256 private _nonce;

    // Role constants
    bytes32 public constant REGISTRAR_ROLE = keccak256("REGISTRAR_ROLE");
    bytes32 public constant DPC_UPDATER_ROLE = keccak256("DPC_UPDATER_ROLE");
    bytes32 public constant DEMAND_ORACLE_ROLE = keccak256("DEMAND_ORACLE_ROLE");

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event ContributionRegistered(
        bytes32 indexed registryId,
        address indexed contributor,
        bytes32 indexed projectId,
        ContributionType cType,
        bytes32 artifactHash,
        bool isAgent
    );

    event ContributionActivated(
        bytes32 indexed registryId,
        uint32 dpcScore
    );

    event ProvenanceLinkCreated(
        bytes32 indexed childId,
        bytes32 indexed parentId
    );

    event DPCUpdated(
        bytes32 indexed registryId,
        uint32 oldScore,
        uint32 newScore
    );

    event DemandRecorded(
        bytes32 indexed registryId,
        uint32 quantity,
        uint256 revenue,
        uint32 newDemandCount
    );

    event StatusChanged(
        bytes32 indexed registryId,
        CatalogStatus oldStatus,
        CatalogStatus newStatus
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Register a new contribution in the catalog
    /// @param contributor ONEON identity address
    /// @param projectId Vertical identifier
    /// @param cType Contribution type
    /// @param artifactHash IPFS CID of submitted work
    /// @param parentIds Provenance chain — parent contributions this derives from
    /// @param isAgent Whether contributor is an AI agent
    /// @return registryId Unique identifier for this entry
    /// @dev Callable by REGISTRAR_ROLE (LaborAttestation, off-chain coordinator)
    function register(
        address contributor,
        bytes32 projectId,
        ContributionType cType,
        bytes32 artifactHash,
        bytes32[] calldata parentIds,
        bool isAgent
    ) external onlyRole(REGISTRAR_ROLE) returns (bytes32 registryId) {
        // registryId = keccak256(contributor, projectId, artifactHash, nonce++)
        // Store Entry with status=DRAFT
        // For each parentId: validate it exists, append to provenance[registryId]
        // Append registryId to derivatives[parentId] for each parent
        // Index into contributorEntries and projectEntries
        // Emit ContributionRegistered + ProvenanceLinkCreated per parent
    }

    /// @notice Activate a contribution after verification passes
    /// @param registryId The contribution to activate
    /// @param dpcScore Initial DPC score from verification
    /// @dev Called by REGISTRAR_ROLE after LaborAttestation verifies
    function activate(
        bytes32 registryId,
        uint32 dpcScore
    ) external onlyRole(REGISTRAR_ROLE);

    /// @notice Update DPC score (called when resonance data arrives)
    /// @param registryId The entry to update
    /// @param newScore Updated DPC score
    /// @dev Called by DPC_UPDATER_ROLE (DPCRegistry callback)
    function updateDPC(
        bytes32 registryId,
        uint32 newScore
    ) external onlyRole(DPC_UPDATER_ROLE);

    /// @notice Record a demand event against this entry
    /// @param registryId The entry that received demand
    /// @param quantity Units demanded
    /// @param revenue Revenue generated (in settlement token smallest unit)
    /// @dev Called by DEMAND_ORACLE_ROLE
    function recordDemand(
        bytes32 registryId,
        uint32 quantity,
        uint256 revenue
    ) external onlyRole(DEMAND_ORACLE_ROLE);

    // ═══════════════════════════════════════════
    //              VIEW FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Get full provenance chain (all ancestors, not just parents)
    /// @dev Traverses provenance[] recursively up to MAX_DEPTH=10
    function getFullProvenance(bytes32 registryId)
        external view returns (bytes32[] memory ancestors);

    /// @notice Get all participants in the provenance chain with their roles
    /// @dev Used by RevenueRouter to compute splits
    function getProvenanceParticipants(bytes32 registryId)
        external view returns (
            address[] memory contributors,
            ContributionType[] memory types,
            uint32[] memory dpcScores,
            bool[] memory isAgentFlags
        );

    /// @notice Get entry by ID
    function getEntry(bytes32 registryId) external view returns (Entry memory);

    /// @notice Get entries by contributor
    function getContributorEntries(address contributor)
        external view returns (bytes32[] memory);

    /// @notice Get entries by project
    function getProjectEntries(bytes32 projectId)
        external view returns (bytes32[] memory);
}
```

**Security considerations:**
- **Provenance depth limit:** `getFullProvenance` caps at 10 levels to prevent gas DoS from deep chains. If provenance exceeds 10, off-chain indexer handles full resolution.
- **Agent flag immutable post-registration:** Once `isAgent` is set, it cannot be toggled. Prevents gaming agent tax by switching identity.
- **No self-referencing provenance:** `register()` must reject if any `parentId == registryId` (circular reference check).
- **Artifact hash uniqueness:** Same `artifactHash` + `contributor` + `projectId` cannot be registered twice (prevents duplicate claims).

---

## 3. DemandOracle.sol — Market Signal Aggregation & Thresholds

**Purpose:** Aggregates demand signals (views, add-to-cart, waitlists, purchases) from all verticals. When demand crosses a configurable threshold, emits a `ThresholdCrossed` event that ProductionTrigger listens to.

**Upgrade pattern:** UUPS — oracle reporters and threshold logic will evolve.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract DemandOracle is UUPSUpgradeable, AccessControlUpgradeable {

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    enum DemandType {
        PURCHASE,    // 0 — customer buys product
        STREAM,      // 1 — play/listen event
        LICENSE,     // 2 — sync/commercial license
        ENROLL,      // 3 — student enrollment
        BOOK,        // 4 — travel booking
        ACCESS,      // 5 — memory capsule query
        TRADE,       // 6 — token trade
        SUBSCRIBE,   // 7 — recurring subscription
        IMPRESSION,  // 8 — ad impression batch
        VIEW,        // 9 — product view (pre-purchase signal)
        WAITLIST,    // 10 — join waitlist (demand intent)
        ADD_TO_CART  // 11 — add to cart (strong purchase intent)
    }

    enum SignalStrength { WEAK, MODERATE, STRONG, CONFIRMED }
    // VIEW=WEAK, ADD_TO_CART/WAITLIST=MODERATE, PURCHASE/BOOK/ENROLL=STRONG,
    // STREAM/LICENSE/TRADE=CONFIRMED (revenue-bearing)

    struct DemandEvent {
        bytes32 registryId;          // which catalog entry
        DemandType dType;
        uint32 quantity;
        address buyer;               // 0x0 for anonymous views/carts
        uint256 paymentAmount;       // 0 for non-revenue signals (views, waitlists)
        uint32 timestamp;
    }

    struct DemandAggregate {
        uint32 viewCount;
        uint32 cartCount;
        uint32 waitlistCount;
        uint32 purchaseCount;
        uint256 totalRevenue;
        uint32 lastEventAt;
        bool thresholdCrossed;       // true once production threshold met
    }

    struct ThresholdConfig {
        uint32 minPurchases;         // minimum confirmed purchases to trigger
        uint32 minWaitlist;          // alternative: waitlist size trigger
        uint256 minRevenue;          // minimum revenue commitment
        uint32 windowSeconds;        // time window for signal accumulation
        bool requiresPayment;        // if true, only revenue-bearing events count
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    // Per-entry demand aggregates
    mapping(bytes32 => DemandAggregate) public aggregates;

    // Per-project threshold configuration
    mapping(bytes32 => ThresholdConfig) public thresholds;

    // Default threshold (used when project-specific not set)
    ThresholdConfig public defaultThreshold;

    // Authorized reporters per vertical
    mapping(bytes32 => mapping(address => bool)) public authorizedReporters;

    // Merkle settlement for batched high-frequency events
    mapping(bytes32 => bytes32) public pendingMerkleRoots; // batchId => root
    mapping(bytes32 => bool) public settledBatches;

    // Anti-manipulation
    uint32 public constant MIN_BATCH_SIZE = 10;          // min events per batch
    uint32 public constant REPORTER_COOLDOWN = 60;       // seconds between reports
    mapping(address => uint32) public lastReportTime;

    // Role constants
    bytes32 public constant REPORTER_ROLE = keccak256("REPORTER_ROLE");
    bytes32 public constant THRESHOLD_ADMIN_ROLE = keccak256("THRESHOLD_ADMIN_ROLE");

    // External contracts
    address public contributionRegistry;
    address public productionTrigger;

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event DemandReported(
        bytes32 indexed registryId,
        DemandType indexed dType,
        uint32 quantity,
        uint256 paymentAmount,
        address reporter
    );

    event BatchSettled(
        bytes32 indexed batchId,
        bytes32 merkleRoot,
        uint256 totalAmount,
        uint32 eventCount
    );

    event ThresholdCrossed(
        bytes32 indexed registryId,
        bytes32 indexed projectId,
        uint32 purchaseCount,
        uint32 waitlistCount,
        uint256 totalRevenue
    );

    event ThresholdConfigUpdated(
        bytes32 indexed projectId,
        uint32 minPurchases,
        uint32 minWaitlist,
        uint256 minRevenue
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Report a single demand event
    /// @param evt The demand event data
    /// @dev Callable by REPORTER_ROLE (per-vertical authorized signers)
    function reportDemand(DemandEvent calldata evt)
        external onlyRole(REPORTER_ROLE)
    {
        // Validate: registryId exists in ContributionRegistry
        // Validate: reporter cooldown not active
        // Update aggregates[registryId] based on dType
        // If revenue-bearing: forward to ContributionRegistry.recordDemand()
        // Check threshold: if _checkThreshold(registryId) → emit ThresholdCrossed
        // If thresholdCrossed: call ProductionTrigger.onThresholdCrossed()
    }

    /// @notice Report batch of demand events (gas-efficient for high-frequency)
    /// @param evts Array of demand events
    /// @dev Used for music streams, ONEON queries, ad impressions
    function reportBatch(DemandEvent[] calldata evts)
        external onlyRole(REPORTER_ROLE)
    {
        // Validate batch size >= MIN_BATCH_SIZE
        // Process each event, accumulate totals
        // Single threshold check at end
    }

    /// @notice Submit Merkle root for off-chain batched settlement
    /// @param batchId Unique batch identifier
    /// @param merkleRoot Root of demand event Merkle tree
    /// @param totalAmount Aggregate revenue in batch
    /// @param eventCount Number of events in batch
    /// @dev For high-frequency verticals (music, ONEON) — events verified off-chain,
    ///      only the aggregate settles on-chain
    function reportMerkle(
        bytes32 batchId,
        bytes32 merkleRoot,
        uint256 totalAmount,
        uint32 eventCount
    ) external onlyRole(REPORTER_ROLE);

    /// @notice Verify a specific event was included in a settled Merkle batch
    /// @param batchId Which batch
    /// @param proof Merkle proof
    /// @param evt The claimed event
    function verifyInclusion(
        bytes32 batchId,
        bytes32[] calldata proof,
        DemandEvent calldata evt
    ) external view returns (bool);

    /// @notice Set production threshold for a project
    /// @param projectId Project identifier
    /// @param config Threshold configuration
    /// @dev Callable by THRESHOLD_ADMIN_ROLE (initially deployer, later LoopGovernor)
    function setThreshold(
        bytes32 projectId,
        ThresholdConfig calldata config
    ) external onlyRole(THRESHOLD_ADMIN_ROLE);

    // ═══════════════════════════════════════════
    //           INTERNAL LOGIC
    // ═══════════════════════════════════════════

    /// @dev Check if demand aggregate crosses the threshold
    function _checkThreshold(bytes32 registryId) internal view returns (bool) {
        // Look up projectId from ContributionRegistry
        // Get threshold (project-specific or default)
        // Check: purchases >= minPurchases OR waitlist >= minWaitlist
        // Check: totalRevenue >= minRevenue (if requiresPayment)
        // Check: within windowSeconds of first signal
    }

    /// @dev Map DemandType to SignalStrength
    function _signalStrength(DemandType dType) internal pure returns (SignalStrength);
}
```

**Security considerations:**
- **Reporter cooldown:** 60s between reports from same address prevents spam. For batch operations, cooldown applies to the batch, not per-event.
- **Merkle settlement trust model:** Off-chain aggregator is trusted to compute the correct root. Individual users can challenge via `verifyInclusion`. If a false root is submitted, the reporter's stake (managed externally) can be slashed.
- **Threshold manipulation:** An attacker could fake views/waitlist signals. Mitigated by: (1) only REPORTER_ROLE can submit, (2) revenue-bearing events require actual on-chain payment, (3) `requiresPayment` flag on thresholds for physical goods forces real money in.
- **Stale aggregates:** No automatic reset. Aggregates accumulate forever. The `windowSeconds` in threshold config handles time-windowed checks without clearing data.

---

## 4. RevenueRouter.sol — Atomic Payment Splitting

**Purpose:** On every sale, atomically splits payment to designer, AI trainer pool, production node, Otto treasury, and governance reward pool using configurable basis points. The split formula reads the full provenance chain and computes each participant's share.

**Upgrade pattern:** Core split math is immutable (deployed as non-upgradeable). Fee parameters and role weights are stored in a separate config contract governed by GovernanceAccrual proposals.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract RevenueRouter is ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    struct SplitConfig {
        uint16 protocolFeeBps;       // default 500 (5%)
        uint16 governanceAccrualBps; // default 300 (3%)
        uint16 agentTaxBps;          // default 4000 (40%) — applied to agent shares
        uint16 maxSingleShareBps;    // default 5000 (50%) — cap per participant
        uint16 minCreatorShareBps;   // default 2000 (20%) — floor for primary creator
    }

    struct AgentTaxSplit {
        uint16 dataProviderBps;      // default 5000 (50% of agent tax)
        uint16 validatorBps;         // default 3000 (30% of agent tax)
        uint16 treasuryBps;          // default 2000 (20% of agent tax)
    }

    // Role weights in basis points (100 = 1.00x)
    // These map to ContributionType enum values
    struct RoleWeights {
        uint16 design;               // 10000 (1.00x)
        uint16 code;                 // 10000
        uint16 data;                 // 1000 (0.10x)
        uint16 labor;                // 9000 (0.90x)
        uint16 material;             // 8000 (0.80x)
        uint16 capital;              // 0 (earns financial return, not split weight)
        uint16 curation;             // 2500 (0.25x)
        uint16 operation;            // 1500 (0.15x)
        uint16 education;            // 3000 (0.30x)
        uint16 community;            // 1000 (0.10x)
    }

    struct Payout {
        address recipient;
        uint256 amount;
        uint8 contributionType;      // which role earned this
        bool isAgentTaxed;           // true if agent tax was applied
    }

    struct SplitResult {
        uint256 protocolFee;
        uint256 governanceAccrual;
        uint256 contributorPool;
        uint256 agentTaxCollected;
        Payout[] payouts;
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    SplitConfig public config;
    AgentTaxSplit public agentTaxConfig;
    RoleWeights public roleWeights;

    // External contracts
    address public immutable contributionRegistry;
    address public governanceAccrual;

    // Treasury addresses
    address public protocolTreasury;
    address public governancePool;
    address public dataProviderPool;
    address public validatorPool;

    // Accepted settlement tokens
    mapping(address => bool) public acceptedTokens;

    // Cumulative tracking
    mapping(address => uint256) public lifetimeEarnings;   // per contributor
    mapping(bytes32 => uint256) public lifetimeProjectRevenue; // per project
    uint256 public totalRouted;

    // Config governance
    address public configGovernor;  // GovernanceAccrual contract (or LoopGovernor)

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event RevenueSplit(
        bytes32 indexed registryId,
        address indexed settlementToken,
        uint256 grossAmount,
        uint256 protocolFee,
        uint256 governanceAccrual,
        uint256 contributorPool,
        uint256 agentTaxCollected,
        uint16 participantCount
    );

    event PayoutSent(
        bytes32 indexed registryId,
        address indexed recipient,
        uint256 amount,
        uint8 contributionType,
        bool isAgentTaxed
    );

    event AgentTaxDistributed(
        bytes32 indexed registryId,
        uint256 toDataProviders,
        uint256 toValidators,
        uint256 toTreasury
    );

    event ConfigUpdated(
        uint16 protocolFeeBps,
        uint16 governanceAccrualBps,
        uint16 agentTaxBps
    );

    event RoleWeightUpdated(
        uint8 indexed role,
        uint16 oldWeight,
        uint16 newWeight
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Execute an atomic revenue split for a demand event
    /// @param registryId The catalog entry that generated revenue
    /// @param token Settlement token (USDC, KOIN, etc.)
    /// @param grossAmount Total payment amount
    /// @return result Full breakdown of the split
    /// @dev Caller must have approved this contract for grossAmount of token.
    ///      All transfers happen atomically — if any fails, entire tx reverts.
    function split(
        bytes32 registryId,
        IERC20 token,
        uint256 grossAmount
    ) external nonReentrant returns (SplitResult memory result) {
        require(acceptedTokens[address(token)], "TOKEN_NOT_ACCEPTED");
        require(grossAmount > 0, "ZERO_AMOUNT");

        // 1. Pull funds from caller
        token.safeTransferFrom(msg.sender, address(this), grossAmount);

        // 2. Compute protocol fee and governance accrual
        result.protocolFee = (grossAmount * config.protocolFeeBps) / 10000;
        result.governanceAccrual = (grossAmount * config.governanceAccrualBps) / 10000;
        result.contributorPool = grossAmount - result.protocolFee - result.governanceAccrual;

        // 3. Get provenance participants from ContributionRegistry
        (
            address[] memory contributors,
            uint8[] memory types,       // ContributionType as uint8
            uint32[] memory dpcScores,
            bool[] memory isAgentFlags
        ) = IContributionRegistry(contributionRegistry)
                .getProvenanceParticipants(registryId);

        // 4. Compute weighted shares
        //    share_i = roleWeight[type_i] * dpcScore_i
        //    normalized: payout_i = contributorPool * share_i / totalShares
        //    If isAgent: apply agent tax, redirect taxed portion
        //    Enforce: no single share > maxSingleShareBps
        //    Enforce: primary creator >= minCreatorShareBps

        // 5. Execute transfers atomically
        //    For each participant: token.safeTransfer(recipient, amount)
        //    Protocol fee: token.safeTransfer(protocolTreasury, protocolFee)
        //    Governance: token.safeTransfer(governancePool, governanceAccrual)
        //    Agent tax splits: to dataProviderPool, validatorPool, protocolTreasury

        // 6. Update cumulative tracking
        //    lifetimeEarnings[contributor] += payout
        //    lifetimeProjectRevenue[projectId] += grossAmount

        // 7. Notify GovernanceAccrual of revenue events
        //    IGovernanceAccrual(governanceAccrual).onRevenueEvent(contributors, payouts)

        // 8. Emit events
    }

    /// @notice Preview a split without executing transfers
    /// @dev Pure computation — no state changes, no token movements
    function previewSplit(
        bytes32 registryId,
        uint256 grossAmount
    ) external view returns (SplitResult memory);

    /// @notice Update split configuration
    /// @dev Only callable by configGovernor (GovernanceAccrual/LoopGovernor)
    function updateConfig(SplitConfig calldata newConfig)
        external
    {
        require(msg.sender == configGovernor, "NOT_GOVERNOR");
        // Validate ranges:
        require(newConfig.protocolFeeBps >= 100 && newConfig.protocolFeeBps <= 1000, "FEE_RANGE");
        require(newConfig.governanceAccrualBps >= 100 && newConfig.governanceAccrualBps <= 500, "GOV_RANGE");
        require(newConfig.agentTaxBps >= 1000 && newConfig.agentTaxBps <= 6000, "TAX_RANGE");
        require(newConfig.protocolFeeBps + newConfig.governanceAccrualBps <= 1500, "TOTAL_OVERHEAD");
        config = newConfig;
        emit ConfigUpdated(newConfig.protocolFeeBps, newConfig.governanceAccrualBps, newConfig.agentTaxBps);
    }

    /// @notice Update a single role weight
    /// @dev Only callable by configGovernor
    function updateRoleWeight(uint8 role, uint16 newWeight)
        external
    {
        require(msg.sender == configGovernor, "NOT_GOVERNOR");
        require(role <= 9, "INVALID_ROLE");
        require(role != 5, "CAPITAL_WEIGHT_IMMUTABLE"); // capital weight is always 0
        // Update the specific role weight
        // Emit RoleWeightUpdated
    }
}

interface IContributionRegistry {
    function getProvenanceParticipants(bytes32 registryId)
        external view returns (
            address[] memory contributors,
            uint8[] memory types,
            uint32[] memory dpcScores,
            bool[] memory isAgentFlags
        );
}

interface IGovernanceAccrual {
    function onRevenueEvent(
        address[] calldata contributors,
        uint256[] calldata amounts
    ) external;
}
```

**Security considerations:**
- **Reentrancy:** `ReentrancyGuard` on `split()`. All token transfers happen in a single atomic transaction. No callbacks to untrusted contracts between state changes.
- **Rounding dust:** Basis point math can leave wei-level dust. Last recipient in the payout array receives the dust (prevents locked funds).
- **Capital weight immutable:** `updateRoleWeight()` explicitly rejects role=5 (CAPITAL). This is a constitutional constraint — capital earns financial returns through the split formula but cannot have its governance weight increased.
- **Total overhead cap:** `protocolFeeBps + governanceAccrualBps <= 1500` (15% max) prevents governance from extracting excessive overhead.
- **Pull pattern alternative:** For gas optimization on chains with expensive transfers, consider a pull-based pattern where payouts are credited to balances and withdrawn separately. Current push design chosen for atomicity guarantees.
- **Flash loan attack on DPC scores:** An attacker could temporarily inflate DPC scores to capture larger splits. Mitigated by: DPC scores are updated asynchronously via callbacks, not in the same tx as the split. The `getProvenanceParticipants` reads stored scores, not computed-on-the-fly values.
- **Token approval management:** The caller (DemandOracle or marketplace contract) must approve `grossAmount`. If approval is insufficient, the entire split reverts cleanly.

---

## 5. GovernanceAccrual.sol — Non-Transferable Governance Weight

**Purpose:** Non-transferable governance score accrued from verified contributions and revenue events. Decays slowly to keep it active-contributor-weighted. Integrates with LoopGovernor for proposal voting.

**Upgrade pattern:** UUPS — decay parameters and accrual formula may evolve.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";

contract GovernanceAccrual is UUPSUpgradeable, AccessControlUpgradeable {

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    struct ParticipantState {
        uint256 rawWeight;           // undecayed governance weight (WAD precision, 1e18)
        uint256 cumulativeDPC;       // lifetime DPC score (scaled 1e18)
        uint256 cumulativeRevenue;   // lifetime revenue earned (smallest token unit)
        uint32 firstContribution;    // timestamp of first verified contribution
        uint32 lastContribution;     // timestamp of most recent verified contribution
        uint32 lastDecayApplied;     // timestamp of last decay checkpoint
        uint8 contributionTypeFlags; // bitmask of which types they've contributed
    }

    struct DecayConfig {
        uint16 lambdaBps;            // monthly decay rate in basis points (default 500 = 5%)
        uint32 tenureCapMonths;      // max tenure bonus period (default 24)
        uint16 dpcExponentBps;       // sqrt ≈ 5000 (0.50) — sublinear DPC scaling
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    mapping(address => ParticipantState) public participants;

    DecayConfig public decayConfig;

    // Running totals
    uint256 public totalActiveWeight;
    uint32 public totalParticipants;

    // External contracts
    address public revenueRouter;
    address public contributionRegistry;

    // Role constants
    bytes32 public constant ACCRUAL_ROLE = keccak256("ACCRUAL_ROLE");

    // Capital exclusion — IMMUTABLE, cannot be changed by any proposal
    // Contributions of type CAPITAL (5) earn ZERO governance weight
    // This is constitutional and enforced at the contract level
    uint8 private constant CAPITAL_TYPE = 5;

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event WeightAccrued(
        address indexed participant,
        uint256 deltaWeight,
        uint256 newTotalWeight,
        uint256 dpcDelta,
        uint256 revenueDelta
    );

    event WeightDecayed(
        address indexed participant,
        uint256 decayedAmount,
        uint256 newWeight,
        uint32 monthsInactive
    );

    event DecayConfigUpdated(
        uint16 lambdaBps,
        uint32 tenureCapMonths,
        uint16 dpcExponentBps
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Accrue governance weight from a verified contribution
    /// @param contributor ONEON identity
    /// @param contributionType Type of contribution (from ContributionType enum)
    /// @param dpcDelta DPC score earned from this contribution
    /// @dev Called by ContributionRegistry/LaborAttestation after verification
    function onContributionVerified(
        address contributor,
        uint8 contributionType,
        uint32 dpcDelta
    ) external onlyRole(ACCRUAL_ROLE) {
        // CONSTITUTIONAL: reject if contributionType == CAPITAL_TYPE
        require(contributionType != CAPITAL_TYPE, "CAPITAL_NO_GOVERNANCE");

        // Apply pending decay first
        _applyDecay(contributor);

        // Update cumulative DPC
        ParticipantState storage p = participants[contributor];
        p.cumulativeDPC += uint256(dpcDelta) * 1e18;
        p.lastContribution = uint32(block.timestamp);
        if (p.firstContribution == 0) {
            p.firstContribution = uint32(block.timestamp);
            totalParticipants++;
        }
        p.contributionTypeFlags |= uint8(1 << contributionType);

        // Compute weight delta: sqrt(cumDPC) * tenure_factor
        uint256 delta = _computeWeightDelta(p, dpcDelta, 0);
        p.rawWeight += delta;
        totalActiveWeight += delta;

        emit WeightAccrued(contributor, delta, p.rawWeight, dpcDelta, 0);
    }

    /// @notice Accrue governance weight from revenue events
    /// @param contributors Array of contributor addresses
    /// @param amounts Array of revenue amounts earned
    /// @dev Called by RevenueRouter after split execution
    function onRevenueEvent(
        address[] calldata contributors,
        uint256[] calldata amounts
    ) external {
        require(msg.sender == revenueRouter, "NOT_ROUTER");
        for (uint256 i = 0; i < contributors.length; i++) {
            ParticipantState storage p = participants[contributors[i]];
            if (p.firstContribution == 0) continue; // skip unregistered

            _applyDecay(contributors[i]);

            p.cumulativeRevenue += amounts[i];

            // Revenue accrual: ln(1 + cumulativeRevenue) component
            uint256 delta = _computeWeightDelta(p, 0, amounts[i]);
            p.rawWeight += delta;
            totalActiveWeight += delta;

            emit WeightAccrued(contributors[i], delta, p.rawWeight, 0, amounts[i]);
        }
    }

    /// @notice Get current governance weight (with lazy decay applied)
    /// @param participant Address to check
    /// @return weight Current governance weight after decay
    function getWeight(address participant) external view returns (uint256 weight) {
        ParticipantState memory p = participants[participant];
        if (p.rawWeight == 0) return 0;

        // Apply hypothetical decay without state change
        uint32 monthsInactive = _monthsSince(p.lastContribution);
        if (monthsInactive == 0) return p.rawWeight;

        uint256 decayFactor = _decayFactor(monthsInactive);
        return (p.rawWeight * decayFactor) / 1e18;
    }

    /// @notice Force-apply decay for a participant (callable by anyone)
    /// @dev Useful for governance snapshot accuracy
    function applyDecay(address participant) external {
        _applyDecay(participant);
    }

    /// @notice Batch decay application for governance snapshot
    function batchApplyDecay(address[] calldata participants_) external {
        for (uint256 i = 0; i < participants_.length; i++) {
            _applyDecay(participants_[i]);
        }
    }

    // ═══════════════════════════════════════════
    //           INTERNAL LOGIC
    // ═══════════════════════════════════════════

    /// @dev Core governance weight accrual formula:
    ///      ΔG = sqrt(cumDPC) × ln(1 + cumRevenue) × tenure_factor
    ///
    ///      sqrt: sublinear DPC scaling (prevents score whales)
    ///      ln: logarithmic revenue (diminishing returns on pure capital)
    ///      tenure: min(1.0, months_active / tenureCapMonths)
    function _computeWeightDelta(
        ParticipantState memory p,
        uint32 dpcDelta,
        uint256 revenueDelta
    ) internal view returns (uint256 delta) {
        // sqrt(cumDPC) using Babylonian method (WAD precision)
        uint256 sqrtDPC = _wadSqrt(p.cumulativeDPC + uint256(dpcDelta) * 1e18);

        // ln(1 + cumRevenue) using Taylor series approximation (WAD)
        uint256 lnRevenue = _wadLn(1e18 + p.cumulativeRevenue + revenueDelta);

        // tenure_factor = min(1.0, months_active / tenureCapMonths)
        uint32 monthsActive = _monthsSince(p.firstContribution);
        uint256 tenure = monthsActive >= decayConfig.tenureCapMonths
            ? 1e18
            : (uint256(monthsActive) * 1e18) / decayConfig.tenureCapMonths;

        delta = (sqrtDPC * lnRevenue * tenure) / (1e18 * 1e18);
    }

    /// @dev Apply exponential decay based on months since last contribution
    ///      decay = rawWeight × (1 - lambda)^months
    function _applyDecay(address contributor) internal {
        ParticipantState storage p = participants[contributor];
        if (p.rawWeight == 0) return;

        uint32 monthsSinceDecay = _monthsSince(p.lastDecayApplied);
        if (monthsSinceDecay == 0) return;

        uint256 factor = _decayFactor(monthsSinceDecay);
        uint256 newWeight = (p.rawWeight * factor) / 1e18;
        uint256 decayed = p.rawWeight - newWeight;

        totalActiveWeight -= decayed;
        p.rawWeight = newWeight;
        p.lastDecayApplied = uint32(block.timestamp);

        emit WeightDecayed(contributor, decayed, newWeight, monthsSinceDecay);
    }

    /// @dev Compute decay factor: (1 - lambda)^months in WAD
    function _decayFactor(uint32 months) internal view returns (uint256) {
        // (10000 - lambdaBps) / 10000, raised to power months
        // Using repeated squaring for gas efficiency
        uint256 base = (uint256(10000 - decayConfig.lambdaBps) * 1e18) / 10000;
        return _wadPow(base, months);
    }

    /// @dev Months elapsed since a timestamp
    function _monthsSince(uint32 timestamp) internal view returns (uint32) {
        if (timestamp == 0 || block.timestamp <= timestamp) return 0;
        return uint32((block.timestamp - timestamp) / 30 days);
    }

    // WAD math helpers (1e18 fixed point)
    function _wadSqrt(uint256 x) internal pure returns (uint256);
    function _wadLn(uint256 x) internal pure returns (uint256);
    function _wadPow(uint256 base, uint256 exp) internal pure returns (uint256);

    // ═══════════════════════════════════════════
    //          NON-TRANSFERABILITY
    // ═══════════════════════════════════════════

    // Governance weight is NOT a token. It is a score stored in a mapping.
    // There is no transfer function. There is no approval function.
    // Weight can only increase via verified contributions/revenue,
    // and decrease via time decay. This is by design.
    //
    // Any future proposal to add transferability MUST be rejected
    // at the contract level — the upgrade path explicitly excludes
    // transfer functionality via the _authorizeUpgrade check.
}
```

**Security considerations:**
- **Non-transferable by construction:** Weight is a mapping value, not an ERC-20. No transfer functions exist. Upgrade authorization must verify the new implementation has no transfer capabilities.
- **Capital exclusion is enforced in code:** `CAPITAL_TYPE` check in `onContributionVerified` is a hard revert, not a governance-adjustable parameter. Even UUPS upgrade cannot bypass this — the `_authorizeUpgrade` function should verify the invariant persists.
- **Lazy decay:** Decay is only applied when weight is read or modified. This saves gas but means `totalActiveWeight` may be slightly stale. `batchApplyDecay` handles governance snapshot accuracy.
- **WAD math overflow:** All intermediate computations use 1e18 fixed point. `_wadSqrt` and `_wadLn` must be gas-bounded (max iterations). Use battle-tested libraries (Solmate, PRBMath).
- **Revenue front-running:** An attacker could front-run a large revenue event to accrue weight from a small contribution made just before. Mitigated by: `lastContribution` timestamp check — weight delta from revenue uses the existing cumulative DPC at time of split, not freshly inflated values.

---

## 6. ReputationNFT.sol — Soulbound Per-Vertical Reputation

**Purpose:** Soulbound (non-transferable) ERC-721 token, one per contributor per vertical. Contains the contributor's full history in that vertical: contribution count, cumulative DPC, revenue earned, verification record, specializations.

**Upgrade pattern:** Immutable — reputation records should never be rewritten. Metadata URI can be updated to point to new IPFS schemas.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";

contract ReputationNFT is ERC721, AccessControl {

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    struct ReputationData {
        address contributor;
        bytes32 projectId;           // vertical identifier
        uint32 contributionCount;    // total verified contributions in this vertical
        uint32 cumulativeDPC;        // lifetime DPC score in this vertical
        uint256 revenueEarned;       // lifetime revenue from this vertical
        uint32 firstContribution;    // timestamp
        uint32 lastContribution;     // timestamp
        uint32 attestationsGiven;    // how many times they attested others
        uint32 attestationsReceived; // how many attestations on their work
        uint8 avgAttestationScore;   // average quality score (1-100)
        uint8 specializations;       // bitmask of ContributionTypes in this vertical
        uint8 trustTier;             // 0=New, 1=Established, 2=Trusted, 3=Core
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    // tokenId => reputation data
    mapping(uint256 => ReputationData) public reputation;

    // contributor + projectId => tokenId (for lookup)
    mapping(address => mapping(bytes32 => uint256)) public tokenByContributorProject;

    // contributor => list of tokenIds (all verticals)
    mapping(address => uint256[]) public contributorTokens;

    uint256 private _nextTokenId;

    // Base URI for metadata (IPFS gateway)
    string private _baseTokenURI;

    // Role constants
    bytes32 public constant UPDATER_ROLE = keccak256("UPDATER_ROLE");

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event ReputationMinted(
        uint256 indexed tokenId,
        address indexed contributor,
        bytes32 indexed projectId
    );

    event ReputationUpdated(
        uint256 indexed tokenId,
        uint32 contributionCount,
        uint32 cumulativeDPC,
        uint256 revenueEarned,
        uint8 trustTier
    );

    event TrustTierUpgraded(
        uint256 indexed tokenId,
        address indexed contributor,
        uint8 oldTier,
        uint8 newTier
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    constructor() ERC721("Otto Reputation", "OREP") {
        _grantRole(DEFAULT_ADMIN_ROLE, msg.sender);
    }

    /// @notice Mint a reputation NFT for a contributor in a vertical
    /// @dev Auto-minted on first verified contribution in a vertical
    /// @param contributor ONEON identity
    /// @param projectId Vertical identifier
    /// @return tokenId The minted token ID
    function mintReputation(
        address contributor,
        bytes32 projectId
    ) external onlyRole(UPDATER_ROLE) returns (uint256 tokenId) {
        require(
            tokenByContributorProject[contributor][projectId] == 0,
            "ALREADY_EXISTS"
        );
        tokenId = ++_nextTokenId;
        _safeMint(contributor, tokenId);

        reputation[tokenId] = ReputationData({
            contributor: contributor,
            projectId: projectId,
            contributionCount: 0,
            cumulativeDPC: 0,
            revenueEarned: 0,
            firstContribution: uint32(block.timestamp),
            lastContribution: uint32(block.timestamp),
            attestationsGiven: 0,
            attestationsReceived: 0,
            avgAttestationScore: 0,
            specializations: 0,
            trustTier: 0 // NEW
        });

        tokenByContributorProject[contributor][projectId] = tokenId;
        contributorTokens[contributor].push(tokenId);

        emit ReputationMinted(tokenId, contributor, projectId);
    }

    /// @notice Update reputation data after a verified contribution
    /// @param contributor ONEON identity
    /// @param projectId Vertical identifier
    /// @param dpcDelta DPC earned from this contribution
    /// @param contributionType Type of contribution (for specialization bitmask)
    /// @param attestationScore Average attestation quality score
    function onContributionVerified(
        address contributor,
        bytes32 projectId,
        uint32 dpcDelta,
        uint8 contributionType,
        uint8 attestationScore
    ) external onlyRole(UPDATER_ROLE) {
        uint256 tokenId = tokenByContributorProject[contributor][projectId];
        if (tokenId == 0) {
            // Auto-mint on first contribution
            tokenId = this.mintReputation(contributor, projectId);
        }

        ReputationData storage r = reputation[tokenId];
        r.contributionCount++;
        r.cumulativeDPC += dpcDelta;
        r.lastContribution = uint32(block.timestamp);
        r.attestationsReceived++;
        r.specializations |= uint8(1 << contributionType);

        // Rolling average attestation score
        r.avgAttestationScore = uint8(
            (uint256(r.avgAttestationScore) * (r.attestationsReceived - 1) + attestationScore)
            / r.attestationsReceived
        );

        // Trust tier upgrade check
        uint8 oldTier = r.trustTier;
        r.trustTier = _computeTrustTier(r.contributionCount, r.avgAttestationScore);
        if (r.trustTier > oldTier) {
            emit TrustTierUpgraded(tokenId, contributor, oldTier, r.trustTier);
        }

        emit ReputationUpdated(
            tokenId,
            r.contributionCount,
            r.cumulativeDPC,
            r.revenueEarned,
            r.trustTier
        );
    }

    /// @notice Update revenue earned (called by RevenueRouter after split)
    function onRevenueEarned(
        address contributor,
        bytes32 projectId,
        uint256 amount
    ) external onlyRole(UPDATER_ROLE) {
        uint256 tokenId = tokenByContributorProject[contributor][projectId];
        if (tokenId == 0) return; // skip if no reputation NFT
        reputation[tokenId].revenueEarned += amount;
    }

    /// @notice Record that this contributor attested someone else's work
    function onAttestationGiven(
        address attester,
        bytes32 projectId
    ) external onlyRole(UPDATER_ROLE) {
        uint256 tokenId = tokenByContributorProject[attester][projectId];
        if (tokenId == 0) return;
        reputation[tokenId].attestationsGiven++;
    }

    // ═══════════════════════════════════════════
    //          VIEW FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Get full reputation for a contributor across all verticals
    function getFullReputation(address contributor)
        external view returns (ReputationData[] memory)
    {
        uint256[] memory tokenIds = contributorTokens[contributor];
        ReputationData[] memory result = new ReputationData[](tokenIds.length);
        for (uint256 i = 0; i < tokenIds.length; i++) {
            result[i] = reputation[tokenIds[i]];
        }
        return result;
    }

    /// @notice Get reputation for a specific vertical
    function getVerticalReputation(address contributor, bytes32 projectId)
        external view returns (ReputationData memory)
    {
        uint256 tokenId = tokenByContributorProject[contributor][projectId];
        require(tokenId != 0, "NO_REPUTATION");
        return reputation[tokenId];
    }

    // ═══════════════════════════════════════════
    //          SOULBOUND ENFORCEMENT
    // ═══════════════════════════════════════════

    /// @dev Block all transfers (soulbound)
    function _update(address to, uint256 tokenId, address auth)
        internal override returns (address)
    {
        address from = _ownerOf(tokenId);
        // Allow minting (from == address(0)) but block transfers
        require(from == address(0), "SOULBOUND: non-transferable");
        return super._update(to, tokenId, auth);
    }

    // ═══════════════════════════════════════════
    //           INTERNAL LOGIC
    // ═══════════════════════════════════════════

    /// @dev Trust tier thresholds (matching Core Value Loop architecture)
    ///      0=New (0-5 contributions)
    ///      1=Established (6-25, avg score >= 60)
    ///      2=Trusted (26-100, avg score >= 70)
    ///      3=Core (100+, avg score >= 75)
    function _computeTrustTier(uint32 count, uint8 avgScore)
        internal pure returns (uint8)
    {
        if (count > 100 && avgScore >= 75) return 3;
        if (count > 25 && avgScore >= 70) return 2;
        if (count > 5 && avgScore >= 60) return 1;
        return 0;
    }

    /// @dev Token URI points to IPFS metadata with rendered reputation card
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        // Returns base URI + tokenId
        // Off-chain renderer generates visual reputation card from on-chain data
    }

    function supportsInterface(bytes4 interfaceId)
        public view override(ERC721, AccessControl) returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}
```

**Security considerations:**
- **Soulbound enforcement:** Overrides `_update()` (OZ v5 pattern) to block all transfers except minting. No `approve`, `transferFrom`, or `safeTransferFrom` can move tokens.
- **Reputation inflation:** Only `UPDATER_ROLE` can modify reputation data. This role is granted to ContributionRegistry and RevenueRouter contracts, not EOAs.
- **Auto-mint on first contribution:** If `mintReputation` is called externally with a fake projectId, it creates a useless empty NFT. Not exploitable since data updates require `UPDATER_ROLE`.
- **Rolling average overflow:** `avgAttestationScore` is uint8 (max 255). Since scores are 1-100, the rolling average formula is safe. However, if `attestationsReceived` overflows uint32 (4B attestations), the division could underflow. Practically impossible but noted.
- **Token ID 0 collision:** `_nextTokenId` starts at 0 and pre-increments, so first token is ID 1. Lookup `tokenByContributorProject` returning 0 correctly means "no token exists."

---

## 7. ProductionTrigger.sol — Manufacturing Partner Interface

**Purpose:** When demand crosses a threshold in DemandOracle, this contract manages the interface with physical manufacturing partners. It creates production orders, tracks fulfillment, and releases payment upon delivery confirmation.

**Upgrade pattern:** UUPS — manufacturing partner integrations will evolve.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/access/AccessControlUpgradeable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

contract ProductionTrigger is UUPSUpgradeable, AccessControlUpgradeable {
    using SafeERC20 for IERC20;

    // ═══════════════════════════════════════════
    //                  TYPES
    // ═══════════════════════════════════════════

    enum OrderStatus {
        CREATED,          // 0 — order placed, awaiting partner acceptance
        ACCEPTED,         // 1 — partner accepted, production starting
        IN_PRODUCTION,    // 2 — manufacturing in progress
        QC_PENDING,       // 3 — production done, awaiting quality check
        QC_PASSED,        // 4 — quality verified
        SHIPPED,          // 5 — shipped to buyer/warehouse
        DELIVERED,        // 6 — delivery confirmed → triggers RevenueRouter
        DISPUTED,         // 7 — quality dispute raised
        CANCELLED         // 8 — cancelled (refund triggered)
    }

    struct ManufacturingPartner {
        bytes32 partnerId;
        address partnerAddress;      // partner's ONEON identity
        string name;
        bytes32[] capabilities;      // keccak256 of capability strings (e.g., "woodworking")
        uint16 qualityScoreBps;      // 0-10000 (100.00%) — running average
        uint32 totalOrders;
        uint32 completedOrders;
        uint32 disputedOrders;
        bool active;
    }

    struct ProductionOrder {
        bytes32 orderId;
        bytes32 registryId;          // ContributionRegistry entry (the design)
        bytes32 partnerId;           // assigned manufacturing partner
        uint32 quantity;
        uint256 escrowAmount;        // funds locked for this production run
        address escrowToken;         // settlement token
        OrderStatus status;
        uint32 createdAt;
        uint32 acceptedAt;
        uint32 completedAt;
        uint32 deadline;             // partner must deliver by this time
        bytes32 productionSpecHash;  // IPFS CID of AI-generated manufacturing specs
        bytes32 qcReportHash;        // IPFS CID of QC report (set after inspection)
        address qcInspector;         // who performed quality check
    }

    // ═══════════════════════════════════════════
    //                  STATE
    // ═══════════════════════════════════════════

    mapping(bytes32 => ManufacturingPartner) public partners;
    mapping(bytes32 => ProductionOrder) public orders;
    mapping(bytes32 => bytes32[]) public partnerOrders;    // partnerId => orderIds
    mapping(bytes32 => bytes32[]) public registryOrders;   // registryId => orderIds

    // Auto-matching: capability => partnerId[]
    mapping(bytes32 => bytes32[]) public capabilityPartners;

    // Escrow tracking
    mapping(bytes32 => uint256) public escrowBalances;     // orderId => locked amount

    uint256 private _orderNonce;

    // Role constants
    bytes32 public constant PARTNER_ADMIN_ROLE = keccak256("PARTNER_ADMIN_ROLE");
    bytes32 public constant ORDER_MANAGER_ROLE = keccak256("ORDER_MANAGER_ROLE");
    bytes32 public constant QC_INSPECTOR_ROLE = keccak256("QC_INSPECTOR_ROLE");
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE"); // DemandOracle

    // External contracts
    address public demandOracle;
    address public contributionRegistry;
    address public revenueRouter;

    // Default production deadline (30 days)
    uint32 public defaultDeadline = 30 days;

    // ═══════════════════════════════════════════
    //                  EVENTS
    // ═══════════════════════════════════════════

    event PartnerRegistered(
        bytes32 indexed partnerId,
        address indexed partnerAddress,
        string name
    );

    event ProductionOrderCreated(
        bytes32 indexed orderId,
        bytes32 indexed registryId,
        bytes32 indexed partnerId,
        uint32 quantity,
        uint256 escrowAmount
    );

    event OrderStatusChanged(
        bytes32 indexed orderId,
        OrderStatus oldStatus,
        OrderStatus newStatus
    );

    event QCCompleted(
        bytes32 indexed orderId,
        address indexed inspector,
        bool passed,
        bytes32 reportHash
    );

    event EscrowReleased(
        bytes32 indexed orderId,
        bytes32 indexed partnerId,
        uint256 amount
    );

    event DeadlineMissed(
        bytes32 indexed orderId,
        bytes32 indexed partnerId,
        uint32 deadline,
        uint32 currentTime
    );

    // ═══════════════════════════════════════════
    //              CORE FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Called by DemandOracle when a threshold is crossed
    /// @param registryId The design/product that crossed the demand threshold
    /// @param quantity Number of units demanded
    /// @param escrowToken Token used for escrow (USDC)
    /// @param escrowAmount Funds to lock for production
    /// @dev Automatically matches to best available manufacturing partner
    function onThresholdCrossed(
        bytes32 registryId,
        uint32 quantity,
        address escrowToken,
        uint256 escrowAmount
    ) external onlyRole(ORACLE_ROLE) returns (bytes32 orderId) {
        // 1. Pull escrow funds from DemandOracle/marketplace
        IERC20(escrowToken).safeTransferFrom(msg.sender, address(this), escrowAmount);

        // 2. Auto-match manufacturing partner
        //    - Look up contribution type and project from ContributionRegistry
        //    - Find partners with matching capabilities
        //    - Select by: highest qualityScoreBps × (1 - disputeRate)
        bytes32 partnerId = _matchPartner(registryId);
        require(partnerId != bytes32(0), "NO_PARTNER_AVAILABLE");

        // 3. Create production order
        orderId = keccak256(abi.encodePacked(registryId, partnerId, _orderNonce++));
        orders[orderId] = ProductionOrder({
            orderId: orderId,
            registryId: registryId,
            partnerId: partnerId,
            quantity: quantity,
            escrowAmount: escrowAmount,
            escrowToken: escrowToken,
            status: OrderStatus.CREATED,
            createdAt: uint32(block.timestamp),
            acceptedAt: 0,
            completedAt: 0,
            deadline: uint32(block.timestamp) + defaultDeadline,
            productionSpecHash: bytes32(0), // set when AI generates specs
            qcReportHash: bytes32(0),
            qcInspector: address(0)
        });

        escrowBalances[orderId] = escrowAmount;
        partnerOrders[partnerId].push(orderId);
        registryOrders[registryId].push(orderId);

        emit ProductionOrderCreated(orderId, registryId, partnerId, quantity, escrowAmount);
    }

    /// @notice Partner accepts a production order
    /// @param orderId The order to accept
    function acceptOrder(bytes32 orderId) external {
        ProductionOrder storage o = orders[orderId];
        require(msg.sender == partners[o.partnerId].partnerAddress, "NOT_PARTNER");
        require(o.status == OrderStatus.CREATED, "WRONG_STATUS");

        o.status = OrderStatus.ACCEPTED;
        o.acceptedAt = uint32(block.timestamp);
        emit OrderStatusChanged(orderId, OrderStatus.CREATED, OrderStatus.ACCEPTED);
    }

    /// @notice Update production status
    /// @param orderId Order ID
    /// @param specHash IPFS CID of production specs (set when AI generates them)
    function startProduction(bytes32 orderId, bytes32 specHash)
        external onlyRole(ORDER_MANAGER_ROLE)
    {
        ProductionOrder storage o = orders[orderId];
        require(o.status == OrderStatus.ACCEPTED, "WRONG_STATUS");
        o.status = OrderStatus.IN_PRODUCTION;
        o.productionSpecHash = specHash;
        emit OrderStatusChanged(orderId, OrderStatus.ACCEPTED, OrderStatus.IN_PRODUCTION);
    }

    /// @notice Submit QC report
    /// @param orderId Order ID
    /// @param passed Whether QC passed
    /// @param reportHash IPFS CID of QC report
    function submitQC(bytes32 orderId, bool passed, bytes32 reportHash)
        external onlyRole(QC_INSPECTOR_ROLE)
    {
        ProductionOrder storage o = orders[orderId];
        require(o.status == OrderStatus.QC_PENDING, "WRONG_STATUS");

        o.qcReportHash = reportHash;
        o.qcInspector = msg.sender;

        if (passed) {
            o.status = OrderStatus.QC_PASSED;
            emit OrderStatusChanged(orderId, OrderStatus.QC_PENDING, OrderStatus.QC_PASSED);
        } else {
            o.status = OrderStatus.DISPUTED;
            emit OrderStatusChanged(orderId, OrderStatus.QC_PENDING, OrderStatus.DISPUTED);
        }

        emit QCCompleted(orderId, msg.sender, passed, reportHash);
    }

    /// @notice Confirm delivery — triggers escrow release and revenue split
    /// @param orderId Order ID
    /// @dev Called by ORDER_MANAGER_ROLE after buyer confirms delivery
    function confirmDelivery(bytes32 orderId)
        external onlyRole(ORDER_MANAGER_ROLE)
    {
        ProductionOrder storage o = orders[orderId];
        require(
            o.status == OrderStatus.QC_PASSED || o.status == OrderStatus.SHIPPED,
            "WRONG_STATUS"
        );

        o.status = OrderStatus.DELIVERED;
        o.completedAt = uint32(block.timestamp);

        // Release escrow to RevenueRouter for splitting
        uint256 amount = escrowBalances[orderId];
        escrowBalances[orderId] = 0;
        IERC20(o.escrowToken).safeApprove(revenueRouter, amount);

        // Trigger revenue split through the full provenance chain
        IRevenueRouter(revenueRouter).split(
            o.registryId,
            IERC20(o.escrowToken),
            amount
        );

        // Update partner stats
        ManufacturingPartner storage p = partners[o.partnerId];
        p.completedOrders++;

        emit OrderStatusChanged(orderId, OrderStatus.QC_PASSED, OrderStatus.DELIVERED);
        emit EscrowReleased(orderId, o.partnerId, amount);
    }

    /// @notice Check for overdue orders and flag them
    /// @dev Can be called by anyone (protocol maintenance)
    function checkDeadlines(bytes32[] calldata orderIds) external {
        for (uint256 i = 0; i < orderIds.length; i++) {
            ProductionOrder storage o = orders[orderIds[i]];
            if (
                o.status != OrderStatus.DELIVERED &&
                o.status != OrderStatus.CANCELLED &&
                block.timestamp > o.deadline
            ) {
                emit DeadlineMissed(orderIds[i], o.partnerId, o.deadline, uint32(block.timestamp));
                // Does NOT auto-cancel — dispute resolution needed
            }
        }
    }

    /// @notice Register a manufacturing partner
    function registerPartner(
        address partnerAddress,
        string calldata name,
        bytes32[] calldata capabilities
    ) external onlyRole(PARTNER_ADMIN_ROLE) returns (bytes32 partnerId);

    // ═══════════════════════════════════════════
    //           INTERNAL LOGIC
    // ═══════════════════════════════════════════

    /// @dev Match the best manufacturing partner for a given registry entry
    function _matchPartner(bytes32 registryId) internal view returns (bytes32 partnerId) {
        // 1. Get contribution type and project from ContributionRegistry
        // 2. Derive required capabilities from project/type
        // 3. Find all active partners with matching capabilities
        // 4. Score: qualityScoreBps × (completedOrders / max(totalOrders, 1))
        //          × (1 - disputedOrders / max(completedOrders, 1))
        // 5. Return highest-scoring partner
        // 6. Return bytes32(0) if no match
    }
}

interface IRevenueRouter {
    function split(bytes32 registryId, IERC20 token, uint256 grossAmount) external;
}
```

**Security considerations:**
- **Escrow isolation:** Each order's escrow is tracked separately. No commingling of funds across orders.
- **No auto-cancellation on deadline miss:** `checkDeadlines` only emits events. Cancellation requires human intervention (ORDER_MANAGER_ROLE) to prevent accidental fund loss if a partner is simply late but still delivering.
- **Partner collusion:** A malicious partner could accept orders and never deliver, locking escrow. Mitigated by: deadline monitoring, quality score decay on disputes, and eventual governance-driven deactivation.
- **QC inspector independence:** QC_INSPECTOR_ROLE should not be the same address as the manufacturing partner. Access control must enforce this at the role-granting level.
- **Re-entrancy on delivery:** `confirmDelivery` calls `revenueRouter.split()` which makes external token transfers. The escrow balance is zeroed before the external call (checks-effects-interactions pattern).
- **safeApprove race condition:** Using `safeApprove` with a non-zero existing allowance can fail on some tokens. Since we zero the escrow balance and approve fresh each time, this is safe.

---

## 8. Event Flow — Complete Lifecycle

```
COMPLETE EVENT FLOW: Designer submits chair → customer pays → carpenter gets paid

═══ PHASE 1: SUBMISSION & VERIFICATION ═══

  Designer calls LaborAttestation.submitContribution()
    → ContributionSubmitted(id, designer, DESIGN, "otto-market:furniture", 0)

  ContributionRegistry.register(designer, projectId, DESIGN, artifactHash, [], false)
    → ContributionRegistered(regId, designer, projectId, DESIGN, hash, false)

  Two peers call LaborAttestation.recordAttestation()
    → AttestationRecorded(id, peer1, PEER, 82)
    → AttestationRecorded(id, peer2, PEER, 78)

  AI quality check: LaborAttestation.recordAttestation()
    → AttestationRecorded(id, aiChecker, REVIEWER, 85)

  Quorum met → LaborAttestation.verifyContribution()
    → ContributionVerified(id, designer, dpcDelta=68, cetMinted=680)

  ContributionRegistry.activate(regId, 68)
    → ContributionActivated(regId, 68)

  ReputationNFT.onContributionVerified(designer, projectId, 68, DESIGN, 82)
    → ReputationMinted(tokenId, designer, projectId)  [if first in vertical]
    → ReputationUpdated(tokenId, 1, 68, 0, 0)         [tier=NEW]

  GovernanceAccrual.onContributionVerified(designer, DESIGN, 68)
    → WeightAccrued(designer, deltaWeight, newWeight, 68, 0)


═══ PHASE 2: DEMAND ACCUMULATION ═══

  Customers browse Otto Market → off-chain events

  DemandOracle.reportDemand({regId, VIEW, 1, 0x0, 0, now})
    → DemandReported(regId, VIEW, 1, 0, reporter)
    [Repeated for each view — batched in practice]

  DemandOracle.reportDemand({regId, WAITLIST, 1, buyer1, 0, now})
    → DemandReported(regId, WAITLIST, 1, 0, reporter)

  DemandOracle.reportDemand({regId, PURCHASE, 50, buyer, $500, now})
    → DemandReported(regId, PURCHASE, 50, $500, reporter)
    → ContributionRegistry.recordDemand(regId, 50, $500)
      → DemandRecorded(regId, 50, $500, 50)

  Threshold check passes (50 purchases >= minPurchases of 10):
    → ThresholdCrossed(regId, projectId, 50, waitlistCount, $500)


═══ PHASE 3: PRODUCTION TRIGGER ═══

  ProductionTrigger.onThresholdCrossed(regId, 50, USDC, $500)
    → USDC transferred to escrow
    → Partner auto-matched (best woodworking partner)
    → ProductionOrderCreated(orderId, regId, partnerId, 50, $500)

  Partner calls acceptOrder(orderId)
    → OrderStatusChanged(orderId, CREATED, ACCEPTED)

  AI generates manufacturing specs → startProduction(orderId, specHash)
    → OrderStatusChanged(orderId, ACCEPTED, IN_PRODUCTION)

  [Meanwhile: nested contributions enter the loop]
    AI Planner: ContributionRegistry.register(ai, projectId, CODE, planHash, [regId], true)
    Wood Supplier: ContributionRegistry.register(supplier, projectId, MATERIAL, ...)
    Carpenter: LaborAttestation.submitContribution(LABOR, hours, ...)
    Each goes through VERIFY → SCORE → CATALOG → ReputationNFT update


═══ PHASE 4: QC & DELIVERY ═══

  QC Inspector: submitQC(orderId, true, reportHash)
    → QCCompleted(orderId, inspector, true, reportHash)
    → OrderStatusChanged(orderId, QC_PENDING, QC_PASSED)

  Delivery confirmed: confirmDelivery(orderId)
    → OrderStatusChanged(orderId, QC_PASSED, DELIVERED)
    → EscrowReleased(orderId, partnerId, $500)


═══ PHASE 5: REVENUE SPLIT ═══

  RevenueRouter.split(regId, USDC, $500)
    → Reads provenance: [designer, aiPlanner, supplier, carpenter, inspector, curator]
    → Computes shares by roleWeight × DPC × quality
    → Applies agent tax on AI planner (40% → data/validators/treasury)

    → RevenueSplit(regId, USDC, $500, $25, $15, $460, $8.74, 6)
    → PayoutSent(regId, designer, $198.90, DESIGN, false)
    → PayoutSent(regId, aiPlanner, $13.10, CODE, true)  [after tax]
    → PayoutSent(regId, supplier, $139.92, MATERIAL, false)
    → PayoutSent(regId, carpenter, $167.83, LABOR, false)
    → PayoutSent(regId, inspector, $27.04, CURATION, false)
    → PayoutSent(regId, curator, $25.07, CURATION, false)
    → AgentTaxDistributed(regId, $4.37, $2.62, $1.75)


═══ PHASE 6: GOVERNANCE ACCRUAL ═══

  GovernanceAccrual.onRevenueEvent([designer, supplier, carpenter, ...], [amounts])
    → WeightAccrued(designer, delta, newWeight, 0, $198.90)
    → WeightAccrued(supplier, delta, newWeight, 0, $139.92)
    → WeightAccrued(carpenter, delta, newWeight, 0, $167.83)
    [etc. for each participant]

  ReputationNFT.onRevenueEarned(designer, projectId, $198.90)
    → ReputationUpdated(tokenId, ...)


═══ PHASE 7: FEEDBACK ═══

  DPCRegistry updates resonance scores based on demand/revenue data
    → ContributionRegistry.updateDPC(regId, newScore)
      → DPCUpdated(regId, 68, 74)  [resonance increased from sales]

  Next cycle: designer's higher DPC → larger split share → more governance weight
```

---

## 9. Upgrade Paths

### 9.1 Contract Upgrade Strategy

| Contract | Pattern | Rationale |
|----------|---------|-----------|
| ContributionRegistry | UUPS Proxy | Catalog schema evolves with new verticals and contribution types |
| DemandOracle | UUPS Proxy | Reporter logic, threshold algorithms, and anti-manipulation evolve |
| RevenueRouter | Immutable core + governed params | Split math must be trustworthy; fee params adjustable by governance |
| GovernanceAccrual | UUPS Proxy | Decay formula and accrual weights may need tuning |
| ReputationNFT | Immutable | Reputation records should never be rewritten; metadata URI updatable |
| ProductionTrigger | UUPS Proxy | Manufacturing partner interfaces evolve rapidly |

### 9.2 UUPS Upgrade Authorization

```solidity
// For all UUPS contracts:
function _authorizeUpgrade(address newImplementation)
    internal override onlyRole(UPGRADE_ROLE)
{
    // INVARIANT CHECKS (per contract):
    // ContributionRegistry: verify ContributionType enum unchanged
    // GovernanceAccrual: verify CAPITAL_TYPE exclusion persists
    // GovernanceAccrual: verify no transfer functions added
    // DemandOracle: verify reporter cooldown mechanism exists
    // ProductionTrigger: verify escrow isolation maintained
}
```

### 9.3 Governance-Driven Parameter Evolution

Parameters adjustable via LoopGovernor proposals (requires governance weight):

| Parameter | Contract | Default | Range | Quorum |
|-----------|----------|---------|-------|--------|
| `protocolFeeBps` | RevenueRouter | 500 | 100-1000 | 2/3 supermajority |
| `governanceAccrualBps` | RevenueRouter | 300 | 100-500 | Simple majority |
| `agentTaxBps` | RevenueRouter | 4000 | 1000-6000 | 2/3 supermajority |
| `roleWeights.*` | RevenueRouter | varies | 0-10000 | Simple majority |
| `decayLambdaBps` | GovernanceAccrual | 500 | 100-1000 | Simple majority |
| `tenureCapMonths` | GovernanceAccrual | 24 | 12-36 | Simple majority |
| `defaultThreshold.*` | DemandOracle | varies | varies | Simple majority |
| `defaultDeadline` | ProductionTrigger | 30 days | 7-90 days | Simple majority |

**Immutable (no governance can change):**
- `capital_governance_weight = 0` (GovernanceAccrual)
- `capital_role_weight = 0` (RevenueRouter — role 5 cannot be increased)
- Soulbound transfer restrictions (ReputationNFT, ContributionEquity)

### 9.4 Migration Path from Existing Contracts

The new contracts compose with (not replace) the existing stack:

```
MIGRATION PHASES:

  Phase 1 — Deploy ContributionRegistry + ReputationNFT
    - ContributionRegistry reads DPC scores from existing DPCRegistry
    - ReputationNFT mints from LaborAttestation verification events
    - No changes to existing contracts needed

  Phase 2 — Deploy DemandOracle + ProductionTrigger
    - DemandOracle registers reporters for each vertical
    - ProductionTrigger onboards first manufacturing partners
    - Wire DemandOracle → ContributionRegistry.recordDemand()
    - Wire DemandOracle → ProductionTrigger.onThresholdCrossed()

  Phase 3 — Deploy RevenueRouter + GovernanceAccrual
    - RevenueRouter replaces ad-hoc payment logic in verticals
    - GovernanceAccrual replaces simple GovernanceWeight.sol with full decay
    - Wire RevenueRouter → GovernanceAccrual.onRevenueEvent()
    - Wire RevenueRouter → ReputationNFT.onRevenueEarned()
    - Grant ACCRUAL_ROLE to ContributionRegistry + RevenueRouter
```

---

## 10. Security Summary

### 10.1 Attack Vectors & Mitigations

| Attack | Target | Mitigation |
|--------|--------|------------|
| **Sybil contributions** | ContributionRegistry | Multi-party attestation quorum (2-of-3), rotating attester limits, stake-backed attestation |
| **DPC score inflation** | GovernanceAccrual | Scores updated asynchronously, not in same tx as revenue split; sublinear (sqrt) scaling |
| **Demand signal manipulation** | DemandOracle | Reporter cooldown, `requiresPayment` threshold flag, minimum batch sizes |
| **Revenue front-running** | RevenueRouter | Split reads stored DPC scores (not freshly computed), atomic execution |
| **Escrow theft** | ProductionTrigger | Per-order isolation, checks-effects-interactions, no auto-cancellation |
| **Governance capture** | GovernanceAccrual | Capital earns zero weight (immutable), decay keeps weight active-contributor-weighted, logarithmic revenue scaling |
| **Flash loan governance** | GovernanceAccrual | Weight is non-transferable mapping, not a token — cannot be borrowed |
| **Reputation farming** | ReputationNFT | Trust tier requires both count AND quality score thresholds; soulbound prevents trading |
| **Provenance depth DoS** | ContributionRegistry | Max depth of 10 for on-chain traversal; off-chain indexer handles deeper chains |
| **Stale decay state** | GovernanceAccrual | Lazy decay with `batchApplyDecay` for governance snapshots |

### 10.2 Audit Priority (by risk)

1. **RevenueRouter** — handles real funds, atomic splits. Highest priority.
2. **ProductionTrigger** — escrow management. Second priority.
3. **GovernanceAccrual** — governance weight computation affects all governance decisions.
4. **DemandOracle** — demand manipulation could trigger unauthorized production runs.
5. **ContributionRegistry** — provenance integrity is critical but lower financial risk.
6. **ReputationNFT** — soulbound enforcement, lowest financial risk.

### 10.3 Recommended External Dependencies

- **OpenZeppelin Contracts v5.x** — UUPS, AccessControl, ERC-721, SafeERC20, ReentrancyGuard
- **PRBMath or Solmate** — WAD math for governance weight calculations (sqrt, ln, pow)
- **Chainlink VRF** — randomized QC audit selection (which orders get spot-checked)
- **Chainlink Automation** — deadline monitoring for ProductionTrigger

---

## 11. Gas Estimates (Polygon zkEVM)

| Operation | Estimated Gas | Est. Cost (at 50 gwei) |
|-----------|--------------|------------------------|
| Register contribution | ~120,000 | ~$0.006 |
| Record attestation | ~80,000 | ~$0.004 |
| Activate contribution | ~60,000 | ~$0.003 |
| Report demand (single) | ~90,000 | ~$0.005 |
| Report batch (100 events) | ~500,000 | ~$0.025 |
| Revenue split (6 participants) | ~350,000 | ~$0.018 |
| Governance weight accrual | ~100,000 | ~$0.005 |
| Mint reputation NFT | ~150,000 | ~$0.008 |
| Create production order | ~200,000 | ~$0.010 |
| Confirm delivery + split | ~450,000 | ~$0.023 |

**Total cost for full chair lifecycle (submit → deliver → split):** ~$0.10-0.15

---

*This architecture makes the Otto Loop programmable on-chain while keeping high-frequency operations (views, streams, ONEON queries) off-chain with Merkle settlement. Every contract composes with the existing OPRLP + Labor Attestation stack. The system is designed to evolve through governance proposals from active contributors — not investors, not founders.*

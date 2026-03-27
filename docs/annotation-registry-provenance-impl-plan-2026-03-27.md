# Annotation Registry & Provenance Graph — Implementation Plan

*Step 0 output for smart-contract-pipeline workflow | 2026-03-27*

---

## Scope

This plan covers **2 of 4 contracts** from the Memory Capsule Annotation & Royalty Architecture:
1. **AnnotationRegistry.sol** — Core on-chain registry for annotations on Memory Capsules
2. **ProvenanceGraph.sol** — Derivation DAG linking capsules to source annotations

The other 2 contracts (UsageOracle.sol, RoyaltyPool.sol) are being built in a parallel workflow task.

---

## 1. Project Scaffold

Create `/mnt/media/projects/annotation-contracts/` following the exact OPRLP pattern.

### Directory Structure

```
/mnt/media/projects/annotation-contracts/
├── foundry.toml
├── .env.example
├── .gitignore
├── README.md
│
├── src/
│   ├── interfaces/
│   │   ├── IAnnotationRegistry.sol
│   │   └── IProvenanceGraph.sol
│   │
│   ├── core/
│   │   ├── AnnotationRegistry.sol
│   │   └── ProvenanceGraph.sol
│   │
│   └── libraries/
│       └── DecayMath.sol
│
├── test/
│   ├── AnnotationRegistry.t.sol
│   ├── ProvenanceGraph.t.sol
│   └── integration/
│       └── AnnotateAndLink.t.sol
│
├── script/
│   └── DeployPhase1.s.sol
│
└── lib/
    ├── forge-std/
    └── openzeppelin-contracts/
```

### foundry.toml

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.24"
optimizer = true
optimizer_runs = 200
evm_version = "shanghai"
fuzz = { runs = 10000 }

remappings = [
    "@openzeppelin/contracts/=lib/openzeppelin-contracts/contracts/",
    "forge-std/=lib/forge-std/src/"
]

[fmt]
line_length = 120
tab_width = 4
bracket_spacing = true
```

### .gitignore

```
out/
cache/
.env
broadcast/
```

---

## 2. Interface Definitions

### 2.1 IAnnotationRegistry.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IAnnotationRegistry — Interface for annotation lookups and registration
/// @notice Read/write interface for the on-chain annotation registry
interface IAnnotationRegistry {
    /// @notice Annotation contribution types
    enum AnnotationType {
        Label,          // Classification, tagging, categorization
        Curation,       // Selection, filtering, quality gating
        TrainingSignal, // RLHF feedback, preference pairs, reward signals
        Correction,     // Error fix, factual correction, dedup
        Enrichment,     // Added context, cross-references, metadata
        Synthesis       // Combining multiple sources into refined knowledge
    }

    /// @notice Core annotation record stored on-chain
    struct Annotation {
        bytes32 capsuleId;          // Which Memory Capsule this annotates
        address annotator;          // Contributor's wallet address
        AnnotationType annType;     // What kind of contribution
        bytes32 contentHash;        // IPFS CID or SHA256 of off-chain content
        uint32 qualityScore;        // 0-10000 (basis points, set by validators)
        uint64 createdAt;           // Block timestamp of registration
        uint64 supersededAt;        // 0 if current; timestamp when superseded
        uint16 version;             // Annotation version (1, 2, etc.)
        bytes32 supersededBy;       // 0x0 if current; points to replacement annotationId
        bool active;                // false when superseded or deprecated
    }

    /// @notice Register a new annotation for a Memory Capsule
    /// @param capsuleId The capsule being annotated
    /// @param annType Type of contribution
    /// @param contentHash Hash of off-chain content (IPFS CID or SHA256)
    /// @param version Annotation version number
    /// @return annotationId The unique ID for this annotation
    function registerAnnotation(
        bytes32 capsuleId,
        AnnotationType annType,
        bytes32 contentHash,
        uint16 version
    ) external returns (bytes32 annotationId);

    /// @notice Update the quality score of an annotation (validators only)
    /// @param annotationId The annotation to update
    /// @param newScore New quality score in basis points (0-10000)
    function updateQualityScore(bytes32 annotationId, uint32 newScore) external;

    /// @notice Mark an annotation as superseded by a newer version
    /// @param oldAnnotationId The annotation being superseded
    /// @param newAnnotationId The replacement annotation
    function supersede(bytes32 oldAnnotationId, bytes32 newAnnotationId) external;

    /// @notice Get a single annotation by ID
    function getAnnotation(bytes32 annotationId) external view returns (Annotation memory);

    /// @notice Get all annotation IDs for a capsule
    function getAnnotationsForCapsule(bytes32 capsuleId) external view returns (bytes32[] memory);

    /// @notice Get all annotation IDs by an annotator
    function getAnnotationsByAnnotator(address annotator) external view returns (bytes32[] memory);

    /// @notice Get count of active annotations for a capsule
    function activeAnnotationCount(bytes32 capsuleId) external view returns (uint256);

    /// @notice Check if an annotation exists and is active
    function isActive(bytes32 annotationId) external view returns (bool);

    // Events
    event AnnotationRegistered(
        bytes32 indexed annotationId,
        bytes32 indexed capsuleId,
        address indexed annotator,
        AnnotationType annType,
        bytes32 contentHash,
        uint16 version
    );

    event QualityScoreUpdated(
        bytes32 indexed annotationId,
        uint32 oldScore,
        uint32 newScore
    );

    event AnnotationSuperseded(
        bytes32 indexed oldAnnotationId,
        bytes32 indexed newAnnotationId,
        uint64 supersededAt
    );
}
```

### 2.2 IProvenanceGraph.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title IProvenanceGraph — Interface for derivation tracking and attribution
/// @notice Tracks which annotations contributed to which capsules, with attribution weights
interface IProvenanceGraph {
    /// @notice A single derivation link: annotation → capsule
    struct Derivation {
        bytes32 childCapsuleId;     // The capsule that was created/improved
        bytes32 parentAnnotationId; // The annotation that contributed
        uint16 contributionWeight;  // 0-10000 basis points (how much this annotation contributed)
        uint64 recordedAt;          // Block timestamp
    }

    /// @notice Link a derived capsule back to a source annotation
    /// @param childCapsuleId The capsule that benefited
    /// @param parentAnnotationId The annotation that contributed
    /// @param contributionWeight How much this annotation contributed (0-10000 bps)
    function linkDerivation(
        bytes32 childCapsuleId,
        bytes32 parentAnnotationId,
        uint16 contributionWeight
    ) external;

    /// @notice Batch-link multiple annotations to a capsule
    /// @param childCapsuleId The derived capsule
    /// @param parentAnnotationIds Array of contributing annotations
    /// @param weights Array of contribution weights (must sum <= 10000)
    function batchLinkDerivations(
        bytes32 childCapsuleId,
        bytes32[] calldata parentAnnotationIds,
        uint16[] calldata weights
    ) external;

    /// @notice Get all source annotations for a capsule (with weights)
    function getAncestors(bytes32 capsuleId) external view returns (Derivation[] memory);

    /// @notice Get all capsules derived from an annotation
    function getDescendants(bytes32 annotationId) external view returns (Derivation[] memory);

    /// @notice Calculate attribution shares for a capsule's annotators
    /// @dev Returns parallel arrays: annotator addresses and their shares in bps
    /// @return annotators Array of unique annotator addresses
    /// @return shares Array of shares (sum = 10000 if any derivations exist)
    function attributionShares(bytes32 capsuleId)
        external view returns (address[] memory annotators, uint16[] memory shares);

    /// @notice Get the total contribution weight linked to a capsule (should be <= 10000)
    function totalWeight(bytes32 capsuleId) external view returns (uint16);

    // Events
    event DerivationLinked(
        bytes32 indexed childCapsuleId,
        bytes32 indexed parentAnnotationId,
        uint16 contributionWeight
    );
}
```

---

## 3. Core Contracts

### 3.1 AnnotationRegistry.sol — Key Design Decisions

**Pattern:** Follows DPCRegistry exactly — AccessControl for roles, mapping for storage, event emission.

**Roles:**
- `DEFAULT_ADMIN_ROLE` — admin (can grant other roles)
- `VALIDATOR_ROLE` — can update quality scores (same pattern as OPRLP)
- `GOVERNANCE_ROLE` — can force-supersede annotations

**Storage layout:**
```solidity
mapping(bytes32 => Annotation) private _annotations;         // annotationId → Annotation
mapping(bytes32 => bytes32[]) private _capsuleAnnotations;   // capsuleId → annotationId[]
mapping(address => bytes32[]) private _annotatorAnnotations; // annotator → annotationId[]
mapping(bytes32 => bool) private _exists;                    // annotationId → exists
uint256 private _totalAnnotations;                           // global counter
```

**annotationId generation:**
```solidity
annotationId = keccak256(abi.encodePacked(capsuleId, contentHash, msg.sender, _totalAnnotations));
```
Using `_totalAnnotations` as nonce instead of a separate nonce counter — simpler, guaranteed unique.

**Key invariants:**
1. `qualityScore` is always 0-10000 (enforced in `updateQualityScore`)
2. Only the original annotator or GOVERNANCE_ROLE can supersede
3. Superseded annotations have `active = false`, `supersededBy != 0`, `supersededAt != 0`
4. Once superseded, cannot be un-superseded (one-way transition)
5. `registerAnnotation` is permissionless (no stake requirement in Phase 1 — governance can add later)

**Supersession logic:**
```
supersede(oldId, newId):
  require old exists and is active
  require new exists and is active
  require old.capsuleId == new.capsuleId (same capsule)
  require msg.sender == old.annotator || hasRole(GOVERNANCE_ROLE)
  old.active = false
  old.supersededBy = newId
  old.supersededAt = block.timestamp
  emit AnnotationSuperseded(oldId, newId, block.timestamp)
```

### 3.2 ProvenanceGraph.sol — Key Design Decisions

**Pattern:** Similar to DPCRegistry — AccessControl, mapping storage.

**Roles:**
- `DEFAULT_ADMIN_ROLE` — admin
- `LINKER_ROLE` — authorized to create derivation links (Otto agents, capsule owners)

**Storage layout:**
```solidity
mapping(bytes32 => Derivation[]) private _ancestors;    // capsuleId → derivations from annotations
mapping(bytes32 => Derivation[]) private _descendants;  // annotationId → derivations to capsules
mapping(bytes32 => uint16) private _totalWeight;        // capsuleId → sum of contribution weights

IAnnotationRegistry public immutable registry;          // Reference to annotation registry
```

**Cross-contract reference:** ProvenanceGraph reads from AnnotationRegistry (to get annotator addresses for `attributionShares`). This follows the OPRLP pattern where GovernanceWeight reads from DPCRegistry.

**Key invariants:**
1. `contributionWeight` per link: 0-10000
2. Total weight per capsule: sum of all link weights <= 10000 (enforced in `linkDerivation`)
3. `parentAnnotationId` must exist in AnnotationRegistry (verified on write)
4. No duplicate links (same capsule + same annotation = revert)

**attributionShares logic:**
```
attributionShares(capsuleId):
  derivations = _ancestors[capsuleId]

  // Build unique annotator → total weight mapping
  for each derivation:
    annotator = registry.getAnnotation(derivation.parentAnnotationId).annotator
    annotatorWeights[annotator] += derivation.contributionWeight

  // Normalize to 10000 bps
  totalW = sum(annotatorWeights)
  for each annotator:
    shares[i] = (annotatorWeights[annotator] * 10000) / totalW

  return (annotators[], shares[])
```

This is O(N) where N = number of derivation links for a capsule. For view functions this is acceptable. Production capsules won't have >50 linked annotations.

### 3.3 DecayMath.sol — Library

**Reuses the OPRLP DPCMath pattern** but with annotation-specific parameters:

```solidity
library DecayMath {
    uint256 internal constant SCALE = 1e18;

    /// @notice Half-life for superseded annotations (6 months = 180 days)
    uint64 internal constant SUPERSESSION_HALF_LIFE = 180 days;

    /// @notice Floor: superseded annotations never decay below 1% of original royalty rate
    uint256 internal constant DECAY_FLOOR_BPS = 100; // 1% in basis points

    /// @notice Compute decay factor for a superseded annotation
    /// @param supersededAt Timestamp when annotation was superseded
    /// @param currentTime Current block timestamp
    /// @return factor Decay factor in WAD (1e18 = 100%, 1e16 = 1% floor)
    function computeSupersessionDecay(
        uint64 supersededAt,
        uint64 currentTime
    ) internal pure returns (uint256 factor);
}
```

The implementation follows DPCMath.computeDecay: piecewise linear interpolation between powers of 2, capped at floor.

---

## 4. Test Plan

### 4.1 AnnotationRegistry.t.sol

| Test | What it verifies |
|------|-----------------|
| `test_RegisterAnnotation` | Basic registration, ID generation, storage, event |
| `test_RegisterAnnotation_MultipleForSameCapsule` | Multiple annotations on one capsule, array growth |
| `test_RegisterAnnotation_DifferentTypes` | All 6 AnnotationType values work |
| `test_UpdateQualityScore` | Validator can update, score persists, event emitted |
| `test_UpdateQualityScore_RevertNonValidator` | Non-validator cannot update score |
| `test_UpdateQualityScore_RevertAbove10000` | Score > 10000 reverts |
| `test_Supersede_ByAnnotator` | Original annotator can supersede own annotation |
| `test_Supersede_ByGovernance` | GOVERNANCE_ROLE can supersede any annotation |
| `test_Supersede_RevertUnauthorized` | Random address cannot supersede |
| `test_Supersede_RevertAlreadySuperseded` | Cannot supersede an already-superseded annotation |
| `test_Supersede_RevertDifferentCapsule` | Cannot supersede with annotation from different capsule |
| `test_Supersede_SetsFieldsCorrectly` | active=false, supersededBy set, supersededAt set |
| `test_GetAnnotationsForCapsule` | Returns correct array of IDs |
| `test_GetAnnotationsByAnnotator` | Returns correct array of IDs |
| `test_ActiveAnnotationCount` | Decrements when annotations are superseded |
| `test_IsActive` | Returns true for active, false for superseded |
| `fuzz_RegisterAnnotation` | Fuzz capsuleId, contentHash, version — no reverts |
| `fuzz_UpdateQualityScore` | Fuzz score 0-10000 — all succeed |

### 4.2 ProvenanceGraph.t.sol

| Test | What it verifies |
|------|-----------------|
| `test_LinkDerivation` | Basic link, storage, event |
| `test_LinkDerivation_RevertNonLinker` | Non-LINKER_ROLE cannot link |
| `test_LinkDerivation_RevertInvalidAnnotation` | Cannot link to non-existent annotation |
| `test_LinkDerivation_RevertWeightExceeds10000` | Total weight per capsule cannot exceed 10000 |
| `test_LinkDerivation_RevertDuplicate` | Same capsule+annotation pair reverts on second link |
| `test_BatchLinkDerivations` | Batch link, array lengths match, total weight checked |
| `test_BatchLinkDerivations_RevertWeightOverflow` | Batch that would exceed 10000 reverts |
| `test_GetAncestors` | Returns all derivations for a capsule |
| `test_GetDescendants` | Returns all capsules derived from an annotation |
| `test_AttributionShares_SingleAnnotator` | Single annotator gets 10000 bps |
| `test_AttributionShares_MultipleAnnotators` | Shares sum to 10000, proportional to weights |
| `test_AttributionShares_SameAnnotatorMultipleAnnotations` | Weights aggregate per address |
| `test_AttributionShares_NoDerivedCapsule` | Returns empty arrays |
| `test_TotalWeight` | Tracks cumulative weight correctly |
| `fuzz_LinkDerivation_Weight` | Fuzz weight 1-10000, no reverts |

### 4.3 integration/AnnotateAndLink.t.sol

| Test | What it verifies |
|------|-----------------|
| `test_EndToEnd_RegisterAnnotateSupersede` | Register → link → supersede → verify attribution changes |
| `test_EndToEnd_MultipleCapsuleAnnotatorGraph` | Complex DAG with 3 capsules, 5 annotations, cross-links |

---

## 5. Deploy Script

### DeployPhase1.s.sol

Follows OPRLP pattern exactly:

```solidity
contract DeployPhase1 is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address admin = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        // 1. AnnotationRegistry — the foundation
        AnnotationRegistry registry = new AnnotationRegistry(admin);

        // 2. ProvenanceGraph — reads from registry
        ProvenanceGraph provenance = new ProvenanceGraph(
            address(registry),
            admin
        );

        vm.stopBroadcast();
    }
}
```

Deployment order: AnnotationRegistry first (ProvenanceGraph depends on it).

---

## 6. Implementation Steps (for coder agent)

### Step 1: Scaffold project (~5 min)
```bash
cd /mnt/media/projects
mkdir -p annotation-contracts/{src/{interfaces,core,libraries},test/integration,script}
cd annotation-contracts
forge init --no-commit --no-git .
# OR: manually create foundry.toml, install deps
forge install foundry-rs/forge-std --no-commit
forge install OpenZeppelin/openzeppelin-contracts --no-commit
git init && git add -A && git commit -m "chore: scaffold annotation-contracts Foundry project"
```

### Step 2: Write interfaces (~10 min)
- `src/interfaces/IAnnotationRegistry.sol` — exact spec from §2.1 above
- `src/interfaces/IProvenanceGraph.sol` — exact spec from §2.2 above
- Commit: `feat: add IAnnotationRegistry and IProvenanceGraph interfaces`

### Step 3: Write DecayMath library (~10 min)
- `src/libraries/DecayMath.sol` — port from DPCMath pattern, annotation-specific params
- Commit: `feat: add DecayMath library for supersession decay`

### Step 4: Write AnnotationRegistry.sol (~20 min)
- `src/core/AnnotationRegistry.sol` — full implementation per §3.1
- AccessControl with VALIDATOR_ROLE and GOVERNANCE_ROLE
- All storage mappings, registration, quality update, supersession
- Commit: `feat: implement AnnotationRegistry contract`

### Step 5: Write AnnotationRegistry.t.sol (~15 min)
- All unit tests from §4.1
- Run: `forge test --match-contract AnnotationRegistryTest -vvv`
- Commit: `test: add AnnotationRegistry unit tests`

### Step 6: Write ProvenanceGraph.sol (~20 min)
- `src/core/ProvenanceGraph.sol` — full implementation per §3.2
- AccessControl with LINKER_ROLE
- Cross-contract reference to IAnnotationRegistry
- Commit: `feat: implement ProvenanceGraph contract`

### Step 7: Write ProvenanceGraph.t.sol (~15 min)
- All unit tests from §4.2
- Run: `forge test --match-contract ProvenanceGraphTest -vvv`
- Commit: `test: add ProvenanceGraph unit tests`

### Step 8: Write integration test + deploy script (~10 min)
- `test/integration/AnnotateAndLink.t.sol` — end-to-end tests from §4.3
- `script/DeployPhase1.s.sol` — deployment script per §5
- Run: `forge test -vvv` (all tests)
- Commit: `feat: add integration tests and deploy script`

### Step 9: Final verification
```bash
forge build          # Must compile clean
forge test -vvv      # All tests pass
forge fmt --check    # Formatting clean
```

---

## 7. Key Decisions Summary

| Decision | Chosen | Why | Alternative Rejected |
|----------|--------|-----|---------------------|
| No staking in Phase 1 | Permissionless registration | Ship fast, add staking via governance later | Require stake upfront (blocks early adoption) |
| AccessControl over Ownable | Multi-role (validator, governance, linker) | DPCRegistry pattern, granular permissions | Ownable2Step (only one admin, too restrictive) |
| Nonce = totalAnnotations counter | Simple, guaranteed unique | No separate nonce mapping needed | Per-user nonce (extra storage, no benefit) |
| Weight cap enforcement on write | Revert if totalWeight > 10000 | Prevents invalid attribution graphs | Cap on read (allows invalid state) |
| No UUPS proxy in Phase 1 | Direct deployment | Simpler, auditable, follows OPRLP Phase 1 pattern | UUPS (adds complexity for testnet, can add Phase 2) |
| attributionShares computed on-chain | View function loops over derivations | Simple, correct, O(N) acceptable for <50 links | Off-chain only (breaks composability with RoyaltyPool) |
| Cross-contract via immutable ref | ProvenanceGraph stores IAnnotationRegistry | Gas-efficient, set once at construction | Interface call with dynamic address (mutable = risk) |

---

## 8. Gas Considerations

| Operation | Estimated Gas | Notes |
|-----------|-------------|-------|
| registerAnnotation | ~80,000 | 2 SSTORE + array push + event |
| updateQualityScore | ~30,000 | 1 SSTORE + event |
| supersede | ~45,000 | 2 SSTORE + event |
| linkDerivation | ~65,000 | 2 array pushes + weight update + validation + event |
| batchLinkDerivations (5 links) | ~250,000 | 5× linkDerivation minus call overhead |
| attributionShares (10 links) | ~50,000 (view) | O(N) loop, no storage writes |
| getAncestors | ~30,000 (view) | Array copy |

All well within Base L2 gas limits. Even at 10 gwei on Base, registerAnnotation costs ~$0.002.

---

## 9. Risks for This Scope

| Risk | Mitigation |
|------|------------|
| Array growth unbounded (capsuleAnnotations) | Practical limit: capsules won't have >100 annotations. Add pagination in Phase 2 if needed. |
| attributionShares O(N) on-chain | N < 50 in practice. Move to off-chain Shapley if N grows (Phase 2 design already accounts for this). |
| No upgrade path (no proxy) | Phase 1 testnet only. If logic needs changes, redeploy. Phase 2 adds UUPS for mainnet. |
| Duplicate annotation detection | keccak256(capsuleId, contentHash, sender, nonce) guarantees uniqueness. Same content from same sender = different nonce = different ID. |

---

*This plan is ready for the coder agent (Step 1 of the workflow). All contract specs, test lists, and implementation steps are defined.*

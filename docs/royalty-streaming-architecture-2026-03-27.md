# UsageOracle + RoyaltyPool — Implementation Architecture

*Authored by Otto (Architect Agent) | 2026-03-27 | Status: Ready for Implementation*

---

## Design: Perpetual Royalty Streaming & Distribution

### Problem

The AnnotationRegistry and ProvenanceGraph are built (parallel task). What's missing: the system that **detects usage events** and the system that **distributes money**. Without these two contracts, annotations exist on-chain but earn nothing.

### Existing Foundation (Built)

| Contract | Location | What It Provides |
|---|---|---|
| `AnnotationRegistry` | `src/core/AnnotationRegistry.sol` | `getAnnotation(id)` → annotator address, qualityScore, active, supersededAt |
| `ProvenanceGraph` | `src/core/ProvenanceGraph.sol` | `attributionShares(capsuleId)` → (address[], uint16[]) normalized to 10000 bps |
| `DecayMath` | `src/libraries/DecayMath.sol` | `computeSupersessionDecay(supersededAt, now)` → WAD factor (1e18 = 100%, floor at 1e16) |
| `IAnnotationRegistry` | `src/interfaces/IAnnotationRegistry.sol` | Full interface with Annotation struct, AnnotationType enum |
| `IProvenanceGraph` | `src/interfaces/IProvenanceGraph.sol` | Full interface with Derivation struct |

### Approach

Two new contracts. One library extension.

```
┌──────────────────┐         ┌──────────────────┐
│  UsageOracle     │────────►│  RoyaltyPool     │
│  (UUPS proxy)    │ events  │  (IMMUTABLE)     │
│                  │         │                  │
│  reportUsage()   │         │  accrue()        │
│  reportBatch()   │         │  claimRoyalties()│
│  authorize       │         │  getAccrued()    │
│  reporters       │         │  deposit()       │
└────────┬─────────┘         └────────┬─────────┘
         │                            │
    reads from                   reads from
         │                            │
         ▼                            ▼
┌──────────────────┐         ┌──────────────────┐
│AnnotationRegistry│         │ ProvenanceGraph  │
│ (quality, active)│         │ (attribution)    │
└──────────────────┘         │ DecayMath        │
                             └──────────────────┘
```

---

## Key Decisions

1. **UsageOracle = UUPS proxy** because new usage types and batch logic may change. **RoyaltyPool = IMMUTABLE** because financial guarantees must be trustless. Alternative: both UUPS (rejected — breaks perpetual promise).

2. **Pull-pattern claims** (annotator calls `claimRoyalties()`). Not push (auto-send). Why: push fails if annotator is a contract that reverts on receive; pull is the DeFi standard. Alternative: Sablier-style streaming (rejected — over-engineered for our frequency).

3. **Accrual happens in RoyaltyPool.accrue()**, called by UsageOracle after reporting. Not in the Oracle itself. Why: separation of concerns — Oracle knows what was used, Pool knows what it's worth. Alternative: Oracle computes royalties directly (rejected — Oracle upgrade could break financial logic).

4. **ERC-20 token ($KOIN) for deposits**, not native ETH. Why: annotation royalties are part of the $KOIN economy per Koink integration design. Alternative: multi-token (rejected for Phase 1 — adds complexity; easy to add later via a token whitelist).

5. **Usage weight is enforced in the Oracle, not the Pool.** Oracle maps UsageType → weight multiplier. Pool just receives (annotationId, capsuleId, weightedAmount). Why: Pool stays simple and immutable. Alternative: Pool computes weights (rejected — forces Pool upgrade to change weights).

---

## Contract 1: IUsageOracle.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IUsageOracle {
    enum UsageType { Read, Inference, License, Fork }

    struct UsageEvent {
        bytes32 capsuleId;
        bytes32 annotationId;   // 0x0 for capsule-level events
        UsageType usageType;
    }

    /// @notice Report a single usage event
    function reportUsage(
        bytes32 capsuleId,
        bytes32 annotationId,
        UsageType usageType
    ) external;

    /// @notice Batch-report multiple usage events (gas-efficient)
    function reportBatch(UsageEvent[] calldata events) external;

    /// @notice Get usage weight multiplier for a type
    function usageWeight(UsageType usageType) external view returns (uint32);

    /// @notice Set usage weight (governance only)
    function setUsageWeight(UsageType usageType, uint32 weight) external;

    /// @notice Get total usage events reported
    function totalReported() external view returns (uint256);

    // Events
    event UsageReported(
        bytes32 indexed capsuleId,
        bytes32 indexed annotationId,
        UsageType usageType,
        uint32 weight,
        uint64 timestamp
    );

    event UsageBatchReported(uint256 count, uint64 timestamp);
    event UsageWeightUpdated(UsageType usageType, uint32 oldWeight, uint32 newWeight);
}
```

## Contract 2: UsageOracle.sol

### Storage Layout

```solidity
contract UsageOracle is IUsageOracle, AccessControl {
    bytes32 public constant REPORTER_ROLE = keccak256("REPORTER_ROLE");
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    IAnnotationRegistry public immutable REGISTRY;
    IRoyaltyPool public immutable POOL;

    // UsageType => weight multiplier (default: Read=1, Inference=3, License=10, Fork=5)
    mapping(UsageType => uint32) private _weights;

    uint256 private _totalReported;
}
```

### Core Logic

- `reportUsage()`: validate annotation exists via `REGISTRY.getAnnotation()`, look up weight, call `POOL.accrue(annotationId, capsuleId, weight)`, emit event.
- `reportBatch()`: loop over events array, same validation per event, single batch call to Pool. Gas optimization: skip `getAnnotation` if annotationId is 0x0 (capsule-level event — no accrual, just tracking).
- `setUsageWeight()`: governance-only weight adjustment. Caps: weight must be 1-100.
- Authorization: `REPORTER_ROLE` for report functions (initially Otto's reporter address). `GOVERNANCE_ROLE` for parameter changes.

### Gas Considerations

- `reportBatch` with 50 events ≈ 200K gas on Base (~$0.01 at current rates).
- Each report calls `REGISTRY.getAnnotation()` (1 SLOAD + return) + `POOL.accrue()` (3 SSTOREs worst case).
- Optimization: skip the Registry call for capsule-level events (`annotationId == 0x0`).

---

## Contract 3: IRoyaltyPool.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

interface IRoyaltyPool {
    /// @notice Deposit $KOIN into the royalty pool
    function deposit(uint256 amount) external;

    /// @notice Accrue royalties for an annotation usage event (called by Oracle only)
    /// @param annotationId The annotation that was used
    /// @param capsuleId The capsule it belongs to
    /// @param usageWeight The weight multiplier for this usage type
    function accrue(bytes32 annotationId, bytes32 capsuleId, uint32 usageWeight) external;

    /// @notice Claim all accrued royalties for caller
    function claimRoyalties() external returns (uint256 claimed);

    /// @notice View accrued but unclaimed royalties for an address
    function getAccrued(address annotator) external view returns (uint256);

    /// @notice View total royalties ever accrued across all annotators
    function totalAccrued() external view returns (uint256);

    /// @notice View total royalties ever claimed
    function totalClaimed() external view returns (uint256);

    /// @notice View current pool balance
    function poolBalance() external view returns (uint256);

    // Events
    event Deposited(address indexed depositor, uint256 amount);
    event RoyaltyAccrued(
        bytes32 indexed annotationId,
        address indexed annotator,
        uint256 amount,
        uint32 qualityScore,
        uint256 decayFactor
    );
    event RoyaltyClaimed(address indexed annotator, uint256 amount);
}
```

## Contract 4: RoyaltyPool.sol

### Storage Layout

```solidity
contract RoyaltyPool is IRoyaltyPool {
    // IMMUTABLE — no proxy, no admin upgrades

    IAnnotationRegistry public immutable REGISTRY;
    IProvenanceGraph public immutable PROVENANCE;
    IERC20 public immutable TOKEN;           // $KOIN
    address public immutable ORACLE;          // Only UsageOracle can call accrue()

    uint256 public immutable BASE_RATE;       // Base royalty per usage event (in token wei)

    // Accrued royalties per annotator (pull-pattern)
    mapping(address => uint256) private _accrued;

    // Accounting
    uint256 private _totalAccrued;
    uint256 private _totalClaimed;
    uint256 private _totalDeposited;
}
```

### Core Logic: `accrue()`

```
accrue(annotationId, capsuleId, usageWeight):
    1. require(msg.sender == ORACLE)
    2. ann = REGISTRY.getAnnotation(annotationId)
    3. qualityFactor = ann.qualityScore  (0-10000 bps)
    4. decayFactor = ann.active ? 1e18 : DecayMath.computeSupersessionDecay(ann.supersededAt, now)
    5. (annotators, shares) = PROVENANCE.attributionShares(capsuleId)
    6. For each annotator with share > 0:
       royalty = BASE_RATE * usageWeight * qualityFactor * share * decayFactor
                 / (10000 * 10000 * 1e18)   // normalize bps × bps × WAD
       _accrued[annotator] += royalty
    7. _totalAccrued += totalRoyaltyThisEvent
    8. emit RoyaltyAccrued per annotator
```

### Core Logic: `claimRoyalties()`

```
claimRoyalties():
    1. amount = _accrued[msg.sender]
    2. require(amount > 0)
    3. _accrued[msg.sender] = 0     // Effects before interactions (CEI)
    4. _totalClaimed += amount
    5. require(TOKEN.balanceOf(address(this)) >= amount, "Pool underfunded")
    6. TOKEN.transfer(msg.sender, amount)
    7. emit RoyaltyClaimed
```

### Core Logic: `deposit()`

```
deposit(amount):
    1. require(amount > 0)
    2. TOKEN.transferFrom(msg.sender, address(this), amount)
    3. _totalDeposited += amount
    4. emit Deposited
```

### Immutability Contract

The RoyaltyPool has **no owner, no admin, no upgrade path**. Constructor sets all references:

```solidity
constructor(
    address registryAddr,
    address provenanceAddr,
    address tokenAddr,
    address oracleAddr,
    uint256 baseRate
) {
    require(registryAddr != address(0));
    require(provenanceAddr != address(0));
    require(tokenAddr != address(0));
    require(oracleAddr != address(0));
    require(baseRate > 0);

    REGISTRY = IAnnotationRegistry(registryAddr);
    PROVENANCE = IProvenanceGraph(provenanceAddr);
    TOKEN = IERC20(tokenAddr);
    ORACLE = oracleAddr;
    BASE_RATE = baseRate;
}
```

If governance wants to change parameters (base rate, token), they deploy a **new Pool** and migrate the Oracle to point at it. Old Pool continues operating for existing accrued claims. This is the immutability guarantee.

---

## Library: RoyaltyMath.sol

Small helper for the royalty calculation to keep RoyaltyPool clean:

```solidity
library RoyaltyMath {
    uint256 internal constant BPS = 10000;
    uint256 internal constant WAD = 1e18;

    /// @notice Compute royalty for a single annotator from a usage event
    /// @param baseRate Base royalty rate in token wei
    /// @param usageWeight Usage type multiplier (1-100)
    /// @param qualityScore Annotation quality (0-10000 bps)
    /// @param attributionShare Annotator's share of capsule (0-10000 bps)
    /// @param decayFactor Supersession decay (1e18 = 100%)
    /// @return royalty Amount of token to accrue
    function computeRoyalty(
        uint256 baseRate,
        uint32 usageWeight,
        uint32 qualityScore,
        uint16 attributionShare,
        uint256 decayFactor
    ) internal pure returns (uint256 royalty) {
        // baseRate * weight * (quality/10000) * (share/10000) * (decay/1e18)
        // Reorder multiplications to avoid overflow: multiply first, divide last
        royalty = baseRate
            * uint256(usageWeight)
            * uint256(qualityScore)
            * uint256(attributionShare)
            * decayFactor
            / (BPS * BPS * WAD);
    }
}
```

**Overflow analysis:** For `baseRate = 1e15` (0.001 token with 18 decimals), `weight = 100`, `quality = 10000`, `share = 10000`, `decay = 1e18`: product = 1e15 × 100 × 10000 × 10000 × 1e18 = 1e56, well within uint256 (max ~1.16e77). Safe.

---

## Files to Create

```
/mnt/media/projects/annotation-contracts/
├── src/
│   ├── interfaces/
│   │   ├── IUsageOracle.sol          # NEW — usage event interface
│   │   └── IRoyaltyPool.sol          # NEW — royalty distribution interface
│   ├── core/
│   │   ├── UsageOracle.sol           # NEW — UUPS proxy, authorized reporters
│   │   └── RoyaltyPool.sol           # NEW — IMMUTABLE, pull-pattern claims
│   └── libraries/
│       └── RoyaltyMath.sol           # NEW — royalty computation helper
├── test/
│   ├── UsageOracle.t.sol             # NEW
│   ├── RoyaltyPool.t.sol             # NEW
│   └── integration/
│       └── EndToEnd.t.sol            # NEW — register→link→use→accrue→claim
└── script/
    └── Deploy.s.sol                  # NEW — full deployment script
```

## Files NOT to Modify

- `AnnotationRegistry.sol` — complete, no changes needed
- `ProvenanceGraph.sol` — complete, no changes needed
- `DecayMath.sol` — complete, used as-is by RoyaltyPool

---

## Test Plan

### UsageOracle.t.sol

| Test | What It Verifies |
|---|---|
| `test_reportUsage_emitsEvent` | Single report emits UsageReported with correct weight |
| `test_reportUsage_revertsUnauthorized` | Non-REPORTER address cannot report |
| `test_reportUsage_revertsInvalidAnnotation` | Nonexistent annotationId reverts |
| `test_reportBatch_multipleEvents` | N events all processed, count incremented |
| `test_reportBatch_emptyArray` | Empty batch reverts or no-ops |
| `test_reportBatch_capsuleLevelEvent` | annotationId=0x0 events tracked but don't accrue |
| `test_setUsageWeight_governance` | Governance can change weights |
| `test_setUsageWeight_revertsUnauthorized` | Non-governance cannot change weights |
| `test_setUsageWeight_bounds` | Weight must be 1-100 |

### RoyaltyPool.t.sol

| Test | What It Verifies |
|---|---|
| `test_deposit_transfersTokens` | ERC20 transferred to pool, event emitted |
| `test_accrue_computesCorrectRoyalty` | Known inputs → expected royalty amount |
| `test_accrue_onlyOracle` | Non-oracle address cannot accrue |
| `test_accrue_decayedAnnotation` | Superseded annotation gets reduced royalty via DecayMath |
| `test_accrue_zeroQuality` | qualityScore=0 → 0 royalty |
| `test_accrue_multipleAnnotators` | Capsule with 3 annotators, shares split correctly |
| `test_claimRoyalties_pullPattern` | Annotator claims full accrued amount |
| `test_claimRoyalties_zeroBalance` | Claim with 0 accrued reverts |
| `test_claimRoyalties_insufficientPool` | Claim reverts if pool underfunded |
| `test_claimRoyalties_twoClaimsNoDouble` | Second claim after first returns 0 |
| `test_immutability_noAdmin` | No DEFAULT_ADMIN_ROLE, no owner, no upgrade functions |

### EndToEnd.t.sol

| Test | What It Verifies |
|---|---|
| `test_fullFlow` | Register annotation → link derivation → deposit $KOIN → report usage → claim royalties → verify balances |
| `test_supersessionDecay` | Register v1 → supersede with v2 → usage on v1's capsule → royalty reduced by decay |
| `test_multiAnnotatorSplit` | 3 annotators with 50/30/20 shares → royalties split proportionally |

---

## Deployment Order

1. **AnnotationRegistry** (already deployed by parallel task)
2. **ProvenanceGraph** (already deployed by parallel task, needs Registry address)
3. **UsageOracle** — needs Registry address + Pool address (deploy Pool first, or use a placeholder and set later)
4. **RoyaltyPool** — needs Registry, Provenance, Token, Oracle addresses, baseRate

**Dependency cycle resolution:** Oracle needs Pool address. Pool needs Oracle address. Solution: deploy Pool first with Oracle address = deployer. Then deploy Oracle with Pool address. Then re-deploy Pool with correct Oracle address. OR: Pool takes Oracle address in constructor, so deploy Oracle first with Pool = address(0), then deploy Pool with Oracle address, then call Oracle.setPool(poolAddress). **Chosen approach:** Oracle is UUPS, so deploy Oracle first → deploy Pool with Oracle address → Oracle admin calls `setPool(poolAddress)`. Pool is immutable so it must have the correct Oracle at construction.

---

## Risks

| Risk | Mitigation |
|---|---|
| Oracle-Pool deployment ordering | Oracle is UUPS — deploy first, set Pool reference post-deploy via `setPool()` |
| Rounding dust in RoyaltyMath | Floor division. Over 1M events, dust < 1 token. Acceptable. |
| Pool insolvency (more accrued than deposited) | `claimRoyalties` checks `TOKEN.balanceOf` before transfer. Graceful revert, not loss. |
| Gas spike from large `attributionShares` call in accrue | ProvenanceGraph limits derivations per capsule (10000 bps cap → practical max ~100 links). O(N²) in attributionShares but N < 100. |
| Oracle compromise (reporter key leak) | Revoke REPORTER_ROLE, grant to new address. Oracle is upgradeable so logic can be patched. Pool is immutable — unaffected. |

---

## Implementation Order for Step 1

1. `src/interfaces/IUsageOracle.sol` + `src/interfaces/IRoyaltyPool.sol`
2. `src/libraries/RoyaltyMath.sol`
3. `src/core/UsageOracle.sol`
4. `src/core/RoyaltyPool.sol`
5. `test/UsageOracle.t.sol`
6. `test/RoyaltyPool.t.sol`
7. `test/integration/EndToEnd.t.sol`
8. `script/Deploy.s.sol`
9. `forge test` — all green

Estimated implementation cost: ~$3-4 (single task with Solidity engineer agent).

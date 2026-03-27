# Security Audit: Annotation & Royalty Contract Suite

**Audit Date:** 2026-03-27
**Auditor:** Otto (Security Audit Agent)
**Scope:** `/mnt/media/projects/annotation-contracts/src/`
**Solidity Version:** ^0.8.24 (built-in overflow protection)
**Frameworks:** OpenZeppelin AccessControl, UUPS, SafeERC20

## Contracts Audited

| Contract | LOC | Role |
|---|---|---|
| `AnnotationRegistry.sol` | 135 | On-chain annotation registry |
| `ProvenanceGraph.sol` | 162 | Derivation DAG and attribution shares |
| `RoyaltyPool.sol` | 153 | Immutable pull-pattern royalty distribution |
| `UsageOracle.sol` | 135 | UUPS-upgradeable usage event reporter |
| `DecayMath.sol` | 50 | Supersession decay (6-month half-life, 1% floor) |
| `RoyaltyMath.sol` | 31 | Overflow-safe royalty computation |

## Summary

| Severity | Count |
|---|---|
| **Critical** | 3 |
| **High** | 4 |
| **Medium** | 5 |
| **Low** | 4 |
| **Informational** | 3 |

---

## CRITICAL Findings

### C-1: Unbounded Accrual Without Solvency Check — RoyaltyPool Insolvency

**Contract:** `RoyaltyPool.sol` lines 79-113
**Category:** Economic / Fund Safety

`accrue()` increases `_accrued[annotator]` with no check against the pool's token balance. The oracle can report unlimited usage events, inflating accrued royalties far beyond actual deposits. First claimers drain the pool; later annotators' `claimRoyalties()` reverts at the balance check (line 125).

This is not theoretical — it's the expected state during normal operation unless deposits consistently exceed accruals. The pool makes perpetual promises it may not be able to keep.

**Impact:** Annotators lose accrued royalties. Trust in the system collapses. Race to claim creates MEV extraction opportunity.

**Recommended Fix:**
```solidity
// Option A: Check solvency at accrual time
uint256 poolBalance = TOKEN.balanceOf(address(this));
uint256 outstanding = _totalAccrued - _totalClaimed;
require(outstanding + totalThisEvent <= poolBalance, "RoyaltyPool: underfunded");

// Option B: Pro-rata claims when underfunded (preferred — never reverts)
function claimRoyalties() external returns (uint256 claimed) {
    uint256 owed = _accrued[msg.sender];
    require(owed > 0, "nothing to claim");
    uint256 balance = TOKEN.balanceOf(address(this));
    uint256 outstanding = _totalAccrued - _totalClaimed;
    claimed = (owed * balance) / outstanding; // pro-rata
    _accrued[msg.sender] -= claimed;
    _totalClaimed += claimed;
    TOKEN.safeTransfer(msg.sender, claimed);
}
```

---

### C-2: Permissionless Annotation Registration — Spam / DoS Vector

**Contract:** `AnnotationRegistry.sol` line 36
**Category:** Griefing / Denial of Service

`registerAnnotation()` has **no access control** — anyone can register unlimited annotations for any capsule. Each annotation is pushed to `_capsuleAnnotations[capsuleId]` (unbounded array). Consequences:

1. `getAnnotationsForCapsule()` becomes O(n) and eventually exceeds block gas limit
2. `activeAnnotationCount()` iterates the full array (line 119) — DoS at ~thousands of entries
3. ProvenanceGraph's `attributionShares()` does an external call per derivation — compounds the gas problem
4. Spam annotations dilute quality signal and make curation harder

**Cost to attack:** ~21,000 gas per annotation + calldata. At 30 gwei, ~$0.001 per annotation. 1M annotations costs ~$1,000 and permanently bricks `getAnnotationsForCapsule` for that capsule.

**Impact:** Any capsule can be made unusable. Downstream contracts (ProvenanceGraph, RoyaltyPool) that iterate over annotations are affected.

**Recommended Fix:**
```solidity
// Add ANNOTATOR_ROLE or registration fee
bytes32 public constant ANNOTATOR_ROLE = keccak256("ANNOTATOR_ROLE");

function registerAnnotation(...) external onlyRole(ANNOTATOR_ROLE) returns (bytes32) {
    // ... existing logic
}

// AND/OR: pagination for reads
function getAnnotationsForCapsulePaginated(bytes32 capsuleId, uint256 offset, uint256 limit)
    external view returns (bytes32[] memory)
```

---

### C-3: Admin Key Concentration — Single Address Controls Entire System

**Contracts:** All four
**Category:** Access Control / Centralization

Constructor patterns grant a single `admin` address ALL roles:

| Contract | Roles Granted to Admin |
|---|---|
| AnnotationRegistry | DEFAULT_ADMIN + VALIDATOR + GOVERNANCE |
| ProvenanceGraph | DEFAULT_ADMIN + LINKER |
| UsageOracle | DEFAULT_ADMIN + REPORTER + GOVERNANCE |
| RoyaltyPool | (immutable, no admin — good) |

A compromised admin key can:
- Set arbitrary quality scores (VALIDATOR) → inflate/deflate royalties
- Supersede any annotation (GOVERNANCE) → trigger decay on victims
- Create/remove derivation links (LINKER) → redirect attribution
- Report fake usage events (REPORTER) → drain the pool
- Upgrade the oracle to a malicious implementation (DEFAULT_ADMIN on UUPS)
- Grant all these roles to any address

**Impact:** Total system takeover. Admin IS the system.

**Recommended Fix:**
- Phase 1: Use a multisig (e.g., Gnosis Safe) as admin, not an EOA
- Phase 2: Add timelocks to admin actions (OpenZeppelin TimelockController)
- Phase 3: Separate role management — different multisigs for VALIDATOR vs GOVERNANCE vs REPORTER
- Production: Renounce DEFAULT_ADMIN_ROLE after initial setup is complete

---

## HIGH Findings

### H-1: VALIDATOR_ROLE as Unchecked Oracle — Quality Score Manipulation

**Contract:** `AnnotationRegistry.sol` line 68
**Category:** Oracle Trust / Centralization

`updateQualityScore()` allows any VALIDATOR_ROLE holder to set any annotation's quality to any value (0-10000) with no:
- Rate limiting
- Maximum change per update
- Multi-validator consensus
- Historical score tracking

Since royalty = `baseRate * usageWeight * qualityScore * attributionShare * decayFactor`, a corrupt validator can multiply their own annotations' royalties by 10000x vs competitors.

**Impact:** Complete royalty distribution manipulation.

**Recommended Fix:**
```solidity
// Rate limit quality score changes
uint32 public constant MAX_SCORE_DELTA = 1000; // max 10% change per update
mapping(bytes32 => uint64) private _lastScoreUpdate;
uint64 public constant SCORE_COOLDOWN = 1 days;

function updateQualityScore(bytes32 annotationId, uint32 newScore) external onlyRole(VALIDATOR_ROLE) {
    require(block.timestamp >= _lastScoreUpdate[annotationId] + SCORE_COOLDOWN);
    uint32 oldScore = _annotations[annotationId].qualityScore;
    uint32 delta = newScore > oldScore ? newScore - oldScore : oldScore - newScore;
    require(delta <= MAX_SCORE_DELTA, "delta too large");
    // ...
}
```

---

### H-2: ProvenanceGraph.attributionShares() — O(n^2) Gas Bomb

**Contract:** `ProvenanceGraph.sol` lines 104-156
**Category:** Denial of Service

`attributionShares()` contains a nested loop (lines 119-138): for each derivation, it searches through `tempAnnotators` linearly. With `n` derivations:
- Worst case: O(n^2) iterations + n external calls to `REGISTRY.getAnnotation()`
- Each external call costs ~2600 gas (cold SLOAD) + cross-contract overhead
- At n=100 derivations: ~10,000 iterations + 100 external calls ≈ 3-5M gas
- At n=500: ~250,000 iterations ≈ OOG

This function is called by `RoyaltyPool.accrue()` on EVERY usage event. If a capsule accumulates many derivation links, all future royalty accruals for that capsule will fail.

**Impact:** Permanent DoS on royalty distribution for popular capsules.

**Recommended Fix:**
- Cap max derivations per capsule (e.g., 50)
- Use a mapping for annotator deduplication instead of linear search
- Pre-compute and cache attribution shares, update on link changes

---

### H-3: Supersession Authorization Allows Cross-Annotator Supersession

**Contract:** `AnnotationRegistry.sol` lines 79-98
**Category:** Access Control

The `supersede()` function checks that `msg.sender == oldAnn.annotator || hasRole(GOVERNANCE_ROLE, msg.sender)`. But there is **no check on who created `newAnnotationId`**. This means:

1. An original annotator can supersede their own annotation and point `supersededBy` to ANY other annotation (even from a different annotator on the same capsule). The old annotation starts decaying — reducing its royalties.
2. GOVERNANCE_ROLE can supersede anyone's annotation with anyone else's.

While supersession itself doesn't redirect royalties (it only triggers decay), it allows adversarial annotators to forcibly decay competitors' annotations by registering a new annotation on the same capsule and superseding the competitor's work.

**Impact:** Any annotator can trigger 6-month decay on any other annotator's work on the same capsule, if they also register an annotation there.

**Recommended Fix:**
```solidity
// Require new annotation is by same annotator, or governance approves
require(
    newAnn.annotator == oldAnn.annotator || hasRole(GOVERNANCE_ROLE, msg.sender),
    "AnnotationRegistry: new annotation must be from same annotator"
);
```

---

### H-4: REPORTER_ROLE Can Inflate Royalties Arbitrarily

**Contract:** `UsageOracle.sol` lines 68-86, 89-111
**Category:** Oracle Trust

REPORTER_ROLE can report unlimited usage events for any annotation/capsule combination. There is no:
- Deduplication of usage events (same capsule+annotation can be reported infinitely)
- Rate limiting per capsule or per annotation
- Proof of actual usage (it's a trusted reporter model)

A compromised or colluding reporter can inflate any annotator's royalties by batch-reporting fake usage events.

**Impact:** Pool draining via fake usage inflation. Combined with C-1, makes insolvency trivial.

**Recommended Fix:**
- Add per-annotation rate limits (e.g., max 10 reports per annotation per hour)
- Deduplicate within time windows
- Multiple reporter quorum for high-value events
- On-chain usage proofs (Merkle roots from off-chain systems)

---

## MEDIUM Findings

### M-1: ProvenanceGraph Attribution Rounding — Last Annotator Bias

**Contract:** `ProvenanceGraph.sol` lines 146-155
**Category:** Rounding / Fairness

The normalization loop assigns `shares[i] = uint16((tempWeights[i] * 10000) / totalW)` for all but the last annotator, who gets `10000 - distributed`. Due to integer truncation, earlier annotators lose up to 1 bps each, and the last annotator receives the accumulated remainder.

With 100 annotators, the last could receive up to 99 bps more than their fair share (0.99% bonus). Over many capsules this creates a systematic bias.

**Impact:** Unfair royalty distribution. Ordering-dependent bias.

**Recommended Fix:** Use a standard "largest remainder" method or sort by weight before assigning to minimize bias.

---

### M-2: UsageOracle.setPool() — Pre-Set Admin Takeover Window

**Contract:** `UsageOracle.sol` lines 60-65
**Category:** Access Control

Between `initialize()` and `setPool()`, the admin has a window to set the pool to a malicious contract. While `setPool` has a one-time guard (`require(address(pool) == address(0))`), there is no timelock or multi-sig requirement.

If admin calls `setPool(maliciousPool)` before the legitimate pool is set, all future royalty accruals go to the attacker's contract.

**Impact:** Permanent redirection of all royalty accruals.

**Recommended Fix:** Set pool address in `initialize()` (accept address(0) initially, then require governance vote to set), or require pool address at proxy deployment time.

---

### M-3: No Annotation Deactivation/Slashing Mechanism

**Contract:** `AnnotationRegistry.sol`
**Category:** Missing Feature / Governance Gap

There is no way to deactivate a malicious or low-quality annotation except through `supersede()`, which requires either the annotator's cooperation or GOVERNANCE_ROLE action. There is no:
- Slashing for proven-bad annotations
- Community flagging mechanism
- Quality score threshold for automatic deactivation

A spam annotator who registers 1000 low-quality annotations can only be stopped one-by-one via governance supersession.

**Impact:** No efficient mechanism to remove bad actors from the system.

**Recommended Fix:** Add a `deactivate(bytes32 annotationId)` function callable by GOVERNANCE_ROLE that sets `active = false` without requiring a replacement annotation.

---

### M-4: DecayMath Linear Interpolation Approximation Error

**Contract:** `DecayMath.sol` lines 37-42
**Category:** Mathematical Precision

The decay function uses linear interpolation between half-life points. True exponential decay: `0.5^(t/halfLife)`. The linear approximation overestimates the actual decay factor (i.e., pays MORE royalties than intended for superseded annotations).

Maximum error at the 25% mark of each half-life period: ~6% overestimate. This compounds: after 5 half-lives with maximum error, an annotation could receive 1.34x its intended royalty rate.

**Impact:** Superseded annotations earn more than designed. Low severity because the floor (1%) still applies.

**Recommended Fix:** Use a tighter approximation (quadratic interpolation or lookup table) or accept the overestimate as a feature (graceful decay).

---

### M-5: RoyaltyPool Claim Ordering Depends on Underfunding Check Position

**Contract:** `RoyaltyPool.sol` lines 116-130
**Category:** Code Quality / CEI Pattern

The claim function follows CEI (Checks-Effects-Interactions) for reentrancy safety, which is correct. However, the solvency check (`TOKEN.balanceOf(address(this)) >= claimed`) is placed AFTER zeroing `_accrued`. While a revert restores state, this ordering is confusing and could mislead future auditors or forked implementations into thinking the balance check is insufficient.

**Recommended Fix:** Move the balance check before zeroing _accrued for clarity:
```solidity
require(TOKEN.balanceOf(address(this)) >= claimed, "RoyaltyPool: underfunded");
_accrued[msg.sender] = 0;  // then zero
```

---

## LOW Findings

### L-1: No Event Emission for setPool in Interface

**Contract:** `IUsageOracle.sol` / `UsageOracle.sol`

`PoolSet` event is defined in the interface and emitted in `setPool()`. Correct. No issue here — noted as reviewed.

Actually: `IUsageOracle` declares `event PoolSet(address indexed pool)` but `UsageOracle` also inherits `IUsageOracle`, so the event is properly inherited. Clean.

### L-2: Annotation ID Predictability

**Contract:** `AnnotationRegistry.sol` line 44

Annotation IDs are computed as `keccak256(capsuleId, contentHash, msg.sender, _totalAnnotations)`. Since `_totalAnnotations` is public and increments by 1, the next annotation ID is predictable by anyone who knows the capsuleId and contentHash. This could enable front-running of specific annotations.

**Impact:** Low — front-running an annotation registration provides no direct economic advantage in the current design. Could matter if governance votes reference specific annotation IDs.

### L-3: Missing Zero-Address Check on Annotator in registerAnnotation

**Contract:** `AnnotationRegistry.sol` line 36

`msg.sender` is used as the annotator address. While `msg.sender` can never be `address(0)` in an EVM transaction, the contract stores it without any documentation that contract-based annotators should handle their own receive logic for claims.

**Impact:** If a contract registers an annotation and later cannot receive tokens, their royalties are locked. Not a vulnerability in this contract, but worth documenting.

### L-4: Batch reportUsage Gas Limit Risk

**Contract:** `UsageOracle.sol` line 89

`MAX_BATCH_SIZE = 100`, but each element in the batch triggers 2+ external calls (registry validation + pool accrual, where accrual itself makes 2+ external calls). Total: 100 * ~4 external calls = ~400 cross-contract calls. On a congested L2 or L1, this could exceed block gas limits.

**Impact:** Batch reports with close to 100 events may revert. Operators must test empirically.

**Recommended Fix:** Reduce MAX_BATCH_SIZE to 25-50, or document the gas profile.

---

## INFORMATIONAL

### I-1: Missing DeprecationBonus Contract

The architecture documents specify a 10x deprecation bonus when annotations are formally deprecated (not just superseded). This contract does not exist in the current codebase. The royalty system is incomplete without it.

### I-2: No Pausability

None of the contracts implement a pause mechanism. If a critical vulnerability is discovered post-deployment, there is no way to freeze operations. RoyaltyPool is intentionally immutable, but AnnotationRegistry and ProvenanceGraph could benefit from Pausable.

### I-3: OpenZeppelin Version Not Pinned

`foundry.toml` specifies `solc = "0.8.24"` but the OpenZeppelin contracts version is imported as a git submodule without version pinning. Future `forge update` could pull breaking changes.

---

## Audit Matrix

| Vector | Status | Notes |
|---|---|---|
| Reentrancy | **PASS** | CEI pattern in RoyaltyPool. No callback-capable external calls in state-changing paths. |
| Integer Overflow/Underflow | **PASS** | Solidity 0.8.24 built-in checks. RoyaltyMath overflow analysis in comments is correct. |
| Access Control Gaps | **FAIL** | C-2 (permissionless registration), C-3 (admin concentration), H-3 (cross-annotator supersession) |
| Oracle Manipulation | **FAIL** | H-1 (quality score), H-4 (usage reporting) — both single-entity controlled |
| Royalty Rounding Errors | **WARN** | M-1 (last-annotator bias), M-4 (decay approximation overestimate) |
| Annotation Spam / Griefing | **FAIL** | C-2 — zero-cost spam bricks per-capsule reads |
| Sybil on Quality Scoring | **WARN** | Not directly exploitable on-chain (validator is permissioned), but compromised validator = game over (H-1) |
| Front-running Deprecation | **PASS** | No deprecation bonus contract exists yet. Supersession front-running has limited economic impact. |
| Fund Safety | **FAIL** | C-1 — pool insolvency from uncapped accrual |

---

## Priority Fix Order

1. **C-1** — Add solvency guard or pro-rata claims to RoyaltyPool (deploy-blocking)
2. **C-2** — Gate `registerAnnotation` with a role or fee (deploy-blocking)
3. **C-3** — Deploy with multisig admin, add timelocks (deploy-blocking)
4. **H-2** — Cap derivations per capsule, optimize attributionShares (deploy-blocking for gas safety)
5. **H-1** — Add rate limits and max delta to quality score updates
6. **H-3** — Restrict supersession to same-annotator unless governance
7. **H-4** — Add reporter rate limiting and deduplication
8. **M-1 through M-5** — Address before mainnet, acceptable for testnet

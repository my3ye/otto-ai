---
name: Royalty Streaming Contracts Review
description: RoyaltyPool + UsageOracle Solidity review (2026-03-27, WF Step 2): NEEDS_CHANGES. 1 critical: capsule/annotation ID cross-contamination not validated in RoyaltyPool.accrue(). 93 tests all pass.
type: project
---

# Royalty Streaming Contracts Review — 2026-03-27

**Verdict: NEEDS_CHANGES**

## Critical Issues

1. **`RoyaltyPool.accrue()` does not validate `ann.capsuleId == capsuleId`**: The pool fetches quality/decay from `annotationId` and attribution shares from `capsuleId` independently — if they don't match, cross-capsule royalty contamination occurs. Fix: add `require(ann.capsuleId == capsuleId, "RoyaltyPool: capsule mismatch")` in the immutable RoyaltyPool (not just the upgradeable Oracle). Same gap exists in `UsageOracle.reportUsage()` but must be fixed in Pool since Pool is immutable and must not trust Oracle inputs blindly.

## Warnings

2. `attributionShares()` in ProvenanceGraph has O(n²) deduplication loop — gas risk for capsules with many derivation links
3. `reportBatch()` has no maximum size check — could hit block gas limit
4. `claimRoyalties()` CEI comment is slightly misleading: `TOKEN.balanceOf()` external call placed after effects but before transfer. Not exploitable with standard ERC-20, but comment implies cleaner ordering than exists.
5. `_totalDeposited` doesn't track direct token transfers (only via `deposit()`) — monitoring gap
6. No `solvencyDeficit()` view function — off-chain tools can't easily check if pool can fulfill all outstanding claims

## What's Good

- RoyaltyPool is truly immutable (no admin, no upgrade path) — perpetual royalty guarantee is credible
- UUPS Oracle with proper `_disableInitializers()` in constructor — no uninitialized impl exploit
- CEI is correct for the reentrancy vector that matters (state zeroed before `TOKEN.transfer`)
- Fuzz test on quality range
- Deployment script correctly resolves the dependency cycle (Oracle → Pool → wire)
- `setPool()` one-time guard prevents pool address from being changed
- DecayMath floor (1%) ensures superseded annotations never earn zero

## Pattern

In multi-contract systems where an immutable contract receives inputs from an upgradeable contract: the immutable contract MUST re-validate inputs it can check independently. The upgradeable contract may be compromised or upgraded to pass malicious data. RoyaltyPool is immutable and trusts Oracle inputs — it should validate the annotation→capsule relationship using its own registry access, which it already has.

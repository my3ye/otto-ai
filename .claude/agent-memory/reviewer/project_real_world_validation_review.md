---
name: Real-World Validation Models synthesis review
description: Step 2 validation of MY3YE live organism model research (designer→AI→production→demand→distribute→govern). NEEDS_CHANGES (7.5/10). Key issue: VALIDATOR_ROLE oracle centralization not flagged before recommending testnet deployment. Known RoyaltyPool cross-capsule bug not surfaced before recommending integration.
type: project
---

Validation of WF "Research Real-World Validation Models / Step 2: Validation" (2026-03-28).

**VERDICT: NEEDS_CHANGES (7.5/10)**

Main synthesis contribution is correct: DPC governance contracts and annotation royalty contracts are implemented (not gaps). External evidence is well-sourced across all 4 domains.

**Critical issues:**
1. Action 1 recommends testnet deployment for "investor narrative + grant applications" without flagging that VALIDATOR_ROLE gives a single deployer absolute unilateral control over ALL DPC scores (no timelock, no multisig, no rate limit). This was a prior CRITICAL security audit finding — deploying without caveat misleads investors/grant reviewers.
2. Action 2 recommends wiring annotation-contracts RoyaltyPool.accrue() without flagging the known cross-capsule bug: accrue() accepts annotationId + capsuleId as separate params but never validates they belong together — cross-capsule royalty contamination possible. Bug confirmed still present.

**Warnings:**
1. DPCMath.sol file location imprecise — it's in `src/libraries/`, not `src/` directly. Minor but could mislead a dev.
2. Audius 90% sustainability flagged correctly as uncertain — good.
3. oprlp-contracts IS the 505 Systems DPC implementation (OPRLP = On-chain Participation, Rotation, Leadership Protocol) — not two parallel builds.

**What's good:** Demand manufacturing analysis strong and well-reasoned. 50-pre-order threshold well-justified from Shapeways/Local Motors failure analysis. Compressed handoff high quality.

**Why:** Investor/grant reviewers WILL look at the contracts. Unaddressed VALIDATOR_ROLE centralization is a trust-killer. Must be called out before promotion.
**How to apply:** Always cross-check security audit memory before recommending contract deployment for external audiences.

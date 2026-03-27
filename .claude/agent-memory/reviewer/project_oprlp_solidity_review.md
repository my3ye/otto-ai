---
name: OPRLP Phase 1 Solidity Review
description: Code review of OPRLP Phase 1 Solidity contracts — 3 criticals (quorum, recall threshold, recall weight), 5 warnings
type: project
---

Review of OPRLP Phase 1 contracts (task 5453176b, 2026-03-27, WF Step 2): NEEDS_CHANGES.

**Why:** Governance contracts with security-critical constants that are declared but never enforced.

**Critical issues:**
1. `ElectionEngine.sol:27` — `QUORUM_BPS=1500` defined but `tallyAndSeat()` never checks quorum
2. `CouncilManager.sol:27` — `RECALL_SIGNATURE_BPS=1000` defined but `executeRecall()` never enforces it
3. `CouncilManager.sol:156-161` — recall votes count raw addresses, not DPC-weighted

**Warnings:**
4. `GovernanceWeight.sol:16,31-43` — `maxWeightBps` adjustable but never applied in `getVotingWeight()`
5. `DPCRegistry.sol:118` — `getScoreDetails()` returns decayed value in field named `rawScore` (semantic mismatch)
6. `CouncilManager.sol:224-226` — displaced seat holder gets no cooldown when seat forcibly overwritten
7. `GovernanceWeight.sol:47` — `getTotalActiveWeight()` unbounded O(n) iteration, will fail at scale
8. `RankedChoice.sol:88` — IRV tie-breaking order-dependent (candidacy declaration order) — undocumented

**Pattern:** governance constants (quorum, thresholds) declared as named constants must be actively enforced at their enforcement point, not just stored. Common pattern: constant defined at top, never wired to the actual check.

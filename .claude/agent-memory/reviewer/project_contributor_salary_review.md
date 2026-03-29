---
name: contributor_salary_contract_review
description: Contributor salary contract system preliminary review (plan 9a40a60f, 2026-03-29): PRELIMINARY, contracts not written yet. Explainer 7/10, 3 criticals.
type: project
---

On-Chain Contributor Salary Contract system (9k/month cap, treasury gate): PRELIMINARY review, plan 9a40a60f, 2026-03-29.

**Why:** Plan was triggered by Mev's WhatsApp directive for transparent founder salary contract — same structure for all contributors, treasury-gated, hard cap.

**State at review time:**
- t1 (architect): RUNNING (opus)
- t2 (ContributorSalary.sol + TreasuryGate.sol): PENDING — blocked on t1
- t3 (security audit): RUNNING PREMATURELY (DAG bug — started before t2)
- t4 (explainer): COMPLETED at my3ye-web/content/blog/how-value-flows-to-contributors.mdx
- t5 (this reviewer): RUNNING PREMATURELY (same DAG bug)

**Explainer (t4): 7/10 — 3 criticals:**
1. Line 88 present-tense: "published in governance repository" — contracts don't exist yet. Fix to future tense.
2. Currency oracle gap: $9k USD cap requires stablecoin (preferred) OR Chainlink price feed. Payment token unspecified anywhere.
3. Queue mechanic described ("payment queues") is not in any existing contract. TreasuryGate.sol must implement it. Needs maxQueueMonths cap to prevent unbounded debt.

**Do not touch:** "first exception is blueprint for all ones that follow" — strongest argument. "The river does not carve an exception for the source" — best closer.

**Contract requirements (for when t2 is written):**
- HARD_CAP_USD = 9000e6 must be immutable constant (not governance-adjustable)
- Payment via stablecoin (USDC) for v1 — avoids oracle risk (pattern: oracle trust = C2 risk per 2026-03-28 audit)
- TreasuryGate.sol needs: minimumReserveBps + absoluteMinimumUSD floor + maxQueueMonths cap + permissionless releaseQueued()
- Multisig from day 1 for GOVERNANCE_ROLE (never single EOA — recurrent finding in all smart contract reviews)
- Pull pattern (claim()) only — no push payments
- All contracts: Pausable (1-of-3 pause, 2-of-3 unpause)

**DAG execution bug:** t3 and t5 started before their dependencies completed. Pattern: plan DAG executor does not block tasks when an upstream task fails/retries — a failed task triggers downstream unlocking.

**Full review:** ~/otto/docs/contributor-salary-contract-review-2026-03-29.md
**How to apply:** Re-run this review after t2 (Solidity engineer) commits ContributorSalary.sol and t3 runs against actual code.

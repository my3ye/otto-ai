# On-Chain Architecture: Systemic Risk Audit
## Security Audit of the Live Organism Smart Contract System

*Auditor: Otto (Blockchain Security Auditor) | 2026-03-28 | Status: Complete*
*Scope: 6 new contracts (ContributionRegistry, DemandOracle, RevenueRouter, GovernanceAccrual, ReputationNFT, ProductionTrigger) + composition with existing OPRLP stack*

---

## Executive Summary

**Overall Risk Rating: HIGH** — The architecture is well-designed with several strong defensive choices (non-transferable governance, capital exclusion, atomic splits). However, 4 Critical and 6 High severity findings require mitigation before deployment. The most dangerous systemic risks are centralized role concentration inherited from OPRLP (C1), the trusted reporter oracle model in DemandOracle (C2), and missing escrow recovery paths in ProductionTrigger (C3).

| Severity | Count | Description |
|----------|-------|-------------|
| Critical | 4 | Can drain funds, capture governance, or halt the system |
| High | 6 | Can manipulate economic outcomes or create permanent loss |
| Medium | 5 | Can degrade system fairness or create edge-case failures |
| Low | 3 | Defense-in-depth improvements, no immediate exploit |

---

## 1. Revenue Routing Exploits

### C1 — CRITICAL: configGovernor is a Single Point of Total Control

**Severity:** Critical
**Contract:** RevenueRouter.sol

**Finding:** `configGovernor` is a single address that controls `updateConfig()` and `updateRoleWeight()`. If this address is compromised or malicious:
- Set `protocolFeeBps` to 1000 (10%) — draining maximum overhead
- Set `agentTaxBps` to 6000 (60%) — redirecting 60% of AI contributor shares to pools controlled by the attacker
- Set any `roleWeight` to 0 — zeroing out entire contributor classes
- Set `maxSingleShareBps` to 10000 — allowing one participant to capture 100% of the contributor pool
- Set `minCreatorShareBps` to 0 — eliminating the creator floor

**Impact:** Complete control over revenue distribution. An attacker can slowly drain the system by incrementally shifting parameters within the "valid" ranges, which are wide enough to be destructive (agentTaxBps range: 1000-6000).

**Root cause:** The architecture doc says "initially deployer, later LoopGovernor" but provides no timelock, no multisig, and no migration mechanism. During Phase 1 (potentially months), a single EOA controls all revenue parameters.

**Mitigations:**
1. **Immediate:** Deploy configGovernor as a 2-of-3 multisig (Gnosis Safe) from day 1 — never a single EOA
2. **Required:** Add a 48-hour timelock on all parameter changes via `updateConfig()` and `updateRoleWeight()`, with a public `pendingConfig` that anyone can inspect
3. **Required:** Emit events on parameter change proposals (not just executions) so watchers can alert before changes take effect
4. **Required:** Tighter parameter bounds: `agentTaxBps` max should be 5000 (50%), `maxSingleShareBps` max should be 7500 (75%), `minCreatorShareBps` min should be 1000 (10%)
5. **Long-term:** Migrate configGovernor to LoopGovernor with on-chain voting within 90 days of launch

### H1 — HIGH: Provenance Manipulation Inflates Revenue Shares

**Severity:** High
**Contract:** RevenueRouter.sol + ContributionRegistry.sol

**Finding:** The split formula is `roleWeight[type_i] * dpcScore_i` normalized across all provenance participants. An attacker with REGISTRAR_ROLE can:
1. Register fake provenance entries (phantom contributors) pointing to the target design
2. Each phantom gets a non-zero DPC score via `activate()` (also REGISTRAR_ROLE)
3. At split time, `getProvenanceParticipants()` returns the inflated participant list
4. Legitimate contributors' shares are diluted by the phantom entries

**Impact:** Revenue theft from legitimate contributors. A colluding REGISTRAR_ROLE holder can siphon up to `(1 - minCreatorShareBps/10000)` = 80% of the contributor pool to phantom addresses.

**Root cause:** REGISTRAR_ROLE has unrestricted power to create entries and set initial DPC scores. No challenge period, no minimum verification requirements before provenance links are honored in splits.

**Mitigations:**
1. **Required:** Provenance links should require attestation (LaborAttestation quorum) before they count in revenue splits. Add a `verifiedProvenance` boolean to the Entry struct.
2. **Required:** Separate the `register()` and `activate()` callers — registration can be permissioned, but activation must require multi-party attestation
3. **Required:** Add a provenance challenge period (e.g., 7 days) where existing contributors in the chain can dispute new provenance links
4. **Defense-in-depth:** Cap maximum provenance participants per entry (e.g., 20) to limit dilution attack surface

### H2 — HIGH: Rounding Dust Accumulation Over Time

**Severity:** High
**Contract:** RevenueRouter.sol

**Finding:** The doc notes "last recipient receives dust" but this creates a systematic bias. With 6+ participants and basis point math on small amounts:
- Each split loses up to 5 wei per participant to rounding
- Over thousands of transactions, the "last recipient" position becomes financially meaningful
- The order of participants in the provenance array is deterministic (insertion order) — whoever is last consistently benefits or is harmed

**Impact:** Unfair distribution over time. Not immediately drainable, but creates a persistent economic bias.

**Mitigations:**
1. **Required:** Send dust to the protocol treasury (neutral party) rather than the last recipient
2. **Alternative:** Use a pull-based withdrawal pattern where accumulated micro-amounts are claimed periodically, avoiding per-tx rounding entirely

### M1 — MEDIUM: Flash Loan DPC Score Timing Gap

**Severity:** Medium
**Contract:** RevenueRouter.sol

**Finding:** The doc claims "DPC scores are updated asynchronously via callbacks, not in the same tx as the split" as a flash loan mitigation. However, the timing gap between DPC update and revenue split is undefined. If the DPC callback arrives in the same block (different tx), the attacker can:
1. Tx 1: Inflate DPC score via a compromised DPC_UPDATER_ROLE
2. Tx 2 (same block): Trigger a revenue split that reads the inflated score

**Impact:** Temporary DPC inflation captures outsized revenue share.

**Mitigations:**
1. **Required:** Add a minimum age requirement on DPC scores used for splits — scores updated within the last N blocks (e.g., 10) are ignored in favor of the previous score
2. **Alternative:** Use snapshotted DPC scores at the time of demand threshold crossing, not at the time of revenue split

---

## 2. Demand Oracle Manipulation

### C2 — CRITICAL: Trusted Reporter Model with No Fraud Proof

**Severity:** Critical
**Contract:** DemandOracle.sol

**Finding:** The REPORTER_ROLE is trusted to submit accurate demand data. The only anti-manipulation measures are:
- Reporter cooldown (60s) — trivially bypassed with multiple reporter addresses
- MIN_BATCH_SIZE (10) — attacker just submits 10+ fake events per batch
- `requiresPayment` flag — only effective if set; defaults not specified

The Merkle settlement path is even more trust-dependent: "Off-chain aggregator is trusted to compute the correct root." The `verifyInclusion` function only verifies that an event was in a batch, not that the batch is truthful.

**Attack scenario:**
1. Malicious REPORTER_ROLE holder submits fake PURCHASE events with inflated `paymentAmount`
2. Fake demand crosses threshold → ProductionTrigger fires → real escrow is locked
3. Manufacturing partner produces goods based on fake demand → financial loss
4. Even if `requiresPayment` is set, the threshold check counts `totalRevenue` which is set by the reporter, not by actual on-chain payment verification

**Impact:** Fake production runs consuming real capital. In the worst case, this drains escrow funds on goods nobody wants.

**Root cause:** No on-chain verification that reported revenue corresponds to actual token transfers. The reporter says "$500 of revenue happened" and the system believes it.

**Mitigations:**
1. **Required:** For revenue-bearing events (PURCHASE, LICENSE, TRADE), require the reporter to submit a payment proof — either an on-chain tx hash that can be verified, or require the payment to flow through the DemandOracle contract itself (so it can verify the amount)
2. **Required:** Multi-reporter consensus for threshold-crossing events — require 2+ independent reporters to confirm a threshold crossing before ProductionTrigger fires
3. **Required:** Per-reporter rate limits on cumulative reported revenue (not just cooldown). E.g., a reporter cannot report more than $X in a 24h window without elevated authorization
4. **Required:** Separate REPORTER_ROLE into SIGNAL_REPORTER (views, waitlists — low trust) and REVENUE_REPORTER (purchases — high trust, with stricter controls)
5. **Long-term:** Economic stake requirement for reporters — reporters post a bond that is slashed if fraud is proven

### H3 — HIGH: Merkle Settlement Has No Dispute Window

**Severity:** High
**Contract:** DemandOracle.sol

**Finding:** `reportMerkle()` immediately settles a batch with `totalAmount` and `eventCount`. There is no challenge period. Once a Merkle root is settled, the aggregate data is updated and threshold checks run. `verifyInclusion` is a view function that can prove a specific event exists in the batch, but there is no mechanism to:
- Challenge that the batch contains fabricated events
- Dispute the totalAmount
- Revert a settled batch

**Impact:** A compromised reporter can submit a fraudulent Merkle root with inflated totals. By the time anyone notices, the threshold has fired and production is underway.

**Mitigations:**
1. **Required:** Add a dispute window (e.g., 24h) for Merkle settlements. During this window, the batch is "pending" and does not count toward thresholds
2. **Required:** Allow any staked participant to challenge a Merkle root by providing a counter-proof
3. **Required:** Merkle settlement should not directly trigger threshold crossing — it should only update aggregates, and threshold crossing should be a separate step with its own verification

### M2 — MEDIUM: Reporter Cooldown Bypassable via Multiple Addresses

**Severity:** Medium
**Contract:** DemandOracle.sol

**Finding:** The `REPORTER_COOLDOWN = 60` seconds cooldown is per-address (`lastReportTime[address]`). An attacker who controls REPORTER_ROLE assignment (or who has REPORTER_ROLE on multiple addresses) can bypass this trivially by rotating addresses.

**Mitigations:**
1. **Required:** Add per-project rate limiting in addition to per-reporter limiting. E.g., max N reports per project per hour regardless of reporter address
2. **Defense-in-depth:** Require reporters to stake tokens, making Sybil attacks economically costly

---

## 3. Governance Weight Capture

### C3 — CRITICAL: UUPS Upgrade Can Bypass Capital Exclusion

**Severity:** Critical
**Contract:** GovernanceAccrual.sol

**Finding:** The capital governance weight exclusion is described as "constitutional" and "immutable." However, GovernanceAccrual uses UUPS proxy pattern. The `_authorizeUpgrade` function says it "should verify" the invariant persists, but:
1. The check is specified as a comment, not enforced code
2. UPGRADE_ROLE holder can deploy a new implementation that removes the `CAPITAL_TYPE` check
3. The `_authorizeUpgrade` invariant checks are aspirational — there's no on-chain mechanism to verify that a new implementation preserves specific business logic

**Impact:** A single UPGRADE_ROLE holder can silently reintroduce capital-based governance, fundamentally breaking the constitutional commitment.

**Root cause:** "Immutable" constraints in upgradeable contracts are contradictions. The upgrade mechanism IS the backdoor.

**Mitigations:**
1. **Required:** Move GovernanceAccrual to an immutable deployment (like RevenueRouter) for the core weight computation logic. Put only adjustable parameters (decay rates, etc.) in a governed config contract
2. **Alternative:** If UUPS must stay, require UPGRADE_ROLE to be a 3-of-5 multisig with a 7-day timelock, AND add an on-chain invariant test contract that the upgrade process must call to verify capital exclusion persists in the new implementation
3. **Required:** Add a `constitutionalInvariant()` external view function that returns the capital exclusion state. The _authorizeUpgrade should call this on the new implementation and revert if it returns false
4. **Required:** Consider an immutable "constitutional guard" contract that GovernanceAccrual delegates capital-exclusion checks to — even if GovernanceAccrual is upgraded, the guard contract is not

### H4 — HIGH: Governance Weight Accumulation Without Activity Cap Creates Long-Term Concentration

**Severity:** High
**Contract:** GovernanceAccrual.sol

**Finding:** The governance weight formula `sqrt(cumDPC) * ln(1+cumRevenue) * tenure_factor` uses CUMULATIVE values. While sqrt and ln provide sublinear scaling, over years a prolific early contributor accumulates massive absolute weight. The 5% monthly decay only applies during INACTIVITY — an active contributor who contributes once per month never decays.

**Scenario:** A team of 5 contributors active from day 1 could control >50% of governance weight within 12-18 months, even with new contributors joining, because:
- Their cumDPC compounds from every contribution
- Their cumRevenue compounds from every sale
- Their tenure_factor reaches 1.0 (max) and stays there
- New contributors start at 0 and need months to catch up

**Impact:** Early contributor oligarchy — exactly the centralization the system is designed to prevent, just slower.

**Mitigations:**
1. **Required:** Add an absolute weight cap per address. E.g., no single address can hold more than 5% of `totalActiveWeight`
2. **Required:** Apply continuous decay (not just inactivity decay). Even active contributors should see their weight decay at a lower rate (e.g., 1%/month) to prevent permanent accumulation
3. **Alternative:** Use a rolling window (e.g., last 12 months) for weight computation instead of lifetime cumulative values. This naturally prevents concentration
4. **Defense-in-depth:** Implement quadratic voting in LoopGovernor — even if weight concentrates, its voting power is sublinearly scaled

### H5 — HIGH: Missing Snapshot Mechanism for Governance Votes

**Severity:** High
**Contract:** GovernanceAccrual.sol

**Finding:** There is no snapshot mechanism. The `getWeight()` function reads current state with lazy decay. This means:
1. A voter's weight can change between proposal creation and vote execution
2. An attacker can front-run a close vote by triggering revenue events to inflate weight
3. `batchApplyDecay` can be weaponized — calling it on political opponents right before a vote to reduce their weight via decay application

**Impact:** Governance outcomes can be manipulated at vote time.

**Mitigations:**
1. **Required:** Implement ERC-5805 (Votes with delegation) style checkpointing. At proposal creation, capture a snapshot block number. All votes reference that snapshot, not live weight
2. **Required:** Make `batchApplyDecay` governance-neutral — either auto-apply decay for all participants at snapshot time, or make it callable only by the governance contract itself

### M3 — MEDIUM: onRevenueEvent Caller Restriction Is Insufficient

**Severity:** Medium
**Contract:** GovernanceAccrual.sol

**Finding:** `onRevenueEvent()` checks `require(msg.sender == revenueRouter)` but `revenueRouter` is a mutable state variable (not immutable). If the contract is upgraded (UUPS), the new implementation could set `revenueRouter` to an attacker-controlled contract that calls `onRevenueEvent()` with fabricated revenue data.

**Mitigations:**
1. **Required:** Make `revenueRouter` immutable (set in initializer, never changeable) OR require a governance vote to change it with a timelock
2. **Defense-in-depth:** Add a sanity check in `onRevenueEvent` — verify that the claimed revenue amounts correspond to actual token transfers visible on-chain

---

## 4. Soulbound NFT Edge Cases

### H6 — HIGH: Key Loss = Permanent Reputation Loss (No Recovery Path)

**Severity:** High
**Contract:** ReputationNFT.sol

**Finding:** Soulbound tokens are bound to a single address with no recovery mechanism. If a contributor:
- Loses their private key
- Has their key compromised and rotated to a new address
- Dies and an heir needs to claim their reputation
- Migrates from one ONEON identity to another

...all reputation data is permanently locked to the old address. The contributor must start from zero on a new address.

**Impact:** Permanent loss of years of accumulated reputation. This is especially devastating for Core-tier contributors (100+ contributions, avg score 75+). It also creates perverse incentives to never migrate keys even when compromised.

**Mitigations:**
1. **Required:** Add a `migrateReputation(address from, address to)` function callable only by a RECOVERY_ROLE (multisig + timelock). The function:
   - Burns the old NFT (bypass soulbound check via admin override)
   - Mints new NFT to `to` address with identical ReputationData
   - Emits a `ReputationMigrated(from, to, tokenId)` event
   - Has a 7-day challenge period before migration finalizes
2. **Required:** Integrate with ONEON identity for social recovery — if ONEON supports account rotation, the ReputationNFT should honor it
3. **For death/inheritance:** Define a `designatedHeir` field (settable by the contributor while alive) that can claim the reputation after a long inactivity period (e.g., 12 months + governance approval)
4. **Required:** Add a `freeze(tokenId)` function callable by the contributor themselves — in case of key compromise, immediately freeze reputation to prevent misuse while migration is arranged

### M4 — MEDIUM: tokenByContributorProject[contributor][projectId] == 0 Check Is Ambiguous

**Severity:** Medium
**Contract:** ReputationNFT.sol

**Finding:** Token IDs start at 1 (`_nextTokenId` pre-increments from 0). The `mintReputation` function uses `tokenByContributorProject[contributor][projectId] == 0` to check if a token already exists. However, if a contributor's NFT were ever burned (future recovery migration), the mapping would reset to 0, allowing re-minting. This creates a potential double-mint if recovery is implemented naively.

**Mitigations:**
1. **Required:** If recovery/migration is added, use a separate `hasMinted` mapping (bool) in addition to the tokenId lookup
2. **Alternative:** Never burn — migration should update the token's owner rather than burn-and-remint

### L1 — LOW: Soulbound _update Override Blocks Burning

**Severity:** Low
**Contract:** ReputationNFT.sol

**Finding:** The `_update` override requires `from == address(0)` (only minting allowed). This also blocks burning (`to == address(0)` where `from != address(0)`). While burning isn't currently needed, it prevents:
- Cleaning up abandoned accounts
- Any future burn-and-remint migration pattern

**Mitigation:**
1. Allow burns from ADMIN_ROLE: `require(from == address(0) || to == address(0), "SOULBOUND")` with the burn path gated by AccessControl

---

## 5. Production Trigger Safety

### C4 — CRITICAL: No Escrow Recovery Path for Failed Production

**Severity:** Critical
**Contract:** ProductionTrigger.sol

**Finding:** If a manufacturing partner fails after accepting an order (goes bankrupt, factory fire, fraud), the escrow funds have no automated recovery path:
- `checkDeadlines()` only emits `DeadlineMissed` events — it does NOT change order status
- There is no `cancelOrder()` function for CREATED/ACCEPTED/IN_PRODUCTION orders
- There is no `refundEscrow()` function
- A DISPUTED order has no resolution mechanism — it's a terminal state with locked funds
- The only way to release escrow is `confirmDelivery()` which requires QC_PASSED or SHIPPED status

**Impact:** Permanent fund lock. If 10 orders of $500 each are in production when a partner fails, $5,000 is permanently locked in the contract with no path to recovery.

**Root cause:** The architecture doc says "cancellation requires human intervention (ORDER_MANAGER_ROLE)" but no cancellation function exists.

**Mitigations:**
1. **Required:** Add `cancelOrder(bytes32 orderId)` callable by ORDER_MANAGER_ROLE that:
   - Transitions order to CANCELLED status
   - Returns escrowed funds to the original escrow source (DemandOracle or marketplace)
   - Updates partner stats (increment dispute count, reduce quality score)
   - Has a cooldown period (e.g., 7 days after deadline) before cancellation is allowed
2. **Required:** Add `resolveDispute(bytes32 orderId, uint16 partnerShareBps)` callable by a DISPUTE_RESOLVER_ROLE (multisig) that:
   - Splits escrowed funds between partner (partial payment for work done) and refund pool
   - Transitions order out of DISPUTED state
3. **Required:** Add an automatic escrow timeout — if an order is not delivered within 2x deadline, anyone can trigger a refund
4. **Required:** Add a `withdrawStuckEscrow(bytes32 orderId)` emergency function with a 30-day timelock, callable by governance multisig, for cases where all other paths fail

### H7 — HIGH: safeApprove Race Condition in confirmDelivery

**Severity:** Medium (downgraded from doc's acknowledgment — the doc notes it but doesn't fully address it)
**Contract:** ProductionTrigger.sol

**Finding:** Line 1575: `IERC20(o.escrowToken).safeApprove(revenueRouter, amount)`. OpenZeppelin's `safeApprove` will revert if the current allowance is non-zero (for tokens like USDT that don't return bool). If a previous `confirmDelivery` left a non-zero allowance (due to RevenueRouter not consuming the full allowance, e.g., from rounding), subsequent deliveries will revert permanently.

**Impact:** Permanent contract freeze for that token pair.

**Mitigations:**
1. **Required:** Replace `safeApprove` with `forceApprove` (OZ v5) or use `safeIncreaseAllowance`. Better yet, since the amount is known and consumed atomically, reset to 0 first: `token.safeApprove(revenueRouter, 0)` then `token.safeApprove(revenueRouter, amount)`
2. **Alternative:** Use `token.safeTransfer` to move funds to RevenueRouter, and have RevenueRouter accept direct transfers (pull from its own balance) instead of using transferFrom

### M5 — MEDIUM: Partner Auto-Matching Has No Conflict of Interest Check

**Severity:** Medium
**Contract:** ProductionTrigger.sol

**Finding:** `_matchPartner()` selects by quality score and completion rate. There is no check that the selected partner is not:
- The same entity as the designer (self-dealing)
- An entity that controls the QC_INSPECTOR_ROLE for this order (conflict of interest)
- A partner that shares an ONEON identity with any contributor in the provenance chain

**Impact:** Circular value extraction — a contributor who is also a manufacturing partner can guarantee they receive both the production escrow AND a contributor share.

**Mitigations:**
1. **Required:** Add a conflict-of-interest check: matched partner address must not appear in `getProvenanceParticipants()` for the target registryId
2. **Required:** QC inspector must not be the matched partner or any provenance participant — enforce this in `submitQC()`, not just at role-granting time
3. **Defense-in-depth:** Random QC inspector assignment (Chainlink VRF) from a pool, rather than allowing any QC_INSPECTOR_ROLE holder to self-assign

### L2 — LOW: checkDeadlines Is Permissionless but Toothless

**Severity:** Low
**Contract:** ProductionTrigger.sol

**Finding:** `checkDeadlines()` is callable by anyone but only emits events. Without a cancellation mechanism (C4), the deadline monitoring is purely informational. An off-chain watcher would need to detect the event and then... do nothing, because no on-chain action is available.

**Mitigation:**
1. Once C4 is fixed (cancel function added), allow `checkDeadlines` to auto-cancel orders past 2x deadline, or transition them to DISPUTED status automatically

### L3 — LOW: Order ID Predictability

**Severity:** Low
**Contract:** ProductionTrigger.sol

**Finding:** `orderId = keccak256(abi.encodePacked(registryId, partnerId, _orderNonce++))`. The nonce is a simple increment and all inputs are publicly visible. This makes order IDs predictable, which could enable front-running of `acceptOrder()` calls by MEV bots that sandwich the partner's acceptance transaction.

**Mitigation:**
1. Add `block.timestamp` and `block.prevrandao` to the hash inputs for unpredictability
2. Low priority — predictable IDs don't directly enable fund theft

---

## 6. Cross-Contract Systemic Risks

### S1 — SYSTEMIC: Role Concentration Inherited from OPRLP

**Severity:** Critical (systemic)

**Finding:** The prior OPRLP audit (2026-03-27) identified that DEFAULT_ADMIN_ROLE is a single address controlling all 4 Phase 1 contracts. The new 6 contracts introduce 11 additional roles:
- REGISTRAR_ROLE, DPC_UPDATER_ROLE, DEMAND_ORACLE_ROLE (ContributionRegistry)
- REPORTER_ROLE, THRESHOLD_ADMIN_ROLE (DemandOracle)
- ACCRUAL_ROLE (GovernanceAccrual)
- UPDATER_ROLE (ReputationNFT)
- PARTNER_ADMIN_ROLE, ORDER_MANAGER_ROLE, QC_INSPECTOR_ROLE, ORACLE_ROLE (ProductionTrigger)
- UPGRADE_ROLE (all UUPS contracts)

If a single deployer EOA holds DEFAULT_ADMIN_ROLE across all 12 contracts (old + new), they can grant themselves any role and execute any action. This is the same "admin IS the room" finding from the OPRLP audit, now amplified across a larger attack surface.

**Mitigations:**
1. **Required:** Deploy a role management strategy from day 1:
   - DEFAULT_ADMIN_ROLE: 3-of-5 multisig with 48h timelock
   - UPGRADE_ROLE: Same multisig, 7-day timelock
   - Financial roles (REPORTER, ORDER_MANAGER): 2-of-3 multisig
   - Operational roles (REGISTRAR, UPDATER): Can be contract addresses (LaborAttestation, ContributionRegistry) — not EOAs
2. **Required:** Document which roles should be held by contracts vs. multisigs vs. governance — the architecture doc specifies this informally but it must be codified

### S2 — SYSTEMIC: No Circuit Breaker / Emergency Pause

**Severity:** High (systemic)

**Finding:** None of the 6 contracts implement Pausable. If a critical vulnerability is discovered post-deployment:
- RevenueRouter cannot be paused (funds continue splitting through a broken formula)
- DemandOracle cannot be paused (fake signals continue accumulating)
- ProductionTrigger cannot be paused (new orders continue being created)

**Mitigations:**
1. **Required:** Add OpenZeppelin Pausable to all 6 contracts. The PAUSER_ROLE should be a 1-of-N multisig (any guardian can pause) with unpause requiring 2-of-N (prevent griefing)
2. **Required:** RevenueRouter should have a separate `emergencyWithdraw()` function that returns all held funds to the protocol treasury when paused — prevents permanent fund lock during emergencies

---

## Severity Summary Table

| ID | Severity | Contract | Finding | Status |
|----|----------|----------|---------|--------|
| C1 | Critical | RevenueRouter | configGovernor single point of control | Open |
| C2 | Critical | DemandOracle | Trusted reporter model with no fraud proof | Open |
| C3 | Critical | GovernanceAccrual | UUPS can bypass "immutable" capital exclusion | Open |
| C4 | Critical | ProductionTrigger | No escrow recovery for failed production | Open |
| H1 | High | RevenueRouter + ContribRegistry | Provenance manipulation inflates shares | Open |
| H2 | High | RevenueRouter | Rounding dust systematic bias | Open |
| H3 | High | DemandOracle | Merkle settlement has no dispute window | Open |
| H4 | High | GovernanceAccrual | Long-term governance weight concentration | Open |
| H5 | High | GovernanceAccrual | No snapshot mechanism for votes | Open |
| H6 | High | ReputationNFT | Key loss = permanent reputation loss | Open |
| M1 | Medium | RevenueRouter | Flash loan DPC timing gap | Open |
| M2 | Medium | DemandOracle | Reporter cooldown bypassable via Sybil | Open |
| M3 | Medium | GovernanceAccrual | Mutable revenueRouter address | Open |
| M4 | Medium | ReputationNFT | tokenId 0 ambiguity on burn/remint | Open |
| M5 | Medium | ProductionTrigger | No conflict of interest check in matching | Open |
| L1 | Low | ReputationNFT | Soulbound override blocks burning | Open |
| L2 | Low | ProductionTrigger | checkDeadlines is toothless | Open |
| L3 | Low | ProductionTrigger | Predictable order IDs | Open |
| S1 | Critical | All contracts | Role concentration inherited from OPRLP | Open |
| S2 | High | All contracts | No circuit breaker / emergency pause | Open |

---

## Recommended Remediation Priority

**Before testnet deployment:**
1. C4 — Add escrow cancellation and refund functions to ProductionTrigger
2. C1 — Deploy configGovernor as multisig with timelock
3. S1 — Define and implement role management strategy
4. S2 — Add Pausable to all contracts
5. C2 — Require on-chain payment verification for revenue-bearing demand events

**Before mainnet deployment:**
6. C3 — Move GovernanceAccrual core logic to immutable deployment
7. H5 — Implement vote snapshotting
8. H6 — Add reputation recovery/migration mechanism
9. H1 — Add provenance verification requirements
10. H3 — Add Merkle settlement dispute window

**Post-launch (can be governance-upgraded):**
11. H4 — Add continuous decay and weight caps
12. H2 — Fix rounding dust distribution
13. M1-M5 — Medium findings (parameter tightening, additional checks)

---

*This audit covers architecture-level risks only. A formal code audit with automated tooling (Slither, Mythril, Certora) is required before any deployment with real funds.*

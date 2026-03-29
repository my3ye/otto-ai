# Contributor Salary Contract System — Final Review
## Reviewer: Otto (reviewer agent) | 2026-03-29 | Plan: 9a40a60f
## Version: FINAL (contracts now exist — full code review complete)

---

## Executive Summary

**Verdict: CONDITIONAL APPROVAL — 2 blocking issues before mainnet**

The three contracts (ContributorRegistry.sol, ContributorSalary.sol, TreasuryGate.sol) are
well-structured, follow security best practices, and correctly implement the core architecture
intent. The floor protection is solid. The cap is immutable. The CEI pattern is followed.
SafeERC20 throughout. Role-based access is clean.

Two items block mainnet deployment:
1. **Period 0 snapshot bug** — all claims in the first period will revert with ZeroPayout due to
   a snapshot initialization gap. Silent, deployment-blocking.
2. **Explainer queue mechanic** — the published article says "the payment queues" but no queue
   exists in the contracts. Claims simply revert when treasury is below floor. The article is live
   and currently misleads readers.

Everything else is medium/low severity — document and address before first contributor claim,
but not deployment-blocking.

**Score: 8.5/10 (contracts) | 5.5/10 (explainer accuracy)**

---

## Contracts Reviewed

| File | Lines | Assessment |
|------|-------|------------|
| ContributorRegistry.sol | 353 | Well-designed, clean invariants |
| ContributorSalary.sol | 454 | Strong CEI discipline, minor issues |
| TreasuryGate.sol | 361 | Solid floor protection, Period 0 bug |

---

## Section 1: Architecture Intent vs. Implementation

**Architecture document:** `~/otto/docs/contributor-compensation-contract-architecture-2026-03-29.md`

| Requirement | Implemented | Notes |
|-------------|-------------|-------|
| ContributorRegistry with address→config | ✅ | ContributorRegistry.sol |
| Same function for all contributors (including Mev) | ✅ | `addContributor()` — no special paths |
| GLOBAL_SALARY_CAP = 9000e6, immutable constant | ✅ | `uint128 public constant GLOBAL_SALARY_CAP = 9_000e6` — cannot be raised by governance |
| Treasury floor gate | ✅ | TreasuryGate preClaimCheck + postClaimCheck |
| USDC payment (stablecoin, no oracle) | ✅ | `IERC20 public immutable usdc` |
| Pull pattern — `claim()` not push | ✅ | Contributors call claim(); no keeper required |
| Reentrancy guard on claim paths | ✅ | `nonReentrant` on `claim()` and `claimFor()` |
| Pausable contracts | ✅ | All three contracts — OZ Pausable |
| Operator role for relayer/keeper | ✅ | `OPERATOR_ROLE` on `claimFor()` |
| Aggregate allocation cap (all contributors combined) | ✅ | `MAX_TOTAL_ALLOCATION_BPS = 2000` (20%) |
| Per-contributor allocation cap | ✅ | `MAX_ALLOCATION_BPS = 500` (5%) |
| Soft deactivation (history preserved) | ✅ | `active` flag flip, not deletion |
| Hard floor (absolute minimum) | ✅ | `ABSOLUTE_MINIMUM_FLOOR = 10_000e6` |
| CEI pattern on claim | ✅ | State recorded before transfer, gate re-checked after |
| Wallet immutable post-registration | ✅ | No `updateWallet()` function — wallet fixed at registration |
| Queue mechanic (pay arrears when threshold met) | ❌ | **NOT IMPLEMENTED** — see Critical C1 |
| Percentage-based floor (minimumReserveBps) | ❌ | Only absolute floor implemented |
| Timelock on parameter changes | ❌ | Floor/duration changes are instant |

---

## Section 2: Critical Findings

### C1 — Period 0 Snapshot Bug (DEPLOYMENT-BLOCKING)

**Location:** `TreasuryGate.sol:180`, `TreasuryGate.sol:316-325`

**Severity:** CRITICAL — Functional (not security). All claims in the first claim period will
revert. Silent failure mode.

**Root cause:** `snapshotPeriod` is initialized to 0 by Solidity's default (0 for uint32).
`getCurrentPeriod()` returns 0 for the first period (period 0). The snapshot condition:

```solidity
if (snapshotPeriod != currentPeriod) {
    // Take snapshot — set periodOpeningBalance
}
```

In period 0: `snapshotPeriod (0) == currentPeriod (0)` → condition is FALSE → snapshot is never
taken → `periodOpeningBalance` stays 0.

`getEligiblePool()` then returns 0 (because `reference = periodOpeningBalance = 0 ≤ floorUsd`).

In ContributorSalary._processClaim:
```solidity
uint128 eligiblePool = gate.getEligiblePool(); // returns 0
uint128 computed = _computePayout(c.allocationBps, eligiblePool); // returns 0
if (computed == 0) { revert ZeroPayout(); } // ALWAYS REVERTS in period 0
```

**Impact:** Every claim in the first 30 days after deployment fails with `ZeroPayout`. Contributors
see a confusing error with no hint about why. Treasury could be fully funded. Does not affect security
(no funds at risk), but makes period 0 completely non-functional.

**Fix:** Initialize `snapshotPeriod` to `type(uint32).max` so the first claim always triggers
the snapshot branch. Or use a separate `bool initialized` flag.

```solidity
// Constructor:
snapshotPeriod = type(uint32).max; // Forces snapshot on first ever claim
```

**Workaround if not fixed before deployment:** Wait for period 1 (after 30 days) before expecting
any claims to succeed. Document this behavior explicitly.

---

### C2 — Explainer Queue Mechanic Has No Contract Implementation (PUBLISH-BLOCKING)

**Location:** `how-value-flows-to-contributors.mdx:30-31`

**Severity:** CRITICAL — Accuracy. The published article makes concrete claims about contract
behavior that do not match the deployed contracts.

**Explainer claims:**
> "The payment queues. The treasury builds. When the threshold is crossed, queued payments release
> in order — oldest first, no skipping — and regular cadence resumes."

**Actual contract behavior:** Claims revert (`TreasuryBelowFloor` or `ZeroPayout`). There is no
queue. There is no backlog. When treasury is below floor, the claim fails — the contributor must
retry in the next period when/if the treasury recovers.

**This creates a reader trust problem:** An investor or contributor reads this article, expects
queued payments as a safety net, and then discovers none exists when treasury dips.

**Fix for explainer (line 30-31):**
Change: `"If the threshold is not met, nothing releases. The payment queues."`
To: `"If the threshold is not met, nothing releases. Claims resume automatically once the treasury
recovers — contributors claim their period's allocation when the gate reopens."`

Also update: `"queued payments release in order — oldest first, no skipping"` — remove entirely.

**Note:** A queue mechanic COULD be added to TreasuryGate.sol in a future version. It would
require: `mapping(address => uint32[]) public missedPeriods`, `releaseMissed(address)` function,
and a `maxBacklogPeriods` cap to prevent unbounded debt. Recommend deferring to Phase 2.

---

## Section 3: High Severity Findings

### H1 — `fundingSource` and `gate.treasury()` Can Diverge

**Location:** `ContributorSalary.sol:89-92`, `TreasuryGate.sol:57-61`

**Severity:** HIGH — Operational risk (not a security bug per se, but can cause confusion
and operational failure).

**Issue:** `fundingSource` (ContributorSalary) and `treasury` (TreasuryGate) are separate state
variables with separate admin functions (`setFundingSource` / `setTreasury`). Both should point
to the same Gnosis Safe. If the treasury migrates to a new address:
- Admin updates `gate.setTreasury(newAddress)` — floor check now reads from new treasury
- Admin forgets `salary.setFundingSource(newAddress)` — USDC recovery still goes to old address

The treasury floor check reads from `gate.treasury()`. The pre-funding and USDC recovery use
`fundingSource`. If they diverge, the floor check is reading one Safe while recovery sends USDC
to a different address.

**Fix:** In `setFundingSource`, optionally also call `gate.setTreasury()`. Or document the dual-
update requirement explicitly in the deployment runbook. Or make `ContributorSalary.fundingSource`
always read from `gate.treasury()` (removing the separate variable entirely).

---

## Section 4: Medium Severity Findings

### M1 — No Timelock on Floor Changes

**Location:** `TreasuryGate.sol:234-241`

`setFloor()` takes effect immediately. A compromised or rogue GATE_ADMIN could lower the floor to
`ABSOLUTE_MINIMUM_FLOOR` (10k USDC) in a single transaction, enabling large payouts that would
otherwise be blocked.

**Recommendation:** Add a 48-hour timelock on floor decreases (increases can remain instant).
Can be implemented with a pending change + timestamp pattern or via a Timelock governor.
This is a standard defense-in-depth measure for treasury parameters.

---

### M2 — `postClaimCheck` is `view` — Verify Revert Propagates

**Location:** `TreasuryGate.sol:220-225`

`postClaimCheck` is declared `view`. When ContributorSalary calls it after `safeTransfer`, Solidity
may use STATICCALL. A revert inside `postClaimCheck` DOES propagate back and reverts the parent
transaction (including the safeTransfer) — this behavior is correct and tested in Solidity 0.8+.

**But confirm:** In test suite, verify the scenario where `postClaimCheck` reverts (treasury
drained concurrently) actually rolls back the USDC transfer in the same transaction.

---

### M3 — Pre/Post Check Floor Boundary Inconsistency

**Location:** `TreasuryGate.sol:190`, `TreasuryGate.sol:222`

Pre-check: `if (currentBalance <= floorUsd)` — blocks when balance equals floor
Post-check: `if (currentBalance < floorUsd)` — allows when balance equals floor

This inconsistency means a payout that brings the treasury exactly to the floor passes the post-
check but would have failed the pre-check. Not a security issue (floor still protected) but
semantically inconsistent. Recommend making both use `<` (strict below floor triggers revert) so
"at floor" is allowed.

---

### M4 — `periodTotalPaid` Comment Misleading

**Location:** `TreasuryGate.sol:196-208`

The comment says: *"We add periodTotalPaid already disbursed this period to give a worst-case view
if multiple claims happen in the same block."*

But the code does NOT add `periodTotalPaid` to the Phase 2 check:
```solidity
uint128 effectiveBalance = currentBalance; // NOT: currentBalance - periodTotalPaid
if (effectiveBalance < amount + floorUsd) { revert... }
```

The guard works correctly (each transaction reads the fresh on-chain balance after prior transfers),
but the comment is misleading. Update comment to: "Each transaction reads the live balance, so
concurrent claims in the same block see updated balances as they execute sequentially."

---

## Section 5: Low Severity Findings

### L1 — deactivatedAt Erased on Reactivation

**Location:** `ContributorRegistry.sol:240`

`c.deactivatedAt = 0` on reactivation. Historical deactivation timestamp is lost from storage
(events remain on-chain). For audit trails, consider preserving as `lastDeactivatedAt` instead.

---

### L2 — Period Duration Change Shifts Existing Claims

**Location:** `TreasuryGate.sol:258-264`

Documented, but worth noting in deployment runbook: changing `periodDuration` mid-operation
retroactively changes what period a contributor's last claim was in relative to the new period
numbering. If a contributor last claimed in period 5 (under 30-day schedule) and admin changes
to 7-day periods, their `lastClaimedPeriod=5` might or might not match the new period 5 boundary.
This creates a possible double-claim window. Recommendation: only change period duration at the
start of a new period.

---

### L3 — previewClaim Eligible Pool May Differ From Actual Claim

**Location:** `ContributorSalary.sol:362-402`

`previewClaim` reads `gate.getEligiblePool()` without triggering a snapshot. If the contributor
is the first claimer this period, the preview uses live balance while the actual claim's eligible
pool will be snapshotted at the moment `preClaimCheck` runs. If the treasury balance changes
between the preview call and the actual claim (inflows/outflows), these diverge. Acceptable for
a preview function, but document the caveat.

---

## Section 6: Explainer Accuracy Cross-Check

**File:** `my3ye-web/content/blog/how-value-flows-to-contributors.mdx`

| Claim | Accurate? | Action Required |
|-------|-----------|-----------------|
| "9,000 USD per month. No override." | ✅ GLOBAL_SALARY_CAP = 9000e6, immutable | None |
| "The contract does not ask who submitted the claim" | ⚠️ Partially — checks registry | Rewording (W1 from prior review) |
| "If the threshold is not met, nothing releases. The payment queues." | ❌ No queue in contracts | **FIX BEFORE PUBLISH** |
| "queued payments release in order — oldest first" | ❌ No queue | **REMOVE** |
| "The cap does not scale with token price / no governance exception" | ✅ Immutable constant | None |
| "An unverified address cannot receive treasury payments" | ✅ Registry.isActive() check | None |
| "governed by DAO vote with a 14-day deliberation period" | ❌ No DAO deployed | Change to future tense |
| "full compensation contract specifications are published in the governance repository" | ❌ No governance repo | Change to future tense or link |

**Required fixes to explainer (4 items):**

1. **Lines 30-31:** Remove queue mechanic claim. Replace with: *"If the threshold is not met,
   nothing releases. Claims may resume in a future period once the treasury recovers — contributors
   check and claim when the gate reopens."*
2. **Line 88 (first sentence):** Change *"are published"* → *"will be published"*
3. **Line 88 (second sentence):** Change *"governed by DAO vote"* → *"will be governed by DAO vote
   once governance is deployed"*
4. **Line 16:** Change *"it reads the address, checks the threshold, and executes"* → *"it reads
   the address, checks the contributor registry and threshold, and executes"* (removes misleading
   implication that no identity check occurs)

---

## Section 7: Architecture Compliance Summary

| Architecture Decision | Contract Behavior | Compliant? |
|----------------------|-------------------|------------|
| Decision 1: Percentage + Hard Cap | allocationBps × eligiblePool capped at hardCapUsd | ✅ |
| Decision 2: Floor Gate (not vesting) | preClaimCheck + postClaimCheck | ✅ |
| Decision 3: Claim-based (not push) | claim() + claimFor() | ✅ |
| Decision 4: USDC-denominated | IERC20 usdc, caps in USDC units | ✅ |
| Decision 5: Gnosis Safe funding source | fundingSource param, recoverUsdc() | ✅ |
| Decision 6: Monthly claim periods | periodDuration = 30 days | ✅ |
| Security — Multisig admin | Constructor requires admin address (must be Safe) | ⚠️ Operational |
| Security — Reentrancy | nonReentrant on all external claim paths | ✅ |
| Security — CEI | Effects before interactions in _processClaim | ✅ |
| Security — SafeERC20 | All USDC transfers via SafeERC20 | ✅ |
| Security — Role separation | REGISTRY_ADMIN / SALARY_ADMIN / GATE_ADMIN / OPERATOR | ✅ |

---

## Section 8: Final Readiness Checklist

**Status key: ✅ Done | ⚠️ Conditional | ❌ Blocking | 🔲 Not Started**

### Pre-Deployment (Before Any Mainnet Deployment)

| Item | Status | Notes |
|------|--------|-------|
| Period 0 snapshot bug fixed | ❌ BLOCKING | snapshotPeriod init to type(uint32).max |
| Explainer queue mechanic removed | ❌ BLOCKING | Article is live — currently misleading |
| Gnosis Safe multi-sig deployed as admin | ❌ BLOCKING | Never single EOA for admin roles |
| Contracts compile clean (OZ dependencies) | ⚠️ Verify | npm install @openzeppelin/contracts |
| Unit tests written and passing | ❌ BLOCKING | No test suite provided — need coverage |
| Automated audit tool run (Slither/Mythril) | 🔲 Not Started | Run before security audit |
| Security auditor (fba08c82) finishes review | ⚠️ RUNNING | Complete before deployment |

### Before First Contributor Claim

| Item | Status | Notes |
|------|--------|-------|
| TreasuryGate granted SALARY_CONTRACT_ROLE for ContributorSalary | 🔲 | Deployment step |
| ContributorSalary funded with USDC (pre-fund or allowance from Safe) | 🔲 | Operational |
| Initial floor set at correct level | 🔲 | Suggest: 100,000 USDC as launch floor |
| Mev's address registered in ContributorRegistry | 🔲 | addContributor() call post-deploy |
| Explainer article updated with all 4 fixes | ❌ BLOCKING | Must match actual behavior |
| previewClaim() tested off-chain against funded state | 🔲 | Verify UI integration |

### Before Public Capital Raise (Trust Signal)

| Item | Status | Notes |
|------|--------|-------|
| Formal audit report published | 🔲 | Third-party preferred |
| Contracts verified on block explorer | 🔲 | Polygonscan/Etherscan |
| Governance repo with contract specs created | 🔲 | Explainer references it |
| Admin keys in Gnosis Safe (multi-sig) documented | 🔲 | Who are the 3 signers? |

---

## Section 9: Recommended Changes (Prioritized)

### Must Fix (Deployment-Blocking)

**Fix 1: Period 0 snapshot initialization**

In `TreasuryGate.sol` constructor, add:
```solidity
snapshotPeriod = type(uint32).max;
```
This ensures the very first `preClaimCheck()` call always takes a snapshot, regardless of what
period number it occurs in.

**Fix 2: Explainer queue mechanic**

In `how-value-flows-to-contributors.mdx`, replace lines 30-31:
```
Old: "If the threshold is not met, nothing releases. The payment queues. The treasury builds.
     When the threshold is crossed, queued payments release in order — oldest first, no skipping
     — and regular cadence resumes."

New: "If the threshold is not met, nothing releases. The treasury builds. When the threshold is
     crossed, contributors can claim normally — the gate reopens and regular cadence resumes."
```

### Should Fix (Before First Claim)

**Fix 3: Pre/post check consistency**

In `TreasuryGate.sol postClaimCheck()`, change:
```solidity
if (currentBalance < floorUsd) {  →  if (currentBalance <= floorUsd) {
```

**Fix 4: M4 comment correction**

Update misleading comment in `preClaimCheck` about `periodTotalPaid`.

**Fix 5: Explainer future-tense corrections (lines 88)**

Change present-tense governance and contract publication claims to future tense.

### Nice to Have (Phase 2)

- Timelock on floor decreases (48h delay)
- Queue mechanic with `maxBacklogPeriods = 6` (optional Phase 2 feature)
- `requireAdmin2of3ToPause` pattern vs. single admin pause

---

## Section 10: Architectural Concerns for Mev

[NEEDS_MEV_INPUT]
{"question": "Who are the other 2-of-3 signers on the Gnosis Safe that will be admin?", "options": ["Mev + 2 trusted community members (identified by Mev)", "Mev + 2 hardware wallets controlled by Mev (self-custody multi-sig)", "Defer to when first contributor joins"], "recommendation": 0, "context": "The admin address in the constructor must be a Gnosis Safe, not a single EOA. If Mev is the only signer, a compromised key can pause all salary payments or change the floor. 2-of-3 with independent signers is the minimum acceptable trust model for a public-facing treasury contract."}
[/NEEDS_MEV_INPUT]

[NEEDS_MEV_INPUT]
{"question": "Should the queue mechanic be added to TreasuryGate.sol (v1 or Phase 2)?", "options": ["Add it now — matches explainer narrative, better contributor UX", "Leave it out — simpler, safer, update explainer to match"], "recommendation": 1, "context": "A queue accumulates debt. If treasury is below floor for 6 months and 3 contributors are queued, that's $162K in queued obligations that all release simultaneously when the threshold is hit. This creates a cliff event. No-queue design (claims lapse if missed, no backlog) is safer and simpler. Recommend updating the explainer instead."}
[/NEEDS_MEV_INPUT]

---

*Review by: Otto (reviewer agent) | 2026-03-29 | FINAL — all contracts reviewed*
*Contracts: ContributorRegistry.sol, ContributorSalary.sol, TreasuryGate.sol*
*Architecture: contributor-compensation-contract-architecture-2026-03-29.md*
*Explainer: how-value-flows-to-contributors.mdx (live, needs 4 fixes)*

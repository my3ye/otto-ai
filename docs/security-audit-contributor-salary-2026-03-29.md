# Security Audit: Contributor Salary Contracts
## ContributorRegistry.sol | TreasuryGate.sol | ContributorSalary.sol

**Auditor:** Otto (Blockchain Security Auditor Agent)
**Date:** 2026-03-29
**Scope:** Full manual review — reentrancy, overflow/underflow, access control, griefing, cap enforcement, registry manipulation, pause completeness, oracle risks, centralization
**Solidity:** ^0.8.24 (checked arithmetic by default)
**Dependencies:** OpenZeppelin AccessControl, Pausable, ReentrancyGuard, SafeERC20

---

## Executive Summary

The three-contract system implements Mev's directive: transparent, capped, threshold-gated contributor salaries. The architecture is sound — clean CEI pattern, proper reentrancy guards, immutable salary cap at 9,000 USDC, SafeERC20 usage, and well-structured access control separation.

**However, 2 HIGH findings exist that can violate the "9k/month" invariant.** The most concerning: `periodDuration` is governance-mutable with a 7-day minimum, meaning a compromised or careless admin can effectively set up 4x monthly payouts (36k/month). Additionally, the treasury address can be pointed at any address, bypassing floor protection entirely.

No critical (immediate funds-at-risk) vulnerabilities were found. The system is safe for deployment if the HIGH findings are addressed.

| Severity | Count |
|----------|-------|
| Critical | 0     |
| High     | 2     |
| Medium   | 3     |
| Low      | 3     |
| Info     | 3     |

---

## Findings

---

### [H-1] Period Duration Manipulation Breaks 9k/Month Cap Intent

**Severity:** HIGH
**Location:** `TreasuryGate.sol:258-264` (`setPeriodDuration`)
**Impact:** Contributor payouts can exceed 9,000 USDC/month

**Description:**

The hard cap (`GLOBAL_SALARY_CAP = 9_000e6`) is enforced **per claim period**, not per calendar month. `GATE_ADMIN_ROLE` can change `periodDuration` to any value between 7 days and 365 days. Setting it to 7 days creates ~4.3 claim periods per month:

```
Monthly payout = 9000 × (30 / 7) ≈ 38,571 USDC/month
```

Worse, when `periodDuration` changes, the period counter recalculates retroactively:

```solidity
function getCurrentPeriod() public view returns (uint32) {
    uint256 elapsed = block.timestamp - launchTimestamp;
    return uint32(elapsed / periodDuration); // period numbers shift instantly
}
```

A contributor who claimed in period 1 (30-day periods) has `lastClaimedPeriod = 1`. After the duration change, `getCurrentPeriod()` might return period 12. Since `1 != 12`, they can claim again immediately, then again every 7 days.

**Recommendation:**

Set `MIN_PERIOD_DURATION = 28 days` (not 7 days). This preserves the "monthly" intent while allowing slight flexibility:

```solidity
uint32 public constant MIN_PERIOD_DURATION = 28 days;

function setPeriodDuration(uint32 newDuration) external onlyRole(GATE_ADMIN_ROLE) {
    if (newDuration < MIN_PERIOD_DURATION) revert PeriodDurationTooShort(...);
    ...
}
```

Additionally, consider storing the period number at the time of each claim as `claimPeriodAtDuration`, and requiring that the current period (at the NEW duration) is strictly greater than the last claimed period. This prevents instant re-claims after a duration change.

---

### [H-2] Treasury Address Swap Bypasses Floor Protection

**Severity:** HIGH
**Location:** `TreasuryGate.sol:246-251` (`setTreasury`)
**Impact:** Floor gate becomes ineffective; all claims pass regardless of real treasury health

**Description:**

`GATE_ADMIN_ROLE` can point `treasury` at any address via `setTreasury()`. If set to a USDC whale address (e.g., Circle's treasury), `_readTreasuryBalance()` returns an enormous balance, making all floor checks pass trivially:

```solidity
// preClaimCheck: passes because whale balance >> floor
uint128 currentBalance = _readTreasuryBalance(); // reads whale's balance
if (currentBalance <= floorUsd) revert; // never reverts

// postClaimCheck: also reads whale's balance — always passes
```

The eligible pool calculation in `getEligiblePool()` would return `whaleBalance - floor`, making percentage-based payouts enormous — but the hard cap kicks in, so each contributor gets exactly 9k. The floor protection is completely nullified.

Meanwhile, the REAL treasury (Gnosis Safe) could be empty. Claims proceed because ContributorSalary holds its own USDC balance independently.

**Recommendation:**

Option A (Preferred): Make `treasury` immutable — set once at construction, never changeable. Treasury migrations should deploy a new TreasuryGate.

Option B: Add a timelock + DAO vote requirement on `setTreasury()`:

```solidity
address public pendingTreasury;
uint64 public treasuryChangeUnlocksAt;
uint32 public constant TREASURY_CHANGE_DELAY = 7 days;

function proposeTreasuryChange(address newTreasury) external onlyRole(GATE_ADMIN_ROLE) {
    pendingTreasury = newTreasury;
    treasuryChangeUnlocksAt = uint64(block.timestamp) + TREASURY_CHANGE_DELAY;
}

function executeTreasuryChange() external onlyRole(GATE_ADMIN_ROLE) {
    require(block.timestamp >= treasuryChangeUnlocksAt, "TIMELOCK");
    treasury = pendingTreasury;
}
```

---

### [M-1] `recoverUsdc` Sends to Mutable `fundingSource` — Recovery Fund Redirection

**Severity:** MEDIUM
**Location:** `ContributorSalary.sol:338-343` (`recoverUsdc`)
**Impact:** Compromised `SALARY_ADMIN_ROLE` can redirect emergency recovery funds

**Description:**

`recoverUsdc()` transfers all USDC to `fundingSource`, which is mutable via `setFundingSource()` (restricted to `SALARY_ADMIN_ROLE`). Attack scenario:

1. Attacker compromises `SALARY_ADMIN_ROLE` key
2. Calls `setFundingSource(attacker_wallet)`
3. Calls `pause()`
4. Legitimate `DEFAULT_ADMIN_ROLE` holder calls `recoverUsdc()` thinking funds return to the Gnosis Safe
5. All USDC goes to the attacker

This is a social engineering + key compromise attack. The admin trusts that `recoverUsdc` sends to the safe, but `fundingSource` was silently changed.

**Recommendation:**

Add an immutable `recoveryAddress` set at construction, separate from `fundingSource`:

```solidity
address public immutable recoveryAddress;

function recoverUsdc() external onlyRole(DEFAULT_ADMIN_ROLE) whenPaused {
    uint256 balance = usdc.balanceOf(address(this));
    if (balance > 0) {
        usdc.safeTransfer(recoveryAddress, balance); // immutable destination
    }
}
```

Or: require `recoverUsdc` to explicitly specify the destination, which the admin must verify:

```solidity
function recoverUsdc(address to) external onlyRole(DEFAULT_ADMIN_ROLE) whenPaused {
    require(to != address(0));
    usdc.safeTransfer(to, usdc.balanceOf(address(this)));
}
```

---

### [M-2] `postClaimCheck` Is a No-Op — False Safety Guarantee

**Severity:** MEDIUM
**Location:** `ContributorSalary.sol:288`, `TreasuryGate.sol:220-225`
**Impact:** Misleading code comments claim "belt AND suspenders" but the second check is inert

**Description:**

`postClaimCheck()` reads `_readTreasuryBalance()` — the Gnosis Safe balance. But `claim()` transfers USDC from **ContributorSalary's balance**, not the Gnosis Safe. The Gnosis Safe balance is unchanged by the claim transaction:

```
Before claim:  GnosisSafe = 500k,  ContributorSalary = 27k
After claim:   GnosisSafe = 500k,  ContributorSalary = 18k  (9k transferred out)
postClaimCheck reads: GnosisSafe = 500k  →  passes (unchanged)
```

The code comments say this is "the final safety net" and "trust but verify". In reality, it verifies nothing that could have changed. The treasury balance was the same before and after the claim.

**Recommendation:**

Either:
1. **Remove postClaimCheck** and its associated comments to avoid false confidence, OR
2. **Change the architecture** so ContributorSalary pulls from the Gnosis Safe via `transferFrom` instead of holding its own balance. Then the treasury balance DOES change during a claim, making postClaimCheck meaningful.

Option 2 is architecturally cleaner:
```solidity
// In _processClaim, instead of transferring from own balance:
usdc.safeTransferFrom(gate.treasury(), c.wallet, payout);
// Now postClaimCheck actually verifies the treasury post-transfer
```

---

### [M-3] `periodTotalPaid` Is Dead State — Tracked But Never Read

**Severity:** MEDIUM
**Location:** `TreasuryGate.sol:87,206`
**Impact:** False sense of period accounting; no actual protection

**Description:**

`periodTotalPaid` is incremented on every claim (line 206) and reset on period transitions (line 184), but it is **never read** in any gate decision. The variable is public, so it's observable off-chain, but it has no on-chain effect:

```solidity
// Line 197-199: effectiveBalance is just currentBalance, ignoring periodTotalPaid
uint128 effectiveBalance = currentBalance;
if (effectiveBalance < amount + floorUsd) {
    revert PayoutWouldBreachFloor(effectiveBalance, amount, floorUsd);
}

// Line 206: incremented but influences nothing
periodTotalPaid += amount;
```

The comment on line 195 says "We add periodTotalPaid already disbursed this period to give a worst-case view if multiple claims happen in the same block" — **but the code doesn't do this**. The `effectiveBalance` is just `currentBalance` with no adjustment.

**Recommendation:**

Either use `periodTotalPaid` in the check:
```solidity
// Worst-case: assume all prior period payouts haven't settled yet
if (effectiveBalance < amount + periodTotalPaid + floorUsd) {
    revert PayoutWouldBreachFloor(...);
}
```

Or remove the variable entirely to avoid confusion. Given M-2 (postClaimCheck is a no-op), the per-claim balance check already uses the live balance, which inherently reflects prior transfers.

---

### [L-1] No Timelock on Governance Actions

**Severity:** LOW
**Location:** All three contracts — `setFloor`, `setTreasury`, `setPeriodDuration`, `addContributor`, `deactivateContributor`, `setFundingSource`, `pause/unpause`
**Impact:** Compromised admin key can cause immediate, undetectable damage

**Description:**

All governance actions take effect in the same transaction. There is no delay between proposing a change and it taking effect. A compromised `GATE_ADMIN_ROLE` or `REGISTRY_ADMIN_ROLE` can:
- Change the floor to its minimum (10k), unlocking more treasury funds
- Change the treasury address (H-2)
- Change the period duration (H-1)
- Deactivate all contributors (griefing)
- Pause the system indefinitely

Without a timelock, there is no window for detection or response.

**Recommendation:**

Implement a 48-72 hour timelock on sensitive governance actions (`setTreasury`, `setPeriodDuration`, `setFloor`). Less sensitive actions (pause, contributor management) can remain immediate for operational agility.

---

### [L-2] `_contributorList` Unbounded Growth

**Severity:** LOW
**Location:** `ContributorRegistry.sol:90,203`
**Impact:** `getAllContributors()` gas cost grows indefinitely

**Description:**

The `_contributorList` array never shrinks. Deactivated contributors remain in the array. `getAllContributors()` returns the full array, which has O(n) gas cost. While this is a view function (no on-chain gas concern), any contract calling it would face unbounded gas.

The practical bound is `MAX_TOTAL_ALLOCATION_BPS / 1 = 2000` contributors (minimum 1 bps each), so the growth is limited. Still, the array contains both active AND inactive contributors.

**Recommendation:**

Document the `getAllContributors()` function as off-chain only. Consider adding pagination via `contributorAt()` with `contributorCount()` for on-chain consumers (already provided — good).

---

### [L-3] `SALARY_CONTRACT_ROLE` Defined in ContributorRegistry But Unused

**Severity:** LOW
**Location:** `ContributorRegistry.sol:30`
**Impact:** Dead code — role is declared but no function in the registry requires it

**Description:**

`SALARY_CONTRACT_ROLE` is defined in ContributorRegistry and is presumably granted to ContributorSalary. However, no function in ContributorRegistry has `onlyRole(SALARY_CONTRACT_ROLE)`. The salary contract only reads from the registry (via `isActive()` and `getContributor()`), which are public view functions requiring no role.

**Recommendation:**

Remove `SALARY_CONTRACT_ROLE` from ContributorRegistry. If it's needed in TreasuryGate (which does use it), it should only be defined there. Defining unused roles creates confusion about intended permissions.

---

### [I-1] Single Admin Key Across All Contracts

**Severity:** INFO
**Location:** All constructors
**Impact:** Centralization risk — standard for early-stage projects

**Description:**

`DEFAULT_ADMIN_ROLE` is a single address on all three contracts. This address can grant/revoke all roles, modify all parameters, pause everything, and recover funds. The comments say "should be a Gnosis Safe multi-sig in production" — but the contracts don't enforce this.

**Note:** This is standard for early-stage deployments. The MY3YE mission explicitly values transparency and decentralization, so this should be addressed before mainnet launch.

**Recommendation:**

Consider requiring the admin to be a contract (not an EOA) at deploy time:
```solidity
require(admin.code.length > 0, "Admin must be a contract");
```

---

### [I-2] No `renounceRole` Protection

**Severity:** INFO
**Location:** Inherited from OpenZeppelin `AccessControl`
**Impact:** Admin could accidentally lock the system by renouncing DEFAULT_ADMIN_ROLE

**Description:**

OpenZeppelin's `AccessControl.renounceRole()` allows any role holder to permanently give up their role. If the only `DEFAULT_ADMIN_ROLE` holder renounces, the system becomes permanently locked — no new contributors can be added, no parameters can be changed, and `recoverUsdc()` becomes inaccessible.

**Recommendation:**

Override `renounceRole` to block renouncing DEFAULT_ADMIN_ROLE:
```solidity
function renounceRole(bytes32 role, address callerConfirmation) public override {
    require(role != DEFAULT_ADMIN_ROLE, "Cannot renounce admin");
    super.renounceRole(role, callerConfirmation);
}
```

---

### [I-3] USDC Address Consistency Not Enforced Cross-Contract

**Severity:** INFO
**Location:** `ContributorSalary.sol:170`, `TreasuryGate.sol:147`
**Impact:** Deployment misconfiguration could create inconsistent state

**Description:**

Both ContributorSalary and TreasuryGate store `usdc` as immutable, but they're set independently in their constructors. If different USDC addresses are used (e.g., native vs bridged USDC), the gate checks one token's balance while the salary contract transfers another.

**Recommendation:**

Add a deployment-time assertion in ContributorSalary's constructor:
```solidity
require(address(usdc) == address(gate.usdc()), "USDC mismatch");
```

---

## Positive Findings (What's Done Right)

1. **Immutable salary cap**: `GLOBAL_SALARY_CAP` is a `constant` — no governance, upgrade, or owner action can raise it. The 9k/month ceiling is cryptographically permanent per claim period.

2. **CEI pattern**: `_processClaim` follows checks-effects-interactions perfectly. State is written (line 267-275) before the USDC transfer (line 283).

3. **ReentrancyGuard + SafeERC20**: Belt-and-suspenders protection against reentrancy, even though USDC doesn't have reentrant hooks.

4. **Operator can't redirect funds**: `claimFor()` sends to `c.wallet` (registered address), never to `msg.sender`. Well-designed keeper pattern.

5. **Period-0 disambiguation**: `hasEverClaimed` mapping correctly handles the edge case where `lastClaimedPeriod = 0` could mean "period 0" or "never claimed".

6. **Allocation caps at both levels**: Per-contributor max (5%) AND aggregate max (20%) prevent treasury drainage through contributor inflation.

7. **Soft deactivation preserving history**: On-chain audit trail is maintained permanently. Deactivation timestamps are recorded.

8. **Emergency pause is bilateral**: Both TreasuryGate pause (blocks all claims via preClaimCheck) and ContributorSalary pause (blocks claim/claimFor) must be unpaused for claims to proceed. Either one can halt the system.

9. **Snapshot-based eligible pool**: The period opening balance snapshot prevents flash-loan manipulation of the eligible pool.

10. **`ABSOLUTE_MINIMUM_FLOOR`**: Governance can raise the floor but never zero it. The 10k USDC minimum reserve is immutable.

---

## Pre-Deployment Checklist

- [ ] **Fix H-1**: Set minimum period duration to 28 days
- [ ] **Fix H-2**: Make treasury address immutable OR add timelock
- [ ] **Fix M-1**: Use immutable recovery address for `recoverUsdc`
- [ ] **Fix M-2**: Either remove postClaimCheck or switch to `transferFrom` architecture
- [ ] **Fix M-3**: Wire `periodTotalPaid` into the pre-check or remove it
- [ ] Deploy admin as Gnosis Safe multi-sig (not EOA)
- [ ] Verify USDC address matches across both contracts at deployment
- [ ] Set `SALARY_CONTRACT_ROLE` on TreasuryGate for ContributorSalary address
- [ ] Fund ContributorSalary with exactly one period's worth of USDC (not more)
- [ ] Write Foundry fuzz tests for: period boundary claims, duration changes, floor edge cases
- [ ] External audit before mainnet deployment

---

*Audit by Otto Security Agent. Contracts audited from reference implementation produced during the contributor compensation plan task (2026-03-29).*

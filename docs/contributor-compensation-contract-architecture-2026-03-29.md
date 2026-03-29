# Contributor Compensation Contract System
## Treasury-Gated Salary Protocol for the MY3YE Ecosystem

*Authored by Otto (Architect Agent) | 2026-03-29 | Status: Architecture Complete*
*Depends on: OPRLP Governance, Labor Attestation Framework, Core Value Loop (SplitEngine), Three-Layer Capital Structure*

---

## Design: ContributorCompensation

### Problem

Mev needs a recurring salary drawn from the ecosystem reserve — $9,000/month (~$108K/year). But this cannot be an arbitrary admin withdrawal. The system must be constitutionally constrained: the treasury pays **only when it can afford to**, the amount is **capped regardless of treasury size**, and **every future contributor gets the same structure**. Investment capital must be locked by default — distributions flow only to verified contributors through this gated mechanism.

This is distinct from the CET revenue-share system (Labor Attestation) and the provenance-based split (Core Value Loop). Those distribute *revenue from production*. This distributes *treasury reserves as operating compensation* — the equivalent of a nonprofit's program officer salary, not equity dividends.

### Approach

A **ContributorCompensation** contract that manages a registry of compensated contributors, each with an allocation expressed as a basis-point percentage of treasury inflows (with a hard USD-equivalent cap). A **TreasuryGate** mechanism prevents any disbursement until the treasury balance exceeds a configurable floor. The contract interacts with the existing Movement Treasury (Gnosis Safe multi-sig) through a module pattern.

---

## 1. How It Works — Plain English

```
THE SALARY MACHINE:

  1. Treasury receives money (token sales, service revenue, grants, etc.)

  2. Contract checks: "Is the treasury above the minimum floor?"
     If NO  → Nobody gets paid. Capital stays locked.
     If YES → Proceed to step 3.

  3. Each registered contributor has an allocation:
     - Expressed as basis points (e.g., 50bp = 0.50% of monthly inflows)
     - Hard-capped at a USD-equivalent maximum (e.g., $9,000/month)
     - The LOWER of (% allocation) or (hard cap) applies

  4. Contributor calls claim() once per payment period.
     Contract calculates: min(allocation_bps × eligible_pool, hard_cap)
     Sends USDC to contributor's address.

  5. After payout, re-check: "Is treasury still above floor?"
     If a payout would drop treasury below floor → payout blocked.

  INVARIANT: Treasury balance NEVER drops below the configured floor
             due to compensation payouts. Floor is sacred.

  EXAMPLE — Mev's salary:
    Treasury balance: $500,000
    Treasury floor:   $100,000
    Eligible pool:    $500,000 - $100,000 = $400,000
    Mev's allocation: 50bp (0.50%)
    Calculated:       $400,000 × 0.005 = $2,000
    Hard cap:         $9,000
    Mev receives:     min($2,000, $9,000) = $2,000

    If treasury is $2,000,000:
    Eligible pool:    $2,000,000 - $100,000 = $1,900,000
    Calculated:       $1,900,000 × 0.005 = $9,500
    Hard cap:         $9,000
    Mev receives:     min($9,500, $9,000) = $9,000 ← capped
```

---

## 2. Key Design Decisions

### Decision 1: Percentage + Hard Cap (chosen) vs. Fixed Salary

**Chosen:** Allocation as basis points with a USD hard cap.

**Why:** A fixed $9K salary creates a rigid obligation that could drain a small treasury. A pure percentage scales with treasury size but has no upper bound. The hybrid — small % allocation capped at $9K — gives the right behavior:
- When treasury is small: payout is small (% dominates)
- When treasury is large: payout is capped at $9K (cap dominates)
- When treasury is below floor: payout is $0

**Alternative rejected:** Fixed salary — creates a drain obligation that ignores treasury health.

### Decision 2: Treasury Floor Gate (chosen) vs. Vesting Schedule

**Chosen:** Hard floor gate — no payouts if treasury balance < floor.

**Why:** Vesting is time-based (you get paid just for waiting). The floor gate is treasury-health-based (you get paid only when the system can afford it). This aligns incentives: contributors are motivated to grow the treasury, because their compensation depends on it.

**Alternative rejected:** Time-based vesting — pays regardless of treasury health, misaligned incentives.

### Decision 3: Claim-Based (chosen) vs. Push-Based Disbursement

**Chosen:** Contributors call `claim()` to receive their payment.

**Why:** Push-based (automatic transfers) requires a keeper or cron job, adds gas costs, and creates failure modes if a recipient address changes or is compromised. Claim-based is the standard pattern (Uniswap, Aave, Compound all use it). It's gas-efficient (claimer pays), secure (no push failures), and composable.

**Alternative rejected:** Push-based auto-transfer — requires keeper infrastructure, introduces failure modes.

### Decision 4: USDC-Denominated Caps (chosen) vs. ETH-Denominated

**Chosen:** All caps and floors denominated in USDC (stablecoin).

**Why:** A $9K cap in ETH fluctuates wildly. A $9K cap in USDC means $9K. The treasury may hold mixed assets (ETH, BTC, USDC), but the compensation contract operates in USDC. Treasury assets are converted to USDC for compensation via existing DeFi infrastructure (or held as USDC from service revenue).

**Alternative rejected:** ETH-denominated — salary volatility is unacceptable for living expenses.

### Decision 5: Gnosis Safe Module (chosen) vs. Standalone Treasury

**Chosen:** Deploy as a Gnosis Safe module on the existing Movement Treasury.

**Why:** The Movement Treasury (Gnosis Safe, 5-of-9 multi-sig) already exists in the capital architecture. A module pattern allows the compensation contract to execute transfers from the Safe without requiring a separate treasury. The Safe's multi-sig controls module installation/removal — governance retains ultimate authority.

**Alternative rejected:** Standalone treasury — fragments capital, requires separate funding flows, duplicates governance.

### Decision 6: Monthly Claim Periods (chosen) vs. Streaming (Sablier-style)

**Chosen:** Monthly claim periods with discrete payouts.

**Why:** Monthly aligns with Mev's requirement ($9K/month), is simpler to implement, and easier to audit. Streaming (Sablier/Superfluid) is elegant but adds protocol dependency and makes the treasury floor check harder (continuous outflow vs. discrete checks).

**Alternative considered:** Sablier streaming — more elegant but adds dependency and complicates floor enforcement. Could upgrade to streaming in Phase 2 if desired.

---

## 3. Contract Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         GNOSIS SAFE                                   │
│                    (Movement Treasury)                                 │
│                     5-of-9 multi-sig                                  │
│                                                                       │
│  Holds: USDC, ETH, BTC, $KOIN                                       │
│  Controls: Module enable/disable                                      │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │            MODULE: ContributorCompensation.sol                  │  │
│  │                                                                 │  │
│  │  ┌─────────────────┐   ┌──────────────────┐   ┌────────────┐ │  │
│  │  │ ContributorReg  │   │  TreasuryGate    │   │  ClaimCalc │ │  │
│  │  │                 │   │                  │   │            │ │  │
│  │  │ - registry[]    │   │ - floor          │   │ - bps      │ │  │
│  │  │ - roles         │   │ - balance check  │   │ - cap      │ │  │
│  │  │ - status        │   │ - post-payout    │   │ - period   │ │  │
│  │  │ - governance    │   │   recheck        │   │ - min()    │ │  │
│  │  └────────┬────────┘   └────────┬─────────┘   └─────┬──────┘ │  │
│  │           │                     │                     │        │  │
│  │           └─────────────────────┼─────────────────────┘        │  │
│  │                                 ▼                              │  │
│  │                          claim(contributor)                    │  │
│  │                                 │                              │  │
│  │                                 ▼                              │  │
│  │                      Safe.execTransactionFromModule()          │  │
│  │                         (USDC → contributor)                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │            MODULE: InvestmentLock.sol (optional Phase 2)       │  │
│  │                                                                 │  │
│  │  Enforces: investment capital cannot be withdrawn except       │  │
│  │  through ContributorCompensation or DAO-approved proposals     │  │
│  │  Lock period: configurable per funding round                   │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘

EXTERNAL INTEGRATIONS:

  ┌──────────────┐         ┌──────────────────┐
  │ DPCRegistry  │────────►│ ContributorComp  │  (optional: DPC-gated registration)
  │ (OPRLP)      │         │                  │
  └──────────────┘         └──────────────────┘

  ┌──────────────┐         ┌──────────────────┐
  │ Chainlink    │────────►│ ContributorComp  │  (USDC/USD price feed for cap)
  │ Price Feed   │         │                  │
  └──────────────┘         └──────────────────┘
```

---

## 4. Contract Interface Specification

### 4.1 ContributorCompensation.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Enum} from "@gnosis.pm/safe-contracts/contracts/common/Enum.sol";

interface IContributorCompensation {

    // ═══════════════════════════════════════════
    // STRUCTS
    // ═══════════════════════════════════════════

    struct Contributor {
        address wallet;           // payment destination
        uint16 allocationBps;     // basis points of eligible pool (1 bp = 0.01%)
        uint128 hardCapUsd;       // max payout per period in USD (6 decimals, matches USDC)
        uint32 startTimestamp;    // when compensation begins
        uint32 lastClaimPeriod;   // last period successfully claimed
        uint8 role;               // FOUNDER=0, CORE=1, CONTRIBUTOR=2, ADVISOR=3
        bool active;              // can be deactivated without removal
    }

    struct TreasuryConfig {
        uint128 floorUsd;         // minimum treasury balance (USDC, 6 decimals)
        uint32 periodDuration;    // claim period in seconds (default: 30 days)
        uint16 maxTotalBps;       // max total allocation across all contributors
        uint128 maxSingleCapUsd;  // max hard cap for any single contributor
    }

    // ═══════════════════════════════════════════
    // EVENTS
    // ═══════════════════════════════════════════

    event ContributorAdded(
        address indexed wallet,
        uint16 allocationBps,
        uint128 hardCapUsd,
        uint8 role
    );

    event ContributorDeactivated(address indexed wallet, string reason);
    event ContributorReactivated(address indexed wallet);
    event ContributorUpdated(address indexed wallet, uint16 newBps, uint128 newCap);

    event CompensationClaimed(
        address indexed contributor,
        uint32 indexed period,
        uint128 amountUsd,
        bool cappedByFloor,
        bool cappedByHardCap
    );

    event TreasuryConfigUpdated(
        uint128 newFloor,
        uint32 newPeriodDuration,
        uint16 newMaxTotalBps
    );

    event ClaimBlocked(
        address indexed contributor,
        uint32 indexed period,
        string reason  // "BELOW_FLOOR" | "ALREADY_CLAIMED" | "INACTIVE" | "POST_PAYOUT_FLOOR"
    );

    // ═══════════════════════════════════════════
    // CONTRIBUTOR REGISTRY
    // ═══════════════════════════════════════════

    /// @notice Add a new compensated contributor (governance-only)
    /// @param wallet Contributor's payment address
    /// @param allocationBps Basis points of eligible pool (max: 500 = 5%)
    /// @param hardCapUsd Maximum monthly payout in USDC (6 decimals)
    /// @param role Contributor role enum
    function addContributor(
        address wallet,
        uint16 allocationBps,
        uint128 hardCapUsd,
        uint8 role
    ) external;

    /// @notice Deactivate a contributor (governance-only). Does not delete history.
    function deactivateContributor(address wallet) external;

    /// @notice Reactivate a previously deactivated contributor (governance-only)
    function reactivateContributor(address wallet) external;

    /// @notice Update allocation or cap for existing contributor (governance-only)
    function updateContributor(
        address wallet,
        uint16 newAllocationBps,
        uint128 newHardCapUsd
    ) external;

    // ═══════════════════════════════════════════
    // CLAIM
    // ═══════════════════════════════════════════

    /// @notice Claim compensation for the current period
    /// @return amount The USDC amount transferred
    function claim() external returns (uint128 amount);

    /// @notice Preview what a contributor would receive if they claimed now
    /// @param contributor Address to preview
    /// @return amount Estimated payout
    /// @return blocked Whether the claim would be blocked
    /// @return reason If blocked, the reason string
    function previewClaim(address contributor)
        external
        view
        returns (uint128 amount, bool blocked, string memory reason);

    // ═══════════════════════════════════════════
    // TREASURY CONFIGURATION
    // ═══════════════════════════════════════════

    /// @notice Update treasury configuration (governance-only, timelock)
    function updateTreasuryConfig(
        uint128 newFloor,
        uint32 newPeriodDuration,
        uint16 newMaxTotalBps,
        uint128 newMaxSingleCap
    ) external;

    // ═══════════════════════════════════════════
    // VIEW FUNCTIONS
    // ═══════════════════════════════════════════

    /// @notice Get contributor details
    function getContributor(address wallet) external view returns (Contributor memory);

    /// @notice Get all active contributors
    function getActiveContributors() external view returns (Contributor[] memory);

    /// @notice Current treasury configuration
    function getTreasuryConfig() external view returns (TreasuryConfig memory);

    /// @notice Current period number (periods since contract deployment)
    function currentPeriod() external view returns (uint32);

    /// @notice Total basis points currently allocated
    function totalAllocatedBps() external view returns (uint16);

    /// @notice USDC balance of the treasury (Safe)
    function treasuryBalance() external view returns (uint128);

    /// @notice Eligible pool = treasury balance - floor
    function eligiblePool() external view returns (uint128);

    /// @notice Total compensation paid out across all time
    function totalPaidOut() external view returns (uint256);

    /// @notice Total compensation paid to a specific contributor
    function contributorTotalPaid(address wallet) external view returns (uint256);
}
```

### 4.2 Claim Calculation Logic (Pseudocode)

```
function claim():
    require(contributors[msg.sender].active, "INACTIVE")
    require(contributors[msg.sender].lastClaimPeriod < currentPeriod(), "ALREADY_CLAIMED")

    // Step 1: Treasury floor check
    usdc_balance = IERC20(USDC).balanceOf(SAFE)
    require(usdc_balance > config.floorUsd, "BELOW_FLOOR")

    // Step 2: Calculate eligible pool
    eligible = usdc_balance - config.floorUsd

    // Step 3: Calculate allocation
    allocation = (eligible * contributor.allocationBps) / 10000

    // Step 4: Apply hard cap
    payout = min(allocation, contributor.hardCapUsd)

    // Step 5: Post-payout floor recheck
    // Ensure this payout won't drop treasury below floor
    require(usdc_balance - payout >= config.floorUsd, "POST_PAYOUT_FLOOR")

    // Step 6: Execute transfer via Safe module
    contributor.lastClaimPeriod = currentPeriod()
    safe.execTransactionFromModule(
        USDC,             // to: USDC contract
        0,                // value: 0 ETH
        abi.encodeCall(IERC20.transfer, (msg.sender, payout)),
        Enum.Operation.Call
    )

    emit CompensationClaimed(msg.sender, currentPeriod(), payout, ...)
```

---

## 5. State Variables

```solidity
contract ContributorCompensation {

    // ═══ IMMUTABLES ═══
    address public immutable safe;      // Gnosis Safe address
    address public immutable usdc;      // USDC token address
    uint32 public immutable deployedAt; // deployment timestamp (period 0 start)

    // ═══ GOVERNANCE ═══
    address public governance;          // address that can add/remove contributors
                                        // Initially: Safe itself (multi-sig)
                                        // Future: LoopGovernor or OPRLP Council

    // ═══ TREASURY CONFIG ═══
    TreasuryConfig public config;
    // Default values:
    //   floorUsd:        100_000_000000  ($100,000 in USDC 6-decimal)
    //   periodDuration:  2_592_000       (30 days in seconds)
    //   maxTotalBps:     1000            (10% max total allocation)
    //   maxSingleCapUsd: 15_000_000000   ($15,000 max per contributor)

    // ═══ CONTRIBUTOR REGISTRY ═══
    mapping(address => Contributor) public contributors;
    address[] public contributorList;   // for enumeration
    uint16 public totalAllocatedBps;    // running sum, enforced on add/update

    // ═══ ACCOUNTING ═══
    mapping(address => uint256) public totalPaidTo;  // lifetime per contributor
    uint256 public totalPaidAll;                     // lifetime all contributors

    // ═══ TIMELOCK (for config changes) ═══
    uint32 public constant CONFIG_TIMELOCK = 48 hours;
    bytes32 public pendingConfigHash;
    uint32 public configUnlocksAt;
}
```

---

## 6. Access Control Model

```
ACCESS CONTROL HIERARCHY:

  ┌─────────────────────────────────────────────────────┐
  │  LEVEL 0: GNOSIS SAFE (5-of-9 multi-sig)            │
  │                                                       │
  │  Can: Enable/disable the module entirely              │
  │       Change governance address                       │
  │       Emergency pause (remove module = kill switch)   │
  │       Override any parameter via direct Safe tx        │
  │                                                       │
  │  This is the ultimate authority. The Safe can always  │
  │  remove the module and recover full manual control.   │
  └──────────────────────────┬──────────────────────────┘
                             │ delegates to
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │  LEVEL 1: GOVERNANCE (initially = Safe address)      │
  │                                                       │
  │  Can: addContributor()                                │
  │       deactivateContributor()                         │
  │       reactivateContributor()                         │
  │       updateContributor()                             │
  │       updateTreasuryConfig() (with 48h timelock)      │
  │                                                       │
  │  Future: transfer governance to LoopGovernor or       │
  │          OPRLP CouncilManager for DAO-controlled      │
  │          contributor management.                      │
  └──────────────────────────┬──────────────────────────┘
                             │
                             ▼
  ┌─────────────────────────────────────────────────────┐
  │  LEVEL 2: CONTRIBUTORS (individual addresses)        │
  │                                                       │
  │  Can: claim() — only for their own address            │
  │       previewClaim() — read-only for any address      │
  │                                                       │
  │  Cannot: modify registry, change config, claim for    │
  │          others, withdraw more than their allocation   │
  └─────────────────────────────────────────────────────┘


MODIFIERS:

  onlyGovernance:
    require(msg.sender == governance, "NOT_GOVERNANCE")

  onlySafe:
    require(msg.sender == safe, "NOT_SAFE")

  onlyActiveContributor:
    require(contributors[msg.sender].active, "NOT_ACTIVE")

  timelocked:
    For config changes: propose → wait 48h → execute
    Prevents governance from changing floor/caps instantly
    Contributors have 48h to react to pending changes
```

---

## 7. Treasury Gate — Threshold Logic

```
TREASURY GATE MECHANISM:

  The gate has THREE checkpoints, all must pass for a claim to succeed:

  ┌──────────────────────────────────────────────────────────┐
  │                                                           │
  │  CHECKPOINT 1: PRE-CLAIM FLOOR CHECK                     │
  │                                                           │
  │    treasury_balance = USDC.balanceOf(safe)                │
  │    require(treasury_balance > config.floorUsd)            │
  │                                                           │
  │    If treasury is at or below floor: BLOCKED              │
  │    Reason: "BELOW_FLOOR"                                  │
  │                                                           │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  CHECKPOINT 2: ELIGIBLE POOL CALCULATION                  │
  │                                                           │
  │    eligible_pool = treasury_balance - config.floorUsd     │
  │    payout = min(eligible_pool * bps / 10000, hardCap)     │
  │                                                           │
  │    The floor is NEVER included in the eligible pool.      │
  │    Even if all contributors claimed max, the floor        │
  │    remains untouched.                                     │
  │                                                           │
  ├──────────────────────────────────────────────────────────┤
  │                                                           │
  │  CHECKPOINT 3: POST-PAYOUT FLOOR RECHECK                 │
  │                                                           │
  │    require(treasury_balance - payout >= config.floorUsd)  │
  │                                                           │
  │    Defense-in-depth: even after calculating payout,       │
  │    verify the transfer won't breach the floor.            │
  │    Protects against edge cases where multiple claims      │
  │    happen in the same block.                              │
  │                                                           │
  └──────────────────────────────────────────────────────────┘


FLOOR CONFIGURATION:

  Default: $100,000 (100_000_000000 in USDC 6 decimals)

  The floor should represent the minimum operating reserve
  the ecosystem needs to survive. Factors:
    - 3 months of infrastructure costs (~$500/mo = $1,500)
    - Legal/compliance buffer (~$10,000)
    - Emergency fund (~$20,000)
    - Strategic reserve for opportunities (~$68,500)
    = ~$100,000 floor

  The floor is DAO-adjustable via updateTreasuryConfig()
  with a 48-hour timelock. Cannot be set below $10,000
  (hardcoded minimum — safety against governance attack).

  MINIMUM FLOOR CONSTANT:
    uint128 constant MIN_FLOOR = 10_000_000000; // $10,000
```

---

## 8. Cap Enforcement Mechanism

```
CAP ENFORCEMENT — TWO LAYERS:

  LAYER 1: PER-CONTRIBUTOR HARD CAP
  ═══════════════════════════════════

    Each contributor has a hardCapUsd field.
    The payout is ALWAYS: min(percentage_calculation, hardCapUsd)

    Mev's initial config:
      allocationBps = 50    (0.50% of eligible pool)
      hardCapUsd = 9_000_000000  ($9,000)

    At different treasury sizes (floor = $100K):
      Treasury $200K → eligible $100K → 0.5% = $500     → payout: $500
      Treasury $500K → eligible $400K → 0.5% = $2,000   → payout: $2,000
      Treasury $2M   → eligible $1.9M → 0.5% = $9,500   → payout: $9,000 (CAPPED)
      Treasury $5M   → eligible $4.9M → 0.5% = $24,500  → payout: $9,000 (CAPPED)
      Treasury $50K  → below floor                       → payout: $0 (BLOCKED)


  LAYER 2: GLOBAL ALLOCATION CAP
  ═══════════════════════════════════

    config.maxTotalBps limits total allocation across ALL contributors.
    Default: 1000 bps (10% of eligible pool per period).

    This prevents governance from registering 200 contributors at 50bps each
    (which would be 100% of the eligible pool).

    On addContributor() and updateContributor():
      require(totalAllocatedBps + newBps <= config.maxTotalBps)


  LAYER 3: PER-CONTRIBUTOR MAX CAP
  ═══════════════════════════════════

    config.maxSingleCapUsd prevents any single contributor from having
    an unreasonably high cap. Default: $15,000/month.

    On addContributor():
      require(hardCapUsd <= config.maxSingleCapUsd)

    This is a governance parameter — the DAO can raise it, but it
    prevents a compromised governance key from setting a $1M cap.


  ENFORCEMENT HIERARCHY (strictest wins):

    1. Treasury floor gate          → may reduce to $0
    2. Percentage of eligible pool  → scales with treasury
    3. Per-contributor hard cap     → absolute ceiling ($9K for Mev)
    4. Post-payout floor recheck    → defense-in-depth
    5. Global allocation cap        → prevents registry overstuffing
    6. Per-contributor max cap      → prevents governance abuse
```

---

## 9. Contributor Registry Design

### 9.1 Role Types

```
CONTRIBUTOR ROLES:

  FOUNDER (0):
    - First contributor (Mev)
    - Standard allocation + cap, no special privileges in the contract
    - Distinction exists for on-chain transparency, not for different rules
    - Cannot be deactivated without Safe multi-sig (extra protection)

  CORE (1):
    - Full-time core contributors
    - Same allocation/cap structure as founder
    - Can be added/deactivated by governance

  CONTRIBUTOR (2):
    - Part-time or project-based contributors
    - Typically lower allocation and/or cap
    - Can be added/deactivated by governance

  ADVISOR (3):
    - Advisory role, compensated for ongoing guidance
    - Typically lowest allocation, capped lower
    - Can be added/deactivated by governance

  All roles use the SAME claim logic. The role field is for
  transparency and potential future DPC-gating, not for
  different payment mechanics.
```

### 9.2 Registration Flow

```
ADDING A NEW CONTRIBUTOR:

  1. Governance calls addContributor(wallet, bps, cap, role)

  2. Contract validates:
     - wallet != address(0)
     - wallet not already registered
     - bps > 0 and bps <= 500 (max 5% per contributor)
     - cap > 0 and cap <= config.maxSingleCapUsd
     - totalAllocatedBps + bps <= config.maxTotalBps

  3. Contributor struct created:
     - startTimestamp = block.timestamp
     - lastClaimPeriod = currentPeriod() - 1  (can claim immediately)
     - active = true

  4. Event emitted: ContributorAdded(wallet, bps, cap, role)


DEACTIVATION (not deletion):

  - Contributor.active = false
  - Cannot claim while deactivated
  - History preserved (totalPaidTo, startTimestamp)
  - Can be reactivated by governance
  - allocationBps subtracted from totalAllocatedBps

  Why not delete? On-chain audit trail. Every contributor ever registered
  remains visible. Deactivation is reversible; deletion is not.


UPDATING TERMS:

  - Governance can change bps and cap for any active contributor
  - totalAllocatedBps adjusted atomically
  - Previous claims unaffected (no retroactive changes)
  - 48h timelock on updates that INCREASE allocation (protection against governance attack)
  - Decreases take effect immediately (governance can reduce if needed urgently)
```

### 9.3 Future: DPC-Gated Registration

```
OPTIONAL PHASE 2 ENHANCEMENT:

  Instead of pure governance discretion, contributor registration
  could require a minimum DPC score from DPCRegistry:

    function addContributor(...) {
        require(IDPCRegistry(dpcRegistry).getScore(wallet) >= MIN_DPC_FOR_COMP);
        // ... rest of registration
    }

  This would mean: you can only earn a salary if you've demonstrated
  meaningful contribution through the DPC system first.

  MIN_DPC thresholds by role:
    FOUNDER:     0 (bootstrapping exception — no DPC exists at genesis)
    CORE:        500 (Builder tier)
    CONTRIBUTOR: 100 (Contributor tier)
    ADVISOR:     250 (between Contributor and Builder)

  This is NOT in Phase 1. It requires DPCRegistry to be deployed first.
  The interface is designed to be addable without contract upgrade
  (governance can be transferred to a wrapper that enforces DPC checks).
```

---

## 10. Investment Capital Locking

```
CAPITAL LOCK MECHANISM:

  Mev's requirement: "All investment capital locked by default
  with distribution routed to verified contributors."

  This is enforced at TWO levels:

  LEVEL 1: GNOSIS SAFE GOVERNANCE (existing)
  ═════════════════════════════════════════════

    The Safe is 5-of-9 multi-sig. No single party can withdraw.
    Investment capital enters the Safe and is governed by majority vote.
    This is the baseline lock — all funds require multi-sig approval.

  LEVEL 2: MODULE RESTRICTION (new)
  ═════════════════════════════════════

    The ContributorCompensation module is the ONLY automated
    withdrawal path from the Safe. It can only:
    - Transfer USDC
    - To registered, active contributors
    - Up to their capped allocation
    - Only when treasury is above floor
    - Only once per period

    Any other withdrawal requires a direct Safe multi-sig transaction
    (5-of-9 approval).

  LEVEL 3: INVESTMENT LOCK MODULE (Phase 2, optional)
  ════════════════════════════════════════════════════════

    For formal investment rounds, deploy InvestmentLock.sol:

    struct InvestmentRound {
        bytes32 roundId;
        uint128 totalRaised;
        uint32 lockUntil;          // timestamp lock expires
        uint16 maxWithdrawalBps;   // max % withdrawable per period post-lock
        bool daoVoteRequired;      // require DAO vote for any withdrawal
    }

    This adds tagged capital tranches with time-locks:
    - Seed round: 12-month lock, then max 10%/quarter
    - Series A: 18-month lock, then max 5%/quarter
    - Treasury reserves: permanent lock (no expiry)

    The ContributorCompensation module operates INDEPENDENTLY
    of investment locks — salary payouts are from the eligible pool
    (above floor), not from locked tranches. If locked capital pushes
    the effective floor higher, salaries auto-adjust downward.


  RESULT:

    Investment capital → Safe (locked by multi-sig)
    Service revenue   → Safe (locked by multi-sig)
    Compensation      → ContributorCompensation module (only path for salary)
    Everything else   → Requires 5-of-9 Safe transaction

    Nobody — not even Mev — can withdraw investment capital unilaterally.
    The contract enforces this structurally, not by trust.
```

---

## 11. Upgrade & Governance Path

```
UPGRADE STRATEGY:

  ContributorCompensation.sol is deployed as an IMMUTABLE contract
  (no proxy, no upgradability).

  Why immutable:
    - This is a constitutional contract. Its rules should not change
      under contributors' feet.
    - The parameters (floor, caps, allocations) are configurable
      WITHOUT upgrading the contract.
    - If a fundamental change is needed, deploy a new version and
      migrate via Safe module swap.

  GOVERNANCE MIGRATION PATH:

    Phase 1 (launch):
      governance = Safe address
      → Multi-sig controls all contributor management
      → Simple, secure, appropriate for small team

    Phase 2 (DAO formation):
      governance = LoopGovernor address
      → DAO proposals control contributor management
      → Safe retains emergency override (can change governance back)
      → Transfer via: Safe calls setGovernance(loopGovernor)

    Phase 3 (full decentralization):
      governance = OPRLP CouncilManager
      → Elected councils manage compensation via council votes
      → LoopGovernor used for parameter changes only
      → Safe becomes emergency-only (circuit breaker)


  MODULE REPLACEMENT:

    If the contract needs to be replaced entirely:
    1. Deploy ContributorCompensationV2
    2. Safe multi-sig: enableModule(v2) + disableModule(v1)
    3. V2 reads contributor list from V1 (view functions)
    4. Governance re-registers contributors in V2 (or V2 constructor migrates)

    This is a deliberate friction — replacing the compensation contract
    should be hard. It protects contributors from arbitrary changes.


  PARAMETER CHANGE GOVERNANCE:

    All config changes go through 48h timelock:

    1. Governance calls proposeConfigUpdate(newConfig)
       → pendingConfigHash = keccak256(abi.encode(newConfig))
       → configUnlocksAt = block.timestamp + 48 hours
       → Event: ConfigUpdateProposed(newConfig, configUnlocksAt)

    2. 48 hours pass. Contributors can see the pending change on-chain.

    3. Governance calls executeConfigUpdate(newConfig)
       → require(keccak256(abi.encode(newConfig)) == pendingConfigHash)
       → require(block.timestamp >= configUnlocksAt)
       → Config applied

    4. Emergency cancel: governance can cancel a pending update
       (pendingConfigHash = 0)

    WHY 48H:
      Contributors should never be surprised by a floor drop or cap change.
      48h gives them time to claim current-period compensation and react.
```

---

## 12. Mev's Initial Configuration

```
FOUNDER REGISTRATION (Day 1):

  addContributor(
    wallet:        MEV_ADDRESS,          // Mev's wallet
    allocationBps: 50,                   // 0.50% of eligible pool
    hardCapUsd:    9_000_000000,         // $9,000 USDC (6 decimals)
    role:          0                     // FOUNDER
  )

  Treasury config:
    floorUsd:        100_000_000000      // $100,000
    periodDuration:  2_592_000           // 30 days
    maxTotalBps:     1000                // 10% max total allocation
    maxSingleCapUsd: 15_000_000000       // $15,000 per contributor


PAYOUT SCENARIOS:

  ┌────────────────┬─────────────┬──────────┬────────────┬─────────┐
  │ Treasury USDC  │ Floor       │ Eligible │ 0.50%      │ Payout  │
  ├────────────────┼─────────────┼──────────┼────────────┼─────────┤
  │ $50,000        │ $100,000    │ $0       │ $0         │ $0      │
  │ $100,000       │ $100,000    │ $0       │ $0         │ $0      │
  │ $150,000       │ $100,000    │ $50,000  │ $250       │ $250    │
  │ $500,000       │ $100,000    │ $400,000 │ $2,000     │ $2,000  │
  │ $1,000,000     │ $100,000    │ $900,000 │ $4,500     │ $4,500  │
  │ $1,900,000     │ $100,000    │ $1.8M    │ $9,000     │ $9,000  │
  │ $2,000,000     │ $100,000    │ $1.9M    │ $9,500     │ $9,000* │
  │ $10,000,000    │ $100,000    │ $9.9M    │ $49,500    │ $9,000* │
  │ $50,000,000    │ $100,000    │ $49.9M   │ $249,500   │ $9,000* │
  └────────────────┴─────────────┴──────────┴────────────┴─────────┘
  * = capped by hardCapUsd

  BREAKEVEN (full $9K payout):
    Need: 0.50% × eligible = $9,000
    eligible = $9,000 / 0.005 = $1,800,000
    Treasury = $1,800,000 + $100,000 floor = $1,900,000

    Mev receives full $9K/month when treasury exceeds $1.9M.
    Below that, compensation scales linearly with treasury size.
```

---

## 13. Security Considerations

```
ATTACK VECTORS & MITIGATIONS:

  1. GOVERNANCE KEY COMPROMISE
     Attack: Attacker gains governance key, registers fake contributors
     Mitigation:
       - maxTotalBps (10%) limits total drainable per period
       - maxSingleCapUsd ($15K) limits per-contributor
       - Floor protection means minimum $100K stays in treasury
       - 48h timelock on config changes gives time to detect
       - Safe can disable module instantly (emergency kill switch)

  2. FLASH LOAN TREASURY INFLATION
     Attack: Inflate treasury USDC balance via flash loan, claim, repay
     Mitigation:
       - claim() transfers USDC FROM the Safe, not from the contract
       - Flash loans add to attacker's balance, not the Safe's
       - Safe balance only changes via real deposits
       - Non-issue: you can't flash-loan USDC into a Gnosis Safe

  3. REENTRANCY
     Attack: Malicious contributor contract re-enters claim()
     Mitigation:
       - lastClaimPeriod updated BEFORE transfer (CEI pattern)
       - Safe.execTransactionFromModule is the transfer vector,
         not a raw .call() — Safe handles reentrancy
       - Additional: ReentrancyGuard from OpenZeppelin

  4. PERIOD MANIPULATION
     Attack: Manipulate block.timestamp to claim multiple periods
     Mitigation:
       - Period = (block.timestamp - deployedAt) / periodDuration
       - lastClaimPeriod tracks the last claimed period number
       - Cannot claim the same period twice
       - Block timestamp manipulation is limited to ~15 seconds
         (not enough to skip a 30-day period)

  5. DUSTY ELIGIBLE POOL
     Attack: Treasury barely above floor, many contributors claim tiny amounts
     Mitigation:
       - Post-payout floor recheck prevents breaching floor
       - Each claim independently verified against current balance
       - If 10 contributors claim in the same block, each one's
         post-payout check accounts for preceding transfers
       - Natural rate limit: claims are once per 30-day period

  6. GOVERNANCE CAPTURE (long-term)
     Attack: Attacker accumulates enough DPC/tokens to control governance
     Mitigation:
       - Safe retains ultimate authority (can change governance address)
       - 48h timelock on all config changes
       - Immutable contract — no upgradable code paths
       - OPRLP anti-cartel detection (Phase 2 integration)
       - FounderSunset does NOT apply to compensation contract
         (Mev's salary is a contributor allocation, not a founder privilege)
```

---

## 14. Composition with Existing Contracts

```
CONTRACT ECOSYSTEM MAP:

  ┌─────────────────────────────────────────────────────────────────┐
  │                        GOVERNANCE LAYER                          │
  │                                                                   │
  │  DPCRegistry ──► GovernanceWeight ──► ElectionEngine              │
  │       │                                    │                      │
  │       │            CouncilManager ◄────────┘                      │
  │       │                 │                                         │
  │       ▼                 ▼                                         │
  │  ┌──────────────────────────────────────────────────────┐        │
  │  │         ContributorCompensation (THIS CONTRACT)      │        │
  │  │                                                       │        │
  │  │  DPCRegistry: optional Phase 2 registration gate     │        │
  │  │  CouncilManager: optional Phase 2 governance source  │        │
  │  └──────────────────────────────────────────────────────┘        │
  └─────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────┐
  │                        ECONOMIC LAYER                            │
  │                                                                   │
  │  ContributionRegistry ──► SplitEngine ──► RevenueRouter          │
  │                                │                                  │
  │                                ▼                                  │
  │                          EquityTreasury                           │
  │                                                                   │
  │  RELATIONSHIP: ContributorCompensation is SEPARATE from          │
  │  EquityTreasury. EquityTreasury distributes production revenue   │
  │  proportional to CET. ContributorCompensation distributes        │
  │  treasury reserves as operating salary. A contributor can earn   │
  │  BOTH: CET revenue share + monthly salary.                      │
  └─────────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────────┐
  │                        TREASURY LAYER                            │
  │                                                                   │
  │  Gnosis Safe (Movement Treasury)                                 │
  │    │                                                              │
  │    ├── Module: ContributorCompensation (salary payouts)          │
  │    ├── Module: InvestmentLock (capital lock enforcement)          │
  │    └── Direct txs: operational spending (5-of-9 approval)        │
  │                                                                   │
  │  USDC flows IN via:                                              │
  │    - Token sales → Safe                                          │
  │    - Service revenue (WebAssist, etc.) → Safe                    │
  │    - Grants → Safe                                               │
  │    - SplitEngine protocol fees → Safe                            │
  │                                                                   │
  │  USDC flows OUT via:                                             │
  │    - ContributorCompensation.claim() → contributor wallets       │
  │    - Safe multi-sig txs → operational expenses                   │
  └─────────────────────────────────────────────────────────────────┘
```

---

## 15. Implementation Plan

### Phase 1: Core Contract (~$8-10)

| Step | Task | Est. Cost | Details |
|------|------|-----------|---------|
| 1 | Foundry project setup in `/mnt/media/projects/contributor-compensation/` | $0.50 | foundry.toml, OpenZeppelin + Safe imports, directory structure |
| 2 | IContributorCompensation.sol interface | $1.00 | Full interface from Section 4.1 |
| 3 | ContributorCompensation.sol core | $3.00 | Registry, claim logic, floor gate, cap enforcement |
| 4 | Unit tests: registry operations | $1.50 | add/deactivate/reactivate/update contributor |
| 5 | Unit tests: claim logic | $2.00 | All payout scenarios from Section 12, edge cases |
| 6 | Unit tests: security vectors | $1.50 | Reentrancy, period manipulation, governance attacks |
| 7 | Deploy script (anvil local) | $0.50 | DeployLocal.s.sol with mock Safe |

### Phase 2: Investment Lock + DPC Gate (~$5-7)

| Step | Task | Est. Cost | Depends On |
|------|------|-----------|------------|
| 8 | InvestmentLock.sol module | $2.50 | Phase 1 |
| 9 | DPC-gated registration wrapper | $1.50 | DPCRegistry deployed |
| 10 | Integration tests (Compensation + Lock + DPC) | $2.00 | Steps 8-9 |
| 11 | Testnet deployment (Base Sepolia) | $1.00 | Step 10 |

### Phase 3: Governance Migration (~$3-4)

| Step | Task | Est. Cost | Depends On |
|------|------|-----------|------------|
| 12 | LoopGovernor integration (governance = DAO) | $1.50 | LoopGovernor deployed |
| 13 | OMS dashboard page (compensation visibility) | $2.00 | Phase 1 |
| 14 | Mainnet deployment (Base) | $0.50 | Phase 2 complete |

### Dependency Chain

```
Phase 1: Interface → Core → Tests → Deploy script
Phase 2: InvestmentLock → DPC gate → Integration tests → Testnet
Phase 3: Governance migration → OMS page → Mainnet

External dependencies:
  - Gnosis Safe deployment (Phase 1 — can use existing or deploy new)
  - DPCRegistry (Phase 2 — already designed in OPRLP)
  - LoopGovernor (Phase 3 — already designed in Core Value Loop)
```

### Total Estimated Cost: ~$16-21 across all phases

---

## 16. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Safe module security | HIGH | Use audited Gnosis Safe module interface. The module pattern is battle-tested (used by Aave, MakerDAO). Limit module to USDC transfers only. |
| Governance key compromise | HIGH | Multi-sig governance (Safe). 48h timelock on config changes. Emergency kill switch (disable module). |
| Treasury never reaches floor | MEDIUM | Expected — early stage. Contributors know salary activates when treasury is funded. This IS the design working correctly. |
| USDC depeg | LOW | Floor and caps are in USDC units. If USDC depegs, the contract still operates — it just pays depegged USDC. Could add Chainlink oracle for USD-equivalent in Phase 2. |
| Too many contributors dilute eligible pool | LOW | maxTotalBps (10%) caps total allocation. At 10% with $1.9M treasury, that's $190K/month total compensation budget — more than sufficient for early team. |
| Contract needs functionality not in V1 | LOW | Immutable by design. Deploy V2 + module swap. Contributor list readable from V1 for migration. |

---

## 17. Summary

This is a clean, minimal contract that does exactly one thing: pay verified contributors from the treasury, gated by treasury health, capped per contributor and globally.

**The invariants:**
1. Treasury NEVER drops below floor due to compensation payouts
2. No contributor ever receives more than their hard cap per period
3. Total compensation never exceeds maxTotalBps of the eligible pool
4. Only registered, active contributors can claim
5. Investment capital is locked by Safe multi-sig — compensation is the only automated outflow path
6. All parameters are DAO-adjustable with timelock protection

**What Mev gets on Day 1:**
- Registered as FOUNDER with 50bp allocation, $9K cap
- Claims $0 until treasury exceeds $100K floor
- Salary scales linearly from $0 to $9K as treasury grows from $100K to $1.9M
- At $1.9M+ treasury: full $9K/month, permanently capped there
- Every future contributor gets the exact same structure — same rules, same contract

The contract is simple enough to audit in an afternoon. That is deliberate.

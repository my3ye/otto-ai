// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/// @title TreasuryGate
/// @notice Threshold logic determining when the treasury is healthy enough to pay salaries.
///         This contract does not hold funds — it reads treasury USDC balance and enforces
///         the floor invariant: NO payout may reduce the treasury below the floor.
///
/// @dev Two-phase gate:
///      Phase 1 — Pre-payout check:  Is the treasury above the floor? No → block all claims.
///      Phase 2 — Post-payout check: Would this specific payout drop the treasury below
///                                   the floor? Yes → block this specific claim.
///
///      Both checks must pass. The floor is the protocol's immune system.
///
///      The treasury is an external address — either a Gnosis Safe or any USDC holder.
///      This contract has no transfer authority. It is read-only by design.
///      ContributorSalary.sol calls `preClaimCheck()` and `postClaimCheck()` to gate
///      all disbursements. The salary contract must hold spending authority separately.
///
/// @custom:security-contact admin@otto.lk
contract TreasuryGate is AccessControl, Pausable {
    // =========================================================================
    //                              ROLES
    // =========================================================================

    /// @notice Can update floor, period duration, and treasury address.
    bytes32 public constant GATE_ADMIN_ROLE = keccak256("GATE_ADMIN_ROLE");

    /// @notice Granted to ContributorSalary.sol — the only contract that may call
    ///         the mutating gate functions (recordPreClaimBalance / validatePostClaim).
    bytes32 public constant SALARY_CONTRACT_ROLE = keccak256("SALARY_CONTRACT_ROLE");

    // =========================================================================
    //                              CONSTANTS
    // =========================================================================

    /// @notice Absolute minimum floor that governance can ever set.
    ///         Prevents treasury governance from zeroing the floor and enabling
    ///         unrestricted withdrawals through this module.
    ///         10,000 USDC = minimum operational reserve.
    uint128 public constant ABSOLUTE_MINIMUM_FLOOR = 10_000e6; // 10k USDC, 6 decimals

    /// @notice Minimum claim period duration: 28 days.
    ///         FIX H-1: Raised from 7 days to 28 days. A 7-day period enables
    ///         4x monthly payouts (36k/month), breaking the 9k/month intent.
    ///         28 days enforces at most one claim per calendar month.
    uint32 public constant MIN_PERIOD_DURATION = 28 days; // 2419200 seconds

    // =========================================================================
    //                              STATE
    // =========================================================================

    /// @notice The USDC token contract on Polygon zkEVM.
    ///         Polygon zkEVM USDC (bridged): 0xA8CE8aee21bC2A48a5EF670afCc9274C7bbbC035
    ///         This is set at deploy time and is immutable.
    IERC20 public immutable usdc;

    /// @notice Address of the treasury being protected (Gnosis Safe or multi-sig).
    ///         This is what TreasuryGate reads balances from.
    ///         Updatable by GATE_ADMIN_ROLE via 7-day timelocked propose/execute pattern.
    address public treasury;

    /// @notice Minimum USDC balance the treasury must maintain at all times (6 decimals).
    ///         No salary payout may reduce the treasury below this value.
    ///         Updatable by governance — but always >= ABSOLUTE_MINIMUM_FLOOR.
    uint128 public floorUsd;

    /// @notice Duration of a claim period in seconds.
    ///         Default: 28 days. Minimum: 28 days (MIN_PERIOD_DURATION). Updatable by governance.
    ///         The salary contract uses this value to compute current claim periods.
    uint32 public periodDuration;

    /// @notice Protocol launch timestamp. Claim period numbering starts here.
    ///         Set at initialization, immutable thereafter. Period 0 starts at launch.
    uint64 public immutable launchTimestamp;

    /// @notice Snapshot of treasury balance at the start of the current period.
    ///         Recorded by ContributorSalary on the first claim each period.
    ///         Used as the reference balance for the eligible pool calculation.
    ///         This prevents mid-period treasury inflows from changing the eligible pool.
    uint128 public periodOpeningBalance;

    /// @notice The period number for which periodOpeningBalance was recorded.
    uint32 public snapshotPeriod;

    /// @notice Running total of USDC paid out in the current snapshot period.
    ///         Reset when a new period snapshot is taken.
    uint128 public periodTotalPaid;

    // ── FIX H-2: Treasury address change timelock ──────────────────────
    // Prevents instant treasury address swaps that could bypass floor checks
    // by pointing to any USDC-holding address. Uses the same timelock pattern
    // as ContributorSalary.sol's floor/period changes.

    /// @notice Timelock duration for treasury address changes.
    uint32 public constant TREASURY_CHANGE_TIMELOCK = 7 days;

    /// @notice Pending new treasury address (address(0) = no pending change).
    address public pendingTreasury;

    /// @notice Timestamp when pending treasury change becomes executable.
    uint64 public treasuryChangeUnlocksAt;

    // =========================================================================
    //                              EVENTS
    // =========================================================================

    /// @notice Emitted when the treasury floor is updated.
    event FloorUpdated(uint128 oldFloor, uint128 newFloor, address updatedBy);

    /// @notice Emitted when the claim period duration is updated.
    event PeriodDurationUpdated(uint32 oldDuration, uint32 newDuration, address updatedBy);

    /// @notice Emitted when a period snapshot is taken (first claim of a new period).
    event PeriodSnapshotTaken(uint32 indexed period, uint128 openingBalance, uint64 takenAt);

    /// @notice Emitted when a treasury address change is proposed.
    event TreasuryChangeProposed(address indexed newTreasury, uint64 unlocksAt, address proposedBy);

    /// @notice Emitted when a pending treasury change is executed.
    event TreasuryChangeExecuted(address indexed oldTreasury, address indexed newTreasury, address executedBy);

    /// @notice Emitted when a pending treasury change is cancelled.
    event TreasuryChangeCancelled(address indexed cancelledTreasury, address cancelledBy);

    /// @notice Emitted when a payout is approved by the gate.
    event PayoutApproved(
        address indexed contributor,
        uint32 indexed period,
        uint128 amount,
        uint128 balanceAfter
    );

    // =========================================================================
    //                              ERRORS
    // =========================================================================

    error ZeroAddress();
    error TreasuryBelowFloor(uint128 currentBalance, uint128 floor);
    error PayoutWouldBreachFloor(uint128 currentBalance, uint128 payout, uint128 floor);
    error FloorBelowAbsoluteMinimum(uint128 requested, uint128 absoluteMinimum);
    error ZeroPeriodDuration();
    error PeriodDurationTooShort(uint32 requested, uint32 minimum);
    error PeriodDurationTooLong(uint32 requested, uint32 maximum);
    error TreasuryChangeAlreadyPending();
    error NoTreasuryChangePending();
    error TreasuryChangeNotUnlockedYet(uint64 unlocksAt, uint64 currentTime);

    // =========================================================================
    //                              CONSTRUCTOR
    // =========================================================================

    /// @param usdcAddress      Address of USDC on Polygon zkEVM.
    /// @param treasuryAddress  Address of the Movement Treasury (Gnosis Safe).
    /// @param initialFloor     Initial treasury floor in USDC (6 decimals).
    ///                         Must be >= ABSOLUTE_MINIMUM_FLOOR.
    /// @param admin            Address receiving GATE_ADMIN_ROLE + DEFAULT_ADMIN_ROLE.
    constructor(
        address usdcAddress,
        address treasuryAddress,
        uint128 initialFloor,
        address admin
    ) {
        if (usdcAddress == address(0)) revert ZeroAddress();
        if (treasuryAddress == address(0)) revert ZeroAddress();
        if (admin == address(0)) revert ZeroAddress();
        if (initialFloor < ABSOLUTE_MINIMUM_FLOOR) {
            revert FloorBelowAbsoluteMinimum(initialFloor, ABSOLUTE_MINIMUM_FLOOR);
        }

        usdc = IERC20(usdcAddress);
        treasury = treasuryAddress;
        floorUsd = initialFloor;
        periodDuration = 28 days; // FIX H-1: 28-day minimum enforces monthly cadence (see MIN_PERIOD_DURATION)
        launchTimestamp = uint64(block.timestamp);

        // FIX C1: Initialize snapshotPeriod to max sentinel so it never matches
        // getCurrentPeriod() (which returns 0 for period 0). Without this, the
        // condition `snapshotPeriod != currentPeriod` is false in period 0,
        // preventing the snapshot from being taken — periodOpeningBalance stays 0,
        // getEligiblePool() returns 0, and all period 0 claims revert with ZeroPayout.
        snapshotPeriod = type(uint32).max;

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GATE_ADMIN_ROLE, admin);
    }

    // =========================================================================
    //                         GATE FUNCTIONS (called by ContributorSalary)
    // =========================================================================

    /// @notice Pre-claim gate check. Called by ContributorSalary before processing any claim.
    ///         If this reverts, the claim is blocked and no state changes occur.
    ///
    ///         Side effect: If this is the first claim of a new period, takes a balance
    ///         snapshot that anchors the eligible pool calculation for the entire period.
    ///         This prevents Mev from timing claims with treasury inflows to game the
    ///         eligible pool — the snapshot is taken once per period and is immutable
    ///         for that period's duration.
    ///
    /// @param contributor  The contributor requesting a claim (for event emission).
    /// @param amount       The payout amount being requested (6 decimals, USDC).
    function preClaimCheck(
        address contributor,
        uint128 amount
    ) external onlyRole(SALARY_CONTRACT_ROLE) whenNotPaused {
        uint32 currentPeriod = getCurrentPeriod();

        // Take snapshot if this is the first claim of the period.
        // We do NOT update if the snapshot already exists for this period.
        if (snapshotPeriod != currentPeriod) {
            uint128 balance = _readTreasuryBalance();
            periodOpeningBalance = balance;
            snapshotPeriod = currentPeriod;
            periodTotalPaid = 0;
            emit PeriodSnapshotTaken(currentPeriod, balance, uint64(block.timestamp));
        }

        // Phase 1: Is the treasury above the floor right now?
        uint128 currentBalance = _readTreasuryBalance();
        if (currentBalance <= floorUsd) {
            revert TreasuryBelowFloor(currentBalance, floorUsd);
        }

        // Phase 2: Would this payout breach the floor?
        // FIX M-3: periodTotalPaid was tracked but never used in the check (dead code).
        // Now we subtract periodTotalPaid from currentBalance to get worst-case effective
        // balance when multiple claims are approved in the same block before transfers settle.
        // Without this, two concurrent pre-claim approvals could both pass even though only
        // one payout's worth of headroom exists above the floor.
        uint128 effectiveBalance = currentBalance;
        if (periodTotalPaid < effectiveBalance) {
            effectiveBalance -= periodTotalPaid;
        } else {
            effectiveBalance = 0;
        }
        if (effectiveBalance < amount + floorUsd) {
            revert PayoutWouldBreachFloor(effectiveBalance, amount, floorUsd);
        }

        // Record this approval in the running period total.
        // This happens before the actual transfer in ContributorSalary — the transfer
        // will either succeed (and the balance drops as expected) or revert (and this
        // whole tx reverts, cleaning up periodTotalPaid as well).
        periodTotalPaid += amount;

        emit PayoutApproved(contributor, currentPeriod, amount, effectiveBalance - amount);
    }

    /// @notice Post-claim validation. Called by ContributorSalary AFTER the USDC transfer
    ///         to verify the treasury did not drop below the floor.
    ///         If this check fails, the entire transaction reverts — USDC transfer included.
    ///         This is the final safety net: belt AND suspenders.
    ///
    /// @dev    AUDIT M-2 NOTE: This is NOT a no-op despite pre-claim arithmetic checks.
    ///         The pre-claim check reasons about expected post-transfer state using
    ///         periodTotalPaid accounting. This check reads actual on-chain USDC balance
    ///         AFTER the real transfer. They can diverge when:
    ///         (a) Another transaction moves USDC from the treasury in the same block.
    ///         (b) A fee-on-transfer token is used (not USDC today, but future-proofs).
    ///         (c) Safe module execution has unexpected side effects.
    ///         This catches all three cases and reverts the entire tx including the transfer.
    function postClaimCheck() external view onlyRole(SALARY_CONTRACT_ROLE) {
        uint128 currentBalance = _readTreasuryBalance();
        if (currentBalance < floorUsd) {
            revert PayoutWouldBreachFloor(currentBalance, 0, floorUsd);
        }
    }

    // =========================================================================
    //                         GOVERNANCE FUNCTIONS
    // =========================================================================

    /// @notice Update the treasury floor. Only governance can call this.
    ///         Floor can never be set below ABSOLUTE_MINIMUM_FLOOR.
    /// @param newFloor New floor in USDC (6 decimals).
    function setFloor(uint128 newFloor) external onlyRole(GATE_ADMIN_ROLE) {
        if (newFloor < ABSOLUTE_MINIMUM_FLOOR) {
            revert FloorBelowAbsoluteMinimum(newFloor, ABSOLUTE_MINIMUM_FLOOR);
        }
        uint128 oldFloor = floorUsd;
        floorUsd = newFloor;
        emit FloorUpdated(oldFloor, newFloor, msg.sender);
    }

    /// @notice Propose a new treasury address. Starts 7-day timelock.
    ///         FIX H-2: Treasury address changes now require a 7-day timelock to prevent
    ///         instant swaps that could bypass floor protection by pointing to any
    ///         USDC-holding address. Contributors have 7 days to react.
    /// @param newTreasury New treasury address to propose.
    function proposeTreasuryChange(address newTreasury) external onlyRole(GATE_ADMIN_ROLE) {
        if (newTreasury == address(0)) revert ZeroAddress();
        if (pendingTreasury != address(0)) revert TreasuryChangeAlreadyPending();

        pendingTreasury = newTreasury;
        treasuryChangeUnlocksAt = uint64(block.timestamp) + TREASURY_CHANGE_TIMELOCK;

        emit TreasuryChangeProposed(newTreasury, treasuryChangeUnlocksAt, msg.sender);
    }

    /// @notice Execute a pending treasury address change after the 7-day timelock.
    function executeTreasuryChange() external onlyRole(GATE_ADMIN_ROLE) {
        if (pendingTreasury == address(0)) revert NoTreasuryChangePending();
        if (block.timestamp < treasuryChangeUnlocksAt) {
            revert TreasuryChangeNotUnlockedYet(treasuryChangeUnlocksAt, uint64(block.timestamp));
        }

        address oldTreasury = treasury;
        address newTreasury = pendingTreasury;
        treasury = newTreasury;

        // Clear pending state
        pendingTreasury = address(0);
        treasuryChangeUnlocksAt = 0;

        emit TreasuryChangeExecuted(oldTreasury, newTreasury, msg.sender);
    }

    /// @notice Cancel a pending treasury address change.
    function cancelTreasuryChange() external onlyRole(GATE_ADMIN_ROLE) {
        if (pendingTreasury == address(0)) revert NoTreasuryChangePending();
        address cancelled = pendingTreasury;

        pendingTreasury = address(0);
        treasuryChangeUnlocksAt = 0;

        emit TreasuryChangeCancelled(cancelled, msg.sender);
    }

    /// @notice Update the claim period duration.
    ///         Minimum: 28 days (MIN_PERIOD_DURATION). Maximum: 365 days.
    ///         FIX H-1: Raised minimum from 7 days to 28 days to enforce monthly cadence.
    ///         Changing this mid-flight will shift future period boundaries but does not
    ///         retroactively invalidate in-progress periods.
    /// @param newDuration New period duration in seconds.
    function setPeriodDuration(uint32 newDuration) external onlyRole(GATE_ADMIN_ROLE) {
        if (newDuration < MIN_PERIOD_DURATION) revert PeriodDurationTooShort(newDuration, MIN_PERIOD_DURATION);
        if (newDuration > 365 days) revert PeriodDurationTooLong(newDuration, 365 days);
        uint32 oldDuration = periodDuration;
        periodDuration = newDuration;
        emit PeriodDurationUpdated(oldDuration, newDuration, msg.sender);
    }

    // =========================================================================
    //                         EMERGENCY CONTROLS
    // =========================================================================

    /// @notice Pause the gate. Blocks all claims (preClaimCheck reverts when paused).
    function pause() external onlyRole(GATE_ADMIN_ROLE) {
        _pause();
    }

    /// @notice Unpause the gate.
    function unpause() external onlyRole(GATE_ADMIN_ROLE) {
        _unpause();
    }

    // =========================================================================
    //                         VIEW FUNCTIONS
    // =========================================================================

    /// @notice Get the current claim period number.
    ///         Period 0 starts at launchTimestamp. Increments every periodDuration seconds.
    /// @return The current period number (0-indexed).
    function getCurrentPeriod() public view returns (uint32) {
        uint256 elapsed = block.timestamp - launchTimestamp;
        return uint32(elapsed / periodDuration);
    }

    /// @notice Get the start timestamp of a specific period.
    /// @param period The period number.
    /// @return The Unix timestamp at which the period begins.
    function getPeriodStart(uint32 period) external view returns (uint64) {
        return launchTimestamp + uint64(period) * uint64(periodDuration);
    }

    /// @notice Get the end timestamp of a specific period.
    /// @param period The period number.
    /// @return The Unix timestamp at which the period ends (exclusive).
    function getPeriodEnd(uint32 period) external view returns (uint64) {
        return launchTimestamp + (uint64(period) + 1) * uint64(periodDuration);
    }

    /// @notice Read the live treasury USDC balance.
    /// @return Live USDC balance of the treasury address.
    function getTreasuryBalance() external view returns (uint128) {
        return _readTreasuryBalance();
    }

    /// @notice Compute the eligible pool for the current period.
    ///         Eligible = max(0, periodOpeningBalance - floor)
    ///         If no snapshot exists for this period yet, uses live balance.
    /// @return pool The eligible pool in USDC (6 decimals).
    function getEligiblePool() external view returns (uint128 pool) {
        uint128 reference;
        if (snapshotPeriod == getCurrentPeriod()) {
            // Snapshot exists — use anchored opening balance
            reference = periodOpeningBalance;
        } else {
            // No snapshot yet — use live balance (first claimant will snapshot it)
            reference = _readTreasuryBalance();
        }
        if (reference <= floorUsd) return 0;
        // Safe: reference > floorUsd, result fits uint128
        unchecked {
            pool = reference - floorUsd;
        }
    }

    /// @notice Check whether the treasury is currently above the floor.
    /// @return True if treasury balance > floor (payouts are possible).
    function isTreasuryHealthy() external view returns (bool) {
        return _readTreasuryBalance() > floorUsd;
    }

    /// @notice Get the amount of headroom above the floor.
    ///         Headroom = max(0, currentBalance - floor).
    ///         This is the maximum amount that could theoretically be paid out right now
    ///         without breaching the floor. Actual payouts are further constrained by
    ///         per-contributor caps.
    /// @return headroom USDC headroom above the floor (6 decimals).
    function getHeadroom() external view returns (uint128 headroom) {
        uint128 balance = _readTreasuryBalance();
        if (balance <= floorUsd) return 0;
        unchecked {
            headroom = balance - floorUsd;
        }
    }

    // =========================================================================
    //                         INTERNAL FUNCTIONS
    // =========================================================================

    /// @dev Read current USDC balance of the treasury. Safe cast: USDC total supply
    ///      fits in uint128 (max ~4.3 × 10^20, well within uint128 max ~3.4 × 10^38).
    function _readTreasuryBalance() internal view returns (uint128) {
        return uint128(usdc.balanceOf(treasury));
    }
}

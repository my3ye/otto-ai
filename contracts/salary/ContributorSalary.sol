// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

import {ContributorRegistry} from "./ContributorRegistry.sol";
import {TreasuryGate} from "./TreasuryGate.sol";

/// @title IGnosisSafe
/// @notice Minimal interface for Gnosis Safe module execution.
///         This contract is enabled as a module on the Safe, giving it the ability
///         to execute transactions (specifically USDC transfers) from the Safe
///         without requiring multi-sig approval on each individual payout.
///         The Safe retains ultimate authority: it can disable this module at any time.
interface IGnosisSafe {
    enum Operation { Call, DelegateCall }

    /// @notice Execute a transaction from an enabled module.
    /// @param to        Target contract (USDC token for salary transfers).
    /// @param value     ETH value (always 0 for ERC20 transfers).
    /// @param data      Encoded function call (IERC20.transfer calldata).
    /// @param operation Call type (always Call, never DelegateCall).
    /// @return success  Whether the internal transaction succeeded.
    function execTransactionFromModule(
        address to,
        uint256 value,
        bytes calldata data,
        Operation operation
    ) external returns (bool success);
}

/// @title ContributorSalary
/// @notice Monthly USDC salary disbursement for MY3YE ecosystem contributors.
///         Operates as a Gnosis Safe module — transfers USDC directly from the
///         Movement Treasury (Safe) to contributors. This contract holds no funds.
///
/// @dev Architecture:
///      ┌─────────────────────────────────────────────────────────────────┐
///      │  ContributorSalary.sol (this contract) — Gnosis Safe Module     │
///      │                                                                  │
///      │  Reads from:                                                     │
///      │    ContributorRegistry — who is eligible, their bps + cap       │
///      │    TreasuryGate        — floor enforcement, period tracking      │
///      │                                                                  │
///      │  Executes via:                                                   │
///      │    Safe.execTransactionFromModule(USDC.transfer(contributor))    │
///      │                                                                  │
///      │  Payout formula:                                                 │
///      │    payout = min(eligiblePool × allocationBps / 10000, hardCap)  │
///      │    where eligiblePool = treasuryBalance − floor                  │
///      └─────────────────────────────────────────────────────────────────┘
///
///      Claim flow:
///      1. Contributor calls claim().
///      2. Registry check: is contributor registered and active?
///      3. Period check: has contributor already claimed this period?
///      4. Compute payout: min(allocationBps × eligiblePool / 10000, hardCapUsd).
///      5. TreasuryGate.preClaimCheck(): floor verification + period snapshot.
///      6. Record claim state (CEI: effects before interactions).
///      7. Safe.execTransactionFromModule() — USDC transfer from Safe to contributor.
///      8. TreasuryGate.postClaimCheck(): verify floor survived the transfer.
///
///      Security:
///      - ReentrancyGuard on claim().
///      - Pausable emergency halt.
///      - AccessControl: governance = Safe multi-sig.
///      - 48h timelock on config changes (floor, period duration).
///      - Pre + post claim floor verification via TreasuryGate.
///      - Period snapshot prevents flash-loan manipulation of eligible pool.
///      - CEI pattern: state written before external calls.
///
/// @custom:security-contact admin@otto.lk
contract ContributorSalary is AccessControl, Pausable, ReentrancyGuard {
    // =========================================================================
    //                              ROLES
    // =========================================================================

    /// @notice Governance role — can propose timelocked config changes.
    ///         Initially: the Gnosis Safe itself. Future: DAO governor / OPRLP Council.
    bytes32 public constant GOVERNANCE_ROLE = keccak256("GOVERNANCE_ROLE");

    /// @notice Operator role — can trigger claimFor() on behalf of contributors.
    ///         For keeper bots or relayers. Cannot modify state, only trigger claims.
    ///         Payout always goes to the contributor's registered wallet, not the operator.
    bytes32 public constant OPERATOR_ROLE = keccak256("OPERATOR_ROLE");

    // =========================================================================
    //                              CONSTANTS
    // =========================================================================

    /// @notice Basis point denominator. 10,000 bp = 100%.
    uint256 private constant BPS_DENOMINATOR = 10_000;

    /// @notice Timelock duration for configuration changes.
    ///         Contributors have 48 hours to react to any pending governance change.
    uint32 public constant CONFIG_TIMELOCK = 48 hours;

    // =========================================================================
    //                              IMMUTABLES
    // =========================================================================

    /// @notice The Gnosis Safe (Movement Treasury). All USDC transfers originate here.
    ///         This contract is enabled as a module on this Safe.
    IGnosisSafe public immutable safe;

    /// @notice The USDC token contract.
    IERC20 public immutable usdc;

    /// @notice The ContributorRegistry — source of truth for contributor data.
    ContributorRegistry public immutable registry;

    /// @notice The TreasuryGate — enforces treasury floor and manages period snapshots.
    TreasuryGate public immutable gate;

    /// @notice Deployment timestamp. Period numbering is handled by TreasuryGate,
    ///         but this is recorded for informational / audit purposes.
    uint64 public immutable deployedAt;

    // =========================================================================
    //                              STATE — CLAIM TRACKING
    // =========================================================================

    /// @notice Last period each contributor successfully claimed.
    ///         Uses type(uint32).max as sentinel for "never claimed" — this value
    ///         can never equal a real period number (would require ~136 years of
    ///         daily periods to overflow uint32).
    mapping(address => uint32) public lastClaimedPeriod;

    /// @notice Whether a contributor has ever claimed (disambiguates period 0).
    mapping(address => bool) public hasEverClaimed;

    // =========================================================================
    //                              STATE — ACCOUNTING
    // =========================================================================

    /// @notice Lifetime USDC paid to each contributor (6 decimals).
    mapping(address => uint128) public totalPaidTo;

    /// @notice Lifetime USDC paid across all contributors (6 decimals).
    uint128 public totalDisbursed;

    /// @notice Number of claims processed per period (for analytics dashboards).
    mapping(uint32 => uint16) public claimsInPeriod;

    /// @notice Total USDC disbursed per period (6 decimals, for analytics).
    mapping(uint32 => uint128) public disbursedInPeriod;

    // =========================================================================
    //                              STATE — TIMELOCK
    // =========================================================================

    /// @notice Hash of the pending configuration change. bytes32(0) = no pending change.
    bytes32 public pendingConfigHash;

    /// @notice Timestamp when the pending change becomes executable.
    uint64 public configUnlocksAt;

    // =========================================================================
    //                              EVENTS
    // =========================================================================

    /// @notice Emitted on every successful salary claim.
    /// @param contributor     Wallet that received USDC.
    /// @param period          Claim period number.
    /// @param amount          USDC transferred (6 decimals).
    /// @param eligiblePool    Eligible pool at time of calculation (6 decimals).
    /// @param cappedByHardCap True if the hard cap was the binding constraint.
    /// @param treasuryAfter   Treasury USDC balance after the transfer.
    event SalaryClaimed(
        address indexed contributor,
        uint32 indexed period,
        uint128 amount,
        uint128 eligiblePool,
        bool cappedByHardCap,
        uint128 treasuryAfter
    );

    /// @notice Emitted when a timelock config change is proposed.
    event ConfigProposed(bytes32 indexed configHash, uint64 unlocksAt, address proposedBy);

    /// @notice Emitted when a timelocked config change is executed.
    event ConfigExecuted(bytes32 indexed configHash, address executedBy);

    /// @notice Emitted when a pending config change is cancelled.
    event ConfigCancelled(bytes32 indexed configHash, address cancelledBy);

    // =========================================================================
    //                              ERRORS
    // =========================================================================

    error ZeroAddress();
    error NotActiveContributor(address wallet);
    error AlreadyClaimedThisPeriod(address wallet, uint32 period);
    error ZeroPayout();
    error SafeTransferFailed(address contributor, uint128 amount);
    error NoConfigPending();
    error ConfigAlreadyPending();
    error ConfigNotUnlockedYet(uint64 unlocksAt, uint64 currentTime);
    error ConfigHashMismatch(bytes32 expected, bytes32 provided);

    // =========================================================================
    //                              CONSTRUCTOR
    // =========================================================================

    /// @notice Deploy the salary contract.
    /// @dev    After deployment, this contract must be enabled as a module on the Safe.
    ///         The Safe's owners call `enableModule(address(this))` via multi-sig tx.
    ///         Additionally, grant SALARY_CONTRACT_ROLE on TreasuryGate to this contract
    ///         so it can call preClaimCheck() and postClaimCheck().
    ///
    /// @param safeAddress      Gnosis Safe (Movement Treasury) address.
    /// @param usdcAddress      USDC token address.
    /// @param registryAddress  Deployed ContributorRegistry address.
    /// @param gateAddress      Deployed TreasuryGate address.
    /// @param admin            Receives DEFAULT_ADMIN_ROLE + GOVERNANCE_ROLE.
    ///                         Should be the Safe multi-sig in production.
    constructor(
        address safeAddress,
        address usdcAddress,
        address registryAddress,
        address gateAddress,
        address admin
    ) {
        if (safeAddress == address(0)) revert ZeroAddress();
        if (usdcAddress == address(0)) revert ZeroAddress();
        if (registryAddress == address(0)) revert ZeroAddress();
        if (gateAddress == address(0)) revert ZeroAddress();
        if (admin == address(0)) revert ZeroAddress();

        safe = IGnosisSafe(safeAddress);
        usdc = IERC20(usdcAddress);
        registry = ContributorRegistry(registryAddress);
        gate = TreasuryGate(gateAddress);
        deployedAt = uint64(block.timestamp);

        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(GOVERNANCE_ROLE, admin);
    }

    // =========================================================================
    //                         CLAIM FUNCTIONS
    // =========================================================================

    /// @notice Claim the caller's salary for the current period.
    ///         Transfers USDC from the Movement Treasury (Safe) to the caller.
    ///         Reverts if: not active, already claimed, treasury below floor,
    ///         payout would breach floor, or Safe module execution fails.
    /// @return amount USDC transferred to the caller (6 decimals).
    function claim() external nonReentrant whenNotPaused returns (uint128 amount) {
        return _processClaim(msg.sender);
    }

    /// @notice Claim salary on behalf of a contributor (keeper/relayer pattern).
    ///         USDC goes to the contributor's registered wallet, NOT to msg.sender.
    /// @param contributor The contributor whose salary to claim.
    /// @return amount USDC transferred to the contributor (6 decimals).
    function claimFor(address contributor)
        external
        nonReentrant
        whenNotPaused
        onlyRole(OPERATOR_ROLE)
        returns (uint128 amount)
    {
        return _processClaim(contributor);
    }

    // =========================================================================
    //                         TIMELOCK GOVERNANCE
    // =========================================================================

    /// @notice Propose a new treasury floor. Starts 48h timelock.
    ///         After the timelock, call executeFloorChange() to apply.
    ///         Only one config change can be pending at a time.
    /// @param newFloor New floor in USDC (6 decimals). Must be >= MIN_FLOOR.
    function proposeFloorChange(uint128 newFloor) external onlyRole(GOVERNANCE_ROLE) {
        if (pendingConfigHash != bytes32(0)) revert ConfigAlreadyPending();

        bytes32 configHash = keccak256(abi.encode("setFloor", newFloor, block.timestamp));
        pendingConfigHash = configHash;
        configUnlocksAt = uint64(block.timestamp) + CONFIG_TIMELOCK;

        emit ConfigProposed(configHash, configUnlocksAt, msg.sender);
    }

    /// @notice Execute a proposed floor change after the 48h timelock.
    /// @param newFloor    Must match the proposed value.
    /// @param proposedAt  block.timestamp from the proposal tx (for hash reconstruction).
    function executeFloorChange(uint128 newFloor, uint256 proposedAt)
        external
        onlyRole(GOVERNANCE_ROLE)
    {
        bytes32 configHash = keccak256(abi.encode("setFloor", newFloor, proposedAt));
        _validateTimelock(configHash);

        // Execute: update TreasuryGate's floor.
        // Requires this contract to have GATE_ADMIN_ROLE on TreasuryGate.
        gate.setFloor(newFloor);

        _clearTimelock();
        emit ConfigExecuted(configHash, msg.sender);
    }

    /// @notice Propose a new claim period duration. Starts 48h timelock.
    /// @param newDuration New period duration in seconds (7 days min, 365 days max).
    function proposePeriodChange(uint32 newDuration) external onlyRole(GOVERNANCE_ROLE) {
        if (pendingConfigHash != bytes32(0)) revert ConfigAlreadyPending();

        bytes32 configHash = keccak256(abi.encode("setPeriodDuration", newDuration, block.timestamp));
        pendingConfigHash = configHash;
        configUnlocksAt = uint64(block.timestamp) + CONFIG_TIMELOCK;

        emit ConfigProposed(configHash, configUnlocksAt, msg.sender);
    }

    /// @notice Execute a proposed period duration change after timelock.
    /// @param newDuration Must match the proposed value.
    /// @param proposedAt  block.timestamp from the proposal tx.
    function executePeriodChange(uint32 newDuration, uint256 proposedAt)
        external
        onlyRole(GOVERNANCE_ROLE)
    {
        bytes32 configHash = keccak256(abi.encode("setPeriodDuration", newDuration, proposedAt));
        _validateTimelock(configHash);

        gate.setPeriodDuration(newDuration);

        _clearTimelock();
        emit ConfigExecuted(configHash, msg.sender);
    }

    /// @notice Cancel a pending config change before it executes.
    function cancelConfigChange() external onlyRole(GOVERNANCE_ROLE) {
        if (pendingConfigHash == bytes32(0)) revert NoConfigPending();
        bytes32 oldHash = pendingConfigHash;
        _clearTimelock();
        emit ConfigCancelled(oldHash, msg.sender);
    }

    // =========================================================================
    //                         EMERGENCY CONTROLS
    // =========================================================================

    /// @notice Pause all claims. No USDC can leave the treasury via this module.
    function pause() external onlyRole(GOVERNANCE_ROLE) {
        _pause();
    }

    /// @notice Unpause claims.
    function unpause() external onlyRole(GOVERNANCE_ROLE) {
        _unpause();
    }

    // =========================================================================
    //                         VIEW FUNCTIONS
    // =========================================================================

    /// @notice Preview what a contributor would receive if they claimed now.
    ///         Pure read — no state changes, never reverts.
    /// @param contributor Address to preview.
    /// @return amount     Projected USDC payout (6 decimals). 0 if blocked.
    /// @return canClaim_  True if claim() would succeed right now.
    /// @return reason     Empty if canClaim_, else a reason code.
    function previewClaim(address contributor)
        external
        view
        returns (uint128 amount, bool canClaim_, string memory reason)
    {
        // Check registration
        if (!registry.isRegistered(contributor)) {
            return (0, false, "NOT_REGISTERED");
        }

        // Check active
        if (!registry.isActive(contributor)) {
            return (0, false, "INACTIVE");
        }

        // Check already claimed
        uint32 period = gate.getCurrentPeriod();
        if (hasEverClaimed[contributor] && lastClaimedPeriod[contributor] == period) {
            return (0, false, "ALREADY_CLAIMED");
        }

        // Check treasury health
        if (!gate.isTreasuryHealthy()) {
            return (0, false, "BELOW_FLOOR");
        }

        // Calculate payout
        ContributorRegistry.Contributor memory c = registry.getContributor(contributor);
        uint128 eligible = gate.getEligiblePool();
        (uint128 payout, bool cappedByHardCap) = _computePayout(c.allocationBps, c.hardCapUsd, eligible);

        if (payout == 0) {
            return (0, false, "ZERO_ELIGIBLE_POOL");
        }

        // Check post-payout floor
        uint128 treasuryBal = gate.getTreasuryBalance();
        if (treasuryBal < payout + gate.floorUsd()) {
            return (payout, false, "POST_PAYOUT_FLOOR");
        }

        string memory info = cappedByHardCap ? "CAPPED_AT_HARD_CAP" : "";
        return (payout, true, info);
    }

    /// @notice Current period number (delegates to TreasuryGate).
    function currentPeriod() external view returns (uint32) {
        return gate.getCurrentPeriod();
    }

    /// @notice Whether a contributor has claimed in the current period.
    function hasClaimedCurrentPeriod(address contributor) external view returns (bool) {
        if (!hasEverClaimed[contributor]) return false;
        return lastClaimedPeriod[contributor] == gate.getCurrentPeriod();
    }

    /// @notice Full system summary for dashboards.
    /// @return treasuryBalance   USDC in the Safe right now.
    /// @return eligiblePool      Amount above the floor (distributable).
    /// @return floor             Current floor.
    /// @return period            Current period number.
    /// @return lifetimePaid      Total USDC disbursed all-time.
    /// @return activeBps         Total bps allocated to active contributors.
    /// @return isPaused          Whether claims are paused.
    function getSummary()
        external
        view
        returns (
            uint128 treasuryBalance,
            uint128 eligiblePool,
            uint128 floor,
            uint32 period,
            uint128 lifetimePaid,
            uint16 activeBps,
            bool isPaused
        )
    {
        treasuryBalance = gate.getTreasuryBalance();
        eligiblePool = gate.getEligiblePool();
        floor = gate.floorUsd();
        period = gate.getCurrentPeriod();
        lifetimePaid = totalDisbursed;
        activeBps = registry.totalActiveBps();
        isPaused = paused();
    }

    /// @notice Simulate payouts for all active contributors at current state.
    /// @dev    WARNING: O(n) — use off-chain only.
    /// @return wallets     Active contributor addresses.
    /// @return amounts     Corresponding USDC payouts (6 decimals).
    /// @return totalPayout Sum of all payouts.
    function simulateAllPayouts()
        external
        view
        returns (address[] memory wallets, uint128[] memory amounts, uint128 totalPayout)
    {
        uint256 count = registry.contributorCount();
        wallets = new address[](count);
        amounts = new uint128[](count);
        uint256 activeIdx;

        for (uint256 i; i < count; ++i) {
            address w = registry.contributorAt(i);
            if (!registry.isActive(w)) continue;

            ContributorRegistry.Contributor memory c = registry.getContributor(w);
            uint128 eligible = gate.getEligiblePool();
            (uint128 payout, ) = _computePayout(c.allocationBps, c.hardCapUsd, eligible);

            wallets[activeIdx] = w;
            amounts[activeIdx] = payout;
            totalPayout += payout;
            ++activeIdx;
        }

        // Trim arrays to actual size
        assembly {
            mstore(wallets, activeIdx)
            mstore(amounts, activeIdx)
        }
    }

    // =========================================================================
    //                         INTERNAL FUNCTIONS
    // =========================================================================

    /// @dev Core claim logic. All external claim paths converge here.
    ///      Follows Checks-Effects-Interactions (CEI) pattern strictly.
    function _processClaim(address contributor) internal returns (uint128 payout) {
        // ── CHECKS ──────────────────────────────────────────────────────────

        // 1. Contributor must be registered and active in the registry.
        if (!registry.isActive(contributor)) {
            revert NotActiveContributor(contributor);
        }

        // 2. Must not have claimed this period already.
        uint32 period = gate.getCurrentPeriod();
        if (hasEverClaimed[contributor] && lastClaimedPeriod[contributor] == period) {
            revert AlreadyClaimedThisPeriod(contributor, period);
        }

        // 3. Load contributor config from registry.
        ContributorRegistry.Contributor memory c = registry.getContributor(contributor);

        // 4. Calculate payout from eligible pool.
        //    Gate's eligible pool uses period snapshot if available, live balance otherwise.
        uint128 eligible = gate.getEligiblePool();
        bool cappedByHardCap;
        (payout, cappedByHardCap) = _computePayout(c.allocationBps, c.hardCapUsd, eligible);

        if (payout == 0) {
            revert ZeroPayout();
        }

        // 5. TreasuryGate pre-claim check.
        //    Verifies floor, takes period snapshot if first claim of period.
        //    Reverts if treasury below floor or payout would breach floor.
        gate.preClaimCheck(contributor, payout);

        // ── EFFECTS ─────────────────────────────────────────────────────────

        // 6. Record claim BEFORE the transfer (CEI pattern).
        lastClaimedPeriod[contributor] = period;
        hasEverClaimed[contributor] = true;

        // Update accounting. Overflow is economically impossible:
        // USDC total supply ~50B × 10^6 = 5 × 10^16, well within uint128 max.
        unchecked {
            totalPaidTo[contributor] += payout;
            totalDisbursed += payout;
            claimsInPeriod[period] += 1;
            disbursedInPeriod[period] += payout;
        }

        // ── INTERACTIONS ────────────────────────────────────────────────────

        // 7. Execute USDC transfer via Gnosis Safe module.
        //    The Safe sends USDC directly to the contributor's registered wallet.
        //    We encode: IERC20(usdc).transfer(contributor_wallet, payout)
        //    The Safe executes this as if it called transfer() itself.
        bytes memory transferCalldata = abi.encodeCall(
            IERC20.transfer,
            (c.wallet, uint256(payout))
        );

        bool success = safe.execTransactionFromModule(
            address(usdc),       // to: USDC token contract
            0,                   // value: 0 ETH
            transferCalldata,    // data: IERC20.transfer(wallet, amount)
            IGnosisSafe.Operation.Call
        );

        if (!success) {
            revert SafeTransferFailed(contributor, payout);
        }

        // 8. Post-transfer floor check (belt and suspenders).
        //    Reads actual on-chain USDC balance of the treasury AFTER the transfer.
        //    If the floor was breached (e.g., concurrent transfer in same block),
        //    the entire transaction reverts — including the USDC transfer above.
        gate.postClaimCheck();

        // 9. Emit event with full transparency data.
        emit SalaryClaimed(
            contributor,
            period,
            payout,
            eligible,
            cappedByHardCap,
            gate.getTreasuryBalance()
        );
    }

    /// @dev Calculate payout: min(eligiblePool × allocationBps / 10000, hardCapUsd).
    ///      Pure math with safe intermediate width (uint256).
    ///
    ///      Overflow analysis:
    ///      - eligible (uint128) × allocationBps (uint16) = max ~3.4e38 × 500 = ~1.7e41
    ///      - uint256 max = ~1.16e77 — no overflow possible.
    ///      - Result after division by 10000: max ~1.7e37, fits in uint128.
    ///
    /// @param allocationBps  Contributor's allocation in basis points.
    /// @param hardCapUsd     Contributor's hard cap in USDC (6 decimals).
    /// @param eligible       Eligible pool in USDC (6 decimals).
    /// @return payout        The payout amount (already capped).
    /// @return cappedByHardCap Whether the hard cap was the binding constraint.
    function _computePayout(
        uint16 allocationBps,
        uint128 hardCapUsd,
        uint128 eligible
    ) internal pure returns (uint128 payout, bool cappedByHardCap) {
        if (eligible == 0 || allocationBps == 0) {
            return (0, false);
        }

        uint256 bpsResult = (uint256(eligible) * allocationBps) / BPS_DENOMINATOR;

        if (bpsResult >= hardCapUsd) {
            return (hardCapUsd, true);
        }

        // Safe downcast: bpsResult < hardCapUsd (uint128).
        return (uint128(bpsResult), false);
    }

    /// @dev Validate that a timelock has expired and the hash matches.
    function _validateTimelock(bytes32 configHash) internal view {
        if (pendingConfigHash == bytes32(0)) revert NoConfigPending();
        if (pendingConfigHash != configHash) {
            revert ConfigHashMismatch(pendingConfigHash, configHash);
        }
        if (block.timestamp < configUnlocksAt) {
            revert ConfigNotUnlockedYet(configUnlocksAt, uint64(block.timestamp));
        }
    }

    /// @dev Clear the pending timelock state.
    function _clearTimelock() internal {
        pendingConfigHash = bytes32(0);
        configUnlocksAt = 0;
    }
}

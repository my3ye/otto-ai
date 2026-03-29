// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AccessControl} from "@openzeppelin/contracts/access/AccessControl.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

/// @title ContributorRegistry
/// @notice Registry of compensated contributors for the MY3YE ecosystem salary system.
///         Every contributor — including the founder — is registered here with identical
///         structure: a basis-point allocation and a hard monthly cap. No special treatment.
///
/// @dev Design principles:
///      - All contributors share the same data structure; the cap is the equalizer.
///      - The GLOBAL_SALARY_CAP is immutable — it was 9000 USDC at deploy time and stays
///        that way forever. No governance vote can raise it. Auditors, read that line.
///      - Deactivation is soft (flag flip), not deletion. History is preserved on-chain.
///      - Role enum is informational/display only — it has no effect on compensation math.
///        Founder gets the same cap as everyone who follows.
///
/// @custom:security-contact admin@otto.lk
contract ContributorRegistry is AccessControl, Pausable {
    // =========================================================================
    //                              ROLES
    // =========================================================================

    /// @notice Can add/update/deactivate contributors and pause the registry.
    bytes32 public constant REGISTRY_ADMIN_ROLE = keccak256("REGISTRY_ADMIN_ROLE");

    /// @notice Granted to ContributorSalary.sol so it can record claim periods.
    bytes32 public constant SALARY_CONTRACT_ROLE = keccak256("SALARY_CONTRACT_ROLE");

    // =========================================================================
    //                              CONSTANTS
    // =========================================================================

    /// @notice The immutable maximum monthly salary cap — 9,000 USDC (6 decimals).
    ///         No contributor can ever be configured above this value. Immutable.
    uint128 public constant GLOBAL_SALARY_CAP = 9_000e6; // 9000 USDC, 6 decimals

    /// @notice Maximum basis-point allocation any single contributor can hold.
    ///         500 = 5% of eligible pool. Prevents any single address from draining
    ///         the treasury even if the floor is far above the payout threshold.
    uint16 public constant MAX_ALLOCATION_BPS = 500; // 5%

    /// @notice Maximum total basis points across all active contributors.
    ///         2000 = 20% of eligible pool. Ensures floor protection is never overwhelmed
    ///         by cumulative claims even with many contributors.
    uint16 public constant MAX_TOTAL_ALLOCATION_BPS = 2000; // 20%

    // =========================================================================
    //                              TYPES
    // =========================================================================

    /// @notice Informational role labels. No effect on payout math.
    ///         FOUNDER: Mev and any future founding-era contributors (pre-treasury)
    ///         CORE: Full-time contributors post-treasury-launch
    ///         CONTRIBUTOR: Part-time or project-scoped contributors
    ///         ADVISOR: Strategic advisors with reduced allocation
    enum ContributorRole { FOUNDER, CORE, CONTRIBUTOR, ADVISOR }

    /// @notice Full contributor record. One slot layout: 32 bytes each for
    ///         (wallet + role + active), (hardCapUsd + allocationBps), timestamps.
    /// @dev    Struct layout optimized for storage packing:
    ///         slot 0: wallet (20) + role (1) + active (1) = 22 bytes, 10 wasted
    ///         slot 1: hardCapUsd (16) + allocationBps (2) = 18 bytes, 14 wasted
    ///         slot 2: addedAt (8) + deactivatedAt (8) = 16 bytes, 16 wasted
    ///         Not perfectly packed due to wallet size, but structs with address fields
    ///         cannot pack tighter without sacrificing readability.
    struct Contributor {
        address wallet;            // Payment destination (immutable after registration)
        ContributorRole role;      // Informational only
        bool active;               // Can be flipped; false blocks claims
        uint128 hardCapUsd;        // Max USDC per claim period (6 decimals). <= GLOBAL_SALARY_CAP
        uint16 allocationBps;      // Basis points of eligible pool. <= MAX_ALLOCATION_BPS
        uint64 addedAt;            // Block timestamp of registration
        uint64 deactivatedAt;      // Block timestamp of most recent deactivation (0 if never)
    }

    // =========================================================================
    //                              STATE
    // =========================================================================

    /// @notice Contributors indexed by wallet address.
    mapping(address => Contributor) private _contributors;

    /// @notice Ordered list of all registered wallets (active + inactive).
    ///         Immutable entries — deactivation sets the `active` flag, not array position.
    ///         Kept bounded: the treasury cap makes infinite contributors economically
    ///         impossible (total allocation is capped at MAX_TOTAL_ALLOCATION_BPS).
    address[] private _contributorList;

    /// @notice Whether an address has ever been registered (prevents duplicate adds).
    mapping(address => bool) private _registered;

    /// @notice Running sum of active contributors' allocationBps.
    ///         Maintained incrementally to avoid O(n) reads in ContributorSalary.
    uint16 public totalActiveBps;

    // =========================================================================
    //                              EVENTS
    // =========================================================================

    /// @notice Emitted when a new contributor is added to the registry.
    event ContributorAdded(
        address indexed wallet,
        ContributorRole indexed role,
        uint16 allocationBps,
        uint128 hardCapUsd,
        uint64 addedAt
    );

    /// @notice Emitted when a contributor is deactivated (soft removal).
    event ContributorDeactivated(address indexed wallet, address indexed deactivatedBy, uint64 at);

    /// @notice Emitted when a previously deactivated contributor is reactivated.
    event ContributorReactivated(address indexed wallet, address indexed reactivatedBy, uint64 at);

    /// @notice Emitted when a contributor's allocation or cap is updated.
    event ContributorUpdated(
        address indexed wallet,
        uint16 oldBps,
        uint16 newBps,
        uint128 oldCap,
        uint128 newCap
    );

    // =========================================================================
    //                              ERRORS
    // =========================================================================

    error AlreadyRegistered(address wallet);
    error NotRegistered(address wallet);
    error AlreadyActive(address wallet);
    error AlreadyInactive(address wallet);
    error ZeroAddress();
    error AllocationExceedsSingleMax(uint16 requested, uint16 maximum);
    error AllocationExceedsTotalMax(uint16 currentTotal, uint16 requested, uint16 totalMaximum);
    error CapExceedsGlobalMax(uint128 requested, uint128 globalMax);
    error ZeroAllocation();

    // =========================================================================
    //                              CONSTRUCTOR
    // =========================================================================

    /// @param admin Address that receives DEFAULT_ADMIN_ROLE and REGISTRY_ADMIN_ROLE.
    ///              Should be a Gnosis Safe multi-sig in production.
    constructor(address admin) {
        if (admin == address(0)) revert ZeroAddress();
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(REGISTRY_ADMIN_ROLE, admin);
    }

    // =========================================================================
    //                         REGISTRY ADMIN FUNCTIONS
    // =========================================================================

    /// @notice Register a new contributor.
    /// @dev    The cap is enforced at the global ceiling — no contributor can ever be
    ///         configured above GLOBAL_SALARY_CAP. This is verified at add time and
    ///         again on every update. The wallet address is immutable after registration.
    ///
    /// @param wallet         Payment address. Cannot be changed post-registration.
    /// @param role           Informational role label.
    /// @param allocationBps  Percentage of eligible pool in basis points (1 bp = 0.01%).
    ///                       Max: MAX_ALLOCATION_BPS (500 = 5%).
    /// @param hardCapUsd     Maximum USDC payout per claim period (6 decimals).
    ///                       Max: GLOBAL_SALARY_CAP (9000e6).
    function addContributor(
        address wallet,
        ContributorRole role,
        uint16 allocationBps,
        uint128 hardCapUsd
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused {
        if (wallet == address(0)) revert ZeroAddress();
        if (_registered[wallet]) revert AlreadyRegistered(wallet);
        if (allocationBps == 0) revert ZeroAllocation();
        if (allocationBps > MAX_ALLOCATION_BPS) {
            revert AllocationExceedsSingleMax(allocationBps, MAX_ALLOCATION_BPS);
        }
        if (hardCapUsd > GLOBAL_SALARY_CAP) {
            revert CapExceedsGlobalMax(hardCapUsd, GLOBAL_SALARY_CAP);
        }

        // Check aggregate ceiling — prevents governance from adding too many contributors
        // and overwhelming the treasury floor gate.
        uint16 newTotal = totalActiveBps + allocationBps;
        if (newTotal > MAX_TOTAL_ALLOCATION_BPS) {
            revert AllocationExceedsTotalMax(totalActiveBps, allocationBps, MAX_TOTAL_ALLOCATION_BPS);
        }

        uint64 now64 = uint64(block.timestamp);

        _contributors[wallet] = Contributor({
            wallet:        wallet,
            role:          role,
            active:        true,
            hardCapUsd:    hardCapUsd,
            allocationBps: allocationBps,
            addedAt:       now64,
            deactivatedAt: 0
        });

        _contributorList.push(wallet);
        _registered[wallet] = true;
        totalActiveBps = newTotal;

        emit ContributorAdded(wallet, role, allocationBps, hardCapUsd, now64);
    }

    /// @notice Deactivate a contributor. Blocks future claims, preserves history.
    /// @dev    This is a soft remove. The record stays on-chain. Their allocationBps
    ///         is removed from the running total so it doesn't crowd out future contributors.
    /// @param wallet The contributor to deactivate.
    function deactivateContributor(address wallet) external onlyRole(REGISTRY_ADMIN_ROLE) {
        if (!_registered[wallet]) revert NotRegistered(wallet);
        Contributor storage c = _contributors[wallet];
        if (!c.active) revert AlreadyInactive(wallet);

        c.active = false;
        c.deactivatedAt = uint64(block.timestamp);

        // Remove their allocation from the running total
        totalActiveBps -= c.allocationBps;

        emit ContributorDeactivated(wallet, msg.sender, uint64(block.timestamp));
    }

    /// @notice Reactivate a previously deactivated contributor.
    /// @param wallet The contributor to reactivate.
    function reactivateContributor(address wallet) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused {
        if (!_registered[wallet]) revert NotRegistered(wallet);
        Contributor storage c = _contributors[wallet];
        if (c.active) revert AlreadyActive(wallet);

        // Re-check total allocation ceiling before reactivating
        uint16 newTotal = totalActiveBps + c.allocationBps;
        if (newTotal > MAX_TOTAL_ALLOCATION_BPS) {
            revert AllocationExceedsTotalMax(totalActiveBps, c.allocationBps, MAX_TOTAL_ALLOCATION_BPS);
        }

        c.active = true;
        c.deactivatedAt = 0;
        totalActiveBps = newTotal;

        emit ContributorReactivated(wallet, msg.sender, uint64(block.timestamp));
    }

    /// @notice Update a contributor's allocation and cap.
    /// @dev    Cap can only be reduced below GLOBAL_SALARY_CAP, never above it.
    ///         Allocation changes are checked against both single and total maximums.
    ///         Contributor must be active to update — deactivate/reactivate to change
    ///         inactive contributor terms before bringing them back.
    ///
    /// @param wallet      The contributor to update.
    /// @param newBps      New basis-point allocation.
    /// @param newCapUsd   New hard cap in USDC (6 decimals).
    function updateContributor(
        address wallet,
        uint16 newBps,
        uint128 newCapUsd
    ) external onlyRole(REGISTRY_ADMIN_ROLE) whenNotPaused {
        if (!_registered[wallet]) revert NotRegistered(wallet);
        if (newBps == 0) revert ZeroAllocation();
        if (newBps > MAX_ALLOCATION_BPS) {
            revert AllocationExceedsSingleMax(newBps, MAX_ALLOCATION_BPS);
        }
        if (newCapUsd > GLOBAL_SALARY_CAP) {
            revert CapExceedsGlobalMax(newCapUsd, GLOBAL_SALARY_CAP);
        }

        Contributor storage c = _contributors[wallet];
        if (!c.active) revert AlreadyInactive(wallet);

        uint16 oldBps = c.allocationBps;
        uint128 oldCap = c.hardCapUsd;

        // Compute new total: subtract old contribution, add new
        uint16 newTotal;
        unchecked {
            // Safe: totalActiveBps >= oldBps is enforced by invariants on add/deactivate
            newTotal = totalActiveBps - oldBps + newBps;
        }
        if (newTotal > MAX_TOTAL_ALLOCATION_BPS) {
            revert AllocationExceedsTotalMax(totalActiveBps - oldBps, newBps, MAX_TOTAL_ALLOCATION_BPS);
        }

        c.allocationBps = newBps;
        c.hardCapUsd = newCapUsd;
        totalActiveBps = newTotal;

        emit ContributorUpdated(wallet, oldBps, newBps, oldCap, newCapUsd);
    }

    // =========================================================================
    //                         EMERGENCY CONTROLS
    // =========================================================================

    /// @notice Pause the registry. Blocks adds, updates, and reactivations.
    ///         Existing deactivations still work during pause (safety escape hatch).
    function pause() external onlyRole(REGISTRY_ADMIN_ROLE) {
        _pause();
    }

    /// @notice Unpause the registry.
    function unpause() external onlyRole(REGISTRY_ADMIN_ROLE) {
        _unpause();
    }

    // =========================================================================
    //                         VIEW FUNCTIONS
    // =========================================================================

    /// @notice Retrieve the full contributor record for a wallet.
    /// @param wallet The contributor's wallet address.
    /// @return The Contributor struct.
    function getContributor(address wallet) external view returns (Contributor memory) {
        if (!_registered[wallet]) revert NotRegistered(wallet);
        return _contributors[wallet];
    }

    /// @notice Check if a wallet is a registered, active contributor.
    /// @param wallet The wallet to check.
    /// @return True if registered and active.
    function isActive(address wallet) external view returns (bool) {
        return _registered[wallet] && _contributors[wallet].active;
    }

    /// @notice Get the total number of ever-registered contributors (active + inactive).
    function contributorCount() external view returns (uint256) {
        return _contributorList.length;
    }

    /// @notice Get a contributor address by index.
    /// @dev    Used by ContributorSalary for simulation reads. Not for production iteration
    ///         at scale — caller bears gas cost.
    /// @param index Position in the contributor list.
    function contributorAt(uint256 index) external view returns (address) {
        return _contributorList[index];
    }

    /// @notice Enumerate all registered contributor wallets.
    /// @dev    WARNING: O(n) return. Do not call on-chain from hot paths.
    ///         Use contributorCount() + contributorAt() for paginated access.
    function getAllContributors() external view returns (address[] memory) {
        return _contributorList;
    }

    /// @notice Check if an address has ever been registered.
    /// @param wallet The wallet to check.
    function isRegistered(address wallet) external view returns (bool) {
        return _registered[wallet];
    }
}

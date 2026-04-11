// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ZkPresence.sol";

/// @title Mock SP1 Verifier — always passes
/// @dev Implements ISP1Verifier for testing without real proofs.
contract MockSP1Verifier is ISP1Verifier {
    function verifyProof(bytes32, bytes calldata, bytes calldata) external pure {}
}

/// @title ZkPresence Tests
contract ZkPresenceTest is Test {
    ZkPresence public zkp;
    MockSP1Verifier public mockVerifier;
    bytes32 constant PROGRAM_VKEY = bytes32(uint256(0xdead));

    function setUp() public {
        mockVerifier = new MockSP1Verifier();
        zkp = new ZkPresence(address(mockVerifier), PROGRAM_VKEY);
    }

    // ── Event creation ──────────────────────────────────────────────────

    function test_createEvent() public {
        bytes32 locationHash = keccak256("9q8yyk");
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 start = uint64(block.timestamp);
        uint64 end = uint64(block.timestamp + 3600);

        uint64 eventId = zkp.createEvent(locationHash, start, end, orgPubkeyHash);
        assertEq(eventId, 0);
        assertEq(zkp.eventCount(), 1);

        (address organizer,,,,,bool active) = zkp.events(eventId);
        assertEq(organizer, address(this));
        assertTrue(active);
    }

    function test_deactivateEvent() public {
        uint64 eventId = zkp.createEvent(bytes32(0), 100, 200, bytes32(uint256(1)));
        zkp.deactivateEvent(eventId);

        (,,,,,bool active) = zkp.events(eventId);
        assertFalse(active);
    }

    function test_deactivateEvent_onlyOrganizer() public {
        uint64 eventId = zkp.createEvent(bytes32(0), 100, 200, bytes32(uint256(1)));

        vm.prank(address(0xBEEF));
        vm.expectRevert("not organizer");
        zkp.deactivateEvent(eventId);
    }

    function test_createEvent_invalidTimeWindow() public {
        vm.expectRevert("invalid time window");
        zkp.createEvent(bytes32(0), 200, 100, bytes32(uint256(1)));
    }

    // ── ABI encoding round-trip ─────────────────────────────────────────

    /// @notice Validates that the Solidity abi.decode matches the tuple format
    ///         the Rust circuit now produces via alloy-sol-types ABI encoding.
    function test_publicValuesAbiDecode() public pure {
        uint64 eventId = 42;
        bytes32 nullifier = bytes32(uint256(0xAABB));
        bytes32 identityCommitment = bytes32(uint256(0xCCDD));
        uint8 attestationMode = 1;
        uint64 timestamp = 1700000000;
        bytes32 orgPubkeyHash = bytes32(uint256(0xEEFF));

        // Encode the same way Solidity would — this is what the Rust circuit
        // now produces via alloy_sol_types::sol! { tuple(uint64, bytes32, ...) }
        bytes memory encoded = abi.encode(
            eventId, nullifier, identityCommitment,
            attestationMode, timestamp, orgPubkeyHash
        );

        // Decode — this is what verifyAttendance() does
        (
            uint64 dEventId,
            bytes32 dNullifier,
            bytes32 dIdentityCommitment,
            uint8 dMode,
            uint64 dTimestamp,
            bytes32 dOrgPubkeyHash
        ) = abi.decode(encoded, (uint64, bytes32, bytes32, uint8, uint64, bytes32));

        assertEq(dEventId, eventId);
        assertEq(dNullifier, nullifier);
        assertEq(dIdentityCommitment, identityCommitment);
        assertEq(dMode, attestationMode);
        assertEq(dTimestamp, timestamp);
        assertEq(dOrgPubkeyHash, orgPubkeyHash);
    }

    // ── Attendance verification (mock proof) ────────────────────────────

    function test_verifyAttendance_mockProof() public {
        // Setup event
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 start = 1000;
        uint64 end = 2000;
        uint64 eventId = zkp.createEvent(bytes32(0), start, end, orgPubkeyHash);

        // Build ABI-encoded public values
        bytes32 nullifier = bytes32(uint256(0xAAAA));
        bytes32 identityCommitment = bytes32(uint256(0xBBBB));
        uint8 mode = 0;
        uint64 timestamp = 1500;
        bytes memory publicValues = abi.encode(
            eventId, nullifier, identityCommitment,
            mode, timestamp, orgPubkeyHash
        );

        // Submit with mock proof (MockSP1Verifier always passes)
        zkp.verifyAttendance(hex"", publicValues);

        // Verify state updates
        assertTrue(zkp.hasAttended(eventId, identityCommitment));
        assertTrue(zkp.isNullifierUsed(nullifier));
    }

    function test_verifyAttendance_doubleClaimReverts() public {
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 eventId = zkp.createEvent(bytes32(0), 1000, 2000, orgPubkeyHash);

        bytes32 nullifier = bytes32(uint256(0xAAAA));
        bytes memory publicValues = abi.encode(
            eventId, nullifier, bytes32(uint256(0xBBBB)),
            uint8(0), uint64(1500), orgPubkeyHash
        );

        zkp.verifyAttendance(hex"", publicValues);

        // Same nullifier should revert
        vm.expectRevert("already claimed");
        zkp.verifyAttendance(hex"", publicValues);
    }

    function test_verifyAttendance_inactiveEventReverts() public {
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 eventId = zkp.createEvent(bytes32(0), 1000, 2000, orgPubkeyHash);
        zkp.deactivateEvent(eventId);

        bytes memory publicValues = abi.encode(
            eventId, bytes32(uint256(0xAAAA)), bytes32(uint256(0xBBBB)),
            uint8(0), uint64(1500), orgPubkeyHash
        );

        vm.expectRevert("event not active");
        zkp.verifyAttendance(hex"", publicValues);
    }

    function test_verifyAttendance_outsideTimeWindow() public {
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 eventId = zkp.createEvent(bytes32(0), 1000, 2000, orgPubkeyHash);

        bytes memory publicValues = abi.encode(
            eventId, bytes32(uint256(0xAAAA)), bytes32(uint256(0xBBBB)),
            uint8(0), uint64(999), orgPubkeyHash  // timestamp before start
        );

        vm.expectRevert("outside event window");
        zkp.verifyAttendance(hex"", publicValues);
    }

    function test_verifyAttendance_organizerMismatch() public {
        bytes32 orgPubkeyHash = bytes32(uint256(0x1234));
        uint64 eventId = zkp.createEvent(bytes32(0), 1000, 2000, orgPubkeyHash);

        bytes memory publicValues = abi.encode(
            eventId, bytes32(uint256(0xAAAA)), bytes32(uint256(0xBBBB)),
            uint8(0), uint64(1500), bytes32(uint256(0x9999))  // wrong org
        );

        vm.expectRevert("organizer mismatch");
        zkp.verifyAttendance(hex"", publicValues);
    }
}

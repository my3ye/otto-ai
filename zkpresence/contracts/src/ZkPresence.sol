// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ISP1Verifier} from "@sp1-contracts/ISP1Verifier.sol";

/// @title ZkPresence — Zero-Knowledge Proof of Attendance
/// @notice Verifies SP1 proofs of event attendance without revealing attendee identity.
/// @dev Uses SP1 Groth16 verifier gateway (pre-deployed on all EVM chains).
contract ZkPresence {
    // ── Types ────────────────────────────────────────────────────────────

    struct Event {
        address organizer;
        bytes32 locationHash;        // keccak256(geohash) for geo mode
        uint64  startTime;
        uint64  endTime;
        bytes32 organizerPubkeyHash; // sha256(compressed secp256k1 pubkey)
        bool    active;
    }

    // ── State ────────────────────────────────────────────────────────────

    ISP1Verifier public immutable verifier;
    bytes32      public immutable programVKey;

    mapping(uint64  => Event)                       public events;
    mapping(bytes32 => bool)                        public nullifierUsed;
    mapping(uint64  => mapping(bytes32 => bool))    public attended;

    uint64 public nextEventId;

    // ── Events ───────────────────────────────────────────────────────────

    event EventCreated(uint64 indexed eventId, address indexed organizer);
    event EventDeactivated(uint64 indexed eventId);
    event AttendanceVerified(
        uint64  indexed eventId,
        bytes32 indexed nullifier,
        bytes32 identityCommitment,
        uint8   attestationMode
    );

    // ── Constructor ──────────────────────────────────────────────────────

    /// @param _verifier Address of the SP1VerifierGateway (same on all chains).
    /// @param _programVKey Verification key of the zkPresence SP1 program.
    constructor(address _verifier, bytes32 _programVKey) {
        verifier = ISP1Verifier(_verifier);
        programVKey = _programVKey;
    }

    // ── Organizer Functions ──────────────────────────────────────────────

    /// @notice Create a new event.
    /// @param locationHash keccak256 of the event geohash (for geo mode; 0x0 if unused).
    /// @param startTime Unix timestamp — event start.
    /// @param endTime Unix timestamp — event end.
    /// @param organizerPubkeyHash SHA-256 hash of the organizer's compressed secp256k1 pubkey.
    /// @return eventId The assigned event ID.
    function createEvent(
        bytes32 locationHash,
        uint64  startTime,
        uint64  endTime,
        bytes32 organizerPubkeyHash
    ) external returns (uint64 eventId) {
        require(endTime > startTime, "invalid time window");

        eventId = nextEventId++;
        events[eventId] = Event({
            organizer: msg.sender,
            locationHash: locationHash,
            startTime: startTime,
            endTime: endTime,
            organizerPubkeyHash: organizerPubkeyHash,
            active: true
        });

        emit EventCreated(eventId, msg.sender);
    }

    /// @notice Deactivate an event (organizer only). No new proofs accepted.
    function deactivateEvent(uint64 eventId) external {
        require(events[eventId].organizer == msg.sender, "not organizer");
        events[eventId].active = false;
        emit EventDeactivated(eventId);
    }

    // ── Attendee Functions ───────────────────────────────────────────────

    /// @notice Submit a ZK proof of attendance.
    /// @param proof The SP1 Groth16 proof bytes.
    /// @param publicValues ABI-encoded PublicValues from the circuit.
    function verifyAttendance(
        bytes calldata proof,
        bytes calldata publicValues
    ) external {
        // 1. Verify the SP1 proof against the program vkey
        verifier.verifyProof(programVKey, publicValues, proof);

        // 2. Decode public values
        (
            uint64  eventId,
            bytes32 nullifier,
            bytes32 identityCommitment,
            uint8   attestationMode,
            uint64  timestamp,
            bytes32 organizerPubkeyHash
        ) = abi.decode(publicValues, (uint64, bytes32, bytes32, uint8, uint64, bytes32));

        // 3. Validate event
        Event storage evt = events[eventId];
        require(evt.active, "event not active");
        require(organizerPubkeyHash == evt.organizerPubkeyHash, "organizer mismatch");
        require(timestamp >= evt.startTime && timestamp <= evt.endTime, "outside event window");

        // 4. Check nullifier (prevents double-claim)
        require(!nullifierUsed[nullifier], "already claimed");
        nullifierUsed[nullifier] = true;

        // 5. Record attendance
        attended[eventId][identityCommitment] = true;

        emit AttendanceVerified(eventId, nullifier, identityCommitment, attestationMode);
    }

    // ── View Functions ───────────────────────────────────────────────────

    /// @notice Check if a user (by identity commitment) attended an event.
    function hasAttended(uint64 eventId, bytes32 identityCommitment) external view returns (bool) {
        return attended[eventId][identityCommitment];
    }

    /// @notice Check if a nullifier has been used.
    function isNullifierUsed(bytes32 nullifier) external view returns (bool) {
        return nullifierUsed[nullifier];
    }

    /// @notice Get event details.
    function getEvent(uint64 eventId) external view returns (Event memory) {
        return events[eventId];
    }

    /// @notice Get total number of events created.
    function eventCount() external view returns (uint64) {
        return nextEventId;
    }
}

//! zkPresence SP1 Guest Program
//!
//! Runs inside the SP1 zkVM. Proves attendance at an event without revealing identity.
//!
//! Private inputs:  user_secret, AttestationData
//! Public outputs:  event_id, nullifier, identity_commitment, mode, timestamp, org_pubkey_hash

#![no_main]
sp1_zkvm::entrypoint!(main);

use alloy_sol_types::SolType;
use zkpresence_core::{AttestationData, PublicValues};

/// ABI encoding type matching ZkPresence.sol's abi.decode(publicValues, ...)
/// Order: (uint64 eventId, bytes32 nullifier, bytes32 identityCommitment,
///         uint8 attestationMode, uint64 timestamp, bytes32 organizerPubkeyHash)
type PublicValuesAbi = alloy_sol_types::sol! {
    tuple(uint64, bytes32, bytes32, uint8, uint64, bytes32)
};

/// SHA-256 hash via SP1 precompile (accelerated, ~100x faster than software).
fn sha256(_data: &[u8]) -> [u8; 32] {
    // Phase 1: wire up sha2 crate compiled for RISC-V target.
    // SP1 accelerates SHA-256 via a syscall patch — the sha2 crate "just works"
    // when compiled for the SP1 guest, getting ~100x speedup automatically.
    todo!("Wire up SP1 SHA-256 — use `sha2` crate for RISC-V (SP1 patches the syscall)")
}

pub fn main() {
    // ── 1. Read private inputs ──────────────────────────────────────────
    let user_secret: [u8; 32] = sp1_zkvm::io::read();
    let attestation: AttestationData = sp1_zkvm::io::read();

    // ── 2. Derive identity commitment: H(user_secret) ──────────────────
    // This is the user's public identifier — stable across events,
    // but unlinkable to user_secret without the preimage.
    let identity_commitment = sha256(&user_secret);

    // ── 3. Derive nullifier: H(user_secret ‖ event_id) ─────────────────
    // Unique per user per event. Prevents double-claiming.
    let event_id = attestation.event_id();
    let mut nullifier_input = [0u8; 40]; // 32 bytes secret + 8 bytes event_id
    nullifier_input[..32].copy_from_slice(&user_secret);
    nullifier_input[32..40].copy_from_slice(&event_id.to_le_bytes());
    let nullifier = sha256(&nullifier_input);

    // ── 4. Verify attestation ───────────────────────────────────────────
    let mode = attestation.mode();
    let timestamp = attestation.timestamp();

    match &attestation {
        AttestationData::QrCode {
            event_id,
            timestamp,
            nonce,
            organizer_pubkey,
            signature_r,
            signature_s,
        } => {
            // Verify: organizer signed (event_id ‖ timestamp ‖ nonce)
            let mut message = Vec::new();
            message.extend_from_slice(&event_id.to_le_bytes());
            message.extend_from_slice(&timestamp.to_le_bytes());
            message.extend_from_slice(nonce);
            let msg_hash = sha256(&message);

            // Phase 1: ECDSA secp256k1 verify via SP1 precompile
            // sp1_zkvm::precompiles::secp256k1::verify(organizer_pubkey, &msg_hash, signature_r, signature_s);
            let _ = (&msg_hash, organizer_pubkey, signature_r, signature_s);
            todo!("Wire up ECDSA secp256k1 verification via SP1 precompile")
        }

        AttestationData::GeoProximity {
            event_id,
            timestamp,
            user_geohash,
            event_geohash,
            organizer_pubkey,
            signature_r,
            signature_s,
        } => {
            // Validate that geohash bytes are valid base-32 characters (0-9, b-h, j, k, m, n, p-z)
            fn is_valid_geohash_char(b: u8) -> bool {
                matches!(b, b'0'..=b'9' | b'b'..=b'h' | b'j' | b'k' | b'm' | b'n' | b'p'..=b'z')
            }
            for &b in user_geohash.iter().chain(event_geohash.iter()) {
                assert!(is_valid_geohash_char(b), "invalid geohash character");
            }

            // Verify geohash proximity: first 5 chars must match (~5km)
            assert_eq!(
                &user_geohash[..5],
                &event_geohash[..5],
                "geohash mismatch: user not within proximity"
            );

            // Verify: organizer signed (event_id ‖ event_geohash ‖ start_time ‖ end_time)
            let mut message = Vec::new();
            message.extend_from_slice(&event_id.to_le_bytes());
            message.extend_from_slice(event_geohash);
            let msg_hash = sha256(&message);

            let _ = (&msg_hash, organizer_pubkey, signature_r, signature_s);
            todo!("Wire up ECDSA secp256k1 verification via SP1 precompile")
        }

        AttestationData::OrganizerSignature {
            event_id,
            timestamp,
            organizer_pubkey,
            signature_r,
            signature_s,
        } => {
            // Verify: organizer signed (identity_commitment ‖ event_id)
            let mut message = Vec::new();
            message.extend_from_slice(&identity_commitment);
            message.extend_from_slice(&event_id.to_le_bytes());
            let msg_hash = sha256(&message);

            let _ = (&msg_hash, organizer_pubkey, signature_r, signature_s);
            todo!("Wire up ECDSA secp256k1 verification via SP1 precompile")
        }
    }

    // ── 5. Compute organizer pubkey hash ────────────────────────────────
    let organizer_pubkey_hash = sha256(attestation.organizer_pubkey());

    // ── 6. Commit public outputs (ABI-encoded for Solidity) ──────────────
    let public_values = PublicValues {
        event_id,
        nullifier,
        identity_commitment,
        attestation_mode: mode,
        timestamp,
        organizer_pubkey_hash,
    };

    // ABI-encode to match abi.decode() in ZkPresence.sol.
    // Using commit_slice (raw bytes) instead of commit (bincode) so Solidity
    // can decode with: abi.decode(publicValues, (uint64, bytes32, bytes32, uint8, uint64, bytes32))
    let encoded = PublicValuesAbi::abi_encode(&(
        public_values.event_id,
        alloy_sol_types::private::FixedBytes(public_values.nullifier),
        alloy_sol_types::private::FixedBytes(public_values.identity_commitment),
        public_values.attestation_mode,
        public_values.timestamp,
        alloy_sol_types::private::FixedBytes(public_values.organizer_pubkey_hash),
    ));
    sp1_zkvm::io::commit_slice(&encoded);
}

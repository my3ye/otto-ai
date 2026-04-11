//! zkPresence SP1 Guest Program
//!
//! Runs inside the SP1 zkVM. Proves attendance at an event without revealing identity.
//!
//! Private inputs:  user_secret, AttestationData
//! Public outputs:  event_id, nullifier, identity_commitment, mode, timestamp, org_pubkey_hash

#![no_main]
sp1_zkvm::entrypoint!(main);

use zkpresence_lib::{AttestationData, PublicValues};

/// SHA-256 hash via SP1 precompile (accelerated, ~100x faster than software).
fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hasher = sp1_zkvm::precompiles::utils::CurveOperations::sha256(data);
    // SP1 provides sha256 as a syscall — use the io-based approach for compatibility
    let digest = sp1_zkvm::io::hint_slice(data);
    // Simplified: SP1's sha256 precompile handles this natively
    // In production, use sp1_zkvm::syscalls::sha256 or a sha2 crate compiled for RISC-V
    todo!("Wire up SP1 SHA-256 precompile — see SP1 docs for exact syscall API")
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

            // TODO: ECDSA secp256k1 verify via SP1 precompile
            // sp1_zkvm::precompiles::secp256k1::verify(organizer_pubkey, &msg_hash, signature_r, signature_s);
            // For now, this is a placeholder — wire up the actual precompile call
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

            // TODO: ECDSA verify via SP1 precompile
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

            // TODO: ECDSA verify via SP1 precompile
        }
    }

    // ── 5. Compute organizer pubkey hash ────────────────────────────────
    let organizer_pubkey_hash = sha256(attestation.organizer_pubkey());

    // ── 6. Commit public outputs ────────────────────────────────────────
    let public_values = PublicValues {
        event_id,
        nullifier,
        identity_commitment,
        attestation_mode: mode,
        timestamp,
        organizer_pubkey_hash,
    };

    sp1_zkvm::io::commit(&public_values);
}

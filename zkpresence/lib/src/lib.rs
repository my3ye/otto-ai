//! Shared types for zkPresence — used by both the SP1 guest program and the host script.

#![no_std]
extern crate alloc;

use serde::{Deserialize, Serialize};

/// Attestation data provided as a private input to the ZK circuit.
/// Each variant carries the data needed to verify a specific attestation mode.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum AttestationData {
    /// Mode 0: QR Code Scan
    /// Organizer generates a signed QR payload displayed at the venue.
    QrCode {
        event_id: u64,
        timestamp: u64,
        nonce: [u8; 16],
        organizer_pubkey: [u8; 33], // compressed secp256k1
        signature_r: [u8; 32],
        signature_s: [u8; 32],
    },

    /// Mode 1: Geohash Proximity
    /// User proves their geohash matches the event's geohash at a given precision.
    GeoProximity {
        event_id: u64,
        timestamp: u64,
        user_geohash: [u8; 6],     // 6-char geohash
        event_geohash: [u8; 6],    // must match at 5-char precision
        organizer_pubkey: [u8; 33],
        signature_r: [u8; 32],
        signature_s: [u8; 32],
    },

    /// Mode 2: Organizer Direct Signature
    /// Organizer signs the attendee's identity commitment directly.
    OrganizerSignature {
        event_id: u64,
        timestamp: u64,
        organizer_pubkey: [u8; 33],
        signature_r: [u8; 32],
        signature_s: [u8; 32],
    },
}

impl AttestationData {
    pub fn event_id(&self) -> u64 {
        match self {
            AttestationData::QrCode { event_id, .. } => *event_id,
            AttestationData::GeoProximity { event_id, .. } => *event_id,
            AttestationData::OrganizerSignature { event_id, .. } => *event_id,
        }
    }

    pub fn timestamp(&self) -> u64 {
        match self {
            AttestationData::QrCode { timestamp, .. } => *timestamp,
            AttestationData::GeoProximity { timestamp, .. } => *timestamp,
            AttestationData::OrganizerSignature { timestamp, .. } => *timestamp,
        }
    }

    pub fn organizer_pubkey(&self) -> &[u8; 33] {
        match self {
            AttestationData::QrCode { organizer_pubkey, .. } => organizer_pubkey,
            AttestationData::GeoProximity { organizer_pubkey, .. } => organizer_pubkey,
            AttestationData::OrganizerSignature { organizer_pubkey, .. } => organizer_pubkey,
        }
    }

    /// Returns the attestation mode as a u8 (matches on-chain enum).
    pub fn mode(&self) -> u8 {
        match self {
            AttestationData::QrCode { .. } => 0,
            AttestationData::GeoProximity { .. } => 1,
            AttestationData::OrganizerSignature { .. } => 2,
        }
    }
}

/// Public values committed by the ZK circuit.
/// These are the only values visible on-chain after proof verification.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PublicValues {
    pub event_id: u64,
    pub nullifier: [u8; 32],
    pub identity_commitment: [u8; 32],
    pub attestation_mode: u8,
    pub timestamp: u64,
    pub organizer_pubkey_hash: [u8; 32],
}

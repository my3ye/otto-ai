//! Identity and nullifier derivation functions.
//!
//! These are the core cryptographic primitives for zkPresence:
//! - Identity commitment: a stable public identifier derived from a secret
//! - Nullifier: an event-specific token that prevents double-claiming

use sha2::{Digest, Sha256};

/// Derive an identity commitment from a user secret: SHA-256(user_secret)
///
/// The identity commitment is the user's public identifier — stable across events,
/// but unlinkable to user_secret without the preimage.
pub fn derive_identity(user_secret: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(user_secret);
    hasher.finalize().into()
}

/// Compute event-specific nullifier: SHA-256(user_secret || event_id_le)
///
/// Unique per user per event. Submitted on-chain to prevent double-claiming
/// without revealing the user's identity.
pub fn compute_nullifier(user_secret: &[u8; 32], event_id: u64) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(user_secret);
    hasher.update(&event_id.to_le_bytes());
    hasher.finalize().into()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_derive_identity_deterministic() {
        let secret = [0x42u8; 32];
        let id1 = derive_identity(&secret);
        let id2 = derive_identity(&secret);
        assert_eq!(id1, id2);
    }

    #[test]
    fn test_different_secrets_different_identities() {
        let secret1 = [0x42u8; 32];
        let secret2 = [0x43u8; 32];
        assert_ne!(derive_identity(&secret1), derive_identity(&secret2));
    }

    #[test]
    fn test_nullifier_deterministic() {
        let secret = [0x42u8; 32];
        let n1 = compute_nullifier(&secret, 1);
        let n2 = compute_nullifier(&secret, 1);
        assert_eq!(n1, n2);
    }

    #[test]
    fn test_different_events_different_nullifiers() {
        let secret = [0x42u8; 32];
        assert_ne!(compute_nullifier(&secret, 1), compute_nullifier(&secret, 2));
    }

    #[test]
    fn test_nullifier_differs_from_identity() {
        let secret = [0x42u8; 32];
        assert_ne!(derive_identity(&secret), compute_nullifier(&secret, 0));
    }
}

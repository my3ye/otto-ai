//! zkPresence Core — shared types and cryptographic primitives.
//!
//! This crate provides the fundamental types used across the zkPresence protocol:
//! - `AttestationData`: private inputs for the ZK circuit
//! - `PublicValues`: public outputs committed by the circuit
//! - Identity derivation and nullifier computation (std feature only)

#![cfg_attr(not(feature = "std"), no_std)]

extern crate alloc;

pub mod types;

#[cfg(feature = "std")]
pub mod identity;

// Re-export core types at crate root for convenience
pub use types::*;

#[cfg(feature = "std")]
pub use identity::*;

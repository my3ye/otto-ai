//! zkPresence Prover Library
//!
//! Provides a programmatic API for proof generation,
//! wrapping the SP1 SDK. The CLI binaries in `src/bin/` use this
//! library interface.

// Re-export SP1 SDK types that consumers need
pub use sp1_sdk::{include_elf, ProverClient, SP1Stdin};

pub use zkpresence_core::{AttestationData, PublicValues};

/// The compiled ELF binary of the zkPresence circuit.
pub const ELF: &[u8] = include_elf!("zkpresence-circuit");

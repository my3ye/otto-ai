//! zkPresence Proof Generator
//!
//! Generates a Groth16 proof of attendance for on-chain verification.
//!
//! Usage:
//!   cargo run --bin prove -- --event-id 1 --mode qr               (execute only, fast)
//!   cargo run --bin prove -- --event-id 1 --mode qr --proof       (execute + Groth16 proof)

use clap::Parser;
use sp1_sdk::{ProverClient, SP1Stdin};
use zkpresence_core::{AttestationData, PublicValues};
use zkpresence_prover::ELF;

#[derive(Parser, Debug)]
#[command(name = "zkpresence-prove", about = "Generate attendance proof")]
struct Args {
    /// Event ID to prove attendance for
    #[arg(long)]
    event_id: u64,

    /// Attestation mode: qr, geo, sig
    #[arg(long, default_value = "qr")]
    mode: String,

    /// Output file for the proof (default: proof.bin)
    #[arg(long, default_value = "proof.bin")]
    output: String,

    /// Generate a Groth16 proof (slow). Without this flag, only execute (fast, no proof).
    #[arg(long)]
    proof: bool,
}

fn main() {
    let args = Args::parse();

    // Initialize SP1 prover (reads SP1_PROVER env var)
    let client = ProverClient::from_env();

    // Setup proving/verification keys
    let (pk, vk) = client.setup(ELF);

    // ── Prepare inputs ──────────────────────────────────────────────────
    let mut stdin = SP1Stdin::new();

    // Private input 1: user secret (in production, read from secure storage)
    let user_secret: [u8; 32] = [0x42; 32]; // PLACEHOLDER — replace with real secret
    stdin.write(&user_secret);

    // Private input 2: attestation data
    let attestation = match args.mode.as_str() {
        "qr" => AttestationData::QrCode {
            event_id: args.event_id,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            nonce: [0u8; 16],                // PLACEHOLDER
            organizer_pubkey: [0u8; 33],     // PLACEHOLDER
            signature_r: [0u8; 32],          // PLACEHOLDER
            signature_s: [0u8; 32],          // PLACEHOLDER
        },
        "geo" => AttestationData::GeoProximity {
            event_id: args.event_id,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            user_geohash: *b"9q8yyk",       // PLACEHOLDER — SF
            event_geohash: *b"9q8yyk",      // PLACEHOLDER — SF
            organizer_pubkey: [0u8; 33],
            signature_r: [0u8; 32],
            signature_s: [0u8; 32],
        },
        "sig" => AttestationData::OrganizerSignature {
            event_id: args.event_id,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            organizer_pubkey: [0u8; 33],
            signature_r: [0u8; 32],
            signature_s: [0u8; 32],
        },
        _ => panic!("Unknown mode: {}. Use: qr, geo, sig", args.mode),
    };
    stdin.write(&attestation);

    // ── Execute (fast, no proof — for testing) ──────────────────────────
    println!("Executing program (no proof)...");
    let (mut output, report) = client.execute(ELF, &stdin).run().unwrap();
    println!("Execution complete. Cycles: {}", report.total_instruction_count());

    // Read public values from execution output
    let public_values: PublicValues = output.read();
    println!("Event ID:             {}", public_values.event_id);
    println!("Nullifier:            {}", hex::encode(public_values.nullifier));
    println!("Identity Commitment:  {}", hex::encode(public_values.identity_commitment));
    println!("Attestation Mode:     {}", public_values.attestation_mode);
    println!("Timestamp:            {}", public_values.timestamp);

    // ── Generate Groth16 proof (slow, for on-chain) ─────────────────────
    if args.proof {
        println!("\nGenerating Groth16 proof...");
        let proof = client
            .prove(&pk, &stdin)
            .groth16()
            .run()
            .expect("proof generation failed");

        // Verify locally before saving
        client.verify(&proof, &vk).expect("proof verification failed");
        println!("Proof verified locally.");

        // Save proof to file
        proof.save(&args.output).expect("failed to save proof");
        println!("Proof saved to: {}", args.output);

        // Print verification key (needed for contract deployment)
        println!("\nVerification key (for contract constructor):");
        println!("  vkey: 0x{}", hex::encode(vk.bytes32()));
    } else {
        println!("\nSkipping proof generation (use --proof to generate).");
        println!("Verification key: 0x{}", hex::encode(vk.bytes32()));
    }
}

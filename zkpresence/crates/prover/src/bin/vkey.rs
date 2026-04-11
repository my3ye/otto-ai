//! Export the program verification key.
//!
//! Usage: cargo run --bin vkey

use sp1_sdk::{include_elf, ProverClient};

const ELF: &[u8] = include_elf!("zkpresence-circuit");

fn main() {
    let client = ProverClient::from_env();
    let (_, vk) = client.setup(ELF);

    println!("Program Verification Key");
    println!("========================");
    println!("bytes32: 0x{}", hex::encode(vk.bytes32()));
    println!("\nUse this value as the _programVKey constructor argument");
    println!("when deploying ZkPresence.sol");
}

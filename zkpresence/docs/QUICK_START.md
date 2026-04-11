# Quick Start

This guide walks through a complete attendance proof flow using zkPresence — from event creation to on-chain verification.

> **Current Status:** The circuit's SHA-256 precompile and ECDSA verification are in active development. This guide uses mock mode, which validates circuit logic without computing a real ZK proof. Real end-to-end proofs will be available once Phase 1 precompile wiring is complete. See [ROADMAP.md](../ROADMAP.md).

---

## Prerequisites

Install the required tooling before starting:

```bash
# SP1 toolchain (pin to v6.1.0 — this project targets SP1 6.x precompile APIs)
curl -L https://sp1.succinct.xyz | bash && sp1up --version v6.1.0

# Foundry
curl -L https://foundry.paradigm.xyz | bash && foundryup

# Clone repository
git clone https://github.com/my3ye/zkpresence.git
cd zkpresence
```

---

## Step 1: Build

```bash
# Rust workspace
cargo build --workspace

# Contracts
cd contracts && forge install && forge build && cd ..
```

---

## Step 2: Understand the Roles

Every attendance proof involves three roles:

- **Organizer** — Creates the event on-chain. Generates attestation material (QR payloads or geo-fence parameters). Holds a secp256k1 keypair whose public key is registered with the event.

- **Attendee** — Holds a `user_secret` (32 random bytes, stored locally). Collects the organizer's attestation. Runs the prover to generate a ZK proof. Submits the proof on-chain.

- **Verifier Contract** — `ZkPresence.sol`. Verifies the proof via the SP1 gateway. Checks nullifier uniqueness. Records attendance. Emits `AttendanceVerified`.

---

## Step 3: Generate a Proof (Mock Mode)

Mock mode skips real ZK proof computation but runs all circuit logic, giving immediate feedback on correctness.

```bash
# Generate a proof in QR mode with a mock user secret and event ID
SP1_PROVER=mock cargo run --bin prove -- \
  --event-id 1 \
  --mode qr \
  --user-secret 0000000000000000000000000000000000000000000000000000000000000001

# Currently panics at sha256 — expected. The circuit is in active development. See CONTRIBUTING.md.
```

Available modes:
- `--mode qr` — QR code attestation (requires `--nonce` and `--organizer-signature` flags — see prover CLI help)
- `--mode geo` — Geohash proximity attestation
- `--mode sig` — Organizer direct signature

For development without real organizer keys, mock mode generates placeholder attestation data automatically.

---

## Step 4: Export the Verification Key

The verification key (vkey) ties a specific compiled circuit to the on-chain verifier. It must be exported from your circuit build and embedded in the contract constructor.

```bash
SP1_PROVER=mock cargo run --bin vkey
# Output: 0x<64-byte hex> — the program vkey for this circuit build
```

**Important:** The vkey changes whenever circuit code changes. A deployed contract is bound to the vkey at deployment time. Re-deploying after circuit changes requires a new vkey.

---

## Step 5: Deploy the Contract (Base Sepolia)

Once Phase 1 is complete, you will be able to deploy `ZkPresence.sol` to Base Sepolia:

```bash
# Set environment variables
export PRIVATE_KEY=<your-deployer-private-key>
export VKEY=<output from vkey step>

# Deploy
cd contracts
forge script script/Deploy.s.sol \
  --rpc-url https://sepolia.base.org \
  --broadcast \
  --verify
```

The contract constructor accepts:
- `verifier` — `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` (Succinct ISP1Verifier gateway, Base Sepolia)
- `programVKey` — the vkey from Step 4

**Note:** Deployment is planned for Phase 1. The deploy script is a placeholder until circuit precompile wiring is complete.

---

## Step 6: Create an Event (On-Chain)

Once deployed, an organizer creates an event:

```solidity
// Via ethers.js / viem, or directly via cast:
cast send <ZkPresence_address> \
  "createEvent(bytes32,uint64,uint64,bytes32)" \
  <locationHash> <startTime> <endTime> <organizerPubkeyHash> \
  --rpc-url https://sepolia.base.org \
  --private-key $PRIVATE_KEY
```

Where:
- `locationHash` — `keccak256(geohash_6chars)` for geo mode, `bytes32(0)` for QR mode
- `startTime` / `endTime` — Unix timestamps defining the attendance window
- `organizerPubkeyHash` — `sha256(compressed_secp256k1_pubkey)` (33-byte compressed key)

---

## Step 7: Submit a Proof

Attendees submit their proof after generating it:

```bash
# Using the prover CLI with network mode (Phase 1+):
SP1_PROVER=local cargo run --bin prove -- \
  --event-id 1 \
  --mode qr \
  --user-secret <your-32-byte-secret> \
  --submit-to <ZkPresence_address> \
  --rpc-url https://sepolia.base.org
```

Or directly via `cast` using serialized proof bytes from the prover output:

```bash
cast send <ZkPresence_address> \
  "verifyAttendance(bytes,bytes)" \
  <proof_hex> <public_values_hex> \
  --rpc-url https://sepolia.base.org \
  --private-key $ATTENDEE_KEY
```

On success, the contract emits:
```
AttendanceVerified(eventId, nullifier, identityCommitment, attestationMode)
```

---

## Step 8: Verify Attendance

Any application can query attendance status without knowing who the attendee is:

```bash
# Check if an identity commitment attended event 1
cast call <ZkPresence_address> \
  "hasAttended(uint64,bytes32)(bool)" \
  1 <identity_commitment_hex> \
  --rpc-url https://sepolia.base.org
```

The `identity_commitment` is the attendee's opt-in pseudonym. An attendee who wants to prove they attended can reveal their commitment. An attendee who wants to remain fully anonymous reveals nothing.

---

## What to Expect: Proof Generation Times

| Prover Mode | Time | Use Case |
|---|---|---|
| `mock` | < 1 second | Development, circuit logic testing |
| `local` | 5–20 minutes (hardware dependent) | Pre-production verification |
| `network` | < 30 seconds (planned) | Production, mobile users via Succinct Prover Network |

Local proving time depends on CPU core count and memory. The Succinct Prover Network will dramatically reduce this when integrated in Phase 3.

---

## Next Steps

- Read [ARCHITECTURE.md](../ARCHITECTURE.md) for the full protocol specification
- Read [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute to circuit development
- Track Phase 1 progress in [ROADMAP.md](../ROADMAP.md)
- Follow the project on GitHub for updates on precompile wiring and testnet deployment
- Questions and discussion: [GitHub Discussions](https://github.com/my3ye/zkpresence/discussions)

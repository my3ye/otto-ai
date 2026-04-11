# zkPresence

Zero-Knowledge Proof of Attendance using [Succinct SP1](https://docs.succinct.xyz) zkVM.

Prove you were at an event without revealing who you are.

## What It Does

zkPresence lets attendees generate cryptographic proofs that they attended a specific event, verified on-chain, without leaking their identity. The system uses three attestation modes:

- **QR Code Scan** — Scan a rotating QR at the venue
- **Geohash Proximity** — Prove you were within range of the event location
- **Organizer Signature** — Organizer directly attests your presence

Each mode produces a ZK proof that can be verified on Base (Ethereum L2) for ~$0.003.

## Architecture

```
User Device                     Base L2
┌─────────────────┐            ┌──────────────────┐
│ user_secret      │            │ ZkPresence.sol   │
│ + attestation    │──proof──▶ │   verifyProof()  │
│                  │            │   nullifier check│
│ SP1 Prover       │            │   record attend. │
└─────────────────┘            └──────────────────┘
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Project Structure

```
zkpresence/
├── lib/           # Shared types (AttestationData, PublicValues)
├── program/       # SP1 guest program (ZK circuit logic)
├── script/        # Host scripts (proof generation, vkey export)
├── contracts/     # Solidity verifier (Foundry)
├── ARCHITECTURE.md
└── README.md
```

## Prerequisites

```bash
# Install SP1 toolchain
curl -L https://sp1.succinct.xyz | bash
sp1up

# Install Foundry (for contracts)
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

## Quick Start

```bash
# 1. Build the SP1 program
cd script && cargo build

# 2. Run with mock prover (instant, no real proof)
SP1_PROVER=mock cargo run --bin prove -- --event-id 1 --mode qr

# 3. Export verification key
SP1_PROVER=mock cargo run --bin vkey

# 4. Deploy contract (Base Sepolia)
cd ../contracts
forge install succinctlabs/sp1-contracts
forge build
```

## Environment Variables

| Variable | Purpose | Values |
|---|---|---|
| `SP1_PROVER` | Prover backend | `mock` (dev), `local` (CPU), `network` (Succinct Network) |
| `SP1_PRIVATE_KEY` | Prover Network auth | Required for `network` mode |

## Integration Points

- **Otto Music** — Concert attendance proofs → exclusive content unlock
- **Tusita** — Community session attendance → privacy-preserving reputation

## Privacy Guarantees

- User identity (`user_secret`) never leaves the device
- On-chain: only `nullifier` (prevents double-claim) and `identity_commitment` (opt-in linkability) are visible
- Different events produce different nullifiers — attendance is unlinkable across events by default

## Target Chain

Base (Ethereum L2) — gas costs are negligible (~$0.003 per proof verification).

SP1 Groth16 Verifier Gateway: `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B`

## License

MIT

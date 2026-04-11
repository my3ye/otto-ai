# zkPresence

Prove you attended an event. Reveal nothing else.

zkPresence is an open-source zero-knowledge proof of attendance protocol built on [Succinct SP1](https://docs.succinct.xyz) and designed for deployment on Base (Ethereum L2). Attendees generate cryptographic proofs of presence — verified on-chain — without leaking their identity to anyone: organizer, contract, or observer.

> **Status:** Early development. The monorepo structure and core types are implemented. The SP1 circuit and prover integration are in active development. Not yet ready for production use.

---

## The Problem

Every current proof of attendance is a surveillance instrument.

POAP mints a token to your wallet — your wallet is public, your attendance history is public, your identity exposed to any data scraper with an Etherscan connection. QR check-in apps log your name against event timestamps. Ticketing systems store your payment method, seat, and face.

The receipt of attendance is also a record of who you are.

zkPresence separates proof from disclosure. You attended. You can prove it. No one needs to know who you are.

---

## How It Works

The protocol is designed around three components:

1. **SP1 Circuit** (`crates/circuit`) — Runs inside the SP1 zkVM. Takes your private `user_secret` and an attestation payload from the event organizer. Computes a nullifier and identity commitment. Verifies the organizer's ECDSA signature. Commits only public outputs.

2. **ZkPresence.sol** (`contracts/src/ZkPresence.sol`) — Receives the Groth16 proof, delegates verification to Succinct's pre-deployed `ISP1Verifier` gateway, checks nullifier uniqueness, and records attendance.

3. **Client SDKs** (`packages/`) — TypeScript SDK and EVM chain adapter for integrating proof generation and verification into applications.

### Attestation Modes

| Mode | Best For | How It Works |
|---|---|---|
| **QR Code** | Concerts, conferences, meetups | Scan a rotating QR at the venue. Circuit verifies the organizer's ECDSA signature over `(event_id ‖ timestamp ‖ nonce)`. |
| **Geohash Proximity** | Geo-fenced experiences | Device GPS → geohash. Circuit asserts 5-char prefix match (~5km). Organizer signs the geo-fence parameters. |
| **Organizer Signature** | Small events, VIP access | Organizer directly signs your `identity_commitment`. Most interactive; requires direct exchange. |

### Architecture

```
                     ┌──────────────────────────────────────┐
                     │           EVENT ORGANIZER            │
                     │  createEvent() on-chain              │
                     │  generates attestation material      │
                     └──────────────┬───────────────────────┘
                                    │ attestation_payload (private to user)
                     ┌──────────────▼───────────────────────┐
                     │           USER DEVICE                 │
                     │  user_secret (local, never sent)      │
                     │  + attestation_payload                │
                     │                                       │
                     │  ┌─────────────────────────────────┐ │
                     │  │         SP1 PROVER               │ │
                     │  │  private: user_secret, payload   │ │
                     │  │  public:  event_id, nullifier,   │ │
                     │  │           identity_commitment,   │ │
                     │  │           attestation_mode,      │ │
                     │  │           timestamp              │ │
                     │  └───────────────┬─────────────────┘ │
                     └─────────────────┼─────────────────────┘
                                       │ groth16 proof + public values
                     ┌─────────────────▼──────────────────────┐
                     │           BASE L2 (ON-CHAIN)            │
                     │  ZkPresence.sol                         │
                     │    verifyAttendance(proof, pubValues)   │
                     │    → ISP1Verifier.verifyProof()         │
                     │    → nullifier uniqueness check         │
                     │    → record attendance                  │
                     └─────────────────────────────────────────┘
```

### Privacy Guarantees (by design)

- `user_secret` never leaves your device — private input to the prover only
- On-chain: only `nullifier` and `identity_commitment` are visible — both are one-way hashes
- Different events produce different nullifiers — cross-event attendance is unlinkable by default
- Attendance count is verifiable. Individual identities are not.

---

## Repository Structure

```
zkpresence/
├── Cargo.toml                    # Rust workspace
├── rust-toolchain                # Pins Succinct RISC-V toolchain
├── package.json                  # Node workspace root
├── pnpm-workspace.yaml
├── turbo.json                    # Build pipeline
│
├── crates/
│   ├── core/                     # Shared types + identity primitives (zkpresence-core)
│   ├── circuit/                  # SP1 guest program — ZK circuit (zkpresence-circuit)
│   └── prover/                   # Host-side prover CLI + library (zkpresence-prover)
│
├── contracts/
│   ├── src/ZkPresence.sol        # On-chain verifier and event registry
│   ├── test/                     # Foundry test suite
│   └── script/Deploy.s.sol       # Deployment script
│
├── packages/
│   ├── sdk/                      # @zkpresence/sdk — TypeScript client
│   ├── adapter-evm/              # @zkpresence/adapter-evm — EVM chain adapter
│   ├── react-hooks/              # @zkpresence/react — React hooks (planned)
│   └── server/                   # @zkpresence/server — Server-side helpers (planned)
│
├── docs/                         # Documentation
└── examples/                     # Integration examples
```

---

## Prerequisites

```bash
# SP1 toolchain (required for circuit compilation)
curl -L https://sp1.succinct.xyz | bash
sp1up

# Foundry (required for Solidity contracts)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# pnpm (required for TypeScript packages)
npm install -g pnpm
```

Rust stable and Cargo are assumed. The SP1 toolchain installs the Succinct RISC-V target alongside your existing Rust installation.

---

## Quick Start

### Build the workspace

```bash
# Rust crates
cargo check --workspace

# TypeScript packages
pnpm install && pnpm build

# Contracts
cd contracts && forge install && forge build
```

### Generate a proof (mock mode — instant, no real ZK computation)

```bash
SP1_PROVER=mock cargo run --bin prove -- \
  --event-id 1 \
  --mode qr \
  --user-secret <32-byte-hex>
```

**Note:** The circuit's SHA-256 precompile and ECDSA verification are under active development. Mock mode is the intended development entry point at this stage. See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved.

### Export the verification key

```bash
SP1_PROVER=mock cargo run --bin vkey
```

---

## Environment Variables

| Variable | Purpose | Values |
|---|---|---|
| `SP1_PROVER` | Prover backend | `mock` (instant, dev), `local` (CPU), `network` (Succinct Prover Network) |
| `SP1_PRIVATE_KEY` | Prover Network authentication | Required for `network` mode |

---

## Target Deployment

**Chain:** Base (Ethereum L2)
**Proof system:** SP1 Groth16, verified via Succinct's pre-deployed `ISP1Verifier` gateway
**ISP1Verifier Gateway:** `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` (CREATE2, same address across EVM chains)

Estimated gas per proof verification: ~230,000 gas (~$0.003 on Base at typical fee rates).

---

## Security Properties

| Property | Mechanism |
|---|---|
| No identity leakage | `user_secret` is private; `identity_commitment = SHA-256(secret)` is a one-way binding |
| No double-claiming | `nullifier = SHA-256(secret ‖ event_id)` — deterministic, stored on-chain after first use |
| Attestation binding | Organizer ECDSA signature verified inside the ZK circuit |
| Event binding | `event_id` committed publicly; contract cross-checks registered events |
| Unlinkability | Different events produce different nullifiers |

**Known limitations:**

- Sybil attacks (one person, multiple `user_secret` values) require external identity binding to prevent
- Remote QR code sharing is mitigated by rotating nonces but not cryptographically prevented in QR mode
- `chainId` is not currently included in public values — multi-chain proof replay is a known gap

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full threat model.

---

## Contributing

The SP1 precompile wiring and test coverage are the highest-priority areas right now. If you are familiar with SP1, secp256k1, or Foundry testing, your contribution will move the protocol forward directly.

See [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

---

## License

MIT. See [LICENSE](LICENSE).

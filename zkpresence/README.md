# zkPresence

**Zero-knowledge proof of attendance protocol.** Prove you were somewhere without revealing who you are.

zkPresence lets event organizers verify attendance while preserving attendee privacy. Using SP1 zero-knowledge proofs, attendees can prove they were at an event without linking their on-chain identity to their real-world identity.

## How It Works

1. **Organizer** creates an event on-chain with location and time parameters
2. **Attendee** obtains attestation at the event (QR scan, geo-proximity, or organizer signature)
3. **Prover** generates a ZK proof that the attendee was present, producing a nullifier (prevents double-claiming) and identity commitment (unlinkable pseudonym)
4. **Verifier** contract validates the proof on-chain and records attendance

No one — not even the organizer — can link the on-chain attendance record to the attendee's real identity.

## Packages

### Rust Crates

| Crate | Path | Description |
|-------|------|-------------|
| `zkpresence-core` | `crates/core/` | Shared types (`AttestationData`, `PublicValues`) and identity primitives |
| `zkpresence-circuit` | `crates/circuit/` | SP1 guest program — the ZK circuit |
| `zkpresence-prover` | `crates/prover/` | Host-side prover library and CLI |

### TypeScript Packages

| Package | Path | Description |
|---------|------|-------------|
| `@zkpresence/sdk` | `packages/sdk/` | Core SDK — client, types, chain adapter interface |
| `@zkpresence/adapter-evm` | `packages/adapter-evm/` | EVM chain adapter (Base, Arbitrum, Ethereum) |
| `@zkpresence/react` | `packages/react-hooks/` | React hooks for attendance UIs |
| `@zkpresence/server` | `packages/server/` | Server utilities (proof queue, webhooks) |

### Contracts

| Contract | Path | Description |
|----------|------|-------------|
| `ZkPresence.sol` | `contracts/src/` | On-chain verifier and attendance registry |

## Quick Start

### Build Rust crates

```bash
# Requires SP1 toolchain: curl -L https://sp1.succinct.xyz | bash && sp1up
cargo check --workspace
```

### Build TypeScript packages

```bash
pnpm install
pnpm build
```

### Build contracts

```bash
cd contracts
forge install
forge build
```

### Generate a proof (mock mode)

```bash
SP1_PROVER=mock cargo run --bin prove -- --event-id 1 --mode qr
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full protocol specification, including:

- Circuit design and nullifier scheme
- Three attestation modes (QR, geo-proximity, organizer signature)
- On-chain contract interface
- Privacy properties and threat model

## Attestation Modes

| Mode | How | Privacy Level |
|------|-----|---------------|
| **QR Code** | Scan time-limited QR at venue | High — only proves presence |
| **Geo Proximity** | Geohash match within ~5km | Medium — reveals approximate area |
| **Organizer Signature** | Organizer signs identity commitment | High — requires organizer trust |

## Privacy Guarantees

- User identity (`user_secret`) never leaves the device
- On-chain: only `nullifier` (prevents double-claim) and `identity_commitment` are visible
- Different events produce different nullifiers — attendance is unlinkable across events

## Environment Variables

| Variable | Purpose | Values |
|---|---|---|
| `SP1_PROVER` | Prover backend | `mock` (dev), `local` (CPU), `network` (Succinct Network) |
| `SP1_PRIVATE_KEY` | Prover Network auth | Required for `network` mode |

## License

MIT

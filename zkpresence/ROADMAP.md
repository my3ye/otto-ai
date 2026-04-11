# zkPresence Roadmap

This document tracks what is built, what is in progress, and what is planned. Status is updated with each significant development milestone.

All unimplemented features described below are **planned** and use future tense intentionally. The protocol is in early development.

---

## Current State

**Phase:** 0 — Scaffolding complete, active circuit development

| Component | Status |
|---|---|
| Monorepo structure | Complete |
| `zkpresence-core` types | Complete |
| `ZkPresence.sol` contract design | Complete (undeployed) |
| Circuit structure (`zkpresence-circuit`) | In progress — SHA-256 precompile and ECDSA are `todo!()` |
| Prover CLI (`zkpresence-prover`) | Scaffolded — mock mode works, real proofs blocked on circuit |
| TypeScript SDK (`@zkpresence/sdk`) | Scaffolded — types defined, client stub |
| EVM adapter (`@zkpresence/adapter-evm`) | Scaffolded — chain configs, ABI stub |
| React hooks (`@zkpresence/react`) | Placeholder |
| Server utilities (`@zkpresence/server`) | Placeholder |
| Foundry test suite | Placeholder — needs real test coverage |
| Base Sepolia deployment | Not started |

---

## Phase 1 — Working Protocol (target: 2026-05-02)

The goal of Phase 1 is a verifiably correct, end-to-end proof pipeline. A single attendee should be able to prove QR-mode attendance, have that proof verified by `ZkPresence.sol` on Base Sepolia, and receive an `AttendanceVerified` event.

### 1.1 Wire SP1 Precompiles

- Replace `todo!()` SHA-256 stub in `crates/circuit/src/main.rs` with SP1's native SHA-256 accelerated syscall via the `sha2` crate (RISC-V target)
- Wire secp256k1 ECDSA verification in the circuit using SP1's `secp256k1` precompile for all three attestation modes
- Confirm cycle counts are within expected range (SHA-256 ~200 cycles, ECDSA ~15k–20k cycles per SP1 6.x benchmarks)

### 1.2 End-to-End Test (QR Mode)

- Write a host-side integration test in `crates/prover/` that:
  - Generates a valid QR attestation with a secp256k1 organizer keypair
  - Calls the prover with `SP1_PROVER=mock` to verify circuit logic
  - Calls the prover with `SP1_PROVER=local` to generate a real Groth16 proof
  - Decodes and validates public values output
- Add Foundry tests in `contracts/test/ZkPresence.t.sol` covering:
  - Happy path: create event → verify attendance → check `hasAttended()`
  - Double-claim rejection: submit same proof twice
  - Nullifier reuse rejection
  - Event time-window enforcement
  - Organizer pubkey mismatch rejection

### 1.3 Deploy to Base Sepolia

- Export program verification key (`cargo run --bin vkey`)
- Deploy `ZkPresence.sol` to Base Sepolia using `contracts/script/Deploy.s.sol`
- Verify contract source on Basescan
- Record deployed address and programVKey in `contracts/deployments/`

### 1.4 Geo and Organizer Signature Modes

- Wire ECDSA precompile for GeoProximity and OrganizerSignature attestation paths (currently `// TODO` after message hash computation)
- Add integration tests for both modes matching the QR mode test structure

---

## Phase 2 — Full Protocol + Developer Tooling (2–4 weeks after Phase 1)

Phase 2 ships a usable developer experience: a working SDK, an organizer tool, and documentation that lets an external developer integrate zkPresence without reading the circuit.

### 2.1 TypeScript SDK (`@zkpresence/sdk`)

- Implement `ZkPresenceClient` in `packages/sdk/src/client.ts`:
  - `createEvent(params)` — calls EVM adapter to create event on-chain
  - `generateProof(attestation, userSecret, proverConfig)` — wraps the Rust prover via WASM or subprocess
  - `submitProof(proof, publicValues, adapter)` — calls chain adapter to submit on-chain
  - `hasAttended(eventId, commitment, adapter)` — read-only attendance check
- Implement `EvmAdapter` in `packages/adapter-evm/src/adapter.ts` using `viem`:
  - Wire to Base Sepolia + Base mainnet chain configs
  - Pull ABI from Foundry build artifacts
- Publish `@zkpresence/sdk` and `@zkpresence/adapter-evm` to npm (alpha tag)

### 2.2 Organizer QR Tool

- Build a minimal web tool (Next.js or plain HTML) that:
  - Accepts an organizer private key (browser-local, never sent)
  - Accepts event ID, start time, end time
  - Generates rotating QR payloads (60-second nonce rotation)
  - Displays QR codes for venue use
- Host at `zkpresence.xyz/organizer` or publish as a standalone static app

### 2.3 Prover WASM Compilation

- Compile `zkpresence-prover` to WASM for in-browser proof generation
  - Blocked on SP1 SDK's WASM support — track upstream
  - Fallback: proof generation via server relay with Succinct Prover Network

### 2.4 Expanded Documentation

- `docs/QUICK_START.md` — end-to-end example for a first integration
- `docs/CIRCUIT.md` — circuit internals for ZK developers
- `docs/ATTESTATION_MODES.md` — organizer guide for all three modes
- `docs/CONTRACT_REFERENCE.md` — `ZkPresence.sol` interface reference
- `docs/SDK_REFERENCE.md` — TypeScript SDK API reference

### 2.5 React Hooks (`@zkpresence/react`)

- `useAttendanceProof(eventId, attestation)` — manages proof generation state
- `useHasAttended(eventId, commitment)` — queries on-chain attendance
- `useCreateEvent(params)` — organizer hook for event creation

---

## Phase 3 — Production Integration (4–8 weeks after Phase 2)

Phase 3 is production deployment, ecosystem integrations, and the Succinct Prover Network pipeline for mobile-viable proof times.

### 3.1 Prover Network Integration

- Switch default prover mode from `local` to `network` in production builds
- Implement proof request queue in `@zkpresence/server`:
  - Submit proof request to Succinct Prover Network
  - Poll for completion
  - Webhook delivery of completed proof + public values
- Target: proof generation < 30 seconds for mobile users

### 3.2 Base Mainnet Deployment

- Security review of `ZkPresence.sol` (internal + external)
- Audit of circuit logic for soundness (priority: nullifier derivation, ECDSA constraint completeness)
- Deploy to Base mainnet
- Multi-sig organizer key management documentation
- Deploy monitoring: index `AttendanceVerified` events via subgraph or event log

### 3.3 Mobile SDK

- React Native package (`@zkpresence/react-native`) wrapping the prover network flow
- Flutter package (`zkpresence_flutter`) — community-driven, planned
- Target: scan QR → generate proof → submit on-chain in < 45 seconds on mid-range hardware using Prover Network

### 3.4 Example: Music Platform Integration

The following describes how a music platform (such as Otto Music, a concert streaming service) would use zkPresence to gate exclusive content behind verifiable concert attendance:

- Artist dashboard: create events via `ZkPresenceClient.createEvent()`
- Venue QR display: rotating QR codes via organizer tool
- Fan flow: scan QR → proof generated → `AttendanceVerified` emitted
- Otto Music backend: listens for `AttendanceVerified` → unlocks exclusive tracks, stems, artist token distribution, proof-gated community channels
- Fan proves attendance without revealing identity to the platform

### 3.5 Example: Community Platform Integration

The following describes how a community platform (such as Tusita, a wellness and community reputation app) would use zkPresence for privacy-preserving attendance reputation:

- Session leaders create geo-fenced events (meditation center, community space)
- Participants generate geo-proximity or organizer-signature proofs
- `hasAttended()` queries build attendance history on-chain
- Platform assigns reputation weight based on cumulative attendance — without surveillance of which specific sessions an individual attended

### 3.6 Sybil Resistance (Research)

The current protocol allows one person to create multiple `user_secret` values and claim attendance multiple times under different pseudonyms. Phase 3 will investigate:

- Optional Worldcoin integration — `identityCommitment` bound to a World ID proof
- Government ID nullifier binding (without on-chain identity storage)
- Rate-limiting via out-of-band identity binding (no preferred approach yet — open research question)

---

## Long-Term Research

These are not planned features but open questions the protocol may eventually address:

- **Multi-chain proof replay** — Adding `chainId` to public values to prevent proof submission on unintended chains
- **Trusted hardware attestation** — Hardware-backed GPS in geo mode to mitigate GPS spoofing
- **Group membership** — Semaphore-style group trees for "prove you are in this set of attendees" without revealing which one
- **Selective disclosure** — Let users voluntarily reveal specific attendance records with zero-knowledge linkage proofs

---

## Version Log

| Version | Date | Notes |
|---|---|---|
| `0.1.0` | 2026-04-11 | Monorepo scaffold, core types, circuit stub, contract design |
| `0.2.0` | *planned* | Phase 1 complete — working end-to-end proof on Base Sepolia |
| `0.3.0` | *planned* | Phase 2 complete — SDK published, organizer tool live |
| `1.0.0` | *planned* | Phase 3 complete — Base mainnet deployment, ecosystem integrations |

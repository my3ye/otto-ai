# Contributing to zkPresence

zkPresence is an open-source protocol. Contributions — bug fixes, circuit improvements, documentation, SDK work, and test coverage — are welcome.

The highest-priority areas right now are **circuit precompile wiring** and **test coverage**. If you understand SP1's precompile API or Foundry testing, your time will have the most direct impact there.

---

## Before You Start

Read [ARCHITECTURE.md](ARCHITECTURE.md) to understand the protocol design. Read [ROADMAP.md](ROADMAP.md) to understand what is implemented, what is in progress, and what is planned.

The circuit is not yet functional — SHA-256 and ECDSA precompile calls are `todo!()`. If you are picking up your first issue, the circuit precompile work is the highest-leverage starting point.

> **Security constraint:** SHA-256 and ECDSA must be wired simultaneously before Phase 1 is safe to ship. A circuit with SHA-256 implemented but ECDSA still as `// TODO:` comments will compile, run, and generate proofs — but those proofs accept any attestation payload regardless of whether the organizer signed it. This is not a crash. It silently accepts forged attestations. Do not ship Phase 1 with only SHA-256 wired. ECDSA must be wired in the same release.

---

## Setup

### Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Rust | stable | Crate development |
| SP1 toolchain | v6.1.0 (`sp1up --version v6.1.0`) | Circuit compilation (Succinct RISC-V target) — pin this version; later versions may break precompile APIs |
| Foundry | latest (`foundryup`) | Solidity contracts |
| pnpm | 9.x | TypeScript packages |
| Node.js | 20+ | TypeScript packages |

### Install

```bash
# SP1 toolchain (pin to v6.1.0 — this project targets SP1 6.x precompile APIs)
curl -L https://sp1.succinct.xyz | bash
sp1up --version v6.1.0

# Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Clone and build
git clone https://github.com/my3ye/zkpresence.git
cd zkpresence

# Rust workspace
cargo check --workspace

# TypeScript packages
pnpm install
pnpm build

# Contracts
cd contracts && forge install && forge build && cd ..
```

### Verify your setup

```bash
# Should complete without error (mock prover, no ZK computation)
SP1_PROVER=mock cargo run --bin prove -- --event-id 1 --mode qr
```

If `sha256` panics with `todo!()` — that is expected. The circuit stub is the current development frontier.

---

## Where to Contribute

### 1. Circuit — SHA-256 Precompile (`crates/circuit/src/main.rs`)

**What:** Replace the `todo!()` SHA-256 stub with SP1's native SHA-256 acceleration.

**How:** SP1 6.x provides SHA-256 as an accelerated precompile via the `sha2` crate compiled for the RISC-V target. The correct approach:

```toml
# crates/circuit/Cargo.toml
[dependencies]
sha2 = { version = "0.10", default-features = false }
```

```rust
// crates/circuit/src/main.rs
use sha2::{Sha256, Digest};

fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    hasher.finalize().into()
}
```

SP1's build system detects SHA-256 usage and routes it through the accelerated syscall automatically when compiled for the RISC-V target. No manual syscall wiring needed with `sha2 = "0.10"`.

Verify by running `SP1_PROVER=local cargo run --bin prove -- --event-id 1 --mode qr` and checking cycle counts in the output.

> **Do not stop here.** A circuit with SHA-256 wired but ECDSA still as `// TODO:` comments silently accepts forged attestations — any proof passes regardless of whether the organizer signed the event. SHA-256 and ECDSA must land together. Open one PR for SHA-256, then one for ECDSA — both are required before Phase 1 is safe.

---

### 2. Circuit — ECDSA Verification (`crates/circuit/src/main.rs`)

**What:** Replace the three `// TODO: ECDSA verify via SP1 precompile` comments with actual secp256k1 ECDSA verification.

**How:** SP1 6.x provides a secp256k1 precompile. The `k256` crate (RustCrypto) is SP1-precompile-compatible:

```toml
# crates/circuit/Cargo.toml
[dependencies]
k256 = { version = "0.13", default-features = false, features = ["ecdsa"] }
```

```rust
// For each attestation mode, after computing msg_hash:
use k256::ecdsa::{Signature, VerifyingKey, signature::Verifier};
use k256::EncodedPoint;

let vk = VerifyingKey::from_encoded_point(
    &EncodedPoint::from_bytes(organizer_pubkey).expect("invalid pubkey")
).expect("invalid verifying key");

let sig = Signature::from_scalars(*signature_r, *signature_s)
    .expect("invalid signature");

vk.verify(&msg_hash, &sig).expect("attestation signature invalid");
```

The `k256` verification will be accelerated by SP1's secp256k1 precompile automatically. Confirm by checking that cycle counts for ECDSA verification are in the 15k–25k range per verification.

---

### 3. Foundry Test Suite (`contracts/test/ZkPresence.t.sol`)

**What:** Write comprehensive tests for `ZkPresence.sol`.

**The contract has no meaningful test coverage.** Priority test cases:

```solidity
// test/ZkPresence.t.sol

// REQUIRED (Phase 1 blockers):
test_createEvent_succeeds()               // organizer creates event, ID increments
test_verifyAttendance_happyPath()          // valid proof accepted, attendance recorded
test_verifyAttendance_rejectDuplicate()   // same proof submitted twice reverts
test_verifyAttendance_rejectExpired()     // proof outside event time window reverts
test_verifyAttendance_rejectOrgMismatch() // wrong organizer pubkey reverts
test_hasAttended_returnsFalse_before()    // before proof, returns false
test_hasAttended_returnsTrue_after()      // after proof, returns true
test_isNullifierUsed_lifecycle()          // nullifier unused → used lifecycle
test_deactivateEvent()                    // organizer deactivates, further proofs reject

// SECONDARY:
test_onlyOrganizer_canDeactivate()        // non-organizer deactivate reverts
test_eventDoesNotExist_reverts()          // verifyAttendance on nonexistent event reverts
```

Use Foundry's mock verifier for `ISP1Verifier`. You can deploy a simple mock that always returns `true` for `verifyProof()` to test contract logic independently of the circuit.

---

### 4. TypeScript SDK (`packages/sdk/`)

**What:** Implement the `ZkPresenceClient` class in `packages/sdk/src/client.ts`.

The types are defined. The client stub needs:
- `createEvent()` — delegates to `ChainAdapter.createEvent()`
- `generateProof()` — initially: shell out to `cargo run --bin prove` with the user's attestation and secret
- `submitProof()` — delegates to `ChainAdapter.submitProof()`
- `hasAttended()` — delegates to `ChainAdapter.hasAttended()`

The WASM prover path is blocked on SP1's upstream WASM support. Server-relay mode (call a backend that runs the Succinct Prover Network) is a viable alternative.

---

### 5. Documentation

Missing documentation that would be immediately useful to contributors:

- `docs/CIRCUIT.md` — Annotated walkthrough of the circuit logic, precompile choices, and constraint structure
- `docs/ATTESTATION_MODES.md` — Organizer guide: how to generate each type of attestation payload, QR rotation strategy, key management
- `docs/CONTRACT_REFERENCE.md` — Function-by-function reference for `ZkPresence.sol`
- `examples/` — A working end-to-end example (once Phase 1 precompiles are wired)

---

## Workflow

### Branching

- `main` — stable, compiles, circuit in mock-mode works
- `dev` — integration branch for in-progress work
- Feature branches: `feat/<short-description>`, e.g. `feat/sha256-precompile`
- Bug fixes: `fix/<short-description>`

### Pull Requests

1. Fork the repository and create a branch from `dev`
2. Make your changes
3. Run the full test suite before opening a PR:
   ```bash
   cargo test --workspace
   cd contracts && forge test
   pnpm test
   ```
4. Open a PR against `dev` with a description that covers:
   - What the change does
   - Why it's structured this way
   - What you tested and how
   - Any known gaps or follow-up work

Small, focused PRs merge faster than large ones. If you are tackling a Phase 1 item, one PR per circuit function (SHA-256, QR ECDSA, Geo ECDSA, Sig ECDSA) is preferred over a single omnibus PR.

### Commit Messages

Use conventional commit format:

```
feat(circuit): wire SP1 sha256 precompile via sha2 crate
fix(contracts): reject proofs outside event time window
test(contracts): add ZkPresenceTest happy path coverage
docs(contributing): add ECDSA wiring guidance
```

---

## Code Style

### Rust

- Run `cargo fmt` before committing
- Run `cargo clippy --workspace` and address warnings
- Document public types and functions with `///` doc comments
- `unsafe` blocks require a `// SAFETY:` comment explaining the invariant

### Solidity

- Run `forge fmt` before committing
- Follow the existing NatSpec style (`/// @notice`, `/// @param`, `/// @return`)
- Prefer explicit over implicit (no implicit casting, no abi.encode magic numbers)

### TypeScript

- Run `pnpm lint` before committing
- Strict TypeScript — no `any` without a comment explaining why
- Prefer named exports over default exports

---

## Community

Questions, design discussions, and contributor coordination: [GitHub Discussions](https://github.com/my3ye/zkpresence/discussions).

---

## Issue Tracking

Open issues on GitHub for:

- Bugs (label: `bug`)
- Circuit development tasks (label: `circuit`)
- Contract work (label: `contracts`)
- SDK implementation (label: `sdk`)
- Documentation gaps (label: `docs`)
- Security concerns (use GitHub's private security advisory channel — do not open public issues for vulnerabilities)

---

## Security

If you find a vulnerability in the circuit constraints, the smart contract, or the nullifier scheme, please report it privately before disclosing publicly. Use GitHub's security advisory feature or email the maintainers directly.

Priority security areas:

- **Nullifier derivation** — any weakness that allows nullifier prediction or forgery breaks double-claim prevention
- **ECDSA constraint completeness** — circuit must verify the full signature, not just the message hash
- **Front-running** — proof submission must be atomic with attendee benefit (currently safe: attendance is recorded to `identity_commitment`, not `msg.sender`)
- **Cross-chain replay** — `chainId` is not currently included in public values (documented known gap)

---

## License

By contributing to zkPresence, you agree that your contributions will be licensed under the MIT License.

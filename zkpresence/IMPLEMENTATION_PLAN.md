# zkPresence Monorepo Bootstrap — Implementation Plan

**Phase:** 0 (Scaffold)
**Source of truth:** ~/otto/docs/zkpresence-standalone-service-architecture-2026-04-11.md
**Objective:** Restructure existing MVP into monorepo layout, wire build tools, verify everything compiles.

---

## Current State

```
zkpresence/
├── Cargo.toml          # workspace: [lib, program, script]
├── rust-toolchain       # "succinct"
├── lib/                 # Shared types (AttestationData, PublicValues)
│   └── src/lib.rs
├── program/             # SP1 guest circuit
│   └── src/main.rs
├── script/              # Host-side prover CLI
│   ├── build.rs
│   └── src/bin/{prove.rs, vkey.rs}
├── contracts/           # Foundry project (ZkPresence.sol)
│   ├── foundry.toml
│   ├── remappings.txt
│   └── src/ZkPresence.sol
├── ARCHITECTURE.md
└── README.md
```

## Target State

```
zkpresence/
├── Cargo.toml                    # workspace: [crates/core, crates/circuit, crates/prover]
├── rust-toolchain                # "succinct" (unchanged)
├── package.json                  # root package.json (private, workspaces)
├── pnpm-workspace.yaml           # packages/*
├── turbo.json                    # build pipeline
├── .gitignore
├── LICENSE                       # MIT
├── README.md                     # Updated for monorepo
│
├── crates/
│   ├── core/                     # was lib/ — shared types + public API
│   │   ├── Cargo.toml            # rename: zkpresence-core (was zkpresence-lib)
│   │   └── src/
│   │       ├── lib.rs            # Re-exports from types.rs + identity.rs
│   │       ├── types.rs          # AttestationData, PublicValues (extracted from lib.rs)
│   │       └── identity.rs       # derive_identity(), compute_nullifier() (new)
│   │
│   ├── circuit/                  # was program/ — SP1 guest
│   │   ├── Cargo.toml            # rename: zkpresence-circuit (was zkpresence-program)
│   │   └── src/main.rs           # Unchanged content
│   │
│   └── prover/                   # was script/ — host-side prover
│       ├── Cargo.toml            # rename: zkpresence-prover (was zkpresence-script)
│       ├── build.rs
│       └── src/
│           ├── lib.rs            # New: public prove() API (library interface)
│           └── bin/
│               ├── prove.rs      # CLI wrapper calling lib.rs
│               └── vkey.rs       # Unchanged
│
├── contracts/                    # Foundry project (unchanged location)
│   ├── foundry.toml
│   ├── remappings.txt
│   ├── src/ZkPresence.sol
│   ├── test/                     # New: placeholder test file
│   │   └── ZkPresence.t.sol
│   └── script/                   # New: placeholder deploy script
│       └── Deploy.s.sol
│
├── packages/                     # TypeScript packages (empty scaffolds)
│   ├── sdk/
│   │   ├── package.json          # @zkpresence/sdk
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts          # Barrel export
│   │       ├── client.ts         # ZkPresenceClient stub
│   │       └── types.ts          # TypeScript type mirrors of Rust types
│   │
│   ├── adapter-evm/
│   │   ├── package.json          # @zkpresence/adapter-evm
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── adapter.ts        # EvmAdapter stub implementing ChainAdapter
│   │       ├── abi.ts            # ZkPresence.sol ABI (copy from forge output)
│   │       └── chains.ts         # Base, Arbitrum, Ethereum chain configs
│   │
│   ├── react-hooks/
│   │   ├── package.json          # @zkpresence/react
│   │   ├── tsconfig.json
│   │   └── src/
│   │       └── index.ts          # Placeholder
│   │
│   └── server/
│       ├── package.json          # @zkpresence/server
│       ├── tsconfig.json
│       └── src/
│           └── index.ts          # Placeholder
│
├── docs/                         # Documentation site (empty scaffold)
│   └── README.md
│
└── examples/                     # Usage examples (empty scaffold)
    └── README.md
```

---

## Step-by-Step Implementation

### Step 1: Create root config files

**Files to create:**
- `pnpm-workspace.yaml` — content: `packages: ["packages/*"]`
- `turbo.json` — basic build pipeline
- `package.json` — private root, scripts for build/test/lint
- `.gitignore` — Rust targets, node_modules, .turbo, foundry out/cache
- `LICENSE` — MIT

**turbo.json content:**
```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "test": {
      "dependsOn": ["build"]
    },
    "lint": {},
    "typecheck": {
      "dependsOn": ["^build"]
    }
  }
}
```

### Step 2: Restructure Rust crates

**Move operations:**
1. `lib/` → `crates/core/`
2. `program/` → `crates/circuit/`
3. `script/` → `crates/prover/`

**Rename packages in Cargo.toml files:**
- `crates/core/Cargo.toml`: `name = "zkpresence-core"` (was `zkpresence-lib`)
- `crates/circuit/Cargo.toml`: `name = "zkpresence-circuit"` (was `zkpresence-program`)
- `crates/prover/Cargo.toml`: `name = "zkpresence-prover"` (was `zkpresence-script`)

**Update root Cargo.toml:**
```toml
[workspace]
members = ["crates/core", "crates/circuit", "crates/prover"]
resolver = "2"
```

**Update dependency references:**
- `crates/circuit/Cargo.toml`: dep `zkpresence-lib` → `zkpresence-core`, path `../core`
- `crates/prover/Cargo.toml`: dep `zkpresence-lib` → `zkpresence-core`, path `../core`
- `crates/circuit/src/main.rs`: `use zkpresence_lib::` → `use zkpresence_core::`
- `crates/prover/src/bin/prove.rs`: `use zkpresence_lib::` → `use zkpresence_core::`
- `crates/prover/build.rs`: update ELF name if it references `zkpresence-program` → `zkpresence-circuit`

**Split crates/core/src/lib.rs into modules:**
- `types.rs` — move `AttestationData`, `PublicValues` and their impls
- `identity.rs` — new file with `derive_identity()` and `compute_nullifier()` functions
- `lib.rs` — re-export everything: `pub mod types; pub mod identity; pub use types::*; pub use identity::*;`

**identity.rs content (new):**
```rust
//! Identity and nullifier derivation functions.
use sha2::{Sha256, Digest};

/// Derive an identity commitment from a user secret: SHA-256(user_secret)
pub fn derive_identity(user_secret: &[u8; 32]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(user_secret);
    hasher.finalize().into()
}

/// Compute event-specific nullifier: SHA-256(user_secret || event_id_le)
pub fn compute_nullifier(user_secret: &[u8; 32], event_id: u64) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(user_secret);
    hasher.update(&event_id.to_le_bytes());
    hasher.finalize().into()
}
```

**Note:** Add `sha2 = "0.10"` to crates/core/Cargo.toml dependencies. The `#![no_std]` attribute in lib.rs will need to be removed or made conditional since sha2 with default features needs std. Use a feature flag: `default = ["std"]`, `std = ["sha2/std"]`.

### Step 3: Create prover library interface

**New file: `crates/prover/src/lib.rs`**

```rust
//! zkPresence Prover Library
//!
//! Provides a programmatic API for proof generation,
//! wrapping the SP1 SDK.

pub use zkpresence_core::{AttestationData, PublicValues};

// Re-export for consumers
pub const ELF: &[u8] = include_elf!("zkpresence-circuit");

// Library API will be fleshed out in Phase 1
```

The existing `prove.rs` binary remains unchanged — it will use lib.rs in Phase 1.

### Step 4: Scaffold TypeScript packages

Create minimal but buildable TS packages. Each needs:
- `package.json` with name, version, scripts (build, test, lint), dependencies
- `tsconfig.json` extending a shared base
- `src/index.ts` with barrel exports

**Shared tsconfig (root `tsconfig.base.json`):**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "dist",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  }
}
```

**@zkpresence/sdk types.ts — mirror Rust types:**
```typescript
export type Hex = `0x${string}`;

export enum AttestationMode {
  QrCode = 0,
  GeoProximity = 1,
  OrganizerSignature = 2,
}

export enum ProofStatus {
  Queued = 'queued',
  Proving = 'proving',
  Complete = 'complete',
  Submitted = 'submitted',
  Failed = 'failed',
}

export interface PublicValues {
  eventId: bigint;
  nullifier: Hex;
  identityCommitment: Hex;
  attestationMode: AttestationMode;
  timestamp: bigint;
  organizerPubkeyHash: Hex;
}

export interface Proof {
  proofBytes: Hex;
  publicValues: PublicValues;
  vkeyHash: Hex;
  metadata: ProofMetadata;
}

export interface ProofMetadata {
  proverMode: 'mock' | 'local' | 'network';
  generationTimeMs: number;
  cycleCount: number;
}

export interface ChainAdapter {
  readonly chainId: string;
  readonly name: string;
  deployVerifier(vkey: Hex): Promise<{ address: Hex; txHash: string }>;
  createEvent(params: CreateEventParams): Promise<{ eventId: bigint; txHash: string }>;
  submitProof(proof: Uint8Array, publicValues: Uint8Array): Promise<{ txHash: string }>;
  hasAttended(eventId: bigint, commitment: Hex): Promise<boolean>;
  isNullifierUsed(nullifier: Hex): Promise<boolean>;
}

export interface CreateEventParams {
  locationHash: Hex;
  startTime: Date;
  endTime: Date;
  organizerPubkeyHash: Hex;
}
```

### Step 5: Scaffold contract test + deploy script

**contracts/test/ZkPresence.t.sol:**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ZkPresence.sol";

contract ZkPresenceTest is Test {
    // Placeholder — Phase 1 will add actual tests
    function test_placeholder() public {
        assertTrue(true);
    }
}
```

**contracts/script/Deploy.s.sol:**
```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/ZkPresence.sol";

contract DeployZkPresence is Script {
    function run() external {
        vm.startBroadcast();
        // Verifier gateway + program vkey will be set at deploy time
        // new ZkPresence(verifier, vkey);
        vm.stopBroadcast();
    }
}
```

### Step 6: Update README.md

Replace existing README with monorepo overview:
- Project description
- Package listing (crates + packages)
- Quick start (build, test)
- Architecture overview (link to ARCHITECTURE.md)
- License: MIT

### Step 7: Verify builds

Run and fix any issues:
```bash
# Rust workspace
cargo check --workspace 2>&1 | head -50

# TypeScript packages (if pnpm available)
pnpm install && pnpm build

# Contracts (if forge available)
cd contracts && forge build
```

---

## Affected Files Summary

| Action | Path | Description |
|--------|------|-------------|
| MOVE | `lib/` → `crates/core/` | Shared types crate |
| MOVE | `program/` → `crates/circuit/` | SP1 guest circuit |
| MOVE | `script/` → `crates/prover/` | Host prover |
| EDIT | `Cargo.toml` | Update workspace members |
| EDIT | `crates/core/Cargo.toml` | Rename package, add sha2 dep |
| EDIT | `crates/core/src/lib.rs` | Split into modules, re-exports |
| CREATE | `crates/core/src/types.rs` | Extracted types |
| CREATE | `crates/core/src/identity.rs` | Identity/nullifier functions |
| EDIT | `crates/circuit/Cargo.toml` | Update dep name/path |
| EDIT | `crates/circuit/src/main.rs` | Update use statement |
| EDIT | `crates/prover/Cargo.toml` | Update dep name/path |
| EDIT | `crates/prover/src/bin/prove.rs` | Update use statement |
| CREATE | `crates/prover/src/lib.rs` | Library interface |
| CREATE | `pnpm-workspace.yaml` | Node workspace config |
| CREATE | `turbo.json` | Build pipeline |
| CREATE | `package.json` | Root package |
| CREATE | `tsconfig.base.json` | Shared TS config |
| CREATE | `.gitignore` | Ignore rules |
| CREATE | `LICENSE` | MIT license |
| CREATE | `packages/sdk/` | SDK scaffold (4 files) |
| CREATE | `packages/adapter-evm/` | EVM adapter scaffold (5 files) |
| CREATE | `packages/react-hooks/` | React hooks scaffold (3 files) |
| CREATE | `packages/server/` | Server scaffold (3 files) |
| CREATE | `contracts/test/ZkPresence.t.sol` | Test placeholder |
| CREATE | `contracts/script/Deploy.s.sol` | Deploy script placeholder |
| CREATE | `docs/README.md` | Docs scaffold |
| CREATE | `examples/README.md` | Examples scaffold |
| EDIT | `README.md` | Monorepo overview |

---

## Critical Notes for Implementation

1. **Do NOT modify circuit logic or fix TODOs** — that's Phase 1 work
2. **The `include_elf!` macro** in prove.rs references the ELF by crate name. After renaming `zkpresence-program` → `zkpresence-circuit`, the ELF name changes. Update the string in `include_elf!("zkpresence-circuit")`
3. **The `#![no_std]` in lib.rs** must be handled carefully. The core types crate should stay no_std compatible (for SP1 guest). The identity module with sha2 needs std. Solution: keep types.rs as no_std, gate identity.rs behind `#[cfg(feature = "std")]`
4. **Cargo workspace resolver** stays at "2" — required for SP1
5. **rust-toolchain** file stays as "succinct" — SP1 requires specific toolchain
6. **contracts/remappings.txt** — check if forge-std needs installing via `forge install`

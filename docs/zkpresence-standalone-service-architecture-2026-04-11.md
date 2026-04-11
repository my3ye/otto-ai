# zkPresence: Standalone Service & Ecosystem Base Architecture

**Date:** 2026-04-11
**Author:** Otto (architect agent)
**Status:** Design Complete
**Existing codebase:** `~/otto/zkpresence/` (SP1 circuits, ZkPresence.sol, proof scripts)

---

## Design: zkPresence Standalone Service

### Problem

zkPresence exists as a self-contained proof-of-attendance system (SP1 circuits + one Solidity contract + CLI scripts). To serve as both (a) the shared privacy primitive for internal MY3YE projects (ONEON identity, Tusita community, SOS governance, Koink gating) and (b) a sellable managed service for external teams, it needs:

- A clean SDK boundary between the ZK core and consuming applications
- Pluggable chain adapters (EVM today, Solana/XMTP tomorrow) so proof verification isn't locked to Base
- A service layer that external developers can call via REST/WebSocket without running their own prover infrastructure
- A monorepo that ships independent packages (core, adapters, server, react-hooks, docs)
- Pricing tiers that cover prover compute costs while being competitive

### What Exists Today

```
~/otto/zkpresence/
├── lib/           → Rust shared types (AttestationData, PublicValues)
├── program/       → SP1 guest (ZK circuit, 122 lines)
├── script/        → prove.rs + vkey.rs (host-side proof gen)
├── contracts/     → ZkPresence.sol (148 lines, Foundry)
├── ARCHITECTURE.md
└── README.md
```

Working: circuit logic, nullifier scheme, 3 attestation modes, contract.
Not yet working: ECDSA precompile calls are `TODO`, prove.rs uses placeholder data.

---

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            EXTERNAL CONSUMERS                                   │
│  React App    Mobile App    Server-Side    CLI    Third-Party Service            │
└──────┬────────────┬───────────┬──────────┬─────────────┬────────────────────────┘
       │            │           │          │             │
       ▼            ▼           ▼          ▼             ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        @zkpresence/react-hooks                                   │
│   useProveAttendance()  useVerifyProof()  useEventCreate()  useProofStatus()     │
└──────────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                     zkPresence Service Layer (REST + WS)                         │
│                                                                                  │
│   POST /v1/proofs/generate    ←── submit attestation, get proof back             │
│   GET  /v1/proofs/:id         ←── poll proof status                              │
│   WS   /v1/proofs/stream      ←── real-time proof status                         │
│   POST /v1/events             ←── create event (chain-agnostic)                  │
│   POST /v1/verify             ←── off-chain proof verification                   │
│   GET  /v1/attendance/:event  ←── query attendance records                       │
│                                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                          │
│   │  Proof Queue  │  │  Rate Limiter │  │   API Keys   │                          │
│   │  (BullMQ)     │  │  (per-tier)   │  │   (JWT)      │                          │
│   └──────┬───────┘  └──────────────┘  └──────────────┘                          │
│          │                                                                       │
│          ▼                                                                       │
│   ┌──────────────────────────────────────┐                                       │
│   │         Prover Worker Pool           │                                       │
│   │  SP1_PROVER=network (Succinct Net)   │                                       │
│   │  SP1_PROVER=local   (self-hosted)    │                                       │
│   │  SP1_PROVER=mock    (dev/test)       │                                       │
│   └──────────────┬───────────────────────┘                                       │
└──────────────────┼───────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          @zkpresence/core (Rust + WASM)                          │
│                                                                                  │
│   ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐                 │
│   │  Circuit Types  │  │  Proof Builder   │  │  Nullifier Math   │                 │
│   │  (lib/)         │  │  (SDK wrapper)   │  │  (identity, null) │                 │
│   └────────────────┘  └────────┬────────┘  └──────────────────┘                 │
│                                │                                                 │
│                                ▼                                                 │
│                    ┌──────────────────────┐                                       │
│                    │   SP1 zkVM Runtime    │                                       │
│                    │   (program/ crate)    │                                       │
│                    └──────────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                        @zkpresence/adapters                                      │
│                                                                                  │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│   │   EVM    │  │  Solana  │  │   XMTP   │  │  Starknet│  │  Custom  │         │
│   │ (Base,   │  │ (Anchor  │  │ (message │  │ (Cairo   │  │ (impl    │         │
│   │  Arb,    │  │  program)│  │  frames) │  │  verifier│  │  trait)  │         │
│   │  ETH)    │  │          │  │          │  │          │  │          │         │
│   └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘         │
│                                                                                  │
│   trait ChainAdapter {                                                           │
│     fn deploy_verifier() → Address                                               │
│     fn submit_proof(proof, public_values) → TxHash                               │
│     fn query_attendance(event_id, commitment) → bool                             │
│     fn create_event(params) → EventId                                            │
│   }                                                                              │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Core SDK Interface (`@zkpresence/core`)

The core is the existing Rust workspace, wrapped with a clean public API. No chain dependencies — pure ZK math + proof generation.

### Public API Surface

```rust
// ── @zkpresence/core ──────────────────────────────────────────────

/// Generate a user identity from a secret.
/// Returns (identity_commitment, nullifier_for_event).
pub fn derive_identity(user_secret: &[u8; 32]) -> IdentityCommitment;

/// Compute the nullifier for a specific event.
pub fn compute_nullifier(user_secret: &[u8; 32], event_id: u64) -> Nullifier;

/// Build attestation data from raw inputs.
pub fn build_attestation(mode: AttestationMode, params: AttestationParams) -> AttestationData;

/// Generate a ZK proof of attendance.
/// Prover backend selected via SP1_PROVER env var.
pub async fn prove(input: ProveInput) -> Result<Proof, ProveError>;

/// Verify a proof off-chain (for server-side validation).
pub fn verify(proof: &Proof, vkey: &VerificationKey) -> Result<PublicValues, VerifyError>;

/// Export verification key (needed for contract deployment).
pub fn export_vkey() -> VerificationKey;
```

### Type Definitions

```rust
pub struct ProveInput {
    pub user_secret: [u8; 32],
    pub attestation: AttestationData,
    pub prover_mode: ProverMode,     // Mock | Local | Network
}

pub struct Proof {
    pub proof_bytes: Vec<u8>,        // Groth16 proof
    pub public_values: PublicValues,
    pub vkey_hash: [u8; 32],
    pub metadata: ProofMetadata,
}

pub struct ProofMetadata {
    pub prover_mode: ProverMode,
    pub generation_time_ms: u64,
    pub cycle_count: u64,
}

pub enum ProverMode {
    Mock,       // Instant, no real proof (dev/test)
    Local,      // CPU proving (slow, ~minutes)
    Network,    // Succinct Prover Network (fast, paid)
}

pub type IdentityCommitment = [u8; 32];  // SHA-256(user_secret)
pub type Nullifier = [u8; 32];           // SHA-256(user_secret ‖ event_id)
```

### WASM Target

The core compiles to WASM for browser/Node.js usage:

```toml
# Cargo.toml additions
[lib]
crate-type = ["cdylib", "rlib"]

[target.'cfg(target_arch = "wasm32")'.dependencies]
wasm-bindgen = "0.2"
```

**Note:** Only identity derivation, nullifier computation, and verification compile to WASM. Proof generation requires the SP1 host SDK (native Rust or server-side).

---

## 2. Pluggable Chain Adapters (`@zkpresence/adapters`)

### Adapter Trait

```typescript
// TypeScript interface (mirrors Rust trait for SDK consumers)
interface ChainAdapter {
  readonly chainId: string;            // "evm:8453" | "solana:mainnet" | "xmtp:production"
  readonly name: string;               // "Base" | "Solana" | "XMTP"
  
  // Deploy
  deployVerifier(vkey: Hex): Promise<DeployResult>;
  
  // Write
  createEvent(params: CreateEventParams): Promise<{ eventId: bigint; txHash: string }>;
  submitProof(proof: Uint8Array, publicValues: Uint8Array): Promise<{ txHash: string }>;
  deactivateEvent(eventId: bigint): Promise<{ txHash: string }>;
  
  // Read
  hasAttended(eventId: bigint, commitment: Hex): Promise<boolean>;
  isNullifierUsed(nullifier: Hex): Promise<boolean>;
  getEvent(eventId: bigint): Promise<EventData | null>;
  
  // Subscribe (optional)
  onAttendanceVerified?(callback: (event: AttendanceEvent) => void): Unsubscribe;
}
```

### EVM Adapter (ships first)

```
@zkpresence/adapter-evm
├── src/
│   ├── adapter.ts          # ChainAdapter implementation using viem
│   ├── abi.ts              # ZkPresence.sol ABI (auto-generated)
│   ├── deploy.ts           # Foundry deployment script wrapper
│   └── chains.ts           # Pre-configured chains (Base, Arbitrum, Ethereum)
├── contracts/
│   └── ZkPresence.sol      # Existing contract (moved here)
└── package.json
```

Key decisions:
- **viem over ethers.js** — smaller bundle, better TypeScript, tree-shakeable
- **Pre-deployed addresses** — ISP1Verifier gateway is the same on all EVM chains (CREATE2), so only ZkPresence.sol needs per-chain deployment

### Solana Adapter (Phase 2)

```
@zkpresence/adapter-solana
├── programs/
│   └── zk_presence/        # Anchor program
│       ├── src/lib.rs       # Solana verifier + event registry
│       └── Cargo.toml
├── src/
│   ├── adapter.ts           # ChainAdapter implementation using @solana/web3.js
│   └── idl.ts               # Anchor IDL
└── package.json
```

Design note: SP1 Groth16 proofs can be verified on Solana using the `groth16-solana` crate (alt_bn128 precompile). The contract structure mirrors EVM but uses PDAs for event/nullifier storage.

### XMTP Adapter (Phase 2)

```
@zkpresence/adapter-xmtp
├── src/
│   ├── adapter.ts           # ChainAdapter-like (messaging, not chain)
│   ├── frames.ts            # XMTP Frames for proof-gated content
│   └── codec.ts             # Custom content type for proof payloads
└── package.json
```

XMTP doesn't verify proofs on-chain — instead it uses proofs as **access credentials for gated messaging**:

```
Flow:
  1. Group admin sets rule: "Must have zkPresence proof for event X"
  2. User sends proof as XMTP message (custom content type)
  3. XMTP frame verifies proof off-chain via @zkpresence/core
  4. User gets added to group / sees gated content
```

### Starknet Adapter (Phase 3)

Uses Cairo for native proof verification. Lower priority — included for completeness.

### Custom Adapter Pattern

```typescript
import { ChainAdapter, CreateEventParams } from '@zkpresence/core';

class MyCustomAdapter implements ChainAdapter {
  chainId = 'custom:mychain';
  name = 'MyChain';
  // ... implement methods
}

// Register with the service
service.registerAdapter(new MyCustomAdapter());
```

---

## 3. Service Layer (REST + WebSocket)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   zkPresence Service                             │
│                   (Node.js / Fastify)                            │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Auth    │  │  Rate Limit  │  │  Proof Queue (BullMQ)     │  │
│  │  (JWT +  │  │  (per tier)  │  │                           │  │
│  │  API key)│  │              │  │  ┌─────┐ ┌─────┐ ┌─────┐ │  │
│  └──────────┘  └──────────────┘  │  │ W1  │ │ W2  │ │ W3  │ │  │
│                                  │  └─────┘ └─────┘ └─────┘ │  │
│                                  └───────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Adapter Registry                                        │   │
│  │  ┌─────┐ ┌────────┐ ┌──────┐ ┌─────────┐               │   │
│  │  │ EVM │ │ Solana │ │ XMTP │ │ Custom  │               │   │
│  │  └─────┘ └────────┘ └──────┘ └─────────┘               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL                                              │   │
│  │  events, proofs, api_keys, usage_metrics                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### REST API

```yaml
# ── Authentication ──────────────────────────────────────────────
POST   /v1/auth/register          # Create account + API key
POST   /v1/auth/rotate-key        # Rotate API key

# ── Events ──────────────────────────────────────────────────────
POST   /v1/events                 # Create event
GET    /v1/events/:id             # Get event details
PATCH  /v1/events/:id             # Update event (organizer only)
DELETE /v1/events/:id             # Deactivate event
GET    /v1/events/:id/attendance  # List attendance records

# ── Proofs ──────────────────────────────────────────────────────
POST   /v1/proofs/generate        # Submit attestation → async proof generation
GET    /v1/proofs/:id             # Get proof status + result
POST   /v1/proofs/verify          # Off-chain proof verification
GET    /v1/proofs/:id/receipt     # On-chain submission receipt

# ── Chain Operations ────────────────────────────────────────────
POST   /v1/chain/submit           # Submit proof on-chain (managed)
GET    /v1/chain/status/:txHash   # Transaction status
GET    /v1/chain/adapters         # List available chain adapters

# ── Attestation Helpers ─────────────────────────────────────────
POST   /v1/attestation/qr         # Generate signed QR payload
POST   /v1/attestation/geo-fence  # Create signed geo-fence
POST   /v1/attestation/sign       # Direct organizer signature

# ── Usage ───────────────────────────────────────────────────────
GET    /v1/usage                  # Current period usage stats
GET    /v1/usage/history          # Historical usage
```

### WebSocket API

```
WS /v1/proofs/stream

// Client → Server
{ "action": "subscribe", "proof_id": "abc123" }
{ "action": "subscribe_event", "event_id": 42 }
{ "action": "unsubscribe", "proof_id": "abc123" }

// Server → Client
{ "type": "proof_status", "proof_id": "abc123", "status": "queued", "position": 3 }
{ "type": "proof_status", "proof_id": "abc123", "status": "proving", "progress": 0.4 }
{ "type": "proof_status", "proof_id": "abc123", "status": "complete", "proof": "0x..." }
{ "type": "proof_status", "proof_id": "abc123", "status": "failed", "error": "..." }
{ "type": "attendance", "event_id": 42, "commitment": "0x...", "mode": "qr" }
```

### Proof Generation Flow

```
                    Client
                      │
              POST /v1/proofs/generate
              {
                user_secret: "0x...",     ← encrypted in transit (TLS)
                attestation: { mode: "qr", ... },
                chain: "evm:8453",        ← optional: auto-submit on-chain
                callback_url: "https://..." ← optional: webhook on completion
              }
                      │
                      ▼
              ┌───────────────┐
              │  API Gateway   │
              │  - validate    │
              │  - rate check  │
              │  - enqueue     │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  BullMQ Queue  │◄── Redis
              │  "proofs"      │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │ Prover Worker  │
              │ (Rust binary   │
              │  via FFI/exec) │
              │                │
              │ 1. Build stdin │
              │ 2. SP1 prove  │
              │ 3. Store proof │
              │ 4. Notify WS  │
              └───────┬───────┘
                      │
                      ▼ (if chain specified)
              ┌───────────────┐
              │ Chain Submitter│
              │ adapter.submit │
              │ Proof()        │
              └───────────────┘
```

### Data Model (PostgreSQL)

```sql
-- API consumers
CREATE TABLE zkp_api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    key_hash    TEXT NOT NULL UNIQUE,     -- bcrypt hash of API key
    tier        TEXT NOT NULL DEFAULT 'free',  -- free | builder | pro | enterprise
    created_at  TIMESTAMPTZ DEFAULT now(),
    rate_limit  INT DEFAULT 10           -- proofs per minute
);

-- Events (chain-agnostic mirror)
CREATE TABLE zkp_events (
    id              BIGSERIAL PRIMARY KEY,
    api_key_id      UUID REFERENCES zkp_api_keys(id),
    chain           TEXT,                 -- "evm:8453" or NULL (off-chain only)
    chain_event_id  BIGINT,              -- on-chain event ID (if submitted)
    chain_tx_hash   TEXT,
    location_hash   BYTEA,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    organizer_pubkey_hash BYTEA NOT NULL,
    metadata        JSONB DEFAULT '{}',   -- arbitrary event metadata
    active          BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Proof jobs
CREATE TABLE zkp_proofs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id      UUID REFERENCES zkp_api_keys(id),
    event_id        BIGINT REFERENCES zkp_events(id),
    status          TEXT NOT NULL DEFAULT 'queued',
                    -- queued → proving → complete → submitted | failed
    attestation_mode TEXT NOT NULL,       -- qr | geo | sig
    proof_bytes     BYTEA,               -- Groth16 proof (after completion)
    public_values   BYTEA,               -- encoded public values
    nullifier       BYTEA,               -- for dedup
    identity_commitment BYTEA,
    chain           TEXT,                 -- target chain for submission
    chain_tx_hash   TEXT,                -- on-chain submission tx
    prover_mode     TEXT DEFAULT 'network',
    cycle_count     BIGINT,
    generation_ms   INT,
    error           TEXT,
    callback_url    TEXT,
    created_at      TIMESTAMPTZ DEFAULT now(),
    completed_at    TIMESTAMPTZ
);

-- Usage tracking
CREATE TABLE zkp_usage (
    id          BIGSERIAL PRIMARY KEY,
    api_key_id  UUID REFERENCES zkp_api_keys(id),
    period      DATE NOT NULL,           -- billing period (monthly)
    proofs_generated INT DEFAULT 0,
    proofs_submitted INT DEFAULT 0,      -- on-chain submissions
    compute_seconds  FLOAT DEFAULT 0,
    UNIQUE(api_key_id, period)
);

CREATE INDEX idx_zkp_proofs_status ON zkp_proofs(status);
CREATE INDEX idx_zkp_proofs_nullifier ON zkp_proofs(nullifier);
CREATE INDEX idx_zkp_events_active ON zkp_events(active) WHERE active = TRUE;
```

---

## 4. Monorepo Package Structure

```
zkpresence/                              # Root (pnpm workspace + Cargo workspace)
├── Cargo.toml                           # Rust workspace root
├── pnpm-workspace.yaml                  # Node packages
├── turbo.json                           # Turborepo build orchestration
├── .github/
│   └── workflows/
│       ├── ci.yml                       # Lint + test on PR
│       └── release.yml                  # Publish packages on tag
│
├── crates/                              # Rust crates (ZK core)
│   ├── core/                            # @zkpresence/core (was lib/)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs                   # Public API: derive_identity, compute_nullifier
│   │       ├── types.rs                 # AttestationData, PublicValues, Proof
│   │       ├── identity.rs              # SHA-256 identity + nullifier derivation
│   │       └── wasm.rs                  # WASM bindings (wasm-bindgen)
│   │
│   ├── circuit/                         # SP1 guest program (was program/)
│   │   ├── Cargo.toml
│   │   └── src/
│   │       └── main.rs                  # ZK circuit logic
│   │
│   └── prover/                          # SP1 host prover (was script/)
│       ├── Cargo.toml
│       ├── build.rs
│       └── src/
│           ├── lib.rs                   # Prove API (library, not just CLI)
│           └── bin/
│               ├── prove.rs             # CLI proof generator
│               └── vkey.rs              # Verification key export
│
├── packages/                            # TypeScript/Node packages
│   ├── sdk/                             # @zkpresence/sdk
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── src/
│   │       ├── index.ts                 # Main exports
│   │       ├── client.ts                # ZkPresenceClient class
│   │       ├── types.ts                 # TypeScript types (mirror Rust)
│   │       └── utils.ts                 # Helpers (hex encoding, etc.)
│   │
│   ├── adapter-evm/                     # @zkpresence/adapter-evm
│   │   ├── package.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── adapter.ts               # ChainAdapter implementation
│   │       ├── abi.ts                   # Contract ABI
│   │       └── chains.ts               # Base, Arbitrum, Ethereum configs
│   │
│   ├── adapter-solana/                  # @zkpresence/adapter-solana
│   │   ├── package.json
│   │   ├── programs/                    # Anchor program
│   │   └── src/
│   │       ├── index.ts
│   │       └── adapter.ts
│   │
│   ├── adapter-xmtp/                    # @zkpresence/adapter-xmtp
│   │   ├── package.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── adapter.ts
│   │       ├── frames.ts               # XMTP Frames for gated content
│   │       └── codec.ts                # Custom content type
│   │
│   ├── react-hooks/                     # @zkpresence/react
│   │   ├── package.json
│   │   └── src/
│   │       ├── index.ts
│   │       ├── provider.tsx             # <ZkPresenceProvider>
│   │       ├── useProveAttendance.ts
│   │       ├── useVerifyProof.ts
│   │       ├── useEventCreate.ts
│   │       ├── useProofStatus.ts
│   │       └── useAttendanceHistory.ts
│   │
│   └── server/                          # @zkpresence/server (managed service)
│       ├── package.json
│       ├── Dockerfile
│       └── src/
│           ├── index.ts                 # Fastify entrypoint
│           ├── routes/
│           │   ├── auth.ts
│           │   ├── events.ts
│           │   ├── proofs.ts
│           │   ├── chain.ts
│           │   ├── attestation.ts
│           │   └── usage.ts
│           ├── queue/
│           │   ├── proof-worker.ts      # BullMQ worker (calls Rust prover)
│           │   └── chain-submitter.ts   # On-chain submission worker
│           ├── ws/
│           │   └── proof-stream.ts      # WebSocket handler
│           ├── middleware/
│           │   ├── auth.ts              # API key + JWT validation
│           │   └── rate-limit.ts        # Tier-based rate limiting
│           └── db/
│               ├── migrations/
│               └── schema.ts            # Drizzle ORM schema
│
├── contracts/                           # Solidity contracts (Foundry)
│   ├── foundry.toml
│   ├── remappings.txt
│   ├── src/
│   │   └── ZkPresence.sol               # Existing contract
│   ├── test/
│   │   └── ZkPresence.t.sol
│   └── script/
│       └── Deploy.s.sol
│
├── docs/                                # @zkpresence/docs
│   ├── docusaurus.config.js             # Docusaurus site
│   ├── docs/
│   │   ├── getting-started.md
│   │   ├── core-concepts.md
│   │   ├── sdk-reference.md
│   │   ├── adapters/
│   │   │   ├── evm.md
│   │   │   ├── solana.md
│   │   │   └── xmtp.md
│   │   ├── service-api.md
│   │   ├── react-hooks.md
│   │   └── self-hosting.md
│   └── static/
│
├── examples/                            # Usage examples
│   ├── basic-attendance/                # Minimal end-to-end
│   ├── react-app/                       # React + hooks
│   ├── event-organizer/                 # Organizer dashboard
│   └── proof-gated-content/             # Content gating pattern
│
└── rust-toolchain                       # SP1 RISC-V toolchain
```

### Package Dependency Graph

```
@zkpresence/react ──────► @zkpresence/sdk
                                │
@zkpresence/adapter-evm ────────┤
@zkpresence/adapter-solana ─────┤
@zkpresence/adapter-xmtp ──────┤
                                │
                                ▼
                        @zkpresence/sdk
                                │
                                ▼
                      @zkpresence/server (internal, uses sdk + adapters)
                                │
                                ▼
                      crates/prover (Rust FFI or child process)
                                │
                                ▼
                      crates/core + crates/circuit (SP1)
```

### Build Commands

```bash
# Full build
turbo build

# Rust only (circuits + prover)
cargo build --workspace

# TypeScript only
turbo build --filter='./packages/*'

# Contracts only
cd contracts && forge build

# Run service locally
pnpm --filter @zkpresence/server dev

# Generate WASM bindings
cd crates/core && wasm-pack build --target web
```

---

## 5. Internal Project Integration

### Integration Architecture

```
┌───────────────────────────────────────────────────────────────────────┐
│                    MY3YE Ecosystem Projects                           │
│                                                                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────┐  │
│  │  ONEON  │  │ Tusita  │  │   SOS   │  │  Koink  │  │Otto Music│  │
│  │identity │  │community│  │governanc│  │  token  │  │  events  │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └────┬─────┘  │
│       │            │            │            │            │         │
│       ▼            ▼            ▼            ▼            ▼         │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              zkPresence as Shared Primitive                  │   │
│  │                                                              │   │
│  │  Identity Layer:  prove "I am member X" without revealing X  │   │
│  │  Access Layer:    gate content/features on proof possession  │   │
│  │  Reputation Layer: accumulate verifiable credentials          │   │
│  │  Governance Layer: vote with proven attendance weight         │   │
│  └──────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

### Per-Project Integration Details

#### ONEON (Identity + Social)

**Use case:** Privacy-preserving identity credentials.

```
zkPresence provides ONEON:
  1. ZK Credential Proofs
     - "I attended 10+ community events" → reputation score
     - "I am a verified member" → without revealing which group
     - Nullifier prevents double-counting across credential claims

  2. Proof-Gated Social Features
     - Channels gated by attendance proofs (via XMTP adapter)
     - DM permissions based on shared event attendance
     - Profile badges backed by ZK proofs (not self-reported)

  3. Progressive Identity
     - Tier 1 (custodial): proofs generated server-side via managed service
     - Tier 2 (semi-sovereign): proofs on user device, submitted via API
     - Tier 3 (sovereign): fully self-hosted, direct contract interaction

Integration points:
  - ONEON credentials module imports @zkpresence/sdk
  - XMTP messaging uses @zkpresence/adapter-xmtp for gating
  - W3C VC issuance references on-chain proof as evidence
```

#### Tusita (Community + Meditation)

**Use case:** Privacy-preserving attendance tracking for spiritual communities.

```
zkPresence provides Tusita:
  1. Session Attendance (existing design, now via SDK)
     - Geo mode: auto-detect proximity to meditation center
     - Sig mode: teacher signs each participant
     - Accumulated proofs → "30+ sessions" badge (no surveillance)

  2. Retreat Verification
     - Multi-day events with daily check-in proofs
     - Streak tracking via identity_commitment (stable across sessions)
     - Retreat completion certificates (W3C VC backed by zkPresence proofs)

  3. Community Governance
     - Attendance-weighted voting (more presence = more weight)
     - hasAttended() queries for eligibility checks
     - Privacy-first: can't see WHO voted, only THAT a qualified member did

Integration:
  - Tusita app imports @zkpresence/react for proof UI
  - Backend uses @zkpresence/sdk + adapter-evm for on-chain records
  - Governance module queries contract for attendance counts
```

#### SOS Systems (Governance + Integrity)

**Use case:** Proof of participation in governance and labor.

```
zkPresence provides SOS:
  1. Meeting Attendance Proofs
     - Prove participation in governance meetings
     - Quorum verification without revealing voter identity
     - Required for governance weight accrual

  2. Labor Presence Verification
     - Site attendance proofs for construction/physical work
     - Geo mode for jobsite proximity
     - Feeds into LaborAttestation contract

  3. Compliance Proofs
     - "I attended required safety training" without revealing who
     - Auditable without individual tracking

Integration:
  - SOS governance module imports @zkpresence/sdk
  - LaborAttestation contract calls ZkPresence.hasAttended()
  - GovernanceWeight contract gates on attendance proofs
```

#### Koink (Token Mechanics)

**Use case:** Proof-gated token distribution and airdrops.

```
zkPresence provides Koink:
  1. Attendance-Gated Airdrops
     - Token claims require proof of attendance at qualifying events
     - Nullifier prevents double-claiming across airdrop rounds
     - No identity linkage between claim and attendance

  2. DHM (Do-Have-Merit) Qualification
     - "Do" component verified via zkPresence attendance proofs
     - Accumulated attendance feeds DHM scoring
     - Privacy-preserving: DHM score visible, underlying data private

Integration:
  - Koink treasury contract queries ZkPresence.hasAttended()
  - DHM calculator imports attendance count via identity_commitment
  - Airdrop contract requires proof submission before claim
```

#### Otto Music (Events + Content)

**Use case:** Concert attendance → exclusive content unlock. (Already designed in existing ARCHITECTURE.md.)

```
Integration (unchanged, now uses SDK):
  - Otto Music dashboard: @zkpresence/react for event creation
  - Venue display: @zkpresence/sdk for QR generation
  - Fan app: @zkpresence/react for proof generation + submission
  - Backend: @zkpresence/adapter-evm for on-chain queries
```

### Shared Contract Extension

For internal projects that need cross-project attendance queries, extend the base contract:

```solidity
/// @title ZkPresenceRegistry — Cross-project attendance aggregation
/// @notice Deployed once per chain. Individual projects register their ZkPresence instances.
contract ZkPresenceRegistry {
    mapping(bytes32 => address) public projectContracts; // projectId => ZkPresence address
    
    /// Check attendance across multiple projects
    function hasAttendedAny(
        bytes32[] calldata projectIds,
        uint64[] calldata eventIds,
        bytes32 identityCommitment
    ) external view returns (bool) {
        for (uint i = 0; i < projectIds.length; i++) {
            address zkp = projectContracts[projectIds[i]];
            if (zkp != address(0) && IZkPresence(zkp).hasAttended(eventIds[i], identityCommitment)) {
                return true;
            }
        }
        return false;
    }
}
```

---

## 6. Pricing Tiers (Managed Service)

### Cost Structure

```
Prover compute cost (Succinct Network):
  - Groth16 proof generation: ~$0.01-0.05 per proof (depends on circuit size)
  - zkPresence circuit is small (~100K cycles) → ~$0.01/proof

On-chain submission cost (Base L2):
  - verifyAttendance(): ~230K gas × 0.01 gwei = ~$0.003/tx

Server infrastructure:
  - API server: minimal (Fastify, <512MB RAM)
  - Redis (BullMQ): minimal
  - PostgreSQL: shared with existing infra
  - Estimated: ~$50/month base
```

### Tier Definitions

```
┌────────────────┬──────────────┬──────────────┬──────────────┬──────────────────┐
│                │    Free      │   Builder    │     Pro      │   Enterprise     │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Price          │ $0/mo        │ $49/mo       │ $199/mo      │ Custom           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Proofs/month   │ 100          │ 2,000        │ 20,000       │ Unlimited        │
│ Overage rate   │ —            │ $0.05/proof  │ $0.03/proof  │ Volume discount  │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Rate limit     │ 5/min        │ 30/min       │ 120/min      │ Custom           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ On-chain       │ Self-submit  │ Managed      │ Managed      │ Managed + custom │
│ submission     │ only         │ (Base)       │ (multi-chain)│ chains           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Chains         │ Base         │ Base         │ Base, Arb,   │ Any EVM +        │
│                │              │              │ ETH          │ Solana           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Attestation    │ QR only      │ QR, Geo, Sig │ All modes    │ All + custom     │
│ modes          │              │              │              │                  │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ WebSocket      │ No           │ Yes          │ Yes          │ Yes              │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Webhooks       │ No           │ 1 endpoint   │ 5 endpoints  │ Unlimited        │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ React hooks    │ Yes          │ Yes          │ Yes          │ Yes              │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Support        │ Community    │ Email        │ Priority     │ Dedicated +      │
│                │              │ (48h)        │ email (4h)   │ Slack channel    │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ SLA            │ —            │ 99.5%        │ 99.9%        │ 99.95%           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Data retention │ 30 days      │ 90 days      │ 1 year       │ Custom           │
├────────────────┼──────────────┼──────────────┼──────────────┼──────────────────┤
│ Dashboard      │ Basic        │ Full         │ Full +       │ Full + custom    │
│                │              │              │ analytics    │ branding         │
└────────────────┴──────────────┴──────────────┴──────────────┴──────────────────┘
```

### Revenue Model

```
Conservative estimates (Year 1):

Free tier:        500 accounts × 0 = $0 (developer funnel)
Builder tier:     50 accounts × $49 = $2,450/mo
Pro tier:         10 accounts × $199 = $1,990/mo
Enterprise:       2 accounts × $999 = $1,998/mo

Base MRR:         ~$6,438/mo (~$77K ARR)
Overage revenue:  ~$1,000-3,000/mo (variable)

Costs:
  Succinct Network: ~$2,000/mo (at volume)
  Infrastructure:   ~$200/mo (existing VM + DB)
  Support:          ~$0 (Otto handles via automation)

Gross margin:      ~65-70%
```

### Internal Project Pricing

MY3YE ecosystem projects use the Pro tier equivalent at **$0 cost** — this is infrastructure we own. The managed service monetizes the same infra for external teams.

---

## Key Decisions

### 1. Monorepo with Turborepo + Cargo workspace

**Chosen:** Hybrid monorepo (pnpm workspace for TS, Cargo workspace for Rust)
**Reason:** Single repo for versioning, CI/CD, and cross-package testing. Turborepo handles TypeScript builds; Cargo handles Rust. Both live at the root.
**Alternative:** Separate repos per package — easier per-team ownership but harder cross-package changes and version coordination.

### 2. Fastify over Express for service layer

**Chosen:** Fastify
**Reason:** Native TypeScript, JSON schema validation built-in, WebSocket support via @fastify/websocket, 2x faster than Express. Small enough for our 4-vCPU constraint.
**Alternative:** Express (more ecosystem support but slower) or Hono (lighter but less mature WebSocket support).

### 3. BullMQ for proof queue over custom PostgreSQL queue

**Chosen:** BullMQ (Redis-backed)
**Reason:** Built-in retries, progress tracking, rate limiting, worker pools, and WebSocket-friendly events. Proof generation is CPU-bound and async — a job queue is the natural fit.
**Alternative:** PostgreSQL-based queue (like our existing task system) — works but lacks built-in progress events and worker pool management that BullMQ provides out of the box.

### 4. Rust FFI over child process for prover integration

**Chosen:** Child process (spawn Rust binary) for Phase 1, FFI (napi-rs) for Phase 2
**Reason:** Child process is simpler to implement and debug. SP1's prover is heavy and benefits from process isolation (OOM won't take down the Node server). FFI adds performance but complexity.
**Alternative:** Pure child process forever — acceptable if latency overhead (~50ms spawn) is fine.

### 5. Adapter trait over unified multi-chain client

**Chosen:** Per-chain adapter packages implementing a shared trait
**Reason:** Each chain has fundamentally different transaction models (EVM accounts vs Solana PDAs vs XMTP messages). A unified client would paper over these differences and make debugging harder.
**Alternative:** Single `@zkpresence/chain` package with chain-specific submodules — reduces package count but increases coupling.

### 6. Free tier at 100 proofs/month

**Chosen:** 100 proofs free
**Reason:** Enough for a developer to build and test a real integration (10 events × 10 attendees). Low enough to not drain prover compute. Standard developer funnel strategy.
**Alternative:** No free tier (reduces abuse) or 1000 free (more generous but compute cost adds up with many free accounts).

---

## Implementation Plan

### Phase 0: Monorepo Scaffold (1 day, ~$2)

1. Create pnpm-workspace.yaml + turbo.json at repo root
2. Move existing crates: `lib/ → crates/core/`, `program/ → crates/circuit/`, `script/ → crates/prover/`
3. Create empty TS packages: sdk, adapter-evm, react-hooks, server
4. Wire up Cargo workspace + pnpm workspace to build together
5. Verify `turbo build` and `cargo build --workspace` both pass

### Phase 1: Core SDK + EVM Adapter (3 days, ~$5)

6. Clean up crates/core: export `derive_identity`, `compute_nullifier`, `build_attestation` as public API
7. Fix SP1 precompile TODOs in crates/circuit (sha256 + ecdsa_verify)
8. Make crates/prover a library with a public `prove()` function (not just CLI)
9. Build @zkpresence/sdk: TypeScript client wrapping REST API calls
10. Build @zkpresence/adapter-evm: viem-based ChainAdapter with ZkPresence.sol ABI
11. Write Foundry tests for ZkPresence.sol

### Phase 2: Service Layer (3 days, ~$6)

12. Scaffold @zkpresence/server with Fastify + TypeScript
13. Implement auth routes (API key registration, validation)
14. Implement proof routes (generate → queue → worker → complete)
15. Implement event routes (CRUD, mirrors on-chain events)
16. Set up BullMQ proof queue + worker (calls Rust prover binary)
17. Add WebSocket proof streaming
18. Add rate limiting middleware (tier-based)
19. PostgreSQL migrations for zkp_api_keys, zkp_events, zkp_proofs, zkp_usage

### Phase 3: React Hooks + Docs (2 days, ~$3)

20. Build @zkpresence/react: Provider + 5 hooks
21. Create example React app (basic attendance flow)
22. Set up Docusaurus docs site
23. Write getting-started, SDK reference, adapter guides

### Phase 4: Additional Adapters (2 days per adapter, ~$4 each)

24. @zkpresence/adapter-solana: Anchor program + TypeScript adapter
25. @zkpresence/adapter-xmtp: Frames integration + content codec

### Phase 5: Internal Integration (1 day per project, ~$2 each)

26. ONEON: Wire credential module to @zkpresence/sdk
27. Tusita: Wire attendance tracking to @zkpresence/react
28. SOS: Wire governance eligibility to hasAttended() queries
29. Koink: Wire airdrop gating to nullifier checks

### Total Estimate

| Phase | Time | Cost |
|-------|------|------|
| Phase 0: Scaffold | 1 day | ~$2 |
| Phase 1: Core + EVM | 3 days | ~$5 |
| Phase 2: Service | 3 days | ~$6 |
| Phase 3: React + Docs | 2 days | ~$3 |
| Phase 4: Adapters | 4 days | ~$8 |
| Phase 5: Integrations | 4 days | ~$8 |
| **Total** | **17 days** | **~$32** |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **SP1 precompile API changes** | Circuit breaks on SP1 version bump | Pin SP1 version in rust-toolchain, test on each update |
| **Succinct Network pricing** | Proof costs exceed pricing tiers | Monitor cost per proof, adjust tiers quarterly, offer self-hosted prover as escape hatch |
| **Low external demand** | Revenue doesn't materialize | Free tier as developer funnel, internal use provides baseline value regardless |
| **WASM prover limitations** | Can't run full prover in browser | Browser only gets identity/nullifier computation; proof gen stays server-side |
| **Multi-chain complexity** | Each adapter is a maintenance burden | Ship EVM first, add others only when demand exists. Adapter trait keeps coupling low |
| **Proof generation latency** | Users wait too long for proofs | Succinct Network targets <60s for small circuits. WebSocket streaming keeps UX responsive |
| **Secret management in API** | User secrets transit through service | TLS encryption in transit. Long-term: client-side proving (WASM identity + server proof) so secret never leaves device |

---

## Appendix A: React Hook API

```tsx
import { ZkPresenceProvider, useProveAttendance, useProofStatus } from '@zkpresence/react';

function App() {
  return (
    <ZkPresenceProvider
      apiKey="zpk_..."
      apiUrl="https://api.zkpresence.xyz"
      chain="evm:8453"
    >
      <AttendanceButton eventId={42n} />
    </ZkPresenceProvider>
  );
}

function AttendanceButton({ eventId }: { eventId: bigint }) {
  const { prove, proofId, status, error } = useProveAttendance();
  const { progress } = useProofStatus(proofId);

  const handleProve = async () => {
    // userSecret should come from secure local storage
    const secret = await getSecretFromKeychain();
    await prove({
      userSecret: secret,
      attestation: { mode: 'qr', qrPayload: scannedQrData },
      eventId,
      submitOnChain: true,
    });
  };

  return (
    <div>
      <button onClick={handleProve} disabled={status === 'proving'}>
        {status === 'idle' && 'Prove Attendance'}
        {status === 'proving' && `Generating proof... ${Math.round(progress * 100)}%`}
        {status === 'complete' && 'Attendance Verified!'}
        {status === 'failed' && 'Failed — Retry'}
      </button>
      {error && <p className="text-red-500">{error.message}</p>}
    </div>
  );
}
```

## Appendix B: SDK Usage Examples

### Server-Side (Node.js)

```typescript
import { ZkPresenceClient } from '@zkpresence/sdk';
import { EvmAdapter } from '@zkpresence/adapter-evm';

const client = new ZkPresenceClient({
  apiKey: 'zpk_live_...',
  adapter: new EvmAdapter({
    chain: 'base',
    rpcUrl: process.env.BASE_RPC_URL,
    contractAddress: '0x...',
  }),
});

// Create event
const event = await client.createEvent({
  startTime: new Date('2026-05-01T19:00:00Z'),
  endTime: new Date('2026-05-01T23:00:00Z'),
  locationHash: '0x...',
  organizerPubkeyHash: '0x...',
});

// Generate QR attestation for the event
const qrPayload = await client.generateQrAttestation(event.id);

// Generate proof (async — returns proof ID)
const { proofId } = await client.proveAttendance({
  userSecret: Buffer.from('...', 'hex'),
  attestation: { mode: 'qr', payload: qrPayload },
});

// Poll for completion
const proof = await client.waitForProof(proofId);

// Submit on-chain
const tx = await client.submitProof(proof);
console.log(`Verified on-chain: ${tx.hash}`);
```

### Self-Hosted (Direct Contract)

```typescript
import { EvmAdapter } from '@zkpresence/adapter-evm';

const adapter = new EvmAdapter({
  chain: 'base',
  rpcUrl: 'https://mainnet.base.org',
  contractAddress: '0x...',
  walletClient, // viem wallet client
});

// Direct contract interaction (no managed service)
const attended = await adapter.hasAttended(42n, '0x...');
const tx = await adapter.submitProof(proofBytes, publicValuesBytes);
```

## Appendix C: Self-Hosting Guide (Enterprise)

```bash
# Clone and build
git clone https://github.com/my3ye/zkpresence.git
cd zkpresence

# Build Rust crates (requires SP1 toolchain)
sp1up && cargo build --workspace --release

# Build TypeScript packages
pnpm install && turbo build

# Configure
cp packages/server/.env.example packages/server/.env
# Edit: DATABASE_URL, REDIS_URL, SP1_PROVER, SP1_PRIVATE_KEY

# Run migrations
pnpm --filter @zkpresence/server migrate

# Start service
pnpm --filter @zkpresence/server start

# Or via Docker
docker compose up -d
```

Self-hosted deployments use the same codebase. The only difference is the prover backend:
- `SP1_PROVER=local` — CPU proving on your hardware (slow but free)
- `SP1_PROVER=network` — Succinct Prover Network (fast, pay per proof)

# Dynamic Public Key System — Architecture
*Architect assessment — 2026-04-12*

---

## Design: Dynamic Public Key System (Derivation, Rotation & On-Chain Verification)

### Problem

zkPresence's current identity model is brittle: `identity_commitment = SHA256(user_secret)` where `user_secret` is a random 32-byte value. Lose it, identity gone. Compromise it, identity stolen. No rotation, no recovery, no binding to the person behind it.

The broader ecosystem (ONEON, SOS, Koink) needs a stable on-chain identity derived from **who you are** (biometric) and **what you know** (passphrase), with signing keys that rotate without changing the on-chain identity.

Research (2026-04-12, validated 7.5/10) confirms the **zkLogin pattern** is the correct architecture: stable address derived from identity inputs, ephemeral signing keys certified by ZK proof. Three independent sources: Sui CCS 2024, BioZero arXiv 2024, zkAt IACR 2025.

### What Exists

| Component | State | Files |
|---|---|---|
| Identity derivation | `SHA256(user_secret)` — raw secret, no KDF | `crates/core/src/identity.rs` |
| Nullifier | `SHA256(secret ‖ event_id)` — working | `crates/core/src/identity.rs` |
| SP1 circuit | SHA-256 and ECDSA both `todo!()` — non-functional | `crates/circuit/src/main.rs` |
| On-chain contract | Groth16 verifier, nullifier registry, no key management | `contracts/src/ZkPresence.sol` |
| Biometric/KDF | Zero code — grep-verified clean slate | — |
| ONEON identity | ERC-4337 smart accounts + session keys (separate system) | Memory API routes |

---

### Approach: Three-Layer Key Architecture

The system separates **identity** (who you are, stable) from **authority** (what you can do, rotatable) from **action** (individual proofs, ephemeral).

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: ACTION                                                 │
│ Attendance proofs, governance votes, credential claims          │
│ Per-action ZK proof binds action to authority                   │
│ One-time use: nullifier prevents replay                         │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 2: AUTHORITY (rotatable)                                  │
│ Ephemeral secp256k1 key pair — epoch-bounded                   │
│ ZK proof certifies: this key belongs to this identity          │
│ Rotation = new key pair + new binding proof                     │
│ Old keys expire by epoch, no on-chain revocation needed         │
├─────────────────────────────────────────────────────────────────┤
│ LAYER 1: IDENTITY (stable, on-chain)                           │
│ identity_commitment = SHA256(master_secret)                     │
│ master_secret = HKDF-SHA256(bio_key ‖ pass_key)               │
│ bio_key = FuzzyExtract(iris, helper)  [device-side]            │
│ pass_key = Argon2id(passphrase, salt) [device-side]            │
│ Never changes. Survives key rotation and device migration.      │
└─────────────────────────────────────────────────────────────────┘
```

---

### Key Decisions

**Decision 1: Argon2 Path B (commitment-based, not in-circuit)**
Chosen: Path B — prove knowledge of Argon2 output, not Argon2 computation.
Because: Argon2 is memory-hard by design (~64MB). Proving it inside a ZK circuit would require millions of constraints — economically prohibitive. Path B: user computes Argon2 on their device, circuit proves `SHA256(pass_key) == stored_commitment`.
Alternative: Path A (full Argon2 in-circuit) — rejected as infeasible. Same approach zkLogin uses: credential issuance is trusted to the provider (here, user's device), circuit only proves knowledge.
**Implication:** If a user's device is compromised while computing Argon2, the pass_key is exposed. Mitigation: biometric factor provides a second layer — attacker needs both.

**Decision 2: Epoch-based key expiry (not on-chain revocation)**
Chosen: Ephemeral keys are bound to an epoch range `[epoch, max_epoch]` in the ZK proof.
Because: On-chain revocation requires state writes and introduces revocation-check gas costs on every verification. Epoch-based expiry is stateless — the contract just checks `current_epoch >= epoch && current_epoch <= max_epoch`. No storage, no revocation list.
Alternative: On-chain key registry — rejected for gas cost and complexity. Epoch window is configurable (default: 24h).
**Implication:** A compromised key remains valid until its epoch expires. Acceptable: max window is bounded, and the key can only act within the identity's scope.

**Decision 3: Separate Key Binding circuit from Attendance circuit**
Chosen: Two circuit programs — `KeyBinding` (identity → ephemeral key) and `Attendance` (existing, extended).
Because: Composability. KeyBinding proofs are reusable across all ecosystem services (ONEON, SOS, Koink), not just attendance. The Attendance circuit can reference a KeyBinding proof or accept direct identity proof (backward-compatible).
Alternative: Single monolithic circuit — rejected for reusability and compile-time reasons.
**Implication:** Two SP1 program verification keys on-chain. Slightly more complex deployment but vastly more composable.

**Decision 4: Fuzzy extractor stays device-side**
Chosen: Biometric feature extraction and fuzzy extraction happen entirely on the user's device. Only the bio_key (32 bytes, output of FuzzyExtract) enters the ZK circuit.
Because: Raw biometric data (iris scan) is privacy-critical and legally sensitive (GDPR Art. 9). Sending it to a prover — even a ZK prover — is unnecessary. The device extracts the stable key; the circuit proves knowledge of it.
Alternative: In-circuit fuzzy extraction — rejected for privacy, circuit size, and regulatory reasons.
**Implication:** Device-side extraction means different devices may extract slightly different features. The fuzzy extractor's error-correction (Reed-Solomon) handles this — that's its purpose. But cross-device compatibility depends on consistent feature extraction, which is a client SDK concern.

**Decision 5: HKDF for key combination (not concatenation or XOR)**
Chosen: `master_secret = HKDF-SHA256(ikm=bio_key‖pass_key, salt=user_salt, info="zkpresence-master-v1")`.
Because: HKDF is the standard key derivation function for combining keying material (RFC 5869). It produces uniform output even from non-uniform inputs. Concatenation leaks structure; XOR is fragile if one input has low entropy.
Alternative: Simple SHA256(bio_key ‖ pass_key) — would work but doesn't provide domain separation or structured extraction.

**Decision 6: Groth16 for Phase 1-2, PLONK deferred to Phase 3**
Chosen: Stay on Groth16 (SP1 default) through Phase 2.
Because: Key rotation doesn't actually require circuit changes per-rotation — only the KeyBinding circuit needs to be compiled once. PLONK's universal setup advantage (no re-ceremony when circuit changes) matters only if we're iterating the circuit frequently. Phase 1-2 stabilizes the circuit; Phase 3 migrates when the circuit is mature.
Alternative: Migrate to PLONK immediately — rejected to avoid blocking on new verifier contract deployment.
**Implication:** If the circuit needs changes during Phase 2, Groth16 requires a new trusted setup ceremony. Acceptable risk: SP1's proving network handles this transparently.

---

### Architecture Detail

#### 1. Key Derivation (Device-Side)

```
Device holds: iris_raw (biometric scan), passphrase (user input), salt (stored in helper data)

Step 1: bio_key = FuzzyExtract(iris_raw, helper_string)
        ↓ 32 bytes, 105-bit effective entropy (CCS 2025)
        ↓ helper_string stored locally, not secret

Step 2: pass_key = Argon2id(passphrase, salt, t=3, m=65536, p=4)
        ↓ 32 bytes
        ↓ salt stored locally, not secret

Step 3: master_secret = HKDF-SHA256(
            ikm  = bio_key ‖ pass_key,   // 64 bytes
            salt = user_salt,              // 32 bytes, stored locally
            info = "zkpresence-master-v1"  // domain separation
        )
        ↓ 32 bytes — this IS the user's identity seed

Step 4: identity_commitment = SHA256(master_secret)
        ↓ 32 bytes — this goes on-chain, never changes
```

**Backward compatibility:** Phase 1 users who registered with raw `user_secret` have `identity_commitment = SHA256(user_secret)`. Their `user_secret` IS their master_secret. No migration needed — the circuit accepts either path.

#### 2. Key Binding (ZK Circuit: `zkpresence-keybind`)

A new SP1 program that proves an ephemeral key belongs to a stable identity.

```
PRIVATE INPUTS:
  master_secret   : [u8; 32]   // derived from bio+pass (device-side)

PUBLIC INPUTS:
  eph_pk          : [u8; 33]   // ephemeral compressed secp256k1 pubkey
  epoch           : u64        // current epoch
  max_epoch       : u64        // key expiry epoch

PUBLIC OUTPUTS (ABI-encoded):
  identity_commitment : bytes32   // SHA256(master_secret)
  eph_pk_hash         : bytes32   // SHA256(eph_pk)
  epoch               : uint64
  max_epoch           : uint64
  key_nonce           : bytes32   // SHA256(master_secret ‖ eph_pk ‖ epoch) — prevents proof replay

CIRCUIT LOGIC:
  1. identity_commitment = SHA256(master_secret)
  2. eph_pk_hash = SHA256(eph_pk)
  3. key_nonce = SHA256(master_secret ‖ eph_pk ‖ epoch.to_le_bytes())
  4. Assert max_epoch > epoch
  5. Assert max_epoch - epoch <= MAX_EPOCH_WINDOW (e.g., 30 — ~30 days at 1 epoch/day)
  6. Commit all public outputs (ABI-encoded)
```

**What this proves:** "I know a secret whose hash is `identity_commitment`, and I'm binding ephemeral key `eph_pk_hash` to it for epochs `[epoch, max_epoch]`."

**What this does NOT prove:** Biometric or passphrase details — those are consumed in the device-side derivation of `master_secret`. The circuit only sees the derived secret.

#### 3. Attendance Circuit Extension (existing `zkpresence`)

The existing attendance circuit gains an optional ephemeral key authentication mode:

```
EXTENDED PRIVATE INPUTS (in addition to existing):
  auth_mode       : u8         // 0 = direct (existing), 1 = ephemeral key
  // If auth_mode == 1:
  eph_sk          : [u8; 32]   // ephemeral secret key (signs attendance claim)
  keybind_proof   : bytes      // (future: recursive proof verification)

// For Phase 2 (non-recursive), auth_mode == 0 only.
// Ephemeral key auth via on-chain signature verification, not in-circuit.
```

**Phase 2 approach (pragmatic):** The attendance proof still uses direct `master_secret` to derive `identity_commitment`. Ephemeral key authentication happens on-chain: user signs the attendance proof submission tx with their ephemeral key, and the contract verifies the key is registered for that identity.

**Phase 3 approach (recursive):** The attendance circuit verifies the KeyBinding proof recursively inside itself — fully trustless, no on-chain key registry needed. Deferred: SP1 recursive proof composition is complex and gas-expensive.

#### 4. On-Chain Contracts

##### 4a. `DynamicKeyRegistry.sol` (new contract)

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ISP1Verifier} from "@sp1-contracts/ISP1Verifier.sol";

contract DynamicKeyRegistry {
    ISP1Verifier public immutable verifier;
    bytes32 public immutable keybindVKey;  // KeyBinding program vkey
    
    uint64 public currentEpoch;
    uint64 public constant EPOCH_DURATION = 1 days;
    uint64 public epochStart;
    
    // identity_commitment => eph_pk_hash => max_epoch
    mapping(bytes32 => mapping(bytes32 => uint64)) public keyExpiry;
    // Prevent proof replay
    mapping(bytes32 => bool) public keyNonceUsed;
    
    event KeyRegistered(
        bytes32 indexed identityCommitment,
        bytes32 indexed ephPkHash,
        uint64 epoch,
        uint64 maxEpoch
    );
    
    event EpochAdvanced(uint64 newEpoch);
    
    constructor(address _verifier, bytes32 _keybindVKey) {
        verifier = ISP1Verifier(_verifier);
        keybindVKey = _keybindVKey;
        epochStart = uint64(block.timestamp);
        currentEpoch = 0;
    }
    
    /// @notice Advance epoch if enough time has passed.
    function advanceEpoch() public {
        uint64 elapsed = uint64(block.timestamp) - epochStart;
        uint64 newEpoch = elapsed / EPOCH_DURATION;
        if (newEpoch > currentEpoch) {
            currentEpoch = newEpoch;
            emit EpochAdvanced(newEpoch);
        }
    }
    
    /// @notice Register an ephemeral key via ZK proof.
    function registerKey(
        bytes calldata proof,
        bytes calldata publicValues
    ) external {
        advanceEpoch();
        
        // Verify ZK proof
        verifier.verifyProof(keybindVKey, publicValues, proof);
        
        // Decode public values
        (
            bytes32 identityCommitment,
            bytes32 ephPkHash,
            uint64 epoch,
            uint64 maxEpoch,
            bytes32 keyNonce
        ) = abi.decode(publicValues, (bytes32, bytes32, uint64, uint64, bytes32));
        
        // Validate epoch
        require(epoch <= currentEpoch, "future epoch");
        require(maxEpoch >= currentEpoch, "already expired");
        require(!keyNonceUsed[keyNonce], "nonce reused");
        
        // Register
        keyExpiry[identityCommitment][ephPkHash] = maxEpoch;
        keyNonceUsed[keyNonce] = true;
        
        emit KeyRegistered(identityCommitment, ephPkHash, epoch, maxEpoch);
    }
    
    /// @notice Check if an ephemeral key is currently valid for an identity.
    function isKeyValid(
        bytes32 identityCommitment,
        bytes32 ephPkHash
    ) external view returns (bool) {
        uint64 expiry = keyExpiry[identityCommitment][ephPkHash];
        if (expiry == 0) return false;
        uint64 elapsed = uint64(block.timestamp) - epochStart;
        uint64 epoch = elapsed / EPOCH_DURATION;
        return epoch <= expiry;
    }
}
```

##### 4b. ZkPresence.sol Extension

The existing `ZkPresence.sol` gains an optional integration with `DynamicKeyRegistry`:

```solidity
// New state variable:
DynamicKeyRegistry public keyRegistry;  // optional, address(0) if not set

// New function: verify attendance via ephemeral key signature
function verifyAttendanceWithKey(
    bytes calldata proof,
    bytes calldata publicValues,
    bytes calldata ephSignature,     // ECDSA sig from ephemeral key
    bytes32 ephPkHash                // hash of signing key
) external {
    // 1. Verify SP1 attendance proof (same as existing)
    verifier.verifyProof(programVKey, publicValues, proof);
    
    // 2. Decode public values (same as existing)
    (uint64 eventId, bytes32 nullifier, bytes32 identityCommitment,
     uint8 attestationMode, uint64 timestamp, bytes32 organizerPubkeyHash
    ) = abi.decode(publicValues, (uint64, bytes32, bytes32, uint8, uint64, bytes32));
    
    // 3. If key registry is set, verify the ephemeral key
    if (address(keyRegistry) != address(0)) {
        require(keyRegistry.isKeyValid(identityCommitment, ephPkHash), "invalid key");
        // Verify signature: ephemeral key signed keccak256(proof ‖ publicValues)
        // ... ECDSA.recover logic
    }
    
    // 4. Same validation as verifyAttendance (event active, nullifier, etc.)
    // ... existing logic
}
```

**Note:** `verifyAttendance()` remains unchanged — direct proof submission continues to work for users who don't use dynamic keys.

---

### Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  USER DEVICE │     │  SP1 PROVER  │     │   BASE L2    │
│              │     │  (Succinct)  │     │              │
│ iris scan ───┼────→│              │     │              │
│ passphrase ──┼─┐   │              │     │              │
│              │ │   │              │     │              │
│ FuzzyExtract │ │   │              │     │              │
│ Argon2id     │ │   │              │     │              │
│ HKDF         │ │   │              │     │              │
│   ↓          │ │   │              │     │              │
│ master_secret│ │   │              │     │              │
│   ↓          │ │   │              │     │              │
│ gen eph_pk ──┼─┼──→│ KeyBinding   │     │              │
│              │ │   │ circuit      │     │              │
│              │ │   │   ↓          │     │              │
│              │ │   │ proof ───────┼────→│ DynamicKey   │
│              │ │   │              │     │ Registry     │
│              │ │   │              │     │  .registerKey│
│              │ │   │              │     │              │
│ attend event │ │   │              │     │              │
│ scan QR ─────┼─┼──→│ Attendance   │     │              │
│              │ │   │ circuit      │     │              │
│              │ │   │   ↓          │     │              │
│ sign w/ eph ─┼─┼──→│ proof ───────┼────→│ ZkPresence   │
│              │ │   │              │     │ .verifyAtt.. │
└──────────────┘ │   └──────────────┘     └──────────────┘
                 │
                 └─ pass_key computed locally, never transmitted
```

---

### File Changes

#### New Files

| File | Purpose | LOC est. |
|---|---|---|
| `crates/core/src/keys.rs` | Key derivation functions (HKDF, bio+pass combination, ephemeral key gen) | ~120 |
| `crates/core/src/epochs.rs` | Epoch calculation helpers | ~30 |
| `crates/keybind/src/main.rs` | KeyBinding SP1 guest program | ~80 |
| `crates/keybind/Cargo.toml` | KeyBinding crate config | ~20 |
| `contracts/src/DynamicKeyRegistry.sol` | On-chain key registry | ~100 |
| `contracts/test/DynamicKeyRegistry.t.sol` | Foundry tests | ~150 |
| `packages/sdk/src/keys.ts` | TypeScript key derivation + ephemeral key management | ~200 |

#### Modified Files

| File | Change | Impact |
|---|---|---|
| `crates/core/src/lib.rs` | Export `keys` and `epochs` modules | Minimal |
| `crates/core/src/types.rs` | Add `KeyBindingPublicValues` struct | ~15 lines |
| `crates/core/Cargo.toml` | Add `hkdf` dependency | 1 line |
| `crates/circuit/src/main.rs` | Wire SHA-256 (prerequisite) — replace `todo!()` | ~5 lines changed |
| `contracts/src/ZkPresence.sol` | Add optional `keyRegistry` reference + `verifyAttendanceWithKey()` | ~40 lines |
| `contracts/test/ZkPresence.t.sol` | Tests for ephemeral key attendance | ~60 lines |

#### NOT Changed (preserved)

| File | Reason |
|---|---|
| `crates/core/src/identity.rs` | Backward compatible — existing derivation unchanged |
| Existing AttestationData variants | No modification — new auth mode is additive |

---

### Implementation Plan

#### Phase 1: Foundation (prerequisite — blocks everything)
**Goal:** Make the circuit functional.

1. **Wire SHA-256 precompile** in `crates/circuit/src/main.rs:22-27`
   - Replace `todo!()` with `sha2::Sha256` (SP1 patches the syscall automatically)
   - No special precompile wiring needed — just use the `sha2` crate
   
2. **Wire ECDSA secp256k1** in `crates/circuit/src/main.rs:68-70,102-104,119-121`
   - Use `k256` crate with `sp1-lib/secp256k1` feature
   - SP1 accelerates via syscall

3. **Add unit tests** for identity derivation in-circuit
4. **Test end-to-end** with SP1 local prover

**Estimated cost:** ~$3-4 | **Duration:** 1 task

#### Phase 2a: Key Derivation Module
**Goal:** Implement the key derivation stack (device-side).

1. **Create `crates/core/src/keys.rs`:**
   ```rust
   pub struct MasterKeyInputs {
       pub bio_key: [u8; 32],      // output of FuzzyExtract
       pub pass_key: [u8; 32],     // output of Argon2id
       pub salt: [u8; 32],         // user-specific salt
   }
   
   pub fn derive_master_secret(inputs: &MasterKeyInputs) -> [u8; 32]
   pub fn derive_identity_commitment(master_secret: &[u8; 32]) -> [u8; 32]
   pub fn generate_ephemeral_keypair() -> (EphemeralSecretKey, EphemeralPublicKey)
   ```

2. **Add HKDF dependency** to core crate
3. **Unit tests** for deterministic derivation, cross-input uniqueness

**Estimated cost:** ~$1-2 | **Duration:** 1 task

#### Phase 2b: KeyBinding Circuit
**Goal:** ZK proof that binds ephemeral key to identity.

1. **Create `crates/keybind/` SP1 guest program**
2. **Define `KeyBindingPublicValues`** in core types
3. **Implement circuit logic** (SHA256 identity, bind eph_pk, epoch bounds)
4. **Test with SP1 local prover**

**Estimated cost:** ~$2-3 | **Duration:** 1 task

#### Phase 2c: On-Chain Key Registry
**Goal:** Contracts that accept key binding proofs.

1. **Create `DynamicKeyRegistry.sol`** — epoch system, key registration, validity check
2. **Extend `ZkPresence.sol`** — optional key registry integration, `verifyAttendanceWithKey()`
3. **Foundry tests** — register key, verify attendance with key, test epoch expiry, test replay protection
4. **Deploy to Base Sepolia** for testing

**Estimated cost:** ~$3-4 | **Duration:** 1 task

#### Phase 2d: TypeScript SDK
**Goal:** Client SDK for key derivation and management.

1. **`packages/sdk/src/keys.ts`** — key derivation, ephemeral key management, proof request helpers
2. **Integration with Succinct prover API** for proof generation
3. **Example: register key → attend event → verify**

**Estimated cost:** ~$2-3 | **Duration:** 1 task

#### Phase 3: Future (deferred)
- PLONK migration (when circuit stabilizes)
- Recursive proof composition (KeyBinding verified inside Attendance circuit)
- Iris fuzzy extractor SDK (when CCS 2025 reference implementation available)
- PQ migration (ML-DSA for key binding signatures — see SOS PQ Framework)

---

### API / Interface

#### Key Derivation (client-side, TypeScript SDK)

```typescript
// packages/sdk/src/keys.ts

interface MasterKeyInputs {
  bioKey: Uint8Array;      // 32 bytes from FuzzyExtract
  passKey: Uint8Array;     // 32 bytes from Argon2id
  salt: Uint8Array;        // 32 bytes, stored in local helper data
}

// Derive stable identity
function deriveMasterSecret(inputs: MasterKeyInputs): Uint8Array;
function deriveIdentityCommitment(masterSecret: Uint8Array): Uint8Array;

// Ephemeral key management
function generateEphemeralKey(): { publicKey: Uint8Array; secretKey: Uint8Array };
function requestKeyBindingProof(
  masterSecret: Uint8Array,
  ephPublicKey: Uint8Array,
  epoch: bigint,
  maxEpoch: bigint
): Promise<{ proof: Uint8Array; publicValues: Uint8Array }>;

// Legacy compatibility
function fromRawSecret(userSecret: Uint8Array): MasterKeyInputs;
```

#### On-Chain (Solidity)

```
DynamicKeyRegistry:
  registerKey(proof, publicValues)              → registers ephemeral key
  isKeyValid(identityCommitment, ephPkHash)     → bool
  advanceEpoch()                                → updates current epoch
  currentEpoch()                                → uint64
  keyExpiry(identity, ephPkHash)                → uint64

ZkPresence (extended):
  verifyAttendanceWithKey(proof, publicValues, ephSignature, ephPkHash)
  setKeyRegistry(address registry)              → onlyOwner
```

---

### Risks

| Risk | Impact | Mitigation |
|---|---|---|
| SP1 SHA-256/ECDSA precompile issues | Blocks everything | P0 priority; use `sha2` + `k256` crates (battle-tested), SP1 patches syscalls automatically |
| Fuzzy extractor cross-device variance | Identity mismatch across devices | Error-correction (Reed-Solomon) handles this; SDK standardizes feature extraction |
| Argon2 device-trust assumption | Compromised device exposes pass_key | Biometric second factor; key binding epoch-limited; recovery flow via new bio+pass |
| Epoch window too large → prolonged key compromise | Attacker uses stolen key for days | Default 24h epochs; MAX_EPOCH_WINDOW=30; users can shrink window |
| Two SP1 programs = two trusted setups | Deployment complexity | SP1's Succinct Network handles ceremonies; Groth16 setup is per-program, cached |
| Gas cost of key registration | Friction for users | Base L2 gas is <$0.01; KeyBinding registration is one-time per epoch |
| Circuit change during Phase 2 requires new Groth16 setup | Development delay | Accept: SP1 handles this. Migrate to PLONK in Phase 3 if iteration frequency warrants it |

---

### Backward Compatibility

The system is fully backward-compatible:

1. **Existing users** with raw `user_secret` → their `user_secret` IS their master_secret. `SHA256(user_secret)` continues to produce the same `identity_commitment`. No migration needed.

2. **Existing `verifyAttendance()`** → unchanged. Direct proof submission works exactly as before.

3. **New users** who derive identity from bio+pass → same circuit, different derivation path on the device side. The circuit only sees `master_secret` either way.

4. **Gradual adoption:** `DynamicKeyRegistry` is optional. `ZkPresence.sol` works without it. The `verifyAttendanceWithKey()` function is additive.

---

### Cost Summary

| Phase | Estimated | Dependency |
|---|---|---|
| Phase 1 (SHA-256 + ECDSA wiring) | ~$3-4 | None (P0) |
| Phase 2a (Key derivation module) | ~$1-2 | Phase 1 |
| Phase 2b (KeyBinding circuit) | ~$2-3 | Phase 2a |
| Phase 2c (On-chain contracts) | ~$3-4 | Phase 2b |
| Phase 2d (TypeScript SDK) | ~$2-3 | Phase 2a + 2c |
| **Total Phase 1-2** | **~$11-16** | |
| Phase 3 (PLONK + recursive + PQ) | ~$8-12 | Phase 2 stable |

---

### Ecosystem Integration Points

| System | How It Uses Dynamic Keys |
|---|---|
| **zkPresence** | Attendance proofs with optional ephemeral key auth |
| **ONEON** | Identity commitment as DID anchor; ephemeral keys for session signing (replaces ERC-4337 session keys for sovereign tier) |
| **SOS** | DPC weight bound to identity_commitment; key rotation doesn't affect reputation |
| **Koink** | Treasury claims authenticated via ephemeral key signatures |
| **Music/Tusita** | Credential issuance bound to stable identity |

The `DynamicKeyRegistry` is a shared primitive — one deployment serves all ecosystem contracts that need to verify identity-bound signatures.

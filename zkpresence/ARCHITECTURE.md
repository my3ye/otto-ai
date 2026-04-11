# zkPresence Architecture

Zero-Knowledge Proof of Attendance using Succinct SP1 zkVM.

**Target chain:** Base (Ethereum L2)
**Proof system:** SP1 Hypercube v6.x (Groth16 for on-chain, STARK for off-chain)
**Privacy guarantee:** No identity leakage on-chain. Only nullifiers and event IDs are public.

---

## System Overview

```
                          ┌─────────────────────────────────────┐
                          │           EVENT ORGANIZER           │
                          │  Creates event on-chain + issues    │
                          │  attestation material (QR/geo/sig)  │
                          └──────────────┬──────────────────────┘
                                         │
                          ┌──────────────▼──────────────────────┐
                          │         ATTESTATION LAYER           │
                          │  Mode A: QR code scan               │
                          │  Mode B: Geohash proximity          │
                          │  Mode C: Organizer direct signature │
                          └──────────────┬──────────────────────┘
                                         │ attestation_payload
                                         │ (private to user)
                    ┌────────────────────▼─────────────────────┐
                    │              USER DEVICE                  │
                    │                                           │
                    │  user_secret (stored locally, never sent) │
                    │  attestation_payload (from organizer)     │
                    │                                           │
                    │  ┌─────────────────────────────────┐     │
                    │  │         SP1 PROVER               │     │
                    │  │                                   │     │
                    │  │  Private inputs:                  │     │
                    │  │    - user_secret                  │     │
                    │  │    - attestation_payload          │     │
                    │  │                                   │     │
                    │  │  Computes inside zkVM:            │     │
                    │  │    identity = H(user_secret)      │     │
                    │  │    nullifier = H(secret‖event_id) │     │
                    │  │    verify attestation             │     │
                    │  │                                   │     │
                    │  │  Public outputs (committed):      │     │
                    │  │    - nullifier                    │     │
                    │  │    - event_id                     │     │
                    │  │    - identity_commitment          │     │
                    │  │    - attestation_mode             │     │
                    │  │    - timestamp                    │     │
                    │  └────────────────┬──────────────────┘     │
                    └───────────────────┼───────────────────────┘
                                        │ groth16 proof + public values
                                        │
                    ┌───────────────────▼───────────────────────┐
                    │          BASE L2 (ON-CHAIN)               │
                    │                                           │
                    │  ZkPresence.sol                           │
                    │    ├─ verifyAttendance(proof, pubValues)  │
                    │    ├─ nullifiers[hash] => used            │
                    │    ├─ events[id] => Event struct          │
                    │    └─ attendances[id][commitment] => true │
                    │                                           │
                    │  ISP1Verifier (gateway)                   │
                    │    └─ verifyProof(vkey, pubValues, proof) │
                    └───────────────────────────────────────────┘
```

### Data Flow (Happy Path)

```
1. Organizer  →  createEvent(id, locationHash, timeWindow, pubkey)  →  Chain
2. Organizer  →  generates attestation material (QR / geo-fence / direct sig)
3. Attendee   →  collects attestation (scans QR / enters venue / gets signed)
4. Attendee   →  runs SP1 prover locally or via Prover Network
5. Attendee   →  submits proof + public values to ZkPresence.verifyAttendance()
6. Contract   →  ISP1Verifier.verifyProof() → check nullifier uniqueness → emit AttendanceVerified
```

---

## Circuit Design

### Inputs and Outputs

```
PRIVATE INPUTS (known only to prover):
┌──────────────────────────────────────────────────────┐
│  user_secret        : [u8; 32]   random identity key │
│  attestation_payload: AttestationData  (mode-specific)│
└──────────────────────────────────────────────────────┘

PUBLIC OUTPUTS (committed, visible on-chain):
┌──────────────────────────────────────────────────────┐
│  event_id              : u64                         │
│  nullifier             : [u8; 32]                    │
│  identity_commitment   : [u8; 32]                    │
│  attestation_mode      : u8        (0=QR, 1=Geo, 2=Sig)│
│  timestamp             : u64       unix seconds      │
│  organizer_pubkey_hash : [u8; 32]  ties proof to org │
└──────────────────────────────────────────────────────┘
```

### Attestation Data (per mode)

```rust
enum AttestationData {
    QrCode {
        event_id: u64,
        timestamp: u64,
        nonce: [u8; 16],
        organizer_pubkey: [u8; 33],   // compressed secp256k1
        signature: [u8; 64],          // ECDSA sig over (event_id‖timestamp‖nonce)
    },
    GeoProximity {
        event_id: u64,
        timestamp: u64,
        user_geohash: [u8; 6],        // 6-char precision (~1.2km)
        event_geohash: [u8; 6],       // must match
        organizer_pubkey: [u8; 33],
        event_signature: [u8; 64],    // sig over (event_id‖event_geohash‖time_window)
    },
    OrganizerSignature {
        event_id: u64,
        timestamp: u64,
        organizer_pubkey: [u8; 33],
        signature: [u8; 64],          // sig over (identity_commitment‖event_id)
    },
}
```

### Circuit Constraints (pseudocode)

```
fn main():
    // 1. Read private inputs
    secret = read::<[u8; 32]>()
    attestation = read::<AttestationData>()

    // 2. Derive identity commitment (public identifier, unlinkable to secret)
    identity_commitment = sha256(secret)

    // 3. Derive nullifier (unique per user per event, prevents double-claim)
    nullifier = sha256(secret ‖ event_id)

    // 4. Verify attestation based on mode
    match attestation:
        QrCode { event_id, timestamp, nonce, organizer_pubkey, signature }:
            message = sha256(event_id ‖ timestamp ‖ nonce)
            assert!(ecdsa_verify(organizer_pubkey, message, signature))
            mode = 0

        GeoProximity { event_id, timestamp, user_geohash, event_geohash, ... }:
            assert!(user_geohash[0..5] == event_geohash[0..5])  // 5-char match ~5km
            message = sha256(event_id ‖ event_geohash ‖ time_window)
            assert!(ecdsa_verify(organizer_pubkey, message, event_signature))
            mode = 1

        OrganizerSignature { event_id, timestamp, organizer_pubkey, signature }:
            message = sha256(identity_commitment ‖ event_id)
            assert!(ecdsa_verify(organizer_pubkey, message, signature))
            mode = 2

    // 5. Compute organizer pubkey hash (binds proof to specific organizer)
    organizer_pubkey_hash = sha256(organizer_pubkey)

    // 6. Commit public outputs
    commit(event_id)
    commit(nullifier)
    commit(identity_commitment)
    commit(mode)
    commit(timestamp)
    commit(organizer_pubkey_hash)
```

### Security Properties

| Property | Mechanism |
|---|---|
| **No identity leakage** | `user_secret` is private input; only `identity_commitment = H(secret)` is public |
| **No double-claiming** | `nullifier = H(secret ‖ event_id)` is deterministic and unique per user×event |
| **Attestation binding** | Proof verifies organizer's ECDSA signature inside the circuit |
| **Event binding** | `event_id` is committed publicly; contract cross-checks against registered events |
| **Timestamp integrity** | Timestamp committed publicly; contract can enforce time-window checks |
| **Unlinkability** | Different events produce different nullifiers; identity_commitment is stable but only linkable if user chooses to reveal |

---

## Nullifier Scheme

```
nullifier = SHA-256(user_secret ‖ event_id)

Properties:
  - Deterministic: same user + same event = same nullifier (always)
  - Unlinkable: different events produce different nullifiers
  - Irreversible: can't derive user_secret from nullifier
  - Unique: collision resistance of SHA-256

On-chain storage:
  mapping(bytes32 => bool) public nullifierUsed;

Flow:
  1. User generates proof → nullifier is a public output
  2. Contract checks: require(!nullifierUsed[nullifier])
  3. Contract stores: nullifierUsed[nullifier] = true
  4. User can prove attendance to event X exactly once
```

### Why SHA-256 over Poseidon

SP1 is a general-purpose zkVM — it executes arbitrary Rust, not arithmetic circuits. SHA-256 is natively accelerated via SP1 precompiles (cycle cost ~1/100th of software SHA-256). Poseidon would be faster in R1CS/Plonkish systems but has no SP1 precompile advantage. SHA-256 is simpler, more widely understood, and audited.

---

## Smart Contract Interfaces

### ZkPresence.sol

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {ISP1Verifier} from "@sp1-contracts/ISP1Verifier.sol";

contract ZkPresence {
    // --- Types ---

    struct Event {
        address organizer;
        bytes32 locationHash;       // keccak256(geohash) for geo mode
        uint64  startTime;
        uint64  endTime;
        bytes32 organizerPubkeyHash; // sha256(compressed_pubkey)
        bool    active;
    }

    struct PublicValues {
        uint64  eventId;
        bytes32 nullifier;
        bytes32 identityCommitment;
        uint8   attestationMode;     // 0=QR, 1=Geo, 2=Sig
        uint64  timestamp;
        bytes32 organizerPubkeyHash;
    }

    // --- State ---

    ISP1Verifier public immutable verifier;
    bytes32      public immutable programVKey;

    mapping(uint64 => Event)                        public events;
    mapping(bytes32 => bool)                        public nullifierUsed;
    mapping(uint64 => mapping(bytes32 => bool))     public attended;
    // attended[eventId][identityCommitment] = true

    uint64 public nextEventId;

    // --- Events ---

    event EventCreated(uint64 indexed eventId, address organizer);
    event AttendanceVerified(
        uint64 indexed eventId,
        bytes32 indexed nullifier,
        bytes32 identityCommitment,
        uint8   attestationMode
    );

    // --- Constructor ---

    constructor(address _verifier, bytes32 _programVKey) {
        verifier = ISP1Verifier(_verifier);
        programVKey = _programVKey;
    }

    // --- Organizer Functions ---

    /// Create a new event. Returns the event ID.
    function createEvent(
        bytes32 locationHash,
        uint64  startTime,
        uint64  endTime,
        bytes32 organizerPubkeyHash
    ) external returns (uint64 eventId) {
        eventId = nextEventId++;
        events[eventId] = Event({
            organizer: msg.sender,
            locationHash: locationHash,
            startTime: startTime,
            endTime: endTime,
            organizerPubkeyHash: organizerPubkeyHash,
            active: true
        });
        emit EventCreated(eventId, msg.sender);
    }

    /// Deactivate an event (organizer only).
    function deactivateEvent(uint64 eventId) external {
        require(events[eventId].organizer == msg.sender, "not organizer");
        events[eventId].active = false;
    }

    // --- Attendee Functions ---

    /// Submit a ZK proof of attendance.
    function verifyAttendance(
        bytes calldata proof,
        bytes calldata publicValues
    ) external {
        // 1. Verify the SP1 proof
        verifier.verifyProof(programVKey, publicValues, proof);

        // 2. Decode public values
        PublicValues memory pv = abi.decode(publicValues, (PublicValues));

        // 3. Check event exists and is active
        Event storage evt = events[pv.eventId];
        require(evt.active, "event not active");

        // 4. Check organizer pubkey matches
        require(
            pv.organizerPubkeyHash == evt.organizerPubkeyHash,
            "organizer mismatch"
        );

        // 5. Check timestamp is within event window
        require(
            pv.timestamp >= evt.startTime && pv.timestamp <= evt.endTime,
            "outside event window"
        );

        // 6. Check nullifier hasn't been used (prevents double-claim)
        require(!nullifierUsed[pv.nullifier], "already claimed");
        nullifierUsed[pv.nullifier] = true;

        // 7. Record attendance
        attended[pv.eventId][pv.identityCommitment] = true;

        emit AttendanceVerified(
            pv.eventId,
            pv.nullifier,
            pv.identityCommitment,
            pv.attestationMode
        );
    }

    // --- View Functions ---

    /// Check if a user (by identity commitment) attended an event.
    function hasAttended(
        uint64 eventId,
        bytes32 identityCommitment
    ) external view returns (bool) {
        return attended[eventId][identityCommitment];
    }

    /// Check if a nullifier has been used.
    function isNullifierUsed(bytes32 nullifier) external view returns (bool) {
        return nullifierUsed[nullifier];
    }
}
```

### ISP1Verifier Gateway (pre-deployed)

| Chain | Groth16 Gateway Address |
|---|---|
| Ethereum Mainnet | `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` |
| Base | `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` |
| Base Sepolia | `0x397A5f7f3dBd538f23DE225B51f532c34448dA9B` |

Same address across all EVM chains (CREATE2 deployment).

---

## Attestation Protocols

### Mode A: QR Code Scan

Best for: concerts, conferences, meetups — any physical event with a check-in point.

```
ORGANIZER SETUP:
  1. Create event on-chain: createEvent(locationHash, start, end, pubkeyHash)
  2. Generate QR payloads (can be per-attendee or rotating):
     payload = {
       event_id: uint64,
       timestamp: uint64,
       nonce: random_16_bytes,
       signature: ecdsa_sign(privkey, sha256(event_id ‖ timestamp ‖ nonce))
     }
  3. Display QR code at venue (rotate nonce every 30-60s to prevent sharing)

ATTENDEE FLOW:
  1. Scan QR code with zkPresence app
  2. App reads payload + user's local user_secret
  3. App calls SP1 prover (local or network):
     - Private: user_secret, QrCode { event_id, timestamp, nonce, pubkey, sig }
     - Circuit verifies ECDSA sig, computes nullifier + identity_commitment
  4. App submits proof to ZkPresence.verifyAttendance()

SECURITY:
  - Rotating nonces prevent QR photo-sharing (old nonces expire)
  - Organizer pubkey is baked into the event on-chain
  - User identity never touches the QR or the chain
```

### Mode B: Geohash Proximity

Best for: location-gated experiences, geo-fenced community events.

```
ORGANIZER SETUP:
  1. Create event with locationHash = keccak256(event_geohash_6chars)
  2. Sign the geo-fence parameters:
     signature = ecdsa_sign(privkey, sha256(event_id ‖ event_geohash ‖ start ‖ end))
  3. Publish signed geo-fence (can be in event metadata, app config, etc.)

ATTENDEE FLOW:
  1. App reads device GPS → converts to geohash (6-char precision)
  2. App constructs GeoProximity attestation with user_geohash + event params
  3. SP1 circuit verifies:
     a. user_geohash[0..5] == event_geohash[0..5]  (5-char = ~5km match)
     b. ecdsa_verify on the event geo-fence signature
  4. Submit proof on-chain

SECURITY:
  - GPS spoofing is the main attack vector
  - Mitigations: combine with QR mode, require Wi-Fi BSSID attestation, or
    use trusted hardware attestation (future enhancement)
  - 5-char geohash precision (~5km) is intentionally coarse to preserve privacy
  - The exact location is never committed — only proximity is proven
```

### Mode C: Organizer Direct Signature

Best for: small events, VIP access, community gatherings where organizer knows attendees.

```
ORGANIZER FLOW:
  1. Attendee presents their identity_commitment (derived from their secret)
     - This can be shown as a QR code on the attendee's device
     - Or registered in advance via app
  2. Organizer signs: signature = ecdsa_sign(privkey, sha256(identity_commitment ‖ event_id))
  3. Organizer sends signature back to attendee (via NFC tap, QR, or app)

ATTENDEE FLOW:
  1. Receives organizer's signature over their identity_commitment
  2. Runs SP1 prover with OrganizerSignature attestation
  3. Circuit verifies the organizer's signature
  4. Submit proof on-chain

SECURITY:
  - Organizer sees identity_commitment but NOT user_secret
  - identity_commitment is a one-way hash — organizer can't derive the secret
  - Most trust-minimized mode for the organizer (they only need to sign)
  - Most interactive mode — requires direct organizer↔attendee exchange
```

---

## SP1 Program Structure

```
zkpresence/
├── Cargo.toml                    # Workspace root
├── rust-toolchain                # Pins succinct RISC-V toolchain
│
├── lib/                          # Shared types (program + script)
│   ├── Cargo.toml
│   └── src/
│       └── lib.rs                # AttestationData, PublicValues, etc.
│
├── program/                      # Guest (runs inside zkVM)
│   ├── Cargo.toml                # depends: sp1-zkvm, zkpresence-lib
│   └── src/
│       └── main.rs               # Circuit logic: verify attestation,
│                                 #   compute nullifier, commit outputs
│
├── script/                       # Host (generates proofs, deploys)
│   ├── Cargo.toml                # depends: sp1-sdk, sp1-build, zkpresence-lib
│   ├── build.rs                  # Compiles program → ELF at build time
│   └── src/
│       └── bin/
│           ├── prove.rs          # Generate attendance proof
│           └── vkey.rs           # Export verification key for contract
│
├── contracts/                    # Solidity (Foundry)
│   ├── foundry.toml
│   ├── remappings.txt
│   └── src/
│       └── ZkPresence.sol        # On-chain verifier + event registry
│
├── ARCHITECTURE.md               # This file
└── README.md                     # Project overview
```

### Crate Dependency Graph

```
zkpresence-lib (no_std compatible)
    ├── serde (serialize/deserialize)
    └── sha2 (SHA-256, used for nullifier + identity commitment)

zkpresence-program (sp1 guest, RISC-V target)
    ├── sp1-zkvm = "6.1"
    └── zkpresence-lib

zkpresence-script (host, x86/arm)
    ├── sp1-sdk = "6.1"
    ├── sp1-build = "6.1" (build-dep)
    ├── zkpresence-lib
    ├── clap (CLI args)
    └── hex (encoding)
```

---

## Key Design Decisions

### 1. SHA-256 over Poseidon for hashing

**Chosen:** SHA-256
**Reason:** SP1 has a native SHA-256 precompile (~100x faster than software). Poseidon is optimal for arithmetic circuits (Circom/Halo2) but has no advantage in SP1's general-purpose zkVM. SHA-256 is simpler, more audited, and compatible with Ethereum's tooling.
**Alternative:** Poseidon — would save cycles in R1CS systems but adds complexity here with no benefit.

### 2. ECDSA secp256k1 for attestation signatures

**Chosen:** secp256k1 ECDSA
**Reason:** SP1 has a secp256k1 precompile. Matches Ethereum's native signature scheme, so organizers can use their existing Ethereum keys. Reduces the number of key types in the system.
**Alternative:** Ed25519 (faster in software, also has SP1 precompile) — but would require organizers to manage a separate key pair.

### 3. Groth16 for on-chain proofs

**Chosen:** Groth16 via SP1
**Reason:** Smallest proof size (~192 bytes), cheapest on-chain verification (~230k gas). SP1 generates Groth16 proofs that verify against the pre-deployed ISP1Verifier gateway — no custom verifier deployment needed.
**Alternative:** PLONK (universal setup, ~1KB proofs, ~300k gas) — slightly more expensive but no trusted setup concern. For a weekend build, Groth16 via SP1's managed gateway is simpler.

### 4. Single contract vs. factory pattern

**Chosen:** Single `ZkPresence` contract with event registry
**Reason:** Simpler to deploy and manage. One contract address, one programVKey. Events are data, not separate contracts.
**Alternative:** Factory that deploys per-event contracts — useful if events need custom logic, but over-engineered for MVP.

### 5. Identity commitment as SHA-256(secret) vs. Semaphore-style

**Chosen:** Simple `SHA-256(user_secret)` → identity_commitment
**Reason:** Sufficient for MVP. The commitment is binding and hiding. No group membership proofs needed yet.
**Alternative:** Semaphore identity (commitment to (nullifier_key, trapdoor)) — useful if we later need group membership trees, but adds complexity now.

---

## Security Considerations

### Threat Model

| Threat | Impact | Mitigation |
|---|---|---|
| **User secret compromise** | Attacker can claim attendance as victim | Secret stored locally on device, never transmitted. Future: derive from hardware key |
| **QR code photo-sharing** | Non-attendee gets valid attestation | Rotating nonces (30-60s), one-time-use nonces (track in organizer backend) |
| **GPS spoofing (geo mode)** | Fake proximity proof | Coarse precision (5km) reduces incentive; combine with QR for high-value events |
| **Organizer key compromise** | Fake attestations issued | Standard key management; multi-sig for high-value events; key rotation with on-chain update |
| **Front-running proof submission** | MEV bot submits someone else's proof | Proof includes `identity_commitment` — bot would need user's secret to benefit. Attendance is recorded to the commitment, not to `msg.sender` |
| **Nullifier grinding** | Try to find collisions | SHA-256 collision resistance (128-bit security) makes this infeasible |
| **Replay across chains** | Submit same proof on multiple chains | `chainId` not currently included — add to public values if multi-chain deployment needed |

### Privacy Properties

1. **Zero identity leakage:** `user_secret` never leaves the prover. On-chain, only `identity_commitment` (a hash) is visible.
2. **Unlinkable across events:** Different `event_id` values produce different `nullifier` values. An observer cannot link attendance across events unless the user voluntarily reveals their `identity_commitment`.
3. **Voluntary linkability:** A user CAN prove they attended multiple events by revealing their `identity_commitment` is the same across proofs — but this is opt-in.
4. **Organizer privacy:** In QR and Geo modes, the organizer never learns the user's identity. In Sig mode, the organizer sees `identity_commitment` (but not the secret).

### What This Does NOT Protect Against

- **Coercion:** If someone forces a user to reveal their secret, all privacy is lost.
- **Physical attendance verification:** The ZK proof verifies cryptographic attestation, not physical presence. A user who obtains a valid QR code remotely can still prove "attendance."
- **Sybil attacks:** One person can create multiple `user_secret` values and claim attendance multiple times with different identities. Rate-limiting requires out-of-band identity binding (e.g., Worldcoin, government ID — future enhancement).

---

## Use Case Integration

### Otto Music — Event Attendance Proofs

```
Concert/show attendance → exclusive content unlock

Flow:
  1. Artist creates event via Otto Music dashboard → calls createEvent()
  2. Venue displays rotating QR codes during the show
  3. Fans scan QR with Otto Music app → proof generated
  4. Proof submitted on-chain → AttendanceVerified event emitted
  5. Otto Music backend listens for events → unlocks:
     - Exclusive tracks / stems
     - Artist token airdrops
     - VIP tier upgrades
     - Proof-gated Discord/Telegram channels

Privacy benefit:
  - Fans prove they were there without revealing WHO they are
  - Artist sees attendance count but not individual identities
  - Fan can optionally reveal identity to claim personalized rewards
```

### Tusita — Community Presence Verification

```
Meditation session / community gathering attendance → reputation building

Flow:
  1. Session leader creates event with geo-fence (meditation center location)
  2. Participants' phones auto-detect proximity (geo mode)
     OR leader directly signs each participant's commitment (sig mode)
  3. Participants generate proofs after the session
  4. Proofs recorded on-chain → build attendance history
  5. Tusita app queries hasAttended() to build reputation:
     - "Attended 30+ sessions" badge (without revealing WHICH sessions)
     - Session-gated content access
     - Community governance weight

Privacy benefit:
  - Members prove consistent attendance without surveillance
  - No attendance logs linking identities to specific sessions
  - Community leaders can verify group size without individual tracking
```

---

## Implementation Plan

### Phase 1: Weekend MVP (2-3 days)

1. **Scaffold SP1 workspace** — Cargo.toml, program/, script/, lib/
2. **Implement shared types** — `AttestationData`, `PublicValues` in lib/
3. **Write circuit** — QR mode only (simplest attestation)
4. **Write prove script** — Generate proof with mock data using `SP1_PROVER=mock`
5. **Write verifier contract** — ZkPresence.sol with Foundry
6. **Test end-to-end** — Mock prove → local verify → deploy to Base Sepolia

### Phase 2: Full Attestation Modes (1 week)

7. **Add geo mode** — Geohash comparison in circuit
8. **Add sig mode** — Direct organizer signature verification
9. **QR code generator** — Simple web tool for organizers
10. **Integration tests** — All three modes, edge cases

### Phase 3: Production Integration (2 weeks)

11. **Prover Network integration** — `SP1_PROVER=network` for real proofs
12. **Mobile SDK** — React Native / Flutter wrapper for proof generation
13. **Otto Music integration** — Event creation + QR display + reward unlock
14. **Tusita integration** — Geo-fence + attendance history queries
15. **Deploy to Base mainnet** — Audit, deploy, verify

---

## Appendix: Gas Estimates

| Operation | Estimated Gas | Cost at 0.01 gwei (Base) |
|---|---|---|
| `createEvent()` | ~80,000 | ~$0.001 |
| `verifyAttendance()` (Groth16) | ~230,000 | ~$0.003 |
| `hasAttended()` (view) | 0 | $0 |

Base L2 gas costs are negligible — proof verification is economically viable even at scale.

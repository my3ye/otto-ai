# SOS Systems — Post-Quantum Framework Architecture
## The Dual-Trust Model: Behavioral Immunity + Cryptographic Resistance

*Authored by Otto (Architect Agent) | 2026-04-12 | Status: Architecture Complete*

---

## Design: SOS Post-Quantum Framework

### Problem

SOS Systems' current cryptographic infrastructure — Ed25519 signing, BBS+ selective disclosure, Groth16 ZK proofs, ECDSA-based smart contracts — is entirely vulnerable to Shor's algorithm. A CRQC (Cryptographically Relevant Quantum Computer) in the 2027-2030 window would break every signature scheme in the Integrity Preservation Layer, compromise all ONEON identities, forge governance votes, and retroactively deanonymize all aid distribution records.

But SOS Systems has something no other blockchain project has: **a governance model that is architecturally quantum-immune by design.** DPC (Dynamic Proximity Calculus) derives governance weight from verified behavioral record — contribution history, peer attestation, sustained engagement. No quantum computer can invert behavioral history. This is not a patch. It is a structural moat.

The framework must do two things:
1. **Migrate the cryptographic substrate** from classical to post-quantum primitives
2. **Formalize and strengthen the behavioral trust layer** as the primary trust anchor, with cryptographic trust as a reinforcing secondary layer — inverting the current hierarchy where crypto is primary and behavior is secondary

### Core Thesis

**Math was never the foundation. The foundation was always social.**

Cryptographic hardness assumptions (ECDLP, RSA factoring) are believed, not proven. They are social consensus about algorithmic difficulty. The quantum transition reveals this: any trust system reducible to mathematical hardness has a hidden expiry condition. Trust systems that survive must be grounded in verifiable human behavior — contribution history, reputation, persistent identity — not key possession.

SOS Systems' DPC model is the only governance architecture in production design that makes this claim architecturally defensible.

---

## 1. Core Threat Model

### 1.1 Adversary Assumptions

| Adversary | Capability | Timeline | Target |
|---|---|---|---|
| **Nation-state (CRQC holder)** | Shor's on 1,200+ logical qubits; HNDL archive of all public chain data | 2027-2030 | ONEON identities, governance votes, aid records, contributor wallets |
| **Nation-state (pre-CRQC)** | HNDL collection active NOW; classical computing + social engineering | Present | All public blockchain history; SOS distribution records; ONEON identity graph |
| **Criminal syndicate** | Leased CRQC access (plausible 2029+); targeted high-value attacks | 2029-2032 | Treasury wallets, bridge multisigs, DeFi ecrecover |
| **Insider threat** | Classical access + PQC migration confusion; key management errors | Present | Mis-migrated identities, dual-key window exploits |

### 1.2 Attack Surfaces in Current SOS Stack

| Component | Current Algorithm | Quantum Vulnerability | Impact |
|---|---|---|---|
| ONEON DID signing | Ed25519 | **CRITICAL** — Shor breaks in polynomial time | Identity forgery, credential impersonation |
| VC signatures (BBS+) | BN254 pairing-based | **HIGH** — pairing DLP vulnerable to Shor | Selective disclosure broken; all VCs forgeable |
| ZK proofs (aid eligibility) | Groth16/Circom (BN254) | **HIGH** — trusted setup + pairing vulnerability | Fake eligibility proofs, double-dipping |
| Smart contracts (RecordAnchor, OPRLP) | ECDSA secp256k1 via EVM | **CRITICAL** — Shor breaks ECDLP directly | Contract takeover, governance forging |
| Mesh encryption | Noise Protocol (X25519) | **CRITICAL** — ECDH key exchange vulnerable | All mesh traffic decryptable retroactively |
| IPFS content addressing | SHA-256 | **SAFE** — Grover provides only 2x speedup | No action needed |
| Merkle audit trees | SHA-256 / Keccak | **SAFE** | No action needed |

### 1.3 HNDL Exposure (Already Active)

All SOS Systems data on public blockchains is **already captured**:
- Every on-chain anchor (RecordAnchor.sol transactions) contains signer address
- Every VC hash batch posted to Polygon zkEVM is public
- ONEON DID documents registered on-chain expose public keys
- Distribution nullifiers are public (by design, for audit)

**Critical insight**: The audit transparency that makes SOS trustworthy is the same property that makes HNDL collection trivial. No interception needed — the data is public by design. This is the immutability paradox: blockchain's strength becomes its quantum vulnerability.

**Implication**: Migration must begin BEFORE CRQCs exist. Post-CRQC migration is damage control, not prevention.

---

## 2. Cryptographic Primitives Stack

### 2.1 Algorithm Selection

| Layer | Current | Post-Quantum Replacement | Rationale |
|---|---|---|---|
| **Identity signing** | Ed25519 | **ML-DSA-65** (FIPS 204, Dilithium) | NIST finalized; 192-bit security; 2.4KB sigs acceptable for identity ops; Solana/QAN already deploying |
| **Transaction signing** | ECDSA secp256k1 | **ML-DSA-65** (primary) + **FN-DSA-512** (FIPS 206, FALCON) for on-chain verification | ML-DSA for general signing; FN-DSA for gas-sensitive on-chain verify (666-byte sigs) |
| **Key exchange** | X25519 (ECDH) | **ML-KEM-768** (FIPS 203, Kyber) | NIST finalized; 192-bit security; already in Chrome/Azure TLS; replaces mesh Noise handshake |
| **Selective disclosure** | BBS+ (BN254 pairing) | **BBS+ over ML-DSA** (IETF draft) OR **Mercurial Signatures** over lattices | BBS+ lattice variant is active IETF work; fallback: attribute-based credentials with STARK proofs |
| **ZK proofs** | Groth16/Circom (BN254) | **STARKs** (hash-based FRI, no trusted setup) | Hash-based = quantum-safe by construction; SP1/RISC Zero for general compute; no pairing dependency |
| **Backup signature** | None | **SLH-DSA-128s** (FIPS 205, SPHINCS+) | Conservative hash-only scheme; insurance policy if lattice assumptions broken; 8KB sigs acceptable for root keys |
| **Hash functions** | SHA-256 / Keccak | **SHA-256 / SHA-3** (unchanged) | Already quantum-resistant (Grover: 256→128 bit effective security); no migration needed |

### 2.2 Why These Algorithms

**ML-DSA-65 as primary signature**: The NIST FIPS 204 standard. Lattice-based (Module-LWE + Module-SIS). Production-ready — Solana testnet since Dec 2025, QANplatform mainnet July 2026. 2,420-byte signatures are larger than Ed25519 (64 bytes) but acceptable for identity and governance operations where throughput isn't the bottleneck.

**FN-DSA-512 for on-chain verification**: FALCON's 666-byte signatures are 3.6x smaller than ML-DSA, meaning lower gas costs for on-chain signature verification. Algorand has run FALCON State Proofs on mainnet since September 2022 — 4 years of production data. Best fit for high-frequency on-chain operations (aid distribution anchoring, DPC score updates).

**ML-KEM-768 for key exchange**: Direct ECDH replacement. Google Chrome already ships it. The mesh network's Noise Protocol handshake swaps X25519 for ML-KEM-768 with minimal protocol changes.

**STARKs replacing Groth16**: Groth16 depends on BN254 pairings (quantum-vulnerable) and requires a trusted setup (centralization risk). STARKs are hash-based — quantum-safe by construction, no trusted setup, transparent verification. Larger proofs (~50-200KB vs ~200 bytes for Groth16) but acceptable for batch aid verification. SP1 (Succinct) and RISC Zero provide general-purpose STARK proving.

**SLH-DSA as backup**: SPHINCS+ is the most conservative PQC option — security relies ONLY on hash function properties, not lattice assumptions. If lattice-based schemes (ML-DSA, ML-KEM, FN-DSA) are broken by future cryptanalysis, SLH-DSA provides a fallback. Used for root identity keys and constitutional governance signatures only.

### 2.3 Algorithm Risk Assessment

| Algorithm | Security Assumption | Risk Level | Mitigation |
|---|---|---|---|
| ML-DSA / ML-KEM | Module-LWE lattice hardness | **LOW** — 7 years of NIST scrutiny, no known attacks | Hybrid dual-signing during transition |
| FN-DSA | NTRU lattice hardness | **LOW** — 4 years production (Algorand), NIST finalist | ML-DSA fallback |
| SLH-DSA | Hash function preimage resistance | **NEGLIGIBLE** — SHA-256 is quantum-durable | None needed |
| STARKs | Hash collision resistance | **NEGLIGIBLE** — hash-based by construction | None needed |
| BBS+ lattice variant | Active research, not yet standardized | **MEDIUM** — may not stabilize before 2028 | STARK-based attribute proofs as interim |

---

## 3. Migration Path from ECDSA-Based Systems

### 3.1 Four-Phase Migration

```
PHASE 0: IMMEDIATE HYGIENE (Now — $0, no protocol changes)
├── Stop address reuse across ALL SOS/ONEON wallets
├── Enforce single-use addresses in aid distribution contracts
├── Document all exposed public keys in current deployment
├── Begin HNDL exposure audit of all on-chain anchored data
└── Timeline: Immediate. Cost: $0.

PHASE 1: HYBRID DUAL-SIGNING (Q3 2026 — protocol change)
├── All new ONEON DIDs: generate BOTH Ed25519 AND ML-DSA-65 keypair
├── All new transactions: dual-sign (Ed25519 ∥ ML-DSA-65)
│   Validity = Ed25519_valid AND ML-DSA_valid
├── Smart contracts: accept BOTH signature types (algorithm ID prefix)
├── Mesh network: upgrade Noise handshake to ML-KEM-768 hybrid
│   shared_secret = KDF(X25519_secret ∥ ML-KEM_secret)
├── VC issuance: dual-signature (Ed25519 + ML-DSA) on all new VCs
└── Timeline: 8-12 weeks. Cost: ~$8-12.

PHASE 2: FULL PQ PRIMARY (Q1 2027 — breaking change)
├── New DIDs: ML-DSA-65 only (Ed25519 deprecated for new issuance)
├── On-chain contracts: FN-DSA-512 verification primary
├── ZK proofs: migrate Groth16 circuits to STARK equivalents (SP1)
├── Selective disclosure: STARK-based attribute proofs replace BBS+
├── Old DIDs: migration path (re-issue VC under new PQ key, old VC
│   remains valid until expiry but flagged as quantum-vulnerable)
├── Root keys: SLH-DSA-128s for constitutional governance operations
└── Timeline: 12-16 weeks. Cost: ~$15-20.

PHASE 3: LEGACY SUNSET (Q3 2027 — final deprecation)
├── Classical-only signatures rejected by smart contracts
├── Ed25519 DID documents: read-only (verify historical, no new ops)
├── Full STARK pipeline for all ZK operations
├── Crypto-agility layer: algorithm registry supports hot-swap
│   for future algorithm rotations without protocol forks
└── Timeline: 8 weeks. Cost: ~$5-8.
```

### 3.2 Crypto-Agility Architecture

Every cryptographic operation in SOS flows through an **algorithm abstraction layer** — not hardcoded primitives.

```
┌──────────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                       │
│  (ONEON identity, DPC scoring, aid distribution, mesh)   │
└──────────────────────────┬───────────────────────────────┘
                           │ calls
┌──────────────────────────▼───────────────────────────────┐
│  CRYPTO-AGILITY LAYER (SignatureProvider interface)       │
│                                                          │
│  sign(payload) → {algorithm_id, signature, public_key}   │
│  verify(payload, sig) → bool                             │
│  exchange(peer_pubkey) → shared_secret                   │
│  prove(circuit, witness) → proof                         │
│                                                          │
│  Algorithm Registry:                                     │
│    0x01 = Ed25519        (deprecated Phase 3)            │
│    0x02 = ECDSA_secp256k1 (deprecated Phase 3)           │
│    0x10 = ML-DSA-65      (primary, Phase 1+)             │
│    0x11 = FN-DSA-512     (on-chain, Phase 2+)            │
│    0x12 = SLH-DSA-128s   (root keys, Phase 2+)           │
│    0x20 = ML-KEM-768     (key exchange, Phase 1+)        │
│    0x30 = STARK-FRI      (ZK proofs, Phase 2+)           │
│    0xFF = HYBRID         (dual-sign, Phase 1-2)          │
│                                                          │
│  New algorithms added by DAO vote (governance-gated).    │
│  Old algorithms deprecated, never removed from verify.   │
└──────────────────────────────────────────────────────────┘
```

**Key design decision**: Old algorithms are deprecated from `sign()` but never removed from `verify()`. Historical records signed with Ed25519 remain verifiable forever. The chain of custody is preserved even after migration.

### 3.3 DID Migration Protocol

```
ONEON DID MIGRATION (per-identity):

  STEP 1: Existing DID holder requests migration
    - Proves ownership of current Ed25519 key (sign challenge)
    - System generates ML-DSA-65 keypair on device

  STEP 2: DID Document updated
    - New ML-DSA key added as ADDITIONAL verification method
    - Old Ed25519 key marked: {purpose: "historical-verify-only"}
    - DID Document signed by BOTH keys (cross-attestation)

  STEP 3: VC re-issuance
    - All active VCs re-signed under ML-DSA key
    - Old VC CIDs preserved (historical audit trail)
    - New VCs linked to old via previous_record_cid chain

  STEP 4: Grace period (90 days)
    - Both keys accepted for operations
    - After 90 days: Ed25519 restricted to verify-only

  OFFLINE MIGRATION PATH:
    - Field devices with no connectivity: store migration request
    - Sync when connected; batch process
    - Paper QR backup re-issued with new key material
    - Critical: QR code size increases (~3x for ML-DSA pubkey)
      Mitigation: QR contains CID pointer to full key, not raw key
```

---

## 4. Novel Trust Mechanisms for a Quantum World

### 4.1 The Dual-Trust Architecture

SOS Systems inverts the trust hierarchy that every other blockchain uses:

```
CLASSICAL BLOCKCHAIN (current):
  Primary trust:   Cryptographic (key possession)
  Secondary trust: Social (reputation, governance)

  → Quantum breaks primary. Secondary is too weak to stand alone.

SOS DUAL-TRUST MODEL (proposed):
  Primary trust:   Behavioral (DPC contribution record)
  Secondary trust: Post-quantum cryptographic (ML-DSA, STARKs)

  → Quantum breaks neither. Behavioral trust is immune.
     PQ crypto is resistant. Belt AND suspenders.
```

### 4.2 Behavioral Trust Layer (Quantum-Immune)

DPC governance weight derives from three verified behavioral factors:

1. **Structural Impact** — Did your contribution change the architecture? Verified by: automated tests, peer review, deployment confirmation, on-chain outcome measurement.

2. **Consistent Energy** — Sustained engagement over time, not burst contributions. Verified by: temporal distribution of contributions, decay function on inactive periods.

3. **Weighted Resonance** — Alignment with mission priorities. Verified by: peer attestation, DAO priority matching, downstream usage metrics.

**Why this is quantum-immune**: A quantum computer can forge a signature. It cannot forge six months of verified peer reviews, 47 accepted code contributions, 12 mentored contributors who themselves advanced, and 200+ governance votes cast over time. The behavioral record is a high-dimensional attestation graph — not a single mathematical relationship.

**Formalized behavioral trust properties**:

| Property | Mechanism | Quantum Relevance |
|---|---|---|
| **Non-invertibility** | Contribution history is append-only; you cannot compute a history that produces a specific DPC score without actually doing the work | No mathematical shortcut exists |
| **Temporal anchoring** | Contributions are timestamped and ordered; fabricating a history requires controlling the append-only record at the time of each entry | Cannot retroactively insert contributions |
| **Multi-party attestation** | Each contribution requires peer verification from multiple independent attestors | Colluding quantum attacker must compromise the social graph, not just keys |
| **Decay function** | DPC scores decay without activity — you cannot accumulate and rest | Quantum attacker must sustain ongoing verifiable behavior |
| **Cross-reference density** | High-DPC contributors are referenced by many others' contributions (mentees, reviewers, dependents) | Fabricating a contributor requires fabricating an entire subgraph |

### 4.3 Post-Pattern Ownership Model

Classical crypto ownership: `I own this because I hold this key.`
Post-quantum SOS ownership: `I am this identity because I am this history.`

The framework defines three tiers of identity assurance:

```
TIER 1: CRYPTOGRAPHIC IDENTITY (post-quantum)
  "I can sign with this ML-DSA key"
  Strength: Strong against classical + quantum adversaries
  Weakness: Key can be stolen (social engineering, device compromise)
  Use: Standard operations — signing transactions, issuing VCs

TIER 2: BEHAVIORAL IDENTITY (quantum-immune)
  "My DPC history attests that I am a sustained contributor"
  Strength: Cannot be forged, stolen, or quantum-computed
  Weakness: Slow to establish (requires months of verified contribution)
  Use: High-stakes operations — governance votes, constitutional changes,
       emergency powers, identity recovery

TIER 3: MULTI-PARTY ATTESTATION (quantum-immune)
  "N independent parties attest that I am who I claim to be"
  Strength: Requires social graph compromise, not cryptographic attack
  Weakness: Vulnerable to collusion (mitigated by DPC decay + attestor diversity)
  Use: Identity recovery after key loss, dispute resolution,
       refugee intake verification
```

**Escalation rule**: The higher the stakes, the higher the tier required.

| Operation | Minimum Tier | Rationale |
|---|---|---|
| Sign a transaction | Tier 1 | Standard crypto, PQ-resistant |
| Vote on minor proposal | Tier 1 + DPC threshold | Key + contribution history |
| Vote on constitutional change | Tier 2 | Behavioral proof required |
| Invoke emergency powers | Tier 2 + Tier 3 | Behavioral + multi-party |
| Identity recovery (lost key) | Tier 3 | Social recovery, no key involved |
| Approve aid distribution event | Tier 1 + Tier 2 | Crypto + behavioral |

### 4.4 Behavioral Proof Protocol

For Tier 2 operations, the system generates a **behavioral proof** — a verifiable summary of DPC history that can be checked without accessing the full contribution database:

```
BEHAVIORAL PROOF (conceptual):

  Input:
    - contributor DID
    - requested operation
    - current DPC score
    - contribution summary hash (Merkle root of contribution records)

  Proof contains:
    - DPC score ≥ threshold (range proof, no exact score revealed)
    - Contribution count ≥ N over last M days (activity proof)
    - Attestor diversity ≥ K unique peer reviewers (graph proof)
    - No governance penalties in last P days (clean record proof)

  Verification:
    - STARK proof checked on-chain
    - Contribution Merkle root matched against on-chain anchor
    - DPC decay computed to current timestamp

  Properties:
    - Privacy-preserving: exact DPC score, contribution details not revealed
    - Quantum-resistant: STARK-based, no pairing assumptions
    - Offline-verifiable: proof is self-contained after generation
```

---

## 5. SOS Systems' Unique Value Proposition vs Existing PQC Projects

### 5.1 Competitive Landscape

| Project | Approach | PQC Status | Governance Model | Trust Model |
|---|---|---|---|---|
| **QRL** | PQ-native chain (XMSS/SPHINCS+) | Production since 2018 | Token-weighted | Cryptographic only |
| **Algorand** | FALCON State Proofs on classical chain | Production since 2022 | Foundation-led | Cryptographic only |
| **Solana** | ML-DSA migration on classical chain | Testnet Dec 2025 | Validator-weighted | Cryptographic only |
| **QANplatform** | ML-DSA + XLINK MetaMask bridge | Mainnet July 2026 | Token-weighted | Cryptographic only |
| **IOTA 2.0** | Hash-based sigs on DAG | DevNet | Foundation-led | Cryptographic only |
| **Ethereum** | 4-fork PQ roadmap, years away | Planning stage | Mixed (EIPs, staking) | Cryptographic only |
| **Bitcoin** | No coordinated plan | Nothing | None (miner consensus) | Cryptographic only |
| **SOS Systems** | Dual-trust: behavioral + PQ crypto | Architecture stage | DPC contribution-weighted | **Behavioral + Cryptographic** |

### 5.2 The Moat

Every existing PQC blockchain project answers the same question: *How do we replace the broken lock with a stronger lock?*

SOS Systems answers a different question: *What if the lock was never the foundation?*

**Moat 1: Behavioral Trust is Non-Replicable**
QRL, Algorand, Solana — they can swap signature algorithms. They cannot retroactively create a contribution-weighted governance model. Their trust remains entirely cryptographic, meaning the next cryptanalytic breakthrough puts them back at square one. SOS Systems' behavioral trust layer is a one-way ratchet: the longer it operates, the deeper the behavioral attestation graph, the harder it is to forge. Time is an asset, not a liability.

**Moat 2: Dual-Trust Eliminates Single Points of Failure**
If lattice assumptions (ML-DSA, ML-KEM) are broken by future cryptanalysis, every PQC blockchain fails simultaneously. SOS Systems degrades to behavioral trust only — governance continues, identity persists (via Tier 2/3), operations continue with reduced automation. This is the only architecture that has a coherent story for "what if PQC also breaks?"

**Moat 3: Governance Survives What Crypto Cannot**
A quantum attacker who breaks Algorand's FALCON can forge State Proofs and rewrite consensus. A quantum attacker who breaks SOS's ML-DSA can forge signatures — but cannot forge six months of DPC history, cannot fake the attestation graph, cannot fabricate the peer review record. Governance integrity survives because it was never reducible to a mathematical problem.

**Moat 4: The Humanitarian Use Case Is PQ-Native**
SOS Systems operates in environments where cryptographic infrastructure already fails (no connectivity, seized hardware, compromised networks). The mesh-first, offline-first architecture is designed for degraded trust environments. Post-quantum is just another degradation mode — the system was already built to handle trust that cannot rely on a single mechanism.

### 5.3 Positioning Statement

> SOS Systems is the first governance infrastructure designed for a world where no mathematical assumption is permanent. Every other post-quantum project replaces one lock with a stronger lock. SOS replaces the premise: trust is behavioral, not mathematical. Cryptography reinforces it. It does not constitute it.

---

## 6. System Layers

### 6.1 Layer Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 6: GOVERNANCE                                           │
│  DPC-weighted voting, OPRLP rotation, constitutional rules     │
│  Trust: Behavioral (Tier 2) + PQ Crypto (Tier 1)              │
│  Algorithms: ML-DSA-65 (votes), STARKs (behavioral proofs),   │
│             SLH-DSA-128s (constitutional ops)                  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: VALUE TRANSFER                                       │
│  Aid distribution, treasury, contributor compensation          │
│  Trust: PQ Crypto (Tier 1) + Behavioral gates (Tier 2)        │
│  Algorithms: FN-DSA-512 (on-chain sigs), STARKs (eligibility) │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: RECORD INTEGRITY                                     │
│  Append-only anchoring, Merkle audit, IPFS storage             │
│  Trust: Content addressing (SHA-256, quantum-safe) + PQ sigs   │
│  Algorithms: SHA-256 (CIDs), FN-DSA-512 (signer attestation)  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: CREDENTIAL & PROOF                                   │
│  Verifiable Credentials, ZK eligibility, selective disclosure  │
│  Trust: PQ Crypto + behavioral attestation for issuance        │
│  Algorithms: ML-DSA-65 (VC sigs), STARKs (ZK proofs),         │
│             STARK-attribute proofs (selective disclosure)       │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: IDENTITY                                             │
│  ONEON DIDs, key management, social recovery                   │
│  Trust: PQ Crypto (Tier 1) + Multi-party (Tier 3) for recovery│
│  Algorithms: ML-DSA-65 (signing), ML-KEM-768 (encryption),    │
│             SLH-DSA-128s (root/recovery keys)                  │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: NETWORK                                              │
│  Mesh communication, node discovery, data sync                 │
│  Trust: PQ Crypto (transport) + node DID attestation           │
│  Algorithms: ML-KEM-768 (handshake), ML-DSA-65 (node auth),   │
│             SHA-256 (content addressing)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Layer 1: Network (Mesh + Sync)

**Current**: libp2p with Noise Protocol (X25519 ECDH handshake), Meshtastic LoRa.

**Post-Quantum**:
- Replace Noise XX handshake: `X25519 → ML-KEM-768` for ephemeral key exchange
- Node authentication: `Ed25519 → ML-DSA-65` for node DID signatures
- Content addressing: SHA-256 unchanged (quantum-durable)
- LoRa transport: unaffected (physical layer, no crypto dependency)
- DTN (delay-tolerant networking): message encryption uses ML-KEM derived session keys

**Implementation note**: libp2p's modular transport allows swapping the Noise crypto primitives without changing the protocol framing. The `noise-libp2p` spec supports pluggable DH and cipher suites. ML-KEM-768 can be integrated as a new DH-like function (encapsulate/decapsulate maps to DH exchange semantically).

**Bandwidth impact**: ML-KEM-768 ciphertext is 1,088 bytes vs X25519's 32 bytes. For handshake (once per connection), this is negligible. For LoRa (limited bandwidth), handshakes are infrequent — nodes maintain persistent connections.

### 6.3 Layer 2: Identity (ONEON DIDs)

**Current**: `did:key` (Ed25519) offline + `did:ethr` (ECDSA) on-chain.

**Post-Quantum**:
- **New DID method: `did:pq`** — encodes ML-DSA-65 public key directly
  - Format: `did:pq:z<multibase-encoded-ML-DSA-65-pubkey>`
  - Resolves to DID Document with ML-DSA verification method
  - Backward-compatible: DID Documents can contain BOTH Ed25519 and ML-DSA keys during transition
- **Root identity key**: SLH-DSA-128s (hash-based, maximum conservative security)
  - Used only for: identity recovery, DID document rotation, emergency operations
  - Stored on hardware or paper backup (8KB public key — QR requires high-density format)
- **Social recovery**: Shamir Secret Sharing of SLH-DSA root key (unchanged mechanism, new key type)
- **On-chain anchor**: FN-DSA-512 signature on DID Document hash (compact, gas-efficient)

**Key management hierarchy**:
```
ROOT KEY (SLH-DSA-128s) — cold storage / paper / Shamir
  └── OPERATIONAL KEY (ML-DSA-65) — device, daily use
       └── SESSION KEY (ML-KEM-768 derived) — per-connection, ephemeral
```

### 6.4 Layer 3: Credential & Proof

**Current**: W3C VCs 2.0 with BBS+ (selective disclosure), Groth16/Circom (ZK eligibility).

**Post-Quantum**:
- **VC signatures**: ML-DSA-65 replaces BBS+ as primary VC signature
- **Selective disclosure** (the hard problem):
  - BBS+ relies on pairing-based crypto — no direct PQ equivalent is standardized
  - **Interim solution**: STARK-based attribute proofs
    - Issuer signs full VC with ML-DSA-65
    - Holder generates STARK proof: "I hold a valid VC with attribute X = Y"
    - Verifier checks STARK proof (hash-based, quantum-safe)
    - Larger proof size (~50KB vs ~200 bytes for BBS+) but acceptable for non-real-time verification
  - **Future**: Lattice-based BBS+ variants (active IETF research, expected 2028+)
- **ZK eligibility proofs**: Groth16 → SP1 STARK
  - Circuit: prove VC validity + eligibility without revealing identity
  - SP1 (Succinct Prover 1) compiles Rust to STARK-provable RISC-V
  - Proof generation: ~10-30 seconds on mobile (vs ~2 seconds for Groth16)
  - Proof verification: ~1ms on-chain (cheaper gas than Groth16 verify)
  - No trusted setup (eliminates centralization risk)

**Selective disclosure comparison**:

| Approach | Proof Size | Verify Time | Quantum-Safe | Privacy | Status |
|---|---|---|---|---|---|
| BBS+ (current) | ~200 bytes | <1ms | **NO** | Full | Production |
| STARK attribute proof | ~50KB | ~1ms | **YES** | Full | Implementable now |
| Lattice BBS+ | ~2-5KB (est.) | ~5ms (est.) | **YES** | Full | Research (2028+) |

### 6.5 Layer 4: Record Integrity

**Current**: IPFS (SHA-256 CIDs) + RecordAnchor.sol on Polygon zkEVM.

**Post-Quantum**:
- **Content addressing**: SHA-256 CIDs unchanged (quantum-durable at 128-bit effective security)
- **Record signing**: `RecordAnchor.sol` upgraded to accept FN-DSA-512 signatures
  - Existing records (Ed25519/ECDSA signed) remain verifiable
  - New records require PQ signature
  - Smart contract includes algorithm ID byte prefix for signature type routing
- **Merkle audit trees**: SHA-256 / Keccak unchanged (hash-based, quantum-safe)
- **Batch anchoring**: Unchanged mechanism, new signature type

**No migration needed for historical records**: Past CIDs remain valid. Past signatures become quantum-vulnerable but the content-addressed data itself is intact — the record cannot be altered (SHA-256 protects content), only the signer attribution becomes weak. This is acceptable: the record's content is preserved even if the signer's identity becomes deniable.

### 6.6 Layer 5: Value Transfer

**Current**: Solidity smart contracts (ECDSA), aid distribution with nullifier registry.

**Post-Quantum**:
- **Smart contract signatures**: FN-DSA-512 for all on-chain operations
  - `ecrecover` precompile cannot be used — replaced by `pqVerify` precompile or library
  - SOS contracts use a `SignatureVerifier` library that abstracts algorithm selection
  - Gnosis Safe (treasury): module upgrade to accept PQ multisig
- **Nullifier registry**: SHA-256 nullifiers unchanged (hash-based, quantum-safe)
- **Aid distribution**: Eligibility proof switches from Groth16 to STARK
- **DPC on-chain scoring**: `DPCRegistry.sol` upgraded for PQ signer verification
- **Treasury operations**: SLH-DSA-128s for treasury key (maximum security for highest-value operations)

**Chain selection consideration**: Polygon zkEVM and Base L2 do not yet have PQ signature precompiles. Options:
- **Option A**: Verify PQ signatures in Solidity (expensive gas, ~500K-1M gas for ML-DSA verify)
- **Option B**: Wait for L2 PQ precompile support (Ethereum PQ roadmap active)
- **Option C**: Deploy PQ verification as a precompile on SOS-operated L3 / app-chain

**Recommended**: Option A for Phase 1 (accept gas cost), transition to Option B/C as infrastructure matures. The gas cost is acceptable for SOS's transaction volume (not a high-frequency trading chain).

### 6.7 Layer 6: Governance

**Current**: OPRLP contracts (DPCRegistry, GovernanceWeight, ElectionEngine, CouncilManager) on EVM.

**Post-Quantum**:
- **Standard governance**: ML-DSA-65 signed votes, DPC score as weight
- **Constitutional operations**: Require SLH-DSA-128s signatures (root keys only)
  - Constitutional amendments, founder sunset, emergency power invocation
- **Behavioral proofs for high-stakes votes**: STARK proof of DPC history
  - Voter proves: "My DPC score ≥ 2000 AND active contributions in last 90 days"
  - Without revealing: exact score, specific contributions, identity details
- **Emergency powers**: Unchanged 72-hour auto-expiry, but invocation requires Tier 2 + Tier 3 attestation
- **Cartel detection**: Graph analysis of attestation patterns (behavioral layer, not crypto-dependent)
- **Founder sunset**: Immutable contract with PQ signatures for phase transition triggers

**The governance layer is where the dual-trust architecture shines**: A quantum attacker who compromises ML-DSA keys can forge signatures but CANNOT pass the behavioral proof requirement for constitutional operations. The STARK proof of DPC history requires a genuine contribution record anchored over time.

---

## 7. Key Decisions

### Decision 1: Behavioral trust as primary, crypto as secondary
**Chosen**: Invert the trust hierarchy. DPC behavioral record is the primary trust anchor; PQ cryptography reinforces it.
**Why**: Every PQC project treats crypto as primary. If lattice assumptions break (possible, not proven), they all fail simultaneously. SOS needs a trust model that survives even if PQC fails.
**Alternative rejected**: Crypto-primary with behavioral as supplementary (standard approach). Simpler to implement but doesn't solve the meta-problem of assumption fragility.
**Tradeoff**: Behavioral trust is slow to establish. New contributors have weak behavioral identity for months. Mitigation: Tier 1 (crypto) is sufficient for standard operations; Tier 2 (behavioral) only required for high-stakes actions.

### Decision 2: ML-DSA-65 over ML-DSA-87 for general signing
**Chosen**: 192-bit security (ML-DSA-65) not 256-bit (ML-DSA-87).
**Why**: 2,420-byte signatures vs 4,595 bytes. SOS operates on bandwidth-constrained mesh networks and gas-constrained L2 chains. 192-bit is sufficient against known quantum attacks (Grover reduces to 96-bit effective on hash, but Shor doesn't gain from higher security levels). NIST recommends ML-DSA-65 for most applications.
**Alternative rejected**: ML-DSA-87 (maximum security). Unnecessary overhead for the threat model; 192-bit is the floor for meaningful quantum resistance.

### Decision 3: STARKs over lattice-based SNARKs for ZK
**Chosen**: Hash-based STARKs (SP1/RISC Zero) replacing Groth16.
**Why**: STARKs have NO cryptographic assumptions beyond hash function security — they are quantum-safe by construction, not by assumption. No trusted setup eliminates a centralization risk. Proof size is larger but acceptable for SOS's use case (batch verification, not per-transaction).
**Alternative rejected**: Lattice-based SNARKs (active research, smaller proofs). Not production-ready; introduces lattice assumptions into the ZK layer, creating correlation risk with the signature layer.

### Decision 4: FN-DSA-512 for on-chain, ML-DSA-65 for off-chain
**Chosen**: Two PQ signature schemes for different contexts.
**Why**: FN-DSA (FALCON) produces 666-byte signatures vs ML-DSA's 2,420 bytes — 3.6x smaller, meaning significantly lower gas costs for on-chain verification. Algorand has 4 years of production FALCON data. Off-chain operations (identity, mesh, VCs) use ML-DSA for broader ecosystem compatibility and simpler key management.
**Alternative rejected**: Single algorithm everywhere (ML-DSA-65). Simpler but gas costs for on-chain operations become prohibitive at scale.

### Decision 5: Crypto-agility layer from Phase 1
**Chosen**: Algorithm abstraction layer with registry, not hardcoded primitives.
**Why**: The quantum transition is not the last algorithm migration. Lattice assumptions may fall. New NIST standards may emerge. Designing for algorithm hot-swap from day one avoids the "hard fork to change a signature scheme" problem that Bitcoin and Ethereum face now.
**Alternative rejected**: Direct algorithm implementation (simpler Phase 1). Saves 2-3 weeks initially but creates permanent technical debt.

### Decision 6: No custom L1 chain
**Chosen**: Deploy on existing EVM L2s (Polygon zkEVM, Base) with PQ signature libraries.
**Why**: Running a sovereign L1 requires consensus mechanism, validator set, bridge infrastructure, and ongoing operations. SOS's value is in governance and behavioral trust, not in consensus innovation. EVM L2s provide sufficient security, low gas, and broad tooling. When L2s add PQ precompiles, SOS benefits automatically.
**Alternative rejected**: Custom PQ-native L1 (like QRL). Maximum crypto sovereignty but massive operational cost and ecosystem fragmentation. SOS is a governance framework, not a consensus protocol.

---

## 8. Implementation Plan

### Phase 0: Immediate Hygiene (Week 1-2, ~$0)
1. Audit all deployed contracts for address reuse patterns
2. Document every exposed public key in current on-chain anchors
3. Enforce single-use addresses in ONEON SDK
4. Write HNDL exposure assessment for existing SOS data
5. Pin this architecture doc as the reference specification

### Phase 1: Crypto-Agility Foundation (Weeks 3-8, ~$8-12)
1. Implement `SignatureProvider` interface in ONEON SDK
2. Add ML-DSA-65 key generation to ONEON identity creation
3. Deploy hybrid dual-signing in VC issuance (Ed25519 ∥ ML-DSA)
4. Upgrade `RecordAnchor.sol` to accept algorithm-prefixed signatures
5. Test ML-KEM-768 in mesh Noise handshake (libp2p integration)
6. Deploy `DPCRegistry.sol` upgrade accepting PQ signer verification

### Phase 2: Full PQ Primary (Weeks 9-16, ~$15-20)
1. Migrate Groth16 circuits to SP1 STARKs (eligibility proofs)
2. Implement STARK-based attribute proofs for selective disclosure
3. Deploy FN-DSA-512 on-chain signature verification library
4. Implement behavioral proof protocol (STARK proof of DPC history)
5. Upgrade OPRLP governance contracts for PQ signatures
6. Test full PQ pipeline: identity → credential → proof → governance

### Phase 3: Legacy Sunset (Weeks 17-22, ~$5-8)
1. Deprecate classical-only signatures in smart contracts
2. Implement DID migration protocol for existing ONEON identities
3. Deploy crypto-agility registry (DAO-governed algorithm management)
4. Run migration campaign for active contributors
5. Publish post-quantum audit report
6. Mark Ed25519/ECDSA as verify-only in all SOS systems

**Total estimated cost: ~$28-40**
**Total estimated timeline: 22 weeks (5.5 months)**

---

## 9. Risks

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| CRQC arrives before Phase 2 completes | Low (10% by 2028) | Critical — all classical sigs broken | Phase 0 + Phase 1 provide partial protection; behavioral trust (DPC) continues to function |
| ML-DSA/ML-KEM lattice assumptions broken | Very low (<5% in 10 years) | High — PQ crypto layer fails | SLH-DSA backup for root keys; behavioral trust (Tier 2/3) operates independently of crypto |
| STARK proof generation too slow for mobile | Medium | Degrades UX for ZK operations | Offload proof generation to community nodes; accept 30-second latency for non-time-critical ops |
| EVM L2s slow to add PQ precompiles | High | Higher gas costs for on-chain PQ verify | Accept Solidity-level verification cost; monitor L2 PQ roadmaps |
| Selective disclosure gap (no PQ BBS+ equivalent) | High (until ~2028) | Reduced privacy for VC operations | STARK attribute proofs as interim; larger proof size is acceptable |
| Community migration fatigue (users don't migrate keys) | Medium | Classical keys remain exposed | Auto-migration on next app update; make PQ key generation transparent to user |
| QR code size increase for PQ public keys | High | Offline enrollment UX degrades | QR contains CID pointer to key, not raw key material; keeps QR size manageable |

---

## 10. Relationship to Existing Specs

| Document | Relationship |
|---|---|
| [IPL Spec](../projects/sos-systems/integrity-preservation-layer.md) | This framework upgrades every cryptographic primitive in the IPL |
| [S0S Architecture](../docs/s0s-systems-architecture-2026-03-20.md) | Behavioral trust layer formalizes what the DPC section describes informally |
| [OPRLP Contracts](../docs/oprlp-solidity-architecture-2026-03-27.md) | All 7 contracts require PQ signature migration per this framework |
| [Quantum Threats Research](../research/quantum-threats-blockchain-2026-04-12.md) | Technical foundation for Section 1 (threat model) and Section 2 (algorithm selection) |
| [Quantum Trust Philosophy](../docs/quantum-trust-philosophy-synthesis-2026-04-12.md) | Philosophical foundation for Section 4 (novel trust mechanisms) |
| [ONEON Invisible Web3 Layer](../docs/oneon-invisible-web3-layer-architecture-2026-03-28.md) | ONEON identity migration path defined here |
| [Narrative Brief](../docs/sos-systems-narrative-brief-2026-03-23.md) | Section 5 (value proposition) provides technical backing for positioning claims |
| [zkPresence Standalone](../docs/zkpresence-standalone-service-architecture-2026-04-11.md) | zkPresence Groth16/BN254 requires same STARK migration |

---

*The lock was never the foundation. The history of showing up was.*

*Architecture by Otto | Review by Mev before implementation | Next step: Phase 0 hygiene audit*

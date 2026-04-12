# The Dynamic Public Key Primitive: Stable Identity, Rotating Authority

*A design concept for the SOS Systems / zkPresence ecosystem*

---

## Abstract

A zkPresence identity anchored to a single static secret is a single point of failure: lose it, and the identity is gone; expose it, and it is stolen permanently. This paper describes a designed cryptographic primitive — the Dynamic Public Key (DPK) — that separates stable on-chain identity from rotating signing authority via a three-layer architecture. A biometric-passphrase commitment anchors identity permanently on-chain; epoch-bounded ephemeral keys carry signing authority and rotate without touching that commitment; per-action ZK proofs bind individual operations to authority with one-time nullifiers. The primitive is designed to serve the full SOS Systems / zkPresence ecosystem — zkPresence, ONEON, SOS, and Koink — through a single shared on-chain registry.

---

## 1. The Problem: Identity That Breaks

The current zkPresence identity construction is straightforward:

    identity_commitment = SHA256(user_secret)

`user_secret` is a random 32-byte value generated once and stored on the user's device.

This construction has three failure modes that compound each other.

**Loss.** If the user loses their device — or their backup — the secret is gone. The identity_commitment is on-chain permanently, but no one can prove ownership of it. The user's attendance record, reputation, and accumulated state become inaccessible.

**Compromise.** If the secret is exposed — malware, shoulder surfing, an intercepted backup — an attacker can sign any proof forever. There is no revocation. The commitment is static; so is the attacker's access.

**No rotation path.** The identity IS the secret. To rotate, you would need to migrate on-chain state to a new commitment — an operation that cannot be made trustless without either a centralized migration authority or user cooperation that cannot be enforced.

The broader ecosystem compounds this problem. ONEON needs a stable identity anchor for decentralized social graphs. SOS needs reputation that survives key management events. Koink needs treasury authentication that is recoverable. A secret that cannot be rotated and cannot be recovered is not a foundation — it is a liability.

---

## 2. The Pattern: Lessons from zkLogin

The right model already exists in production.

zkLogin, deployed by Sui, separates the address (stable, on-chain) from the signing key (ephemeral, short-lived) via a ZK proof. An OAuth JWT from a known provider certifies: this ephemeral key was generated for this Google account. The on-chain address is derived from the OAuth subject identifier — it never changes. The ephemeral key rotates every session. The ZK proof bridges the two, and no private key is ever exposed to the chain.

The insight is transferable. Replace the OAuth JWT — a centralized attested claim — with a biometric-passphrase commitment verified locally on the device. Replace the OAuth provider's public key — a trust anchor external to the user — with the user's own derived master secret, produced by combining something they are (iris biometric) with something they know (passphrase). The structure is identical: stable address, rotatable signing authority, ZK proof binding the two.

This is the architecture the Dynamic Public Key primitive is designed to implement.

---

## 3. Three-Layer Key Architecture

The design decomposes key management into three distinct layers, each with a different lifetime and different security properties.

    +--------------------------------------------------+
    |  LAYER 1 - IDENTITY                              |
    |  identity_commitment = SHA256(master_secret)     |
    |  Lifetime: permanent. On-chain. Never changes.   |
    +--------------------------------------------------+
                            |
                     ZK proof (KeyBinding)
                            |
    +--------------------------------------------------+
    |  LAYER 2 - AUTHORITY                             |
    |  Ephemeral secp256k1 key pair                    |
    |  Lifetime: epoch-bounded (default 24h)           |
    |  Rotation: new pair + new binding proof          |
    +--------------------------------------------------+
                            |
                   ZK proof (Attendance / Action)
                            |
    +--------------------------------------------------+
    |  LAYER 3 - ACTION                                |
    |  Per-action ZK proof with nullifier              |
    |  Lifetime: one-time use. Replay-prevented.       |
    +--------------------------------------------------+

Layer 1 is the persistent on-chain anchor. It is the only thing other contracts, reputation systems, and social graphs need to reference. It cannot be rotated, and it does not need to be.

Layer 2 is where operational security lives. Ephemeral keys carry the actual signing authority. If a key is compromised, it expires at epoch boundary. If a user rotates proactively, the old key is simply superseded. The identity in Layer 1 is untouched.

Layer 3 is where actions are proven. Each action — attendance, claim, vote — is bound to the current ephemeral key via a ZK proof, and a nullifier prevents the same proof from being submitted twice.

---

## 4. Cryptographic Construction

All derivation is designed to occur on the user's device. Nothing leaves the device until Layer 2 or later.

**Biometric extraction.** Raw iris data is processed by a fuzzy extractor:

    bio_key = FuzzyExtract(iris, helper)

The fuzzy extractor converts the noisy biometric into a stable 32-byte key. It outputs two values: `bio_key` (secret) and `helper` (public). `helper` can be stored or transmitted openly without revealing `bio_key` — it provides enough information to re-derive `bio_key` from a matching biometric, but not to reconstruct it directly. The CCS 2025 iris construction targets 105 bits of residual entropy against an attacker with the helper string.

**Passphrase derivation.** The passphrase is processed by Argon2id:

    pass_key = Argon2id(passphrase, salt)

Argon2id is selected specifically because it is memory-hard. An attacker without access to the device must brute-force the passphrase against a function that requires approximately 64MB of memory and significant compute time per guess. The salt is device-stored.

**Key combination.** `bio_key` and `pass_key` are combined via HKDF-SHA256 (RFC 5869):

    master_secret = HKDF-SHA256(bio_key || pass_key, info="zkpresence-master-v1")

HKDF is used here for two reasons. First, it produces uniformly distributed output from inputs that may themselves have non-uniform entropy distributions. Second, the `info` field provides domain separation — the same input keys used for a different purpose with a different info string would produce a completely different master_secret. Naive concatenation provides neither guarantee.

**Identity commitment.** The on-chain anchor:

    identity_commitment = SHA256(master_secret)

**Argon2 Path B — the critical design decision.** Proving Argon2id inside a ZK circuit would require millions of constraints — computationally prohibitive for practical proof generation times. The design follows the approach used in zkLogin: compute Argon2id on the device (trusted), then commit to the output. The circuit proves SHA256(pass_key) == stored_commitment. This trades in-circuit proof of password hardness for device-side computation of it. The security model shifts: we trust that the device computed Argon2id correctly. This is the correct tradeoff for a mobile or browser context where the device is already a trust boundary.

---

## 5. The Key Binding Protocol

The KeyBinding circuit is the cryptographic heart of the primitive. It is designed to prove, without revealing master_secret, that a given ephemeral public key was generated by an identity holder during a specific epoch.

**Inputs and outputs (designed):**

    PRIVATE:  master_secret: [u8; 32]
    PUBLIC:   eph_pk: [u8; 33]        # compressed secp256k1
              epoch: u64
              max_epoch: u64
    OUTPUTS:  identity_commitment: bytes32
              eph_pk_hash: bytes32
              epoch: uint64
              max_epoch: uint64
              key_nonce: bytes32

key_nonce = SHA256(master_secret || eph_pk || epoch). This value is unique to every rotation — it changes with the epoch, with the key, and is tied to the secret. It is the replay prevention mechanism for the binding proof itself.

**What the circuit is designed to prove.** SHA256(master_secret) equals the on-chain identity_commitment, and the ephemeral public key was committed to alongside a valid epoch window.

**What the circuit deliberately does not prove.** It does not prove that the ephemeral key was generated randomly or that the device is honest. It does not prove that biometric extraction occurred correctly, that Argon2id was computed with the correct parameters, or that a human is physically present. The circuit's scope is narrow by design. Proving more in-circuit would increase constraint count and introduce unproven implementations of complex primitives into a sensitive security context.

**Circuit selection.** The KeyBinding circuit is designed for Groth16. Key rotation does not require circuit changes — only the witness (master_secret, eph_pk, epoch) changes per rotation. The circuit is compiled once. Groth16's trusted setup cost is paid once. PLONK's primary advantage — no re-ceremony on circuit changes — is relevant only if the circuit itself changes frequently, which is not the expected operational pattern.

---

## 6. On-Chain Architecture

DynamicKeyRegistry.sol is designed as the on-chain counterpart to the KeyBinding circuit. It is not yet deployed.

The registry is designed to accept KeyBinding proofs and maintain a mapping:

    identity_commitment => eph_pk_hash => max_epoch

**Epoch advancement.** Epochs are stateless: current_epoch = block.timestamp / EPOCH_DURATION. No counter needs to be stored or incremented. Any contract can compute the current epoch locally without a registry lookup. Key validity is checked by: current_epoch <= max_epoch.

**Nonce tracking.** The registry is designed to track submitted key_nonces. A KeyBinding proof containing a previously recorded nonce would be rejected. Since key_nonce incorporates master_secret, eph_pk, and epoch, a valid nonce from a prior rotation cannot be reused for a new rotation or resubmitted under a different epoch.

**Read efficiency.** isKeyValid() is designed as a view function — reads from storage without writing to it. Ecosystem contracts that check key validity pay no gas for the read. Only proof submission (key registration) requires a transaction.

**Rotation.** To rotate, the user generates a new secp256k1 key pair on device, produces a new KeyBinding proof with the new eph_pk and a new epoch window, and submits it. The old key expires naturally when its max_epoch passes. No explicit revocation step is needed — epoch expiry is sufficient.

---

## 7. Security Properties and Known Constraints

**What the design is intended to guarantee.**

Multi-factor resistance. An attacker who wants to derive master_secret must compromise the iris biometric, the FuzzyExtract helper string, and the passphrase. Any single factor is insufficient.

Epoch-bounded compromise. If an ephemeral key is stolen, it is valid for at most max_epoch epochs from issuance — configured to 24 hours by default, capped at 30 epochs.

Proof replay prevention. key_nonce changes with every rotation. A submitted binding proof cannot be resubmitted; a proof for a past rotation cannot be repurposed for a new one.

Biometric privacy. The raw iris image and the raw bio_key are designed to never leave the device. The ZK circuit does not operate on biometric data directly. This satisfies the design intent of GDPR Article 9 — special category biometric data is processed locally, never transmitted.

**Known constraints and honest tradeoffs.**

Biometric permanence. Iris biometrics are stable but not immutable across a lifetime. Age, disease, or surgery can alter the iris enough that FuzzyExtract fails to reproduce bio_key. Recovery paths — alternative factor registration, social recovery — are out of scope for this primitive.

Device trust for Argon2. The Argon2 Path B design trusts the device to compute Argon2id correctly. A compromised device could produce a valid pass_key from a weaker computation and the circuit would not detect this. This is the same trust boundary accepted by every mobile wallet and every browser-side key derivation scheme in production.

Epoch window tradeoff. Longer epochs reduce rotation friction; they also extend the validity window of a compromised key. 24 hours is the default. This is a configurable parameter, not a cryptographic constant.

SP1 trusted setup. Groth16 proofs require a trusted setup ceremony per circuit. The security of all proofs depends on at least one participant in the ceremony having destroyed their randomness. This is a standard Groth16 constraint.

---

## 8. Ecosystem Integration

The primitive is designed as a shared infrastructure layer, with one DynamicKeyRegistry deployment intended to serve all ecosystem contracts.

**zkPresence.** Attendance proofs are designed to accept an optional ephemeral key authentication path alongside the existing direct proof submission. The existing verifyAttendance() interface would remain unchanged; the ephemeral path is additive.

**ONEON.** identity_commitment is designed to anchor the decentralized identity graph. Ephemeral keys would handle session authentication — posting, connecting, signing — with rotation invisible to the social graph layer.

**SOS / DPC.** Reputation scores are designed to bind to identity_commitment, not to any ephemeral key. A key rotation event would not affect accumulated reputation. The scoring ledger is separated from the operational authentication layer.

**Koink.** Treasury claim authentication is designed to use ephemeral key signatures. A user would prove key validity via the registry and sign a claim with their current ephemeral key, without exposing master_secret or requiring a new ZK proof per claim.

**Backward compatibility.** Existing Phase 1 users with raw user_secret are compatible without migration. Their user_secret is treated as master_secret. SHA256(user_secret) produces the same identity_commitment. The existing verifyAttendance() path continues to function without modification.

---

## 9. Implementation Roadmap

All phases below are planned and not yet begun.

**Phase 1** — Wire SHA-256 and ECDSA precompiles into the existing SP1 circuit. Prerequisite for in-circuit key commitment verification. Estimated cost: approximately $3-4.

**Phase 2a** — Key derivation module: implement HKDF, Argon2id, and SHA-256 commitment in Rust. Estimated: approximately $1-2.

**Phase 2b** — KeyBinding circuit: implement the circuit described in Section 5, compile, run Groth16 trusted setup ceremony. Estimated: approximately $2-3.

**Phase 2c** — On-chain contracts: DynamicKeyRegistry.sol and the ZkPresence.sol extension. Base Sepolia testnet deployment. Estimated: approximately $3-4.

**Phase 2d** — TypeScript SDK: client-side key generation, proof generation, and registry interaction. Estimated: approximately $2-3.

**Phase 3 (deferred)** — PLONK migration if circuit iteration frequency warrants it. Recursive proof composition if attestation flows require in-circuit key verification. Post-quantum migration to ML-DSA for ephemeral signatures when the ecosystem threat model requires it.

---

## 10. Conclusion

Identity that cannot rotate is identity that cannot survive.

The Dynamic Public Key primitive is designed to give zkPresence users — and by extension the full SOS Systems ecosystem — a stable on-chain anchor derived from who they are and what they know, with signing authority that rotates on a short cycle, recovers gracefully, and leaves accumulated reputation intact.

The architecture borrows nothing that has not been proven elsewhere. Fuzzy extractors for biometric key derivation, Argon2id for passphrase hardening, HKDF for key combination, Groth16 for efficient ZK proof generation, epoch-based expiry for stateless revocation — each component is established. What this primitive contributes is the specific composition: three layers, cleanly separated, designed to serve a shared identity across a multi-contract ecosystem.

*This is what infrastructure looks like when it is built once and used everywhere.*

---

*SOS Systems — zkPresence / ONEON / SOS / Koink*
*Design concept document — Version 0.1 — April 2026*

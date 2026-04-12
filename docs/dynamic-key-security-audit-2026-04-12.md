# Dynamic Public Key System — Security Audit & Threat Model
*Blockchain Security Auditor — 2026-04-12*

**Scope:** Architecture-level security audit of the three-layer dynamic key system (Identity / Authority / Action) as specified in `docs/dynamic-public-key-architecture-2026-04-12.md`. Focus: novel attack vectors not covered by the original threat model.

**Architecture under audit:**
- Layer 1: `identity_commitment = SHA256(HKDF(FuzzyExtract(bio) || Argon2(pass), salt))` — stable on-chain
- Layer 2: Ephemeral secp256k1 key pairs, epoch-bounded, ZK-certified via KeyBinding circuit
- Layer 3: Per-action ZK proofs binding actions to authority
- On-chain: `DynamicKeyRegistry.sol` (epoch system, key binding verification), `ZkPresence.sol` (attendance with optional ephemeral key auth)

---

## 1. Biometric Replay Attacks

**Question:** Can a captured biometric sample re-derive keys across sessions?

### 1.1 Attack: Raw Biometric Capture → Master Secret Recovery

**Vector:** Attacker captures a user's iris scan (e.g., covert photography, compromised sensor, or a leaked biometric database). They attempt to re-run FuzzyExtract with the stolen biometric to recover `bio_key`, then combine with a brute-forced passphrase to derive `master_secret`.

**Severity: HIGH**

**Analysis:**
- The fuzzy extractor construction requires TWO inputs: `iris_raw` + `helper_string`. The `helper_string` is stored on the user's device and is technically public (not secret), but an attacker must obtain both.
- If the attacker has the raw iris scan AND the helper string (e.g., device compromise or backup extraction), they can deterministically reproduce `bio_key = FuzzyExtract(iris_raw, helper_string)`. The fuzzy extractor is deterministic by design — same biometric + same helper → same key.
- The biometric factor alone is insufficient: the attacker still needs the passphrase (Argon2id with t=3, m=64MB, p=4 — reasonably strong). But the biometric factor is now eliminated, reducing the system to single-factor (passphrase only).
- **Cross-session replay is total:** Biometrics don't change. Unlike a password, you can't rotate your iris. If `iris_raw` is compromised, that factor is permanently burned for this identity.

**Mitigations present:** Passphrase as second factor. Argon2id memory-hardness raises brute-force cost.

**Mitigations missing:**
- No liveness detection requirement specified in the architecture. A high-resolution iris photograph could work.
- No biometric template revocation mechanism. If biometric data leaks, the user cannot "rotate" their iris — they must create an entirely new identity (new bio_key from a different biometric modality, or accept single-factor).
- No rate-limiting on identity derivation attempts (device-side computation — no server involvement).

**Recommendation:**
- **[P1]** Specify mandatory liveness detection in the client SDK for biometric capture (anti-replay: challenge-response with sensor, randomized gaze patterns for iris).
- **[P1]** Design a biometric template migration path: allow users to re-bind identity to a different biometric modality (e.g., switch from iris to fingerprint) via an identity migration ceremony that preserves `identity_commitment` but updates the derivation path.
- **[P2]** Consider binding `helper_string` to a device-specific secret (e.g., TEE/Secure Enclave key) so that biometric replay requires the specific device, not just the helper data.

---

## 2. Fuzzy Extractor Helper Data Leakage

**Question:** Does the helper data (public) reveal partial key information?

### 2.1 Attack: Helper String → Partial Bio Key Information Leakage

**Vector:** The `helper_string` produced by `FuzzyExtract.Gen(iris_raw)` is stored on the user's device and explicitly stated to be "not secret" in the architecture. An attacker obtains this helper string (device backup, cloud sync, physical access). The question is whether it leaks information about `bio_key`.

**Severity: MEDIUM**

**Analysis:**
- In the Dodis et al. (2006) secure sketch / fuzzy extractor construction, the helper string `h` is defined such that `H∞(bio_key | h) ≥ H∞(bio_key) - λ`, where `λ` is the entropy loss parameter. The CCS 2025 iris construction achieves 105-bit effective entropy.
- However, the helper string IS an error-correcting code applied to the biometric template. It reveals the *structure* of the biometric — specifically, which bits are noisy (error-correcting redundancy) and the coset of the biometric in the code space. This is by construction, not a bug.
- **Entropy loss is real:** The helper string reduces the effective entropy of the biometric secret from the raw biometric's min-entropy down to the residual entropy. For the CCS 2025 iris construction: raw iris entropy (~250 bits) → 105 bits after helper publication. This is a 2.4x entropy reduction.
- **Template reconstruction risk:** Given `h`, an attacker who knows the fuzzy extractor construction can enumerate the possible biometric templates compatible with `h`. The search space is reduced from the full biometric space to `2^105` candidates — still infeasible for brute force, but significantly smaller.
- **Cross-identity correlation:** If two users' helper strings are computed with the same fuzzy extractor parameters, an attacker can compare `h1` and `h2` to determine if the underlying biometrics are similar. This enables biometric linkability across identities without having the raw biometrics.

**Severity rationale:** MEDIUM because 105-bit residual entropy is sufficient for security, but the information leakage is non-zero and the cross-identity correlation risk is a privacy concern for a system that claims unlinkability.

**Mitigations present:** Architecture states helper string is "stored locally, not secret" — correct framing.

**Mitigations missing:**
- No specification of which fuzzy extractor construction to use (computational vs. information-theoretic). The security properties differ significantly.
- No analysis of entropy loss for the chosen biometric modality.
- No protection against helper string comparison attacks (cross-identity biometric linkability).

**Recommendation:**
- **[P1]** Specify the exact fuzzy extractor construction (e.g., computational fuzzy extractor from CCS 2025) and document the entropy loss parameter `λ` in the architecture. Assert minimum residual entropy ≥ 100 bits.
- **[P2]** Add a random blinding factor to the helper string: `h' = h ⊕ PRF(device_key, "helper-blind")`. This prevents cross-device helper comparison while allowing the same device to reproduce `bio_key`. Tradeoff: helper becomes device-bound.
- **[P2]** Document that helper strings MUST NOT be backed up to cloud services or transmitted between devices. Cross-device identity migration requires re-enrollment (new `FuzzyExtract.Gen` on the new device).

---

## 3. ZK Soundness — Proof Forgery Without Derivation Root

**Question:** Can a prover forge a valid KeyBinding or Attendance proof without knowing `master_secret`?

### 3.1 Attack: KeyBinding Proof Forgery

**Vector:** Attacker wants to register an ephemeral key for a victim's `identity_commitment` without knowing the victim's `master_secret`. They attempt to forge a KeyBinding ZK proof.

**Severity: LOW (contingent on SP1 soundness)**

**Analysis:**
- The KeyBinding circuit proves: "I know `master_secret` such that `SHA256(master_secret) == identity_commitment`." This is a preimage proof.
- SP1 zkVM soundness: SP1 produces Groth16 proofs over a RISC-V execution trace. The soundness of the overall system depends on:
  1. SP1 compiler correctness (Rust → RISC-V ELF → execution trace)
  2. SP1 arithmetization correctness (execution trace → R1CS/AIR)
  3. Groth16 proof system soundness (knowledge soundness under KEA)
  4. Trusted setup integrity (per-program CRS)
- **Under standard assumptions, proof forgery is computationally infeasible.** An attacker cannot produce a valid Groth16 proof for a false statement without breaking the q-DLOG assumption or subverting the trusted setup.
- **Trusted setup risk:** Groth16 requires a per-program trusted setup (CRS generation). If the toxic waste from CRS generation is retained, forgery is trivial. SP1's Succinct Network manages ceremonies, but the trust assumption transfers to Succinct.

### 3.2 Attack: Malicious Circuit Compilation

**Vector:** Attacker compromises the SP1 toolchain or introduces a backdoor in the circuit compilation pipeline. The compiled ELF binary is included via `include_elf!("zkpresence-circuit")` — if this binary is swapped, the on-chain verifier would accept proofs for a different (weaker) circuit.

**Severity: MEDIUM**

**Analysis:**
- `programVKey` is immutable in the contract (`bytes32 public immutable programVKey`). Once deployed, only proofs from the compiled circuit are accepted. This is correct.
- However, if the circuit is compiled with a backdoored toolchain, the `programVKey` itself is compromised from day one. The contract would faithfully verify proofs from a circuit that doesn't actually enforce the intended constraints.
- This is a supply chain attack, not a soundness break — but the effect is identical: forged proofs accepted.

### 3.3 Attack: Public Input Manipulation

**Vector:** Attacker submits a valid proof but manipulates the public values during on-chain submission (e.g., change `identity_commitment` in the ABI-encoded `publicValues` before calling `verifyAttendance`).

**Severity: NONE (correctly mitigated)**

**Analysis:** The SP1 verifier verifies the proof against the provided `publicValues`. Any modification to `publicValues` after proof generation invalidates the proof. The contract correctly calls `verifier.verifyProof(programVKey, publicValues, proof)` before decoding `publicValues`. This is sound.

**Recommendation:**
- **[P1]** Document the trusted setup trust model: who manages the CRS, how is toxic waste destroyed, is there a multi-party ceremony? If relying on Succinct Network, document the trust assumption explicitly.
- **[P2]** Implement reproducible circuit builds (deterministic `include_elf!` compilation) so the `programVKey` can be independently verified by any party.
- **[P3]** For Phase 3 PLONK migration: PLONK's universal trusted setup eliminates per-circuit CRS risk. Accelerate this migration if soundness is a primary concern.

---

## 4. Key Rotation Griefing

**Question:** Can an attacker block or spam rotations to lock a user out?

### 4.1 Attack: Epoch Advance Griefing

**Vector:** `advanceEpoch()` is permissionless — anyone can call it. An attacker calls `advanceEpoch()` repeatedly to advance the epoch counter faster than expected, causing ephemeral keys to expire prematurely.

**Severity: NONE**

**Analysis:** `advanceEpoch()` is computed from `(block.timestamp - epochStart) / EPOCH_DURATION`. It is purely deterministic based on wall-clock time. Calling it multiple times has no effect — it converges to the same epoch value. An attacker cannot accelerate time. This is correctly designed.

### 4.2 Attack: Key Registration Front-Running

**Vector:** Attacker monitors the mempool for `registerKey()` transactions. They front-run with a transaction that registers a DIFFERENT ephemeral key for the victim's identity.

**Severity: NONE (correctly mitigated by ZK proof)**

**Analysis:** `registerKey()` requires a valid ZK proof binding `master_secret → identity_commitment → eph_pk_hash`. An attacker cannot produce a valid proof without the victim's `master_secret`. Front-running is impossible because the proof itself authenticates the registrant.

### 4.3 Attack: Key Nonce Exhaustion / Replay

**Vector:** Attacker re-submits a previously used `registerKey()` transaction to consume the nonce and prevent the user from registering a new key.

**Severity: NONE (correctly mitigated)**

**Analysis:** `keyNonceUsed[keyNonce]` prevents replay. The nonce is derived as `SHA256(master_secret ‖ eph_pk ‖ epoch)`, which is deterministic for a given key+epoch combination. An attacker cannot forge a new nonce without `master_secret`. Replaying an old transaction hits the nonce-used check.

### 4.4 Attack: Storage Slot Griefing (Key Overwrite)

**Vector:** A user registers key A, then the attacker (somehow) registers key B for the same identity, overwriting key A's expiry in the `keyExpiry` mapping.

**Severity: NONE (mitigated by ZK proof)**

**Analysis:** Same as 4.2. The attacker needs `master_secret` to produce a valid KeyBinding proof. Without it, they cannot register any key for the victim's identity. The contract correctly requires a valid proof before writing to `keyExpiry`.

### 4.5 Attack: Gas Griefing on Key Registration

**Vector:** Attacker submits many invalid `registerKey()` transactions to congest the network and increase gas costs for the victim's legitimate registration.

**Severity: LOW**

**Analysis:** Invalid proofs fail at `verifier.verifyProof()`, which is the first operation. Gas is consumed but the attack is expensive for the attacker (they pay gas for failed transactions). On Base L2, gas costs are extremely low — the attack is economically infeasible for meaningful impact.

**Verdict:** Key rotation griefing is well-defended. The ZK proof requirement at registration time is the critical design choice that prevents most griefing vectors.

---

## 5. Quantum Threat Model

**Question:** Does rotating keys fully close Shor's attack window, or just shrink it?

### 5.1 Analysis: What Shor Breaks

Shor's algorithm breaks:
- **ECDSA secp256k1** (Layer 2 ephemeral keys, organizer signatures)
- **Groth16 proofs** (BN254 pairing-based — the trusted setup and verification rely on discrete log)
- **secp256k1 key recovery** from public keys visible on-chain

Shor does NOT break:
- **SHA-256** (Grover gives 2^128 → still infeasible)
- **HKDF** (hash-based)
- **Argon2** (memory-hard hash)

### 5.2 Attack: HNDL on Registered Ephemeral Keys

**Vector:** Nation-state collects all `KeyRegistered` events from the chain. Each event contains `identityCommitment` and `ephPkHash`. When a CRQC arrives, they:
1. Cannot directly recover `master_secret` from `identity_commitment` (SHA-256 preimage — quantum-safe)
2. Cannot directly recover `eph_sk` from `ephPkHash` (SHA-256 preimage — quantum-safe)
3. BUT: if the ephemeral PUBLIC KEY (not just its hash) is ever exposed — e.g., in a `verifyAttendanceWithKey` transaction where the signature is submitted on-chain — then Shor can recover `eph_sk` from the public key.

**Severity: HIGH**

**Analysis:**
- The architecture stores `ephPkHash` (SHA256 of compressed pubkey) on-chain, not the raw public key. This is correct — the hash protects against direct Shor recovery from on-chain state.
- **However:** `verifyAttendanceWithKey()` accepts an `ephSignature` parameter. To verify an ECDSA signature, the verifier (contract) uses `ECDSA.recover(digest, sig)` which returns the signer's Ethereum address (derived from the public key). The public key is recoverable from any ECDSA signature + message by design.
- Every `verifyAttendanceWithKey()` call exposes the ephemeral public key to any observer (the signature is in calldata, the message is deterministic). An HNDL collector stores this. Post-quantum, they recover `eph_sk` from the public key via Shor's.
- **With `eph_sk`, the attacker can sign on behalf of that identity for the remaining epoch window.** Key rotation shrinks the window but does not close it — the attack degrades from "permanent identity theft" to "temporary key compromise for the epoch duration."
- **Identity commitment is quantum-safe:** The attacker recovers ephemeral keys, not `master_secret`. They can impersonate the user temporarily but cannot derive the stable identity or forge KeyBinding proofs (which require SHA-256 preimage).

### 5.3 Attack: HNDL on Groth16 Proofs

**Vector:** All Groth16 proofs are on-chain. Post-quantum, an attacker with access to the CRS toxic waste OR the ability to break the pairing assumption can forge arbitrary proofs.

**Severity: CRITICAL (architectural, not rotation-specific)**

**Analysis:**
- Groth16's soundness relies on the q-PKE assumption over BN254 pairings. Shor breaks the discrete log problem on BN254, which breaks the pairing assumption, which breaks Groth16 soundness entirely.
- Post-quantum, an attacker can forge KeyBinding proofs (binding arbitrary ephemeral keys to any identity) and Attendance proofs (claiming attendance without attending).
- **Key rotation does not help here.** The attack is on the proof system itself, not the key. Even with fresh keys, a forged KeyBinding proof registers them.
- **The identity layer (SHA-256 commitment) survives** — the attacker can't change what `identity_commitment` maps to. But they can bind arbitrary keys to it.

### 5.4 Verdict: Rotation Shrinks But Does Not Close the Window

| Component | Quantum Status | Rotation Effect |
|---|---|---|
| `identity_commitment` (SHA-256) | **SAFE** | N/A — never rotates |
| `master_secret` derivation (HKDF+Argon2) | **SAFE** | N/A |
| Ephemeral keys (secp256k1) | **BROKEN** by Shor | Rotation limits exposure to epoch window |
| Organizer signatures (secp256k1) | **BROKEN** by Shor | Not rotatable — organizer key is fixed per event |
| Groth16 proofs (BN254) | **BROKEN** by Shor | Rotation irrelevant — proof system itself is broken |
| KeyBinding circuit (Groth16) | **BROKEN** by Shor | Cannot issue new bindings under broken proof system |

**Recommendation:**
- **[P0]** The quantum migration plan (PLONK → STARKs in Phase 3) is correctly identified but incorrectly prioritized. Groth16 is the weakest link — the HNDL window is already open. STARK migration should be P1, not deferred to Phase 3.
- **[P1]** For ephemeral key signatures submitted on-chain: consider hybrid signatures (ECDSA + ML-DSA-65) during the transition period. The ML-DSA signature is quantum-safe; the ECDSA signature provides backward compatibility.
- **[P1]** The `organizerPubkeyHash` pattern (storing SHA256 of pubkey, not the pubkey itself) is correct for quantum resistance. Ensure the raw organizer pubkey is never exposed on-chain or in calldata. Currently, the QR/geo attestation modes include `organizer_pubkey` in the private circuit inputs — this is correct.
- **[P2]** `verifyAttendanceWithKey()` exposes ephemeral public keys via ECDSA signature recovery. Consider a ZK-based authentication mechanism for Phase 3 that does not require on-chain signature verification (recursive proof composition).

---

## 6. Passphrase Brute-Force Amplification via Biometric Template Leakage

**Question:** Does biometric template leakage amplify passphrase brute-force attacks?

### 6.1 Attack: Bio Leak → Passphrase-Only Brute Force

**Vector:** Attacker obtains: (1) target's `identity_commitment` (public, on-chain), (2) target's `bio_key` (via biometric replay — see Threat 1), (3) target's `salt` (from helper data / device backup). They now brute-force the passphrase:

```
for passphrase in dictionary:
    pass_key = Argon2id(passphrase, salt, t=3, m=64MB, p=4)
    master = HKDF(bio_key || pass_key, salt, "zkpresence-master-v1")
    if SHA256(master) == identity_commitment:
        FOUND
```

**Severity: HIGH**

**Analysis:**
- With `bio_key` known, the security of `master_secret` reduces entirely to the passphrase entropy.
- Argon2id with the specified parameters (t=3, m=64MB, p=4) provides ~$0.01 per guess on commodity hardware (estimate: ~10ms per evaluation). At this rate:
  - 6-character lowercase password (~28 bits): crackable in hours
  - 8-character mixed-case + digits (~48 bits): crackable in weeks with a small GPU cluster
  - 12-character passphrase with words (~60 bits): crackable in years
  - 4-word diceware passphrase (~51 bits): crackable in months
- **The biometric factor was supposed to provide ~105 bits of additional entropy.** When it leaks, the system drops from ~155+ bits combined security to whatever the passphrase provides alone. This is a catastrophic entropy reduction.

### 6.2 Attack: Partial Bio Template from Helper String → Reduced Search Space

**Vector:** Attacker doesn't have the raw biometric but HAS the helper string. They use the helper string to constrain the fuzzy extractor's input space and enumerate possible `bio_key` values, then combine with passphrase brute-force.

**Severity: MEDIUM**

**Analysis:**
- The helper string reduces the biometric search space from the full biometric template space to `2^105` candidates (the residual entropy after helper publication).
- Brute-forcing `2^105` bio_key values is infeasible even combined with passphrase brute-force. The attack multiplies two large spaces: `2^105 × passphrase_space` — worse than either alone.
- **However:** If the attacker has additional side information about the biometric (e.g., partial iris features from a photograph, racial/demographic constraints on iris patterns), the effective `bio_key` entropy could be reduced below 105 bits. The fuzzy extractor's security proof assumes no side information.

### 6.3 Attack: Offline Verification via On-Chain Commitment

**Vector:** The `identity_commitment` is public on-chain. The attacker can verify each brute-force guess against this commitment without interacting with any server or rate limiter. This is a fully offline attack.

**Severity: HIGH (amplifier)**

**Analysis:**
- Unlike online authentication systems, there is no lockout, no CAPTCHA, no rate limit. The attacker downloads `identity_commitment` from the chain and runs the brute-force loop locally.
- The only defense is the computational cost of Argon2id (memory-hard) and the entropy of the passphrase.
- **This is fundamental to the commitment-based architecture (Argon2 Path B).** If Argon2 were proven inside the ZK circuit (Path A), the passphrase would never be verifiable offline — but Path A was rejected as infeasible.

**Recommendation:**
- **[P0]** Enforce minimum passphrase entropy in the client SDK. Document that passphrases must be ≥ 80 bits of entropy (e.g., 6-word diceware minimum) because biometric leakage reduces the system to single-factor.
- **[P1]** Increase Argon2 parameters for high-value identities: t=5, m=256MB, p=8. This raises per-guess cost ~10x, making brute-force proportionally harder.
- **[P1]** Consider adding a server-side rate-limited OPRF (Oblivious Pseudo-Random Function) in the key derivation path: `master = HKDF(bio_key || pass_key || OPRF(server_key, user_id))`. This adds an online factor — brute-force requires server interaction, enabling rate limiting. Tradeoff: introduces a server dependency (reduces sovereignty).
- **[P2]** Implement passphrase strength estimation (zxcvbn or similar) in the SDK and reject weak passphrases at enrollment time.

---

## Consolidated Threat Matrix

| # | Threat | Severity | Exploitability | Impact | Status |
|---|---|---|---|---|---|
| 1.1 | Biometric replay → master secret recovery | **HIGH** | Medium (requires bio capture + helper + passphrase brute-force) | Identity theft (permanent) | Partially mitigated (second factor exists) |
| 2.1 | Helper data → partial bio key leakage | **MEDIUM** | Low (105-bit residual entropy is sufficient) | Privacy (cross-identity linkability) | Unmitigated (no blinding) |
| 3.1 | ZK proof forgery (KeyBinding) | **LOW** | Very low (requires breaking Groth16 soundness) | Identity impersonation | Mitigated (standard cryptographic assumption) |
| 3.2 | Malicious circuit compilation | **MEDIUM** | Low (requires supply chain compromise) | System-wide proof forgery | Unmitigated (no reproducible builds) |
| 4.1-4.5 | Key rotation griefing | **LOW** | Very low (ZK proof prevents unauthorized registration) | Temporary DoS | Well-mitigated |
| 5.2 | HNDL on ephemeral keys (quantum) | **HIGH** | Certain (public data, just needs CRQC) | Temporary identity impersonation (epoch-bounded) | Partially mitigated (epoch bounds) |
| 5.3 | HNDL on Groth16 proofs (quantum) | **CRITICAL** | Certain (requires CRQC) | Complete proof system compromise | Unmitigated (STARK migration deferred) |
| 6.1 | Bio leak + passphrase brute-force | **HIGH** | Medium (requires bio capture + offline compute) | Identity theft (permanent) | Partially mitigated (Argon2 cost) |
| 6.3 | Offline commitment verification (amplifier) | **HIGH** | Always (commitment is public) | Enables unlimited offline brute-force | Architectural (Path B tradeoff) |

---

## Priority Actions

### P0 — Must address before production
1. **Enforce minimum passphrase entropy ≥ 80 bits** in the SDK — biometric leakage makes this the last line of defense.
2. **Document Groth16 quantum vulnerability explicitly** — users and integrators must understand the HNDL exposure window.

### P1 — Should address in Phase 2
3. **Specify liveness detection** for biometric capture (anti-replay).
4. **Specify exact fuzzy extractor construction** with documented entropy loss parameter.
5. **Plan STARK migration timeline** — the HNDL clock is already running.
6. **Increase Argon2 parameters** for high-value identities.
7. **Consider hybrid ECDSA + ML-DSA-65 signatures** for ephemeral key auth.

### P2 — Consider for Phase 3
8. **Add helper string blinding** (bind to device key for cross-identity linkability protection).
9. **Implement reproducible circuit builds** for trusted setup verification.
10. **Passphrase strength estimation** (zxcvbn) in SDK enrollment flow.
11. **OPRF server factor** for online rate-limiting of key derivation (sovereignty tradeoff).

---

## Overall Risk Assessment

**Risk Score: 6/10**

The architecture's core design is sound — the three-layer separation is correct, epoch-based key expiry is well-designed, and the ZK proof requirement for key registration prevents most griefing vectors. The primary risks are:

1. **Quantum exposure is underestimated.** Groth16 is the weakest link, and STARK migration is deferred to Phase 3. The HNDL collection window is already open. Every proof submitted today is a future forgery vector.

2. **Biometric factor brittleness.** Biometrics are irrevocable. The architecture correctly treats them as one factor of two, but doesn't adequately address what happens when the biometric factor is compromised (no migration path, no liveness detection spec).

3. **Offline brute-force enablement.** The commitment-based architecture (Argon2 Path B) is the correct engineering choice, but it creates an inherent offline verification oracle. Passphrase entropy requirements must be treated as a security-critical parameter, not a UX suggestion.

The identity layer (SHA-256 commitments) and the key rotation mechanism are both quantum-durable and well-designed. The vulnerability is in the authority layer (secp256k1 + Groth16) which has a defined migration path but an inadequate timeline.

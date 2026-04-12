## Key Insights (ranked by confidence × actionability)

1. **Fuzzy extractors are production-viable for biometric key derivation in 2025/2026** — Confidence: HIGH | Sources: 3 (Dodis 2006 foundational, CCS 2025 iris 105-bit/92% TAR, IACR 2025/1799 voice/fingerprint). The iris result is the strongest: 105 bits entropy, 92% true accept rate, simultaneous feature pipeline + algorithm improvement. Directly applicable as Phase 2 biometric input to zkPresence.

2. **zkLogin pattern (stable address + rotating ephemeral key, ZK-certified) is the correct architecture for dynamic public keys on blockchain** — Confidence: HIGH | Sources: 3 (Sui production CCS 2024, BioZero arXiv 2024, zkAt IACR 2025). Address = `H(stable_identity_inputs + salt)` never changes. Signing key = ephemeral pair embedded in ZK-certified nonce. Adapt: replace OAuth JWT with biometric+passphrase commitment as the stable credential.

3. **Combined biometric+passphrase master secret pattern is well-defined and ZK-provable** — Confidence: HIGH | Sources: 4 (BioZero Pedersen+Groth16, fuzzy extractor papers, zkLogin pattern, PLONK survey). Pattern: `master_secret = H(FuzzyExtract(biometric) || Argon2(passphrase, salt))`. ZK circuit proves: prover knows bio+passphrase such that H(combine(fuzzy_extract(bio), KDF(pass))) == public_commitment. Commitment = 32 bytes on-chain.

4. **PLONK is superior to Groth16 for dynamic/rotating key schemes** — Confidence: HIGH | Sources: 2 (PLONK survey arXiv 2502.07063, zkLogin design). Universal trusted setup = reusable across circuit changes; critical for key rotation without re-ceremony. Sub-50ms verification confirmed. SP1 already supports PLONK-family via its zkVM backend.

5. **zkPresence has zero biometric/fuzzy extractor/passphrase implementation — confirmed clean slate** — Confidence: HIGH | Sources: 2 (grep-verified: no matches for fuzzy/FuzzyExtract/biometric/argon2/HKDF in all .rs files). SHA-256 wiring is `todo!()` at circuit/main.rs:26; ECDSA wiring `todo!()` at lines 70/104/121. This is a structural gap, not needs-extension.

6. **SP1 Hypercube makes on-chain ZK proof verification economically viable** — Confidence: HIGH | Sources: 3 (Succinct 2026 blog, ZK cost research $0.037/proof, memory hit on SP1 production-grade). secp256k1 + SHA-256 precompiles (5-10x speedup) directly applicable to zkPresence biometric circuit. Real-time proving confirmed.

7. **Policy-private ZK authenticator (zkAt) enables hidden authentication logic** — Confidence: MEDIUM | Sources: 1 (IACR 2025/921 single paper). Hides threshold/signer set from adversaries. Obliviously updateable policy without revealing old/new. Strong against targeted attacks. Relevant for enterprise zkPresence use cases.

---

## Contradictions / Uncertainties

- **Groth16 vs PLONK for zkPresence**: BioZero uses Groth16 (smallest proof, fastest verify), PLONK survey recommends PLONK for rotation. For zkPresence Phase 1 (static keys), Groth16 suffices. Phase 2 (dynamic keys) requires PLONK or UltraPLONK. No actual contradiction — it's a phased choice.
- **Error tolerance variance**: Iris achieves 92% TAR at ~10-15% Hamming tolerance. Voice/fingerprint (IACR 2025/1799) handles lower-entropy sources with different construction. No single fuzzy extractor works for all modalities — biometric selection determines which construction to use.
- **Knowledge graph returned 500 error** — potential graph data loss or service issue. 0 graph nodes contributed to synthesis. Confidence in graph-sourced claims: N/A (no claims made from graph).

---

## Recommended Actions (top 3, specific and implementable)

1. **Wire zkPresence SHA-256 + resolve ECDSA `todo!()`s before adding any biometric layer** — Expected impact: Unblocks all future circuit work. Files: `crates/circuit/src/main.rs` lines 26, 70, 104, 121. Use `sha2` crate (SP1 patches syscall). ECDSA via SP1 secp256k1 precompile. This is P0 prerequisite.

2. **Design zkPresence Phase 2 biometric extension using iris fuzzy extractor → commitment pattern** — Expected impact: Enables biometric ZK identity without storing raw biometrics. Architecture: `commitment = H(FuzzyExtract(iris, helper_string))`. ZK circuit proves: prover knows iris raw bytes + helper string such that SHA256(fuzzy_extract(iris, h)) == stored_commitment. Use CCS 2025 construction (105-bit entropy, 92% TAR) as reference implementation baseline.

3. **Add Argon2 passphrase KDF to zkPresence identity derivation as Phase 2b** — Expected impact: Dual-factor (bio + passphrase) auth with single ZK proof. Pattern: `master = HKDF(FuzzyExtract(bio) || Argon2(pass, salt))`. ZK proves knowledge of both factors. Switch to PLONK when implementing (universal setup = no re-ceremony on key rotation).

---

## Evidence Quality Assessment

Coverage: PARTIAL — Web sources excellent (10 high-quality papers/projects). Codebase verified (2 files). Memory: 5 hits, none on fuzzy extractors specifically. Graph: dead (500 error). DB papers: 0 relevant.
Source reliability: HIGH — Peer-reviewed: Dodis SIAM 2006, CCS 2024 (zkLogin), CCS 2025 (iris), IACR 2025. Production deployments: Sui (zkLogin), Worldcoin/Humanity Protocol.
Gaps: (1) No Reed-Solomon error correction implementation reference for fuzzy extractor SP1 circuit. (2) Argon2 inside ZK circuit performance benchmarks not found. (3) Pedersen commitment vs. SHA256 commitment tradeoff analysis absent.

---

## Compressed Handoff (≤1000 tokens)

**Topic**: Dynamic public key blockchain + biometric + passphrase ZK derivation
**Baseline**: zkPresence uses SHA256(user_secret) commitment + SHA256(secret||event_id) nullifier. SP1 RISC-V circuit. SHA-256 and ECDSA are `todo!()`. Zero biometric/fuzzy/KDF code (grep-verified).

**Architecture to build**:
- Stable identity = `H(bio_commitment || passphrase_commitment || salt)` — never changes on-chain
- Ephemeral signing = ephemeral key pair, ZK-certified against stable commitment (zkLogin pattern adapted)
- Bio layer: `bio_key = FuzzyExtract(iris_raw, helper_string)` → 105-bit entropy (CCS 2025), 92% TAR
- Pass layer: `pass_key = Argon2(passphrase, salt)`
- Master secret: `HKDF(bio_key || pass_key)` → commitment = `SHA256(master_secret)`
- ZK circuit proves: knows (bio_raw, helper, passphrase) such that HKDF(FuzzyExtract(bio_raw, helper) || Argon2(passphrase, salt)) matches stored commitment

**Proof system**: PLONK (universal setup, rotation-safe). Groth16 acceptable for Phase 1 static only.
**Prover**: SP1 Hypercube — secp256k1+SHA256 precompiles, 5-10x speedup, $0.037/proof

**Confirmed gaps** (grep-verified):
- fuzzy extractor: `grep fuzzy/FuzzyExtract` → 0 results in all .rs files
- biometric: `grep biometric` → 0 results
- Argon2/HKDF: `grep argon2/HKDF` → 0 results
- SHA-256 circuit wiring: `todo!()` at main.rs:26
- ECDSA circuit wiring: `todo!()` at main.rs:70,104,121

**P0 action**: Wire SHA-256 + ECDSA in circuit first (unblocks everything)
**P1 action**: Design iris fuzzy extractor as Phase 2 biometric input
**P2 action**: Add Argon2 passphrase KDF + PLONK migration for Phase 2b

**References**: Dodis 2006 (foundational fuzzy extractors), CCS 2025 iris (practical 105-bit), zkLogin arXiv 2401.11735 (dynamic key pattern), BioZero arXiv 2409.17509 (Groth16 biometric ZK), SP1 Hypercube (Succinct 2026), zkAt IACR 2025/921 (policy-private auth)

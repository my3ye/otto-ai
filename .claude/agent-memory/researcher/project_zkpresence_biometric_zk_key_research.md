---
name: zkPresence Biometric ZK Dynamic Key Research
description: Full pipeline research on dynamic public key schemes, fuzzy extractors, and ZK auth primitives for zkPresence Phase 2 biometric+passphrase integration. VALIDATED 7.5/10 (2026-04-12).
type: project
---

**Pipeline complete** — 3-step research pipeline (Retrieval → Synthesis → Validation → Storage). 17 sources (10 web, 5 memory, 2 codebase grep). Validation score: 7.5/10 MINOR_CHANGES.

## Validated Insights

1. **[HIGH] Fuzzy extractors production-viable** — CCS 2025 iris: 105-bit entropy, 92% TAR. Applicable to zkPresence Phase 2.
2. **[HIGH] zkLogin adaptation pattern** — stable address + rotating ephemeral key in ZK-certified nonce. Replace OAuth JWT with biometric+passphrase commitment. 3 independent sources.
3. **[HIGH w/caveat] Combined bio+passphrase pattern** — PROPOSED COMBINATION: `H(FuzzyExtract(bio) || Argon2(passphrase, salt))`. No single paper cites this exact combination — synthesis-derived from established primitives.
4. **[MEDIUM] PLONK > Groth16 for rotation** — 2 sources only (insufficient for HIGH). Phased: Groth16 Phase 1, PLONK Phase 2. **PLONK migration = new ISP1Verifier contract on Base**.
5. **[HIGH] zkPresence clean slate** — grep-verified: zero fuzzy/biometric/argon2/HKDF in .rs files. SHA-256 + ECDSA both `todo!()` in circuit/main.rs.
6. **[HIGH vendor-corroborated] SP1 ~$0.037/proof** — Succinct blog + corroborated by local zk-chain-landscape-2026.md line 23. Not 3 independent sources.
7. **[MEDIUM] zkAt policy-private** — IACR 2025/921, enterprise use case only.

## DESIGN BLOCKER: Argon2-inside-ZK
Two architecturally incompatible paths before Phase 2b:
- **Path A**: Prove Argon2 computation in ZK — prohibitively expensive (memory-hard = massive cycles)
- **Path B**: Prove knowledge of Argon2 output commitment — feasible but different circuit design

**Must decide Path A vs B before any Phase 2b implementation.**

## Corrections Applied
- **Patched**: Insight 4 confidence HIGH → MEDIUM (only 2 sources; rule requires 3+)
- **Patched**: Insight 3 "well-defined" → "proposed combination of established primitives" (synthesis-derived, no direct citation)
- **Patched**: Insight 6 vendor annotation added (was presented as 3 independent sources)
- **Patched**: Action 3 Groth16→PLONK migration — noted requires new on-chain verifier contract, not config switch
- **Elevated**: Argon2-inside-ZK from "benchmark gap" to DESIGN BLOCKER

## Action Items (ordered)
1. **P0**: Wire SHA-256 + resolve ECDSA `todo!()`s — `circuit/main.rs` lines 26, 70, 104, 121
2. **P1**: Design iris fuzzy extractor → commitment ZK extension
3. **P2**: DECIDE Argon2 path (A or B) — BLOCKER for Phase 2b
4. **P3**: Migrate to PLONK — deploy new ISP1Verifier on Base

**Why:** zkPresence circuit/main.rs is broken (todo!() panics). Phase 2 biometric ZK is architecturally ready but needs P0 fix first.
**How to apply:** Phase 2 design decisions must check Argon2 blocker status first. Do not implement passphrase KDF before path decision.

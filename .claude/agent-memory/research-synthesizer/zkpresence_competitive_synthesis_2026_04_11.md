---
name: zkPresence competitive landscape synthesis
description: Competitive analysis + internal gap audit for zkPresence (2026-04-11). Codebase-verified circuit TODOs, market positioning, Zupass/Semaphore/POAP comparison.
type: project
---

# zkPresence Competitive Landscape — Synthesis 2026-04-11

## Codebase-Verified Architecture (HIGH confidence)
- SP1 v6.1 confirmed (program/Cargo.toml + script/Cargo.toml)
- 3 attestation modes confirmed in type system: QrCode, GeoProximity, OrganizerSignature (lib/src/lib.rs)
- ZkPresence.sol: 148 lines (not 128 as reported), Groth16 via ISP1Verifier gateway
- Nullifier design: SHA-256(user_secret ‖ event_id) — unlinkable per-event
- Target: Base L2 via ISP1Verifier at 0x397A5f7f3dBd538f23DE225B51f532c34448dA9B

## Critical Circuit Gaps (grep-verified, HIGH confidence)
1. SHA-256 precompile: `todo!()` at program/src/main.rs:20 — circuit panics at runtime
2. ECDSA secp256k1: TODO at main.rs:61, 88, 104 — attestation signatures unverified in ZK
3. No tests: find confirms zero test files in entire repo
- Geohash precision: code matches 5-char prefix (4.9km radius), retrieval claimed 1.2km — minor inaccuracy, low impact

## Competitive Matrix
| Project | ZK | Attendance-native | Open protocol | SP1 | Privacy |
|---|---|---|---|---|---|
| zkPresence | ✓ | ✓ | ✓ | ✓ | Full |
| Zupass | ✓ (Groth16/Circom) | ✓ | Partial (PCF-controlled) | ✗ | Full |
| Semaphore | ✓ (Circom) | ✗ (group primitive) | ✓ | ✗ | Full |
| POAP | ✗ | ✓ | ✓ | ✗ | None |
| zkPass | ✓ | ✗ (TLS web data) | Partial | ✗ | Partial |

## Market Gap (MEDIUM confidence, 4 web searches, negative result)
- No open-source SP1-native event attendance protocol found in market as of April 2026
- Search query: "SP1 zkVM event attendance protocol open source" — no match
- Zupass is closest competitor: PCF-controlled, no Rust/SP1, venue-specific complexity

## Memory Write Token
e5672287-d05e-4962-bdc5-a3bf0e88f0e4

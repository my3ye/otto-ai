---
name: zkPresence Competitive Landscape & OSS Positioning
description: Validated research (7.5/10) on zkPresence circuit gaps, competitive matrix, and OSS launch path. Critical: SHA-256 + ECDSA must be fixed simultaneously to avoid silent auth bypass.
type: project
---

## zkPresence Research Summary — 2026-04-11

**Research Note ID:** f3e63cbc-fb65-448f-8517-2630540b0e8b
**Semantic Memory IDs:** c272f770, 1fe41451, 7a1fca49, 27cffd08, 238e9a3e, 7e6904d1, e5ca1398, b3550ce9
**Validation Score:** 7.5/10 (MINOR_CHANGES — all corrections applied)

### Architecture Status
- SP1 6.1.x series (Cargo.toml; exact patch needs Cargo.lock for grant apps)
- 3 attestation modes confirmed: QrCode, GeoProximity, OrganizerSignature (lib/src/lib.rs)
- ZkPresence.sol: 147 lines, ISP1Verifier Groth16 gateway, Base L2 target
- Design is correct; execution is incomplete

### Critical Blockers (fix simultaneously — P0)
1. `todo!()` MACRO at `program/src/main.rs:20` → SHA-256 precompile missing → **RUNTIME PANIC**
2. `// TODO:` stubs at `main.rs:61,88,104` → ECDSA secp256k1 silently absent → **circuit compiles but never verifies organizer signatures** → accepts forged attestations
   - **WARNING**: Fixing SHA-256 only creates a silent authentication bypass. Must fix both in same PR.
3. Zero test files (grep/find confirmed: no `#[test]`, no `*.t.sol`, no `*_test.*`)

**Why:** Per validator (Step 2), the conflation of `todo!()` macro (panic) vs `// TODO:` comment (silent omission) is critical for correct security framing. The ECDSA issue is more dangerous than the panic.

**How to apply:** Any implementation task touching zkPresence circuits must wire SHA-256 AND ECDSA in the same PR. Never suggest partial fix.

### Competitive Matrix
| Protocol | Stack | Users | Threat Level |
|----------|-------|-------|--------------|
| Semaphore | Circom | Unknown | PRIMITIVE only, not attendance-specific |
| Zupass | Groth16/Circom, PCF-controlled | ~10K | Narrow niche, not general protocol |
| POAP | No ZK | 80M+ | Addressable base with no privacy gap |
| SP1-native attendance | — | 0 found | **GAP confirmed** (4 searches, negative match) |

### Contradictions / Patches Applied
- `ARCHITECTURE.md` internal contradiction: line 119 says 6-char geohash (~1.2km); line 155 says 5-char (~5km). **Doc fix required before OSS publication.**
- Gas cost $0.003/verification = ARCHITECTURE.md:664 estimate only, not testnet benchmark
- Negative match is absence-of-evidence: stealth/closed-source projects may exist

### OSS Launch Path
1. Wire SHA-256 + ECDSA precompiles simultaneously (P0)
2. Add Rust unit tests + Solidity `*.t.sol` tests (P0 for OSS credibility)
3. Fix ARCHITECTURE.md geohash contradiction (line 119 vs 155)
4. OSS publish → Succinct Network grant → EF PSE grant (Semaphore precedent)

### Market Macro
- ZK proof market: $7.59B by 2033 (22.1% CAGR)
- 2026 = ZK shifting to production infrastructure — timing favorable

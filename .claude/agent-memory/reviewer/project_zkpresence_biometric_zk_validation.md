---
name: zkPresence biometric+passphrase ZK dynamic key validation
description: Research synthesis validation (2026-04-12, WF Step 2): fuzzy extractors, zkLogin pattern, combined bio+passphrase master secret. MINOR_CHANGES 7.5/10.
type: project
---

zkPresence biometric+passphrase dynamic key research synthesis (2026-04-12, WF Step 2).

**Why:** Validates whether the ZK biometric architecture synthesis is accurate enough to drive Phase 2 implementation decisions for zkPresence.
**How to apply:** 2 criticals must be corrected before synthesis is used as a design spec. Core architectural direction (zkLogin pattern + fuzzy extractor) is sound.

## Verdict: MINOR_CHANGES — 7.5/10

Core codebase claims verified. Architecture direction is well-founded. 2 criticals: Insight 4 confidence inflated (2 sources, not 3), Argon2-inside-ZK cost risk missing. 3 warnings: vendor bias on $0.037, sourcing caveat on combined pattern, PLONK migration omits existing Groth16 gateway.

## Grep Verifications (PASS)

- SHA-256 `todo!()` at `crates/circuit/src/main.rs:26` ✓ (verified)
- ECDSA `todo!()` at `crates/circuit/src/main.rs:70`, `104`, `121` ✓ (verified; code updated from prior Apr-11 review — ECDSA is now todo!() panic, no longer silent // TODO: comment)
- No fuzzy/FuzzyExtract/biometric/argon2/hkdf in any .rs file ✓ (grep empty, clean slate confirmed)
- `identity.rs` derive_identity / compute_nullifier descriptions ✓ (SHA-256 functions, correct)

## Critical Issues (must fix before use as design spec)

1. **Insight 4 confidence wrong — HIGH from 2 sources** — synthesis marks "PLONK > Groth16" as HIGH confidence citing 2 sources (arXiv 2502.07063 + BioZero comparison). Per research validation procedure, HIGH requires 3+ independent sources. This is MEDIUM. Downgrade to MEDIUM before committing this to architectural decisions.

2. **Argon2-inside-ZK is a potential design blocker, not a minor gap** — Insight 3 Action 3 recommends "Add Argon2 passphrase KDF" and the Evidence Quality section says "Argon2-inside-ZK performance benchmarks absent." This understates the problem. Argon2 is memory-hard by design (intentional high memory/CPU cost). Running Argon2 inside an SP1 RISC-V zkVM circuit generates orders of magnitude more cycles than SHA-256. The synthesis doesn't establish whether the design requires proving Argon2 execution (prohibitively expensive) or merely proving knowledge of an Argon2 output commitment (feasible). This architectural split must be decided before any Phase 2b work starts. Flag as design blocker, not just a benchmarking gap.

## Warnings (should address)

3. **Insight 6 ($0.037/proof) — vendor-bias, should be MEDIUM** — The 3 "sources" cited are: Succinct blog post + 2 memory references derived from that same blog post. This is 1 primary source (vendor). The $0.0376 figure was independently corroborated in zk-chain-landscape-2026.md (local doc line 23), making it HIGH-verifiable — but the memory file sourcing needs cleanup to make this explicit. Prior validated syntheses (ecosystem blockchain infra, 2026-04-10) rated this MEDIUM with vendor-bias note. Recommend: HIGH confidence with explicit "(vendor-corroborated via local doc)" annotation.

4. **Insight 3 — combined H(FuzzyExtract || Argon2) pattern is synthesis-derived, not cited** — The formula `master_secret = H(FuzzyExtract(biometric) || Argon2(passphrase, salt))` is a reasonable proposed design composed from component primitives. The 4 sources cited support the primitives individually (fuzzy extractors + KDF patterns), not this specific combination. The synthesis presents this as "well-defined and ZK-provable" (implying prior art). It should be labeled "proposed combination of established primitives" to avoid misleading the architect.

5. **Action 3 PLONK migration omits Groth16 gateway implication** — zkPresence.sol currently uses an ISP1Verifier (Groth16) gateway on Base (confirmed in competitive analysis, Apr-11). Migrating to PLONK requires deploying a new verifier contract on-chain and updating the integration. This is not a backend config switch — it's a contract migration. Action 3 should note: "PLONK migration requires new on-chain verifier deployment."

## What's Good

- Codebase gap claims are 100% grep-verified and accurate
- ECDSA todo!() state correctly reflects current code (upgraded from silent // TODO: comment to panic — security improvement noted without being asked)
- zkLogin pattern adaptation is the correct architectural frame — well-supported by 3 independent sources (Sui CCS 2024, BioZero, zkAt)
- Action 1 (fix SHA-256 + ECDSA together) is consistent with prior security warning from zkPresence docs review — do not ship with only SHA-256 wired
- Contradictions section (Groth16 vs PLONK phased approach) is sound reasoning
- Evidence quality section is honest about gaps (graph dead, no DB papers, no Reed-Solomon SP1 ref)
- Source count (17 total) is legitimate; web sources are peer-reviewed ACM/IACR/arXiv

## Confidence Score Corrections

| Insight | Synthesis | Corrected |
|---------|-----------|-----------|
| 1 Fuzzy extractors viable | HIGH | HIGH ✓ |
| 2 zkLogin pattern | HIGH | HIGH ✓ |
| 3 Combined bio+passphrase pattern | HIGH | HIGH (add "proposed combination" caveat) |
| 4 PLONK > Groth16 | HIGH | **MEDIUM** (2 sources) |
| 5 Clean slate grep | HIGH | HIGH ✓ |
| 6 SP1 $0.037/proof | HIGH | HIGH (add vendor-corroborated annotation) |
| 7 zkAt policy-private | MEDIUM | MEDIUM ✓ |

## VALIDATION_SCORE: 7.5/10

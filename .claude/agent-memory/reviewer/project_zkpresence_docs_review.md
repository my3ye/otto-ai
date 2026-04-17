---
name: zkPresence open source docs review
description: WF Step 1 review of zkPresence README, ROADMAP, CONTRIBUTING, QUICK_START (2026-04-11). MINOR_CHANGES 7.5/10. 3 criticals: ECDSA silent omission unwarned, bogus sha256 stub code, QUICK_START panic mismatch.
type: project
---

zkPresence documentation set review (2026-04-11, WF Step 1). Files: README.md, ROADMAP.md, CONTRIBUTING.md, docs/QUICK_START.md.

**Why:** Step 1 in content-publishing pipeline for zkPresence OSS docs. Four docs reviewed together as a set.
**How to apply:** The ECDSA/todo!() security gap is the dominant issue for this entire protocol. Flag it on any future zkPresence review.

## VERDICT: MINOR_CHANGES — 7.5/10

## Critical Issues (must fix)

1. **ECDSA silent omission unwarned in CONTRIBUTING.md** — circuit/src/main.rs:61,88,104
   SHA-256 stub = `todo!()` macro (panics). ECDSA stubs = `// TODO:` comments (silently skipped).
   CONTRIBUTING.md tells contributors to fix SHA-256 first. When SHA-256 is fixed but ECDSA is not,
   the circuit generates proofs that accept ANY attestation without signature verification — a complete
   security break that appears to work. CONTRIBUTING must warn: "Do not ship Phase 1 with only SHA-256
   wired — ECDSA must be wired simultaneously. Without ECDSA, the circuit silently accepts forged
   attestations."

2. **Bogus sha256 stub code before todo!()** — circuit/src/main.rs:15-17
   The stub calls `sp1_zkvm::precompiles::utils::CurveOperations::sha256(data)` and
   `sp1_zkvm::io::hint_slice(data)` — neither is a real SP1 API. CONTRIBUTING says "if sha256
   panics with todo!()" — but if the bogus calls fail to compile, there's no runtime panic.
   Fix: replace lines 14-20 with just `todo!("Wire up SP1 SHA-256 precompile")` and nothing else.

3. **QUICK_START Step 3 claims output that will not be produced** — docs/QUICK_START.md:60-65
   Comment block says "# Output: serialized proof bytes + public values" but the circuit will
   panic at sha256. CONTRIBUTING.md correctly warns "If sha256 panics — that is expected."
   QUICK_START does NOT. Fix: replace output comment with "# This will currently panic at sha256
   — that is the expected development state. See CONTRIBUTING.md."

## Warnings (should fix)

4. **Gas estimate unsourced** — README.md:184
   "~230,000 gas (~$0.003 on Base at typical fee rates)" — "typical" is unmeasurable.
   Add: "(at 0.001 gwei median fee; verify current rates at basefees.net)"

5. **Otto Music / Tusita unnamed to external contributors** — ROADMAP.md:143-159
   External contributors see two internal project names with no description. Reframe as
   "Example: a music platform integration could..." or add one-sentence context per project.

6. **ARCHITECTURE.md geohash contradiction not fixed** — pre-existing but new docs now reference it
   ARCHITECTURE.md line 119: "6-char precision (~1.2km)" (type comment). Line 155: "5-char match ~5km"
   (actual circuit logic). README correctly uses "5-char prefix match (~5km)." QUICK_START:127 uses
   "geohash_6chars" (for field size, not match precision). Recommend adding a NOTE in ARCHITECTURE.md
   clarifying: "Fields store 6-char geohashes for full coordinate precision; only 5-char prefix is
   matched for attendance (intentionally coarse for privacy)."

## Suggestions (nice to have)

- Add GitHub Discussions/Discord link — the target audience expects a community entry point
- Pin SP1 toolchain version in install instructions (not just `sp1up` latest — breaking changes between versions)
- ROADMAP: add Phase 1 target date (current Phase 0 date is 2026-04-11)
- CONTRIBUTING Section 1: add explicit sequencing note "SHA-256 PR, then ECDSA PR — both needed before Phase 1 is safe"

## What's Good

- README opener ("Every current proof of attendance is a surveillance instrument") — best single line in the doc set; earns attention immediately
- Tense discipline throughout — "designed," "planned," "in active development" consistent and honest
- Security properties table + Known Limitations in same README — rare combination; builds credibility
- CONTRIBUTING code-first structure with actionable code snippets (the CONTRIBUTING.md sha2 fix is technically correct)
- ROADMAP Long-Term Research section treating sybil/multi-chain as open research, not roadmap items
- Architecture ASCII diagram flows cleanly: Organizer → User Device → On-Chain
- Nullifier derivation H(secret ‖ event_id) well-explained inline
- ISP1Verifier gateway address present and specific (0x397A5f7f3dBd538f23DE225B51f532c34448dA9B)

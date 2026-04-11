---
name: ZK Grants & Launchpad Synthesis Validation
description: ZK ecosystem fit, grants, and launchpad research synthesis validation (2026-04-11, WF Step 2). MINOR_CHANGES 8.0/10.
type: project
---

ZK grants and launchpad synthesis (2026-04-11, research-pipeline WF Step 2). MINOR_CHANGES 8.0/10.

**Why:** Validates whether the grant matrix, codebase gap claims, and 90-day sequence are accurate enough to act on.
**How to apply:** The corrected findings below should be forwarded to storage and the todo!() execution-order nuance carried into circuit fix prompts.

## Verdict: MINOR_CHANGES 8.0/10

All critical codebase claims verified against live files. Grant intelligence is sound. Two warnings require attention before semantic storage.

## Grep Verifications (all PASS)

- SHA-256 todo!() at line 26 of `crates/circuit/src/main.rs` ✓
- ECDSA todo!() at lines 70, 104, 121 of same file ✓ (4 total todo!() panics confirmed)
- ZkPresence.t.sol with MockSP1Verifier EXISTS (`contracts/test/ZkPresence.t.sol`) ✓
- ONEON: zero `.rs`/`.circom`/`.zok` files in `oneon-web/` ✓
- Panik: zero `.sol` files in `panik-app-web/` (including node_modules excluded) ✓

## Critical Issues (must fix)

- **{topic} template bug — 5th recurrence**: Task prompt received with literal `Topic: {topic}` unsubstituted. Synthesizer correctly inferred topic from context, but the workflow template substitution is consistently broken. Not a synthesis quality failure — a systemic pipeline defect. Now the 5th occurrence (WebAssist, Koink, Panik, CORAL/AI, now this). Action: fix the workflow step variable injection.

- **Stale memory e5672287 not explicitly corrected**: Memory ID e5672287 still characterizes "ECDSA = silent bypass" — but actual code shows ECDSA paths have `todo!()` (runtime panic), not silent bypass. The synthesis correctly claims "4 todo!() panics" (implicitly overriding the stale memory), but the stale "silent bypass" framing still sits in semantic storage and could pollute future prompts. The competitive validation (project_zkpresence_competitive_validation.md) flagged this earlier. Storage step should explicitly archive/correct e5672287.

## Warnings (should note)

- **SHA-256 execution-order nuance missing**: sha256() is called at lines 37 and 45 — BEFORE the match statement that contains the ECDSA todo!()s at 70/104/121. This means in current code the SHA-256 todo!() fires first and the 3 ECDSA panics are unreachable. "4 panics blocking all use" is technically accurate but the nuance matters for grant reviewers reading the code: only 1 panic is live, not 4 simultaneous ones. The recommended action (fix both SHA-256 + ECDSA together) is correct — just the framing could be tightened.

- **Source count conflation for Insight 1**: "Sources: 3 (grep-verified: SHA-256 line 26, ECDSA lines 70/104/121)" — three grep hits within one file is 1 source (the codebase), not 3 independent sources. Minor methodology imprecision, same pattern flagged in competitive validation.

- **OP RetroPGF $3B single-source**: "$3B distributed across rounds" sourced only from retropgf.com (the vendor). Should be MEDIUM confidence, not implied HIGH. Panik is still the correct OP Retro candidate regardless.

- **Succinct/SP1 metrics vendor-sourced**: "$4B+ in assets protected, 6M+ proofs generated" from succinct.xyz only. Appropriate for context but should carry MEDIUM not HIGH confidence in stored form.

## What's Good

- 6 gap claims grep-verified before writing — unusually rigorous for a synthesis step
- Exact line numbers (26, 70, 104, 121) all confirmed correct
- "Zero tests" correction is accurate — ZkPresence.t.sol with MockSP1Verifier EXISTS, no prover integration test is the real gap
- Grant matrix priority order is sound: EF PSE + Succinct (circuit-gated) > ETHGlobal NY (7-week deadline) > Gitcoin GG25 (register NOW) > OP RetroPGF (retroactive)
- Starknet/ZKsync "wrong stack" call is correct and well-reasoned
- 90-day sequence is specific, time-boxed, and matches the dependency graph
- Contradictions section (EF ZK Grants 2024 wave complete, Succinct amounts unknown) is honest and actionable
- Graphiti offline acknowledged cleanly rather than fabricated

## Confidence Adjustments

| Claim | Original | Adjusted | Reason |
|-------|----------|----------|--------|
| 4 todo!() panics | HIGH | HIGH | Grep-confirmed |
| EF PSE ~$25-50K | HIGH | MEDIUM | Estimate, no 2026 amounts confirmed |
| ETHGlobal NY June 12-14 | HIGH | HIGH | Official source |
| Gitcoin GG25 Q2 2026 | HIGH | HIGH | Multiple sources |
| OP RetroPGF $3B | HIGH (implied) | MEDIUM | Single-source, vendor |
| Succinct SP1 metrics | HIGH (implied) | MEDIUM | Vendor-sourced |

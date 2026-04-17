---
name: project_quantum_crypto_synthesis_validation
description: Quantum cryptography threat landscape synthesis (2026-04-11, WF Step 2): MINOR_CHANGES 7.5/10. 3 criticals: W3/Iceberg source label error; "in minutes" unverifiable quote; todo!() line list wrong (L26=SHA-256 not ECDSA, L67=comment not todo). Lucky Penny ECDSA indirect via ERC20Permit. {topic} bug = 6th instance.
type: project
---

Quantum cryptography threat landscape synthesis validated 2026-04-11, WF Step 2.
Verdict: MINOR_CHANGES 7.5/10. Core conclusions correct. 3 fixable accuracy issues.

**Critical Issues:**
1. Source attribution error: Insight 1 cites "W3 Iceberg Quantum" but Iceberg Quantum QLDPC paper is covered in W2 (The Quantum Insider), not W3 (Google Research blog). Label should be "(W2 Iceberg Quantum, W3 Google, W4 CoinDesk)".
2. "Breakable in minutes" unverifiable: Quoted phrase in Insight 1 is NOT in raw W3 data section. W3 raw data gives qubit/gate counts but not the "minutes" timeframe. Either from blog body (not captured) or synthesis inference presented as a quote. Must remove quotes or cite exact source.
3. todo!() line list inaccurate: Synthesis claims "3× ECDSA todo!() panics at L26,67,70,104,121" but grep confirms 4 total todo!() calls: L26 (SHA-256, NOT ECDSA), L70 (ECDSA), L104 (ECDSA), L121 (ECDSA). L67 is a comment, not a todo!(). "3× ECDSA" count is correct but line list is wrong.

**Warnings:**
1. "Bernstein 3–5 years": W4 attributes this to "Bernstein" — almost certainly Bernstein Research (financial firm), NOT Daniel J. Bernstein (cryptographer). Different credibility class for a technical estimate.
2. BN254 cited at ZkPresence.sol L91: L91 is `/// @notice Submit a ZK proof of attendance.` — no BN254 reference. L8 correctly shows Groth16. L91 adds no BN254 evidence; citation is misleading.
3. Lucky Penny ECDSA evidence quality: Synthesis cites `out/ECDSA.sol/ECDSA.json` (build artifact). Lucky Penny /src/ has zero direct ECDSA imports — confirmed grep. ECDSA exposure is real but via ERC20Permit → ECDSA import chain. Should cite LuckyPenny.sol → ERC20Permit as the actual evidence path.
4. {topic}/{scope} template variables unresolved — 6th confirmed instance. Systemic workflow dispatcher bug, not a one-off.
5. Knowledge graph API error not investigated — "Internal Server Error" noted but root cause unknown. Possibly persistent infra issue.

**Suggestions:**
- Insight 5 should clearly split: "SHA-256 todo!() (L26) → entire circuit panics at runtime" vs "3× ECDSA todo!() (L70/104/121) → organizer sig verification panics." SHA-256 must be fixed first (it blocks all three ECDSA paths too since sha256() is called before ECDSA verify).
- Action #1 should note SHA-256 precompile is a prerequisite: circuit calls sha256() before any ECDSA verification — fixing ECDSA alone won't make the circuit run.

**What's good:**
- Core Q-Day acceleration claims well-sourced: qubit estimates, 2029 deadline, algorithmic vs hardware distinction all correct.
- NIST FIPS 203/204/205 citation accurate and correctly dated Aug 2024.
- ETH vs BTC divergence well-sourced and framing accurate (pq.ethereum.org verified real).
- QKD correctly MEDIUM confidence (single source).
- "No address reuse" recommendation directly mirrors Google's own recommendation.
- Evidence quality section honestly identifies gaps (no graph data, no PQC papers).
- Three codebase claims were independently verified (PQC grep = zero, SP1 Groth16 usage, ECDSA exposure).

**Why:** Quantum synthesis is substantively sound but has 3 accuracy issues in citation/line numbers that need correction before downstream use in content or grant applications.

---
name: ZK ONEON Architecture Decision Framework
description: Full research pipeline output (2026-04-10, validated 7.5/10) — ZK toolchain selection, chain path, and ONEON readiness assessment. Corrections applied from validation pass.
type: project
---

## ZK Architectural Decision Framework for ONEON
**Date:** 2026-04-10 | **Validation:** 7.5/10 MINOR_CHANGES | **Research Note ID:** 2bfcac20-aba5-4457-86f3-6ed301bea124

### Verified Facts (post-correction pass)

1. **ONEON = ZERO ZK** (HIGH, 0.95) — grep-verified. oneon-web src/ has only .next/ artifact; no circuits, provers, verifiers, groth16, plonk, halo2, noir, or circom. OPRLP contracts also clean. Privacy model = AES-256-GCM + ECDSA session keys only.

2. **SP1 = production-ready NOW** (HIGH, 0.90) — MIT, $4B+ assets secured, $0.04/proof (45x cheaper than 2024). No blockers. **CAVEAT:** Succinct Prover Network = Testnet Stage 2.5 only — self-hosted prover required initially. Assumes Rust capability on ONEON team.

3. **Aztec/Noir = BLOCKED until July 2026** (HIGH, 0.95) — Critical proving system vulnerability Mar 17 2026. Gate active. Sources: zk-ecosystem-research-2026-04-10.md §1, zk-chain-landscape-2026.md. **PATCHED:** Prior citation of memory `873df1fd` was wrong (that memory = Midnight GitHub dep failure, not Aztec vuln).

4. **Lens Chain = ONEON L3 blueprint** (MEDIUM, 0.75) — ZK Stack L3, identity/social, launched April 2025, $31M raised, $22.4M ZK grant, Avail DA, GHO gas.

5. **L3 RaaS = MVP chain entry** (MEDIUM, 0.75) — Caldera/Conduit/Zeeve. Days to deploy, $99-$5K/mo, no sequencer ops. Do not build sovereign chain before demand proven.

6. **Midnight = partner, not fork** (MEDIUM, 0.75) — GitHub repo has unresolvable deps (IOG CI only); Aliit Fellowship (9.6B NIGHT) is the correct approach. Frame ONEON as app layer Midnight lacks.

7. **Proof system matrix** (HIGH, 0.92) — **PATCHED:** Aztec is a chain, not a proof system. Matrix corrected:
   - Groth16 = cheapest L1 verify (200K-300K gas)
   - Halo2 = no trusted setup + recursion (Midnight)
   - SP1 = general Rust computation (production leader)
   - STARK/FRI = post-quantum (Starknet/zkSync)
   - **Noir/Honk (UltraHonk) = private contracts (WAIT until July 2026)**

### Three-Phase Roadmap
1. **NOW (P0):** SP1 ZK credential proofs on Base L2. Prerequisite: define ZK predicate (wallet binding vs. selective disclosure vs. anon credentials) before sprint starts. Self-hosted prover.
2. **PARALLEL:** Midnight Aliit Fellowship application.
3. **Q3 2026 (P1):** L3 RaaS deploy (Lens Chain template).
4. **July 2026:** 2-week Noir/Honk spike for private contracts.

### Validation Flags Applied
- PATCHED: Claim 3 source attribution (873df1fd removed, ecosystem doc §1 cited)
- PATCHED: Proof system matrix (Aztec→Noir/Honk UltraHonk)
- WARNING ADDED: SP1 prover network testnet-only; self-hosted required
- NOTE: P0 needs ZK predicate design step first
- BLOCKER: Knowledge graph (Neo4j) returned 500 during retrieval — may contain prior ONEON architecture decisions not captured in semantic memory. Verify before finalizing.

### Gates (DO NOT VIOLATE)
- **GATE: Aztec/Noir** — DO NOT USE before July 2026 (critical vuln Mar 17 2026)
- **GATE: Polygon zkEVM** — SUNSETTING 2026, do not deploy

### Action Items
1. Define ZK predicate for ONEON P0 (wallet-binding? selective disclosure? anon credentials?)
2. Set up SP1 self-hosted prover for Base L2
3. Apply Midnight Aliit Fellowship
4. Fix Neo4j (500 error) and query prior ONEON architecture decisions
5. Evaluate Noir/Honk for private contracts after July 2026 vuln fix
6. Evaluate Taiko for SOS/DPC governance contracts (most decentralized ZK rollup in production)

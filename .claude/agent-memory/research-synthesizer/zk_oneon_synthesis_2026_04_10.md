---
name: ZK ONEON Architectural Decision Framework Synthesis
description: Full synthesis of ZK build/fork/layer research for ONEON identity protocol — phased path, proof system selection, Midnight strategy, Lens Chain precedent
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **ONEON has zero ZK implementation today** — Confidence: HIGH | Sources: 2 (codebase grep verified: `grep -r "zk|circuit|prover|verifier|groth16|plonk|halo2|noir|circom" /mnt/media/projects/oneon-web/` returned only `.next/` build artifact; OPRLP `src/` contracts returned no matches). Gap claim confirmed with search evidence.

2. **SP1 is the production-ready ZK toolchain to use NOW** — Confidence: HIGH | Sources: 3 (semantic memory ID bdb5e743, ecosystem research doc, memory ID 8e014cd3). 99.7% ETH block coverage <12s, $4B+ assets secured, MIT license, Optimism/Base/Unichain prover. Proving cost dropped 45x in 2025 ($1.69→$0.0376/proof). No blockers.

3. **Aztec/Noir is BLOCKED until July 2026** — Confidence: HIGH | Sources: 3 (semantic memory ID 8e014cd3, chain landscape doc, memory ID 873df1fd cross-validates Midnight vuln timing). Critical proving system vulnerability disclosed Mar 17 2026; v5 fix expected July 2026. Do not use for any production work before then.

4. **Lens Chain is the exact ONEON precedent** — Confidence: MEDIUM | Sources: 2 (build/fork analysis doc, embedded URLs). ZK Stack L3, identity/social use case, Avail DA, GHO gas token, $31M raised, $22.4M ZK grant received. Launched April 4 2025. Direct template for ONEON chain phase.

5. **L3 RaaS is the best MVP chain path** — Confidence: MEDIUM | Sources: 2 (build/fork analysis doc, RaaS landscape). Caldera/Conduit/Zeeve — deploy in days, $99-$5K/mo, zero commitment. Only valid step before demand is proven at chain level.

6. **Midnight is a strategic ZK partner, not a build target** — Confidence: MEDIUM | Sources: 3 (semantic memories 46afe0b6, 30bf5a98, 873df1fd). Mainnet live Mar 30 2026 (federated). Halo2 BLS12-381, compliance-native privacy. BUT: `midnight-node` GitHub has unresolvable dependencies — independent build impossible without CI access (search: `ls /mnt/media/projects/midnight-*` → no local clone found; confirmed via semantic memory 873df1fd). Aliit Fellowship offers 9.6B NIGHT grant — partnership > fork.

7. **Proof system selection is deterministic by use case** — Confidence: HIGH | Sources: 3 (memory bdb5e743, ecosystem doc, chain landscape). Groth16: cheapest L1 verify (200K-300K gas); Halo2: no trusted setup + recursion (Midnight); SP1: general Rust computation (production leader); STARK/FRI: post-quantum (Starknet/zkSync); Aztec: private contracts (WAIT).

8. **Polygon zkEVM is sunsetting 2026** — Confidence: MEDIUM | Sources: 1 (chain landscape doc). Migrating to CDK/AggLayer. Do not build on Polygon zkEVM — choose CDK or ZK Stack instead.

---

## Contradictions / Uncertainties

- **Midnight build feasibility**: Mainnet is live (confirmed) but `midnight-node` GitHub dependencies are unresolved (confirmed). Contradiction: "live" chain vs "unbuildable" repo. Resolution: federated mainnet uses IOG-controlled CI; public repos are incomplete by design. Treat as partnership-only until public build path exists.
- **ZK Stack vs OP Stack + SP1**: Both are valid chain paths at similar cost ($50K-$500K). Lens Chain chose ZK Stack. The distinction is Elastic Chain interoperability (ZK Stack) vs lower engineering risk (OP Stack). No single-source resolution — requires ONEON architecture decision.
- None found that affect the P0 action (SP1 circuits on Base is unambiguous).

---

## Recommended Actions (top 3, specific and implementable)

1. **P0 NOW: Build SP1-based ZK credential proofs on Base** — Spin up SP1 circuit for ONEON identity credential (e.g., wallet→identity proof without revealing underlying data). No chain deployment needed. Timeline: 2-4 weeks. Expected impact: ONEON gets ZK capability immediately; proves the privacy story before chain work starts.

2. **PARALLEL: Apply for Midnight Aliit Fellowship** — Submit application at Midnight Network Aliit Fellowship program (9.6B NIGHT grant pool). Frame ONEON as the application layer Midnight lacks. Expected impact: grant funding + ecosystem positioning + partnership access to CI build pipeline (unblocks Midnight integration).

3. **P1 Q2 2026: Evaluate Aztec/Noir post-July vuln fix** — After July 2026, run a 2-week spike comparing SP1 vs Noir for private smart contract functionality. Expected impact: informed decision on whether ONEON needs a private contract layer (Aztec) or SP1-based proofs are sufficient.

---

## Evidence Quality Assessment

Coverage: PARTIAL — Three high-quality research docs on disk cover build/fork/layer options, 10-chain landscape, and ZK ecosystem toolchain. Knowledge graph returned 500 error (no graph data). No ZK-specific papers in implement queue. Codebase verified directly.

Source reliability: HIGH — Semantic memory (6 hits, confidence 0.88-0.92), on-disk research docs (sourced from ZK Stack docs, Lens Chain blog, Midnight GitHub analysis), direct codebase grep verification.

Gaps: (1) Knowledge graph unavailable — may contain prior ZK-related decisions not captured in semantic memory. (2) No Midnight local clone to verify dependency resolution status firsthand (confirmed via memory only). (3) SP1 circuit development effort estimate not quantified — needs a spike task to size properly.

---

## Compressed Handoff (≤1000 tokens)

**ONEON ZK Decision Framework — 2026-04-10**

**State**: ONEON = zero ZK code. Next.js app on Base. No circuits, provers, verifiers (grep-verified).

**Three-phase path**:
- **Phase 1 (NOW, weeks)**: SP1 ZK credential proofs on Base L2. No chain needed. SP1: MIT, $4B+ secured, 45x cost reduction, production-ready. Proof cost ~$0.04/proof.
- **Phase 2 (Q3 2026)**: L3 RaaS via ZK Stack if chain isolation justified. Lens Chain = exact precedent (SocialFi/identity, $31M raised, $22.4M ZK grant, Avail DA, GHO gas). Deploy in days via Caldera/Zeeve, $99-$5K/mo.
- **Phase 3 (long-term)**: Full ZK Stack sovereign chain only after demand proven at RaaS L3.

**Parallel track**: Midnight partnership. Mainnet live Mar 30 2026. Halo2 BLS12-381, compliance-native privacy. ONEON = application layer Midnight lacks; Midnight = ZK proof infra ONEON needs. Apply Aliit Fellowship (9.6B NIGHT grants). Do NOT attempt to fork/build independently — GitHub repos have unresolvable dependencies.

**Hard blocks**:
- Aztec/Noir: BLOCKED until July 2026 (critical proving system vuln Mar 17 2026)
- Midnight independent build: BLOCKED (unresolvable GitHub dependencies, no CI access)
- Polygon zkEVM: SUNSETTING — avoid

**Proof system selection matrix**:
| Need | System |
|------|--------|
| Cheapest L1 verify | Groth16 (200K-300K gas) |
| No trusted setup + recursion | Halo2 |
| General Rust computation | SP1 (production leader) |
| Post-quantum | STARK/FRI |
| Private smart contracts | Aztec (WAIT until July 2026) |

**ZK auditors when ready**: Veridise (specialist), Trail of Bits (circomspect), Nethermind Security (Noir/Aztec), ZK Security (Halo2).

**Grants available**: EF $900K, Starknet $25K-$1M STRK, ZKsync 5M ZK tokens, Midnight 9.6B NIGHT (Aliit).

**memory_write_token**: `17041e37-b680-4990-8966-a630c97e8dfc`

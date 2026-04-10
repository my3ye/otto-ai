---
name: ZK ONEON Architectural Decision Framework — Step 2 Validation
description: Validation of ZK synthesis for ONEON (2026-04-10, WF Step 2): MINOR_CHANGES 7.5/10. 2 criticals: source attribution error on Claim 3; "Aztec" in proof system matrix is a chain not a proof system. Core conclusions solid.
type: project
---

## Review: ZK ONEON Decision Framework Validation
**Date:** 2026-04-10 | **WF Step:** 2 (Validation) | **Verdict:** MINOR_CHANGES | **Score:** 7.5/10

### Critical Issues
1. **Source attribution error on Claim 3 (Aztec/Noir blocked)**: Synthesis cites memory ID 873df1fd as "cross-validates Midnight vuln timing" — but 873df1fd is about Midnight's GitHub dependency issues, NOT Aztec/Noir's critical vulnerability. Correct third source is the ecosystem research doc. The claim itself is valid (HIGH confidence justified), but the cited source doesn't support what's attributed to it.

2. **Category error in proof system matrix (Claim 7)**: Matrix lists "Aztec: private contracts (WAIT)" but Aztec is a chain/platform, not a proof system. Should be "Noir/Honk" — Aztec's DSL and underlying proof system. Conflates platform with protocol.

### Warnings
1. **SP1 prover network is testnet-only**: The synthesis correctly identifies SP1 zkVM as production-ready, but the Succinct Prover Network (outsourced proving) is still in TESTNET Stage 2.5. For ONEON using SP1, they'll need to run their own prover or use centralized proving initially — this operational detail is absent from the P0 action item.

2. **P0 action lacks circuit specificity**: "Build SP1-based ZK credential proofs on Base" doesn't define what credential is being proven. ONEON's privacy model is AES-256-GCM + ECDSA session keys. The synthesis doesn't identify which specific predicate ONEON needs to prove (e.g., wallet-to-identity binding, selective attribute disclosure, anonymous credentials). This affects proof system choice — SP1 is for general Rust computation, not specifically credential predicates where circom or Noir may be more appropriate primitives.

3. **Ecosystem doc executive summary inconsistency**: The ecosystem research doc's executive summary (line 13) originally stated "Aztec + Noir is the strongest path for adding ZK privacy" — written without the Aztec vulnerability context fully factored in. The synthesis correctly overrides this with SP1 priority, but does not explicitly acknowledge the resolution, leaving a subtle contradiction between source and synthesis.

4. **Knowledge graph gap is underweighted**: Graph API returned 500 error; this is flagged but described only as "may contain prior ZK-related decisions." Given that prior architecture sessions (e.g., ONEON invisible web3 architecture, ONEON competitive gap analysis) were ingested to the graph, this could contain architectural constraints that contradict the synthesis. Should be explicitly flagged as a required follow-up before finalizing architectural decisions.

### What's Good
- Core conclusion cluster is correct and well-supported: ONEON zero ZK (grep-verified), SP1 production-ready (3 sources), Aztec/Noir blocked (3 sources, even with one attribution error), Midnight partnership > fork (3 sources)
- Contradictions section handles the Midnight "live vs unbuildable" paradox cleanly and correctly
- Confidence calibration is appropriate: HIGH claims have 3 sources; MEDIUM claims have 2
- Three-phase roadmap (Base circuits → L3 RaaS → sovereign chain) matches source recommendations exactly
- Proof cost data ($0.04/proof, 45x reduction) is correctly sourced from chain landscape doc
- BLOCKED flags (Aztec, Midnight build, Polygon zkEVM sunset) are all verified in source documents
- Lens Chain precedent is accurate: ZK Stack L3, same identity/social use case, confirmed April 4 2025 launch

### What's Missing (would change conclusions)
1. **ONEON's specific ZK use case undefined** — what predicates need proofs? This is the missing input that determines SP1 vs circom vs Noir priority
2. **Team Rust capability** — SP1 requires Rust; if ONEON team is TypeScript-native, Noir is more appropriate (when unblocked)
3. **Graph data** — prior architectural constraints in Neo4j not accessible during this synthesis

**Pattern noted:** Source attribution errors in synthesis Step 1 are a recurring issue in multi-source research pipelines. Synthesizer needs to verify each cited memory ID actually supports the specific claim before tagging it.

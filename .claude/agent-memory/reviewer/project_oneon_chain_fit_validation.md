---
name: ONEON chain fit & technical direction synthesis validation
description: ONEON chain fit synthesis (2026-04-13, WF Step 2): MINOR_CHANGES 7.5/10. 1 critical (session key custody omitted from known prior gap), 2 warnings (SP1 prover testnet-only absent; Insight 3 HIGH confidence from negative grep). No {topic} bug. All codebase claims verified correct.
type: project
---

## Review: MINOR_CHANGES
**Date:** 2026-04-13 | **WF Step:** 2 (Validation) | **Score:** 7.5/10

### Codebase Claims — All Verified Correct
- Zero .sol, .rs, .circom, .nr files in oneon-web: CONFIRMED (find = 0)
- Zero wagmi/viem/ethers/web3 imports in oneon-web app: CONFIRMED
- package.json has zero blockchain deps (Next.js + Tailwind only): CONFIRMED
- Base L2 in invisible-web3-layer-architecture doc Decision 2: CONFIRMED (exact text present)
- Polygon zkEVM at line 6 of on-chain-architecture doc: CONFIRMED
- Section 11 "Gas Estimates (Polygon zkEVM)" at line 1883: CONFIRMED (50 gwei pricing)
- 6 contract names (ContributionRegistry, DemandOracle, RevenueRouter, GovernanceAccrual, ReputationNFT, ProductionTrigger): CONFIRMED
- oneon_identities table + tier column (waitlist/custodial/self_sovereign/sovereign): CONFIRMED (migration 069)
- ERC-4337 eager deploy + session keys + paymaster in arch doc: CONFIRMED
- Zero SP1/ZK code in oneon memory routes: CONFIRMED

### Critical Issues (1)
1. **Session key private key custody omitted** — Prior review (March 2026, invisible web3 architecture) flagged as CRITICAL: for Tier 1 auto-signing, the server must hold the private key corresponding to the session key. Where does it live (vault, HSM, memory-only)? This gap is still unresolved in the arch doc and is absent from the synthesis. The P0 ZK sprint and ERC-4337 implementation both depend on resolving this before any coding starts. Should appear as Action 4 or a NEEDS_MEV_INPUT.

### Warnings (3)
1. **SP1 Prover Network is testnet-only** — Prior ZK ONEON validation flagged this: the Succinct Prover Network (outsourced proving) is Stage 2.5 testnet. For ONEON P0, they must run their own prover or use centralized proving. Synthesis Action 1 doesn't include this operational constraint. Affects timeline and infra budget.

2. **Insight 3 HIGH confidence is reasoning-based, not evidence-count-based** — "ZK Predicate = P0 Decision Gate — HIGH | Sources: grep-verified (zero hits)". Negative grep evidence proves the gap exists; calling it HIGH confidence uses that as a proxy for the P0 gate classification. The P0 classification is an architectural judgment from one memory hit (ZK arch doc). Should be labeled "HIGH (code-verified gap, architectural judgment)" to clarify the distinction.

3. **Gas estimate direction note missing** — The synthesis correctly identifies Section 11 gas estimates as stale (Polygon at 50 gwei). It says "recalculate for Base" but doesn't note the direction: Base L2 gas is dramatically cheaper (10-100x lower). Full chair lifecycle at $0.10-0.15 on Polygon would be $0.001-0.015 on Base. This is favorable news that informs the architecture (even more operations can be on-chain than the Polygon estimates suggested).

### Suggestions
- Source independence caveat for Insight 1 "5 sources": The 5 sources for Base L2 include several semantic memories derived from the same prior architecture decision (echo chamber risk). The primary source (invisible-web3-layer arch doc Decision 2) is definitive alone — the memory count inflates independence. Still correctly labeled HIGH; just worth noting.
- No {topic} template bug (first occurrence of clean synthesis in recent series — good)

### What's Good
- All codebase claims independently verified correct against grep/find
- Chain conflict correctly identified and resolved (Base wins over Polygon — right call, right rationale)
- Contradictions section handles the Polygon/Base conflict cleanly
- Berachain MEDIUM/1-source is correctly calibrated
- Recommended actions are specific and implementable (named file, named contract, named testnet)
- ZK phase roadmap matches prior synthesis (consistent across review cycles)
- No {topic} template bug — clean synthesis

### Pattern
Session key private key custody is a recurring CRITICAL gap in ONEON architecture reviews. Appears in: invisible web3 review (March 2026), present synthesis omission. Must be included in any ONEON implementation review until explicitly resolved.

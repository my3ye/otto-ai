---
name: ONEON Technical Direction & Chain Fit (2026-04-13)
description: Full research pipeline on ONEON chain selection, ZK architecture, and contract readiness — Base confirmed, Polygon stale conflict found, session key custody gap surfaced
type: project
---

## Status: PIPELINE COMPLETE — 7.5/10 (MINOR_CHANGES)

**Date:** 2026-04-13
**Research Note ID:** 824cf9b8
**Semantic Memories:** 8 stored (IDs: 2b73ce8b, 8108562d, 9315a105, a49d0422, a5e3392d, 0f8df928, 6269ca86, d5242168)
**Sources:** 33 (4 web, 20 semantic memory, 0 graph/Neo4j 500 error, 5 code files, 4 internal docs)

## Key Findings

1. **Base L2 = CONFIRMED** — Decision 2 in invisible-web3-layer-architecture-2026-03-28.md. Full ecosystem (zkPresence/SOS/Otto Music/ONEON) = Base.

2. **Critical stale conflict** — on-chain-architecture-live-organism-2026-03-28.md line 6 = "Polygon zkEVM" (sunsetting). Section 11 gas estimates Polygon-based. Must be updated to Base before any contract deployment. Gas direction: Base is 10-100x cheaper → $0.001-0.015 vs $0.10-0.15 (favorable).

3. **ZK predicate undefined** — zero SP1/circuit/zk_predicate code (grep-verified). P0 decision gate. Recommend Option B: DPC selective disclosure. NEEDS_MEV_INPUT.

4. **Phase 0 backend exists** — /oneon/* routes, oneon_identities DB, WalletAdapter interface, DID stubs all live. Foundation ready.

5. **Zero contracts, 6 fully specified** — ContributionRegistry, DemandOracle, RevenueRouter, GovernanceAccrual, ReputationNFT, ProductionTrigger — spec-complete, not code-complete.

6. **ZK path = 3-phase** — SP1 on Base P0 (self-hosted prover required; Succinct Prover Network = testnet only) → Midnight partnership (parallel) → ZK Stack L3 RaaS Q3 2026. BLOCKED: Aztec/Noir July 2026, Polygon zkEVM.

7. **ERC-4337 production-ready on Base** — BUT session key private key custody UNRESOLVED (vault/HSM/memory-only). Must decide before ERC-4337 + SP1 sprint.

8. **Session key custody = CRITICAL gap** — Tier 1 auto-signing requires server to hold session key private key. Custody model undefined. Flagged March 2026, not resolved. NEEDS_MEV_INPUT.

## Patches Applied (5 total)

- Insight 2: Gas estimate direction added (Base 10-100x cheaper; favorable cost reduction)
- Insight 3: HIGH confidence label clarified (gap code-verified; P0 gate = 1-source architectural judgment)
- Insight 6: SP1 Prover Network testnet-only caveat (self-hosted prover required)
- Insight 7: Session key custody gap added as critical prerequisite
- New Insight 9: Session key private key custody = critical unresolved gap

## Recommended Actions (4 total)

**Why:** Two NEEDS_MEV_INPUT items gate the entire P0 sprint. Without ZK predicate + custody decisions, no SP1 or ERC-4337 work can proceed safely.

1. **NEEDS_MEV_INPUT: Define ZK predicate** — wallet-binding / DPC selective disclosure / anon creds. Recommend Option B.
2. **Fix arch doc** — on-chain-architecture-live-organism-2026-03-28.md: Polygon zkEVM → Base L2 throughout; recalculate Section 11 gas (significant reduction expected).
3. **Implement ContributionRegistry.sol on Base Sepolia** — first contract, highest leverage.
4. **NEEDS_MEV_INPUT: Session key custody** — vault / HSM / memory-only?

**How to apply:** Before any ONEON contract or ZK work, confirm ZK predicate (item 1) and custody model (item 4) with Mev. Then fix the arch doc (item 2) before starting item 3.

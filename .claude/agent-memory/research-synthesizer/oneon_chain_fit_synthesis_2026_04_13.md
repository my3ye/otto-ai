---
name: oneon_chain_fit_synthesis_2026_04_13
description: ONEON technical direction & chain fit synthesis — Base confirmed, Polygon stale, ZK predicate undefined, 6 contracts unimplemented, 3-phase ZK path
type: project
---

ONEON Technical Direction Synthesis — 2026-04-13

**Confirmed**: Base L2 = primary chain (arch doc Decision 2, invisible-web3-layer-architecture-2026-03-28.md). Full ecosystem consensus.

**Critical stale conflict**: on-chain-architecture-live-organism-2026-03-28.md line 6 targets "Polygon zkEVM" — sunsetting, must update to Base. Gas estimates (Section 11) must be recalculated.

**P0 decision gate**: ZK predicate undefined (grep-verified zero sp1/zk_predicate code). Blocks SP1 sprint. Use zkLogin pattern: DPC contribution hash as stable identity input.

**Zero contracts**: 6 fully-specified interfaces (ContributionRegistry, DemandOracle, RevenueRouter, GovernanceAccrual, ReputationNFT, ProductionTrigger) — spec-complete, not code-complete.

**Phase 0 backend EXISTS**: /oneon/* routes, WalletAdapter abstract interface, oneon_identities DB table, DID stubs.

**ZK path**: SP1 on Base (P0, after predicate defined) → Midnight Aliit Fellowship (parallel) → ZK Stack L3 RaaS Q3 2026. Aztec/Noir BLOCKED until July 2026.

**Why:** Synthesis needed to unblock ONEON Phase 1 chain integration and SP1 ZK sprint.
**How to apply:** Use this to prioritize: (1) define ZK predicate, (2) fix stale arch doc, (3) start ContributionRegistry.sol on Base.

memory_write_token: da8268e2-61a1-4992-b23f-a4ca9f63c246

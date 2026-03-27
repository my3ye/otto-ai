---
name: annotation_royalty_2026_03
description: Memory Capsule annotation layer + perpetual royalty flow — 4 contracts (AnnotationRegistry, ProvenanceGraph, UsageOracle, RoyaltyPool), Foundry on Base, 3 phases ~$24-31
type: project
---

Memory Capsule annotation & royalty architecture designed 2026-03-27. Full doc at ~/otto/docs/memory-capsule-annotation-royalty-architecture-2026-03-27.md.

**Why:** Mev directive — contributors who help build Otto's intelligence must earn perpetual royalties on-chain. Data workers are the most exploited group in AI.

**Key decisions:**
- 4 contracts: AnnotationRegistry (UUPS), ProvenanceGraph (UUPS), UsageOracle (UUPS), RoyaltyPool (IMMUTABLE — financial guarantees must be trustless)
- Foundry on Base chain (consistent with Otto Music/data layer, different from OPRLP on Polygon)
- Off-chain Shapley attribution → on-chain shares (O(2^N) infeasible on-chain)
- Batch usage reporting (60s window) not per-event (100x gas savings)
- Explicit versioning for supersession (Option C): annotator submits v2 → v1 enters 6-month half-life decay with 1% floor
- Annotations only on capsule layers 3-7 (resolves encryption boundary blocker — private layers 0-2 never on-chain)
- 6 annotation types: Label, Curation, TrainingSignal, Correction, Enrichment, Synthesis
- 4 usage triggers: Read (1×), Inference (3×), License (10×), Fork (5×)
- Phase 1: contracts + testnet (~$12-15), Phase 2: off-chain integration (~$8-10), Phase 3: mainnet + governance (~$4-6)

**Blockers:** Mev decision on supersession trigger (Option C recommended, proceeding as default). Encryption boundary formal policy needed before mainnet.

**Dependency chain:** AnnotationRegistry → ProvenanceGraph → UsageOracle → RoyaltyPool (immutable, deployed last)

**How to apply:** When scoping implementation, follow the 12-step plan across 3 phases. RoyaltyPool must be deployed last (immutable — no fixes after deploy). Shapley module is the most complex off-chain component.

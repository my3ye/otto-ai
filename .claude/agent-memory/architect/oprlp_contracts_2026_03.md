---
name: oprlp_contracts_2026_03
description: OPRLP Solidity contract architecture for 505 Systems governance — 7 contracts, Foundry, 2-phase plan
type: project
---

OPRLP smart contract architecture designed 2026-03-27. Full doc at ~/otto/docs/oprlp-solidity-architecture-2026-03-27.md.

**Why:** Mev directive for transparent rotating leadership. Contracts enforce DPC gating, council rotation, elections, emergency powers, cartel detection, and founder sunset on-chain.

**Key decisions:**
- Foundry (not Hardhat) — faster tests, native fuzz, industry standard for governance
- 7 contracts in 2 phases: Phase 1 core (DPCRegistry, GovernanceWeight, ElectionEngine, CouncilManager ~$14), Phase 2 safety (EmergencyPower, CartelDetector, FounderSunset ~$6.50)
- UUPS proxy for operational contracts; EmergencyPower + FounderSunset are immutable (no proxy, no admin)
- Lazy DPC decay at read time (not per-block keeper)
- On-chain IRV tally with 21-candidate cap (Phase 3: ZK tally for scale)
- Address-based identity Phase 1; ONEON DID migration Phase 2
- DPCMath library: Babylonian sqrt, fixed-point decay, uint128 with 18 decimals
- Oracle bridge: DB → chain one-way. New `GET /sos/dpc-export` endpoint needed.
- Repo: `/mnt/media/projects/oprlp-contracts/` (Foundry monorepo)
- Target: Polygon zkEVM primary, Arbitrum One fallback

**Dependency chain:** ONEON Identity → DPCRegistry → GovernanceWeight → ElectionEngine → CouncilManager

**Blockers:** ONEON identity not yet on-chain (Phase 1 uses raw addresses). Sortition layer awaiting Mev input.

**How to apply:** When scoping implementation tasks, follow the 9-step Phase 1 plan. Each step has a clear file target and cost estimate. Phase 2 is separate scope.

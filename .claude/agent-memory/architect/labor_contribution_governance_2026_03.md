---
name: labor_contribution_governance_2026_03
description: On-Chain Labor Contribution & Governance Framework — 6 contracts (LaborAttestation, ContributionEquity, VestingEngine, SiteOracle, SkillBountyRegistry, EquityTreasury), multi-party attestation, soulbound CET, 3 phases ~$30-40
type: project
---

On-Chain Labor Contribution & Governance Framework designed 2026-03-28. Full doc at ~/otto/docs/on-chain-labor-contribution-governance-architecture-2026-03-28.md.

**Why:** Mev directive — physical labor and real-world contributions must translate to verifiable on-chain equity and governance. Traditional employer-employee extraction must be structurally impossible. Builds on DPC formula (Pink Paper) and OPRLP governance.

**Key decisions:**
- ERC-1155 soulbound CET (non-transferable) — prevents equity extraction via market purchase
- Multi-party attestation (2-of-3: self + peers + site oracle) — no single-employer sign-off
- 7 contribution types (PHY/MAT/SKL/OPS/EDU/COM/DIG) with DPC component weights — not flat hours
- Contribution-weighted vesting (hours-based, not time-cliff) — rewards work, not patience
- Daily batched on-chain submission (merkle root + claims) — gas: $0.50/day vs $5-10 per-tx
- Same chain as OPRLP (Polygon zkEVM) — DPCRegistry on same chain
- Agent tax 30% (DAO-adjustable) flows to redistribution pool per Mev directive
- Anti-collusion: temporal separation, rotating attesters, attestation staking, statistical detection

**Dependency chain:** OPRLP DPCRegistry (blocker) → LaborAttestation → ContributionEquity → VestingEngine. Phase 2: SiteOracle → SkillBountyRegistry → EquityTreasury.

**Open question for Mev:** CET revenue governance model — hybrid (CET holders decide within bounds set by OPRLP Treasury council) recommended.

**How to apply:** Phase 1 core contracts ~$14-18, Phase 2 oracle+incentives ~$10-14, Phase 3 Memory API integration ~$6-8. Requires OPRLP DPCRegistry deployed first.

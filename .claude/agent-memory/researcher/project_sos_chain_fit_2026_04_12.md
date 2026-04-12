---
name: SOS Technical Direction & Chain Fit (2026-04-12)
description: 505 Systems (SOS) governance protocol chain selection and contract build state — oprlp-contracts audit, Phase 1 chain fit, build gaps, grant paths
type: project
---

## 505 Systems (SOS) — Technical Direction & Chain Fit Research
**Completed:** 2026-04-12 | **Validation:** 7.5/10 MINOR_CHANGES | **DB Note:** 2e838710

### Chain Selection: Base (Phase 1)
- Aragon OSx live on Base (official blog confirmed)
- Chainlink VRF v2.5 available on Base
- oprlp-contracts chain-agnostic (no hardcoded RPC in foundry.toml)

### Contract State (grep-verified, internal audit — not external audit)
**EXIST + TESTED:**
- `DPCRegistry.sol`, `GovernanceWeight.sol`, `ElectionEngine.sol`, `CouncilManager.sol`
- Foundry, Solidity 0.8.24, Shanghai EVM. Integration test: `FullRotation.t.sol`
- All prior review issues RESOLVED: maxWeightBps cap (GovernanceWeight.sol ~L40-55), voteRecall weighting (CouncilManager.sol), QUORUM_BPS (ElectionEngine.sol L200), RECALL_VOTE_BPS (CouncilManager.sol L199)

**CRITICAL PATCH: ElectionEngine uses IRV, NOT sortition**
- `ElectionEngine.sol:11` declares IRV tallying, uses `RankedChoice.sol`
- Elections CAN run without Chainlink VRF under current IRV model
- VRF sortition (dpc^0.7 + VRF) is designed but unbuilt — separate from current election path
- VRF integration = future sortition path build, not elections blocker

### Verified Gaps (grep-verified: 0 matches each)
1. **VRF sortition** — 0 VRF references in src/ — needs build when moving from IRV to sortition
2. **Aragon OSx DPC plugin** — no plugin code in any repo — P1 build dependency for Phase 1 mainnet
3. **Labor contracts** — 0 code (LaborAttestation, ContributionEquity, VestingEngine, SiteOracle, SkillBountyRegistry, EquityTreasury) — design at ~/otto/docs/labor-contribution-smart-contract-architecture-2026-03-28.md
4. **505-systems-web** — 0 wagmi/viem/ethers/web3 matches — pure content site
5. **Deployed addresses** — none, pre-deployment

### Phases
- Phase 0: Snapshot + Gnosis Safe (current)
- Phase 1: Aragon OSx + DPC plugin on Base
- Phase 2: Custom Solana (full Rust/Anchor rewrite — not extension)

### Grants
- W3F Level 1 ($10K) + Gitcoin GG24 VIABLE
- MIT license CONFIRMED (SPDX headers, all 10 source files — NOT pending verification)

### Sybil
- Paper 2505.09313 (LightGBM, 0.94 precision) → 3-wallet-per-person cap enforcement (off-chain, pre-mainnet)

### Top Actions
1. Build Aragon OSx custom DPC plugin (Phase 1 mainnet dependency)
2. Wire VRF into ElectionEngine.sol (sortition path — not elections blocker)
3. Build LaborAttestation.sol + VestingEngine.sol in oprlp-contracts/src/labor/
4. Register for Gitcoin GG24 (MIT confirmed, governance tooling)
5. Wire 505-systems-web web3 (wagmi + DPC dashboard)

### Corrections Applied
- Patched Insight 3: VRF "P0 elections blocker" → elections CAN run under IRV; VRF = future sortition path
- Patched Insight 8: MIT license "pending verification" → confirmed via SPDX headers

**Why:** SOS governance protocol audit needed before Phase 1 planning. Confirms chain fit and exposes build gaps.
**How to apply:** Use this as ground truth for oprlp-contracts build roadmap decisions. Check contract code before assuming review issues still open.

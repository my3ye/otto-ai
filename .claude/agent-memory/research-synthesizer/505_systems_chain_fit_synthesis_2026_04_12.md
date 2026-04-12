---
name: 505_systems_chain_fit_synthesis_2026_04_12
description: 505 Systems (SOS) technical direction & chain fit synthesis — contract status, chain selection, pre-deployment blockers, governance phases, grant paths
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Base is confirmed primary chain for Phase 1** — Chainlink VRF v2.5 live on Base, Aragon OSx live on Base, oprlp-contracts chain-agnostic (no hardcoded RPC), EVM Shanghai target confirmed. — Confidence: HIGH | Sources: 4 sources (web + code + memory)

2. **4 core contracts compiled + tested; CRITICAL/HIGH review issues resolved** — DPCRegistry.sol, GovernanceWeight.sol, ElectionEngine.sol, CouncilManager.sol all in src/core/. Integration test (FullRotation.t.sol) exists. maxWeightBps cap is enforced. voteRecall uses voterWeight>0 check + weighted accumulation. — Confidence: HIGH | Sources: 3 sources (grep-verified)

3. **Chainlink VRF NOT wired into ElectionEngine.sol** — Zero VRF/chainlink/vrfCoordinator references in oprlp-contracts/src/ (grep: 0 matches). ElectionEngine exists but runs no randomness. Sortition requires VRF before any mainnet election can run. — Confidence: HIGH (grep-verified gap) | Sources: code

4. **Labor contribution contracts are designed-only; not in codebase** — LaborAttestation, ContributionEquity, VestingEngine, SiteOracle, SkillBountyRegistry, EquityTreasury — grep across oprlp-contracts/: 0 matches. Documented in ~/otto/docs/ but not built. — Confidence: HIGH (grep-verified gap) | Sources: memory + code

5. **Phase 2 (Solana) requires full rewrite** — All contracts are Solidity/Foundry/EVM. No Rust/Anchor contracts exist. Governance phase 2 target is "fully custom on Solana" — this is a major multi-month effort, not an extension. — Confidence: HIGH | Sources: code + memory

6. **505-systems-web has zero on-chain integration** — wagmi/viem/ethers/web3/useWallet grep returned 0 code matches. Pure content/marketing site. Connect-wallet and DPC dashboard are future work. — Confidence: HIGH (grep-verified) | Sources: code

7. **DPC formula + governance tier structure fully designed** — P=f(Is,Ec,Rw), 3 tiers (18+7+5 seats, 90/180/365-day terms, DPC min 500/2000/5000), sortition via dpc^0.7 + VRF. Pink Paper live at 505.systems/pink-paper. — Confidence: HIGH | Sources: 5 sources (web + memory)

8. **Sybil detection paper 2505.09313 applicable** — LightGBM subgraph analysis, precision 0.94. Directly maps to 505 Systems 3-wallet-per-person governance cap. Implementation candidate. — Confidence: MEDIUM | Sources: 1 paper

9. **W3F + Gitcoin GG24 grant paths viable** — W3F Level 1 ($10K) for governance tooling, Gitcoin GG24 quadratic matching. Requires Apache 2.0/MIT license (verify foundry.toml license field). — Confidence: MEDIUM | Sources: memory + web

## Contradictions / Uncertainties

- **voteRecall weighted accumulation**: Memory flags this as a HIGH pre-mainnet issue. Code review shows weightFor/weightAgainst accumulation IS present. Status appears RESOLVED but auditor confirmation not available.
- **Phase 2 Solana timeline**: Multiple sources confirm intent, none specify a date. Long-term only.
- **Aragon DPC plugin**: Exists in roadmap but no code for the custom OSx plugin found in any repo. This may be the next discrete build after VRF wiring.

## Recommended Actions (top 3, specific and implementable)

1. **Wire Chainlink VRF into ElectionEngine.sol** — File: `/mnt/media/projects/oprlp-contracts/src/core/ElectionEngine.sol`. Add VRFConsumerBaseV2 inheritance, requestRandomWords() call in election trigger, fulfillRandomWords() handler for sortition execution. Expected impact: unblocks mainnet elections — Phase 1 governance can't run without this.

2. **Build labor contribution contracts layer** — Create `/mnt/media/projects/oprlp-contracts/src/labor/` with LaborAttestation.sol, VestingEngine.sol as first two (highest-value). Design doc at `~/otto/docs/labor-contribution-smart-contract-architecture-2026-03-28.md`. Expected impact: enables contributor equity on-chain — core to DPC economic model.

3. **Register for Gitcoin GG24 now** — Open registration window (deadline unspecified, treat as urgent). Project: open-source DPC governance tooling. Repo: oprlp-contracts. License check required first (grep foundry.toml for SPDX / check README). Expected impact: quadratic funding = non-dilutive capital for protocol dev.

## Evidence Quality Assessment

Coverage: PARTIAL — Web (4), Memory (9), Code (5), Papers (1). Knowledge graph returned empty (no 505 Systems nodes indexed). Core governance contract internals inspected directly.
Source reliability: HIGH — Memory entries from recent verified tasks (0.362–0.979 scores). Code grep direct observation. Web sources authoritative (Aragon official blog).
Gaps: VRF implementation specifics (VRF subscription setup, coordinator address per chain), Aragon OSx plugin architecture for DPC custom plugin, grant deadline dates.

## Compressed Handoff (≤1000 tokens)

**505 Systems / SOS — Chain Fit & Technical State (2026-04-12)**

PRIMARY CHAIN: Base. Rationale: Aragon OSx live on Base (confirmed), Chainlink VRF v2.5 on Base (required for sortition), oprlp-contracts chain-agnostic. Phase 1 = Aragon OSx + custom DPC plugin.

CONTRACT STATE (grep-verified):
- 4 core contracts EXIST + TESTED: DPCRegistry.sol, GovernanceWeight.sol, ElectionEngine.sol, CouncilManager.sol (Foundry, Solidity 0.8.24, Shanghai EVM). Integration test: FullRotation.t.sol.
- CRITICAL issue (maxWeightBps cap) = RESOLVED in GovernanceWeight.sol.
- HIGH issue (voteRecall DPC check) = RESOLVED via voterWeight>0 + weightFor/weightAgainst accumulation.

VERIFIED GAPS:
1. Chainlink VRF: grep oprlp-contracts/src/ → 0 VRF/chainlink/vrfCoordinator matches. ElectionEngine has no randomness. **P0 blocker for mainnet elections.**
2. Labor contracts: grep oprlp-contracts/ → 0 LaborAttestation/ContributionEquity/VestingEngine matches. Designed (doc at ~/otto/docs/), not built.
3. Web3 frontend: 505-systems-web grep wagmi/viem/ethers → 0 matches. Pure content site.
4. Deployed addresses: zero production addresses in oprlp-contracts/src/. Pre-deployment.

DOWNGRADED (was gap, now needs extension):
- Sortition design: ElectionEngine.sol EXISTS. It needs VRF extension, not a full build.
- voteRecall: CouncilManager.sol EXISTS with DPC check. Review issues appear resolved.

PHASE ROADMAP:
- Phase 0: Snapshot + Gnosis Safe (off-chain, current)
- Phase 1: Aragon OSx + DPC plugin on Base (needs VRF + plugin build)
- Phase 2: Custom Solana (full Rust/Anchor rewrite — long-term)

DPC FORMULA: P=f(Is,Ec,Rw). Tiers: 3 (18+7+5 seats, 90/180/365-day, DPC min 500/2000/5000). Sortition: dpc^0.7 + VRF.

GRANTS: W3F Level 1 ($10K), Gitcoin GG24. License check needed.
SYBIL: Paper 2505.09313 (LightGBM, 0.94 precision) → maps to 3-wallet cap enforcement.

memory_write_token: a9dec1eb-ccf4-4767-b23f-f16550e16c2d

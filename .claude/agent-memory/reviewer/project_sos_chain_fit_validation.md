---
name: SOS 505 Systems chain fit synthesis validation
description: 505 Systems technical direction & chain fit synthesis (2026-04-12, WF Step 2). MINOR_CHANGES 7.5/10. Critical: IRV/sortition conflation makes VRF "P0 blocker" claim misleading. {topic} bug (12th+ instance). Grants: MIT license confirmed.
type: project
---

SOS 505 Systems chain fit synthesis validation — 2026-04-12, WF Step 2.

**VERDICT: MINOR_CHANGES — 7.5/10**

## Critical Issues

1. **VRF/sortition vs IRV conflation** — Insight 3 claims "DPC-weighted sortition requires VRF to execute any council election. Mainnet elections cannot run without this integration." WRONG. ElectionEngine.sol uses **IRV (Instant Runoff Voting)** via `RankedChoice.sol`, not sortition. Elections can run without VRF. VRF is needed for the dpc^0.7 sortition design (documented in governance spec/memory), but that design is NOT implemented in ElectionEngine.sol. The correct framing: VRF sortition is a designed but unbuilt feature. Elections can run via IRV without it. The "P0 blocker" label is misleading.

2. **{topic} unsubstituted** — Task header shows "Topic: {topic}" — 12th+ instance of this recurring template injection failure.

## Warnings

3. **Grant license: already confirmed — action not pending** — Synthesis flags "Requires Apache 2.0/MIT license verification." Grep confirms all SPDX headers = MIT. Not a pending action — it's done. Report should say "MIT confirmed."

4. **Aragon DPC custom plugin gap** — Synthesis flags this as a "contradiction/uncertainty" but it should be promoted to a Recommended Action (build the Aragon OSx plugin interface). Currently buried.

## Verified Correct

- All 4 core contracts confirmed in /src/core/ via ls: DPCRegistry.sol, GovernanceWeight.sol, ElectionEngine.sol, CouncilManager.sol
- VRF gap CONFIRMED: 0 grep matches for VRF/chainlink/vrfCoordinator in src/ (gap is real but misframed as P0 election blocker)
- Labor contracts gap CONFIRMED: 0 matches for LaborAttestation/ContributionEquity/VestingEngine in oprlp-contracts/
- maxWeightBps cap CONFIRMED resolved: GovernanceWeight.sol lines ~40-55 implement anti-whale cap correctly
- voteRecall DPC fix CONFIRMED: CouncilManager.sol has `voterWeight>0` guard + `weightFor`/`weightAgainst` accumulation
- QUORUM_BPS CONFIRMED enforced: ElectionEngine.sol line 200 (was a prior unfixed issue per earlier review — now fixed)
- RECALL_VOTE_BPS CONFIRMED enforced: CouncilManager.sol line 199
- Base chain selection: HIGH/4-source is appropriate
- 505-systems-web web3 gap: confirmed (node_modules only, no source imports)

**Why:** IRV vs sortition is a fundamental distinction — one needs VRF, one doesn't. Mislabeling IRV elections as VRF-blocked would mislead builders about what needs to be done before mainnet.

**How to apply:** In any SOS governance synthesis, verify whether ElectionEngine uses IRV or sortition before labeling VRF a P0 blocker.

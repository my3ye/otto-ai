---
name: Tusita chain fit synthesis validation
description: Tusita technical direction & chain fit synthesis (2026-04-13, WF Step 2): MINOR_CHANGES 8.0/10. 2 warnings: Aragon "1 codebase" source fabricated (zero Aragon refs in tusita-web); "structurally isomorphic" overstates DPCRegistry fork complexity (single-dim uint128 vs 3-weighted Tusita CS). Core claims all grep-verified. No {topic} bug.
type: project
---

## Tusita Chain Fit Synthesis Validation (2026-04-13, WF Step 2)

**Verdict: MINOR_CHANGES 8.0/10**

All 8 core claims grep-verified in tusita-web codebase. Two warnings require correction before implementation planning proceeds.

### Claims Verified

- **Zero .sol files**: CONFIRMED. No `.sol`, `.rs`, `.circom`, `.nr` in tusita-web.
- **CS dimensions (Capital 30% / Resources 25% / Labour 45%)**: CONFIRMED. governance.ts weights: 30, 25, 45.
- **$TUSITA 35% contributor pool + 25% treasury**: CONFIRMED. tokenomics.ts label "Contributor Rewards Pool"=35%, "Community Treasury"=25%.
- **4-tier NFT (Islander/Steward/Founder/Sovereign)**: CONFIRMED. tokenomics.ts nftTiers.
- **Dynamic NFT metadata**: CONFIRMED. faq.ts line 35: "NFT metadata evolves dynamically with your Contribution Score."
- **"Base governance voting" = feature label, not chain declaration**: CONFIRMED. It appears in Islander tier benefits list. Context = "Residency rights, base contributor status" → basic/foundational governance access.
- **Phase 4 RWA = "60+ Months"**: CONFIRMED. roadmap.ts Phase 4 timeline.
- **Phase 0 includes "Smart contract architecture" + "Founding NFT drop"**: CONFIRMED. roadmap.ts milestones.
- **DPCRegistry + lazy decay pattern**: CONFIRMED. DPCRegistry.sol line 9 "computes lazy decay on read." DPCMath.sol implements exponential decay.

### Warning 1 — Aragon "1 codebase" source FABRICATED
Insight 5 claims "Sources: 1 memory, 1 codebase" for Aragon OSx. Grep of `/mnt/media/projects/tusita-web/src/` returns ZERO Aragon references. The codebase source does not exist. Only source = SOS chain fit memory (Aragon confirmed for SOS, extrapolated to Tusita). Correct to: "Sources: 1 memory (SOS-confirmed, extrapolated)." Confidence MEDIUM is appropriate but source count is inflated.

### Warning 2 — "Structurally isomorphic" overstates fork complexity
Insight 3 claims "direct fork path via DPCRegistry + LazyDecay" and Recommended Action 3 says "fork oprlp DPCRegistry." The DPCRegistry stores a SINGLE composite score (`uint128 rawScore`). Tusita CS has THREE explicitly weighted dimensions (Capital 30%, Resources 25%, Labour 45%) requiring separate per-dimension tracking and weighted aggregation. This is not a simple fork — it requires new multi-dimensional storage (3 mappings per address) + a weighted aggregator not present in DPCRegistry. The decay pattern IS reusable, but the data model must be extended. Recommendation 3 should specify: "Fork DPCRegistry decay pattern as foundation; design new 3-dimension weighted CS storage — not a direct rename."

**Why:** The DPCRegistry uses `contributionTypes` (uint8 bitmask) for type tracking, not stored per-dimension weights. If Tusita forks as-is, Capital/Resources/Labour contributions will collapse to a single unweighted score, breaking the governance model.

### Confidence Adjustments
- Insight 5 Aragon: MEDIUM is correct; correct source count from "1 codebase" to "1 memory"
- Insight 7 SP1: Correctly labeled MEDIUM; SP1 is from zkPresence (not in tusita-web). Technology.ts says only "ZK privacy-preserving options" — generic, not SP1-specific. Extrapolation is reasonable but labeled accurately.

### What's Good
- Synthesis correctly identified "Base governance voting" as a feature label, not chain evidence — this is a subtle but important distinction that would mislead a naive reader.
- All phase timelines correctly sourced from roadmap.ts.
- CRITICAL gap verification (grep for empty .sol count) was thorough and correctly executed.
- Action 1 (write on-chain-architecture.md + declare Base) and Action 2 (Phase 0 $TUSITA ERC20 + Founding IslanderNFT) are specific and implementable.
- Source quality is honest — avoids overclaiming for a zero-contract project.

**How to apply:** Before implementing Recommended Action 3, flag that CS Registry design requires 3-dimension weighted architecture, not direct DPCRegistry fork. Build spec first.

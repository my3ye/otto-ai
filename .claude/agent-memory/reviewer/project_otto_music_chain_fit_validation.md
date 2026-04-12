---
name: otto_music_chain_fit_validation
description: Otto Music technical direction & chain fit synthesis validation (2026-04-13, WF Step 2): NEEDS_CHANGES 6.5/10. 3 criticals: Base vs Polygon zkEVM chain conflict; invented contract names (MusicTrack/MusicFactory/RevenueRouter) vs existing roadmap names (OttoMusicRights/RoyaltySplitter/StreamingPayment); security audit scope misleading. {topic} bug 14th+ instance.
type: project
---

Otto Music chain fit synthesis validation (2026-04-13, WF Step 2).

**Verdict: NEEDS_CHANGES 6.5/10**

**Why:** 3 critical issues found via grep cross-referencing. The synthesis core correction (docs-only claim for Core Value Loop contracts) is accurate and valuable. But the recommended build order introduces contract names that conflict with both the existing otto-music-roadmap (which has its own contract names) and the Core Value Loop architecture (SplitEngine.sol ≠ RevenueRouter.sol).

**Critical issues:**
1. Chain recommendation conflict: synthesis recommends Base as Phase 1, but `~/otto/docs/on-chain-architecture-live-organism-2026-03-28.md` explicitly targets "Polygon zkEVM (L2) — same as labor contracts" for the ecosystem. Deploying Otto Music on Base while CVL contracts are on Polygon zkEVM creates an undisclosed cross-chain split.
2. Invented contract names: synthesis recommends MusicTrack.sol, MusicFactory.sol, RevenueRouter.sol — none of these appear in any doc. Existing roadmap (`otto-music-roadmap-2026-03-20.md`) defines OttoMusicRights.sol, RoyaltySplitter.sol, StreamingPayment.sol, PublishingRights.sol. CVL architecture uses SplitEngine.sol (not RevenueRouter.sol). Synthesizer appears to have invented a hybrid architecture without reconciling with either.
3. Security audit claim misleading: "Security audit already complete" cites `on-chain-security-audit-2026-03-28.md` — but that audit covers Core Value Loop contracts (ContributionRegistry, DemandOracle, etc.), NOT the Otto Music-specific contracts (OttoMusicRights.sol etc.) that still need to be written. A fresh audit will be required for the music contracts.

**What was correct and verified:**
- Zero .sol files with OttoMusic/OTTM identifiers (grep-confirmed, 2737 total .sol scanned)
- RevenueRouter/DemandOracle/ContributionRegistry = docs only (zero .sol found)
- ERC-2981 at `/mnt/media/projects/oprlp-contracts/lib/openzeppelin-contracts/contracts/token/common/ERC2981.sol` ✅
- ERC721Royalty.sol available in same lib ✅
- StreamOracle absent ✅, discovery staking absent ✅, ERC-4337 paymaster (Otto Music-specific) absent ✅
- Solana rejection valid (EVM rewrite required)

**{topic} template bug**: 14th+ instance in WF Step 2 tasks — `Topic: {topic}` unresolved in task prompt.

**How to apply:** When validating chain fit syntheses, always cross-reference recommended chain against existing ecosystem architecture docs (not just web sources). When build orders propose new contract names, grep existing docs to ensure naming consistency.

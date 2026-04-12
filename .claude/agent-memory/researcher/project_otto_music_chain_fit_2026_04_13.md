---
name: Otto Music Technical Direction & Chain Fit
description: Research pipeline complete 6.5/10 (post-corrections). Otto Music=concept phase (zero .sol files). Chain choice OPEN QUESTION (Base vs Polygon zkEVM). Build order patched to use documented contract names from otto-music-roadmap-2026-03-20.md.
type: project
---

## Otto Music Chain Fit Research — PIPELINE COMPLETE 6.5/10

**Date:** 2026-04-13  
**DB Note ID:** 551809c1  
**Memories stored:** 11 (10 insights + 1 system bug)

### Key Findings (validated, post-corrections)

1. **OPEN QUESTION — Chain Selection (MEDIUM):** Base has ecosystem arguments (Sound.xyz, ONEON EVM compat, ERC-2981 in OZ lib, Coinbase distribution). BUT `on-chain-architecture-live-organism-2026-03-28.md` targets Polygon zkEVM for OPRLP/CVL. Cross-chain split unjustified. Must resolve BEFORE writing first contract.

2. **Critical correction (HIGH, grep-verified):** RevenueRouter, DemandOracle, ContributionRegistry = architecture DOCS ONLY. Zero .sol files across 2,737 scanned. Cannot be integrated without implementation sprint.

3. **Otto Music = pure concept phase (HIGH, grep-verified):** Zero .sol files with OttoMusic/OTTM identifiers. All contracts unbuilt.

4. **ERC-2981 immediately adoptable (HIGH):** OZ lib confirmed in oprlp-contracts. Only technical building block already in place.

5. **Solana = Phase 2+ only (HIGH):** Full EVM rewrite required, ONEON is EVM-native.

6. **PATCHED build order:** Must use names from `otto-music-roadmap-2026-03-20.md`:  
   OttoMusicRights.sol → RoyaltySplitter.sol → StreamingPayment.sol → PublishingRights.sol.  
   CVL architecture uses SplitEngine.sol. Prior synthesis invented MusicTrack.sol / MusicFactory.sol / RevenueRouter.sol — none exist in any doc.

7. **PATCHED security audit:** Existing audit (`on-chain-security-audit-2026-03-28.md`) covers CVL contracts ONLY. Fresh audit required after Otto Music contracts written.

8. **Competitor gap real (HIGH):** Audius/Sound.xyz/Royal all have capability gaps Otto Music fills. Market position uncontested — execution is the only blocker.

### Corrections Applied
- Chain recommendation: HIGH → OPEN QUESTION (MEDIUM) — conflicts with architecture doc
- Build order names: invented → use roadmap names
- Security audit: misleading readiness → CVL-only scope
- Sound.xyz ecosystem advantage: HIGH → MEDIUM (single source)
- $7.5M gas figure: HIGH → MEDIUM (vendor-biased source)

### P0 Action
**Resolve Base vs Polygon zkEVM FIRST.** Then: full contract implementation sprint using documented names.

**Why:** Mev needs to know Otto Music chain decision conflicts with existing architecture. Every contract written on the wrong chain is a rewrite.  
**How to apply:** Flag chain conflict whenever Otto Music contracts or deployment comes up. Do not assume Base is settled.

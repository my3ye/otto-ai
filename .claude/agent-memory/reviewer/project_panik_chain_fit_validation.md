---
name: Panik chain fit synthesis validation
description: Panik technical direction & chain fit synthesis (2026-04-10, WF Step 2): MINOR_CHANGES 8.0/10. {topic} template bug (3rd instance). $3B Retro Funding figure single-source vendor bias. Celo stats vendor source. All gap claims grep-verified correct.
type: project
---

Panik technical direction & chain fit synthesis validated 2026-04-10, WF Step 2.

**Verdict: MINOR_CHANGES 8.0/10**

**Why:** All codebase claims are grep-verified accurate. Gap analysis (PNK, soulbound, ZK, sybil) is correct. LazyDecay pattern confirmed. Two confidence issues found.

**How to apply:** This synthesis is reliable as a technical foundation. Fix 2 confidence downgrades and the template bug before using in downstream steps.

## Critical Issues Found

1. **{topic} template bug** — Task prompt contains "Topic: {topic}" (unresolved). Third instance in pipeline (also in WebAssist and ZK ONEON steps). Root cause: workflow step variable substitution is broken for the `topic` field.

2. **$3B Retro Funding: single-source vendor bias** — Synthesis claims HIGH confidence for the $3B Optimism Retro Funding pool with 4 sources, but the $3B figure appears in only 1 source: Optimism's own Mirror blog post (vendor-authored). The other 3 sources support Base deployment generally, not the $3B amount. Downgrade to MEDIUM confidence on the specific figure.

3. **Celo vendor-sourced stats** — "11M MiniPay wallets, 300M+ stablecoin txns" come from Celo's own year-in-review (vendor bias). Synthesis correctly rates Celo MEDIUM but doesn't flag bias. Confirm via third-party source before quoting in published content.

## What Verified

- DPCRegistry LazyDecay: `DPCMath.computeDecay()` called in `getScore()`, contract comment confirmed "computes lazy decay on read" — accurate
- PNK/ERC20 gap: grep confirmed no files in oprlp-contracts/src — accurate
- Soulbound/ERC4973/ERC5484 gap: grep confirmed no files — accurate
- ZK/SP1 gap in contracts: grep confirmed no files — accurate
- Sybil gap: grep confirmed no files — accurate
- UI claims: PrivacyControl.tsx line 154 (+150 PNK), line 187 ("Running on the blockchain"), AgentNetwork.tsx 0/10+/50+ thresholds — all accurate
- Governance contracts: DPCRegistry.sol, GovernanceWeight.sol, CouncilManager.sol, ElectionEngine.sol — all exist
- foundry.toml: no network RPC targets, only compiler config — validates synthesis uncertainty note
- No panik-app-web/src/contracts directory — confirmed

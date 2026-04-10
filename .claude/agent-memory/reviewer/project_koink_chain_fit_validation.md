---
name: Koink chain fit synthesis validation
description: Koink technical direction & chain fit synthesis (2026-04-10, WF Step 2): MINOR_CHANGES 7.5/10. 2 warnings: zero-.sol claim imprecise (ContributorSalary exists in otto/); ChainMarquee severity understated (full Ctrl Wallet section, not just copy). {topic} template bug recurs. Core conclusions verified solid.
type: project
---

## Verdict: MINOR_CHANGES — 7.5/10

### Critical Issues
None blocking. Core chain-fit conclusions are well-evidenced and codebase-verified.

### Warnings
1. **Zero .sol claim imprecision**: Synthesis states "no `.sol` files in `/home/web3relic/otto/`" — FALSE as stated. ContributorSalary contracts exist there (`contracts/salary/*.sol`). Correct claim: "no Koink-specific .sol files." Downstream agents may misread this as "no contracts anywhere."
2. **ChainMarquee severity understated**: Synthesis frames the Ctrl Wallet issue as "chain count mismatch" — but the entire section is Ctrl Wallet's own product page. Headline: "2,300+ chains. One wallet." H2 and body copy are all Ctrl Wallet. More severe than described — full branding contamination, not a copy detail.
3. **{topic} template bug (recurs)**: Task prompt shows "Topic: {topic}" unsubstituted. Same pattern as WebAssist synthesis (2026-04-10). Workflow template variable injection is broken for this step.
4. **Graph 500 error (3rd occurrence in same run)**: Knowledge graph returning errors across multiple synthesis tasks in this run. Infrastructure issue — not a synthesis fault, but should be flagged for investigation.

### What's Verified Correct
- standard.py: SUPPORTED_CHAINS, CHAIN_VRF_MAP, phase note, VRF validation error — all confirmed ✅
- launch.py: "OWS deploy wallet registration" unblock confirmed in docstring + message field ✅
- Ctrl Wallet placeholder: confirmed in FAQ.tsx:37 and ChainMarquee.tsx:17 ✅
- Zero Koink-specific .sol files: confirmed (no KoinkToken.sol, KoinkLauncher.sol, etc.) ✅
- Privy/paymaster grep = 0 results: confirmed ✅
- 19 chains in ChainMarquee array: confirmed ✅
- Chainlink VRF NOT on Solana: validated message at standard.py:112-113 ✅

### Confidence Rating Accuracy
- All HIGH ratings are backed by code/multi-source: appropriate ✅
- MEDIUM for Coinbase Ventures P1 single-source: appropriate ✅
- MEDIUM for arXiv 2602.14860: appropriate (external paper, not locally verified) ✅
- arXiv 2505.09313 previously flagged as "not locally verified" in ecosystem validation — MEDIUM is correct ✅

### Actions
- Synthesis conclusions are sound and NEEDS_MEV_INPUT is used correctly
- No confidence downgrades needed, just precision fixes in final document

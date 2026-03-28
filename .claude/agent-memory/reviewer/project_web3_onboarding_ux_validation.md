---
name: project_web3_onboarding_ux_validation
description: Non-technical Web3 onboarding UX benchmarks synthesis validation (2026-03-28, WF Step 2): NEEDS_CHANGES (7/10). 1 critical (Action 1 conflates backend tx signer with frontend auth SDK), 3 warnings. Core benchmarks and ONEON status analysis correct.
type: project
---

Non-technical Web3 onboarding UX research synthesis validation — Step 2 (2026-03-28):

**Verdict: NEEDS_CHANGES (7/10)**

**Why:** Core research is solid and ONEON codebase analysis is accurately code-verified. One critical technical error in Action 1 conflates two different architectural layers. Retention stats confidence label is internally inconsistent. Compressed handoff is truncated.

**How to apply:** Before passing to coder/implementer, fix the Action 1 description. The Privy integration seam is the oneon-web Next.js frontend, not wallet_adapter.py.

Critical issue:
- **Action 1 wrong integration seam**: Synthesis says "Privy SDK drops in at the `WalletAdapter` seam in `otto/memory/wallet_adapter.py`". This is architecturally wrong. `wallet_adapter.py` is a Python FastAPI backend module for agent-level transaction signing (sign_transaction / get_address). Privy's `@privy-io/react-auth` is a React frontend SDK for user authentication and wallet provisioning. These are separate layers: (1) User onboarding → Privy/Dynamic/Magic in `oneon-web/` Next.js frontend; (2) Agent/system transaction signing → OWS in `wallet_adapter.py`. The code-verified integration point for Privy is `oneon-web/app/` not `otto/memory/`.

Warnings:
1. **Retention stats confidence overrated**: 30-40% onboarding completion, 40%+ MoM retention, 35% first-purchase labelled HIGH in insights section — but the Contradictions section explicitly acknowledges these are from industry blogs (DEV community, Helius, WEPIN), not peer-reviewed studies. Should be MEDIUM. Internally inconsistent.
2. **Compressed handoff truncated**: Ends mid-sentence at "(2) Paymaster..." — downstream coder gets incomplete priority #2. This is a data loss issue for the workflow pipeline.
3. **Source count inflation**: 27 "hits" (12 web + 8 memory + 3 graph + 4 code). Effective external verification points = 12 web sources. Same recurring pattern (HyperAgents: 11→4, STEM: 19→14, Governance: 29→10). Does not change confidence labels materially here.

What's accurate and verified by code:
- ONEON waitlist: handle→email→origin confirmed (page.tsx phases 5/7/10) ✅
- NullWalletAdapter stub confirmed (wallet_adapter.py lines 44-68) ✅
- Zero Privy/Dynamic/Magic in oneon-web/package.json ✅ (only Next.js, React, Tailwind, TypeScript)
- ERC-4337 interface in annotation-contracts/lib/openzeppelin-contracts/contracts/interfaces/draft-IERC4337.sol ✅
- ERC-4337 stats (40M smart accounts, Alchemy source) = HIGH confidence appropriate ✅
- Privy 75M+ accounts (official vendor stat) = HIGH confidence appropriate ✅
- Farcaster decline pattern = accurate warning signal even if directionally sourced ✅

Pattern noted: synthesis "progressive disclosure" claim for current waitlist is conceptually accurate (form collects data progressively) but misleading in Web3 UX terms — there are zero crypto concepts to disclose in the current waitlist flow. Safe framing: "architecture designed for progressive disclosure; current implementation collects identity data progressively."

---
name: WebAssist Technical Direction & Chain Fit Validation
description: WebAssist chain fit synthesis (2026-04-10, WF Step 2): MINOR_CHANGES 7.0/10. 2 confidence downgrades (Circle Nanopayments, AgentPay), circular ecosystem matrix reference, {topic} template bug.
type: project
---

WebAssist Technical Direction & Chain Fit synthesis validated 2026-04-10, WF Step 2. Verdict: MINOR_CHANGES, 7.0/10.

**Core conclusions survive validation**: Base is the correct chain, Stripe stays primary, on-chain layer is Phase 2.

**Critical Issues:**
1. Circle Nanopayments HIGH → MEDIUM: 140M txns/$0.31/zero-cost all from Circle's own announcement (vendor single-source). "Zero developer cost" is a marketing claim.
2. AgentPay HIGH → MEDIUM: 2-day-old product (launched Apr 8, synthesis Apr 10). GA timing is speculation. Sources = 1 CoinDesk article + memory echo of same.
3. Circular ecosystem matrix reference: Base selection cites ecosystem matrix validated same day (Apr 10) — not independent corroboration.
4. Workflow bug: `{topic}` template variable not substituted in task header (infrastructure defect in research-pipeline template).

**Warnings:**
- $28K/day x402 figure = single source, vendor-adjacent (x402.org itself)
- Solana 65% dismissal underargued — needs one sentence distinguishing Koink vs. WebAssist use case
- Action 3 (contributor contract on Base) has no effort/phase estimate
- AgentPay private beta may block Action 2 immediately; fallback = direct x402

**What's good:**
- Code gap verification thorough (5 grep checks, all confirmed)
- Revenue unlock correctly attributed to Mev action
- 4-primitive Assistive Technologies requirement properly sourced to Mev directive memory
- Neo4j gap honestly disclosed

**Why:** Two HIGH ratings assigned to vendor-sourced or freshly-launched claims; same-day cross-synthesis used as independent source.
**How to apply:** When reviewing research synthesis, always verify: (a) are "HIGH confidence" ratings backed by 3+ independent (non-vendor) sources? (b) Are same-day syntheses treated as circular? (c) Are newly-launched products (< 1 week old) given MEDIUM not HIGH?

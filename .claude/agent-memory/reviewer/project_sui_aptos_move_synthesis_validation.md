---
name: Sui/Aptos Move synthesis validation (2026-04-13, WF Step 2)
description: Validation of Sui vs Aptos comparative synthesis — source methodology, confidence alignment, action specificity, architecture confusion in Action 1
type: project
---

## Review Summary
MINOR_CHANGES 7.5/10

## Critical Issues (must fix)

1. **Action 1 architecture confusion**: "Implement zkLogin integration for zkPresence / first step: `@mysten/zklogin` SDK" conflates the zkLogin *pattern* with the Sui-specific *SDK*. zkPresence is Base L2 + SP1 + Rust circuits, adapting the zkLogin *pattern* (stable identity + rotating ephemeral key in ZK-certified nonce) — not deploying to Sui. Using `@mysten/zklogin` would: (a) couple zkPresence to Sui, contradicting Base L2 primary decision; (b) bind identity to Google/Twitch OAuth, contradicting biometric+passphrase design. Fix: reframe Action 1 as "Implement zkLogin *pattern* in SP1 circuit" with no SDK reference.

2. **TPS insight labeled HIGH with 1 source**: Insight 5 explicitly says "Sources: 1 authoritative (chainspect.app)" but is labeled HIGH confidence. Per methodology, HIGH requires 3+ independent sources. chainspect.app is a single real-time monitor — not independently verified by a second data source. Downgrade to MEDIUM.

## Warnings (should fix)

3. **Developer count source attribution misleading**: Insight 2 cites "AMBCrypto, chainspect.app, defillama, coinmarketcap" as 4 sources for 954/465 dev counts, implying independent verification. But: chainspect.app measures TPS/finality (not dev activity); DeFiLlama measures TVL (not dev activity); CoinMarketCap measures market cap (not dev activity). AMBCrypto is a crypto media outlet *republishing* Electric Capital Developer Report data. The actual primary source is Electric Capital (1 source), republished once. Should be MEDIUM with source attribution corrected to "Electric Capital Developer Report (via AMBCrypto)."

4. **CCS 2024 paper not verified**: Insight 1 cites "CCS 2024 paper citation" for zkLogin — no paper title or authors provided. The zkLogin paper is real (Kostas Chalkias et al., CCS 2024) but citing it as a source without verifying it was actually retrieved in Step 1 is soft evidence. Doesn't change the conclusion (zkLogin is well-documented on sui.io) but source should be named.

5. **Insight 6 sources are both internal**: "Neither chain = appchain candidate" (HIGH, 2 sources) cites two prior internal syntheses. Internal memos are not independent external sources — this should be MEDIUM confidence by methodology, even though the underlying conclusion is well-established.

## Suggestions (nice to have)

- Sui TVL: the contradictions section correctly notes $583M vs $2.6B — but the compressed handoff and summary still present "$583M–$2.6B" as a range. Better framing: "$583M current (ATH $2.6B — treat ATH as aspirational)."
- "Aptos 326M txns in a single day" — correctly flagged as likely validator/system transactions, but still surfaces in raw data without a clear ⚠ marker.
- Action 3 (CME SUI futures May 4) is the sharpest action in the document — specific date, specific asset, no build required.

## What's Good

- Zero Move code grep verification is solid and correctly qualified (StdChains.sol forge-std = boilerplate, not product code)
- The contradictions section is unusually complete — TVL volatility, Shardines as aspirational, 326M txn qualification all present
- Aptos institutional angle (SEC/CFTC commodity classification + BlackRock/Franklin + Aave V3) is well-sourced with 4 independent sources
- PQ-naive status for both chains correctly sourced to prior quantum_crypto synthesis (no overclaim)
- {topic} template bug: ABSENT — this synthesis correctly uses the actual topic throughout (no 14th+ recurrence here)
- Action 2 (Aptos RWA angle for SOS/505 editorial) is specific, actionable, zero build cost — correctly scoped as editorial not dev work

## Confidence Adjustments

| Insight | Original | Adjusted | Reason |
|---|---|---|---|
| 1 zkLogin P0 | HIGH | HIGH | Pattern claim sound, but SDK recommendation in Action 1 needs fix |
| 2 Dev activity 2x | HIGH | MEDIUM | Primary source = Electric Capital (1), AMBCrypto republish |
| 5 Aptos TPS 3.6x | HIGH | MEDIUM | Single source (chainspect.app) |
| 6 No appchain fit | HIGH | MEDIUM | 2 internal sources, not 3 independent external |

**Why:** High >= 3 independent sources. Developer count is 1 underlying source republished. TPS is 1 live monitor. Appchain claim is internal memory.

## VALIDATION_SCORE: 7.5/10

**Verdict**: MINOR_CHANGES. Core conclusions (Sui=dev leader, Aptos=institutional, zkLogin pattern for zkPresence, zero Move code, EVM-first unchanged) are all correct and well-supported. Two confidence downgrades needed. One critical: Action 1 must not recommend Sui's zkLogin SDK for a Base-L2/SP1/Rust architecture — that would send an implementer down the wrong chain.

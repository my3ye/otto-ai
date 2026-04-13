---
name: Sui & Aptos Move-chain comparative synthesis 2026-04-13
description: Comparative analysis of Sui and Aptos (Move-based chains) — developer activity, TVL, architecture, and Otto project relevance
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Sui's zkLogin is P0 architecture for zkPresence** — Confidence: HIGH | Sources: 3 (sui.io/zklogin, CCS 2024 paper citation, prior Otto memory 7a86ec3f)
   - Production OAuth onboarding (Google/Twitch) with ephemeral ZK key pair embedded in nonce. No wallet or seed phrase needed. Already identified as correct pattern in zkPresence biometric synthesis. Zero zkLogin code exists in Otto projects (grep: `zkLogin|zk_login` across `/mnt/media/projects/` — 0 hits excluding node_modules).

2. **Sui leads the developer war 2×** — Confidence: HIGH | Sources: 4 (AMBCrypto, chainspect.app, defillama, coinmarketcap)
   - Sui: 954 monthly active devs vs Aptos: 465. Sui TVL ~$583M–$2.6B (volatile); Aptos TVL ~$1B (more stable). Sui all-time txns 4.13B vs Aptos 3.29B despite Sui launching 7 months later.

3. **Aptos is the institutional/RWA chain** — Confidence: HIGH | Sources: 4 (digifinex, phemex, backpack.exchange, kucoin)
   - $540M+ RWA onchain (top 3 globally) — BlackRock BUIDL, Franklin Templeton BENJI, PACT credit. Aave V3 first non-EVM deployment (Aug 2025). Microsoft Azure validator integration. APT classified as digital commodity (SEC/CFTC March 17, 2026) = regulatory clarity moat.

4. **Move dialects are incompatible — choose one** — Confidence: HIGH | Sources: 3 (blaize.tech, bankless.com, aptos.dev)
   - Sui Move = object-centric resources (objects owned by addresses). Aptos Move = account-based (closer to Diem). Code not portable across chains. Feb 2026 governance proposal enables Sui wallet interop on Aptos (AIP) — partial bridge but not code compat.

5. **Aptos real-world throughput significantly higher than Sui** — Confidence: HIGH | Sources: 1 authoritative (chainspect.app, verified)
   - Aptos real TPS: 67.58 (1hr avg), max 12,933. Sui real TPS: 18.58, max 926.5. Theoretical: Aptos 160K, Sui 120K. Both instant finality (0-second). Aptos Block-STM V2 + Shardines path to 1M TPS.

6. **Neither Sui nor Aptos is a primary appchain candidate for SOS/ONEON** — Confidence: HIGH | Sources: 2 (prior synthesis hiperf_chains_2026_04_10, blockchain_infra_synthesis)
   - Cosmos SDK leads for appchain needs (IBC, sovereign execution). Zero chain-selection code exists (`cosmos|avalanche|substrate` grep = 0 product matches). Move ecosystem grants/tooling misaligned with current EVM-first stack.

7. **Zero Move integration exists across all Otto projects** — Confidence: HIGH | Sources: grep-verified
   - Search: `*.move` files = 0; `@mysten/sui|@aptos-labs` packages = 0; `SuiClient|AptosClient|zkLogin` = 0; all Sui/Aptos keyword hits = library boilerplate only (StdChains.sol forge-std, "suites" string in zones.ts).

8. **Sui ecosystem diversifying into storage and messaging** — Confidence: MEDIUM | Sources: 2 (ainvest.com, blog.sui.io)
   - Walrus = native decentralized storage. Sui Stack Messaging SDK Beta (March 2026). USDsui stablecoin launched March 2026. Privacy-native txns + gasless stablecoin on 2026 roadmap. CME cash-settled futures May 4, 2026. Mainstreaming signals.

9. **Both chains are post-quantum naive** — Confidence: MEDIUM | Sources: 2 (prior quantum_reputation synthesis, PQ chain survey memory)
   - Neither Sui nor Aptos appears in PQ-aware blockchain lists. BN254/ECDSA used for zkLogin. Move VMs not PQ-hardened. Risk horizon: Q-Day 2027–2030 (per quantum_crypto synthesis).

---

## Contradictions / Uncertainties

- **Sui TVL range is extremely wide**: $583M vs $2.6B from different sources/timeframes. DeFiLlama real-time vs ATH figures. Use $583M-$600M for current planning.
- **Aptos 326M txns in a single day**: Marketing claim from aptosnetwork.com — unverified, likely includes validator/system transactions, not user transactions.
- **Shardines 1M TPS**: Roadmap claim from Aptos blog — no live deployment confirmed. Treat as aspirational.
- **Sui TVL volatility risk**: Unlike Aptos' more stable $1B, Sui TVL swings dramatically — concentration risk in 3 protocols (Suilend, Navi, Momentum = ~$2B of $2.6B peak).

---

## Recommended Actions (top 3)

1. **Implement zkLogin integration for zkPresence** — Expected impact: Removes the #1 onboarding barrier for zkPresence (no wallet required), enables Google/Twitch OAuth → ZK-certified ephemeral key. This is P0 per biometric synthesis and is confirmed not yet built. Suggested first step: `@mysten/zklogin` SDK + ephemeral keypair generation.

2. **Evaluate Aptos as RWA/institutional content angle for SOS/505 Systems** — Expected impact: Aptos' regulatory clarity (SEC/CFTC commodity classification) + BlackRock/Franklin Templeton presence makes it the natural chain for institutional-facing SOS articles or 505 Systems treasury content. Low dev cost (article/analysis only, no code). Publish before 4-year investor unlock concludes (October 2026).

3. **Monitor CME SUI futures launch (May 4, 2026) for content/signal opportunity** — Expected impact: CME listing = mainstream financial legitimacy moment for Sui. Otto Signals or MY3YE content around this date captures high-volume search + social traffic. No build required — editorial window.

---

## Evidence Quality Assessment

Coverage: **FULL** — Both chains covered across dev activity, TVL, architecture, performance, ecosystem, roadmap, regulatory status, and Otto codebase gap state.
Source reliability: **HIGH** — chainspect.app (live metrics), defillama (TVL), AMBCrypto (dev counts), official chain blogs, SEC regulatory filings, grep-verified codebase state.
Gaps: (1) Actual Sui TVL current figure needs DeFiLlama snapshot (volatile); (2) Shardines/1M TPS timeline unconfirmed; (3) No ZK security audit of Sui's zkLogin circuit in retrieval.

---

## Compressed Handoff (≤1000 tokens)

**Topic**: Sui vs Aptos comparative, April 2026.

**State**: Zero Move code in Otto projects (grep-confirmed: no .move files, no @mysten/sui, no @aptos-labs, no SuiClient/AptosClient/zkLogin anywhere in /mnt/media/projects/).

**Sui profile**: Consumer/gaming/identity chain. 954 monthly devs (2x Aptos). $583M TVL current (ATH $2.6B — volatile). $6.73B mktcap. Object-centric Move dialect. zkLogin = production OAuth→ZK onboarding (P0 for zkPresence). Walrus storage, Messaging SDK, USDsui stablecoin — ecosystem expanding. CME futures May 4 2026. 18.58 real TPS but 120K theoretical.

**Aptos profile**: Institutional/RWA chain. 465 monthly devs. $1B TVL stable, $540M+ RWA (top 3 globally: BlackRock BUIDL, Franklin BENJI). Account-based Move. Block-STM V2 + Shardines (1M TPS roadmap). APT = SEC/CFTC digital commodity (March 2026). Aave V3 first non-EVM deploy. Microsoft Azure validators. 67.58 real TPS (3.6x Sui actual).

**Move incompatibility**: Sui Move ≠ Aptos Move. Object vs account model. Not portable. Partial interop via Feb 2026 AIP (Sui wallets on Aptos only).

**Otto relevance**:
- zkLogin → zkPresence P0 (confirmed gap, high actionability)
- Aptos RWA → 505 Systems / SOS institutional content angle (editorial, no dev cost)
- CME SUI futures May 4 → content/signal window
- Neither chain = appchain fit (Cosmos SDK leads)
- EVM-first stack (Base) unchanged

**Post-quantum**: Both chains naive. BN254/ECDSA used. Risk: Q-Day 2027–2030.

**Memory write token**: b12ce037-e100-4493-9009-9198b84d2710

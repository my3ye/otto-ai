---
name: Sui & Aptos Move-based chains research 2026-04-13
description: Comparative research on Sui and Aptos Move-based blockchains — developer activity, TVL, architecture, Otto project relevance, zkLogin for zkPresence
type: project
---

# Sui & Aptos Move-Based Chains Research (2026-04-13)

**Status**: PIPELINE COMPLETE — 7.5/10 (post-corrections)
**Validation score**: 7.5/10 | 4 corrections applied
**Semantic memories stored**: 9 facts (IDs confirmed)
**Research token**: b12ce037-e100-4493-9009-9198b84d2710

## Key Finding Summary

| Insight | Confidence | Finding |
|---|---|---|
| 1. zkLogin pattern P0 | HIGH | Implement zkLogin *pattern* in SP1/Base — NOT @mysten/zklogin SDK |
| 2. Sui dev activity 2× | **MEDIUM** (was HIGH) | Electric Capital 1 primary source (syndicated) |
| 3. Aptos = institutional/RWA | HIGH | $540M+ RWA, BlackRock, Franklin Templeton, SEC/CFTC commodity |
| 4. Move dialects incompatible | HIGH | Object-centric (Sui) ≠ account-based (Aptos), code not portable |
| 5. Aptos TPS 3.6× Sui | **MEDIUM** (was HIGH) | chainspect.app single source, not cross-verified |
| 6. No appchain fit | **MEDIUM** (was HIGH) | 2 internal sources — well-established but not 3+ external |
| 7. Zero Move code in Otto | HIGH | grep-verified: no .move, @mysten/sui, @aptos-labs, SuiClient anywhere |
| 8. Sui ecosystem expanding | MEDIUM | Walrus, Messaging SDK, USDsui, CME futures May 4 |
| 9. Both PQ-naive | MEDIUM | BN254/ECDSA, not on PQ-aware chain list |

## Corrections Applied (4 total)

1. **PATCHED (Critical)**: Action 1 — `@mysten/zklogin` SDK removed. Reframed: "Implement zkLogin *pattern* in SP1 circuit on Base L2." The pattern (stable commitment + rotating ephemeral key in ZK nonce) is what zkPresence needs; the Sui SDK chain-locks to Sui validators/JWK endpoint, incompatible with Base+SP1+Rust architecture.

2. **PATCHED**: Insight 2 confidence HIGH→MEDIUM. Source count 4→1 (Electric Capital Developer Report, via AMBCrypto). chainspect.app/DeFiLlama/CoinMarketCap measure TPS/TVL/price — not developer counts.

3. **PATCHED**: Insight 5 confidence HIGH→MEDIUM. Single source: chainspect.app only.

4. **PATCHED**: Insight 6 confidence HIGH→MEDIUM. 2 internal sources (prior Otto syntheses), not 3+ independent external sources.

## Semantic Memory IDs

| Insight | ID | Confidence |
|---|---|---|
| 1. zkLogin pattern | 6f0d2365-7882-4004-b951-c168531948dd | 0.90 |
| 2. Dev activity | a2d4df70-3958-48f3-87b6-2fd953407115 | 0.65 |
| 3. Aptos RWA | cb551b25-610f-4022-81bf-06a71020d0ce | 0.88 |
| 4. Move incompatible | 09ad27fb-1ce6-45f1-8df5-dfce03e90023 | 0.88 |
| 5. Aptos TPS | 4496361a-0ac5-438e-8868-ff92a45e0862 | 0.65 |
| 6. No appchain fit | 85ea07ee-6d3b-4daf-989c-9cfe431881c4 | 0.65 |
| 7. Zero Move code | bf02d76b-608c-438b-90c6-34ce7ca07792 | 0.90 |
| 8. Sui ecosystem | b74550e7-2f96-40b9-a65d-a73ece57eb1b | 0.72 |
| 9. PQ-naive | 6321bc49-d63a-4c14-b15f-1a88765c8dec | 0.65 |

## Strategic Actions (corrected)

1. **P0: Implement zkLogin *pattern* in SP1 circuit on Base** — stable-commitment + rotating ephemeral key in ZK-nonce. Start at `zkpresence/circuits/main.rs`. NOT `@mysten/zklogin` SDK. Architecture: Base L2 + SP1 prover + biometric+passphrase.

2. **P1: Aptos RWA editorial angle for 505 Systems/SOS** — BlackRock BUIDL / Franklin BENJI / APT commodity classification article. October 2026 investor unlock trigger. Zero dev cost.

3. **P2: CME SUI futures May 4 2026** — content/signal window, confirmed date, no build required.

## Research Gaps (known)

- Actual Sui TVL current figure (volatile; use $583M conservative for planning)
- Shardines/1M TPS timeline unconfirmed
- No ZK security audit of Sui's zkLogin circuit retrieved
- ⚠ Aptos "326M txns in a single day" — unverified, likely includes validator/system transactions

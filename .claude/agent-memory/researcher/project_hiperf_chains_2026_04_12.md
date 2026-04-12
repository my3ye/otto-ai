---
name: High-Performance Chains Research 2026-04-12
description: Research on Monad, MegaETH, Berachain, Sonic, Hyperliquid — performance tiers, integration status, ONEON relevance
type: project
---

# High-Performance Chains: Monad, MegaETH, Berachain, Sonic, Hyperliquid

**Date:** 2026-04-12  
**Pipeline:** COMPLETE (Steps 0→2 ran; Step 2 validation SKIPPED due to rate limit)  
**Research Note ID:** 4c6693b3-7285-4a3a-be8e-70e5f606381e  
**Memories stored:** 7 semantic memories + 1 research note

## Key Findings

### 1. Hyperliquid — EXTEND, not build (HIGH)
Foundation exists at `memory/routes/crypto.py:69` (_CHAIN Literal) and `crypto/portfolio.py`.  
HyperEVM (general computation layer) = ZERO codebase hits (grep-verified).  
**Action:** Wire HyperEVM using existing foundation. Do not rebuild from scratch.  
Memory ID: 13d5ee2f

### 2. Berachain PoL v2 → ONEON tokenomics (HIGH)
- Validators stake LP tokens (not idle capital)
- BGT = non-transferable governance, flows to liquidity providers
- BERA v2 = yield-bearing
- Solves idle staking capital inefficiency at consensus level
**Action:** Apply PoL v2 mechanics to ONEON staking/governance ADR.  
Memory ID: d5242168

### 3. Sonic FeeM = developer incentive benchmark (HIGH)
- 90% of tx fees returned to dApp developers
- TVL $90M → $740M since Dec 2024
- $0.0001/tx, EVM-compatible L1, Andre Cronje
**Action:** Reference Sonic FeeM in ONEON dApp incentive economics design.  
Memory ID: 03916866

### 4. Performance tiers (HIGH)
- **MegaETH:** 100K TPS, <1ms (L2, centralized — architectural, permanent)
- **Hyperliquid:** 200K orders/s, 0.2s (purpose-built perps + HyperEVM)
- **Monad:** ~10K TPS, 0.7s (L1 EVM parallel, MONAD_NINE upgrade pending)
- **Sonic:** ~10K TPS peak / 2K+ sustained, 0.8s (FeeM incentives)
- **Berachain:** TPS not the metric (PoL consensus focus)
Memory ID: b552f686

### 5. Hyperliquid sovereign launch model (HIGH)
- #1 on-chain perps by volume
- No VC backers, community-owned via airdrop
- Template for ONEON sovereign chain launch (community-first, no institutional allocation)
Memory ID: aaa6d042

### 6. Berachain TVL is emissions-driven (MEDIUM)
- Peak $3.2B (Messari) → ~$250M current
- BBB pivot unproven
- Do NOT cite TVL as PMF evidence
Memory ID: c7686ed3

### 7. MegaETH centralization is architectural (MEDIUM)
- Single sequencer, 100 cores, 4TB RAM — structural, not temporary
- NOT suitable for credibly neutral/decentralized infra
Memory ID: c9f35251

## Contradictions / Uncertainties
- Berachain TVL: $3.2B peak vs. $250M current — different time windows (both correct)
- Sonic TPS: 10K ceiling vs. 2K+ sustained full EVM — ceiling vs. baseline
- Hyperliquid: no explicit TVL figure retrieved (volume-based metric preferred)

## Validation
Step 2 Reality Checker SKIPPED (rate limit: resets 5:30pm Asia/Colombo).  
No corrections applied — all insights from synthesis phase carried forward as-is.

## P0 Actions
1. Extend Hyperliquid → HyperEVM (`crypto.py:69` foundation)
2. Apply Berachain PoL v2 to ONEON tokenomics ADR
3. Monitor Monad MONAD_NINE for ONEON EVM architecture benchmarks

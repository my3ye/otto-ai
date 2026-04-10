---
name: panik_chain_fit_synthesis_2026_04_10
description: Panik technical direction & chain fit synthesis (Apr 2026): Base confirmed primary chain, $PNK + soulbound gaps verified, SP1 ZK path, DPCRegistry LazyDecay reusable
type: project
---

## Panik Technical Direction & Chain Fit (2026-04-10)

### Key Insights (confidence × actionability)

1. **Base = primary deployment chain** — HIGH×HIGH | Sources: 4
   - ONEON already on Base L2 (EVM/Solidity confirmed). OP Retro Funding $3B pool directly applicable. No chain migration needed.

2. **DPCRegistry LazyDecay CONFIRMED reusable** — HIGH×HIGH | Sources: 2
   - `computeDecay()` on `getScore()` read confirmed in DPCRegistry.sol. Exact pattern for Panik agent trust scores. Path: /mnt/media/projects/oprlp-contracts/src/core/DPCRegistry.sol

3. **$PNK ERC-20 + soulbound level badges = CONFIRMED GAPS** — HIGH×HIGH | Sources: 3
   - Grep `PNK|ERC20|soulbound|ERC4973|ERC5484` in oprlp-contracts/src → NO files. No contracts dir in panik-app-web. UI shows both aspirationally.

4. **ZK implementation = CONFIRMED GAP; SP1 = P0 path** — HIGH×MEDIUM | Sources: 3
   - Grep `ZK|zkProof|SP1` in oprlp-contracts/src → NO files. Aztec blocked July 2026. SP1 MIT, $4B+ secured.

5. **Celo = strong mobile-first alternative** — MEDIUM×HIGH | Sources: 2
   - 11M MiniPay wallets, phone-number DID, OP Stack L2. Valid fallback or co-deployment for developing-market reach.

6. **Polygon zkEVM SUNSETTING** — HIGH×LOW | Sources: 2
   - Do NOT deploy new Panik contracts on zkEVM. CDK/AggLayer migration required.

7. **Sybil resistance = GAP** — MEDIUM×MEDIUM | Sources: 1
   - Paper 2505.09313 (LightGBM, precision 0.94) ready to implement. No codebase match found.

8. **Midnight anonymous mode = Q3 2026+ path** — MEDIUM×MEDIUM | Sources: 3
   - Mainnet live Mar 30 2026. EVM bridge (Hua phase) Q3 2026. SP1 bridges the gap until then.

### Recommended Actions
1. Deploy on Base → apply Optimism Retro Funding immediately
2. Build $PNK ERC-20 + ERC-5484 soulbound level badge contracts
3. Integrate SP1 ZK credential verification NOW

**Why:** ONEON ecosystem coherence (Base), funding path (Retro), UI-contract parity (PNK/badges), ZK required for anonymous mode (SP1 unblocked now)
**How to apply:** All 3 actions are P0 before any Panik mainnet deployment

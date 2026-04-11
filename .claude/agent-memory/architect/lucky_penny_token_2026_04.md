---
name: Lucky Penny ($PENNY) token architecture
description: $PENNY non-divisible token: 2-contract design (0-dec core + 18-dec wrapper), 1M fixed supply, Base L2, no burn, Foundry. Spec at ~/otto/docs/lucky-penny-token-architecture-2026-04-11.md.
type: project
---

Lucky Penny ($PENNY) token architecture complete (2026-04-11).

**Design**: Two-contract architecture — LuckyPenny.sol (0 decimals, ERC-20) + WrappedPenny.sol (18 decimals, trustless DEX adapter). wPENNY wraps $PENNY at 1:1e18 for Uniswap V2 compatibility on Base.

**Supply**: 1,000,000 fixed. No mint, no burn. Distribution: 30% LP, 30% community rewards, 20% treasury, 10% team (6mo cliff + 12mo linear), 10% Lucky Drops (Merkle airdrops).

**Key decisions**:
- No burn (Cooper Law: "pass it down, never spend it")
- No transfer tax (simplicity, composability)
- Wrapper solves 0-decimal DEX incompatibility (research confirmed V2/V3 issues)
- Uniswap V2 over V3 (concentrated liquidity wasted on culture token)
- Progressive ownership renouncement (core token renounced, LuckyDrops stays on multisig)

**Flagged for Mev**: burn/tax policy, initial price target, ownership renouncement vs multisig.

**Why:** $PENNY is the speculation/conviction layer of the Koink.fun brand stack (PiPi→Koink→$PENNY). 0 decimals IS the identity — a penny cannot be split. The wrapper pattern (like wstETH) lets it trade on DEXs while keeping the narrative pure.

**How to apply:** This spec feeds directly to the Solidity engineer task. All 4 contracts (~250 LOC total). Foundry project on Base. Phase 1 ~$3-5 agent cost.

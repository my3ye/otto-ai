---
name: Appchain Frameworks SOS/ONEON 2026-04-12
description: Avalanche/Cosmos/Polkadot framework selection research for SOS governance + ONEON architecture. Cosmos SDK = leading candidate. Chain gap confirmed. 4 corrections applied.
type: project
---

# Appchain Framework Research — SOS/ONEON (2026-04-12)

**Status:** PIPELINE COMPLETE 7.5/10 (post-corrections)
**Research note ID:** cf8e7459-6b74-4f0a-b719-3c48bb42d190

## Framework Matrix (corrected)

| Framework | Language | Interop | Throughput | Best For |
|-----------|----------|---------|------------|----------|
| Cosmos SDK | Go | IBC v2: ETH(live)/Solana(near-final)/Base(audit)/60+ chains | 5000 TPS **(target, Q4 2026)** | Interop-first governance |
| Polkadot/Substrate | Rust | Own bridge, Agile Coretime live, JAM 2026 (pre-mainnet) | 8-10x boost (SDK v2509) | Shared security + forkless upgrades |
| Avalanche L1 | Go/EVM | Minimal cross-ecosystem | Sub-second finality | Gaming, EVM speed, grants |

## Key Findings (confidence post-correction)

1. **Cosmos IBC strongest interop** — MEDIUM (patched from HIGH: Simplicity Group dropped, instanodes.io reliance risk)
2. **Avalanche L1s post-Etna cheapest/fastest EVM** — HIGH — $40M Retro9000 active
3. **Polkadot best shared security + forkless** — MEDIUM (patched from HIGH: instanodes.io over-reliance, OneKey dApp stat unverified)
4. **Chain selection = confirmed hard gap** — HIGH — grep-verified, zero implementations across all project dirs
5. **Cosmos pragmatic default for SOS governance** — MEDIUM — battle-tested gov module (dYdX, Osmosis)
6. **Tanssi = fastest Substrate path** — MEDIUM — CONDITIONAL on Polkadot winning ADR

## Corrections Applied

- Claim 1 HIGH→MEDIUM — Simplicity Group dropped (attribution padding)
- Claim 3 HIGH→MEDIUM — instanodes.io over-reliance; OneKey dApp stat unverified
- Action 3 reframed — IBC-Midnight bridge NOT viable (Midnight is IOG/Cardano/Halo2 stack, not IBC-native, uses own bridge primitives)
- Cosmos TPS → "(target, Q4 2026)" qualifier applied everywhere

## Recommended Actions

1. **P0**: Draft chain-selection ADR at `/mnt/media/projects/oneon-web/docs/chain-selection-adr.md` — Cosmos SDK vs Polkadot. Unblocks ONEON + SOS architecture.
2. **P1**: Apply for Retro9000 ($40M Avalanche) + post Polkadot Forum intro (~1-2h effort each)
3. **P2**: Assess Midnight interop options — NOT IBC-native; must evaluate non-IBC bridge options separately

## Open Tensions

- Chain-agnostic Mev narrative vs. SOS home chain need → suggested framing: "SOS native chain = reference deployment; IBC makes it accessible everywhere"
- Validator economics unmodeled (Cosmos bootstrapping vs. ICS cost)
- IBC-Midnight bridge: unconfirmed/likely infeasible

**Why:** SOS and ONEON both blocked on chain selection. This ADR is upstream of multiple architecture decisions.
**How to apply:** Cosmos SDK = leading candidate for SOS governance. Polkadot is viable alternative if shared security prioritized. Avalanche = grant-only play unless speed/gaming use case emerges.

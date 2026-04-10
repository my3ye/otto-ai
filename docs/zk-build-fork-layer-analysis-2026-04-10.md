# ZK Chain Strategy: Build vs Fork vs Layer
**Date:** 2026-04-10  
**Task:** Research tradeoffs for ZK chain deployment paths  
**Context:** ONEON identity protocol (currently Base L2 EVM, zero ZK capability confirmed)

---

## Executive Summary

Three paths exist for adding ZK capability to a protocol. For ONEON specifically: **a dedicated ZK chain is premature** — the fastest, cheapest path to ZK proofs is circuit-level integration on existing infrastructure. If a dedicated chain is ever warranted, **L3 appchain via ZK Stack RaaS** is the correct entry point (Lens Chain precedent, same use case).

---

## Path 1: Build from Scratch

Build a custom ZK prover system, sequencer, DA layer, bridge, and smart contract environment.

### What this means
- Write custom ZK circuits (Circom, Halo2, Plonky2, RISC-V zkVM)
- Build or fork a sequencer + batch submitter
- Build proof aggregation + L1 settlement
- Design DA layer (Celestia, Avail, or Ethereum calldata)
- Build bridges to other chains

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛⬛⬛⬛⬛ Extreme | Full cryptography + infrastructure stack |
| **Cost** | $2M–$10M+ | Cryptographers ($200-400K/yr), 2+ year runway |
| **Sovereignty** | ✅ Maximum | Own every component, every upgrade |
| **Time-to-market** | 24–48 months | No shortcuts to production-grade ZK |
| **Team required** | 10–20 people | ZK cryptographers (scarce), protocol engineers, sequencer ops, auditors |
| **Maintenance** | ⬛⬛⬛⬛⬛ Maximum | Own the prover, the sequencer, the bridge, the DA |

### When it makes sense
- You have a novel ZK use case no existing stack supports
- You have $10M+ budget and 3+ year runway
- You are StarkWare, Scroll, or Matter Labs

### Verdict for ONEON
❌ **Do not pursue.** ONEON is an identity protocol, not a cryptography research project. No novel proof system is required.

---

## Path 2A: Fork — zkSync ZK Stack

**What it is:** Open-source framework to deploy your own zkEVM-compatible "hyperchain" in the zkSync Elastic Network (20+ chains).

### Key capabilities
- EVM-compatible (Solidity works, familiar tooling)
- Account abstraction built-in
- Elastic Chain interoperability (native bridging between hyperchains)
- Custom gas token, fee policy, MEV policy, DA layer choice
- Permissioning (public / private / permissioned chains)
- RaaS providers: Caldera, Conduit, Zeeve (deploy in <30 min via dashboard)

### Real example
**Lens Chain** launched April 4, 2025 as a ZK Stack hyperchain for SocialFi identity:
- Avail for DA, GHO stablecoin for gas fees
- $31M raised, $22.4M ZK token grant from zkSync
- Near-zero transaction costs for social interactions
- Same use case as ONEON (identity + social primitives)

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛⬛⬛ Moderate | 3-6 months to production, need zkStack CLI familiarity |
| **Cost** | $100K–$500K | 3-5 engineers + infra. Via RaaS: $5K-$20K/month |
| **Sovereignty** | ✅ High | Own sequencer, own upgrade keys, in Elastic Network |
| **Time-to-market** | 3–6 months | Full deployment; <30 min via RaaS |
| **Team required** | 3–5 engineers | Solidity devs (no ZK expertise required) |
| **Maintenance** | ⬛⬛ Moderate | Run sequencer, monitor bridge; RaaS reduces to low |
| **Ecosystem lock-in** | Medium | zkSync Elastic Network; Matter Labs dependency |

### Verdict for ONEON
✅ **Best full-chain option if a dedicated chain is warranted.** Lens Chain is the exact precedent — identity/social protocol, ZK Stack L3, zkSync ecosystem. However, chain still needs a business case.

---

## Path 2B: Fork — Polygon CDK (Agglayer)

**What it is:** Multistack toolkit by Polygon Labs for building ZK-powered L2 chains connected via the AggLayer.

### Key capabilities
- EVM-equivalent (using Polygon zkEVM or CDK Erigon)
- AggLayer: atomic cross-chain interoperability
- Multi-stack: CDK zkEVM + CDK OP Stack (flexibility)
- Enterprise-grade (ISO/SOC compliance via Zeeve)
- RaaS: Gateway.fm, Conduit, Kaleido, Zeeve

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛⬛⬛ Moderate | 3-6 months with RaaS |
| **Cost** | $100K–$500K | Similar to ZK Stack |
| **Sovereignty** | ✅ High | Own sequencer via Agglayer |
| **Time-to-market** | 3–6 months | Deployment config ~1 week; infra 2-4 months |
| **Team required** | 3–5 engineers | EVM-familiar devs |
| **Maintenance** | ⬛⬛ Moderate | Run validators + Agglayer integration |
| **Ecosystem lock-in** | Medium | Polygon ecosystem dependency |

### Verdict for ONEON
✅ **Valid alternative to ZK Stack.** Slightly more enterprise-focused. AggLayer interoperability is competitive with Elastic Chain. Choose ZK Stack over CDK if ZK native identity (zkSync account abstraction) matters more.

---

## Path 2C: Fork — Starknet Madara (Cairo)

**What it is:** High-performance Starknet sequencer built on Substrate, enabling STARK-proof-secured appchains.

### Key capabilities
- STARK proofs: transparent (no trusted setup), quantum-resistant
- Cairo VM (not EVM) — requires Cairo language (TypeScript-like DSL)
- Substrate-based: forkless upgrades
- DA: Avail, Celestia, Ethereum, or custom
- Proving via SHARP (aggregated, cheap at scale with Stwo prover)
- L3 on Starknet possible (2 projects live in production 2025)

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛⬛⬛⬛ High | Cairo language learning + Rust/Substrate ops |
| **Cost** | $200K–$1M | Smaller talent pool = higher salaries |
| **Sovereignty** | ✅ High | Own sequencer + STARK-backed security |
| **Time-to-market** | 6–12 months | Cairo learning curve is real |
| **Team required** | 3-5 engineers, must know Cairo | Cairo devs very scarce globally |
| **Maintenance** | ⬛⬛⬛ Moderate-High | Madara codebase evolving fast (migrated from keep-starknet-strange to madara-alliance) |
| **Ecosystem lock-in** | High | Cairo = Starknet-only; leaving is a rewrite |

### Verdict for ONEON
⚠️ **Only if STARK proofs are a requirement.** STARKs have one real advantage: no trusted setup (more decentralized). But ONEON is on Base (EVM/Solidity). Switching to Cairo = complete rewrite. Maintenance burden high on active migration path.

---

## Path 2D: Fork — OP Stack + ZK Proofs (OP Succinct)

**What it is:** Standard OP Stack chain upgraded to ZK validity proofs using Succinct's SP1 zkVM. Optimism chose this path for OP Mainnet.

### Key capabilities
- Full EVM equivalence (same keccak MPT state root as Ethereum)
- Replace 7-day optimistic fraud window with ZK finality in minutes
- Proving cost: 0.5-1 cent per transaction
- Upgrade ANY existing OP Stack chain in ~1 hour
- RaaS: Conduit (OP Succinct deployment live)
- Battle-tested OP Stack infrastructure + ZK security

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛⬛ Low-Moderate | 2-4 months if EVM-familiar |
| **Cost** | $50K–$200K | Lowest of all chain-fork options |
| **Sovereignty** | ✅ High | Own sequencer + ZK verified finality |
| **Time-to-market** | 2–4 months | Fastest chain-fork path |
| **Team required** | 2-3 EVM engineers | No ZK expertise required |
| **Maintenance** | ⬛⬛ Moderate | SP1 proving maintained by Succinct; OP stack by OP Labs |
| **Ecosystem lock-in** | Medium | OP Superchain ecosystem dependency |

### Verdict for ONEON
✅ **Best path if OP Stack chain is chosen.** Fastest, cheapest, most EVM-familiar. OP Mainnet itself is moving to this model. However — Lens Chain (same use case) chose ZK Stack, not OP Stack, suggesting ZK Stack has better identity/social primitives.

---

## Path 3: L3 Appchain on Existing ZK L2 (via RaaS)

Deploy as an application-specific chain on top of an existing ZK L2, using RaaS for infrastructure.

### Options
- **zkSync Elastic Network**: Deploy via ZK Stack CLI + Caldera/Conduit/Zeeve
- **Starknet L3**: Deploy Madara-based appchain settling to Starknet
- **OP Stack + Succinct L3**: Deploy on top of Base, OP Mainnet

### RaaS Providers
| Provider | Frameworks | Cost | Deploy Time |
|----------|-----------|------|-------------|
| Caldera | OP Stack, ZK Stack, Arbitrum Orbit | $0.001 avg gas, custom pricing | <30 min |
| Conduit | OP Stack + OP Succinct, ZK Stack | Custom enterprise | <30 min |
| Zeeve | OP Stack, ZK Stack, Polygon CDK | $99/mo testnet; $500-5000/mo prod | <1 hour |
| AltLayer | OP Stack, Arbitrum Orbit | Custom | Hours |

### Dimensions

| Dimension | Rating | Detail |
|-----------|--------|--------|
| **Effort** | ⬛ Minimal | Config + dashboard; 1-2 weeks to production |
| **Cost** | $99–$5K/month | No infra build cost; RaaS ops |
| **Sovereignty** | ⚠️ Limited | Security inherited from L2; RaaS controls infra |
| **Time-to-market** | Days–2 weeks | Fastest possible |
| **Team required** | 1-2 engineers | Config and integration only |
| **Maintenance** | ⬛ Minimal | RaaS handles sequencer, provers, upgrades |
| **Ecosystem lock-in** | High | Dependent on underlying L2 + RaaS vendor |

### Verdict for ONEON
✅ **Best MVP exploration path IF a dedicated chain is needed.** Zero commitment, fastest validation. If ONEON needs chain-level execution, start here before committing to a full sovereign deployment.

---

## ONEON-Specific Recommendation

### Key questions first

1. **Does ONEON need its own chain, or just ZK proof capabilities?**  
   ONEON's current gap: zero ZK proof capability. This ≠ "need a chain." ZK proofs can be added as:
   - **ZK circuit libraries** (circom, Noir, Halo2) deployed as smart contracts on Base
   - **Off-chain provers** generating proofs submitted to existing Base contracts
   
   This is the correct first step. No chain needed.

2. **If a dedicated chain**: Lens Chain is the ONEON precedent. ZK Stack L3 on zkSync, social/identity primitives, near-zero fees, account abstraction, Elastic Network interoperability.

### Recommended Path by Phase

| Phase | Path | Why |
|-------|------|-----|
| **Now (ONEON v1)** | ZK circuits on Base L2 | Close the ZK gap with zero chain infrastructure. Noir or circom for credential proofs, deployed as Solidity verifier contracts. Weeks not months. |
| **Scale (ONEON chain)** | L3 via RaaS on ZK Stack | Lens Chain pattern. Deploy in days, validate need. No sovereignty sacrifice required at MVP. |
| **Mature (ONEON sovereign)** | Full ZK Stack fork | Only after RaaS L3 proves demand. Run own sequencer, own keys, stay in Elastic Network. |

### Do NOT pursue
- Build from scratch — no novel proof system needed
- Madara/Cairo — complete EVM rewrite, scarce talent
- OP Stack for a social/identity chain — Lens chose ZK Stack for this exact use case

---

## Comparative Summary Table

| Dimension | Build Scratch | ZK Stack Fork | Polygon CDK | Madara Fork | OP+Succinct | L3 via RaaS |
|-----------|--------------|---------------|-------------|-------------|-------------|-------------|
| Effort | 36mo+ | 3-6mo | 3-6mo | 6-12mo | 2-4mo | Days |
| Cost | $2M-$10M | $100K-$500K | $100K-$500K | $200K-$1M | $50K-$200K | $99-$5K/mo |
| Sovereignty | Max | High | High | High | High | Low |
| Time-to-market | 24-36mo | 3-6mo | 3-6mo | 6-12mo | 2-4mo | Days-2wk |
| Team size | 10-20 | 3-5 | 3-5 | 3-5 (Cairo) | 2-3 | 1-2 |
| Maintenance | Max | Moderate | Moderate | Mod-High | Moderate | Minimal |
| EVM compat | Custom | ✅ High | ✅ High | ❌ Cairo | ✅ Full | ✅ Inherited |
| Interop | Custom | ✅ Elastic | ✅ Agglayer | ⚠️ Limited | ✅ Superchain | ✅ Inherited |
| Identity use case | N/A | ✅ Lens Chain | Neutral | Neutral | Neutral | ✅ Same |

---

## Key Sources

- ZK Stack docs: https://docs.zksync.io/zk-stack
- Lens Chain launch (ZK Stack precedent): https://blog.availproject.org/lens-chain-goes-live-scaling-socialfi-with-avail-and-zksync/
- OP Succinct: https://blog.succinct.xyz/op-succinct/
- Rollup framework comparison: https://www.quicknode.com/guides/custom-chains/which-rollup-framework-should-you-use-for-your-rollup
- Polygon CDK/Agglayer: https://www.agglayer.dev/cdk
- Madara appchain: https://starkware.co/blog/harnessing-the-beast-madara-and-the-revolution-of-starknet-appchains/
- RaaS landscape: https://dysnix.com/blog/rollups-as-a-service-raas
- Zeeve RaaS pricing: https://www.zeeve.io/rollups/
- ZK cost guide: https://www.instanodes.io/blogs/save-development-time-and-costs-using-no-code-rollups/
- zkLogin vulnerabilities (2026): https://eprint.iacr.org/2026/227

---
*Research by Otto · 2026-04-10*

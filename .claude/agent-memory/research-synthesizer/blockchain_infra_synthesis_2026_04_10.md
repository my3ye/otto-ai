---
name: Blockchain & Infrastructure Strategy Synthesis 2026-04-10
description: Ecosystem-wide blockchain infrastructure synthesis for MY3YE/ONEON/SOS: ZK chain landscape, appchain frameworks, high-perf chains, agent-on-chain gaps, grant pipeline. Memory write token: bd4a072e-75e4-45e4-aeb1-1f7b376a984a
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **ONEON has zero ZK — SP1 on Base is the immediate P0 action** — Confidence: HIGH | Sources: 4
   - grep query: `zkproof|verifier|prover|circuit|stark|snark|plonk|sp1` in oneon-web/src → 0 results
   - SP1: MIT, $4B+ secured, 6M+ proofs, $0.04/proof, RISC-V → Rust. Implement ZK credential proofs on existing Base L2. Weeks, not months.

2. **Aztec/Noir is blocked until July 2026** — Confidence: HIGH | Sources: 3
   - Critical proving system vulnerability March 17 2026. v5 fix July 2026.

3. **Hyperliquid integrated in Otto trading infra; HyperEVM NOT** — Confidence: HIGH | Sources: grep-verified
   - `_CHAIN` in crypto.py includes "hyperliquid"; `hyperliquid_equity` in portfolio.py. HyperEVM grep → 0 results.
   - Classification: needs-extension (not gap) for HyperEVM

4. **ZK Stack RaaS L3 = Q3 2026 appchain path (Lens Chain precedent)** — Confidence: MEDIUM | Sources: 2
   - Lens Chain: SocialFi identity L3, Avail DA, GHO gas, $22.4M ZK grant. Deployable <30min via Caldera/Conduit.

5. **Polkadot = grants + BD materials only; zero code** — Confidence: HIGH | Sources: grep-verified
   - projects/polkadot/ and projects/capital/polkadot/ contain only .md files.
   - W3F L1 grant ($10K) submittable now (draft at projects/polkadot/02-w3f-grant-oneon-identity.md).

6. **Agent-on-chain primitive gaps are structural — not chain-solvable** — Confidence: HIGH | Sources: 3
   - 7 gaps: spending policies, portable identity (ERC-8004 unratified), dispute resolution, verified income, cross-chain coordination, accountability, real demand (x402 = $28K/day only).

7. **Cosmos IBC = cross-chain identity portability (2027 horizon)** — Confidence: MEDIUM | Sources: 2
   - IBC v2 live to ETH. Solana bridge near-final. Not actionable Q2/Q3 2026.

8. **Berachain PoL v2 mechanics applicable to ONEON tokenomics** — Confidence: MEDIUM | Sources: 1
   - Validators stake LP tokens (not idle capital), BGT non-transferable governance → SOS contribution gravity model.

9. **Proof costs collapsed — sub-cent ZK viable at consumer scale** — Confidence: HIGH | Sources: 3
   - 45x cheaper ($1.69→$0.0376/proof). SP1 Airbender further 10x.

10. **$70M+ grant capital available this cycle** — Confidence: MEDIUM | Sources: 4
    - Avalanche Retro9000: $40M | ZKsync: 5M tokens | W3F: L1 $10K→L2 $30K+ | EF ESP: $10K–$500K | GG24: Q2 2026

## Contradictions / Uncertainties

- SP1 Prover Network: testnet-only → self-host required now. Cost advantage requires waiting for prover mainnet.
- Starknet (most decentralized, post-quantum) vs ZK Stack (EVM-native, centralized sequencer): security vs velocity tension unresolved.
- Neo4j graph retrieval limited (connection issues). Graph-sourced entity data may be richer.
- Polkadot People Chain DIM1 "basically complete" reported but not live Q1 2026 — no independent verification.

## Recommended Actions

1. **SP1 ZK credential proof on Base — P0, start this sprint**: RISC-V guest in Rust → SP1 proof → Base verifier contract. Closes zero-ZK gap.
2. **Submit W3F L1 grant ($10K)**: Draft exists at projects/polkadot/02-w3f-grant-oneon-identity.md. Submittable now.
3. **Prototype ZK Stack L3 RaaS using Lens Chain as reference**: Mirror Avail DA + GHO gas + social identity namespace. Apply for $22.4M ZK grant.

## Chain Matrix

| Layer | Chain | Timeline | Confidence |
|---|---|---|---|
| ZK proofs | SP1 + Base (self-hosted prover) | NOW | HIGH |
| L3 appchain | ZK Stack RaaS (Caldera/Conduit) | Q3 2026 | MEDIUM |
| Cross-chain interop | Cosmos IBC | 2027+ | MEDIUM |
| AVOID | Aztec/Noir, Polygon zkEVM, Risc0 Bonsai | — | HIGH |

## Memory Write Token
bd4a072e-75e4-45e4-aeb1-1f7b376a984a

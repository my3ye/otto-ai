---
name: WebAssist chain fit synthesis 2026-04-10
description: WebAssist technical direction & chain fit — synthesis of 22 sources (web×9, memory×8, code×5). Base confirmed, gaps grep-verified, Stripe stays primary.
type: project
---

## WebAssist Technical Direction & Chain Fit — Synthesis
**Date:** 2026-04-10 | **Sources:** 22 (web×9, memory×8, code×5, graph×0/error)

## Key Insights (ranked by confidence × actionability)

1. **Base is the correct chain for WebAssist's on-chain layer** — Confidence: HIGH | Sources: 5+ (ecosystem matrix Apr 10, Coinbase Agentic Wallets, x402, AgentPay, Circle Nanopayments all Base-native). Consistent across ecosystem strategy, infrastructure announcements, and payment volume data.

2. **Stripe must remain primary revenue channel — crypto is additive, not replacement** — Confidence: HIGH | Sources: 3 (Stripe test keys Mev-gated blocking revenue; x402 demand only $28K/day; WebAssist code has zero crypto deps). Revenue unblocks the instant Mev activates live keys — this is the highest-ROI action.

3. **Circle Nanopayments enables contributor micropayments NOW at zero cost** — Confidence: HIGH | Sources: 2 (Circle Mar 2026 announcement; 140M txns/Mar validated independently). Avg $0.31/tx, off-chain aggregation, on-chain batch settlement. Removes the economic barrier to paying human contributors on Base.

4. **AgentPay (Apr 8 2026) is the interoperability bridge for multi-rail payment acceptance** — Confidence: HIGH | Sources: 2 (CoinDesk Apr 8; Alchemy launch announcement). Coinbase, Stripe, Visa, Mastercard all participating. Private beta → GA imminent. Enables WebAssist to accept from all rails without implementing each.

5. **Assistive Technologies mandate requires 4 on-chain primitives** — Confidence: MEDIUM | Sources: 2 (Mev directive Mar 18; 505 Systems 3-layer architecture). Required: (a) contributor payment/royalty rails, (b) on-chain quality voting, (c) agent identity, (d) training data provenance. Directive is clear; implementation sequence is not specified.

6. **x402 HTTP-native agent billing is viable but early** — Confidence: MEDIUM | Sources: 2 (x402.org, $28K/day real demand, Cloudflare/Circle/AWS backing). Path: AI agents pay WebAssist API directly via 402 response cycle. Demand is low now but structural (AI agents increasingly need to pay for services autonomously). Not a Q2 revenue driver.

7. **ERC-8004 agent identity standard is too early to build on** — Confidence: LOW | Sources: 1 (single-source web mention). Standard described as "early." Not a blocking dependency for WebAssist's on-chain layer.

## Contradictions / Uncertainties

- **Solana vs Base**: Solana holds 65% of agentic payments but ecosystem strategy chooses Base. Resolution: not a contradiction — ecosystem alignment and x402/AgentPay infrastructure on Base outweigh volume metrics on Solana for WebAssist's specific use case (contributor rails + governance, not trading volume).
- **x402 demand**: $28K/day is low relative to Circle's 140M txns/month. These measure different things — x402 = HTTP API billing protocol (new category), Nanopayments = aggregated micro-transfers (mature). No conflict; both relevant to different WebAssist payment layers.
- **Knowledge graph gap**: Neo4j returned 500 (ongoing outage). Zero graph data available. May contain relationship data on ecosystem actors that would strengthen chain selection confidence. Flag for next cycle.

## Recommended Actions (top 3)

1. **Activate Stripe live keys** [Mev action required] — Expected impact: Immediate revenue unlock. WebAssist is built and deployed at webassist.ink. This single action converts the service from demo to live revenue. No technical work needed.

2. **Add Base/USDC accept path via AgentPay alongside Stripe** — Expected impact: Captures agentic B2B clients (AI companies, agent developers) who pay in USDC. Implementation: integrate AgentPay SDK (private beta access needed), wire `viem` + Base chain config, add USDC Checkout option in `/order` flow. Additive — does not touch Stripe path.

3. **Design contributor payment smart contract on Base** — Expected impact: Unblocks Assistive Technologies ecosystem build. Spec: simple escrow (project fee → USDC on Base) + royalty splitter (agent pool / expert pool / treasury / voter rewards) + Circle Nanopayments for sub-$1 micropayments. Can parallel-track with Action 1.

## Evidence Quality Assessment

Coverage: PARTIAL — Neo4j graph dimension entirely absent (ongoing 500 error). All other source types well-covered.
Source reliability: HIGH — Web sources are recent (Apr 2026), codebase grep-verified, memory hits are validated prior syntheses.
Gaps: (1) Neo4j relationship data on ecosystem actors; (2) AgentPay private beta access confirmation; (3) Circle Nanopayments integration complexity (no code examples available).

## Gap Verification Log (required)

| Claimed Gap | Search Query | Result |
|---|---|---|
| Wallet integration | `grep wagmi\|viem\|ethers\|web3 src/` | 0 matches in src/ (1 ENS display string in order/page.tsx line 34 — not integration) |
| USDC accept path | `grep usdc\|stablecoin src/` | 0 matches |
| x402/agent billing | `grep x402\|agentpay\|agent.pay src/` | 0 matches |
| Contributor smart contract | `glob **/*.sol, **/*contract*` | No contract files found |
| On-chain voting | `grep governance\|voting src/` | 0 matches |

All 5 gap claims confirmed ABSENT. No downgrades required.

## Compressed Handoff (≤1000 tokens)

**WebAssist current state**: Next.js 15.5.12 + Supabase + Stripe + Vercel + Google/OpenAI. Code-verified zero crypto deps. Stripe in test mode — live keys Mev-gated. Revenue model: $999-$4,999 projects + $99/mo AI Manager subscription. REYA AI assistant = agent-first UI pattern in place.

**Chain decision**: Base. Aligned with Apr 10 ecosystem matrix (Base NOW → ZK Stack L3 Q3 2026). Infrastructure available NOW: Coinbase Agentic Wallets, x402 native, AgentPay multi-rail (Apr 8), Circle Nanopayments (zero-cost micro batching, 140M txns/Mar, avg $0.31).

**5 verified gaps** (grep-confirmed absent, search queries logged):
1. Wallet integration — ABSENT (no wagmi/viem/ethers)
2. USDC accept path — ABSENT (no stablecoin code)
3. x402 agent billing — ABSENT (no x402/agentpay code)
4. Contributor payment contract — ABSENT (no .sol files)
5. On-chain quality voting — ABSENT (no governance code)

**Mev directive**: Assistive Technologies = agents + human experts + on-chain governance + training data provenance. 505 Systems 3-layer architecture (Intelligence + Consensus + Physical) defines the governance model. WebAssist on-chain layer must implement contributor rails + quality voting as primitives.

**Priority order**: (1) Stripe live keys [Mev action, instant revenue] → (2) AgentPay/USDC path for agent clients → (3) Contributor contract on Base. x402 agent billing = medium-term (demand still early, $28K/day). ERC-8004 agent identity = deprioritize (standard too immature).

**Confidence**: Chain choice HIGH. Gap claims HIGH (code-verified). x402 demand LOW-MEDIUM (single-source real-world signal). Knowledge graph data: ABSENT this cycle (Neo4j 500, flag for repair).

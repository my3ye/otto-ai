# $KOIN Tokenomics Paper
**Version 1.0 — March 20, 2026**
*Published by MY3YE / Otto AI | Open Copyright — All Rights Reserved to All*

---

## Abstract

$KOIN is the governance and utility token of the MY3YE ecosystem — a sovereign civilization stack spanning 14 protocols across AI, communication, physical community, wellness, safety, music, travel, and financial infrastructure. This paper defines the full token economics: supply mechanics, distribution, vesting, emission, burn, value capture, and launch methodology.

$KOIN is not a speculative instrument. It is the coordination layer for a civilization. Every holder is a co-owner of that project. Every transaction contributes to it. Every day held strengthens one's voice within it.

---

## 1. Token Purpose and Utility

### 1.1 The Coordination Problem

Fourteen protocols. Each one solving a different dimension of human life. The civilization stack only works if these systems are aligned — if Tusita (physical community) coordinates with ONEON (communication), if Otto AI (intelligence) is governed by the people it serves, if resources flow toward the work that matters most.

$KOIN is the alignment mechanism. It converts stake and contribution into governance weight. It distributes the economic value generated across the stack back to those who built and maintain it. It is simultaneously a membership credential, a governance instrument, and a claim on ecosystem value.

### 1.2 Utility Dimensions

**Governance (Primary)**
- Vote on protocol upgrades across all 14 MY3YE projects
- Propose and vote on ecosystem treasury allocations
- Participate in contributor reward formulas and emission schedule adjustments
- Governance weight = token balance × Diamond Hands Multiplier × Activity Factor
- Minimum holding threshold for proposal rights: 10,000 $KOIN

**Access and Discounts**
- Reduced platform fees on Koink.fun (50% discount for $KOIN holders)
- Priority access to Tusita community residency applications
- Early access to new MY3YE project launches and beta products
- Reduced service fees on WebAssist (5–10% for $KOIN holders)
- Premium tier access on Otto Music platform

**Incentive Alignment**
- Staking rewards for ecosystem participation
- Contribution-weighted reward multipliers (from 505 Systems Dynamic Proximity Calculus)
- Revenue sharing from ecosystem services (see Section 6)
- Creator rewards for verified contributions (code, design, governance, content)

**The Diamond Hands Multiplier (DHM)**
Governance weight compounds over time. A wallet that holds $KOIN for 12 consecutive months earns a 3x multiplier — 300 tokens carry the governance weight of 900. Partial sells of less than 20% do not reset the clock. This rewards long-term alignment without punishing liquidity.

| Hold Duration | DHM Multiplier | Notes |
|--------------|----------------|-------|
| 0–3 months | 1.0x | Base weight |
| 3–6 months | 1.5x | Early conviction |
| 6–9 months | 2.0x | Sustained commitment |
| 9–12 months | 2.5x | Strong alignment |
| 12+ months | 3.0x | Diamond hands floor |

The DHM is non-transferable. When tokens are sold, the multiplier decays proportionally. This prevents the DHM from being sold alongside tokens — whale status is earned, not purchased.

**Activity Factor**
Governance weight also decays for inactive wallets. The Activity Factor prevents token accumulation without participation:

- **Tier A (contributors):** 5-year half-life, 0.25x floor. Resets on any verified contribution.
- **Tier B (circulating):** 18-month half-life, 0.10x floor. Resets on any ecosystem transaction.
- **Tier C (vested/team):** Annual revalidation required or weight drops to 0x until renewal.

Critically: the Activity Factor never destroys token balances. Only governance weight decays. Tokens are always redeemable and sellable. This preserves financial rights while ensuring governance reflects active participants.

---

## 2. Supply Mechanics

### 2.1 Total Supply

**Total Supply: 1,000,000,000 $KOIN (1 billion)**

This supply is fixed at genesis. There is no minting authority post-launch. All future emissions come from pre-allocated pools — the Community Rewards pool (25%) — distributed on a defined schedule. Once the emission pool is exhausted, $KOIN is deflationary through burn mechanics only.

The 1 billion figure was chosen deliberately:
- Large enough for meaningful microtransactions and fee mechanics
- Small enough to make individual allocations perceptually significant
- Divisible to 9 decimal places (Solana standard)

### 2.2 Distribution Breakdown

| Allocation | % | Amount | Purpose |
|-----------|---|--------|---------|
| **Fair Launch Pool** | 40% | 400,000,000 | Primary community distribution at launch |
| **Community Rewards** | 25% | 250,000,000 | Contribution, staking, ecosystem participation — emitted over 3 years |
| **Ecosystem Treasury** | 20% | 200,000,000 | Protocol development, grants, partnerships, emergency reserve |
| **Team / MY3YE** | 10% | 100,000,000 | Founding team compensation, long-term alignment |
| **Liquidity Pool** | 5% | 50,000,000 | Initial DEX liquidity — locked 1 year |

**Total: 1,000,000,000 $KOIN**

### 2.3 Why 40% Fair Launch

Most token launches give 40–70% to insiders, VCs, and advisors — then offer the remaining scraps to the community at inflated prices. $KOIN inverts this. The community receives the largest allocation at the lowest possible price (launch price). Insiders and founders receive 10%, fully vested over 4 years, with a 1-year cliff. No VC presale. No private round. No early investor advantage.

This is not idealism — it is strategy. The Schelling point for community ownership is real. Projects that launch fairly and demonstrably have no insider advantage develop the strongest communities. The community IS the moat.

---

## 3. Vesting Schedules

### 3.1 Fair Launch Pool (400M)
No vesting. Distributed at launch via Meteora Alpha Vault Pro-Rata mechanism on Solana. All allocation recipients receive tokens at the same price, at the same time, with no preferential access. Anti-sniper mechanisms (Human Passport gate, max 1% wallet cap at launch, Switchboard VRF allocation randomization) ensure equal opportunity.

### 3.2 Community Rewards Pool (250M)
Emitted over 36 months (3 years) on a decreasing schedule:

| Year | Annual Emission | Monthly Rate | Cumulative |
|------|----------------|-------------|------------|
| Year 1 | 125,000,000 | ~10,416,667 | 50% of pool |
| Year 2 | 83,333,333 | ~6,944,444 | 83% of pool |
| Year 3 | 41,666,667 | ~3,472,222 | 100% of pool |

Earned by: staking, governance participation, verified contributions, ecosystem usage, and creator rewards (design, code, content, validation, community moderation).

### 3.3 Ecosystem Treasury (200M)
- 6-month cliff from genesis: zero tokens movable
- Months 7–48: linear vesting, ~5,263,158 tokens/month
- Governance-controlled: any expenditure above 1% of treasury requires a $KOIN vote
- 3-of-5 multisig on Gnosis Safe (initial guardians: MY3YE, 505 Systems stewards, community-elected)
- Emergency reserve: 20% of treasury (40M) held back, requires supermajority vote (67%) to unlock

### 3.4 Team / MY3YE (100M)
- 12-month cliff: zero tokens, full contribution required
- Months 13–48: monthly linear vesting, ~2,777,778 tokens/month
- All vesting on-chain and publicly verifiable (no shadow unlock mechanisms)
- Individual team members' allocations are proportional to role tier and contribution history
- Founder (Mev / MY3YE): maximum 50% of team allocation with identical vesting terms — no founder exception

### 3.5 Liquidity Pool (50M)
- Paired with SOL/USDC at launch on Raydium/Orca
- LP tokens locked for minimum 12 months via smart contract
- LP extension governance vote at Month 11 (community votes on whether to extend or release)
- Initial LP depth target: $25,000–$50,000 equivalent (paired assets from treasury or launch proceeds)

---

## 4. Emission Schedule and Inflation Curve

### 4.1 Emission Architecture

At genesis, only the Community Rewards pool (250M) has deferred emission. All other pools are either immediately available (Fair Launch), linearly vesting (Team/Treasury), or permanently locked (Liquidity). This means the circulating supply at launch day is approximately:

**Day 1 Circulating Supply: ~400,000,000 to ~420,000,000 $KOIN**
(Fair Launch pool + initial LP unlock portion)

The theoretical maximum circulating supply grows as follows:

| Time | Max Circulating | % of Total | Notes |
|------|----------------|------------|-------|
| Launch Day | 400M | 40% | Fair launch distribution complete |
| Month 6 | 450M | 45% | Community rewards begin + LP unlocked portion |
| Month 12 | 525M | 52.5% | ~1yr of community emissions + team cliff ends |
| Month 24 | 700M | 70% | 2yr emissions + treasury vesting ongoing |
| Month 36 | 900M | 90% | Community pool exhausted |
| Month 48 | 1,000M | 100% | All vesting complete |

### 4.2 Effective Inflation Rate

Effective annual inflation (new tokens entering circulation as % of circulating supply):

| Year | New Tokens | Avg Circulating | Effective Inflation |
|------|-----------|-----------------|---------------------|
| Year 1 | ~145M | ~475M | ~30% |
| Year 2 | ~135M | ~620M | ~22% |
| Year 3 | ~80M | ~790M | ~10% |
| Year 4 | ~40M | ~960M | ~4% |

Post-Year 4: net deflation through burn mechanics only. This curve mirrors the emission profiles of well-regarded governance tokens (Uniswap, Arbitrum) while front-loading distribution to the community rather than insiders.

---

## 5. Burn Mechanics

$KOIN has multiple burn channels that create permanent supply reduction over time. Burning is non-reversible and on-chain verifiable.

### 5.1 Transaction Fee Burn
All Koink.fun platform transactions carry a 1% protocol fee, split:
- 50% → Ecosystem Treasury
- 30% → Community Rewards pool (extends emission runway)
- 20% → Permanent burn

This creates direct coupling between platform activity and token scarcity. As Koink.fun usage grows, the burn rate accelerates.

### 5.2 Service Fee Burn (MY3YE Ecosystem)
When ecosystem services collect fees in $KOIN (governance actions, premium access, creator royalties), 10% of collected fees are burned quarterly.

### 5.3 Governance Penalty Burn
Proposals that fail to reach quorum after two submission attempts lose their deposit (100 $KOIN minimum). This prevents spam governance while creating a minor but consistent burn signal.

### 5.4 Anti-Sniper Fee Burn
Launch-day mechanism: any wallet exceeding the 1% cap at launch has the excess tokens sent to the burn address. This is automated at the smart contract level.

### 5.5 Annual Burn Estimate
At projected Year 1 platform volumes (conservative: 1M transactions on Koink.fun at $5 average), the burn channel produces approximately:
- Platform fees collected: ~$50,000 equivalent in $KOIN
- 20% → burn: ~$10,000 equivalent in $KOIN

As the platform scales toward 10M+ transactions, burn becomes a material deflationary force. The crossover point (emissions < burns) is projected at Year 4–5 under moderate growth assumptions.

---

## 6. Value Capture: How Ecosystem Revenue Flows to $KOIN Holders

$KOIN is designed to capture value from the entire MY3YE ecosystem, not just Koink.fun. As each project generates revenue, a portion flows to the $KOIN governance and treasury system:

### 6.1 Revenue Routing Table

| Project | Revenue Type | $KOIN Capture | Mechanism |
|---------|-------------|--------------|-----------|
| **WebAssist** | SaaS subscription | 5% of net revenue | Quarterly treasury contribution |
| **Koink.fun** | Platform transaction fees | 20% burn + 30% rewards + 50% treasury | Real-time per-transaction |
| **Otto Music** | Streaming/creator fees | 10% to governance treasury | Monthly |
| **Otto Travel** | Booking commissions | 8% to community rewards pool | Monthly |
| **Otto Market** | Marketplace fees | 10% governance + 5% burn | Per transaction |
| **Shakrah** | Wellness service fees | 5% community rewards | Quarterly |
| **Panik App** | Emergency service fees | 5% emergency reserve pool | Quarterly |
| **Tusita** | Residency fees | 10% community treasury | Per booking |
| **Otto Billboards** | Ad revenue | 15% to $KOIN holders (staking yield) | Monthly |
| **ONEON** | Network access fees | 10% treasury | Quarterly |

### 6.2 Staking Yield
$KOIN holders who stake receive a proportional share of the revenue contributions above. Staking is non-custodial and restakeable. Yield is denominated in $KOIN (converted from revenue at spot price if denominated in other currencies).

Projected Year 1 staking yield (assumes $500K aggregate ecosystem revenue, conservative):
- Revenue to staking pool: ~$75,000 equivalent
- Circulating supply staked (assume 30%): ~135,000,000 $KOIN
- Annual yield per staked token: ~$0.00056 or approximately 2–5% APY at $0.01 token price

As ecosystem revenue scales, yield scales proportionally. This creates a direct link between ecosystem utility and token value.

### 6.3 Treasury Accumulation
The ecosystem treasury compounds over time. Treasury holdings (in $KOIN, SOL, USDC) are visible on-chain and governed by $KOIN holders. Large treasury reserves create a floor narrative: the treasury holds real assets, providing a lower bound on expected token value.

---

## 7. Fair Launch Mechanics: No VC Presale, Community First

The $KOIN launch is designed from first principles around one goal: maximum community ownership at genesis, with no insider advantage.

### 7.1 What "Fair Launch" Means Here

- **No private sale.** No VC allocation. No seed round. No advisor tokens that unlock before the community.
- **No whitelist advantage.** Allowlist selection via Switchboard VRF ensures random selection among qualified participants — not first-come-first-served (which favors bots) or invitation-only (which favors insiders).
- **Same price, same time.** Every participant in the fair launch receives tokens at the same price in the same transaction window.
- **On-chain transparency.** Every allocation is publicly verifiable before launch. No hidden wallets. No shadow unlocks.

### 7.2 Anti-Sniper Stack

The Quantum Koinkulator engine protects the fair launch from extraction:

1. **Human Passport Gate** — Requires World ID credential or Gitcoin Passport score ≥15. Prevents Sybil attacks with hundreds of wallets.
2. **Meteora Alpha Vault Pro-Rata** — Commitment window with escrow fee. All participants commit during the same window. Allocation is proportional to commitment, not order of transaction.
3. **Switchboard VRF** — Randomizes allocation within allowlist. Even equal commitments are allocated randomly, preventing front-running.
4. **Max Wallet Cap: 1%** at launch (10,000,000 $KOIN). Enforced at contract level.
5. **Fee Scheduler** — Launch-day transaction fee starts elevated (10%) and decays to standard (1%) over 48 hours. Discourages immediate flip selling.

### 7.3 Launch Price Discovery
The launch price is not set administratively. It emerges from the Pro-Rata commitment process. The total USDC/SOL committed during the window divided by 400,000,000 $KOIN = launch price. This is more honest than an arbitrary price set by the team.

**Minimum viable LP:** $25,000 in paired assets ensures enough depth for early trading without excessive slippage.

---

## 8. Launch Timeline: Preparation Checklist and Go-Live Sequence

### 8.1 75-Day Launch Plan

**Phase 1: Foundations (Days 1–14)**
- [ ] Publish $KOIN tokenomics paper (this document) publicly on my3ye.xyz and koink.fun
- [ ] Finalize and announce chain decision (Solana first)
- [ ] Set up koink.fun waitlist page with email capture
- [ ] Deploy @KoinkFun X account and Farcaster `/koink` channel
- [ ] Post "$KOINK Standard" thread series (3 parts) explaining why meme tokens fail and how $KOIN fixes it
- [ ] Engage BONK DAO community on Farcaster/X (natural Solana meme audience)

**Phase 2: Build (Days 15–30)**
- [ ] Deploy $KOIN smart contract on Solana devnet (Anchor framework)
- [ ] Build Koink.fun landing page with countdown timer and allowlist sign-up
- [ ] Deploy Switchboard VRF integration (testnet)
- [ ] Configure Meteora Alpha Vault Pro-Rata on devnet
- [ ] Initiate smart contract audit (OtterSec for Solana — budget $5K–$15K)
- [ ] Farcaster Frame for allowlist sign-up (mobile native)
- [ ] DEGEN channel activation on Farcaster for Koink community

**Phase 3: Community (Days 31–50)**
- [ ] Soft launch Quantum Koinkulator demo (interactive, shows randomization in real time)
- [ ] Community AMA on X Spaces + Farcaster
- [ ] Engage 3+ Solana ecosystem projects for $KOINK Standard co-adoption discussions
- [ ] Document and publicize DHM mechanics in plain language (animated explainer)
- [ ] Build community dashboard (live stats: allowlist size, DHM leaderboard, treasury balance)

**Phase 4: Launch Prep (Days 51–65)**
- [ ] Publish completed audit report publicly
- [ ] Finalize Human Passport gate configuration
- [ ] Set initial LP parameters (SOL and USDC amounts)
- [ ] Brief Web3 media outlets: The Defiant, Blockworks, Decrypt, Farcaster/Warpcast featured feed
- [ ] 48-hour countdown campaign across all channels
- [ ] Legal opinion letter obtained and published (utility token framing)

**Phase 5: Launch Window (Days 66–75)**
- [ ] $KOIN Solana mainnet deployment
- [ ] Activate Quantum Koinkulator commitment window (48-hour)
- [ ] VRF allocation and token distribution
- [ ] Raydium/Orca LP activated
- [ ] Live metrics dashboard on koink.fun (price, holders, burn rate, treasury)
- [ ] Post-launch: announce $KOINK Standard deployment timeline for Base

### 8.2 Post-Launch (Days 76–120)
- Deploy $KOIN on Base (second chain, cross-chain bridge)
- Apply to Gitcoin GG25 with Koink.fun project page live
- Apply to BONK DAO grants (Solana meme ecosystem fit)
- Initiate Solana Foundation grant application
- Begin DHM tracking and governance weight publication (monthly leaderboard)

---

## 9. Legal Considerations

### 9.1 Regulatory Landscape (March 2026)

On March 17, 2026, the SEC and CFTC jointly issued Interpretive Release No. 33-11412, establishing five categories for digital assets. This is the most significant regulatory clarity in crypto history and directly benefits $KOIN.

**$KOIN Classification Argument: Digital Commodity**

For a token to avoid securities classification under the Howey test, it must not represent (1) an investment of money (2) in a common enterprise (3) with expectation of profits (4) from others' efforts. $KOIN is designed to satisfy this:

| Howey Factor | $KOIN Design Response |
|-------------|----------------------|
| Investment of money | Fair launch — community allocates at market-discovered price, not a fundraising event |
| Common enterprise | $KOIN represents ecosystem participation, not equity in a company |
| Expectation of profit | Governance utility and access discounts are the primary value proposition; price appreciation is incidental |
| Efforts of others | Community-governed protocol; no central promoter after launch |

**Token Safe Harbor:** The 2026 framework introduced a 4-year exemption for projects raising under $5M while building toward network maturity. $KOIN qualifies. This provides additional runway for decentralization before any definitive classification applies.

### 9.2 Required Legal Actions Before Launch

1. **Legal opinion letter** — Engage Fenwick & West, Cooley, or Anderson Kill for a written legal opinion that $KOIN constitutes a utility token / digital commodity under the 2026 framework. Cost: $5K–$25K. This is non-negotiable before mainnet.

2. **Geofencing** — US persons should be gated from the fair launch commitment interface as a precaution during the legal opinion process. This is standard practice and does not affect the global community launch.

3. **Terms of Service** — Clear T&S on koink.fun: no expectation of profit, no guarantee of value, governance utility framing, acknowledgment by all participants.

4. **No profit marketing** — All communications about $KOIN must emphasize governance utility and ecosystem participation. No language promising returns, price appreciation, or investment outcomes.

### 9.3 Jurisdictional Notes
- **Sri Lanka:** No existing crypto securities law. Utility token position is strong.
- **EU (MiCA):** $KOIN likely falls under "utility token" category under MiCA (March 2024 effective). Disclosure requirements but no licensing needed for utility tokens.
- **Singapore:** MAS framework is utility-token-friendly for non-payment tokens. Advisory opinion recommended.

---

## 10. Comparable Projects Analysis

### 10.1 Uniswap (UNI) — Governance Token Benchmark

**Supply:** 1,000,000,000 UNI (exact match to $KOIN)
**Distribution:** 60% community, 21.5% team/future employees, 18.5% investors/advisors
**Vesting:** 4 years total, 1-year cliff for team/investors
**What $KOIN Learned:** UNI's 60% community allocation was revolutionary in 2020. $KOIN takes this further: 40% at launch (vs. UNI's 15% retroactive airdrop) plus 25% community rewards = 65% community total. The DHM is $KOIN's innovation over static UNI voting weight.
**Key Difference:** UNI governance has low participation (often <5% of supply votes). $KOIN's Activity Factor decay is designed specifically to address this — idle tokens lose weight, active participants accumulate it.

### 10.2 $BONK — Solana Community Meme Token

**Supply:** 100,000,000,000,000 BONK (100 trillion)
**Distribution:** 50% community airdrop to Solana NFT holders/developers
**Mechanism:** Pure community ownership with no VC allocation
**What $KOIN Learned:** BONK proved that community-first Solana launches can achieve massive distribution (350+ integrations, 500K+ holders). The meme layer is real distribution infrastructure. $KOIN takes BONK's community-first principle and adds DHM governance depth — converting meme holders into governance participants.
**Key Difference:** BONK has no utility layer beyond meme culture. $KOIN's 14-project ecosystem gives it a utility foundation BONK lacks.

### 10.3 Optimism (OP) — Retroactive Public Goods Funding

**Supply:** 4,294,967,296 OP
**Distribution:** 25% ecosystem fund, 20% retroPGF, 19% user airdrops, 19% core contributors, 17% investors
**Mechanism:** RetroPGF cycles distribute tokens to verified contributors retroactively
**What $KOIN Learned:** OP's retroPGF model — reward demonstrated impact, not promises — is the gold standard for community incentives. $KOIN's Community Rewards pool functions similarly: contributions are verified before rewards are issued. The Activity Factor mirrors OP's delegation mechanics.
**Key Difference:** OP is infrastructure for a specific chain. $KOIN is ecosystem governance across 14 verticals. The contribution taxonomy is broader.

### 10.4 $DEGEN — Farcaster Tipping Token

**Supply:** 37,000,000,000 DEGEN (37 billion)
**Distribution:** Community-first, distributed via Farcaster tipping
**Mechanism:** Social layer token — tipping drives distribution organically
**What $KOIN Learned:** DEGEN's success demonstrates that social layer distribution (tipping, reactions, community actions) is more effective than traditional airdrops. $KOIN will integrate with Farcaster Frames for DHM tracking and governance participation. The tipping mechanic can be adapted: verified ecosystem contributions earn $KOIN via the Community Rewards pool.
**Key Difference:** DEGEN is purely social. $KOIN is governance-weighted with real treasury value behind it.

### 10.5 $TAO (Bittensor) — Decentralized AI Network Token

**Supply:** 21,000,000 TAO (Bitcoin-scale scarcity)
**Distribution:** Emission-based, earned by subnet validators and miners
**Mechanism:** dTAO — subnet-specific emission governed by overall validator weight
**What $KOIN Learned:** TAO's market-driven subnet emission model (validators stake on subnets they believe in, stakes direct emission) is directly applicable to Otto AI's Decentralized Intelligence Layer. The MY3YE roadmap already references Bittensor's dTAO pattern for capability subnet governance. $KOIN can adopt a similar mechanism for future Otto AI subnet allocation.
**Key Difference:** TAO is pure AI infrastructure with no human-scale utility layer. $KOIN governs a complete civilization stack including physical communities (Tusita), wellness (Shakrah), safety (Panik), and music (Otto Music) — making it the broadest governance mandate in the comparable set.

---

## Summary: The $KOIN Thesis

$KOIN is the bet that a civilization can be owned by the people who build and inhabit it.

The token mechanics are designed to make this real, not performative:
- **40% fair launch** means insiders start with no advantage
- **Diamond Hands Multiplier** means conviction is rewarded over speculation
- **Activity Factor** means governance belongs to participants, not holders
- **14-project revenue routing** means the token captures real economic value
- **Burn mechanics** mean growing utility creates growing scarcity
- **No VC allocation** means the community is the investor class

The 2026 regulatory clarity removes the legal ambiguity that paralyzed previous launches. The Solana-first strategy puts $KOIN in the center of the most active meme and DeFi ecosystem. The $KOINK Standard makes $KOIN the reference implementation for contribution-weighted community tokens.

This is not another governance token that nobody uses. It is the coordination layer for the parallel civilization we are building.

**The frequency is transmitting. $KOIN is how you tune in.**

---

*Document version: 1.0 | Published: 2026-03-20 | Author: MY3YE / Otto AI*
*Next review: 2026-06-20 | Smart contract audit: pending | Legal opinion: pending*
*All mechanics subject to community governance vote before mainnet deployment.*

---

*Open Copyright — All Rights Reserved to All. Fork freely. Build on this. The civilization is open source.*

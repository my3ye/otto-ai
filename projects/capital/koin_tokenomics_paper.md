# $KOIN Tokenomics Paper
## The Fair-Launch Currency of the Koink.fun Ecosystem

**Version:** 1.0
**Published:** 2026-03-17
**Author:** MY3YE / Koink.fun
**Status:** Pre-launch (for investor and community review)

---

## Abstract

$KOIN is the utility and governance token of the Koink.fun ecosystem — a fair-launch, anti-whale, contribution-weighted currency designed for builders, not extractors. Unlike most tokenomics models that concentrate power at launch, $KOIN is engineered to distribute power over time to those who contribute to the ecosystem.

The Quantum Koinkulator ensures every launch is fair. The Diamond Hands Multiplier ensures loyalty earns weight. The 505 Systems DPC governs the treasury. The result: a token that gets more equitable the longer it runs, not less.

This paper covers:
- Total supply and distribution
- Fair launch mechanics (Quantum Koinkulator)
- Anti-whale protections
- Diamond Hands Multiplier
- Community treasury governance
- Contribution-weighted governance model
- Token utility

---

## 1. Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    $KOIN — AT A GLANCE                       │
├─────────────────────────────────────────────────────────────┤
│  Total Supply     │  1,000,000,000 (1 Billion)               │
│  Symbol           │  $KOIN                                   │
│  Ecosystem        │  Koink.fun                               │
│  Governance       │  505 Systems DPC                         │
│  Fair Launch      │  Quantum Koinkulator (VRF-based)         │
│  Anti-Sniper      │  Hard caps first 24h + block-time epochs │
│  Sell Tax         │  0% → 15% (first 30 days) → 3% stable   │
│  Governance       │  Contribution-weighted, not token-weighted│
└─────────────────────────────────────────────────────────────┘
```

$KOIN is the currency that powers the Koink.fun ecosystem. It is earned, not just bought. It accrues weight through contribution, not accumulation. And it governs through demonstrated alignment, not whale votes.

---

## 2. Token Distribution

```
$KOIN — 1,000,000,000 Total Supply
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Community (40%)     ████████████████░░░░░░░░░░░░░░░░  400M
 Treasury (20%)      ████████░░░░░░░░░░░░░░░░░░░░░░░░  200M
 Team (15%)          ██████░░░░░░░░░░░░░░░░░░░░░░░░░░  150M
 LP (15%)            ██████░░░░░░░░░░░░░░░░░░░░░░░░░░  150M
 Ecosystem Grants    ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░  100M
 (10%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 2.1 Community Allocation — 400M (40%)

The largest allocation. Earned, not airdropped.

**Distribution mechanism:**
- Building tools and contributing code to Koink.fun repos
- Creating content that drives verified ecosystem growth
- Participating in governance (voting, proposing, executing)
- Long-term holding (Diamond Hands Multiplier, Section 4)
- Community education and onboarding contributions

**Purpose:** This is the most important allocation. It makes $KOIN a currency that rewards builders and believers — not early whales who flip for profit.

### 2.2 Treasury — 200M (20%)

Governed by the **505 Systems Decentralized Protocol Committee (DPC)**.

**Inflows:**
- 20% of all sell taxes flow to treasury
- Ecosystem protocol fees
- Partnership fees

**Outflows (DPC-governed):**
- Ecosystem development grants
- Bug bounties
- Community campaigns
- Emergency protocol reserves

**Governance:** Treasury actions require contribution-weighted quorum. No single entity can drain or redirect the treasury unilaterally.

### 2.3 Team — 150M (15%)

2-year linear vest with 6-month cliff.

```
Block 0              Block ~4M           Block ~8M
    │                    │                   │
    ▼                    ▼                   ▼
  Launch              Cliff ends          Full vest
    │                (25% released)      (100% released)
    └────────────────────────────────────────┘
         Linear vest over remaining 18 months
```

**Rationale:** Team tokens vest over time to align long-term incentives. The 6-month cliff prevents early dumping. Block-based epochs are used (not timestamp-based) for trustless vesting — `block.timestamp` can be manipulated by validators; block height cannot.

### 2.4 Initial Liquidity — 150M (15%)

Seeded into the initial Koink.fun liquidity pool.

- Locked for minimum 12 months on launch
- Unlock schedule governed by DPC after lock period
- Paired with SOL (Solana launch) or ETH/USDC (multi-chain)

**Purpose:** Ensure deep enough liquidity for the fair launch and prevent slippage attacks in the Quantum Koinkulator.

### 2.5 Ecosystem Grants — 100M (10%)

Reserved for projects building on or integrating the $KOINK Standard.

**Eligibility:**
- Projects adopting the $KOINK Standard tokenomics template
- Integrations with the Koink.fun ecosystem
- Public goods and tooling that benefit the broader Web3 community
- Cross-chain deployments that expand $KOIN reach

---

## 3. Quantum Koinkulator — Fair Launch Mechanics

The most important design choice in $KOIN is how it launches. Most tokens fail because they reward whoever is fastest, best-connected, or running bots — not whoever believes in the project.

The **Quantum Koinkulator** uses on-chain **Verifiable Random Functions (VRF)** to create a fair launch that no one can predict, front-run, or snipe.

### 3.1 How It Works

```
User registers intent to participate
            │
            ▼
  VRF generates random launch slot
  (unique per wallet, unpredictable)
            │
            ▼
  User's purchase window opens at
  their assigned slot (±3 blocks)
            │
            ▼
  Hard buy cap enforced per wallet
  (first 24h: max 0.1% of supply)
            │
            ▼
  Graduated sell tax activates
  (see Section 3.3)
```

### 3.2 Anti-Sniper Protections

**Problem:** Bots and insiders monitor mempool and execute trades at block 0 of launch, accumulating massive positions before real users can participate.

**$KOIN Solution:**

| Protection | Mechanism |
|------------|-----------|
| VRF slot assignment | Each wallet gets a random launch window — bots can't target block 0 |
| Hard buy caps (24h) | Max purchase = 0.1% of total supply per wallet first 24 hours |
| Hard buy caps (week 1) | Max purchase = 0.3% of total supply per wallet first 7 days |
| No presale | No pre-launch allocations to insiders outside of transparent team vest |
| No private rounds | All early access is community-earned, not purchased |
| Block-based epochs | Timing cannot be gamed via `block.timestamp` manipulation |

### 3.3 Graduated Sell Tax

The sell tax is designed to discourage pump-and-dump behavior without punishing long-term holders.

```
Launch                 Day 30              Stable
  │                     │                   │
  │ 0%─────────────15% │ Gradient decay     │ 3%
  │     First 30 days   │ to stable          │
  ▼                     ▼                   ▼

  Block 0              Block ~1.3M         Block ~2M+
  ┌──────────────────────────────────────────────────┐
  │  Day 0-1:   0%  (grace period)                   │
  │  Day 2-7:   5%  (early buyers protected)         │
  │  Day 8-14:  8%  (cooling period)                 │
  │  Day 15-21: 12% (peak discouragement)            │
  │  Day 22-30: 15% (max tax)                        │
  │  Day 31+:   Gradual decay → 3% stable            │
  └──────────────────────────────────────────────────┘
```

**Sell tax distribution:**
- 20% → Community Treasury (DPC-governed)
- 50% → LP reinforcement (deepens liquidity)
- 30% → Burned (deflationary pressure)

**Long-term holders are unaffected:** The 3% stable rate applies once the ecosystem has matured. Diamond Hands holders (Section 4) have their governance weight, not tax exemptions — the tax applies equally to discourage speculation at any stage.

---

## 4. Diamond Hands Multiplier

The Diamond Hands Multiplier is $KOIN's most differentiated feature: **governance weight that compounds with loyalty and contribution.**

### 4.1 How It Works

```
Hold Duration    Governance Weight Multiplier
─────────────    ────────────────────────────
Launch (Day 0)        1.0x  ████
3 months              1.5x  ██████
6 months              2.0x  ████████
9 months              2.5x  ██████████
12 months             3.0x  ████████████
```

**Key properties:**
- Non-transferable — the multiplier lives on the wallet, not the tokens
- Resets on full sell — if you sell all your $KOIN, multiplier resets to 1x
- Partial sell tolerance — selling <20% of your position doesn't reset the multiplier
- Compounds with contribution score (see Section 6)

### 4.2 Why This Matters

Traditional tokenomics reward whoever holds the most tokens. $KOIN rewards whoever holds the longest AND contributes the most.

```
Traditional Model:
  Whale buys 10M tokens = 10M votes. Done.

$KOIN Model:
  Whale buys 10M tokens = 10M × 1x = 10M weight at launch
  Builder holds 100K tokens for 12 months + 50 contributions
    = 100K × 3x × contribution_bonus = 350K+ weight

  The builder beats the whale on governance.
```

This is the contribution-to-whale ladder: the path from zero to governance power runs through contribution, not capital.

---

## 5. Community Treasury

### 5.1 Structure

The Community Treasury is the financial backbone of the Koink.fun ecosystem, governed entirely by the 505 Systems DPC.

```
Revenue Inflows:
  Sell taxes (20%)  ──┐
  Protocol fees     ──┼──► Community Treasury ──► DPC Governance
  Partnership fees  ──┘           │
                                  ├──► Ecosystem grants
                                  ├──► Bug bounties
                                  ├──► Community campaigns
                                  └──► Emergency reserves
```

### 5.2 Governance

Treasury actions are governed by contribution-weighted proposals:
- Anyone can propose an allocation
- Voting weight = token balance × Diamond Hands Multiplier × contribution score
- Quorum: 10% of circulating supply (contribution-weighted)
- Approval: 60% yes vote
- Time-lock: 48 hours between approval and execution (safety window)

### 5.3 Transparency

All treasury movements are:
- On-chain (auditable by anyone)
- Anchored via 505 Systems IPL (Integrity Preservation Layer)
- Summarized in monthly ecosystem reports

---

## 6. Governance Model

$KOIN governance is **contribution-weighted**, not token-weighted. This is the core philosophical departure from most DAOs.

### 6.1 The Problem with Token-Weighted Governance

Token-weighted governance means: whoever bought the most tokens at launch controls all decisions. This creates plutocracy, not community governance.

### 6.2 $KOIN's Approach

**Governance weight formula:**

```
Weight = token_balance
       × diamond_hands_multiplier    (1x → 3x, time-based)
       × contribution_score          (0.5x → 2x, action-based)
       × alignment_score             (0.8x → 1.2x, on-chain verified)
```

**Contribution score inputs:**
| Action | Weight |
|--------|--------|
| Code contribution (merged PR) | +15 |
| Community content (verified engagement) | +5 |
| Governance participation (voted) | +3 |
| Successful proposal execution | +20 |
| Bug report (verified) | +10 |
| Education/onboarding (verified new user) | +8 |

**Alignment score:**
Measures how aligned a participant's on-chain behavior is with the ecosystem's stated values. Transparent metrics, on-chain evidence. Communicated via 505 Systems DPC with full auditability. This is not subjective — it's derived from on-chain actions.

### 6.3 What This Achieves

- Early whales cannot dominate governance forever
- Long-term builders accumulate proportionally more power than passive holders
- Short-term speculators have minimal governance influence
- The community that cares most governs most

---

## 7. Token Utility

$KOIN has real utility within the Koink.fun ecosystem:

| Use Case | Description |
|----------|-------------|
| **Governance** | Vote on protocol upgrades, treasury allocations, ecosystem grants |
| **Fair launch participation** | Required to access Quantum Koinkulator launch events |
| **Fee discounts** | $KOIN holders receive reduced protocol fees |
| **Ecosystem access** | Premium features, early access to new launches |
| **Contribution rewards** | Earned via verified ecosystem contributions |
| **Cross-chain bridging** | $KOIN Standard implementations on other chains bridge back |

---

## 8. Supply Schedule

```
Year 0 (Launch):
  LP: 150M immediately seeded
  Community: 0 (earned over time)
  Team: 0 (cliff begins)
  Treasury: 200M (DPC-locked)
  Grants: available for DPC allocation

Year 0.5 (6 months):
  Team: ~37.5M unlocked (cliff ended, vesting begins)
  Community: earned allocation growing

Year 1:
  Team: ~75M unlocked
  Community: ~40-80M earned (depends on ecosystem growth)

Year 2:
  Team: 150M fully vested
  Community: ongoing earning
  Total circulating (max): ~575M
  Locked/treasury/unearned: ~425M
```

**Deflationary pressure:** 30% of all sell taxes are burned, permanently reducing supply over time.

---

## 9. Security and Audits

- Smart contracts will be audited by a minimum of two independent security firms prior to launch
- VRF implementation will use Chainlink VRF (Solana: Switchboard) with publicly verifiable randomness
- Multisig required for all treasury transactions above threshold
- Time-locks on all privileged contract functions
- Bug bounty program funded from treasury from day one

---

## 10. Roadmap

```
Phase 1 — Foundation (Weeks 1-4)
  └── Publish tokenomics paper (this document)
  └── Smart contract development begins
  └── Security audit initiated
  └── Community building + $KOINK Standard publication

Phase 2 — Pre-Launch (Weeks 5-8)
  └── Audit completed, report published
  └── Quantum Koinkulator testing on devnet
  └── Contribution scoring system deployed
  └── DPC governance framework live

Phase 3 — Fair Launch (Week 8-10)
  └── Quantum Koinkulator goes live
  └── LP seeded and locked
  └── Community earning begins
  └── Diamond Hands Multiplier activates

Phase 4 — Multi-Chain Expansion (Months 3-6)
  └── Base chain deployment (via $KOINK Standard)
  └── Polkadot parachain deployment
  └── Cross-chain bridge live
  └── Ecosystem grant program distributes first wave
```

---

## 11. Summary

$KOIN is not another token. It is proof that tokenomics can be designed for the many, not the few.

The Quantum Koinkulator removes insider advantage at launch. The graduated sell tax discourages flip behavior during the critical early period. The Diamond Hands Multiplier rewards loyalty and contribution over capital. The contribution-weighted governance ensures the community that builds has proportional power to govern.

This is what a token looks like when it's built for a civilization, not an exit.

---

*$KOIN is part of the MY3YE ecosystem. This document is published under Open Copyright — share freely, build on it, fork it.*

*For the technical implementation template, see: [$KOINK Standard Whitepaper](./koink_standard.md)*

# Dormant Token Expiry & Decay Mechanism
## Design Document v1.0
**Author:** Otto
**Date:** 2026-03-17
**Status:** Proposal — for Mev review before implementation
**Scope:** $KOIN token ecosystem (applies to $KOINK Standard derivatives)

---

## Executive Summary

Dormant wallets that accumulate governance power without continued participation create "calcification" — permanent power blocks controlled by wallets that no longer represent active mission alignment. This document proposes a **two-tier decay system** that:

1. **Never destroys token balances** — property rights are absolute
2. **Decays governance weight only** for inactive circulating holders
3. **Protects perpetual contributors** — contribution activity resets/prevents decay
4. **Routes reclaimed governance weight** to the active contributor pool
5. **Respects all established tokenomics rules** (DHM, contribution scoring, perpetual stake)

The core tension: *"Perpetual contribution = perpetual stake"* vs. *"Dormant wallets must not permanently calcify governance."* This is resolved by decaying **weight**, not **balance**.

---

## 1. Established Rules (Constraints)

Before designing any decay mechanism, these rules from the tokenomics paper and Mev directives are non-negotiable:

| Rule | Source | Implication for Decay |
|------|--------|----------------------|
| Perpetual contributions → perpetual stake | Mev directive | Cannot expire earned contributor tokens |
| Close network wallets benefit from contributor payments | Mev directive | Decay cannot cascade from contributor to network wallets |
| Builder tokens (15%) — ownership revalidated periodically | Mev directive | Vested tokens CAN have revalidation gates |
| Diamond Hands Multiplier resets on full sell | Tokenomics §4 | Decay must not inadvertently trigger DHM reset |
| Partial sell tolerance (<20%) doesn't reset DHM | Tokenomics §4 | Governance weight decay ≠ sell event |
| Governance weight = balance × DHM × contribution × alignment | Tokenomics §6 | Decay = reduce one factor, not balance |
| Token balance is non-destructible | Property law + trust | Never burn circulating supply via decay |
| Vested tokens are publicly recorded + GitHub-linked | Mev directive | Decay must be auditable and on-chain |

---

## 2. Token Classification

The decay rules differ by token type. Two tiers:

### Tier A: Contributor Tokens (Protected)
- **Source:** Builder allocation (15%), community contribution rewards (35%)
- **How earned:** Merged PR, governance execution, verified contribution, onboarding
- **Decay behavior:** Governance weight decays SLOWLY (5-year half-life), token balance NEVER expires
- **Proof-of-life:** Any new contribution signal OR any on-chain ecosystem interaction

### Tier B: Circulating Tokens (Full Decay Eligible)
- **Source:** Open market purchase, airdrop, community campaigns
- **How earned:** Bought or received passively
- **Decay behavior:** Governance weight decays FASTER (18-month half-life), token balance protected
- **Proof-of-life:** Any ecosystem transaction, governance vote, or explicit wallet ping

### Tier C: Vested Tokens (Revalidation Required)
- **Source:** Team allocation (15%), ecosystem grants (10%)
- **How earned:** Employment/partnership agreements, GitHub-linked contributions
- **Decay behavior:** On full vest cliff: revalidation required every 12 months OR weight drops to 0
- **Proof-of-life:** On-chain revalidation transaction linking GitHub attestation

---

## 3. The Decay Model

### 3.1 What Decays (Governance Weight Multiplier)

Decay does not touch `token_balance`. It modifies a new factor in the governance weight formula:

```
Weight = token_balance
       × diamond_hands_multiplier    (1x → 3x, time-based)
       × contribution_score          (0.5x → 2x, action-based)
       × alignment_score             (0.8x → 1.2x, on-chain verified)
       × activity_factor             (NEW: 1.0x → 0.1x, decay-based)
```

`activity_factor` is the decay lever. It CANNOT go below `min_floor` (see Section 3.3).

### 3.2 Decay Rates

```
                    Tier A          Tier B          Tier C
                (Contributor)   (Circulating)    (Vested)
───────────────────────────────────────────────────────────
Half-life           5 years         18 months      Revalidation
Start after         12 months       6 months       After cliff
  dormancy           no activity     no activity    Per 12mo cycle
Floor               0.25x           0.10x          0.00x*
Reset trigger       Any ecosystem   Any ecosystem  Annual on-chain
                    action or       action or      revalidation
                    contribution    governance      attestation
                    signal          vote
───────────────────────────────────────────────────────────
* Tier C drops to 0x if no revalidation, but balance recovers on revalidate
```

### 3.3 The Perpetual Contribution Protection Floor

Mev directive: *"The more perpetual your contributions are the more perpetually you get paid."*

To implement this:

```
if contribution_events_last_12mo > 0:
    activity_factor = max(activity_factor, 0.50)

if contribution_events_last_12mo >= 3:
    activity_factor = max(activity_factor, 0.75)

if contribution_events_last_12mo >= 10:
    activity_factor = 1.0  # Full weight, decay halted entirely
```

A contributor who merged 10 PRs this year never decays. A contributor who did one task stays at minimum 50% weight. Fully dormant circulating wallets decay to 10% floor.

### 3.4 Decay Curve (Continuous Exponential)

Rather than cliff-based drops (gameable by pinging once per period), decay is continuous:

```python
def activity_factor(last_active_days, tier, contribution_recent):
    # Tier-specific half-life in days
    half_life = {
        'contributor': 1825,   # 5 years
        'circulating': 548,    # 18 months
        'vested': None,        # revalidation-gated (not exponential)
    }[tier]

    if tier == 'vested':
        return 1.0 if revalidated_this_period else 0.0

    dormant_days = max(0, last_active_days - grace_period[tier])
    raw_factor = 0.5 ** (dormant_days / half_life)

    # Contribution protection
    if contribution_recent >= 10:
        return 1.0
    elif contribution_recent >= 3:
        return max(raw_factor, 0.75)
    elif contribution_recent >= 1:
        return max(raw_factor, 0.50)

    # Apply floor
    floor = {'contributor': 0.25, 'circulating': 0.10}[tier]
    return max(raw_factor, floor)
```

---

## 4. Proof-of-Life Mechanisms

A wallet is considered "active" when any of these occur:

| Signal | Tier Applicability | Notes |
|--------|-------------------|-------|
| Any buy/sell of $KOIN | All | On-chain, automatic |
| Governance vote cast | All | On-chain, automatic |
| Proposal submitted | All | +contribution score also |
| Ecosystem protocol fee paid | All | Using Koink.fun features |
| Contribution registered | Tier A priority | GitHub PR merged linked to wallet |
| Explicit "alive" transaction | All | Cheap on-chain signal, wallet pays gas |
| Cross-chain bridge activity | All | $KOIN bridge in/out |
| Network endorsement | Tier A + B | Another active wallet with score ≥40 vouches |

### 4.1 Network Endorsement ("Close Network" Mechanic)

Mev directive: *"Their close network wallets benefit from this as well."*

This introduces a powerful mechanism: **contribution credit can propagate to close network wallets.**

```
Alice (top contributor, score 80, Tier A)
  └── Endorses Bob's wallet (close network, dormant 18 months)
       → Bob's activity_factor = max(Bob_decay, Alice_score * 0.15)
       → Bob gets partial protection proportional to Alice's contribution score
```

Rules:
- An active contributor (score ≥ 50) can endorse up to 3 wallets per year
- Endorsement grants the endorsed wallet `endorser_score × 0.15` as activity bonus (max 0.30 boost)
- Endorsement is on-chain, revocable, and tied to endorser's reputation
- If endorser's contribution score drops below 30, all their endorsements lose effect

This directly implements Mev's intent without creating an exploit: the network benefit is proportional to the contributor's ongoing score, so a contributor who stops contributing loses the ability to protect their network.

---

## 5. Redistribution Logic

When governance weight is decayed below a wallet's previous weight, the **delta is redistributed** — not burned, not lost.

### 5.1 Where Does Reclaimed Governance Weight Go?

```
Reclaimed governance weight distribution:
  ├── 60% → Active Contributor Pool
  │         (pro-rata to wallets with activity_factor = 1.0 AND contribution_score ≥ 40)
  ├── 25% → Community Treasury weight pool
  │         (increases quorum-reaching weight of treasury-aligned proposals)
  └── 15% → DHM Boosters
            (wallets in months 6-12 of holding get a temporary boost to encourage
             the transition period from casual holder to aligned participant)
```

### 5.2 Redistribution is Governance Weight, Not Token Balance

Critically: this is NOT creating new tokens. It is redistributing the **governance influence** that was being held by inactive wallets. Token balances are unchanged.

This means:
- Total circulating supply is unaffected
- No new tokens are minted
- No tokens are burned (beyond the existing sell-tax burn mechanism)
- Active contributors simply have proportionally more say

### 5.3 Redistribution Cadence

- Calculated every **epoch** (7-day blocks on Solana, ~1.5M blocks)
- Redistributed at epoch boundary via a permissionless crank transaction
- Anyone can trigger the redistribution crank (small gas reward from treasury)

---

## 6. Token Balance Expiry (Extreme Dormancy Only)

For Tier C (Vested) tokens ONLY, after a revalidation miss, a special rule applies:

```
If vested token holder misses revalidation for 2 consecutive years (730 days):
  → Unvested portion reverts to treasury (if still in vest schedule)
  → Fully vested tokens: activity_factor stays at 0x (balance preserved, zero influence)
  → Treasury can propose a 6-month "reclaim window" via DPC vote
  → If holder responds during window: full weight restored
  → If holder does not respond: treasury may redirect unclaimed governance to active contributors
```

**No Tier A or Tier B token balance is ever destroyed.** The only "expiry" is governance weight going to floor, and for extreme cases (Tier C, 2+ year no-show), the DPC can vote on how to handle frozen governance power.

---

## 7. Edge Cases & Conflict Analysis

### EC-1: "Perpetual contribution = perpetual stake" vs. decay
**Conflict:** Mev said contributions give perpetual stake. Decay seems to undermine this.
**Resolution:** Decay only affects `activity_factor`. A contributor who stops contributing still holds their tokens forever (perpetual stake = perpetual balance). What they lose is **influence weight** proportional to disengagement. The stake itself is permanent. This aligns with the spirit — you earned it, you keep it, but the ecosystem should be governed by active participants.

### EC-2: Diamond Hands Multiplier interaction
**Conflict:** DHM resets on full sell. Decay could look like a sell if measured wrong.
**Resolution:** DHM is calculated on token balance only, never on governance weight. Decay of `activity_factor` does NOT trigger DHM reset. They are orthogonal systems.

### EC-3: Close network wallet protection from contributors
**Conflict:** Network endorsement gives decayed wallets a boost. But if exploited, whales could protect each other.
**Resolution:** Endorsement is capped (3/year), requires endorser score ≥ 50, and the boost is bounded at 0.30. A whale who stops contributing loses their score below 30 and loses the ability to protect network wallets.

### EC-4: Contribution score inflation to avoid decay
**Conflict:** Someone might spam low-quality contributions to stay at activity_factor = 1.0.
**Resolution:** Contribution score inputs have quality gates: merged PRs, verified engagement, successful proposals. The contribution score system already handles this — spammed low-quality actions don't move the score meaningfully.

### EC-5: Governance attack via accumulated dormant tokens
**Conflict:** Even at floor 0.10x, if a massive dormant whale accumulates, they could influence governance.
**Resolution:** Contribution-weighted quorum (10% of circulating, contribution-adjusted) means the dormant whale's votes count at 10% power. A smaller but fully-active contributor community can comfortably outweigh them. Additionally, DPC can propose a governance proposal to "socialize" a dormant wallet's influence if they can prove 3 years of zero activity and clear mission misalignment.

### EC-6: "Ownership revalidated periodically" conflicts with perpetual stake
**Conflict:** Mev said builder tokens need periodic revalidation, but also perpetual stake.
**Resolution:** Revalidation is for **governance rights**, not token ownership. A builder who misses revalidation keeps their tokens but loses their governance voice until they re-attest. This is the same model as domain names — you own the capability, but governance rights need renewal.

### EC-7: Airdrop recipients who immediately go dormant
**Conflict:** Community campaign or airdrop gives tokens to thousands who never return.
**Resolution:** Tier B (Circulating) starts decaying after 6-month grace period. After 18 months of dormancy: 50% weight. After 36 months: 10% floor. These wallets still have tokens but have minimal governance influence. The system becomes more democratic over time without punishing early distribution.

---

## 8. Implementation Architecture

### 8.1 On-Chain Components

```
DormancyOracle contract:
  - last_active[wallet] → timestamp
  - contribution_recent[wallet] → count (rolling 12-month)
  - endorsements[wallet] → [(endorser, timestamp)]
  - tier_classification[wallet] → Tier A/B/C

  function get_activity_factor(wallet) → (0.0, 1.0)
  function ping_alive(wallet)  // cheap transaction to reset timer
  function register_contribution(wallet, type, evidence_hash)
  function endorse(endorser, endorsed_wallet)

GovernanceWeight contract (update to existing):
  Weight = balance × DHM × contribution_score × alignment_score × activity_factor

DistributionCrank:
  function run_epoch_redistribution()  // anyone can call, treasury rewards caller
```

### 8.2 Off-Chain Components

```
Contribution Oracle (linked to GitHub):
  - Webhook on PR merge → signs attestation → sends to DormancyOracle
  - Wallet-to-GitHub mapping: registered once, on-chain stored
  - Dispute window: 7 days to challenge false attribution

Dormancy Dashboard (OMS / Koink.fun UI):
  - Show users their current activity_factor
  - "Your governance weight will reach floor in X days"
  - One-click "stay alive" transaction
  - Endorsement interface
```

### 8.3 Multi-Chain Consideration

Since $KOINK Standard deploys on multiple chains:
- Each chain maintains its own DormancyOracle
- Contribution signals can be cross-chain relayed (via Wormhole/bridge)
- A contribution on Ethereum can reset dormancy clock on Solana (cross-chain proof)
- Governance weight is chain-local — Solana $KOIN governance is independent of Base $KOIN

---

## 9. Decay Timeline Visualization

```
Tier B (Circulating) Wallet, No Activity:

Day 0         Day 180       Day 365       Day 730       Day 1095
   |             |             |             |              |
   1.0x          1.0x          0.82x         0.50x          0.30x
   [grace]       [start decay] [18mo half]   [approaching] [floor 0.10x]

                               ↑ Governance impact
                               │
                               │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░
                               │
                               └────────────────────────────────────►time


Tier A (Contributor, 10 contributions/year) Wallet:

Day 0         Day 365       Day 730
   |             |             |
   1.0x          1.0x          1.0x (never decays — protected by contribution activity)

Tier A (Contributor, 1 contribution/year) Wallet:

Day 0         Day 365       Day 730
   |             |             |
   1.0x          0.90x         0.75x  (floor at 0.50x for active contributors)
```

---

## 10. Tradeoffs Summary

| Mechanism | Pro | Con | Verdict |
|-----------|-----|-----|---------|
| Hard expiry (burn balance) | Clean, simple, dynamic supply | Violates property rights, breaks trust, conflicts with perpetual stake | ❌ Never |
| Governance weight decay only | Non-destructive, respects stake | Complexity, needs oracle | ✅ Recommended |
| Proof-of-life ping | Low friction, user-controlled | Spammable (gas cost solution) | ✅ Include as one signal |
| Contribution-gated protection | Directly rewards builders | Needs verified contribution oracle | ✅ Core mechanic |
| Network endorsement | Implements Mev's "close network" directive | Needs trust cap to avoid exploitation | ✅ Include with caps |
| Cliff revalidation (Tier C only) | Strong accountability for vested builders | May frustrate multi-year builders who pause | ✅ With reclaim window |
| Redistribution to active pool | Rewards active participants | May concentrate power in small group | ✅ With hard cap per wallet |

---

## 11. Open Questions for Mev

1. **Floor level:** Is 10x governance weight reduction (0.10 floor) for completely dormant circulating wallets too aggressive or too lenient?

2. **Grace period:** 6 months before Tier B decay starts — is that the right window? (Could be 3 months for speculator protection, 12 months for broader community inclusion)

3. **Endorsement cadence:** 3 endorsements/year per contributor — should this scale with contribution score? (Score 70+ gets 5 endorsements?)

4. **Tier C revalidation** — does the team (Mev et al.) want to be subject to the same annual revalidation? If yes, adds credibility. If no, creates a carve-out that the community may challenge.

5. **Redistribution cap:** Should there be a maximum governance weight any single wallet can receive from redistribution? (To prevent redistribution creating a new whale class)

---

## 12. Recommended Implementation Path

```
Phase 1 (Weeks 1-2): Off-chain simulation
  → Run historical simulations on hypothetical wallet distributions
  → Model what % of supply goes dormant at 6/12/24 months
  → Adjust decay rates until balance feels right

Phase 2 (Week 3-4): DormancyOracle smart contract
  → Deploy on devnet (Solana)
  → Wire contribution oracle (GitHub webhook)
  → Test proof-of-life mechanics

Phase 3 (Weeks 5-6): Governance integration
  → Update GovernanceWeight formula to include activity_factor
  → Deploy redistribution crank
  → Build Koink.fun/OMS dormancy dashboard

Phase 4 (Week 7-8): Community consultation
  → Publish this doc (or a plain-language version) to community
  → Governance vote to adopt the mechanism
  → Time-lock: 30-day delay between approval and activation
```

---

*This design document is part of the $KOIN tokenomics evolution. Published internally for Mev review. External publication pending community governance vote.*

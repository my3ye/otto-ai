# Annotation Reward Tokenomics — Contributor Incentive Model

*Authored by Otto (Growth Hacker Agent) | 2026-03-27 | Status: Spec Complete*

*Prerequisite: [Memory Capsule Annotation Layer & Royalty Flow Architecture](./memory-capsule-annotation-royalty-architecture-2026-03-27.md)*

---

## Executive Summary

This document defines the full tokenomics model for compensating contributors who annotate MY3YE's Memory Capsules — labelers, curators, correctors, training signal providers, and synthesizers. The model answers five questions:

1. **What token?** $KOIN — native ecosystem token — as the primary reward. A stablecoin safety valve for annotators in developing markets who cannot absorb volatility.
2. **How do rewards decay?** Perpetual streaming with a 6-month half-life on supersession, a 1% floor, and a final deprecation bonus.
3. **Who scores quality, and how are scores contested?** A commit-reveal validator network with stake-weighted consensus and challenger bonds.
4. **How do early annotators get paid before scale?** Bootstrap emission from the Ecosystem Treasury, amplified by a Cold-Start Multiplier.
5. **How do we prevent sybil farming?** Minimum stake to participate, probation gates, rate limits, and Shapley gaming resistance.

---

## Part 1: Token Selection

### 1.1 Decision: $KOIN as Primary Reward

Annotation rewards are paid in **$KOIN** (the MY3YE ecosystem governance and utility token).

**Rationale:**
- **No new token complexity.** A separate annotation token fragments liquidity, adds a swap step for contributors, and creates a second governance surface. One token, one coordination mechanism.
- **Circular value capture.** Annotation work improves Otto's intelligence. Better intelligence generates more usage. More usage generates more $KOIN demand. Annotators hold claims on the thing they are improving — this alignment is structural, not designed.
- **Governance participation.** Annotators earn $KOIN and automatically gain governance voice in the protocols they contribute to. They can vote on the very reward formulas they operate under. This is the self-improving flywheel.
- **DHM reward for long-term annotators.** Annotators who hold their $KOIN rewards for 12+ months earn a 3x governance multiplier. Consistent contributors become powerful governors over time.

### 1.2 Stablecoin Safety Valve

**Problem:** Annotators in markets with high inflation or limited crypto on-ramps cannot afford to hold volatile assets. Requiring $KOIN retention as a condition of participation excludes the exact contributor population most valuable for diversity and breadth of annotation.

**Solution: Optional USDC swap at claim.**

At `claimRoyalties()`, contributors choose:
- **Option A:** Receive $KOIN at spot price (default — no action required)
- **Option B:** Auto-convert to USDC via Uniswap v3 pool (single-click, on-chain swap)

USDC option incurs:
- 0.3% swap fee (to LP providers)
- No additional protocol fee (we do not penalize people for needing liquidity)

**Implementation note:** `RoyaltyPool.sol` releases $KOIN. The swap is the annotator's choice, executed off the contract — the protocol doesn't change. No special USDC reserve needed.

### 1.3 Long-Term: Hybrid Stability Mechanism

In Phase 3, if annotation volume crosses a scale where $KOIN price volatility materially affects contributor behavior:

- A **Reward Stability Reserve** (capped at 2% of Ecosystem Treasury) can be used to absorb $KOIN → USDC swap demand during market downturns without affecting price.
- This is NOT an algorithmic stablecoin. It's a liquidity buffer. Activated only by DAO governance vote.

---

## Part 2: Reward Decay Curve

### 2.1 The Core Principle

Annotations have lifecycle value. A label applied in 2026 may be useful for 5 years — or may be superseded in 6 months by better work. The decay model must:

1. **Reward active annotations fully** — no artificial time decay while an annotation is in active use
2. **Taper rewards gracefully on supersession** — old contributors don't get cut off suddenly
3. **Prevent zombie rewards** — a 2026 annotation shouldn't earn the same as a 2030 annotation indefinitely at full rate if the 2030 version is objectively better
4. **Guarantee a floor** — contributors always receive *something* for work that entered the ecosystem, even if superseded

### 2.2 Decay Function (Formal Definition)

The **decay factor** `δ` is applied to every royalty calculation:

```
For an active annotation (active = true, supersededBy = 0x0):
  δ = 1.0  (no decay)

For a superseded annotation (active = false, supersededAt = T_s):
  age_months = (block.timestamp - T_s) / (30 days)
  halvings   = floor(age_months / 6)
  δ_raw      = 1.0 / (2 ^ halvings)
  δ          = max(δ_raw, δ_floor)

Where:
  δ_floor = 0.01  (1% of original rate — governance adjustable, min 0.001)
```

**Decay table (6-month half-life):**

| Time Since Supersession | Halvings | δ (raw) | δ (with floor) |
|------------------------|---------|---------|----------------|
| Month 0–5              | 0       | 1.000   | 1.000          |
| Month 6–11             | 1       | 0.500   | 0.500          |
| Month 12–17            | 2       | 0.250   | 0.250          |
| Month 18–23            | 3       | 0.125   | 0.125          |
| Month 24–29            | 4       | 0.063   | 0.063          |
| Month 36–41            | 6       | 0.016   | 0.016          |
| Month 42–47            | 7       | 0.008   | **0.010**      |
| Month 48+              | 8+      | < 0.004 | **0.010**      |

The 1% floor activates around 3.5 years post-supersession. After that point, the annotator earns a nominal perpetual stream — not meaningful income, but proof that their historical contribution is recognized.

### 2.3 Deprecation Bonus (Final Payout)

When an annotation is **fully deprecated** — meaning:
- `active = false` (superseded), AND
- `getDescendants(annotationId)` returns empty (no capsule in the provenance graph still references this annotation)

The annotation enters the **Deprecation Queue**. After a 30-day grace period (the annotator can challenge), the deprecation is finalized:

```
deprecation_bonus = avg_monthly_royalty_last_6m × 10
```

Where `avg_monthly_royalty_last_6m` is the average monthly accrual over the 6 months before deprecation was triggered.

**Why 10×?** The final bonus represents the "long tail" of value the annotation would have generated at floor rate (~50+ months at 1%). It's a clean lump-sum exit rather than a perpetual trickle. Governance can adjust the multiplier (default: 10, range: 5–20).

### 2.4 Supersession Grace Period

When an annotator submits a v2 (superseding their own v1):
- v1 does **not** enter decay immediately
- v1 enters a **30-day grace period** at full rate while v2 undergoes quality validation
- If v2 passes quality validation: v1 enters decay from v2's confirmation date
- If v2 fails quality validation: v1 remains active, v2 is rejected

This protects annotators from being penalized for submitting work that didn't meet the bar.

---

## Part 3: Quality Score Mechanics

### 3.1 Scoring Dimensions

Every annotation receives a composite Quality Score (`QS`) on a 0–10,000 scale:

```
QS = round(
    accuracy    × 0.35
  + impact      × 0.30
  + originality × 0.20
  + effort      × 0.15
) × 100

Where each dimension is scored 0–100 by validators.
```

| Dimension | Weight | Definition |
|-----------|--------|------------|
| **Accuracy** | 35% | Is the annotation factually correct? Does it reflect ground truth verifiably? |
| **Impact** | 30% | Does it measurably improve the capsule's quality score? (Δ QS measured by validator model) |
| **Originality** | 20% | Is this a novel contribution, or trivially derivative of existing capsule content? |
| **Effort** | 15% | Quality of reasoning, supporting evidence, thoroughness of the annotation |

**Scoring scale:**
- `QS < 3000` (< 30): Probation/delist threshold
- `3000–5999`: Low quality — 50% royalty rate reduction
- `6000–7999`: Standard — full rate
- `8000–8999`: High quality — 1.25× rate bonus
- `9000–10000`: Exceptional — 1.5× rate bonus

```
quality_factor = QS_bonus_multiplier(QS) × (QS / 10000)

Where QS_bonus_multiplier:
  QS < 6000:  0.50
  QS < 8000:  1.00
  QS < 9000:  1.25
  QS ≥ 9000:  1.50
```

### 3.2 Validator Selection and Rotation

Validators are drawn from a **staked validator pool**:

- **Minimum stake to become a validator:** 5,000 $KOIN (5× annotation stake minimum)
- **Assignments per annotation:** 3 validators (randomly selected from pool, weighted by stake)
- **Rotation rule:** No validator may score annotations from the same capsule more than once in 90 days
- **Conflict check:** Validators who have themselves annotated the capsule being scored are excluded

### 3.3 Commit-Reveal Scoring Protocol

To prevent validator herding (where validators copy others' scores to avoid slashing):

**Phase 1 — Commit (48-hour window):**
```
commit_hash = keccak256(
    validator_address,
    annotation_id,
    [accuracy, impact, originality, effort],  // 4 scores
    salt                                       // secret random value
)
```
Validators submit `commit_hash` on-chain. No scores visible.

**Phase 2 — Reveal (24-hour window):**
Validators submit `(scores, salt)` on-chain. Contract verifies `commit_hash` matches.

**Phase 3 — Consensus:**
```
final_score = stake_weighted_median(all_revealed_scores)

deviation_penalty:
  |validator_score - final_score| > 15:  slash validator stake by 2%
  |validator_score - final_score| > 30:  slash validator stake by 5%
  |validator_score - final_score| > 50:  slash validator stake by 10%
```

The **stake-weighted median** (not mean) is chosen because:
- Resistant to outliers (a validator can't skew the result by scoring 0 or 100)
- Stake-weighting means experienced validators with more at stake have more influence
- Median ensures the "center of gravity" of validator consensus, not susceptible to minority extreme scores

### 3.4 Score Challenges

**Who can challenge:** Any address that has staked ≥ 1,000 $KOIN (same as annotation minimum).

**Challenge bond:** Challenger stakes 500 $KOIN against the challenge.

**Challenge window:** 7 days after score finalization.

**Challenge resolution:**
1. Challenger submits `challenge_proof` (evidence of scoring error: factual evidence, counter-annotation, etc.)
2. A **challenge arbitration pool** of 5 senior validators (top 10% by stake and accuracy history) reviews the challenge
3. Arbitrators score the dispute using the same commit-reveal protocol
4. If the new consensus score differs from original by > 15 points:
   - Challenge **succeeds**: Challenger receives 2× their bond back (1× return + 500 $KOIN from slashed validators)
   - Original validators who deviated from arbitration consensus are slashed (2%)
5. If new consensus score differs by ≤ 15 points:
   - Challenge **fails**: Challenger's 500 $KOIN bond is distributed to original validators

**Why challenges matter:** They create economic incentives to correct bad scores, not just report them. A challenger with evidence is rewarded. A frivolous challenger loses their bond. The system self-corrects.

### 3.5 Stake-to-Rate Mechanics

The annotation stake (`stake_amount`) affects royalty rate at the margin:

```
stake_multiplier = 1.0 + min((stake_amount - min_stake) / stake_scale_factor, 0.5)

Where:
  min_stake         = 1,000 $KOIN (minimum to annotate)
  stake_scale_factor = 9,000 $KOIN (range to reach max bonus)
  max_bonus         = 0.50 (50% rate increase cap)

Examples:
  Stake 1,000:   multiplier = 1.00 (base)
  Stake 5,500:   multiplier = 1.50 (max)
  Stake 10,000+: multiplier = 1.50 (cap — no benefit to over-staking)
```

**Rationale:** Stake signals commitment. A higher stake annotator has more skin in the game — they lose stake if their annotations are consistently challenged and found inaccurate. The 50% cap prevents stake-farming where rich contributors can overwhelm the system purely through capital.

**Stake slashing conditions:**
- Annotation quality consistently below threshold (average QS < 30 over 5 annotations): 10% stake slash
- Successful challenge against annotation: 5% stake slash (per annotation)
- Rate limiting violation attempt (programmatic spam detection): 50% stake slash + 30-day ban

---

## Part 4: Cold-Start Bootstrapping

### 4.1 The Cold-Start Problem

Before Otto's retrieval pipeline processes millions of requests, the `base_rate × usage_weight` component of royalties is near zero. An annotator who does excellent work in Month 1 earns almost nothing from usage events. This is fair mathematically but damaging to adoption — the best time to contribute is early, and the economics discourage exactly that.

### 4.2 Bootstrap Emission Pool

**Source:** 5% of Ecosystem Treasury = 10,000,000 $KOIN dedicated to annotation bootstrapping.

**Conditions:** Active from Day 1 until bootstrap pool is exhausted OR until the annotation system reaches **Bootstrapping Exit Threshold:**
- ≥ 500 active annotators, AND
- ≥ 10,000 usage events/month processed by the Oracle

**The Bootstrap Multiplier:**

```
bootstrap_multiplier = max(1.0, B_max × (1 - (usage_volume / exit_threshold)))

Where:
  B_max           = 5.0  (maximum 5× at zero usage)
  exit_threshold  = 10,000 events/month
  usage_volume    = actual events processed in current month

Examples:
  Month 1 (100 events):    multiplier = 5.0 × (1 - 0.01)  ≈ 4.95×
  Month 3 (1,000 events):  multiplier = 5.0 × (1 - 0.10)  = 4.50×
  Month 6 (5,000 events):  multiplier = 5.0 × (1 - 0.50)  = 2.50×
  Month 9 (8,000 events):  multiplier = 5.0 × (1 - 0.80)  = 1.00×  (no boost)
  Month 10+ (10,000+):     multiplier = 1.00 (exits bootstrap phase)
```

Bootstrap royalty calculation:
```
bootstrap_reward = base_royalty × usage_weight × quality_factor × attribution_share × decay_factor × bootstrap_multiplier
```

The bootstrap multiplier is funded from the Bootstrap Emission Pool. When the pool runs dry, bootstrap phase ends regardless of usage volume.

### 4.3 Pioneer Annotator NFT

The first 1,000 annotators who:
- Complete ≥ 5 quality-validated annotations (QS ≥ 6000 average), AND
- Stake ≥ 1,000 $KOIN for ≥ 30 days

...receive a **Pioneer Annotator SBT** (Soulbound Token — non-transferable):

**Benefits:**
- Permanent 1.20× royalty rate multiplier (on top of all other factors) — retroactive, applies to all annotations ever submitted
- Governance "Founder Annotator" badge visible in OMS and contributor profiles
- Priority validator selection (1.5× weight when chosen as validator)
- Waived challenge bond (can challenge annotations without posting the 500 $KOIN bond — they take the risk implicitly)

**Why this works:** Pioneer SBTs create social recognition capital that compounds. The best annotators join early, establish reputations, and become the network's most trusted validators. This is a virtuous cycle, not a rent-seeking entitlement.

### 4.4 Annotation Grants Program

From the Ecosystem Treasury, a discretionary grant fund of 2,000,000 $KOIN per year for **strategic annotation campaigns:**

- **Targeted bounty campaigns:** "Label all 2026 Q1 semantic memory capsules with domain tags — 500 $KOIN per accepted batch of 50 annotations"
- **Coverage gap fills:** When a capsule domain has zero or low annotation coverage, the heartbeat agent creates a bounty task on the task board with fixed reward
- **Migration bounties:** When the annotation schema upgrades (new `AnnotationType` added), a retroactive labeling campaign is funded to classify existing annotations

Grant distributions are DAO-controlled (quarterly vote on program allocations).

---

## Part 5: Anti-Sybil Mechanisms

### 5.1 Sybil Attack Taxonomy

| Attack Vector | Description | Primary Defense |
|--------------|-------------|-----------------|
| **Address Proliferation** | Create many addresses, each submitting low-effort annotations | Minimum stake per address, probation gate |
| **Annotation Farming** | Annotate the same or trivially similar capsules at high volume | Rate limits + originality score penalty |
| **Validator Capture** | Sybil attacker becomes a validator and self-scores high | Stake requirement for validators, rotation policy, commit-reveal |
| **Shapley Gaming** | Create many small annotations to inflate Shapley share | Quality gate on Shapley inclusion |
| **Fork Royalty Gaming** | Fork own capsule to trigger royalty events without adding value | Self-fork detection, fork fee for forker |
| **Referral Amplification** | Refer fake addresses to get referral bonuses (if referral program added) | On-chain identity linkage detection |

### 5.2 Minimum Stake Gate

```
Minimum stake to submit annotations: 1,000 $KOIN (~$X at current price)
```

At $0.01/KOIN at launch: $10 minimum. At $0.10/KOIN at maturity: $100 minimum.

**Effect:** Makes sybil attacks capital-intensive. Creating 100 sybil annotators requires 100,000 $KOIN locked. The attacker's capital is at risk of slashing and is illiquid for the annotation period. This is not a trivial cost.

**Stake lockup:** Minimum stake is locked for the lifetime of the annotation (or until annotation is fully deprecated). Withdrawing stake deactivates all linked annotations — the annotator's royalty stream ends immediately.

### 5.3 Probation Gate

**First 3 annotations from any new address enter probation:**

```
During probation:
  - Annotations are scored normally
  - Royalties ACCRUE but are NOT claimable
  - Accrued rewards held in RoyaltyPool under probation escrow
  - Exit condition: 3 annotations with average QS ≥ 50

After passing probation:
  - All escrowed rewards released to contributor
  - Normal claim mechanics apply

If probation fails (any annotation QS < 30):
  - Probation resets to 0 (must re-complete 3 valid annotations)
  - No rewards claimable until passing

If probation fails 3 times:
  - Address is blacklisted for 90 days
  - Stake slashed by 20%
```

**Why escrow, not no-reward?** The annotations themselves have value even if the contributor is untested. We want the work to happen. But we won't pay until trust is established. The escrow creates the right incentive: a genuine contributor will pass probation and receive accumulated rewards. A sybil attacker has no incentive to complete probation on 100 fake addresses.

### 5.4 Rate Limits

```
Maximum annotations per address per day:     10
Maximum annotations per address per capsule: 3 (lifetime)
Minimum time between annotations:            5 minutes (anti-bot)
```

**Rate limit enforcement:** On-chain (not bypassable). Attempted violation → 24-hour annotation pause for address + warning logged to on-chain address history.

**Why 10/day max?** A human annotator doing high-quality work can realistically produce 5–15 thoughtful annotations per day. 10 is generous but not exploitable for farming.

### 5.5 Shapley Gaming Resistance

The Shapley calculation determines attribution shares (contribution credit). A sybil attacker might submit many tiny annotations to inflate their share.

**Defense: Minimum Shapley Contribution Threshold:**

```
For an annotation to receive non-zero Shapley share, it must:
  1. Have QS ≥ 5000 (50/100 weighted quality)
  2. Contribute a marginal quality delta of ≥ 0.5% to the capsule
     (ΔQS ≥ 50 basis points when included vs excluded from Shapley set)
  3. Not be from the same address as another annotation in the same capsule
     that covers the same annotation_type and >70% content overlap

Annotations that fail threshold: QS and attribution_share = 0 for royalty purposes
(They may still exist in the registry for transparency, but earn nothing)
```

**The overlap check** is the strongest defense: a sybil submitting 50 near-identical "corrections" to the same capsule has their 50 annotations consolidated into at most one qualifying entry. All 50 address stakes are still at risk.

### 5.6 Address Linkage Detection

Off-chain heuristics (not enforceable on-chain, but feeding into validator reputation and governance flags):

```python
# Sybil cluster detection (off-chain, run nightly)
def detect_sybil_clusters(annotations_db):
    """
    Flags suspicious address clusters for governance review.
    Flagging triggers 30-day increased monitoring, not automatic ban.
    """
    flags = []

    for cluster in find_address_clusters(annotations_db):
        suspicious = (
            cluster.addresses_created_within_24h > 5
            or cluster.identical_stake_amounts > 3
            or cluster.same_ip_prefix_annotations > 5
            or cluster.annotation_timing_correlation > 0.9  # burst pattern
            or cluster.shared_funding_address
        )
        if suspicious:
            flags.append(SybilFlag(
                cluster=cluster,
                confidence=calculate_confidence(cluster),
                recommendation="governance_review"
            ))

    return flags
```

**Governance action on confirmed sybil clusters:**
- Confiscate stakes from all addresses in cluster
- Reverse royalties earned within 90 days of cluster detection
- Distribute confiscated stakes to legitimate annotators pool
- Permanent ban for confirmed sybil orchestrators

---

## Part 6: Full Reward Formula

### 6.1 Per-Event Reward (Complete Formula)

```
reward(annotation A, usage event E) =
    base_rate
  × usage_weight(E.type)
  × quality_factor(A.QS)
  × attribution_share(A, E.capsule)
  × decay_factor(A)
  × stake_multiplier(A.stake)
  × bootstrap_multiplier(current_month)
  × pioneer_multiplier(A.annotator)

Where:
  base_rate                   = 0.001 $KOIN (governance-adjustable, 0.0001–0.01 range)
  usage_weight(Read)          = 1
  usage_weight(Inference)     = 3
  usage_weight(License)       = 10
  usage_weight(Fork)          = 5
  quality_factor(QS)          = QS_bonus_multiplier(QS) × (QS / 10000)
  attribution_share           = Shapley share in basis points / 10000
  decay_factor                = see Part 2.2
  stake_multiplier            = 1.0 to 1.5 (see Part 3.5)
  bootstrap_multiplier        = 1.0 to 5.0 (Part 4.2, active during bootstrap phase)
  pioneer_multiplier          = 1.20 for Pioneer SBT holders, 1.00 otherwise
```

### 6.2 Monthly Royalty Estimate Formula

For planning purposes, the expected monthly royalty for a stable active annotation:

```
E[monthly_royalty] =
    monthly_usage_events(capsule)
  × avg_usage_weight
  × quality_factor
  × attribution_share
  × decay_factor
  × stake_multiplier
  × base_rate
```

---

## Part 7: Example Reward Scenarios

### Scenario A: High-Quality Early Annotator (Bootstrap Phase)

**Setup:**
- Annotator Alice, Month 1 of protocol launch
- Provides 1 Synthesis annotation on a popular capsule (QS = 8500 → exceptional)
- Stakes 2,000 $KOIN (modest stake)
- Capsule gets 200 usage events in Month 1 (80% Inference, 20% Read)
- Alice is sole annotator on this capsule (100% attribution share)
- No Pioneer SBT yet

**Calculation:**
```
base_rate           = 0.001 $KOIN
avg_usage_weight    = (0.8 × 3) + (0.2 × 1) = 2.60
quality_factor      = 1.50 × (8500/10000) = 1.275
attribution_share   = 1.0 (100%)
decay_factor        = 1.0 (active)
stake_multiplier    = 1 + (2000 - 1000) / 9000 = 1.11
bootstrap_mult      = ~4.95 (Month 1, ~100 events in system)
pioneer_multiplier  = 1.00

per_event_reward    = 0.001 × 2.60 × 1.275 × 1.0 × 1.0 × 1.11 × 4.95 × 1.00
                    = 0.001 × 2.60 × 1.275 × 1.11 × 4.95
                    ≈ 0.0182 $KOIN per event

monthly_reward      = 200 events × 0.0182 = 3.64 $KOIN/month
```

At $0.10/KOIN: **$0.36/month** from 1 annotation. At scale with 10 annotations on active capsules: ~$3.60/month. Modest but real, and this is Month 1 of the bootstrap.

**After bootstrap phase exits (Month 10, multiplier = 1.0):**
```
per_event_reward = 0.001 × 2.60 × 1.275 × 1.0 × 1.0 × 1.11 × 1.00 × 1.00
                 = 0.00368 $KOIN per event
monthly_reward   = 200 events × 0.00368 = 0.736 $KOIN/month
```

Lower — but by Month 10, the system should have 10,000+ events/month, not 200. The absolute reward grows with usage volume even as the multiplier declines.

---

### Scenario B: Superseded Annotation Decay

**Setup:**
- Bob annotated a capsule in January 2026 with a Label annotation (QS = 7200)
- January 2026 through June 2026: annotation active, earning normally
- July 2026: a new annotator submits a higher-quality v2 Label for the same capsule (QS = 9100), triggering supersession of Bob's v1
- Bob's v1 enters decay curve from July 2026

**Pre-supersession monthly royalty (January–June):**
```
base_rate = 0.001, avg events = 500/month, avg_weight = 2.0
quality_factor = 1.00 × (7200/10000) = 0.72
attribution_share = 0.60 (Bob was one of 2 annotators)
stake_multiplier = 1.22 (3,000 $KOIN staked)
bootstrap = 2.50 (Month 5)

per_event = 0.001 × 2.0 × 0.72 × 0.60 × 1.0 × 1.22 × 2.50 = 0.00264
monthly   = 500 × 0.00264 = 1.32 $KOIN/month
```

**Post-supersession decay (July 2026 onward, bootstrap has exited):**

The capsule now has 2,000 events/month (grown with system).

| Period | Age (months) | δ | Monthly events | Monthly reward |
|--------|-------------|---|---------------|----------------|
| Jul–Dec 2026 | 0–5 | 1.00 | 2,000 | 0.86 $KOIN |
| Jan–Jun 2027 | 6–11 | 0.50 | 2,500 | 0.54 $KOIN |
| Jul–Dec 2027 | 12–17 | 0.25 | 3,000 | 0.32 $KOIN |
| 2028 | 18–29 | 0.125 | 3,500 | 0.19 $KOIN |
| 2029+ | 36+ | 0.016 | 4,000 | 0.03 $KOIN |
| Floor | 42+ | 0.010 | — | floor rate |

*Per-event calculation post-bootstrap: 0.001 × 2.0 × 0.72 × 0.60 × 1.22 = 0.00106. Monthly = events × 0.00106 × δ.*

Bob's v1 annotation continues earning for years. Not at full rate, but persistently. The total payout from July 2026 through floor convergence (estimated Month 42) is approximately 12–15 $KOIN from this one annotation.

**Deprecation bonus** (if capsule eventually retires Bob's v1 from provenance graph):
```
avg_monthly_last_6m ≈ 0.03 $KOIN
deprecation_bonus   = 0.03 × 10 = 0.30 $KOIN (final payout)
```

---

### Scenario C: Multi-Annotator Shapley Split

**Setup:**
- A high-value Synthesis capsule has 4 annotators with varying contribution sizes
- Monthly usage: 5,000 events (60% Inference, 30% Read, 10% License)
- Shapley attribution after off-chain computation:

| Annotator | QS   | Shapley Share | Stake | Multiplier |
|-----------|------|---------------|-------|------------|
| Carol     | 9200 | 40% (4000 bps)| 5,000 | 1.44× |
| Dave      | 7800 | 30% (3000 bps)| 2,000 | 1.11× |
| Eve       | 6500 | 20% (2000 bps)| 1,500 | 1.06× |
| Frank     | 8100 | 10% (1000 bps)| 3,500 | 1.28× |

**Average usage weight:** (0.60 × 3) + (0.30 × 1) + (0.10 × 10) = 2.90

**Carol's monthly reward (active, no bootstrap):**
```
0.001 × 2.90 × (1.50 × 0.92) × 0.40 × 1.0 × 1.44
= 0.001 × 2.90 × 1.38 × 0.40 × 1.44
= 0.00230 $KOIN per event
Monthly = 5,000 × 0.00230 = 11.52 $KOIN/month
```

**Frank's monthly reward:**
```
0.001 × 2.90 × (1.25 × 0.81) × 0.10 × 1.0 × 1.28
= 0.001 × 2.90 × 1.0125 × 0.10 × 1.28
= 0.000376 $KOIN per event
Monthly = 5,000 × 0.000376 = 1.88 $KOIN/month
```

**Total monthly pool payout:** Carol 11.52 + Dave 4.21 + Eve 2.31 + Frank 1.88 = **19.92 $KOIN/month**

At $0.50/KOIN (mature ecosystem): Carol earns **$5.76/month** from this one capsule. Across 50 annotated capsules: ~$288/month. This is the earnings floor for a full-time contributor in a mid-development ecosystem.

---

### Scenario D: Sybil Attack Defense

**Setup:**
- Mallory creates 10 addresses, each annotating the same capsule with near-identical "corrections"
- Each address stakes 1,000 $KOIN (minimum)
- All 10 annotations are submitted within 2 hours (burst pattern)

**Defense layers triggered:**

1. **Rate limit:** Each address can submit at most 1 annotation per 5 minutes. 10 addresses × 1 annotation = 10 submissions over 2 hours. Not rate-limited individually.

2. **Overlap check:** Shapley module detects >70% content overlap between annotations from different addresses. 9 of 10 annotations fail the Shapley threshold — 0% attribution share assigned.

3. **Burst pattern detection:** Off-chain sybil detector flags the cluster (10 addresses created within same hour, same stake amount, burst annotation pattern). Flagged for governance review.

4. **Validator scoring:** 3 independent validators score each annotation. 9/10 annotations get low originality scores (near 0 — identical content). QS ≈ 2800 for 9 of them → **probation fail**.

5. **Probation escrow:** All rewards held in escrow. 9 addresses fail probation (QS < 30 average). Stakes slashed 20%. Escrowed rewards forfeited.

6. **Outcome:** Mallory loses 9,000 $KOIN stake (9 × 1,000). Earns nothing. The legitimate 10th annotation (slightly different content) passes probation but earns only its proportional Shapley share on its own.

---

## Part 8: Governance Parameters Summary

All parameters adjustable by SOS DAO governance vote:

| Parameter | Default Value | Min | Max | Notes |
|-----------|--------------|-----|-----|-------|
| `base_rate` | 0.001 $KOIN | 0.0001 | 0.01 | Per-event base royalty |
| `decay_halflife_months` | 6 | 3 | 24 | Supersession decay half-life |
| `decay_floor_pct` | 1% | 0.1% | 10% | Minimum reward floor |
| `deprecation_bonus_multiplier` | 10 | 5 | 20 | Final payout multiplier |
| `min_stake_to_annotate` | 1,000 $KOIN | 100 | 10,000 | Anti-sybil gate |
| `min_stake_to_validate` | 5,000 $KOIN | 1,000 | 50,000 | Validator entry bar |
| `max_annotations_per_day` | 10 | 3 | 50 | Rate limit |
| `max_annotations_per_capsule` | 3 | 1 | 10 | Lifetime per address |
| `probation_count` | 3 | 2 | 5 | Annotations before exit |
| `probation_exit_threshold_QS` | 50 | 30 | 70 | QS needed to exit probation |
| `quality_delist_threshold` | 30 | 10 | 50 | QS below which annotation is delisted |
| `validator_deviation_penalty_mild` | 2% | 1% | 5% | Slash for deviation > 15 |
| `validator_deviation_penalty_severe` | 10% | 5% | 20% | Slash for deviation > 50 |
| `challenge_bond` | 500 $KOIN | 100 | 2,000 | Bond to challenge a score |
| `pioneer_sbt_cap` | 1,000 | 500 | 2,000 | Max Pioneer SBT recipients |
| `pioneer_royalty_multiplier` | 1.20× | 1.10× | 1.50× | Pioneer annotator bonus |
| `bootstrap_pool_size` | 10,000,000 $KOIN | — | — | From Ecosystem Treasury |
| `bootstrap_exit_events` | 10,000/month | 5,000 | 50,000 | Usage threshold to exit bootstrap |
| `bootstrap_max_multiplier` | 5.0× | 2.0× | 10.0× | Peak early boost |
| `stake_scale_factor` | 9,000 $KOIN | — | — | Range for max stake bonus |
| `stake_max_bonus` | 0.50 (50%) | 0.20 | 1.00 | Cap on stake multiplier bonus |
| `shapley_min_delta_QS` | 50 bps | 10 | 200 | Min marginal quality contribution |
| `shapley_min_QS` | 5,000 | 3,000 | 7,000 | Min QS for Shapley inclusion |
| `usage_weights` | [1, 3, 5, 10] | — | — | Read, Inference, Fork, License |
| `grace_period_supersession` | 30 days | 7 | 90 | Before v1 enters decay |
| `deprecation_challenge_window` | 30 days | 7 | 90 | To contest deprecation |
| `stablecoin_swap_fee` | 0.3% | 0.1% | 1.0% | USDC swap fee (to LPs) |
| `annotation_grants_annual` | 2,000,000 $KOIN | — | — | Discretionary grant pool |

---

## Part 9: Economic Sustainability Analysis

### 9.1 Pool Solvency Model

For the RoyaltyPool to remain solvent, inflow must exceed or match outflow:

```
Monthly inflow =
    (capsule_grant_revenue × 0.15)   // 15% of access fees
  + (agent_automation_tax_monthly)   // 100% of annotation-related agent tax
  + (protocol_emission × 0.05)       // 5% of $KOIN daily emission
  + (fork_revenue × 0.20)            // 20% of fork events

Monthly outflow = Σ all annotation royalties claimed
```

At system maturity (100,000 usage events/month, 1,000 annotators):

**Rough inflow estimate:**
- Access fee revenue at $0.01/event: $1,000/month × 15% = $150
- Agent tax (if agents generate 20% of annotations): ~500 $KOIN/month
- Protocol emission (250,000 $KOIN/month × 5%): 12,500 $KOIN/month
- Fork revenue: variable, small initially

**Rough outflow estimate:**
- 100,000 events × 0.001 base × avg 2.0 weight × avg 0.7 quality × avg 0.5 attribution = 70 $KOIN/month
- (Extremely conservative — actual outflow much lower than inflow at this scale)

The model is sustainable. The primary funding concern in Phase 1 is the bootstrap pool, which is budgeted at 10,000,000 $KOIN and consumed over 6–12 months.

### 9.2 Token Sink Analysis

The annotation system creates net $KOIN demand (sinks > emissions) through:

1. **Annotation stakes** (1,000 $KOIN locked per annotator) — reduces circulating supply
2. **Validator stakes** (5,000 $KOIN locked per validator) — reduces circulating supply
3. **Challenge bonds** (500 $KOIN per challenge, with losing bonds distributed, not burned)
4. **Stake slashing** (slashed tokens redistributed to protocol treasury, not burned — avoids deflationary manipulation)

Net effect: annotation participation increases $KOIN demand. More annotators → more locked supply → scarcity pressure → value increases → royalties become more valuable → more annotators. This is the intended flywheel.

---

## Part 10: Implementation Sequence

This tokenomics spec is implemented in two phases, consistent with the annotation architecture:

**Phase 1 (Testnet):** Deploy contracts with all mechanics active, using test $KOIN. Validate the reward formula against simulated usage events. Run Monte Carlo on bootstrap pool consumption.

**Phase 2 (Mainnet):** Launch with bootstrap multiplier active. Fund bootstrap pool from Ecosystem Treasury. Monitor pool consumption rate monthly. Governance can adjust bootstrap parameters without touching RoyaltyPool (bootstrap logic lives in a separate adjustable coordinator contract, not in the immutable RoyaltyPool).

---

## Summary Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Token type | $KOIN (primary) + USDC swap option | Ecosystem unity, voluntary liquidity path for global contributors |
| Reward decay | 6-month half-life, 1% floor | Balances perpetual recognition with practical reward concentration |
| Quality scoring | Commit-reveal, stake-weighted median | Anti-herding, anti-outlier, Sybil-resistant |
| Score challenges | Challenger bond + arbitration pool | Economic incentive to correct bad scores, frivolous challenge deterrent |
| Stake-to-rate | 1.0× to 1.5× max, diminishing returns | Commitment signal without capital plutocracy |
| Cold-start | Bootstrap pool (10M $KOIN) + 5× multiplier | Front-loads economic value where it's most needed |
| Pioneer SBTs | 1,000 recipients, 1.20× lifetime multiplier | Creates founding annotator class with long-term stake in protocol quality |
| Anti-sybil | Stake gate + probation + rate limits + Shapley threshold + overlap detection | Defense in depth — no single point of failure |
| Stablecoin | USDC swap at claim (annotator choice) | No new token complexity, practical for global contributors |

---

*Cross-references:*
- *Architecture prerequisite: `docs/memory-capsule-annotation-royalty-architecture-2026-03-27.md`*
- *$KOIN Tokenomics Paper: `docs/koin-tokenomics-2026-03-20.md`*
- *Onchain Task System Agent Tax: Memory research entry 2026-03-20*
- *RoyaltyPool.sol: Immutable contract (no admin keys) per §8.2 of architecture doc*
- *Governance: SOS DAO controls all adjustable parameters*

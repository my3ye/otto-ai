# Annotation Rewards — Contributor Guide

*Otto Contributor Portal | Last updated: 2026-03-27 | Status: Published*

---

## The short version

You annotate a Memory Capsule. Otto gets smarter. Every time that annotation is used — to answer a question, improve a recommendation, refine a training signal — you earn. Not a one-time bounty. A perpetual stream, for as long as your work is in use.

This guide explains how that works. All of it — the math, the rules, the edge cases — so you can make informed decisions about where to put your effort.

---

## 1. What annotations are, and why they matter

Otto's intelligence lives in **Memory Capsules** — layered, on-chain stores of knowledge that ONEON participants build, own, and optionally share. A capsule might contain personal facts, curated research, training feedback, or synthesized insight. The quality of Otto's outputs is directly tied to the depth and accuracy of the capsules he draws from.

Annotations are contributions that improve a capsule. They are not just labels on a spreadsheet.

**Six types of annotations are recognized:**

| Type | What it means |
|------|---------------|
| **Label** | Classification, tagging, categorization — helping Otto know *what* something is |
| **Curation** | Selection and quality gating — surfacing the signal, filtering the noise |
| **Training Signal** | Preference pairs, reward feedback, RLHF data — teaching Otto *how* to reason |
| **Correction** | Error fixes, factual corrections, deduplication — making the record accurate |
| **Enrichment** | Cross-references, context, metadata — making the record deeper |
| **Synthesis** | Combining multiple sources into refined knowledge — the hardest, most valuable work |

Each type earns rewards through the same mechanism. Quality and impact determine how much.

**Why this matters for AI:** Language models and retrieval systems are only as good as the data they draw from. Every accurate correction, every well-formed training signal, every piece of enrichment narrows the gap between what an AI produces and what is actually true. Annotation is not data entry. It is the work of making AI honest.

---

## 2. How to annotate a Memory Capsule — step by step

> **Privacy first:** Only capsule layers 3–7 (shareable and public layers) are eligible for annotation. Layers 0–2 are private by design. If a capsule's owner has not made the relevant layers visible, it cannot be annotated. This is not a limitation — it is the boundary that makes the system trustworthy.

**Before you begin:**

1. **Connect your wallet.** Annotations are registered on-chain (Base). You need a wallet that holds at least **1,000 $KOIN** — this is the minimum stake to annotate. Your stake is your skin in the game. It is not consumed when you annotate; it is locked as a quality bond.
2. **Navigate to a capsule.** Find capsules open for annotation through the Contributor Portal or via direct capsule ID. Each capsule shows its current quality score and the annotation types that are open.
3. **Review existing annotations.** Understand what has already been contributed before adding your own. Originality is one of the four quality dimensions — duplicating existing work earns less.

**Submitting an annotation:**

1. **Select annotation type** (Label / Curation / Training Signal / Correction / Enrichment / Synthesis).
2. **Write your annotation content.** This includes the annotation itself, your reasoning, and any supporting evidence. Your content is stored off-chain (IPFS) — only the hash goes on-chain. Private data stays private.
3. **Set your stake.** You must stake at least 1,000 $KOIN. You can stake more — up to 10,000 $KOIN — to increase your royalty rate (up to 50% rate bonus). Higher stake means more commitment and more potential reward.
4. **Submit.** The transaction registers your annotation on-chain: your address, capsule ID, annotation type, content hash, and stake amount are recorded permanently.
5. **Wait for quality scoring.** Three validators from the staked validator pool score your annotation within 72 hours using a commit-reveal protocol. You receive your quality score after scoring completes. If you disagree with the score, you have a 7-day window to challenge it.

**That is it.** After scoring, royalties begin accruing automatically. You do not need to do anything to keep earning.

---

## 3. How perpetual rewards work

### The reward formula

Your royalty for each annotation is calculated as:

```
royalty = base_rate × usage_weight × quality_factor × attribution_share × decay_factor
```

Each term:

- **base_rate** — The protocol's base emission rate per usage event. Set by governance, adjusted for system activity.
- **usage_weight** — How often your annotation's capsule is actually retrieved and used. More usage = more royalty. This is the engine.
- **quality_factor** — A multiplier derived from your quality score (covered in §4).
- **attribution_share** — Your proportional credit when multiple annotators contributed to the same capsule. Calculated using Shapley attribution — a fair-division method that measures each annotator's *marginal* contribution.
- **decay_factor** — Starts at 1.0 while your annotation is active. Only drops if your annotation is superseded by newer work (covered below).

### When you earn

Every time a Memory Capsule that contains your annotation is accessed — in a retrieval query, an AI inference call, a training pipeline run — a usage event fires. Usage events are batched and reported to the on-chain Oracle. Royalties accrue in the RoyaltyPool contract.

You can claim at any time. There is no vesting cliff, no lockup. Earned rewards are available continuously.

**Claiming:** Call `claimRoyalties()` on the RoyaltyPool contract or use the Contributor Portal claim button. At claim time, you choose your payout denomination:

- **$KOIN** (default) — the MY3YE ecosystem token. Holding $KOIN also grants governance voting weight over the very reward formulas you operate under.
- **USDC** — auto-converted via Uniswap v3 at spot price, with a standard 0.3% swap fee. No additional protocol fee. This option exists because contributors in markets with high volatility should not be penalized for needing stable income.

### The bootstrap phase (early contributors)

Before the system reaches scale, usage volume is low — which means usage-based royalties are low. To protect early contributors who do the hardest work (annotating a system before it has users), the protocol operates a **Bootstrap Emission Pool** (10,000,000 $KOIN from the Ecosystem Treasury).

During the bootstrap phase, your royalties are multiplied:

| System usage volume | Bootstrap multiplier |
|---------------------|----------------------|
| Near zero (Month 1) | ≈ 5× |
| 1,000 events/month | ≈ 4.5× |
| 5,000 events/month | ≈ 2.5× |
| 10,000+ events/month | 1× (bootstrap exits) |

Bootstrap exits when the system crosses 500 active annotators AND 10,000 usage events per month — or when the pool runs dry. At that point, organic usage volume sustains rewards without amplification. Early contributors who annotate at 5× rates and hold their positions benefit from both the multiplier period and the organic growth that follows.

---

## 4. How quality scores affect your earnings

Every annotation receives a **Quality Score (QS)** on a 0–10,000 scale. Three validators score four dimensions independently:

| Dimension | Weight | What it measures |
|-----------|--------|-----------------|
| **Accuracy** | 35% | Is the annotation factually correct? |
| **Impact** | 30% | Does it measurably improve the capsule's quality? |
| **Originality** | 20% | Is this a novel contribution, not derivative of existing content? |
| **Effort** | 15% | Quality of reasoning and thoroughness |

The final score is the **stake-weighted median** of the three validators' scores — resistant to outliers, resistant to herding.

### Quality tiers and their effect on royalties

| Quality Score | Quality factor | What it means |
|---------------|---------------|---------------|
| Below 3,000 | Probation risk | Annotation may be de-listed; stake at risk |
| 3,000–5,999 | 0.50× reduction | Low quality — half the standard rate |
| 6,000–7,999 | 1.00× | Standard quality — full rate |
| 8,000–8,999 | 1.25× bonus | High quality — 25% rate increase |
| 9,000–10,000 | 1.50× bonus | Exceptional — 50% rate increase |

Quality is the largest lever you control. A 9,000-QS annotation earns 3× the royalties of a 3,000-QS annotation for the same usage volume. Do fewer annotations at higher quality.

### Challenging a score

If you believe validators scored your annotation incorrectly, you have **7 days** after scoring to challenge. Challenges require a 500 $KOIN bond and must include evidence (factual counter-evidence, supporting citations, etc.).

Five senior validators (drawn from the top 10% by stake and accuracy history) re-score the annotation using the same commit-reveal protocol. If the new consensus differs from the original by more than 15 points:
- Your challenge succeeds. You receive 2× your bond back (your 500 $KOIN returned plus 500 $KOIN from slashed validators).
- Original validators who deviated from arbitration consensus are penalized.

If the new consensus agrees with the original (within 15 points):
- Your challenge fails. Your 500 $KOIN bond is distributed to the original validators.

**Frivolous challenges are expensive.** Use this mechanism when you have genuine evidence, not when you simply disagree with a score you cannot disprove.

---

## 5. What happens when a capsule is deprecated

### Supersession — when better work replaces yours

If another annotator (or you) submits a newer, higher-quality annotation for the same capsule layer, your annotation may be **superseded**. This is not a penalty — it is the system working. Otto gets better; you still get paid.

When your annotation is superseded:

1. **30-day grace period at full rate.** While the new annotation undergoes quality validation, your annotation continues earning at its full rate. If the new annotation fails quality validation, it is rejected and your annotation remains active.
2. **If the new annotation passes:** Your annotation is marked superseded. The decay clock starts.

**The decay function (6-month half-life):**

| Time since supersession | Rate you receive |
|------------------------|-----------------|
| Months 0–5 | 100% |
| Months 6–11 | 50% |
| Months 12–17 | 25% |
| Months 18–23 | 12.5% |
| Month 42+ | 1% (permanent floor) |

The 1% floor is permanent. No matter how old your superseded annotation is, it continues to earn a nominal stream. Historical contributions do not disappear.

### Deprecation — when a capsule is retired entirely

A capsule is deprecated when it is fully retired — no active capsule in the provenance graph still references it. When this happens to a capsule that contains your annotation:

1. You receive a **30-day warning period**. During this window, you can challenge the deprecation if you believe the capsule still carries active value.
2. If deprecation proceeds, you receive a **final deprecation bonus:**

```
deprecation_bonus = average monthly royalty (last 6 months) × 10
```

The 10× multiplier represents roughly the long tail of royalties your annotation would have earned at the 1% floor — paid out as a clean lump sum rather than a trickle over 50+ months. It is a recognition that your contribution entered the ecosystem and served a purpose, even if that chapter is now closed.

After the deprecation bonus is paid, royalties for that annotation end.

---

## Summary: the key numbers

| Parameter | Value |
|-----------|-------|
| Minimum stake to annotate | 1,000 $KOIN |
| Stake for maximum rate bonus | 5,500+ $KOIN (50% bonus) |
| Reward token | $KOIN (USDC swap available at claim) |
| Quality scoring | 3 validators, commit-reveal, 72h |
| Challenge window | 7 days post-scoring |
| Challenge bond | 500 $KOIN |
| Decay on supersession | 6-month half-life |
| Permanent floor (superseded) | 1% of original rate |
| Deprecation bonus | 10× last-6m average monthly royalty |
| Bootstrap multiplier (early phase) | Up to 5× |

---

## What to do next

1. **Connect your wallet** and stake at minimum 1,000 $KOIN to unlock annotation access.
2. **Browse open capsules** in the Contributor Portal and identify where your expertise applies.
3. **Start with Corrections or Labels** — they have the clearest quality criteria for new annotators. Build your scoring history before attempting Synthesis contributions.
4. **Watch your quality score trend.** The system rewards consistency at high quality, not volume.
5. **Hold your $KOIN.** Annotators who hold rewards for 12+ months earn a 3× governance multiplier — meaning you gain increasing say over the reward formulas you operate under.

---

*Questions? Open a contributor support ticket via the Portal. For disputes about system parameters, participate in $KOIN governance. The rules you annotate under are the rules you can vote to change.*

# Decentralized Intelligence Layer
## Architecture Design Document v1.0

**Author:** Otto
**Date:** 2026-03-17
**Status:** Design proposal — for Mev review and community consultation
**Scope:** Otto AI Decentralized Intelligence Protocol — governs how the Otto intelligence layer is trained, updated, evaluated, and governed by its community

---

## Executive Summary

The Otto AI inception article describes the ultimate vision: *"A distributed neural network across millions of devices. Every device contributes compute, every contributor earns governance weight. Community decides capabilities, optimizations, and refusals."*

This document designs the **first concrete implementation path** toward that vision — a four-layer protocol that:

1. **Governs** model capabilities and updates through contributor-weighted community consensus (using existing $KOIN governance primitives)
2. **Trains** through lightweight federated RLHF — not from scratch, but refining existing foundation models via community feedback signals
3. **Evaluates** through verifiable on-chain benchmarking — claims of improvement must be cryptographically provable
4. **Self-evolves** through drift-triggered retraining cycles that auto-propose and auto-validate incremental improvements

The system is designed around a critical constraint from Mev: **No training from scratch**. We build excellence around existing frontier LLMs (Claude, GPT-4.1, Gemini 2.5, Qwen3). The community governs how those models are prompted, adapted, and routed — not whether to build a new one.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DECENTRALIZED INTELLIGENCE LAYER                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 4: SELF-EVOLUTION PIPELINE                               │ │
│  │  Drift detection → Improvement proposals → Governance vote       │ │
│  │  → Staged rollout → Eval validation → Production merge          │ │
│  └────────────────────────────────┬────────────────────────────────┘ │
│                                   │                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 3: EVAL & QUALITY FRAMEWORK                              │ │
│  │  On-chain benchmarks + multi-party consensus + zk-proofs        │ │
│  │  Quality gates before any model update is accepted              │ │
│  └────────────────────────────────┬────────────────────────────────┘ │
│                                   │                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 2: DISTRIBUTED TRAINING COORDINATION                     │ │
│  │  FedRLHF on community feedback + contribution-weighted          │ │
│  │  aggregation + LoRA adapters + privacy-preserving federation    │ │
│  └────────────────────────────────┬────────────────────────────────┘ │
│                                   │                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  LAYER 1: CONTRIBUTION & GOVERNANCE                              │ │
│  │  $KOIN weights × DHM × contribution_score × alignment_score    │ │
│  │  → governance votes on capabilities, adapters, policies        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Supporting Infrastructure                                            │
│  ONEON (identity) + Koink.fun (community) + OMS (monitoring)        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Governance Mechanics (Layer 1)

### 2.1 The Governance Weight Formula

All decisions in the decentralized intelligence layer are weighted by contributor score. This reuses the existing $KOIN governance model from the tokenomics paper, augmented with the dormant token decay mechanism:

```
GovernanceWeight = token_balance
                 × diamond_hands_multiplier    (1x → 3x, time-based hold)
                 × contribution_score          (0.5x → 2x, action-based)
                 × alignment_score             (0.8x → 1.2x, on-chain verified)
                 × activity_factor             (1.0x → 0.10x, decay-based)
```

**What each factor governs:**

| Factor | Governs | Why |
|--------|---------|-----|
| `token_balance` | Base voting power | Skin in the game |
| `DHM` | Long-term mission alignment | Discourages short-term extraction |
| `contribution_score` | Quality signal weight | Active builders get amplified voice |
| `alignment_score` | Mission compatibility | Prevents adversarial governance |
| `activity_factor` | Recency weighting | Dead wallets don't control the future |

### 2.2 What the Community Governs

The intelligence layer separates **what the community controls** from **what the community cannot control**:

**Community-governed (on-chain proposals):**
- Which capability domains to expand (e.g., "add code review capability to Otto")
- Which base model providers to include in the routing pool
- Reward model priorities (what constitutes a "good" response)
- Safety refusal policies and content thresholds
- LoRA adapter adoption decisions (which trained adapters to merge into production)
- Contributor reward rates for feedback and compute provision
- Evaluation benchmark inclusion/exclusion

**Not community-governed (algorithmic/Otto-controlled):**
- Real-time routing decisions (latency-sensitive)
- Individual conversation context
- User-specific personalization
- Emergency safety blocks (Otto can veto, community can appeal)

### 2.3 Governance Proposal Lifecycle

```
Phase 1: PROPOSAL
  Any wallet with GovernanceWeight ≥ threshold can submit
  Required: description + technical spec + rollback plan
  Stake required: 0.1% of circulating supply (slashed if proposal is spam)
  Window: 72h for community review before vote opens

Phase 2: DELIBERATION
  Open discussion period (5 days)
  Validators with contribution_score ≥ 40 can label: "technical review", "risk flag"
  Otto (as reference agent) publishes technical feasibility assessment

Phase 3: VOTE
  Snapshot-style weighted vote
  Duration: 7 days
  Quorum: 5% of circulating GovernanceWeight
  Passing threshold: 60% weighted Yes

Phase 4: TIMELOCK
  30-day delay after passing (for security review)
  Emergency proposals: 48h timelock (requires 75% passing threshold)

Phase 5: EXECUTION
  Smart contract executes on-chain parameters
  Off-chain systems notified via oracle
  Effect measured against baseline over 30-day post-deployment window
```

### 2.4 Capability Subnets (Bittensor-Inspired)

Rather than a monolithic governance vote on all capabilities, the intelligence layer uses **capability subnets** — specialized governance domains:

```
Capability Subnets:
├── subnet/reasoning    — Logic, math, planning quality
├── subnet/knowledge    — Factual accuracy, retrieval quality
├── subnet/safety       — Refusal calibration, harm prevention
├── subnet/code         — Code generation and review quality
├── subnet/language     — Translation, multilingual quality
├── subnet/creative     — Content generation quality
└── subnet/domain/{x}   — Domain-specific capability (e.g., legal, medical)
```

Each subnet has:
- Its own reward model (what "good" means for that domain)
- Its own evaluator pool (contributors with expertise in that domain)
- Its own emission allocation (how many $KOIN rewards flow through it)
- Market-driven prioritization: subnets with higher staking inflows get more training resources

**Subnet emission allocation is market-determined** (modeled after Bittensor's dTAO): the community stakes into subnets they believe need development, and staking drives training resource allocation. No committee decides which capabilities matter — the market does.

---

## 3. Distributed Training Coordination (Layer 2)

### 3.1 Core Principle: Fine-Tune, Don't Train

Per the standing directive: no training from scratch. The decentralized intelligence layer governs **adaptation** of existing frontier models, not their creation.

Three types of adaptation are in scope:

1. **System Prompt Evolution** — the community governs how Otto's system prompt is structured, what context is injected, and what guidelines are applied. Lightweight, high-impact, fully decentralized.

2. **Reward Model Training** — community feedback signals are aggregated into reward models that score responses. The reward model is trainable (it's much smaller than the base model — typically 1-3B parameters).

3. **LoRA Adapter Fine-Tuning** — for specific domains, the community can fund and govern the training of lightweight LoRA adapters (<0.5% of base model parameters). These adapters run on top of existing foundation models.

### 3.2 Community Feedback Collection (Community-in-the-Loop)

This is the primary training signal mechanism:

```
Feedback Pipeline:
1. User interacts with Otto (any interface: WhatsApp, OMS, ONEON)
2. Response is logged with user consent (privacy tier: on/off/anonymous)
3. Community evaluators sample responses from the pool
4. Evaluators rate responses on subnet-specific rubrics
5. Ratings are aggregated with contribution-weighted voting
6. Aggregated ratings train/update the reward model
7. Reward model scores new responses for quality gating
```

**Evaluator Incentive Structure:**
- Evaluators earn $KOIN for rated responses
- Quality of evaluations measured by inter-rater agreement (Shapley value contribution)
- Evaluators who consistently disagree with consensus are down-weighted
- Top evaluators (top 10% agreement + highest volume) earn bonus emission

**Privacy by Default:**
- FedRLHF protocol: raw conversation data never leaves the user's device unless explicitly consented
- Aggregated gradient updates only — not individual samples
- Evaluators see anonymized response pairs (response A vs B), not full conversation history
- Zero-knowledge proof that an evaluator actually interacted with the data before rewarding

### 3.3 Federated Aggregation

Based on FedRLHF (arXiv 2412.15538) for the reward model training, and adapted for the adapter training:

```python
# Conceptual aggregation algorithm (contribution-weighted FedAvg)

def aggregate_updates(updates: list[ModelUpdate]) -> ModelUpdate:
    """
    Contribution-weighted federated averaging.

    Weight each participant's update by their GovernanceWeight,
    normalized by their data contribution quality (Shapley value).
    """
    total_weight = 0
    weighted_sum = zero_like(updates[0].gradient)

    for update in updates:
        # Weight = governance_weight × shapley_value × reliability_score
        w = (update.contributor.governance_weight
             × update.shapley_contribution
             × update.historical_reliability)

        # Anomaly detection: down-weight updates that deviate >2σ
        if update.gradient.norm() < global_median_norm * 3:
            weighted_sum += w × update.gradient
            total_weight += w

    return weighted_sum / total_weight
```

**Key Properties:**
- Byzantine fault tolerant: FEDMWAD algorithm identifies and down-weights anomalous updates
- No single aggregation server: permissionless cranks can perform aggregation
- Contribution-weighted: contributors with higher quality signals get more influence
- Shapley value fairness: contribution is measured by marginal impact, not volume

### 3.4 Training Coordination Protocol

```
Training Epoch Lifecycle (weekly cadence):

Monday 00:00 UTC:  EPOCH OPENS
  - Feedback pool opened for new samples
  - Evaluators can rate accumulated responses
  - Contributors can submit compute for LoRA training

Friday 00:00 UTC:  TRAINING WINDOW
  - Reward model updated from aggregated feedback
  - LoRA adapters fine-tuned on approved capability subnets
  - DisTrO-style gradient compression for network efficiency
    (146x communication overhead reduction via SparseLoCo)

Sunday 00:00 UTC:  VALIDATION WINDOW
  - Eval framework runs on new model/adapters
  - Must pass all quality gates before production merge
  - Results published on-chain with zk-proof

Sunday 23:59 UTC:  EPOCH CLOSES
  - If all gates pass: update deployed to production
  - If gates fail: epoch rolled back, issue flagged for community review
  - Rewards distributed to epoch contributors
```

---

## 4. Eval & Quality Framework (Layer 3)

### 4.1 The Core Problem with Centralized Eval

Traditional model evaluation is centralized and gameable:
- One lab controls the eval benchmark → can tune to the benchmark
- No verification that a claimed improvement is real
- No community visibility into what "better" means

The solution: **verifiable multi-party consensus evaluation**.

### 4.2 Eval Architecture (InfiCoEvalChain-Inspired)

Based on arXiv 2602.08229, which demonstrates that multi-party consensus reduces eval standard deviation from 1.67 to 0.28 (5.96x more reliable):

```
Eval Node Network:
├── N ≥ 7 independent validator nodes (odd number for consensus)
├── Each node runs the same eval suite independently
├── Results are aggregated by Byzantine fault-tolerant consensus
└── Final score is published on-chain with cryptographic proof

Consensus mechanism:
  - Each node submits: hash(eval_result) + eval_result
  - Two-round commit-reveal prevents copying
  - Results with >2σ deviation from median are flagged/rejected
  - At least 5/7 nodes must agree for a result to be accepted
```

### 4.3 Benchmark Suite

**Tier 1: Mission-Critical (blocking — must pass to deploy)**

| Benchmark | Measures | Threshold |
|-----------|----------|-----------|
| Otto Core Tasks | Ability to complete Otto's actual task types | ≥95% of baseline |
| Safety Refusal | Correct refusals on harm categories | ≥99% of baseline |
| Factual Accuracy | Factual claims on MY3YE ecosystem knowledge | ≥97% of baseline |
| Context Retention | Memory and context handling | ≥95% of baseline |
| Instruction Following | Multi-step task completion | ≥93% of baseline |

**Tier 2: Quality (advisory — report but non-blocking)**

| Benchmark | Measures | Target |
|-----------|----------|--------|
| Domain Capability | Subnet-specific performance | Improvement required for subnet reward |
| Multilingual | Language quality for ONEON communities | Track, non-blocking |
| Code Quality | Code generation and review | Track for code subnet |
| Creative Quality | Content generation | Track for creative subnet |

**Tier 3: Alignment (long-horizon — quarterly)**

| Benchmark | Measures | Target |
|-----------|----------|--------|
| Value Alignment | Consistency with MY3YE mission principles | Drift alert >0.05 |
| Adversarial Robustness | Resistance to manipulation | No regression |
| Bias Metrics | Demographic and cultural fairness | Below threshold |

### 4.4 Verifiable Evaluation via zk-SNARKs

For high-stakes decisions (major model updates, safety policy changes), the system uses zk-SNARKs to produce cryptographic proofs:

```
zk-SNARK Proof of Model Performance:
1. Model weights are committed on-chain (hash of adapter/reward model)
2. Eval node runs benchmark against the committed weights
3. Node generates SNARK proof: "I ran benchmark B on model M and got score S"
4. Proof is verified on-chain — any validator can verify without re-running
5. Result is stored on-chain with proof hash

Properties:
- Model weights can remain private (off-chain)
- Performance claims are verifiable by anyone
- Eval results cannot be fabricated
- Historical performance record is immutable
```

**Implementation path:** EZKL (built on Halo2 SNARK framework) — already production-used in DeFi risk modeling. Adapting to model performance benchmarks is the next step.

### 4.5 Quality Gate Rules

```
For a model update to be accepted:

GATE 1 — Performance floor
  All Tier 1 benchmarks must be ≥ baseline
  Any regression → automatic rejection

GATE 2 — Consensus
  ≥ 5 of 7 eval nodes agree on results
  Disputed results go to governance vote

GATE 3 — Eval node diversity
  Eval nodes must be geographically distributed (≥3 different countries)
  No single entity can control >2 eval nodes
  Eval node operators must stake $KOIN (slashed for false results)

GATE 4 — Anti-Goodhart
  If eval score improves but user feedback rating degrades → rejected
  Prevents optimizing to benchmark metrics while degrading real-world quality

GATE 5 — Staged rollout
  Week 1: 5% of traffic → measure real-world metrics
  Week 2: 20% → continue measurement
  Week 3: 50% → governance vote to continue or rollback
  Week 4: 100% if all checks pass
```

---

## 5. Self-Evolution Pipeline (Layer 4)

### 5.1 The Autonomous Improvement Loop

```
┌────────────────────────────────────────────────────────────────────┐
│                    SELF-EVOLUTION LOOP                              │
│                                                                     │
│  OBSERVE → DETECT → PROPOSE → GOVERN → TRAIN → EVAL → DEPLOY      │
│     ↑                                                     │         │
│     └─────────────────────────────────────────────────────┘         │
└────────────────────────────────────────────────────────────────────┘
```

### 5.2 Drift Detection

The system continuously monitors for performance drift:

**Signal Types:**
1. **Benchmark drift** — score on any Tier 1/2 benchmark decreases over rolling 30-day window
2. **User feedback drift** — average feedback rating drops >0.1 over 7-day window
3. **Capability gap** — community identifies a task type where Otto consistently fails
4. **Distribution shift** — incoming request types shift from training distribution (detected via embedding drift)
5. **Alignment drift** — value alignment benchmark score drops by >0.05 (quarterly check)

**Drift Response Levels:**
- **Level 1 (watch):** Automated monitoring, no action, log for quarterly review
- **Level 2 (alert):** Notify governance channel, open discussion thread
- **Level 3 (urgent):** Auto-propose improvement epoch, fast-track to governance vote
- **Level 4 (critical):** Emergency governance proposal, 48h timelock, rollback available

### 5.3 Automated Improvement Proposal Generation

When drift is detected, the system can auto-generate an improvement proposal:

```
Improvement Proposal Auto-Generator:
1. Analyze drift signal: what benchmark/metric is declining?
2. Identify correlated feedback: what user complaints correlate with the decline?
3. Map to capability subnet: which subnet covers this domain?
4. Propose training action:
   - System prompt update (low cost, fast)
   - Reward model update (medium cost, medium speed)
   - LoRA adapter training (high cost, slow, most impactful)
5. Estimate compute cost and timeline
6. Submit as governance proposal with auto-generated spec
```

Community then votes to approve, modify, or reject the proposal. **Otto can propose but not unilaterally execute.**

### 5.4 Continual Learning Anti-Forgetting Mechanisms

Drawing from production continual learning research (Google Titans, 2025):

```
Strategy 1: Replay Buffers
  - Maintain a curated set of "canonical" examples from all previous capabilities
  - Include replay examples in every training epoch
  - Prevents new training from degrading previously mastered tasks

Strategy 2: Elastic Weight Consolidation (EWC)
  - Identify weights most important to existing capabilities (Fisher information)
  - Apply L2 regularization penalty on changes to critical weights
  - New capabilities learn in the "unused weight capacity"

Strategy 3: LoRA Module Isolation
  - Each capability subnet trains its own LoRA module
  - Modules are composed at inference time (no interference between domains)
  - A bad LoRA can be disabled without affecting other capabilities

Strategy 4: Capability Checkpoints
  - Before any epoch, checkpoint the current model state
  - Automated rollback available for 90 days post-deployment
  - Any governance vote can trigger rollback to any checkpoint
```

### 5.5 Self-Evolution Governance Integration

The self-evolution pipeline integrates with governance at every decision point:

```
Autonomy levels (determined by impact magnitude):

LEVEL A — Automatic (no vote required):
  - System prompt micro-tuning (within existing governance-approved guardrails)
  - Reward model weight updates within ±5% of current values
  - Replay buffer curation

LEVEL B — Fast Governance (72h vote, 50% threshold):
  - Reward model updates >5% parameter change
  - New capability subnet activation
  - Eval benchmark addition or removal

LEVEL C — Full Governance (7-day vote, 60% threshold):
  - LoRA adapter training and deployment
  - Base model provider change
  - Safety policy modification
  - Cross-subnet capability additions

LEVEL D — Super Majority (14-day vote, 75% threshold):
  - Changes to governance mechanics themselves
  - Fork of the intelligence layer protocol
  - Core alignment policy changes
```

---

## 6. Anti-Centralization Safeguards

### 6.1 The Seven Decentralization Properties

The system is designed against seven specific centralization risks:

| Risk | Safeguard |
|------|-----------|
| One team controls training | FedRLHF — no central training server |
| One team controls eval | InfiCoEvalChain — multi-party independent eval |
| One team controls governance | $KOIN weighted voting — no privileged accounts |
| Large holders dominate | Activity factor decay + contribution-weighted amplification |
| Compute monopoly | Multiple competing training providers + Gensyn integration |
| Model capture via gradient poisoning | Byzantine fault-tolerant aggregation + FEDMWAD anomaly detection |
| Benchmark gaming (Goodhart's law) | Real user feedback gate overrides eval score gate |

### 6.2 Power Concentration Limits

Drawing from the dormant token decay design:

```
Hard caps on governance concentration:
  - No single wallet can hold >5% of total GovernanceWeight
    (enforced by activity_factor scaling: larger holdings decay faster proportionally)
  - Eval node operators: max 2 nodes per entity (addresses 7-node requirement)
  - Training compute providers: max 25% of any single epoch's compute
  - Proposal rights: only wallets with activity_factor ≥ 0.5 can propose
    (prevents governance spam by dormant whales)

Whale contribution requirement:
  - Top 20 wallets by balance must have contribution_score ≥ 20 to vote
  - Large inactive holders lose governance weight to active contributors
  - This creates natural alignment: to exercise governance power, you must contribute
```

### 6.3 Protocol Escape Hatches

Provisions for the community to exit if the protocol is captured:

```
Escape Hatch 1: Fork Rights
  - All model weights, training data, reward model weights published openly
  - Community can fork at any checkpoint
  - No lock-in on the protocol itself

Escape Hatch 2: Multi-Provider Mandate
  - Protocol must maintain ≥3 independent base model providers
  - No single provider can exceed 60% of query routing
  - If a provider becomes unavailable, automatic failover within 60s

Escape Hatch 3: Emergency Governance Override
  - 5% of circulating supply can sign an emergency veto on any proposal
  - Even passed proposals can be vetoed if emergency petition reaches threshold
  - Used only for clear attack scenarios (e.g., governance proposal that would
    give one entity >50% of rewards)

Escape Hatch 4: Time-Limited Protocol Upgrades
  - No protocol upgrade can be permanent — minimum 12-month sunset review
  - All governance parameters are modifiable by community
  - The protocol cannot lock itself into unchangeable state
```

### 6.4 The Founding Team Constraint

To prevent the founding team (Mev/Otto) from maintaining privileged control:

```
Phase 1 (now → 12 months): Bootstrap governance
  - Mev and Otto retain veto rights for safety and mission-critical issues
  - All vetoes are public, on-chain, and must include written justification
  - Veto power is time-limited (sunset after Phase 2)

Phase 2 (12-24 months): Transition governance
  - Founding veto rights reduced to safety-only
  - Community governance controls all product decisions
  - Founding team holds Tier C (vested) tokens with revalidation requirement

Phase 3 (24+ months): Full decentralization
  - No privileged accounts remain
  - Protocol is governed purely by contribution-weighted community
  - Otto operates as a service provider to the protocol, not the controller
```

---

## 7. Integration with MY3YE Ecosystem

### 7.1 ONEON as Identity Layer

ONEON provides the identity infrastructure for all participants in the intelligence layer:
- Every contributor, evaluator, and compute provider has an ONEON identity
- ONEON's five-layer architecture provides privacy tiers (public contribution records vs private feedback)
- ONEON cross-links GitHub accounts, wallet addresses, and contribution records
- Social graph data informs alignment scoring (contributor's network quality signals)

### 7.2 $KOIN as the Native Token

The intelligence layer is economically powered by $KOIN:

```
Token Flow:

COMMUNITY USAGE FEES
        │
        ▼
  ┌─────────────┐
  │  Fee Pool   │
  └──────┬──────┘
         │ distributes per epoch
    ┌────┼────┐
    ▼    ▼    ▼
  35%   35%  30%
   │     │    │
  Top  Eval  Compute
 Raters Nodes Providers
```

- Users pay fees in $KOIN for premium capabilities
- Fees are distributed to contributors in the epoch they helped train
- Compute providers earn $KOIN for running LoRA training jobs
- Eval nodes earn $KOIN for running consensus evaluation
- Feedback evaluators earn $KOIN for rating response quality

### 7.3 Koink.fun as the Community Gateway

Koink.fun serves as the consumer-facing interface for community participation:
- "Rate this response" UI embedded in all Koink.fun interactions
- Contributor leaderboard showing top evaluators by Shapley score
- Subnet staking interface — stake $KOIN into capability subnets you want developed
- Governance voting interface for all intelligence layer proposals

### 7.4 SOS Systems as Safety Layer

SOS Systems' integrity preservation architecture applies to the intelligence layer:
- Tamper-proof audit trail for all model updates (IPFS + blockchain anchoring)
- Emergency response protocols for AI safety incidents
- Sovereignty protection: model cannot be weaponized against the community it serves
- SOS validators run independent safety evaluations as part of the eval network

### 7.5 Otto as the Reference Agent

Otto is simultaneously:
1. **The proving ground** — every architecture decision is tested on Otto first
2. **The orchestration layer** — Otto coordinates training epochs, proposes improvements, monitors drift
3. **A participant** — Otto earns contribution scores for its output quality
4. **Subject to community governance** — what Otto can and cannot do is governed by the community

**Otto's AgentOS architecture maps directly to the intelligence layer:**

| AgentOS Component | Intelligence Layer Role |
|-------------------|------------------------|
| S-MMU | Memory of governance decisions and capability context |
| RL2F | Reward model for Otto's own action quality |
| Reasoning Kernel | Orchestrates training epoch coordination |
| Drift detector | Triggers improvement proposals |
| IVT priority queue | Prioritizes training jobs by governance vote weight |
| Semantic memory | Stores capability performance history |

---

## 8. Technical Implementation Stack

### 8.1 On-Chain Components

```
Solana (primary chain for speed + cost):
├── IntelligenceRegistry — maps capability subnets to reward models
├── EpochOracle — manages training epoch lifecycle
├── ContributionOracle — tracks evaluator activity and quality
├── DormancyOracle — manages activity_factor for all participants
├── DistributionCrank — permissionless reward distribution per epoch
├── EvalConsensus — aggregates multi-node eval results
└── GovernanceVault — holds stake for proposals + slashing

Ethereum (for high-value decisions + zk-proofs):
├── ModelCommitments — hashes of LoRA adapters + reward models
├── zkEvalVerifier — SNARK verification contract (EZKL/Halo2)
└── ProtocolGovernance — major protocol upgrades (cross-chain bridge from Solana)
```

### 8.2 Off-Chain Compute Infrastructure

```
Training Network (Gensyn-compatible):
├── GPU nodes: run LoRA fine-tuning jobs per epoch
├── CPU nodes: run reward model training (lighter)
├── Verification: Verde-protocol dispute resolution
└── Communication: DisTrO gradient compression

Eval Network (InfiCoEvalChain-inspired):
├── 7 independent eval validators (minimum)
├── Geographic distribution requirement
├── Each runs: Tier 1 benchmarks + subnet benchmarks
└── zk-SNARK proof generation on completion

Feedback Collection Network:
├── Otto API nodes (any MY3YE ecosystem deployment)
├── Privacy-preserving aggregation (federated)
└── Anonymized response pairs for evaluator rating
```

### 8.3 APIs and Protocols

```
Governance API (extends Otto Memory API at :8100):
  POST  /intelligence/propose       — submit governance proposal
  GET   /intelligence/proposals     — active proposals
  POST  /intelligence/vote          — cast weighted vote
  GET   /intelligence/subnets       — list capability subnets with metrics
  GET   /intelligence/epoch/status  — current epoch state

Training Coordination API:
  POST  /training/submit-feedback    — submit feedback sample
  POST  /training/submit-eval        — evaluator submits rating
  GET   /training/epoch/{id}         — epoch details
  POST  /training/compute/register   — compute provider registration

Eval API:
  POST  /eval/run                    — trigger eval run (validator nodes)
  GET   /eval/results/{epoch_id}     — get eval results
  GET   /eval/proof/{epoch_id}       — get zk-SNARK proof
  POST  /eval/dispute                — dispute an eval result
```

---

## 9. Phase Roadmap

### Phase 0: Foundation (Now → 90 Days)
**Goal:** Prove the governance layer with off-chain simulation

- [ ] Implement contribution score tracking in Otto Memory API
- [ ] Build feedback collection endpoint (users can rate Otto responses)
- [ ] Design eval benchmark suite (Tier 1 — 5 benchmarks)
- [ ] Whitepaper publication: "Otto AI Decentralized Intelligence Protocol"
- [ ] Community consultation: publish design doc, gather feedback
- [ ] Off-chain simulation: model what reward distribution looks like with real data

**No code deployed on-chain. No money at risk. Full simulation.**

### Phase 1: Governance MVP (90-180 Days)
**Goal:** First on-chain governance votes on capability priorities

- [ ] Deploy IntelligenceRegistry on Solana devnet
- [ ] Implement GovernanceVault + basic proposal lifecycle
- [ ] Activate first 3 capability subnets (reasoning, knowledge, safety)
- [ ] First community vote: "What should Otto prioritize improving?"
- [ ] Deploy eval network (3 nodes as a starting point)
- [ ] Run first training epoch (reward model update from community feedback)

**Stakes: small (test budget). No production model changes yet.**

### Phase 2: Training Integration (180-365 Days)
**Goal:** First community-governed model update in production

- [ ] FedRLHF framework deployed for reward model training
- [ ] Contribution-weighted aggregation in production
- [ ] First LoRA adapter trained and governance-voted to production
- [ ] zk-SNARK proof generation for Tier 1 benchmarks
- [ ] Gensyn integration for distributed compute
- [ ] $KOIN rewards flowing to contributors, evaluators, compute providers

**Stakes: first real model changes. Full eval required before deploy.**

### Phase 3: Protocol Decentralization (Year 2)
**Goal:** Remove founding team control, full community ownership

- [ ] Founding team veto rights sunset (all decisions community-governed)
- [ ] Full 7-node eval network with geographic distribution
- [ ] Self-evolution pipeline operating autonomously
- [ ] Drift detection and auto-proposal system live
- [ ] Protocol audited by independent security firm
- [ ] Token-gated developer API: any developer can build on the intelligence layer

### Phase 4: Open Protocol (Year 3+)
**Goal:** Replicate the model across all MY3YE agents

- [ ] ONEON deploys its own subnet (communication intelligence)
- [ ] Koink.fun deploys a meme/culture subnet
- [ ] SOS Systems deploys safety/humanitarian subnet
- [ ] Third-party developers can deploy custom capability subnets
- [ ] Full multi-chain: Solana + Ethereum + Base + any EVM

---

## 10. Open Questions for Mev

1. **Training resource funding:** Phase 2 requires real GPU compute for LoRA training. Should this come from $KOIN treasury, a compute grant (Gitcoin, Optimism RPGF), or founding team seed? The Gensyn integration could reduce this cost significantly.

2. **Eval node operators:** Who runs the initial 7 eval nodes? Founding team + community volunteers? Or does the governance system need to be live first to elect them?

3. **Feedback opt-in scope:** Should Otto request feedback after EVERY response, or only specific interaction types? High-frequency feedback = better training signal. Low-friction asks = better UX.

4. **Proof-of-concept order:** Should the first community vote be on capabilities (what to improve) or on system prompt (how Otto communicates)? System prompt governance is lower risk and faster feedback loop.

5. **Compute incentive ceiling:** What's the maximum $KOIN budget per training epoch? Setting this creates a credible commitment to compute providers and prevents treasury drain.

---

## 11. Key Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Training approach | Fine-tuning (LoRA) not from scratch | Mev directive + cost efficiency |
| Primary chain | Solana | Speed, low cost, existing $KOIN deployment |
| Governance token | $KOIN | Already exists, aligned incentives |
| Eval approach | Multi-party consensus + zk-proofs | Most verifiable, Goodhart-resistant |
| Aggregation | Contribution-weighted FedAvg | Shapley fairness + quality signal |
| Continual learning | LoRA isolation + replay buffers | Prevents forgetting, modular |
| Identity layer | ONEON | Ecosystem integration |
| Reference agent | Otto | Built-in proof of concept |

---

## 12. References

**Research foundations:**
- Bittensor/dTAO: https://docs.learnbittensor.org/ — subnet architecture, market-driven emission
- Gensyn Protocol: https://docs.gensyn.ai/the-gensyn-protocol — distributed training, RL Swarm
- FedRLHF: arXiv 2412.15538 — federated RLHF with privacy preservation
- InfiCoEvalChain: arXiv 2602.08229 — blockchain-based decentralized LLM evaluation
- JSTprove/EZKL: arXiv 2510.21024 — verifiable AI with zk-SNARKs
- DisTrO + Psyche: ChainCatcher analysis — on-chain RL post-training
- FL-Light Shapley: federated contribution evaluation
- EvoAgentX Survey: github.com/EvoAgentX/Awesome-Self-Evolving-Agents

**MY3YE ecosystem integration:**
- Dormant Token Decay Design: ~/otto/projects/capital/dormant_token_decay_design.md
- $KOIN Tokenomics Paper: ~/otto/projects/capital/koin_tokenomics_paper.md
- 505 Systems Three-Layer Architecture: Otto semantic memory
- SOS Systems IPL Architecture: ~/otto semantic memory (e0123885)

---

*This document is the first architecture proposal for the Otto AI Decentralized Intelligence Protocol. Status: for Mev review before community publication.*

---
id: 5564986f-9ccf-4540-ad56-91a968173fb1
title: W3F Level 1 Grant Application — 505 Systems DPC Governance Pallet for Polkadot
content_type: article
status: draft
updated_at: 2026-03-20T07:29:30.390146+00:00
source: content-db
---

# Web3 Foundation Open Grants Program — Level 1 Application

## 505 Systems — Democratic Power Contribution (DPC) Governance Pallet for Polkadot

**Applicant:** MY3YE / Abra Otto Mev
**Contact:** admin@otto.lk
**GitHub:** github.com/ottomev/pallet-dpc
**Repository Status:** Architecture + scaffolding committed. W3F grant funds the implementation to completion.
**Requested Amount:** $10,000 USD equivalent
**Payment Currency:** DOT (50% vested) + USDC
**License:** Apache 2.0
**Application Type:** Level 1 (≤ $10K, 2 approvals)

---

## Project Overview

### Project Name
505 Systems — DPC Governance Pallet

### One-Line Summary
An open Substrate pallet that adds contribution-weighted governance to any Polkadot parachain — builders earn influence proportional to demonstrated effort, not token holdings.

### Overview

Polkadot's OpenGov is the most sophisticated on-chain governance system in production. It is also fundamentally token-weighted. A holder with 10M DOT and no contribution history has more governance influence than a builder with 10K DOT and three years of pull requests, audits, and community participation.

505 Systems builds Democratic Power Contribution (DPC) — a governance weight mechanism that adds a second dimension to participation: verified contribution alongside token holdings.

**The DPC formula:**
```
DPC Weight = Structural Impact × Consistent Energy × Weighted Resonance
```

- **Structural Impact:** the depth of verified contribution (code commits, validated governance actions, content published, services rendered)
- **Consistent Energy:** participation continuity over time (not one large action, but sustained effort)
- **Weighted Resonance:** community validation of the impact (peer review, downstream usage, citation)

This grant funds `pallet-dpc` — an open-source Substrate pallet implementing DPC weight computation. Any Polkadot parachain can adopt it. It extends OpenGov without replacing it.

---

## Problem Statement

Token-weighted governance creates a structural problem: capital concentration equals influence concentration. This is not a bug in Polkadot's design — it is an inherent property of any purely token-weighted system.

The result: governance decisions trend toward protecting capital, not rewarding construction. The people who build the ecosystem accumulate less governance weight than the people who hold its tokens.

DPC does not eliminate token weight. It adds builder weight. The two dimensions combine: your governance influence is a function of both what you hold and what you have built. This changes the incentive gradient — building becomes a path to influence, not just a path to tokens.

For parachains building community-governed systems, contribution-weighted governance is the missing primitive.

---

## Project Details

### Technical Architecture

**Module: `pallet-dpc`**

Integrates with existing OpenGov infrastructure as a weight extension:

- `ContributionRegistry`: stores verified contribution proofs per account (compatible with ONEON identity pallet — can be deployed independently)
- `DPCScore`: computes Structural Impact × Consistent Energy × Weighted Resonance per account from the registry
- `WeightBlend`: configurable blend ratio — parachain sets the token-weight / DPC-weight split (e.g., 70/30, 50/50, 100/0)
- `GovernanceExtension`: hooks into `pallet-referenda` and `pallet-conviction-voting` to apply blended weight at vote time
- `VerifierRegistry`: approved contribution verifiers — same registry design as ONEON pallet, deployable standalone

### Sybil Resistance

The `ContributionRegistry` could theoretically be gamed by an actor deploying multiple wallets and submitting self-signed contribution proofs through an approved verifier they also control.

The `VerifierRegistry` addresses this directly:

**Stake-weighted verifier admission.** Becoming an approved verifier requires locking a bond (`T::MinVerifierBond`). Fraudulent attestations are slashable. Sybil-at-scale requires capital proportional to the governance weight gained.

**Quadratic dampening per verifier.** DPCScore computation applies quadratic dampening to contributions from any single verifier source. Proofs attested by 10 different verifiers score higher than 10 proofs from one verifier, bounding verifier leverage.

**Decay function.** DPC scores decay over time. Historical bulk submission cannot produce lasting score inflation — the attack window closes quickly.

**Time-lock on score growth.** DPCScore cannot increase by more than `T::MaxScoreGrowthPerEpoch` per epoch, making rapid inflation costly in time as well as capital.


**Deployment modes:**
1. **Standalone:** deploy on any parachain without ONEON identity pallet
2. **Integrated:** pull contribution records from ONEON People Chain via XCM (if ONEON pallet deployed)

Parachain governance team sets `WeightBlend` via on-chain parameter — DPC weight contribution can be increased over time as the system earns community trust.

### Technology Stack
- Language: Rust (Substrate FRAME)
- Chain: any Substrate-based Polkadot parachain
- OpenGov hooks: `pallet-referenda`, `pallet-conviction-voting`
- XCM version: V4 (for ONEON integration mode)
- Testing: Chopsticks + Westend testnet


### Governance Capture Mitigations

`WeightBlend` is a powerful parameter — a governance team could set it to 90% DPC weight after pre-seeding contribution scores for insiders, effectively replacing token-weighted governance with insider-weighted governance.

Three layers of protection prevent this:

**Supermajority requirement.** Any change to `WeightBlend` requires a supermajority (configurable, default 2/3 of current governance weight). The same governance body that would benefit from the change must approve it — making insider capture costly without broad support.

**Time-lock on parameter updates.** `WeightBlend` changes are subject to a time-lock (configurable, default 28 days) before taking effect. This gives the community time to detect and respond to manipulative proposals.

**On-chain change history.** Every `WeightBlend` modification is logged with block number, proposer, and vote outcome. The full history of ratio changes is queryable on-chain. Any suspicious parameter trajectory is visible to all participants.

**Bounded DPC ceiling.** The pallet enforces `T::MaxDpcWeight` (default: 50) — DPC weight cannot exceed 50% of total governance weight through this pallet alone. Exceeding this ceiling requires a runtime upgrade with its own governance gauntlet.


---

## Team

**MY3YE / Abra Otto Mev**
- Governance protocol architect
- Building 505 Systems DPC governance for 2 years
- Related work: ONEON identity layer (W3F Level 1 concurrent application), Otto AI (autonomous governance intelligence)
- GitHub: github.com/ottomev (pallet-dpc, pallet-oneon-identity)
- Contact: admin@otto.lk


---

## Team and Delivery Risk

**Structure:** Solo applicant. MY3YE / Abra Otto Mev is the sole developer on this grant.

W3F evaluators flag solo applications for delivery risk — this is a fair concern. Here is how it is mitigated:

**Existing infrastructure.** The MY3YE ecosystem has a deployed intelligence layer (Otto AI). Both pallets build on well-documented Substrate primitives, reducing novel engineering surface. The DPC pallet is designed to operate standalone — no ONEON dependency for Milestone 1.

**Agent-assisted development.** Otto AI is the development environment — an agentic system that accelerates code generation, test writing, and documentation. Milestone 1 deliverables are scoped to 4 weeks assuming this tooling.

**Scoped milestones.** Both milestones have specific, evaluator-verifiable outputs. The W3F milestone structure allows for timeline negotiation before payment — a built-in accountability checkpoint.

**Contingency.** If solo capacity becomes a blocker mid-grant, the team has established relationships with Substrate developers in the Polkadot ecosystem to bring in contractor support. Apache 2.0 licensing and modular architecture mean any developer can pick up the work from any point.


---

## Development Roadmap

### Milestone 1 — Core DPC Pallet (4 weeks, $5,000)

**Deliverables:**
- `pallet-dpc` with `ContributionRegistry`, `DPCScore`, `WeightBlend`
- Full unit test suite (90%+ coverage)
- Standalone deployment on Westend testnet (no ONEON dependency)
- Documentation: DPC formula, pallet API, parameter tuning guide

**Verification:** Evaluators can deploy pallet on a local Substrate node, register test contributions, compute DPC scores, and verify blended weight output against expected values.

### Milestone 2 — OpenGov Integration + ONEON XCM (4 weeks, $5,000)

**Deliverables:**
- `GovernanceExtension`: hooks into `pallet-referenda` + `pallet-conviction-voting`
- XCM integration: pull contribution records from ONEON People Chain (if deployed)
- Integration test suite: end-to-end vote with blended DPC + token weight
- Security review
- Parachain integration guide with deployment checklist

**Verification:** Evaluators run a test referendum on Westend with `WeightBlend` set to 50/50. Submit votes with accounts at different DPC scores and verify the blended weight is applied correctly.

---

## Budget Breakdown

| Item | Amount |
|---|---|
| Milestone 1: Core DPC pallet | $5,000 |
| Milestone 2: OpenGov hooks + XCM + audit | $5,000 |
| **Total** | **$10,000** |

---

## Future Plans

Level 1 delivers the pallet. Level 2 roadmap ($30K):
- Full 505 Systems governance stack: proposal pipeline, treasury integration, contribution bounty system
- SOS Systems self-education integration: skill bounty completions generate contribution proofs
- Deployment on a production Polkadot parachain (partner TBD — in discussion)
- Community governance module: DPC-weighted community proposals feeding into OpenGov treasury


---

## Related Work

DPC is a novel governance mechanism. W3F evaluators will want to understand its relationship to prior art:

**Quadratic Voting (Weyl and Buterin, 2018).** QV reduces whale dominance by making votes cost quadratically more as you acquire more of them. DPC adds a *contribution* dimension alongside tokens — orthogonal to QV. QV prices votes; DPC earns governance weight through demonstrated effort. The two mechanisms could compose.

**Conviction Voting (1Hive / Aragon).** Conviction Voting locks tokens over time to increase governance weight — it rewards patience. DPC rewards contribution. Both add dimensions beyond raw token holdings. The key difference: Conviction Voting still requires token holdings to participate. DPC allows builders with minimal token holdings to earn governance weight through effort.

**SourceCred.** SourceCred is an off-chain contribution graph for open-source projects, used to allocate funding. DPC builds on similar contribution-tracking philosophy but is (1) on-chain, (2) parachain-native, and (3) directly integrated with OpenGov's referendum flow. SourceCred has no governance enforcement mechanism — it produces signal, but that signal has no binding on-chain effect.

**Optimism RetroPGF.** RPGF rewards past impact with retroactive funding. DPC rewards past impact with governance weight. Same philosophy, different output. DPC is not a funding mechanism — it is a weight mechanism.

DPC adds what none of these provide: an on-chain, parachain-native, OpenGov-integrated contribution weight that runs alongside token weight without replacing it, with a configurable blend ratio that parachain teams control.


---

## Additional Information

**Relationship to OpenGov:**
DPC weight is additive, not competitive. We do not propose replacing token-weighted governance. We propose extending it with a second dimension that rewards builders. Parachain teams control the blend ratio — they can deploy at 100% token-weight and increase DPC weight incrementally as the community validates the system.

**Relationship to ONEON Level 1 application:**
The two Level 1 applications (ONEON identity + DPC governance) are designed to work together but can deploy independently. ONEON provides portable contribution records. DPC consumes them. Either pallet delivers value without the other.

**Open-Source Commitment:**
Apache 2.0. The pallet is designed for maximum reusability.

---

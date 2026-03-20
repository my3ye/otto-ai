---
title: "W3F Level 1 Grant Proposal — 505 Systems: Contribution-Weighted Governance Tooling for Polkadot OpenGov"
content_id: 7adfb851-1da6-4d95-9e10-d3303271ec32
version: 2
status: draft
tags: ['polkadot', 'w3f', 'grant', '505-systems', 'governance', 'opengov', 'dpc', 'level-1']
last_updated: 2026-03-20T07:18:38.250379+00:00
---

# Web3 Foundation Open Grants Program
## Grant Application: 505 Systems Governance Tooling

**Proposal Title:** 505 Systems — Contribution-Weighted Governance Module for Polkadot OpenGov
**Grant Level:** Level 1 (up to $10,000 USD)
**Team:** MY3YE / Ottolabs
**Contact:** admin@otto.lk
**Repository:** github.com/my3ye (fork of w3f/Grants-Program)

---

## Project Overview

505 Systems is a governance DAO protocol built as part of the MY3YE ecosystem. This Level 1 grant funds development of a contribution-weighted governance module — an alternative or complement to token-weighted voting in Polkadot's OpenGov framework.

**The problem:** Token-weighted governance concentrates decision power in large holders. Early contributors, builders, and active community members — those with the most relevant knowledge — are outweighed by capital. This degrades governance quality and long-term ecosystem health.

**What this grant delivers:** A working governance module implementing Decentralized Proof of Contribution (DPC) — on-chain reputation-weighted voting that integrates with Polkadot's existing OpenGov mechanics.

---

## Project Description

### Background

Polkadot's OpenGov is among the most sophisticated on-chain governance systems in production. 505 Systems does not replace it — it extends it. The DPC module adds a reputation weight layer: votes are scaled by verified on-chain contribution history alongside token balance. This is additive, not oppositional. Token weight and contribution weight together produce a more complete picture of governance legitimacy.

This aligns governance power with ecosystem knowledge and commitment — producing decisions more likely to serve the long-term health of the protocol.

### The DPC Mechanism

Decentralized Proof of Contribution scores contributors on:
- On-chain activity (transactions, proposals, code contributions)
- Ecosystem participation (governance votes cast, referenda engaged)
- Temporal weighting (sustained contribution over time beats one-time activity)

The score is public, auditable, and decays without continued contribution. DPC weight is configurable — parachains and governance communities decide the balance between token weight and contribution weight for their context.

### Deliverables

*All development milestones begin upon grant approval.*

**Milestone 1 (Weeks 1-4 post-approval): DPC Scoring Engine**
- Contribution scoring algorithm implemented as Substrate pallet
- On-chain event indexing for activity signals (configurable inputs)
- Decay function: contribution score degrades without activity
- Unit tests: 90%+ coverage
- Technical specification document

**Milestone 2 (Weeks 5-8 post-approval): OpenGov Integration Module**
- Voting weight modifier: integrates DPC score with token weight in configurable ratio
- Demo: governance referendum with DPC-weighted voting enabled
- Governance UI component (React) for score display and vote weight visualization
- Full documentation and integration guide
- Open-source release Apache 2.0

### Technical Stack
- Substrate / FRAME pallets (Rust)
- Polkadot OpenGov pallet integration
- React governance UI component

---

## Team

**[ACTION REQUIRED before PR submission: complete team credentials below — W3F requires individual names, GitHub handles, and LinkedIn profiles for all team members]**

**Mev — Lead Developer and Project Lead**
- GitHub: [MEV_GITHUB_HANDLE]
- LinkedIn: [MEV_LINKEDIN_URL]
- Role: Architecture, Substrate pallet development, project management
- Background: [2-3 sentences: relevant software engineering experience, open-source contributions, delivered products]

**On prior Substrate experience:**

This is our first Substrate pallet implementation. We have strong software engineering experience across other stacks and have shipped production systems. We acknowledge this directly — we are building Substrate capability through this grant, not presenting prior Substrate work.

To demonstrate toolchain capability, we will attach a basic compilable Substrate pallet (proof-of-concept level, with tests) to the PR at submission. Evaluators will see the code before committing to review.

**Team distribution:** The team is distributed across timezones. Budget rates reflect regional labor costs.

**Shipped products:**
- WebAssist — production SaaS product, live at webassist.ink
- Otto Management System — internal ops and intelligence tooling, live at mev.otto.lk

**Ecosystem:**
- SOS Systems / 505 Systems (governance DAO) — this proposal
- ONEON (sovereign network)
- Otto AI (decentralized intelligence)
- Koink.fun (chain-agnostic meme tokenomics)

Web: my3ye.xyz

**Note:** The ONEON Level 1 grant proposal is being submitted simultaneously. The two systems are composable: ONEON identity provides the verified identity layer that DPC scoring uses. Both Level 1 deliverables are self-contained and independent.

---

## Ecosystem Fit

**Why Polkadot?**
Polkadot's OpenGov is the most active on-chain governance system in production. Improving its quality directly improves the Polkadot ecosystem's decision-making capacity. The DPC module is designed as an OpenGov extension — it works with the existing system, not against it.

**What gap does 505 Systems fill?**
Polkadot has robust token-weighted governance. It lacks a contribution-weighted layer. The OpenGov community has discussed this limitation across multiple forum threads. 505 Systems delivers a concrete, deployable module for parachains and communities that want both.

The Electric Capital Developer Report (2024) and Polkadot State of the Network data both indicate flat developer growth (450-500 monthly active devs over 18 months). Governance quality that rewards sustained contribution is one mechanism for attracting and retaining serious builders.

**Alignment with W3F values:**
W3F's mission is to facilitate a fully functional and user-friendly decentralized web. Governance that accurately represents contributor knowledge — not just token holdings — is a foundational requirement for that web.

---

## Budget

| Item | Cost |
|---|---|
| DPC scoring pallet development | $5,000 |
| OpenGov integration module | $3,000 |
| UI component and documentation | $1,500 |
| Testing infrastructure | $500 |
| **Total** | **$10,000** |

*Team is distributed; rates reflect regional labor costs.*

---

## Additional Information

The 505 Systems governance module is designed to be reusable: any Substrate chain or Polkadot parachain can integrate DPC-weighted voting. This creates compounding value across the ecosystem — each new integration strengthens contribution-based governance as a Polkadot primitive.

**Rejection fallback:** If this proposal is returned for revision, we will complete a 30-day revision cycle based on evaluator feedback and resubmit with an expanded code sample.

All code: open-source Apache 2.0.

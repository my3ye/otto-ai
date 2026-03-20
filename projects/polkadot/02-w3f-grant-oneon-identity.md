---
id: e5744ea3-bb99-4e7e-b1da-0b298165124b
title: W3F Level 1 Grant Application — ONEON Sovereign Identity on Polkadot People Chain
content_type: article
status: draft
updated_at: 2026-03-20T07:26:30.534777+00:00
source: content-db
---

# Web3 Foundation Open Grants Program — Level 1 Application

## ONEON Sovereign Identity Layer for Polkadot People Chain

**Applicant:** MY3YE / Abra Otto Mev  
**Contact:** admin@otto.lk  
**GitHub:** github.com/ottomev/pallet-oneon-identity  
**Repository Status:** Architecture + scaffolding committed. W3F grant funds the implementation to completion.  
**Requested Amount:** $10,000 USD equivalent  
**Payment Currency:** DOT (50% vested) + USDC  
**License:** Apache 2.0  
**Application Type:** Level 1 (≤ $10K, 2 approvals)  

---

## Project Overview

### Project Name
ONEON — Sovereign Identity Module for Polkadot People Chain

### One-Line Summary
A portable, self-sovereign identity primitive for Polkadot's People Chain — built open-source as a reusable module any parachain can adopt.

### Overview

ONEON is the identity and communication layer of the MY3YE ecosystem. It operates on Zero-Extraction Network principles: identity is a structural property of the person, not a permission granted by a platform.

This grant funds a focused deliverable: an open-source identity module that anchors ONEON's identity primitives on Polkadot's People Chain. People Chain is Polkadot's dedicated identity infrastructure — the natural home for sovereign, portable, contribution-trackable identity. ONEON's module extends People Chain's existing identity pallet with contribution history portability across parachains.

**What this builds:**
- A Substrate pallet that stores ONEON identity proofs on People Chain
- A contribution-history registry: verifiable, parachain-portable, user-owned
- An open API layer any Polkadot dApp can query for identity + contribution score
- Documentation and integration guide for parachain developers

All code is Apache 2.0. Any project on Polkadot can use it.

---

## Problem Statement

Polkadot's People Chain provides the infrastructure for on-chain identity. What it does not provide is contribution history — the record of what a person has actually built, validated, or contributed across the ecosystem.

The result: governance weight is determined by token holdings, not demonstrated effort. Builders with minimal token holdings but years of active contribution have no on-chain record to show for it. Treasury proposals and OpenGov referenda reward capital concentration over builder concentration.

ONEON's identity module closes this gap. It attaches a portable contribution record to any People Chain identity — one that follows the person across parachains, not one that lives only in a single dApp's database.

---

## Project Details

### Technical Architecture

**Module: `pallet-oneon-identity`**

Builds on top of the existing `pallet-identity` (People Chain). Adds:
- `ContributionRecord` struct: timestamped, signed, parachain-tagged contribution proofs
- `PortabilityIndex`: cross-chain contribution score computed on-chain
- `VerifierRegistry`: approved contribution verifiers (dApps, DAOs, oracles)
- XCM integration: contribution records can be queried cross-chain via XCM messages

### Sybil Resistance

The `ContributionRecord` model could theoretically be gamed by an actor controlling multiple accounts and submitting self-signed proofs through an approved verifier they also control. The `VerifierRegistry` addresses this directly.

**Stake-weighted verifier admission.** Becoming an approved verifier requires locking a bond (`T::MinVerifierBond`). Fraudulent attestations are slashable. The attacker must risk capital proportional to the influence they wish to gain.

**Quadratic dampening per verifier.** The `PortabilityIndex` computation applies quadratic dampening to contributions from any single verifier. Ten proofs from ten different verifiers outweigh ten proofs from one verifier. This bounds verifier leverage over any single contributor's score.

**Decay function.** Contribution weight decays over time. Bulk historical proof submission cannot produce lasting score inflation — sustained contribution is required to maintain a high weight.

**Time-lock on score growth.** `PortabilityIndex` scores cannot increase by more than `T::MaxScoreGrowthPerEpoch` per epoch, making rapid score inflation costly in time as well as capital.

**Identity Proof Flow:**
1. User completes a contribution action (governance vote, PR merge, content publish, service rendered)
2. Verifier (any approved MY3YE or third-party dApp) signs and submits a `ContributionProof` to the pallet
3. Proof is anchored on People Chain with timestamp and parachain source
4. User's `PortabilityIndex` updates in real time
5. Any parachain querying the user's identity via XCM receives full contribution history alongside standard identity fields

### Technology Stack
- Language: Rust (Substrate framework)
- Chain: Polkadot People Chain (parachain)
- Standard: Substrate FRAME pallets
- XCM version: V4
- Testing: Chopsticks (fork testing) + integration tests against Westend

---

## Team

**MY3YE / Abra Otto Mev**
- Protocol architect and lead developer
- 2 years building decentralized identity and governance systems
- Building: ONEON (sovereign identity), SOS Systems (DPC governance), Otto AI (autonomous intelligence layer)
- GitHub: github.com/ottomev (pallet-oneon-identity)
- Contact: admin@otto.lk

We are a small, focused team. We build without outside capital. Every component delivered under this grant is a production commitment — not a proof-of-concept that requires further funding to ship.


---

## Team and Delivery Risk

**Structure:** Solo applicant. MY3YE / Abra Otto Mev is the sole developer on this grant.

W3F evaluators flag solo applications for delivery risk — this is a fair concern. Here is how it is mitigated:

**Existing infrastructure.** The MY3YE ecosystem has a deployed intelligence layer (Otto AI). The pallet architecture builds on existing, well-documented Substrate primitives (`pallet-identity`, `pallet-xcm`), reducing novel engineering surface area.

**Agent-assisted development.** Otto AI is the development environment — an agentic system that accelerates code generation, test writing, and documentation. Milestone 1 deliverables are scoped to 4 weeks assuming this tooling.

**Scoped milestones.** Both milestones have specific, evaluator-verifiable outputs with test scripts. The W3F milestone structure allows for timeline negotiation before payment — a built-in accountability checkpoint.

**Contingency.** If solo capacity becomes a blocker mid-grant, the team has established relationships with Substrate developers in the Polkadot ecosystem to bring in contractor support. Apache 2.0 licensing and modular architecture mean any developer can pick up the work from any point.


---

## Development Roadmap

### Milestone 1 — Core Pallet (4 weeks, $5,000)

**Deliverables:**
- `pallet-oneon-identity` with `ContributionRecord`, `PortabilityIndex`, `VerifierRegistry`
- Full unit test suite (90%+ coverage)
- Deployment on Westend testnet
- Documentation: architecture, pallet API, integration guide

**Verification:** Evaluators can run the pallet on a local Substrate node and submit test `ContributionProof` extrinsics. Test scripts included.

### Milestone 2 — XCM Integration + Audit (4 weeks, $5,000)

**Deliverables:**
- XCM V4 cross-chain query integration
- Integration test suite against Westend relay chain
- Security review of pallet (internal + community audit)
- Sample integration: ONEON identity query from a test parachain
- Deployment guide for any parachain wishing to adopt the module

**Verification:** Evaluators can submit a cross-chain XCM message querying a test identity's contribution history from a second test parachain.

---

## Budget Breakdown

| Item | Amount |
|---|---|
| Milestone 1: Core Pallet development | $5,000 |
| Milestone 2: XCM integration + testing + audit | $5,000 |
| **Total** | **$10,000** |

---

## Future Plans

This Level 1 grant delivers the foundation. Level 2 roadmap:

- Full ONEON protocol implementation on Polkadot ($30K Level 2): encrypted messaging layer, guardian network for Panik App, five-layer ZEN architecture
- 505 Systems DPC pallet integration: contribution weight flows from People Chain identity into OpenGov
- Community self-education system (SOS Systems): contribution records from SOS skill bounties anchor on People Chain

The identity module is load-bearing infrastructure. Everything else in the MY3YE ecosystem builds on top of it.

---

## Additional Information

**Why People Chain?**
People Chain is Polkadot's dedicated infrastructure for decentralized identity. Building ONEON's identity primitives anywhere else would be ignoring the design. People Chain + XCM is the correct architecture for portable, cross-chain identity.

**Open-Source Commitment:**
All code delivered under this grant is Apache 2.0. The pallet is designed for maximum reusability — any Polkadot project building governance, reputation, or contribution tracking can adopt it without permission.

**Related Work:**
The existing `pallet-identity` on People Chain is our starting point, not our replacement target. We extend it, not compete with it. This is additive infrastructure.

---

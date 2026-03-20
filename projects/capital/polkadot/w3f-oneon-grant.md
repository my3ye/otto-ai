---
title: "W3F Level 1 Grant Proposal — ONEON: Sovereign Identity on Polkadot People Chain"
content_id: 3c1ed085-7845-4068-99ad-29322587c012
version: 2
status: draft
tags: ['polkadot', 'w3f', 'grant', 'oneon', 'identity', 'people-chain', 'level-1']
last_updated: 2026-03-20T07:17:40.820961+00:00
---

# Web3 Foundation Open Grants Program
## Grant Application: ONEON Sovereign Identity Protocol

**Proposal Title:** ONEON — Sovereign Identity Infrastructure on Polkadot People Chain
**Grant Level:** Level 1 (up to $10,000 USD)
**Team:** MY3YE / Ottolabs
**Contact:** admin@otto.lk
**Repository:** github.com/my3ye (fork of w3f/Grants-Program)

---

## Project Overview

ONEON is a sovereign identity and mesh networking protocol built as part of the MY3YE open-source ecosystem. This Level 1 grant funds the implementation of ONEON's identity layer on Polkadot's People Chain — the dedicated parachain for on-chain identity that launched in June 2024.

**The problem:** Digital identity is controlled by centralized gatekeepers — platforms that revoke, censor, or commodify identity at will. Billions of people lack credible, portable identity. Those who have it cannot own it.

**What this grant delivers:** A working implementation of the ONEON identity protocol on Polkadot People Chain — portable, user-owned digital identities that persist across chains, platforms, and services.

---

## Project Description

### Background

Polkadot People Chain launched in June 2024 as the designated home for decentralized identity in the Polkadot ecosystem. ONEON is purpose-built for this architecture.

The ONEON protocol encodes three principles into the identity layer:
1. **Sovereignty** — identity cannot be revoked by any centralized party
2. **Portability** — identity works across every chain the user inhabits
3. **Contribution tracking** — the identity record grows richer as the holder contributes

### Deliverables

*All development milestones begin upon grant approval.*

**Milestone 1 (Weeks 1-4 post-approval): Core Identity Pallet**
- Extend Polkadot identity pallet for People Chain integration
- Implement ONEON identity schema: handle, bio, contribution_hash, reputation_vector
- Unit tests: 90%+ coverage
- API reference documentation

**Milestone 2 (Weeks 5-8 post-approval): Reputation and Portability Layer**
- Cross-chain identity lookup via XCM (readable from any parachain)
- Reputation vector: on-chain record of contribution activity
- Integration demo: identity resolution from a test parachain
- Full developer documentation
- Open-source release under Apache 2.0

### Technical Stack
- Substrate / FRAME pallets (Rust)
- People Chain integration via XCM
- ONEON identity schema (open standard)

---

## Team

**[ACTION REQUIRED before PR submission: complete team credentials below — W3F requires individual names, GitHub handles, and LinkedIn profiles for all team members]**

**Mev — Lead Developer and Project Lead**
- GitHub: [MEV_GITHUB_HANDLE]
- LinkedIn: [MEV_LINKEDIN_URL]
- Role: Architecture, Substrate pallet development, project management
- Background: [2-3 sentences: relevant software engineering experience, open-source projects, other delivered work]

**On prior Substrate experience:**

This is our first Substrate pallet implementation. We have strong software engineering experience across other stacks and have shipped production systems (see below). We are approaching this grant as a learning-and-delivering engagement — not a credential recitation.

To demonstrate toolchain capability before formal review begins, we will attach a basic compilable Substrate pallet (proof-of-concept level, with tests) to the PR at submission. Evaluators will not need to take our word for it.

**Team distribution:** The team is distributed across timezones. Budget rates reflect regional labor costs for this geography.

**Shipped products:**
- WebAssist — production SaaS product, live at webassist.ink
- Otto Management System — internal ops and intelligence tooling, live at mev.otto.lk

We build, not just plan.

**Ecosystem:**
- ONEON (sovereign network) — this proposal
- SOS Systems / 505 Systems (governance DAO)
- Otto AI (decentralized intelligence)
- Koink.fun (chain-agnostic meme tokenomics)

Web: oneon.ink | my3ye.xyz

---

## Ecosystem Fit

**Why Polkadot?**
People Chain is the only production blockchain built specifically for decentralized identity at scale. ONEON on People Chain connects to Polkadot's 50+ parachains via XCM.

**What gap does ONEON fill?**
Current Polkadot identity is limited to handle and social verification. ONEON adds:
- Contribution-weighted reputation (decentralized credit based on work, not capital)
- Cross-service portability without re-verification
- Mesh identity: functional when centralized infrastructure fails

This addresses a documented ecosystem gap. The Electric Capital Developer Report (2024) measured Polkadot's monthly active developers at 450-500 — flat for 18+ months. Insufficient identity rails for contribution-aware Web3 applications is one contributing factor. Polkadot forum discussions on identity infrastructure have surfaced this gap across multiple threads.

---

## Budget

| Item | Cost |
|---|---|
| Core pallet development (2 engineers x 4 weeks) | $6,000 |
| XCM integration and testing | $2,000 |
| Documentation and open-source release | $1,000 |
| Infrastructure and deployment | $1,000 |
| **Total** | **$10,000** |

*Team is distributed; rates reflect regional labor costs.*

---

## Additional Information

This Level 1 proposal is the first step toward a Level 2 application ($30,000) for the full ONEON protocol: mesh networking, offline-capable identity, and the complete reputation engine. The Level 1 deliverable is a self-contained, production-ready contribution to the Polkadot ecosystem regardless of Level 2 outcome.

**Rejection fallback:** If this proposal is returned for revision, we will complete a 30-day revision cycle based on evaluator feedback and resubmit with an expanded code sample and addressed gaps.

All code: open-source Apache 2.0, maintained by MY3YE/Ottolabs.

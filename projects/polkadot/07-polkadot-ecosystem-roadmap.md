---
id: 94c8c63d-41bf-4567-86ec-dfad0629b730
title: Polkadot Ecosystem Entry Roadmap — MY3YE 2026
content_type: roadmap
status: draft
updated_at: 2026-03-20T07:21:26.628800+00:00
source: content-db
---

# MY3YE x Polkadot Ecosystem Entry Roadmap
## 2026 Execution Plan

---

## Phase 0: Foundation (Week 1-2, March 2026)

### Deliverables
- [ ] Post Polkadot forum introduction (forum.polkadot.network, Ecosystem category)
- [ ] Join Polkadot Discord, post introduction in #ecosystem channel
- [ ] Register MY3YE, ONEON, SOS Systems, Otto AI at builder.gitcoin.co (GG24 preparation)
- [ ] Fork github.com/w3f/Grants-Program repository
- [ ] Draft ONEON W3F Level 1 proposal (identity-pallet.md)
- [ ] Draft 505 Systems W3F Level 1 proposal (dpc-governance.md)
- [ ] Twitter/X announcement thread: MY3YE enters Polkadot ecosystem

### Success Criteria
- Forum post live with 3+ community replies
- Both W3F grant drafts peer-reviewed internally
- Gitcoin project profiles created and verified

---

## Phase 1: Grant Submissions (Week 3-6, April 2026)

### W3F Level 1 — ONEON
- Submit PR to w3f/Grants-Program with ONEON identity pallet proposal
- Respond to evaluator questions within 48 hours
- Begin development milestone 1 (core identity pallet on People Chain)
- Expected review time: 4-8 weeks (W3F Level 1 standard)
- Development milestones begin upon approval
- Grant value: $10,000 (50% vested DOT)

### W3F Level 1 — 505 Systems
- Submit PR to w3f/Grants-Program with DPC governance module proposal
- Submit simultaneously with ONEON (two independent PRs)
- Begin DPC scoring engine development
- Expected review time: 4-8 weeks (W3F Level 1 standard)
- Development milestones begin upon approval
- Grant value: $10,000 (50% vested DOT)

### Gitcoin GG24
- Activate projects when round opens (expected Q2 2026)
- Launch community mobilization campaign (quadratic matching = breadth matters)
- Target: 500+ unique donors across all three projects
- Projects: ONEON, SOS Systems, Otto AI

### W3F Rejection Fallback
If either W3F Level 1 is rejected: 30-day revision cycle based on evaluator feedback. Resubmit with expanded code sample addressing evaluator notes. Do not wait for both decisions — handle each grant independently.

### Forum Engagement
- Respond to governance discussions relevant to identity and OpenGov
- Post technical article on DPC governance philosophy
- Engage with People Chain working group

---

## Phase 2: Development Milestones (Week 5-12, April-June 2026)

### ONEON Milestone 1 (Weeks 5-8)
- Core identity pallet: fork + extend Polkadot identity pallet for People Chain
- ONEON identity schema implementation (handle, bio, contribution_hash, reputation_vector)
- Unit tests: 90%+ coverage
- API reference documentation
- Submit milestone report to W3F

### ONEON Milestone 2 (Weeks 9-12)
- XCM cross-chain identity lookup (readable from any parachain)
- Reputation vector: on-chain contribution activity recording
- Integration demo: identity resolution from test parachain
- Full developer documentation
- Open-source release (Apache 2.0)
- Submit final milestone to W3F for payment

### 505 Systems Milestone 1 (Weeks 5-8)
- DPC scoring engine: Substrate pallet
- On-chain event indexing for contribution signals
- Decay function implementation
- Technical specification document
- Submit milestone report to W3F

### 505 Systems Milestone 2 (Weeks 9-12)
- OpenGov voting weight modifier (DPC + token weight, configurable ratio)
- Demo: governance referendum with DPC weighting enabled
- React governance UI component
- Integration guide for Substrate chains
- Submit final milestone to W3F

---

## Phase 3: Ecosystem Expansion (Q3 2026)

### W3F Level 2 — ONEON Full Protocol ($30K)
- Submit Level 2 proposal after Level 1 approved
- Scope: full ONEON protocol — mesh networking, offline identity, complete reputation engine
- Prerequisite: Level 1 milestone 2 complete and approved

### Koink.fun — Polkadot Hub dApp
- Deploy $KOINK Standard on Polkadot Asset Hub
- Community launch: Polkadot-native meme launchpad
- Cultural campaign: PiPi x Polkadot narrative activation

### Polkadot OpenGov Treasury Proposal
- Apply for uncapped treasury funding for larger ecosystem integration
- Prerequisite: 3-6 months of active forum engagement + at least one delivered grant milestone
- Propose: ONEON + 505 Systems as native Polkadot infrastructure components

### BD Depth
- Parachain partnerships: approach 3-5 parachains for ONEON identity integration
- 505 Systems integration: propose DPC module to 2-3 Substrate chains beyond Polkadot
- Community ambassador program: onboard Polkadot builders as MY3YE contributors

---

## Phase 4: Full Integration (Q4 2026)

### Protocol Composability
- ONEON identity + 505 Systems DPC fully composable on-chain
- SOS Systems using ONEON identity for contributor verification
- Koink.fun creator profiles backed by ONEON sovereign identity

### PiPi Cultural Campaign
- PiPi established as recognized Polkadot ecosystem presence
- $PIPI token on Koink.fun: Polkadot-native deployment
- Community governance: Polkadot community has voice in PiPi ecosystem decisions

### Revenue Targets
- WebAssist (separate path) funding operations
- W3F grants ($20K from two Level 1) covering development costs
- Gitcoin GG24 matching supplementing
- Treasury proposal (if approved) enabling team expansion

---

## Key Contacts and Dependencies

### W3F Contacts
- Sebastian Mueller — sebastian@web3.foundation (primary evaluator contact)
- Rouven Pérez — ecosystem development

### Polkadot Forum
- Post intro before any formal proposal submission
- 3-6 months of engagement increases Treasury proposal approval odds

### Technical Dependencies
- Polkadot SDK / Substrate (already public, no gating)
- People Chain testnet access (public)
- Asset Hub access for Koink.fun (public)
- XCM documentation (available)

### Blockers
- Developer capacity: ONEON + 505 Systems pallets require Rust / Substrate expertise
- WebAssist revenue must come online to fund operations while grants are in review
- Forum engagement is time-intensive: allocate Mev time for Polkadot community

---

## Budget Summary

| Source | Amount | Timeline |
|---|---|---|
| W3F Level 1 — ONEON | $10,000 | 8-12 weeks |
| W3F Level 1 — 505 Systems | $10,000 | 8-12 weeks |
| W3F Level 2 — ONEON | $30,000 | Q3 2026 |
| Gitcoin GG24 (est.) | $5,000-15,000 | Q2 2026 |
| OpenGov Treasury (est.) | TBD | Q3 2026+ |
| **Total (confirmed paths)** | **$20,000** | **by June 2026** |

---

## Success Metrics

**Phase 0-1:**
- Forum post live + 5+ substantive replies
- Both W3F PRs submitted
- Gitcoin profiles active

**Phase 2:**
- W3F Milestone 1 delivered for both grants (on-time)
- First grant payment received

**Phase 3-4:**
- Full ONEON identity pallet in production on People Chain
- 505 Systems DPC module deployed and actively used
- Koink.fun live on Asset Hub
- PiPi recognized in Polkadot ecosystem discourse

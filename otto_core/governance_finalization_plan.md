# MY3YE Ecosystem — Governance Document Finalization Plan
*Drafted: 2026-03-17 | Author: Otto | Status: Working Draft*

---

## Overview

This plan governs the finalization of four foundational MY3YE documents over a 6-month period:

1. **Constitution** — Mission, identity, core commitments, boundaries
2. **Core Values & Ethos** — Philosophical anchors that guide every decision
3. **Core Rules** — Operational governance rules binding all participants
4. **Roadmap** — Phased ecosystem build plan with milestones and dependencies

Each document passes through five stages before it is ratified:

```
DRAFT → COMMUNITY REVIEW → IOU HOLDER VOTE → REVISION → RATIFICATION
```

IOU holders ($KOIN IOUs) are the voting constituency throughout. They hold voting power proportional to their IOU balance and use it to shape each document before the token fully launches.

---

## Document Pipeline & Timeline

| Document | Draft | Community Review | IOU Vote | Revision | Ratification |
|---|---|---|---|---|---|
| **Core Values & Ethos** | Weeks 1–2 | Weeks 3–4 | Week 5 | Week 6 | Week 6 (end) |
| **Constitution** | Weeks 3–5 | Weeks 6–7 | Week 8 | Weeks 9–10 | Week 10 (end) |
| **Core Rules** | Weeks 8–10 | Weeks 11–12 | Week 13 | Weeks 14–15 | Week 15 (end) |
| **Roadmap** | Weeks 12–16 | Weeks 17–20 | Week 21 | Weeks 22–23 | Week 24 (end) |

*Total duration: 24 weeks (~6 months) from kick-off date.*

Documents are sequenced so that each ratified layer informs the next:
- Values → Constitution (values anchor the mission statement)
- Constitution → Core Rules (rules must comply with constitutional boundaries)
- All three → Roadmap (roadmap must serve the mission, stay within rules, reflect values)

---

## Stage Definitions

### Stage 1: DRAFT
**Who**: Otto (primary drafter) + Mev (review and direction)
**Output**: A clean working document ready for public review
**Format**: Markdown, versioned in git, published to OMS and relevant ecosystem pages
**Criteria to advance**: Mev signs off on the draft as "ready for community eyes"

### Stage 2: COMMUNITY REVIEW
**Who**: All ecosystem participants (anyone can comment)
**Channels**: Dedicated Discord thread, Telegram, OMS forum (when live)
**Duration**: 2 weeks per document (1 week for Values/Ethos given its shorter length)
**Output**: Collected feedback, categorized by topic (mission, fairness, clarity, scope)
**Criteria to advance**: Feedback collection period ends + Otto/Mev synthesize into revision notes

### Stage 3: IOU HOLDER VOTE
**Who**: All $KOIN IOU holders at snapshot time
**What they vote on**: Approval of the draft (Yes / No / Abstain) + up to 3 amendment proposals per vote cycle
**Voting power**: 1 IOU = 1 vote (unweighted — everyone who participated early gets equal voice)
**Duration**: 7 days per vote
**Quorum**: 20% of total IOU supply must vote for the result to be binding
**Pass threshold**: 60% Yes to advance without revision; 50–60% triggers mandatory revision; <50% triggers full redraft
**Platform**: Snapshot (off-chain, gas-free) using the IOU token contract address
**Criteria to advance**: Vote passes or mandatory revision is triggered

### Stage 4: REVISION
**Who**: Otto + Mev, informed by vote outcome and community feedback
**Duration**: 1–2 weeks depending on the volume of required changes
**Scope limit**: Revisions address only issues raised in the vote; no new content added without a new vote cycle
**Output**: Revised document, changelog appended, version bumped (e.g., v0.9 → v1.0-rc)
**Criteria to advance**: Mev approves the revised draft

### Stage 5: RATIFICATION
**Who**: IOU holders (final confirming vote)
**What they vote on**: Ratify the revised document as v1.0 (Yes / No)
**Duration**: 5 days (shorter — document already voted on once)
**Pass threshold**: 55% Yes
**On ratification**: Document is published as immutable (IPFS-anchored), version locked, announced ecosystem-wide
**On failure**: Return to Revision stage with extended community input

---

## Document-Specific Detail

### 1. Core Values & Ethos (Weeks 1–6)

**Purpose**: Establish the philosophical foundation — what the MY3YE ecosystem believes, why it exists, and what it refuses to do.

**Key topics to cover**:
- Sovereignty over dependency
- Abundance over extraction
- Contribution-weighted governance (not wealth-weighted)
- Open by default, decentralized by design
- Privacy as a right, not a product feature
- Technology in service of life, not the reverse
- Anti-war, pro-peace as a structural commitment
- Ecological integrity — Tusita as proof of concept
- Transparency in all systems

**Format**: 1–2 pages. Not a manifesto — a living reference used to evaluate future proposals.

**Draft owner**: Otto
**Review deadline**: End of Week 4
**Vote window**: Week 5
**Ratification target**: End of Week 6

---

### 2. Constitution (Weeks 3–10)

**Purpose**: The legal and philosophical ground truth — mission, boundaries, Admin relationship model, community authority structure, amendment process.

**Key topics to cover**:
- Mission statement (immutable core — requires supermajority to change)
- Ecosystem structure and project hierarchy
- The Admin relationship model (Mev's role, Otto's autonomy boundaries)
- IOU holder rights and responsibilities
- Foundation of the governance system (how rules get made and changed)
- Amendment process (what requires community vote vs. admin directive)
- What can never be changed (core mission, anti-surveillance stance, contribution-weighted governance)
- Dissolution clause — what happens if the project ends

**Format**: 8–15 pages. Structured as a legal-grade document with numbered articles.

**Note**: Mev's Koink conversation established that IOU holders can vote to shape the constitution — their votes are binding, not advisory. The constitution must reflect this.

**Draft owner**: Otto (with heavy Mev input on Admin relationship sections)
**Review deadline**: End of Week 7
**Vote window**: Week 8
**Ratification target**: End of Week 10

---

### 3. Core Rules (Weeks 8–15)

**Purpose**: Operational governance — the rules binding all participants, contributors, agents, and the foundation itself.

**Key topics to cover**:
- Contribution validation rules (what counts as a contribution, how it's verified)
- Token eligibility and activity requirements (using dormant decay model already designed)
- Proposal lifecycle rules (who can propose, submission format, review SLA)
- Voting rules (quorum, thresholds, snapshot windows)
- Conflict of interest rules (founder lockup, agent creator compensation)
- AI agent governance rules (how Otto is governed by the community, not just by Mev)
- Revenue allocation rules (WebAssist/service income → ecosystem)
- Enforcement and dispute resolution
- Emergency powers (temporary suspension of rules under defined conditions)

**Format**: 20–30 rules, each numbered and self-contained. Plain language.

**Dependency**: Must not contradict the ratified Constitution.

**Draft owner**: Otto
**Review deadline**: End of Week 12
**Vote window**: Week 13
**Ratification target**: End of Week 15

---

### 4. Roadmap (Weeks 12–24)

**Purpose**: The full ecosystem build plan — phased, milestoned, dependency-mapped. A living document updated quarterly.

**Key topics to cover**:
- Phase 0 (now → Month 3): Revenue foundation (WebAssist live, first paying clients, token launch prep)
- Phase 1 (Months 3–6): Token launch ($KOIN), IOU conversion, governance live on Snapshot
- Phase 2 (Months 6–12): First Tusita land secured, ONEON network alpha, SOS Systems MVP
- Phase 3 (Months 12–24): Full ecosystem products live (Music, Travel, Market, Properties)
- Phase 4 (Months 24–48): Physical infrastructure (factories, farms, Tusita first community)
- Phase 5 (Months 48+): Sovereign infrastructure (devices, satellite comms, energy grid)
- Dependency chains across all 14 projects
- Capital requirement per phase with source (revenue, grants, token launch)
- Key risks and mitigation per phase

**Format**: Full document with phase summaries, milestone tables, and dependency graph. 30–50 pages.

**Note**: This is the only living document — it updates quarterly. Ratification locks the structure and Phase 0–1 content; subsequent phases are reviewed and re-ratified annually.

**Draft owner**: Otto (research-first, multiple agent subtasks for each project section)
**Review deadline**: End of Week 20
**Vote window**: Week 21
**Ratification target**: End of Week 24

---

## IOU Holder Voting Mechanics

### Setup (required before first vote — Week 4)

1. **Snapshot space**: Create `my3ye.eth` space on Snapshot.org
   - Strategy: ERC-20 balance of $KOIN IOU token contract
   - Voting power: 1 token = 1 vote
   - Network: the chain where IOUs are deployed
2. **Quorum setting**: 20% of total supply
3. **Vote duration**: 7 days (standard) / 5 days (ratification)
4. **Delegation**: IOU holders can delegate votes to another address (Snapshot native feature)

### Per-Proposal Cycle

Each document vote runs as follows:

**Proposal package** (published 72h before vote opens):
- Link to the draft document (IPFS + GitHub)
- Summary of changes since last version (if revision)
- Community feedback synthesis (top 5 themes raised)
- Specific amendment proposals (max 3 per cycle, submitted by IOU holders with ≥1,000 IOUs)

**Voting choices**:
- `YES` — approve the document as written
- `YES with amendments` — approve but require specific listed changes
- `NO` — reject, requires redraft
- `ABSTAIN` — counted toward quorum but not outcome

**Results interpretation**:
| Outcome | Action |
|---|---|
| ≥60% YES | Advance to next stage |
| ≥60% YES with amendments | Advance after incorporating amendments |
| 50–60% YES | Mandatory revision + second vote |
| <50% YES | Full redraft + new community review |
| Quorum not met | 7-day extension, then admin discretion |

**Amendment proposal mechanics**:
- Any IOU holder with ≥1,000 IOUs can submit an amendment proposal
- Proposals submitted via OMS form or designated Discord channel
- Proposals must be submitted at least 48h before the vote opens
- Otto synthesizes all proposals and groups them into ≤3 amendment options for the vote
- Winning amendments (>40% of voters select them) are incorporated in revision

**Voting power note**: IOU tokens hold voting power proportional to balance — but voting power does NOT increase with wealth. The 1 IOU = 1 vote mechanic is flat. Large holders have more power, but there is no multiplier for holding more. This reflects the founding ethos: early participants are rewarded, but governance is not plutocratic.

---

## Governance Infrastructure Timeline

| Milestone | Target | Prerequisite |
|---|---|---|
| Snapshot space created | Week 3 | $KOIN IOU contract deployed |
| OMS governance page live | Week 4 | OMS functional (done) |
| First community review forum (Discord) | Week 4 | Discord server (Mev action) |
| First IOU vote (Core Values) | Week 5 | Snapshot space + quorum rules set |
| IPFS anchoring workflow | Week 6 | First ratification |
| Quarterly roadmap review process | Month 6 | Roadmap ratified |

---

## Key Decisions Requiring Mev Input

1. **IOU contract address**: Voting power requires the deployed IOU token contract. Snapshot needs this before any vote.
2. **Quorum percentage**: 20% proposed — adjust based on expected IOU holder count.
3. **Amendment threshold**: 1,000 IOU minimum to propose — set based on total supply and distribution.
4. **Discord vs. Forum**: Community review needs a channel. Discord recommended (quickest to set up); a dedicated forum is better long-term.
5. **Mev's constitutional role**: The Constitution must define Mev's role explicitly — "Founder with overriding veto" vs. "equal participant" vs. "declining authority over time." This is a major design decision.

---

## Success Criteria

By end of Month 6:

- [ ] Core Values & Ethos ratified and IPFS-anchored
- [ ] Constitution ratified with Mev's role explicitly defined
- [ ] Core Rules ratified with all 4 governance domains covered
- [ ] Roadmap ratified with Phases 0–2 fully milestoned
- [ ] Snapshot space operational with at least 2 completed vote cycles
- [ ] IOU holders meaningfully shaped at least 2 documents (verifiable via vote results)
- [ ] All documents accessible from OMS and ecosystem-facing pages

---

*This plan is a living document. Update it as Mev provides direction, IOU deployment details, and community feedback.*

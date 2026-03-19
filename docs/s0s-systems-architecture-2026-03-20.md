# S0S Systems: Architecture Brief
## Two Systems, One Ladder

*Authored by Otto (Architect Agent) | 2026-03-20 | Status: Design Phase*

---

## 1. System Overview

S0S Systems is not a governance framework with an education feature bolted on. It is not a refugee aid platform with a learning module attached. It is a single organism with two entry points that converge into one path: arrive from anywhere, learn by contributing what matters most, rise through effort and impact.

The name carries both meanings simultaneously. **SOS** -- Save Our Souls -- is the distress call. **505** -- Sovereign Operating System -- is the answer. The architecture encodes this duality. System 1 (Self-Education) takes anyone from zero to skilled using their own strengths and passions. System 2 (Refuge + Extraction) extends the same path to people fleeing war zones, living in underprivileged areas, or experiencing homelessness. Both systems share the same identity layer (ONEON), the same reputation mechanics (DPC contribution scoring), and the same advancement track. A developer in Berlin and a displaced family in Khartoum enter through different doors but walk the same ladder.

The design principle that governs everything: **learning and contributing to the most critical parts of the system IS the fastest path to advancement.** There is no curriculum committee deciding what you should learn. The system surfaces what the ecosystem needs most, matches it against your strengths and passions, and rewards you for building it. You learn by doing the work that matters. The more critical the work, the faster you rise. This is the river -- contribution flows downhill toward what the ecosystem needs, and the river carries contributors upward.

---

## 2. Education System Architecture

### 2.1 How Passion-Based Learning Works

Traditional education imposes a curriculum. S0S inverts this. The system discovers what you are good at, what you care about, and what the ecosystem needs -- then builds a path at the intersection of all three.

**Assessment Phase:**

```
ONBOARDING FLOW:

  1. ONEON identity creation (or existing ONEON login)
  2. Conversational skill assessment (LLM-driven, 15-20 minutes)
     - Not a quiz. A conversation.
     - "What do you already know how to do?"
     - "What problems make you angry enough to fix them?"
     - "Show me something you've built, written, organized, or fixed."
  3. System generates a Passion-Skill Map:
     ┌────────────────────────────────────────────────┐
     │  PASSION-SKILL MAP                             │
     │                                                │
     │  Passions:  [music, community organizing]      │
     │  Skills:    [basic Python, graphic design]      │
     │  Gaps:      [smart contracts, audio engineering]│
     │  Strengths: [visual thinking, persistence]      │
     │                                                │
     │  Ecosystem Needs (current):                    │
     │    - P1: Mesh network node documentation       │
     │    - P2: Tusita onboarding UX                  │
     │    - P3: Otto Music audio pipeline             │
     │    - P4: Translation (Sinhala, Arabic, Swahili)│
     │                                                │
     │  Recommended Path:                             │
     │    "Learn audio engineering by building the    │
     │     Otto Music pipeline. Your Python + design  │
     │     skills transfer directly. Gap: audio DSP.  │
     │     First contribution: waveform visualizer."  │
     └────────────────────────────────────────────────┘
  4. Learner confirms or adjusts ("I'd rather do translations")
  5. Path created. First contribution assigned.
```

**Path Adaptation:**

The path is not static. Every contribution generates signal. The LLM reassesses after each completed contribution:
- Did the learner struggle or flow?
- Did peer reviewers rate the work highly?
- Has the ecosystem's need profile shifted?
- Did the learner express interest in something adjacent?

Paths fork, merge, and redirect based on real performance and real need. No semesters. No grades. Contribution quality IS the grade.

**Tech Stack for Assessment:**

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Conversational assessment | Claude API (via Otto) | Natural language, no quiz anxiety, discovers latent skills |
| Skill taxonomy | Custom ontology stored in Neo4j | Graph relationships between skills, projects, and ecosystem needs |
| Need scoring | DPC demand signal from 505 DAO | What the ecosystem actually needs right now, weighted by urgency |
| Path generation | LLM + graph traversal | Shortest path from current skills to highest-impact contribution |
| Reassessment trigger | Every completed contribution | Continuous, not periodic |

### 2.2 How Contributions to S0S Itself = Advancement

This is the core mechanism. The education system does not teach you things and then hope you contribute. **The contribution IS the curriculum.**

**Contribution Types and DPC Weight:**

```
CONTRIBUTION TAXONOMY:

  CODE          Build features, fix bugs, ship infrastructure
                DPC weight: Structural Impact (high) + Consistent Energy
                Verified by: automated tests + peer review + deployment

  TEACHING      Create learning materials, mentor other contributors
                DPC weight: Weighted Resonance (high) + Consistent Energy
                Verified by: learner outcomes (did their mentees advance?)

  TRANSLATION   Translate docs, interfaces, learning materials
                DPC weight: Consistent Energy + coverage metrics
                Verified by: native speaker review + automated quality checks

  COORDINATION  Organize events, manage projects, facilitate governance
                DPC weight: Structural Impact + Weighted Resonance
                Verified by: project outcomes + participant feedback

  DOCUMENTATION Write guides, record processes, maintain knowledge base
                DPC weight: Consistent Energy + usage metrics
                Verified by: page views, learner citations, freshness

  DESIGN        Visual, UX, audio, architectural design
                DPC weight: Structural Impact + peer review quality score
                Verified by: peer review + implementation adoption

  RESOURCE      Provide hardware, hosting, physical space, connectivity
                DPC weight: Consistent Energy (sustained provision)
                Verified by: uptime monitoring + community confirmation

  FIELD OPS     Aid distribution, mesh node maintenance, community work
                DPC weight: All three DPC factors
                Verified by: on-chain distribution records + peer attestation
```

**Advancement Track:**

```
CONTRIBUTOR LEVELS:

  LEARNER (Level 0)
    Entry. Anyone who completes onboarding assessment.
    Can: take guided contributions, access learning materials, join community channels.
    DPC score: 0-99

  CONTRIBUTOR (Level 1)
    3+ verified contributions. Peer-reviewed positively.
    Can: propose contributions, review Level 0 work, vote on minor proposals.
    DPC score: 100-499

  BUILDER (Level 2)
    Sustained contribution over 30+ days. Multiple contribution types.
    Can: mentor Learners, propose ecosystem changes, vote on major proposals.
    DPC score: 500-1999

  STEWARD (Level 3)
    Deep structural impact. Leading a domain (education, mesh, governance).
    Can: approve new contribution types, set domain priorities, serve on review panels.
    DPC score: 2000-4999

  ARCHITECT (Level 4)
    Cross-domain impact. Trusted with constitutional-level decisions.
    Can: propose constitutional amendments, veto harmful proposals, shape ecosystem direction.
    DPC score: 5000+
```

The levels are not titles. They are capability unlocks tied to proven contribution. DPC score decays without activity -- you cannot rest on past work. Sustained contribution is the only way to maintain standing.

### 2.3 MVP Features (Phase 1)

1. **Skill Assessment Onboarding** -- Conversational LLM flow that generates a Passion-Skill Map and recommends a first contribution
2. **Contribution Tracker** -- Dashboard showing contributions submitted, under review, and verified. DPC score visible.
3. **Ecosystem Need Board** -- Live list of what the ecosystem needs, ranked by urgency, filterable by skill match
4. **Peer Review System** -- Contributors review each other's work. Review quality itself earns DPC.
5. **Advancement Badges** -- Verifiable Credentials (W3C VC 2.0) issued on-chain when contributors reach new levels. Portable across the ecosystem.

---

## 3. Refuge + Extraction System Architecture

### 3.1 Identity Verification Without Exploitation

The existing IPL (Integrity Preservation Layer) spec covers the technical cryptography in depth. This section focuses on the human design -- how the system serves people without exploiting their vulnerability.

**Core Principle:** Identity in S0S is self-sovereign. No central database stores "who you are." Your identity is a cryptographic key pair on your device (or printed on paper). Credentials are issued to you, not stored about you.

**What the system verifies:**
- You are a unique person (biometric on-device, never transmitted)
- You have a credential saying you are eligible for aid (issued by a verified field worker)
- You have not already received this specific aid distribution (nullifier check)

**What the system does NOT do:**
- Store your name, nationality, or ethnicity in any database
- Require government-issued ID (many refugees have none)
- Share your location with anyone (geohash at 5km precision, only in aggregated reports)
- Create a record that could be used to target you

**Why this matters:** Traditional humanitarian identity systems (UNHCR biometric enrollment, WFP SCOPE) create centralized databases that become targeting tools when governments change or conflict actors gain access. S0S identity cannot be weaponized because it does not exist in a central location.

### 3.2 Offline-Capable Mesh (ONEON Mesh Network Integration)

The mesh architecture (detailed in the IPL spec) operates in three tiers:

```
CONFLICT ZONE DEPLOYMENT:

  Tier 0: DEVICE MESH (0-5km, zero infrastructure)
    Smartphones + LoRa devices communicate directly.
    Identity verification, aid distribution, P2P messaging.
    Works with NO internet, NO cell towers, NO power grid.
    Cost per device: ~$30-40 (Meshtastic LoRa node)

  Tier 1: COMMUNITY NODES (5-50km, solar-powered)
    Raspberry Pi + LoRa hat + solar panel + battery.
    Stores local copies of records, caches identity data,
    relays messages between Tier 0 clusters.
    Cost per node: ~$150, 5W power draw.

  Tier 2: REGIONAL BACKBONE (satellite uplink)
    Starlink or Iridium terminal shared by 50+ community nodes.
    Syncs pending records to IPFS + blockchain when connected.
    Cost: ~$300 hardware + $50/mo satellite.
```

**ONEON Integration:** The mesh network is not a separate system from ONEON. Mesh nodes ARE ONEON nodes running in degraded mode. When full connectivity exists, they participate in the ONEON network at all five layers. When connectivity drops, they fall back to Tier 0 operations -- identity verification and aid distribution continue without interruption.

### 3.3 Refuge Intake Flow

```
ARRIVAL FLOW:

  ARRIVE
    Person reaches an S0S intake point (physical location or
    mobile field team). No documents required.
    │
    ▼
  VERIFY
    Field worker creates ONEON identity (did:key, offline).
    Issues Verifiable Credential: aid eligibility category.
    Paper backup (QR code) printed for the person.
    Total time: 5-10 minutes. No internet needed.
    │
    ▼
  ENROLL
    Conversational skill assessment (same as education system).
    Passion-Skill Map generated. First contribution suggested.
    If person is in immediate crisis: assessment deferred,
    basic needs (food, shelter, medical) addressed first via
    aid distribution system.
    │
    ▼
  CONTRIBUTE
    Person begins contributing at whatever level they can.
    Translation (many refugees are multilingual).
    Teaching (lived experience, local knowledge).
    Coordination (organizing within their community).
    Technical work (many displaced people have professional skills).
    Field operations (aid distribution, mesh node maintenance).
    │
    ▼
  ADVANCE
    Same DPC-scored advancement track as everyone else.
    Learner → Contributor → Builder → Steward → Architect.
    No ceiling. No separate "refugee track."
    A displaced person who becomes a Steward has the same
    governance power as a developer in Berlin.
```

**Critical design decision:** There is no "refugee mode" vs "normal mode." There is one system with one ladder. The refuge intake adds a pre-step (immediate needs) and allows deferred assessment, but the advancement track is identical. This is not charity. This is a path.

### 3.4 Physical Connection to Tusita Communities

Tusita communities serve as the physical anchor for the S0S system:

```
TUSITA <-> S0S INTEGRATION:

  Tusita Node = S0S Community Node
    Every Tusita location runs Tier 1 mesh infrastructure.
    Physical hardware, solar power, connectivity.

  Tusita Islander Program = S0S Contributor Path
    Tusita's Islander → Steward → Founder → Sovereign progression
    maps directly to S0S's Learner → Contributor → Builder →
    Steward → Architect progression. Same DPC scoring engine.

  Tusita Physical Space = S0S Safe Harbor
    Tusita communities can host S0S participants.
    Not as charity recipients -- as contributors earning
    their place through the same ladder everyone else climbs.

  Tusita Governance = 505 DAO
    Both systems governed by the same 505 Systems DAO.
    A contributor's DPC score in S0S counts for governance
    weight in Tusita decisions, and vice versa.
```

### 3.5 MVP Features (Phase 1)

1. **Intake Portal** -- Mobile-first, offline-capable enrollment app. ONEON identity creation + VC issuance in under 10 minutes.
2. **Resource Allocation Engine** -- Smart contract that locks aid allocations, tracks distribution, prevents double-dipping via nullifier registry.
3. **Location-Based Mesh Nodes** -- Deployable Tier 1 community node kit (Raspberry Pi + LoRa + solar). Documented, reproducible, community-maintainable.
4. **Deferred Assessment Queue** -- People in immediate crisis skip assessment. System tracks and re-engages them when they are ready to begin contributing.
5. **Field Worker Toolkit** -- Android app for field workers: identity creation, VC issuance, aid distribution, offline sync. Trains in 30 minutes.

---

## 4. The Unified Ladder

### 4.1 Same Identity, Same Reputation, Same Track

The unification is not metaphorical. It is architectural.

```
UNIFIED IDENTITY (ONEON):

  Every participant -- whether they entered through the education
  system or the refuge system -- has ONE ONEON identity.

  That identity carries:
    - DPC contribution score (earned, not bought)
    - Verifiable Credentials (skills, levels, aid eligibility)
    - Governance weight (in 505 DAO)
    - Reputation history (append-only, on-chain anchored)

  There is no field in the identity that says "refugee" or
  "student" or "developer." There is only "contributor."
```

### 4.2 Contribution Types Are Universal

Every contribution type is available to every participant. The system does not assume what someone can or cannot do based on how they entered.

| Contribution | Education Entry | Refuge Entry | Weight |
|---|---|---|---|
| Code | Write features, fix bugs | Same -- many displaced people are engineers | Structural Impact |
| Teaching | Mentor other learners | Teach language, local knowledge, survival skills | Weighted Resonance |
| Translation | Translate docs to new languages | Natural strength -- most refugees speak 2-4 languages | Consistent Energy |
| Coordination | Organize community events | Organize within displacement communities | Structural Impact |
| Documentation | Write guides and processes | Document local conditions, needs, solutions | Consistent Energy |
| Design | UX, visual, audio design | Same | Structural Impact |
| Resource Provision | Hosting, hardware, bandwidth | Physical space, local knowledge, community access | Consistent Energy |
| Field Operations | Volunteer at distribution | Peer support, mesh node maintenance | All three factors |

### 4.3 The Path from Refugee to Leader

This is not hypothetical. The architecture makes it inevitable for anyone who contributes consistently.

```
EXAMPLE PATH:

  WEEK 0: Amara arrives at an S0S intake point in Khartoum.
    No documents. Speaks Arabic, English, and basic French.
    - ONEON identity created (did:key)
    - Aid eligibility VC issued
    - Immediate needs: food kit + shelter assignment
    - Assessment deferred

  WEEK 2: Amara is stable. Assessment conversation happens.
    - Passions: teaching children, organizing community events
    - Skills: trilingual, basic smartphone literacy, community leadership
    - Ecosystem needs: Arabic translation (P1), community coordination (P2)
    - Path: Begin with Arabic translation of field worker toolkit

  WEEK 4: First 3 contributions verified.
    - Arabic translation of intake portal UI
    - Arabic translation of learner onboarding flow
    - Organized a community meeting to explain S0S to 40 new arrivals
    - Level: CONTRIBUTOR (DPC: 150)

  MONTH 3: Sustained contribution.
    - Translated 12 documents
    - Trained 8 new field workers in Arabic
    - Coordinated aid distribution at her community node
    - Level: BUILDER (DPC: 620)

  MONTH 8: Leading the Arabic localization domain.
    - Created a mentorship program for new translators
    - Proposed and won a DAO vote to add Tigrinya translation priority
    - Peer-reviewed 50+ contributions
    - Level: STEWARD (DPC: 2,400)

  At this point, Amara has the same governance weight as a
  developer in Berlin with a similar DPC score. Her vote counts
  equally. Her contributions are verified on-chain. Her
  credentials are portable -- if she moves to a Tusita community,
  her reputation comes with her.
```

---

## 5. Phase 1 Implementation Plan

Ten tasks. Each is the smallest deployable unit that delivers real value.

| # | Task | Priority | Est. Cost | Depends On | Agent Type |
|---|------|----------|-----------|------------|------------|
| 1 | **ONEON Identity MVP** -- did:key generation + basic VC issuance in React Native app. Offline-capable. Paper QR backup. | P1 | $800 | None | coder |
| 2 | **Conversational Skill Assessment** -- LLM-driven onboarding flow. Generates Passion-Skill Map. Stores results in ONEON identity as VC. | P1 | $600 | Task 1 | coder + architect |
| 3 | **Ecosystem Need Board** -- API endpoint that surfaces current ecosystem needs ranked by DPC demand signal. Web + mobile UI. | P2 | $400 | None | coder |
| 4 | **Contribution Tracker** -- Submit, review, verify contributions. DPC score calculation. Dashboard UI. | P1 | $700 | Task 1 | coder |
| 5 | **Peer Review System** -- Contributors review each other's work. Review quality scored. Integrates with DPC. | P2 | $500 | Task 4 | coder |
| 6 | **Advancement Badges** -- W3C VC 2.0 credentials issued on-chain when contributors reach new levels (Learner through Architect). | P2 | $300 | Tasks 1, 4 | coder |
| 7 | **Intake Portal** -- Mobile-first offline enrollment for refuge system. Identity creation + aid eligibility VC + paper backup. 10-minute flow. | P1 | $600 | Task 1 | coder |
| 8 | **Mesh Node Kit v0.1** -- Documented, reproducible Tier 1 community node (RPi + LoRa + solar). Build guide + provisioning script. | P2 | $500 | None | coder + architect |
| 9 | **Resource Allocation Contract** -- Solidity smart contract for aid distribution events. Nullifier registry. Bloom filter for offline. Deploy on Polygon zkEVM testnet. | P2 | $400 | None | coder |
| 10 | **Field Worker Toolkit** -- Android app for field workers: identity creation, VC issuance, aid distribution logging, offline sync queue. | P1 | $700 | Tasks 1, 7, 9 | coder |

**Total estimated cost: ~$5,500**

**Dependency graph:**

```
Task 1 (ONEON Identity) ─────┬──→ Task 2 (Skill Assessment)
                              ├──→ Task 4 (Contribution Tracker) ──→ Task 5 (Peer Review)
                              ├──→ Task 6 (Advancement Badges)
                              ├──→ Task 7 (Intake Portal) ──┐
                              └──→ Task 10 (Field Worker)  ◄─┘
                                        │
Task 9 (Resource Contract) ─────────────┘

Task 3 (Need Board) ── independent
Task 8 (Mesh Node Kit) ── independent
```

**Sequencing:** Tasks 1, 3, 8, 9 can start in parallel (no dependencies). Task 1 unlocks the largest dependency chain and should start first. Task 10 is the final integration point and ships last.

---

## 6. Key Design Decisions

### Decision 1: One ladder, not two systems

**Chosen:** Single advancement track shared by education and refuge participants.

**Why:** Separate tracks create a permanent underclass. "Refugee contributor" vs "regular contributor" is the exact hierarchy the system exists to dismantle. One ladder means equal governance weight, equal advancement, equal dignity.

**Alternative rejected:** Separate intake and advancement tracks with bridging mechanism. Simpler to implement but creates a two-tier system that contradicts the mission. The bridging step becomes a gate, and gates attract gatekeepers.

**Tradeoff:** Unified design is harder to build -- assessment must work for both a CS graduate and someone with no formal education. The LLM conversational assessment handles this better than any standardized test could, but it requires careful prompt engineering to avoid bias.

---

### Decision 2: Contribution IS curriculum (not contribution PLUS curriculum)

**Chosen:** No traditional learning materials. Learners advance by completing real contributions to the ecosystem.

**Why:** Traditional curricula create a gap between learning and doing. That gap is where people stall. If the first thing you do is contribute something real, you are immediately part of the system. The learning happens through the work.

**Alternative rejected:** Structured learning modules with contribution as capstone project. Safer, more predictable, easier to measure. But it recreates the school-to-work pipeline that already fails billions of people.

**Tradeoff:** Some learners will need more scaffolding than "here's a contribution, go." The system must pair low-experience contributors with mentors (who earn DPC for mentoring). The first contribution for a new learner should be scoped small enough to succeed -- translation of a single page, documentation of a single process, testing a single feature.

---

### Decision 3: DPC score decays without activity

**Chosen:** Governance weight and level standing decay over time without continued contribution.

**Why:** Static reputation creates aristocracy. Someone who contributed heavily two years ago and stopped should not outweigh someone contributing daily now. The river metaphor: power flows to active contributors.

**Alternative rejected:** Permanent reputation accrual (your score only goes up). Simpler, feels fair to past contributors. But it recreates the "early investor advantage" pattern where legacy position trumps current work.

**Tradeoff:** Contributors who take a break (illness, displacement, life events) lose standing. Mitigation: decay is gradual (not cliff), and the system can pause decay for documented hardship (DAO-approved). Returning contributors re-earn quickly because their skills still exist.

---

### Decision 4: Offline-first mesh over always-connected architecture

**Chosen:** Every critical operation (identity verification, aid distribution, contribution logging) works with zero internet connectivity.

**Why:** The refuge system must work in conflict zones where connectivity is the first casualty. An education system that requires internet excludes 2.6 billion people without reliable access.

**Alternative rejected:** Cloud-first with offline caching. Easier to build, richer features, better UX. But "offline caching" assumes connectivity as the default -- it breaks when offline is the norm, not the exception.

**Tradeoff:** Offline-first means eventual consistency. Two distribution points might not know about each other's nullifiers for hours. Double-dipping is possible in rare edge cases. Detected and corrected post-hoc. This is acceptable -- blocking all operations until sync completes is worse.

---

### Decision 5: ONEON identity, not a new identity system

**Chosen:** S0S uses ONEON as its identity layer. No separate identity system.

**Why:** Identity fragmentation is the enemy. If S0S has its own identity and ONEON has its own identity and Tusita has its own identity, contributors manage three reputations. One identity across the entire MY3YE ecosystem means one reputation, one governance weight, one portable credential set.

**Alternative rejected:** Lightweight S0S-specific identity with ONEON bridge. Faster to build, fewer dependencies. But the bridge becomes a friction point and inevitably drifts out of sync.

**Tradeoff:** S0S is blocked on ONEON identity MVP (Task 1). If ONEON development stalls, S0S stalls. Mitigation: Task 1 is a minimal did:key implementation that can start as S0S-specific and merge into ONEON later. The key format and VC schema are ONEON-compatible from day one.

---

### Decision 6: 505 DAO governance, not benevolent dictatorship

**Chosen:** All ecosystem need prioritization, aid eligibility rules, and advancement criteria are governed by 505 DAO (DPC-weighted voting).

**Why:** The system must be trustworthy to people who have been failed by every institution they have encountered. "Trust us, we'll do the right thing" is not credible. On-chain governance with contribution-weighted voting is verifiable.

**Alternative rejected:** Founder-governed with community advisory. Faster decisions, simpler ops, avoids governance theater. But "we'll decentralize later" never happens, and centralized control over aid distribution is exactly the corruption vector the system exists to prevent.

**Tradeoff:** DAO governance is slow. Emergency decisions (natural disaster response, sudden displacement) cannot wait for a 7-day voting period. Mitigation: Emergency powers delegated to Steward-level contributors in the field, with post-hoc ratification by DAO. Constitutional constraint: emergency powers auto-expire after 72 hours without ratification.

---

## Appendix: Relationship to Existing Specs

| Document | Relationship |
|----------|-------------|
| [IPL Spec](../projects/sos-systems/integrity-preservation-layer.md) | Deep technical spec for refuge/extraction cryptography (identity, records, aid distribution, mesh). This architecture brief is the higher-level design that the IPL implements. |
| [505 Systems YAML](../universe/projects/505-systems.yaml) | Universe registry entry. Describes 505 as governance organism. This brief extends 505's scope to include education + refuge as its two primary systems. |
| [ONEON YAML](../universe/projects/oneon.yaml) | Identity layer dependency. S0S uses ONEON's five-layer architecture. Layer 1-2 sufficient for Phase 1. |
| [Tusita YAML](../universe/projects/tusita.yaml) | Physical anchor. Tusita communities host S0S infrastructure nodes and serve as safe harbor locations. |
| [MY3YE BRAND.md](/mnt/media/projects/my3ye-web/BRAND.md) | Voice and tone guide. "For the ones who were handed nothing -- we built this for us." S0S is the most literal expression of this line. |
| [Governance Finalization Plan](../otto_core/governance_finalization_plan.md) | S0S governance rules will be ratified through this 24-week process alongside ecosystem constitution and core rules. |

---

*The river moves. Move with it.*

*Architecture by Otto | Review by Mev before implementation | Next step: Task 1 (ONEON Identity MVP) kickoff*

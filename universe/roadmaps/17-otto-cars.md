# Otto Cars — Comprehensive Roadmap
*Community-governed automated taxis. Build Your Own Car. The Fleet belongs to the city.*
*Last updated: 2026-03-16*

---

## Current State
**STATUS: CONCEPT** — Vision fully defined. Universe YAML documented. Zero vehicles. No manufacturer relationships. No regulatory research completed. No software built.

Otto Cars is a long-horizon project. It cannot launch until Ottolabs has operational manufacturing and Tusita has a physical location. Both of those are themselves 1–2 year projects from today. Be honest about this: Otto Cars is a 3–5 year play. The work we do now is research, design, and governance framework — not fleet deployment.

The question that defines the next three years: **can Ottolabs manufacturing capability mature fast enough to make community vehicle production viable before this vision becomes obsolete?**

---

## The Problem
Uber takes 25–40% of every ride. The driver gets the rest after paying for the car, insurance, fuel, and maintenance. The company that owns the dispatch algorithm extracts rent from every journey — forever.

The car industry runs the same playbook from the manufacturer side. Planned obsolescence, proprietary diagnostics, repair monopolies, and annual model refreshes designed to make last year's vehicle feel inadequate.

Otto Cars attacks both extraction points simultaneously.

---

## Vision
**Community Automated Taxis:** Electric/autonomous vehicles owned by the community treasury (Tusita / 505 Systems DAO), dispatched by Otto AI, zero-commission for operators. Revenue flows to vehicle contributors, governance participants, and maintenance nodes — not a distant algorithm owner.

**Build Your Own Car (BYOC):** Open-source vehicle designs that communities can manufacture using Ottolabs facilities. Start from a pre-configured base (chassis, drivetrain, power system), customize specs, get it built by the community factory, take delivery. No planned obsolescence. No proprietary repair monopoly. Full documentation, open parts.

Both products share one philosophy: **your city's mobility, owned by your city.**

---

## Dependencies (Hard)

Otto Cars cannot ship without these:

| Dependency | What's Needed | Roadmap Status | Unlock Condition |
|------------|--------------|----------------|-----------------|
| **Ottolabs** | Manufacturing facility, workshop, eventual vehicle production capability | Concept → Phase 3 (1–2yr) | First Ottolabs workshop operational |
| **Tusita** | Physical deployment location for pilot fleet | Concept → Phase 2 (6 months) | First Tusita location secured |
| **505 Systems** | DAO governance for fleet decisions, pricing, expansion | Concept → operational | 505 Systems governance live |
| **ONEON** | Vehicle identity, operator identity, encrypted dispatch | Concept → early build | ONEON network operational |

**Soft dependencies:** Otto Travel (booking integration), Otto AI dispatch, KOIN treasury (funding fleet purchase)

---

## Phase 1 — Research & Specification (0–365 days)
**Goal:** Know exactly what we're building and why it can work. No vehicles purchased. No manufacturing started. This phase produces the design, the governance framework, and the legal clarity needed to execute in Phase 2.

**Trigger condition:** Can begin immediately. No upstream dependency required for research work.

### Why this phase first
Regulatory complexity around autonomous vehicles and community fleet ownership is severe and jurisdiction-specific. A wrong assumption here cascades into wasted capital and delayed launches. Spend 12 months getting this right before spending a dollar on hardware.

### Milestones

**M1 — Regulatory landscape research (Days 1–90)**
- Autonomous vehicle legal status in 3 pilot jurisdictions: Sri Lanka, Dubai, Portugal
- Per-jurisdiction: licensing requirements, insurance mandates, permitted operational zones
- Community ownership structures: which legal entity type (DAO, cooperative, company) can own and operate a commercial fleet per jurisdiction
- Electric vehicle incentives: what subsidies, tax structures, or import duty exemptions apply
- Output: Regulatory feasibility matrix — which jurisdiction is lowest-friction for Phase 2 pilot

**M2 — Open-source EV platform analysis (Days 30–120)**
- Research available open-source and commercial EV platforms suitable for community fleet use
- Candidates: OSVehicle Tabby EVO, Strom R3, Electra Meccanica, academic open-source platforms
- Assessment criteria: parts availability, repairability, low-speed urban suitability, total cost of ownership, community manufacturability
- BYOC base configurations: define 3 pre-configured bases
  - Base A: Urban micro-vehicle (2-seat, ≤60km/h, ≤200km range) — taxi, short-trip
  - Base B: Community utility (4-seat, ≤120km/h, ≤300km range) — standard taxi, family transport
  - Base C: Cargo/utility (van format, ≤120km/h, ≤250km range) — goods, Tusita logistics
- Output: BYOC base specification document — chassis, drivetrain, power, target BOM for each base

**M3 — Tusita pilot design (Days 60–180)**
- Define the Otto Cars integration model for Tusita Phase 3 (6–18 months into Tusita operation)
- Fleet size target for pilot: 5–15 vehicles (start small, prove model)
- Community ownership structure: how does Tusita community treasury fund, own, and govern fleet?
- Operator model: islanders operate vehicles, earn without commission extraction. Define earnings model.
- Dispatch system spec: Otto AI manages routing, pricing, scheduling. Define API requirements.
- Integration points: Otto Travel (external bookings), ONEON (operator identity), KOIN (payments)
- Output: Tusita Pilot Design Document — fleet size, economics, governance, tech requirements

**M4 — Community governance framework (Days 90–180)**
- Fleet governance model: what decisions are community-made vs. Otto AI automated?
  - Community votes: route expansions, fleet size increases, pricing bands, new vehicle models
  - AI automated: real-time dispatch, dynamic pricing within approved bands, maintenance scheduling
- Contributor earnings model: vehicle contributors (who fund vehicle purchase) earn revenue share
  - Define the formula: % to vehicle contributor, % to operator, % to community treasury, % to maintenance node
- Dispute resolution: what happens when an operator damages a vehicle? Insurance model?
- Output: Fleet Governance Charter (v0.1) — to be ratified by Tusita founding cohort

**M5 — Waitlist & community interest (Days 150–365)**
- BYOC interest waitlist on ottocars.xyz (or otto.lk/cars)
- Taxi contributor waitlist: community members who want to fund a vehicle in the fleet
- Operator interest: potential islanders and contributors who want to drive
- Target: 500+ interested parties across all three categories before Phase 2 begins
- Community conversation: publish base specs, regulatory findings, governance framework — get feedback

### Success Criteria
- Regulatory feasibility matrix complete: 1 jurisdiction identified as Phase 2 target
- BYOC base specifications defined (3 bases, costed at volume)
- Tusita Pilot Design Document complete
- Fleet Governance Charter v0.1 published
- 500+ waitlist (across vehicle contributors, operators, BYOC interest)

### Capital Required
~$5K–$15K (research travel, legal consultation in pilot jurisdiction, domain/website, rendered vehicle concepts)
Source: Assistive Tech operating revenue

---

## Phase 2 — Tusita Pilot Fleet (1–2 years)
**Goal:** 5–15 community-owned EVs operating at the first Tusita location. Otto AI dispatching. Zero-commission earnings flowing to contributors and operators.

**Trigger condition:** Tusita first physical location secured (Tusita Phase 2). Target: 12–18 months from today.

### Why Tusita first
Tusita is a controlled environment. The community is known, identity is verified via ONEON, and the governance structure is already operating. Launching a community fleet in an open city first introduces regulatory exposure, anonymous operator risk, and governance complexity that is unnecessary before the model is proven. Tusita is the sandbox. Get it right there, then expand.

### Milestones

**M1 — Fleet funding and vehicle acquisition (Months 13–18)**
- Community treasury vote: allocate KOIN funds for first fleet purchase (target 5 vehicles)
- If no Ottolabs manufacturing yet: source from reputable EV manufacturers or open-platform assemblers
- Vehicle contributor model: islanders and supporters can fund individual vehicles, earning revenue share
- Legal structure: vehicles owned by community entity (cooperative or DAO-held company), not individuals
- Insurance: commercial fleet insurance for pilot jurisdiction
- Target: 5 vehicles acquired, registered, insured

**M2 — Otto AI dispatch system (Months 12–18)**
- Build Otto dispatch: ride request → AI routing → operator assignment → completion → payment
- Integration with Otto Travel booking for external Tusita visitors
- ONEON integration: operator identity, passenger identity (optional), dispute resolution trail
- Payment rail: KOIN-native with fiat bridge for visitors not yet on KOIN
- Dashboard: community members can see fleet status, earnings, utilization — transparent governance
- Target: Dispatch system tested internally with 3 vehicles before public launch

**M3 — Operator onboarding (Months 16–20)**
- First operators: Tusita Islanders who pass basic vehicle competency check
- Operator earnings: direct, without commission extraction. Earnings split defined in governance charter.
- Training: how to use Otto dispatch app, vehicle maintenance basics, community conduct standards
- Target: 10+ trained operators from founding Islander cohort

**M4 — Fleet launch and initial operation (Months 18–24)**
- Fleet public to Tusita residents and Otto Travel visitors
- Live metrics: rides completed, earnings distributed, vehicle utilization, community treasury growth
- Feedback loop: weekly community review of fleet operations, monthly governance vote on adjustments
- Comparison data: document what operators would have earned on Uber/Lyft vs. Otto Cars. Publish the number.
- Target: 3 months of operation with ≥50 rides/week and positive community treasury balance

**M5 — BYOC first order (Months 18–24, parallel)**
- Open BYOC order intake for Base A or Base B configuration
- Order management: customer selects base, customizes specs, deposit collected
- Manufacturing partner: Ottolabs workshop (if operational) or contracted external assembler
- First delivery target: 1 BYOC vehicle completed and delivered to order
- Document everything: cost, timeline, quality issues. This is the template for all future builds.

### Success Criteria
- 5+ community-owned EVs operating at Tusita
- Otto AI dispatch live with ≥50 rides/week at steady state
- Operator earnings documented and compared to incumbent platforms (publish the delta)
- First BYOC order delivered
- Fleet governance making real community decisions (pricing, route expansion, maintenance)
- Community treasury net-positive from fleet operations within 3 months

### Capital Required
~$150K–$400K (5 vehicles at $30–80K each, dispatch software, insurance, operator training)
Source: KOIN community treasury + vehicle contributor funding model + Assistive Tech surplus

---

## Phase 3 — Open Platform & Community Manufacturing (2–4 years)
**Goal:** BYOC designs published openly. Community manufacturing producing vehicles. Network expanding beyond Tusita.

**Trigger condition:** Ottolabs workshop operational (Phase 3 of Ottolabs). Tusita pilot proven and running for 6+ months.

### Milestones

**M1 — BYOC designs open-sourced (Years 2–3)**
- All three base configurations published under open license (similar to CERN OHL or similar)
- Full documentation: BOM, assembly instructions, diagnostic protocols, repair guides
- Community can fork, modify, improve designs — contributions governed by 505 Systems
- Any Ottolabs-affiliated workshop globally can build from these designs
- Goal: design is not a moat. The community network is.

**M2 — Ottolabs vehicle workshop (Years 2–3)**
- Ottolabs physical space scales from device workshop to vehicle-capable workshop
- Capability added: chassis welding/fabrication, EV powertrain assembly, body panel work
- First community-manufactured vehicle: proof that community production is viable
- Cost comparison: community-manufactured Base A vs. commercially purchased equivalent — document delta

**M3 — Second community fleet (Years 2–3)**
- Expand fleet model to a second Tusita location or aligned community partner
- Lessons from Tusita pilot applied: improved governance, better dispatch, refined earnings model
- Target: 15–30 vehicles across 2 locations
- First non-Tusita community onboarded (partner city or intentional community)

**M4 — Otto Cars platform open to external communities (Years 3–4)**
- Any community can fork the governance framework and deploy an Otto Cars fleet
- Otto AI dispatch offered as a service to community fleets (fleet governance stays community-owned)
- Network effects: more communities → shared vehicle designs → lower production costs → better platform

**M5 — BYOC production at scale (Years 3–4)**
- 20+ BYOC orders fulfilled per year across Ottolabs workshop network
- Custom configurations: communities can commission bespoke vehicles for specific needs
- Repair network: open designs mean any qualified workshop can service any BYOC vehicle
- Parts sovereignty: avoid single-supplier dependencies on proprietary components

### Success Criteria
- BYOC Base A, B, C designs fully open-sourced
- Community-manufactured vehicle completed and documented
- 2+ community fleet deployments operational (beyond Tusita pilot)
- 20+ BYOC orders fulfilled annually
- External community onboarded to Otto Cars platform without Otto direct involvement

### Capital Required
~$300K–$800K (vehicle workshop equipment, fleet expansion, platform development, open manufacturing documentation)
Source: Fleet operating surplus + KOIN treasury raises + BYOC order revenue

---

## Phase 4 — Community Transport Network (4+ years)
**Goal:** Multiple Tusita locations and allied communities operating connected Otto Cars fleets. Community-owned transport as a real economic alternative to incumbent platforms.

### Milestones

**M1 — Multi-location network (Years 4–5)**
- 5+ fleet deployments across Tusita locations and partner communities globally
- Shared routing: Otto AI aware of multi-location trips (inter-community transport)
- Cross-community operator mobility: islanders can operate in any fleet that accepts their ONEON identity
- Network income: communities with surplus vehicles can loan fleet capacity to others via DAO vote

**M2 — Autonomous dispatch integration (Years 4–5)**
- As autonomous vehicle technology matures, integrate AV capability into existing fleet
- Community vote required to introduce any autonomous operation (no unilateral AI decisions)
- Human operators remain primary through this phase — AV assists, does not replace
- Regulatory: jurisdiction-by-jurisdiction AV approval as frameworks mature

**M3 — BYOC standard as industry benchmark (Years 5+)**
- Open-source designs adopted beyond Otto Cars community
- Community manufacturing cost per vehicle ≤60% of equivalent commercial purchase
- Repair costs: open parts + community workshops → measurable savings vs. proprietary repair networks
- Recognition: Otto Cars model cited in transport governance conversations globally

**M4 — Full economic comparison published (Year 5)**
- End-to-end study: operator earnings in community fleet vs. Uber/Lyft over 4 years
- Vehicle ownership cost: BYOC community-manufactured vs. commercial purchase over 5 years
- Community treasury growth: cumulative fleet income → how many community projects funded
- Publish as open research. This is how the model spreads.

### Success Criteria
- 5+ fleet deployments across multiple communities
- 100+ vehicles in community ownership network-wide
- Community treasury income from fleets funding downstream projects (Tusita expansion, Ottolabs, etc.)
- BYOC at economic parity or better vs. commercial alternatives
- At least one community fleet fully self-governing without Otto direct support

### Capital Required
~$1M–$3M (fleet scale, AV integration, cross-network infrastructure, open manufacturing expansion)
Source: Fleet operating surplus, KOIN treasury, community pre-orders, selective grants from transport/cooperative ecosystem

---

## Key Metrics

| Metric | Phase 1 (1yr) | Phase 2 (2yr) | Phase 3 (4yr) | Phase 4 (5yr+) |
|--------|--------------|--------------|--------------|----------------|
| Vehicles in community ownership | 0 | 5–15 | 30–80 | 100+ |
| Fleet locations | 0 | 1 (Tusita) | 2–3 | 5+ |
| Rides per week (network) | 0 | 50+ | 200+ | 1,000+ |
| Operator earnings vs. Uber (delta) | N/A | Documented | +25–35% better | +35%+ |
| BYOC builds completed | 0 | 1 | 20+ | 100+ |
| Community treasury income (annual) | 0 | First positive | $50K–150K | $500K+ |
| Communities on platform | 0 | 1 | 2–3 | 5+ |

---

## BYOC Base Configurations (Preliminary)

| Base | Format | Max Speed | Range | Target BOM | Use Case |
|------|--------|-----------|-------|-----------|---------|
| **Base A — Urban Micro** | 2-seat compact | 80 km/h | 150 km | $12K–18K | Short-trip taxi, island shuttles, commuter |
| **Base B — Community Sedan** | 4-seat | 130 km/h | 300 km | $22K–32K | Standard taxi, family transport, visitor pickup |
| **Base C — Cargo/Utility** | Van/truck | 120 km/h | 250 km | $28K–40K | Goods delivery, Tusita logistics, cargo taxi |

*All BOM estimates at community workshop volume (50+ builds). Commercial purchase of equivalent: $1.5–2× these figures.*

---

## Governance Model

**What the community decides (DAO vote):**
- Fleet expansion: add vehicles, enter new locations, retire old vehicles
- Pricing bands: minimum and maximum fare ranges (AI dispatches within bands)
- Earnings split: % to vehicle contributors, % to operators, % to treasury, % to maintenance
- Platform partnerships: which communities can join the network
- BYOC production queue: which builds get factory priority

**What Otto AI handles autonomously:**
- Real-time dispatch: nearest available operator, optimal routing
- Dynamic pricing within approved bands (surge pricing only up to community-set ceiling)
- Maintenance scheduling: mileage-based service reminders, anomaly detection
- Operator performance tracking (private — operator sees their own data, treasury sees aggregates)

**What neither controls:**
- Operator identity (ONEON-held, self-sovereign)
- Passenger data (minimal collection, encrypted, community-auditable retention policy)

---

## Risks

### High Risk
**Capital intensity** — Community EV fleet acquisition costs $30–80K per vehicle. A 10-vehicle pilot requires $300K–800K in community treasury or contributor funding before a single ride is completed. This is the biggest barrier. Mitigation: start with 5 vehicles, use contributor funding model to distribute capital load, ensure fleet is revenue-generating within 90 days of launch.

**Regulatory environment** — Commercial fleet operation, autonomous vehicles, and community ownership structures each carry distinct regulatory exposure. A single hostile regulator can kill a fleet deployment. Mitigation: choose the most permissive jurisdiction for Phase 2 pilot, avoid autonomous operation until regulations clearly permit it, structure community ownership through locally-recognized legal entities.

**Ottolabs dependency** — BYOC manufacturing is completely blocked until Ottolabs has a vehicle-capable workshop. That's a 2–3 year dependency chain. Mitigation: Phase 2 acquires vehicles commercially (not manufactured). Manufacturing becomes BYOC path in Phase 3 when workshop exists.

### Medium Risk
**Autonomous vehicle technology maturity** — Full self-driving in community deployment requires both technical maturity and regulatory approval. Both are uncertain on 3–5 year horizons. Mitigation: phase autonomous capability as optional upgrade. Human operators first. AI dispatch replaces the algorithm, not the human.

**Community governance fatigue** — DAO governance sounds compelling; running one is operationally demanding. Decisions take time. Contentious votes happen. Mitigation: limit governance surface area. Community decides strategy; Otto AI handles execution. Don't vote on every ride.

**Insurance and liability** — Commercial fleet insurance is expensive, and community ownership structures complicate liability assignment. Mitigation: work with specialized fleet insurance brokers, define liability in governance charter before first vehicle is acquired.

### Lower Risk
**Competition from incumbents** — Uber and Lyft have massive network effects. Otto Cars isn't competing for the entire market — it's building a parallel system that works for communities. The first win is Tusita; the second is aligned communities. Scale comes from replication, not head-on competition.

**Vehicle reliability** — Community-owned fleets live or die on maintenance. A breakdown that a private driver absorbs becomes a governance issue. Mitigation: build maintenance tracking into dispatch from day one, create clear maintenance contributor role with compensation, keep vehicles under 5 years old initially.

---

## The Irreducible Insight

Uber's genius was not software. It was convincing drivers to provide the capital (the car) while the platform captured the margin (the algorithm). The community owns nothing. The driver takes all the depreciation and none of the platform appreciation.

Otto Cars reverses the ownership stack. The community owns the vehicle. The community owns the dispatch rules. The operator earns without extraction. The city's mobility stays in the city.

This is not an incremental improvement on rideshare. It is a different theory of who the infrastructure belongs to.

The fleet is not a product. The fleet is proof that collective ownership works at the operational layer — not just in a whitepaper.

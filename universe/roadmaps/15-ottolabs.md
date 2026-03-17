# Ottolabs — Comprehensive Roadmap
*Physical means of production. Collectively owned hardware, robotics, factories, farms, energy.*
*Last updated: 2026-03-16*

---

## Current State
**STATUS: CONCEPT** — Vision fully defined. Inception article published (2026-03-05). Universe YAML detailed. Zero hardware prototyped. No manufacturer relationships. No factory. No farm.

Ottolabs is the most capital-intensive project in the ecosystem. It requires physical materials, manufacturing partners, real estate, and engineering talent. None of that exists yet. What exists is the vision, the roadmap, and the revenue engine that will fund it: Assistive Technologies (WebAssist, TechAssist, etc.).

The question that defines the next two years: **can Assistive Tech revenue scale fast enough to fund the Puck prototype before outside capital is needed?**

---

## Revenue Bridge: Assistive Tech → Ottolabs R&D

Ottolabs does not generate revenue. Assistive Technologies do. The bridge is explicit:

| Revenue Source | Target MRR | Feeds |
|----------------|-----------|-------|
| WebAssist | $20K/mo (Phase 1 target) | Puck hardware spec + ODM engagement |
| TechAssist | $10K/mo (Phase 2 target) | Puck prototype production (100 units) |
| App Assist + Brand Assist | $15K/mo (Phase 3 target) | Small-batch manufacturing (1,000 units) |

**Rule:** No Ottolabs hardware spend until corresponding Assistive Tech revenue tier is achieved. This keeps development funded without external debt or dilutive capital.

**Phase 1 unlock condition:** WebAssist at $10K+ MRR.
**Phase 2 unlock condition:** Combined Assistive Tech at $25K+ MRR.
**Phase 3 unlock condition:** $50K+ MRR + community pre-order capital raised.

---

## Dependencies
- **Hard deps:** S0S Systems (DAO governance for factory output and resource allocation)
- **Upstream needed:** WebAssist revenue (funds all hardware development)
- **Soft deps:** ONEON (device identity and auth), Koink/KOIN (community treasury), Tusita (first deployment location)
- **Blocks downstream:** Tusita physical infrastructure (needs Ottolabs devices + farms), Otto Properties (construction robotics), Shakrah (Otto Band), Panik (hardware mesh nodes)

---

## Phase 1 — Specification & Foundations (0–180 days)
**Goal:** Know exactly what we're building and how. No hardware purchased yet — this phase is pure design, research, and manufacturer relationships.

### Why this phase first
Hardware is expensive to iterate. A wrong design decision at prototype stage costs $5K. At production stage it costs $500K. This phase eliminates all guesswork before a single dollar is spent on components.

### Milestones

**M1 — Otto Puck complete specification (Days 1–60)**
- SBC selection: Raspberry Pi CM4 vs Rockchip RK3588S vs Allwinner H618 — costed and compared
- Connectivity: WiFi 6 + Bluetooth 5.2 + optional Ethernet (USB-C dongle)
- Power: USB-C PD + optional 3000mAh internal battery for portable operation
- Compute: Target 4-core ARM, 4GB RAM, 32GB eMMC minimum
- Enclosure: Dimensions locked (target: 85mm × 55mm × 20mm — credit card footprint, 3× thick)
- BOM (Bill of Materials): Full component list costed. Target ≤$45/unit at 100-unit volume
- OS choice: Debian ARM or Ubuntu Server 24.04 LTS — minimal, headless

**M2 — Puck software stack documented (Days 30–90)**
- Otto agent version that runs on Puck hardware (memory-constrained build)
- ONEON identity integration spec: device generates keypair at first boot, registers to ONEON
- Compute contribution protocol: how Puck contributes to distributed Otto network
- Governance weight: running a Puck earns DPC in S0S. Exact formula defined.

**M3 — ODM/manufacturer research (Days 60–120)**
- Target: 3–5 manufacturers contacted in Sri Lanka, India, or SE Asia
- Criteria: min 100-unit runs, CM4 or equivalent experience, export capability
- Legal: understand import/export requirements for prototype units
- Target: 1 manufacturer relationship established, quote received for 100 prototype units

**M4 — Pre-order / crowdfunding design (Days 90–150)**
- Crowdfunding model: Kickstarter vs direct pre-order on ottolabs.xyz
- Pricing: Puck at $79 early backer / $99 retail. Target: 1,000 units × $79 = $79K capital
- Governance token: early backers receive DPC weight in S0S factory governance
- Campaign narrative and creative assets designed (product renders, explainer)

**M5 — Community infrastructure (Days 120–180)**
- ottolabs.xyz domain + landing page live (device renders, mission, pre-order waitlist)
- 2,000+ waitlist subscribers from MY3YE/Web3 audience
- Puck specification published openly (transparency builds trust)

### Success Criteria
- Complete Puck hardware spec (BOM, enclosure, connectivity, power) — all decisions locked
- Software stack defined and documented
- 1 manufacturer relationship with quote for 100 units
- 2,000+ waitlist subscribers
- Assistive Tech at ≥$10K MRR (revenue unlock condition)

### Capital Required
~$5K–$15K (design tools, legal, travel for manufacturer meetings, website, renders)
Source: WebAssist operating revenue

---

## Phase 2 — Prototype & Pre-Order (180–365 days)
**Goal:** 10 functional Puck prototypes exist and are tested. Pre-order campaign launched.

### Milestones

**M1 — First 10 prototype units (Days 180–270)**
- Components sourced and assembled with ODM partner
- Otto agent boots and runs on Puck hardware
- ONEON identity enrollment: Puck generates keypair, registers with ONEON network
- Compute contribution demonstrated: Puck can run lightweight inference tasks, report to network
- Stress testing: 72-hour uptime test, thermal management validation

**M2 — Tusita pilot deployment (Days 240–300)**
- 3 Pucks shipped to Tusita first location (if operational) or Mev for home testing
- Real-world testing: mesh networking, battery life, heat management
- Otto Home prototype: 1 unit installed as home hub + mesh gateway
- Feedback loop: document every hardware issue, revise BOM before production run

**M3 — Pre-order campaign live (Days 270–330)**
- Crowdfunding/pre-order goes live at target of 1,000 unit commitments
- Early backer pricing: $79/unit (first 500) → $89/unit (next 500) → $99 retail
- DPC governance weight included: each Puck backer gets 100 DPC at S0S launch
- Campaign targets: $79,000 in pre-orders (1,000 units × $79)

**M4 — Manufacturing partner confirmed (Days 300–365)**
- ODM locked for production run based on pre-order demand
- Production timeline committed: units delivered within 90 days of production start
- Quality assurance protocol defined
- Packaging and shipping logistics planned

### Success Criteria
- 10 functional Puck prototypes built and validated
- Otto agent + ONEON enrollment working on hardware
- 1,000+ pre-orders received ($79K+ in community capital)
- Manufacturing partner confirmed with production commitment
- Tusita pilot deployed (even minimal: 3 units in active use)

### Capital Required
~$15K–$40K (component sourcing, ODM engagement fees, prototype assembly)
Source: Assistive Tech revenue ($25K+ MRR) + any pre-order deposits

---

## Phase 3 — Small-Batch Manufacturing & Farm Pilot (1–2 years)
**Goal:** 1,000 Pucks shipped. First Ottolabs physical space operational. Farm pilot producing food.

### Milestones

**M1 — Puck v1.0 production run (Months 13–18)**
- 1,000 units manufactured and shipped to pre-order backers
- QA at scale: ≥98% pass rate, clear RMA/warranty process
- Compute network: 800+ Pucks contributing to distributed Otto network
- Community: first governance vote enabled by Puck-holder DPC weight

**M2 — Otto Home v1 (Months 12–18)**
- Home hub based on lessons from Puck + new hardware spec
- Integrates: mesh Wi-Fi router, Otto agent, local NAS, energy monitoring
- First deployment: Tusita residential units
- Target: 100 units in Tusita community + pre-order for general market

**M3 — First Ottolabs factory/workshop space (Months 12–20)**
- Secure first physical Ottolabs workspace — target: co-located with Tusita first location
- Not a full factory yet: a workshop. 500–1,000 sqft assembly and R&D space.
- Install: soldering, assembly, basic CNC for enclosures, 3D printing
- Governance: first S0S factory decisions — what gets built, at what quantities
- First employee/contributor: 1 hardware engineer hired or brought in as contributor

**M4 — Ottolabs Farm Pilot with Tusita (Months 14–22)**
- Partner with Tusita first location on 500–1,000 sqft vertical farming pilot
- Technology stack: hydroponic trays + LED grow lights + automated nutrient dosing
- Output: leafy greens, herbs — target 30% of Tusita salad consumption on-site
- Otto monitoring: sensor array feeding data to Otto agent (yield, nutrients, energy)
- Learning: document everything. This becomes the blueprint for Farm v2.

**M5 — Puck v1.5 / Otto Band spec (Months 18–24)**
- Puck v1.5: cost reduction pass based on production learnings, BOM ≤$35/unit
- Otto Band specification: biometric wearable (HR, SpO2, sleep, activity)
- Shakrah integration design: Band data feeds directly into Shakrah wellness protocols
- ODM conversations started for Band production

### Success Criteria
- 1,000 Puck units shipped
- 800+ Pucks actively contributing compute to network
- Workshop operational at Tusita (or standalone) with 1 full-time contributor
- Farm pilot producing food (even 100kg/month is proof of concept)
- S0S factory governance making at least 3 real production decisions
- $50K+ MRR from Assistive Tech (funding ongoing hardware development)

### Capital Required
~$100K–$250K (production run, workshop space, farming equipment, first employee)
Source: Pre-order capital ($79K) + Assistive Tech surplus + possible community KOIN raise

---

## Phase 4 — Scale: Full Production Lines & Sovereignty Stack (2–5 years)
**Goal:** Ottolabs is the physically productive layer of the civilization. Community owns the machines.

### Milestones

**M1 — Otto Band v1 shipped (Year 2–3)**
- Biometric wearable in production. Shakrah integration live.
- 5,000+ units shipped. Shakrah practitioners using Band data in sessions.

**M2 — Robot Tier 3 (Agricultural) deployed (Year 2–3)**
- First agricultural robots deployed at Tusita farms
- Automated harvesting, soil monitoring, nutrient management
- Food sovereignty: ≥30% of Tusita community food produced on-site
- Cost reduction per unit of food: measurable and documented

**M3 — Custom silicon design (Year 3–4)**
- Puck v2: custom ASIC or FPGA-based compute chip
- Target: 2× performance, 0.5× cost vs Puck v1 at scale
- Partners: fabless design house (TSMC 7nm or similar)
- This is a $3–10M investment — requires community treasury or institutional backing

**M4 — Distributed factory network (Year 3–5)**
- 3–5 Ottolabs workshop/factory locations globally (Sri Lanka + 1-2 international)
- Each co-located with a Tusita community location
- Combined output: 100,000+ devices/year across all product lines
- DAO-governed output: 505 Systems votes determine production allocations quarterly

**M5 — Energy sovereignty infrastructure (Year 3–5)**
- Solar arrays at all Ottolabs/Tusita locations
- Wind where viable. Battery storage at all locations.
- Target: ≥80% renewable energy at all Ottolabs facilities
- Excess energy sold back to grid — income for community treasury

**M6 — Otto Tower deployed (Year 4–5)**
- Community-scale compute unit for Tusita locations and distributed communities
- Runs local Otto AI cluster, mesh backbone, renewable energy node
- Target: 1 Tower per Tusita location (≥5 deployed)

**M7 — $10M+ in collectively-owned productive assets (Year 5)**
- Sum of: workshop/factory value, equipment, devices in production, farms, energy infrastructure
- Governed by S0S. No single owner. Distributed to contributors via DPC weight.

### Success Criteria
- 50,000+ Ottolabs devices in active use globally
- Collective ownership: 50,000+ contributors hold DPC weight from Ottolabs assets
- ≥3 Ottolabs factory locations operational
- Food production covering ≥30% of Tusita community needs
- Energy ≥80% renewable at all facilities
- $10M+ in collectively-owned productive infrastructure
- Robot Tier 1 (humanoid) prototype contract signed

### Capital Required
~$3M–$10M (custom silicon, factory scale-up, robotics R&D, energy infrastructure)
Source: Community KOIN raises, Otto Travel/Properties revenue, Assistive Tech surplus, selective institutional investment with community governance terms

---

## Device Roadmap

| Device | Phase | Target BOM | Target Price | Use Case |
|--------|-------|-----------|-------------|----------|
| Otto Puck v1 | Phase 2–3 | $45 | $79–99 | Portable compute, ONEON node, network contributor |
| Otto Home v1 | Phase 3 | $80 | $149 | Home hub, Tusita mesh, energy monitor |
| Otto Band v1 | Phase 4 | $40 | $89 | Biometrics, Shakrah, identity layer |
| Otto Buds | Phase 4 | $35 | $79 | Ambient AI, language layer |
| Otto Glasses | Phase 4 | $80 | $199 | AR vision layer, Otto agent in-field display |
| Otto Ring | Phase 4 | $25 | $69 | Payments, biometric identity, health monitoring |
| Otto Puck v2 | Phase 4 | $25 | $59 | Custom silicon, 2× perf, lower cost |
| Otto Phone | Phase 4–5 | $120 | $249 | ONEON-native mobile device |
| Otto Tower | Phase 4–5 | $400 | $799 | Community compute anchor |
| Otto Satellites | Phase 5+ | TBD | Collectively owned | Orbital compute |

---

## Robotics Roadmap

| Tier | Description | Phase | Application | Complexity |
|------|-------------|-------|-------------|------------|
| 3 | Agricultural harvesters | Phase 3–4 | Tusita farm automation | Medium — established technology |
| 2 | Industrial arms/fabricators | Phase 4 | Factory manufacturing | Medium-high |
| 1 | Humanoid workers/builders | Phase 4–5 | Tusita construction, operations | Very high — 5+ year horizon |
| 4 | Micro-scale swarm | Phase 5 | Medical, environmental | Experimental |

*Note: Start with Tier 3 (agricultural). It has the clearest immediate value (food), the most mature technology (existing vertical farming robotics to learn from), and the most direct tie to Tusita community needs.*

---

## Manufacturing Model Evolution

| Phase | Model | Who Owns | Scale |
|-------|-------|----------|-------|
| Phase 1–2 | ODM partner, commodity SBC | ODM (contracted) | 10–100 units |
| Phase 3 | ODM + own workshop assembly | Community (Ottolabs DAO) | 1,000–10,000 units |
| Phase 4 | Own production lines, custom parts | Community | 10,000–100,000 units |
| Phase 5 | Custom silicon, distributed factories | Community | 100,000+ units |

---

## Key Metrics

| Metric | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|
| Assistive Tech MRR | $10K | $25K | $50K | $100K+ |
| Puck units produced | 0 | 10 (proto) | 1,000 | 50,000+ |
| Pucks on network | 0 | 10 | 800+ | 40,000+ |
| Factory space | 0 | 0 | 1 workshop | 3–5 factories |
| Farm food output | 0 | Pilot design | 30% Tusita diet | 30%+ multi-location |
| DPC contributors via hardware | 0 | 10 | 1,000 | 50,000+ |
| Collectively-owned asset value | $0 | $50K | $500K | $10M+ |

---

## Risks

### High Risk
**Hardware complexity** — First-time hardware companies fail 70%+ of the time. Prototype-to-production gaps, supply chain surprises, and quality at scale are each individually hard. Mitigation: use established SBCs (not custom silicon) for v1, partner with experienced ODMs, ship slowly and get it right.

**Capital requirements** — Even Phase 2 requires $40K+, Phase 3 requires $100K–$250K. If Assistive Tech revenue doesn't scale as planned, Ottolabs stalls. Mitigation: explicit MRR unlock conditions, pre-order capital supplements revenue.

### Medium Risk
**Manufacturer dependence** — ODM partners can drop, delay, or raise prices. Mitigation: qualify 2+ manufacturers in Phase 1 before committing to any single partner.

**Community pre-order trust** — Hardware crowdfunding has a long history of delays and failures (Cybertruck, etc.). Community knows this. Mitigation: only launch pre-order after prototypes are validated, publish specs openly, don't overpromise.

**Farm operations** — Vertical farming is capital-intensive and technically demanding. Many startups have failed here. Mitigation: start tiny (500 sqft, leafy greens), use off-the-shelf systems before custom robotics, learn before scaling.

### Lower Risk
**Regulatory** — Device certification (FCC/CE for wireless) adds cost and timeline. Mitigation: budget $10–20K for certification in Phase 2 planning.

**Competition** — Consumer hardware incumbents (Apple, Raspberry Pi, etc.) have huge advantages. Mitigation: Ottolabs isn't competing on specs — it's competing on ownership model. The value prop is "you own the factory" not "this is the fastest device."

**Talent** — Hardware engineers are rare and expensive. Mitigation: build a contributor model early where hardware engineers earn DPC weight, not just salary.

---

## The Irreducible Insight

Every industrial revolution has been captured by whoever owned the means of production at the moment automation tipped. Steam: factory owners. Electricity: utilities. Computing: tech companies.

Automation is tipping now — faster than any previous wave. The window to establish collective ownership of the machines is measured in years, not decades.

Ottolabs doesn't move fast because it's excited about gadgets. It moves with urgency because the factories that will run on robot labor are being built today — and right now, they all belong to someone else.

The Puck is the first neuron. The Tower is the spine. The factory is the body. And it belongs to everyone who builds it.

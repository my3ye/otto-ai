# Otto Billboards — Comprehensive Roadmap
*Decentralized physical broadcast. Community-owned displays. The real world hears the signal.*
*Last updated: 2026-03-16*

---

## Current State
**STATUS: CONCEPT** — Vision defined. Inception article published (2026-03-05). Universe YAML detailed. Zero hardware purchased. Zero locations contracted. No content governance model. No revenue.

Otto Billboards is the physical broadcast layer of the MY3YE ecosystem — the point where the digital signal hits the real world. Before it can exist, three other things must exist first: Tusita (physical locations to host displays), Ottolabs (hardware to manufacture or spec displays), and 505 Systems (governance for content decisions). None of those are operational yet.

This roadmap is deliberately long-horizon and capital-gated. Physical infrastructure at scale requires meaningful capital, and that capital must be earned — not speculated into existence.

---

## The Insight That Drives This

Advertising is the largest legal transfer of attention in history. Trillion-dollar industry. 100% captured by incumbent platforms (Meta, Google, Clear Channel). The community that views the ad pays for it — and sees none of the revenue.

Otto Billboards inverts that. Location owners earn. Community votes on what runs. Ecosystem projects get reach without paying extractive platform fees. And every display is a physical signal that the parallel civilization is real — you can see it with your eyes, not just on a screen.

The first billboard is not primarily a revenue play. It's a proof of reality.

---

## Revenue Bridge: Ecosystem First, External Advertising Later

Otto Billboards does not generate meaningful revenue until Phase 3. Phases 1 and 2 are funded by the ecosystem:

| Revenue Source | Feeds |
|----------------|-------|
| WebAssist / Assistive Tech | Phase 1 spec, pilot display hardware |
| KOIN community treasury | Phase 2 Tusita deployment (5–10 displays) |
| Ecosystem advertising (projects promoting within MY3YE) | Phase 3 operational costs |
| External advertising (city locations) | Phase 3+ real revenue |

**Rule:** No external advertising revenue expected before Phase 3. The displays earn their keep through ecosystem promotion first — proving the model, documenting reach, establishing governance norms — before commercial advertisers are invited in.

**Phase 1 unlock condition:** Tusita first location secured AND Ottolabs Puck prototype validated (hardware partnership exists).
**Phase 2 unlock condition:** Tusita location operational with 20+ Islanders AND KOIN community treasury holds ≥$20K.
**Phase 3 unlock condition:** 5+ Tusita displays operational, community governance proven, advertising model documented.

---

## Dependencies

- **Hard deps:**
  - **Tusita** — Physical locations are where Billboards are hosted. No Tusita, no deployment sites.
  - **505 Systems** — DAO governance for content approval. Without 505, content decisions have no legitimate mechanism.
  - **Ottolabs** — Either manufactures the display hardware directly, or validates the hardware spec so ODM partners can. Billboards need compute nodes (Puck/Tower class) for content delivery and governance integration.

- **Soft deps:**
  - **ONEON** — Content identity verification: who submitted what, DPC weight for approval, on-chain content log
  - **KOIN / Community Treasury** — Funds initial hardware before external ad revenue exists
  - **Otto AI** — Programmatic content scheduling, performance analytics, automated content optimization

- **Blocks downstream:**
  - **Otto Travel** — Billboards at Tusita locations become part of the visitor experience ("you saw the sign")
  - **Otto Market** — Vendor promotion slots on Billboards become an Otto Market product
  - **Ottolabs** — Billboard hardware becomes a product line, not just internal infrastructure

---

## Phase 1 — Specification & Pilot Design (0–365 days)
**Goal:** Know exactly what we're building and where. First pilot display installed at Tusita. Content governance model documented.

### Why this phase first
Physical display hardware has a wide cost range ($500–$50,000/unit depending on size, resolution, weatherproofing, and connectivity). Wrong hardware decisions at this stage waste capital we don't have. This phase eliminates guesswork before a single unit is purchased.

### Milestones

**M1 — Hardware specification locked (Days 1–90)**
- Display types evaluated:
  - Indoor (lobby, common areas): Commercial-grade LED panels, 65"–85", ~$800–2,000/unit
  - Outdoor (entrance, street-facing): Weatherproof LED billboard, P4–P6 pixel pitch, ~$3,000–8,000/unit
  - Micro (hallway, elevator, info kiosk): 32"–43" commercial IPS, ~$300–600/unit
- Compute node: Raspberry Pi CM4 or Otto Puck (when available) handles content delivery
- Connectivity: Ethernet primary, Wi-Fi fallback, cellular optional for city placements
- Power: 24/7 commercial display requires 150–400W. Solar supplementation designed for outdoor.
- Software stack: what drives the display (chosen from: open-source digital signage — Screenly OSE, Xibo, Concerto — or purpose-built Otto Display Agent)
- BOM per display type: components + install costs costed at 1-unit and 10-unit volumes
- Target: spec sheet covers 3 display tiers with locked vendor options and costed BOMs

**M2 — Content governance model designed (Days 30–120)**
- Who can submit content: verified ONEON identity holders (no anonymous submissions)
- Approval mechanism: 505 Systems DPC vote — content requires threshold approval before display
- Content categories: ecosystem projects (MY3YE/Tusita/ONEON/etc.), community announcements, approved commercial (Phase 3+)
- Revenue split design: advertising revenue → 40% location owner, 30% community treasury (KOIN), 20% content contributor, 10% network operations
- Emergency removal: any Steward can request emergency content removal; auto-removes pending governance review
- Content scheduling: rotating playlist model, time slots with weight based on DPC spent
- All decisions documented as the "Otto Billboards Content Charter v1"

**M3 — Tusita pilot display installed (Days 180–330)**
- Target: 1 indoor display (65"–85") at Tusita first location common area
- Hardware: commercial LED panel + Otto Puck (or Raspberry Pi CM4 if Puck not ready)
- Content: MY3YE ecosystem projects carousel, Tusita community announcements, Otto Music artist highlights
- Governance: first 505 Systems content vote (even with small cohort)
- Data: impressions tracked (camera-optional, wifi probe optional), uptime logged, Islander feedback collected
- Learning: every hardware issue, governance friction, and content gap documented

**M4 — ottobillboards.xyz / Billboard section in OMS (Days 240–365)**
- Admin interface in OMS (mev.otto.lk): display status, content queue, governance votes, revenue tracking
- Public-facing page: what Otto Billboards is, how to submit content, how to become a location partner
- Analytics: basic dashboard showing displays online, content running, uptime %

### Success Criteria
- Hardware spec complete for all 3 display tiers (BOM, vendor options, install guide)
- Content Charter v1 published
- 1 pilot display live at Tusita with governance active
- OMS Billboard section live (admin visibility into network)
- Total capital deployed: ≤$5,000

### Capital Required
~$2,000–$5,000 (1 pilot display + Puck compute + install)
Source: WebAssist operating revenue

---

## Phase 2 — Tusita Network (1–2 years)
**Goal:** All Tusita locations covered. Community governance battle-tested. Revenue model proven internally.

### Milestones

**M1 — Display network at Tusita first location (Months 12–18)**
- 5–8 displays at Tusita first location: entrance (outdoor), common areas (indoor), info kiosks (micro)
- Full content governance loop operational: submission → DPC vote → scheduling → display → analytics
- Islanders submitting content and voting on approvals
- Location owner revenue: first real payouts (even if small) to Tusita community treasury

**M2 — Ecosystem advertising model operational (Months 15–20)**
- MY3YE projects can purchase display time using KOIN
- Pricing model: DPC-weighted slot auctions OR flat-rate booking
- Revenue flows back to: location owner (Tusita community) + network treasury
- First external ecosystem projects promoted: Otto Music artists, Koink launches, community events

**M3 — Remote content management mature (Months 12–18)**
- Any authorized submitter can push content from anywhere
- Content approval time: ≤24h (governance vote completes within 24h for standard content)
- Scheduling: automated playlists by time of day, Islander population level
- Alerts: display offline → auto-paged to location ops team within 15 minutes

**M4 — Second and third Tusita location deployed (Months 18–24)**
- Scale learnings from first location: hardware reliability data, governance patterns, content preferences
- Standardized "Tusita Billboard Package": hardware list, install guide, governance onboarding
- 3–5 displays per new Tusita location
- Total network target: 15–25 displays across all Tusita locations

**M5 — Non-Tusita partnership template (Months 18–24)**
- Design the agreement template for non-Tusita location partners (hostels, co-working spaces, cafes)
- Revenue split: location owner 40% / community treasury 30% / content contributor 20% / operations 10%
- Legal: simple partnership agreement for physical hosting
- Target: 1–2 non-Tusita pilot locations signed (co-working space, independent cafe) to test model outside ecosystem

### Success Criteria
- 15+ displays operational across Tusita locations
- Content governance completing ≤24h cycle consistently
- First non-Tusita pilot location live (1–2 displays)
- Revenue flowing to location owners (Tusita treasury receiving KOIN equivalent)
- Uptime ≥95% across network
- Islander satisfaction: content feels community-driven, not broadcast-at-us

### Capital Required
~$25K–$60K (15–25 display units at $1,500–$3,000 installed average)
Source: KOIN community treasury + Assistive Tech surplus + ecosystem advertising revenue

---

## Phase 3 — City Placements & Commercial Model (2–4 years)
**Goal:** Urban locations. External advertisers. Real billboard revenue flowing to community.

### Milestones

**M1 — First urban billboard locations (Year 2–3)**
- Target: 2–4 high-footfall city locations (Sri Lanka focus initially: Colombo)
- Outdoor LED panels: commercial quality, weatherproof, 2–5 sqm viewing area
- Legal: understand city permitting requirements, signage licenses, and renewal cycles (varies widely by municipality)
- Revenue: commercial advertising at market rates, community treasury receives 30%
- Hardware upgrade: larger format displays ($5K–$15K/unit installed at city scale), cellular connectivity

**M2 — Commercial advertiser onboarding (Year 2–3)**
- Advertising dashboard: external buyers purchase time slots via ottobillboards.xyz
- Pricing: CPM model or flat weekly rates — benchmarked against Clear Channel/OOH market rates
- Targeting: location-based, time-of-day, no personal data (this is a privacy differentiator)
- Content review: commercial ads still go through 505 content governance — community can reject advertisers that conflict with values
- Target: 5+ recurring commercial clients generating ≥$2,000/month combined

**M3 — Programmatic content optimization (Year 2–3)**
- Otto AI integration: analyze display performance data (view count estimates, time-of-day patterns)
- Auto-scheduling: high-value time slots served to highest-bidding content (ecosystem or commercial)
- Dynamic content: weather-responsive, event-responsive (local sports, holidays), community-pulse content
- A/B testing: ecosystem projects can test creative variations, get performance data back

**M4 — 50+ display network (Year 3–4)**
- Combination of Tusita locations + urban placements + non-Tusita partners
- Network management: centralized OMS dashboard, per-display health monitoring, content SLA tracking
- Hardware standardization: 2 display tiers (indoor community + outdoor commercial)
- Supplier relationship: preferred display vendor or Ottolabs manufacturing (if Phase 3+ there)
- Revenue at scale: 50 displays × $1,000/month average = $50K/month gross; after splits → $15K/month to community treasury

**M5 — International expansion begins (Year 3–4)**
- Model proven in Sri Lanka, replicated in 1–2 new markets
- International legal research: signage law, corporate structures per country
- Tusita location expansion drives international Billboard expansion naturally
- Target: displays in 3+ countries

### Success Criteria
- 50+ displays across Tusita, urban, and partner locations
- ≥$20K/month gross advertising revenue
- ≥$6K/month flowing to community treasury (KOIN)
- Community governance rejection rate <5% (content is mostly appropriate)
- Otto AI optimization running (not manual scheduling)
- International presence in 3+ countries

### Capital Required
~$150K–$400K (urban display hardware, permits, commercial infrastructure, operations team)
Source: Commercial advertising revenue (self-funding from Phase 3 onwards) + community KOIN raises

---

## Phase 4 — Global Network (4+ years)
**Goal:** Otto Billboards is the community-owned alternative to Clear Channel. Real-world manifestation of MY3YE visible in cities worldwide.

### Milestones

**M1 — 200+ display global network (Year 4–5)**
- Displays in 10+ countries, covering all major MY3YE ecosystem markets
- Each Tusita location anchors the regional network
- Non-Tusita partners (cafes, hostels, independent venues) substantially outnumber Tusita placements
- Revenue: 200 displays × $1,500/month avg = $300K/month gross; $90K/month to community treasury

**M2 — Ottolabs display manufacturing (Year 4–5)**
- Ottolabs designs and manufactures display hardware (or components) in-house
- Cost reduction: community-manufactured display vs. commercial display at scale
- Target: 30% cost reduction vs. ODM-sourced hardware at Phase 3
- New product line: Otto Billboard hardware sold to external partners (revenue stream for Ottolabs)

**M3 — Display-as-a-Service for communities (Year 4–5)**
- Any community (not just MY3YE-affiliated) can license the Otto Billboard platform
- SaaS model: content governance system + display management + revenue splits
- White-label: runs as "Community Boards" or custom brand for non-MY3YE partners
- Revenue: platform licensing fees paid to MY3YE community treasury

**M4 — AR/holographic tier (Year 5+)**
- Next-generation displays: transparent OLED, outdoor holographic projection (as technology matures)
- Integration: QR-codes and NFC tap for interactive content
- ONEON tie-in: verified contributors can interact with displays using their identity (personalized community info, governance alerts)
- Experimental: AR overlay for mobile (point phone at display for extended content layer)

**M5 — $1M+ annual community treasury inflow (Year 5+)**
- Billboard network becomes a meaningful, durable revenue source for the ecosystem
- No single corporate owner. Revenue governed by 505 Systems.
- Every community that hosts a Billboard shares in its commercial success
- The physical landscape reads: this world belongs to more than the wealthy

### Success Criteria
- 200+ displays in 10+ countries
- $1M+ annual gross advertising revenue
- $300K+ annual to community treasury
- Ottolabs manufacturing displays (end-to-end community stack)
- Display-as-a-Service licensed to 5+ non-MY3YE communities
- Otto Billboards recognized as a legitimate alternative to corporate OOH advertising

### Capital Required
~$1M–$3M (global expansion, Ottolabs display manufacturing, DaaS platform development)
Source: Phase 3 advertising revenue (majority self-funded) + community KOIN raises + Ottolabs hardware revenue

---

## Content Governance Model

### Submission → Display Pipeline

```
Submitter (ONEON identity) → Content Queue
       ↓
505 Systems DPC vote (24h window)
  - Standard content: 10% DPC quorum to approve
  - Ecosystem project promotion: 5% DPC quorum (lower bar — trusted internal)
  - Commercial advertising: 20% DPC quorum + value-alignment check
       ↓
Approved → Scheduling Queue
  - DPC weight determines slot priority
  - Time-of-day rules applied
  - Otto AI optimizes for engagement (Phase 3+)
       ↓
Display → Analytics → Feedback to Submitter
```

### Revenue Distribution

| Stakeholder | Share | Rationale |
|-------------|-------|-----------|
| Location owner | 40% | They provide the physical space and maintain hardware |
| Community treasury (KOIN) | 30% | Funds future Billboard expansion, ecosystem projects |
| Content contributor | 20% | Incentivizes quality content creation |
| Network operations | 10% | Covers hosting, compute, Otto AI scheduling costs |

*Note: Ecosystem project promotion (Phase 1–2) may run at subsidized or zero rates to bootstrap content quality before commercial advertising is invited.*

---

## Display Hardware Tiers

| Tier | Format | Use Case | Size | Installed Cost | Phase |
|------|--------|----------|------|----------------|-------|
| Micro | 32"–43" IPS commercial | Hallway, kiosk, info point | Indoor | $400–800 | Phase 1 |
| Indoor | 65"–85" LED panel | Common area, lobby | Indoor | $1,000–2,500 | Phase 1–2 |
| Outdoor Community | P4–P6 LED, weatherproof | Tusita entrance, courtyard | Outdoor | $3,000–8,000 | Phase 2 |
| Outdoor Commercial | 2–5 sqm billboard | Street-facing, city | Outdoor | $8,000–20,000 | Phase 3 |
| Large Format | 10+ sqm digital billboard | High-traffic urban | Outdoor | $20,000–50,000 | Phase 3–4 |
| Otto-manufactured | Custom Ottolabs design | All tiers | Both | ~30% less at Phase 4 | Phase 4 |

---

## Key Metrics

| Metric | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|
| Displays deployed | 1 (pilot) | 15–25 | 50+ | 200+ |
| Locations covered | 1 Tusita | All Tusita + 1–2 partners | Tusita + urban + international | 10+ countries |
| Gross monthly revenue | $0 | $500–2,000 (ecosystem only) | $20K–50K | $250K+ |
| Community treasury monthly | $0 | $150–600 | $6K–15K | $75K+ |
| Content submissions/month | <5 | 20–50 | 100–300 | 500+ |
| DPC participants in governance | <10 | 50–200 | 500–2,000 | 5,000+ |
| Display uptime | ≥90% (pilot) | ≥95% | ≥97% | ≥99% |
| Non-ecosystem commercial clients | 0 | 1–2 (pilot) | 5–20 | 50+ |

---

## Risks

### High Risk
**Permitting and regulation** — Digital billboards are regulated in most jurisdictions. City signage laws, zoning restrictions, and permit timelines can add 6–18 months and $5–30K per location before a display ever turns on. Mitigation: start inside Tusita locations (private property, no permit needed for indoors) and treat Phase 1–2 as learning the regulatory landscape before spending money on street-facing city displays.

**Capital intensity** — A serious urban billboard network requires $150K–$400K just for Phase 3. If ecosystem advertising revenue doesn't grow as projected and community treasury can't fund hardware, Phase 3 stalls. Mitigation: self-funding model — each phase must prove revenue before next phase hardware spend is authorized. No pre-purchasing at scale.

### Medium Risk
**Hardware reliability** — Commercial displays in outdoor environments degrade faster than expected (heat, humidity, power surges). Sri Lanka climate is particularly demanding. Mitigation: specify commercial-grade hardware (not consumer TVs), budget for 15–20% annual replacement rate, build maintenance into location partnership agreements.

**Content governance friction** — If content voting is slow, submitters abandon the platform. If it's too permissive, quality degrades. First 50 votes are the template. Mitigation: manually curate the first 20 content pieces alongside governance (don't rely on pure vote mechanics until the model is proven).

**Community treasury dependency** — Phase 2 hardware relies on KOIN treasury, which is speculative before Phase 3 revenue. Mitigation: size Phase 2 to what Assistive Tech revenue can cover if treasury is unavailable.

### Lower Risk
**Competition from corporate OOH** — Clear Channel, Lamar, JCDecaux have massive networks and entrenched city contracts. Mitigation: Otto Billboards doesn't compete on scale or location count at Phase 1–3. It competes on community ownership, values-aligned content governance, and ecosystem alignment. The audiences are different.

**Vandalism and theft** — Physical displays are physical targets. Mitigation: outdoor displays co-located with active community spaces (Tusita) reduce vandalism risk. Insurance is available and budgeted.

---

## The Irreducible Insight

The largest outdoor advertising companies on earth own the right to put any message in front of millions of people every day. That right was purchased, not earned. The communities who live alongside those billboards — who walk past them, drive past them, can't avoid them — receive nothing and were asked nothing.

Otto Billboards is a simple inversion: the people who see the display govern what it says, and the location that hosts it earns what it generates. It's not a technology problem. The technology is commodity hardware and open-source software. It's a governance and ownership problem — and that's exactly what the MY3YE ecosystem was built to solve.

The first billboard at Tusita is not a revenue event. It's a declaration: the parallel civilization has a physical voice, and it belongs to the community.

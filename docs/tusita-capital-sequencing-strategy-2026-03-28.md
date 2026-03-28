# Tusita Islands & Resorts — Capital Sequencing & Milestone Strategy
**Date:** 2026-03-28 | **Authored by:** Otto
**Status:** Architecture Complete
**Inputs:** Tusita Capital Landscape Research (WF validated), On-Chain Labor Architecture, Smart Contract Specs, Investor Outreach Plan, Capital Alignment Review

---

## Executive Summary

Three phases. Each one unlocks the next. None is skippable.

**Phase 1 (NOW — Month 9): Land Acquisition + Community Fractional Round**
Secure the land. Launch community ownership via fractional NFTs. Deploy on-chain land governance. Mobilize early contributor labor to reduce cash capital required. Target: $75K–$500K. Zero dilution to governance.

**Phase 2 (Month 9–24): Resort Development + RWA Tokenization Raise**
Break ground. Build Phase 0 resort (10–20 dome units + community commons). Fund via RWA tokenization of the land asset + impact investor round. On-chain SiteOracle tracks every labor hour. Target: $1M–$5M. Sovereignty-preserving terms only.

**Phase 3 (Month 24–48): Scale to Full Island/Resort Network**
Multi-site expansion. Green bond and PPP capital for infrastructure. Full island governance live. $TUSITA token activated. Network reaches operational self-sufficiency through resort revenue. Target: $5M–$20M+.

**Core principle:** Physical labor tracked on-chain is not just a values statement — it is a capital reduction mechanism. In Phase 1, coordinated contributor labor can replace $150K–$300K of cash capital. In Phase 2, it lowers the construction financing threshold by 20–35%. Every tracked hour is economic value, verifiable by any investor.

---

## The Sovereignty Constraint

All three phases operate under a non-negotiable structural rule inherited from the MY3YE mission:

> **Capital must serve the community, not own the land.**

This means:
- No investor receives governance majority over the land or community charter
- Land title is held by the Tusita Foundation (community trust structure), not by any capital investor
- Revenue distributions are investor-accessible; land governance is contribution-earned (non-buyable)
- All capital events are publicly verifiable on-chain (multisig + OPRLP milestone attestations)
- CET (Contribution Equity Tokens) are soulbound — labor equity earned by workers cannot be diluted by capital raises
- SiteOracle on-chain attestations provide investors real-time verified progress updates

These are structural constraints, enforced at the smart contract layer. Every capital partner is disclosed these terms before term sheet.

---

## On-Chain Governance as Investor De-Risking

Traditional land development capital fails because investors have no verified visibility into progress until completion. Tusita's on-chain architecture changes this equation:

### What Investors See On-Chain (in real time)

| Signal | Contract | Update Frequency |
|--------|----------|-----------------|
| Land title custody transfer | Foundation multisig | On transaction |
| Construction labor hours attested | LaborAttestation.sol | Per work session |
| Material deliveries verified | SiteOracle.sol | Per delivery oracle |
| Milestone completion attestations | OPRLP DPCRegistry | Per milestone |
| Treasury balance and drawdowns | EquityTreasury.sol | Per transaction |
| Community governance votes | $TUSITA token contract | Per vote |
| Revenue inflows (resort) | EquityTreasury.sol | Per transaction |

### Why This De-Risks Investment

1. **Fraud elimination:** No construction firm can claim completed work without on-chain attestation from site oracles + peer validators. Payment gates are contract-enforced.
2. **Milestone gating:** Capital is released in tranches, each unlocked by verified on-chain milestones — not by self-reported progress.
3. **Labor cost transparency:** Every hour of contributor labor is on-chain, allowing investors to verify actual cost basis at any time.
4. **Governance visibility:** Investors can observe (but not override) community governance votes — full transparency without control.
5. **Exit mechanism:** RWA tokens provide a liquid secondary market for investors who need earlier liquidity than the resort cash flow timeline.

---

## How Physical Labor Reduces Capital Requirements

The Tusita model contains a structural capital efficiency that is unique to sovereign community projects: **organized contributor labor replaces hired contractor labor at zero cash cost.**

### The Math

In standard resort development, 30–40% of budget goes to manual labor (site preparation, foundation, frame, landscaping, community infrastructure). For a 15-unit Phase 0 resort:

| Category | Market Rate | CET Labor Coverage | Cash Required |
|----------|-------------|-------------------|---------------|
| Site clearing & leveling | $80K | 100% | $0 |
| Foundation & structural prep | $120K | 60% | $48K |
| Dome frame assembly | $150K | 80% | $30K |
| Landscaping + permaculture | $60K | 100% | $0 |
| Community commons construction | $90K | 70% | $27K |
| Solar + water system install | $70K | 30% | $49K |
| **Total** | **$570K** | **~65% covered** | **~$154K** |

*Assumptions: 50 active contributors, average 20 hours/week over 6 months. Typical early intentional community labor mobilization benchmarks.*

### How It Works (Contract Flow)

1. Contributor arrives at site, checks in via **ONEON identity** scan
2. **LaborAttestation.sol** opens a work session with timestamp + GPS coordinate
3. Work session closes at end of shift — hours + contribution type recorded on-chain
4. Two peer attestors (randomly assigned) confirm the contribution via mobile UI within 24h
5. **SiteOracle.sol** (Phase 2+) adds site supervisor verification for high-value contributions
6. After quorum, **ContributionEquity.sol** mints CET tokens proportional to hours and skill tier
7. **VestingEngine.sol** begins a 24-month vesting schedule, with 10% immediate liquid and 90% vesting over 2 years
8. Contributor's DPC score (Distributed Participation Credits) increases — unlocking governance weight, progression tiers, and resort service access

### What CET Holders Receive

CET tokens represent a claim on resort net revenue, not land governance. This separation protects both investors and community:

- **Economic:** 20% of annual resort net revenue distributed to CET holders proportional to CET balance
- **Governance:** CET holders vote on resort policies (pricing, services, expansion) but NOT on land ownership or community charter
- **Progression:** CET balance + DPC score together determine Steward/Founder/Sovereign tier eligibility
- **Liquidity:** Phase 2 CET secondary market launched via DEX — contributors who need to exit can sell economic claims without selling governance rights

---

## Phase 1 — Land Acquisition + Community Fractional Round

**Timeline:** NOW through Month 9
**Minimum Viable Capital:** $75K–$500K (range reflects site cost uncertainty)
**Dilution:** Zero governance dilution
**Capital Sources:** Community fractional NFT round, impact investor bridge, contributor labor equity
**Primary entity:** Tusita Foundation (proposed) + MY3YE treasury

### What Gets Built (Phase 1 Deliverables)

| Deliverable | Timeline | Capital Required | Labor Coverage |
|------------|----------|-----------------|----------------|
| Legal: Tusita Foundation structure registered | Month 1 | $5–15K legal | N/A |
| Site: Sri Lanka location shortlisted (2–3 candidates) | Month 1–2 | $5K (surveys) | 100% site scouting labor |
| Smart contracts: LaborAttestation + ContributionEquity + VestingEngine deployed | Month 2 | ~$200 gas | Dev labor (CET) |
| Community: $TUSITA token deployed (governance only) | Month 2–3 | $10–20K (audit) | Dev labor (CET) |
| Community Round: Fractional land NFT mechanics live | Month 3 | $15–25K dev | Dev labor (CET) |
| Community Round: $50K–$200K raised from Islanders | Month 3–5 | — | — |
| Land: Site selected + purchase agreement signed | Month 4–6 | $50K–$400K | N/A (cash required) |
| Land: Title held by Foundation multisig (on-chain) | Month 5–7 | $5–10K (legal) | N/A |
| Infrastructure: Water access + road + power survey | Month 6–8 | $10–20K | 60% survey labor |
| Community: 100+ contributors registered on ONEON | Month 9 | $0 | — |

### Phase 1 Capital Sources

**1. Community Fractional Land Ownership Round**

The community round is not a fundraise — it is a governance bootstrap. Early participants receive Islander NFTs that represent fractional participation rights in the land governance and resort revenue. This is not a security under most jurisdictions when structured as a community membership + revenue share NFT (verify with Sri Lanka Securities Commission for local compliance).

| Tier | NFT Name | Min Contribution | What You Get |
|------|----------|-----------------|--------------|
| Visitor | Wanderer NFT | $50 | Access to Tusita resort discount network + community news |
| Islander | Islander NFT | $500 | 1 governance vote, 0.1% annual resort revenue share, 7 days/year resort access |
| Steward | Steward NFT | $5,000 | 5 governance votes, 1% annual resort revenue share, 30 days/year resort access |
| Founder | Founder NFT | $25,000 | 10 governance votes, 5% annual revenue share, 90 days/year resort access + buildout input |

*Target: 100 Islanders ($50K), 20 Stewards ($100K), 4 Founders ($100K) = $250K community round*

**2. Impact Investor Bridge (Site Acquisition)**

For site acquisition specifically, the community round alone may not cover land cost (Sri Lanka coastal land: $100K–$500K depending on location and size). A bridge round from 1–2 impact investors — structured as a convertible note into Phase 2 equity — covers the gap.

Target terms:
- Amount: $100K–$300K
- Structure: Convertible note, converting into Phase 2 resort equity at 15–20% discount
- Governance: Zero — investors receive economic participation only
- Repayment trigger: Phase 2 close or resort revenue exceeds $500K/year, whichever first

Target investors for bridge:
- Omidyar Network (impact first, P0 contact — Week 2)
- Ceniarth (patient capital, no governance requirement)
- Private individuals in MY3YE community (most aligned, lowest dilution friction)

**3. Contributor Labor (Capital Reduction)**

Organized community labor replaces $150K–$300K in Phase 1 cash expenditures:
- Site surveys and assessment
- Legal research and documentation
- Smart contract development (dev contributors receive CET)
- Community platform development (web3 + CMS)
- Marketing and community building
- Infrastructure reconnaissance

All labor tracked via LaborAttestation.sol. All contributors receive CET. No cash required.

### Phase 1 Milestones (Unlock Phase 2)

All five must be met before Phase 2 fundraising begins:

| Milestone | Target | Verification |
|-----------|--------|-------------|
| **T1.1** — Foundation legally registered | Month 2 | Company registration certificate |
| **T1.2** — Community round: $100K+ raised | Month 5 | On-chain treasury balance |
| **T1.3** — Site acquisition complete (land secured) | Month 7 | On-chain title transfer attestation |
| **T1.4** — 50+ active contributors on-chain (DPC scores live) | Month 8 | LaborAttestation contract events |
| **T1.5** — Phase 2 investor packet complete + 3 conversations open | Month 9 | Deal room access granted |

---

## Phase 2 — Resort Development + RWA Tokenization Raise

**Timeline:** Month 9–24
**Minimum Viable Capital:** $1M–$5M
**Capital Sources:** RWA tokenization of land asset, impact investor equity round, development finance (UNDP/ADB PPP), resort pre-sales
**Primary entity:** Tusita Islands & Resorts Ltd (operating company, Foundation-owned majority)

### What Gets Built (Phase 2 Deliverables)

| Deliverable | Timeline | Capital Required | Labor Coverage |
|------------|----------|-----------------|----------------|
| Architecture: Dome design finalized (multi-faith integration) | Month 9–11 | $30–60K (architect) | 40% via contributor architects (CET) |
| Permits: Sri Lanka construction + environmental approvals | Month 10–13 | $15–30K | 30% contributor legal labor |
| SiteOracle deployed: On-chain construction verification live | Month 10 | ~$500 gas | Dev labor (CET) |
| SkillBountyRegistry deployed: Skilled bounties open | Month 10 | ~$200 gas | Dev labor (CET) |
| Foundation: Site preparation + foundation pour | Month 12–14 | $100–200K | 50% contributor labor |
| Construction: 5-unit Phase 0A (first dome cluster) | Month 13–18 | $250–400K | 40% contributor labor |
| Infrastructure: Solar grid + water system + road | Month 15–19 | $200–300K | 25% contributor labor |
| Community commons: Meditation circle + shared spaces | Month 17–21 | $100–150K | 60% contributor labor |
| Construction: 10-unit Phase 0B (second cluster) | Month 18–24 | $400–600K | 35% contributor labor |
| Operations: Staff training + resort soft launch | Month 22–24 | $50–100K | 20% contributor labor |
| RWA Tokenization: Land + resort tokenized on Polygon | Month 14 | $20–40K | Dev labor (CET) |
| CET secondary market: DEX liquidity pool launched | Month 16 | $30–50K LP | — |

### Phase 2 Capital Sources

**1. RWA Tokenization of Land Asset**

The secured land (Phase 1) becomes the collateral for Phase 2 capital through Real World Asset tokenization. The land is tokenized as an NFT with fractional ERC-1155 tokens representing economic participation rights.

| Mechanism | Capital Target | Structure |
|-----------|---------------|-----------|
| Primary RWA sale (Centrifuge / RealT / Parcl) | $500K–$1.5M | Fractional land tokens, 3-year revenue distribution |
| Investor RWA tokens (institutional tranche) | $200K–$500K | Priority revenue share, 5-year lock |
| Community RWA upgrade (existing Islanders) | $50K–$150K | Upgrade Islander NFT to fractional land token |

Platform options:
- **Centrifuge** (most credible DeFi RWA, real yield, institutional traction)
- **RealT** (residential/mixed-use RWA, tokenized across EVM chains)
- **Backed Finance** (European compliant, strong for family office distribution)
- Note: Both Parcl and RealT are under regulatory review in some jurisdictions — verify current status before commitment.

Key disclosure to RWA investors: The tokenized land earns yield from resort revenue, not from land price appreciation. Revenue share = 25% of resort net income distributed quarterly to RWA holders.

**2. Impact Investor Equity Round**

Target: $1M–$2M from 2–4 impact investors. Sovereignty-preserving terms only.

| Investor | Target Amount | Type | Contact Priority |
|---------|--------------|------|-----------------|
| Omidyar Network | $500K–$1M | Equity (impact first, patient capital) | P0 — Month 9 |
| Acumen South Asia | $300K–$500K | Program-related investment | P0 — Month 9 |
| Ceniarth | $200K–$500K | Evergreen capital, no exit pressure | P1 — Month 10 |
| Collaborative Fund | $200K–$300K | Mission-aligned, community models | P1 — Month 11 |

**Non-negotiable equity terms:**
- Economic equity (revenue share): up to 20% aggregate across all Phase 2 investors
- Governance rights: zero — land governance is community-only
- Exit: Secondary RWA market OR resort acquisition at 5x revenue multiple, investor option at Year 5
- Anti-dilution: Phase 3 raises cannot dilute Phase 2 investors below 12% economic participation

**3. Development Finance (UNDP / ADB / Sri Lanka Green Bond)**

The largest single capital source, and the most credible institutional endorsement:

| Program | Amount | Timeline | Action |
|---------|--------|----------|--------|
| UNDP Sri Lanka Green Bond Framework | $500K–$3M | Month 12–18 | Submit project brief at Phase 2 open |
| ADB Sustainable Tourism Sri Lanka ($100M program) | $500K–$2M | Month 12–20 | Apply via Sri Lanka Ministry of Tourism |
| BOI FDI facilitation (construction finance) | $200K–$1M | Month 10 | Register Phase 2 as BOI-approved project |
| Sri Lanka Green Climate Fund | $200K–$500K | Month 14 | Climate adaptation + renewable energy framing |

*Development finance is non-dilutive (grant or concessional loan). UNDP/ADB are the primary targets because they require sustainability credentials Tusita already has by design.*

**4. Pre-Sales and Deposits (Resort Revenue)**

Phase 2 construction can be partially funded through pre-sales of resort stays (similar to hotel pre-opening deposits):

| Pre-sale Tier | Price | Units | Revenue |
|--------------|-------|-------|---------|
| Founding Guest (7-night pre-opening stay) | $2,500 | 200 | $500K |
| Founding Member Annual Pass | $15,000/year | 30 | $450K |
| Steward Upgrade (from Phase 1 NFT holders) | $5,000 upgrade | 50 | $250K |

*Pre-sales reduce construction loan requirement without equity dilution. Must be structured with clear refund terms if project doesn't launch.*

### Phase 2 Milestones (Unlock Phase 3)

| Milestone | Target | Verification |
|-----------|--------|-------------|
| **T2.1** — $1M Phase 2 capital raised (any combination) | Month 12 | On-chain treasury |
| **T2.2** — Phase 0A (5 domes) construction complete | Month 18 | SiteOracle attestation batch |
| **T2.3** — Soft launch: 50+ paying guests | Month 22–23 | Reservation system + payment records |
| **T2.4** — Resort monthly revenue > $25K | Month 24 | EquityTreasury inflow records |
| **T2.5** — 200+ active contributors with CET vested | Month 24 | ContributionEquity contract events |
| **T2.6** — UNDP/ADB or development finance MOU signed | Month 20 | Signed agreement |

---

## Phase 3 — Scale to Full Island/Resort Network

**Timeline:** Month 24–48
**Minimum Viable Capital:** $5M–$20M+
**Capital Sources:** Green bond issuance (public), sovereign fund PPP, Series A resort equity, $TUSITA token utility activation
**Primary entity:** Tusita Islands & Resorts Ltd (operational) + Tusita Foundation (land governance)

### What Gets Built (Phase 3 Deliverables)

| Deliverable | Timeline | Capital Required |
|------------|----------|-----------------|
| Site 2: Second Tusita location (target: coastal or island Sri Lanka) | Month 24–30 | $1M–$3M |
| Full resort capacity: 50+ dome units across sites | Month 30–40 | $3M–$8M |
| $TUSITA token: Utility activation (resort payments, governance) | Month 25 | $50K (audit + launch) |
| EquityTreasury: Full revenue distribution contract live | Month 26 | ~$1K gas |
| Governance: Multi-site DAO live (Foundation + $TUSITA holders) | Month 27 | Governance sprint |
| Otto Travel integration: Tusita bookable via Otto Travel network | Month 28 | Integration sprint |
| Community ladder: 1,000+ contributors across all tiers | Month 36 | $0 (system cost) |
| Reef/land regeneration program: Certified carbon credits | Month 30–42 | $200–500K (certification) |
| Site 3+ expansion: Regional (Maldives, Thailand, Philippines) | Month 40–48 | $5M–$15M |

### Phase 3 Capital Sources

**1. Green Bond Issuance (Public)**

With Phase 0A operational and development finance MOU in hand, Tusita qualifies for a standalone green bond issuance through Sri Lanka's Green Bond Framework (UNDP + GGGI backed):

- Amount: $3M–$10M
- Structure: 5–7 year green bond, 4–6% coupon, backed by resort revenue and carbon credits
- Use of proceeds: Site 2 acquisition, full resort buildout, renewable energy + regeneration program
- Eligibility basis: Phase 2 impact metrics (jobs created, carbon offset, community income)

**2. PPP with Sri Lanka Government**

Sri Lanka's 3M visitor target for 2026 and active "green economy hub" positioning creates a genuine PPP opportunity for infrastructure:

- Road, water, power infrastructure shared with government (government builds, Tusita uses)
- Potential government equity stake (non-governance — economic only) in exchange for concession and infrastructure support
- Tourism Ministry is the access point; BOI facilitates the formal PPP structure

**3. Series A Resort Equity**

If green bond and PPP don't fully close the Phase 3 gap, a Series A from hospitality-specialist investors rounds out the stack:

| Investor Type | Target Amount | Terms |
|--------------|--------------|-------|
| Kembara / Mundi Ventures | $2M–$5M | Sovereign/community infrastructure mandate, patient |
| Regenerative tourism funds (Paladin, R360, conservation funds) | $1M–$3M | ESG-first, B-Corp alignment expected |
| Family offices (Sri Lanka diaspora) | $500K–$2M | Community connection, long horizon |

**Non-negotiable Series A terms:**
- Governance cap: No single investor > 10% economic equity
- Land governance: Zero investor control — Foundation-only
- Pro-rata rights: Phase 3 investors get pro-rata in Phase 4 expansion only
- Exit: Resort acquisition at 7x revenue or IPO of resort operating company at Year 7

**4. $TUSITA Token Activation**

Phase 3 activates $TUSITA as a utility token for the resort network:
- Resort payments (10% discount on all stays paid in $TUSITA)
- Governance voting on multi-site expansion decisions
- Staking for yield (funded from 5% of resort revenue)
- Cross-ecosystem integration: $TUSITA accepts $KOIN for resort payments

*$TUSITA is not a Phase 3 capital raise — it is an operational utility token. No ICO. No public sale. Distribution is labor-earned (CET → $TUSITA conversion at vesting) and pre-sale reward.*

### Phase 3 Milestones (Network Self-Sufficiency)

| Milestone | Target | Verification |
|-----------|--------|-------------|
| **T3.1** — Resort revenue > $100K/month | Month 30 | EquityTreasury inflows |
| **T3.2** — Site 2 land secured | Month 32 | On-chain title transfer |
| **T3.3** — $5M Phase 3 capital raised | Month 36 | On-chain treasury |
| **T3.4** — Carbon credit program certified (first issuance) | Month 40 | Carbon registry certificate |
| **T3.5** — 1,000+ active contributors across all tiers | Month 42 | ContributionEquity events |
| **T3.6** — Network revenue > $300K/month (self-sustaining) | Month 48 | EquityTreasury inflows |

---

## Capital Stack Summary

| Phase | Timeline | Min Capital | Max Capital | Sources | Dilution |
|-------|----------|-------------|-------------|---------|---------|
| Phase 1 | NOW–Month 9 | $75K | $500K | Community NFT round + bridge + labor | Zero governance |
| Phase 2 | Month 9–24 | $1M | $5M | RWA tokens + impact equity + dev finance + pre-sales | ≤20% economic |
| Phase 3 | Month 24–48 | $5M | $20M+ | Green bond + PPP + Series A + $TUSITA | ≤30% economic total |

**Total capital stack (Phase 1–3):** $6M–$25M+
**Labor equity (CET) capital reduction vs pure cash model:** $1.5M–$4M equivalent

---

## Phase Unlock Logic

Each phase has hard gates. If milestones are not met, fundraising for the next phase does not begin.

```
Phase 1 Gate (Month 9):
  ├── T1.1: Foundation registered ✓
  ├── T1.2: Community round $100K+ ✓
  ├── T1.3: Land secured ✓
  ├── T1.4: 50+ contributors on-chain ✓
  └── T1.5: Phase 2 investor packet + 3 conversations ✓
       → UNLOCK Phase 2 fundraising

Phase 2 Gate (Month 24):
  ├── T2.1: $1M raised ✓
  ├── T2.2: Phase 0A construction complete ✓
  ├── T2.3: 50+ paying guests ✓
  ├── T2.4: $25K/month revenue ✓
  ├── T2.5: 200+ contributors with CET ✓
  └── T2.6: Dev finance MOU ✓
       → UNLOCK Phase 3 fundraising

Phase 3 Gate (Month 48):
  ├── T3.1: $100K/month revenue ✓
  ├── T3.3: $5M raised ✓
  ├── T3.5: 1,000+ contributors ✓
  └── T3.6: $300K/month (self-sustaining) ✓
       → Network self-sufficiency achieved
```

---

## Risk Map

| Risk | Phase | Severity | Mitigation |
|------|-------|----------|------------|
| Sri Lanka coastal land acquisition price spike | 1 | High | Identify 3 sites, negotiate in parallel. Community round raised before land approach. |
| Community round undersubscription (<$100K) | 1 | High | My3ye community pre-launch list before round open. Steward/Founder NFTs sell via direct outreach first. |
| RWA tokenization regulatory uncertainty (Sri Lanka) | 2 | Medium | Structure as revenue-sharing NFT membership, not a security. Obtain Sri Lanka Securities Commission no-action letter. |
| Construction cost overrun | 2 | Medium | CET labor model creates 35–65% cost flexibility. SiteOracle contract prevents fraudulent billing. |
| Impact investor governance creep | 2 | High | Non-negotiable term sheet language. Foundation structure ensures land governance is legally insulated. |
| UNDP/ADB process delays (12–18 month cycles) | 2–3 | Medium | Begin applications Month 9, not Month 12. Submit pre-feasibility brief at Phase 1 close. |
| $TUSITA token treated as security | 3 | Medium | Utility-only launch. No public sale. Distribution is contribution-earned or pre-sale reward. Legal opinion before activation. |
| Climate event / force majeure (Sri Lanka coastal) | 2–3 | Medium | Select inland sites or elevated coastal. Renewable energy + water resilience by design. Parametric insurance at Phase 2. |

---

## Ottolabs + Tusita Capital Synergy

Per the alignment review, this synergy is currently underdocumented. It matters for both capital efficiency and narrative:

1. **Ottolabs is Tusita's captive first hardware customer:** Every dome needs Otto Puck (compute), Otto Band (biometric), Otto Ring (payments), and future solar management hardware. The resort is a live deployment environment for Ottolabs devices — this reduces Ottolabs hardware VC risk (paid pilot customer from Day 1).

2. **Shared labor pool:** Contributors who build Tusita earn CET. Those who also build Ottolabs hardware earn CET on the Ottolabs registry. The same ONEON identity + DPC score accumulates across both — contributors become dual-equity holders in two verticals of the same civilization.

3. **Shared capital conversations:** UNDP/ADB/Omidyar pitches for Tusita open the door for Ottolabs grant conversations about sustainable hardware infrastructure in the same community. One relationship, two capital paths.

4. **Framing:** Pitch Tusita as the first city that Ottolabs devices power. Pitch Ottolabs as the infrastructure supplier for the sovereign resort network. One story, reinforcing both.

---

## First 30 Days — Action Priority

| Action | Owner | Deadline | Capital Impact |
|--------|-------|----------|---------------|
| Register Tusita Foundation (Sri Lanka / BVI hybrid) | Mev + lawyer | Day 14 | Enables land acquisition |
| Deploy LaborAttestation + ContributionEquity contracts | Otto | Day 7 | Starts labor tracking immediately |
| Open community pre-registration on tusita.xyz | Otto | Day 5 | Builds Islanders list before round open |
| Identify 3 candidate land sites (Sri Lanka) | Mev | Day 21 | Phase 1 T1.3 prerequisite |
| Draft 2-page project brief (UNDP/ADB pre-submission) | Otto | Day 10 | Positions Phase 2 dev finance |
| Email UNDP Sri Lanka country office | Mev | Day 7 | Starts 12–18 month institutional clock |
| Design Islander/Steward/Founder NFT mechanics | Otto | Day 14 | Community round mechanics |
| Price Islanders list: 20 Stewards + 4 Founders directly | Mev | Day 10 | $120K+ from known community before open round |

---

*Document generated by Otto — Sprint Prioritizer Agent | 2026-03-28*
*Related: tusita-islands-investor-outreach-plan-2026-03-28.md | capital-strategy-alignment-review-2026-03-28.md | labor-contribution-smart-contract-architecture-2026-03-28.md*

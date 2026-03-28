# The Otto Loop: Core Value Loop Architecture
## Canonical Economic Primitive for the MY3YE Ecosystem

*Authored by Otto (Architect Agent) | 2026-03-28 | Status: Architecture Complete*
*Depends on: DPC Formula, OPRLP Governance, Labor Attestation, Memory Capsule Annotation, Koink Tokenomics*

---

## Design: The Otto Loop

### Problem

Every MY3YE vertical — music, furniture, travel, education, code, devices — produces value through the same underlying pattern: someone contributes, demand emerges, production happens, revenue flows back. But each vertical is being designed independently with its own ad-hoc economic model. Without a canonical primitive, the ecosystem fragments: revenue split logic gets reinvented per vertical, contribution scoring diverges, governance weight accrual becomes inconsistent, and the self-reinforcing feedback loop that makes the whole system compound breaks.

Mev's furniture designer scenario makes this concrete: Designer submits → AI plans production → demand triggers manufacturing → sales revenue flows back to designer, AI trainers, production nodes, governance. That's not a furniture-specific flow. That's the **universal value cycle** every vertical runs.

### Approach

Define a single reusable primitive — **The Otto Loop** — that all verticals inherit. The Loop has 8 stages, 10 participant roles, configurable parameters per vertical, and a self-reinforcing feedback mechanism where output from one cycle becomes input to the next.

---

## 1. The Otto Loop — 8 Stages

```
                    ┌──────────────────────────────────────────────────┐
                    │                  THE OTTO LOOP                    │
                    │                                                    │
                    │    ┌─────────┐      ┌─────────┐      ┌─────────┐ │
                    │    │ 1.SUBMIT│─────►│2.VERIFY │─────►│ 3.SCORE │ │
                    │    └─────────┘      └─────────┘      └────┬────┘ │
                    │         ▲                                  │      │
                    │         │                                  ▼      │
                    │    ┌─────────┐                        ┌─────────┐ │
                    │    │8.EVOLVE │                        │4.CATALOG│ │
                    │    └────┬────┘                        └────┬────┘ │
                    │         ▲                                  │      │
                    │         │                                  ▼      │
                    │    ┌─────────┐      ┌─────────┐      ┌─────────┐ │
                    │    │7.GOVERN │◄─────│6.SPLIT  │◄─────│5.TRIGGER│ │
                    │    └─────────┘      └─────────┘      └─────────┘ │
                    │                                                    │
                    └──────────────────────────────────────────────────┘
```

### Stage 1: SUBMIT — Contribution Enters the System

A participant submits a contribution. This is the loop's entry point.

| Field | Description |
|-------|-------------|
| `contributor` | ONEON identity (wallet address) |
| `contribution_type` | One of: `DESIGN`, `CODE`, `DATA`, `LABOR`, `MATERIAL`, `CAPITAL`, `CURATION`, `OPERATION`, `EDUCATION`, `COMMUNITY` |
| `artifact_hash` | IPFS CID of the submitted work (design file, code commit, training data, photo evidence) |
| `project_id` | Which vertical/project this serves |
| `metadata` | Type-specific context (e.g., material receipts, skill credentials, git diff) |

**Furniture example:** Designer uploads a chair design as a 3D model. `artifact_hash` = IPFS CID of the model. `contribution_type` = `DESIGN`. `project_id` = `otto-market:furniture`.

**Music example:** Artist uploads a master recording. `contribution_type` = `DESIGN`. `project_id` = `otto-music:releases`.

**Education example:** Mentor submits a curriculum module. `contribution_type` = `EDUCATION`. `project_id` = `sos-systems:learning`.

### Stage 2: VERIFY — Multi-Party Attestation

No self-attestation. Every contribution requires independent verification before it earns credit.

```
VERIFICATION MATRIX (by contribution type):

  DESIGN:    Peer review (2+ designers) + AI quality check
  CODE:      Automated tests + reviewer attestation + CI pass
  DATA:      Quality validators + cross-reference check + commit-reveal consensus
  LABOR:     Peer (2+) + Site Oracle (GPS/IoT) — existing MPAP protocol
  MATERIAL:  Receipt hash + delivery confirmation + 1 validator
  CAPITAL:   On-chain transaction proof (self-verifying)
  CURATION:  Peer attestation + quality score convergence
  OPERATION: Attendance + peer attestation
  EDUCATION: Student attestation + completion rates
  COMMUNITY: Peer attestation (weighted by attester DPC)
```

**Quorum rule:** 2-of-3 independent sources must agree. Capital is the exception — on-chain tx is self-proving.

**Furniture example:** Two other designers in the community review the chair design for structural soundness, aesthetic quality, and manufacturability. An AI model scores the design against production constraints. If 2 of 3 pass, the contribution is verified.

### Stage 3: SCORE — DPC Contribution Scoring

Verified contributions are scored using the DPC formula: `P = f(Is, Ec, Rw)`.

```
DPC COMPONENT WEIGHTS (by contribution type):

  DESIGN:     Is=0.6,  Ec=0.2,  Rw=0.2   — structural impact dominates
  CODE:       Is=0.6,  Ec=0.2,  Rw=0.2   — same as design (digital creation)
  DATA:       Is=0.5,  Ec=0.2,  Rw=0.3   — resonance matters (data quality = downstream impact)
  LABOR:      Is=0.7,  Ec=0.2,  Rw=0.1   — physical impact dominates
  MATERIAL:   Is=0.8,  Ec=0.1,  Rw=0.1   — raw structural value
  CAPITAL:    Is=0.4,  Ec=0.3,  Rw=0.3   — balanced (capital enables, doesn't create)
  CURATION:   Is=0.3,  Ec=0.3,  Rw=0.4   — resonance dominates (taste-making)
  OPERATION:  Is=0.2,  Ec=0.6,  Rw=0.2   — consistency is the primary value
  EDUCATION:  Is=0.3,  Ec=0.3,  Rw=0.4   — resonance (teaching impact) matters most
  COMMUNITY:  Is=0.1,  Ec=0.3,  Rw=0.6   — pure resonance value
```

**Scoring formula per contribution:**

```
contribution_score = (
    Is_weight × structural_impact(artifact, attestation_scores) +
    Ec_weight × consistency_factor(contributor_history, project_tenure) +
    Rw_weight × resonance(downstream_usage, peer_ratings, demand_signal)
) × quality_multiplier(attestation_median_score / 100)
```

Where:
- `structural_impact()` = measurable output (lines of code, design complexity score, hours×skill_level, material value)
- `consistency_factor()` = how regularly the contributor delivers (streak bonus, decay for long gaps)
- `resonance()` = downstream impact (how much other work or demand this contribution generates)
- `quality_multiplier` = median attestation quality score, normalized to [0.5, 1.5] range

**Furniture example:** The chair design scores high on Is (novel structural approach), moderate on Ec (designer has submitted 3 designs in 6 months), and will accrue Rw over time as demand materializes.

### Stage 4: CATALOG — Contribution Enters the Marketplace

Scored contributions are registered in the **Contribution Registry** — the universal catalog that all demand-facing surfaces read from.

```
CONTRIBUTION REGISTRY ENTRY:

  registry_id:        bytes32         — unique identifier
  contributor:        address         — ONEON identity
  project_id:         bytes32         — which vertical
  contribution_type:  enum            — type code
  artifact_hash:      bytes32         — IPFS CID
  dpc_score:          uint32          — current DPC score (updates with resonance)
  catalog_status:     enum            — DRAFT | ACTIVE | SUSPENDED | ARCHIVED
  listed_at:          uint32          — timestamp when catalog-ready
  provenance_chain:   bytes32[]       — parent contributions this derives from
  revenue_share_bps:  uint16          — creator's base share in basis points (see Stage 6)
  demand_count:       uint32          — total demand events (orders, plays, uses)
  total_revenue:      uint256         — lifetime revenue generated (wei)
```

**Catalog surfaces by vertical:**

| Vertical | Catalog Surface | Discovery |
|----------|----------------|-----------|
| Otto Market | Product listing (furniture, goods) | Search, browse, AI recommendation |
| Otto Music | Release page (tracks, albums) | Player, playlist, discovery algorithm |
| WebAssist | Service offering | Client matching |
| SOS Systems | Learning module | Skill path recommendation |
| Otto Travel / Tusita | Experience listing | Location-based, community governed |
| ONEON | Memory Capsule layer | Quality-ranked, privacy-gated |

**Furniture example:** The verified, scored chair design appears in Otto Market as a product listing. Customers can browse, view the design, read attestation scores, see the designer's contribution history.

### Stage 5: TRIGGER — Demand Oracle Fires

Demand events trigger the production and revenue cycle. Each vertical has its own demand oracle, but they all emit the same signal: `DemandEvent(registry_id, quantity, buyer, payment_amount)`.

```
DEMAND ORACLES (by vertical):

  OTTO MARKET:    Purchase order (customer buys N units)
  OTTO MUSIC:     Stream event / download / sync license
  WEBASSIST:      Client contract signed
  SOS SYSTEMS:    Module enrollment / completion milestone
  OTTO TRAVEL:    Booking confirmed
  ONEON:          Memory Capsule layer accessed / queried
  KOINK.FUN:      Token trade / memecoin launch
  OTTOLABS:       Device order / subscription
  OTTO BILLBOARD: Ad impression batch (auditable on-chain)
```

**Demand signal structure:**

```
DemandEvent {
    registry_id:    bytes32     — which catalog entry
    demand_type:    enum        — PURCHASE | STREAM | LICENSE | ENROLL | BOOK | ACCESS | TRADE
    quantity:       uint32      — units / plays / seats / queries
    buyer:          address     — ONEON identity (or zero for anonymous)
    payment_amount: uint256     — gross payment in settlement token (USDC/KOIN)
    timestamp:      uint32
    metadata:       bytes       — vertical-specific context
}
```

**Furniture example:** A customer orders 50 chairs. `DemandEvent` fires with `registry_id` = the chair design, `quantity` = 50, `payment_amount` = total order value.

**Production triggering:** For physical goods, the demand event triggers the **Production Pipeline**:

```
DEMAND EVENT → PRODUCTION PIPELINE:

  1. AI Production Planner generates manufacturing specs from design artifact
     → New SUBMIT (contribution_type=CODE, project=same)
     → Creates dependency: design_registry_id ← production_plan_registry_id

  2. Material Sourcing — bill of materials triggers procurement
     → New SUBMIT (contribution_type=MATERIAL) for each supplier
     → Supply chain participants enter the loop

  3. Manufacturing — physical production begins
     → New SUBMIT (contribution_type=LABOR) for each worker
     → Multi-party attestation on quality, hours, output

  4. Quality Control — finished product verified
     → VERIFY stage for the aggregate product
     → Attestation from QC inspectors + automated checks

  5. Distribution — product ships to buyer
     → SUBMIT (contribution_type=OPERATION) for logistics
     → Delivery confirmation closes the production pipeline
```

Each production step is itself a SUBMIT → VERIFY → SCORE cycle, creating **nested loops**. Revenue from the sale traces back through the entire provenance chain.

### Stage 6: SPLIT — Revenue Distribution

This is the core economic engine. Revenue from a demand event splits across **every contributor in the provenance chain**, weighted by their DPC score and role.

```
REVENUE SPLIT FORMULA:

  gross_payment
    │
    ├── protocol_fee (5%) ──────────► Ecosystem Treasury
    │
    ├── governance_accrual (3%) ────► Governance Staking Pool
    │
    └── contributor_pool (92%) ─────► Split across provenance chain
```

**Contributor pool distribution:**

```
CONTRIBUTOR POOL SPLIT:

  For each contributor i in provenance_chain:

    share_i = (role_weight_i × dpc_score_i × quality_i) / Σ(role_weight_j × dpc_score_j × quality_j)

    payout_i = contributor_pool × share_i
```

**Role weights (default, DAO-adjustable):**

| Role | Weight | Rationale |
|------|--------|-----------|
| Primary Creator | 1.00 | The person who submitted the original artifact |
| AI System | 0.15 | AI that assisted (production planning, generation, curation) |
| AI Data Providers | 0.10 | Training data contributors whose data trained the AI |
| Material Suppliers | 0.80 | Raw material sourcing (high for physical goods) |
| Manufacturers | 0.90 | Physical production labor |
| Quality Validators | 0.20 | Attestation and QC work |
| Curators | 0.25 | Discovery, recommendation, taste-making |
| Platform Operators | 0.15 | Infrastructure maintenance |
| Educators | 0.30 | Training that enabled the contributor's skill |
| Community Governance | 0.10 | DAO participants who shaped the policies |

**Agent tax:** When an AI agent completes work (per Mev's directive), its role weight is reduced by the **agent_tax_rate** (default 40%). The taxed portion flows to the **Redistribution Pool**, which funds:
- Training data providers (perpetual royalty — Memory Capsule annotation layer)
- Human validators who verified the agent's work
- Ecosystem treasury for public goods

```
AGENT TAX FLOW:

  agent_share = contributor_pool × share_agent
  taxed_amount = agent_share × agent_tax_rate
  agent_receives = agent_share - taxed_amount

  taxed_amount splits:
    ├── 50% → Training data providers (proportional to capsule usage)
    ├── 30% → Human validators
    └── 20% → Ecosystem treasury
```

**Furniture example revenue split:**

```
Customer pays $500 for a custom chair:

  Protocol fee:     $25.00  → Ecosystem Treasury
  Governance:       $15.00  → Governance Staking Pool
  Contributor pool: $460.00 → Split:

  PROVENANCE CHAIN:
  ┌─────────────────────────┬────────┬─────┬─────┬──────────┐
  │ Participant             │ Weight │ DPC │ Qlty│ Payout   │
  ├─────────────────────────┼────────┼─────┼─────┼──────────┤
  │ Furniture Designer      │  1.00  │ 85  │ 0.9 │ $198.90  │
  │ AI Production Planner   │  0.15  │ 70  │ 0.8 │  $21.84  │
  │   └─ Agent tax (40%)    │        │     │     │  -$8.74  │
  │   └─ Designer net       │        │     │     │  $13.10  │
  │ AI Training Data (3ppl) │  0.10  │ 60  │ 0.7 │  $10.92  │
  │ Wood Supplier           │  0.80  │ 75  │ 0.9 │ $139.92  │
  │ Carpenter               │  0.90  │ 80  │ 0.9 │ $167.83  │
  │ QC Inspector            │  0.20  │ 65  │ 0.8 │  $27.04  │
  │ Market Curator          │  0.25  │ 55  │ 0.7 │  $25.07  │
  │ Platform Ops            │  0.15  │ 50  │ 0.8 │  $15.60  │
  ├─────────────────────────┼────────┼─────┼─────┼──────────┤
  │ TOTAL (before rounding) │        │     │     │ ~$460.00 │
  └─────────────────────────┴────────┴─────┴─────┴──────────┘

  Agent tax redistribution ($8.74):
    $4.37 → Training data providers
    $2.62 → Human validators (Designer + QC Inspector)
    $1.75 → Ecosystem treasury
```

Note: These numbers are illustrative. Actual payouts depend on relative DPC scores across the full provenance chain. The formula is `share_i = (W_i × DPC_i × Q_i) / Σ(W_j × DPC_j × Q_j)` applied to the $460 pool.

### Stage 7: GOVERN — Governance Weight Accrual

Every revenue event accrues governance weight for participants. This is how the system becomes self-governing: the people who create and produce earn the right to shape policy.

**Governance Weight Accrual Formula:**

```
ΔG_i = sqrt(cumulative_dpc_i) × ln(1 + revenue_earned_i) × tenure_factor_i

where:
  cumulative_dpc_i  = lifetime DPC score for participant i
  revenue_earned_i  = lifetime revenue earned through the loop (in USDC)
  tenure_factor_i   = min(1.0, months_active / 24)  — caps at 2 years

  Final governance weight: G_i = ΔG_i × decay(months_since_last_contribution, λ=0.05)
```

**Design properties:**
- `sqrt(DPC)` — sublinear: prevents score whales from dominating governance
- `ln(1 + revenue)` — logarithmic: diminishing returns on pure capital
- `tenure_factor` — rewards sustained participation, caps at 2 years (no infinite incumbency bonus)
- `decay` — governance weight fades if you stop contributing (use it or lose it)
- No governance weight for pure capital — investors earn financial returns, not policy control

**Governance actions unlocked by weight:**
- Vote on role weights (Stage 6 parameters)
- Vote on protocol fee rate
- Vote on agent tax rate
- Propose new verticals or contribution types
- Vote on quality standards for verification
- Elect council members (OPRLP integration)

**Furniture example:** The designer's governance weight increases with each sale. After 12 months and 200 chairs sold, they have meaningful say in Otto Market policies — pricing standards, quality thresholds, new material requirements.

### Stage 8: EVOLVE — Feedback Loop Closes

The output of each cycle feeds the input of the next. This is what makes the Otto Loop self-reinforcing rather than a static pipeline.

```
FEEDBACK SIGNALS (output → input):

  1. DEMAND → RESONANCE SCORE UPDATE
     Every DemandEvent retroactively increases the Rw component of all
     contributions in the provenance chain. More demand = higher DPC for
     the original creator = higher share in future splits.

  2. REVENUE → QUALITY BENCHMARK UPDATE
     Revenue-per-contribution becomes a quality signal. High-revenue designs
     set new quality benchmarks. The verification stage (Stage 2) evolves:
     attestation criteria tighten as the bar rises.

  3. GOVERNANCE → PARAMETER EVOLUTION
     Governance votes change split ratios, quality thresholds, tax rates.
     The loop's behavior evolves based on participant decisions, not
     founder fiat.

  4. AGENT TAX → DATA IMPROVEMENT
     Tax revenue funds better training data → better AI → better production
     plans → higher quality output → more demand → more revenue → more tax
     → better data. The AI improvement flywheel.

  5. CONTRIBUTION HISTORY → TRUST SCORE
     Repeated verified contributions build contributor trust. High-trust
     contributors get expedited verification (Stage 2) and premium
     catalog placement (Stage 4). Trust compounds.

  6. NESTED LOOPS → ECOSYSTEM DENSITY
     Each production step (Stage 5) creates new Submit events. One furniture
     sale spawns 5-8 new loop entries (AI planner, supplier, carpenter, QC,
     logistics). Ecosystem density grows exponentially with demand.
```

**Furniture example feedback:** The designer's chair sells well → demand signals increase → DPC resonance score rises → designer's governance weight grows → designer votes to improve quality standards → average design quality increases → Otto Market attracts higher-end customers → more demand → the loop accelerates.

---

## 2. Participant Model — The 10 Roles

Every Otto Loop instance involves some subset of these 10 canonical roles. Not all roles are present in every vertical.

```
PARTICIPANT ROLES:

  ┌───────────────────────────────────────────────────────────┐
  │                     CREATOR TIER                           │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
  │  │  Primary     │  │  Secondary  │  │  Data        │       │
  │  │  Creator     │  │  Creator    │  │  Provider    │       │
  │  │              │  │  (collab)   │  │  (training)  │       │
  │  └─────────────┘  └─────────────┘  └─────────────┘       │
  ├───────────────────────────────────────────────────────────┤
  │                    PRODUCTION TIER                          │
  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
  │  │  Material    │  │  Manufacturer│  │  AI Agent    │       │
  │  │  Supplier    │  │  / Builder   │  │  (automated) │       │
  │  └─────────────┘  └─────────────┘  └─────────────┘       │
  ├───────────────────────────────────────────────────────────┤
  │                    QUALITY TIER                             │
  │  ┌─────────────┐  ┌─────────────┐                         │
  │  │  Validator   │  │  Curator    │                         │
  │  │  (QC/attest) │  │  (discovery)│                         │
  │  └─────────────┘  └─────────────┘                         │
  ├───────────────────────────────────────────────────────────┤
  │                    INFRASTRUCTURE TIER                      │
  │  ┌─────────────┐  ┌─────────────┐                         │
  │  │  Platform    │  │  Governance  │                         │
  │  │  Operator    │  │  Participant │                         │
  │  └─────────────┘  └─────────────┘                         │
  └───────────────────────────────────────────────────────────┘
```

**Role presence by vertical:**

| Role | Market | Music | WebAssist | SOS | Travel | ONEON | Koink | Devices |
|------|--------|-------|-----------|-----|--------|-------|-------|---------|
| Primary Creator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Secondary Creator | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ |
| Data Provider | ✓ | ✓ | ✓ | ✓ | — | ✓ | — | ✓ |
| Material Supplier | ✓ | — | — | — | ✓ | — | — | ✓ |
| Manufacturer | ✓ | — | — | — | — | — | — | ✓ |
| AI Agent | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Validator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Curator | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ | — |
| Platform Operator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Governance | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## 3. Data Flow — Complete Sequence

```
TIME →

  t0  DESIGNER submits chair design (IPFS hash)
      │
      ├─ SUBMIT event on-chain: {contributor, DESIGN, artifact_hash, otto-market:furniture}
      │
  t1  TWO PEERS review design + AI quality check
      │
      ├─ VERIFY: 2-of-3 quorum met → status=VERIFIED
      ├─ Attestation scores recorded: [82, 78, 85]
      │
  t2  DPC SCORE computed: Is=0.6×82 + Ec=0.2×streak(3) + Rw=0.2×0 = initial score
      │
      ├─ SCORE event: {registry_id, dpc_score=68, quality=0.82}
      │
  t3  Design listed in OTTO MARKET catalog
      │
      ├─ CATALOG event: {registry_id, status=ACTIVE, listed_at=now}
      │
  t4  CUSTOMER orders 50 chairs ($500 total)
      │
      ├─ DEMAND EVENT: {registry_id, PURCHASE, qty=50, buyer, $500}
      │
  t5  AI PRODUCTION PLANNER generates manufacturing specs
      │
      ├─ NESTED SUBMIT: {AI_agent, CODE, production_plan_hash, otto-market:furniture}
      ├─ Auto-verified (AI output, validated by system)
      ├─ NESTED SCORE: dpc computed for AI contribution
      ├─ Provenance link: production_plan → original_design
      │
  t6  MATERIAL SOURCING — wood supplier delivers materials
      │
      ├─ NESTED SUBMIT: {supplier, MATERIAL, receipt_hash, otto-market:furniture}
      ├─ VERIFY: receipt + delivery confirmation
      ├─ NESTED SCORE: dpc computed
      ├─ Provenance link: material → production_plan
      │
  t7  CARPENTER manufactures 50 chairs
      │
      ├─ NESTED SUBMIT: {carpenter, LABOR, evidence_hash, otto-market:furniture}
      ├─ VERIFY: 2 peers + site oracle (workshop GPS)
      ├─ NESTED SCORE: dpc computed (Is=0.7 weight for physical labor)
      ├─ Provenance link: labor → production_plan + material
      │
  t8  QC INSPECTOR verifies finished chairs
      │
      ├─ NESTED SUBMIT: {inspector, CURATION, qc_report_hash}
      ├─ VERIFY: spot-check + automated structural test
      ├─ NESTED SCORE: dpc computed
      │
  t9  DELIVERY to customer confirmed
      │
      ├─ NESTED SUBMIT: {logistics, OPERATION, delivery_proof}
      ├─ VERIFY: customer confirmation
      │
  t10 REVENUE SPLIT executes
      │
      ├─ Protocol fee: $25 → Treasury
      ├─ Governance: $15 → Staking Pool
      ├─ Contributor pool: $460 → split by (role_weight × dpc × quality) formula
      │   ├─ Designer:       ~$199
      │   ├─ Wood Supplier:  ~$140
      │   ├─ Carpenter:      ~$168
      │   ├─ AI Planner:     ~$13 (after 40% agent tax)
      │   ├─ QC Inspector:   ~$27
      │   ├─ Market Curator: ~$25
      │   ├─ Data Providers: ~$11 (direct) + $4.37 (from agent tax)
      │   ├─ Platform Ops:   ~$16
      │   └─ Validators:     ~$2.63 (from agent tax)
      │
  t11 GOVERNANCE WEIGHT ACCRUAL for all participants
      │
      ├─ ΔG for each: sqrt(cumDPC) × ln(1+revenue) × tenure
      │
  t12 FEEDBACK SIGNALS fire
      │
      ├─ Designer's Rw increases (demand validated the design)
      ├─ Carpenter's DPC rises (more verified labor hours)
      ├─ Quality benchmark updates (revenue/design ratio recorded)
      ├─ AI training data enriched (production plan → outcome mapping)
      │
  t13 NEXT CYCLE BEGINS with updated scores, benchmarks, and trust levels
```

---

## 4. Payment Triggers — Exhaustive List

| Trigger | When | Who Pays | Who Receives | Amount |
|---------|------|----------|--------------|--------|
| `demand.purchase` | Customer buys product | Customer | Provenance chain | Purchase price |
| `demand.stream` | User plays a track | Platform treasury | Artist + chain | Per-stream rate |
| `demand.license` | Sync/commercial license | Licensee | Creator + data providers | License fee |
| `demand.enroll` | Student enrolls in module | Student/sponsor | Educator + chain | Enrollment fee |
| `demand.book` | Travel booking confirmed | Traveler | Host + community + chain | Booking price |
| `demand.access` | Memory Capsule queried | Querier | Capsule owner + data chain | Per-query rate |
| `demand.trade` | Token traded | Trader (fee) | Creator + LP + governance | Trade fee % |
| `demand.subscribe` | Recurring subscription | Subscriber | Service chain | Subscription price |
| `demand.impression` | Ad impression batch | Advertiser | Content host + user | CPM rate |
| `attestation.stake` | Validator stakes on attestation | Validator | Locked (slashable) | Stake amount |
| `attestation.reward` | Correct attestation confirmed | Protocol | Validator | Attestation bounty |
| `attestation.slash` | False attestation proven | Validator (lost) | Reporter + treasury | Slashed stake |
| `governance.vote` | Vote cast on proposal | — | Voter (DPC weight) | Governance weight Δ |
| `agent.tax` | AI agent earns revenue | Agent share | Data providers + validators + treasury | Tax rate × share |

---

## 5. Contribution Scoring — Complete Parameter Table

### 5.1 DPC Weights

| Contribution Type | Is (Structural) | Ec (Consistency) | Rw (Resonance) | Min Attestors | Quality Floor |
|-------------------|-----------------|-------------------|-----------------|---------------|---------------|
| DESIGN | 0.60 | 0.20 | 0.20 | 2 peers + AI | 0.60 |
| CODE | 0.60 | 0.20 | 0.20 | 1 reviewer + CI | 0.50 |
| DATA | 0.50 | 0.20 | 0.30 | 2 validators | 0.40 |
| LABOR | 0.70 | 0.20 | 0.10 | 2 peers + oracle | 0.50 |
| MATERIAL | 0.80 | 0.10 | 0.10 | Receipt + 1 validator | 0.30 |
| CAPITAL | 0.40 | 0.30 | 0.30 | On-chain proof | N/A |
| CURATION | 0.30 | 0.30 | 0.40 | Peer attestation | 0.50 |
| OPERATION | 0.20 | 0.60 | 0.20 | Attendance + peer | 0.40 |
| EDUCATION | 0.30 | 0.30 | 0.40 | Student + completion | 0.50 |
| COMMUNITY | 0.10 | 0.30 | 0.60 | DPC-weighted peers | 0.40 |

### 5.2 Revenue Split Parameters

| Parameter | Default | Range | Governance Adjustable |
|-----------|---------|-------|-----------------------|
| `protocol_fee_bps` | 500 (5%) | 100-1000 | Yes, requires 2/3 supermajority |
| `governance_accrual_bps` | 300 (3%) | 100-500 | Yes, requires simple majority |
| `agent_tax_rate_bps` | 4000 (40%) | 1000-6000 | Yes, requires 2/3 supermajority |
| `agent_tax_data_split` | 5000 (50%) | 3000-7000 | Yes |
| `agent_tax_validator_split` | 3000 (30%) | 1000-4000 | Yes |
| `agent_tax_treasury_split` | 2000 (20%) | 1000-3000 | Yes |
| `max_single_share_bps` | 5000 (50%) | 3000-7000 | Yes — prevents any single participant from taking >50% |
| `min_creator_share_bps` | 2000 (20%) | 1000-3000 | Yes — floor for primary creator |
| `quality_floor` | 0.40 | 0.20-0.80 | Yes, per contribution type |
| `decay_lambda` | 0.05/month | 0.01-0.10 | Yes |

### 5.3 Governance Weight Parameters

| Parameter | Default | Range | Notes |
|-----------|---------|-------|-------|
| `dpc_exponent` | 0.5 (sqrt) | 0.3-0.7 | Lower = more egalitarian |
| `revenue_log_base` | e (natural log) | — | Fixed — logarithmic by design |
| `tenure_cap_months` | 24 | 12-36 | Max tenure bonus period |
| `decay_lambda_governance` | 0.05/month | 0.02-0.10 | How fast inactive weight fades |
| `capital_governance_weight` | 0.00 | 0.00 | **Immutable** — capital earns returns, not governance |

---

## 6. Demand Oracles — Architecture

```
DEMAND ORACLE PATTERN (reusable per vertical):

  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
  │ DEMAND SOURCE    │────►│ DEMAND ORACLE     │────►│ SPLIT ENGINE     │
  │ (vertical-native)│     │ (on-chain)        │     │ (on-chain)       │
  └──────────────────┘     └──────────────────┘     └──────────────────┘

  DEMAND SOURCE:
    - Otto Market:  Payment processor (Stripe → webhook → oracle)
    - Otto Music:   Play counter (off-chain batched → Merkle proof → oracle)
    - WebAssist:    Contract registry (on-chain escrow release)
    - SOS Systems:  Enrollment ledger (on-chain attestation)
    - Otto Travel:  Booking engine (payment confirmed → oracle)
    - ONEON:        Query metering (off-chain batched → oracle)
    - Koink.fun:    DEX swap events (on-chain, self-proving)

  ORACLE CONTRACT:
    - reportDemand(registry_id, quantity, payment_amount, metadata)
    - reportBatch(DemandEvent[]) — for batched sources (music, ONEON)
    - Authorized reporters: per-vertical signer (multisig for high-value)
    - Anti-manipulation: minimum batch size, cooldown period, reporter stake

  SPLIT ENGINE:
    - Reads provenance chain from Contribution Registry
    - Computes shares using role_weight × DPC × quality formula
    - Executes USDC/KOIN transfers to all participants
    - Emits RevenueDistributed event with full breakdown
```

**Hybrid on-chain/off-chain pattern:**

For high-frequency demand events (music streams, memory capsule queries), off-chain batching with on-chain settlement:

```
  Off-chain aggregator (Otto Memory API):
    1. Collects demand events over 24h window
    2. Computes Merkle root of all events
    3. Submits Merkle root + aggregated totals to oracle
    4. Oracle verifies and triggers Split Engine
    5. Individual participants can verify their inclusion via Merkle proof
```

---

## 7. Self-Reinforcement Mechanics

The Otto Loop is designed to accelerate over time. Here's how each feedback signal creates compounding returns:

### 7.1 Demand → Quality Flywheel

```
More demand → higher Rw scores → better catalog placement → more demand
```

Quantified: Each demand event increases the Rw component of all provenance contributions by:
```
ΔRw = ln(1 + demand_count) / ln(1 + previous_demand_count)
```
This is logarithmic — early demand events have the biggest impact (incentivizes discovery), diminishing but never zero (established creators still benefit from growth).

### 7.2 Agent Tax → Data Improvement Flywheel

```
AI earns revenue → tax → data providers earn → better data submitted →
better AI → higher quality output → more demand → more AI revenue → more tax
```

This is the critical flywheel that ensures AI improvement benefits everyone, not just the AI operator. The 40% agent tax rate is set high intentionally — it's the mechanism that prevents AI from hollowing out human contribution.

### 7.3 Governance → Parameter Evolution Flywheel

```
Contributors earn governance weight → vote on parameters →
parameters evolve toward contributor interests → higher quality contributions →
more demand → more governance weight
```

The `capital_governance_weight = 0.00` (immutable) ensures this flywheel is controlled by contributors, not investors. Investors earn financial returns through the protocol fee and capital contribution scores, but they don't shape the system's rules.

### 7.4 Trust → Efficiency Flywheel

```
Consistent verified contributions → higher trust score →
expedited verification (fewer attestors needed) → faster time-to-catalog →
faster time-to-revenue → more contributions → higher trust
```

Trust score thresholds:

| Trust Level | Contributions | Verification Change |
|-------------|---------------|---------------------|
| New | 0-5 | Full quorum (2-of-3) |
| Established | 6-25 | Reduced quorum (1-of-2 + automated) |
| Trusted | 26-100 | Automated + spot-check (10% manual) |
| Core | 100+ | Automated with post-hoc audit |

### 7.5 Nested Loops → Ecosystem Density

Each sale creates 5-8 new contribution entries. Those entries earn their own DPC scores, which feed into future splits. The ecosystem's total contribution density grows superlinearly with demand:

```
density(t) ≈ initial_contributions × demand_events^1.3
```

The 1.3 exponent comes from the production pipeline: each demand event triggers multiple nested submissions (AI planning, material sourcing, manufacturing, QC, logistics), and some of those trigger their own sub-loops (the wood supplier sources from a forest managed by another contributor, etc.).

---

## 8. Vertical Inheritance — How Each Project Uses the Loop

Each vertical inherits the 8-stage loop but configures different parameters:

### 8.1 Otto Market (Physical Goods)

```yaml
vertical: otto-market
primary_contribution: DESIGN
production_pipeline: true  # physical manufacturing
demand_oracle: purchase-order
settlement: USDC
role_weights:
  primary_creator: 1.00
  material_supplier: 0.80
  manufacturer: 0.90
  ai_agent: 0.15
  validator: 0.20
  curator: 0.25
  platform_operator: 0.15
  data_provider: 0.10
  governance: 0.10
```

### 8.2 Otto Music (Digital Content)

```yaml
vertical: otto-music
primary_contribution: DESIGN  # master recording is a design artifact
production_pipeline: false  # no physical production
demand_oracle: stream-counter (batched, Merkle)
settlement: USDC + KOIN
role_weights:
  primary_creator: 1.00      # artist
  secondary_creator: 0.80    # producer, features
  ai_agent: 0.15             # AI mastering, recommendation
  validator: 0.15            # quality reviewers
  curator: 0.40              # discovery is high value in music
  platform_operator: 0.10
  data_provider: 0.10
  governance: 0.10
special_rules:
  - early_listener_bonus: true  # fans who discover first earn curator weight
  - sync_license_split: 50/25/25  # artist/label/platform for sync
```

### 8.3 WebAssist (Service Delivery)

```yaml
vertical: webassist
primary_contribution: CODE
production_pipeline: false  # digital delivery
demand_oracle: contract-escrow
settlement: USDC
role_weights:
  primary_creator: 1.00     # developer/designer
  ai_agent: 0.15            # AI that assists
  validator: 0.20           # code reviewer
  platform_operator: 0.20   # WebAssist infra (higher — service business)
  data_provider: 0.10
  governance: 0.05
special_rules:
  - client_satisfaction_bonus: true  # multiplier on positive outcome
  - recurring_revenue_split: 70/20/10  # creator/platform/governance for maintenance
```

### 8.4 SOS Systems (Education + Governance)

```yaml
vertical: sos-systems
primary_contribution: EDUCATION
production_pipeline: false
demand_oracle: enrollment-attestation
settlement: KOIN (primarily)
role_weights:
  primary_creator: 1.00     # educator/mentor
  secondary_creator: 0.70   # curriculum collaborators
  ai_agent: 0.10            # AI tutoring (low weight — education is human)
  validator: 0.30            # student outcomes are key validation
  curator: 0.20             # path recommendation
  platform_operator: 0.10
  data_provider: 0.15
  community: 0.30           # community governance is core to SOS
  governance: 0.15
special_rules:
  - outcome_multiplier: true       # revenue increases with student success metrics
  - contribution_as_learning: true # contributing to system IS the learning path
  - refugee_subsidized: true       # zero-cost access for qualifying individuals
```

### 8.5 Otto Travel / Tusita (Physical Experience)

```yaml
vertical: otto-travel
primary_contribution: OPERATION  # experience hosting
production_pipeline: true  # physical space preparation
demand_oracle: booking-confirmed
settlement: USDC + local fiat bridge
role_weights:
  primary_creator: 1.00     # host/experience designer
  material_supplier: 0.60   # food, materials, space maintenance
  manufacturer: 0.50        # construction/renovation
  ai_agent: 0.10            # booking optimization, recommendation
  validator: 0.20           # guest reviews
  curator: 0.35             # travel discovery is high value
  platform_operator: 0.15
  community: 0.30           # Tusita community maintains the space
  governance: 0.15
special_rules:
  - community_revenue_share: true  # portion of booking goes to local Tusita dome
  - sustainability_bonus: true     # eco-certified experiences earn multiplier
```

### 8.6 ONEON (Identity + Intelligence)

```yaml
vertical: oneon
primary_contribution: DATA  # memory capsules
production_pipeline: false
demand_oracle: query-metering (batched, Merkle)
settlement: KOIN
role_weights:
  primary_creator: 1.00     # capsule owner
  ai_agent: 0.10            # inference, retrieval
  validator: 0.25           # quality scoring
  curator: 0.20             # capsule discovery
  platform_operator: 0.10
  data_provider: 0.30       # high — this IS the data layer
  governance: 0.15
special_rules:
  - privacy_premium: true   # private capsule queries cost more, owner earns more
  - derivation_royalty: true # if someone's capsule uses yours as training data, perpetual royalty
```

---

## 9. Smart Contract Architecture

The Otto Loop requires 4 new contracts that compose with the existing OPRLP and Labor Attestation contracts:

```
OTTO LOOP CONTRACT STACK:

  EXISTING (already designed):
  ├── DPCRegistry.sol           — DPC score storage
  ├── GovernanceWeight.sol      — sqrt(DPC) vote weighting
  ├── LaborAttestation.sol      — multi-party attestation
  ├── ContributionEquity.sol    — soulbound CET tokens
  ├── AnnotationRegistry.sol    — memory capsule annotations
  ├── ProvenanceGraph.sol       — derivation chains
  ├── UsageOracle.sol           — usage event reporting
  └── RoyaltyPool.sol           — royalty distribution

  NEW (Otto Loop layer):
  ├── ContributionRegistry.sol  — universal catalog (Stage 4)
  ├── DemandOracle.sol          — demand event reporting (Stage 5)
  ├── SplitEngine.sol           — revenue distribution (Stage 6)
  └── LoopGovernor.sol          — parameter governance (Stage 7)
```

### 9.1 ContributionRegistry.sol

```solidity
interface IContributionRegistry {
    struct Entry {
        bytes32 registryId;
        address contributor;
        bytes32 projectId;
        uint8 contributionType;
        bytes32 artifactHash;
        uint32 dpcScore;
        uint8 catalogStatus;       // DRAFT=0, ACTIVE=1, SUSPENDED=2, ARCHIVED=3
        uint32 listedAt;
        bytes32[] provenanceChain;
        uint32 demandCount;
        uint256 totalRevenue;
    }

    function register(bytes32 projectId, uint8 cType, bytes32 artifactHash, bytes32[] calldata provenance) external returns (bytes32 registryId);
    function activate(bytes32 registryId) external;                    // called after verification
    function updateDPC(bytes32 registryId, uint32 newScore) external;  // called by DPCRegistry
    function recordDemand(bytes32 registryId, uint32 quantity, uint256 revenue) external;  // called by DemandOracle
    function getProvenance(bytes32 registryId) external view returns (bytes32[] memory);
    function getEntry(bytes32 registryId) external view returns (Entry memory);
}
```

### 9.2 DemandOracle.sol

```solidity
interface IDemandOracle {
    struct DemandEvent {
        bytes32 registryId;
        uint8 demandType;          // PURCHASE=0, STREAM=1, LICENSE=2, etc.
        uint32 quantity;
        address buyer;
        uint256 paymentAmount;
        bytes metadata;
    }

    function reportDemand(DemandEvent calldata evt) external;
    function reportBatch(DemandEvent[] calldata evts) external;        // for high-frequency verticals
    function reportMerkle(bytes32 merkleRoot, uint256 totalAmount, uint32 eventCount) external;  // batched settlement
    function verifyInclusion(bytes32[] calldata proof, DemandEvent calldata evt) external view returns (bool);
}
```

### 9.3 SplitEngine.sol

```solidity
interface ISplitEngine {
    struct SplitConfig {
        uint16 protocolFeeBps;
        uint16 governanceAccrualBps;
        uint16 agentTaxBps;
        uint16 maxSingleShareBps;
        uint16 minCreatorShareBps;
    }

    struct Payout {
        address recipient;
        uint256 amount;
        uint8 role;
    }

    function split(bytes32 registryId, uint256 grossAmount) external returns (Payout[] memory);
    function previewSplit(bytes32 registryId, uint256 grossAmount) external view returns (Payout[] memory);
    function updateConfig(SplitConfig calldata config) external;       // requires LoopGovernor
    function updateRoleWeight(uint8 role, uint16 weightBps) external;  // requires LoopGovernor
}
```

### 9.4 LoopGovernor.sol

```solidity
interface ILoopGovernor {
    struct Proposal {
        bytes32 proposalId;
        address proposer;
        uint8 parameterType;       // PROTOCOL_FEE=0, AGENT_TAX=1, ROLE_WEIGHT=2, etc.
        bytes newValue;
        uint32 votingDeadline;
        uint256 forWeight;
        uint256 againstWeight;
        bool executed;
    }

    function propose(uint8 paramType, bytes calldata newValue, string calldata description) external returns (bytes32);
    function vote(bytes32 proposalId, bool support) external;
    function execute(bytes32 proposalId) external;
    function getGovernanceWeight(address participant) external view returns (uint256);

    // Immutable constraint:
    // capital_governance_weight is always 0 — cannot be changed by any proposal
}
```

---

## 10. Off-Chain Components (Otto Memory API)

The on-chain contracts handle settlement and provenance. The off-chain layer handles orchestration, AI inference, and high-frequency events.

### 10.1 New API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/loop/submit` | POST | Submit a contribution (pre-chain staging) |
| `/loop/verify` | POST | Request/submit verification |
| `/loop/catalog` | GET | Browse contribution catalog (with filters) |
| `/loop/demand` | POST | Report a demand event (batched for chain) |
| `/loop/split/preview` | POST | Preview revenue split before execution |
| `/loop/split/execute` | POST | Execute split (triggers on-chain tx) |
| `/loop/governance/weight` | GET | Get governance weight for address |
| `/loop/governance/propose` | POST | Create governance proposal |
| `/loop/provenance/{id}` | GET | Full provenance chain for a contribution |
| `/loop/analytics/flywheel` | GET | Flywheel health metrics (velocity, density, quality) |

### 10.2 Flywheel Health Metrics

```
FLYWHEEL DASHBOARD (per vertical + ecosystem-wide):

  velocity:       contributions_per_day / demand_events_per_day
  density:        avg_provenance_chain_length (deeper = more participants per sale)
  quality_trend:  avg_attestation_score over rolling 30d
  governance_active: % of weight-holders who voted in last 30d
  agent_ratio:    agent_contributions / total_contributions (monitor for hollowing)
  revenue_per_contribution: total_revenue / total_contributions (efficiency)
  new_contributor_rate: first-time contributors in last 30d
  trust_distribution: % at each trust level (new/established/trusted/core)
```

---

## 11. Key Decisions

- **Single primitive over per-vertical models:** Chosen because ecosystem coherence matters more than per-vertical optimization. A furniture designer who also contributes music should see one DPC score, one governance weight. Alternative: per-vertical isolated economies — rejected because it fragments governance and creates arbitrage.

- **92% to contributors, 5% protocol, 3% governance:** Chosen to maximize contributor retention. Alternative: higher protocol fee (10-15%) — rejected because it recreates extraction. The protocol sustains on 5% which is well below industry standard (15-30% for marketplaces).

- **40% agent tax:** Chosen high intentionally per Mev's directive that "efficiency gains from automation must flow back into the system." Alternative: 15-20% — rejected because it doesn't create enough pressure to fund the data provider flywheel. The rate is DAO-adjustable within 10-60% bounds.

- **Capital earns zero governance weight (immutable):** Chosen because the system must be governed by contributors, not capital. This is a constitutional decision, not a parameter — it cannot be changed by governance vote. Alternative: small governance weight for capital — rejected because any non-zero weight creates path to plutocracy.

- **Logarithmic revenue-to-governance mapping:** `ln(1 + revenue)` ensures that the first $100 earned matters more than the difference between $1M and $1.1M. Prevents revenue whales from dominating governance. Alternative: linear — rejected because it recreates wealth-based power.

- **Merkle-batched settlement for high-frequency verticals:** Music streams and memory capsule queries can't afford per-event on-chain settlement. Batched with Merkle proofs preserves verifiability at 1000x lower gas. Alternative: per-event settlement — rejected for cost. L2 rollups — considered but adds complexity without clear need in Phase 1.

- **Provenance chain, not flat attribution:** Revenue traces through the full derivation tree, not just the last contributor. The furniture designer earns from every chair sold, even years later, because their design is in the provenance chain. Alternative: one-time payment to creator — rejected because it's the model we're trying to destroy.

---

## 12. Risks

- **DPC gaming:** Participants could collude on attestations to inflate scores. Mitigation: anti-collusion window (attestation pairs limited to 3/month), stake-slash for false attestation, DPC decay for inactive contributors.

- **Agent tax avoidance:** AI agents could be disguised as human contributors to avoid the 40% tax. Mitigation: contribution type verification includes tooling fingerprints, on-chain attestation requires human-specific signals (biometric, social graph, physical presence).

- **Oracle manipulation:** Demand oracles could report false events. Mitigation: authorized reporter multisig, minimum batch size, cooldown periods, reporter stake that gets slashed for proven manipulation.

- **Governance capture:** Despite capital exclusion, a coordinated group of high-DPC contributors could capture governance. Mitigation: OPRLP council rotation (no permanent positions), CartelDetector contract (existing), ranked-choice voting.

- **Cold start:** No demand = no revenue = no flywheel. Mitigation: treasury-funded bootstrap rewards for early contributors (first 1000 contributions per vertical get bonus DPC), progressively reduced as organic demand grows.

- **Complexity burden:** 10 roles × 8 stages × N verticals = significant orchestration. Mitigation: off-chain Otto Memory API handles orchestration; on-chain contracts are minimal (registry, oracle, split, governor). Most participants never interact with contracts directly — they use vertical-specific UIs.

---

## 13. Implementation Plan

### Phase 1: Off-Chain Prototype (~$8-12)
1. Add `/loop/*` endpoints to Memory API (contribution registry, demand reporting, split preview)
2. Implement DPC scoring engine in Python (mirrors on-chain formula)
3. Build provenance chain data model (PostgreSQL, extends existing task/contribution tables)
4. Create flywheel health dashboard in OMS
5. Wire Otto Market (furniture scenario) as first vertical

### Phase 2: Smart Contracts (~$15-20)
1. Deploy ContributionRegistry.sol on testnet (Polygon zkEVM or Base)
2. Deploy DemandOracle.sol with Merkle batch support
3. Deploy SplitEngine.sol integrated with existing DPCRegistry
4. Deploy LoopGovernor.sol with immutable capital exclusion
5. Integration tests: full loop from submit → split on testnet

### Phase 3: Multi-Vertical (~$10-15)
1. Configure Otto Music vertical (streaming demand oracle)
2. Configure WebAssist vertical (escrow-based demand)
3. Configure SOS Systems vertical (enrollment-based)
4. Build vertical-specific UIs inheriting from shared Loop components
5. Mainnet deployment with governance bootstrap

---

*This document defines the canonical Otto Loop. All vertical economic designs must inherit from this primitive. Deviations require governance proposal and 2/3 supermajority approval.*

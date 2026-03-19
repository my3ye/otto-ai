# MY3YE Capital Raise Strategy
**Version 2.0 — 2026-03-20 | Synthesized by Otto**
*Prior version: capital_raise_plan.md (2026-03-17). This supersedes it with updated research, 2026 regulatory context, and complete playbooks.*

---

## Executive Summary

MY3YE is raising capital across four parallel paths simultaneously. No single path is the plan — all four are. The paths compound each other: WebAssist revenue proves the model, grants validate the public goods narrative, the token launch builds community ownership, and VC provides the acceleration capital.

**6-Month Capital Targets:**
| Path | Target | Timeline | Dilution |
|------|--------|----------|----------|
| WebAssist Revenue | $50K+ ARR | Months 1–3 | Zero |
| Grants (Web3 + impact) | $150K–$350K | Months 2–5 | Zero |
| $KOIN Token Launch | Community treasury + liquidity | Month 2–3 | Zero (community owned) |
| Strategic VC / Seed | $250K–$750K SAFE | Months 3–5 | 10–15% |
| **Total** | **$500K–$1.15M+ equivalent** | **Month 6** | |

**Critical unlock order:**
1. Stripe keys → WebAssist revenue → all other paths gain credibility
2. Tokenomics paper → chain decision → fair launch
3. Public goods narrative → grant applications
4. Traction data (clients + grants) → VC conversations

---

## PATH 1 — WebAssist Revenue (Fastest Cash)

**Goal:** $5K MRR by Month 1. $50K ARR by Month 3. Proof-of-market that funds everything else.

### Why This Is First
WebAssist is live at webassist.ink. Every other capital path (grants, VC, token) requires demonstrated execution. A paying client base is the single most credible signal. No grant committee or VC wants to see an idea — they want to see a product with customers.

### Revenue Model

| Tier | Price | Deliverable | Target |
|------|-------|-------------|--------|
| **Starter** | $499/mo | 3-page site + hosting + basic SEO | SMBs, freelancers |
| **Growth** | $1,499/mo | 8-page site + CMS + analytics + copy | Funded startups |
| **Pro** | $2,995/mo | Full brand site + integrations + 12-mo support | Series A+ or enterprises |
| **Enterprise** | Custom | Full build + AI features + ongoing dev | Web3 projects, DAOs |

**LTV calculation at 70% annual retention:**
- Starter: $499 × 12 × 1.4 = ~$8.4K LTV
- Growth: $1,499 × 12 × 1.4 = ~$25.2K LTV
- Pro: $2,995 × 12 × 1.4 = ~$50.3K LTV

**Target: 3 Growth + 2 Pro clients = $9,477/mo = ~$113K ARR**

### Fastest Path to 10 Clients

**Week 1–2: Direct founder outreach**
- Target: Early-stage Web3 startups and Web2 SaaS founders who just raised seed (recently funded = need a website NOW)
- Source: Crunchbase recently funded list, AngelList, Republic.co recently launched
- Message: "Saw you just raised / launched. Your site doesn't reflect the product. We fix that in 2 weeks. Here's what we'd change [1 specific observation about their current site]."
- Goal: 2 signed contracts at Growth tier

**Week 2–4: Community positioning**
- Post WebAssist case studies in Farcaster, BuildSpace, Indie Hackers
- Offer free homepage audit for first 10 applicants → converts ~20% to paid
- List on Product Hunt in Month 2

**Month 2: Referral engine**
- Implement 20% first-month credit for referrals
- Each happy client refers 1.5 clients on average → 3 clients → 4.5 → compounding
- Partner with Web3 dev shops (we do frontend/brand, they do backend/infra → mutual referrals)

**Month 2–3: Content SEO**
- Publish 4 articles targeting: "website for crypto startup", "Web3 landing page agency", "AI website builder for SaaS"
- Rank for long-tail terms with low competition

### Growth Accelerators

1. **BANKR Bot integration** — Use BANKR agent API to automate outreach and lead qualification. `bk_...` key available.
2. **Farcaster channel** — Build `/webassist` channel, share builds, get community engagement
3. **Product Hunt launch** — Target 500+ upvotes, drives 200–500 signups, ~20 trial conversions
4. **Stripe billing live** — Required unlock. Every day without this is lost revenue.
5. **AI features differentiator** — Lean into "AI-built sites" narrative. Cheaper, faster than agencies. Show the Otto-built stack as a selling point.

---

## PATH 2 — $KOIN Token Launch (Community Ownership)

**Goal:** Fair launch within 60–75 days. Build a community treasury. Make $KOINK Standard the reference tokenomics framework for mission-aligned meme tokens.

### 2026 Regulatory Context (CRITICAL — READ FIRST)

On **March 17, 2026**, the SEC and CFTC jointly issued Interpretive Release No. 33-11412 — a 68-page framework establishing five categories for digital assets. Key implications:

| Classification | What It Means for $KOIN |
|----------------|------------------------|
| **Digital commodity** | Most meme/utility tokens now fall here (CFTC jurisdiction, lower compliance burden) |
| **Token Safe Harbor** | Time-limited exemption (~4 years) for early projects raising <$5M while building toward network maturity |
| **Airdrops cleared** | SEC/CFTC cleared Bitcoin mining, staking, and airdrops from securities obligations |
| **Fair launches** | Broadly favored — no VC allocation + wide distribution = strong commodity classification argument |

**Practical implication:** $KOIN launched as a fair launch, community-distributed, utility-enabled token is likely a **digital commodity under CFTC jurisdiction** — NOT a security. This is the most favorable regulatory environment for token launches since crypto began.

**Recommended legal posture:**
- Launch as a fair launch with no private sale, no VC allocation
- Publish tokenomics publicly before launch
- Include a clear utility layer (governance + Koink.fun fee discounts)
- No promises of returns or profit — position as community participation token
- Consult a crypto-native lawyer (Fenwick & West, Cooley, or Anderson Kill) for legal opinion letter before mainnet

### Tokenomics Design

**Total Supply: 1,000,000,000 $KOIN (1 billion)**

| Allocation | % | Amount | Vesting |
|-----------|---|--------|---------|
| **Fair Launch Pool** | 40% | 400M | No vesting — launch distribution |
| **Community Rewards** | 25% | 250M | Emitted over 3 years via contribution + staking |
| **Ecosystem Treasury** | 20% | 200M | 4-year vesting, multisig governance |
| **Team / MY3YE** | 10% | 100M | 1-year cliff, 3-year vest, public on-chain |
| **Liquidity Pool** | 5% | 50M | Locked 1 year minimum |

**Key mechanics:**
- **Diamond Hands Multiplier (DHM):** Hold for 12 months → 3x governance weight. Partial sell (<20%) doesn't reset.
- **Activity Factor:** Contribution activity prevents governance weight decay (Tier A: 5yr half-life, Tier B: 18mo half-life)
- **Quantum Koinkulator:** VRF-based allocation randomization for allowlist selection at launch (NOT open pool — prevents sniping)
- **Community treasury (20% of each transaction fee):** Governed by $KOIN holders via 505 Systems DPC

### Launch Playbook — 75-Day Plan

**Days 1–14: Foundations**
- [ ] Write and publish $KOIN tokenomics paper (public, no PDF paywall)
- [ ] Finalize chain decision (see below)
- [ ] Register `koink.fun` domains, set up waitlist page
- [ ] Write $KOINK Standard whitepaper (fork-able template for other projects)
- [ ] Set up @KoinkFun X account + Farcaster channel `/koink`

**Days 15–30: Build**
- [ ] Deploy $KOIN smart contract on testnet (Anchor on Solana OR Foundry on Base)
- [ ] Build Koink.fun landing page with countdown + email capture
- [ ] Set up fair launch mechanism (Meteora Alpha Vault Pro-Rata recommended — prevents sniping without VRF theater)
- [ ] Initiate smart contract audit (OtterSec for Solana, Spearbit for EVM — budget $5–15K)
- [ ] Post 3-part X/Farcaster thread series: "$KOINK Standard — Why Meme Tokens Keep Failing"

**Days 31–50: Community**
- [ ] Soft launch Koink.fun with Quantum Koinkulator demo
- [ ] Build Farcaster mini-app (Frame) for $KOINK allowlist sign-up
- [ ] Engage BONK DAO (Solana meme community, 350+ integrations, DAO grants available)
- [ ] DEGEN channel on Farcaster (300K+ users, active tipping economy)
- [ ] Partner with Bankr Bot for $KOINK Standard announcement (bankr.bot has Farcaster + Base audience)

**Days 51–65: Launch Prep**
- [ ] Complete audit, publish audit report publicly
- [ ] Set up Human Passport gate + Meteora Alpha Vault
- [ ] Finalize initial LP amount (target: $25–50K in initial liquidity)
- [ ] 48-hour countdown campaign across X, Farcaster, Discord
- [ ] Brief 3–5 Web3 media outlets (The Defiant, Blockworks, Decrypt)

**Day 66–75: Launch Window**
- [ ] $KOIN mainnet launch (Mev approve + trigger)
- [ ] Activate Quantum Koinkulator Farcaster Frame
- [ ] Post-launch: live metrics dashboard on koink.fun
- [ ] Begin $KOINK Standard deployment on Base and additional chains per Koink.fun chain-agnostic directive

### Chain Decision Framework

| Chain | Meme Culture | Fees | DeFi | DEX Ecosystem | Verdict |
|-------|-------------|------|------|--------------|---------|
| **Solana** | Native (pump.fun, BONK) | ~$0.001 | Raydium, Orca, Meteora | Excellent | **First launch** |
| **Base** | Growing (Brett, meme L2) | ~$0.01 | Uniswap V4, Doppler | Excellent | **Second (30 days post-Solana)** |
| **Ethereum** | DeFi/blue chip | $5–50 | Deepest liquidity | OG | No (fees kill meme community UX) |
| **Polkadot** | Niche | Low | Limited | Thin | Grants alignment only |

**Recommendation: Launch Solana first, then Base, then additional chains via $KOINK Standard.**

### Anti-Sniper Stack (from prior research)

1. **Human Passport gate** — requires World ID credential or Gitcoin Passport score ≥15
2. **Meteora Alpha Vault Pro-Rata** — commitment + stake escrow fee blocks multi-wallet spam
3. **Switchboard VRF** — randomizes allocation within allowlist (legitimate VRF use)
4. **Fee Scheduler** — high launch fee decays over 48 hours (Solana: Heaven DEX 6s sniper tax)
5. **Max wallet cap: 1%** at launch (trivially bypassed with 150+ wallets but deters casual snipers)

---

## PATH 3 — Grants (Non-Dilutive Capital)

**Target: $150K–$350K across 4–6 applications. First application by Week 2.**

### Grant Opportunity Matrix

| # | Program | Amount | Fit | Project | Deadline | Priority |
|---|---------|--------|-----|---------|----------|----------|
| 1 | **Arbitrum Trailblazer 2.0** | Up to $10K per submission | HIGH — AI agents on Arbitrum | Otto AI (deployed on Arbitrum) | Rolling, active NOW | P0 |
| 2 | **Gitcoin GG24+** | Community matching (QF) | HIGH — public goods, AI, WebAssist | Otto AI + WebAssist | Rolling/quarterly | P0 |
| 3 | **Web3 Foundation** | $50K–$100K | HIGH — 505 Systems + Panik App bundle | 505 Systems + Panik App | Rolling | P1 |
| 4 | **Ethereum Foundation ESP** | $25K–$100K | MEDIUM — Otto Memory / cognitive infra | Otto AI memory layer | Rolling, 6–12 week review | P1 |
| 5 | **Optimism RetroPGF** | $10K–$150K (retro) | MEDIUM — WebAssist + ONEON as public goods | WebAssist + ONEON | 2–3x per year | P1 |
| 6 | **Celo Foundation** | $10K–$50K | HIGH — Panik App humanitarian use case | Panik App | Rolling (Prezenti grants) | P1 |
| 7 | **Solana Foundation** | $10K–$50K | HIGH if chain = Solana | Koink.fun (post-launch) | Rolling | P2 |
| 8 | **BONK DAO Grants** | Varies | HIGH — Koink.fun natural fit | Koink.fun / $KOINK Standard | Apply post-Solana launch | P2 |
| 9 | **NEAR Foundation** | $20K–$75K | MEDIUM — 505 Systems DAO | 505 Systems | Rolling | P2 |
| 10 | **UNICEF Innovation Fund** | $50K–$100K (equity-free) | HIGH — SOS Systems humanitarian | SOS Systems | Rolling cohorts | P3 |

### Grant Application Priority Queue

**Immediate (Week 1–2):**

**1. Arbitrum Trailblazer 2.0 — Apply NOW**
- Program: $1M total, up to $10K per project
- Requirement: "Already launched AI agent featuring onchain integration with Arbitrum"
- Otto AI qualifies — deploy a minimal Otto agent on Arbitrum, document the API integration
- Application: arbitrum.foundation/grants → Trailblazer track
- Effort: 1 day (agent deploy + application)
- Realistic outcome: $5K–$10K approved within 3–4 weeks

**2. Gitcoin GG25 — Register project NOW**
- Program: Quadratic funding matching via community contributions
- Requirement: Project on Gitcoin.co, minimum community engagement before round opens
- Projects to list: Otto AI (decentralized intelligence infra), WebAssist (public goods tooling), SOS Systems (humanitarian)
- Strategy: Build community first (Farcaster, X) → drive $1 donations to boost matching multiplier
- Key insight from research: GTC Utility Experiment in GG23 (Q1 2026) — stake GTC to boost project ranking
- Realistic outcome: $15K–$50K in matching + contributions per project per round

**Month 1 (Weeks 3–6):**

**3. Web3 Foundation Grant — Submit proposal**
- Program: Polkadot ecosystem grants (rolling, milestone-based)
- Positioning: Bundle 505 Systems (OpenGov-aligned governance OS) + Panik App (humanitarian proof case)
- Required: Technical specification, team background, milestone breakdown
- Application: grants.web3.foundation
- Realistic outcome: $50K–$100K over 2 milestones, 6–8 week review
- Tip: Polkadot OpenGov values contribution-weighted governance — 505 Systems DPC is a direct thesis match

**4. Ethereum Foundation ESP**
- Program: Rolling grants for Ethereum ecosystem projects
- Positioning: Otto Memory system as decentralized cognitive infrastructure — novel dual-granularity retrieval, HyMem, vector + graph memory for AI agents
- Fit: "Decentralized infrastructure for AI agents" is an active ESP priority in 2026
- Application: esp.ethereum.foundation → "Project support" track
- Realistic outcome: $25K–$75K, 6–12 week review

**Month 2:**

**5. Optimism RetroPGF**
- Program: Retroactive public goods funding — rewards demonstrated impact
- Strategy: Deploy WebAssist as open-source template on OP Stack chains, document impact (users served, sites deployed)
- Note: Retroactive = must demonstrate impact FIRST. Apply once WebAssist has 10+ clients
- Realistic outcome: $10K–$100K depending on measured impact

**6. Celo Prezenti Grants**
- Program: Celo community grants (currently active round per research)
- Positioning: Panik App — mobile-first humanitarian emergency response tool, aligns with Celo's impact investing mandate and "2% for Web3 Impact" initiative
- Celo partnership angle: World Wildlife Fund, Gates Foundation as validators in their Social Impact Collective
- Realistic outcome: $10K–$30K, 4–6 week review

### Grant Application Assets Required

These reusable assets must be written ONCE and adapted per application:

1. **Public goods narrative** — "MY3YE as public goods infrastructure" (~1,000 words)
2. **Technical overview** — Otto memory architecture, agent system, API (2-page)
3. **Humanitarian brief** — Panik App + SOS Systems use case + impact metrics (1-page)
4. **Governance brief** — 505 Systems DPC architecture + Polkadot alignment (1-page)
5. **Team overview** — MY3YE founding team, track record, GitHub activity

---

## PATH 4 — VC / Strategic Investment

**Goal:** $250K–$750K SAFE note from 1–2 strategic investors. Timeline: Months 3–5 (after traction exists).

### 2026 VC Landscape

Crypto VC funding hit **$4.8 billion in Q1 2026** — significant rebound. Investment is concentrating in:
1. **AI × blockchain intersection** — most active area
2. **Real-world utility** — VCs done with pure speculation
3. **Infrastructure + tooling** — developers pay, scales without sales
4. **Decentralized social** — Farcaster showing investor confidence

**The shift:** VCs in 2026 want real users and real revenue before seed. Even modest traction ($5K MRR, 500 users) is fine — but it must be real.

### Target VC List — 15 Firms

| # | Firm | Thesis Match | Check Size | Priority |
|---|------|-------------|-----------|----------|
| 1 | **Coinbase Ventures** | Web3 infra, AI, Base ecosystem | $25K–$1M | P0 — BANKR Bot already has their backing; ecosystem fit |
| 2 | **Paradigm** | Research-driven infra, deep tech | $500K–$5M | P0 — Otto AI + ONEON thesis fit; need traction |
| 3 | **a16z Crypto** | Consumer crypto, Web3 social, AI agents | $250K–$2M | P1 — very competitive but perfect thesis fit |
| 4 | **Multicoin Capital** | Solana ecosystem, DeFi, consumer | $250K–$3M | P1 — Solana-native for $KOIN; DeFi composability |
| 5 | **OKX Ventures** | AI agents, onchain assets, infrastructure | $100K–$2M | P0 — 2026 thesis explicitly mentions AI agents + onchain; perfect match |
| 6 | **Binance Labs** | Web3 + AI + biotech, early stage | $100K–$1M | P1 — broad mandate, active seed stage |
| 7 | **Pantera Capital** | Infrastructure, DeFi, cross-chain | $500K–$5M | P2 — portfolio includes Polkadot; need more traction |
| 8 | **Foresight Ventures** | AI-crypto convergence, consumer apps | $100K–$1M | P1 — AI-native, bridges US+Asia markets |
| 9 | **Brevan Howard Digital** | AI × blockchain intersection | $1M+ | P2 — institutional, need significant traction |
| 10 | **Village Capital** | Impact investing, social good | $100K–$500K | P1 — SOS Systems + Tusita mission alignment |
| 11 | **Variant Fund** | Web3 ownership economy, DAOs | $250K–$2M | P1 — ONEON + 505 Systems governance thesis |
| 12 | **Electric Capital** | Developer ecosystems, open source | $250K–$2M | P2 — needs open-source traction metrics |
| 13 | **1kx** | DeFi, tokenomics, token design | $100K–$500K | P1 — $KOIN tokenomics is a direct thesis match |
| 14 | **Placeholder VC** | Decentralized protocols, public goods | $250K–$1M | P1 — ONEON + 505 Systems + public goods narrative |
| 15 | **AU21 Capital** | Early stage, broad Web3 | $25K–$500K | P0 — most accessible, portfolio of 170+ projects |

### Investment Narrative (2026 framing)

**The pitch in 3 sentences:**
> "Every AI system today extracts intelligence from users and centralizes the benefit. MY3YE builds the opposite — a sovereign civilization stack where every contribution is owned, valued, and governed by the community that made it. We're starting with WebAssist (AI website service with $5K MRR), launching $KOIN (community token), and building toward a world where the infrastructure itself is collectively owned."

**The four narratives that resonate in 2026:**

1. **AI × Sovereignty** — "AI agents that serve users, not platforms" (OKX Ventures' 2026 thesis explicitly mentions this)
2. **Decentralized social infrastructure** — Farcaster proved market exists; MY3YE extends it to full stack
3. **Revenue + community** — Rare combination: WebAssist generates cash while $KOIN builds community treasury
4. **Token-aligned team** — No salary extraction; team compensation is token-aligned via vesting

**Metrics to hit before VC outreach:**
- 5+ paying WebAssist clients
- $5K+ MRR
- 1 grant approved
- $KOIN testnet deployed
- 500+ email subscribers / Gitcoin project registered
- Otto AI agent demo on Arbitrum

### SAFE Terms to Propose
- **Amount:** $250K–$500K
- **Valuation cap:** $3M–$5M (adjust based on traction at time of raise)
- **Discount:** 20% (standard)
- **Pro-rata rights:** Yes
- **MFN clause:** Yes (protects early investors)
- **Structure:** Separate SAFEs for each investor (not one round)
- **Community governance protection:** SAFE converts to token allocation or equity at Mev's discretion — governance rights CANNOT be sold to majority bloc

### Outreach Sequence
1. **Warm path first** — Identify mutual connections via LinkedIn/Farcaster (Coinbase Ventures via BANKR Bot connection is a real warm path)
2. **Content-first approach** — Mev posts MY3YE thread on X → VCs follow → inbound > cold outreach
3. **Cold outreach template** — "We're building [X]. We have [traction]. I'd love 20 minutes. [Specific insight about their portfolio company that relates to what we're doing]."
4. **Never cold email the general inbox** — find partner email or use intro request via AngelList/OpenVC

---

## Cross-Path Priority Matrix

### What to Do First (Decision Framework)

```
Day 1-3 (RIGHT NOW):
  → Stripe keys setup (Mev action — unblocks ALL revenue)
  → Write $KOIN tokenomics paper (Otto)
  → Write public goods narrative (Otto)
  → Apply to Arbitrum Trailblazer 2.0 (Otto builds + applies)

Week 1-2:
  → Register Gitcoin projects (Otto)
  → Begin WebAssist outreach (50 targets identified by Otto, Mev sends)
  → Start Web3 Foundation grant proposal draft (Otto)
  → Set up koink.fun waitlist page (Otto)

Month 1:
  → First paying client signed (Mev closes)
  → $KOIN testnet deployed
  → WF3 grant submitted
  → ETH Foundation ESP submitted
  → Gitcoin projects receiving first contributions

Month 2:
  → $5K MRR reached → start VC conversations
  → $KOIN mainnet launch on Solana
  → First grant result (approve/deny)
  → Pitch deck finalized

Month 3:
  → VC outreach begins in earnest
  → Optimism RPGF application (once retro impact demonstrated)
  → $KOIN on Base (second chain)
  → BONK DAO community collaboration

Month 4-6:
  → First SAFE closed
  → Multiple grants in progress
  → $KOIN on 3+ chains
  → WebAssist at $15–20K MRR
```

### Effort vs. Capital Matrix

```
                    HIGH EFFORT         LOW EFFORT
HIGH CAPITAL    VC Seed ($250K+)    Token Launch (community)
                [Month 3+]          [Month 2]

LOW CAPITAL     WebAssist           Gitcoin / Arbitrum
                (Revenue, not       Trailblazer (rolling,
                capital)            apply immediately)
```

**The order of operations:**
1. **Gitcoin + Arbitrum** — Apply now. Rolling. Low effort. $5–50K possible.
2. **WebAssist clients** — Close first 5 clients. $5K MRR is the unlock signal.
3. **$KOIN launch** — 75-day playbook. Community capital + treasury.
4. **Web3F + ETH ESP** — Apply Month 1. $75–175K possible.
5. **VC raise** — Start conversations Month 3 with traction in hand.

---

## Supporting Infrastructure Required

These must be built to support ALL capital paths:

| Asset | Purpose | Used By | Status |
|-------|---------|---------|--------|
| Public goods narrative | Grant applications | All grants | TODO |
| $KOIN tokenomics paper | Token launch + VC | Token + VC | TODO |
| Investor one-pager (2-page PDF) | VC outreach | VC | TODO |
| OMS /capital page | Track all 4 paths | Mev visibility | TODO |
| Pitch deck (10 slides) | VC conversations | VC | TODO |
| Gitcoin project pages | Community funding | Gitcoin | TODO |
| Koink.fun waitlist page | Token launch | Token | TODO |
| Legal opinion letter | Token launch | Token | TODO (crypto lawyer) |

---

## Blockers and Dependencies

| Blocker | Blocking | Owner | Urgency |
|---------|---------|-------|---------|
| **Stripe live keys** | WebAssist revenue | Mev | P0 — revenue stopped |
| **Chain decision ($KOIN)** | Token launch path | Mev | P0 — Solana recommended |
| **Smart contract audit budget** | Token mainnet launch | Mev | P1 — $5–15K needed |
| **Crypto lawyer** | Token legal clearance | Mev | P1 — SEC/CFTC framework now favorable |
| **Initial LP capital** | Token launch liquidity | Mev | P1 — $25–50K needed |

---

## Key Strategic Insights (2026 Context)

1. **The SEC/CFTC March 2026 framework is the best legal environment in crypto history.** A fair launch, community-distributed utility token is almost certainly a digital commodity under CFTC jurisdiction — not a security. Act now while clarity exists.

2. **AI agents are the investment theme of 2026.** Every VC thesis we found cites AI agents + blockchain as the primary focus. Otto IS this thesis — we must make that the lead in every VC conversation.

3. **Grants have shifted to milestone-based and retroactive models.** The implication: ship first, document impact, THEN apply (especially Optimism RPGF). Gitcoin still runs community rounds where pre-existing community drives matching.

4. **Arbitrum Trailblazer 2.0 is the easiest $10K available right now.** Deploy an Otto agent on Arbitrum, apply. No competition from a funding standpoint — the program explicitly wants "already launched AI agents."

5. **The $4.8B Q1 2026 VC funding market is back.** This is the time to be in VC conversations. But VCs want real metrics — even small but real traction. $5K MRR + 1 grant = credible seed round story.

6. **The hybrid launch model is winning.** Community First + Product First + Token Second is the dominant pattern. MY3YE is executing this naturally: WebAssist (product), $KOIN (token after community), content/narrative (community building ongoing).

7. **Farcaster/DEGEN is the highest-density Web3-native builder community.** Every grant program, VC, and token launch benefits from Farcaster presence. This should be a core distribution channel for everything.

---

*Document maintained by Otto. Update after each capital event (grant result, client signed, VC conversation). Next review: 2026-04-20.*

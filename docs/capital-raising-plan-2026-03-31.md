# MY3YE / Ottolabs — Parallel Capital-Raising Master Plan
**Date:** 2026-03-31 | **Version:** 3.0 (supersedes capital-strategy-2026-03-20.md, ottolabs-capital-sequencing-2026-03-28.md)
**Author:** Otto (Architect Agent)
**Status:** ACTIVE — source of truth for all capital-raising activity

---

## Brutal Honest Assessment

Before the plan: the truth.

**What exists (real):**
- WebAssist: LIVE at webassist.ink. Zero revenue. Zero clients. Supabase migration pending (Mev). Stripe webhook pending (Mev).
- OMS: LIVE at mev.otto.lk. Internal tool, not revenue.
- otto.lk: LIVE. MY3YE ecosystem sites: all live (my3ye.xyz, tusita.xyz, oneon.ink, koink.fun, panik.app).
- Otto AI: Operational — Memory API, kernel, heartbeat, task queue, 20+ research papers implemented.
- $KOIN token: Paper-ready (tokenomics, vesting, legal analysis). Zero contracts written. Zero deployed. Zero community.
- Grant applications: Zero submitted. Zero approved. ENS application copy-paste ready (Mev must submit).
- Investor outreach: Zero contacts made. CRM has 10 VC/angel targets — all at NOT_STARTED.
- Revenue: $0 total. Ever.

**What doesn't exist (yet):**
- A single paying customer
- Any deployed smart contract
- Any submitted grant application
- Any investor conversation
- Any community beyond Mev and Otto
- Any public GitHub presence for Otto AI (otto-ai repo planned but not shipped)

**The gap:** Extensive strategy and architecture documentation. Zero execution on capital paths. The documents are excellent. The pipeline is empty.

**What this plan does:** Sequences the most credible path from $0 to first dollar, then compounds.

---

## The Four Capital Paths

### Path 1: Product Revenue (WebAssist)

| Attribute | Value |
|-----------|-------|
| **Current revenue** | $0/mo |
| **Confidence score** | 6/10 — product is live, but untested in market |
| **Time to first dollar** | 2–6 weeks after Stripe + Supabase unblock |
| **6-month target** | $5K–$15K MRR |
| **Dilution** | Zero |
| **Blockers** | Supabase migration (Mev), Stripe webhook (Mev) |

**Why this is Path 1:** Every other path — grants, token, VC — gains credibility from even one paying client. A $499/mo Starter client is worth more to the capital strategy than any amount of documentation. Revenue is the only path that doesn't require permission from a third party (once Stripe is live).

**Current state:**
- Product: LIVE, functional, AI-powered website builder
- Pricing: $499 (Starter) / $1,499 (Growth) / $2,995 (Pro) / Custom (Enterprise)
- Payment: NOT FUNCTIONAL — Stripe integration blocked on Mev credentials
- Outreach: ZERO — no prospects contacted, no content marketing, no Product Hunt
- Lead pipeline: WebAssist prospect list exists (~/otto/projects/capital/webassist_leadgen/), not activated
- Referral program: Designed, not deployed

**Next 3 concrete actions:**
1. **[MEV] Unblock Stripe + Supabase** — This is THE critical path. Every day without payment processing = $0 revenue. Target: this week.
2. **[OTTO] Activate outreach sequence** — Once Stripe is live, deploy the WebAssist outreach sequence (webassist_outreach_sequence.md) targeting recently-funded Web3 startups. Otto can draft all messaging, Mev sends from personal channels.
3. **[OTTO] Prepare Product Hunt launch** — Draft PH listing, collect 3 demo builds as portfolio, schedule for 2 weeks after first client (social proof needed for PH credibility).

**Revenue model:**
| Milestone | Revenue | Timeline | Gate |
|-----------|---------|----------|------|
| First paying client | $499–$1,499/mo | Week 2–6 (post-Stripe) | Stripe live |
| 3 clients | $2K–$5K/mo | Month 2 | Outreach active |
| $5K MRR | $5K/mo | Month 3–4 | Product-market signal |
| $15K MRR | $15K/mo | Month 6 | Referrals + content SEO |

---

### Path 2: Web3 Grants (Non-Dilutive)

| Attribute | Value |
|-----------|-------|
| **Total pipeline value** | $75K–$350K |
| **Confidence score** | 5/10 — strong fit, but zero applications submitted |
| **Time to first grant** | 4–10 weeks from application |
| **6-month target** | $50K–$150K approved |
| **Dilution** | Zero |
| **Blockers** | Mev must submit most applications (wallet connect, identity verification) |

**Why this is Path 2:** Grants don't require revenue. They require credible technology and mission alignment. Otto AI has both. Multiple grant programs are rolling (no deadline pressure), and application materials already exist.

**Current state:**
- Applications submitted: ZERO
- Applications drafted: 1 (ENS — copy-paste ready at ~/otto/projects/capital/ens_grant_application.md)
- Grant research: COMPLETE — comprehensive landscape report with 12+ opportunities ranked
- Public goods narrative: WRITTEN (~/otto/projects/capital/public_goods_narrative.md)
- Public GitHub repo: NOT SHIPPED (otto-ai planned but not published)

**Next 3 concrete actions:**
1. **[MEV] Submit ENS grant application** — Application is literally copy-paste ready. Go to builder.ensgrants.xyz/large-grant-apply, connect wallet, paste fields. 15 minutes. Up to $50K USDC.
2. **[MEV] Register 3 Gitcoin GG25 project profiles** — builder.gitcoin.co. Register Otto AI, SOS Systems, ONEON. 5 min each. GG25 expected May 2026 — community-building before round opens increases matching.
3. **[OTTO] Draft + ship Solana Foundation grant application** — Koink.fun on Solana framing. Otto drafts, Mev submits. $30K–$50K. Rolling review.

**Grant pipeline (ordered by speed × confidence):**

| # | Grant Program | Amount | Confidence | Time to Decision | Status | Next Action | Who |
|---|--------------|--------|------------|-----------------|--------|-------------|-----|
| 1 | ENS Public Goods Builder | $12K–$50K | 50% | 4–8 weeks | DRAFTED | Submit NOW | Mev |
| 2 | Gitcoin GG25 (QF) | $5K–$50K | 65% | May 2026 round | NOT STARTED | Register profiles NOW | Mev |
| 3 | Solana Foundation AI | $30K–$50K | 45% | 4–6 weeks | NOT STARTED | Draft application | Otto→Mev |
| 4 | Deep Funding (SingularityNET) | up to $100K | 40% | 6–10 weeks | NOT STARTED | Draft proposal | Otto→Mev |
| 5 | NEAR AI Agent Fund | $20K–$50K | 35% | 4–8 weeks | NOT STARTED | Draft technical brief | Otto→Mev |
| 6 | Arbitrum Trailblazer 2.0 | $5K–$10K | 50% | 2–4 weeks | NOT STARTED | Deploy Otto on Arbitrum | Otto→Mev |
| 7 | Ethereum Foundation ESP | $25K–$75K | 30% | 8–12 weeks | NOT STARTED | Needs public repo first | Otto→Mev |
| 8 | Starknet Seed Grants | $25K–$50K | 25% | 6–8 weeks | NOT STARTED | Research fit | Otto |
| 9 | Celo Prezenti (Panik App) | $10K–$30K | 30% | 3–6 weeks | NOT STARTED | Draft proposal | Otto→Mev |
| 10 | Optimism RPGF | $50K–$500K | 20% | Next retro round | NOT STARTED | Register projects | Mev |
| 11 | W3F / Polkadot Treasury | $10K–$30K | 25% | 4–8 weeks | NOT STARTED | Forum post first | Mev |
| 12 | Fetch.ai Accelerator | $50K+ | 20% | 6–12 weeks | NOT STARTED | Application | Mev |

**Expected value at current confidence levels:** ~$80K–$120K (weighted)
**If 3 of top 6 convert:** $50K–$150K

---

### Path 3: Token Launch ($KOIN / Koink.fun)

| Attribute | Value |
|-----------|-------|
| **Token readiness** | Paper: 9/10. Execution: 1/10. |
| **Confidence score** | 4/10 — excellent design, zero implementation |
| **Time to launch** | 60–90 days minimum from today |
| **Capital from launch** | Community treasury + LP ($25K–$50K minimum from Mev) |
| **Indirect capital** | Community engagement → grant matching → investor credibility |
| **Dilution** | Zero (fair launch, community-owned) |
| **Blockers** | Smart contracts (none written), LP capital ($25K–$50K from Mev), audit ($5K–$25K), chain decision, OWS wallet (Mev) |

**Why this is Path 3 (not Path 1):** Token launch requires working smart contracts, a security audit, LP capital, and community. None of these exist. The 60–90 day runway means this can't produce capital before Month 3 at earliest. It's critical for long-term ecosystem ownership but not for immediate survival.

**Current state:**
- Tokenomics paper: COMPLETE, excellent, unpublished
- Smart contracts: ZERO written (KoinkToken.sol, KoinkLauncher.sol, DiamondHandsVault.sol, KoinkTreasury.sol all needed)
- Chain decision: Solana recommended, not formally committed
- Security audit: Not arranged, estimated $5K–$25K
- LP capital: $0 committed
- Community: Zero members beyond Mev
- Koink.fun site: LIVE (landing page only, no token mechanics page, no deploy UI)
- OWS deploy wallet: NOT REGISTERED (Mev action)
- Gnosis Safe: NOT CREATED
- PiPi mascot integration: NOT DONE
- EasyA Kickstart listing: NOT DONE

**Next 3 concrete actions:**
1. **[OTTO] Write $KOIN smart contracts** — This is pure engineering work. Use the smart-contract-pipeline workflow. 4 contracts, Foundry, targeting Solana first (or Base if chain decision flips). Estimated 3–5 days of agent compute.
2. **[MEV] Decide chain: Solana-first or Base-first** — Tokenomics paper recommends Solana. Directive says "chain agnostic." Need a formal decision to unblock contract deployment.
3. **[MEV] Register OWS deploy wallet** — Single action, CRITICAL blocker for all on-chain deployment.

**Token launch readiness checklist:**

| # | Requirement | Status | Owner | Est. Effort |
|---|------------|--------|-------|-------------|
| 1 | Chain decision (Solana vs Base first) | ❌ PENDING | Mev | Decision |
| 2 | OWS deploy wallet registered | ❌ NOT DONE | Mev | 15 min |
| 3 | Smart contracts written (4 contracts) | ❌ NOT STARTED | Otto | 3–5 days |
| 4 | Contract test suite (>95% coverage) | ❌ NOT STARTED | Otto | 2–3 days |
| 5 | Devnet deployment + testing | ❌ NOT STARTED | Otto | 1–2 days |
| 6 | Security audit arranged | ❌ NOT STARTED | Mev ($5K–$25K) | 2–4 weeks |
| 7 | Gnosis Safe / multisig created | ❌ NOT STARTED | Otto | 1 hour |
| 8 | LP capital committed ($25K–$50K) | ❌ $0 COMMITTED | Mev | Financial decision |
| 9 | Tokenomics paper published | ❌ UNPUBLISHED | Otto | 1 hour |
| 10 | Koink.fun token mechanics page | ❌ NOT BUILT | Otto | 1 day |
| 11 | Community channels (Farcaster/Discord) | ❌ NOT CREATED | Mev+Otto | 1 day |
| 12 | $KOINK Standard published to GitHub | ❌ NOT DONE | Otto | 2 hours |
| 13 | EasyA Kickstart listing | ❌ NOT DONE | Otto | 1 hour |
| 14 | Farcaster Frame for allowlist | ❌ NOT BUILT | Otto | 1–2 days |
| 15 | PiPi mascot integration | ❌ NOT DONE | Otto | 1 day |
| 16 | Launch date announced | ❌ — | Mev | After items 1–10 |
| 17 | Mainnet deployment | ❌ — | Otto+Mev | After audit |
| 18 | First governance vote | ❌ — | Community | Day 30 post-launch |

**Critical path:** Items 1→2→3→4→5→6→17 (sequential). Items 9–15 can run in parallel.

---

### Path 4: VC / Investor Capital

| Attribute | Value |
|-----------|-------|
| **Target raise** | $250K–$750K SAFE |
| **Confidence score** | 2/10 — zero traction, zero conversations, zero warm intros |
| **Time to close** | 3–6 months minimum |
| **Dilution** | 10–15% (at $3M–$5M cap) |
| **Blockers** | Revenue ($0), community (none), product metrics (none), warm introductions (none) |

**Why this is Path 4 (last):** VCs invest in traction. MY3YE has zero traction metrics — no revenue, no users, no community, no deployed contracts. The documentation is impressive, but no VC writes a check on documentation. This path becomes viable only after Path 1 (revenue) and/or Path 2 (grants) produce tangible results.

**Current state:**
- Investor CRM: 10 targets identified, ALL at NOT_STARTED
- Pitch deck: WRITTEN (~/otto/projects/capital/investor_pitch_deck.md)
- Investor letter: WRITTEN (multiple variants)
- Outreach messaging: WRITTEN (X DM, LinkedIn sequences)
- Warm introductions: ZERO
- Revenue metrics to share: ZERO
- Product metrics to share: ZERO
- Public presence: Minimal (sites live, no social engagement, no thought leadership)

**Honest assessment:** Starting VC outreach now would waste credibility. VCs remember founders who come too early. It's better to approach with $5K MRR + one approved grant than with a pitch deck and no numbers.

**Exception — accelerators that accept pre-revenue:**
| Program | Status | Terms | Timeline |
|---------|--------|-------|----------|
| a16z CSX | NOT_STARTED | $500K SAFE, rolling | Apply anytime |
| Outlier Ventures Base Camp | NOT_STARTED | $150K SAFE + 6% equity | Apply anytime |
| Y Combinator S26 | NOT_STARTED | ~$500K, standard terms | **Deadline ~May 4** |

**Next 3 concrete actions:**
1. **[OTTO] Build Twitter/X thought leadership presence** — Execute the twitter-web3-inbound-strategy. 30 days of consistent posting builds the warm-intro pipeline that VC conversations require.
2. **[MEV] Evaluate YC S26 application** — Deadline ~May 4, 2026. YC accepts pre-revenue but requires a demo and clear market thesis. Decision needed: is this worth the founder time commitment?
3. **[DEFER] Begin VC outreach at $5K MRR or first grant approval** — Whichever comes first. Until then, VC outreach is premature.

**VC readiness gates:**
| Gate | Current | Target | Required For |
|------|---------|--------|-------------|
| Revenue | $0 | $5K+ MRR | All VC conversations |
| Users/clients | 0 | 5+ paying | Credibility signal |
| Community | 0 | 500+ | Token/ecosystem VCs |
| Grant approved | 0 | 1+ | Validation signal |
| Public repo | None | otto-ai on GitHub | Technical credibility |
| Social presence | Minimal | 1K+ followers | Warm intro pipeline |

---

## Ordered Execution Sequence

Based on speed-to-capital × confidence × effort required:

```
PRIORITY ORDER (what to do in what order):

1. UNBLOCK WEBASSIST REVENUE          [Mev — this week]
   ├── Supabase migration
   ├── Stripe webhook
   └── Gate: WebAssist can take payments

2. SUBMIT READY GRANT APPLICATIONS    [Mev — this week]
   ├── ENS grant (copy-paste ready)
   ├── Gitcoin GG25 registration (3 projects)
   └── Gate: Applications in pipeline

3. DRAFT REMAINING GRANT APPS         [Otto — Week 1-2]
   ├── Solana Foundation application
   ├── Deep Funding proposal
   ├── NEAR AI Agent Fund brief
   └── Gate: 5+ applications in pipeline

4. ACTIVATE WEBASSIST OUTREACH        [Otto+Mev — Week 2-4]
   ├── Deploy outreach sequence
   ├── First prospect contacts
   └── Gate: First paying client

5. BEGIN TOKEN IMPLEMENTATION         [Otto — Week 2-6]
   ├── Chain decision (Mev)
   ├── Smart contracts written
   ├── Publish tokenomics paper
   └── Gate: Contracts on devnet

6. BUILD PUBLIC PRESENCE              [Otto — Ongoing]
   ├── Twitter/X thought leadership
   ├── otto-ai GitHub repo
   ├── Community channels
   └── Gate: 500+ social followers

7. TOKEN LAUNCH                       [Otto+Mev — Month 3-4]
   ├── Security audit
   ├── LP capital committed
   ├── Mainnet deployment
   └── Gate: $KOIN live, community governance active

8. VC OUTREACH                        [Mev — Month 3-6]
   ├── Triggered by: $5K MRR OR first grant
   ├── Start with accelerators (a16z CSX, Outlier)
   ├── Progress to strategic VCs
   └── Gate: Term sheet
```

---

## Immediate Action Items — Otto (No Mev Required)

These are things Otto can execute autonomously right now:

| # | Action | Output | Est. Cost | Priority |
|---|--------|--------|----------|----------|
| 1 | Draft Solana Foundation grant application | Application doc ready for Mev submission | $1.50 | P1 |
| 2 | Draft Deep Funding (SingularityNET) proposal | Proposal doc for Otto AI OSS infra | $1.50 | P1 |
| 3 | Draft NEAR AI Agent Fund technical brief | Technical brief for Otto multi-agent | $1.00 | P2 |
| 4 | Publish tokenomics paper to koink.fun | Public page with $KOIN tokenomics | $1.00 | P2 |
| 5 | Publish $KOINK Standard to GitHub | Open-source spec repo | $0.50 | P2 |
| 6 | Ship otto-ai public GitHub repo | Curated Memory API SDK, 6 core routes | $2.00 | P2 |
| 7 | Draft Arbitrum Trailblazer application | Application for Otto on Arbitrum | $1.00 | P2 |
| 8 | Build WebAssist portfolio (3 demo sites) | Screenshot gallery for outreach | $1.50 | P2 |
| 9 | Draft Celo Prezenti proposal (Panik App) | Grant application for humanitarian tech | $1.00 | P3 |
| 10 | Draft Ethereum Foundation ESP application | Wishlist-aligned proposal for Otto AI | $1.50 | P3 |
| 11 | Create Polkadot forum introduction post | Forum.polkadot.network intro (prerequisite for W3F) | $0.50 | P3 |
| 12 | Prepare Product Hunt launch materials | PH listing draft, tagline, screenshots | $1.00 | P3 |
| 13 | Build token mechanics page for koink.fun | Interactive tokenomics page | $2.00 | P3 |
| 14 | Create EasyA Kickstart listing | Self-service listing for Koink | $0.50 | P3 |

**Total estimated cost: ~$16.50**
**If budget-constrained (top 5 only): ~$5.50**

---

## Immediate Action Items — Mev (Requires Mev)

Ordered by impact × effort. Each item includes estimated time.

| # | Action | Why It Matters | Time | Priority |
|---|--------|---------------|------|----------|
| 1 | **Complete Supabase migration for WebAssist** | Unblocks entire revenue path. Every day without this = $0 | 1–2 hours | 🔴 CRITICAL |
| 2 | **Set up Stripe webhook for WebAssist** | Payment processing. No Stripe = no revenue | 30 min | 🔴 CRITICAL |
| 3 | **Submit ENS grant application** | Copy-paste ready. Up to $50K USDC. 15 min effort | 15 min | 🔴 HIGH |
| 4 | **Register 3 Gitcoin GG25 project profiles** | builder.gitcoin.co — Otto AI, SOS Systems, ONEON. Free, 5 min each | 15 min | 🟡 HIGH |
| 5 | **Decide: Solana-first or Base-first for $KOIN** | Unblocks all smart contract work | Decision | 🟡 HIGH |
| 6 | **Register OWS deploy wallet** | Blocks all on-chain deployment (Koink, OPRLP, CET) | 15 min | 🟡 HIGH |
| 7 | **Evaluate YC S26 application** | Deadline ~May 4. $500K. Worth the founder time? | 1 hour review | 🟡 MEDIUM |
| 8 | **Submit Solana Foundation grant** (after Otto drafts) | $30K–$50K, rolling. Otto preps, Mev submits form | 30 min | 🟡 MEDIUM |
| 9 | **Authorize security audit budget** ($5K–$25K) | Required before $KOIN mainnet launch | Financial decision | 🟡 MEDIUM |
| 10 | **Commit LP capital** ($25K–$50K) | Required for $KOIN liquidity at launch | Financial decision | 🟡 MEDIUM |
| 11 | **Submit Deep Funding proposal** (after Otto drafts) | Up to $100K for Otto AI OSS | 30 min | 🟢 NORMAL |
| 12 | **Submit NEAR AI Fund application** (after Otto drafts) | $20K–$50K for Otto multi-agent | 30 min | 🟢 NORMAL |
| 13 | **Register Solana Tracker API key** | Unblocks paper trader → friends-and-family capital path | 5 min | 🟢 NORMAL |

**Mev time required for items 1–6: ~4 hours total**
**Items 1 and 2 alone unlock the entire revenue path.**

---

## Grant Application Tracker

### Status Dashboard

| Grant | Amount | Status | Application Ready? | Deadline | Est. Decision | Probability |
|-------|--------|--------|-------------------|----------|--------------|-------------|
| ENS Public Goods | $12K–$50K | ✅ DRAFTED | YES — copy-paste | Rolling | 4–8 weeks | 50% |
| Gitcoin GG25 | $5K–$50K | ❌ NOT REGISTERED | Profile creation only | Pre-May 2026 | May–June 2026 | 65% |
| Solana Foundation | $30K–$50K | ❌ NOT DRAFTED | Otto to draft | Rolling | 4–6 weeks | 45% |
| Deep Funding | up to $100K | ❌ NOT DRAFTED | Otto to draft | Rolling | 6–10 weeks | 40% |
| NEAR AI Fund | $20K–$50K | ❌ NOT DRAFTED | Otto to draft | Rolling | 4–8 weeks | 35% |
| Arbitrum Trailblazer | $5K–$10K | ❌ NOT DRAFTED | Otto to draft | Rolling | 2–4 weeks | 50% |
| ETH Foundation ESP | $25K–$75K | ❌ NOT DRAFTED | Needs public repo | Rolling | 8–12 weeks | 30% |
| Starknet Seed | $25K–$50K | ❌ NOT RESEARCHED | TBD | Rolling | 6–8 weeks | 25% |
| Celo Prezenti | $10K–$30K | ❌ NOT DRAFTED | Otto to draft | Rolling | 3–6 weeks | 30% |
| Optimism RPGF | $50K–$500K | ❌ NOT REGISTERED | Profile needed | Next retro round | Months | 20% |
| W3F / Polkadot | $10K–$30K | ❌ NOT STARTED | Forum post first | Rolling | 4–8 weeks | 25% |
| Fetch.ai Accelerator | $50K+ | ❌ NOT STARTED | Application needed | Rolling | 6–12 weeks | 20% |

### Expected Value Analysis

**Conservative (bottom-3 convert):** $30K–$70K
**Base case (3–4 of top 6 convert):** $60K–$150K
**Optimistic (5+ convert):** $150K–$350K

### Grant Submission Schedule

| Week | Action | Grant | Who |
|------|--------|-------|-----|
| Week 1 (Mar 31) | Submit ENS application | ENS Public Goods | Mev |
| Week 1 (Mar 31) | Register GG25 profiles | Gitcoin | Mev |
| Week 1–2 | Draft + submit Solana Foundation | Solana AI | Otto→Mev |
| Week 2 | Draft + submit Arbitrum Trailblazer | Arbitrum | Otto→Mev |
| Week 2–3 | Draft + submit Deep Funding | SingularityNET | Otto→Mev |
| Week 3 | Draft + submit NEAR AI Fund | NEAR | Otto→Mev |
| Week 3–4 | Draft + submit Celo Prezenti | Celo | Otto→Mev |
| Week 4 | Post on Polkadot forum | W3F prerequisite | Mev |
| Week 4–5 | Ship otto-ai repo, then ESP | ETH Foundation | Otto→Mev |
| Week 5–6 | Research + apply Starknet | Starknet | Otto→Mev |

**Target: 6+ applications submitted within 6 weeks.**

---

## Token Launch Readiness Checklist

### Phase Gate Model

```
PHASE A: Foundation (Week 1-2)
  □ Chain decision: Solana-first or Base-first          [Mev — DECISION]
  □ OWS deploy wallet registered                        [Mev — 15 min]
  □ Tokenomics paper published on koink.fun             [Otto — 1 hour]
  □ $KOINK Standard published to GitHub                 [Otto — 2 hours]
  □ Community channels created (Farcaster + Discord)    [Mev+Otto — 1 day]

PHASE B: Smart Contracts (Week 2-5)
  □ KoinkToken.sol written + tested                     [Otto — 2 days]
  □ KoinkLauncher.sol written + tested                  [Otto — 1 day]
  □ DiamondHandsVault.sol written + tested              [Otto — 1 day]
  □ KoinkTreasury.sol written + tested                  [Otto — 1 day]
  □ Full test suite >95% coverage                       [Otto — 2 days]
  □ Devnet deployment + integration testing             [Otto — 1 day]

PHASE C: Security + Community (Week 5-8)
  □ Audit firm selected (OtterSec for Solana, Trail of Bits for EVM)  [Mev — decision]
  □ Audit completed                                     [Auditor — 2-4 weeks]
  □ Gnosis Safe / multisig created (3-of-5)            [Otto — 1 hour]
  □ LP capital committed ($25K–$50K)                    [Mev — financial decision]
  □ Farcaster Frame allowlist built                     [Otto — 1 day]
  □ PiPi mascot integration on koink.fun               [Otto — 1 day]
  □ Token mechanics page live on koink.fun              [Otto — 1 day]
  □ EasyA Kickstart listing                             [Otto — 1 hour]

PHASE D: Launch (Week 8-12)
  □ Audit remediation (if needed)                       [Otto — 1-3 days]
  □ Launch date announced (7-day notice)                [Mev]
  □ Mainnet deployment                                  [Otto+Mev]
  □ LP seeded and locked                                [Mev]
  □ Token live on DEX                                   [Automatic]
  □ First governance vote (Day 30)                      [Community]

TOTAL TIMELINE: 8-12 weeks from Phase A start
TOTAL CAPITAL REQUIRED: $30K-$75K (LP + audit + gas)
```

### Token Launch Dependencies

```
Chain Decision ──► Contract Architecture
                       │
OWS Wallet ────────────┤
                       ▼
              Contract Development
                       │
                       ▼
                 Devnet Deploy
                       │
          ┌────────────┤
          ▼            ▼
    Security Audit   Community Build
          │            │
          ▼            ▼
    Audit Complete   500+ followers
          │            │
          └─────┬──────┘
                ▼
          LP Capital Committed
                │
                ▼
          Mainnet Launch
```

---

## 30 / 60 / 90 Day Milestones

### Day 30 — April 30, 2026: "First Blood"

**Capital target: $0–$5K revenue + 3–6 grant applications submitted**

| Milestone | Metric | Confidence |
|-----------|--------|------------|
| WebAssist taking payments | Stripe live | 70% (Mev-dependent) |
| First paying client | $499–$1,499/mo | 40% |
| ENS grant submitted | Application in review | 90% (if Mev submits this week) |
| 3+ grant applications in pipeline | Applications submitted | 75% |
| Gitcoin GG25 profiles registered | 3 project profiles | 90% |
| Tokenomics paper published | Public on koink.fun | 85% |
| Twitter/X presence started | 100+ followers | 60% |
| Smart contracts in progress | 2+ contracts written | 50% |

**Revenue at Day 30: $0–$1,500/mo (best case: 1 client)**
**Grants pipeline: $75K–$200K in submitted applications**
**Cash in hand: $0–$1,500**

### Day 60 — May 30, 2026: "Traction Signal"

**Capital target: $2K–$8K MRR + first grant decision**

| Milestone | Metric | Confidence |
|-----------|--------|------------|
| 2–5 paying WebAssist clients | $2K–$8K MRR | 35% |
| First grant approved | $10K–$50K | 40% |
| 6+ grant applications submitted | Pipeline coverage | 70% |
| $KOIN contracts on devnet | All 4 contracts deployed | 55% |
| Security audit in progress | Auditor engaged | 35% |
| otto-ai public repo shipped | GitHub live | 80% |
| Product Hunt launch | 500+ upvotes target | 30% |
| GG25 round active | Community donations flowing | 50% |
| Twitter/X presence | 500+ followers | 40% |

**Revenue at Day 60: $2K–$8K/mo (2–5 clients)**
**Grants: $10K–$50K approved, $100K+ in pipeline**
**Cash in hand: $10K–$60K cumulative (revenue + grant)**

### Day 90 — June 29, 2026: "Escape Velocity"

**Capital target: $5K–$15K MRR + $50K+ in grants + token launch imminent**

| Milestone | Metric | Confidence |
|-----------|--------|------------|
| $5K–$15K MRR from WebAssist | Sustainable revenue | 25% |
| $50K+ in approved grants | 2+ grants closed | 30% |
| $KOIN mainnet launch (or imminent) | Token live / audit complete | 25% |
| VC conversations started | 2–3 active conversations | 20% |
| Community | 1,000+ across channels | 20% |
| Product Hunt + content SEO | Inbound leads flowing | 30% |
| Total capital raised | $50K–$200K equivalent | 25% |

**Revenue at Day 90: $5K–$15K/mo**
**Grants: $50K–$150K approved/received**
**Token: Community treasury seeded**
**Cash in hand: $60K–$200K cumulative**

### Day 180 — September 27, 2026: "Phase 2 Gate"

**Target: Meet Phase 2 unlock conditions**

| Phase 2 Gate | Requirement | Realistic? |
|-------------|-------------|-----------|
| M1.1 — WebAssist $5K MRR | $5K+/mo recurring | Possible if started Month 1 |
| M1.2 — First grant approved | At least 1 of 12 | Likely |
| M1.3 — $KOIN mainnet | Token live | Possible if started Month 1 |
| M1.4 — OPRLP deployed | Governance on-chain | Otto can do alone |
| M1.5 — WebAssist $15K MRR | $15K+/mo | Ambitious |
| M1.6 — 200+ on-chain contributors | DPC scores | Requires community |

**Honest likelihood of meeting ALL 6 gates by Month 6: 15%**
**Likelihood of meeting 4 of 6 (enough to start Phase 2 conversations): 35%**

---

## Capital Flow Projection

```
Month 0 (April):     $0–$1.5K    ← WebAssist first client (if Stripe unblocked)
Month 1 (May):       $2K–$8K     ← 2–5 clients + Gitcoin GG25 start
Month 2 (June):      $15K–$60K   ← Grant #1 lands + 5–8 clients + GG25 matching
Month 3 (July):      $25K–$100K  ← Grant #2 + $KOIN launch + 8–12 clients
Month 4 (August):    $35K–$130K  ← Revenue compounding + grant pipeline
Month 5 (September): $50K–$180K  ← Phase 2 gate assessment
Month 6 (October):   $70K–$250K  ← Phase 2 fundraising begins (if gates met)
```

**Cumulative 6-month range:**
- **Floor (nothing works):** $0–$5K (only a couple clients, no grants)
- **Conservative:** $30K–$80K (3 clients + 1 grant)
- **Base case:** $80K–$200K (8 clients + 2 grants + token launch)
- **Optimistic:** $200K–$400K (15 clients + 3 grants + token + accelerator)

---

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Stripe/Supabase remains blocked >30 days | 30% | CRITICAL — blocks all revenue | Alternative: Paddle/Lemon Squeezy. Escalate to Mev weekly. |
| Zero grant approvals in 90 days | 25% | HIGH — no external validation | Shotgun approach: submit 6+ applications. Diversify across ecosystems. |
| $KOIN contracts fail audit | 15% | MEDIUM — delays launch 4–8 weeks | Use established patterns (OpenZeppelin). Budget for remediation. |
| No paying WebAssist clients in 60 days | 40% | HIGH — no revenue signal for VCs | Offer free builds to 3 high-visibility projects. Use as portfolio/case studies. |
| Mev bandwidth bottleneck | 50% | HIGH — Mev is single point for submissions | Otto pre-drafts everything. Mev effort = copy-paste + submit. Batch actions. |
| LP capital not available for token launch | 40% | MEDIUM — blocks launch or reduces credibility | Smaller initial LP ($10K). Community raise for LP via Gitcoin/community. |
| Market downturn reduces grant funding | 20% | MEDIUM — grant pools shrink | Diversify: Web3 + impact + AI grants (different funding sources). |
| VC market remains cold for pre-revenue | 60% | LOW (since VC is Path 4) | Focus on non-dilutive paths first. VC is gravy, not the meal. |

---

## What's Different From Previous Plans

This plan supersedes:
- `capital-strategy-2026-03-20.md` (v2.0) — same paths, but assumed faster execution
- `ottolabs-capital-sequencing-strategy-2026-03-28.md` — excellent Phase 1/2/3 framework, retained
- `funding_action_plan_2026_march.md` — ranked opportunities, incorporated above
- `investor-crm-live.md` — CRM status unchanged (all NOT_STARTED)

**Key differences:**
1. **Honest starting point** — Previous plans assumed Week 1 actions were imminent. This plan acknowledges 11+ days of zero execution on capital actions (the gap since the last plan was written).
2. **Lower confidence scores** — Previous plans scored VC at 30–40%. Adjusted to 10–20% given zero traction.
3. **Mev bottleneck explicit** — ~80% of immediate actions require Mev. This is the primary constraint, not strategy or preparation.
4. **Revenue before everything** — Previous plans treated all paths as equal. This plan is explicit: WebAssist revenue is the unlock for everything else.
5. **Token launch timeline realistic** — Previous plans suggested 60 days. Adjusted to 60–90 days given zero contracts exist and audit timeline.

---

## The One Thing That Matters Most

If you read nothing else in this document:

> **Stripe + Supabase unblock for WebAssist is the single highest-leverage action in the entire capital strategy.** It takes 2 hours. It unblocks the only path to revenue. Revenue unblocks grants (credibility), token (resources), and VC (traction). Until WebAssist can take payments, every other capital path is running on credibility borrowed from the future.

Mev: items 1 and 2 on the Mev action list. Everything else follows.

---

## Appendix A: Document Map

All capital-related documents in the system:

### Strategy (read first)
| Doc | Location | Purpose |
|-----|----------|---------|
| **This document** | ~/otto/docs/capital-raising-plan-2026-03-31.md | Master plan (source of truth) |
| Capital Strategy v2.0 | ~/otto/docs/capital-strategy-2026-03-20.md | Detailed 4-path playbook |
| Ottolabs Sequencing | ~/otto/docs/ottolabs-capital-sequencing-strategy-2026-03-28.md | Phase 1/2/3 framework |
| Funding Action Plan | ~/otto/projects/capital/funding_action_plan_2026_march.md | Ranked opportunity list |
| Alignment Review | ~/otto/docs/capital-strategy-alignment-review-2026-03-28.md | 5 issues to fix before external use |

### Grant Applications (ready or in-progress)
| Doc | Location | Status |
|-----|----------|--------|
| ENS Grant | ~/otto/projects/capital/ens_grant_application.md | ✅ READY — Mev submit |
| Gitcoin + Optimism | ~/otto/projects/capital/gitcoin_optimism_grants.md | Draft |
| W3F — ONEON | ~/otto/projects/capital/polkadot/w3f-oneon-grant.md | Draft |
| W3F — SOS Systems | ~/otto/projects/capital/polkadot/w3f-505-systems-grant.md | Draft |
| ONEON×ENS 1-pager | ~/otto/projects/capital/oneon_ens_1pager.md | Draft |
| Grant Landscape | ~/otto/projects/capital/grants_landscape_2026_march.md | Research (reference) |

### Token Launch
| Doc | Location | Status |
|-----|----------|--------|
| $KOIN Tokenomics | ~/otto/docs/koin-tokenomics-2026-03-20.md | ✅ Complete, unpublished |
| Koink Tokenomics | ~/otto/docs/koink-tokenomics-2026-03-20.md | ✅ Complete |
| Token Readiness Audit | ~/otto/docs/token-launch-readiness-audit-2026-03-25.md | ✅ Complete |
| Koink Readiness | ~/otto/docs/koink-readiness-report-2026-03-25.md | ✅ Complete |
| Koink Protocol Research | ~/otto/docs/koink-protocol-research-2026-03-23.md | Reference |

### Investor Materials
| Doc | Location | Status |
|-----|----------|--------|
| Pitch Deck | ~/otto/projects/capital/investor_pitch_deck.md | Draft |
| Investor Letter | ~/otto/docs/investor-letter.md | Draft |
| Investor Letter (HQ) | ~/otto/docs/investor-letter-highcalibre.md | Draft |
| Investor CRM | ~/otto/docs/investor-crm-live.md | Tracking (all NOT_STARTED) |
| Outreach Plan | ~/otto/docs/ottolabs-investor-outreach-plan-2026-03-28.md | Draft |
| Web3 Investor Personas | ~/otto/docs/web3-investor-persona-brief-2026-03-28.md | Reference |

### Outreach
| Doc | Location | Status |
|-----|----------|--------|
| Twitter Inbound Strategy | ~/otto/docs/twitter-web3-inbound-strategy-2026-03-27.md | Strategy |
| X DM Outreach | ~/otto/docs/x-dm-outreach-web3-investors-2026-03-28.md | Messaging |
| LinkedIn Outreach | ~/otto/docs/linkedin-investor-outreach-2026-03-28.md | Messaging |
| LinkedIn Private Funding | ~/otto/docs/linkedin-outreach-private-funding-2026-03-28.md | Messaging |
| WebAssist Prospects | ~/otto/projects/capital/webassist_leadgen/webassist_prospect_list.md | List |
| WebAssist Outreach Seq | ~/otto/projects/capital/webassist_leadgen/webassist_outreach_sequence.md | Sequence |
| WebAssist LinkedIn | ~/otto/projects/capital/webassist_leadgen/webassist_linkedin.md | Strategy |
| WebAssist Referral | ~/otto/projects/capital/webassist_leadgen/webassist_referral.md | Program design |

### Tusita / Sri Lanka
| Doc | Location | Status |
|-----|----------|--------|
| Tusita Capital Sequencing | ~/otto/docs/tusita-capital-sequencing-strategy-2026-03-28.md | Phase 1/2/3 |
| Tusita Pitch Narrative | ~/otto/docs/tusita-islands-capital-raise-strategy-pitch-narrative-2026-03-28.md | Narrative |
| Tusita Investor Outreach | ~/otto/docs/tusita-islands-investor-outreach-plan-2026-03-28.md | Plan |
| Sri Lanka Movement | ~/otto/docs/sri-lanka-movement-capital-model-2026-03-29.md | Model |
| Sri Lanka Outbound | ~/otto/docs/sri-lanka-outbound-strategy.md | Strategy |
| Sri Lanka Proposal | ~/otto/docs/sri-lanka-national-proposal-2026-03-29.md | Proposal |

---

## Appendix B: Key Alignment Issues to Fix

From the capital-strategy-alignment-review-2026-03-28.md, these 5 issues must be resolved before any document goes external:

1. **🔴 Remove YZI Labs (Binance Labs)** from investor targets — conflicts with sovereignty narrative
2. **🔴 Outlier 6% equity vs 5% governance cap** — structural contradiction, needs explicit economic/governance separation
3. **🔴 CET income path for physical workers** — soulbound tokens with no income mechanism = extraction pattern
4. **🟡 M1.1 Stripe dependency not flagged** — investor docs don't mention this risk
5. **🟡 Ottolabs as Tusita's first hardware customer** — missed synergy story

**These must be fixed before any pitch deck or investor letter is sent externally.**

---

## Appendix C: Weekly Cadence

Starting Week 1 (March 31):

| Day | Otto Actions | Mev Actions |
|-----|-------------|-------------|
| Monday | Draft Solana Foundation app | Supabase migration |
| Tuesday | Draft Deep Funding proposal | Stripe webhook setup |
| Wednesday | Draft NEAR AI brief | Submit ENS grant (15 min) |
| Thursday | Draft Arbitrum Trailblazer app | Register GG25 profiles (15 min) |
| Friday | Publish tokenomics to koink.fun | Review drafts, submit 1–2 apps |
| Weekend | Ship otto-ai GitHub repo | Chain decision for $KOIN |

**Week 2:** Submit remaining grant applications, begin WebAssist outreach, start smart contract development.
**Week 3:** Continue outreach, contracts on devnet, community building begins.
**Week 4:** Product Hunt prep, audit firm selection, social presence acceleration.

---

*This document is the source of truth for MY3YE capital-raising activity as of 2026-03-31. It will be reviewed and updated by the heartbeat cycle weekly. Previous versions are retained for reference but this plan supersedes all prior capital strategy documents.*

*Generated by Otto (Architect Agent) — synthesized from 68 existing documents across ~/otto/docs/ and ~/otto/projects/capital/.*

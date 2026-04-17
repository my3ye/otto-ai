# Capital Raise Release Plan — MY3YE / Ottolabs
*Version 1.0 — Created 2026-03-17 | Self-evolving: update after each milestone*

---

## Mission Context

We are raising capital to fund development of the MY3YE ecosystem — a sovereign civilization stack starting with WebAssist (revenue wedge) and Koink.fun ($KOIN token). Capital unlocks: infrastructure, team, and accelerated build velocity.

**Revenue target (6 months):** $50K+ ARR from WebAssist + grant funding
**Token event target:** $KOIN fair launch within 60 days of tokenomics paper finalization
**Investor target:** 1-2 strategic seed investors or grants at $100K–$500K

---

## Four Parallel Paths

| Path | Vehicle | Speed | Credibility Req | Mev Effort |
|------|---------|-------|-----------------|------------|
| A | WebAssist Revenue | Weeks | Low — just close | High (sales) |
| B | $KOIN Token Launch | 30–60 days | Tokenomics paper + audit | High (approve) |
| C | Web3/Impact Grants | 30–90 days | Technical docs + proposal | Medium |
| D | VC/Strategic Investors | 60–120 days | Traction + deck | High (outreach) |

---

## PATH A — WebAssist Revenue
**Goal:** First $5K MRR by end of Month 1. Fastest real-money signal.

### Status
- ✅ LIVE at webassist.ink
- ❌ BLOCKED: Bank/Wise payment processing (Mev must action)
- ❌ BLOCKED: Stripe webhook not configured

### Ordered Tasks

| # | Task | Owner | Priority | Est. Time |
|---|------|-------|----------|-----------|
| A1 | **[MEV ACTION]** Set up Wise or Stripe account, provide Otto with webhook key | Mev | P0 | 1 day |
| A2 | Configure Stripe webhook + live keys in WebAssist Supabase env | Otto | P0 | 2 hours |
| A3 | Build WebAssist lead gen: landing page CTA + email capture → Supabase | Otto | P1 | 1 day |
| A4 | Create WebAssist outbound list: 50 target startups/SMBs | Otto | P1 | 2 hours |
| A5 | Draft 3-email cold outreach sequence (founders of early-stage startups) | Otto | P1 | 1 hour |
| A6 | **[MEV ACTION]** Send outreach to first 20 prospects | Mev | P1 | ongoing |
| A7 | Set up WebAssist referral system — 20% first-month credit for referrals | Otto | P2 | 2 hours |
| A8 | Monthly metrics dashboard: MRR, clients, churn → OMS | Otto | P2 | 3 hours |

### Milestones
- **Week 1:** Payment unblocked, first client onboarded
- **Week 2:** 3+ clients, $3K+ contracted
- **Month 1:** $5K MRR, outreach at 50 contacts

---

## PATH B — $KOIN Token Launch (Koink.fun)
**Goal:** Fair launch of $KOIN on Solana/Base within 60 days. Web3-native capital inflow + community.

### Status
- Status: concept — inception article published
- Chain decision: **UNDECIDED** (Solana vs Base vs Polkadot)
- Smart contract: not started
- Tokenomics paper: not written

### Chain Decision Framework

| Chain | Pros | Cons |
|-------|------|------|
| **Solana** | Meme culture native, low fees, fast | Network congestion risk, less DeFi composability |
| **Base** | L2 ETH, Coinbase audience, growing meme scene | Less meme-native than Solana |
| **Polkadot** | Grant opportunities, 505 Systems alignment | Smaller retail audience, complex |

**Recommendation:** Launch on Solana first (fastest, meme-native). Then Koink.fun deploys $KOINK Standard to Base and Polkadot via cross-chain expansion.

### Ordered Tasks

| # | Task | Owner | Priority | Est. Time |
|---|------|-------|----------|-----------|
| B1 | Write $KOIN tokenomics paper (supply, distribution, vesting, Quantum Koinkulator spec) | Otto | P0 | 1 day |
| B2 | **[MEV DECISION]** Approve chain selection (Solana recommended) | Mev | P0 | — |
| B3 | Draft $KOINK Standard whitepaper (fork-ready tokenomics template) | Otto | P1 | 1 day |
| B4 | Build $KOINK Solana smart contract (Anchor framework, testnet) | Otto | P1 | 2-3 days |
| B5 | Create Koink.fun landing page with countdown + mailing list | Otto | P1 | 1 day |
| B6 | Set up @KoinkFun Twitter/X persona and post thread announcing $KOIN Standard | Otto | P1 | 2 hours |
| B7 | **[MEV ACTION]** Engage 3 Solana/meme influencer communities for awareness | Mev | P1 | 1 week |
| B8 | Smart contract audit (Ottersec or equivalent — budget $5-15K) | Otto sources, Mev approves | P1 | 2 weeks |
| B9 | Create fair launch liquidity provision strategy (initial LP, Raydium/Orca) | Otto | P2 | 1 day |
| B10 | **[MEV ACTION]** Approve and trigger $KOIN mainnet fair launch | Mev | P0 | — |
| B11 | Post-launch: Quantum Koinkulator live dashboard on koink.fun | Otto | P2 | 2 days |

### Milestones
- **Week 1:** Tokenomics paper published, chain confirmed
- **Week 2:** Smart contract testnet deployed + landing page live
- **Week 3-4:** Audit initiated, community building begins
- **Day 60:** Mainnet launch

---

## PATH C — Web3 / Impact Grants
**Goal:** $50K–$200K in non-dilutive funding from grants within 60-90 days.

### Best-Fit Grants

| Grant | Project | Ask | Fit | Deadline |
|-------|---------|-----|-----|----------|
| **Web3 Foundation** | 505 Systems + Panik App | $50K–100K | High (Polkadot OpenGov alignment) | Rolling |
| **Gitcoin Grants** | Otto AI + WebAssist | Community round | High (public goods) | Quarterly |
| **Optimism RPGF** | WebAssist + 505 Systems | $10K–100K | Medium (retroactive public goods) | 2-3x/year |
| **Solana Foundation** | Koink.fun | $10K–50K | High if chain = Solana | Rolling |
| **Ethereum Foundation ESP** | Otto Memory / ONEON | $25K–100K | Medium (infra/research) | Rolling |
| **Celo Foundation** | Panik App | $10K–50K | High (humanitarian/mobile-first) | Rolling |
| **NEAR Foundation** | 505 Systems DAO | $20K–75K | Medium | Rolling |

### Ordered Tasks

| # | Task | Owner | Priority | Est. Time |
|---|------|-------|----------|-----------|
| C1 | Write Web3 Foundation grant proposal: 505 Systems + Panik App bundle | Otto | P0 | 2 days |
| C2 | Register on Gitcoin and set up project profiles (Otto AI, WebAssist) | Otto | P0 | 2 hours |
| C3 | Write Solana Foundation grant proposal (pending chain decision B2) | Otto | P1 | 1 day |
| C4 | Write Optimism RPGF project brief (WebAssist as public goods infra) | Otto | P1 | 1 day |
| C5 | Write Ethereum Foundation ESP application (Otto Memory / cognitive infra) | Otto | P1 | 1 day |
| C6 | Write Celo Foundation application (Panik App humanitarian use case) | Otto | P2 | 1 day |
| C7 | **[MEV ACTION]** Review, approve, and submit grant applications (1 per week) | Mev | P1 | ongoing |
| C8 | Set up grant tracking dashboard in OMS (status, deadlines, amounts) | Otto | P2 | 2 hours |
| C9 | Write MY3YE ecosystem public goods narrative (used across all applications) | Otto | P0 | 3 hours |

### Strategy Notes
- Lead with **Panik App + 505 Systems** for Web3 Foundation — strongest alignment with Polkadot OpenGov
- **Gitcoin** is community-driven; need community engagement BEFORE applying for matching
- **Retroactive** grants (Optimism) need deployment evidence — ship more, document impact
- Lead grants should total $150K+ by Month 3 if 2-3 applications are approved

### Milestones
- **Week 1:** Public goods narrative written, Gitcoin profile live, WF3 proposal drafted
- **Week 2:** First application submitted (Web3 Foundation)
- **Month 1:** 3+ applications submitted
- **Month 3:** First grant result (approve or deny + lessons)

---

## PATH D — VC / Strategic Investors
**Goal:** 1-2 strategic investors at $250K–$500K seed within 90-120 days.

### Target Investor Profiles

| Type | Who | What They Want | Fit |
|------|-----|----------------|-----|
| Web3 seed | Multicoin, a16z crypto, Pantera | Token upside + ecosystem thesis | High |
| Impact seed | Village Capital, Capria | Social impact + revenue | Medium |
| Strategic | Coinbase Ventures, Solana Foundation, Polkadot Ventures | Ecosystem expansion | High |
| Angels | Crypto-native builders with exits | Mission alignment + early | High |

### Ordered Tasks

| # | Task | Owner | Priority | Est. Time |
|---|------|-------|----------|-----------|
| D1 | Create investor pitch deck: 10-slide MVP (problem, solution, traction, team, ask) | Otto | P0 | 1 day |
| D2 | Write MY3YE one-pager / executive summary (2-page PDF) | Otto | P0 | 3 hours |
| D3 | Build investor landing page at mev.otto.lk/investors (password-protected) | Otto | P1 | 3 hours |
| D4 | Build 30-name target investor list with warm paths identified | Otto | P1 | 2 hours |
| D5 | Write 3 investor outreach email templates (cold, intro via mutual, follow-up) | Otto | P1 | 2 hours |
| D6 | Create traction slide content: WebAssist revenue, grant pipeline, token metrics | Otto | P2 | 1 hour |
| D7 | **[MEV ACTION]** Post MY3YE thread on X — narrative + product traction (visibility) | Mev | P1 | — |
| D8 | **[MEV ACTION]** Review pitch deck and provide feedback/approve | Mev | P0 | — |
| D9 | **[MEV ACTION]** Begin warm outreach to 5 target investors/angels | Mev | P1 | ongoing |
| D10 | Set up CRM tracking in OMS: investor name, stage, last contact, notes | Otto | P2 | 2 hours |

### Milestones
- **Week 1:** Pitch deck MVP done, one-pager done
- **Week 2:** Investor page live, outreach list finalized
- **Week 3:** Mev begins outreach
- **Month 2:** 10+ conversations initiated
- **Month 3:** Term sheet from 1 investor

---

## Cross-Path Dependencies

```
WebAssist MRR (A)  ──────────────────────────────→  Investor Traction Slide (D6)

Tokenomics Paper (B1) ──→ Chain Decision (B2) ──→  Solana Grant (C3)

Public Goods Narrative (C9) ───→  WF3 Proposal (C1)
                                  Gitcoin Profile (C2)
                                  Optimism Brief (C4)

Pitch Deck (D1) ──→  Investor Page (D3) ──→  Outreach (D9)

Grant Wins (C) ──────────────────────────────────→  Investor Credibility (D)
```

---

## Priority Sequence (What Otto Does First)

1. **Day 1-2:** Write tokenomics paper (B1) + public goods narrative (C9) + pitch deck (D1)
2. **Day 2-3:** Draft WF3 grant proposal (C1) + investor one-pager (D2)
3. **Day 3-4:** Build koink.fun landing page (B5) + Gitcoin profile (C2)
4. **Day 4-5:** $KOINK Solana smart contract testnet (B4)
5. **Day 5-7:** WebAssist lead gen system (A3-A5) + investor page (D3)
6. **Week 2:** Submit first grant application; Mev outreach begins

---

## Capital Table (What We're Raising)

| Source | Vehicle | Target | Timeline |
|--------|---------|--------|----------|
| WebAssist | Revenue | $5K MRR | Month 1 |
| Grants | Non-dilutive | $150K | Month 3 |
| $KOIN launch | Token treasury | TBD | Month 2 |
| Seed round | Equity/SAFE | $250K–500K | Month 4 |

---

## Self-Evolution Notes
- Update this plan every 2 weeks with actual results vs milestones
- Add "lessons learned" section after each grant application submitted
- Track grant pipeline in OMS (C8) with real-time status
- Token metrics tracked in Koink.fun dashboard (B11)

*Last updated: 2026-03-17*

# MY3YE Partner & Collaborator Outreach Plan
## Pre-Requisites, Angles, and Sequenced Tasks

**Version:** 1.0
**Created:** 2026-03-17
**Author:** Otto (MY3YE)
**Purpose:** Structured outreach across all partner categories — never reach out before the prerequisites are met. Sequence matters.

---

## Universal Pre-Requisites (Gate Before ANY Outreach)

These must be true before approaching anyone. Check these first.

| # | Pre-Requisite | Status | Notes |
|---|---------------|--------|-------|
| U1 | MY3YE landing page live (otto.lk) | ✅ LIVE | Panik aesthetic, Next.js, multiple projects |
| U2 | WebAssist live (webassist.ink) | ✅ LIVE | AI website product |
| U3 | Inception articles published | ✅ DONE | Open Copyright, projects across many verticals |
| U4 | Public goods narrative written | ✅ DONE | `capital/public_goods_narrative.md` |
| U5 | GitHub org public (my3ye) | ✅ DONE | otto-core open-sourced |
| U6 | Email identity set up | ✅ DONE | my3ye.otto@gmail.com |
| U7 | Twitter/X presence (@MY3YE or @OttoAgent) | ❌ NOT SET UP | Need handle + bio + pinned post |
| U8 | Farcaster profile active | ❌ NOT SET UP | Needed for Web3 native communities |
| U9 | Koink.fun landing page with mailing list | ❌ NOT BUILT | Required before any meme community outreach |
| U10 | $KOIN tokenomics paper published | ✅ DONE | `capital/koin_tokenomics_paper.md` |
| U11 | Investor pitch deck ready | ✅ DONE | `capital/investor_pitch_deck.md` |

**Rule:** If U7 + U8 are not done, only do email-based outreach to grants programs. Community outreach requires social presence.

---

## Category 1: Grant Programs
### Priority: HIGHEST — Non-dilutive, no social prereqs, materials ready now

---

### 1A. Gitcoin Grants (Otto AI + WebAssist)

**What Gitcoin Is:** Quarterly public goods funding rounds, community-voted. $50M+ distributed. Projects get listed and the community donates — Gitcoin Grants matching amplifies small donations.

**Pre-Requisites:**
- [x] Otto AI Gitcoin profile written (`capital/gitcoin_optimism_grants.md` Section 1)
- [x] WebAssist Gitcoin profile written (same doc, Section 2)
- [x] GitHub repos public and active
- [ ] Mev must create Gitcoin account at gitcoin.co/grants (requires wallet)
- [ ] Submit project applications for both Otto AI and WebAssist
- [ ] Prepare project cover images (1500x500px recommended)
- [ ] Set up wallet address to receive funding (ETH mainnet or Optimism)

**Outreach Angle:**
> "Otto is open-source persistent AI infrastructure — built for communities, not corporations. Any developer can deploy their own Otto on a $20/mo VM. The memory layer, reasoning kernel, and task execution system are all public domain. We're applying to Gitcoin to fund the documentation and community onboarding that turns internal architecture into a deployable public good."

**No cold outreach needed for Gitcoin** — it's a platform submission. Quality of profile determines funding.

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| G1 | [MEV] Create Gitcoin account + connect wallet | Mev | U6 | Day 1 |
| G2 | Submit Otto AI profile to active Gitcoin round | Mev | G1 | Day 2 |
| G3 | Submit WebAssist profile to Gitcoin | Mev | G1 | Day 2 |
| G4 | Share Gitcoin projects on Twitter/X and Farcaster | Mev/Otto | U7, U8 | Day 3 |
| G5 | Post in Web3 community chats about Gitcoin projects | Otto drafts, Mev sends | G4 | Day 4 |

---

### 1B. Optimism RPGF (WebAssist + 505 Systems)

**What RPGF Is:** Retroactive Public Goods Funding — Optimism Foundation distributes OP tokens to projects that have already delivered value. Rounds happen 2-3x/year. Apply to each round.

**Pre-Requisites:**
- [x] Public goods narrative ready
- [x] WebAssist live with users
- [ ] WebAssist usage metrics documented (clients, pages deployed, SMBs served)
- [ ] Submit to Optimism Agora (agora.optimism.io) badgeholder nomination list
- [ ] Write RPGF-specific brief (retroactive framing: what value have we already delivered?)
- [ ] OP wallet for receiving funds

**Outreach Angle:**
> "WebAssist has already delivered AI-grade websites to small businesses who couldn't afford it. Every site we build is a business that can now compete with enterprises. That's demonstrable, retroactive public value. We're not asking for funding to build — we're applying for RPGF for what we've already shipped."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| R1 | Document WebAssist real-world impact metrics (clients, businesses served) | Otto | WebAssist clients | Day 1 |
| R2 | Write RPGF application brief (retroactive framing, impact metrics) | Otto | R1 | Day 2 |
| R3 | [MEV] Register on Agora and submit project when round opens | Mev | R2 | Next round |
| R4 | Engage Optimism Collective community on Farcaster (not asking, just contributing) | Mev/Otto | U8 | Ongoing |

---

### 1C. Web3 Foundation (505 Systems + Panik App)
**Grant program URL:** grants.web3.foundation | Open Grants Program, rolling applications

**What W3F Is:** Polkadot Foundation grant arm. $10K–$100K for technical projects building on or complementing the Polkadot/Kusama ecosystem. Reviewed by W3F team, milestone-based payouts.

**Pre-Requisites:**
- [x] W3F grant proposal written (`capital/w3f_grant_proposal.md`)
- [x] 505 Systems architecture documented
- [x] Panik App concept documented
- [ ] GitHub repo for `pallet-dpc` (Substrate pallet) — at minimum a spec doc
- [ ] Mev review and approve grant proposal before submission
- [ ] Set up DOT wallet for receiving grant
- [ ] Answer W3F application questions on their GitHub (grant applications are public PRs)

**Outreach Angle:**
> "Polkadot's OpenGov is the most advanced multi-chain governance system in Web3 — but it's fundamentally token-weighted. 505 Systems adds Democratic Power Contribution (DPC) as a Substrate pallet: governance weight earned through verified contribution, not token accumulation. Panik App pairs with ONEON identity to create humanitarian infrastructure on Polkadot. Both are Apache 2.0, designed for any parachain to adopt."

**Cold Outreach Contact:**
- grants@web3.foundation (formal)
- W3F team on Element (matrix.to/#/#w3f:matrix.org)
- @substrate_io on Twitter

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| W1 | Create `pallet-dpc` spec doc in GitHub (tech implementation stub) | Otto | GitHub org | Day 2 |
| W2 | [MEV] Review and approve W3F grant proposal | Mev | W3F doc | Day 1 |
| W3 | Submit W3F grant proposal as GitHub PR to w3f/grants-program | Otto/Mev | W2 | Day 3 |
| W4 | Post in W3F Element channel introducing the application | Mev | W3 | Day 4 |
| W5 | Follow up with W3F grants team if no response in 14 days | Mev | W3 | Day 17 |

---

### 1D. Solana Foundation (Koink.fun / $KOIN)

**What SF Is:** Rolling grants program for projects building on Solana. Prioritizes ecosystem growth, developer tools, consumer apps, DeFi. Grant range: $10K–$50K.

**Pre-Requisites:**
- [x] $KOIN tokenomics paper written
- [ ] Chain decision confirmed: Solana (awaiting Mev approval)
- [ ] Koink.fun landing page live (not started)
- [ ] Smart contract on Solana testnet (Anchor framework)
- [ ] Solana wallet set up
- [ ] Write Solana Foundation grant application (community + ecosystem angle)
- [ ] Active Solana community presence (Discord: discord.gg/solana, X)

**Outreach Angle:**
> "The $KOINK Standard is open-source tokenomics infrastructure for the Solana meme ecosystem. Any project launching a token can fork the Quantum Koinkulator and Diamond Hands Multiplier — getting VRF-based fair distribution and anti-whale mechanics without reinventing the wheel. We're building the tokenomics layer that raises the floor for every Solana token launch."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| S1 | [MEV] Confirm Solana as $KOIN launch chain | Mev | — | ASAP |
| S2 | Build Koink.fun landing page with mailing list | Otto | S1 | Day 3 |
| S3 | Deploy $KOINK Standard to Solana devnet (Anchor) | Otto | S1 | Week 2 |
| S4 | Write Solana Foundation grant application | Otto | S2, S3 | Week 2 |
| S5 | Join Solana Foundation Grizzlython / hackathon if timing aligns | Otto/Mev | S2 | Check dates |
| S6 | [MEV] Submit Solana Foundation grant application | Mev | S4 | Week 2 |
| S7 | Post in Solana Discord #grants channel after submission | Mev | S6 | Week 2 |

---

### 1E. Ethereum Foundation ESP (Otto Memory / ONEON)

**What ESP Is:** Ethereum Foundation's Ecosystem Support Program. $25K–$100K for research, tooling, and infrastructure that benefits Ethereum. Focused on fundamental public goods.

**Pre-Requisites:**
- [ ] Otto Memory API packaged as public-deployable project (Docker + docs)
- [ ] ONEON identity protocol spec document (W3C DID compatible)
- [ ] Evidence of public good value (GitHub stars, deployments, academic references)
- [ ] Write ESP application (forms.ethereum.org/ecosystem-support-program)
- [ ] Ethereum wallet for receiving ETH grant
- [ ] Reference: at minimum 2 external developers who have used/reviewed the Memory API

**Outreach Angle:**
> "Otto Memory is persistent cognitive infrastructure for AI agents — not a wrapper, not a RAG layer. It's a full memory stack (episodic, semantic, procedural, knowledge graph) that gives AI genuine continuity. Every architecture decision is documented and published. Any Ethereum builder can deploy this for their own AI agent without reinventing the memory layer. We're applying for ESP to fund the public documentation and packaging that makes this genuinely usable by the wider community."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| E1 | Package Otto Memory API for public deployment (Docker quickstart, README) | Otto | otto-core open source | Week 1 |
| E2 | Publish ONEON identity spec document (DID-compatible) | Otto | — | Week 2 |
| E3 | Write ESP application covering Otto Memory + ONEON | Otto | E1, E2 | Week 2 |
| E4 | [MEV] Submit ESP application | Mev | E3 | Week 2 |
| E5 | Post otto-core on HackerNews/ETH Research forum for visibility | Otto/Mev | E1 | Week 2 |

---

### 1F. Celo Foundation (Panik App)

**What Celo Is:** Mobile-first blockchain, deeply focused on financial inclusion and humanitarian impact. Grants range $10K–$50K, prioritize real-world impact in developing regions.

**Pre-Requisites:**
- [ ] Panik App MVP prototype or demo (even a Figma walkthrough)
- [ ] SOS Systems architecture brief (with Panik App included)
- [ ] Impact narrative focused on Global South / emergency scenarios
- [ ] Write Celo Foundation grant application
- [ ] Celo wallet for receiving CELO/cUSD
- [ ] Community presence on Celo Discord

**Outreach Angle:**
> "Panik App works without cell towers. When disaster strikes in regions with weak infrastructure — the exact communities Celo is built for — existing emergency systems fail. Panik App uses Bluetooth mesh, local WiFi, and satellite fallback to route distress signals through a guardian network. ONEON provides tamper-proof identity so aid can reach the right people. This is emergency infrastructure designed for exactly the communities Celo serves."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| C1 | Create Panik App Figma prototype / demo walkthrough | Otto (spec) | — | Week 1 |
| C2 | Write SOS Systems + Panik App architecture brief | Otto | — | Week 1 |
| C3 | Write Celo Foundation grant application | Otto | C1, C2 | Week 2 |
| C4 | [MEV] Submit Celo grant via celo.org/grants | Mev | C3 | Week 2 |
| C5 | Join Celo Discord, introduce project in #grants channel | Mev | C4 | Week 2 |

---

## Category 2: Web3 Ecosystem Partnerships
### Priority: HIGH — Community, distribution, co-marketing

---

### 2A. BONK DAO / Solana Meme Ecosystem

**What BONK Is:** Largest Solana meme community (~500K holders, 350+ integrations). BONK DAO has grants. Koink.fun is a natural cultural fit — meme tokenomics standard, playful brand.

**Pre-Requisites:**
- [ ] Koink.fun landing page live (minimum viable)
- [ ] $KOIN on Solana testnet or clear public roadmap
- [ ] Koink.fun Twitter presence active with posts
- [ ] Draft BONK DAO grant proposal (Koink Standard as Solana meme infra)
- [ ] Join BONK DAO Discord as active community member (BEFORE asking for anything)

**Outreach Angle:**
> "Koink.fun is building the $KOINK Standard — open-source fair tokenomics for the entire Solana meme ecosystem. Every future meme coin can fork our anti-whale, fair-distribution mechanics. BONK is the king of Solana memes. We want to build INSIDE that ecosystem, contributing infrastructure that makes every BONK-adjacent token launch fairer and more fun."

**Outreach Channel:** BONK DAO Discord → #grants channel, then DM BONK DAO multisig holders

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| B1 | [MEV] Join BONK DAO Discord, participate for 1 week before any ask | Mev | — | Week 1 |
| B2 | Create @KoinkFun Twitter account and post $KOINK Standard thread | Otto/Mev | Koink.fun page | Week 1 |
| B3 | Write BONK DAO grant proposal (Koink as Solana meme infra) | Otto | B2 | Week 2 |
| B4 | [MEV] Post proposal in BONK DAO #grants after 1 week community participation | Mev | B1, B3 | Week 2 |
| B5 | Explore BONK integration in Koink.fun (BONK as accepted meme currency) | Otto | chain confirmed | Week 3 |

---

### 2B. Farcaster / DEGEN Community

**What Farcaster Is:** Decentralized social protocol, ~300K users, builder-heavy. DEGEN (L3 chain) has tipping culture. Farcaster Frames allow mini-apps in feed. Very high-signal Web3 community.

**Pre-Requisites:**
- [ ] Mev creates Farcaster account (warpcast.com)
- [ ] Post 5+ quality casts before promoting anything (establish presence)
- [ ] Create /my3ye or /koink Farcaster channel
- [ ] Build a simple Koink.fun Farcaster Frame (interactive mini-app)
- [ ] Otto.lk and koink.fun must work well on mobile

**Outreach Angle:**
> "Built a decentralized AI that never forgets — now building the open tokenomics layer for meme culture. Multiple projects across many verticals, all open source, all for the community. If you're building on Farcaster, I'm building the infrastructure layer underneath. Let's talk."

**No cold DMs needed** — presence + quality posts attracts inbound on Farcaster.

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| F1 | [MEV] Create Farcaster account, connect wallet | Mev | ETH wallet | Day 1 |
| F2 | Post MY3YE ecosystem introduction thread on Farcaster (5-cast thread) | Mev | F1 | Day 2 |
| F3 | Create /koink channel on Farcaster | Mev | F1 | Day 2 |
| F4 | Build simple Koink.fun Farcaster Frame (PiPi mascot interaction) | Otto | Koink page | Week 2 |
| F5 | Post Koink Frame on Farcaster, engage with builders who interact | Mev | F4 | Week 2 |
| F6 | Explore DEGEN tipping integration for Koink community rewards | Otto | — | Week 3 |

---

### 2C. Polkadot / Kusama Community

**What Polkadot Is:** Multi-chain architecture, strong governance culture, OpenGov is sophisticated. 505 Systems and Panik App have direct alignment. W3F grant is already in pipeline.

**Pre-Requisites:**
- [x] W3F grant proposal written
- [x] BD pitch strategy prepared (PiPi as cultural mascot angle)
- [ ] `pallet-dpc` spec doc on GitHub
- [ ] Polkadot.js wallet set up
- [ ] Join Polkadot Discord + Element matrix channels

**Outreach Angle:**
> "OpenGov is the most sophisticated multi-chain governance system built — but governance weight still tracks token balance. 505 Systems adds the missing layer: contribution-weighted power that earns standing through impact, not accumulation. We want to build pallet-dpc inside the Polkadot ecosystem, not alongside it."

**Key Contacts:**
- Web3 Foundation Grants Team: grants@web3.foundation
- Parity Technologies Discord: #substrate-dev
- Polkadot OpenGov forum: polkadot.polkassembly.io

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| P1 | [MEV] Join Polkadot Discord and Element (w3f:matrix.org) | Mev | — | Week 1 |
| P2 | Post `pallet-dpc` concept in Polkadot OpenGov forum | Otto/Mev | W1 (spec doc) | Week 1 |
| P3 | Engage Substrate developers in technical discussion (not promoting) | Mev | P1 | Ongoing |
| P4 | Submit W3F grant proposal as GitHub PR | Otto/Mev | W3F grant doc | Week 1 |
| P5 | Introduce PiPi as Polkadot cultural mascot concept in community chat | Mev | P3 (after trust built) | Week 3 |

---

### 2D. Optimism Collective

**What Optimism Is:** L2 blockchain with strong public goods culture. Retroactive grants (RPGF), active governance community. WebAssist and 505 Systems fit naturally.

**Pre-Requisites:**
- [ ] Submit RPGF brief (R2 from grants section)
- [ ] Optimism wallet + OP identity
- [ ] Engage in governance discussion on Agora before asking for anything
- [ ] Build something small on Optimism (even deploying a contract) to be a participant

**Outreach Angle:**
> "WebAssist has already deployed AI-grade websites for small businesses who couldn't afford enterprise solutions. That's retroactive public value — we're asking RPGF to recognize impact that already happened. Separately, 505 Systems DPC is governance infrastructure that Optimism Collective can adopt to recognize builders, not just token holders."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| O1 | [MEV] Create Optimism Agora profile, connect wallet | Mev | OP wallet | Week 1 |
| O2 | Participate in 2 Optimism governance discussions before asking anything | Mev | O1 | Week 1-2 |
| O3 | Submit WebAssist + 505 Systems RPGF brief when next round opens | Mev | O2, R2 | Next round |
| O4 | Post about 505 Systems DPC in Optimism governance forum | Mev | O2 | Week 3 |

---

### 2E. NEAR Protocol / Proximity Labs

**What NEAR Is:** Developer-friendly L1 with strong DAO tooling and governance experiments. Proximity Labs funds ecosystem projects. 505 Systems DAO governance is relevant.

**Pre-Requisites:**
- [ ] 505 Systems technical specification document
- [ ] NEAR wallet set up
- [ ] NEAR developer community presence
- [ ] Write NEAR-specific grant application (governance + DAO focus)

**Outreach Angle:**
> "505 Systems is building Democratic Power Contribution — governance weight that tracks contribution, not token accumulation. NEAR has one of the most sophisticated developer communities in Web3 and a culture that values governance experiments. We want to build a NEAR-native implementation alongside the Substrate pallet."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| N1 | Write 505 Systems technical specification document | Otto | — | Week 2 |
| N2 | Write NEAR Foundation grant application | Otto | N1 | Week 3 |
| N3 | [MEV] Join NEAR Discord, introduce project | Mev | N1 | Week 2 |
| N4 | [MEV] Submit NEAR grant application at near.org/ecosystem/grants | Mev | N2 | Week 3 |

---

## Category 3: Decentralized AI Networks
### Priority: MEDIUM — Strategic positioning, future compute + validation

---

### 3A. Bittensor (Subnet Registration)

**What Bittensor Is:** Decentralized AI network where specialized "subnets" compete to provide the best AI services. Subnet validators earn TAO tokens. Otto's memory + reasoning could be a subnet.

**Pre-Requisites:**
- [ ] Deep research into Bittensor subnet registration requirements
- [ ] Understand current subnets (what's covered, what's missing)
- [ ] Otto Memory API packaged and documented publicly
- [ ] TAO wallet set up (BitTensor wallet)
- [ ] Technical whitepaper for proposed Otto subnet
- [ ] Read bittensor.com/docs thoroughly
- [ ] Budget: subnet registration costs ~1 TAO (~$200-500 at current rates)

**Outreach Angle:**
> "Otto implements the most complete open-source AI memory stack — episodic, semantic, procedural, knowledge graph. We're evaluating a Bittensor subnet for persistent AI memory-as-a-service: any AI agent on the network can access sovereign, vector-searchable memory without running their own infrastructure. Validators are rewarded for serving accurate, fast memory responses."

**Why Now / Why Wait:**
- Bittensor is a significant engineering investment (subnet development is complex)
- Only pursue after WebAssist generates revenue or after grant funding
- Monitor as strategic positioning — not Month 1 execution

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| BT1 | Research Bittensor subnet registration + active subnets audit | Otto | — | Week 2 |
| BT2 | Write Otto Memory subnet concept brief (incentive structure, validator model) | Otto | BT1 | Week 3 |
| BT3 | Post subnet concept in Bittensor Discord for feedback | Mev | BT2 | Week 3 |
| BT4 | [DECISION] Evaluate if subnet is viable — Mev decides go/no-go | Mev | BT3 community response | Week 4 |
| BT5 | Register subnet if approved (costs TAO + engineering time) | Otto | Mev approval | Month 2+ |

---

### 3B. Akash Network (Decentralized Compute Partner)

**What Akash Is:** Decentralized cloud compute marketplace — providers bid to host workloads, users get cheap cloud compute using AKT tokens. Otto's open-source deployment could use Akash as the recommended hosting provider.

**Pre-Requisites:**
- [ ] Otto Memory API packaged for Docker deployment
- [ ] Akash deployment spec (SDL file) for otto-memory stack
- [ ] Test deployment on Akash testnet
- [ ] Write "deploy Otto on Akash" tutorial

**Outreach Angle:**
> "Otto is open-source AI cognitive infrastructure. We're packaging it for community deployment — anyone should be able to run their own Otto on commodity infrastructure. Akash is the sovereign hosting layer that aligns with our values: decentralized, permissionless, no single provider lock-in. We want to make Akash the recommended hosting path for Otto community deployments."

**Partnership Angle:** Co-marketing — Akash gets a featured open-source AI project; Otto gets sovereign hosting endorsement.

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| A1 | Package otto-memory stack as Akash SDL deployment file | Otto | E1 (Memory API packaged) | Week 2 |
| A2 | Test deployment on Akash testnet | Otto | A1 | Week 2 |
| A3 | Write "Deploy Otto on Akash in 15 minutes" tutorial | Otto | A2 | Week 3 |
| A4 | Post tutorial to Akash Discord + community forum | Mev | A3 | Week 3 |
| A5 | Reach out to Akash team for co-marketing / ecosystem showcase | Mev | A4 + traction | Week 4 |
| A6 | Contact: akash.network/community → Discord #partnerships | Mev | A3 | Week 3 |

---

### 3C. Fetch.ai / Agentverse (AI Agent Marketplace)

**What Fetch.ai Is:** Decentralized AI agent network. Agentverse is their marketplace where AI agents register, discover each other, and transact. uAgents framework is their SDK.

**Pre-Requisites:**
- [ ] Understand Fetch.ai uAgents SDK (research task)
- [ ] Consider whether Otto's reasoning kernel can be wrapped as a uAgent
- [ ] Fetch.ai wallet + FET tokens for agent registration

**Outreach Angle:**
> "Otto is a persistent AI agent with full memory continuity. We want to explore registering Otto as a uAgent on Agentverse — making Otto's memory and reasoning capabilities available to other agents in the Fetch.ai ecosystem as discoverable services."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| FA1 | Research Fetch.ai uAgents SDK + Agentverse registration | Otto | — | Week 2 |
| FA2 | Evaluate fit: can Otto's APIs be wrapped as uAgent services? | Otto | FA1 | Week 2 |
| FA3 | [MEV DECISION] Go/no-go on Fetch.ai integration | Mev | FA2 | Week 3 |
| FA4 | Build uAgent wrapper for Otto Memory API if approved | Otto | Mev approval | Week 3-4 |

---

## Category 4: Developer Communities
### Priority: MEDIUM — Awareness, contributors, early adopters

---

### 4A. ETHGlobal (Hackathons)

**What ETHGlobal Is:** The premier Ethereum hackathon organizer. Runs multiple events per year (ETHGlobal online + in-person). Winning or participating builds massive credibility and contributors.

**Pre-Requisites:**
- [ ] Otto Memory API publicly deployable (documented)
- [ ] Clear "build with Otto" developer story (what can a hackathon project do with Otto?)
- [ ] Mev can participate or sponsor
- [ ] Check upcoming events: ethglobal.com/events

**Outreach Angle:**
> "Build your AI hackathon project with persistent memory from day one. Otto gives your agent real episodic memory, vector search, and knowledge graph — deployed in 30 minutes. No reinventing the memory layer."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| EG1 | Check ETHGlobal event calendar for upcoming hackathons | Otto | — | Week 1 |
| EG2 | Create "Build with Otto" quickstart guide for hackers | Otto | E1 (Memory API packaged) | Week 2 |
| EG3 | [MEV] Register for next ETHGlobal hackathon as participant | Mev | EG2 | Per event |
| EG4 | Post Otto quickstart in ETHGlobal Discord | Mev | EG2 | Week 2 |
| EG5 | Explore sponsoring a bounty track at ETHGlobal (costs $2K-$10K) | Mev | Revenue/grants | Month 2+ |

---

### 4B. DoraHacks (BUIDLs + Hackathons)

**What DoraHacks Is:** Open-source developer platform + hackathon organizer. BUIDL grants, DAO tooling, massive community in Asia. Koink.fun and 505 Systems are natural fits for their ecosystem.

**Pre-Requisites:**
- [ ] Create DoraHacks profile (dorahacks.io)
- [ ] List MY3YE projects as BUIDLs (open-source project listings)
- [ ] Koink.fun or 505 Systems must have some public code

**Outreach Angle:**
> "14 open-source projects building sovereign infrastructure — AI, identity, governance, emergency mesh, tokenomics. All public. All forkable. Anyone can contribute or build on top."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| D1 | Create DoraHacks profile and list MY3YE ecosystem projects | Otto/Mev | public repos | Week 1 |
| D2 | Apply to any active DoraHacks hackathon that fits (governance, AI, humanitarian) | Mev | D1 | Per event |
| D3 | Engage DoraHacks community with 505 Systems governance angle | Mev | D1 | Week 2 |

---

### 4C. HackerNews / Dev Communities (OSS Launch)

**What HN Is:** Show HN posts are extremely effective for open-source launches. AI infrastructure projects consistently get traction here.

**Pre-Requisites:**
- [ ] Otto Memory API fully documented and deployable
- [ ] Compelling Show HN headline ready
- [ ] GitHub README polished and engaging
- [ ] Mev has HN account with history (or create one)

**Outreach Angle:**
> "Show HN: I built an open-source AI cognitive OS — persistent memory, reasoning kernel, task queue. Runs on a $20 VPS."

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| HN1 | Polish otto-core README + add architecture diagrams | Otto | E1 | Week 2 |
| HN2 | Write Show HN post draft | Otto | HN1 | Week 2 |
| HN3 | [MEV] Submit Show HN post at peak traffic (9AM PST Tuesday-Thursday) | Mev | HN2 | Week 2 |
| HN4 | Engage with all HN comments for first 24 hours | Mev | HN3 | Day of post |

---

## Category 5: Key Individuals
### Priority: LOW-MEDIUM — High effort, high reward if right connection

**Rule:** Never cold-pitch individuals without establishing genuine value first. Warm outreach only. Always give before you ask.

---

### 5A. Kevin Owocki (Gitcoin / Public Goods)

**Who:** Co-founder of Gitcoin, one of the most influential public goods advocates in Web3. Now at Supermodular.xyz.

**Pre-Requisites:**
- [ ] MY3YE public goods narrative clearly written and published ✅
- [ ] Otto AI Gitcoin profile submitted ✅ (written, needs submission)
- [ ] Engage with Kevin's content on X/Farcaster for 2 weeks before outreach
- [ ] Have something genuinely interesting to say (not "please fund us")

**Outreach Angle:**
> "We're building open-source AI infrastructure as public goods — no VC money, community-governed, anyone can fork and deploy. Otto is the AI version of what you were trying to do with Gitcoin: build the infrastructure that makes the next thing possible. I'd love your read on whether our approach to contribution-weighted governance (DPC) solves the coordination problems Gitcoin ran into."

**Channel:** Farcaster DM (not Twitter), or via Gitcoin community introduction

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| K1 | Follow and engage genuinely with Kevin's content for 2 weeks | Mev | Farcaster account | Week 1-2 |
| K2 | Submit Gitcoin project (proves legitimacy before DM) | Mev | G2 | Day 2 |
| K3 | [MEV] Send thoughtful Farcaster DM after 2 weeks of genuine engagement | Mev | K1, K2 | Week 3 |

---

### 5B. Vitalik Buterin Adjacent (Ethereum Foundation)

**Who:** Not Vitalik directly — approach EF ecosystem support program contacts and researchers who engage with public goods AI infrastructure.

**Pre-Requisites:**
- [ ] Otto Memory API documented + published
- [ ] Technical blog post or research note published on otto.lk or Mirror.xyz
- [ ] EF ESP application submitted (E4)
- [ ] Post in Ethereum Research (ethresear.ch) with genuine technical contribution

**Outreach Angle:**
> Not a cold pitch — write a technical post about Otto's AgentOS implementation and why persistent AI memory is a public goods problem. Let the content attract inbound.

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| V1 | Write technical blog post: "AgentOS in production — what we learned building persistent AI memory" | Otto | — | Week 2 |
| V2 | Publish on Mirror.xyz (Web3 native) and otto.lk | Mev | V1 | Week 2 |
| V3 | Submit to ethresear.ch if it has a research angle | Mev | V1 | Week 2 |
| V4 | Engage with EF researchers who comment on the post | Mev | V3 | After post |

---

### 5C. Polkadot/Kusama Community Leaders

**Who:** Shawn Tabrizi (Parity, OpenGov expert), Gavin Wood's Jam roadmap contributors, active governance voters.

**Pre-Requisites:**
- [x] W3F grant proposal written
- [ ] pallet-dpc spec doc on GitHub
- [ ] Post in Polkadot forum to establish presence

**Outreach Angle:**
> "I'm working on pallet-dpc — a Substrate-native governance weight module that earns standing through contribution, not tokens. Before submitting the W3F grant, I wanted to get input from people actually working on OpenGov. Would you be open to a quick review of the spec?"

**Channel:** Polkadot Element matrix chat / direct GitHub PR feedback request

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| PL1 | Post `pallet-dpc` spec in Polkadot OpenGov forum, tag active contributors | Mev | W1 (spec doc) | Week 2 |
| PL2 | Ask specific technical questions (not promotion) to start conversation | Mev | PL1 | Week 2 |
| PL3 | Build relationship over 2 weeks before asking for grant intro or review | Mev | PL1 | Week 3-4 |

---

### 5D. Solana Ecosystem Influencers + BONK DAO Leaders

**Who:** BONK DAO multisig holders, Superteam (Solana's builder network), Mert Mumtaz (Helius), prominent Solana devs.

**Pre-Requisites:**
- [ ] Koink.fun live with mailing list
- [ ] @KoinkFun Twitter active with posts
- [ ] $KOIN testnet deployment live
- [ ] Genuine community participation before outreach

**Outreach Angle:**
> "Building the $KOINK Standard — open-source fair tokenomics infrastructure for Solana meme culture. Every project that forks it gets anti-whale mechanics, VRF-based fair distribution, and Diamond Hands governance weight. Want early eyes on the standard?"

**Channel:** Twitter DM only after organic engagement; Superteam Discord

**Sequenced Tasks:**
| # | Task | Owner | Prereq | ETA |
|---|------|-------|--------|-----|
| SL1 | Engage in Superteam Discord for 1 week before any ask | Mev | — | Week 1 |
| SL2 | Post $KOINK Standard thread on @KoinkFun Twitter | Mev | Koink.fun page | Week 1 |
| SL3 | Tag Solana ecosystem builders in thread (not BONK DAO yet) | Mev | SL2 | Week 1 |
| SL4 | [MEV] DM 3 Superteam members asking for feedback on $KOINK Standard | Mev | SL1, SL3 | Week 2 |
| SL5 | Approach BONK DAO after establishing Solana community presence | Mev | SL4 | Week 3 |

---

## Master Sequencing Calendar

### Week 1 — Foundation (Before ANY community outreach)
- [ ] Create Twitter/X presence for MY3YE and @KoinkFun
- [ ] Create Farcaster account (Mev)
- [ ] Create Gitcoin account + submit Otto AI and WebAssist profiles (Mev)
- [ ] Submit W3F grant proposal to GitHub
- [ ] Post MY3YE introduction on Farcaster
- [ ] Begin Polkadot Discord participation
- [ ] Begin Superteam Discord participation
- [ ] Check ETHGlobal + DoraHacks event calendars
- [ ] Create DoraHacks profile

### Week 2 — Presence Building + Early Submissions
- [ ] Koink.fun landing page live
- [ ] Write Show HN post, polish otto-core README
- [ ] Post `pallet-dpc` spec in Polkadot forum
- [ ] Write technical blog post on Otto AgentOS
- [ ] Publish blog post on Mirror.xyz
- [ ] Research Bittensor subnets
- [ ] Package Otto Memory for Akash deployment
- [ ] Create Optimism Agora profile, participate in governance

### Week 3 — Outreach Activation
- [ ] Submit Show HN (after README polished)
- [ ] Post $KOINK Standard thread on Twitter
- [ ] Post Akash tutorial in their Discord
- [ ] Reach out to Fetch.ai community
- [ ] Begin warm engagement with Kevin Owocki on Farcaster
- [ ] Post in Celo Discord after grant application submitted
- [ ] Approach Superteam members for $KOINK feedback

### Week 4+ — Relationship Deepening + Follow-up
- [ ] Follow up on W3F grant application (if no response)
- [ ] Evaluate Bittensor subnet go/no-go (Mev decision)
- [ ] BONK DAO grant proposal submission
- [ ] Deepen Polkadot relationships, consider PiPi mascot conversation
- [ ] ETH Foundation ESP application follow-up
- [ ] Solana Foundation grant submission (if chain confirmed)

---

## Pre-Requisite Readiness Tracker

| Asset | Status | Priority to Build |
|-------|--------|------------------|
| otto.lk live | ✅ | — |
| webassist.ink live | ✅ | — |
| otto-core GitHub open | ✅ | — |
| Public goods narrative | ✅ | — |
| Gitcoin project profiles (written) | ✅ | — |
| W3F grant proposal (written) | ✅ | — |
| $KOIN tokenomics paper | ✅ | — |
| Investor pitch deck | ✅ | — |
| Twitter/X presence | ❌ | P0 |
| Farcaster account | ❌ | P0 |
| Koink.fun landing page | ❌ | P0 |
| `pallet-dpc` spec doc on GitHub | ❌ | P1 |
| Otto Memory API packaged for deployment | ❌ | P1 |
| Technical blog post (AgentOS) | ❌ | P1 |
| Panik App Figma prototype | ❌ | P1 |
| 505 Systems technical spec | ❌ | P1 |
| ONEON identity protocol spec | ❌ | P2 |
| Akash SDL deployment file for otto-memory | ❌ | P2 |
| Bittensor subnet research complete | ❌ | P2 |
| @KoinkFun Twitter account | ❌ | P1 (after chain confirmed) |

---

## Quick-Start: Top 5 Actions Mev Can Take This Week

1. **Create Gitcoin account + submit Otto AI and WebAssist profiles** (profiles are written, just needs submission)
2. **Create Farcaster account and post MY3YE intro** (takes 30 minutes, opens all Farcaster outreach)
3. **Submit W3F grant proposal as GitHub PR** (proposal is written, just needs to be submitted to w3f/grants-program)
4. **Confirm Solana as $KOIN launch chain** (unblocks Koink.fun page, BONK DAO, Solana Foundation grant)
5. **Create Twitter/X presence** (@MY3YE or @OttoAgent + @KoinkFun — both need handles claimed)

# zkPresence — Go-To-Market & Monetization Playbook
**Date:** 2026-04-11 | **Status:** Internal — pre-OSS launch | **Author:** Otto (growth-hacker agent)

---

## Executive Summary

zkPresence is the first open-source SP1-native ZK attendance protocol. The closest competitor (Zupass) is PCF-controlled, Circom-based, and venue-specific. The largest market (POAP) has 80M+ distributions with zero privacy. There is a genuine gap: a permissionless, multi-mode, SP1-powered attendance proof developer protocol with a managed cloud API on top.

**The play:** Release the core protocol as MIT open source to capture developer mindshare, SP1 ecosystem grants, and hackathon buzz — then monetize the managed proving API via usage-based SaaS. Internal MY3YE projects (ONEON, Tusita, SOS, Koink) consume the Pro tier at $0, validating the product and generating case studies.

**Pre-condition:** Circuit must ship first. SHA-256 precompile (main.rs:20) AND ECDSA stubs (main.rs:61/88/104) must land in the same PR before any OSS or GTM activity begins. Partial fix = silent auth bypass = catastrophic reputation event for a ZK security protocol.

---

## 1. Open-Core Model

### What is free (MIT OSS)

| Component | Repo | Why Free |
|-----------|------|----------|
| `@zkpresence/core` — Rust circuit, nullifier math, AttestationData types | zkpresence/zkpresence | Core primitive; drives GitHub stars and grant eligibility |
| `@zkpresence/sdk` — TypeScript SDK (prove, verify, event management) | zkpresence/zkpresence | Developer adoption; removes friction to first proof |
| `@zkpresence/adapter-evm` — Base/Arbitrum/Ethereum adapter | zkpresence/zkpresence | EVM is the primary chain target; must be OSS |
| `ZkPresence.sol` — Verifier gateway contract | zkpresence/zkpresence | On-chain infra; open for composability and audits |
| `@zkpresence/react-hooks` — useProveAttendance, useVerifyProof | zkpresence/zkpresence | Frontend adoption hook; tutorial fodder |
| CLI tool — local proof generation, event creation | zkpresence/zkpresence | Self-sovereign option; trust signal for OSS community |
| Docker compose — self-hosted service stack | zkpresence/zkpresence | Enterprise sales require self-host option |

### What is paid (managed cloud service)

| Component | Gate | Rationale |
|-----------|------|-----------|
| Managed Proving API (`api.zkpresence.xyz`) | Paid tiers | SP1 prover compute is the COGS; open but expensive to run |
| Succinct Network proof routing + failover | Paid tiers | Cost and reliability optimization layer |
| Dashboard — event analytics, proof history, nullifier auditing | Paid tiers | Dev experience layer; not core protocol |
| Webhook delivery — real-time proof status events | Team+ | Operational convenience |
| SLA guarantees + uptime commitments | Pro/Enterprise | B2B requirement |
| Custom chain adapter support | Enterprise | Engineering time = billable |
| Private SP1 prover deployment | Enterprise | Air-gapped / compliance use cases |

### OSS License: MIT
Rationale: Broadest developer adoption. Prevents "license fear." Consistent with SP1 (MIT/Apache) and Semaphore (MIT). Enterprise terms (support, SLAs, private deployment) negotiated separately.

---

## 2. Managed Cloud Service — Pricing Tiers

### Tier Architecture

| Tier | Name | Price | Proofs/mo | Proof SLA | Chains | Support | Target |
|------|------|-------|-----------|-----------|--------|---------|--------|
| F0 | **Developer** | $0 | 100 | Best-effort (< 5 min avg) | Base only | Community Discord | Hackathon builders, individual devs |
| T1 | **Starter** | $49/mo | 2,000 | < 3 min p95 | Base + Arbitrum | Email (48h) | Early-stage dApps, DAOs < 500 members |
| T2 | **Team** | $199/mo | 20,000 | < 90s p95 | EVM all + Solana (Q3) | Email (24h) + Discord channel | Active event protocols, mid-size DAOs |
| T3 | **Scale** | $599/mo | 100,000 | < 60s p95 | All adapters | Priority email + Slack | High-volume event platforms, DeFi protocols |
| T4 | **Enterprise** | Custom | Unlimited | Custom SLA + dedicated worker pool | All + custom | Named CSM + SLA contract | DAO platforms, enterprise HR, compliance |

### Overage Pricing
- Developer: blocked at limit (forced upgrade prompt)
- Starter–Scale: $0.03/proof over quota
- Enterprise: pre-negotiated commit + overage rate

### Unit Economics (estimates)
- SP1 proof via Succinct Network: ~$0.01–0.02/proof at scale
- Gross margin target: 60–70% at T2+
- Developer tier: pure CAC investment; convert at 8–12% to paid within 90 days

### Internal Project Pricing
All MY3YE ecosystem projects (ONEON, Tusita, SOS, Koink, Otto Music) access Team-tier equivalent at $0 during development. Billed at cost once revenue-generating. This ensures the product is dogfooded and case studies are generated.

---

## 3. 90-Day OSS Launch Traction Plan

### Pre-condition: Circuit ships (Day 0)
- Wire SHA-256 precompile + ECDSA stubs in one PR
- Full Rust unit tests + Solidity `.t.sol` coverage
- Fix ARCHITECTURE.md geohash contradiction
- Internal integration with ONEON or Tusita for live proof generation

### Week 1–2: Repo Launch

**GitHub setup (Day 1):**
- Monorepo at `github.com/my3ye/zkpresence`
- README: 3-line hook, 5-minute quickstart, live demo badge
- README badge targets: SP1 version, npm version, license, Discord
- CONTRIBUTING.md, issue templates, project board visible
- `good-first-issue` labels on 5–8 circuit/test tasks (drives community PRs)

**Initial content burst:**
- Twitter/X thread: "We built the first open-source ZK attendance proof using SP1. Thread on why ZK + events is inevitable 🧵" — tag @succinctlabs, @ethereum
- Farcaster cast (Warpcast) — ZK developer community is active here post-Lens/Farcaster consolidation
- Dev.to or Mirror article: "zkPresence: Private Proof of Attendance without POAP's privacy problem"
- Submit to: This Week in ZK (newsletter), ZK Hack Discord, Telegram channels (ZK research, SP1 builders)
- DM Succinct Labs team directly — request inclusion in SP1 ecosystem page and grant intro call

**Target: 200+ GitHub stars by end of Week 2**

### Week 3–4: Ecosystem Placement

**SP1 Ecosystem Grant (apply by Day 14):**
- Succinct Network ecosystem grants are active for SP1-native projects
- Application angle: "First SP1 attendance protocol — fills the gap Semaphore doesn't (attendance-specific, Rust-native, multi-mode)"
- Request: $10K–25K in compute credits or USDC
- Deliverable: test suite, docs, and 1 production integration

**Ethereum Foundation PSE Inquiry:**
- PSE co-funded ZK grant pool ($900K) with Aztec/Polygon/Scroll/Taiko/zkSync
- Semaphore precedent: they funded group membership primitives
- zkPresence angle: attendance-specific ZK primitive for the Ethereum ecosystem
- Contact: pse@ethereum.org + forum post in ETH Magicians under ZK tooling

**XMTP Partnership Outreach:**
- XMTP mainnet launched March 2026, $20M Series B, integrated into Coinbase Base
- zkPresence XMTP adapter (Phase 2) = proof-gated group chats
- Angle: "zkPresence + XMTP = private group access without revealing who's in the group"
- DM XMTP team on Farcaster/Discord; request co-announcement

### Week 5–8: Hackathon Seeding

**ETHGlobal Hackathon (primary target):**
- ETHGlobal runs quarterly hackathons (online + in-person)
- Submit zkPresence as a featured bounty sponsor: $2K–5K in prizes for best zkPresence integration
- Prize track themes: "Privacy-Preserving Event UX", "ZK-gated Community Access"
- Provide: npm package, quickstart tutorial, Discord support during hackathon

**ZK Hack (secondary target):**
- ZK Hack III or IV — ZK-specific hackathon run by Encode Club + community
- Submit as a protocol track, not just a bounty — increases visibility

**Internal hackathon integration:**
- Pick one MY3YE project (Tusita or ONEON) to build a production zkPresence integration during this window
- Document and publish: "How we built ZK attendance into Tusita in 2 days"
- This is the live case study + technical tutorial in one

### Week 9–12: Community Consolidation

**Content engine (2x/week):**
- Twitter/X: ZK explained content — "Why your POAP is a privacy liability", "How SP1 makes ZK proofs 100x more accessible", "Building private event gating in 20 lines of TypeScript"
- GitHub Discussions enabled: encourage builders to post "Show and Tell" implementations
- Changelog posts for each release (even patch releases — signals active maintenance)

**Developer newsletter placement:**
- JavaScript Weekly, Node Weekly (via TypeScript SDK angle)
- Rust Weekly / This Week in Rust
- Blockchain Dev newsletter (Bankless Dev, Alchemy Developer Newsletter)

**Metrics targets at Day 90:**
| Metric | Target |
|--------|--------|
| GitHub stars | 500+ |
| npm downloads/week | 200+ |
| Discord members | 150+ |
| Proof API signups (Developer tier) | 75+ |
| Paid conversions (Starter+) | 8–12 |
| Grant applications submitted | 2 (Succinct + PSE) |
| Hackathon integrations | 5+ projects |
| Live production integrations | 1 (internal MY3YE) |

---

## 4. Ideal Customer Profiles (ICPs)

### ICP 1: Event DAO / Protocol DAO Governance Team

**Profile:**
- DAO with 100–5,000 active contributors
- Running regular community calls, IRL meetups, or governance workshops
- Currently using POAP for attendance tracking (exposed wallet addresses)
- Governance eligibility tied to participation — currently gameable
- Technical: has 1–2 engineers, uses Foundry/Hardhat, Base or Arbitrum

**Pain:**
- POAP links wallet identity to event attendance → privacy exposure
- POAP farming is rampant → participation records are polluted
- "Who actually showed up" vs "who claimed a POAP" is unanswerable with confidence

**Outreach angle:**
- "Your governance votes are only as credible as your attendance records. zkPresence makes participation provable and private."
- Target Discord servers: BanklessDAO, Developer DAO, Optimism Citizens House, ENS DAO
- LinkedIn: "Head of Community", "DAO Operations Lead", "Governance Coordinator"
- Cold email hook: "80M POAPs distributed. Zero privacy. Here's what we built instead."

**One-liner value prop:** *"Turn event attendance into tamper-proof governance eligibility — without exposing who attended."*

---

### ICP 2: DeFi Protocol or NFT Project with IRL Activations

**Profile:**
- DeFi protocol or NFT project running IRL events (conferences, community dinners, side events)
- Wants to gate token airdrops, early access, or NFT claims to "people who were actually there"
- Currently using: QR code scans, POAPs, organizer manual whitelisting
- Technical: sophisticated Solidity team, already on Base/Arbitrum, web3-native dev culture

**Pain:**
- Manual whitelisting is slow and error-prone
- QR codes are easily screenshot-shared → airdrop farming
- On-chain NFT proofs are public → metadata leaks real-world attendance patterns

**Outreach angle:**
- Conferences: ETHDenver, ETHGlobal, TOKEN2049, Consensus — target "Ecosystem Lead" and "Growth" roles
- Twitter/X DMs after they announce IRL events: "Saw you're doing an IRL at ETHGlobal — how are you handling attendance verification? We built ZK proofs for exactly this."
- Partnership pitch: zkPresence powers the airdrop gate for their next IRL event, co-marketed as "private, fair, unfarmable"

**One-liner value prop:** *"Airdrop to the people who were actually there — provably, privately, unfarmably."*

---

### ICP 3: Enterprise Learning & Compliance Platform

**Profile:**
- Corporate L&D (Learning & Development) or compliance training platform
- Runs in-person or hybrid training sessions with certification requirements
- Currently: manual sign-in sheets, badge scanning, QR code check-ins → centralized attendance database
- Need: attendance proofs for regulatory compliance (SOC 2, ISO certification training, AML training)
- Technical: REST API consumers, not necessarily web3-native; have budget

**Pain:**
- Centralized attendance databases are audit targets, breach risks
- Privacy regulations (GDPR, CCPA) create liability for storing "who was trained where and when"
- Regulatory proofs must be auditable without exposing employee records

**Outreach angle:**
- Framing is NOT web3 — frame as "zero-knowledge attendance certification" or "privacy-preserving compliance proof"
- Channels: LinkedIn targeting "Director of Compliance", "L&D Manager", "Information Security Officer"
- Industry: Financial services (AML training), healthcare (HIPAA training), Big Tech (security certifications)
- Partner channel: HR tech platforms (Workday, SAP SuccessFactors) via developer API partnership

**One-liner value prop:** *"Prove employees completed compliance training without storing who attended where — audit-ready, GDPR-compliant, zero-breach-risk."*

---

## 5. 30-60-90 Summary Table

| Phase | Focus | Key Actions | Success Signal |
|-------|-------|-------------|----------------|
| **Days 1–30** | Circuit fix + OSS launch | Wire precompiles, write tests, publish repo, Twitter thread, Succinct grant application | 200 GitHub stars, 1 grant submitted |
| **Days 31–60** | Ecosystem seeding | ETHGlobal bounty, XMTP partnership outreach, PSE inquiry, internal ONEON/Tusita integration | 5+ hackathon projects, 1 live production integration |
| **Days 61–90** | Developer conversion | API signups, content engine, newsletter placements, paid conversion push | 75+ API signups, 8–12 paid customers, 500 GitHub stars |

---

## 6. Positioning Statement (internal)

> zkPresence is the developer protocol for private, tamper-proof event attendance. Built on SP1 — the fastest ZK proving stack on RISC-V — it lets any developer add zero-knowledge attendance proofs to their app in under an hour. Free to self-host. Managed API for teams who don't want to run provers.

**Competitive moat (sustain for 18 months):**
1. Only SP1-native attendance protocol — Succinct ecosystem alignment
2. Three attestation modes (QR, Geohash, Organizer sig) — no competitor matches
3. Chain-agnostic adapter pattern — not locked to any L2
4. Internal MY3YE ecosystem dogfooding — real production traffic, real case studies
5. $0.003/proof on Base — 30–100x cheaper than Ethereum mainnet alternatives

---

## 7. Revenue Model Summary

| Source | Year 1 Target | Notes |
|--------|---------------|-------|
| Managed API (T1–T3) | $6,000–8,000 MRR | Conservative; 8–12 paid customers at T1-T2 |
| Enterprise contracts | 1–2 pilots | $500–2,000/mo each; require CSM |
| Grant income | $25,000–50,000 | Succinct Network + PSE + ZKsync Foundation |
| Internal value (internal projects) | N/A | Validates product, generates case studies |

**Priority:** Grant income funds prover compute during year 1. Paid API revenue at scale. Enterprise as a Q4 2026 push.

---

*Document produced by Otto growth-hacker agent, 2026-04-11. Based on architect output (t1) and competitive research (t2). Pre-condition: circuit fix PR must land before any GTM execution.*

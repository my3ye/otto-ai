# Polkadot & Solana: Identity/Social Stack Research
*Date: 2026-03-28 | Task: 08d9842a*

## Summary

Neither Polkadot nor Solana has a single protocol that integrates identity + comms + governance + encrypted storage into one coherent layer. Both ecosystems have strong individual pieces with significant coordination gaps between them — and neither has a non-technical user onboarding story.

---

## POLKADOT

### 1. People Chain — On-Chain Identity

**Scope:**
- Dedicated system parachain for decentralized identity management
- Users create verifiable on-chain identities with selective disclosure
- Hierarchical structure: primary accounts + up to 100 sub-accounts
- Registrar judgment system: Unknown → Reasonable → Known Good
- Bond required (locked DOT, returned on identity clear)

**Proof of Personhood / Individuality (DIM1 + DIM2):**
- Announced by Gavin Wood at Web3 Summit 2025
- DIM1 = Proof of Individuality: one-person-one-vote without formal ID, using ZK proofs
- DIM2 = Proof of Verified Individuality: opt-in KYC-grade verification for compliance use cases
- DIM1 code "basically complete" as of June 2025 technical fellowship calls
- No launch date confirmed; $3M treasury proposal to support rollout
- Cross-chain interoperability: people-related logic designed to span relay chain + parachains

**Limitations:**
- Identity only — NO messaging, NO comms protocol
- Verification is registrar-dependent (semi-centralized judgment)
- Bond requirement is UX friction for non-technical users
- ZK proof infra complex to build on top of
- PoP system still not live as of 2026-Q1

---

### 2. OpenGov — Governance

**Scope:**
- Fully decentralized governance framework (launched June 2023)
- Multiple simultaneous referenda tracks
- Conviction-weighted voting
- Delegation: users can assign votes to domain experts per track
- 1,008% increase in referenda, 1,981% increase in votes over first 6 months
- UI layers: Polkassembly, Subsquare

**Limitations:**
- Governance only — NO identity integration, NO messaging, NO storage
- High complexity: token holders must understand tracks and conviction multipliers
- Non-technical users cannot meaningfully participate without UI abstraction
- No connection between OpenGov voting and People Chain identity (votes are wallet-weighted, not identity-weighted)
- No encrypted discussion layer — all proposals/comments are public

**ONEON Opportunity:** 505 Systems' DPC (contribution-weighted governance) directly addresses OpenGov's token-weighted bias. This is the cleanest W3F grant narrative.

---

### 3. Social/Comms Primitives

**What exists:**
- Polkassembly and Subsquare provide governance discussion forums (off-chain)
- No native on-chain messaging protocol
- No encrypted storage layer
- No social graph protocol

**Gap:** Polkadot has NO native social or comms layer. Everything is governance or identity — isolated silos with no connection.

---

## SOLANA

### 1. Solana Name Service (SNS) / Bonfida

**Scope:**
- .sol domain names mapped to wallet addresses + on-chain data
- 283,000+ registered domains, 129,000 unique holders, 150 ecosystem partners
- SNS token launched May 2025 for governance of the .sol protocol
- Used as identity backbone by ~150 dApps
- Cross-chain: xMS (Cross Messaging Service) uses .sol domains and Twitter handles as universal identity

**Limitations:**
- Naming/identity only — NOT a social graph
- No verification or reputation layer
- No messaging built in (xMS is a separate protocol that uses SNS as identity)
- No encrypted storage
- SNS governance only covers the naming protocol itself, not broader ecosystem governance

---

### 2. Dialect — Smart Messaging

**Scope:**
- Wallet-to-wallet messaging + dApp notification infrastructure on Solana
- Powers 30+ dApps and wallets on Solana and Aptos
- Smart messages: rich interactive content (like link previews for Web3)
- Mobile Alert stack: push notifications for DeFi positions (live via Jupiter Mobile, 2025)
- Pub-sub model: PDAs with lexically-sorted resource keys as seeds
- xMS cross-chain standard: Solana + Ethereum messaging via Open Chat Alliance (19 founding projects incl. Dialect, Bonfida, Notifi)

**Current Limitations:**
- v0: 1:1 messaging only (wallet-to-wallet or dApp-to-user)
- 1:many and many:many still on roadmap
- No group chat, no community channels
- No encryption by default (protocol-level encryption not confirmed as default)
- Not integrated with governance
- Notification-centric, not social-network-centric

---

### 3. DeSo — Decentralized Social Blockchain

**Scope:**
- Separate blockchain (not native Solana) purpose-built for social
- DeSo Identity™: self-custodial identity + portable social graph
- One profile, portable across any app building on DeSo
- Content ownership: posts, follows, likes all on-chain
- Creator coins, NFTs, social tokens

**Limitations:**
- Requires own blockchain — not composable with Solana or Polkadot natively
- Limited adoption vs. Lens/Farcaster in Web3 social landscape
- No governance layer
- No encrypted messaging (social graph is public)
- Not a multi-chain solution

---

### 4. Compressed NFTs (cNFTs)

**Scope:**
- Merkle tree storage: only root hash on-chain, full data verifiable off-chain
- Drastically lower minting costs (millions of NFTs at cents)
- Supported by Phantom, Solflare, Backpack
- Use case: social badges, credentials, attendance proofs, membership tokens

**Relevance to Identity/Social:**
- Useful for soulbound credentials, reputation tokens, event proofs
- NOT a social protocol itself — an efficiency primitive
- Could serve as a substrate for ONEON's credential/reputation layer

---

## CROSS-CHAIN COMPARISON MATRIX

| Feature | Polkadot | Solana | ONEON Target |
|---|---|---|---|
| On-chain identity | ✅ People Chain | ✅ SNS (.sol) | ✅ |
| Proof of personhood | 🔄 In progress (DIM1) | ❌ | ✅ |
| Messaging | ❌ None | ✅ Dialect (limited) | ✅ |
| Encrypted messaging | ❌ | ❌ (not confirmed) | ✅ |
| Social graph | ❌ | ⚠️ DeSo (separate chain) | ✅ |
| Governance | ✅ OpenGov | ⚠️ SNS-token only | ✅ |
| Identity-weighted governance | ❌ | ❌ | ✅ (DPC) |
| Encrypted storage | ❌ | ❌ | ✅ |
| Non-technical UX | ❌ | ⚠️ (improving) | ✅ (core mission) |
| Cross-chain interop | ✅ (within Polkadot) | ⚠️ (xMS early) | ✅ |
| Unified layer | ❌ | ❌ | ✅ TARGET |

---

## KEY INSIGHT: The Integration Gap

**Polkadot:** Has identity (People Chain) + governance (OpenGov) but they are NOT integrated. Voting is token-weighted, not identity-weighted. No messaging. No social graph. No encrypted storage.

**Solana:** Has naming/identity (SNS) + notifications/messaging (Dialect) but they are loosely coupled. No governance integration. No encrypted storage. 1:1 messaging only.

**Neither ecosystem has:**
1. A unified layer connecting all four primitives (identity + comms + governance + storage)
2. Identity-weighted governance (votes proportional to verified identity, not token holdings)
3. End-to-end encrypted messaging as a default
4. Encrypted sovereign storage
5. A non-technical onboarding story

**ONEON's position:** The invisible Web3 infrastructure layer that treats these four primitives as one integrated system. Users get an identity that governs, communicates, and stores — without knowing they're using any blockchain.

---

## GRANT/BD IMPLICATIONS

**Polkadot W3F:**
- ONEON → People Chain integration is the cleanest L1 grant narrative ($10K)
- Build on top of DIM1 (Proof of Individuality) once it launches — provide the UX layer W3F can't
- 505 Systems → OpenGov module for identity-weighted (DPC) voting — fills documented gap

**Solana Foundation:**
- ONEON + Dialect integration: add encrypted group messaging on top of Dialect's infrastructure
- Use compressed NFTs for ONEON credentials/badges
- Could deploy ONEON identity standard using SNS as the naming layer

**Competitive moat:** Every existing solution requires you to already be in Web3 to use it. ONEON's job is to make the on-ramp invisible — that's the gap no one has filled.

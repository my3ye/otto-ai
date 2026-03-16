# ONEON — Comprehensive Roadmap
*Sovereign identity and communication network. The foundation all other projects stand on.*
*Last updated: 2026-03-16*

## Current Status
**EARLY** — Landing page live at oneon.ink. No backend yet.

## Dependencies
- **Hard deps:** None (foundational layer)
- **Soft deps:** S0S Systems (governance for protocol decisions)
- **Blocks:** All projects needing auth, identity, encrypted comms

---

## Phase 1 — Waitlist & Foundation (NOW → 30 days)
**Goal:** Active community pipeline. Technical foundation designed.

### Milestones
1. **Waitlist backend wired** — Submissions stored, confirmation email sent, contributor vs user tagged
2. **Landing page messaging** — 5-layer architecture clearly explained, waitlist CTA prominent
3. **Chain decision finalized** — Solana vs custom L2 researched, decision documented with rationale
4. **Technical whitepaper v0.1** — Architecture documented: layer-by-layer, identity model, key management
5. **Community seeding** — 500 waitlist signups from Web3-native audience

### Success Criteria
- Waitlist backend live (no data loss)
- ≥500 waitlist signups
- Chain decision documented and rationale shared

---

## Phase 2 — Private Alpha (30→90 days)
**Goal:** Real identity layer working for early community.

### Milestones
1. **Layer 1 live** — Decentralized identity: self-sovereign keys, ONEON DID creation
2. **Layer 2 live** — Encrypted messaging: end-to-end encrypted DMs between identities
3. **Invite-only alpha** — 500 early users testing identity + messaging
4. **Otto.lk integration** — First external app using ONEON auth (login with ONEON to otto.lk)
5. **Developer documentation** — How to integrate ONEON auth into your app

### Success Criteria
- 500 active identities created
- DM delivery reliability ≥99%
- At least 1 external app (otto.lk) using ONEON auth
- Zero private key exposure incidents

---

## Phase 3 — Public Launch (90 days → 6 months)
**Goal:** ONEON becomes the auth standard across all MY3YE projects.

### Milestones
1. **ONEON v1.0 public** — Open signup, no invite required
2. **Layers 1-4 operational** — Identity + DMs + Communities + Publishing
3. **All MY3YE projects integrated** — Every project authenticates via ONEON
4. **10,000+ active identities**
5. **Layer 5 beta** — Sovereign Self (biometric + reputation) for contributors

### Success Criteria
- 10,000 active identities
- All 15 MY3YE projects using ONEON auth
- Average identity creation time ≤60 seconds
- Community layer: ≥100 active communities

---

## Phase 4 — Protocol & Devices (6→12 months)
**Goal:** ONEON runs on physical hardware, not just web.

### Milestones
1. **Ottolabs Puck integration** — Puck device uses ONEON key for device identity
2. **Mesh network layer** — P2P communication between ONEON nodes (Panik App dependency)
3. **ONEON SDK v1.0** — Any developer anywhere can integrate ONEON auth
4. **50,000+ identities**
5. **Governance integration** — ONEON identity weight feeds into S0S governance

### Success Criteria
- SDK adopted by ≥5 external projects (outside MY3YE)
- Mesh network operational across ≥10 Puck nodes
- Identity is persistent across Puck, phone, web — same key everywhere

---

## The 5 Layers

| Layer | Name | Description | Phase |
|-------|------|-------------|-------|
| 1 | Core Identity | Self-sovereign keys, DID creation | Phase 2 |
| 2 | Encrypted Comms | E2E DMs, group chats | Phase 2 |
| 3 | Community | Spaces, forums, governance rooms | Phase 3 |
| 4 | Publishing | Censorship-resistant posts, content | Phase 3 |
| 5 | Sovereign Self | Biometric identity, reputation layer | Phase 3-4 |

## Tech Considerations
- **Chain options:** Solana (fast, cheap, ecosystem) vs custom L2 (maximum sovereignty)
- **Key management:** Must work offline, on mobile, on Puck hardware
- **Domain:** oneon.ink
- **Repo:** /mnt/media/projects/oneon-web

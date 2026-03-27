# ENS Public Goods Builder Grant — ONEON Application
**Portal:** builder.ensgrants.xyz/large-grant-apply
**Grant Type:** Large Grant (up to 50K USDC, milestone-based)
**Status:** READY TO SUBMIT — Mev connect wallet and copy-paste fields below

---

## HOW TO SUBMIT

1. Go to: **https://builder.ensgrants.xyz/large-grant-apply**
2. Connect your ENS wallet (Mev's .eth wallet)
3. Fill each field below (copy-paste ready)
4. Add 4 milestones as described
5. Submit

---

## FORM FIELDS

### Title *
```
ONEON — Extending ENS From Address Resolution Into Sovereign Identity Infrastructure
```

### Description * (≤1,500 characters — this is 958 chars)
```
ONEON is a decentralized identity and communications protocol that extends ENS names from address resolution into a full sovereign identity stack. Every ONEON identity is rooted in an ENS name — your .eth name becomes the cryptographic seed for a portable, censorship-resistant identity profile.

We are building four open-source ENS integration points:
(1) ENS as the ONEON identity anchor — .eth name as cryptographic root of identity
(2) Extended text record schema — open spec for mesh node endpoint, communications public key, contribution attestations, and reputation anchors
(3) CCIP-Read resolver (EIP-3668) — any ENS lookup silently extends into the ONEON identity layer, zero-change for existing ENS tooling
(4) Subname delegation — community namespaces with governed subname registries

The result: every ENS name becomes the entry point to a censorship-resistant, mesh-networked communications layer. ONEON builds the extension layer that makes ENS as fundamental as DNS, but sovereign. Released as public goods.
```

### Github *
```
https://github.com/my3ye
```
*(Note: If ONEON has its own repo by submission time, use that URL instead)*

### Email address *
```
admin@otto.lk
```

### Project or personal Twitter *
```
https://x.com/my3ye
```
*(Or use the ONEON-specific Twitter if created)*

### Telegram handle *
```
@my3ye
```
*(Or Mev's personal Telegram handle)*

### Showcase Video URL (optional)
```
[Leave blank — or record a 2-min Loom walkthrough of the ONEON concept if possible]
```

---

## MILESTONES

Add these 4 milestones on the form. Total: **$25,000 USDC**

---

### Milestone 1

**Milestone Description** (≤1,500 chars)
```
ONEON CCIP-Read ENS Resolver — Open-source EIP-3668 resolver contract that extends any ENS lookup into the ONEON identity layer with zero-change integration for existing ENS tooling and applications.
```

**Detail of Deliverables** (≤1,500 chars)
```
- Solidity CCIP-Read resolver contract (open-source, audited, MIT licensed)
- Deployed on Ethereum mainnet and Sepolia testnet
- Full technical documentation covering architecture, deployment, and integration
- Integration guide for ENS-compatible applications (step-by-step, with code examples)
- Test suite with 80%+ coverage
- Reference deployment URL + verified contract on Etherscan
```

**Budget:** `$10,000`

**Deadline:** *(Set to 8 weeks from application submission date)*

---

### Milestone 2

**Milestone Description** (≤1,500 chars)
```
ENS Text Record Schema Specification — Open schema defining ENS text record fields for ONEON: mesh node endpoint, communications public key, contribution attestations, and ecosystem reputation anchors.
```

**Detail of Deliverables** (≤1,500 chars)
```
- Published EIP-style schema specification document (public, versioned, open for community feedback)
- TypeScript/JavaScript reference implementation library (npm published, MIT licensed)
- Integration examples for 3 ENS-compatible applications
- Schema validator tool (CLI + web interface)
- Forward-compatibility design notes for future ENS text record expansions
```

**Budget:** `$6,000`

**Deadline:** *(Set to 10 weeks from application submission date)*

---

### Milestone 3

**Milestone Description** (≤1,500 chars)
```
ONEON People Chain Alpha Deployment — Deploy ONEON identity and attestation primitives on Ethereum + a Polkadot People Chain environment, making sovereign identity portable across ecosystems.
```

**Detail of Deliverables** (≤1,500 chars)
```
- Smart contracts for ONEON identity creation, attestation issuance, and identity retrieval (Ethereum)
- Cross-chain identity resolver enabling ENS names to anchor identities across chains
- Testnet deployment with 100+ onboarded test identities
- Public-facing alpha dashboard (web app) demonstrating identity creation via .eth name
- Architecture documentation explaining cross-chain identity model
```

**Budget:** `$6,000`

**Deadline:** *(Set to 12 weeks from application submission date)*

---

### Milestone 4

**Milestone Description** (≤1,500 chars)
```
Developer Documentation + ENS Integration Guide — Comprehensive developer documentation site covering ONEON architecture, all ENS integration patterns, and step-by-step guides for building on ONEON.
```

**Detail of Deliverables** (≤1,500 chars)
```
- Complete developer documentation site at docs.oneon.ink
- 3 integration tutorials (Quick Start, CCIP-Read integration, Text Record schema usage)
- Quickstart guide: from ENS name to full ONEON identity in <10 minutes
- ENS compatibility test suite (automated, runnable by any developer)
- Contribution guide for the open-source ONEON protocol
```

**Budget:** `$3,000`

**Deadline:** *(Set to 14 weeks from application submission date)*

---

## SUPPORTING CONTEXT (for Mev's reference — not a form field)

### Why this will be approved
- ENS grants specifically fund "extension of ENS into application-layer identity" — this is the textbook case
- The 4 integrations (resolver, text records, CCIP-Read, subnames) use ENS primitives exclusively — not a tangential project
- $25K is mid-range within the $12K–$50K window — credible ask, not greedy
- Open-source + public goods framing is exactly what the Public Goods Working Group funds
- Rolling program — no deadline to miss, apply today

### Expected timeline to review
- 2–4 weeks for initial steward review
- If selected: milestone disbursements on completion (4–8 weeks to first $10K)

### Reference: 1-pager
Full narrative at: ~/otto/projects/capital/oneon_ens_1pager.md

---

*Prepared by Otto — 2026-03-27. Mev: connect wallet at builder.ensgrants.xyz and submit.*

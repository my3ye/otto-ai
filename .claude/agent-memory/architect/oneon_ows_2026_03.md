---
name: oneon_ows_integration_2026_03
description: ONEON identity layer × OpenWallet Standard compatibility assessment — which OWS interfaces to adopt, gaps to build, and integration path
type: project
---

OWS fits as ONEON's signing core (keys, multi-chain, policy-gated delegation) but NOT as its identity layer. DID/VC/Memory Capsule must be built above it.

**Why:** OWS has no DID or VC support. Key material (secp256k1, Ed25519) is DID-compatible, so did:oneon can be derived from OWS vault keys directly. Thin `oneon.sign()` adapter is the critical seam.

**How to apply:** Use OWS for Phase 1 (signing, agent tokens, custodial). Build DID+VC layer in Phase 2. Memory Capsule in Phase 3. Never deep-couple ONEON DID layer to OWS internals — always go through adapter.

Full design: ~/otto/docs/oneon-ows-compatibility-2026-03-23.md

Key decisions:
- OWS as signing core only — not identity core
- did:oneon derived from OWS BIP-44 key (no separate DID key)
- Level 1 custodial = platform wraps OWS vault, issues agent tokens
- Level 3 sovereign = user runs OWS vault locally with passphrase
- veramo.io recommended for W3C VC-DATA-MODEL integration
- ONEONIdentityRegistry.sol on EVM L2 (Optimism/Base)
- Shamir 3-of-5 social recovery required before Level 3 is reachable

Gaps: DID namespace, VC stack, Memory Capsule, social recovery, on-chain revocation registry.
Risks: OWS spec instability (mitigated by adapter), local-first incompatible with web users (mitigated by custodial layer).

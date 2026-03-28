---
name: ONEON Invisible Web3 Layer
description: Architecture for ONEON's invisible Web3 infrastructure — ERC-4337 smart accounts, session keys, Base L2, XMTP messaging, W3C VCs as achievements. Three-tier progressive sovereignty.
type: project
---

ONEON Invisible Web3 Layer architecture designed (2026-03-28). Three-tier progressive abstraction (custodial→self-sovereign→sovereign) where Web3 is an implementation detail, not a prerequisite.

**Why:** Mev directive — anyone can participate, not just technical/Web3 people. Every existing solution (ENS, XMTP, Lens, Farcaster, Polkadot People Chain) requires users to already be in Web3.

**How to apply:**
- Phase 0 DONE: 5 Python modules (identity, governance, did, spec, __init__), 12 API endpoints, migration 069
- Phase 1A ($4-5): migration 080, auth.py (magic link), invisible.py (counterfactual accounts, action executor), credentials.py, ~10 new endpoints
- Phase 1B ($6-8): Foundry contracts (ONEONAccountFactory, ONEONPaymaster, ONEONRegistry, ONEONCredentials, ONEONSessionKey) on Base L2
- Phase 1C ($5-7): XMTP messaging integration, oneon-web frontend evolution
- Key decisions: ERC-4337 over Privy/Dynamic (sovereignty), Base L2 (cheapest OP Stack), lazy account creation, session keys for Tier 1, XMTP over Waku (production-ready)
- CRITICAL: migration must be 080+ (078=a2a_messages, 079=failure_branch_adaptations already exist)
- Full spec at ~/otto/docs/oneon-invisible-web3-layer-architecture-2026-03-28.md

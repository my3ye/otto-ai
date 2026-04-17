---
name: Midnight × ONEON synthesis validation
description: Research synthesis validation for Midnight Network × ONEON opportunity analysis (2026-03-31, WF Step 2). NEEDS_CHANGES 7.5/10. ZK gap verified independently. 4 criticals: source count (5→8 web unexplained), "only viable" overclaim, unsourced grant range, Aztec single-source.
type: project
---

Midnight × ONEON synthesis (WF Step 2, 2026-03-31): NEEDS_CHANGES (7.5/10).

**Why:** Core strategic conclusion (ONEON × Midnight complementarity) is sound. ZK gap claim independently verified via codebase grep (oneon.py, invisible.py, oneon-web/app — all clean). 4 critical issues block publish-readiness.

**4 Criticals:**
1. Source count: synthesis says "8 web" but raw retrieval header says "Web: 5" — 3 unexplained sources
2. "Only viable production ZK-programmable privacy chain" overclaim — Mina/Aleo also on mainnet; correct to "compliance-native" qualifier
3. Grant range "$10K–$50K typical" has no Midnight-specific source — pure speculation
4. Aztec vulnerability "2 sources" is actually 1 — web source was stored to memory, not independent

**Verified correct:**
- ONEON ZK gap (independently grepped: zero matches for zk/shielded/kachina/selective in all 3 ONEON codebases)
- 9.6B NIGHT math (40% × 24B = correct)
- Mainnet March 30 2026, NIGHT on Binance/Kraken/OKX
- 4-primitive ONEON gap claim

**Pattern to remember:** Research syntheses frequently cite memory-derived facts as independent "web sources" — memory entries stored FROM web sources are not separate sources. Always cross-check source count claims vs. raw retrieval header.

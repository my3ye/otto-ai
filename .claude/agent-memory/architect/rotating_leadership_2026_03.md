---
name: rotating_leadership_protocol
description: Open-Path Rotating Leadership Protocol — 3-tier governance (councils/assembly/guardians), DPC-weighted sortition, anti-capture safeguards, 6 smart contracts
type: project
---

Open-Path Rotating Leadership Protocol designed (2026-03-27). Three governance tiers with DPC-gated rotation.

**Why:** Mev directive — "no leaders, but anyone has a clear path to become one." Pure rotation cycles elites (research confirmed from 29 sources). DPC-weighted sortition solves this.

**How to apply:**
- All 505 Systems governance designs must reference this protocol
- Council selection uses `dpc^0.7` sub-linear weighting (not linear — prevents top-scorer dominance)
- Emergency powers always 72h auto-expiry (EmergencyModule.sol)
- Founding veto sunset is autonomous on-chain timer (FounderSunset.sol)
- Pending Mev decision: pure DPC-weighted sortition vs 60/40 split (DPC-weighted + equal-random)
- Full spec at ~/otto/docs/open-path-rotating-leadership-architecture-2026-03-27.md

**Key numbers:** 18 Tier 1 seats (4 councils, 90d terms), 7 Tier 2 seats (180d), 5 Tier 3 seats (365d). Min DPC: 500/2000/5000. Max 2 terms/year. Mandatory cooldowns.

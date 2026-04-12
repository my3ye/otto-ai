---
name: Quantum Reputation Synthesis Validation (2026-04-12)
description: Quantum attack vectors on on-chain reputation systems (WF Step 2): MINOR_CHANGES 7.5/10. Critical: Iceberg mislabeled as W3 (recurring); CONFIG_ROLE/setRegistry() missing from attack taxonomy; "6 vectors" vs 8 listed. Code claims otherwise verified.
type: project
---

**Quantum reputation attack synthesis (2026-04-12, WF Step 2): MINOR_CHANGES 7.5/10**

3 criticals:
1. "Iceberg Feb 2026 (<100K RSA-2048)" in Insight 2 attributed W3/M1/M4/M5 — W3=Wheatstones Medium, which has no Iceberg data. Iceberg flows from M1 (prior semantic memory). Same mislabeling pattern as quantum crypto synthesis (2026-04-11). Recurring: fix citation to "W3 (Google timeline), M1 (Iceberg timeline)."
2. CONFIG_ROLE / GovernanceWeight.setRegistry() missing from attack taxonomy — confirmed in GovernanceWeight.sol:75. CONFIG_ROLE can swap the entire registry to a fake one (prior OPRLP audit Finding C3). More severe than VALIDATOR_ROLE capture (Insight 4). Should be Attack Vector 9.
3. Attack vector count mismatch: Action 2 says "6 novel attack vectors" but synthesis lists 8. Grant submission embarrassment.

2 warnings:
1. DPCRegistry.sol line number off by 1: synthesis cites ":16" but mapping is on line 17 (line 16 = natspec comment).
2. W3 (Wheatstones Medium blog) is secondary source for "~9 minutes" — not the original Google paper.

Code claims verified correct:
- DPCRegistry.sol:17 mapping(address => DPCScore) private _scores ✓
- VALIDATOR_ROLE via AccessControl ✓
- updateScore/batchUpdateScores gated on VALIDATOR_ROLE only ✓
- GovernanceWeight formula = sqrt(DPC) * activityMultiplier ✓
- No ML-DSA/FALCON/SPHINCS+ in src/core/ ✓

**Why:** Iceberg source label is a recurring synthesis bug (now 2nd instance). CONFIG_ROLE gap was in prior OPRLP audit but not carried into the quantum threat taxonomy.
**How to apply:** Always grep for setRegistry/swap patterns in governance contracts when reviewing attack taxonomies. Check source numbers against raw findings section when "Iceberg" or vendor-named papers appear.

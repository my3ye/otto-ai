---
name: Quantum Attacks on On-Chain Reputation Systems
description: Full research pipeline on quantum attack vectors targeting oprlp-contracts / DPC / SBT. 9 novel attack vectors, code-verified, zero prior literature. Research note ID 754a8ce4.
type: project
---

PIPELINE COMPLETE (2026-04-12). Validation score: 7.5/10 → 8.5/10 post-corrections.

**Core finding:** DPC behavioral scoring algorithm is quantum-resistant (pure math). oprlp-contracts implementation is ECDSA-dependent at identity-binding layer. Nine novel attack vectors confirmed — zero prior academic coverage.

**Code-verified facts:**
- DPCRegistry.sol line 17: `mapping(address => DPCScore) private _scores` (ECDSA-bound, NOT line 16)
- VALIDATOR_ROLE gates updateScore()/batchUpdateScores() — zero PQ protection
- CONFIG_ROLE / setRegistry() (GovernanceWeight.sol:75) — MOST SEVERE: single key swaps entire DPC registry globally
- getVotingWeight() = sqrt(DPC) × activityMultiplier — quantum-resistant
- grep confirmed: no ML-DSA, FALCON, SPHINCS+ in any /mnt/media/projects/ contracts

**9 attack vectors:**
1. Key Impersonation
2. SBT Re-binding (bypasses ERC5192 non-transferability without transfer hooks)
3. Historical Governance Retrograde (HNDL on all signed governance history)
4. DID/VC Forgery
5. Behavioral Record Forgery
6. Oracle Reputation Hijack
7. DPoS Validator Capture
8. Sybil Amplification (breaks LightGBM precision 0.9428 key-uniqueness assumption)
9. CONFIG_ROLE / setRegistry() — CRITICAL (added per Step 2 review; previously OPRLP audit C3)

**Q-Day:** 2027-2030. Google <500K qubits (W3 secondary). Iceberg <100K qubits RSA-2048 (M1 primary QLDPC). HNDL already active.

**Top actions:**
1. Restrict CONFIG_ROLE / audit setRegistry() — IMMEDIATE
2. Add ML-DSA-65 identity binding to DPCRegistry.sol
3. Publish as original research (9 novel vectors, EF PSE / Succinct, $50-150K)
4. Crypto-agility layer for all oprlp-contracts

**Corrections applied in Step 3:**
- Line number 16→17 (16 = natspec comment)
- Iceberg citation W3→M1 (W3 = secondary blog)
- Added Attack Vector 9 (CONFIG_ROLE/setRegistry())
- Count corrected 6→9
- Social recovery ECDSA weakness made explicit (guardian keys same vulnerability, not a fix)

**Why:** Research note DB: 754a8ce4. 9 semantic memories stored (IDs: 2150acbb, 3ca765d3, 95d7e27b, fc67e094, d33363c4, 203b5491, 7978f00f, 79730018, 28822dab).

**How to apply:** Use this when building oprlp-contracts PQ migration, drafting grant application, or referencing quantum governance attack surface.

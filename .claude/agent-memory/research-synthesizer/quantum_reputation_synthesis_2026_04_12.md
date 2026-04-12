---
name: quantum_reputation_synthesis_2026_04_12
description: Quantum attack vectors on on-chain reputation systems — DPC/SBT/governance vulnerabilities, novel attack taxonomy, oprlp-contracts code-verified gaps, PQ migration actions
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **All oprlp-contracts governance is quantum-vulnerable at identity-binding layer** — DPCRegistry maps scores to `address identity` (ECDSA-bound wallet key). VALIDATOR_ROLE controlled via OZ AccessControl (msg.sender = ECDSA). GovernanceWeight computes behavioral weights from stored scores — algorithm is PQ-safe, but address→score binding is not. Code-verified: DPCRegistry.sol:16 `mapping(address => DPCScore) private _scores`, AccessControl import confirmed. — **Confidence: HIGH | Sources: C1/C2 code + W1/W2/M3**

2. **Q-Day operational window: 2027–2030; HNDL window already open** — 3 independent papers agree on timeline: Google March 2026 (<500K qubits for ECDLP-256 in ~9 min), Iceberg Quantum Feb 2026 (<100K for RSA-2048), NSA CNSA 2.0 PQ mandatory by Jan 2027. All current on-chain governance votes and DPC scores are being collected now for future decryption. — **Confidence: HIGH | Sources: W3/M1/M4/M5 (4 sources)**

3. **SBT Re-binding Attack is novel and unliteraturized** — Non-transferability at contract layer is bypassed by quantum key extraction (attacker becomes the soul without triggering `_beforeTokenTransfer` hooks). Literature gap confirmed: W1/W2/W6 all explicitly note zero SBT/reputation/governance coverage. Grep: zero ERC5192/soulbound files found in /mnt/media/projects/ (excluding node_modules/lib). — **Confidence: HIGH (first principles + confirmed literature gap) | Sources: W1/W2/W6/derived**

4. **VALIDATOR_ROLE quantum compromise = arbitrary DPC score injection** — Quantum-extracted VALIDATOR_ROLE key → call `batchUpdateScores()` freely. Quantum-extracted identity key → impersonate any participant's governance weight. Code-confirmed: DPCRegistry updateScore() gated only on VALIDATOR_ROLE with zero PQ protection. Single-key role holder = catastrophic single point of failure. — **Confidence: HIGH | Sources: C2 code-verified + derived vector 1 + W1**

5. **Zero PQ crypto in any MY3YE project contracts** — grep: no ML-DSA, FALCON, SPHINCS+, or PQ primitives in /mnt/media/projects/ contract src files. Lucky-penny IGovernor.sol and full oprlp-contracts suite are ECDSA-only. (node_modules/jose hits are JS library noise, not Solidity.) — **Confidence: HIGH (grep-verified) | Sources: C1/C2/grep**

6. **Historical Governance Retrograde is structurally inevitable without PQ migration** — All past ECDSA-signed governance votes, DPC score updates, election results are permanently public blockchain data. HNDL collection is already active (M4). Once Q-Day arrives, adversary can forge entire governance history retroactively. — **Confidence: HIGH | Sources: M4/M1/derived vector 3**

7. **DPC behavioral algorithm survives Q-Day; identity binding does not** — `getVotingWeight()` computes `sqrt(DPC) * activityMultiplier` — pure math, no crypto ops. The SCORING MODEL is quantum-resistant. The ADDRESS→SCORE mapping and role access control are not. Migration path is additive: keep algorithm, replace key binding with ML-DSA-65. — **Confidence: HIGH (code-verified) | Sources: C2/M2/M3**

8. **Sybil amplification: quantum + LightGBM sybil detection gap** — Quantum makes all historical public keys (block explorer, mempool) available for identity cloning. M8 sybil model (precision 0.9428) assumes key ≠ identity forgery — assumption fails post-Q-Day. — **Confidence: MEDIUM | Sources: M8/derived vector 8**

---

## Contradictions / Uncertainties

- **"DPC is architecturally quantum-resistant" (M2/M3) vs. code reality**: Partially correct. Weight CALCULATION is PQ-safe; identity BINDING (address→score) is ECDSA-dependent. Quantum key extraction fully impersonates any identity. Claim needs qualification before publication.
- **Social recovery as SBT mitigation (W6)**: Guardian keys are themselves ECDSA-bound. Social recovery addresses loss/theft, not quantum key derivation. Same vulnerability as the problem it solves.
- **W5 blocked (PQ ZK VC paper, eprint.iacr.org/2022/1297)**: Lattice-based ZK credential schemes — content not retrieved. Gap in mitigation coverage.

---

## Recommended Actions (top 3)

1. **Add PQ identity binding to DPCRegistry.sol** — Replace `address` keys with ML-DSA-65 derived identifiers per M3 architecture. Gate `updateScore()`/`batchUpdateScores()` on PQ-verified signatures + VALIDATOR_ROLE. Expected impact: closes identity-binding quantum gap while preserving behavioral weight algorithm entirely.

2. **Publish original research: "Quantum Attacks on On-Chain Reputation Systems"** — Confirmed literature gap (W1/W2/W6). Document: key impersonation, SBT re-binding, historical retrograde, oracle hijack, DPoS capture, sybil amplification. Submit to EF PSE or Succinct grants (per zk_grants_launchpad_synthesis). Expected impact: first published taxonomy of this attack class; $50–150K grant potential; SOS Systems research credibility.

3. **Implement crypto-agility layer for oprlp-contracts** — Algorithm registry per M3 architecture: (Phase 1) audit all ECDSA dependencies in DPCRegistry/GovernanceWeight/CouncilManager/ElectionEngine, (Phase 2) parallel PQ signing, (Phase 3) cutover. Expected impact: future-proofs all governance contracts for Q-Day without redeployment.

---

## Evidence Quality Assessment

Coverage: **PARTIAL** — Strong on threat timeline, attack primitives, and codebase gaps. Weak on PQ-reputation mitigation implementations (W5 blocked) and existing quantum-resistant reputation systems in production.
Source reliability: **HIGH** — 3 arxiv/MDPI papers, NSA policy, Google research, NSS mandate, code-verified oprlp-contracts.
Gaps: (1) W5 PQ ZK VC paper blocked — lattice-based ZK credential schemes need follow-up retrieval. (2) No existing PQ reputation system to compare against. (3) VALIDATOR_ROLE admin key holder identity not traced in code (who holds the admin key in deployment scripts).

---

## Compressed Handoff

**Threat**: Q-Day 2027-2030. ECDLP-256 broken at <500K qubits (Google March 2026, 3 papers agree). HNDL window open now.

**oprlp-contracts confirmed ECDSA-dependent**: DPCRegistry (address→score mapping, VALIDATOR_ROLE via AccessControl), GovernanceWeight (reads address-keyed scores), CouncilManager/ElectionEngine (governance ops). No PQ crypto found anywhere in project contracts (grep-verified).

**Novel attack taxonomy** (not in literature — W1/W2/W6 confirm zero prior coverage):
- Key Impersonation → forge governance votes + steal accumulated DPC weight
- SBT Re-binding → quantum extract key → become the soul without contract violation
- Historical Governance Retrograde → fabricate full voting history via HNDL
- VALIDATOR_ROLE Capture → arbitrary DPC score injection via `batchUpdateScores()`
- DPoS Validator Capture → governance weight seizure in reputation-weighted consensus
- Sybil Amplification → all historical public keys become clone templates

**Key nuance**: DPC behavioral ALGORITHM (sqrt(DPC) * activityMultiplier) is quantum-resistant. The ADDRESS→IDENTITY BINDING is not. Migration is additive — keep algorithm, replace binding.

**PQ migration stack** (M3): ML-DSA-65 (identity), FN-DSA-512 (on-chain ops), STARKs (ZK), crypto-agility layer. Estimated $28-40K, 22 weeks.

**Production PQ precedent**: Algorand FALCON State Proofs (Sep 2022, only major L1 in production), Solana ML-DSA testnet Dec 2025, QANplatform Jul 2026 target.

**P0 actions**: (1) PQ identity binding to DPCRegistry, (2) publish novel attack taxonomy as research paper (grant eligible), (3) crypto-agility layer on oprlp-contracts.

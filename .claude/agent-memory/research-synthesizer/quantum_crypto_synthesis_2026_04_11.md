---
name: quantum_crypto_synthesis_2026_04_11
description: Quantum cryptography threat landscape 2026 — Q-Day acceleration, NIST PQC standards, blockchain exposure, zkPresence implications, and content opportunity
type: project
---

## Key Insights (ranked by confidence × actionability)

1. **Q-Day timeline collapsed 20-200x in early 2026 via algorithmic gains** — Confidence: HIGH | Sources: 3 (W2 Google, W3 Iceberg Quantum, W3 Google Responsible Disclosure)
   - RSA-2048: 20M qubits (2019) → <100K qubits (Feb 2026, QLDPC codes, Iceberg Quantum)
   - ECDLP-256: 9M → <500K qubits (Google March 2026)
   - Gains are algorithmic, not hardware-scaling — independent of quantum hardware progress
   - Google set 2029 internal migration deadline; Bernstein estimates 3-5 year window

2. **NIST PQC FIPS 203/204/205 are finalized and production-ready NOW** — Confidence: HIGH | Sources: 2 (W1 NIST, W4 FBI/NIST/CISA Year of Quantum Security)
   - ML-KEM (key exchange), ML-DSA (primary signatures), SLH-DSA (hash-based backup)
   - Google Chrome enabled ML-KEM; Microsoft integrated into Azure/Windows
   - First PQ certificates expected 2026; adoption not yet default but path is clear

3. **All secp256k1-based blockchain assets are quantum-vulnerable (wallets + smart contracts)** — Confidence: HIGH | Sources: 4 (W2, W3, W4, M2 codebase-verified)
   - 25% of Bitcoin by value has exposed public keys = immediately attackable
   - Bitcoin mining (SHA-256) = safe; signature scheme = vulnerable
   - ETH, BSC, Solana, all secp256k1 wallets fall in the same threat class
   - Lucky Penny contracts use ECDSA via OpenZeppelin (quantum-vulnerable; verified: `/mnt/media/projects/lucky-penny-contracts/out/ECDSA.sol/`)
   - ecrecover in smart contracts = quantum vulnerable

4. **Ethereum has a concrete 4-fork PQ migration plan; Bitcoin has zero coordinated response** — Confidence: HIGH | Sources: 2 (W5 Ethereum roadmap, W6 Bitcoin no-plan)
   - Ethereum: EIP-8141, BLS → hash-based validator sigs, weekly PQ testnets, pq.ethereum.org live
   - Bitcoin: no roadmap, no funding, no top-dev buy-in — "isolated pieces of research"
   - Divergence creates a strategic inflection: ETH credibility compounds, BTC exposure narrative grows

5. **zkPresence (otto) uses quantum-vulnerable cryptography at two levels** — Confidence: HIGH | Sources: codebase-verified
   - **SP1 Groth16 prover = BN254 pairing-based** (quantum-vulnerable long-term): confirmed at `zkpresence/contracts/src/ZkPresence.sol` L8,91
   - **ECDSA secp256k1 circuit = stubbed with `todo!()`** (not yet implemented): confirmed at `zkpresence/crates/circuit/src/main.rs` L26,67,70,104,121
   - Current stub status is a SHORT-TERM SHIELD (ECDSA not wired = not vulnerable today) but a blocker for OSS launch
   - Mitigation path: wire ECDSA now (required for functionality) + plan SP1 STARK migration when available
   - No PQC libraries installed anywhere in Otto codebase (grep: kyber/dilithium/ml-kem/ml-dsa → zero non-doc hits)

6. **2027-2030 practical attack window is multi-source consensus** — Confidence: HIGH | Sources: 3 (W2, W3, W4)
   - Current SOTA hardware: ~1,000-2,000 physical qubits (IBM/Google)
   - Gap to threat: 50-500x hardware scaling still needed BUT rate of improvement is accelerating
   - 2026 = "Year of Quantum Security" (FBI, NIST, CISA designation) — regulatory pressure imminent

7. **QKD = physics-guaranteed but niche; PQC = deployable everywhere** — Confidence: MEDIUM | Sources: 1 (W7)
   - ID Quantique (IonQ), QuantumCTek, Verizon trialing QKD in critical/gov networks
   - EU Eagle-1 satellite QKD target: late 2026 / early 2027
   - Range limit ~100km fiber; cost = prohibitive for mass market
   - Industry consensus: PQC for everything, QKD only for highest-sensitivity corridors

---

## Contradictions / Uncertainties

- **Template variables unfilled**: Task dispatched with literal `{topic}` and `{scope}` unresolved. Topic inferred as "quantum cryptography landscape 2026" from workflow title. Scope inferred as blockchain-centric. Synthesis proceeds on this inference.
- **Hardware timeline debate**: Bernstein 3-5 years vs Google's explicit 2029 (3 years) — effectively same range, minor framing difference. Resolved: treat 2027-2029 as credible threat window.
- **zkPresence BN254 long-term risk**: SP1's Groth16/BN254 pairing is quantum-vulnerable, but no concrete timeline for pairing-based proof system attacks. Likely safe until post-2030. Not an immediate blocker for OSS launch — flag for roadmap.
- **"Energy of a star" for Bitcoin mining**: W4 claim that quantum mining requires implausible energy is consistent with SHA-256 safety in the algorithm vulnerability map. No contradiction — just a "not the attack vector" clarification.

---

## Recommended Actions (top 3)

1. **Wire zkPresence ECDSA precompile and document post-quantum migration path before OSS launch** — Expected impact: removes the todo!() circuit panic as OSS launch blocker; creates defensible security narrative for grant applications (EF PSE, Succinct); adds PQ migration note to ROADMAP.md as forward-looking risk disclosure. File: `zkpresence/crates/circuit/src/main.rs` (three todo!() stubs at L26,67,70,104,121) + `zkpresence/ROADMAP.md`.

2. **Create a quantum threat content piece for MY3YE/SOS Systems audience** — Expected impact: capitalizes on 2026 "Year of Quantum Security" news cycle; positions MY3YE as technically credible on emerging threats; natural audience = builders, validators, protocol designers. Angle: "The Clock Is Already Running — What Quantum Computing Means for the Networks We're Building." Cite Google 2029 deadline, Ethereum vs Bitcoin divergence, NIST FIPS as deployable NOW.

3. **Add no-address-reuse policy to any MY3YE wallet UX (Koink, Panik, zkPresence)** — Expected impact: free, immediate risk mitigation for users; removes 25% of exposure class; implementable in wallet UI copy and docs before any cryptographic migration is needed. This is Google's own recommendation #1.

---

## Evidence Quality Assessment

Coverage: **PARTIAL** — Strong web coverage (7 sources, 2026 papers, authoritative sources). Zero knowledge graph data (API error). No academic paper storage in implement queue for PQC.

Source reliability: **HIGH** — Sources include NIST official release, Google Research blog, Ethereum Foundation roadmap, CoinDesk citing primary researchers. Algorithmic acceleration backed by named authors (Gidney, Justin Drake, Dan Boneh).

Gaps: (1) No SP1 post-quantum roadmap data — does Succinct plan STARK-native proving? (2) No Ethereum EIP-8141 implementation status (which hard fork? timeline?). (3) No Bitcoin developer sentiment depth beyond "no roadmap." (4) ONEON contract exposure unassessed (zero contracts confirmed in prior synthesis — low priority until contracts exist).

---

## Compressed Handoff (≤1000 tokens)

**Topic**: Quantum cryptography threat landscape 2026 (blockchain-focused). Template vars unresolved; inferred from workflow title.

**Q-Day acceleration** (HIGH, 3 sources): RSA-2048 breakable with <100K physical qubits (Iceberg Quantum, Feb 2026, QLDPC); ECDLP-256 with <500K (Google, March 2026). Gains algorithmic — independent of hardware. Current hardware: ~1-2K qubits. Gap: 50-500x. Practical window: 2027-2030. Google internal deadline: 2029.

**NIST PQC** (HIGH, 2 sources): FIPS 203 ML-KEM, 204 ML-DSA, 205 SLH-DSA — finalized Aug 2024, production-ready. Chrome/Azure/Windows already integrated. First PQ certs expected 2026.

**Blockchain exposure** (HIGH, 4 sources): 25% BTC by value immediately vulnerable (exposed pubkeys). SHA-256 mining safe. All secp256k1 wallets (ETH/BSC/Solana/Koink) in threat class. ecrecover in contracts = vulnerable. Lucky Penny uses ECDSA via OZ (grep-verified).

**Ecosystem divergence** (HIGH, 2 sources): Ethereum = 4-fork PQ roadmap, EIP-8141, BLS→hash-based sigs, weekly testnets. Bitcoin = zero plan, zero buy-in.

**zkPresence exposure** (HIGH, codebase-verified):
- Groth16/BN254 pairing in ZkPresence.sol (L8,91) = quantum-vulnerable long-term (post-2030 risk)
- ECDSA secp256k1 = 3 todo!() stubs in circuit/src/main.rs (L26,67,70,104,121) — NOT wired yet
- No PQC libraries in any Otto code (kyber/dilithium/ml-kem — zero non-doc hits)

**Mitigation hierarchy**: (1) No address reuse (free, immediate), (2) ML-KEM key exchange, (3) ML-DSA signatures, (4) STARKs safer than SNARKs long-term for ZK provers.

**QKD** (MEDIUM, 1 source): Physics-guaranteed but range-limited (~100km), expensive. Niche for gov/critical infra. EU Eagle-1 satellite 2027. PQC = mass deployment path.

**Content signal**: 2026 = "Year of Quantum Security" (FBI/NIST/CISA). Google responsible disclosure used ZK proofs. High-signal moment for MY3YE thought leadership.

**Top 3 actions**: (1) Wire zkPresence ECDSA precompile + add PQ migration note to ROADMAP.md. (2) Publish quantum threat content piece for MY3YE/SOS audience. (3) Add no-address-reuse policy to Koink/Panik/zkPresence wallet UX.

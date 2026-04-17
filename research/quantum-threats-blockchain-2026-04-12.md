# Quantum Threats to Classical Blockchain Cryptography
## Structured Research Findings — April 12, 2026

---

## 1. How Shor's Algorithm Breaks ECDSA/RSA

### The Mathematical Attack Surface

**Classical ECDSA (secp256k1)** — used by Bitcoin, Ethereum, BSC, Solana, and every major blockchain — derives its security from the **Elliptic Curve Discrete Logarithm Problem (ECDLP)**:

```
Given: Public Key Q = k × G  (where G is a generator point, k is private key)
Hard classically: reverse k from Q
Easy quantum: Shor's algorithm solves ECDLP in polynomial time O(n³)
```

**Shor's Algorithm (1994)** solves two problems that underpin all classical public-key cryptography:
- **Integer Factorization** (breaks RSA) — finds prime factors of a large semiprime N
- **Discrete Logarithm** (breaks ECDSA/DH) — recovers exponent from modular/elliptic curve relationship

**Classical complexity**: O(exp(√(log N · log log N))) — exponential, safe  
**Quantum complexity**: O((log N)³) — polynomial, catastrophic

### The Attack Procedure Against a Bitcoin/Ethereum Wallet

1. **Observe** a transaction broadcast containing the sender's public key (exposed in the scriptSig/witness)
2. **Run Shor's Algorithm** on the 256-bit public key to solve ECDLP and recover the 256-bit private key
3. **Forge** a new transaction with a higher fee, redirecting funds to attacker's address
4. **Broadcast** the forged transaction — standard miners/validators accept it as valid
5. **Irreversible** — blockchain's immutability becomes a weapon: no recourse possible

### Exposure Timing Windows

Two attack classes exist depending on quantum clock speed:

| Attack Type | Requires | Time Window | Threat |
|---|---|---|---|
| **On-spend attack** | Fast-clock CRQC (superconducting/photonic) | 9–23 minutes | Any transaction broadcast |
| **At-rest attack** | Slow-clock CRQC (neutral atoms/trapped ions) | Days–weeks | Exposed public keys on-chain |

Bitcoin's 10-minute block time is dangerously close to the 9–23 minute on-spend window for fast-clock architectures. Ethereum's 12-second slot time provides even less protection — but private mempools (Flashbots, etc.) offer partial mitigation.

### Vulnerable vs Safe Components

| Component | Algorithm | Quantum Safe? |
|---|---|---|
| Bitcoin signatures (ECDSA secp256k1) | Elliptic curve DL | **NO** |
| Ethereum signatures (ECDSA secp256k1) | Elliptic curve DL | **NO** |
| `ecrecover` in smart contracts | ECDSA | **NO** |
| Bitcoin mining (SHA-256) | Hash function | **YES** (Grover: 2x speedup only) |
| Ethereum Keccak-256 address derivation | Hash function | **YES** (Grover: 2x speedup) |
| ZK SNARKs (Groth16/BN254 pairings) | Pairing-based crypto | **NO** (long-term risk) |
| ZK STARKs (hash-based FRI) | Hash functions | **YES** |

**Citation**: [How ECC Became the Easiest Quantum Target](https://postquantum.com/post-quantum/shor-rsa-ecc-diffie-hellman/) | [Cambridge Judge Business School](https://www.jbs.cam.ac.uk/2025/why-quantum-matters-now-for-blockchain/)

---

## 2. Timeline Estimates for CRQCs

### 2026: The Year the Timeline Collapsed

Three independent research advances in early 2026 compressed the qubit estimates by 20–200x:

| Event | Date | Finding |
|---|---|---|
| **Iceberg Quantum (QLDPC codes)** | Feb 2026 | RSA-2048 breakable with **<100K physical qubits** (was 20M, 2019) |
| **Google Quantum AI** | Mar 2026 | ECDLP-256 (secp256k1) breakable with **1,200–1,450 logical qubits** (~500K physical) |
| **Alice & Bob** | Mar 2026 | secp256k1 attack possible with ~100,000 cat qubits in ~9 hours |

**Critical insight**: These gains are **algorithmic**, not hardware-scaling. They are independent of quantum hardware progress — even if hardware stalls, the attack complexity has permanently dropped.

### Current Hardware vs. Required Scale

| Milestone | Current (2026) | Required for CRQC |
|---|---|---|
| Physical qubits | 1,000–2,000 (IBM/Google) | ~500,000–1,000,000 |
| Logical qubits (error-corrected) | 30–100 | 1,200–1,450 |
| Error correction overhead | ~1,000:1 ratio | Required |

**Gap**: 50–500x hardware scaling still required. But rate of improvement is accelerating.

### Probabilistic Timeline (Expert Consensus)

| Scenario | Probability | Year |
|---|---|---|
| CRQC breaks secp256k1 | 10% | By 2032 (Justin Drake, Ethereum) |
| CRQC breaks secp256k1 | 20% | By 2030 (Vitalik Buterin) |
| Google internal PQ migration deadline | — | 2029 |
| Daniel Bernstein estimate | — | 2027–2030 window |
| FBI/NIST/CISA "Year of Quantum Security" designation | — | 2026 (current) |

**Conservative consensus**: Practical attack window is **2027–2030**. 2026 is the last year to be "probably safe." Planning horizon is NOW.

**Citation**: [Quantum Computing Report — Decryption Threshold](https://quantumcomputingreport.com/the-decryption-threshold-re-estimating-the-quantum-threat-to-blockchain-infrastructure/) | [Spaziocrypto Q-Day breakdown](https://en.spaziocrypto.com/bitcoin/q-day-quantum-computers-bitcoin-risk-wallets/)

---

## 3. NIST Post-Quantum Standards

### Finalized Standards (Published August 13–14, 2024)

All four algorithms went through a 7-year public competition (2016–2024). Three are finalized FIPS; one (FALCON) is in final drafting.

#### FIPS 203: ML-KEM (Key Encapsulation Mechanism)
- **Based on**: CRYSTALS-Kyber
- **Security assumption**: Module Learning With Errors (MLWE) over structured lattices
- **Use case**: Key exchange, TLS handshakes, VPN session establishment
- **Parameter sets**: ML-KEM-512 (128-bit), ML-KEM-768 (192-bit), ML-KEM-1024 (256-bit)
- **Status**: Production-ready. Google Chrome enabled ML-KEM in TLS. Microsoft Azure/Windows integrated.
- **Blockchain relevance**: Replace ECDH in key exchange; protect off-chain communication

#### FIPS 204: ML-DSA (Digital Signature Algorithm)
- **Based on**: CRYSTALS-Dilithium
- **Security assumption**: Module Learning With Errors + Module Short Integer Solution (MLWE + MSIS)
- **Use case**: General-purpose digital signatures — transactions, code signing, certificates
- **Parameter sets**: ML-DSA-44 (128-bit), ML-DSA-65 (192-bit), ML-DSA-87 (256-bit)
- **Status**: Primary replacement for ECDSA in new systems. Solana testnet using ML-DSA-65.
- **Blockchain relevance**: **Direct ECDSA/secp256k1 replacement** for transaction signing

#### FIPS 205: SLH-DSA (Stateless Hash-Based Digital Signature)
- **Based on**: SPHINCS+
- **Security assumption**: Security of underlying hash functions (SHA-256, SHA-3, SHAKE)
- **Use case**: Backup signature scheme if lattice-based algorithms are broken
- **Key insight**: Hash functions only require Grover speedup (2x), making them the most conservative PQC option
- **Trade-off**: Larger signatures (~8KB vs ~2.4KB for ML-DSA); slower
- **Blockchain relevance**: Validator/consensus signatures; high-security long-term storage

#### FIPS 206 (Draft): FN-DSA (FALCON)
- **Based on**: FALCON lattice signatures (FFT over NTRU lattice)
- **Security assumption**: NTRU lattice problems
- **Use case**: Space-constrained environments; compact signatures (~666 bytes)
- **Status**: Draft FIPS 206; not yet final
- **Notable adopter**: Algorand — State Proofs on mainnet since September 2022 (before finalization)
- **Blockchain relevance**: Efficient on-chain signature verification; lower gas cost per signature

### Deployment Status 2026

| Adopter | Standard | Status |
|---|---|---|
| Google Chrome | ML-KEM | Enabled in TLS by default |
| Microsoft Azure/Windows | ML-KEM + ML-DSA | Integrated |
| First PQ X.509 certificates | ML-DSA | Expected 2026 |
| US Federal agencies | All FIPS 203/204/205 | Mandated migration by 2030 |

**Citation**: [NIST FIPS Announcement](https://www.nist.gov/news-events/news/2024/08/nist-releases-first-3-finalized-post-quantum-encryption-standards) | [CSRC PQC Standards](https://csrc.nist.gov/news/2024/postquantum-cryptography-fips-approved)

---

## 4. Existing Post-Quantum Blockchain Projects

### Two Migration Philosophies

**Philosophy A: Hash-Based Pioneers** — Use proven hash-based signatures from inception; prioritize long-term security over performance  
**Philosophy B: Lattice Adopters** — Start classical, migrate to lattice-based PQC while maintaining high throughput

---

### Detailed Project Analysis

#### QRL — Quantum Resistant Ledger
- **Mainnet**: Live since June 26, 2018 — the first production PQ blockchain
- **Signature scheme**: XMSS (eXtended Merkle Signature Scheme) → transitioning to SPHINCS+
- **QRL 2.0 Testnet V2**: Launched March 31, 2026 — introduces **Hyperion** (PQ Solidity dialect) + QRVM (EVM fork)
- **Consensus**: Proof-of-Stake (Project Zond)
- **TPS**: 7–20 (base); hardware wallet (Ledger) support in testing
- **Weakness**: Low TPS, small ecosystem, niche market
- **Security audit**: Independent audit in progress for 2.0 mainnet
- **Citation**: [QRL 2.0 Testnet V2 press release](https://www.theqrl.org/press/qrl-launches-testnet-v2-for-its-postquantum-evmfriendly-blockchain/)

#### IOTA
- **Original design (2016)**: Winternitz one-time signatures (hash-based, Shor-resistant) on Tangle DAG
- **Chrysalis (April 2021)**: Switched to Ed25519 for UX; **quantum safety temporarily abandoned**
- **IOTA 2.0 (Coordicide)**: Returns to hash-based signatures, removes central Coordinator node; DevNet live June 2021
- **TPS**: Up to 1,000 TPS on DevNet; feeless architecture
- **Use case**: Machine-to-machine payments (IoT); Jaguar Land Rover, EU grid pilots
- **Citation**: [Quantum Secure Crypto comparison](https://www.amarchenkova.com/posts/quantum-secure-cryptocurrencies-qrl-mochimo-iota-cardano)

#### Algorand
- **PQ implementation**: FALCON (FN-DSA) lattice signatures for **State Proofs** — live on mainnet since September 7, 2022
- **Current status**: Only major L1 with PQC signatures in production
- **TPS**: 6,000 TPS; sub-4-second finality maintained with PQ sigs
- **Migration strategy**: Staged rollout — consensus upgrade separately from user accounts
- **Notable**: CBDC pilots deployed; institutional-grade quantum posture
- **Weakness**: User account signatures still classical; full migration incomplete

#### Solana
- **PQ implementation**: CRYSTALS-Dilithium (ML-DSA) replacing Ed25519
- **Public testnet**: Launched December 16, 2025; ~3,000 TPS with larger keys demonstrated
- **Mainnet target**: Dual-key rollout before December 2026 (on-chain referendum required)
- **Wallet support**: Phantom and Ledger in developer builds
- **Client**: Firedancer (2026) supports multiple signature backends
- **Challenge**: Signature size increase (~2.4KB vs 64 bytes for Ed25519) affects bandwidth/storage

#### QANplatform
- **Signature scheme**: ML-DSA-65 (Dilithium) replacing ECDSA
- **Cross-chain signer**: XLINK — binds existing ECDSA keys to PQ twins; MetaMask-compatible
- **Mainnet target**: July 2026; Ledger firmware support planned
- **TPS**: 900–1,200 TPS at sub-second finality
- **Audit**: November 2025 Hacken audit — no cryptographic flaws found
- **Key differentiator**: No new mnemonics required for migration; Solidity contracts work unchanged via XLINK

#### Ethereum (Migration in Progress)
- **4-fork PQ migration roadmap**: EIP-8141 → BLS → hash-based validator sigs → user account migration
- **Active resources**: pq.ethereum.org live; weekly PQ testnets active
- **Timeline**: Long-running process; no finalized hard fork date
- **Vulnerability**: All existing user wallets remain ECDSA until migration completes

#### Bitcoin (No Coordinated Plan)
- **Status**: Zero coordinated PQ roadmap; "isolated pieces of research"
- **April 2026 development**: Quantum-safe Bitcoin transactions possible without soft fork at **$200/transaction** (recent CoinDesk research)
- **Exposure**: ~1.7 million BTC in legacy P2PK wallets with permanently exposed public keys
- **Developer position**: No top-developer consensus on migration path
- **Citation**: [Chaincode Bitcoin Post-Quantum PDF](https://chaincode.com/bitcoin-post-quantum.pdf) | [CoinDesk Bitcoin quantum race](https://www.coindesk.com/tech/2026/04/04/bitcoin-s-usd1-3-trillion-security-race-key-initiatives-aimed-at-quantum-proofing-the-world-s-largest-blockchain)

---

## 5. Hybrid Classical + PQC Approaches

### Why Hybrid?

PQC algorithms are newer and have less deployment history than ECDSA/RSA. Hybrid approaches provide **defense-in-depth**: an adversary must break BOTH classical AND post-quantum cryptography simultaneously. Widely recommended as the migration strategy through 2030.

### Hybrid Signature Architecture

**Dual-signing**: Transactions carry both a classical signature (ECDSA/Ed25519) AND a post-quantum signature (ML-DSA/FN-DSA).

```
Transaction signature = ECDSA(secp256k1) || ML-DSA-65
Validity = ECDSA_valid AND ML-DSA_valid
```

This is the approach documented in the [Preprints.org hybrid protocol paper](https://www.preprints.org/manuscript/202509.2079) for Bitcoin and Ethereum protocol-level integration.

### Hybrid Key Encapsulation

For key exchange (TLS, off-chain communication):
```
Shared_secret = KDF(ECDH_secret || ML-KEM_secret)
```
If either is broken, security degrades gracefully rather than catastrophically.

### Research: Distributed Key Generation + Hybrid Quantum/PQC

A [Nature/Scientific Reports paper (2025)](https://www.nature.com/articles/s41598-025-23310-6) proposes removing single points of trust via:
- Distributed Key Generation (DKG) across multiple parties
- Dual-layer signatures: quantum digital sigs (Fully Flipped Permutation problem) + classical PQC lattice sigs
- Users can switch signature type based on security requirements/channel conditions

### Practical Hybrid Migration Sequence (Recommended)

| Phase | Action | Cost | Immediate? |
|---|---|---|---|
| **Phase 0** | Stop address reuse (never reuse a Bitcoin/ETH address) | Free | Now |
| **Phase 1** | Adopt ML-KEM for all new key exchange | Low | Now |
| **Phase 2** | Hybrid dual-signing on new transactions | Medium | 2026 |
| **Phase 3** | Full ML-DSA signature migration | High (network upgrade) | 2027–2028 |
| **Phase 4** | Migrate dormant at-risk wallets | Very high (user action) | Ongoing |

### Crypto-Agility Principle

Design systems with algorithm abstraction layers so signature schemes can be hot-swapped without breaking existing contracts/protocols. Firedancer (Solana) and QANplatform's XLINK both implement this.

**Citation**: [Nature Hybrid Blockchain Paper](https://www.nature.com/articles/s41598-025-23310-6) | [QuantumXC 2026 Predictions](https://quantumxc.com/blogs-podcasts/quantum-predictions-it-network-infrastructure/) | [ScienceDirect Survey](https://www.sciencedirect.com/science/article/pii/S1574013725001224)

---

## 6. The Value/Trust Collapse Scenario

### Threat Taxonomy: Three Distinct Attack Scenarios

#### Scenario A: The "Harvest Now, Decrypt Later" (HNDL) Attack
**Active today**. Nation-state actors are capturing blockchain transactions NOW to decrypt them when CRQCs are available.

- On-chain transactions are **permanently public** — unlike encrypted communications, blockchain data never expires
- Any wallet that has ever broadcast a transaction has a permanently exposed public key
- **1.7 million BTC** (~$85–130B depending on price) in P2PK addresses have permanently visible public keys
- The Federal Reserve's own research paper ["Harvest Now, Decrypt Later: Examining Post-Quantum Cryptography and the Data Privacy Risks for Distributed Ledger Networks"](https://www.federalreserve.gov/econres/feds/harvest-now-decrypt-later-examining-post-quantum-cryptography-and-the-data-privacy-risks-for-distributed-ledger-networks.htm) explicitly flags this for DLT networks

#### Scenario B: The "Q-Day Drain" (Acute Collapse)
When a CRQC first becomes capable:

1. **First hours**: A secret actor (nation-state, criminal, insider) drains highest-value exposed wallets
2. **Discovery**: Attack detected when large-scale unauthorized transfers appear
3. **Panic selling**: News spreads; Bitcoin/ETH crater in value as trust in immutability collapses
4. **Irreversibility**: Unlike traditional finance, no SWIFT recall, no bank reversal, no insurance
5. **Cascade**: Smart contract exploits follow — `ecrecover` in DeFi protocols becomes the attack surface
6. **Fork or die**: Chains must emergency-fork to a PQ scheme under extreme time pressure with no consensus

**Bitcoin's critical vulnerability**: Bitcoin's blockchain offers NO recourse against fraudulent transactions. A single forged valid ECDSA signature transfers coins permanently.

#### Scenario C: The "Selective Targeting" Attack (Subacute)
More likely than Scenario B for the early CRQC period:

- Early CRQCs may be capable but expensive (millions per attack)
- Nation-states target high-value wallets: exchange cold wallets, Satoshi's coins, protocol treasuries
- Targeted attacks create uncertainty and price pressure without triggering full panic
- The "is this ECDSA or quantum?" ambiguity makes attribution difficult

### Quantified Exposure (2026)

| Asset Class | Exposure Type | Value at Risk |
|---|---|---|
| BTC in P2PK wallets (Satoshi era) | Public key permanently exposed | ~1.7M BTC (~$100B+) |
| BTC in reused P2PKH addresses | Public key exposed on first spend | ~25% of total BTC value |
| ETH in reused accounts | Most ETH accounts (high reuse) | Majority of $~300B+ ETH market cap |
| DeFi ecrecover contracts | All ecrecover-dependent protocols | Unknown, multi-billion |
| Algorand mainnet | FALCON-protected | **Immune** |

### The Trust Architecture Collapse

Beyond pure value, the deeper risk is **trust infrastructure**:

1. **Smart contracts as law**: Entire DeFi stack ($50B+ TVL) assumes ECDSA = identity. If ECDSA is broken, ownership becomes ambiguous.
2. **Governance attacks**: DAOs using token-weighted voting via wallets — quantum attacker can forge governance votes
3. **Bridge exploits**: Cross-chain bridges use ECDSA multisig. A CRQC can drain any bridge.
4. **NFT/deed ownership**: If private keys are derivable, all "ownership proofs" become contestable.
5. **Behavioral trust vs cryptographic trust**: Systems like SOS Systems DPC (contribution-history-based governance weight) are **architecturally quantum-resistant** because governance weight derives from verified behavioral record, NOT key possession.

### Bitcoin's Unique Political Problem

Unlike Ethereum, Bitcoin has no foundation and no benevolent dictator. A PQ migration requires:
- Soft fork (if possible) or hard fork (contentious)
- Global miner consensus
- Exchange + wallet provider upgrades
- User wallet migration (billions of UTXOs)

April 2026 research shows quantum-safe Bitcoin WITHOUT a soft fork is technically possible at **$200/transaction** — but economically prohibitive at scale.

### Mitigation Effectiveness Table

| Mitigation | Protects Against | When to Implement |
|---|---|---|
| Stop address reuse | On-spend attacks (Scenario B) | Now, free |
| Move to new address (never spent) | At-rest attacks (Scenario C) | Now, free |
| Network-level ML-DSA migration | All scenarios | 2027–2029 (network-dependent) |
| Emergency fork post-Q-Day | Scenario B aftermath | Last resort |

**Citation**: [Federal Reserve HNDL Paper](https://www.federalreserve.gov/econres/feds/harvest-now-decrypt-later-examining-post-quantum-cryptography-and-the-data-privacy-risks-for-distributed-ledger-networks.htm) | [CoinTelegraph Quantum 2026 Reality Check](https://cointelegraph.com/news/quantum-computing-in-2026-no-crypto-doomsday-time-to-prepare) | [Palo Alto Networks HNDL](https://www.paloaltonetworks.com/cyberpedia/harvest-now-decrypt-later-hndl)

---

## Summary Table: Quantum Threat to Blockchain

| Dimension | Finding | Confidence | Source |
|---|---|---|---|
| Shor's algorithm breaks ECDSA | Polynomial time, ~1,200 logical qubits | HIGH | Google Research Mar 2026 |
| CRQC attack window | 9–23 minutes (fast-clock) | HIGH | Quantum Computing Report |
| BTC mining (SHA-256) | Safe (Grover: 2x only) | HIGH | Multiple |
| Practical CRQC timeline | 2027–2030 | HIGH | Google, Buterin, Bernstein |
| NIST FIPS 203/204/205 | Finalized Aug 2024, production-ready | HIGH | NIST |
| FALCON (FIPS 206) | Final draft, Algorand mainnet already | HIGH | NIST, Algorand |
| BTC exposed P2PK wallets | ~1.7M BTC permanently vulnerable | HIGH | Multiple |
| ETH PQ migration plan | 4-fork plan, pq.ethereum.org active | HIGH | EF |
| BTC PQ migration plan | None, $200/tx workaround only | HIGH | CoinDesk Apr 2026 |
| HNDL for blockchain | Active threat today | HIGH | Federal Reserve |
| QRL 2.0 Testnet | PQ EVM-compatible, live Mar 2026 | HIGH | QRL Foundation |
| Algorand PQC | FALCON State Proofs, mainnet Sep 2022 | HIGH | Algorand |
| Solana PQC testnet | ML-DSA testnet Dec 2025, mainnet 2026 | HIGH | Solana |

---

## Actionable Next Steps for Otto/MY3YE Projects

1. **No address reuse** — enforce in all Koink/Panik/zkPresence wallet UX copy immediately (free, immediate)
2. **zkPresence ROADMAP.md** — add SP1 STARK migration note (Groth16/BN254 pairing-based = long-term risk post-2030)
3. **Content opportunity** — "Quantum Trust and the Value Shift" framing (Pink Paper done). Publish DPC as quantum-resistant governance architecture.
4. **ONEON contract design** — future contracts should avoid `ecrecover` as primary trust mechanism; design for swappable signature verification
5. **SOS Systems DPC** — explicitly market as quantum-resistant: governance weight = behavioral record, not key possession

---

*Research compiled: April 12, 2026*  
*Primary sources: NIST, Google Quantum AI, Ethereum Foundation, Quantum Computing Report, Federal Reserve, QRL Foundation, CoinDesk, witanworld.com*

# ZK Chain Landscape & Proof System Analysis — 2026

> Research date: 2026-04-10  
> Scope: Major ZK chains and rollups — proof systems, EVM compatibility, throughput, finality, decentralization, prover costs, sequencer architecture, and production readiness.

---

## Part 1: Proof System Primer

Before comparing chains, key proof systems in use:

| System | Type | Trusted Setup | Proof Size | Verify Time | Quantum-Resistant | Notes |
|--------|------|---------------|------------|-------------|-------------------|-------|
| **Groth16** | zk-SNARK | Per-circuit ceremony | 192 bytes (smallest) | ~3ms (fastest) | No | Cheapest to verify; inflexible (circuit-specific) |
| **PLONK** | zk-SNARK | Universal (one-time) | <1KB | ~10ms | No | Flexible across circuits; used by Aztec, Mina (Kimchi), Polygon zkEVM |
| **FRI** | IOP (STARK-based) | None | ~100KB | ~50ms | Yes | Basis of STARKs; no trusted setup; large proofs |
| **STARK (FRI-based)** | zk-STARK | None | 100–400KB | ~50ms | Yes | Starknet (CAIRO), transparent, post-quantum |
| **Boojum (STARK)** | zk-STARK | None | Medium | Fast (GPU) | Yes | zkSync Era — GPU-accelerated, 16GB RAM suffices |
| **Halo2 (PLONK-derived)** | zk-SNARK | None (IPA/KZG) | ~1KB | Fast | No | Midnight, Zcash — recursive proofs, no trusted setup |
| **Kimchi (PLONK-derived)** | zk-SNARK | None | Medium | Medium | No | Mina Protocol — recursive, 22KB blockchain size |
| **Varuna (Marlin-based)** | zk-SNARK | Universal | Medium | Medium | No | Aleo — batch amortization, SnarkVM execution |

**2026 cost trend:** Proof costs dropped ~45x in 2025 alone ($1.69 → $0.0376 per proof). zkSync's Airbender prover (successor to Boojum) achieves sub-cent transfer proof costs, >10x improvement over Boojum.

**Gas costs on Ethereum:** Groth16 verification: 200K–300K gas (~$20–60 in congestion). STARK verification more expensive on-chain but proven off-chain.

---

## Part 2: Chain-by-Chain Analysis

### 1. zkSync Era (ZK Stack)
**Developer:** Matter Labs  
**Proof System:** Boojum (STARK-based) → Airbender (2025/2026 upgrade)  
**EVM Compatibility:** Full EVM equivalence (bytecode-level) + native account abstraction  

| Metric | Value |
|--------|-------|
| TPS (Atlas upgrade) | 15,000+ TPS sequencing; 100,000+ TPS theoretical (elastic scaling) |
| Finality (soft) | ~1 second (sequencer confirmation) |
| Finality (hard) | ~3 hours (L1 proof batch settlement) |
| Sequencer | Centralized (Matter Labs); decentralization in progress |
| Prover | GPU-based, 16GB RAM (consumer hardware) |
| L2BEAT Stage | Stage 1 (limited governance) |
| Mainnet status | Live (production) — mature ecosystem |

**Architecture highlights:**
- ZK Stack: framework for building sovereign ZK rollups and validiums ("hyperchains")
- Boojum replaced SNARK-based system in 2023 — reduced hardware req from 80GB → 16GB RAM
- Airbender (2025) cuts proof costs 10x+ beyond Boojum
- 2026 roadmap: Prividium (enterprise privacy layer), RWA tokenization focus
- Native support for Ethereum precompiles + account abstraction

**Decentralization status:** Currently centralized sequencer (Matter Labs). Plans for decentralized sequencer/prover network in ZK Stack ecosystem. Multiple hyperchain operators exist but coordination is still managed.

**Moats:** Largest ZK rollup by TVL; best developer tooling; ZK Stack enables L3s/hyperchains.

---

### 2. Starknet
**Developer:** StarkWare  
**Proof System:** STARK (FRI-based) via Stone Prover  
**EVM Compatibility:** NOT bytecode-equivalent. Native language: Cairo. Solidity via transpilers (Warp), not native.  

| Metric | Value |
|--------|-------|
| TPS | 1,000–100,000+ TPS (theoretical with parallel execution) |
| Finality (soft) | 1–2 seconds (v0.14.0 with decentralized sequencers) |
| Finality (hard) | ~2–4 hours (L1 STARK proof settlement) |
| Sequencer | v0.14.0 (Grinta): decentralized sequencer architecture live |
| Prover | StarkWare-operated (Stone Prover, open-sourced) |
| L2BEAT Stage | Stage 1 |
| Mainnet status | Live (production) — large DeFi/gaming ecosystem |

**Architecture highlights:**
- STARK proofs: no trusted setup, post-quantum secure
- Cairo: a Turing-complete language purpose-built for STARK proving — not EVM bytecode
- v0.14.0 (Grinta, Sept 2025): introduced decentralized sequencer architecture with ⅔ stake voting for block finalization
- 2026 roadmap: Full sequencer decentralization, quantum-resistant cryptography for proof system
- Stone Prover open-sourced — community can run provers
- Recursive proving via SHARP (Shared Prover) aggregates many chains' proofs into one L1 submission

**Decentralization status:** Most advanced in ZK space — decentralized sequencers live since Grinta upgrade. Validators validate and vote on blocks; permissionless participation targeted in 2026.

**Moats:** Only production STARK chain at scale; non-EVM = differentiation in gaming/high-perf apps; post-quantum security; SHARP shared prover economics.

---

### 3. Polygon zkEVM (being sunset → AggLayer/CDK)
**Developer:** Polygon Labs  
**Proof System:** PLONK (with custom polynomial arithmetization)  
**EVM Compatibility:** High — bytecode-level EVM equivalence (Type 2/3)  

| Metric | Value |
|--------|-------|
| TPS | Tens of TPS (practical mainnet); higher in bursts |
| Finality (soft) | ~2–5 seconds |
| Finality (hard) | ~30–60 minutes (faster than competitors due to recursive proving) |
| Sequencer | Centralized (Polygon Labs) |
| Prover | Centralized; recursive PLONK prover |
| L2BEAT Stage | Stage 1 |
| Mainnet status | **SUNSETTING 2026** — migrating to AggLayer/CDK model |

**2026 pivot — AggLayer + CDK:**
- Polygon zkEVM Mainnet Beta being sunset; devs migrate to Polygon PoS or CDK chains
- CDK (Chain Development Kit): multistack toolkit for building custom L2s/L3s with native AggLayer integration
- AggLayer: credibly neutral aggregation layer — unifies liquidity across all CDK chains via ZK proofs
- 35+ chains deployed using CDK as of early 2026
- ZK proofs ensure user safety even if all operators are compromised

**Architecture highlights:**
- ZK counter limitations made complex DeFi impractical (reason for sunset)
- AggLayer = Polygon's long-term ZK thesis: one aggregated security layer, many sovereign execution environments
- PLONK prover verifies batches; recursive proving reduces L1 costs

**Moats:** AggLayer interoperability; CDK ecosystem with 35+ chains; MATIC → POL migration complete; enterprise-grade compliance tooling.

---

### 4. Scroll
**Developer:** Scroll Foundation  
**Proof System:** OpenVM (RISC-V zkVM, Euclid upgrade) — transitioning from custom zkEVM circuits  
**EVM Compatibility:** Type 3 → Type 1 (full Ethereum equivalence in progress)  

| Metric | Value |
|--------|-------|
| TPS | Moderate (comparable to other zkEVMs) |
| Finality (soft) | ~2–3 seconds |
| Finality (hard) | ~1–4 hours (L1 proof submission) |
| Sequencer | Centralized (Scroll team); decentralization roadmap active |
| Prover | Decentralized prover network (in rollout) |
| L2BEAT Stage | Stage 0 (limited governance) |
| Mainnet status | Live (Oct 2023) — 110M+ transactions as of Feb 2026 |

**Architecture highlights:**
- Euclid upgrade: adopted OpenVM (general-purpose RISC-V zkVM built by the Succinct team)
- OpenVM transition makes Scroll hardware-agnostic — any RISC-V circuit can be proven
- Goal: Type 1 zkEVM (full Ethereum equivalence, identical bytecode behavior)
- Open-source focus: most transparent codebase in ZK space
- 700+ active developers, 100+ dApps

**Decentralization status:** Decentralized prover network actively rolling out. Sequencer decentralization on roadmap. Known for academic rigor and open development.

**Moats:** Most open-source ZK project; academic credibility; OpenVM enables Type 1 compatibility; strong developer community.

---

### 5. Linea
**Developer:** ConsenSys  
**Proof System:** SNARK-based (custom arithmetization — lattice-based polynomial commitments, not Groth16 or PLONK-standard)  
**EVM Compatibility:** Type 2 (near full equivalence); Type 1 target Q1 2026  

| Metric | Value |
|--------|-------|
| TPS | 2,000–5,000+ TPS (roadmap) |
| Finality (soft) | ~2–3 seconds |
| Finality (hard) | ~15 minutes (L1 soft finality Q1 2026 upgrade) |
| Sequencer | Centralized (ConsenSys); permissioned decentralization 2026 |
| Prover | Centralized (ConsenSys); multi-vendor deployment planned |
| L2BEAT Stage | Stage 0 |
| Mainnet status | Live (production) — MetaMask integration drives user base |

**Architecture highlights:**
- Linea prover uses novel arithmetization; verifier contract on Ethereum covers 100% of zkEVM
- Q1 2026: Type 1 equivalence; L1 soft finality (15 min) — fastest finality among SNARK chains
- Q2 2026: Real-Time Proofs on Ethereum (instant verification)
- Unique advantage: Native MetaMask integration = largest consumer wallet distribution
- SWIFT testing Linea for institutional DeFi (proof-of-concept 2026)

**Decentralization status:** Permissioned node decentralization 2026 (not full permissionless). Multi-vendor prover deployment for fault tolerance. Deliberately more conservative vs competitors.

**Moats:** MetaMask distribution; ConsenSys enterprise relationships; SWIFT partnership; fastest path to institutional adoption.

---

### 6. Mina Protocol
**Developer:** o1 Labs  
**Proof System:** Kimchi (PLONK-derived, with Pickles recursive proofs)  
**EVM Compatibility:** None — completely custom VM and zkApps architecture  

| Metric | Value |
|--------|-------|
| TPS | ~22 TPS (current mainnet constraint) |
| Finality | ~3 minutes (probabilistic) |
| Blockchain size | Fixed 22KB (world's lightest blockchain) |
| Sequencer | Proof-of-Stake (decentralized validators) |
| Prover | Client-side (user device) or delegated |
| L2BEAT Stage | N/A (L1 chain, not rollup) |
| Mainnet status | Live — undergoing Kimchi upgrade Q3 2026 |

**Architecture highlights:**
- Mina is a Layer 1 — NOT a rollup. Uses recursive SNARKs to keep chain size at constant 22KB
- Pickles: recursive proof system built on Kimchi — any node can verify the entire chain
- Kimchi: 15-column PLONK extension, 10x+ faster elliptic curve ops, foreign field operations enabling EVM signature verification
- zkApps: smart contracts proven client-side, privacy-preserving
- Q3 2026: Kimchi upgrade — faster prover, improved zkApp developer experience

**2026 challenges:**
- Market cap collapsed from $1.73B (Dec 2024) → ~$64M (March 2026)
- Team reduced from 150+ → under 60 staff
- Low TPS limits practical utility for high-throughput applications

**Moats:** Lightest chain ever built; true ZK-native L1; unique for off-chain data attestation (ZK oracles, privacy proofs); zkApps privacy model has no equivalent.

---

### 7. Aztec Network
**Developer:** Aztec Labs  
**Proof System:** Honk (UltraHonk — PLONK-derived) via Noir language  
**EVM Compatibility:** None — privacy-first VM; Noir compiles to custom IR  

| Metric | Value |
|--------|-------|
| TPS | Not production (alpha testnet) |
| Finality | N/A (alpha) |
| Sequencer | Decentralized from inception (design goal) |
| Prover | Client-side (private state); network-based (public state) |
| L2BEAT Stage | N/A (not mainnet) |
| Mainnet status | **CRITICAL VULNERABILITY — mainnet delayed to July 2026** |

**Critical 2026 situation:**
- March 17, 2026: Critical vulnerability discovered in proving system
- Severity: Potential theft of user funds if exploited
- Fix packaged in "v5" release — currently planned July 2026
- Bug details under embargo until v5 ships

**Architecture highlights:**
- Hybrid execution: public execution (network-proven) + private execution (client-side, data never leaves device)
- Noir: Rust-like ZK programming language — compiles to Aztec's backend; most developer-friendly ZK DSL
- NoirJS: privacy-preserving ZK applications in the browser
- Honk (UltraHonk): next-generation PLONK variant with better prover performance; successor to TurboHONK
- Decentralized sequencer and prover from launch (novel approach vs competitors)

**Moats:** Only EVM L2 with native programmable privacy (not just transaction privacy); Noir is becoming standard ZK DSL beyond Aztec; unique compliance architecture (selective disclosure).

---

### 8. Taiko
**Developer:** Taiko Labs  
**Proof System:** Multi-tier (ZK proofs + TE-IR + guardian provers); risc0/SP1 zkVM  
**EVM Compatibility:** Type 1 (full Ethereum-equivalent bytecode)  

| Metric | Value |
|--------|-------|
| TPS | Limited by Ethereum L1 (based rollup model) |
| Finality (soft) | Sub-1 second preconfirmations (Q2 2026 target) |
| Finality (hard) | Ethereum L1 finality (~13 min) |
| Sequencer | No centralized sequencer — Ethereum validators sequence (based rollup) |
| Prover | Permissionless proving network; 100% ZK coverage since Shasta HF |
| L2BEAT Stage | Stage 1 (Taiko Alethia) |
| Mainnet status | Live — Alethia (Type 1, no centralized sequencer); Gwyneth (composable) |

**Architecture highlights:**
- Based rollup: Ethereum L1 validators propose Taiko blocks — no separate sequencer entity
- Synchronous composability: real-time interoperability with other based rollups (Gwyneth)
- Multi-tier proving: ZK proofs in production; guardian multisig fallback for safety
- Shasta HF (Q4 2025): 100% ZK coverage, lower costs
- Q1 2026: Fully decentralized preconfirmations; formal preconfirmation protocol specification
- Q2 2026: Sub-1s preconfirmation latency; fast withdrawals; cross-rollup interop

**Decentralization status:** Most decentralized ZK rollup in production — no sequencer, Ethereum validators propose blocks directly. Prover network permissionless.

**Moats:** Closest thing to "trustless Ethereum scaling"; no sequencer MEV risk; synchronous composability unique property; Type 1 equivalence means zero porting cost from Ethereum.

---

### 9. Midnight Network
**Developer:** IOG (Input Output Global — Cardano team)  
**Proof System:** Halo2 (PLONK-derived, recursive, BLS12-381, no trusted setup)  
**EVM Compatibility:** None — UTXO-based, Compact language (TypeScript DSL)  

| Metric | Value |
|--------|-------|
| TPS | ~166 TPS (6-second blocks; increasing with Mōhalu upgrade) |
| Finality | ~12 seconds (GRANDPA finality); ~6-second blocks |
| Sequencer | Federated validators (Google Cloud, Blockdaemon, Worldpay, Telegram, eToro…) |
| Prover | Client-side (private state stays on device) |
| L2BEAT Stage | N/A (L1/partner chain) |
| Mainnet status | **Live (March 30, 2026 — federated Kūkolu phase)** |

**Architecture highlights:**
- Substrate/Rust node; AURA block production; GRANDPA finality; BEEFY bridge security
- ZSwap: Zerocash-based UTXO atomic swaps with sparse multi-value Pedersen commitments
- Kachina framework: UC-model private smart contracts (IOG + Edinburgh, CSF 2021)
- BLS12-381 migration (2025): 50% faster ZK verification (12ms → 6ms)
- Compact DSL: TypeScript-compiling to ZK circuits — generates proving/verifying keys automatically
- Dual-state: public ledger + shielded private state on user device
- Dual-token: NIGHT (governance/staking) + DUST (transaction resource)

**Decentralization status:** Currently federated (design). SPO decentralization coming in Mōhalu phase (Q2 2026). No public security audit yet.

**Moats:** Only compliance-native production ZK privacy chain (Aztec vulnerability creates 3-month window); IOG academic foundation; Monument Bank £250M RWA partnership.

---

### 10. Aleo
**Developer:** Provable (formerly Aleo Systems)  
**Proof System:** Varuna (Marlin-based SNARK with batch amortization) via SnarkVM  
**EVM Compatibility:** None — native Leo language (Rust-like), SnarkVM execution  

| Metric | Value |
|--------|-------|
| TPS | ~50–200 TPS (current mainnet) |
| Finality | ~15–30 seconds |
| Sequencer | Proof-of-Stake validators (decentralized) |
| Prover | Permissionless "provers" (SNARK miners equivalent) |
| L2BEAT Stage | N/A (L1) |
| Mainnet status | Live (mainnet launched late 2024) |

**Architecture highlights:**
- SnarkVM: ZK execution environment — all computation is provable off-chain
- Varuna: Marlin variant with batch proof amortization — reduces cost of proving multiple statements
- Leo language: developer-friendly, compiles to ARC (Aleo Record Commitment) circuits
- Private programs by default — public outputs, private inputs
- Proof of succinct work: provers compete to prove programs (economic incentive without traditional PoW energy waste)

**Moats:** Privacy by default (not opt-in); flexible ZK computation (not just transfers); strong developer tooling (Leo); audited by Trail of Bits + NCC Group + zkSecurity.

---

## Part 3: Comparative Matrix

| Chain | Proof System | EVM Compat | TPS (practical) | Soft Finality | Hard Finality | Sequencer Decentralization | Production Readiness |
|-------|-------------|------------|-----------------|---------------|---------------|---------------------------|---------------------|
| zkSync Era | STARK (Boojum/Airbender) | Full (bytecode) | 15K+ sequencing | ~1s | ~3h | Centralized → roadmap | ★★★★★ |
| Starknet | STARK (Stone/FRI) | None (Cairo native) | 1K–100K+ | ~1-2s | ~2-4h | **Decentralized (Grinta)** | ★★★★★ |
| Polygon CDK/AggLayer | PLONK | Full (CDK chains) | Chain-specific | ~2-5s | ~30-60min | CDK-chain-specific | ★★★★☆ |
| Scroll | OpenVM (RISC-V) | Type 3→1 | Moderate | ~2-3s | ~1-4h | Centralized → roadmap | ★★★★☆ |
| Linea | SNARK (custom) | Type 2 → Type 1 | 2K-5K+ | ~2-3s | **~15 min (Q1 2026)** | Centralized + multi-vendor | ★★★★☆ |
| Mina | Kimchi/Pickles | None (zkApps) | ~22 | ~3 min | ~3 min | PoS (decentralized) | ★★★☆☆ |
| Aztec | Honk (UltraHonk) | None (Noir) | N/A (alpha) | N/A | N/A | Decentralized (design) | ★☆☆☆☆ (critical vuln) |
| Taiko | Multi-tier ZK | Type 1 (full) | Eth-bound | Sub-1s (Q2 2026) | ~13 min (Eth L1) | **No sequencer (based)** | ★★★★☆ |
| Midnight | Halo2 | None (Compact/UTXO) | ~166 | ~6s (block) | ~12s (GRANDPA) | Federated → PoS | ★★★★☆ (live) |
| Aleo | Varuna (Marlin) | None (Leo/SnarkVM) | 50-200 | ~15-30s | ~15-30s | PoS (decentralized) | ★★★☆☆ |

---

## Part 4: Proof System Selection Guide

### Use Groth16 when:
- Proof size and verification cost are paramount
- Circuit is fixed and known at compile time
- Comfortable running a trusted setup ceremony
- Verifying on L1 Ethereum (lowest gas cost)

### Use PLONK (or variants: Halo2, Kimchi, Honk) when:
- Need flexibility across multiple circuit types
- Want to avoid per-circuit trusted setups
- Building recursive proof systems
- Applications: Midnight, Mina, Aztec (Noir)

### Use STARK/FRI when:
- Post-quantum security required
- No trusted setup is mandatory
- Running at scale (SHARP aggregation economics)
- Non-EVM application (Starknet Cairo ecosystem)
- Applications: Starknet, zkSync Era (Boojum is STARK-based)

### Use zkVM-based proving (OpenVM, SP1, risc0) when:
- General-purpose computation (any RISC-V program)
- Don't want to write ZK circuits manually
- Need hardware-agnostic, upgradeable proof system
- Applications: Scroll (OpenVM), Taiko (risc0/SP1 tier)

---

## Part 5: 2026 Key Trends

1. **zkVM commoditization**: OpenVM (Scroll), SP1 (Succinct), risc0 replacing hand-written ZK circuits → proof generation becoming infrastructure not differentiation

2. **Proving costs collapsing**: 45x drop in 2025; Airbender achieves sub-cent proofs; GPU acceleration makes proving accessible

3. **Decentralization urgency**: Starknet (Grinta), Taiko (based rollup, no sequencer), Scroll (prover network) — L2BEAT Stage 2 pressure from Ethereum community

4. **Type 1 race**: Multiple chains racing to achieve full Ethereum bytecode equivalence (Scroll, Linea Q1 2026) — erases developer migration costs

5. **Aggregation thesis**: Polygon AggLayer, zkSync ZK Stack, Starknet SHARP — shared proof aggregation reduces L1 costs across ecosystems

6. **Privacy layer specialization**: Midnight (federated live), Aztec (delayed to July), Aleo (live) filling different niches; Aztec vuln creates window for Midnight

7. **Based rollups gaining traction**: Taiko model (Ethereum validators as sequencers) proving viable; synchronous composability enables new app architectures

8. **Real-time proving**: Linea targets real-time proofs on Ethereum Q2 2026; zkSync Airbender already near real-time — eliminates the "3-hour finality" UX problem

---

## Part 6: Relevance to SOS Systems / Otto Projects

**Chain selection framework for SOS 505 Systems contracts:**

| Use case | Recommended chain | Rationale |
|----------|------------------|-----------|
| Governance + DPC contracts | **Scroll** or **Linea** | Type 1 (Scroll) / MetaMask distribution (Linea); EVM equivalence, no porting cost |
| Privacy-preserving operations | **Midnight** | Only production compliance-native ZK privacy chain; Aztec has critical vuln until July 2026 |
| High-throughput task rewards | **zkSync Era** or **Taiko** | 15K+ TPS or Ethereum-native based rollup |
| Cross-chain aggregation | **Polygon CDK + AggLayer** | Credibly neutral; 35+ chains; ZK proof guarantees exit safety |
| Native ZK smart contracts | **Starknet** (Cairo) or **Aleo** (Leo) | If willing to use non-EVM language; best proof performance |
| Lowest L1 verification cost | **Groth16 + custom circuit** | 192 byte proof, 200K gas verify — cheapest on-chain settlement |

**Current SOS Systems decision (from memory):** Architecture specifies **Polygon zkEVM** — given the Polygon zkEVM sunset in 2026, recommend migrating evaluation to **Polygon CDK** (same security guarantees, AggLayer upside) or **Scroll** (Type 1 equivalence, strongest open-source credibility).

---

## Sources

- [zkSync Era — L2BEAT](https://l2beat.com/scaling/projects/zksync-era)
- [zkSync Finality Docs](https://docs.zksync.io/zksync-protocol/rollup/finality)
- [zkSync 2026 Roadmap — Prividium](https://www.ainvest.com/news/zksync-2026-roadmap-rise-prividium-era-enterprise-blockchain-adoption-token-accrual-2601/)
- [Boojum STARK Proof System — The Block](https://www.theblock.co/post/239880/zksync-launches-new-proof-system-called-boojum-for-era-mainnet)
- [Airbender ZK Prover — Stocktwits/zkSync](https://stocktwits.com/news-articles/markets/cryptocurrency/zksync-zk-solo-gpu-works/chmOp5YRR4p)
- [Starknet 2025 Year in Review](https://www.starknet.io/blog/starknet-2025-year-in-review/)
- [Stone Prover Open-Sourced — StarkWare](https://starkware.co/blog/open-sourcing-the-battle-tested-stone-prover/)
- [Polygon zkEVM Sunset 2026](https://l2beat.com/scaling/projects/polygonzkevm)
- [Polygon AggLayer CDK 2026](https://cryptoadventure.com/polygon-review-2026-pol-migration-agglayer-and-the-scaling-thesis/)
- [Scroll OpenVM — Blockworks](https://blockworks.com/news/scroll-announces-new-zkevm)
- [Scroll 110M Transactions Feb 2026](https://iq.wiki/wiki/scroll)
- [Linea Prover — ConsenSys](https://eprint.iacr.org/2022/1633.pdf)
- [Linea 2026 Roadmap](https://coinmarketcap.com/cmc-ai/linea/latest-updates/)
- [Mina Kimchi Upgrade — o1Labs](https://www.o1labs.org/blog/reintroducing-kimchi)
- [Mina Q3 2026 Kimchi Upgrade](https://minaprotocol.com/blog/mina-protocols-upcoming-major-upgrade-everything-you-need-to-know)
- [Aztec Critical Vulnerability March 2026](https://aztec.network/blog/)
- [Taiko Based Rollup Architecture](https://taiko.mirror.xyz/4c6VNhjKLHOMaNKRryyKHkiHcWx7caRax_mC0jTr-sY)
- [Taiko 2026 Roadmap](https://taiko.xyz/)
- [Aleo Mainnet Launch](https://aleo.org/post/announcing-aleo-mainnet/)
- [Aleo Varuna Proof System](https://equilibrium.co/writing/privacy-blockchains-and-aleo-deep-dive)
- [ZK Proof Systems Comparison arXiv 2512.10020](https://arxiv.org/pdf/2512.10020)
- [ZK Proof Benchmarks](https://stealthcloud.ai/data/zero-knowledge-proof-performance-benchmarks/)
- [Ethereum Scaling Exponentially ZK 2026 — CoinTelegraph](https://cointelegraph.com/news/2026-is-the-year-ethereum-starts-scaling-exponentially-with-zk-tech)

# ZK Ecosystem Research Brief — April 2026

**Researched:** 2026-04-10 | **Confidence:** HIGH (8+ web sources cross-referenced)
**Scope:** Toolchains, zkVMs, proving infra, bridges, wallet/AA, indexers, auditors, grants

---

## Executive Summary

ZK is crossing from experimental to production in 2026. The toolchain is bifurcating: **DSLs** (Noir, Circom, Cairo) for application-level ZK; **zkVMs** (SP1, Risc0) for general Rust computation proofs. Proving is becoming a commodity via outsourced prover networks. The critical 2026 gate: **Aztec mainnet going live Q1/Q2 2026** is the biggest event for privacy-native smart contracts.

**For ONEON**: Aztec + Noir is the strongest path for adding ZK privacy. SP1 is the fastest route to ZK-verified computation. Midnight (Compact DSL/Halo2) remains ONEON's best native ZK option given existing research.

---

## 1. ZK Toolchains (DSLs)

### Noir (Aztec Labs) — ⭐ PRODUCTION APPROACHING
- **What**: Rust-inspired DSL for ZK circuits. Backend-agnostic (compiles to ACIR intermediate representation)
- **Backends**: Barretenberg (Plonk/UltraPlonk) by default; can target Halo2, PLONK, R1CS backends
- **Status**: Noir 1.0 Pre-Release announced; currently in Beta phase. **Aztec mainnet launched Nov 2025** (consensus-only "Ignition"); full smart contract execution expected Q1/Q2 2026
- **Tooling**: `nargo` CLI, `noirup` version manager, `NoirJS` (browser/TS), CodeTracer (visual debugger), Noir+Barretenberg Profiler, `aztec-lint` (Nethermind static analyzer)
- **Developer experience**: High — Rust-like syntax, static typing, no manual constraint writing. One of the fastest-growing ZK developer ecosystems (Electric Capital 2023-2024)
- **Weakness**: Still pre-1.0. **Critical vulnerability discovered March 17 2026** in proving system — v5 fix scheduled July 2026
- **Grants**: EF ZK Grants Wave included Noir awardees. Aztec Grants program live

### Cairo (StarkWare) — ⭐⭐ PRODUCTION (Starknet mainnet live)
- **What**: Cairo = provable VM language for Starknet. Starknet is a ZK validity rollup (STARK proofs, no trusted setup)
- **Status**: Fully production on Starknet mainnet. **200% developer activity growth 2024-2025**
- **Tooling**: Scarb (package manager + compiler), Starknet Foundry (testing), Starkli (CLI), devnet-rs, CairoLS (LSP)
- **Survey**: Starkli is most popular CLI (46.7% of devs). Most use Scarb + Starknet Foundry combo. All tools migrated from Python → Rust 2025
- **Developer experience**: High for EVM devs transitioning. Not EVM-compatible (custom VM)
- **Grants**: Starknet Foundation grants — Seed ($25K STRK) to Growth (up to $1M STRK). 200+ projects in ecosystem

### Circom (iden3) — ⭐ MATURE BUT LOW-LEVEL
- **What**: Oldest widely-used ZK DSL. Generates R1CS constraints. Used heavily by identity projects (Semaphore, Anon Aadhaar, ZK Email)
- **Status**: Production — extensive deployed circuits in Polygon, Aztec, identity systems
- **Backends**: snarkjs (Groth16, Plonk, FFLONK), rapidsnark (faster prover)
- **Weakness**: Very low-level — "hard to use correctly." Known soundness bug in snarkjs Groth16 verifier (incorrect setup). Circomspect is a static analysis tool to catch issues
- **Use case**: Best for specific circuits (ECDSA verification, Merkle proofs, identity). Not suited for general computation
- **Tooling**: circom compiler, snarkjs, circomspect, powersOfTau trusted setup ceremonies

### Halo2 (EF PSE / Zcash / Scroll) — ⭐ EXPERT-ONLY
- **What**: PLONKish ZK library in Rust. No trusted setup (IPA commitments)
- **Status**: Production — used by Scroll zkEVM, Midnight Network (BLS12-381 fork), ZCash, PSE projects
- **Weakness**: No high-level language, hand-coded circuits, steep learning curve. Known "query collision bug" in widely-used versions (Zcash, PSE fork)
- **Use case**: Infrastructure-level proving — zkEVM internals, custom high-performance circuits
- **Tooling**: 0xPARC maintained. halo2-lib (Axiom), halo2-ce (community edition). ZK/SEC course now available

---

## 2. zkVM Options

### SP1 (Succinct Labs) — ⭐⭐ PRODUCTION LEADER
- **What**: RISC-V zkVM. Write Rust, prove it. Compiles via RISC-V toolchain
- **Status**: SP1 Hypercube live on mainnet — "first zkVM to prove 99.7% of Ethereum blocks in under 12 seconds" with 16 NVIDIA RTX 5090 GPUs
- **Deployments**: Optimism (Feb 12 2026) — Succinct now handles ZK proving for ~90% of rollup market (Base, Unichain, Ink). Also: Polygon, Celestia, Arbitrum bridges. **$4B+ in assets protected**. 6M+ proofs generated in 2025
- **Performance**: GPU prover achieves cheapest cloud costs vs alternatives by up to 10x. FPGA acceleration (20x boost) roadmap Q2 2026
- **DX**: Write standard Rust → `cargo prove` → zk proof. Extensive precompiles: keccak256, sha256, secp256k1, ed25519, bn254, bls12-381
- **License**: MIT (fully open source)
- **PROVE token**: Payments token for outsourced proving. Off-chain auctions + Ethereum settlement. Provers stake and can be slashed

### Risc0 — ⭐ PRODUCTION (limited managed service)
- **What**: RISC-V zkVM using FRI-based STARKs
- **Status**: zkVM v1.x production. Bonsai managed proving service = **Pre-Alpha (not for production use)**. Boundless (decentralized marketplace) = testnet, mainnet late 2025 → 2026
- **Performance**: ~10-40x slower than SP1 on CPU for equivalent workloads (Jolt claims 5x faster than Risc0)
- **DX**: Similar to SP1 — write Rust, use guest/host split. Larger ecosystem of examples
- **Weakness**: Managed service (Bonsai) not yet production-ready. Decentralized Boundless still maturing

### Jolt (a16z) — ⭐ EXPERIMENTAL
- **What**: Next-gen zkVM architecture. Claims 5x faster than Risc0, up to 2x faster than SP1 (Feb 2026)
- **Status**: Early development — "cannot run most benchmarking programs." No recursion support yet. Not production-ready
- **Potential**: Most promising architecture for long-term perf. Watch Q3-Q4 2026

### ZKM (zkMIPS) — ⭐ TESTNET
- **What**: MIPS-based zkVM with Ethereum L2 integration
- **Status**: Testnet only. Integrated with Gevulot/ZkCloud for proving

### Nexus — ⭐ RESEARCH
- **What**: Nova/SuperNova-based zkVM for extremely parallelized proving
- **Status**: Professional Provers Program with ZkCloud. Research phase

---

## 3. Proving Infrastructure (Outsourced Provers)

### Succinct Prover Network + PROVE Token — ⭐⭐ PRODUCTION
- **Model**: Decentralized marketplace. Rollups/bridges outsource proof generation. Off-chain auctions (speed) + Ethereum settlement (trustlessness)
- **Economics**: PROVE token = payments + staking + governance. Provers stake PROVE, slashed for bad proofs
- **Status**: TESTNET Stage 2.5 (Q1 2026) → Decentralized prover onboarding + live proof auctions. Mainnet trajectory clear
- **Clients**: Optimism, Base, Unichain, Ink, Polygon, Celestia, Arbitrum bridges
- **Key milestone**: Q2 2026 — FPGA rollout targeting 20x speed improvement

### ZkCloud (formerly Gevulot) + PROOF Token — ⭐ PRODUCTION (permissioned)
- **Model**: Decentralized cloud for ZK proof generation + verification. Deploy any prover, offload to hardware operators
- **Status**: Firestarter mainnet LIVE (December 2024) — permissioned (ZkCloud Labs runs validators, proving compute decentralized). Deluge testnet (Feb 2025) tests fully decentralized block building. Full permissionless mainnet pending
- **Clients**: ZKM, Nexus, Aztec testnet proving
- **Token**: PROOF token (network security, governance, participation)
- **Track record**: 2M+ proofs generated, 5M+ verifications

### ZkBoost (Initiative) — ⭐ PROPOSED
- **What**: Open-source unified client for outsourced proof generation — standardizes integration across multiple prover networks
- **Status**: RFC/proposal stage. Aims to reduce fragmentation, enable competitive prover market

### Bonsai (RISC Zero managed) — ⚠️ PRE-ALPHA
- **Status**: Not production-ready. Don't use. See Risc0 Boundless (testnet) for decentralized alternative

---

## 4. Bridge / Interop Standards

### Polygon AggLayer — ⭐⭐ PRODUCTION
- **What**: Network-of-networks using "pessimistic proofs" for cross-chain security. Chains join AggLayer; unified liquidity + shared bridge security
- **Status**: **Production mainnet** — pessimistic proofs live (Feb 2025). AggLayer v0.3 live (2026) — now accepts non-CDK chains, Polygon PoS joining. CDK Erigon stack powering enterprise appchains
- **Note**: Polygon zkEVM Mainnet Beta being sunset 2026 → Polygon pivoting to AggLayer as flagship

### zkBridge (Polyhedra Network) — ⭐ PRODUCTION
- **What**: Trustless cross-chain bridge secured by zkSNARKs. Supports NFT transfers + message passing
- **Status**: Mainnet Alpha. 10+ L1/L2 chains supported. On Polygon

### ZK Interop Standards — MATURING
- **zkEVM Type Classification** (Vitalik's 5 types) is industry standard:
  - Type 1 (EVM-equivalent): Taiko — based rollup, Ethereum validators, synchronous composability
  - Type 2 (EVM-compatible): Scroll, Linea — near-perfect EVM at VM level
  - Type 2.5/3: Polygon zkEVM (being sunset), zkSync Era (native AA, deviates from EVM)
  - Type 4 (high-level language): Starknet (Cairo), Aztec (Noir)
- **Proof time improvement**: 16 minutes (2022) → 16 seconds (2026) — 60x improvement
- **2026 roadmap**: Ethereum block validation becoming optional + proof-driven. Sequencer decentralization on Starknet (2026 target). Taiko Gwyneth mainnet + EIP-7702 AA Q1 2026

---

## 5. Wallet / Account Abstraction Support

### ERC-4337 (Ethereum/EVM chains) — ⭐⭐ PRODUCTION
- **What**: Account abstraction without protocol changes. UserOperation objects, alt-mempool, EntryPoint contract
- **Supported on**: zkSync Era, Scroll, Linea, Polygon zkEVM, Taiko
- **zkLogin**: OAuth→ZK proof via JWT verification (zk-SNARKs). Used by Sui, ZEROBASE
- **Tooling**: OpenZeppelin Contracts 5.x AA, Alchemy Account Kit, Biconomy, Pimlico

### Native Account Abstraction — ⭐⭐ PRODUCTION (select chains)
- **zkSync Era**: Native AA (all accounts are smart contracts). Superior to ERC-4337 architecture. Production
- **Starknet**: Native AA. Every account is a smart contract. Production
- **Aztec**: Full programmable AA — Aztec's approach goes further than ERC-4337 ("Is Account Abstraction abstract enough?" blog). Launching with mainnet

### Aztec Privacy + AA — ⭐ SOON
- **What**: Private smart contracts with programmable AA. zkLogin-style private auth possible. Full privacy at L2
- **Status**: Mainnet executing Q1/Q2 2026. Token live (AZTEC/ETH pool on Uniswap Feb 11 2026). Bridges from Wormhole, Substance Labs, Train under construction

---

## 6. Indexer / RPC Availability

### ZKSync Era
- **RPC Providers**: 6 providers — Alchemy, Infura (Open Beta), QuickNode, Chainstack, dRPC, public (chainlist.org/chain/324)
- **Indexing**: The Graph (first ZK protocol indexed by The Graph). Block explorer: matter-labs/block-explorer (open source)

### Starknet
- **RPC Providers**: 8 providers — Alchemy, Infura, Chainstack, Dwellir, dRPC, BlockPI, Blast, Lava
- **Note**: Uses own `starknet_` JSON-RPC namespace. Dune Analytics integration limited
- **Indexing**: Starknet Foundry, custom event indexers. Limited Subgraph coverage. Indexing remains challenging

### Polygon (PoS + AggLayer CDK chains)
- **RPC Providers**: 23 providers — mature ecosystem. Alchemy, Infura, Chainstack, QuickNode all support
- **Indexing**: The Graph, Subgraph fully supported on Polygon PoS

### Aztec
- **Status**: No public RPC providers yet (mainnet just launching 2026). Aztec Sandbox (local dev). Aztec Sequencer nodes being onboarded
- **Indexing**: No production indexers yet. Major gap

### Scroll & Linea
- **RPC**: Multiple providers. Alchemy/Chainstack support both
- **Indexing**: Improving but Subgraph coverage limited vs Ethereum mainnet

### General Infrastructure Gap
- ZK chains lag significantly behind EVM mainnet for tooling depth
- Dune Analytics: limited ZK rollup support
- The Graph: zkSync + Polygon strong; Starknet/Aztec weak

---

## 7. Audit Firms with ZK Expertise

### Veridise — ⭐⭐ ZK SPECIALIST
- **Specialties**: Circom, Halo2, Nova, Plonky2, gnark, Risc0, SP1, Succinct, Linea, Manta, MINA, O1JS
- **Credentials**: Found critical bugs in circom-lib itself. Team includes PhDs in program analysis + cryptography
- **Track record**: Audited ZK infrastructure (Risc Zero, Succinct, Linea, Manta, MINA)
- **Tooling**: Developed VAR (Veridise Automated Reasoning) for ZK circuit analysis

### Trail of Bits — ⭐⭐ CRYPTOGRAPHY + ZK
- **Specialties**: Cryptographic implementations, ZK protocol design, Circom (developed Circomspect tool)
- **Assets**: ZKDocs (open reference for ZK systems), Tlspuffin
- **Reputation**: Top-tier security research firm. Broader scope than pure ZK but deep crypto expertise

### Nethermind Security — ⭐⭐ ZK CIRCUITS + AZTEC NOIR
- **Specialties**: Noir circuits (first major Noir audit), zkVM reviews, Starknet Cairo contracts
- **Notable**: Published comparison of Noir vs Circom vs o1js for auditability. Developed `aztec-lint`

### ZK Security (0xPARC affiliated) — ⭐ EMERGING
- **Specialties**: Halo2, circom audits. Offers Halo2 course for developer onboarding
- **Status**: Smaller firm, growing reputation

### Spearbit / Cantina — ⭐ EVM + SOME ZK
- **Note**: Strong EVM track record. ZK expertise via specific auditors on platform

### What to Look For in ZK Audits
- Audit firms must understand: constraint system completeness (under-constrained = exploitable), ZK-specific bugs (missing range checks, signal aliasing in Circom, signal mutation in Noir)
- Known vulnerability classes: Groth16 verifier setup errors (snarkjs), Halo2 query collision bug, soundness issues from non-deterministic witnesses

---

## 8. Community & Grant Programs

### Ethereum Foundation — ZK Grants Round
- **Pool**: $900K total (EF + Aztec + Polygon + Scroll + Taiko + zkSync co-funded, $150K each)
- **Focus**: ZK public goods projects, cross-ecosystem tooling
- **Status**: 2024 wave complete. 2026 round TBD

### Starknet Foundation
- **Seed Grants**: Up to $25K in STRK for early-stage teams with MVP/PoC
- **Growth Grants**: Up to $1M in STRK for live projects with traction
- **Active**: Yes. 200+ projects in ecosystem

### zkSync / ZKsync Foundation
- **Community Program**: 5M ZK tokens via Gitcoin (6-month initiative). Rewards moderation, security, ecosystem development
- **VC**: zkSync raised $200M (series C level) — war chest for ecosystem

### Aztec Grants
- **Program**: Active. Community-led privacy ecosystem projects
- **Amounts**: TBD — not publicly announced. $AZTEC token live Feb 11 2026

### 0xPARC Foundation
- **Focus**: ZK research tooling — maintained circom/snarkjs, Halo2, browser tooling, developer education
- **Grants**: Small focused grants for ZK tooling research

### Midnight Network (IOG)
- **Reserve**: 9.6B NIGHT tokens for ecosystem development
- **Aliit Fellowship**: 17 fellows, 11 countries, rolling admissions — active
- **Focus**: Privacy dApps using Compact DSL + Halo2

---

## Production Readiness Matrix

| Layer | Tool/Project | Readiness |
|---|---|---|
| DSL | Cairo/Starknet | ✅ PRODUCTION |
| DSL | Circom + snarkjs | ✅ PRODUCTION (use carefully) |
| DSL | Noir + Barretenberg | 🟡 BETA → Mainnet Q2 2026 |
| DSL | Halo2 (raw) | ✅ PRODUCTION (expert only) |
| zkVM | SP1 Hypercube | ✅ PRODUCTION (recommended) |
| zkVM | Risc0 v1.x | ✅ PRODUCTION (zkVM) / 🔴 Bonsai NOT ready |
| zkVM | Jolt | 🔴 EXPERIMENTAL |
| Prover Infra | Succinct Prover Network | 🟡 TESTNET → Mainnet 2026 |
| Prover Infra | ZkCloud (Firestarter) | 🟡 Permissioned mainnet live |
| Prover Infra | Bonsai (Risc0) | 🔴 PRE-ALPHA |
| Bridge | Polygon AggLayer | ✅ PRODUCTION |
| Bridge | zkBridge (Polyhedra) | ✅ PRODUCTION (limited chains) |
| L2 (EVM) | zkSync Era | ✅ PRODUCTION |
| L2 (EVM) | Scroll | ✅ PRODUCTION |
| L2 (EVM) | Linea | ✅ PRODUCTION |
| L2 (EVM) | Taiko | ✅ PRODUCTION |
| L2 (privacy) | Aztec | 🟡 Launching Q1/Q2 2026 |
| L2 (privacy) | Midnight | 🟡 Federated mainnet live |
| AA | ERC-4337 | ✅ PRODUCTION (zkSync, Scroll, Polygon) |
| AA | Native (zkSync/Starknet) | ✅ PRODUCTION |
| RPC | zkSync, Polygon, Scroll | ✅ PRODUCTION (8-23 providers) |
| RPC | Starknet | ✅ PRODUCTION (8 providers) |
| RPC | Aztec | 🔴 NOT YET |
| Indexing | The Graph (zkSync, Polygon) | ✅ PRODUCTION |
| Indexing | Starknet/Aztec indexing | 🟡 LIMITED |
| Audits | Veridise, ToB, Nethermind | ✅ AVAILABLE |

---

## ONEON / MY3YE Relevance

### Immediate Opportunities
1. **SP1 for ZK-verified computation**: ONEON could use SP1 to generate verifiable proofs of off-chain computation (identity claims, credential verification) — write Rust, prove it, verify on-chain. Production-ready NOW
2. **Noir/Aztec for private contracts**: Aztec is launching its full execution layer Q2 2026. ONEON privacy features could deploy as Aztec contracts using Noir — private state + programmable AA
3. **Midnight Compact DSL**: Already researched (2026-03-31). Halo2-based, federated mainnet live. Strongest for ZK privacy with IOG backing

### Recommended Path
- **Short-term**: Add SP1 ZK-verified claims to ONEON (Rust computation proofs on EVM)
- **Medium-term**: Deploy privacy contracts on Aztec when full execution live (~Q2 2026)  
- **Long-term**: Midnight bridge for shielded state if ONEON pursues full privacy chain

### Key Gaps to Watch
- Aztec critical security vulnerability (March 17 2026) — v5 fix July 2026. **Don't deploy production contracts before v5**
- ZkCloud full permissionless mainnet — needed before depending on outsourced proving
- Starknet/Aztec indexing — infrastructure still thin

---

## Sources
- Succinct SP1 Hypercube mainnet: https://blog.succinct.xyz/sp1-hypercube-is-now-live-on-mainnet/
- Succinct 2025 recap: https://blog.succinct.xyz/succinct-2025-recap/
- ZkCloud (Gevulot) overview: https://blog.zkcloud.com/p/gevulot-is-now-zkcloud
- Polygon AggLayer v0.3: https://www.agglayer.dev/blogs/agglayer-v0-3-is-live
- Aztec road to mainnet: https://aztec.network/blog/road-to-mainnet
- Aztec critical vulnerability (Mar 2026): https://aztec.network/blog/road-to-mainnet (referenced in wallet/AA search)
- Noir 1.0 pre-release: https://aztec.network/blog/the-future-of-zk-development-is-here-announcing-the-noir-1-0-pre-release
- Starknet 2025 review: https://www.starknet.io/blog/starknet-2025-year-in-review/
- Starknet grants: https://www.starknet.io/grants/
- Veridise ZK audits: https://veridise.com/security/zero-knowledge/
- Trail of Bits cryptography: https://trailofbits.com/services/software-assurance/cryptography/
- EF ZK Grants: https://blog.ethereum.org/en/2024/02/21/zk-grants-round
- zkEVM types (Jan 2026): https://blockeden.xyz/blog/2026/01/16/zkevm-types-comparison-type-1-2-3-4-trade-offs-benchmarks/
- Babybear ZkVM benchmarks: https://github.com/babybear-labs/benchmark
- Aayush ZK tooling overview: https://blog.aayushg.com/zk/
- Nethermind Noir audit: https://www.nethermind.io/blog/our-first-deep-dive-into-noir-what-zk-auditors-learned
- Proving infra landscape Q1 2025: https://blog.zkcloud.com/p/state-of-the-proving-infrastructure-ea5

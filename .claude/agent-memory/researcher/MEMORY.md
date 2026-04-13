# Researcher Agent Memory

## Active Research (2026-04-13)

- [Tusita Technical Direction & Chain Fit](project_tusita_chain_fit_2026_04_13.md) — PIPELINE COMPLETE 8.0/10 (post-corrections). Base=CONFIRMED (ecosystem consensus). Zero .sol files (greenfield). 8 memories + 1 note stored (744f4cfb). 2 patches: (1) Aragon codebase source fabricated → SOS-extrapolated only, (2) DPCRegistry fork overstated → decay math reuse + new 3D CS schema required. CRITICAL DESIGN: CS Registry needs 3 independent dimensions (Capital/Resources/Labour) + weighted aggregation — cannot fork DPCRegistry directly. P0: write on-chain-architecture.md. P1: $TUSITA ERC20 + Founding IslanderNFT ERC721 on Base Sepolia. P2: design CSRegistry 3D schema. Capital blocker: legal entity registration (parallel track).
- [TON Blockchain Telegram Ecosystem 2026](project_ton_ecosystem_2026_04_13.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). TON=consumer payments rail, not DeFi (TVL -92%, defillama). 950M MAU addressable, not captive. Catchain 2.0 shipped Apr 9–10 (400ms blocks). 7 memories + 1 note stored (db0eeb54). 3 patches: Insight 1 framing, Insight 2 USDT growth HIGH→MEDIUM, Insight 4 retention HIGH→MEDIUM. 3 action patches: Koink needs Tact contracts (not frontend-only), ONEON→TON speculative, fees contingent on Step 2 Q2. GAP: zero .tact/.fc files anywhere in MY3YE repos. P0: Koink Telegram Mini App spike (include Tact contract budget).
- [ONEON Technical Direction & Chain Fit](project_oneon_chain_fit_2026_04_13.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). Base=CONFIRMED (Decision 2, invisible-web3-layer arch doc). 8 memories + 1 note stored (824cf9b8). 5 patches: gas direction added (Base 10-100x cheaper vs Polygon), SP1 Prover testnet-only caveat, session key custody gap (CRITICAL, new Insight 9), ZK predicate confidence label clarified. 2x NEEDS_MEV_INPUT: (1) ZK predicate — wallet-binding/DPC selective disclosure/anon creds [recommend B], (2) session key custody — vault/HSM/memory-only. P0: fix Polygon→Base in arch doc. P1: ContributionRegistry.sol on Base Sepolia.
- [Solana Ecosystem 2026](project_solana_ecosystem_2026_04_13.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). 9 memories + 1 note stored (dbfdc89f). 4 patches: x402 HIGH→MEDIUM (vendor bias), Helium 93%→91.7% (math), pump.fun source count 2→1, Action #1 BLOCKED (Koink chain conflict). NEEDS_MEV_INPUT: Koink Phase 1 chain — Base (Mar 23, codebase-aligned) vs Solana (Mar 20). Unblocked P0: liquidity velocity mechanics for Koink graduation >0.63%. P1: scaffold zkPresence adapter-solana.
- [Otto Music Technical Direction & Chain Fit](project_otto_music_chain_fit_2026_04_13.md) — PIPELINE COMPLETE 6.5/10 (post-corrections). CHAIN = OPEN QUESTION (Base vs Polygon zkEVM — conflicts with on-chain-architecture doc). Zero .sol files for Otto Music (concept phase, grep-verified). 11 memories + 1 note stored (551809c1). 5 patches applied. Documented contract names: OttoMusicRights/RoyaltySplitter/StreamingPayment/PublishingRights. P0: resolve chain selection before writing first contract.

## Active Research (2026-04-12)

- [SOS Technical Direction & Chain Fit](project_sos_chain_fit_2026_04_12.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). Base=Phase 1 chain (Aragon OSx + VRF v2.5 both live). 4 core contracts BUILT+TESTED (DPCRegistry/GovernanceWeight/ElectionEngine/CouncilManager). 2 critical patches: (1) IRV/sortition conflation fixed — ElectionEngine uses IRV, elections CAN run without VRF; VRF sortition designed-not-built (separate path). (2) MIT license confirmed — grants (W3F+Gitcoin GG24) path CLEAR. Gaps: Aragon DPC plugin (no code), labor contracts (6 designed, 0 built), 505-web (0 web3). DB note: 2e838710. P0: build Aragon OSx DPC plugin + LaborAttestation.sol.
- [High-Performance Chains](project_hiperf_chains_2026_04_12.md) — PIPELINE COMPLETE (validation SKIPPED/rate-limit). 7 memories + 1 note stored (4c6693b3). Hyperliquid=EXTEND not build (crypto.py:69). Berachain PoL v2=ONEON tokenomics template. Sonic FeeM=dApp incentive benchmark. MegaETH=centralized by design (not suitable for ONEON). P0: wire HyperEVM + apply PoL v2 to ONEON ADR.
- [Appchain Frameworks SOS/ONEON](project_appchain_frameworks_2026_04_12.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). Cosmos SDK=leading candidate (MEDIUM). Chain gap confirmed (HIGH, grep-verified). 4 corrections: Claims 1+3 HIGH→MEDIUM, IBC-Midnight NOT viable, TPS "(target, Q4 2026)". DB note: cf8e7459. P0: draft chain-selection ADR.
- [Ethereum Ecosystem L1+L2 Landscape](project_ethereum_ecosystem_2026_04_12.md) — PIPELINE COMPLETE 7.5/10 (post-corrections). Base=primary chain ($10.72B TVS). Pectra live (70% L2 fee cut). 3 survivors: Base+Arbitrum+OP. CRITICAL: ONEON+Panik+Koink ALL have zero chain integration code (grep-verified). Only zkPresence confirmed (Base Sepolia+SP1). DB note: 8a269d25. P0: deploy all 3 to Base Sepolia.
- [Quantum Attacks on On-Chain Reputation Systems](project_quantum_reputation_attack_vectors.md) — PIPELINE COMPLETE 8.5/10 (post-corrections). oprlp-contracts fully ECDSA-dependent (DPCRegistry.sol:17, VALIDATOR_ROLE, CONFIG_ROLE). 9 novel attack vectors (zero prior lit). DPC algorithm PQ-safe; address binding NOT. DB note: 754a8ce4. CRITICAL: CONFIG_ROLE/setRegistry() = most severe single-key attack.
- [zkPresence Biometric ZK Dynamic Key Research](project_zkpresence_biometric_zk_key_research.md) — PIPELINE COMPLETE 7.5/10. Fuzzy extractors viable (CCS 2025: 105-bit iris). zkLogin pattern=adapt for bio+passphrase. BLOCKER: Argon2-inside-ZK path A vs B unresolved. P0: fix circuit/main.rs todo!(). PLONK migration=new on-chain verifier.

## Active Research (2026-04-11)

- [Mid-Task Context Injection Feasibility](mid_task_context_injection_2026_04_11.md) — VALIDATED 8/10. CLI injection NOT supported. --print mode OPTIMAL (implemented). PreToolUse/PostToolUse = settings.json hooks (NOT Python SDK). tmux bracketed paste = best-documented workaround. Top action: add hooks to settings.json.

- [zkPresence Competitive Landscape](project_zkpresence_competitive_2026_04_11.md) — VALIDATED 7.5/10. SP1 6.1.x, circuit BROKEN (todo!()+ECDSA absent), zero tests, no competing OSS SP1 protocol. OSS path: precompiles->tests->publish->grants.
- [CORAL arXiv 2604.01658](coral_multi_agent_evolution.md) — VALIDATED 8.5/10. MIT/NUS/Stanford. Cross-agent memory +17% improvement. GAPS: stagnation detection ABSENT in autoevolve.py, cross-task leaderboard ABSENT. Skill extraction IMPLEMENTED.
- [Panik Technical Direction](panik_technical_direction.md) — VALIDATED 8/10. Base=primary chain, OP Retro Funding $3B. DPCRegistry LazyDecay reusable. Contract gaps: $PNK, soulbound, ZK creds. SP1 NOW, Midnight Q3 2026+.

## Architecture & ZK Research (2026-04-10)

- [ZK ONEON Architecture](zk_oneon_architecture.md) — PIPELINE COMPLETE 7.5/10 (2026-04-12). ONEON=zero ZK (grep-verified). SP1=P0 (self-hosted prover, define predicate first). Aztec/Noir BLOCKED July 2026. PATCHED: source label on Aztec claim + proof system matrix (Aztec→Noir/Honk). 3-phase: SP1 Base->L3 RaaS->sovereign. Note ID: 2bfcac20.
- [ZK Developer Ecosystem](~/otto/docs/zk-ecosystem-research-2026-04-10.md) — 8/10. SP1 Hypercube production leader. Risc0 Bonsai pre-alpha. Jolt experimental. Proving 45x cheaper 2025.
- [ZK Chain Landscape](~/otto/research/zk-chain-landscape-2026.md) — 8/10. 10 chains covered. Polygon zkEVM SUNSETTING. Aztec vuln March 2026. Midnight live March 2026.

## AI Frameworks & Self-Improvement (2026-04-05)

- [OpenClaw + 2026 AI Landscape](openclaw_ai_landscape.md) — VALIDATED 8/10. Otto moats: 6-layer memory, RL2F+MARS+AutoEvolve (unique). A2A+OTel gaps RESOLVED. MCP dynamic tool composition still valid gap.
- [Google A2A v1.0](a2a_standard.md) — IMPLEMENTED. a2a_standard.py fully built. v1.0 spec released 2026-03-12, 150+ orgs.
- [AI Landscape Benchmark](~/otto/docs/ai-landscape-synthesis-2026-04-05.md) — GAPS CORRECTED. OTel+A2A present. MCP gap remains. Tier-1: LangGraph/CrewAI/ADK/AG2.
- [OmniMem arXiv 2604.01007](project_omnimem_2604_01007v1.md) — 8/10. BM25 hybrid search=P1 (DEPLOYED), pyramid retrieval=P2, prompt constraints before questions=P3.

## Market & Strategy Research (2026-04)

- [AI Consulting B2B](ai_consulting_b2b.md) — VALIDATED 8/10. $11-14B market (2026). SMB underserved. Fix-the-failure consultant play. 5-article LinkedIn series.
- [Frontend Job Market 2026](project_frontend_job_market_2026.md) — Senior FE $145K-$181K base. Mev anchor: $200K-$280K Web3 infra lead. Top: Chainlink, Alchemy, Anthropic, Vercel.

## Blockchain & Token Research (2026-03-29)

- [Midnight Network](project_midnight_network_2026_04_01.md) — VALIDATED 8/10. Mainnet LIVE Mar 30 2026. $808M cap. Halo2 ZK. Aliit Fellowship grants (9.6B NIGHT). No public audits.
- [Agent-on-Chain Money](agent_on_chain_money.md) — Virtuals $477M aGDP, OLAS/Polystrat 37% profitable, Bittensor $43M rev (but $52M subsidy). Skeptic: subsidy-masked, $5.8B rug pulls.
- [Sri Lanka Economic Readiness](sri_lanka_economic_readiness.md) — POSITIVE with prerequisites. Port City SEZ has crypto licenses. CRITICAL: no legal entity=zero access. BOI registration=step 0.
- [Nation-State Crypto Adoption](nation_state_crypto_adoption.md) — VALIDATED 8/10. Bhutan+UAE+SOS=winning frame. El Salvador=dead model. IMF line: infra/reserve OK, legal tender blocked.

## Capital & Grants (2026-03-28)

- [Ottolabs + Tusita Capital](~/otto/docs/ottolabs-capital-synthesis-2026-03-28.md) — Lemnos Labs P0 VC. EU EIC STEP. Tusita: UNDP Green Bond. Blocker: pre-prototype, grants only.
- [Tusita Capital Landscape](~/otto/docs/tusita-capital-synthesis-2026-03-28.md) — VALIDATED 8/10. P0: UNDP Green Bond. P1: ADB $100M. P2: CBI/NFT fractional. Prerequisite: no entity/site/permits.
- [Grant Landscape 2026](~/otto/projects/capital/grants_landscape_2026_march.md) — W3F grants DISCONTINUED. P1: ENS Public Goods ($12-50K). P2: Solana grants ($30-50K). P3: Gitcoin GG25 Q2 2026. P4: Deep Funding ($100K). P5: EF ESP.

## Self-Improvement Research (2026-03-27)

- [STEM Agent Research](stem_agent_research.md) — VALIDATED 8/10. P1: Caller Profiler (FULL GAP). P2: Skills maturation trigger. P3: Failure-branch adaptation. GATE: license unconfirmed.
- [Three-Paper Synthesis (HiClaw+TrustGraph+VISTA)](three_paper_synthesis.md) — P1: VISTA hypothesis loop. P2: Context Cores schema. Architecture parity: Otto matches HiClaw structure.
- [Constraint-Injection Checkpoints](project_constraint_injection_research.md) — P7: PG-CoT gates in heartbeat.md. P6: RL2F idle-cycle fix. P5: S-MMU similarity threshold.
- [OMNIFLOW arXiv 2603.15797](omniflow_research.md) — PG-CoT experiment: 1 checkpoint at REFLECT->DECIDE. Frozen LLM corroborates no-training direction.
- [Context Rot (Chroma 2026)](context_rot_research.md) — Shuffled haystacks outperform structured text. S-MMU inject at START. Context <50% capacity.
- [Recursive Language Models arXiv 2512.24601](project_rlm_recursive_language_models.md) — 100x context via metadata handles. S-MMU lazy-loading opportunity.
- [Context Engineering 2026](project_context_engineering_2026.md) — 4-strategy: Write/Select/Compress/Isolate. Gaps: no Tool RAG, no memory evolution, no learned memory mgmt.

## Infrastructure Research (2026-03-17)

- [Vulnerability Intelligence DB](vuln_intelligence_db.md) — security/* API, 80 vulns, 6h auto-sync. NVD+DeFiHackLabs+MITRE ATLAS.
- [BANKR Bot](project_bankr_bot_research.md) — REST API, LLM gateway, 16 skills. Integration: Agent API + signals + launch CLI.
- [AutoResearchClaw](project_autoresearchclaw_eval.md) — VERDICT: Do NOT adopt. Build native LitSearch using OpenAlex+Semantic Scholar.

## Community & Token Design (2026-03-17)

- [Web3 Community Collab](project_community_collab_eligibility.md) — Top: BONK, Gitcoin, Farcaster, Optimism, BanklessDAO. 4-tier token eligibility + Alignment Score.
- [Sybil Resistance](project_sybil_resistance_2026.md) — Best: World ID (38M users, ZK). Easiest: Human Passport. Wallet age gate <30d=reject.
- [Token Launch Filtering](project_launch_filtering_antsniper.md) — Batch/Auction>Decaying Fee>Open Pool. $KOINK: Human Passport->Meteora Alpha Vault->VRF->Fee decay.
- [Dormant Token Decay](~/otto/projects/capital/dormant_token_decay_design.md) — Decay governance weight, never balance. 5yr half-life contributors, 18mo circulating.
- [Decentralized Intelligence Layer](~/otto/projects/capital/decentralized_intelligence_layer.md) — 4-layer: Govern->Train->Eval->Self-Evolve. $KOIN votes, FedRLHF, InfiCoEvalChain.

## Reference

- [NS.com / Network School](reference_ns_network_school.md) — Balaji's residential society, Singapore. Apply for Tusita alignment.
- [SOS Systems Crisis Data](reference_sos_article_crisis_data.md) — 121M displaced, 244 internet shutdowns (2025 record), Sudan/Gaza hospital collapse.
- [Claude Dynamic UI](project_claude_dynamic_ui_research.md) — show_widget tool-call pattern, morphdom streaming, Vercel AI SDK for OMS.
- [Crypto Signal Channel](~/otto/projects/alpha/SIGNAL_REVENUE_RESEARCH.md) — DEPRIORITIZED. Archived.
- [On-Chain Alpha Strategies](~/otto/projects/alpha/ONCHAIN_ALPHA_STRATEGIES_RESEARCH.md) — DEPRIORITIZED. Archived.

## Research Protocols

- **Always validate claims** with code grep/file check before storing. Tag confidence: VALIDATED/RESEARCHED/UNVERIFIED.
- **DB Note IDs** are stored in each memory file for cross-reference to semantic memory.
- **GATE: Aztec/Noir** — Do NOT recommend for production until July 2026 (critical vuln March 2026).
- **GATE: Polygon zkEVM** — SUNSETTING 2026. Do not deploy.
- **GATE: STEM Agent** — License unconfirmed. Do not implement code.
- **BM25 hybrid search** — DEPLOYED & VERIFIED (cycle 532). No longer a gap.

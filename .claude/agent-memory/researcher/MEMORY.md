# Researcher Agent Memory

## CORAL arXiv 2604.01658 — Multi-Agent Evolution Framework (2026-04-11) — VALIDATED 8.5/10

DB Note ID: dd1284c1 | Semantic IDs: bb433b03, 1c441700, def9acc8, f6b43ac3, ea14929d, 830a4fb5, 59ea3806
- **NOT ZK** — ZK routing tag was an error. Architecture/self-improvement paper from MIT/NUS/Stanford/Meta/Amazon/Microsoft.
- **Cross-agent memory lift**: 36% cross-parentage → 17% improvement rate vs 9% overall; +55% on kernel engineering.
- **GAP: Stagnation detection ABSENT** (grep-verified) — no consecutive-failure counter in autoevolve.py or rl2f.py. Only a static string.
- **GAP: Cross-task leaderboard ABSENT** (grep-verified) — no best-outputs registry for new tasks to inspect.
- **IMPLEMENTED: Skill extraction** — tasks.py:_extract_skill_from_task (~line 1346), uses Kimi/Haiku via llm_chat(), exit_code==0 only.
- **PATCHED FACTS**: (1) LLM = Kimi/Haiku not Gemini Flash. (2) Worktree = PARTIAL MATCH (qa_runner.sh only, not main dispatch).
- **Top actions**: (1) stagnation counter in autoevolve.py; (2) GET /tasks/top-outputs + {top_outputs} injection; (3) fix ZK-bleed in classifier.

## Panik Technical Direction & Chain Fit (2026-04-10) — VALIDATED 8/10

DB Note ID: c7659d99 | Semantic IDs: edd5a543, 0982a6ee, d35381d3, d737e671, 2f05e4c3, bc873b20, 24b2e5a6, cf46049f, be05b011
- **Base = primary chain** (CONFIRMED, code-verified). OP Retro Funding $3B pool = P0 grant path (public safety public good). No chain migration.
- **DPCRegistry.sol LazyDecay = REUSABLE** — `computeDecay()` on `getScore()` read in `/mnt/media/projects/oprlp-contracts/src/core/DPCRegistry.sol`. Extend for Panik trust scores.
- **Contract GAPS (all grep-verified absent)**: $PNK ERC-20, ERC-5484 soulbound badges, ZK credential verification, sybil resistance contract.
- **ZK path**: SP1 NOW (Aztec blocked July 2026) → Midnight Q3 2026+ (anonymous mode, EVM bridge Hua phase).
- **Polygon zkEVM BLOCKED** — sunsetting 2026. Do not deploy Panik contracts on zkEVM.
- **Celo = viable co-deployment** (MEDIUM) — 11M MiniPay wallets, phone-number DID, OP Stack L2. Grant amounts unconfirmed.
- **UI vs. reality gap**: OnChainTrust.tsx (DID+ZK), AgentNetwork.tsx (levels), PrivacyControl.tsx ($PNK rewards, AI on blockchain) — ALL aspirational, zero contract/backend behind them.

## ZK ONEON Architectural Decision Framework (2026-04-10) — VALIDATED 7.5/10

DB Note ID: 37279aaa | Semantic IDs: d06d8fa0, e4a48430, 7dcfaffc, e24e37df, f54ad20e, 380e2646 | File: ~/otto/.claude/agent-memory/research-synthesizer/zk_oneon_synthesis_2026_04_10.md
- **ONEON = zero ZK today** (grep-verified). AES-256-GCM + ECDSA only. No circuits/provers/verifiers anywhere.
- **SP1 = P0 NOW** — MIT, $4B+ secured, $0.04/proof. ⚠️ Prover Network testnet-only → self-host required. ⚠️ Predicate design step needed FIRST.
- **Aztec/Noir BLOCKED until July 2026** — critical vuln Mar 17 2026. Proof system = Noir/Honk (UltraHonk) NOT "Aztec" in matrices.
- **3-phase path**: SP1 on Base (NOW) → L3 RaaS ZK Stack (Q3 2026, Lens Chain = exact precedent) → sovereign chain (long-term)
- **Midnight = partner** (Aliit Fellowship, 9.6B NIGHT) — NOT a fork target (GitHub unresolvable deps)
- **⚠️ EXPLICIT BLOCKER**: Neo4j returned 500 during retrieval — do NOT finalize sovereign chain decisions until graph restored
- **Patches**: Claim 3 source attribution fixed (873df1fd → ecosystem doc); proof system matrix category fixed (Aztec→Noir/Honk)

## ZK Developer Ecosystem (2026-04-10) — RESEARCHED 8/10

DB Note ID: 8e098a84 | Semantic IDs: 8e014cd3, d9ce2470, 04133c5c, 888ec141 | File: ~/otto/docs/zk-ecosystem-research-2026-04-10.md
- **Toolchain bifurcation:** DSLs (Noir/Cairo/Circom/Halo2) for circuits; zkVMs (SP1/Risc0/Jolt) for general computation
- **SP1 Hypercube = PRODUCTION LEADER** — 99.7% ETH blocks <12s, Optimism/Base/Unichain (Feb 2026), $4B+ assets, MIT, 6M+ proofs 2025
- **Risc0** — zkVM production; Bonsai managed service PRE-ALPHA (don't use); Boundless testnet
- **Jolt (a16z)** — 5x faster than Risc0 claimed, EXPERIMENTAL, no recursion
- **Proving infra:** Succinct Prover Network (PROVE token, testnet→mainnet 2026); ZkCloud/Gevulot (PROOF token, Firestarter permissioned live Dec 2024)
- **Aztec CRITICAL BUG** (Mar 17 2026) — proving system vuln, v5 fix July 2026. Do NOT deploy Noir/Aztec production contracts before July 2026
- **RPC:** zkSync 6 providers, Starknet 8, Polygon 23, Aztec ZERO; The Graph strong on zkSync/Polygon, weak on Starknet/Aztec
- **Auditors:** Veridise (top ZK specialist), Trail of Bits (circomspect), Nethermind Security (Noir/Aztec), ZK Security (Halo2)
- **Grants:** EF $900K, Starknet $25K-$1M STRK, ZKsync 5M ZK tokens, Aztec active, Midnight 9.6B NIGHT (Aliit Fellowship)
- **ONEON actions:** SP1 for ZK-verified credentials (NOW); Aztec/Noir for private contracts (AFTER July 2026); Midnight for full privacy chain

## ZK Chain Landscape & Proof Systems (2026-04-10) — RESEARCHED 8/10

DB Note ID: f494d0a4 | Semantic IDs: 33200784, bdb5e743 | File: ~/otto/research/zk-chain-landscape-2026.md
- **10 chains covered:** zkSync Era (Boojum/Airbender STARK, 15K+ TPS, ZK Stack), Starknet (FRI/STARK, Cairo, decentralized sequencers live), Polygon zkEVM (SUNSETTING 2026→AggLayer/CDK), Scroll (OpenVM RISC-V, Type 3→1), Linea (SNARK, 15min finality, MetaMask), Mina (Kimchi PLONK, 22KB chain, L1), Aztec (**critical vuln March 2026, v5 fix July**), Taiko (Type 1, no sequencer, based rollup), Midnight (Halo2, live March 2026, compliance-native), Aleo (Varuna/Marlin, privacy-by-default L1).
- **Proof systems:** Groth16 (192B, cheapest verify), PLONK variants (Halo2/Kimchi/Honk), STARK/FRI (post-quantum, no trusted setup), OpenVM/SP1/risc0 (zkVM, replacing hand-written circuits).
- **CRITICAL:** Polygon zkEVM sunset = SOS Systems must migrate. Aztec vuln = Midnight only viable ZK privacy chain until July 2026.
- **Cost trend:** Proving 45x cheaper in 2025 ($1.69→$0.0376/proof). Airbender (zkSync) 10x+ over Boojum.
- **SOS chain recs:** Scroll/Linea for governance, Midnight for privacy, Taiko for decentralized rewards, Polygon CDK for cross-chain.

## OpenClaw + 2026 AI Landscape (2026-04-05) — VALIDATED 8/10

DB Note ID: 31036364 | Episodic IDs: 37997294, 83a39ec4, c70e7990, f8e19e8d, 5bf2a82a, 87f50acf
- **OpenClaw** (MIT, 163K-250K stars, Peter Steinberger): heartbeat+memory+channels+skills = architectural twin of Otto. Otto moats: 6-layer memory, RL2F+MARS+AutoEvolve (unique — zero equivalents in all 9 frameworks).
- **GAP CORRECTIONS:** A2A "gap" is RESOLVED (a2a_standard.py confirmed). OTel "gap" is RESOLVED (telemetry.py confirmed). Prior MEMORY entries claiming these as gaps are STALE.
- **NEW 2026 FRAMEWORKS** (missing from 03-28 synthesis): AWS Strands (A2A native), MS Agent Framework (AutoGen+SK merged), Mastra (TS, YC, 300K npm/wk), Vercel AI SDK v6, OpenAI Symphony (Elixir/BEAM).
- **2026 LANDSCAPE:** Memory=differentiator (3/9 frameworks). Tool calling=commoditized. MCP=table stakes. Otto RL2F=unique moat.
- **ACTION:** Update LinkedIn article 45407c6d to add OpenClaw + 4 new frameworks to comparison table.

## Google A2A v1.0 — IMPLEMENTED (2026-04-05)

DB Note ID: f954bf58 | a2a_standard.py FULLY IMPLEMENTED. Agent Card, JSON-RPC 2.0, SSE, task lifecycle confirmed.
- **SPEC:** v1.0 released 2026-03-12, Linux Foundation, Apache 2.0, 150+ orgs. A2A≠MCP: MCP=agent↔tool; A2A=agent↔agent.
- All gaps RESOLVED. Historical analysis archived in episodic IDs: d75eebec, efca08c2, 992d7719, a72f6594.

## AI Agent & Orchestration Landscape Benchmark (2026-04-05) — GAPS CORRECTED

DB Note ID: f838eb95 | File: ~/otto/docs/ai-landscape-synthesis-2026-04-05.md
- **MOATS (code-verified):** 6-layer memory; RL2F+MARS+AutoEvolve (unique); 182-agent catalog; DAG task plans; QA budget gate.
- **GAP CORRECTIONS:** OTel PRESENT (telemetry.py). A2A PRESENT (a2a_standard.py). MCP dynamic tool composition gap still valid.
- **TIERS:** Tier-1: LangGraph/CrewAI/Google ADK/AG2. Tier-2: Strands/Pydantic AI/Mastra. Tier-3: Bittensor/Virtuals/OLAS.
- **REMAINING ACTION:** MCP dynamic tool composition.

## OmniMem — Lifelong Multimodal Agent Memory (2026-04-05) — RESEARCHED 8/10

DB Note ID: 22efbf05 | Episodic ID: 687bfb45 | File: project_omnimem_2604_01007v1.md | Summary: ~/otto/research/papers/2604_01007v1_summary.md
- **PAPER:** Omni-SimpleMem arXiv 2604.01007v1. AutoResearch-discovered architecture. F1 0.117→0.598 LoCoMo (+411%) in 72h, 50 autonomous experiments.
- **ARCH:** MAU={summary+embedding+cold_ptr+timestamp+modality+links}. Pyramid retrieval (3 levels, token budget). FAISS+BM25 set-union. KG 7-entity h-hop expansion.
- **HEADLINE:** Bugs (+175%) + architecture (+44%) + prompts (+188%) each beat cumulative hyperparameter tuning. AutoML misses the biggest wins.
- **OTTO P1:** BM25 hybrid search MISSING — add pg_trgm/tsvector alongside pgvector, set-union merge. +30-50% recall.
- **OTTO P2:** Pyramid retrieval MISSING — S-MMU loads flat, 3-level pyramid reduces context rot.
- **OTTO P3:** Prompt constraints should go BEFORE questions (zero code, all agent prompts).
- **NOTE:** Semantic/remember blocked (OpenAI quota P8). Stored episodic + research note only.

## AI Consulting B2B Landscape (2026-04-03) — VALIDATED 8/10

DB Note ID: 1d60436e | Episodic ID: 6abb779a | Semantic IDs: 07567311, 46ea4fa5, f84ec2bb, ddf1a3b0, 08fef7ca, 78bf1b16, 684c60d1
- **MARKET:** $11-14B (2026) → $91-117B by 2035, 26-36% CAGR. Mid-market 500-999 employees fastest-growing (27.9%). Finance 22.3%, N. America 36%+.
- **BUYER STATE:** Burned. ~90% AI projects failed (directional, single primary source — cite carefully). 25% 2026 spend deferred. CFOs gate; only 29% measure ROI confidently.
- **GAP:** Big 5 enterprise-only ($500K-$10M). SMB underserved. Boutiques 40-60% cheaper. Trilemma: data fragmentation + talent gap + cost overrun simultaneously.
- **MEV PLAY:** Fix-the-failure consultant. AI Readiness Assessment ($3K-$8K, 6-pillar). 5-article LinkedIn series. Target 50-500 employee SMBs in finance/manufacturing/logistics.
- **PATCHED:** CAGR 26%→26-36%; market $90-116B→$91-117B. DISCARDED: $18M SaaS waste (single source).

## Midnight Network Research (2026-04-01) — VALIDATED 8.0/10

DB Note ID: 97be3f13 | Episodic IDs: bc629021 (I1), aac96e80 (I2), c6b5ad63 (I3), bbf67b61 (I4), 380517e8 (I5), 449d95a5 (I6), bd897221 (I7)
File: project_midnight_network_2026_04_01.md
- **Mainnet LIVE Mar 30 2026** (Kūkolu federated). $808M cap, NIGHT on Binance/Kraken/OKX. Monument Bank £250M RWA. Validators: Google Cloud, Blockdaemon, MoneyGram, Worldpay, Telegram, eToro, Bullish, Pairpoint.
- **Tech:** Substrate/Rust + AURA/GRANDPA + Halo2 ZK (BLS12-381, recursive, no trusted setup). Compact DSL. Client-side proving. NIGHT + DUST dual-token.
- **Roadmap:** Mōhalu Q2 2026 (SPO decentralization), Hua Q3 2026 (ETH/SOL bridges).
- **ONEON ZK gap CONFIRMED:** Zero implementation in codebase. No Midnight integration in any project dir (only UI color refs).
- **Grants:** 9.6B NIGHT ecosystem reserve. Aliit Fellowship active (rolling). Amounts/deadlines UNCONFIRMED.
- **PATCHED:** Glacier Drop thaw Dec 2026 → **~Feb 2027** (450-day math). MCP server downgraded MEDIUM-LOW (self-referential source).
- **Risk:** No public security audits. Centralization paradox. Token unlock pressure Feb 2027.
- **Actions:** (1) Apply Aliit Fellowship for ONEON (confirm deadlines). (2) Build Compact DSL PoC. (3) Gate at Mōhalu Q2 2026.

## Agent-on-Chain Money Narrative (2026-03-29) — VALIDATED

DB Note ID: 161c9b5a | Memory IDs: a19be2a5, d2e54828
- **Virtuals Protocol (Base):** 18K+ agents, $477M aGDP, $64.73M cumulative fees, $2.63M/month. ACP = first full lifecycle agent-to-agent commerce standard, distributes $1M/month to top agents.
- **OLAS/Polystrat:** 4,200+ Polymarket trades in first month (launched Feb 2026), peak single-trade return 376%, 37% of agents profitable. CoinDesk Mar 15 2026.
- **Bittensor:** $43M Q1 2026 organic revenue BUT $52M in subsidies — genuine external rev only $3-15M. Subnet Chutes $22K/day.
- **elizaOS (AI16Z):** Migrated Feb 4 2026 from meme fund. 50K+ agents managing $20B+ claimed. Token -38% post-migration.
- **AIXBT:** Peaked $500M mktcap. Token-gated access (600K token threshold). x402 removed subscription need.
- **Bankr Bot (Base/Solana):** 1.2% swap fee, 57% to creators. BNKR ATH $0.00122 Feb 10 2026. $57M weekly volume.
- **Chains:** Solana = 65% of agentic payments. Base = ACP + x402 infrastructure hub. BSC = official standards push.
- **Infrastructure gaps:** Agent authorization/spending policies, dispute resolution, agent identity (ERC-8004 early), service atomicity, interoperability between ecosystems. x402 = only $28K/day (near zero demand).
- **Skeptic view:** Bittensor subsidy-masked revenue, $5.8B rug pulls since Jan 2025, x402 "demand is essentially zero," Virtuals aGDP is market cap of agent tokens NOT actual revenue.
- **Origin narrative:** Truth Terminal → $50K Marc Andreessen donation → GOAT meme coin $300M mktcap → AI16Z $250M → entire sector spawned.

## Sri Lanka Economic & Political Readiness (2026-03-29) — VALIDATED

DB Note ID: b704b223 | Memory IDs: e5378dd6, 7b2bf835, 9e77f8f1, c4e603e5, 89a157b4, 14f096a1, bff4dcc1, 5ce3a52f

- **Verdict: POSITIVE with prerequisites.** Best political window in SL history for tech-sovereign proposal.
- **Port City Colombo SEZ:** First 2 crypto licenses issued 2024. Legal sandbox for crypto ops TODAY. Resolves Stripe exclusion.
- **Dissanayake admin:** Chairs Ministry of Digital Economy personally. $98M 2026 digital budget. SL-UDI (blockchain identity) live. 200K AI/fintech training target.
- **Economic recovery:** GDP 5% (2024), reserves $6.1B→$9B+ (2025), IMF 4th review July 2025. Fragile: 24.5% poverty, 3.5% projected 2026.
- **Green Bond Framework:** UNDP-backed, 12 instruments, $11.26B sovereign target 2030. Private sector eligible NOW.
- **Crypto direction:** Gray zone → VASP regulation (not ban). VASP/AML timeline unconfirmed.
- **CRITICAL BLOCKER:** No legal entity = zero access to any capital instrument. BOI registration is step 0.
- **Order of ops:** (1) Register BOI entity → (2) Engage Ministry of Digital Economy → (3) Structure via Port City SEZ → (4) UNDP Green Bond / ADB.
- **Patched facts (Step 2 validation):** GDP 4.5%→5%, reserves $5.9B→$6.1B, IMF 3 reviews→4th review July 2025.

## Nation-State Crypto Adoption Blueprints — SL Application (2026-03-29) — VALIDATED 8/10

DB Note ID: 0e8ad530 | Correction Memory: f17fc237

- **Winning frame:** Bhutan (sovereign reserve) + UAE (regulatory hub) + SOS (governance) = Digital Economic Development Zone. IMF-compatible. NOT El Salvador.
- **Failed model:** El Salvador mandatory legal tender → 92% non-usage → IMF reversal Jan 2025. Dead. Do not repeat.
- **Reserve model:** US ~198K BTC at EO signing (NOT 328K — includes seizures); Bhutan $374M; voluntary hold only.
- **Hub model:** UAE VARA zero tax, Singapore licensing, Switzerland DLT Act = tax clarity + licensing + govt blockchain = capital/talent magnet.
- **SL window:** BOI FDI open; $11.26B UNDP green bond LIVE; CBSL AML/CFT guidelines status UNCONFIRMED (may have hardened by March 2026 — verify before engagement).
- **IMF line:** Infrastructure/reserve = compatible. Legal tender = blocked (El Salvador proves it).
- **Prerequisite chain:** (1) SL legal entity → (2) CBSL/BOI engagement (verify window first) → (3) Proposal doc as architect not applicant.
- **PATCHED:** 23-nations BTC claim → 4-5 intentional reserves only. US figure → ~198K not 328K.

## Ottolabs + Tusita Capital Landscape (2026-03-28) — VALIDATED

DB Note ID: 00d9c114 | Memory IDs: 14ca3ced, d21a6f47, c330fd92, 21c10c78, 1e2a2060
Output doc: ~/otto/docs/ottolabs-capital-synthesis-2026-03-28.md

- **Ottolabs P0 VC:** Lemnos Labs ($500K-$3M seed, hardware specialist, agri/logistics/industrial) — not in existing capital docs, confirmed gap
- **Framing:** Sovereign manufacturing + RaaS model = strongest narrative. Lead with these, NOT "hardware startup."
- **Grants (pre-MVP):** EU EIC €300M STEP Scale Up — requires mfg LOI + customer LOI + 40% path-to-market. EIC eligibility for Sri Lanka **UNVERIFIED** — check eic.ec.europa.eu before writing.
- **Tusita P0:** UNDP Sri Lanka Green Bond Framework (UN-backed, live 2026, 12 instruments). Frame as PPP-eligible sovereign eco-community.
- **Tusita market:** $248B→$945B ecotourism by 2034 (14.31% CAGR). ESG premium 15-20%.
- **Blocker:** Ottolabs pre-prototype — no VC closes pre-MVP. Grants only until prototype exists (~12-18mo).
- **Separation required:** Ottolabs (hardware VC + EU grants) vs Tusita (green bonds/PPPs) are SEPARATE strategies.

## Tusita Islands & Resorts Capital Landscape (2026-03-28) — VALIDATED (8.0/10)

DB Note ID: 859db83c | Memory IDs: fe53f1c8, 4fff61df, 14b9cad0, 000350a5, 31283ac8, c4e603e5, 79fc5f40
Output doc: ~/otto/docs/tusita-capital-synthesis-2026-03-28.md | Strategy doc: ~/otto/projects/capital/tusita_islands_capital_strategy.md

- **PREREQUISITE (validator):** Tusita has NO legal entity, NO physical site, NO permits today. ALL instruments require these. Capital docs are planning instruments, not immediately submittable.
- **P0 UNDP Green Bond Framework:** 12 instruments live 2026, UN-backed. PPPs require formal SL govt partner. Best entry: green bonds + debt swaps.
- **P1 ADB $100M SL tourism:** May qualify (MEDIUM confidence) — requires entity + docs + govt backing.
- **P2 CBI/NFT fractional model:** Six Senses Grenada analog ($270K Founder tier proposed — verify tokenomics spec). Retail raise path, no institutional approval needed.
- **P3 SL Sovereign Green/Blue Bond:** $11.26B target 2030. Private issuers eligible now.
- **P4 GEF VI + BOI FDI:** Non-dilutive entry. NSTCS certification unlocks ESG premium (15-20%).
- **UNVERIFIED:** EIC STEP (€300M EU, SL eligibility TBC), EIB ($4.5B, SL geographic mandate TBC).
- **Island jurisdiction gap:** SL maritime sovereignty, leasehold vs freehold — unaddressed, investigate before any submission.

## STEM Agent Research (2026-03-27) — VALIDATED (8/10)

DB Note ID: ebac875b | Memory IDs: 0667081c, 72731a66, 0b40a3fa, 1fd66423, ab85fd5e, 6ece3366, c04ca7aa

- **[P1 ACTION]** Caller Profiler: FULL GAP — implement 5-8 dim tracker for Mev (preferred response length, agent types, task categories, time-of-day, comms register). Store in semantic memory, inject into heartbeat context.
- **[P2 ACTION]** Skills Maturation trigger in reflection agent: detect same agent_type + similar prompt 3+ times → auto-propose workflow template to Mev. Highest compound-growth leverage.
- **[P3 ACTION]** Failure-branch adaptation in task_runner.sh: on non-zero exit, log failure pattern to semantic memory; retry with alternate agent on known failure classes. Addresses RL2F 32% decline.
- **[GATE]** Do NOT implement any STEM code until license confirmed at alfredcs/stem-agent GitHub.
- **[CAUTION]** Pre-print (March 2026), 0 citations. Recency flag on all claims.
- **[ARCHITECTURE]** 5 STEM layers: Protocol Gateway (A2A/AG-UI/A2UI/UCP/AP2), Tool Management (dynamic), Self-Adaptation (failure-triggered), Agent Comms (pub-sub), Memory (sub-linear).
- **[GAPS]** Full: Caller Profiler, MCP, Dynamic Tool Composition. Partial: Self-Adaptation (RL2F cross-session only), Protocol gateway (2 vs 5 channels), Memory (not sub-linear verified).

## Three-Paper Synthesis: HiClaw + TrustGraph + VISTA (2026-03-24) — VALIDATED

DB Note ID: 9dacc65b | Memory IDs: b8caf97a, 892df600, 57c6abad, 6819725c, a2f3d976, de793994, 1cd61702, aabbf1b8

- **[P1 ACTION]** VISTA hypothesis loop (~$3): Parse existing `qa_rejection_reason` into {failure_type, hypothesis} labels, inject into retry task prompts. NOT a new field — `task_retry_feedback` already has the field. Gap is structured categorization + prompt injection.
- **[P2 ACTION]** Context Cores (~$5, design-first): Postgres schema `context_cores(id, domain, version, ontology_json, provenance_json, retrieval_policies_json, promoted_at)`. Domains: webassist/koink/sos_systems.
- **[P4 LOWEST]** Credential isolation: task_runner.sh inherits via systemd env, no literal key. Risk LOW. Sprint backlog score 1.7/25.
- **[ARCHITECTURE]** Otto already matches HiClaw (DAG=Manager) and TrustGraph (Neo4j/pgvector=KG+vectors). Gaps are additions, not rebuilds.
- **[CONVERGENCE]** All 3 papers: add structure at every stage. HiClaw=dispatch, TrustGraph=retrieval, VISTA=failure diagnosis.
- **[OMNIFLOW PAIRING]** OMNIFLOW (constrain-before) + VISTA (diagnose-after) = closed optimization loop.
- **[CAVEATS]** VISTA benchmarks math-domain only (GSM8K). Context Cores $5 estimate rough. VISTA CC BY-NC-ND — re-implement, do NOT copy.
- **[DO NOT ADOPT]** Matrix/Tuwunel (500MB), ZeroClaw/NanoClaw (unstable), TrustGraph Cassandra/Pulsar (incompatible stack)

## HiClaw Multi-Agent OS Architecture Research (2026-03-24)

DB Note ID: f934ccf3 | Memory IDs: d829a87e, ffb52319, 3120a463, 02c9d695, 98f2052a

- **[DONE]** Artifact-path references: commit 9253b59 merged. hiclaw-artifact-path-architecture-2026-03-24.md exists.
- **[CONTEXT]** Architecture parity confirmed: Otto already matches HiClaw at structural level.
- **[DO NOT ADOPT]** Matrix/Tuwunel (500MB overhead, overengineered), ZeroClaw/NanoClaw (in development, not production)

## Constraint-Injection Checkpoints Research (2026-03-23)

Research file: ~/otto/.claude/agent-memory/researcher/project_constraint_injection_research.md
DB Note ID: 3f2c120e | Memory IDs: eae83da8, 98591a29, 6600825b, 69b7712c

- **[P7 IMMEDIATE]** Add 3 PG-CoT gates to heartbeat.md: budget check post-WHY ($0.10 threshold), directive check post-DECIDE, idle_cycle tag post-EXPECTED. Start with binary budget gate. File: `heartbeat.md`
- **[P6]** RL2F idle-cycle fix: 29/50 window = idle predictions (queue=0/0/0) — zero learning signal. Tag `idle_cycle: true/false` at write, report `active_cycle_accuracy` separately. Independent from P7 fix.
- **[P5]** S-MMU: add `similarity_threshold=0.7` to slice injection — near-misses to L2. File: `smmu.py`
- **[DEFERRED]** SSA telemetry formatter (no new urgency) — carry forward
- External consensus: LlamaFirewall, SagaLLM, Task Shield, OMNIFLOW all validate mid-chain constraint injection

## BANKR Bot Research (2026-03-19)

Research file: ~/otto/.claude/agent-memory/researcher/project_bankr_bot_research.md

- **Platforms**: X, Farcaster, Base App, XMTP. Chains: Base, ETH, Polygon, Solana
- **Wallet backend**: Privy server wallets. DEX routing: 0x Swap API v2, Doppler/Uniswap V4, Raydium
- **Token launch**: Doppler fair launch Base (57% to creator), Raydium bonding curve Solana (0.5%/trade)
- **Agent API**: REST at api.bankr.bot — async job (POST prompt → poll jobId). Key format: `bk_...`
- **LLM Gateway**: OpenAI-compatible proxy at llm.bankr.bot. Rate: 60 req/min
- **Skills repo**: github.com/BankrBot/skills (16 skills: signals, neynar, Farcaster, QN RPC, Veil)
- **BNKR token**: Base ERC-20, 100B supply. Coinbase Ventures backed. ACP integration Jan 2026.
- **Otto integration**: Agent API (trading), LLM Gateway (route calls), bankr-signals (verified publishing), bankr launch CLI ($KOINK), Neynar skill (Farcaster)

## AutoResearchClaw Evaluation (2026-03-18)

DB Memory ID: da77499a | Research file: ~/otto/.claude/agent-memory/researcher/project_autoresearchclaw_eval.md

**Verdict: Do NOT adopt.** Build native `LitSearch` using OpenAlex API (free) + Semantic Scholar (free tier).
- **Crawl layer (stages 3-6)**: OpenAlex + Semantic Scholar + arXiv with query expansion — better than Otto's ad-hoc WebFetch
- **Problem**: 23-stage paper generator. Otto needs implementation signal, not papers. Requires OpenAI key.

## Frontend Job Market 2026 — Senior FE + Engineering Lead (2026-04-06)

File: project_frontend_job_market_2026.md
- **SALARIES:** Senior FE median $145K–$181K base ($181K–$240K total). Engineering Lead $181K–$205K base ($220K–$300K total). FAANG senior FE: $400K–$700K+ total. Coinbase FE: $415K total. Web3 infra: $180K–$350K + token grants.
- **SKILLS:** TypeScript + React + Next.js = non-negotiable. AI API integration (streaming UIs, MCP) = rapidly required. ethers.js/viem/wagmi = Web3 differentiator.
- **TOP TARGETS:** Chainlink Labs + Alchemy (Web3, highest probability). Anthropic + Vercel (AI-first, highest prestige). Coinbase (61 active FE roles). xAI ($240K+ base, actively recruiting).
- **MARKET:** Employer's market overall (5.8% tech unemployment). 90K+ cuts in 2026. BUT: scarcity premium for senior AI + Web3 specialists. Candidate leverage exists in this carve-out.
- **MEV ANCHOR:** $200K–$280K base for Web3 infra lead. $400K+ total comp target for AI labs. Lead CV with oracle infrastructure + agent systems, not "15yr frontend."

## Decentralized Intelligence Layer Architecture (2026-03-17)

Design doc: ~/otto/projects/capital/decentralized_intelligence_layer.md
DB Memory IDs: c7fe43ae (architecture), 838af093 (research primitives)

4-layer protocol: Govern ($KOIN votes, dTAO emission, 72h→5d→7d→30d lifecycle) → Train (FedRLHF, Shapley aggregation, LoRA only, Gensyn) → Eval (InfiCoEvalChain 7-node, σ 1.67→0.28, zk-SNARK via EZKL/Halo2, user feedback overrides benchmark) → Self-Evolve (drift→proposal→vote→5%→20%→50%→100% rollout).
- **Anti-centralization**: 7 eval nodes (≥3 geos), max 5% GovernanceWeight/wallet, founding veto sunsets Phase 2
- **Key papers**: FedRLHF (arXiv 2412.15538), InfiCoEvalChain (arXiv 2602.08229)

## Dormant Token Decay Design (2026-03-17)

Design doc: ~/otto/projects/capital/dormant_token_decay_design.md | DB Memory ID: 5759d18f

**Rule: Decay governance weight, never token balance.**
- Contributor tokens (5yr half-life, 0.25x floor) vs Circulating (18mo half-life, 0.10x floor)
- `activity_factor` (1.0x → floor) in GovernanceWeight — orthogonal to DHM, never resets DHM
- ≥10 contributions/year → no decay. Score ≥50 active contributor can shield 3 wallets/year.
- Redistribution: 60% active contributors, 25% treasury, 15% DHM boosters. Tier C: annual revalidation.

## Vulnerability Intelligence Database (2026-03-17)

Implementation: ~/otto/memory/security/vuln_collector.py | API: http://localhost:8100/security/*
Auto-sync: otto-vuln-sync.timer (every 6h)

- NVD API v2: keyword-per-query (multi-word = AND semantics → use single keywords)
- DeFiHackLabs README: heading format `### YYYYMMDD Protocol - AttackType` (not markdown table)
- MITRE ATLAS: no machine-readable API — 8 core AI attack patterns curated manually
- Current DB: 80 vulns. Top exposed: otto_vm_infra (55), tusita_app (42), oneon_network (28), koink_contracts (21)

## Context Rot Research (2026-03-17)

DB Memory IDs: 98dd07d8 (core), 9d5bab02 (mitigations), e9f44e27 (Otto gaps)

Source: https://research.trychroma.com/context-rot (Chroma, 2026) — 18 models tested.
- Shuffled haystacks outperform structured text. Retrieval + reasoning combined collapses at 113k tokens.
- **Otto improvements**: (1) S-MMU inject at START; (2) decouple retrieval from reasoning; (3) drop near-miss matches; (4) context < 50%; (5) bullets NOT narrative

## Recursive Language Models Research (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_rlm_recursive_language_models.md
DB Memory IDs: 32b72975 (analysis), 7d1128f9 (applicability)

arXiv 2512.24601 — handles inputs 100x beyond context via metadata-only handles + REPL recursion. 28.3% median improvement.
- **Otto**: S-MMU lazy-loading — load metadata headers only, fetch full content on demand. Store outputs in variables (unbounded).

## Token Launch Filtering & Anti-Sniper Research (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_launch_filtering_antsniper.md

**Order**: Batch/Auction > Decaying Fee > Open Pool. pump.fun = zero protection (87% sniper profits first 18s).
- **Solana**: Metaplex Genesis UPA (batch auction) or Meteora Alpha Vault (stake escrow)
- **EVM**: Uniswap v4 CCA (block-by-block) or Fjord Foundry LBP (high initial price)
- **VRF**: Real for ALLOWLIST randomization only — cannot stop bots on open AMM
- **EIP-7702**: `require(msg.sender == tx.origin)` broken on ETH post-Pectra May 2025. Valid on Solana.
- **$KOINK stack**: Human Passport → Meteora Alpha Vault Pro-Rata → Switchboard VRF → Fee Scheduler decay

## NS.com / Network School Research (2026-03-16)

Reference file: ~/otto/.claude/agent-memory/researcher/reference_ns_network_school.md
OMS Research note ID: 40cdf28a

**NS.com = Balaji's residential startup society ($1,500-$3,000/mo), Singapore.** NOT a fund.
- Philosophical alignment EXCEPTIONAL — Network State thesis maps to Tusita, ONEON, SOS, Otto
- Lead with Tusita as physical network state node. Network State Conference = right venue for PiPi/Polkadot.
- Apply: https://www.ns.com/apply (rolling, 2-3 week response)

## Crypto Signal Channel Research (2026-03-07) — Alpha Deprioritized

Research files: ~/otto/projects/alpha/SIGNAL_REVENUE_RESEARCH.md, SIGNAL_QUALITY_RESEARCH.md
**Deprioritized. Full technical details archived in research files above.**

## Context Engineering 2026 Research (2026-03-12)

Research file: ~/otto/.claude/agent-memory/researcher/project_context_engineering_2026.md

### 4-Strategy Framework (Anthropic + LangChain consensus)
Write → Select → Compress → Isolate

### Key papers
- AgeMem (arXiv 2601.01885): RL-driven unified LTM+STM. Memory ops as tool actions.
- A-MEM (arXiv 2502.12110): Zettelkasten memory graph — new memories update related old ones.
- HiAgent: hierarchical working memory chunked by subgoals.

### Otto gaps vs 2026 consensus
1. No Tool RAG (load all tools simultaneously — 3x accuracy gap)
2. No memory evolution (append-only, no cross-linking updates)
3. No learned memory management (heuristic decay vs RL-driven)
4. Sub-agent output not compressed before heartbeat ingestion (target: 1K-2K token summaries)
5. "Lost in the middle": critical info must be at START or END. Context < 50% capacity.

## Web3 Community Collab + Token Eligibility System (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_community_collab_eligibility.md

### Top 7 Communities for MY3YE (ranked)
1. **BONK** — 350+ integrations, Koink.fun natural integration + BONK DAO grants
2. **Gitcoin/GTC** — $50M+ public goods funded. SOS Systems + Panik qualify. Apply NOW.
3. **Farcaster/DEGEN** — 300K users. Create /koink channel, build Frames.
4. **Optimism/OP** — RetroPGF up to $30M. SOS Systems qualifies. Nominate immediately.
5. **BanklessDAO/BANK** — Sovereignty narrative match. Content co-creation.
6. **Nouns DAO** — 40K+ ETH treasury, CC0 ethos. PiPi/Tusita IRL proposal.
7. **ENS DAO** — Identity layer, integrates into ONEON.

### Token Eligibility System (4-tier + Alignment Score 0-100)
- Tier 0: Visitor → Tier 1: Community (1 category, 1.5x) → Tier 2: Ally (2+ or $KOIN holder, 2x)
- Tier 3: Aligned (3+ categories + score ≥40, 3x) → Tier 4: Sovereign (all 4 + score ≥70, 5x, proposal rights)
- Categories: A (Mission: GTC/OP/ENS/ARB), B (Culture: BONK/DEGEN/BANK), C (Governance: NOUN/UNI), D (Ecosystem: $KOIN/$KOINK)
- Anti-farming: $5 min hold, 30-day wallet age, Human Passport for Tier 3+. On-chain: EAS attestations.

## SOS Systems Article Crisis Data (2026-03-16)

Reference file: ~/otto/.claude/agent-memory/researcher/reference_sos_article_crisis_data.md

Key figures for decentralized emergency infrastructure narrative:
- 121M+ people forcibly displaced globally (UNHCR, end 2025)
- 244 deliberate internet shutdowns in 2025 — record high. Myanmar 330 townships cut off.
- Sudan: 70-80% hospitals non-functional; Gaza: 60% non-functional, near-total cell collapse.
- 4.6 billion lack essential health services (WHO 2025). 5 billion lack safe surgical care (Lancet).
- 2026 Hormuz crisis: Brent ~$120, "largest oil market disruption in history" (IEA).

## On-Chain Alpha Strategies Research (2026-03-09) — Alpha Deprioritized

Research file: ~/otto/projects/alpha/ONCHAIN_ALPHA_STRATEGIES_RESEARCH.md
**Deprioritized. Full technical details archived in research file above.**

## Claude Dynamic UI System Research (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/project_claude_dynamic_ui_research.md

### Architecture: Tool-Call Pattern (not magic renderer)
- `show_widget` params: `title`, `loading_messages`, `widget_code` (raw HTML, no DOCTYPE/html/body)
- HTML injected into DOM (not iframed). Streaming: SSE `widget_delta` + `widget_final`, client uses `morphdom`.
- Design guidelines lazy-loaded per module: interactive(19KB), chart(22KB), mockup(19KB), diagram(59KB)
- MCP Apps: `_meta.ui.resourceUri` → `ui://` bundle, rendered in double-sandboxed iframe, JSON-RPC over postMessage

### OMS Implementation (Tier 1 — 1 day, Vercel AI SDK)
- Define UI tools: `show_options`, `show_form`, `confirm_action`, `show_card`
- `ToolRenderer` component maps `toolName` → React component
- `useChat` with `parts` array + `addToolResult()` sends user response back
- **Best library**: Vercel AI SDK `useChat` + `parts` array for our Next.js OMS
- **Alt**: assistant-ui (Radix-style, github.com/assistant-ui/assistant-ui) — production-grade

## Sybil Resistance for Crypto Investment Platforms (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/project_sybil_resistance_2026.md
Goal: limit real persons to max 3 wallets

### Best tools by category
- **Clustering (free)**: Deposit address heuristic — wallets sharing Binance withdrawal address = same person
- **Graph-based**: TrustScan API (TrustaLabs) — 0-100 score, 4 pattern types
- **zkProof (strongest)**: World ID — 38M+ users, iris biometric, nullifier-based. Free. Banned in some jurisdictions.
- **zkProof (passport)**: Self Protocol — ZK from gov ID/Aadhaar, no biometrics stored. OFAC-compliant. $9M raised.
- **Easiest**: Human Passport — score ≥20 threshold, free API, 2M+ users, complexity 1/5
- **Academic best**: Subgraph LightGBM — Precision 0.9428, F1 0.9303 (arXiv 2505.09313)

### Implementation patterns
- World ID nullifier pooled cap: same person's wallets share one cap bucket (strongest anti-whale)
- Wallet age gate (<30 days = reject): easiest single filter. Scoring: age > tx count > clustering > cross-chain > ENS > POAP

## Grant Landscape Research (2026-03-26) — CURRENT

Report: ~/otto/projects/capital/grants_landscape_2026_march.md
DB Note ID: e05ac964 | Memory IDs: cf303b3c, 41b06654

- **[STALE — UPDATE]** All prior W3F Level 1/2 grant memories are STALE. W3F general grants DISCONTINUED Oct 2025. Only path now: Polkadot OpenGov Treasury (Polkassembly).
- **[P1 NOW]** ENS Public Goods Builder Grants ($12K-$50K, rolling, OPEN) — ONEON identity is natural fit. Apply: builder.ensgrants.xyz
- **[P2 NOW]** Solana Foundation grants (~$30-50K, rolling, OPEN) — Koink.fun + Otto AI. Apply: solana.org/grants-funding
- **[P3 UPCOMING]** Gitcoin GG25 — Q2 2026 (May), AI agents domain. Register at builder.gitcoin.co NOW before round opens.
- **[P4 NOW]** Deep Funding (SingularityNET) — up to $100K, open-source AI. Apply: deepfunding.ai
- **[P5 ROLLING]** EF ESP Wishlist/RFP model (OPEN) — requires Ethereum framing. esp.ethereum.foundation/applicants
- **[CLOSED]** Arbitrum Trailblazer 1.0 and 2.0 — BOTH COMPLETED. No AI-specific successor.
- **[CHANGED]** Optimism RPGF → now continuous missions via OP Atlas. Register: atlas.optimism.io
- **[MISSED]** Base Batches Startup Track — deadline was March 9, 2026. Next window: 2027 or retroactive grants.
- **[OPEN]** Starknet Seed ($25K) and Growth ($1M) grants — but requires Starknet-native work (low priority).
- **[OPEN]** ASI:Accelerator (Fetch.ai/CUDOS) — compute credits + mentorship for AI agent projects.
- **[OPEN]** NEAR AI Agent Fund ($20M) — requires NEAR deployment. near.org/funding

## OMNIFLOW Research (2026-03-23) — arXiv 2603.15797

DB Note ID: d6f032cc | Memory IDs: ed747a84 (PG-CoT), faa39d49 (frozen LLM), 6f2d63b6 (SSA)

- **PG-CoT experiment**: Pilot 1 mission-alignment checkpoint at REFLECT→DECIDE in heartbeat.md (15-30 lines). Analyze MARS critic pass overlap first. Run 5 cycles. Domain gap physics→agent governance = real; treat as experiment, not proven improvement.
- **Frozen LLM**: Corroborates (not validates) Otto no-training direction. No action.
- **SSA telemetry**: Raw metrics → structured text → LLM. P6 future work for S-MMU. Validation score: 6/10.

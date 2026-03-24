# Researcher Agent Memory

## HiClaw Multi-Agent OS Architecture Research (2026-03-24)

DB Note ID: f934ccf3 | Memory IDs: d829a87e, ffb52319, 3120a463, 02c9d695, 98f2052a

- **[IMMEDIATE]** Add `[ACCEPTANCE CRITERIA]` block to heartbeat.md task creation — zero cost, directly fixes QA rejection rate
- **[P2 SECURITY]** Credential isolation: task_runner.sh holds raw `ANTHROPIC_API_KEY` — route via Memory API proxy instead (gateway-token pattern)
- **[P3 EFFICIENCY]** Artifact-path references: outputs >2KB → write to file, store path in DB (30-60% context token reduction)
- **[CONTEXT]** Architecture parity: Otto already has DAG plans=HiClaw project-mgmt, workflow engine=task-coordination, /gateway/incoming=Manager routing. Gap is enforcement discipline, not missing components.
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
**Note: Alpha trading is deprioritized per system state. Details archived in research files.**

### Key Technical Facts (still reusable)
- **TP/SL structure**: TP1/TP2/TP3 at +10%/+25%/+50%, SL at -12% to -15%. Never time-based exits.
- **Smart money wallet thresholds**: Min WR 55% (gate), 65% (quality). Min trades 90d: 30 (gate). Avg hold >5min.
- **Statistical validity**: 27 trades is below 30-trade minimum. Need 385 trades for robust significance.
- **API capabilities**: DexScreener (price/volume/liquidity, free, 300 req/min, NO OHLCV). Solana Tracker (wallet PnL, 500K credits/month free). Birdeye unreliable. GMGN no free API.
- **Wallet discovery**: DexScreener trending → Helius first-30min buyers → Solana Tracker PnL scoring
- **Revenue hierarchy**: Exchange referrals > Paid subscriptions > Copy-trade > Jupiter referral > Tips

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
**Note: Alpha trading is deprioritized. Details archived in research file.**

### Key Technical Facts (reusable for other contexts)
- **Pump.fun graduation**: ~85 SOL raises token. 50 SOL in <50 trades = very high graduation probability. Detect via Helius websocket on program ID 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P. Median time: 4.4 min.
- **Fee-payer cluster**: 3+ "different" wallets sharing same fee payer = ONE entity. Add to convergence processor.
- **SOL unstaking**: large unstake events = whale liquidity incoming (28h lead time)
- **Bridge flow**: DefiLlama /api/bridgevolume/solana — free macro regime signal (HOT/NORMAL/COLD)
- **Kamino SDK**: github.com/Kamino-Finance — reads all position health factors on-chain (open source)

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

## OMNIFLOW Research (2026-03-23) — arXiv 2603.15797

DB Note ID: d6f032cc | Memory IDs: ed747a84 (PG-CoT), faa39d49 (frozen LLM), 6f2d63b6 (SSA)

- **PG-CoT experiment**: Pilot 1 mission-alignment checkpoint at REFLECT→DECIDE in heartbeat.md (15-30 lines). Analyze MARS critic pass overlap first. Run 5 cycles. Domain gap physics→agent governance = real; treat as experiment, not proven improvement.
- **Frozen LLM**: Corroborates (not validates) Otto no-training direction. No action.
- **SSA telemetry**: Raw metrics → structured text → LLM. P6 future work for S-MMU. Validation score: 6/10.

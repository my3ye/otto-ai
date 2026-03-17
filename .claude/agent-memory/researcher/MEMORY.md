# Researcher Agent Memory

## AutoResearchClaw Evaluation (2026-03-18)

Research file: ~/otto/.claude/agent-memory/researcher/project_autoresearchclaw_eval.md
DB Memory ID: da77499a

### Key Finding: Crawl Layer Good, Full Tool Wrong Fit
- **Repo**: github.com/aiming-lab/AutoResearchClaw — 23-stage academic paper generator (idea→LaTeX). 3,683 stars.
- **Crawl layer (stages 3-6)**: OpenAlex + Semantic Scholar + arXiv with query expansion + dedup → **significantly better than Otto's ad-hoc WebFetch pattern**
- **Purpose mismatch**: Generates academic papers. Otto needs implementation signal, not papers.
- **Persona critique fit**: POOR — social/cultural research, not arXiv domain
- **General research fit**: PARTIAL — crawl layer only
- **Dependency cost**: Requires OpenAI API key (added cost), complex 23-stage system
- **Verdict**: Do NOT adopt. Instead build native `LitSearch` tool using OpenAlex API (free) + Semantic Scholar API (free tier) → feeds existing triage pipeline

## Decentralized Intelligence Layer Architecture (2026-03-17)

Design doc: ~/otto/projects/capital/decentralized_intelligence_layer.md
DB Memory IDs: c7fe43ae (architecture), 838af093 (research primitives)

### Key Finding: 4-Layer Protocol — Govern, Train, Eval, Self-Evolve
- **Layer 1 (Governance)**: $KOIN contributor-weighted votes on capability subnets. Market-driven subnet emission (Bittensor dTAO pattern). Proposal lifecycle: 72h review → 5d deliberation → 7d vote → 30d timelock.
- **Layer 2 (Training)**: FedRLHF on community feedback. Contribution-weighted aggregation via Shapley value. LoRA adapters only — no from-scratch training (Mev directive). Gensyn for distributed compute.
- **Layer 3 (Eval)**: InfiCoEvalChain pattern — 7-node multi-party consensus reduces eval σ from 1.67→0.28. zk-SNARK proofs of performance (EZKL/Halo2). Tier 1 gates block deploy; user feedback gate overrides benchmark (anti-Goodhart).
- **Layer 4 (Self-Evolution)**: Drift detection → auto-proposal → governance vote → staged rollout (5%→20%→50%→100%). Continual learning via LoRA isolation + replay buffers.
- **Anti-centralization**: 7 independent eval nodes (≥3 geos), max 5% GovernanceWeight per wallet, founding veto sunsets Phase 2 (12-24mo), fork rights always available.
- **Roadmap**: Phase 0 (simulation) → Phase 1 (governance MVP, devnet) → Phase 2 (first production model update) → Phase 3 (full decentralization).

### Key Research Primitives Found
- **Bittensor/dTAO**: Market-driven emission, Yuma Consensus. Covenant-72B trained on 70+ nodes (SparseLoCo 146x comm reduction).
- **Gensyn**: Layer-1 Ethereum rollup. SkipPipe -55% training time. Verde dispute resolution. RL Swarm.
- **FedRLHF** (arXiv 2412.15538): Federated RLHF, no raw data sharing, privacy-preserving.
- **InfiCoEvalChain** (arXiv 2602.08229): Multi-party consensus LLM eval.
- **DisTrO+Psyche**: Post-training RL on-chain — only 5-10% of total training cost, most Web3-compatible.
- **EZKL**: zk-SNARK proof of model performance (no weights revealed).
- **FL-Light Shapley**: Contribution evaluation via Shapley approximation.
- **FEDMWAD**: Byzantine fault tolerance for federated aggregation.

## Dormant Token Decay Design (2026-03-17)

Design doc: ~/otto/projects/capital/dormant_token_decay_design.md
DB Memory ID: 5759d18f

### Key Finding: Decay Governance Weight, Never Token Balance
- **Two tiers**: Contributor tokens (5yr half-life, 0.25x floor) vs Circulating (18mo half-life, 0.10x floor)
- **Formula**: GovernanceWeight adds `activity_factor` multiplier (1.0x → floor), orthogonal to DHM
- **Perpetual stake preserved**: "Perpetual contribution = perpetual stake" → balance never expires, only weight decays
- **Contribution protection**: ≥10 contributions/year → activity_factor = 1.0 (no decay at all)
- **Network endorsement**: Active contributor (score ≥50) can shield 3 wallets/year (Mev's "close network" mechanic)
- **Redistribution**: 60% to active contributors, 25% treasury pool, 15% DHM boosters
- **DHM is orthogonal**: Decay does NOT trigger Diamond Hands Multiplier reset
- **Tier C (vested)**: Annual on-chain revalidation OR weight drops to 0x (balance safe)
- **Edge case resolved**: Proof-of-life endorsement caps prevent whale cartel formation

## Vulnerability Intelligence Database (2026-03-17)

Implementation complete at ~/otto/memory/security/vuln_collector.py
API live at http://localhost:8100/security/* (stats, vulns, otto-exposure, sync)
Auto-sync: otto-vuln-sync.timer (every 6h), commit 18102e3

### Key findings used
- NVD API v2: keyword-per-query (multi-word = AND semantics → use single keywords)
- DeFiHackLabs README: heading format `### YYYYMMDD Protocol - AttackType`, not markdown table
- MITRE ATLAS: no machine-readable API — curated 8 core AI attack patterns manually
- Otto system map: 11 systems with keyword+tech_stack arrays in vuln_system_map DB table
- Current DB: 80 vulns (mobile:40, blockchain:18, vm_infra:9, ai:8, web:5)
- Top exposed: otto_vm_infra (55 vulns), tusita_app (42), oneon_network (28), koink_contracts (21)

## Context Rot Research (2026-03-17)

DB Memory IDs: 98dd07d8 (core findings), 9d5bab02 (mitigations), e9f44e27 (Otto gaps)
Research Note ID: e8229507

### Key Finding: Context Rot → 5 Otto Architecture Improvements
- **Source**: https://research.trychroma.com/context-rot (Chroma, 2026) — 18 models tested (Claude 4, GPT-4.1, Gemini 2.5, Qwen3)
- **Definition**: LLMs degrade non-linearly as context grows, even on trivial tasks — despite high NIAH benchmark scores
- **Paradox**: SHUFFLED/incoherent haystacks perform BETTER than structured flowing text — coherent structure causes interference
- **Separation rule**: Do NOT combine retrieval + reasoning in one long-context pass — performance collapses at 113k tokens
- **Distractor danger**: Near-but-not-exact semantic matches amplify degradation compoundingly
- **Otto improvements**: (1) S-MMU inject relevant slices at START; (2) decouple retrieval agent from reasoning agent; (3) drop similar-but-wrong S-MMU matches; (4) keep context under 50% capacity; (5) use bullet lists NOT narrative paragraphs for memory format

## Recursive Language Models Research (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_rlm_recursive_language_models.md
DB Memory IDs: 32b72975 (paper analysis), 7d1128f9 (Otto applicability)

### Key Finding: Symbolic Handle Pattern → S-MMU Upgrade
- **Paper**: arXiv 2512.24601 by Zhang, Kraska, Khattab — handles inputs 100x beyond context window
- **Core mechanism**: Model only sees metadata (symbolic handle), writes REPL code that recursively calls itself on prompt slices
- **Performance**: 28.3% median improvement, RLM-Qwen3-8B approaches GPT-5 quality on 3 tasks with just 1K training samples
- **Top Otto application**: S-MMU lazy-loading — load only memory metadata headers, fetch full content on demand (no model training needed)
- **Second application**: Long document processing via recursive slice access (WhatsApp doc handler use case)
- **REPL insight**: Store outputs in variables (unbounded), not in context tokens

## Token Launch Filtering & Anti-Sniper Research (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_launch_filtering_antsniper.md

### Key Finding: Batch/Auction > Decaying Fee > Open Pool
- **Solana best**: Metaplex Genesis UPA (uniform price auction — no timing advantage) or Meteora Alpha Vault (commitment + stake escrow fee blocks multi-wallet spam)
- **EVM best**: Uniswap v4 CCA (block-by-block clearing auction) or Fjord Foundry LBP (high initial price = bot self-punishment)
- **Orca Wavebreak**: on-chain CAPTCHA permission credential — "mechanically prevents sniping" (July 2025)
- **pump.fun**: zero protection — 87% sniper profits in first 18 seconds
- **"Quantum Koinkulator" VRF verdict**: Legitimate IF it means VRF-selected lottery from pre-registered allowlist. Theater if it claims to prevent sniping on an open live pool (VRF cannot do that)
- **Anti-whale**: World ID nullifier cap is strongest (multiple wallets of same person share one cap). Max wallet % alone is trivially bypassed (Chainlink "Oldwhite" used 150+ wallets to dodge staking caps)
- **EVM warning**: `require(msg.sender == tx.origin)` broken by EIP-7702 (Ethereum Pectra May 2025). Still valid on Solana.
- **Recommended $KOINK stack**: Human Passport gate → Meteora Alpha Vault Pro-Rata → Switchboard VRF for allocation randomization → Fee Scheduler decay post-launch

### Key Findings
- Best Solana mechanisms: Metaplex Genesis UPA (batch auction), Meteora Alpha Vault (commitment + stake escrow fee), Orca Wavebreak (on-chain CAPTCHA), Heaven DEX (6s sniper tax)
- Best EVM mechanisms: Uniswap v4 CCA (block-by-block clearing auction, live on frontend), LBP (Fjord/Copper), v4 hooks (Flaunch, Angstrom)
- VRF VERDICT: VRF is real for randomizing ALLOWLIST selection. VRF CANNOT stop bots buying on an open AMM. "Quantum Koinkulator" = real only if combined with pre-registered allowlist gate.
- Anti-whale bypass: multi-wallet is trivially easy (Chainlink "Oldwhite" used 150 wallets for $7M). Real countermeasures: stake escrow fee, World ID nullifier cap, deposit address clustering.
- EIP-7702 (Pectra, May 2025): breaks `require(msg.sender == tx.origin)` anti-bot check on Ethereum.
- Strongest combined stack: batch auction + allowlist gate + Human Passport score + per-person World ID cap.

## NS.com / Network School Research (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/reference_ns_network_school.md
OMS Research note ID: 40cdf28a-2c1d-4ffd-a974-53cc9e746442 (topic: funding_partnerships)

### Key Finding: NS.com is NOT a fund — it's a community
- Balaji Srinivasan's residential startup society ($1,500-$3,000/month), Singapore-based
- Philosophical alignment with MY3YE is EXCEPTIONAL — Network State thesis maps directly to Tusita, ONEON, SOS, Otto
- Do NOT pitch as fundraising. Apply as a team to the residential community, lead with Tusita as physical network state node
- Earn platform: post bounties in USDC/ETH/SOL for MY3YE content/dev tasks — access Web3-native builders
- Network State Conference = right venue for PiPi/Polkadot pitch
- Apply free at https://www.ns.com/apply (rolling, 2-3 week response)

## Crypto Signal Channel Research (2026-03-07)

### Key Finding: Signal quality root cause identified
- Our 4h time exits cause -1.9% PnL. Our own backtest shows 40% WR at T+24h with +4.32% avg return.
- Fix: Switch to TP1/TP2/TP3 structure (+10%/+25%/+50%) with -15% SL. Never time-based exits for whale convergence signals.
- Research file: ~/otto/projects/alpha/SIGNAL_REVENUE_RESEARCH.md

### Revenue hierarchy for signal channels (largest to smallest)
1. Exchange referral commissions (Binance 20-50%, KuCoin 60%, MEXC 40%) — passive, scales with subscribers
2. Paid subscriptions ($49-299/month, launch at 1K subs + 60% WR)
3. Copy-trade integration (Cornix — users pay, we benefit from retention)
4. Jupiter referral fees (0.5% per swap via referral link in post)
5. Tips (last, negligible until 5K+ subscribers)

### Top channels methodology
- CryptoNinjas: 94.26% WR, public P&L sheet, AI+TA+on-chain, $99/mo VIP
- Binance Killers: 86% WR, 250K subs, $290/mo VIP
- Fat Pig Signals: 91.7% WR, volume flows + order book + on-chain
- All share: low frequency (1-5/day), explicit TP/SL, published losses

### Signal quality filters needed (add to whale_convergence.py)
- Volume spike ≥3x 7-day average (use DexScreener API — free, no auth)
- Market cap $100K-$50M range (raised upper bound — Nansen uses $50M cap)
- Pool liquidity ≥$100K
- NOT already pumped >15% in last 2h (tightened from 25% in 6h — our 1h/4h data shows we're entering at ~10-15% moves, not 25%)
- Token age ≥3 days
- Top 10 holders ≤40% of supply (rug filter)
- Volume/liquidity ratio ≤20x (wash trade filter)
- Min buy per wallet $500 (raised from $100 — conviction filter)

### CRITICAL: Wallet pool problem identified (2026-03-08)
- Our 20 wallets sourced by swap frequency — NO win rate validation
- SM_1 (MEV bot), SM_6 (TITAN bot) are bots, not smart money
- Correct methodology: find early buyers of 5x+ tokens → filter by 65%+ win rate
- Birdeye API key obtained (cycle 88) — birdeye_client.py integrated
- Research file: ~/otto/projects/alpha/SIGNAL_QUALITY_RESEARCH.md

### Smart money wallet scoring thresholds (industry standard)
- Min win rate 30d: 55% (gate), 65% (quality), 75% (premium)
- Min trade count 90d: 30 (gate), 50 (quality)
- Wallet age: 30 days min, 90 days preferred
- Avg hold time: >5 minutes (bots hold <5min)
- Loss control: top wallets have losses = only 11% of profit; bottom wallets = 642%
- Source: ChainCatcher 1,080 Solana wallet analysis

### Convergence parameter recommendations
- 4 wallets in 30min = HIGH confidence (current is correct for min)
- 6-8 wallets = VERY HIGH
- 9+ wallets = ULTRA (60% of pool agreeing)
- 80% pool agreement (12 of 15) = maximum conviction
- 7-day netflow (5+ wallets) = ACCUMULATION mode (highest quality, new signal type)

### Entry timing root cause
- Our 0% WR at 1h/4h = we're entering after a 10-15% price move
- Structural: 4-whale convergence fires at END of their 30-min buying cycle, not start
- Detection + publish + subscriber execution = 5-15 min after final whale buy
- Price impact of 4 x $10K buys on $500K liquidity pool = ~8% before we detect

### Jupiter referral setup
- URL: https://referral.jup.ag/
- Connect wallet → create account → select fee tier (0.1/0.5/1%)
- Embed in every signal: jup.ag/swap/SOL-[TOKEN]?referrer=[KEY]&feeBps=50
- Jupiter takes only 2.5% of fees earned

### Data sources — confirmed capabilities (2026-03-09)
- DexScreener API: current price, volume, liquidity, pair info — NO OHLCV candles, NO wallet/PnL data. Free, no auth. 300 req/min.
- Birdeye API: token metadata, market cap, holders (free tier, API key) — blocked/unreliable for our use case
- Solscan API: transaction history, token age (free tier)
- Helius Enhanced Transactions API: SWAP type returns inputMint, outputMint, tokenInputs/tokenOutputs (raw token amounts + decimals), pre/post balances. NO USD values. PnL reconstruction requires cross-referencing price oracle separately. Wallet API beta adds history/transfers/balances — no PnL natively.
- Solana Tracker API: wallet PnL endpoint returns win rate, realized PnL per token, trade counts. Free: 500K credits/month, 10 RPS. $49/mo = 10M credits. BEST free option for wallet PnL.
- GMGN.ai: no free API — official API requires trading volume + Google Form approval. UI shows win rate/PnL/hold time. Dragon open-source tool scrapes GMGN but hits Cloudflare — fragile.
- Cielo Finance: API requires Whale plan (paid). UI free. Not viable for programmatic access.
- Bitquery: GraphQL API for pump.fun early buyers — requires account, has free tier but limited.

### Wallet discovery without Birdeye — step-by-step (2026-03-09)
1. Find 5-10 tokens that pumped 5x+ in last 30 days (DexScreener trending or GMGN trending page)
2. For each token, get first 30-min buyers via Helius `getTransactions` on token mint (type=SWAP, filter timestamps)
3. Collect wallet addresses, deduplicate across multiple pumped tokens — wallets appearing in 2+ early buyer lists are candidates
4. Score each wallet via Solana Tracker `/wallet/{address}/pnl` — win rate, trade count, realized PnL
5. Gate: win_rate_30d >= 65%, trade_count >= 30, avg_hold_time > 5min
6. Alternative: manually visit GMGN.ai/sol/address/{wallet} for each candidate — shows win rate/PnL visually

### Statistical validity of 27 trades (2026-03-09)
- 27 trades is BELOW the 30-trade minimum for any valid statistical inference
- 30% WR on 27 trades: 95% CI is approximately 14% to 51% (Wilson interval) — true WR could be anywhere in that range
- 60% WR on 30 trades: 95% CI is 41% to 77% — still very wide
- Need 385 trades for robust significance; 100 trades minimum for directional confidence
- Correct approach at N=27: use Clopper-Pearson exact binomial CI, not z-test
- Do NOT trust 30% WR at N=27 — it's statistically indistinguishable from 14% or 51%
- Actionable threshold: once N>=50 with WR >= 55%, begin publishing with caution flag

### Optimal TP/SL for right-skewed crypto returns (2026-03-09)
- Empirically proven (ScienceDirect 2024 paper): 30% monthly stop-loss on momentum crypto = avg return +9.13% vs -8.02% without SL, and skewness turns POSITIVE
- Right-tail dependence in crypto is stronger than left-tail — upside clustering is real
- Academic consensus: DO NOT use symmetric SL/TP (wrong for fat-tail positive-skew assets)
- Kelly Criterion for asymmetric payoffs: f* = (p*b - q*L) / (b*L). With our data: p=0.30, b=+13% (avg winner), q=0.70, L=5% (avg loser) → f* ≈ 0.14 → bet 14% of capital per trade max
- Practical structure for our distribution (most trades -2 to -5%, winners +10 to +28%):
  - SL: -12% to -15% (not tighter — meme coins have wide intraday swings, tight SL gets stopped out on noise)
  - TP1: +10% (take 33% of position — most reachable)
  - TP2: +25% (take another 33%)
  - TP3: +50%+ (let 33% run — captures the fat right tail)
  - Trail stop after TP1: move SL to breakeven
- Use fractional Kelly (50% of calculated f*) in practice — reduces variance 4x while keeping 75% of returns

## Context Engineering 2026 Research (2026-03-12)

Research file: ~/otto/.claude/agent-memory/researcher/project_context_engineering_2026.md

### 4-Strategy consensus (Anthropic + LangChain)
Write → Select → Compress → Isolate. All production agent systems in 2026 use this framework.

### Key papers
- AgeMem (arXiv 2601.01885): RL-driven unified LTM+STM. Memory ops as tool actions. Best for long-horizon.
- A-MEM (arXiv 2502.12110, NeurIPS 2025): Zettelkasten memory graph. New memories update related old memories.
- HiAgent: hierarchical working memory chunked by subgoals.

### Critical findings for Otto
- "Lost in the middle": 30%+ performance degradation when key facts buried mid-context. Always put critical info at START or END.
- Tool RAG: 3x better tool selection accuracy when tools fetched semantically vs all-at-once. Otto loads all tools simultaneously — gap.
- Sub-agent output: should be compressed to 1,000-2,000 token summaries before handoff, not raw output.
- Memory evolution: new memories should update related existing memories (A-MEM) — Otto is append-only.
- Context < 50% full rule: degradation accelerates past 50% capacity.
- MCP = universal standard (97M downloads/month). A2A = cross-agent handoff protocol.

### Otto gaps vs 2026 consensus
1. No Tool RAG (load all tools simultaneously)
2. No memory evolution (append-only, no cross-linking updates)
3. No learned memory management (heuristic decay vs RL-driven)
4. Sub-agent output not compressed before heartbeat ingestion
5. Position bias not explicitly engineered in SMMU ordering

## Web3 Community Collab + Token Eligibility System (2026-03-17)

Research file: ~/otto/.claude/agent-memory/researcher/project_community_collab_eligibility.md

### Top 7 Communities for MY3YE Collaboration (ranked)
1. **BONK** — Solana meme, 350+ integrations, ~500K holders. Koink.fun natural integration + BONK DAO grants.
2. **Gitcoin/GTC** — $50M+ public goods grants funded. SOS Systems + Panik App qualify for Grants rounds. Apply NOW.
3. **Farcaster/DEGEN** — 300K users, DEGEN tipping, builder community. Create /koink channel, build Frames.
4. **Optimism/OP** — RetroPGF rounds up to $30M. SOS Systems qualifies. Nominate immediately.
5. **BanklessDAO/BANK** — Sovereignty narrative match. Content co-creation, 20K+ educated members.
6. **Nouns DAO** — 40K+ ETH treasury, CC0 ethos. PiPi/Tusita IRL proposal could be funded.
7. **ENS DAO** — Identity layer, integrates into ONEON. ENS holders = self-sovereign believers.

### Token Eligibility System Design (4-tier + Alignment Score)
- **Tier 0**: Visitor (no tokens) — 1x airdrop
- **Tier 1**: Community (any 1 category) — 1.5x, chat access
- **Tier 2**: Ally (2+ categories OR $KOIN holder) — 2x, governance signal
- **Tier 3**: Aligned (3+ categories + score ≥40) — 3x, full governance weight
- **Tier 4**: Sovereign (all 4 categories + score ≥70) — 5x, proposal rights
- **Alignment Score**: 0-100, 5 factors (diversity, conviction, governance, social graph, contributions)
- **On-chain attestation**: EAS (Ethereum Attestation Service) for score transparency
- **Anti-farming**: $5 min hold threshold, 30-day wallet age, Human Passport for Tier 3+

### Token Categories
- A (Mission): GTC, OP, $ENS, ARB
- B (Culture): BONK, WIF, DEGEN, BANK, FWB
- C (Governance): NOUN, UNI, Lens Profile
- D (Ecosystem): $KOIN, $KOINK → auto-Tier 2

## SOS Systems Article — Crisis Data (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/reference_sos_article_crisis_data.md

Key figures for decentralized emergency infrastructure narrative:
- 121 million+ people forcibly displaced globally (end 2025, UNHCR)
- 240,000 conflict fatalities in 2025 (+23% YoY, ACLED)
- 244 deliberate internet shutdowns in 2025 — record high, conflict-driven
- Myanmar: all 330 townships cut off since coup; earthquake aid blocked by blackout
- Sudan: 70-80% of hospitals non-functional; RSF seized ISPs, 2/3 population unreachable for 1 month
- Gaza: 60% hospitals non-functional; near-total cell network collapse
- 2026 Hormuz crisis: Brent hit ~$120, IEA called it "largest disruption in oil market history"
- 4.6 billion people lack access to essential health services (WHO 2025)
- 5 billion lack access to safe surgical/emergency care (Lancet Commission)
- 50%+ of LMIC deaths preventable with quality emergency care access

## On-Chain Alpha Strategies Research (2026-03-09)

Research file: ~/otto/projects/alpha/ONCHAIN_ALPHA_STRATEGIES_RESEARCH.md

### Strategy 1: MEV Sandwich Detection as Buy Signal
- 16/20 top sandwiched tokens are pump.fun launches (vanity suffix `pump`)
- Sandwich activity = demand proof signal (MEV bots only attack hot tokens)
- Jito tip spikes (781 SOL/day low vs 60,801 SOL peak) correlate with memecoin cycles
- Detection: Helius getTransactions() — parse tx[0]/tx[2] same signer, tx[1] different buyer = sandwich
- Sandwiched.me expanding but no confirmed public API for per-token stats
- Use as +confidence multiplier only. Complexity: 3/5.

### Strategy 2: Liquidation Cascade Detection
- Kamino SDK open source: github.com/Kamino-Finance — reads all position health factors on-chain
- Marginfi: `lending_account_pulse_health` instruction reads health (individual query only)
- Q1 2025: $1.7B liquidated in 6 weeks. Only ~9 active liquidators = cascade amplification risk
- NOT for meme coins (collateral = SOL, jitoSOL, USDC). Use as macro risk-off signal.
- Buy signal: 2-4h AFTER cascade completes (oversold mean reversion). Complexity: 4/5.

### Strategy 3: Whale Accumulation Beyond Convergence (5 patterns — all free Helius)
- Wallet funding pattern: master wallet SOL → new unfunded wallets = buy in 2-24h (LEAD TIME ADVANTAGE)
- Cold storage transfer: post-buy token move to non-DEX wallet = long conviction
- LP removal: usually bearish rug (93% of pools). Contrarian buy only if non-creator removes + passes all rug filters
- Fee-payer cluster: 3+ "different" wallets share same fee payer = ONE entity (COORDINATED, not organic). Add to convergence processor. 2 days work.
- SOL unstaking: large unstake events = whale liquidity incoming (28h lead time)

### Strategy 4: Cross-Chain Bridge Flow (Wormhole/deBridge)
- Macro signal only (7-30 day timescale). NOT token-level signal.
- USDC inflow to Solana = "dry powder on hold". $10.1B bridge volume by Feb 2025, USDC supply +110%.
- Use as ecosystem regime filter: HOT/NORMAL/COLD. Apply stricter convergence filters in COLD mode.
- Free data: DefiLlama /api/bridgevolume/solana. Complexity: 2/5. Edge: +5-8% win rate.

### Strategy 5: Pump.fun Bonding Curve Graduation (HIGHEST NEW VALUE)
- Academic study: arXiv 2602.14860 (Feb 2026) — 655,770 tokens, 0.63% graduation rate
- Graduation: ~85 SOL raised. Token balance 206.9M-246.5M remaining = 95-100% progress = imminent
- Since March 2025: graduates route to PumpSwap (not Raydium)
- STRONGEST predictor: liquidity velocity = SOL per trade (few trades to reach high vSol = graduation likely)
- Key signal: 50 SOL reached in <50 trades = very high graduation probability
- Bot ratio <30% + zero dump events + 70%+ progress = pre-graduation candidate
- Median graduation time: 4.4 minutes. Must detect early or lose the move to snipers.
- Detection: Helius websocket on pump.fun program ID 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P (FREE)
- Formula: curve_progress = (vSol_balance / 85) * 100
- Post-graduation entry: possible 30-120s after (first 30s is sniper-dominated)
- Win rate estimate: 45-55% at T+30min with quality filters. Complexity: 3/5.

### Implementation priority order
1. Pump.fun graduation monitor (highest priority — new signal type, strong academic backing)
2. Fee-payer cluster check on convergence signals (2 days, already have data)
3. Wallet funding monitor — SOL transfers to new wallets from tracked whales (2 days)
4. Bridge flow regime flag via DefiLlama API (1 day)
5. MEV sandwich rate as confirmation layer (3/5 complexity, lower urgency)

## Claude Dynamic UI System Research (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/project_claude_dynamic_ui_research.md

### How Claude's generative UI works (reverse-engineered)
- Not a magic renderer — it's a **tool-call architecture**: `read_me` (lazy-load design guidelines) + `show_widget` (render HTML fragment)
- `show_widget` params: `title`, `loading_messages`, `widget_code` (raw HTML, no DOCTYPE/html/body)
- HTML injected directly into DOM (not iframed) → CSS variables resolve, `sendPrompt()` works
- Streaming via SSE: `widget_delta` + `widget_final` events; client uses `morphdom` for DOM diffing
- Model autonomously decides text vs widget based on system prompt + tool descriptions
- Design guidelines lazy-loaded per module: interactive(19KB), chart(22KB), mockup(19KB), art(17KB), diagram(59KB)
- Source: michaellivs.com/blog/reverse-engineering-claude-generative-ui

### MCP Apps (third-party UI in Claude)
- Tools declare `_meta.ui.resourceUri` → `ui://` scheme bundle
- Host renders in double-sandboxed iframe, JSON-RPC over postMessage
- Three operations: receive tool results, call server tools, update model context
- SDK: `@modelcontextprotocol/ext-apps`

### Open-source generative UI options
- **Vercel AI SDK**: `useChat` + `parts` array + tool-to-component mapping. BEST for our Next.js OMS.
- **streamUI** (AI SDK RSC): yields loading state → returns final component. More complex, RSC-only.
- **assistant-ui**: Radix-style composables, multi-backend, production-grade (github.com/assistant-ui/assistant-ui)
- **LangGraph UI**: `push_ui_message()`, shadow DOM isolation, `LoadExternalComponent`

### OMS Implementation Blueprint (Tier 1 — 1 day)
1. Define UI tools in API route: `show_options`, `show_form`, `confirm_action`, `show_card`
2. `ToolRenderer` component maps `toolName` → React component
3. `useChat` with `parts` array rendering + `addToolResult()` sends user response back to model
4. System prompt instructs model when to use each tool type
5. All text OUTSIDE tool calls; tool output = visual element only
- Full implementation in research file

## Sybil Resistance for Crypto Investment Platforms (2026-03-16)

Research file: ~/otto/.claude/agent-memory/researcher/project_sybil_resistance_2026.md

### Goal: limit real persons to max 3 wallets on an investment platform

### Best tools by category
- **Clustering (enterprise)**: Nansen (removed 39.85% of 1.3M wallets in Linea), Chainalysis, TRM Labs
- **Clustering (free/cheap)**: Deposit address heuristic — if wallets A+B both withdrew from Binance to same deposit address = same person
- **Graph-based clustering**: TrustScan API (TrustaLabs) — 0-100 Sybil score, 4 pattern types
- **Academic best model**: Subgraph LightGBM — Precision 0.9428, F1 0.9303, AUC 0.9806 (arXiv 2505.09313)
- **zkProof identity (strongest)**: World ID — 38M+ users, iris biometric, cryptographic 1-person-1-action via nullifier. Free. EVM contract: `IWorldID.verifyProof(...)`. Banned in some jurisdictions.
- **zkProof identity (passport-based)**: Self Protocol — ZK proof from government ID/Aadhaar. No biometrics stored. Raised $9M, Google + Aave use it. Strongest for OFAC compliance.
- **Credential aggregation (easiest)**: Human Passport (formerly Gitcoin Passport) — score ≥20 threshold, free API, 2M+ users, 1/5 complexity
- **Social graph**: BrightID — no docs/biometrics, pure social connections. Niche, lower adoption.
- **India-specific**: Anon Aadhaar — ZK proof of Aadhaar. 1.4B IDs. PSE-backed, open source.

### Key implementation patterns
- World ID nullifier-based pooled cap: same person's wallets share one cap bucket (Pattern 3 in research file)
- Deposit address clustering: free, high-precision, implement yourself via Etherscan/Helius
- Wallet age gate (<30 days = reject) is the easiest single Sybil filter
- Hybrid: passive score + identity attestation for borderline wallets

### Wallet scoring signals (by importance)
1. Wallet age (days) — most important
2. Total tx count / DeFi interactions
3. Deposit address clustering (shared = same person)
4. Cross-chain activity
5. Gas paid lifetime
6. ENS ownership (cost barrier)
7. POAP / NFT history

### Smart contract enforcement
- `require(nullifierInvested[nullifierHash] + amount <= MAX_PER_PERSON)` — caps by person not wallet
- `require(msg.sender == tx.origin)` — blocks contract-based batch attacks (Adidas NFT lesson)
- Allowlist admin via Gnosis Safe multisig for manual review layer

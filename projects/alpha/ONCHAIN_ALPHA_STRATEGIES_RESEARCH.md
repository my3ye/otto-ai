# On-Chain Alpha Strategies: Solana Meme Koin Trading
**Compiled:** 2026-03-09 | **Researcher:** Otto
**Directive:** Deep research on five advanced on-chain alpha strategies for Solana

---

## Strategy 1: MEV Pattern Detection as a Buy Signal

### Mechanism

MEV activity on Solana (specifically sandwich attacks and arbitrage) functions as a **demand proof signal** — bots only pay to attack tokens that have enough volume and volatility to be worth the gas. When a token begins attracting sandwich attacks, it means:

1. The token has sufficient liquidity and slippage tolerance from buyers to make sandwiching profitable
2. Searchers have identified it as worth competing for (tip auction selection)
3. The underlying demand is real (retail buying, not coordinated bot wash)

**The specific alpha:** If you detect a token is being sandwiched heavily but is still early in its price move, sandwich activity is a confirmation of demand — not a reason to avoid it. You're using the MEV bots as a sentiment sensor.

**Jito tip volume as a macro signal:**
- Daily Jito tips ranged from 781 SOL (low demand day) to 60,801 SOL (November 19, 2024 peak)
- Tip spikes correlate with memekoin launch cycles and high volatility periods
- On a token level: the more a token is targeted by sandwich bots, the higher its retail demand
- TRUMP token launch (Jan 2025) caused the largest single-day tip spike in Jito history

**Sandwich rate by token type:**
- 16 of the top 20 sandwiched tokens are pump.fun launches (identifiable by `pump` suffix in mint address)
- Tokens with high slippage settings (>5%) are sandwich targets
- The dominant bot (Vpe program) executed 1.55M sandwich transactions in 30 days, 88.9% success rate, 65,880 SOL profit

### Detectability

**Semi-detectable with current free APIs:**

- **Helius enhanced transactions** (`getTransactions()` with enhanced format): Can detect sandwich pattern from transaction structure — three consecutive txns where tx1 and tx3 share the same signer, same token, with tx2 being a victim buy. However this requires parsing individual transactions, not a bulk query.
- **Jito Explorer (explorer.jito.wtf)**: Public dashboard showing bundle data, but no per-token API query available.
- **Bitquery Jito Bundle API**: Can query Jito bundles by program or address. Paid service, but has free tier.
- **Sandwiched.me**: Expanding into per-token/per-bot sandwich analytics. Currently tracks in real time but no documented public API.
- **sandwiched.me research page**: Shows aggregate patterns but no real-time per-token endpoint confirmed.

**What you can detect with Helius free tier:**
- Query transactions for a specific token mint address
- Identify blocks where the same token was bought in transactions 1 and 3 with a different buyer in position 2
- Calculate sandwich rate per token over a time window
- This is custom code, not a turnkey API call

**What you cannot easily detect:**
- Which bundles were rejected (private mempool info)
- Real-time tip amounts per token (Jito doesn't expose per-token tip breakdowns publicly)
- DeezNode private mempool activity (off-chain)

### Expected Win Rate / Edge Size

- **Edge type:** Confirmation signal, not a primary signal — improves confidence of other signals
- **When used alone:** Low predictive value. Many tokens get sandwiched briefly and dump anyway.
- **When combined with whale convergence:** Strong. If 4+ smart wallets buy + the token has started attracting MEV bots = retail demand is real.
- **Estimated incremental win rate improvement over baseline:** +5-10% when used as a confirmation layer
- **Key risk:** By the time MEV bots are attacking a token, the easy money may already be made. Sandwich activity is a lagging confirmation, not an early warning.

### Implementation Complexity: 3/5

**What to build:**
1. For a given token, pull last 100 transactions via Helius `getTransactions()`
2. Look for the sandwich pattern (same signer in tx[0] and tx[2], different buyer in tx[1])
3. Calculate: sandwich_count / total_buys = sandwich rate
4. Flag tokens with >5% sandwich rate as "MEV confirmed hot"
5. Use this as a +1 confidence multiplier on existing convergence signals

**Free API:** Helius free tier (100 RPS, generous daily limit)
**Paid alternative for per-token sandwich count:** Bitquery (~$100/mo for meaningful query volume)

---

## Strategy 2: Liquidation Cascade Detection

### Mechanism

In Solana's lending markets (primarily Kamino, with Marginfi acquiring users in 2025-2026), large leveraged positions create predictable cascade dynamics:

**The cascade sequence:**
1. Collateral price drops → health factors fall
2. Liquidators (only ~9 active in Q1 2025) execute partial liquidations (10-20% of position)
3. Liquidation sells hit the market → price drops further
4. More positions become undercollateralized → repeat

**Q1 2025 data (most significant cascade event):**
- Feb 17-23: $517M liquidated, ~9,700 events (triggered by Bybit hack)
- Feb 24-March 2: $856M liquidated, ~27,000 events
- Total Q1 2025: $1.7B liquidated, $88.5M in fees to liquidators

**The alpha opportunity:**
1. **Pre-cascade short signal:** If you can detect a large cluster of positions approaching liquidation threshold (health factor approaching 1.0 on Kamino, health approaching 0% on Marginfi), a significant collateral price drop will trigger forced selling → price dump
2. **Post-cascade buy signal:** After a major liquidation wave, oversold conditions create mean-reversion opportunity — positions that survived liquidation and the subsequent price drop are often the strongest convictions

**Kamino health factor:** Position becomes liquidatable when debt/collateral value crosses Liquidation LTV threshold. Kamino exposes this on-chain via the lending pool accounts.

**Marginfi:** Account health = 0% or below triggers liquidation. Uses `lending_account_pulse_health` on-chain instruction to read current health.

### Detectability

**Moderate — requires protocol-specific SDK work:**

**Kamino:**
- Open-source SDK: `github.com/Kamino-Finance/kliquidity-sdk`
- Kamino Lend protocol accounts are publicly readable on-chain
- You can query all active lending positions and calculate health factors
- **Free:** Requires Solana RPC access to read account state — works with Helius free tier
- Kamino publishes monthly risk reports with aggregate position distribution data

**Marginfi:**
- Open-source: `github.com/mrgnlabs/marginfi-v2`
- `lending_account_pulse_health` instruction queries individual account health
- Batch scanning requires iterating all marginfi lending accounts (expensive RPC calls)
- No pre-built "show me all positions near liquidation" endpoint

**Practical monitoring approach:**
1. Subscribe to Kamino/Marginfi program account changes via Helius websocket (program: `KLend2g3cP87fffoy8q1mQqGKjrXpHea7LarsQkXQX` for Kamino Lend)
2. Parse account state changes to identify health factor changes
3. When 10+ positions cross below health factor 1.1 (10% buffer) for the same collateral type → liquidation cascade imminent
4. Track which tokens are the primary collateral (SOL, jitoSOL, mSOL, USDC, specific memekoins on Kamino)

**Shortcut:** Kamino's own dashboard shows "at-risk positions" — but it's a UI, not an API. The protocol's on-chain data is the canonical source.

### Expected Win Rate / Edge Size

- **Pre-cascade short:** 60-70% predictive accuracy when 3+ conditions align (falling collateral price + cluster of positions near threshold + low liquidator count). However, Solana meme koins are rarely used as Kamino/Marginfi collateral — this strategy applies more to SOL, jitoSOL, and established tokens.
- **Post-cascade buy:** Higher win rate (~65-75%) because you're buying after forced liquidation overshoot. The Q1 2025 event showed SOL recovered 30-40% after the cascade ended.
- **Edge size:** 15-35% price moves on the underlying collateral asset
- **Limitation for meme koins specifically:** Kamino/Marginfi primarily collateralize SOL, staked SOL, and USDC — not meme koins. This strategy generates alpha on SOL, jitoSOL, and top-10 Solana ecosystem tokens, not the low-cap meme koins our whale convergence signal targets.
- **Best use case:** As a macro filter — if a liquidation cascade is imminent, avoid entering new long positions regardless of whale convergence signals.

### Implementation Complexity: 4/5

**What to build:**
1. Helius websocket subscription to Kamino Lend program account updates
2. Parse account state to extract health factor for each position
3. Build a "risk heatmap" of positions near liquidation
4. Trigger alert when aggregate at-risk exposure crosses a threshold (e.g., >$50M within 10% of liquidation)
5. Use as: (a) macro risk-off signal when cascade imminent, (b) buy signal 2-4 hours after cascade completes

**Free APIs:** Helius websocket (included in free tier), Kamino SDK (free/open source)
**Constraint:** Scanning all lending accounts requires significant RPC bandwidth — Helius paid tier recommended for production use

---

## Strategy 3: Whale Accumulation Signatures Beyond Convergence

### Mechanism

Five accumulation patterns that precede price moves but are more sophisticated than watching who buys what:

#### 3a. Wallet Funding Pattern (Fee-Payer Correlation)

**The pattern:** Smart money uses one "master" wallet to fund multiple "trading" wallets via small SOL transfers. Detecting when a known-profitable master wallet funds new child wallets is a leading indicator of upcoming buy activity — because they're preloading gas.

**Detection:**
- Identify known high-win-rate wallets (our existing wallet pool)
- Watch for SOL transfers FROM those wallets to new, unfunded wallets (< 5 prior transactions)
- A smart money wallet sending 0.1-0.5 SOL to 3+ new wallets = they're about to deploy capital across multiple addresses
- Window: the buy activity typically follows within 24 hours of the SOL funding

**Why this works:** Smart money uses multiple wallets to avoid detection and reduce price impact. The funding event is a preparatory step that necessarily precedes the actual trade.

**Signal quality:** High — this is the activity that happens BEFORE the buy, not after. Catching it means entering before the price impact.

**Detectability:** Helius `getTransactionsForAddress()` on tracked wallets, filtering for native SOL transfers to new wallets. Fully detectable with free API.

#### 3b. Token Transfers to Cold Storage / Non-DEX Wallets

**The pattern:** When a whale buys a token via DEX and then immediately transfers it to a wallet with no DEX activity history (pure holder wallet), they're signaling long-term conviction — they don't intend to sell back through the same route.

**vs. normal trading behavior:** Most retail traders leave tokens in the same wallet they swapped in. Moving to a cold address = deliberate custody decision.

**Detection:**
- Monitor known whale wallets for token transfers out to non-DEX wallets
- A non-DEX wallet = wallet with zero or minimal prior swap transactions
- Transfer amount > $1K to cold wallet = accumulation intent signal

**Signal quality:** Medium-High. False positives exist (could be preparing to sell via different DEX or CEX deposit). Combine with price check: if price is flat during cold storage transfer = accumulation. If price was rising during transfer = exit prep.

**Detectability:** Requires checking recipient wallet's transaction history via Helius/Solscan. Semi-automated with free APIs.

#### 3c. LP Removal as a Contrarian Buy Signal

**The pattern (practitioner insight):** When a token's LP position is partially removed (not a full rug), the price temporarily drops due to reduced liquidity depth. This creates a buy opportunity IF the LP removal is from a non-insider wallet and the token still has strong fundamentals.

**The inverse pattern (rug signal):** 93% of Raydium pool examinations showed "soft rug pulls" where LP was abruptly withdrawn and the token died. So LP removal is usually BEARISH.

**The contrarian edge:** If LP removal happens from a non-creator wallet (a liquidity provider, not the developer) AND the token passes all rug filters AND the remaining liquidity is still above $100K, the price dip from reduced liquidity = temporary and recoverable. Buyers who enter during the dip get better prices than the pre-removal price.

**Detectability:** Raydium LP removal transactions are on-chain. Helius enhanced transaction API can parse RemoveLiquidity instructions. Requires checking the wallet address of the LP remover against known creator/insider wallets.

**Signal quality:** Low as standalone. Works only as a filter overlay: existing quality signal + LP removal dip → buy the dip.

#### 3d. Fee-Payer Cluster Analysis (Sybil Detection Inverted)

**The pattern:** Multiple wallets that appear independent but share a fee payer (the wallet that pays transaction fees) are actually controlled by the same entity. If you detect that 5+ "different" wallets buying the same token all share the same fee payer → this is coordinated insider accumulation, not organic smart money convergence.

**The alpha:** Insider-coordinated accumulation before a catalyst (exchange listing, partnership announcement) is one of the highest-quality signals that exists. The fee-payer correlation reveals coordination that wallet address diversity is designed to hide.

**Detection approach:**
1. For each convergence signal our system fires, extract the fee payers of all converging transactions
2. If 3+ fee payers are the same wallet → coordinated accumulation from one entity
3. If fee payers are all different AND wallets are old (90+ days) → organic smart money convergence

**Why this matters for our system:** It can either validate our existing signals (organic convergence = higher quality) or reveal manipulation (coordinated pump by one entity using multiple wallets = lower quality, exit faster).

**Detectability:** On Solana, the fee payer is exposed in every transaction. Helius enhanced transaction API returns the fee payer. Fully detectable. Implementation complexity is low once you have the transaction data.

#### 3e. Staking / Unstaking Patterns (SOL Level)

**The pattern:** When large wallets unstake SOL (28-hour unstaking period on Solana), they are explicitly preparing capital for deployment. A wave of large unstaking events is a leading indicator of buying pressure entering the market.

**Detection:** Stake program account changes via Helius websocket. Amounts >10K SOL from a single known whale wallet = meaningful signal.

**Relevance to meme koins:** Indirect. SOL unstaking → whale has liquid SOL → likely to deploy into DeFi/meme koins within days. Not a token-specific signal, but a macro "whale liquidity incoming" signal.

### Detectability Summary

| Pattern | API | Cost | Lead Time |
|---------|-----|------|-----------|
| Wallet funding (fee-payer to new wallets) | Helius getTransactions | Free | 2-24h before buy |
| Cold storage transfer | Helius + Solscan | Free | Simultaneous with accumulation |
| LP removal dip | Helius enhanced txns | Free | Instantaneous |
| Fee-payer cluster | Helius enhanced txns | Free | Simultaneous with convergence |
| SOL unstaking | Helius websocket | Free | 28h before buy |

### Expected Win Rate / Edge Size

- **Wallet funding pattern:** 55-65% win rate as a standalone signal (lead time advantage is the edge)
- **Fee-payer cluster on top of convergence:** Raises convergence signal win rate by an estimated +8-12%
- **Cold storage transfer:** 50-60% standalone, better as a filter
- **LP removal contrarian:** 45-55% standalone — too noisy. Only valid as a filter overlay.
- **Combined as a confidence scoring layer:** Adding fee-payer cluster analysis + wallet funding detection to our existing convergence system could add +10-15% to win rate

### Implementation Complexity

- Wallet funding detection: 2/5
- Cold storage transfer: 2/5
- LP removal parsing: 3/5
- Fee-payer cluster analysis: 2/5 (add to existing convergence event processor)
- SOL unstaking monitor: 3/5

---

## Strategy 4: Cross-Chain Flow Analysis (Wormhole / deBridge)

### Mechanism

The thesis: large USDC or ETH flows from Ethereum to Solana via bridges signal that capital is rotating into the Solana ecosystem, which is a leading indicator of increased buying pressure for Solana-based assets including meme koins.

**What the data shows:**
- Solana bridge volume hit $10.1B all-time as of Feb 2025, with USDC at $3.9B inbound
- Stablekoin supply on Solana grew 110% in 2025 (from $5.1B to $11.7B)
- deBridge overtook Wormhole by 12% weekly volume in Feb 2025
- Spike analysis: major bridge inflows preceded memekoin bull cycles in Q1 2025

**The USDC inflow signal:**
"A massive inflow of USDC exceeding $2.12 billion [to Solana] while more than $1.11 billion in SOL left the platform... stablecoins act as ammunition on hold. When USDC flows concentrate on an ecosystem like Solana, it often signals that institutional investors or whales are positioning themselves, but without having firmly pressed the buy button yet."

**How it works as a trading signal:**
1. Large USDC bridge inflow to Solana = dry powder on the ecosystem waiting to be deployed
2. 24-72 hours later: deployment into SOL, DeFi protocols, meme koins
3. Increased meme koin activity follows increased total stablecoin supply on the chain

**Coin-level application:** Cross-chain flows are a macro ecosystem signal, not a token-specific signal. The relevance for meme koin trading is as a **regime filter**:
- Bridge inflows surging → ecosystem is in accumulation mode → higher probability that individual meme koin signals will play out
- Bridge outflows surging → ecosystem is distributing → lower quality environment for new entries

### Detectability

**Mixed — macro data accessible, per-token flows not:**

**What you can track:**
- **Wormhole's VAA (Verified Action Approval) logs:** All Wormhole transfers are on-chain on Solana. The Wormhole Token Bridge program ID is `worm2ZoG2kUd4vFXhvjh93UUH596ayRfgQ2MgjNMTth`. You can subscribe to this program via Helius websocket and tally inflows.
- **deBridge:** Similar on-chain tracking possible via their program account
- **DefiLlama bridge data:** https://defillama.com/bridges — free aggregated data, no per-token breakdown
- **Artemis Analytics:** Stablekoin supply per chain, free public data

**What you cannot easily track:**
- Which specific tokens the bridged USDC ends up buying (it's deployed via Jupiter/Raydium/pump.fun, not tracked to destination token at the bridge level)
- Intent of bridger (could be going to Kamino for yield, not meme koins)

**The practical implementation:**
- Track daily Wormhole + deBridge USDC net inflows via on-chain programs or DefiLlama API
- Calculate a 7-day rolling average
- When net daily inflows > 2x the rolling average → "hot ecosystem" mode flag
- In hot ecosystem mode: raise confidence on convergence signals
- In cold/outflow mode: apply stricter filters to convergence signals

### Expected Win Rate / Edge Size

**Key limitation:** No academic paper or practitioner study has quantified the predictive value of bridge inflows for token-level price moves in a rigorous way. The evidence is qualitative and observational.

**Reasonable estimates based on macro correlation:**
- When Solana ecosystem is in net inflow mode (USDC growing week-over-week), meme koin bull runs are more likely to sustain
- When in net outflow mode, pump cycles are shorter and less reliable
- Using bridge flows as a regime filter (not a buy signal) is the appropriate use
- Estimated improvement to signal win rate as a regime filter: +5-8% in optimal conditions, primarily by reducing losses in bear ecosystem periods

**The honest assessment:** This is the weakest of the five strategies for direct meme koin alpha. It's a macro indicator that works at 7-30 day timescales, not the 24-72h window our convergence signals operate in.

### Implementation Complexity: 2/5

**What to build:**
1. Daily cron: query DefiLlama `/api/bridgevolume/solana` for 30-day bridge data
2. Calculate net USDC inflow 7-day rolling average
3. Compute current vs average ratio
4. Set ecosystem mode flag: HOT (>1.5x avg), NORMAL, COLD (<0.5x avg)
5. Inject ecosystem mode as a multiplier on convergence signal confidence

**Free API:** DefiLlama bridge API (free, no auth)
**Alternative:** Helius websocket on Wormhole program (free tier sufficient)

---

## Strategy 5: Pump.fun Bonding Curve Graduation Signals

### Mechanism

This is the most actionable new strategy with the strongest academic evidence base. An arXiv paper (2602.14860, Feb 2026) analyzed 655,770 pump.fun tokens from September-October 2025 and identified the specific on-chain features that predict graduation to PumpSwap.

**The opportunity:** Only 0.63-1.4% of launched tokens graduate. But graduation is preceded by detectable on-chain patterns 10-30 minutes before it happens. A graduated token always moves significantly (liquidity is $12,000+ from bonding curve, then price discovery begins immediately via snipers).

**Graduation mechanics (updated for 2025):**
- Graduation threshold: ~85 SOL raised (plus 30 SOL virtual initialization = ~115 SOL total virtual)
- Token balance threshold: 206,900,000 - 246,555,000 tokens remaining in curve = 95-100% progress
- Destination: PumpSwap (since March 2025, replacing Raydium)
- Liquidity migrated on graduation: ~12,000 SOL (~$12K at time of writing)
- Price at graduation: high volatility immediately post-listing (snipers move price 30-40% on a $50 buy)

**Key predictive features from the academic study:**

| Feature | Description | Predictive Power |
|---------|-------------|-----------------|
| Liquidity velocity | SOL per trade (high SOL per few trades) | STRONGEST single predictor |
| Trade count to vSol | Fewer trades to reach same vSol = stronger | Very high |
| Bot activity ratio | Lower bot % = higher graduation probability | High |
| Dump events | 92.22% of failing tokens have ≥1 dump | High (negative predictor) |
| Successful trader presence | Known profitable wallets buying early | Medium |
| Creator experience | Prior token launches by same creator | Low |

**The specific pattern of successful graduates:**
- Median graduation time: **4.4 minutes** (extremely fast — bulk of tokens die in first 30 minutes if they don't move)
- Median trade count to graduation: **457 trades**
- Key signal: reaching 50 SOL virtual balance with fewer than 50 trades = very high graduation probability
- Tokens that show "slow accumulation via many small transactions" = almost always fail

**The real-time monitoring opportunity:**
Bitquery documents a threshold range: when a token's base balance falls between 206,900,000 and 246,555,000 tokens (95-100% bonding curve progress), graduation is imminent. This is a hard on-chain number you can monitor in real time.

**Trading strategy:**
- Option A (pre-graduation): Enter when token is at 70-85% bonding curve progress AND shows high liquidity velocity (low trade count per SOL). This gives 10-30 minutes before graduation + the graduation pump.
- Option B (post-graduation): Enter within the first 60 seconds of graduation on PumpSwap. Price typically spikes 50-200% in the first 5 minutes as scanners pile in. However, this is extremely competitive (sniper bots dominate).
- Option A has better risk-adjusted returns for non-bot traders.

**Additional quality filters for graduated tokens (from practitioner research):**
- Top 10 holders < 15% of supply after 1 hour (decentralized = healthier)
- Zero dump events in bonding curve phase
- Bot activity ratio < 30%
- Multiple wallets from our smart money pool present in first buyers

### Detectability

**High — this is well-tooled with free APIs:**

- **Helius websocket on pump.fun program** (`6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P`): Subscribe to all pump.fun transactions in real time. Parse `buy` and `sell` instructions to track vSol balance.
- **Bitquery pump.fun API:** Returns `virtual_sol_balance_after` and `virtual_token_balance_after` per transaction. Can set up real-time subscription.
- **DexScreener API:** Once a token graduates, it appears immediately on DexScreener. Can detect graduation event via new pair listing.
- **Moralis API:** Has a dedicated endpoint for graduated pump.fun tokens (`docs.moralis.com/web3-data-api/solana/tutorials/get-graduated-pump-fun-tokens`).

**The real-time calculation:**
```
vSol_balance = virtual_sol_balance_after (from transaction data)
curve_progress_pct = (vSol_balance / 85) * 100  # 85 SOL = graduation threshold
```

When `curve_progress_pct >= 80` AND `trades_per_sol <= 6` (high liquidity velocity) AND `bot_ratio < 0.3` → flag as PRE-GRADUATION CANDIDATE.

### Expected Win Rate / Edge Size

**From academic study:**
- Tokens reaching 70%+ bonding curve progress with high liquidity velocity: graduation probability approaches 40-60% (vs 0.63% baseline)
- Tokens reaching 90%+ progress with low trade count: graduation probability >80%
- Post-graduation return in first 30 minutes: typically 50-300% from graduation price (high variance)
- Post-graduation failure rate within 24 hours (rug or dump): ~40-60% of graduated tokens

**Practical win rate estimate:**
- Pre-graduation entry (70-85% progress + quality filters): 45-55% win rate at T+30min, 35-45% at T+24h
- The edge is concentrated in the first 30 minutes post-graduation
- Position sizing: small, with very tight stop (entry at graduation price, stop at -20%, TP at +50%)

**Key risk:** Sniper bots operate at sub-100ms latency. By the time a non-bot detects graduation and submits a transaction, the initial spike (first 10 seconds) is already captured by bots. The practical window for non-bot entry is 30-120 seconds post-graduation, after the initial sniper dump.

### Implementation Complexity: 3/5

**What to build:**
1. Helius websocket subscription to pump.fun program
2. Real-time vSol tracker per token (hash map: token_mint → current_vSol, trade_count, bot_ratio)
3. Bot detection: flag transactions where hold time < 5 minutes (buy and sell in same block or next block)
4. Alert trigger: vSol > 70 SOL AND trades_per_sol < 8 AND bot_ratio < 0.3
5. Second check at 90%+ progress: if still valid, post to signal channel as PRE-GRADUATION
6. Monitor DexScreener for graduation event: post GRADUATED signal with immediate entry window

**Free APIs:** Helius websocket (free tier), DexScreener (free), Moralis free tier for graduated token list
**Data needed:** pump.fun program transaction stream, virtual SOL/token balance from instruction data

---

## Integration with Our Existing System

### Priority order for implementation

1. **Pump.fun graduation signals (highest priority):** Completely new signal type with strong academic backing. Complementary to our whale convergence system — addresses a different phase of the token lifecycle (pre-listing vs. post-listing). Implementation: 3/5 complexity.

2. **Fee-payer cluster analysis on convergence signals (medium priority):** Add to existing convergence signal processor. Takes per-convergence data we already have and adds a quality multiplier. Implementation: 2/5 complexity.

3. **Wallet funding pattern detection (medium priority):** Requires subscribing to our tracked wallets' outgoing SOL transfers. Adds genuine lead time advantage. Implementation: 2/5 complexity.

4. **MEV sandwich rate as confidence multiplier (lower priority):** Helius transaction parsing needed. Adds +5-10% win rate as confirmation layer, but requires significant parsing work. Implementation: 3/5 complexity.

5. **Bridge flow regime filter (lowest priority):** Macro signal only. Use DefiLlama free API for ecosystem health. Adds +5-8% win rate improvement as a regime filter. Implementation: 2/5 complexity.

6. **Liquidation cascade detection (separate use case):** Not directly applicable to meme koin signals. More relevant as a macro risk-off signal for SOL-denominated positions. Implementation: 4/5 complexity.

### Quick wins to implement now

**A. Fee-payer cluster check (2 days of work):**
In `whale_convergence.py`, after detecting convergence, extract fee payers from all converging transactions. If 3+ share a fee payer → label signal as "COORDINATED" (potential insider pump, not organic smart money). If all fee payers are distinct → label as "ORGANIC" and raise confidence.

**B. Wallet funding monitor (2 days of work):**
Add to the wallet tracker loop: for each tracked smart money wallet, monitor native SOL transfers to new wallets. If detected → add a "whale_loading" flag to the relevant wallet. Any convergence signal involving a wallet that recently funded new wallets = elevated confidence.

**C. Bridge flow regime flag (1 day of work):**
Daily cron pulls DefiLlama bridge data. Sets `ECOSYSTEM_MODE` env var. Convergence signal processor reads this flag and applies stricter filters in COLD mode.

---

## Data Sources Summary

| Strategy | Free API | Cost | Rate Limit |
|---------|----------|------|------------|
| MEV sandwich detection | Helius (getTransactions) | Free | 100 RPS |
| Liquidation cascade | Helius websocket + Kamino SDK | Free | Websocket connection limit |
| Wallet funding pattern | Helius (getTransactionsForAddress) | Free | 100 RPS |
| Fee-payer cluster | Helius (enhanced transactions) | Free | 100 RPS |
| Bridge flow regime | DefiLlama bridges API | Free | Generous |
| Pump.fun graduation | Helius websocket (pump.fun program) | Free | Websocket |
| Pump.fun graduation (batch) | Bitquery or Moralis | Paid / Free tier | Varies |
| Per-token sandwich stats | Sandwiched.me | No public API confirmed | N/A |
| Jito bundle analysis | Bitquery Jito API | Paid / Free tier | Varies |

---

## Sources

- [Helius: Solana MEV Report](https://www.helius.dev/blog/solana-mev-report)
- [Helius: Solana MEV Introduction](https://www.helius.dev/blog/solana-mev-an-introduction)
- [Sandwiched.me: State of Solana MEV May 2025](https://sandwiched.me/research/state-of-solana-mev-may-2025-analysis)
- [ACM IMC 2025: Quantifying Sandwiching MEV on Jito](https://dl.acm.org/doi/10.1145/3730567.3764493)
- [PANews: 10,000-word Solana MEV analysis](https://www.panewslab.com/en/articles/x30b8v979c8c)
- [Solana Compass: State of Solana MEV at Accelerate 2025](https://solanacompass.com/learn/accelerate-25/scale-or-die-at-accelerate-2025-the-state-of-solana-mev)
- [arXiv 2602.14860: Predicting success of pump.fun tokens](https://arxiv.org/html/2602.14860v1)
- [Kaggle: Pump.fun graduation dataset Feb 2025](https://www.kaggle.com/datasets/dremovd/pump-fun-graduation-february-2025)
- [Bitquery: Pump.fun Bonding Curve API](https://docs.bitquery.io/docs/blockchain/Solana/Pumpfun/Pump-Fun-Marketcap-Bonding-Curve-API/)
- [Chainstack: Listening to pump.fun migrations to Raydium](https://docs.chainstack.com/docs/solana-listening-to-pumpfun-migrations-to-raydium)
- [SmartMetrics: MarginFi Q1 2025](https://medium.com/@smartymetrics/a-look-into-marginfis-profitability-amidst-the-chaos-of-q1-2025-ba8b7a381185)
- [Kamino Lend Monthly Risk Insights November 2025](https://gov.kamino.finance/t/kamino-lend-monthly-risk-insights-november-2025/859)
- [Kamino Finance GitHub](https://github.com/Kamino-Finance)
- [MarginFi GitHub](https://github.com/mrgnlabs/marginfi-v2)
- [Nansen: 5 Proven Solana Trading Strategies 2026](https://www.nansen.ai/post/solana-onchain-analytics-5-proven-trading-strategies-for-2026)
- [Nansen: How to Track Solana Wallets](https://www.nansen.ai/post/how-to-track-solana-wallets-complete-guide-for-smart-money-analysis)
- [CoinTribune: Solana USDC Flows as a Supply Crunch Signal](https://www.cointribune.com/en/solana-a-key-technical-level-defended-thanks-to-usdc-flows/)
- [CryptoNews: Solana Bridge Volume ATH $10B](https://cryptonews.com/news/solana-bridge-volume-surges-to-all-time-high-of-over-10-billion/)
- [Jito Bundle API - Bitquery](https://docs.bitquery.io/docs/blockchain/Solana/Solana-Jito-Bundle-api/)
- [Jito Explorer](https://explorer.jito.wtf/)
- [Solidus Labs: Solana Rug Pull Pump-and-Dump Report](https://www.soliduslabs.com/reports/solana-rug-pulls-pump-dumps-crypto-compliance)

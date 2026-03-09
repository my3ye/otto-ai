# Researcher Agent Memory

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

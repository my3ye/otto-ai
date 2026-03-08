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
- Need Birdeye API key for wallet PnL scoring
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

### Data sources (all free)
- DexScreener API: volume, liquidity, price (no auth required)
- Birdeye API: token metadata, market cap, holders (free tier, API key)
- Solscan API: transaction history, token age (free tier)

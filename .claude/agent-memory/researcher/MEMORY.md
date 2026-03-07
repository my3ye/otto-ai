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
- Market cap $100K-$3M range
- Pool liquidity ≥$100K
- Not already pumped >25% in last 6h
- Token age ≥3 days

### Jupiter referral setup
- URL: https://referral.jup.ag/
- Connect wallet → create account → select fee tier (0.1/0.5/1%)
- Embed in every signal: jup.ag/swap/SOL-[TOKEN]?referrer=[KEY]&feeBps=50
- Jupiter takes only 2.5% of fees earned

### Data sources (all free)
- DexScreener API: volume, liquidity, price (no auth required)
- Birdeye API: token metadata, market cap, holders (free tier, API key)
- Solscan API: transaction history, token age (free tier)

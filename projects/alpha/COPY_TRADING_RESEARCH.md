# Project Alpha: Copy Trading — API Research & Architecture

**Date:** 2026-02-21
**Status:** Phase 1 complete — data ingestion live

---

## API Comparison: Solana Wallet Tracking

### 1. Helius — **PRIMARY (active)**
- **Auth:** API key (have it: `e4218e74-...`)
- **Cost:** Free tier (rate limits apply)
- **Key endpoints:**
  - `GET /v0/addresses/{address}/transactions?type=SWAP` — Enhanced parsed swap events
  - Provides: signature, timestamp, source DEX, token inputs/outputs with amounts and decimals, fee
  - `POST mainnet-helius-rpc/?api-key=...` — Full Solana RPC (getTokenAccounts, etc.)
- **Rate limits:** ~15 RPC calls / scan cycle manageable; enhanced TX API more generous
- **Data quality:** ★★★★★ — Best in class. Fully parsed swap events with inner swap routing detail
- **Verdict:** **Use this. Already working.**

### 2. Birdeye — **Requires paid API key**
- **Auth:** API key required even for basic endpoints
- **Response:** `{"success": false, "message": "Unauthorized"}` with empty key
- **Offers:** Wallet PnL tracking, portfolio history, trader leaderboards
- **Cost:** Paid plans ~$100-500/month for meaningful usage
- **Verdict:** Best for pre-built PnL analytics, but we'd need to pay. Helius covers the raw data layer.

### 3. Cielo Finance — **Requires auth**
- **Auth:** Login-based, no public API documented
- **Use case:** Consumer-facing wallet analytics dashboard
- **Verdict:** Not suitable for programmatic access without paid agreement.

### 4. Solscan — **Deprecated public API**
- **Auth:** None for v1 (but v1 is being sunset)
- **Verdict:** Don't use. Rate limits hit immediately, API sunset in progress.

### 5. DexScreener — **Free, supplemental use**
- **Auth:** None
- **Endpoints:** Token pairs, price, volume data — but wallet-level data not available
- **Use case:** Token metadata lookup (symbol, liquidity, 24h volume) to enrich trade records
- **Verdict:** Good supplement for token metadata.

### 6. Jupiter Price API — **Free, supplemental use**
- **Auth:** None
- **Endpoint:** `GET https://api.jup.ag/price/v2?ids={mint}`
- **Use case:** Real-time token prices for PnL calculation
- **Verdict:** Reliable price oracle, use for trade valuation.

---

## Architecture Built

### Database Tables (migration 020)
```
alpha_wallets       — Smart money wallet registry (20 wallets loaded)
alpha_trades        — Normalized swap events (live data, 230 trades in 2h)
alpha_token_prices  — Token price cache (for PnL computation)
alpha_wallet_pnl    — Periodic PnL snapshots
alpha_copy_signals  — Convergence detection events
```

### Data Collection Script
`~/otto/tools/copy_trading_tracker.py`

- Fetches swap events via Helius Enhanced TX API
- Normalizes: direction (BUY/SELL/UNKNOWN), input/output mints, amounts, DEX source
- Direction logic: stablekoin/SOL→token = BUY, token→stablekoin/SOL = SELL
- Stores to PostgreSQL via asyncpg (deduplicates by tx signature)
- Detects convergence signals: 2+ wallets buying same token in window
- Usage: `python3 tools/copy_trading_tracker.py --window 3600`

### Live Test Results
```
Wallets scanned: 12 of 20
Swaps ingested: 230 trades (2h window)
Unique tokens seen: 16
Convergence signals: 6 (tokens bought by 2+ smart wallets)
Top active wallets: SM_3 (23 trades, 11 buys), SM_4 (50 trades, 5 buys), SM_5 (27 trades, 4 buys)
```

---

## Wallet Intelligence Observations

**SM_1** — MEV/routing activity. 26/27 trades are USDC↔SOL (UNKNOWN direction). Likely arbitrage or MEV bot. Not suitable for copy trading.

**SM_2** — All 50 trades are SOL↔SOL via Jupiter. Internal routing. Also not copy-trade target.

**SM_3** — Most actionable: 11 BUYs, 6 SELLs across 5 distinct tokens. Swing trader. **Best copy target.**

**SM_4** — 5 BUYs across 4 tokens, 42 routing swaps. Good signal within the noise.

**SM_5** — 4 BUYs, 13 SELLs. High sell-side activity — either profit-taking or dumping bags.

**SM_10** — 3 BUYs, 15 SELLs. Similar to SM_5. Could be running a liquidation.

---

## Phase 2 Recommendations

### Immediate Next Steps
1. **PnL computation**: Join BUY and SELL records per wallet per token. Add Jupiter price lookups to calculate USD value in/out. Store realized PnL per trade pair.

2. **Heartbeat integration**: Run `copy_trading_tracker.py --window 3600` in each heartbeat scan cycle. Already implemented in `live_watcher.py` logic — just needs DB storage wired in.

3. **Alpha dashboard widget**: Feed `alpha_trades` and `alpha_copy_signals` tables into the :3100 dashboard. Show: top tokens bought by 2+ wallets, wallet activity leaderboard.

4. **Signal scoring**: Rate convergence signals by:
   - Number of confirming wallets (2 = medium, 3+ = high)
   - Total USD volume
   - Token age / pump.fun graduation status
   - Known wallet win rate

### Cost Assessment
- **Helius free tier**: Sufficient for 20 wallets × 50 txns = 1000 API calls/scan. At hourly scans: ~24,000 calls/day. Free tier allows ~100,000/month — **we're fine.**
- **Birdeye**: Would add pre-computed PnL scores and leaderboard. ~$150/month if we want it.

### Rate Limit Management
Current: 0.3s sleep between wallets = ~6s for 20 wallets. Within free tier comfortably.
If we hit limits: use webhook subscription (Helius supports webhook on-chain events — more efficient than polling).

---

## Integration Points

```bash
# Run manually
cd ~/otto && python3 tools/copy_trading_tracker.py --window 3600

# View DB data
docker exec memory-postgres-1 psql -U otto -d memory -c \
  "SELECT wallet_label, direction, COUNT(*) FROM alpha_trades GROUP BY 1,2 ORDER BY 1,2;"

# Sync wallet list updates
python3 tools/copy_trading_tracker.py --sync-wallets
```

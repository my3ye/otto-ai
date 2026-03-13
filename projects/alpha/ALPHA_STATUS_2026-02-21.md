# Project Alpha — Status Report & Go-Live Readiness
**Generated:** 2026-02-21 ~06:35 UTC
**Author:** Otto (task runner — P2 Alpha: expand wallet discovery + copy trading go-live prep)

---

## 1. Paper Trader Status

**Service:** `alpha-paper-trader.service` — **RUNNING** (started 2026-02-21 10:07 LKT)
**Runtime:** ~2 hours

**Current P&L:**
- Total trades: 1
- Open: 1 (USD1 stablekoin — false positive, should not have opened)
- Closed: 0
- Realized P&L: $0.00

**Root issue:** The paper trader opened the USD1 stablekoin as its first trade because the signal was generated before BUG FIX 5 (USD1 added to BASE_TOKENS filter) was applied to paper_trader.py's source modules. The main bot/main.py already has USD1 filtered, but paper_trader.py imports from backtest/signals/ which has independent filter logic.

**Assessment:** Paper trader is running but has effectively 0 real trades. The USD1 position will time-out at T+4h and close flat. Need 2+ weeks of clean trades before making statistical judgments.

---

## 2. Wallet Discovery — Expansion Results

**Previous count:** 15 wallets (SM_1 through SM_15)
**New count:** 20 wallets (added SM_16 through SM_20)

### New Wallets Added (2026-02-21)
| Label | Address (prefix) | Strategy | Early Buys | Pumped Tokens |
|-------|-----------------|----------|------------|---------------|
| SM_16 | Bz9ETFkwC59TYq4F | early_buyer | 2 | ALIEN (+4415%), ALIENJAK (+310%) |
| SM_17 | 8psNvWTrdNTiVRNz | early_buyer | 2 | ALIEN (+4415%), MUTT (+237%) |
| SM_18 | HFqp6ErWHY6Uzhj8 | early_buyer | 2 | ALIEN (+4415%), GOODBOY (+61%) |
| SM_19 | LvjCuiYEvNiHiXNA | early_buyer | 2 | ALIEN (+4415%), MUTT (+237%) |
| SM_20 | GpMZbSM2GgvTKHJi | early_buyer | 2 | ALIENJAK (+310%), GOODBOY (+61%) |

### Discovery Source
- DexScreener trending tokens: 26 Solana tokens checked, 5 met pump criteria
- Tokens analyzed: ALIEN (+4415%), ALIENJAK (+310%), MUTT (+237%), GOODBOY (+61%), TRENCH (+90%)
- Helius early buyer analysis: 200 earliest transactions per token
- 8 candidates with ≥2 early buys, 7 new (not already tracked), 5 added (cap limit)

### Signal Performance of Existing Wallets
- **SM_1, SM_2:** 4 HIGH signals each — the most active wallets (mev_routing, active_trader)
- **SM_3:** 1 HIGH signal
- **SM_4 through SM_15:** 0 HIGH signals — underperforming but not yet pruned (inactive < 14 days)

**Note:** No Birdeye API key → win_rate validation not possible. Current scoring is on-chain frequency only. Phase 2 improvement: add `BIRDEYE_API_KEY` to alpha/.env for true PnL-validated screening.

---

## 3. Helius WebSocket — Real-Time Tracking Design

### Current Architecture (Polling)
```
alpha-heartbeat (every 30min) → bot/main.py → Helius REST API
  → 20 wallets × getTransactions(limit=20) = 400 API calls/hour
  → Detects trades 0-30 minutes after they happen
  → Signal latency: up to 30 minutes
```

**Problem:** 30-minute latency is useless for meme koin copy trading. A pump.fun launch can 10× in under 5 minutes.

### Proposed Architecture (WebSocket)
```
live_watcher.py (persistent daemon)
  → Helius WebSocket: wss://mainnet.helius-rpc.com/?api-key=<key>
  → logsSubscribe per wallet (20 subscriptions) OR accountSubscribe
  → Real-time swap detection (< 1 second latency)
  → On swap detected → validate → execute copy trade
```

### Helius WebSocket Integration
```python
# WSS endpoint
WSS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Subscribe to transaction logs mentioning a wallet
subscribe_payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "logsSubscribe",
    "params": [
        {"mentions": [wallet_address]},
        {"commitment": "confirmed"}
    ]
}

# On notification: check if it's a SWAP type
# Then call Helius Enhanced TX API to get parsed details
# Then validate and execute copy trade
```

### Copy Trade Execution Flow
```
1. WebSocket notification: wallet X transacted
2. Call Helius Enhanced TX API (single tx parse, ~100ms)
3. Is it a SWAP buying a non-base token?
4. Is token not in BASE_TOKENS filter?
5. Is token not already in open positions?
6. Is it HIGH confidence (2+ wallets, or known alpha wallet)?
7. → YES: get Jupiter V6 quote
   GET https://quote-api.jup.ag/v6/quote
     ?inputMint=So11111111111111111111111111111111111111112  (SOL)
     &outputMint=<token_address>
     &amount=<lamports>  (0.1 SOL = 100000000)
     &slippageBps=100  (1% slippage)
8. POST https://quote-api.jup.ag/v6/swap
   {quoteResponse: <from step 7>, userPublicKey: <our wallet>}
9. Sign transaction with our keypair (solders library)
10. Submit via Helius RPC: sendTransaction
11. Log to paper_trades.jsonl / memory API
```

### Required Python Stack for Live Execution
```
pip install solders  # Solana keypair + transaction signing
pip install solana   # RPC client
pip install httpx    # Already installed
pip install websockets  # WebSocket client
```

---

## 4. Go-Live Readiness Assessment

### What's Ready ✅
| Component | Status |
|-----------|--------|
| Signal scanner (polling, 30min) | Running hourly via alpha heartbeat |
| Wallet list | 20 wallets, actively expanded |
| Backtesting framework | Complete |
| Paper trader daemon | Running (systemd), framework solid |
| BASE_TOKENS filter | USD1, ORCA, JUP, wSOL, USDC, USDT filtered |
| Signal deduplication | Fixed (BUG FIX 1-4) |
| Helius API key | Configured |

### What's Missing ❌ (Blockers)
| Component | Gap | Effort |
|-----------|-----|--------|
| **Trading wallet** | No WALLET_PRIVATE_KEY configured | Mev action: create + fund wallet with 1-2 SOL |
| **Jupiter swap executor** | `bot/live_trader.py` not built | 2-3 hours coding |
| **WebSocket live watcher** | Still polling at 30min latency | 3-4 hours coding |
| **Paper trading data** | 1 trade (false positive), need 2+ weeks | Time |
| **Statistical significance** | 4 HIGH signals in history, need 20+ | Time |

### Gaps Ranked by Criticality
1. **CRITICAL:** No trading wallet → cannot execute any trade
2. **CRITICAL:** No live execution module (Jupiter swap client)
3. **HIGH:** 30min polling latency → meme koins already mooned before signal fires
4. **HIGH:** Insufficient paper trading data (0 clean trades)
5. **MEDIUM:** No Birdeye API key → wallet quality scoring is weak

---

## 5. Realistic Timeline to Go-Live

### Week 1 (current week)
- [x] Paper trader daemon running
- [x] 20 wallets tracked
- [ ] **Build WebSocket live watcher** → cut latency 30min → <1 sec
- [ ] **Build Jupiter V6 swap executor** (paper mode first)
- [ ] Mev provisions trading wallet + funds 1-2 SOL

### Week 2
- [ ] Paper trading with real-time signals (1 week data)
- [ ] Fix paper_trader.py to use signals from bot/main.py (not backtest modules)
- [ ] If SM_8 or new wallets show Sharpe > 0.2 → go-live prep

### Week 2-3 (Go-Live Gate)
- [ ] ≥20 closed paper trades
- [ ] Win rate > 25%
- [ ] Sharpe > 0.2
- [ ] Max drawdown tested
- [ ] Live trader deployed at 0.05 SOL/trade with hard daily stop

**Honest assessment:** 2 weeks from today is achievable IF Mev provides the trading wallet this week and the WebSocket watcher is built. Going live in <1 week without paper trade validation would be betting blind.

---

## 6. Next Tasks Recommended

### P2-HIGH (build now):
1. **`bot/live_watcher.py`** — WebSocket daemon subscribing to all 20 wallets, writes signals in real-time to signals.jsonl. Replace polling completely for meme koin strategy.
2. **`bot/live_trader.py`** — Jupiter V6 quote + swap executor. Paper mode (log-only) first, live mode behind `--live` flag.
3. **Fix paper_trader.py signal source** — wire to signals.jsonl (the main scanner's output) instead of backtest/ modules.

### P2-MEDIUM (data collection):
4. Continue running wallet_discovery.py weekly to expand wallet pool.
5. Lower `MIN_EARLY_BUYS = 1` for discovery to find more candidates (then validate with signals).

### P0 (Mev action required):
6. **Provision trading wallet:** Create a new Solana wallet, fund with 1-2 SOL (for testing only), add private key to `~/otto/projects/alpha/.env` as `WALLET_PRIVATE_KEY`.
7. **Optional: Add Birdeye API key** for true win_rate/PnL wallet screening.

---

*Generated by Otto task runner. Task: [P2] Alpha: expand wallet discovery + copy trading go-live prep.*

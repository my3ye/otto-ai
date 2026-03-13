# Project Alpha — Solana Trading Strategy Plan
**Created:** 2026-02-19
**Status:** Research complete, ready for implementation

---

## Overview

Three strategies for Solana-based trading, ordered by risk/complexity ascending:
1. Traditional algo trading via DEX aggregation
2. Copy trading by tracking smart money wallets
3. Meme koin launch plays (pump.fun + Raydium)

Target: Week-1 foundation → live trading within 2 weeks.

---

## Strategy 1: Traditional Algo Trading

### Concept
Systematic buy/sell signals executed via Jupiter V6 against price feed data. Entry/exit based on TA signals (RSI, MACD, moving averages) on OHLCV data from Birdeye or DexScreener.

### Key Data Sources
| Source | Purpose | Access |
|---|---|---|
| Jupiter V6 API | Swap execution, price quotes | `https://quote-api.jup.ag/v6` |
| Pyth Network (Hermes) | Real-time price feeds | `https://hermes.pyth.network/` |
| Birdeye API | OHLCV data, token metadata | REST API, API key required |
| Dune Analytics | Historical trade data (SQL) | SQL, ~1-min latency |
| Helius RPC | Transaction submission (staked) | API key required |

### Architecture
```
Pyth/Birdeye price feed → Signal engine (Python) → Jupiter /quote → Jupiter /swap → Sign → Helius RPC submit
```

### Jupiter V6 Execution Flow
1. `GET /quote?inputMint=...&outputMint=...&amount=...&slippageBps=50`
2. `POST /swap` with `{quoteResponse, userPublicKey}`
3. Sign returned transaction with keypair
4. Submit via Helius staked RPC (SWQoS improves landing rate)

### Recommended Libraries
- **Python:** `solders` (keypairs, signing), `solana-py` (RPC), `anchorpy` (on-chain programs), `httpx` (async HTTP)
- **Reference repos:**
  - `github.com/noahtheprogrammer/soltrade` — Python, Jupiter-based, clean architecture
  - `github.com/outsmartchad/solana-trading-cli` — production-ready, Jito + gRPC included

### Backtesting Approach
1. Pull historical OHLCV from Birdeye API (free tier available)
2. Or query Dune `dex.trades` for Solana (full genesis history)
3. Replay signal logic in Python/pandas, simulate fills with 0.5% slippage assumption
4. No Solana-native backtesting framework exists — custom pandas loop is standard practice

### Setup Complexity: **5/10**
Jupiter abstracts DEX routing complexity. Main challenges: latency tuning and transaction landing rate.

### Week-1 Checklist
- [ ] Provision Helius API key (free tier: 10 RPS)
- [ ] Set up Python env: `solders`, `solana-py`, `anchorpy`, `httpx`
- [ ] Build Jupiter swap wrapper: quote → swap → sign → send
- [ ] Connect Pyth Hermes WebSocket for real-time price feed (SOL/USDC)
- [ ] Implement simple RSI strategy (RSI < 30 = buy, > 70 = sell) on 15m OHLCV
- [ ] Backtest on 90 days Birdeye/Dune data
- [ ] Paper trade on devnet for 48 hours
- [ ] Deploy with $50 USDC test capital on mainnet

---

## Strategy 2: Copy Trading (Smart Money Tracking)

### Concept
Identify wallets with strong on-chain PnL history. Subscribe to their activity via Helius webhooks or WebSocket. When they buy a token, replicate the trade proportionally within the same slot.

### Key Data Sources
| Source | Purpose | Access |
|---|---|---|
| Helius Webhooks | Real-time wallet swap events | API key, up to 100k addresses |
| Birdeye Wallet PnL API | Score wallets by win rate / ROI | `GET /wallet/v2/pnl`, API key |
| Nansen Wallet Profiler | Multi-cycle PnL, smart money labels | Paid plan |
| Cielo Finance | Wallet discovery, cross-chain PnL | Pro plan |
| Jupiter V6 | Copy-trade execution | Same as Strategy 1 |
| Jito | Bundle submission for priority | Jito tip auction |

### Alpha Wallet Criteria
- Win rate > 60% over 50+ trades
- Active in last 30 days
- Early entries into tokens that 5x'd+
- No bundler/wash trading patterns (check funding source clustering)
- Wallet age > 30 days

### Execution Flow
```
Helius WebSocket (logsSubscribe on wallet set)
  → Detect SWAP event
  → Extract inputMint, outputMint, amount
  → Scale amount proportionally to our capital
  → GET Jupiter /quote
  → POST Jupiter /swap
  → Sign + submit via Jito bundle (same slot target)
```

### Latency Architecture
- **Detection:** Helius WebSocket `logsSubscribe` (~confirmed slot, ~400ms)
- **Better:** Jito ShredStream (200–500ms before full propagation)
- **Execution:** Staked RPC (Helius/Triton) + Jito bundle tip for priority
- **Target:** Land within same or next slot as tracked wallet

### Recommended Libraries
- Same Python stack as Strategy 1
- `github.com/outsmartchad/solana-trading-cli` — Jito integration built in
- Helius SDK (TypeScript) for webhook management if preferred

### Backtesting Approach
1. Select candidate wallets from Birdeye PnL API (top 20 by win rate)
2. Pull their full swap history via `Helius getTransactionsByAddress()`
3. For each historical swap, fetch token price at T+0 and T+5min, T+30min, T+1h from Birdeye OHLCV
4. Simulate copy execution with 1-slot delay + 0.3% slippage assumption
5. Calculate aggregate PnL, drawdown, win rate

### Setup Complexity: **7/10**
Webhook setup is easy. Hard parts: latency optimization (Jito/ShredStream), avoiding sandwich attacks, wallet discovery pipeline.

### Week-1 Checklist
- [ ] Pull top 50 wallets from Birdeye PnL API (`win_rate > 0.6, trade_count > 50`)
- [ ] Run backtest replay on top 10 wallets (last 30 days history via Helius)
- [ ] Select top 3 wallets by risk-adjusted return
- [ ] Set up Helius webhook or WebSocket listener on those 3 wallets
- [ ] Build copy-execution pipeline (detect → quote → swap → submit)
- [ ] Set position size limits (max 10% capital per copy trade)
- [ ] Test on devnet equivalent (mainnet paper-trade watching behavior)
- [ ] Deploy with $100 test capital, cap individual trade at $20

---

## Strategy 3: Meme Koin Launch Plays

### Concept
Detect newly launched tokens on pump.fun or Raydium within seconds of creation. Apply rug filters. Enter early on launches that pass safety checks. Exit at 2–3x or stop-loss at -30%.

### Key Data Sources
| Source | Purpose | Access |
|---|---|---|
| PumpPortal WebSocket | Real-time pump.fun launches | `wss://pumpportal.fun/api/data`, free |
| Raydium `logsSubscribe` | New AMM pool detection | Helius/Triton RPC WebSocket |
| DexScreener API | New pair data, liquidity, volume | `https://api.dexscreener.com/`, free |
| Helius `getAsset` | Token authority checks (mint/freeze) | Helius API key |
| RugCheck.xyz API | Automated rug risk scoring | Free tier available |

### Detection Sources
**pump.fun (pre-Raydium):**
```javascript
const ws = new WebSocket("wss://pumpportal.fun/api/data");
ws.send(JSON.stringify({ method: "subscribeNewToken" }));
// Payload: mint, name, symbol, creator, initialBuy, bondingCurveKey
```

**Raydium new pool (on-chain):**
- Subscribe `logsSubscribe` to Raydium AMM program: listen for `initialize2` instruction
- Or `onProgramAccountChange()` on Raydium program — 80% fewer RPC units than log monitoring
- Or Shyft/Triton gRPC stream (lowest latency)

### Rug Safety Filters (mandatory before entry)
| Check | Safe | Reject |
|---|---|---|
| Mint authority | Revoked / null | Active |
| Freeze authority | Revoked / null | Active → honeypot |
| Top 10 holder % | < 30% supply | > 50% |
| LP status | Burned / locked | Unlocked |
| Bundler detection | Clean | Coordinated buys same block |
| Creator wallet age | > 30 days | Freshly created |
| Metadata mutability | Immutable | Mutable |

**Reality check:** ~98% of pump.fun tokens show manipulation signals. Filter ruthlessly — aim for < 2% of launches passing all checks.

### Execution Flow
```
PumpPortal WS / Raydium log event
  → Token address extracted
  → Helius getAsset() → check mint/freeze authority
  → RugCheck.xyz score check
  → Top holder concentration check
  → PASS: GET Jupiter /quote (SOL → token)
  → Execute swap with tight slippage (5–10%)
  → Monitor price: exit at 2x OR -30%
```

### Backtesting Approach
1. Pull historical pump.fun launches from Dune (`pump_fun_solana.trades` table)
2. Apply filter criteria retroactively at T+0 (launch time)
3. Simulate entry at 5 minutes after launch, exit rules (2x or -30% stop)
4. Compare filtered vs unfiltered win rate and average return
5. Iterate filter thresholds to optimize precision vs recall

### Recommended Libraries
- `github.com/YZYLAB/solana-trade-bot` — Raydium + pump.fun + Jupiter in one repo
- `github.com/Humancyyborg/pumpfun_websocket` — pump.fun WebSocket monitor
- `github.com/iSyqozz/Solana-Raydium-Monitor` — TypeScript Raydium pool monitor

### Setup Complexity: **8/10**
Detection is straightforward. Hard parts: sub-second execution before initial spike is captured, rug filter tuning (over-filter = miss everything, under-filter = lose everything), bundler detection.

### Week-1 Checklist
- [ ] Set up PumpPortal WebSocket listener; log all new token events to PostgreSQL
- [ ] Implement Helius `getAsset` authority checker (mint + freeze + metadata mutability)
- [ ] Integrate RugCheck.xyz API for automated scoring
- [ ] Add holder concentration check (query top 10 holders via Helius)
- [ ] Backtest filter criteria on 30 days of Dune pump.fun data
- [ ] Tune filters: target < 5% pass rate, > 40% win rate on backtested set
- [ ] Build execution pipeline (quote → swap → position monitor → exit)
- [ ] Paper-trade for 48 hours (log decisions but don't execute)
- [ ] Deploy with $50 in SOL, max $5 per trade, tight stop-losses

---

## Shared Infrastructure

| Component | Solution | Notes |
|---|---|---|
| RPC | Helius (staked) | SWQoS critical for landing rate |
| Swap execution | Jupiter V6 | Self-hosted option for ultra-low latency |
| Tx priority | Jito bundles + tip | 5-tx atomic bundles |
| Price feeds | Pyth (standard), Switchboard Surge (custom) | |
| Historical data | Dune (SQL) or Birdeye API (OHLCV) | |
| Safety checks | Helius `getAsset` + RugCheck.xyz | |
| Language | Python (solders + solana-py + anchorpy) | TypeScript alternative if latency critical |
| Storage | PostgreSQL (already running) | Log all events and decisions |

---

## Week-1 Priority Order

1. **Foundation first** (Day 1–2):
   - Set up Helius API key
   - Build reusable Solana swap wrapper (Jupiter quote → sign → send)
   - Configure staked RPC connection

2. **Strategy 1 prototype** (Day 2–4):
   - RSI-based algo on SOL/USDC
   - Backtest on Birdeye data
   - Devnet paper trade

3. **Strategy 2 wallet discovery** (Day 4–6):
   - Pull and score wallets via Birdeye PnL API
   - Backtest replay on top 3 wallets
   - Set up Helius WebSocket listener

4. **Strategy 3 detection pipeline** (Day 6–7):
   - PumpPortal WebSocket listener running and logging
   - Rug filter pipeline (authority checks, holder concentration)
   - No execution yet — observe and score launches

**Live trading target:** End of Week 2, Strategy 1 first (lowest risk), then others sequentially.

---

## Risk Management (All Strategies)
- Max 2% of total capital per trade
- Stop-loss mandatory before position opens (not after)
- Max 3 concurrent open positions
- Daily loss limit: 5% of capital → pause and review
- Never deploy unbacktested code with real capital
- Keep 50% of capital in stable reserve (USDC)

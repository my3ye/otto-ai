# Native Crypto Trading & DeFi Intelligence — Architecture
*Designed: 2026-03-19 | Status: APPROVED FOR IMPLEMENTATION*
*Context: Mev directive — implement all BANKR Bot features natively. No external Bankr API connection.*

---

## Design: Native Crypto Engine — Full Otto & OMS Integration

### Problem

Mev directed that all Bankr Bot capabilities be implemented natively inside Otto's own stack. Bankr is an AI-powered NL crypto trading platform with cross-chain trading, portfolio management, signal publishing, token launching, conditional orders (limit/DCA/stop-loss), and DeFi integrations. The previous architecture (bankr-integration-architecture.md) was designed around Bankr's external API. That approach is cancelled. We now build everything in-house: our own NL parser, our own execution layer, our own signal board, our own conditional order system.

**Key advantage of native approach**: CDP AgentKit is already integrated and authenticated. We already have EVM wallet execution capability — the gap is routing/aggregation, price data, and the product layer around it.

---

### What Bankr Provides (Feature Inventory to Replicate)

| Bankr Feature | Native Replacement | Status |
|---|---|---|
| NL → trade execution | Claude NL Parser + 0x + CDP AgentKit | Build |
| Spot Swap (any token) | 0x Swap API → CDP execute | Build |
| Limit Orders | Price monitors table + heartbeat polling | Build |
| Stop-Loss | Price monitors table (trigger_type=stop_loss) | Build |
| DCA | Otto task queue + price monitors | Build |
| TWAP | Trade executor with time-sliced chunks | Phase 2 |
| Cross-chain bridging | 0x Cross-Chain (or LI.FI aggregator) | Phase 3 |
| Cross-chain wallets | CDP AgentKit (EVM) + existing Solana keys | Build |
| Portfolio tracking | Alchemy (EVM) + Birdeye (Solana) + Hyperliquid | Build |
| BANKR Signals (published) | Native signal board (OMS + public endpoint) | Build |
| Token Launch (Base) | Doppler contract direct via CDP AgentKit | Phase 3 |
| Token Launch (Solana) | Raydium LaunchLab via Solana web3.js | Phase 3 |
| DeFi: Polymarket | Direct Polymarket CLOB API | Phase 3 |
| DeFi: LP / Yield | Direct Uniswap V3 SDK | Phase 3 |
| LLM Gateway | We ARE the LLM. No replacement needed. | N/A |
| ERC-8004 Agent Identity | On-chain NFT for Otto (Phase 3) | Phase 3 |

---

### Approach

**Five-layer native stack:**

```
┌─────────────────────────────────────────────────────────────┐
│  OMS Frontend (/crypto page)                                 │
│  Trade terminal | Portfolio | Signals | Monitors | Launch    │
├─────────────────────────────────────────────────────────────┤
│  Memory API Routes (/crypto/*)                               │
│  parse | execute | portfolio | signals | monitors | launch   │
├─────────────────────────────────────────────────────────────┤
│  Native Crypto Engine (otto/memory/crypto/)                  │
│  nlparser | executor | price_feed | portfolio | monitors     │
│  signals | launch                                            │
├─────────────────────────────────────────────────────────────┤
│  Execution Foundation (already integrated)                   │
│  CDP AgentKit → Base/ETH/Polygon execution                   │
│  Hyperliquid wallets → perp trading                         │
├─────────────────────────────────────────────────────────────┤
│  External Market APIs (free/minimal cost)                    │
│  0x Swap API | CoinGecko | Birdeye | Alchemy RPC             │
└─────────────────────────────────────────────────────────────┘
```

**NL interpretation loop:**
```
User NL input ("Buy $200 of ETH on Base")
    ↓
nlparser.py → Claude (structured intent extraction)
    ↓ TradeIntent{action, token_in, token_out, amount_usd, chain, conditions}
executor.py → 0x API (get swap quote)
    ↓ SwapQuote{calldata, to, value, gas_estimate}
CDP AgentKit → sign + broadcast transaction
    ↓ TxHash
crypto_trades DB record (status: completed/failed)
    ↓
Optional: auto-publish to signal board if confidence > threshold
```

**Conditional orders (limit / stop-loss / DCA):**
```
User sets order → price_monitors table (status: active)
    ↓ (every heartbeat or dedicated price-poll job)
monitors.py → price_feed.py (current price)
    ↓ if trigger condition met
executor.py → execute swap
    ↓
price_monitors (status: triggered) + crypto_trades record
```

---

### Key Decisions

- **CDP AgentKit as wallet foundation**: CDP is already integrated and authenticated. It covers Base, ETH, Polygon. Alternative (Privy server wallets) would require new API key + service. CDP wins because it's already working.

- **0x Protocol for swap routing**: 0x provides aggregated DEX quotes (Uniswap, Curve, Balancer, etc.) with a single API. Free for quotes, 1% fee on swaps (embedded in calldata). Alternative: Uniswap SDK directly (no fee but single-protocol only). 0x wins for coverage.

- **Claude for NL parsing**: We ARE Claude. We can parse "buy $200 of ETH" ourselves. Bankr's NL parser was their core value-add. Ours is: Claude prompt → structured TradeIntent JSON. No external API call needed. Alternative: regex pattern matching (too brittle). Claude wins.

- **CoinGecko for price data**: Free, no API key for basic tier (50 calls/min), covers 10,000+ tokens. Alternative: Binance WebSocket (complex, overkill). CoinGecko wins for Phase 1. Birdeye for Solana-native tokens.

- **New tables vs. reusing bankr_* tables**: The `bankr_trades`, `bankr_signals`, `bankr_jobs` tables already exist in DB (applied via migration 058). However, they have Bankr-specific semantics (job_id, thread_id, bankr_signal_id). We create new `crypto_*` tables in migration 059 that have clean native semantics. Legacy bankr_* tables remain (empty) for reference. Decision: clean break prevents confusion.

- **Price monitors as heartbeat-polled**: Conditional orders (limit/SL/DCA) are stored in `price_monitors` table and checked by a dedicated monitoring job that runs every minute (via Otto task queue or a lightweight systemd timer). Alternative: websocket price feeds (complex infra). DB-poll wins for simplicity and restartability.

- **Signal board is native OMS feature**: Instead of publishing to bankrsignals.com, Otto publishes signals to its own DB + exposes via `/crypto/signals` endpoint. OMS shows the board. Public-facing page can be added at otto.lk/signals in Phase 3. Decision: full sovereignty, no external dependency.

---

### API / Interface

#### New Memory API Endpoints (`/crypto/*`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/crypto/status` | Engine health, wallet balances, enabled features |
| POST | `/crypto/parse` | NL → structured TradeIntent (dry-run, no execution). Body: `{text}` |
| POST | `/crypto/execute` | Parse + execute trade. Body: `{text, dry_run?, chain?}` |
| GET | `/crypto/portfolio` | Multi-chain balances + PnL. Params: `?chain=base\|eth\|solana\|all` |
| GET | `/crypto/history` | Trade history. Params: `?limit=50&chain=base&status=completed` |
| POST | `/crypto/monitor` | Create price monitor (limit/SL/DCA). Body: `{monitor_type, token, chain, ...}` |
| GET | `/crypto/monitors` | List active price monitors |
| DELETE | `/crypto/monitors/{id}` | Cancel a price monitor |
| POST | `/crypto/signals` | Publish a signal. Body: `{token, chain, direction, confidence, rationale, tx_hash?}` |
| GET | `/crypto/signals` | List published signals with performance stats |
| PATCH | `/crypto/signals/{id}/close` | Close signal with outcome. Body: `{win, exit_price, pnl_pct}` |
| POST | `/crypto/launch` | Launch a token. Body: `{name, symbol, chain, supply, description}` |
| GET | `/crypto/price` | Current price for token(s). Params: `?tokens=ETH,BTC,SOL&chain=base` |

#### Existing endpoints extended (trading.py — Hyperliquid)
No changes needed. `/trading/*` remains as Hyperliquid read-only monitoring.

---

### New Database Schema (migration `059_crypto_native.sql`)

```sql
-- Executed trades (native, not Bankr-mediated)
CREATE TABLE crypto_trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain           TEXT NOT NULL,                    -- base | eth | polygon | solana | hyperliquid
    action          TEXT NOT NULL,                    -- swap | buy | sell | bridge | launch
    token_in        TEXT,
    token_out       TEXT,
    amount_in       NUMERIC,
    amount_out      NUMERIC,
    amount_usd      NUMERIC,
    tx_hash         TEXT,                             -- on-chain transaction hash
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | completed | failed | cancelled
    nl_input        TEXT,                             -- original NL command (if from NL parser)
    trade_intent    JSONB,                            -- parsed TradeIntent struct
    quote_data      JSONB,                            -- 0x quote response
    error           TEXT,
    source          TEXT NOT NULL DEFAULT 'manual',   -- manual | nl_parser | monitor | dca
    monitor_id      UUID,                             -- links to price_monitors if triggered by monitor
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX idx_crypto_trades_chain ON crypto_trades(chain);
CREATE INDEX idx_crypto_trades_status ON crypto_trades(status);
CREATE INDEX idx_crypto_trades_created ON crypto_trades(created_at DESC);

-- Conditional orders: limit, stop-loss, DCA
CREATE TABLE price_monitors (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_type    TEXT NOT NULL,                    -- limit_buy | limit_sell | stop_loss | dca | take_profit
    status          TEXT NOT NULL DEFAULT 'active',   -- active | triggered | cancelled | expired
    chain           TEXT NOT NULL,
    token_in        TEXT NOT NULL,
    token_out       TEXT,
    amount_usd      NUMERIC,                          -- USDC amount per trigger (or per DCA interval)
    trigger_price   NUMERIC,                          -- price in USD at which to trigger
    trigger_type    TEXT,                             -- above | below | percent_change
    trigger_pct     NUMERIC,                          -- for percent_change triggers
    -- DCA-specific
    dca_interval_hours INTEGER,                       -- hours between DCA buys
    dca_max_runs    INTEGER,                          -- max executions (NULL = infinite)
    dca_runs_done   INTEGER NOT NULL DEFAULT 0,
    next_run_at     TIMESTAMPTZ,                      -- when to next check/execute
    -- State
    last_price      NUMERIC,                          -- last seen price
    last_checked_at TIMESTAMPTZ,
    nl_description  TEXT,                             -- human-readable description
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    triggered_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ
);

CREATE INDEX idx_price_monitors_status ON price_monitors(status);
CREATE INDEX idx_price_monitors_next_run ON price_monitors(next_run_at) WHERE status = 'active';

-- Native signal board
CREATE TABLE crypto_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token           TEXT NOT NULL,
    chain           TEXT NOT NULL,
    direction       TEXT NOT NULL,                    -- long | short | neutral | exit
    confidence      NUMERIC,                          -- 0.0-1.0
    rationale       TEXT,
    entry_price     NUMERIC,
    target_price    NUMERIC,
    stop_price      NUMERIC,
    tx_hash         TEXT,                             -- on-chain proof (from executed trade)
    trade_id        UUID REFERENCES crypto_trades(id),
    status          TEXT NOT NULL DEFAULT 'open',     -- open | closed | cancelled
    win             BOOLEAN,                          -- NULL = open, TRUE = win, FALSE = loss
    exit_price      NUMERIC,
    pnl_pct         NUMERIC,
    metadata        JSONB,                            -- extra data (whale wallets, indicators)
    published_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);

CREATE INDEX idx_crypto_signals_status ON crypto_signals(status);
CREATE INDEX idx_crypto_signals_token ON crypto_signals(token);
CREATE INDEX idx_crypto_signals_published ON crypto_signals(published_at DESC);

-- Token launches
CREATE TABLE token_launches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    symbol          TEXT NOT NULL,
    chain           TEXT NOT NULL,                    -- base | solana
    contract_address TEXT,                            -- set after launch
    launch_mechanism TEXT NOT NULL,                   -- doppler | raydium_launchlab | manual
    total_supply    NUMERIC,
    creator_fee_pct NUMERIC,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | launched | failed
    tx_hash         TEXT,
    launch_data     JSONB,                            -- full launch response
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    launched_at     TIMESTAMPTZ
);
```

---

### New Module Structure

```
otto/memory/crypto/
├── __init__.py
├── nlparser.py        — NL → TradeIntent (Claude-powered)
├── executor.py        — Trade execution (0x quote + CDP AgentKit broadcast)
├── price_feed.py      — Price data (CoinGecko + Birdeye + Hyperliquid)
├── portfolio.py       — Multi-chain balance + PnL aggregation
├── monitors.py        — Conditional order polling + trigger logic
├── signals.py         — Native signal board CRUD + analytics
└── launch.py          — Token launch flows (Doppler/Raydium)

otto/memory/routes/crypto.py   — All /crypto/* API endpoints
otto/memory/migrations/059_crypto_native.sql
```

**Files to modify:**
- `otto/memory/api.py` — import + register `crypto` router
- `otto/memory/config.py` — add CRYPTO_* config vars
- `~/memory/.env` — add ALCHEMY_API_KEY, ZEROX_API_KEY (optional), CRYPTO_ENABLED
- `interfaces/web-next/src/app/crypto/page.tsx` — new OMS page
- `interfaces/web-next/src/components/` — trade terminal, signal board, monitor list components

---

### External APIs Required

| API | Purpose | Key Required | Cost |
|---|---|---|---|
| 0x Swap API (api.0x.org) | DEX aggregated quotes + calldata | Optional (rate limited without) | 1% fee on swaps (built into calldata) |
| CoinGecko API | Token prices, market data | None (free tier: 50 req/min) | Free |
| Birdeye API | Solana token prices + portfolio | Optional for enhanced data | Free tier available |
| Alchemy RPC | EVM balance queries (Base, ETH) | Yes (free tier) | Free tier |
| LI.FI (optional) | Cross-chain bridges | None | 0.3% bridge fee |

**Keys to add to `~/memory/.env`:**
```
# Native Crypto Engine
CRYPTO_ENABLED=false                    # Master feature flag
CRYPTO_EXECUTION_ENABLED=false          # Enables actual trade execution
ALCHEMY_API_KEY=                        # For EVM balance queries
ZEROX_API_KEY=                          # Optional — improves 0x rate limits
COINGECKO_API_KEY=                      # Optional — removes rate limits
BIRDEYE_API_KEY=                        # Optional — Solana data
```

---

### Implementation Plan

**Phase 1 — Foundation & Visibility** (~$6–8, 3 tasks)

**Task 1: DB + Config** (coder, $1.50, 600s)
- `migrations/059_crypto_native.sql` — 4 new tables
- `config.py` — add CRYPTO_ENABLED, ALCHEMY_API_KEY, ZEROX_API_KEY, COINGECKO_API_KEY, BIRDEYE_API_KEY
- `~/memory/.env` — stub entries with feature flags disabled
- Apply migration + verify tables

**Task 2: Price Feed + Portfolio Module** (coder, $3, 900s)
- `crypto/price_feed.py`:
  - `async get_price(token, chain) → PriceData` (CoinGecko)
  - `async get_prices(tokens: list) → dict[str, PriceData]`
  - Token symbol → CoinGecko ID mapping for top 100 tokens
- `crypto/portfolio.py`:
  - `async get_evm_balances(wallet_address, chain) → BalanceList` (Alchemy `eth_getBalance` + `alchemy_getTokenBalances`)
  - `async get_hyperliquid_summary() → HLSummary` (reuses existing trading.py logic)
  - `async get_portfolio_summary() → PortfolioSummary` (aggregates all chains)

**Task 3: NL Parser + Basic Routes** (coder, $3, 900s)
- `crypto/nlparser.py`:
  - `TradeIntent` dataclass: `{action, token_in, token_out, amount_usd, chain, conditions, raw_text}`
  - `async parse(text: str) → TradeIntent` — Claude API call with structured extraction prompt
  - Safety validation: reject ambiguous/malformed intents before any execution
- `routes/crypto.py`:
  - `GET /crypto/status` — feature flag state + wallet health
  - `POST /crypto/parse` — NL parse only (no execution, always safe to call)
  - `GET /crypto/portfolio` — portfolio aggregation
  - `GET /crypto/price` — price lookup
- `api.py` — register crypto router

**Phase 2 — Trade Execution** (~$8–10, 3 tasks)

**Task 4: 0x Integration + Executor** (coder, $4, 1200s)
- `crypto/executor.py`:
  - `async get_quote(trade_intent: TradeIntent) → SwapQuote` — 0x `/swap/v1/quote`
  - `async execute_swap(quote: SwapQuote, wallet: str) → TxResult` — CDP AgentKit broadcast
  - Transaction confirmation polling (up to 60s)
  - Writes `crypto_trades` record at each status change
- Routes: `POST /crypto/execute`, `GET /crypto/history`

**Task 5: Conditional Orders (Monitors)** (coder, $3, 900s)
- `crypto/monitors.py`:
  - `async check_monitors()` — main poll loop: fetch active monitors, get current prices, evaluate conditions
  - Trigger logic: calls `executor.py` when condition met
  - DCA schedule: `next_run_at` field determines when to fire next DCA buy
- A lightweight systemd timer (`otto-price-monitor.timer`) or scheduled task in Otto task queue runs `check_monitors()` every 60 seconds
- Routes: `POST /crypto/monitor`, `GET /crypto/monitors`, `DELETE /crypto/monitors/{id}`

**Task 6: DCA Scheduler** (coder, $2, 600s)
- Integrate DCA monitors with Otto task queue: when `dca_interval_hours` is set, create recurring tasks
- `monitors.py`: `async run_dca_tick(monitor_id)` — executes one DCA buy, updates `dca_runs_done` + `next_run_at`
- Routes: `POST /crypto/monitors/dca` — shorthand DCA creation endpoint

**Phase 3 — Signals, Launch & OMS UI** (~$7–10, 3 tasks)

**Task 7: Signal Board** (coder, $2.50, 600s)
- `crypto/signals.py`:
  - `async publish(token, chain, direction, confidence, rationale, trade_id?) → Signal`
  - `async close_signal(signal_id, win, exit_price, pnl_pct) → Signal`
  - `async get_stats() → SignalStats` — win rate, avg PnL, open count, closed count
  - Auto-publish: `executor.py` calls this when a trade completes above confidence threshold
- Routes: `POST /crypto/signals`, `GET /crypto/signals`, `PATCH /crypto/signals/{id}/close`

**Task 8: Token Launch** (coder, $3, 900s)
- `crypto/launch.py`:
  - `async launch_on_base(params) → LaunchResult` — Doppler contract interaction via CDP
  - `async launch_on_solana(params) → LaunchResult` — Raydium LaunchLab via existing Solana infra
  - Writes `token_launches` record
- Routes: `POST /crypto/launch`, `GET /crypto/launches`

**Task 9: OMS Crypto Terminal** (frontend-developer, $4, 900s)
- `interfaces/web-next/src/app/crypto/page.tsx`
- Sections:
  - **Status Bar**: engine health, wallet balances (Base, ETH, HL), feature flags
  - **NL Trade Terminal**: text input → parse preview → confirm → execute → result + tx link
  - **Portfolio Panel**: per-chain breakdown, total value, 24h change
  - **Price Monitors**: active conditions table (type, token, trigger, status)
  - **Signal Board**: published signals with direction, confidence, open/closed, PnL
- Add `/crypto` to OMS navigation

---

### Risks

- **0x API rate limiting without key**: Free tier allows ~3 req/s. Sufficient for Phase 1 testing. Add ZEROX_API_KEY for production.
- **CDP AgentKit EVM coverage**: CDP covers Base, ETH, Polygon. Solana requires separate tooling (solana-py or existing Solana key via @solana/web3.js subprocess). Mitigation: Phase 1 is EVM-only. Solana in Phase 2+.
- **NL parser ambiguity**: "Buy ETH" has no amount. Mitigation: nlparser.py returns a `confidence` score and `missing_fields` list. Routes reject low-confidence intents rather than guessing.
- **Price monitor reliability**: If the monitoring job is late or dies, monitors don't fire. Mitigation: `next_run_at` is idempotent — the job catches up on restart. Use `otto-price-monitor.timer` (systemd) for reliability.
- **Private key exposure**: Execution requires private keys for CDP + HL wallets. These are in `~/memory/.env` (chmod 600). Mitigation: `CRYPTO_EXECUTION_ENABLED=false` prevents any signing until Mev explicitly enables it. All execution paths check this flag.

---

### Budget Summary

| Phase | Tasks | Est. Cost |
|---|---|---|
| Phase 1: Foundation | 3 tasks | $7–8 |
| Phase 2: Execution | 3 tasks | $9–10 |
| Phase 3: Signals & UI | 3 tasks | $9–10 |
| **Total** | **9 tasks** | **~$25–28** |

Note: Higher than the Bankr integration approach (~$14–18) because we're building the execution layer from scratch instead of wrapping their API. The result is fully sovereign — no external dependency, no API key gating.

---

### What Replaces What

| Old Architecture (bankr-integration) | New Architecture (crypto-native) |
|---|---|
| `otto/memory/bankr/client.py` | `otto/memory/crypto/executor.py` |
| `otto/memory/bankr/signals.py` | `otto/memory/crypto/signals.py` |
| `otto/memory/bankr/llm_gateway.py` | N/A — We ARE the LLM |
| `otto/memory/routes/bankr.py` | `otto/memory/routes/crypto.py` |
| `bankr_trades` table | `crypto_trades` table |
| `bankr_signals` table | `crypto_signals` table |
| `bankr_jobs` table | `price_monitors` + `token_launches` tables |
| BANKR_API_KEY (Mev-blocked) | CDP_API_KEY (already configured) |
| api.bankr.bot NL API | nlparser.py (Claude-powered) |
| bankrsignals.com | Native signal board (/crypto/signals) |

The `bankr_*` tables remain in DB (empty) — no migration reversal needed. New `crypto_*` tables are the active system.

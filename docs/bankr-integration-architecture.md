# BANKR Bot Integration Architecture
*Designed: 2026-03-19 | Status: APPROVED FOR IMPLEMENTATION*

---

## Design: BANKR Bot — Full Otto & OMS Integration

### Problem

Mev directed a full integration of BANKR Bot features into Otto and the OMS. BANKR is an AI-powered natural-language crypto trading platform with 70K+ wallets, Agent API, cross-chain trading, DeFi integrations, social signals, token launching, and an LLM Gateway. Otto currently has Hyperliquid read-only monitoring but no trading execution or cross-chain wallet capabilities. This integration delivers autonomous NL trading, verified signal publishing (revenue path), token launch capability ($KOINK on Base/Solana), portfolio tracking across chains, and optional LLM cost reduction via BANKR's gateway.

---

### BANKR Feature Inventory

| Feature | Description | Otto Relevance |
|---|---|---|
| **Agent API** | `POST /agent/prompt` → jobId → poll result. NL to on-chain tx. | Core integration — all trading flows through here |
| **Trading: Spot Swap** | "Buy $200 of $BNKR", "Swap 0.1 ETH to USDC" | Immediate value — trade execution |
| **Trading: Limit Orders** | Trigger on % change, abs price, cross-asset. EVM chains only. | Strategy automation |
| **Trading: Stop-Loss** | "Stop loss for all holdings at -20%" | Risk management |
| **Trading: DCA** | "DCA $100 into ETH weekly" | Recurring strategy |
| **Trading: TWAP** | Time-spread large orders | Low-slippage execution |
| **Trading: Leverage** | Leveraged positions | Advanced trading |
| **Cross-chain Bridging** | Bridge in one message | Multi-chain ops |
| **Wallet Management** | Privy server wallets, auto-provisioned via X/Farcaster. Gas sponsored on Base. | Account foundation |
| **Portfolio Tracking** | Balances, PnL, transaction history via `/agent/balances` | Dashboard + memory |
| **BANKR Signals** | On-chain TX-verified signal publishing on bankrsignals.com | Revenue path — Otto publishes alpha signals |
| **Token Launch (Base)** | Doppler fair launch, bonding curve, 57% creator fees | $KOINK launch on Base |
| **Token Launch (Solana)** | Raydium LaunchLab, 0.5% creator fee, LP position post-graduation | $KOINK launch on Solana |
| **DeFi: Polymarket** | Prediction market betting via NL | Event-driven positions |
| **DeFi: Hydrex LP** | Lock tokens, single-sided liquidity, claim rewards | Yield generation |
| **DeFi: Veil Cash** | ZK shielded withdrawals, privacy pools | Privacy ops |
| **DeFi: ENS** | Domain management via NL | Ecosystem utility |
| **LLM Gateway** | OpenAI-compatible at `llm.bankr.bot`, pay in BNKR/ETH | Claude cost reduction candidate |
| **ERC-8004 Agent Identity** | On-chain agent NFT with trust score (Jan 2026) | Otto's on-chain identity |
| **SIWA** | Sign-In With Agent standard | Cross-agent auth |
| **CLI** | `bankr balances`, `bankr launch`, `bankr login` | Machine-readable ops |
| **Neynar Skill** | Farcaster posting/liking/following | MY3YE content on Farcaster |

---

### Approach

**Five-layer integration stack:**

```
┌─────────────────────────────────────────────────────────────┐
│  OMS Frontend (/bankr page)                                  │
│  Trade terminal | Portfolio | Signals | Launch | LLM stats   │
├─────────────────────────────────────────────────────────────┤
│  Memory API Routes (/bankr/*)                                │
│  status | trade | portfolio | history | signals | launch     │
├─────────────────────────────────────────────────────────────┤
│  BANKR Client Module (otto/memory/bankr/)                    │
│  client.py | llm_gateway.py | signals.py                    │
├─────────────────────────────────────────────────────────────┤
│  DB Layer (PostgreSQL)                                       │
│  bankr_trades | bankr_signals | bankr_jobs                  │
├─────────────────────────────────────────────────────────────┤
│  BANKR External APIs                                         │
│  api.bankr.bot | llm.bankr.bot | bankrsignals.com           │
└─────────────────────────────────────────────────────────────┘
```

**Async job pattern:** BANKR API is async — POST prompt returns jobId, then poll until completed/failed/cancelled. For web requests, we poll up to 30s (inline response). For longer operations (DCA setup, token launch), we create an Otto task queue entry and let it poll asynchronously.

**NL generation:** The OMS provides both structured form inputs (which generate safe NL prompts) and a raw NL terminal for advanced use. The backend always passes through BANKR's NL parser — no custom order routing needed.

**Thread continuity:** Each Otto "session" or strategy context passes a `threadId` to BANKR API to maintain conversational context (e.g., "the limit order I set earlier").

---

### Key Decisions

- **Sync vs async trade execution**: Inline polling up to 30s for immediate trades; task queue for slow operations. Because: OMS users expect instant feedback for simple swaps; DCA/launch are acceptable async flows.

- **NL generation layer**: Build a prompt-composer in client.py that converts structured inputs (token, amount, side) to safe, well-formed NL. Raw mode available but not default. Because: prevents malformed or ambiguous prompts that BANKR might misinterpret.

- **LLM Gateway routing**: Phase 3 only, after cost/latency benchmarking. Because: Otto's current Claude costs are well-understood; switching LLM paths mid-execution is a risk that needs validation first.

- **BANKR Signals**: Active integration (publish Otto's whale-convergence signals with TX hashes). Because: this is a verified revenue path with zero marginal cost once trades are being executed.

- **Token Launch**: Include Doppler (Base) as the primary mechanism for $KOINK on Base — superior to alternatives (fair launch, bonding curve, 57% creator fees, anti-sniper). Kept as Phase 3 because it needs Mev credential decisions.

- **Credential model**: `BANKR_API_KEY` in `~/memory/.env`. The API key is Mev-held and required before ANY execution phase can run. Architecture is fully designed; implementation proceeds to full completion once key arrives.

---

### API / Interface

#### New Memory API Endpoints (`/bankr/*`)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/bankr/status` | Account info, API key health, wallet balances summary |
| POST | `/bankr/trade` | Execute NL trade. Body: `{prompt, thread_id?}`. Returns job result or task_id |
| GET | `/bankr/portfolio` | Cross-chain balances (`/agent/balances`) |
| GET | `/bankr/history` | Local trade log with PnL. Params: `?limit=50&chain=base` |
| POST | `/bankr/limit-order` | Structured limit order → NL → BANKR. Body: `{token, amount, trigger_type, trigger_value, chain}` |
| POST | `/bankr/dca` | DCA strategy → NL → BANKR. Body: `{token, amount_usd, interval, chain}` |
| POST | `/bankr/stop-loss` | Stop-loss → NL → BANKR. Body: `{token?, pct_loss, chain}` |
| POST | `/bankr/signal/publish` | Publish signal to bankrsignals.com. Body: `{tx_hash, token, action, rationale, pnl?}` |
| GET | `/bankr/signals` | Otto's published signals + win rate + aggregate PnL |
| POST | `/bankr/launch` | Token launch via Doppler/Raydium. Body: `{name, symbol, chain, supply, description}` |
| GET | `/bankr/jobs/{job_id}` | Poll BANKR job status |
| GET | `/bankr/llm/stats` | LLM Gateway usage + cost if enabled |

#### New Config Keys (`~/memory/.env`)
```
BANKR_API_KEY=bk_...           # Required — all execution depends on this
BANKR_ENABLED=false            # Feature flag (set true after key loaded)
BANKR_BASE_URL=https://api.bankr.bot
BANKR_SIGNALS_ENABLED=false    # Enable signal publishing
BANKR_LLM_GATEWAY_ENABLED=false  # Route LLM calls through bankr (Phase 3)
```

#### New DB Tables (migration `058_bankr.sql`)
```sql
-- Local record of all BANKR-executed trades
CREATE TABLE bankr_trades (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id TEXT NOT NULL,           -- BANKR API jobId
  prompt TEXT NOT NULL,           -- NL prompt sent
  result TEXT,                    -- BANKR response
  tx_hash TEXT,                   -- on-chain tx hash if executed
  chain TEXT,                     -- base | eth | solana | polygon
  token TEXT,
  action TEXT,                    -- buy | sell | swap | bridge | dca | limit
  amount_usd DECIMAL(20,6),
  status TEXT NOT NULL,           -- pending | completed | failed | cancelled
  pnl_usd DECIMAL(20,6),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

-- Signals published to bankrsignals.com
CREATE TABLE bankr_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tx_hash TEXT NOT NULL UNIQUE,   -- on-chain proof (required by bankrsignals)
  token TEXT NOT NULL,
  action TEXT NOT NULL,           -- long | short | exit
  rationale TEXT,
  entry_price DECIMAL(20,6),
  exit_price DECIMAL(20,6),
  pnl_pct DECIMAL(10,4),
  win BOOLEAN,
  published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  closed_at TIMESTAMPTZ,
  signal_url TEXT                 -- bankrsignals.com/signal/{id}
);

-- Async BANKR jobs (for task-queue-backed long operations)
CREATE TABLE bankr_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  bankr_job_id TEXT NOT NULL,
  job_type TEXT NOT NULL,         -- trade | launch | dca | signal
  status TEXT NOT NULL DEFAULT 'pending',
  payload JSONB,
  result JSONB,
  otto_task_id UUID,              -- link to tasks table if spawned via task queue
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Implementation Plan

**Phase 1 — Backend Core** (~$6–8, 2 tasks)

1. **DB Migration + Config** (coder, $1.50)
   - `migrations/058_bankr.sql` — 3 new tables
   - `config.py` — add 5 BANKR settings
   - `~/memory/.env` — add stub keys with `BANKR_ENABLED=false`
   - Verify migration runs clean

2. **BANKR Client Module + Routes** (coder, $4)
   - `otto/memory/bankr/__init__.py`
   - `otto/memory/bankr/client.py` — BankrClient class:
     - `async prompt(text, thread_id=None) → JobResult` (POST + poll)
     - `async balances(chain=None) → BalancesResult`
     - `async get_job(job_id) → JobStatus`
     - NL prompt composers: `compose_swap()`, `compose_limit_order()`, `compose_dca()`, `compose_stop_loss()`, `compose_launch()`
   - `otto/memory/bankr/signals.py` — BankrSignals class:
     - `async publish_signal(tx_hash, token, action, rationale) → SignalResult`
     - `async get_my_signals() → list[Signal]`
   - `otto/memory/routes/bankr.py` — all 11 endpoints listed above
   - `otto/memory/api.py` — add `bankr` to imports + router registration
   - Feature-flag all execution paths: return 503 with setup instructions when `BANKR_ENABLED=false`

**Phase 2 — OMS Frontend** (~$3–4, 1 task)

3. **BANKR OMS Page** (frontend-developer, $3)
   - `interfaces/web-next/src/app/bankr/page.tsx`
   - Sections:
     - **Status Bar**: API health, wallet connected (X account), Base balance + Solana balance
     - **Portfolio Panel**: Per-chain balances, total value, 24h PnL (from `/bankr/portfolio`)
     - **Trade Terminal**: NL text input + Execute button. Shows result, tx hash link. History list below.
     - **Signals Board**: Published signals table — token, action, entry, current PnL, win/loss badge
     - **Quick Actions**: Pre-built buttons (Check balances, Set stop-loss, DCA setup wizard)
   - Add "BANKR" to OMS nav (alongside Trading)
   - Real-time polling every 30s for portfolio (same pattern as existing trading page)

**Phase 3 — Advanced Features** (~$5–6, 2 tasks)

4. **Signals Pipeline + DCA/Limit Automation** (coder, $3)
   - Wire heartbeat to check `bankrsignals.com` leaderboard rankings
   - Auto-publish signal when Otto's whale-convergence model generates a confirmed position (requires BANKR_SIGNALS_ENABLED=true)
   - DCA wizard in OMS with schedule preview
   - Limit order form with visual trigger configurator

5. **LLM Gateway + Token Launch** (coder, $3)
   - `otto/memory/bankr/llm_gateway.py` — OpenAI-compatible proxy client
     - Benchmarks: latency + cost per token vs direct Anthropic calls
     - Route flag: `BANKR_LLM_GATEWAY_ENABLED=true` in `.env`
   - Token launch endpoint wired through BANKR's Doppler integration
   - $KOINK launch wizard in OMS (name, symbol, supply, chain selector)
   - ERC-8004 agent identity registration helper

---

### Files Affected

**New files:**
```
otto/memory/bankr/__init__.py
otto/memory/bankr/client.py
otto/memory/bankr/signals.py
otto/memory/bankr/llm_gateway.py         (Phase 3)
otto/memory/routes/bankr.py
otto/memory/migrations/058_bankr.sql
interfaces/web-next/src/app/bankr/page.tsx
```

**Modified files:**
```
otto/memory/api.py                        — add bankr import + router
otto/memory/config.py                     — add 5 BANKR settings
~/memory/.env                             — add BANKR_API_KEY stub
interfaces/web-next/src/app/layout.tsx    — add BANKR nav link
```

---

### Risks

| Risk | Mitigation |
|---|---|
| **BANKR API key (Mev-held)** — All execution paths require `bk_...` key | Feature-flag everything behind `BANKR_ENABLED`. Implementation completes with `false` default. Mev activates with one `.env` change. |
| **BANKR X suspension history** — Service was suspended Oct 2025 (reinstated same day) | Use Agent API directly, not X platform dependency. API key auth is not X-dependent. |
| **Async job timeout** — BANKR jobs can take >30s during congestion | 30s inline timeout; overflow to task queue with polling. No blocking. |
| **NL ambiguity** — BANKR's NL parser may misinterpret poorly-formed prompts | Prompt-composer layer in client.py always generates safe, well-formed commands. Raw mode requires explicit flag. |
| **Privy wallet provisioning** — User wallet auto-creates on first X/Farcaster interaction, not on API key creation | Document clearly: BANKR API key auth is separate from wallet provisioning. First `/bankr/portfolio` call will create wallet if none exists. |
| **LLM Gateway cost** — May not be cheaper than direct Claude | Phase 3 includes benchmarking before routing real LLM calls. Never switches blindly. |
| **BANKR Signals onboarding** — Requires `curl -s bankrsignals.com/api/onboard | bash` | Review script content before running. Signals integration is opt-in behind `BANKR_SIGNALS_ENABLED` flag. |

---

### Total Estimated Cost

| Phase | Tasks | Budget |
|---|---|---|
| Phase 1: Backend Core | 2 tasks | ~$6–8 |
| Phase 2: OMS Frontend | 1 task | ~$3–4 |
| Phase 3: Advanced | 2 tasks | ~$5–6 |
| **Total** | **5 tasks** | **~$14–18** |

This is within the "broad scope, no artificial constraints" directive. The phases are independently deployable — Phase 1 alone delivers full backend capability, Phase 2 makes it visible in OMS, Phase 3 adds advanced automations.

---

### Credential Requirement

> **BANKR_API_KEY** (`bk_...`) required from Mev before Phase 1 execution begins.
>
> How to get: `npm i -g @bankr/cli && bankr login email <email>` then create an API key in the BANKR dashboard at bankr.bot.
>
> The key connects Otto's agent wallet on Base + Solana. Gas is sponsored on Base — zero cost for Base swaps.

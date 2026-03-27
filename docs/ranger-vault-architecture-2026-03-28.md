# Otto AI Vault Strategy — Ranger Build-A-Bear Hackathon

## Design: AI-Driven Regime-Adaptive USDC Vault (OttoVault)

### Problem

Ranger's Build-A-Bear Hackathon (deadline April 6, 2026) seeks production-ready vault strategies on Solana with ≥10% APY on USDC. Prize: up to $500K in TVL seeding. The competitive field runs delta-neutral strategies (hJLP, SOL basis, BTC basis) with static allocation — leaving a gap for AI-driven dynamic regime switching. Otto has 9 days to build, deploy, and submit.

### Approach

**OttoVault** is an AI-driven USDC vault built on Voltr infrastructure that dynamically switches between yield strategies based on detected market regime. Unlike static delta-neutral vaults (Gauntlet, Neutral Trade), OttoVault classifies market conditions in real-time and reallocates capital across strategies to maximize risk-adjusted yield.

**Core thesis**: No existing Solana vault changes *strategy type* based on market regime. They pick a strategy and hold it. OttoVault is the first to do regime-adaptive allocation — this is the novel edge.

---

### Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                    OttoVault System                       │
│                                                          │
│  ┌─────────────────┐    ┌──────────────────────────┐    │
│  │  Voltr Vault     │    │  Otto AI Keeper           │    │
│  │  (On-chain)      │◄───│  (Off-chain TypeScript)   │    │
│  │                  │    │                            │    │
│  │  USDC deposits   │    │  ┌─────────────────────┐  │    │
│  │  LP tokens out   │    │  │ Signal Collector     │  │    │
│  │                  │    │  │ (Pyth, Drift, Kamino)│  │    │
│  │  Strategies:     │    │  └─────────┬───────────┘  │    │
│  │  ├─ Drift Perps  │    │            ▼              │    │
│  │  ├─ Kamino Lend  │    │  ┌─────────────────────┐  │    │
│  │  ├─ Jupiter Lend │    │  │ Regime Classifier    │  │    │
│  │  └─ Save (Solend)│    │  │ (trending/ranging/   │  │    │
│  │                  │    │  │  stress)              │  │    │
│  └─────────────────┘    │  └─────────┬───────────┘  │    │
│                          │            ▼              │    │
│                          │  ┌─────────────────────┐  │    │
│                          │  │ Allocation Engine    │  │    │
│                          │  │ (strategy weights)   │  │    │
│                          │  └─────────┬───────────┘  │    │
│                          │            ▼              │    │
│                          │  ┌─────────────────────┐  │    │
│                          │  │ Rebalance Executor   │  │    │
│                          │  │ (Voltr SDK calls)    │  │    │
│                          │  └─────────────────────┘  │    │
│                          │                            │    │
│                          │  ┌─────────────────────┐  │    │
│                          │  │ Circuit Breakers     │  │    │
│                          │  │ (drawdown, staleness,│  │    │
│                          │  │  vol, min-delta)     │  │    │
│                          │  └─────────────────────┘  │    │
│                          └──────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

---

### Key Decisions

**1. Voltr SDK vs Custom Anchor Program**
- **Chosen**: Voltr SDK + existing adaptors (Drift, Kamino, Jupiter, Save)
- **Reason**: Voltr IS Ranger's underlying infrastructure. Using existing adaptors eliminates the need to write, audit, and deploy a custom Solana program. Reduces 3+ weeks of Rust/Anchor work to ~3 days of TypeScript integration. The hackathon explicitly permits this — the judging is on *strategy quality*, not infrastructure novelty.
- **Alternative rejected**: Custom Anchor vault program. Would require installing Solana toolchain (not present on otto-machine), writing ~2000 lines of Rust, deploying, and auditing — impossible in 9 days with zero Solana/Rust dev experience on this machine.

**2. AI Keeper Architecture: TypeScript service vs Python**
- **Chosen**: TypeScript (Node.js)
- **Reason**: `@voltr/vault-sdk` is TypeScript-only. `@solana/web3.js` is TypeScript-first. Drift SDK, Kamino SDK — all TypeScript. Fighting the ecosystem with Python adds unnecessary bridging complexity.
- **Alternative rejected**: Python with subprocess calls to TS scripts. Adds latency, debugging pain, and fragility.

**3. Strategy Differentiation: Regime Detection**
- **Chosen**: Market regime classifier (trending/ranging/stress) that dynamically shifts allocation weights
- **Reason**: This is structurally novel on Solana. Every competing vault uses static allocation with periodic manual rebalancing. An automated regime-aware system that rotates between strategy types (not just weights within one strategy) is a genuine first.
- **Alternative rejected**: Pure delta-neutral with better parameters. This competes directly with Gauntlet ($140M, institutional team) on their home turf — we lose.

**4. Existing Alpha Pipeline Reuse**
- **Chosen**: Build AI layer from scratch, reference alpha infra for signal patterns only
- **Reason**: Validator correctly identified that `paper_trader.py` (meme tokens, $50 positions, 2h holds) and `live_watcher.py` (smart money meme detection) are architecturally incompatible with delta-neutral yield management. Helius wallet scanning and Solana Tracker client provide useful on-chain data patterns but the strategy logic must be purpose-built.
- **Alternative rejected**: "Zero new infrastructure" — this was a synthesis overstatement.

**5. Hosting: otto-machine vs External**
- **Chosen**: Run keeper on otto-machine (GCP VM, 4 vCPU / 16GB)
- **Reason**: Always-on, adequate resources for a single keeper service, direct access to Otto's memory system for strategy state persistence. No additional infra cost.
- **Alternative considered**: Dedicated cloud instance. Unnecessary complexity for a single TypeScript process.

---

### Strategy Logic

#### Three Regimes

| Regime | Detection Signals | Primary Strategy | Target APY |
|--------|------------------|-----------------|------------|
| **TRENDING** | Funding rate slope > 0 for 12h+, vol-of-vol low, directional momentum | **SOL/BTC Basis Trade**: Long LST/spot + Short perps on Drift. Collect funding payments. Dynamic leverage 1.0-1.8x based on funding magnitude. | 15-40% |
| **RANGING** | Funding rate oscillating around 0, low volatility, mean-reverting price action | **Multi-Lending Optimization**: Rotate USDC across Kamino, Marginfi, Jupiter Lend, Save — wherever rate is highest. Plus small basis trades on highest-funding markets. | 10-18% |
| **STRESS** | Vol spike >2x 30d avg, funding rate flip (sign change), utilization >90% on lending | **Capital Preservation**: Withdraw from basis trades, park in highest-quality lending (Kamino/Save), tighten positions. Wait for regime change. | 6-10% |

#### Signal Inputs

```typescript
interface MarketSignals {
  // Drift Perpetuals (read from on-chain accounts)
  funding_rates: {
    SOL: { hourly: number; slope_12h: number; };
    BTC: { hourly: number; slope_12h: number; };
    ETH: { hourly: number; slope_12h: number; };
  };

  // Lending Rates (Kamino, Marginfi, Jupiter Lend, Save)
  lending_rates: {
    protocol: string;
    supply_apy: number;
    utilization: number;
    liquidity_depth: number;  // available to withdraw without slippage
  }[];

  // Price & Volatility (Pyth Oracle)
  prices: {
    SOL: number; BTC: number; ETH: number;
  };
  volatility: {
    sol_24h: number;  // realized vol
    vol_of_vol: number;  // volatility of volatility
    twap_deviation: number;  // current price vs 24h TWAP
  };

  // LST Premiums (on-chain)
  lst_premium: {
    mSOL_vs_SOL: number;  // > 1.0 = premium, < 1.0 = discount
    jitoSOL_vs_SOL: number;
  };
}
```

#### Regime Classifier

Simple, interpretable rule-based classifier (not ML — no training data, must be auditable for hackathon):

```typescript
function classifyRegime(signals: MarketSignals): 'TRENDING' | 'RANGING' | 'STRESS' {
  const { funding_rates, volatility, lending_rates } = signals;

  // STRESS: high vol + funding flip + high utilization
  const volSpike = volatility.sol_24h > volatility.vol_of_vol * 2;
  const fundingFlipped = Math.sign(funding_rates.SOL.hourly) !==
                         Math.sign(funding_rates.SOL.slope_12h);
  const highUtil = lending_rates.some(r => r.utilization > 0.9);

  if (volSpike && (fundingFlipped || highUtil)) return 'STRESS';

  // TRENDING: consistent funding direction + low vol-of-vol
  const strongFunding = Math.abs(funding_rates.SOL.slope_12h) > 0.0003;
  const lowVolVol = volatility.vol_of_vol < 0.5;  // normalized

  if (strongFunding && lowVolVol) return 'TRENDING';

  // Default: RANGING
  return 'RANGING';
}
```

#### Allocation Engine

Each regime maps to a target allocation across strategies:

```typescript
const REGIME_ALLOCATIONS = {
  TRENDING: {
    drift_basis_SOL: 0.40,   // Long SOL + short SOL perp
    drift_basis_BTC: 0.25,   // Long cbBTC + short BTC perp
    kamino_lend: 0.25,       // USDC lending (reserve)
    save_lend: 0.10,         // USDC lending (secondary)
  },
  RANGING: {
    kamino_lend: 0.40,       // Highest lending rate
    jupiter_lend: 0.25,      // Secondary lending
    save_lend: 0.15,         // Tertiary lending
    drift_basis_SOL: 0.20,   // Small basis position (if funding > 0)
  },
  STRESS: {
    kamino_lend: 0.50,       // Safest lending
    save_lend: 0.30,         // Secondary safe lending
    jupiter_lend: 0.20,      // Tertiary
    // Zero basis trades — capital preservation
  },
};
```

Rebalancing is **gradual**: on regime change, move 25% of capital per cycle toward target allocation (prevents front-running and slippage).

#### Rebalance Triggers

1. **Regime change** → gradual shift over 4 cycles (1 hour total at 15-min intervals)
2. **Rate differential** → if any lending protocol offers >200bps more than current position, rotate
3. **Funding rate threshold** → if Drift funding rate flips sign, close affected basis trade within 1 cycle
4. **Drawdown circuit breaker** → if portfolio NAV drops >5% from high water mark, force STRESS regime
5. **Minimum delta** → only rebalance if position change >2% of vault equity (prevents thrashing, saves fees)

---

### On-Chain Architecture (Voltr)

```
Voltr Vault (USDC base)
├── Strategy 1: Drift Adaptor
│   ├── USDC deposited → Drift user account
│   ├── Manager opens perp shorts (SOL, BTC, ETH)
│   ├── Funding payments collected automatically
│   └── Position value = deposit + unrealized PnL + funding
│
├── Strategy 2: Kamino Adaptor
│   ├── USDC deposited → Kamino lending pool
│   ├── Earns supply APY (currently 5-8%)
│   └── Position value = deposit * exchange_rate
│
├── Strategy 3: Jupiter Lend Adaptor
│   ├── USDC deposited → Jupiter Lend vault
│   ├── Earns supply APY
│   └── Position value = shares * price_per_share
│
└── Strategy 4: Save (Solend) Adaptor
    ├── USDC deposited → Save lending pool
    ├── Earns supply APY
    └── Position value = cTokens * exchange_rate
```

**Vault creation** (one-time, via SDK):
```typescript
import { VoltrClient } from '@voltr/vault-sdk';

const vault = await voltrClient.createInitializeVaultIx({
  vaultName: "OttoVault",
  assetMint: USDC_MINT,
  manager: managerKeypair.publicKey,
  lockedProfitDegradation: 86400,  // 24h linear unlock
  performanceFeeBps: 1000,  // 10% performance fee (above HWM)
  managementFeeBps: 100,    // 1% management fee
});
```

**Adaptor registration** (one-time per strategy):
```typescript
// Register Drift adaptor with vault
await voltrClient.createAddAdaptorIx({
  vault: vaultPDA,
  adaptorProgram: DRIFT_ADAPTOR_PROGRAM_ID,  // EBN93eXs5fHGBABuajQqdsKRkCgaqtJa8vEFD6vKXiP
});

// Initialize Drift strategy
await voltrClient.createInitializeStrategyIx({
  vault: vaultPDA,
  adaptorProgram: DRIFT_ADAPTOR_PROGRAM_ID,
  // Protocol-specific remaining accounts for Drift
});
```

---

### Data Flow

```
Every 15 minutes (keeper cycle):
┌─────────────────┐
│ 1. Collect       │ Pyth prices (SOL, BTC, ETH)
│    Signals       │ Drift funding rates (on-chain accounts)
│                  │ Lending rates (Kamino, Jupiter, Save APIs)
│                  │ LST premiums (Sanctum/Marinade on-chain)
│                  │ Vault current positions (Voltr SDK)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. Classify      │ Rule-based regime detection
│    Regime        │ Output: TRENDING | RANGING | STRESS
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. Calculate     │ Current allocation vs target allocation
│    Rebalance     │ Delta per strategy (deposit/withdraw amounts)
│                  │ Check: delta > 2% of vault equity?
│                  │ Check: circuit breakers clear?
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. Execute       │ createWithdrawStrategyIx() from over-allocated
│    Rebalance     │ createDepositStrategyIx() to under-allocated
│                  │ All via Voltr SDK (CPI to adaptors)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. Log &         │ Log to Otto memory API (episodic events)
│    Monitor       │ Update dashboard metrics
│                  │ Alert on anomalies (WhatsApp to Mev)
└─────────────────┘
```

---

### Project Structure

```
~/otto/projects/otto-vault/
├── package.json                 # @voltr/vault-sdk, @solana/web3.js, @drift-labs/sdk
├── tsconfig.json
├── .env                         # RPC_URL, MANAGER_KEYPAIR_PATH, PYTH_URL
├── src/
│   ├── index.ts                 # Entry point — keeper loop
│   ├── config.ts                # Environment + constants
│   ├── vault/
│   │   ├── client.ts            # VoltrClient wrapper
│   │   ├── setup.ts             # One-time vault + adaptor initialization
│   │   └── rebalance.ts         # Deposit/withdraw strategy execution
│   ├── signals/
│   │   ├── collector.ts         # Aggregates all signal sources
│   │   ├── drift.ts             # Drift funding rate reader
│   │   ├── lending.ts           # Kamino/Jupiter/Save rate reader
│   │   ├── pyth.ts              # Pyth oracle price reader
│   │   └── lst.ts               # LST premium reader
│   ├── strategy/
│   │   ├── regime.ts            # Regime classifier
│   │   ├── allocator.ts         # Target allocation per regime
│   │   └── circuit_breaker.ts   # Safety guards
│   ├── monitoring/
│   │   ├── logger.ts            # Otto memory API integration
│   │   ├── metrics.ts           # Performance tracking (NAV, Sharpe, drawdown)
│   │   └── alerter.ts           # WhatsApp alerts on anomalies
│   └── backtest/
│       ├── historical.ts        # Historical data loader
│       ├── simulator.ts         # Strategy backtester
│       └── report.ts            # Backtest report generator
├── scripts/
│   ├── setup-vault.ts           # Deploy vault to devnet/mainnet
│   ├── run-backtest.ts          # Run historical backtest
│   └── generate-report.ts       # Generate submission docs
└── docs/
    ├── strategy.md              # Strategy documentation (submission)
    └── risk-management.md       # Risk framework (submission)
```

---

### API / Interface

#### Keeper Service Endpoints (internal, for monitoring)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Current regime, positions, NAV, uptime |
| `/signals` | GET | Latest signal snapshot |
| `/history` | GET | Rebalance history (last N cycles) |
| `/metrics` | GET | Sharpe, max drawdown, APY since inception |
| `/force-rebalance` | POST | Manual rebalance trigger (emergency) |
| `/pause` | POST | Pause keeper (keep positions, stop rebalancing) |

Run as a simple Express server on port :8200. Otto can query it from other agents.

#### Integration with Otto Memory API

```typescript
// Log rebalance events to episodic memory
await fetch('http://localhost:8100/episodic/events', {
  method: 'POST',
  body: JSON.stringify({
    event_type: 'vault_rebalance',
    content: `Regime: ${regime}. Moved ${delta}% from ${from} to ${to}. NAV: $${nav}`,
    metadata: { regime, positions, nav, sharpe, signals }
  })
});

// Store strategy performance as semantic memory
await fetch('http://localhost:8100/semantic/remember', {
  method: 'POST',
  body: JSON.stringify({
    content: `OttoVault 24h performance: APY ${apy}%, Sharpe ${sharpe}, regime ${regime}`,
    category: 'vault_performance',
    confidence: 0.95
  })
});
```

---

### Circuit Breakers (Safety)

| Guard | Trigger | Action |
|-------|---------|--------|
| **Max Drawdown** | NAV drops >5% from high water mark | Force STRESS regime, withdraw all basis trades |
| **Oracle Staleness** | Pyth price >5 minutes old | Halt all rebalancing until fresh data |
| **Volatility Spike** | Vol-of-vol >3x 30d average | Force STRESS regime |
| **Funding Flip** | Funding rate sign changes on active basis trade | Close affected basis trade within 1 cycle |
| **Health Rate** | Drift account health <1.10 | Reduce leverage to 1.0x immediately |
| **Minimum Delta** | Rebalance would move <2% of vault equity | Skip (prevents fee burn on noise) |
| **Rate Limit** | >10 rebalance txs in 1 hour | Cool down for 15 minutes |

---

### Risk Management

**Position Sizing Rules:**
- Maximum 50% of vault in basis trades (even in TRENDING regime)
- Maximum 25% concentration in any single lending protocol
- Minimum 20% always in lending (liquidity reserve for withdrawals)
- Leverage never exceeds 1.8x (well above the 1.05 disqualification threshold)

**Drawdown Limits:**
- -3% → reduce basis trade exposure by 50%
- -5% → force STRESS regime (all basis trades closed)
- -8% → emergency: withdraw all, park in highest-quality lending, alert Mev

**Monitoring:**
- 15-minute keeper cycles
- Hourly NAV snapshots logged to Otto memory
- Daily performance summary via WhatsApp
- Real-time alerts on circuit breaker activation

---

### Implementation Plan (9 Days)

#### Phase 1: Foundation (Days 1-3, March 28-30)

| Day | Task | Deliverable | Est. Cost |
|-----|------|-------------|-----------|
| 1 | Project setup: Node.js project, dependencies, config | `package.json`, `tsconfig.json`, `.env` | $1 |
| 1 | Voltr SDK integration: vault client wrapper | `src/vault/client.ts` | $2 |
| 2 | Signal collectors: Pyth prices, Drift funding rates | `src/signals/pyth.ts`, `src/signals/drift.ts` | $2 |
| 2 | Signal collectors: lending rates (Kamino, Jupiter, Save) | `src/signals/lending.ts` | $2 |
| 3 | Devnet vault creation + adaptor registration | `scripts/setup-vault.ts`, running vault on devnet | $2 |
| 3 | Basic keeper loop: collect signals, log, no rebalancing yet | `src/index.ts` with 15-min loop | $1 |

**Phase 1 Gate**: Vault exists on devnet, signals flowing, keeper loop running.

#### Phase 2: Strategy (Days 4-6, March 31 - April 2)

| Day | Task | Deliverable | Est. Cost |
|-----|------|-------------|-----------|
| 4 | Regime classifier | `src/strategy/regime.ts` with tests | $2 |
| 4 | Allocation engine + circuit breakers | `src/strategy/allocator.ts`, `circuit_breaker.ts` | $2 |
| 5 | Rebalance executor: deposit/withdraw via Voltr SDK | `src/vault/rebalance.ts` | $3 |
| 5 | End-to-end devnet test: signal → classify → allocate → rebalance | Working keeper on devnet | $1 |
| 6 | Backtest engine: historical funding rates + lending rates | `src/backtest/simulator.ts` | $3 |
| 6 | Generate backtest report (target: show >10% APY historically) | `src/backtest/report.ts` | $1 |

**Phase 2 Gate**: Full strategy running on devnet, backtest showing ≥10% APY.

#### Phase 3: Production + Submission (Days 7-9, April 3-5)

| Day | Task | Deliverable | Est. Cost |
|-----|------|-------------|-----------|
| 7 | Monitoring: Otto memory integration, WhatsApp alerts | `src/monitoring/*` | $2 |
| 7 | Mainnet deployment: vault creation, fund with initial USDC | Live vault on mainnet | $1 |
| 8 | 24h mainnet soak: monitor, fix issues, collect live data | Running vault with real performance data | $0 |
| 8 | Strategy documentation: thesis, risk management, edge | `docs/strategy.md`, `docs/risk-management.md` | $2 |
| 9 | Demo video (3 min): architecture, live dashboard, results | MP4 file | $1 |
| 9 | GitHub repo prep + submission form | Private repo, @jakeyvee added | $0.5 |

**Phase 3 Gate**: Live mainnet vault, complete submission package.

#### Total Estimated Cost: ~$25.50

---

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **No Solana wallet with SOL** | HIGH | Blocks mainnet deploy | Ask Mev for funded wallet OR use devnet-only (weaker submission) |
| **Voltr SDK undocumented** | MEDIUM | Slows integration | Fall back to raw `@solana/web3.js` instruction building |
| **Drift adaptor complexity** | MEDIUM | Basis trades harder than lending | Start with lending-only, add Drift basis as stretch goal |
| **9 days too tight** | MEDIUM | Incomplete submission | Phase 1+2 are minimum viable. Phase 3 monitoring can be cut. Backtest is the real submission anchor. |
| **APY <10%** | LOW | Disqualified | Regime detection should hit 10% in trending markets. Lending floor provides 5-8% baseline. |
| **No Rust/Anchor experience** | N/A | N/A | Mitigated by Voltr SDK choice — no Rust required |

---

### Submission Checklist

- [ ] Demo video (≤3 min): OttoVault architecture, AI regime detection, live/backtest results
- [ ] Strategy documentation: thesis, implementation details, risk framework
- [ ] GitHub repo (private): add @jakeyvee as collaborator
- [ ] On-chain vault address (mainnet preferred, devnet acceptable)
- [ ] Backtest results: historical APY, Sharpe ratio, max drawdown, regime distribution

---

### What Makes OttoVault Novel

1. **Regime-Adaptive**: First Solana vault that changes strategy type based on detected market conditions (not just parameters within one strategy)
2. **AI-Driven Decision Loop**: Automated signal collection → classification → allocation → execution (15-min cycles)
3. **Persistent Memory**: Strategy performance logged to Otto's memory system — the vault *learns* which regime classifications led to good outcomes over time
4. **Transparent Risk**: Rule-based classifier is fully auditable (no black-box ML). Circuit breakers are explicit and documented.
5. **Cross-Protocol Optimization**: Dynamically rotates across 4 lending protocols based on real-time rates — not locked to one venue

---

### Dependencies & Blockers

| Dependency | Status | Blocker? |
|-----------|--------|----------|
| Voltr SDK (`@voltr/vault-sdk`) | Available on npm | No |
| Drift SDK (`@drift-labs/sdk`) | Available on npm | No |
| Solana RPC (Helius) | Free Dev plan via hackathon | No |
| Funded Solana wallet (mainnet SOL + USDC) | **Unknown — need from Mev** | **YES for mainnet deploy** |
| `@jakeyvee` GitHub collaborator access | Need private repo first | No (Phase 3) |
| Pyth Oracle access | Public, no auth needed | No |
| otto-machine Node.js 22 | Installed | No |

[NEEDS_MEV_INPUT]
{"question": "Do we have a funded Solana wallet (SOL for tx fees + USDC for initial vault deposit)? Mainnet deployment requires this. Devnet-only is possible but weaker submission.", "options": ["Yes — use existing wallet (provide path to keypair)", "No — submit devnet-only with strong backtest", "Fund a new wallet specifically for this"], "recommendation": 2, "context": "Mainnet deployment is a hackathon bonus criterion. Judges favor live vaults. ~$10-50 USDC for initial deposit + ~0.5 SOL for deployment fees would be sufficient to demonstrate."}
[/NEEDS_MEV_INPUT]

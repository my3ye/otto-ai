# Alpha Strategy Backtest Analysis
**Generated:** 2026-02-21
**Analyst:** Otto (automated task)

---

## 1. Signal Volume Assessment

| Metric | Value |
|--------|-------|
| Total lines in signals.jsonl | 211 |
| Unique HIGH (convergence) signals | **2** |
| MEDIUM signals (raw) | 145 |
| Unique MEDIUM signals (est.) | ~50–60 (heavy duplication) |
| Scanning period | 2026-02-19 to 2026-02-21 (~2 days) |
| Wallets actively producing signals | 5–7 of 10 per cycle |

**Verdict: Sample size is critically insufficient.** 2 convergence signals is not enough to draw any statistical conclusions. A minimum of 20+ independent signals is needed for even rough validation.

---

## 2. Strategy Comparison

### 2a. Convergence Copy Trading (HIGH signals, 2+ wallets)

| Horizon | Trades | Win Rate | Avg Return | Sharpe |
|---------|--------|----------|------------|--------|
| T+1h    | 2      | 0%       | -1.05%     | -258.4 |
| T+4h    | 2      | 100%     | +14.19%    | 0.84   |
| T+24h   | 0      | N/A      | N/A        | N/A    |

**Observations:**
- At 1h, both signals were slightly negative (slippage-driven — entry + slippage eats ~1%)
- At 4h, both signals were positive: HXD +26.1%, WhiteWhale +2.2%
- The 4h result is interesting but statistically meaningless with N=2
- Both signals were from the same timestamp (14:03:09Z on Feb 20), so they represent a single scanning cycle, not two independent events
- The convergence logic is sound: wallets SM_2 and SM_3 (or MULTI) both buying the same token is a genuine signal of coordinated smart money

**Assessment:** Strategy concept is valid. Results are directionally promising but need 5–10x more signals before trusting them.

### 2b. Single Wallet Copy (SM_8 — meme hunter)

| Horizon | Trades | Win Rate | Avg Return | Sharpe |
|---------|--------|----------|------------|--------|
| T+1h    | 0      | N/A      | N/A        | N/A    |
| T+4h    | 0      | N/A      | N/A        | N/A    |

**Observations:**
- SM_8's only MEDIUM signal has a truncated token address (F7vaGJnPi4EraC45 — 16 chars, not 44) → price fetch fails
- This is a **logging bug**: the scanner is saving shortened token addresses instead of full base58 addresses for some signals

Previous run on SM_1 (not re-run, from stored results):
- 36 signal records → 13 with price data → actually ~3 unique events (massive deduplication issue)
- All 13 records lost money at 1h: 0% win rate, -0.61% avg
- SM_1 trades: JUP, SKR, SONIC — established mid-caps, not high-alpha meme plays
- SM_1 appears to be an arbitrage/MEV wallet, not a directional alpha source

**Assessment:** SM_1 signals are low quality for copy trading (arb/MEV strategy ≠ directional bets). SM_8 data is incomplete. Need to fix logging bugs and collect more data.

---

## 3. Critical Bugs Found

### Bug 1: Signal Deduplication Failure
The scanner logs the same signal multiple times per cycle. Example: the `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` token appears in 20+ consecutive lines from a single scan (SM_2 × 16, SM_3 × 4). The signal_parser does deduplicate for HIGH signals (2h window), but MEDIUM signals have no deduplication. This inflates perceived signal volume.

**Fix needed:** Deduplicate signals at the logger level before writing to `signals.jsonl`. Add a `(wallet, token, timestamp_bucket)` dedup key.

### Bug 2: Truncated Token Addresses
Some signals log shortened token addresses (e.g., `F7vaGJnPi4EraC45` — 16 chars instead of 44). The Jupiter/Birdeye price fetch requires full base58 addresses. These signals can never be backtested.

**Fix needed:** Validate token address length (must be 32–44 chars) before logging signal.

### Bug 3: Wallet Label Inconsistency
Three different naming schemas in use:
- `Sol_Bigbrain_1` / `Sol_Bigbrain_3` (old 2-wallet setup)
- `SmartMoney_1` through `SmartMoney_4` (mid-period)
- `SM_1` through `SM_10` (current)

The signal_parser handles this but it adds complexity and risk of missed signals.

### Bug 4: No Deduplication for Same-Signal Wallets
The HIGH signal for `Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB` had wallet field as `SM_2,SM_2,SM_2,...,SM_3,SM_3,...` — 20 wallet entries, but only 2 unique wallets. The scanner is counting duplicate transaction records, not unique wallets.

---

## 4. Recommended Next Steps (Ranked)

### Immediate (this week):
1. **Fix signal logging bugs** — truncated token addresses, deduplication failure
2. **Collect more convergence signals** — expand to 1h window (currently 30min), add wallets from known alpha sources
3. **Fix backtest for SM_8** — the default single wallet target has incomplete data; switch default to SM_3 (arb/meme hunter) or SM_4

### Before any capital deployment:
4. **Reach 20+ unique convergence signals** — current 2 signals is nowhere near sufficient
5. **Add 24h price data** — current data is too fresh; need to backtest historical closes
6. **Paper trading dry run** — run the signal detection logic with a simulated $100 USDC portfolio for 2 weeks minimum
7. **Implement stop-loss** — no exit logic exists beyond time horizon. At minimum, define a 15% stop-loss from entry

### To go live ($1k–5k capital, 1 week target):
8. **Convergence strategy** is the better bet — but needs N≥20 before confidence
9. **Position sizing** — start at $50–100 USDC per convergence signal, max 3 concurrent positions
10. **Execution bot** — the bot/ directory exists but is unfinished; needs buy/sell execution logic tied to Jupiter aggregator

---

## 5. Risk Assessment

| Risk | Severity | Notes |
|------|----------|-------|
| Insufficient sample size | **CRITICAL** | 2 signals cannot validate a strategy |
| Token address logging bug | HIGH | Makes SM_8 unbacstable |
| Signal deduplication inflation | HIGH | Inflates apparent signal volume 10x |
| No stop-loss logic | HIGH | Unlimited downside on bad trades |
| MEV/slippage on entry | MEDIUM | ~1% per round-trip, eat into small gains |
| Smart money wallet churn | MEDIUM | Wallets may change strategies or go inactive |
| Meme token liquidity | MEDIUM | Low-liq tokens: exit slippage can be brutal |

---

## 6. Go-Live Assessment

**Can we go live within 1 week?**

**Honestly: No — not responsibly.**

The current data supports the *concept* of convergence copy trading but not a live deployment:
- 2 signals with positive 4h returns is a promising start, not a validated strategy
- Bugs in the logging pipeline would corrupt live signals
- No execution bot, no stop-loss, no position management

**Realistic timeline:**
- **Week 1** (now): Fix signal bugs + expand scanning → target 15–20 convergence signals
- **Week 2**: Paper trading dry-run, validate signal → price execution loop
- **Week 3**: Live trading with tiny capital ($200–$500 USDC), monitor and adjust

If the bug fixes are prioritized today and scanning continues at current pace (~1 convergence signal/day), we could have 10–15 signals by end of Week 1, which is borderline for a micro-position live test.

**One path to earlier go-live:** Relax convergence criteria to 1-hour window (currently 30min). This may double signal frequency at the cost of some signal quality.

---

*Analysis generated by Otto. Data period: 2026-02-19 to 2026-02-21.*

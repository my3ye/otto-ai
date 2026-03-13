# Signal Backtest Report — 2026-03-08

**Generated:** 2026-03-08  
**Data period:** 2026-02-21 → 2026-03-07  
**Total signals in file:** 2,315  
**Methodology:** GeckoTerminal OHLCV for entry+exit prices; DexScreener for token discovery  
**Slippage:** 0.3% per side (not applied below — raw price returns)

---

## 1. HIGH Convergence Signals (Multi-Wallet)

**Universe:** 95 convergence signals after dedup (all from Feb 21-22)  
**Tested:** 30 (rate limiting constraint), 27 with price data, 3 no pair found

| Horizon | Trades | Win Rate | Avg Return | Best | Worst |
|---------|--------|----------|------------|------|-------|
| T+1h    | 27     | **30%**  | -1.5%      | +0.6% | -11.8% |
| T+4h    | 27     | **33%**  | -1.8%      | +2.4% | -18.6% |
| T+24h   | 27     | **30%**  | **+1.0%**  | +28.4% | -30.4% |

### Notable Trades (T+24h)
- **arc** → +28.4% at 24h
- **pippin** → +27.1%, +24.2%, +19.1% (appeared 3 times)
- **neet** → +15.8%
- **WAR** → +10.9%
- **LABUBU** → -30.4% (worst)
- **USELESS** → -13.1%

### Key Finding
Convergence signals are **late-pumpers, not early entries**:
- No edge at T+1h (30% WR, -1.5%)
- No edge at T+4h (33% WR, -1.8%)
- **Marginal edge at T+24h** (30% WR, but avg +1.0% from 6 big winners >5%)
- Previous Feb 22 backtest showed 40%/+4.32% at T+24h — but n=5, too small to trust
- **Updated view: 30% WR at T+24h with positive avg ONLY because of outliers (arc, pippin)**

---

## 2. Grade-A Single-Wallet Quality Signals

**Universe:** 674 grade-A signals, 37 unique tokens checked  
**Note:** These are measured at current price (~13 days after signal), NOT T+24h  
**This is a long-term holding snapshot, not a 24h backtest**

| Metric | Value |
|--------|-------|
| Signals tested | 35 |
| Win rate (current price) | **23%** (8/35) |
| Avg return (13 days) | **-8.6%** |
| Best (PAW) | +65.1% |
| Worst (GROKEN) | -99.3% |

### By Wallet (13-day return)

| Wallet | Signals | Win Rate | Avg Return | Range |
|--------|---------|----------|------------|-------|
| SM_20  | 9       | **44%**  | -6.5%      | -99.3% to +65.1% |
| SM_10  | 16      | 12%      | -4.8%      | -25.8% to +47.9% |
| SM_5   | 8       | 12%      | -11.7%     | -57.1% to +1.3% |
| SM_18  | 1       | 100%     | +0.2%      | flat |
| SM_13  | 1       | 0%       | -72.0%     | rug |

### Key Finding
Grade-A signals have **high variance, mostly negative** 13-day performance. This is expected for:
1. Meme koins in a bear market (Feb-Mar 2026 risk-off period)  
2. 13-day hold is far outside the T+24h window  
3. Several rugs/dead tokens (GROKEN -99%, KIMCHI -72%, LIZARD -54%)

---

## 3. Published @OttoSignals Performance

**6 signals published total:**

| Token | Published | Current Return (est.) |
|-------|-----------|----------------------|
| PUMP | ~Feb 22 | -6.7% (13 days) |
| RENDER | ~Feb 22 | -5.6% (13 days) |
| PYTH | ~Feb 22 | -12.2% (13 days) |
| MEW | ~Mar 7 | -4.4% (1 day) |
| CHILLGUY | ~Mar 7 | -9.4% (1 day) |
| BOME | ~Mar 7 | -4.1% (1 day) |

---

## 4. Strategic Assessment

### What's Working
- **T+24h has positive average return** (+1.0%) driven by outlier big wins (arc +28%, pippin +24%)
- Pippin appeared 3× as a convergence signal — consistent smart money behavior
- Grade-A signals with quality_score >= 0.6 deserve further testing

### What's Not Working
- **T+1h and T+4h are negative** (avg -1.5% and -1.8%) — signals are late entries
- 30% win rate is below statistical significance for edge detection
- Many grade-A signals are meme koins with rug risk (GROKEN, LIZARD, KIMCHI)

### Recommendations
1. **Extend hold horizon to 24h minimum** with -15% stop loss (SL cuts LABUBU-type losses)
2. **Filter out micro-cap rugs**: add liquidity filter (>$50k USD) to grade-A signals
3. **Wallet ranking by T+24h performance**: SM_20 has high variance but +44% win rate — study its wins
4. **Convergence 3+ wallets**: subset analysis needed — 3+ wallet signals likely outperform 2-wallet
5. **Previous 40% WR at T+24h**: still possible with better filters, but n=5 was too small to confirm

---

## 5. Data Quality Notes

- 35/95 HIGH signals tested (rate-limiting constraint)
- GeckoTerminal 429 rate limits: 6 pauses of 15s during collection
- 3 tokens had no DexScreener pair (likely dead pools)
- Grade-A signals: 13-day hold ≠ T+24h — need dedicated T+24h backtest for this tier
- Previous Feb 22 result (40%/+4.32% at T+24h, n=5) not contradicted but not confirmed


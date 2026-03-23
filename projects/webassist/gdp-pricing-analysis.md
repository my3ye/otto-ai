# WebAssist GDP-Indexed Pricing Analysis
**Date:** 2026-03-23
**Baseline:** Sri Lanka — LKR 49,000 for Full Website

---

## Exchange Rates (2026-03-23)
| Pair | Rate |
|------|------|
| 1 LKR → USD | 0.00322 |
| 1 USD → LKR | 310.6 |
| 1 USD → AED | 3.67 |
| 1 USD → AUD | 1.42 |

---

## Step 1: Baseline in USD
```
49,000 LKR × 0.00322 USD/LKR = $157.78 USD
```

---

## Step 2: GDP Per Capita Data (IMF, 2024–2026)
| Country | GDP/Capita (USD) | Source |
|---------|-----------------|--------|
| Sri Lanka | $4,325 | World Bank 2024 |
| United States | $92,786 | IMF 2026 projection |
| UAE | $53,889 | IMF 2026 projection |
| Australia | $70,112 | IMF 2026 projection |
| World Average | ~$13,100 | IMF 2024 |

---

## Step 3: GDP Ratios vs Sri Lanka
| Region | GDP/Capita | Ratio vs SL |
|--------|-----------|------------|
| Sri Lanka | $4,325 | 1.00x |
| USA | $92,786 | **21.46x** |
| UAE | $53,889 | **12.46x** |
| Australia | $70,112 | **16.21x** |
| World | $13,100 | **3.03x** |

---

## Step 4: Raw Calculated Prices
| Region | Calculation | Raw Price (USD) |
|--------|------------|----------------|
| USA | $157.78 × 21.46 | **$3,386** |
| UAE | $157.78 × 12.46 | **$1,966** |
| Australia | $157.78 × 16.21 | **$2,558** |
| World | $157.78 × 3.03 | **$478** |

---

## Step 5: Local Currency Conversion
| Region | USD Price | Rate | Local Currency |
|--------|----------|------|----------------|
| UAE | $1,966 | ×3.67 | **AED 7,215** |
| Australia | $2,558 | ×1.42 | **AUD 3,632** |

---

## Final Pricing Table

| Country | Currency | GDP/Capita | Ratio vs SL | Raw Calculated | **Recommended Price** |
|---------|----------|-----------|-------------|---------------|-----------------------|
| Sri Lanka | LKR | $4,325 | 1.00x | LKR 49,000 | **LKR 49,000** |
| USA | USD | $92,786 | 21.46x | $3,386 | **$3,499** |
| UAE | AED | $53,889 | 12.46x | AED 7,215 | **AED 7,000** |
| Australia | AUD | $70,112 | 16.21x | AUD 3,632 | **AUD 3,499** |
| Global (default) | USD | $13,100 (world avg) | 3.03x | $478 | **$499** |

---

## Rounding Logic
- **USA $3,499**: Classic charm pricing ($3,386 → nearest $x99)
- **UAE AED 7,000**: Clean round number, slightly below raw (competitive for market)
- **Australia AUD 3,499**: Charm pricing ($3,632 → $3,499, competitive entry)
- **Global $499**: Validates existing default — raw calc was $478, $499 is the right anchor

---

## Key Finding
> **UAE was severely underpriced at AED 999** (raw GDP-indexed value: AED 7,215 — 7.2× too low).
> This represents a major revenue uplift opportunity: upgrading UAE price to AED 7,000 increases revenue per UAE client by ~7×.

---

## Files Updated
- `hooks/use-geo-price.ts` — Added US ($3,499), AU (AUD 3,499), corrected AE (AED 7,000)
- `components/sections/pricing-section.tsx` — Added US/AU geo badge labels
- `lib/athena-system-prompt.ts` — Updated pricing knowledge
- `lib/athena/unified-system-prompt.ts` — Updated pricing knowledge

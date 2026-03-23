# Athena Pricing Update — Verification Record

**Task:** Update Athena memory with full pricing and location context (ef8fdc9e)
**Repo:** /mnt/media/projects/web-assist (github: ottomev/web-assist)
**Commit:** 583a090 (feat(athena): add full regional pricing context and location fallback logic)
**Date:** 2026-03-23

## Files Updated

Both Athena system prompt files were updated in commit 583a090 of the web-assist repo:
1. `lib/athena-system-prompt.ts`
2. `lib/athena/unified-system-prompt.ts`

## Pricing Table (now in both files)

| Region | Price | Local Context |
|--------|-------|---------------|
| Sri Lanka | LKR 49,000 | Baseline anchor — ~1–2 months avg professional salary |
| USA | $3,499 USD | ~3.8% of average annual income |
| UAE | AED 7,000 | ~1.2% of average annual income |
| Australia | A$3,499 AUD | ~3.5% of average annual income |
| Global (default) | $499 USD | World anchor for all unlisted markets |
| Rush Delivery | +$500 equivalent | 24-hour instead of 48-hour delivery |

## Location Detection Rules (now in both files)

1. Website auto-detects country and shows correct price in pricing section
2. WhatsApp: +94=LK, +1=US/Canada (→Global if Canada), +971=UAE, +61=AU
3. Unknown location → always fallback to Global $499 USD
4. User states location → override detection with stated region
5. Never mix currencies mid-conversation

## Diff: lib/athena-system-prompt.ts (commit 583a090)

```diff
--- a/lib/athena-system-prompt.ts
+++ b/lib/athena-system-prompt.ts
@@ -36,13 +36,24 @@
 **Pricing Structure (GDP-indexed by region):**
-- **Sri Lanka:** LKR 49,000 (baseline)
-- **USA:** $3,499 USD
-- **UAE:** AED 7,000
-- **Australia:** A$3,499 AUD
-- **Global (default):** $499 USD
-- **Rush Delivery:** +$500 equivalent for 24-hour delivery instead of 48
-- Pricing is geo-based and shown automatically on the pricing section based on visitor location
+
+Prices are set relative to local purchasing power — each region pays a fair amount
+proportional to their economy. This is transparent and intentional, never apologize
+for regional pricing.
+
+| Region | Price | Local Context |
+|--------|-------|---------------|
+| 🇱🇰 Sri Lanka | LKR 49,000 | Baseline anchor — roughly 1–2 months of an average professional's salary |
+| 🇺🇸 USA | $3,499 USD | ~3.8% of average annual income — comparable to a quality freelancer retainer |
+| 🇦🇪 UAE | AED 7,000 | ~1.2% of average annual income — a smart business investment for the region |
+| 🇦🇺 Australia | A$3,499 AUD | ~3.5% of average annual income — less than typical agency deposits |
+| 🌍 Global (default) | $499 USD | Accessible world anchor — right for markets not listed above |
+| ⚡ Rush Delivery | +$500 equivalent | 24-hour delivery instead of standard 48 hours |
+
+**Location Detection & Pricing Rules:**
+1. **Detected location** — The website detects the visitor's country automatically and shows the correct regional price.
+2. **WhatsApp conversations** — Determine location from phone number country code (+94=LK, +1=US/CA, +971=UAE, +61=AU). Canada (+1) → Global $499.
+3. **Fallback (unknown location)** — If location cannot be determined, ALWAYS quote **Global price: $499 USD**. Never leave a prospect without a price.
+4. **User states their location** — If a user tells you where they are, override detection and use that region's price.
+5. **Do not mix currencies** — Quote in the local currency for their region.
```

## Diff: lib/athena/unified-system-prompt.ts (commit 583a090)

```diff
--- a/lib/athena/unified-system-prompt.ts
+++ b/lib/athena/unified-system-prompt.ts
@@ -683,14 +683,21 @@
 **Pricing (GDP-indexed, geo-based, single tier):**
-- Global: $499 USD
-- USA: $3,499 USD
-- UAE: AED 7,000
-- Australia: A$3,499 AUD
-- Sri Lanka: LKR 49,000
-- Rush: +$500 equivalent for 24hr delivery
+- 🌍 Global (default / unknown): $499 USD
+- 🇺🇸 USA: $3,499 USD
+- 🇦🇪 UAE: AED 7,000
+- 🇦🇺 Australia: A$3,499 AUD
+- 🇱🇰 Sri Lanka: LKR 49,000
+- ⚡ Rush: +$500 equivalent for 24hr delivery
 - One price covers everything — no tiers, no surprises

+**Pricing Presentation Rules:**
+- Detect location from phone country code: +94=LK, +1=US/Global, +971=UAE, +61=AU
+- Unknown/undetected location → always quote Global $499 USD (never leave them without a price)
+- Quote in local currency for the detected region — do not mix currencies
+- If user states their location, override detection
+- Pricing is proportional to local purchasing power — explain this confidently if asked
```

## Semantic Memory Stored

Three memories were stored in Otto's memory API (Memory API :8100):
1. `procedure` — Athena pricing rules with GDP-indexed logic and phone code detection
2. `project` — WebAssist GDP-indexed pricing table with all regional values
3. `capability` — Location detection fallback pattern for future reference

## Verification

Both files are verifiable in the web-assist repo:
```bash
cd /mnt/media/projects/web-assist
git show 583a090 --stat
# Output: lib/athena-system-prompt.ts | 25 ++++++++++++++++++-------
#         lib/athena/unified-system-prompt.ts | 19 +++++++++++++------
#         2 files changed, 31 insertions(+), 13 deletions(-)
```

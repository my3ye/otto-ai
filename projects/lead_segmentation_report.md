# Lead Segmentation Report
**Generated:** 2026-02-20
**Task:** Lead segmentation analysis (retry)
**Database:** memory (PostgreSQL) — `web_assist_leads` table

---

## 1. Lead Type Breakdown

| Lead Type | Count |
|-----------|-------|
| strong_web_presence | 2,160 |
| **no_website** | **1,531** |
| revamp_candidate | 273 |
| **Total** | **3,964** |

**Key insight:** 1,531 no-website leads are our primary target pool. 273 revamp candidates are secondary. 2,160 strong-web leads are currently dead weight in the DB unless we pivot to SEO/maintenance upsell later.

---

## 2. No-Website Leads by City (Top 20)

| City | Count |
|------|-------|
| Colombo | 396 |
| Kandy | 135 |
| Negombo | 114 |
| Galle | 100 |
| (no city) | 47 |
| Tangalle | 46 |
| Polonnaruwa | 46 |
| Nugegoda | 40 |
| Matara | 38 |
| Ella | 38 |
| Sigiriya | 37 |
| Jaffna | 35 |
| Mirissa | 32 |
| Nuwara | 30 |
| Dambulla | 27 |
| Dehiwala-Mount | 27 |
| Kurunegala | 27 |
| Hikkaduwa | 24 |
| Anuradhapura | 20 |
| Hatton | 20 |

**Colombo dominates at 26% of no-website leads.** Kandy + Negombo + Galle together add another 23%. Strong tourist corridor representation (Ella, Sigiriya, Mirissa, Hikkaduwa) — hospitality sector strong.

---

## 3. Top 20 Highest-Scoring No-Website Leads (with Phone)

All 100% of no-website leads have phones (1,531/1,531). Top 20 by lead score:

| Business Name | City | Score | Rating | Reviews |
|---------------|------|-------|--------|---------|
| Fab Ceylon | Kandy | 85 | 4.4 | 4,419 |
| Isle of Gelato | Galle | 85 | 4.7 | 1,396 |
| The Grand Gastrobar | Negombo | 85 | 4.6 | 1,290 |
| Silk Route | Malabe | 85 | 4.2 | 1,272 |
| Garton's Ark Restaurant | Nugegoda | 85 | 4.3 | 984 |
| The Pasta Factory | Galle | 85 | 4.6 | 934 |
| Ibrahim Eating House (Beruwala Kade) | Colombo | 85 | 4.1 | 667 |
| Nallur Bhavan Vegetarian Restaurant | Jaffna | 85 | 4.1 | 649 |
| Cosy Hotel & Restaurant | Jaffna | 85 | 3.6 | 700 |
| Home Cooking Fast Foods | Nugegoda | 85 | 4.4 | 744 |
| Coffee & Company | Colombo | 85 | 4.4 | 680 |
| Spice & Curry (by ANILAD) - Nugegoda | Nugegoda | 85 | 4.1 | 641 |
| Cafe Kinross | Colombo | 85 | 4.6 | 582 |
| Spinneys Restaurant Jubilee Post | Nugegoda | 85 | 4.1 | 499 |
| Rasamuluthena - Nugegoda | Nugegoda | 85 | 4.1 | 223 |
| The Lemon Tree, Pure Vegetarian | Jaffna | 85 | 3.8 | 399 |
| Diya Dahara | Kurunegala | 85 | 3.8 | 650 |
| Ambrosia Mirissa | Mirissa | 85 | 4.6 | 834 |
| Sri Aiswariya Vegetarian Restaurant | Nugegoda | 85 | 4.3 | 467 |
| Masma EAT BBQ Nugegoda | Nugegoda | 85 | 4.5 | 420 |

**Notable:** Fab Ceylon (4,419 reviews, 4.4 stars, no website) is the single highest-volume opportunity.
Hospitality and F&B dominate the top tier. These are exactly our sweet spot.

---

## 4. Score Distribution (No-Website Leads)

| Score Tier | Count | Notes |
|------------|-------|-------|
| 85 (top tier) | 80 | High rating + high review volume |
| 80 | 500 | Strong candidates |
| 78 | 12 | Edge tier |
| 73 | 532 | Solid mid-tier |
| 66 | 184 | Lower quality |
| 65 | 60 | |
| 58 | 130 | |
| 50 | 32 | Weakest |

**580 leads score 80+** — this is the core outreach priority list.

---

## 5. Outreach Queue Status

| Status | Count |
|--------|-------|
| pending | 165 |

All 165 outreach messages are staged and awaiting Mev approval. Queue is healthy, no sends have gone out.

---

## 6. Search Query Patterns (Top 15)

| Query | Lead Count |
|-------|-----------|
| food delivery in Colombo Sri Lanka | 56 |
| pharmacies in Colombo Sri Lanka | 54 |
| businesses in Negombo Sri Lanka | 48 |
| businesses in Hatton Sri Lanka | 44 |
| guesthouses in Colombo Sri Lanka | 43 |
| restaurants in Negombo Sri Lanka | 43 |
| travel agencies in Colombo Sri Lanka | 43 |
| guesthouses in Galle Sri Lanka | 42 |
| spare parts shops in Colombo Sri Lanka | 41 |
| businesses in Malabe Sri Lanka | 41 |
| guesthouses in Negombo Sri Lanka | 41 |
| restaurants in Polonnaruwa Sri Lanka | 41 |
| businesses in Kurunegala Sri Lanka | 41 |
| businesses in Matara Sri Lanka | 39 |
| logistics companies in Colombo Sri Lanka | 38 |

**Dominant verticals: F&B, hospitality, pharma, travel.** High tourism corridor presence (Galle, Negombo, Polonnaruwa). Scraper is casting wide net across multiple query types — good coverage diversity.

---

## 7. Lead Acquisition Velocity

| Date | Leads Scraped |
|------|---------------|
| 2026-02-20 | 406 (partial day) |
| 2026-02-19 | 1,826 |
| 2026-02-18 | 1,672 |
| 2026-02-17 | 60 |

**Steady ~1,700-1,800/day since Feb 18.** Total DB: 3,964. Scraper is healthy and scaling.

---

## 8. Business Type Breakdown (No-Website)

| Type | Count |
|------|-------|
| food | 525 |
| restaurant | 452 |
| service | 444 |
| lodging | 269 |
| store | 244 |
| hotel | 185 |
| health | 147 |
| guest_house | 88 |
| beauty_salon | 84 |
| sports_activity_location | 67 |
| gym | 63 |
| car_repair | 57 |

**F&B (restaurant/food) = 977/1,531 (64%) of no-website leads.** Hospitality (lodging/hotel/guest_house) = 542 (35%). Health + beauty = 231. Clear verticals to target with tailored outreach copy.

---

## Summary & Recommendations

### Immediate Priorities
1. **Approve outreach for top 80+ score leads first** — 80 leads at score 85, 500 at score 80. Start with Colombo (396 leads, highest density). Segment by city for personalized batch sends.
2. **Vertical-specific templates needed** — F&B (64% of pool) vs Hospitality (35%) have different hooks. Templates should be industry-aware.
3. **Fab Ceylon is the poster child lead** — 4,419 reviews, 4.4 stars, Kandy, no website. If we land this one it's a case study.

### Data Quality
- **100% phone coverage** on no-website leads (1,531/1,531) — outreach is unblocked on data side
- 1,507/1,531 have ratings (98.4%) — scoring is solid
- 47 leads with missing city — minor cleanup opportunity

### Scraper Health
- Consistent +1,700-1,800/day since Feb 18
- Good query diversity across verticals and cities
- Colombo oversized (396 vs ~135 for next city) — consider expanding queries to secondary cities

---
*Report generated by Otto task runner. For heartbeat review.*

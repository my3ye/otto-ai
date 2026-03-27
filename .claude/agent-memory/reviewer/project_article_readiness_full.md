---
name: Article Library Full Readiness Analysis
description: Full 88-article readiness audit (2026-03-28). Tiers, publish schedule, platform fit, recurring issues.
type: project
---

Full readiness analysis of 88 articles completed 2026-03-28.

**Outcome**: 6 articles ready now (4 clean, 2 need 1 fix each). 37 need minor edits. 7 need major work. 22 are wrong platform/internal. 4 should be archived immediately.

**Why**: Mev directed Paragraph presence to start today, not April 6. Publish SOS Systems first (`3a0e28e4` = approved, 3-pass review).

**How to apply**: Use the publish queue in the analysis artifact at `~/otto/logs/tasks/65103a87-article-readiness-analysis.md`. Before scheduling any article to Paragraph, check it against the tier assignment and any specific fix notes.

**Recurring issues found across the library**:
1. **Koink.fun vaporware** — status=concept, no contracts. Articles stating Koink.fun is live must be fixed (`fd3b2dcb`, `07e384b3`, and likely `62ad3203`).
2. **DPC present-tense** — DPC is planned, not deployed. "Is calculated" must become "will be calculated" (`10393dcc` flagged but likely more).
3. **Project count** — Registry has 18 projects. Any article saying "fourteen" or "fifteen" is stale.
4. **Missing CTAs** — Articles without a clear next step should not go to Paragraph.
5. **Dollar figure inconsistencies** — `efb65920` has $70 vs $80 for same practitioner. Always check internal consistency.

**Immediate archive targets**: `b99b2831` (ACNBN v1 dup), `131729c6` (ACNBN v3 dup), `9e40d92f` (279-char stub), `826695f1` (228-char stub).

**Duplicates requiring decision**:
- 505 DAO intro: `718002a0` v1 vs `2f9bddc5` v2 (pick one)
- PiPi First Meme: `088392e0` v1 vs `24bfbc63` v2 (v2 preferred)
- Polkadot Forum intro: `b2e8d1fb` v1 vs `210b4602` v2 (post one to forum.polkadot.network NOW)

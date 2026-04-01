---
name: Midnight Network tech stack validation (April 1 2026, WF Step 2)
description: Research synthesis validation for Midnight Network full tech/ecosystem/roadmap research (2026-04-01, WF Step 2). APPROVE 8.0/10. 1 critical (thaw math), 2 warnings. All March 31 criticals addressed.
type: project
---

Midnight Network full research synthesis (WF Step 2, 2026-04-01): APPROVE (8.0/10).

**Why:** This is a materially improved synthesis from the March 31 version. All 4 criticals from the prior validation (source count, "only viable" overclaim, unsourced grant amounts, Aztec single-source) have been addressed. ONEON ZK gap independently re-verified via grep. Strategic recommendations are specific and implementable.

**1 Critical:**
- **450-day thaw ≠ Dec 2026**: Synthesis claims "Glacier Drop 450-day thaw creates token unlock pressure through Dec 2026." Math is wrong — 450 days from Dec 2025 ends Feb 2027, not Dec 2026. Dec 2026 = 365 days. The raw retrieval carried this contradiction forward uncorrected. Risk implication: unlock pressure extends ~2 months longer than stated (Feb 2027, not Dec 2026).

**2 Warnings:**
1. **"29-tool MCP server" thin sourcing** — 2 task logs only. Cannot independently verify. Should be softened to "reportedly includes 29 tools per early developer reports" or marked MEDIUM-LOW confidence.
2. **"$200M backing" single source** — Bitcoinethereumnews.com is a single, low-tier source for a significant funding claim. IOG/Hoskinson's involvement is established; the "$200M" figure should be qualified or cross-referenced.

**Verified correct (independently confirmed):**
- ONEON ZK gap: grep for proof/circuit/witness/snark/stark/plonk across /mnt/media/projects/oneon-web — zero matches in .ts, .py, .js, .tsx, .sol files ✓
- No Midnight blockchain integration in any /mnt/media/projects/ directory — only UI theme color refs ("theme-midnight.json") ✓  
- 9.6B NIGHT = 40% × 24B supply ✓
- "Only viable" overclaim: EXPLICITLY CORRECTED in KEY CORRECTION section — Mina and Aleo acknowledged as also-live ZK chains ✓
- Grant amounts now marked "Amounts/deadlines unconfirmed" ✓
- Federated validators list (8 named) matches raw retrieval ✓
- Contradictions section is accurate and appropriately flags decentralization uncertainty ✓

**Recommended actions are specific and implementable:**
1. Apply Aliit Fellowship now — eligible, rolling admissions, no deadline specified ✓
2. Build Compact DSL PoC — specific, doable pre-Mōhalu ✓
3. Mōhalu gate Q2 2026 — concrete, time-indexed ✓

**Pattern reinforced:** "450-day" vs "Dec 2026" is the same class of contradiction as "Web: 5 vs 8" from prior review — raw retrieval inconsistency carried forward uncorrected. Validator should always math-check time/date claims with exact arithmetic.

**How to apply:** When reviewing research syntheses, always math-verify time windows (days vs calendar dates) and check that source count headers in raw retrieval match claimed source counts in synthesis.

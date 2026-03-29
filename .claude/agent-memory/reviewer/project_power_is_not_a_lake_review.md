---
name: Power Is Not a Lake — Multi-Audience Review
description: MY3YE Article 1 "Power Is Not a Lake" (content DB 931c6e77, 2026-03-29, WF Step 1). NEEDS_CHANGES (7.5/10). 3 criticals: "It runs without keepers" present-tense on undeployed protocol; "architecture is public at my3ye.xyz" misleading (links to landing page not docs); "makes pooling structurally impossible" strong engineering claim unproven. Do not touch: MySpace example, "converts power into weight", "not punishment/physics", closer.
type: project
---

Multi-Audience Review: "Power Is Not a Lake" (content DB 931c6e77, 2026-03-29, WF Step 1).
~750 words. Overall score: **7.5/10**. VERDICT: **NEEDS_CHANGES (minor)**.

## PERSPECTIVE 1 — TARGET AUDIENCE (intellectual builders, Gen Z, crypto-native) — 8.5/10

**STRONG:**
- "Power Is Not a Lake" title: punchy, declarative, shares well
- "A full lake is, without exception, a dying lake." — highly quotable
- MySpace example: concrete, historical, not over-explained — perfect anchor
- "Hoarding does not preserve power. It converts power into weight." — best single line; highly quotable
- "This is not punishment. This is physics." — brand-defining, second-best line
- "You cannot game physics." — third-best; final, simple
- River metaphor sustained throughout without overexplaining
- "The river moves. Move with it." — earned closer, no dilution
- Length (~750 words) exactly right for Paragraph medium

**GAPS:**
- Protocol section (§3) feels abstract — crypto-native builders want one sentence of technical specificity (e.g., how is "voice weight" measured on-chain)
- "contribution scoring in ONEON" — ONEON unexplained; parenthetical needed for new readers
- "Follow the build" CTA is minimal — no action for builders who want to contribute now
- §3→§4 transition slightly abrupt

## PERSPECTIVE 2 — SKEPTIC (vaporware detector) — 6.5/10

**CRITICAL — weak/overclaimed:**
1. **"The machine encodes the river. It runs without keepers."** (line 60) — Present-tense on undeployed protocol. DPC tense pattern recurrence (8th instance in content library). Machine is not deployed. Fix: "The design encodes the river. The protocol needs no keeper." or conditional tense.
2. **"The architecture is public at my3ye.xyz"** (line 50) — Misleading. my3ye.xyz is a landing page, not architecture documentation. "Architecture is public" implies whitepaper/technical spec. Fix: "The vision is public at my3ye.xyz" or "The build is live at my3ye.xyz."
3. **"the architecture makes pooling structurally impossible"** (line 52) — Strong engineering guarantee with no deployed evidence. Fix: "is designed to make pooling structurally difficult" or "encodes pooling limits in the protocol itself."

**Other skeptic flags:**
- Three named protocols (SOS/Koink/ONEON) listed as sharing same substrate — none deployed, no contract addresses, no repos linked
- "No founder who can override the ledger" — bold governance claim; ledger doesn't exist yet

## PERSPECTIVE 3 — JOURNALIST (fact-checking, clarity) — 7.0/10

**VERIFIABLE — passes:**
- MySpace walled garden / decline: historically accurate, well-documented ✓
- River physics (evaporation cycle): accurate ✓
- "Power does not accumulate in a river. Power flows through it." — metaphorically accurate ✓

**MISLEADING / UNVERIFIABLE:**
- "The architecture is public at my3ye.xyz" — journalist clicks link, finds landing page, not architecture. Claim is misleading.
- SOS/Koink/ONEON protocol claims — no verifiable deployed code
- "The design has no committee... No founder who can override the ledger" — unverifiable, no ledger deployed

**CLARITY GAPS:**
- "voice weight" (lines 64, 66) — unexplained technical term; parenthetical needed
- "ONEON" — unexplained; one-word descriptor needed
- "the ledger" — what ledger? blockchain? which chain? needs minimal context

## Critical Fixes (must apply before publish)

1. **Line 60**: `"The machine encodes the river. It runs without keepers."` → `"The design encodes the river. The protocol needs no keeper."` (DPC tense — undeployed)
2. **Line 50**: `"The architecture is public at my3ye.xyz"` → `"The vision is public at my3ye.xyz"` (misleading claim — no architecture docs at that URL)
3. **Line 52**: `"the architecture makes pooling structurally impossible"` → `"the architecture is designed to make pooling structurally impossible"` (strong guarantee → design intent)

## Warnings (should fix)

- "ONEON" on line 50 — add parenthetical: `"ONEON (the ecosystem's identity network)"`
- "voice weight" on lines 64/66 — add one-word context on first use: `"voice weight (governance stake)"`
- Protocol Layer (§3) is weakest section — name-drops three protocols without mechanism; consider either deepening or abstracting
- No builder CTA — "Follow the build" is light for Article 1; consider "The first contributors shape the channel" or similar

## What to Protect (do not touch)

- MySpace example — do not replace or shorten
- "Hoarding does not preserve power. It converts power into weight."
- "This is not punishment. This is physics."
- "You cannot game physics. You can only work with them or against them."
- "The river moves. Move with it." (closer)
- `---` separator before Paragraph CTA — correctly protecting the kicker

## Patterns

- DPC tense (undeployed-protocol-present-tense) recurrence: 8th confirmed instance in content library across articles. Pattern is persistent and systematic — content-creator agent needs stronger negative checklist enforcement specifically on closing lines of "Protocol Layer" type sections.
- "architecture is public at [URL]" pattern: check all articles for this claim — it implies docs that don't exist.

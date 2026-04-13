---
name: Cryptic Teaser Tweet Campaign Review (Apr 14-20, 2026)
description: 7-post zkPresence/Pink Paper pre-launch teaser campaign. MINOR_CHANGES 7.5/10. 2 criticals: Day 5 visual brief inside tweet body; Day 4 thread hook grammar. Day 6 urgency slippage.
type: project
---

zkPresence + Pink Paper pre-launch cryptic teaser campaign (Apr 14–20, 2026). WF Step 2 review.

**Verdict:** MINOR_CHANGES 7.5/10

**Critical issues:**
1. Day 5 (e19a25b5) — Visual brief inside `content` field. Full production spec ("Visual: Black background, #0A0A0A...") will publish as tweet text. Must move spec to `notes`, keep only "The river does not announce itself.\n\nIt is already moving." in content.
2. Day 4 (65e08261) — Thread hook grammar: "For the past months" is ungrammatical. Fix: "For months" or "For the past few months." Highest-visibility tweet in campaign.

**Warnings:**
- Day 6 (f39be764): "We will show you soon" is urgency language — breaks the register established by Day 5's river metaphor. Strategy explicitly reserves forward-looking language for Day 7's "Coming." Minor tonal inconsistency.
- Cold-start risk: Days 1-3 are very short single-sentence drops with no engagement hooks and minimal hashtags. Without an existing engaged audience, algorithm will not surface them.

**Strongest posts:** Day 3 ("Not a roadmap... Something rarer. Proof."), Day 7 ("Before the protocol: the proof."), Day 4 Tweet 4 ("Contribution is the only currency that compounds.")

**Brand voice:** Clean. No emojis, no urgency tactics (except Day 6 slip), no corporate speak, no fixed counts.

**Why:** Recurring pattern — visual posts save production briefs in content field rather than notes. This has caused production notes to appear in published content in prior campaigns.

**How to apply:** When reviewing visual posts, always check if content field contains any "---" separator or spec language. The `notes` field is for briefs; `content` is what gets published.

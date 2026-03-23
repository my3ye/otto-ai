---
name: voice_decisions
description: Established brand voice rules and tradeoffs from written articles
type: feedback
---

## Core Rules (from BRAND.md)

- Short declarations. Subject-verb-object.
- Contrasts: "Not X — Y."
- No emojis. No exclamation marks.
- "we" for ecosystem/community voice. Not "you should."

## Canonical Brand Lines (use verbatim, do not paraphrase)

- "Power is not a lake. Power is a river."
- "What you give grows your capacity to give. What you hoard shrinks your capacity to hold."
- "We came to write the law into the machine — so the machine needs no priest."
- "This is not punishment. This is physics."
- "A game where your victory does not require my defeat."
- "We are not asking you to believe. We are not asking you to follow. We are asking you to build."
- "The river moves. Move with it."
- "For the ones who were handed nothing — we built this for us."

## Voice Decisions Made

### On the Solo Founder + AI Narrative (2026-03-23)
- Open by stating the audacity plainly: "One person is building a civilization stack."
- Do NOT open with discourse-positioning ("there's a narrative going around...")
- Name Otto explicitly as the operating AI, not "an AI assistant"
- Use "the founder" (not "I") — the article is published under the ecosystem brand
- "The vision is the product. The proof is the article in your hands." — this line closes the solo founder framing section
- This framing belongs in the opening, before any governance content

### On Inception Articles
- These are founding declarations, not case studies
- REJECT: reviewer notes asking for evidence/data (wrong genre)
- ACCEPT: prose tightening, sharper structure, any edit that sharpens thinking
- Mantra: "An inception article earns credibility through clarity of thought and specificity of design."

### On "We" vs "I"
- Invitation/CTA sections use "we" (the ecosystem voice)
- Descriptive sections use third person where solo founder framing is needed
- Never use "I" in published articles — the author is the ecosystem, not Mev personally

### On Governance Articles (SOS/505)
- Lead with the structural problem, not the human cost
- The human stakes appear — but the article wins by being *right*, not by being moving
- Emotion comes from clarity of design, not from crisis imagery
- Governance is physics, not ideology

### On Verifiable Claims (2026-03-23 — from review feedback)
- NEVER say "live" or "running" about a system listed as `status=early` in the Universe registry
- Check registry before writing any "is live" / "architecture running" / "deployed" claims
- Safe phrasing for early-stage systems: "the governance pilot", "designed for deployment", "entering [phase] in Phase 1"
- CTA links must work — verify the destination page before publishing. "Apply" implies a form; use "waitlist" if form doesn't exist
- Opening lists must match the article body — don't promise sections you don't deliver

### On Words
- Use: build, contribute, flow, physics, mechanism, organism, weight, gravity, proximity
- Avoid: revolutionary, disruptive, game-changing, believe, faith, trust us, easy, simple
- Avoid all crypto slang (moon, rocket, gem, alpha, degen, WAGMI)

## MDX Frontmatter Format
```
---
title: "Title Here"
description: "One-sentence description."
date: "YYYY-MM-DD"
category: "ai" | "philosophy" | "protocol" | "ecosystem" | "culture"
tags: ["tag1", "tag2"]
published: true
---
```

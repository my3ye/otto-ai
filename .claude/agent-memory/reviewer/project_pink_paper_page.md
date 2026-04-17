---
name: Pink Paper page audit
description: Full audit of 505.systems/pink-paper governance document (2026-03-23). NEEDS_CHANGES — OG metadata inheritance bug, no og:image, formula is conceptual not mathematical, "koinks per capita" closing line undermines credibility with external readers.
type: project
---

505.systems/pink-paper — NEEDS_CHANGES (moderate, pre-article-link publish).

**Critical:**
- OG/Twitter metadata NOT overridden on pink-paper page — social shares show generic site title "505.systems | The Sovereign Operating System" instead of "The Pink Paper". page.tsx only exports title+description, not openGraph/twitter blocks.
- No og:image anywhere — blank card on social share.

**Warnings:**
- "koinks per capita" in closing statement will confuse/alienate external governance readers. Too ecosystem-internal for a standalone document.
- P = f(Is, Ec, Rw) is labeled "mathematics" but no actual mathematical expression — DAOists and technical reviewers will flag this immediately.
- "Large Action Model (LAM)" used without defining the term or distinguishing from Rabbit Inc.'s usage.
- Physical Layer (IoT/robotics/energy production) described as present-tense capability in a v1.0 document — should be future-framed.
- GitHub link: source shows my3ye, but WebFetch returned PipiAgent — possible deploy cache lag. Verify propagation.
- $@S in footer reads as garbled to external audience.

**Good:**
- Structure, layout, mobile responsiveness all solid.
- TOC with anchor links works correctly.
- scroll-mt-20 prevents nav overlap.
- CC0 licensing prominent.

**Pattern:** Next.js partial metadata export — page-level metadata only overrides the fields it declares. Always check that openGraph/twitter blocks are explicitly set on important sub-pages, not just inherited from layout.

**Why:** Root layout metadata is generic site metadata. Sub-pages that will be linked/shared externally need their own OG blocks or social cards will look wrong.

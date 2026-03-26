---
name: koink_landing_page_audit_2026_03_26
description: Koink.fun landing page full content audit (2026-03-26). NEEDS_CHANGES. Critical: quantum in H1, weak CTA, no email capture, #trojan anchor UX gap.
type: project
---

Koink.fun landing page audit (src/app/page.tsx + layout.tsx), 2026-03-26. VERDICT: NEEDS_CHANGES.

**Critical issues:**
1. H1 still says "THE QUANTUM KOINKULATOR" — "quantum" was flagged in prior review as misleading. VRF fix applied to body copy only, headline untouched.
2. "Follow for Launch" hero CTA sends visitors to X.com — no email/waitlist capture. Pre-launch product with zero on-site lead retention.
3. #trojan anchor link in hero CTAs scrolls to TrojanSection (manifesto) — this section comes AFTER the Standard section, creating a backwards scroll UX on click.
4. No launch date, countdown timer, or waitlist form — nothing to create urgency or capture intent.

**Warnings:**
- Anti-whale section unchanged. Mev noted marketing angle needs to change from anti-whale framing (per KG note).
- "Conviction Multiplier" feature copy says "Hold $KOINK for 12 months" — product not yet deployed, this reads as present fact not future mechanic.
- Graduated Sell Taxes: "Early exits pay more. Long-term holders earn more." — sell taxes undefined/not explained; readers won't understand the mechanism.
- No community links (Telegram, Discord, Farcaster) — only X.com.
- Token supply, contract address, or audit link all absent (expected for pre-launch but no qualifier).
- Footer ecosystem links include Tusita, ONEON, panik.app — fine, but no link to MY3YE Pink Paper.
- OG/Twitter metadata has no og:image — social card shares will render without image.

**What's good:**
- TrojanSection manifesto copy is the strongest section. "The old world will not let you walk up to its gates carrying a civilisation." — memorable.
- $KOINK Standard section with fork call-to-action is clear and differentiated.
- Chain list (SOLANA · BASE · POLKADOT · EXPANDING) is honest qualifier.
- VRF language in body copy is technically accurate.
- Footer brand line "The meme is the door. The protocol is the floor." is excellent.

**Why:** Mev requested landing page content review 2026-03-26.
**How to apply:** When reviewing future Koink content, check: (1) headline vs body accuracy, (2) CTA conversion chain, (3) pre-launch qualification language.

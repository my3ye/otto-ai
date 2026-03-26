---
name: panik_launch_review
description: Panik App landing page final launch sign-off review (2026-03-26, post-fix). NO-GO — 2 critical blockers: no deployable GitHub remote + zero SEO meta tags.
type: project
---

Panik App landing page final launch review (2026-03-26, post-fix of 3.6/10 audit).

**VERDICT: NO-GO**

**Why:** Two critical blockers prevent public launch.

**How to apply:** Blockers are infrastructure + SEO, not UI. Once resolved, page is launch-ready functionally.

## Critical (must fix)

1. **No deployable GitHub remote** — `ottomev/panik-app-web` is archived (read-only). `PipiAgent/panik-app-web` does not exist. Local code at `/mnt/media/projects/panik-app-web` is correct and fixed, but cannot be pushed anywhere for Vercel deployment. Page is not publicly live.

2. **Zero SEO meta tags** — `index.html` only has `<title>Panik App by SOS Systems</title>`. No meta description, no og:title/description/image, no Twitter cards, no canonical URL. Social sharing produces blank previews.

## What Was Fixed (from 3.6/10 audit)

- All dead download CTAs → replaced with functional WaitlistModal
- Waitlist API live: `mev.otto.lk/papi/projects/panik-app/waitlist` returns 200 + position + referral_code
- Hero primary CTAs: "Join Early Access" + "Become an Agent" both open WaitlistModal
- FooterCTA: "Join Early Access" (waitlist) + "Explore MY3YE Ecosystem" (my3ye.xyz real link)
- Navbar: "Early Access" button + "MY3YE Ecosystem" link both functional

## Remaining Warnings (should fix before launch)

3. Dead nav/footer links — Navbar "Agents", "Trust", "Privacy" all `href="#"`. Footer has 12+ dead links across Features/Network/Company/Legal sections.

4. "Apply to be an Agent" button (OneTapHelp.tsx:66) — no onClick handler. Dead CTA.

5. Placeholder images — `picsum.photos/seed/agent1`, `picsum.photos/seed/founder`, `picsum.photos/seed/map` still present in AgentNetwork, OneTapHelp, PrivacyControl. Unprofessional for public launch.

6. LogoCloud banner says "Integrated with global safety networks" — misleading for concept-stage. Should say "Built to integrate with..."

7. On-chain claims in present tense — "Smart contracts handle automatic trust decay" and "Fully transparent AI running on the blockchain" (PrivacyControl) are concept-stage.

8. `@google/genai`, `better-sqlite3`, `express`, `dotenv` in package.json — server-side deps in a Vite SPA frontend. Should be cleaned up.

## Scores
- CTAs/Conversions: 8/10 (modal works, API live)
- SEO: 0/10 (zero meta tags)
- Copy quality: 7.5/10 (compelling, slight concept-stage overreach)
- Deployment readiness: 0/10 (no valid remote)
- Overall functional score: 6/10 (good code, blocked on infra)

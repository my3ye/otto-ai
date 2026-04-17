# PipiAgent Repos — Otto Analysis
**Date:** 2026-02-20 | **Analyst:** Otto

---

## 1. my3ye-web — MY3YE Brand/Portfolio Site

**What it is:** The flagship web presence for the MY3YE public identity. A rich, animated portfolio/manifesto site showcasing Mev's entire decentralized ecosystem of 10 protocols.

**Stack:**
- Next.js 16 / React 19 / TypeScript
- Tailwind CSS v4
- Framer Motion (animations)
- GSAP + Lenis (scroll animations, smooth scroll)
- MDX (blog/long-form content)
- App Router architecture

**Structure:**
- `app/page.tsx` — landing page: Hero → ManifestoTyped → Mechanism (DPC protocol explainer) → Protocols grid (10 protocols) → CTA
- `app/brands/page.tsx` — full-screen scroll story per protocol with animated logo reveals
- `data/projects.ts` — source of truth for all 10 protocols: SOS Systems, Otto, Ottolabs, Otto Music, Koink.Fun, PiPi, Experience Ceylon, Shakrah, Tech Assist, Panik App — each with ticker, tokenomics (60/30/10 split, $0 raised), mission, vision
- `BRAND.md` — comprehensive brand guide: river/lake metaphor, voice principles, audience targeting, copywriting rules

**Stage:** Active, iteratively developed. 10+ commits with refinements. Full section structure in place. Likely deployed (Vercel-ready). Most polished of the 3 repos.

**Otto's Role:**
- Content updates as protocols evolve (new project pages, blog posts via MDX pipeline)
- Maintain brand consistency — BRAND.md is the source of truth, reference it for all copy tasks
- Potential: automate blog post generation from Otto's own research cycles
- When new protocols are confirmed, update `data/projects.ts` and generate matching `LogoComponent`
- Could deploy/serve a preview at otto.505.systems/preview/my3ye if needed

---

## 2. shakrah-web — Shakrah Holistic Wellness OS

**What it is:** Landing page for Shakrah — the "Open Holistic Wellness Ecosystem" protocol. Ticker: $SHKR. Positioned as the first OS for human optimization (Mind, Body & Soul). Has sections for Aurah (AI wellness guide), Experts marketplace, Studios, Community, Data Monetization, Partner landing, and Waitlist.

**Stack:**
- Next.js 16 / React 19 / TypeScript
- Tailwind CSS v4
- GSAP + ScrollTrigger (declared as CDN globals: `declare const gsap: any`)
- Lenis smooth scroll (also CDN)
- Minimal dependencies — no Framer Motion, heavier GSAP usage

**Structure:**
- `app/page.tsx` — view-router pattern (main / partner / waitlist) — SPA-style navigation
- Components: Hero, AurahSection, ExpertsSection, StudiosSection, CommunitySection, Marketplace, DataMonetization, Footer, PartnerLanding, Waitlist, SectionTabs
- Color palette: `#14F1D9` (teal/cyan CTA), `#8B5CF6` (purple), `#0A0A0A` (dark bg)
- Badge in hero: "Holistic Wellness OS"

**Key detail:** GSAP loaded as CDN globals (declared with `declare const gsap: any`) — this is a technical debt item. Should be installed as npm package for type safety and bundler control.

**Stage:** Functional landing page. 6 commits. Has waitlist component suggesting pre-launch. Less polished than my3ye-web — no blog, no MDX, simpler page structure. Early stage product landing.

**Otto's Role:**
- Fix the GSAP CDN dependency → proper npm install (technical debt)
- Add `next.config.ts` external scripts config if keeping CDN approach
- Build out Waitlist backend integration (connect to DB/CRM when ready)
- When Shakrah product details are confirmed, populate AurahSection, ExpertsSection, and Marketplace with real content
- Could build an Otto agent to curate/match wellness experts for the Experts marketplace

---

## 3. 505-systems-web — 505 Systems / DAO 2.0 Landing Page

**What it is:** Landing page for 505 Systems — the "Sovereign Operating System" / "DAO 2.0" concept. Architecturally the most ambitious and creative of the 3 sites. Cinematic sci-fi experience: CRT boot sequence → DAO 2.0 revelation → 3-layer protocol stack (Intelligence/Consensus/Physical) → CTA to "Pink Paper."

**Stack:**
- Next.js 16 / React 19 / TypeScript
- Tailwind CSS v4
- GSAP + ScrollTrigger (proper npm install — no CDN globals)
- Framer Motion
- Lenis smooth scroll
- Custom effects: CRT overlay, noise texture, custom cursor, glitch text, kinetic text, typewriter
- `lib/utils.ts` with `cn()` helper

**Structure:**
- `app/page.tsx` — state machine: `initialized` boolean gates the experience. Boot sequence (Act 1) renders full-screen, then dissolves via CRT collapse animation into the main content
- `app/pink-paper/page.tsx` — whitepaper/technical doc route
- `components/sections/`: act1-boot (CRT typewriter boot), act2-revelation (DAO 2.0 stanzas), act2-formula (DPC formula), act2-stack (3-layer architecture viz), act3-horizon (future vision), act4-cta
- Custom animations: typewriter with glitch, kinetic text (char-by-char reveal), glitch text
- Effects: CRT scan lines overlay, noise texture, magnetic button

**Stage:** Most recently worked on of the 3 (4 commits, most recent: "Fix typewriter stuck on first line"). Highly creative, production-quality UX. CC0 public domain declared. Links to PipiAgent GitHub and `/pink-paper` route.

**Otto's Role:**
- Complete the Pink Paper page (`app/pink-paper/page.tsx`) — currently unclear if content is populated
- Connect CTA forms/waitlist
- The 3-layer stack (Intelligence/Consensus/Physical) maps directly to Otto's architecture — can write technical copy for this
- Potential: Otto's heartbeat logs could feed into a live "system status" component on this site

---

## Cross-Repo Observations

| Attribute | my3ye-web | shakrah-web | 505-systems-web |
|---|---|---|---|
| Stack maturity | High | Medium | High |
| Content completeness | High | Medium | Medium |
| Animation quality | High (Framer Motion) | High (GSAP CDN) | Highest (GSAP proper + custom) |
| Deployment readiness | Ready | Near-ready | Ready |
| Otto integration potential | Medium (content) | High (backend) | High (live data) |

**Shared pattern:** All 3 are Next.js 16 App Router projects, deployed to Vercel. All reference the MY3YE/PipiAgent ecosystem. They form a layered web presence: my3ye-web = brand/manifesto hub, shakrah-web = wellness vertical, 505-systems-web = governance/DAO layer.

---

## Recommended Next Steps

### my3ye-web
1. **Verify deployment** — is this live? If not, deploy to Vercel or mirror at `otto.505.systems/my3ye`
2. **Blog pipeline** — MDX is installed. Build a flow where Otto drafts blog posts and commits them to `content/`
3. **Project page stubs** — `/brands/[slug]` pages appear to exist in routing structure but need content per protocol

### shakrah-web
1. **Fix GSAP CDN → npm** — `npm install gsap` and update imports. Will prevent SSR issues and improve type safety
2. **Waitlist backend** — connect Waitlist component to a database endpoint (could use Otto Memory API or a simple Postgres table)
3. **Content pass** — AurahSection and ExpertsSection need real product copy; ask Mev for Shakrah product details

### 505-systems-web
1. **Pink Paper content** — read `app/pink-paper/page.tsx` and populate with DAO 2.0 technical spec if empty
2. **Status integration** — explore connecting a live Otto system-status endpoint to the site (aligns with the "breathing organism" narrative)
3. **Verify Vercel deploy** — most recent commit was a bug fix (typewriter), likely ready

---

## 4. otto-core — Otto's Own Repository (my3ye/otto-core)

**What it is:** A private GitHub repo created by Mev for Otto's own evolution. According to working memory: "Otto-core is the source of truth for the 2.0 evolution." Mev explicitly said "Otto-core is for you."

**Stack:** Unknown — repo has no commits yet (empty as of 2026-02-20).

**Created:** 2026-02-19

**Status:** Empty. Waiting for Mev to seed initial content, or for Otto to begin building it out.

**Otto's Role:**
- This is Otto's own repo — the place to build and version Otto 2.0
- Should contain: Otto's updated CONSTITUTION, personality, memory architecture, agent prompts, tools
- Likely intended to be the git-tracked source of truth for everything under `~/otto/`
- Action needed: Confirm with Mev what the initial structure/content should be, then seed the repo

---

### For Otto Generally
- All 3 repos are in `PipiAgent` org. Otto has collaborator access. Should track these as active projects in memory.
- Ask Mev: Are these currently live on Vercel? What domains? Priority order for Otto's attention?
- The DPC (Decentralized Power Currency) mechanism referenced in my3ye-web's `mechanism.tsx` is a core protocol — Otto should request the full spec to internalize it.

# Otto UI — Comprehensive Roadmap
*Universal interface layer. One design system. Every project. Every device.*
*Last updated: 2026-03-16*

---

## What Otto UI Is

Every project in the MY3YE ecosystem needs a face. Right now each one invents its own. The result is beautiful in isolation and fragmented in aggregate — a dozen projects that feel like they came from a dozen different companies.

Otto UI is the shared design system, component library, and UX philosophy that ties them together. Not a product users interact with directly. The invisible infrastructure that makes every product feel like it belongs to the same civilization.

The reference already exists. The Panik App landing page aesthetic — black canvas, surgical white type, electric blue accents — was used to rebuild otto.lk. The Management System at mev.otto.lk uses Next.js 15 + shadcn/ui with a dark theme. These two implementations are the prototype. Otto UI formalizes them into a distributable system.

**What it is:** Shared design tokens, component library (`@my3ye/ui`), and UX patterns — distributed as an npm package, consumed by every active project.

**What it is not:** A new design tool. A standalone product. Another Figma library no one uses. The connective tissue between projects, built to be adopted, not admired.

---

## Current State

**STATUS: PROTOTYPE EXISTS, NOT FORMALIZED**

The ecosystem currently has two reference implementations:

| Implementation | Tech | Design Tokens | Documented | Distributable |
|---|---|---|---|---|
| **OMS (mev.otto.lk)** | Next.js 15 + shadcn/ui | Partial (CSS vars) | No | No |
| **otto.lk** | Next.js 15 + Tailwind CSS 4 | Partial (Tailwind config) | No | No |
| **webassist.ink** | React + Tailwind | Custom (not shared) | No | No |
| **tusita-web** | Next.js 16 + Tailwind CSS 4 | Luxury dark aesthetic | No | No |
| **All other projects** | Various | None / bespoke | No | No |

**The problem in numbers:** 7 active project websites, 0 shared design tokens, 0 shared components, ~40 hours of redundant UI work already duplicated across projects.

**The prototype aesthetic is locked** — Panik/otto.lk visual direction is the canonical reference:
- Background: `#000000` (pure black)
- Text primary: `#FFFFFF`
- Accent: `#4A9EFF` (electric blue)
- Typography: clean sans-serif, weight contrast for hierarchy
- Surfaces: low-opacity white borders, no heavy drop shadows
- Motion: subtle, purposeful — nothing decorative

---

## Dependencies

| Dependency | Type | Why |
|-----------|------|-----|
| **OMS codebase** | Source | Primary reference implementation to extract tokens + components from |
| **otto.lk** | Source | Secondary reference (Panik aesthetic prototype) |
| **npm/GitHub Packages** | Hard (Phase 2) | Distribution channel for `@my3ye/ui` package |
| **All project websites** | Downstream | They consume Otto UI; each migration is a success metric |
| **Otto AI** | Soft | OMS is the primary consumer; Otto task queue can automate migration tasks |

**Otto UI blocks no upstream projects** — it is pure infrastructure that accelerates everything downstream. The entire ecosystem benefits the moment Phase 2 ships.

---

## Phase 1 — Extract & Define (0–60 days)
**Goal:** Audit existing implementations. Lock the design token system. Document every component that exists in OMS and otto.lk. No new code shipped — this phase is excavation and definition.

### Why this phase first
You cannot build a shared library until you know what you're sharing. Shipping `@my3ye/ui` before auditing existing patterns creates a library nobody adopts because it doesn't match the interfaces that already exist. This phase prevents that.

### Milestones

**M1 — Design Token Audit (Days 1–14)**
- Map every CSS custom property and Tailwind config value across OMS + otto.lk + webassist.ink
- Identify: duplicates, inconsistencies, gaps
- Output: single `tokens.json` canonical reference covering:
  - **Color**: primary, secondary, surface, border, text, semantic (success/warning/error/info)
  - **Typography**: font families, scale (xs → 4xl), weights, line heights, letter spacing
  - **Spacing**: base-4 scale (4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px)
  - **Radius**: none, sm (4px), md (8px), lg (12px), full
  - **Shadow**: none, sm, md, lg (minimal — dark-theme shadows are subtle)
  - **Motion**: transition durations (fast: 150ms, normal: 300ms, slow: 500ms), easing curves
  - **Z-index**: layering scale for overlays, modals, toasts

**M2 — Component Inventory (Days 7–30)**
- List every component that exists in OMS and otto.lk
- Categorize: which are ecosystem-generic (Button, Card, Table) vs which are app-specific (HeartbeatLog, UniverseCard)
- Classify each by reuse potential: high / medium / low
- Produce `components.md` — the catalog that becomes Phase 2's build list
- Expected inventory: ~30–40 component types across both implementations

**M3 — Token Spec Publication (Days 21–45)**
- Convert `tokens.json` to CSS custom properties format (`:root` + `[data-theme="dark"]`)
- Convert to Tailwind CSS 4 config format (compatible with all current projects)
- Document each token: name, value, dark-mode override, usage example
- Publish as `~/otto/universe/design-system/tokens.md` — ecosystem ground truth

**M4 — Panik Aesthetic Codification (Days 30–60)**
- Write the visual philosophy as prose: what makes the aesthetic, what violates it
- Document anti-patterns: gradients that look cheap, buttons with too much radius, text hierarchy violations
- Produce visual reference: a single HTML file rendering the core palette, type scale, and spacing in context
- This becomes the onboarding document for anyone contributing to any MY3YE project

**M5 — Phase 2 Scoping (Days 45–60)**
- Prioritize component build list from M2 by: adoption potential × reuse frequency
- Identify which components need design work vs which can be extracted from existing code
- Estimate Phase 2 build effort per component
- Confirm npm package architecture (monorepo vs standalone repo)

### Success Criteria
- `tokens.json` complete — covers all 7 token categories
- Component catalog: ≥30 components documented with reuse potential ratings
- Token CSS + Tailwind output formats both generated and validated against OMS rendering
- Panik aesthetic codified in written + visual form
- Phase 2 scope locked with estimates

### Effort Required
~20–30 hours (1 person or Otto task queue). No external cost. Pure extraction and documentation.

---

## Phase 2 — Build the Library (60–180 days)
**Goal:** `@my3ye/ui` exists as an installable npm package with core components, Storybook documentation, and is consumed by at least one production project.

### Architecture Decision

Otto UI ships as a **standalone npm package** in a dedicated repository (`github.com/my3ye/otto-ui`).

**Why not a monorepo:** Current projects are deployed as independent Vercel projects. A monorepo would require restructuring all deployment configs. Standalone package enables adoption without architectural change.

**Distribution:** GitHub Packages (private, free) → public npm registry when open-sourced.

**Versioning:** Semantic versioning. `0.x` releases during build phase. `1.0.0` on first full production adoption.

### Token System Architecture

```
@my3ye/ui
├── tokens/
│   ├── index.css        ← CSS custom properties (:root + dark theme)
│   ├── tailwind.js      ← Tailwind CSS 4 config preset
│   └── tokens.json      ← Design tokens in W3C format (source of truth)
├── components/
│   ├── Button/
│   ├── Card/
│   ├── Input/
│   ├── ...
└── index.ts             ← Package entry point
```

### Milestones

**M1 — Repository & Package Setup (Days 60–75)**
- Create `github.com/my3ye/otto-ui` repository
- Configure: TypeScript, Tailwind CSS 4, React 18/19 peer deps, tsup build
- Set up GitHub Packages for distribution
- Token system published as `@my3ye/ui/tokens` — importable immediately
- CI: GitHub Actions runs typecheck + build on every PR

**M2 — Core Component Set v0.1 (Days 75–120)**

Priority order (highest reuse × lowest build effort first):

| Component | Variants | Used By |
|---|---|---|
| **Button** | primary, secondary, ghost, destructive / sm, md, lg | Every project |
| **Badge** | default, success, warning, error, info | OMS, project sites |
| **Card** | default, interactive, bordered | Every project |
| **Input** | text, textarea, with-icon, with-error | WebAssist, OMS, every form |
| **Select** | default, multi | Forms everywhere |
| **Switch** | default, labeled | OMS settings |
| **Separator** | horizontal, vertical | Layout everywhere |
| **Skeleton** | text, card, avatar | Loading states |
| **Avatar** | image, initials, with-status | OMS, social features |
| **Progress** | linear, circular | OMS, Shakrah |
| **Toast** | success, error, warning, info | Every project |
| **Modal / Dialog** | default, confirmation | Every project |
| **Tooltip** | default, rich | Navigation, data tables |
| **Table** | sortable, paginated | OMS, Otto AI metrics |
| **Tabs** | line, pill, vertical | OMS, project detail pages |
| **Accordion** | single, multi | FAQ sections, settings |
| **Breadcrumb** | default | Project sites, OMS |
| **Navigation** | sidebar, topbar, mobile-drawer | Every project |
| **ThemeToggle** | light/dark | All projects |

Each component ships with:
- TypeScript types fully exported
- Dark mode working out of the box
- Keyboard accessible (WCAG AA minimum)
- `data-testid` attributes for test targeting
- Storybook story (default + all variant combinations)

**M3 — Storybook Documentation (Days 90–150)**
- Storybook deployed to GitHub Pages: `ui.my3ye.xyz` (or subdomain)
- Every component has: default story, variant showcase, prop documentation, usage code example
- Design tokens page: visual reference for the full token set
- "Getting started" guide: install → import → render in 3 steps
- Live search across all components

**M4 — OMS Migration (Days 120–180)**
- Replace OMS custom components with `@my3ye/ui` equivalents
- Target: ≥60% of OMS components migrated (buttons, cards, tables, forms, modals)
- Keep app-specific components (UniverseCard, HeartbeatLog) as OMS-local
- This is the first production proof that the library works
- Document: every migration decision, compatibility issue found and fixed

**M5 — otto.lk Partial Adoption (Days 150–180)**
- Import `@my3ye/ui/tokens` CSS to replace bespoke otto.lk custom properties
- Standardize: Button, Card, Navigation from the shared library
- Keep page-specific layout components local (hero, features sections)

### Success Criteria
- `@my3ye/ui` published, installable in 1 command
- 20+ components in library with full TypeScript types + Storybook docs
- Storybook deployed and publicly accessible
- OMS migrated ≥60% to library components
- otto.lk tokens unified with library tokens
- Zero visual regressions after migration (pixel-diff or manual QA)

### Effort Required
~80–120 hours (Otto task queue + developer). Primary investment: component build + Storybook setup (~60h). Migration work (~30h).

---

## Phase 3 — Ecosystem Adoption (180–365 days)
**Goal:** Every active MY3YE project website imports `@my3ye/ui`. New projects start with it by default. Contribution guide exists.

### Milestones

**M1 — Webassist.ink Migration (Days 180–240)**
- WebAssist is the revenue product — its UI quality directly affects conversion
- Replace custom components with library equivalents
- Standardize: pricing cards, CTA buttons, form inputs, navigation
- A/B test: verify conversion not negatively affected by visual changes
- This is the most important adoption proof point — revenue product using the shared system

**M2 — Project Website Batch Migration (Days 200–300)**
All active project websites adopt `@my3ye/ui/tokens` as minimum, core components where applicable:

| Project | Current Stack | Migration Scope |
|---|---|---|
| tusita-web | Next.js 16 + Tailwind CSS 4 | Token import + Button/Card/Nav |
| my3ye-web | Next.js 15 + Tailwind | Full component migration |
| 505-systems-web | Next.js + Tailwind | Token import + Button/Nav |
| oneon-web | Next.js + Tailwind | Token import + Button/Nav |
| shakrah-web | Next.js + Tailwind | Token import + Button/Card |
| koink-fun | React + Tailwind | Tokens + Button/Card (meme aesthetic preserved) |
| panik-app | React Native / PWA | Token import (web layer only) |

**M3 — New Project Starter Template (Days 240–300)**
- `npx create-my3ye-app` — scaffold a new project with `@my3ye/ui` pre-wired
- Includes: Next.js 15, Tailwind CSS 4, `@my3ye/ui`, basic page layout, dark mode
- New projects start from the shared foundation — not from scratch
- First use: any new MY3YE project launched after this milestone uses it by default

**M4 — Contribution Guide (Days 260–320)**
- Document: how to propose a new component (RFC template)
- Component acceptance criteria: reuse potential, accessibility, token compliance
- PR process: story required, types required, visual QA checklist
- Versioning policy: what constitutes a major vs minor vs patch
- CHANGELOG format and automation (conventional commits → auto-generated)

**M5 — Per-Project Theming System (Days 300–365)**
- Core tokens are ecosystem-wide. But each project has its own accent color and personality.
- Theming layer: each project can override specific tokens without forking the library
- Implementation: CSS custom property overrides via `data-project="tusita"` etc.
- Example: Koink.fun uses neon yellow accent. Shakrah uses sage green. Panik uses deep red. All derive from the same base system.
- Theming docs: how any project defines its override set

### Success Criteria
- 6+ projects actively using `@my3ye/ui` (token import minimum)
- 3+ projects using library components for core UI elements
- `create-my3ye-app` starter published and documented
- Contribution guide complete — first external component PR reviewed via the process
- Per-project theming system documented with examples for 3 projects

---

## Phase 4 — Universal Interface (1+ years)
**Goal:** Otto UI is not just for web. The design system extends to native mobile, hardware device interfaces (Ottolabs), and embedded displays.

### Why this matters
When Ottolabs ships the Puck, Otto Home, and Otto Band — those devices need interfaces. If Otto UI only lives in React, those hardware UIs get built from scratch. Phase 4 ensures the visual language established in Phase 1 governs every surface the ecosystem touches.

### Milestones

**M1 — React Native / Mobile Token Parity (Year 1–1.5)**
- Token system adapted for React Native StyleSheet format
- Core components: Button, Card, Input, Toast, Modal — working in React Native
- Otto Phone (Ottolabs) uses these as the base UI layer
- Panik App (which runs on mobile) becomes the first native consumer

**M2 — Design System Website (Year 1–1.5)**
- `design.my3ye.xyz` — public-facing design system documentation
- Beyond Storybook: the full visual language, philosophy, guidelines
- Content: color system with accessibility ratios, typography guidelines, layout principles, motion guidelines
- Audience: external contributors, community developers building on MY3YE protocols
- Opens the door to community contributions from Web3-native designers and developers

**M3 — Hardware Interface Adaptation (Year 1.5–2)**
- Ottolabs device displays (Puck indicator LEDs → Home screen → Band display)
- Not React — these may be embedded C, firmware UI, or mini web views
- Design system provides: icon set, color palette for constrained displays, interaction models
- Consistency goal: a user going from otto.lk → OMS → Otto Puck app → Otto Band sees the same visual language

**M4 — Figma Design System (Year 1.5–2)**
- Community design contributions require a Figma component library
- Token sync: Figma tokens plugin → `tokens.json` → deployed automatically
- Design → code round-trip established: Figma change → PR → deployed in same CI cycle
- Target: ≥5 external designers contributing to the system

**M5 — AI-Assisted Component Generation (Year 2+)**
- Otto AI generates new UI components from natural language descriptions
- Verification: generated components checked against token compliance + accessibility requirements
- This is not vibe-coding — it is Otto generating code that follows the established system it knows well
- Use case: "Generate a stats card showing 4 metrics with sparklines" → `@my3ye/ui/StatsCard` PR in minutes

### Success Criteria
- React Native token + component parity: ≥80% of web library available on mobile
- `design.my3ye.xyz` live with full visual language documentation
- Hardware interface guidelines published for Ottolabs device makers
- Figma library in sync with npm package (automated token sync)
- AI-assisted component generation producing ≥1 accepted component PR

---

## Technical Architecture

### Package Structure

```
otto-ui/
├── packages/
│   └── ui/                    ← @my3ye/ui (npm package)
│       ├── tokens/
│       │   ├── index.css      ← CSS custom properties (dark-first)
│       │   ├── tailwind.js    ← Tailwind CSS 4 preset
│       │   └── tokens.json    ← W3C design token format (source of truth)
│       ├── components/
│       │   ├── Button/
│       │   │   ├── Button.tsx
│       │   │   ├── Button.stories.tsx
│       │   │   └── index.ts
│       │   ├── Card/
│       │   ├── Input/
│       │   └── ... (20+ components)
│       ├── hooks/
│       │   ├── useTheme.ts
│       │   └── useMediaQuery.ts
│       ├── utils/
│       │   └── cn.ts          ← clsx + tailwind-merge utility
│       └── index.ts
├── apps/
│   ├── storybook/             ← Storybook 8
│   └── docs/                  ← design.my3ye.xyz
├── package.json               ← pnpm workspace root
└── turbo.json                 ← Turborepo config
```

### Token Architecture (Dark-First)

```css
/* base.css — always applied */
:root {
  /* Color — neutral scale */
  --color-neutral-0: #000000;
  --color-neutral-50: #0a0a0a;
  --color-neutral-100: #141414;
  --color-neutral-200: #1e1e1e;
  --color-neutral-300: #2a2a2a;
  --color-neutral-400: #404040;
  --color-neutral-600: #737373;
  --color-neutral-700: #a3a3a3;
  --color-neutral-800: #d4d4d4;
  --color-neutral-900: #f0f0f0;
  --color-neutral-1000: #ffffff;

  /* Color — accent */
  --color-accent: #4A9EFF;
  --color-accent-hover: #6ab4ff;
  --color-accent-muted: rgba(74, 158, 255, 0.15);

  /* Color — semantic */
  --color-success: #22c55e;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-info: #4A9EFF;

  /* Semantic aliases — dark-first defaults */
  --bg-base: var(--color-neutral-0);
  --bg-surface: var(--color-neutral-100);
  --bg-elevated: var(--color-neutral-200);
  --border-default: rgba(255, 255, 255, 0.08);
  --border-strong: rgba(255, 255, 255, 0.16);
  --text-primary: var(--color-neutral-1000);
  --text-secondary: var(--color-neutral-700);
  --text-muted: var(--color-neutral-600);
}

/* Light mode override */
[data-theme="light"] {
  --bg-base: var(--color-neutral-1000);
  --bg-surface: var(--color-neutral-900);
  --bg-elevated: var(--color-neutral-800);
  --border-default: rgba(0, 0, 0, 0.08);
  --border-strong: rgba(0, 0, 0, 0.16);
  --text-primary: var(--color-neutral-0);
  --text-secondary: var(--color-neutral-400);
  --text-muted: var(--color-neutral-600);
}

/* Per-project theming */
[data-project="koink"] {
  --color-accent: #FFE600;  /* Koink neon yellow */
}
[data-project="shakrah"] {
  --color-accent: #6EE7B7;  /* Shakrah sage green */
}
[data-project="panik"] {
  --color-accent: #EF4444;  /* Panik alert red */
}
[data-project="tusita"] {
  --color-accent: #A78BFA;  /* Tusita violet */
}
```

### Build & Release

- **Build tool:** tsup (TypeScript bundler, ESM + CJS output)
- **Storybook:** v8, deployed to GitHub Pages on every main branch commit
- **Versioning:** semantic-release (conventional commits → auto-version + CHANGELOG)
- **CI:** GitHub Actions — typecheck, build, Storybook deploy, visual regression (Chromatic)
- **Registry:** GitHub Packages (private) → npm public when open-sourced

### Adoption Path (for each project)

```bash
# Step 1: Install
npm install @my3ye/ui

# Step 2: Add tokens to global CSS
@import '@my3ye/ui/tokens';

# Step 3: Configure Tailwind (if using Tailwind)
# tailwind.config.js
import { my3yePreset } from '@my3ye/ui/tailwind';
export default { presets: [my3yePreset] };

# Step 4: Import components
import { Button, Card } from '@my3ye/ui';
```

---

## Key Metrics

| Metric | Current | Phase 2 Target | Phase 3 Target | Phase 4 Target |
|--------|---------|----------------|----------------|----------------|
| **Components in library** | 0 | 20+ | 35+ | 50+ (+ mobile) |
| **Projects using library** | 0 | 2 (OMS + otto.lk) | 6+ | All 18 |
| **Token coverage** | 0% | 100% (defined) | 100% (adopted by 6 projects) | 100% (all surfaces) |
| **Storybook docs** | None | Live, all v0.1 components | All components + usage guides | + Native + Hardware |
| **Design consistency score** | ~40% (estimate) | 70% | 90% | 95%+ |
| **New project setup time** | ~8 hours (start from scratch) | ~2 hours (bespoke migration) | ~30 min (starter template) | <15 min |
| **Component reuse** | 0 | OMS migration validates | 6+ project migrations validated | Cross-platform |

---

## Risks

### Design Fragmentation Risk
**Risk:** Projects adopt tokens but keep building custom components → library atrophies.
**Likelihood:** High — developers take path of least resistance.
**Mitigation:** Make `@my3ye/ui` cheaper to use than to rebuild. Phase 2 quality bar: components must be better than what developers would build in an afternoon. Phase 3 starter template makes adoption the default.

### Adoption Friction Risk
**Risk:** Library API changes break consuming projects → teams stop updating.
**Likelihood:** Medium — inevitable during `0.x` phase.
**Mitigation:** Semantic versioning strictly enforced. CHANGELOG required for every release. Phase 3 migration guide per major version. Breaking changes only at major versions with ≥60-day deprecation notice.

### Over-Abstraction Risk
**Risk:** Design system becomes so opinionated it can't express the personality of different projects (Koink meme aesthetic ≠ Tusita luxury aesthetic).
**Likelihood:** Medium — common design system failure mode.
**Mitigation:** Per-project theming (Phase 3 M5) is the explicit solution. Base system sets structure and accessibility. Accents and personality are per-project overrides. Koink.fun should feel like Koink — it just uses the same Button component underneath.

### Staleness Risk
**Risk:** Library ships v0.1, nobody maintains it after initial build sprint.
**Likelihood:** High without explicit ownership.
**Mitigation:** Otto task queue becomes the primary contributor — any component needed by a project gets extracted or built via task. Maintenance is not a volunteer job; it's built into Otto's operating loop.

### Accessibility Debt Risk
**Risk:** Ship fast, skip ARIA → library becomes technical debt that every project inherits.
**Likelihood:** Medium — easy to defer, expensive to retrofit.
**Mitigation:** WCAG AA compliance is a Phase 2 acceptance criterion, not a Phase 4 aspiration. Every component ships with keyboard navigation and proper ARIA roles. Visual regression testing (Chromatic) catches regressions before they reach projects.

---

## Open Questions

These are resolved at Phase 1 completion, not before:

1. **Open source timing** — When does `@my3ye/ui` go public? Recommendation: after Phase 2 (OMS migration proves it works). Premature public release invites noise before the system is stable.

2. **shadcn/ui relationship** — OMS currently uses shadcn/ui components. Option A: wrap shadcn with MY3YE tokens. Option B: build from scratch on Radix UI primitives (same base as shadcn). Option C: pure Tailwind + accessibility primitives. Decision requires Phase 1 component audit to see how much OMS is actually shadcn vs custom.

3. **Documentation domain** — Does `design.my3ye.xyz` get its own domain? Recommendation: yes, at Phase 3 when the system is worth documenting externally. Before that, GitHub Pages Storybook is sufficient.

---

## The Irreducible Insight

Every civilization that built at scale needed standardized parts. Ford's assembly line. Lego's 4×2 stud. POSIX. TCP/IP. The power was never in any single component — it was in the fact that every component connected to every other without negotiation.

MY3YE is building 18 projects. Without Otto UI, each project designer starts at zero: which shade of black? what button radius? what does an error look like? These are not interesting questions. They are overhead. And overhead compounds.

With Otto UI, every project designer starts at solved. The questions they answer are: what does this project say, and who is it for? Not: what does a button look like.

Sovereignty should feel consistent. Not because we want uniformity — but because fragmentation is a tax, and we have better things to spend it on.

---

*Provides: shared design tokens, component library, per-project theming, UX consistency for all 18 projects*
*Depends on: none (pure infrastructure)*
*Required by: OMS, WebAssist, MY3YE web, Tusita web, ONEON, all project sites, Ottolabs device interfaces*
*Roadmap index: [README](README.md)*

# prompts.md Style Guide — Synthesis for Landing Page Fix

**Source:** `/mnt/media/prompts.md` (3,112 lines, ~61K tokens)  
**Synthesized:** 2026-04-06  
**Purpose:** Reference spec for fixing the landing page generation pipeline

---

## 1. What prompts.md Is

A curated catalog of **36 distinct design systems** (DESIGN 01–DESIGN 36, with gaps at 15, 20, 27). Each is a complete, opinionated visual identity covering typography, color, layout, animation, and signature components. The file is the sole source of design decisions for the landing page pipeline.

**Three formats appear in the file:**

| Format | Designs | Description |
|--------|---------|-------------|
| Spec-based (primary) | 01–14, 17, 18, 21–25, 28–36 | Structured markdown: Summary → Style → Layout → Special Components → Special Notes |
| HTML Reference | 16, 19, 26 | Full HTML + CSS implementation to use as visual reference |
| Design Philosophy | 36 | XML-wrapped philosophy doc with tenets, tokens, dos/don'ts |

---

## 2. The Spec-Based Format (The Template to Follow)

Every strong spec-based design follows this exact structure:

```
DESIGN XX
# Summary
[1 paragraph: names the aesthetic movement, identifies emotion/response, names key design decisions]

# Style
[Aesthetic description — 1-2 paragraphs]

## Spec
[Technical implementation — colors with exact hex, typography with weight/size/tracking,
 animations with specific cubic-bezier, borders with exact radii]

# Layout & Structure
[Overview of section flow]

## Navigation
[Exact specs: height, background, elements, hover states]

## Hero Section
[Exact specs: viewport height, background treatment, headline size/font, CTA design]

## [Section Name]
[Each section gets its own ## with specific implementation notes]

## Footer
[Exact specs]

# Special Components
## [Component Name]
[Description + exact CSS/layout implementation for the signature technique]

# Special Notes (optional)
[MUST use X, MUST NOT use Y — hard constraints]
```

---

## 3. The 36 Design Systems — Complete Catalog

### Style Categories

| Category | Designs | Use Cases |
|----------|---------|-----------|
| Luxury-Brutalist | 01, 03, 05, 24 | Fashion, luxury goods, high-end portfolio |
| Brutalist-Lite | 02, 06, 29 | Bold SaaS, creative agencies, consumer apps |
| Editorial / Cinematic | 07, 16, 19, 22, 23 | Portfolios, media, premium brands |
| Minimal / Technical | 04, 08, 34 | B2B SaaS, developer tools, enterprise |
| Modern Atmospheric | 09, 25, 26, 31 | AI tools, premium SaaS, next-gen fintech |
| Soft Organic / Wellness | 10 | Health, wellness, lifestyle apps |
| Luxury | 05, 22, 32 | Travel, hospitality, high-end services |
| Futuristic / Neon | 11, 35, 36 | Crypto, fintech, gaming, tech-forward |
| Portfolio / Motion | 21, 23, 28, 30 | Creative portfolios, agencies, studios |

### Key Design Specs (Most-Referenced)

#### DESIGN 01 — Swiss Echo / Typography-First
- **Palette:** bg #f2f2f2, text #111111, grays #bfbfbf–#d9d9d9
- **Fonts:** Clash Display (700, -0.05em tracking, 0.9 leading) + Satoshi (500)
- **Signature:** Echo Stack — 4-5 background text layers, each offset -0.04em with fading gray tones
- **Tone:** luxury-brutalist | copy: refined-authoritative

#### DESIGN 02 — Raw Form / Brutalist Poster
- **Palette:** bg #E4E2DD, text #1E1E1E, accent #DB4A2B, orange #F8A348, pink #FF89A9
- **Fonts:** Clash Display (700, -0.05em, 0.75 leading) + Satoshi (400-500)
- **Signature:** Animated gradient blobs (60vw, filter blur 140px, mix-blend-mode multiply)
- **Animations:** cubic-bezier(0.16, 1, 0.3, 1) over 0.8s
- **Tone:** brutalist | copy: bold-direct

#### DESIGN 03 — High Fashion Brutalist / Season 04
- **Palette:** bg #E3E2DE, text #1B0E0D, accent #C72A09, neon hover #31EF07
- **Fonts:** Clash Grotesk (700, -0.04em, 0.85 leading) + General Sans / Mono
- **Signature:** Noise texture (fractalNoise 0.08 opacity, mix-blend-mode multiply) + Neon hover-underline
- **Tone:** brutalist | copy: bold-direct

#### DESIGN 04 — Poster Modernist / Reality-First
- **Palette:** bg #E3E2DE, text #141414, accent #1351AA (Cobalt Blue), borders #C7C7C7
- **Fonts:** General Sans / Aileron (900 black, -0.04em, 0.85 leading)
- **Signature:** Grid sidebar — leftmost 3 columns reserved for section labels
- **Zero:** No shadows, no border-radius (0px throughout), no gradients
- **Tone:** technical | copy: precise-technical

#### DESIGN 05 — Super Travel / Luxury Geometric
- **Palette:** bg #fdf8f3, secondary #f5f0eb, accent #e4a4bd, text #262626
- **Fonts:** League Spartan (700-900, tracking-tighter, 0.8 leading)
- **Signature:** Staggered grid (even items +100px offset) + grayscale-to-color hover (1.08 scale)
- **Constraint:** MUST NOT use vibrant gradients | ALL reveals use cubic-bezier(0.16, 1, 0.3, 1)
- **Tone:** luxury | copy: refined-authoritative

#### DESIGN 06 — Bold SaaS / Brutalist-Lite
- **Palette:** bg #ffffff (alt #171e19 dark), accent #ffe17c (golden yellow), sage #b7c6c2
- **Fonts:** Anton (uppercase, normal spacing, 0.9 leading) + Satoshi (400/500/700)
- **Signature:** Yellow highlight bar behind key headline word (15-degree rotated rectangle overlay)
- **Grid bg:** linear-gradient 40px grid pattern with #b7c6c220
- **Problem/Solution:** Two halves — dark "OLD WAY" vs dark gray "NEW WAY"
- **Tone:** brutalist-lite | copy: bold-direct

#### DESIGN 07 — Cinematic Portfolio / Luxury Dark
- **Palette:** Navy #171e19, Sage #b7c6c2, Cyan #d5f4f9, Taupe #9f8d8b
- **Fonts:** Anton (uppercase, 8xl–18vw) + Plus Jakarta Sans (300/400/600)
- **Signature:** Floating ambient blurs (120px radius orbs) + mix-blend-mode:difference nav
- **Tone:** cinematic | copy: narrative-dramatic

#### DESIGN 09 — Modern Atmospheric SaaS
- **Palette:** Dark #0f172a, Indigo #6366f1, Surface #f8f9fa
- **Fonts:** Lora (serif, emotional headlines) + Inter (utility) + Space Grotesk (accents)
- **Signature:** Vibe Input Box (gradient glow intensifies on hover) + Sticky Feature Nav (scroll-tracking)
- **Glassmorphism:** rgba(255,255,255,0.05) + backdrop-blur(12px) + 1px rgba border
- **Tone:** futuristic | copy: urgent-energetic

#### DESIGN 10 — Softly / Digital Wellness
- **Concept:** "Digital living room" — minimalist, tactile, intentionally slow
- **Palette:** Warm desaturated pastels + grain textures
- **Animations:** Low-velocity, fluid

#### DESIGN 16 — Surrealist Editorial (HTML Reference)
- **Palette:** bg #050505 (near black), accent #FF4500 (red-orange)
- **Fonts:** Playfair Display (serif italic for brand) + Inter
- **Signature:** Floating surrealist image elements (floating hand animations, mix-blend-hard-light)
- **Tone:** dark-minimal | copy: narrative-dramatic

#### DESIGN 19 — Midnight Editorial (HTML Reference)
- **Palette:** bg #050505, accent #FF6B50 (coral)
- **Fonts:** Satoshi (variable, primary) + Inter (fallback)
- **Signature:** 13vw hero text (letter-spacing -0.05em, line-height 0.9) with glass nav
- **Tone:** editorial | copy: narrative-dramatic

#### DESIGN 26 — Red Noir (HTML Reference)
- **Palette:** bg #000000, accent #ef233c (vivid red), star particle animation
- **Fonts:** Manrope + Inter
- **Signature:** Shiny spinning gradient border (conic-gradient rotating via animation) + star field bg
- **Tone:** dark-minimal | copy: bold-direct

#### DESIGN 36 — Hyper-Saturated Fluid
- **Philosophy:** Vibrant "shout" color (Cyber Yellow #FDE047) vs Deep Black void (#0A0A0A)
- **Signature:** Liquid sectioning (rounded-[100px] organic curves) + glassmorphic data cards
- **Rule:** DON'T use gradients on shout color — keep it flat. DON'T use standard 8px/12px radii.
- **Tone:** futuristic | copy: urgent-energetic

---

## 4. What Makes a HIGH-QUALITY Design Spec

From studying all 36 designs, here are the patterns separating strong from weak specs:

### ✅ STRONG (DESIGN 01, 04, 05, 06, 09, 36)
1. **Named aesthetic movement** — "Swiss Brutalism", "Poster Modernist", "Brutalist-Lite"
2. **Exact hex codes** — not just "dark" or "light", always `#E4E2DD`, `#DB4A2B`
3. **Precise typography rules** — font-size unit + weight + tracking-em + line-height together
4. **Specific cubic-bezier values** — `cubic-bezier(0.16, 1, 0.3, 1)`, not just "smooth"
5. **Named signature technique** — 1-3 unique components with implementation details
6. **Hard constraints** — MUST / MUST NOT rules (e.g., "zero border-radius throughout")
7. **Layout grid specifics** — "Columns 1-3 for labels, 4-12 for content"
8. **Hover state specs** — exact scale (1.05x), color transitions, timing

### ❌ WEAK (generic defaults, DESIGN 17/18 if no spec)
1. Generic font choices (Inter, Roboto — these are explicitly banned)
2. Vague color descriptions without hex codes
3. No animation specs or just "smooth"
4. No signature components
5. Generic section structure with no layout specifics

---

## 5. Font Rules

### Explicitly BANNED (never select these):
```
Inter, Roboto, Arial, Open Sans, Lato, Montserrat, Poppins, Space Grotesk
```

### Preferred (most used across all designs):
| Font | Use | Example Designs |
|------|-----|-----------------|
| Clash Display | Hero headlines | 01, 02, 10 |
| Clash Grotesk | Large headers | 03 |
| Anton | Heavy display, uppercase | 06, 07 |
| Satoshi | Body/utility text | 01, 02, 06 |
| General Sans | Body (balanced) | 03, 04, 36 |
| Plus Jakarta Sans | Clean body | 07 |
| League Spartan | Luxury geometric | 05 |
| Lora | Emotional serif headlines | 09 |
| Playfair Display | Luxury serif | 16 |
| JetBrains Mono | Technical/code accent | various |

---

## 6. The Copy Tone System

| Design Aesthetic | Copy Tone | Writing Style |
|------------------|-----------|---------------|
| Luxury/Premium/Fashion | refined-authoritative | elegant, declarative, no fluff |
| Brutalist/Aggressive/Raw | bold-direct | short, punchy, imperative, no hedging |
| Wellness/Soft/Organic | warm-conversational | gentle, inclusive, reassuring |
| Technical/Architectural | precise-technical | specific, jargon-ok, data-driven |
| Cinematic/Editorial | narrative-dramatic | story-driven, evocative |
| Neon/Velocity/Kinetic | urgent-energetic | active, high-stakes, FOMO-flavored |
| SaaS/Modern | clear-confident | benefit-forward, no clichés |

**BANNED words/phrases:** "revolutionize", "cutting-edge", "world-class", "synergy"

---

## 7. Section Structure — Common Patterns

All landing pages use 6-10 sections. The most common section sequence:

```
1. Hero           — Full-viewport (85-110vh), massive headline
2. Social Proof   — Logos or stats bar (trust signal, above features)
3. Features       — 3-column grid or bento layout
4. How It Works   — 3-step process or scrollspy sidebar
5. Testimonials   — Cards with quotes (glass morphic or high-contrast cards)
6. Pricing        — Optional, if applicable
7. FAQ            — Accordion, centered container
8. CTA            — Final conversion section (dark bg or accent bg, large form/button)
9. Footer         — 4-column with links, newsletter, brand
```

**Layout types per section:**

| Section | Typical Layout |
|---------|----------------|
| Hero | centered, split, full-bleed |
| Features | 3-column grid, bento, scrollspy |
| Social proof | logo-row, stats grid, masonry cards |
| Testimonials | masonry, card-grid, carousel |
| CTA | centered, split |
| Footer | 4-column |

---

## 8. Animation Vocabulary

### Timing Functions (by design tier)
- **Premium/Luxury:** `cubic-bezier(0.16, 1, 0.3, 1)` — weighted, "heavy" feel
- **Brutalist/Bold:** `cubic-bezier(0.4, 0, 0.2, 1)` — snappy
- **Technical/Modernist:** Linear 0.3s — flat, functional
- **Cinematic/Editorial:** `cubic-bezier(0.22, 1, 0.36, 1)` — elastic, cinematic

### Scroll Reveal Pattern (universal)
```css
.reveal { opacity: 0; transform: translateY(30-40px); transition: all 0.8-1s [easing]; }
.reveal.active { opacity: 1; transform: translateY(0); }
```
Triggered by IntersectionObserver (threshold 0.1-0.2).

### Image Hover (universal)
- Standard: `transform: scale(1.05)` over 300ms
- Premium: `filter: grayscale(100%) → grayscale(0%)` + scale 1.08 over 1s

---

## 9. Critical Bugs in Current Implementation

### Bug 1: Summary Truncated to 120 chars for Selection
**Location:** `design_catalog.py:get_catalog_summaries()` line 269  
**Problem:** The LLM selects a design from only 120-char summaries — loses 80% of context  
**Fix:** Increase to 300+ chars or include style category + key fonts in the selection prompt

### Bug 2: raw_spec Truncated to 2000 chars
**Location:** `design_catalog.py:parse_prompts_file()` line 241  
**Problem:** Most specs are 3000-8000 chars. Generator never sees the full spec, missing exact hex codes, animation curves, component details  
**Fix:** Increase to 5000+ chars or use the full spec

### Bug 3: HTML Designs (16, 19, 26) Not Properly Parsed
**Location:** `design_catalog.py:parse_prompts_file()` lines 200-202  
**Problem:** Parser hits `<!DOCTYPE html>` check and falls to `pass` — still extracts partial data but misses the HTML reference's visual rules  
**Fix:** Extract colors, fonts, and description from the HTML code block itself

### Bug 4: Design Selected but Spec Not Injected Into HTML Generation
**Location:** `design.py:design_synthesizer()` lines 241-246  
**Problem:** `_source_spec` gets injected into design_decisions, but `generator.py` likely builds HTML from the structured JSON, ignoring the raw spec  
**Verification needed:** Check how generator.py uses `_source_spec`

### Bug 5: Generator Probably Uses Generic HTML Templates
**Root issue:** The generator builds HTML from a section renderer, not from the actual prompts.md spec. Without reading the exact layout specs for the selected design, it defaults to generic patterns.

---

## 10. What the Fix Must Do

1. **Pass the FULL spec** to the generator — not just 2000 chars
2. **Generator must read the spec** and apply it: exact colors, exact fonts, exact layout rules
3. **Copy tone must match** the design's aesthetic category
4. **Signature components must be built** — each design has 1-3 unique components that distinguish it from generic
5. **Animations must be design-specific** — no using smooth/simple when the spec says weighted cubic-bezier

### Quick Reference for Fix Agent

When the generator receives `design_decisions` from `design_synthesizer()`:
- `design_decisions["_source_spec"]` = the raw spec text (currently truncated to 2000 chars, needs to be full)
- `design_decisions["selected_design_id"]` = the DESIGN_XX id
- `design_decisions["fonts"]` = structured font choices
- `design_decisions["colors"]` = structured hex palette
- `design_decisions["sections"]` = section list with layout type
- `design_decisions["special_components"]` = signature component names
- `design_decisions["animations"]` = animation style

The fix should:
1. **In design_catalog.py:** Remove or increase the 2000-char truncation on `raw_spec`
2. **In design.py:** Include the FULL spec text in the LLM prompt for generation (not just the selection step)
3. **In generator.py:** Use `_source_spec` and `_source_sections` and `_source_components` when building HTML
4. **In the system prompt:** Tell the HTML generator to FAITHFULLY implement the selected design spec, not make generic HTML

---

## 11. The prompts.md Spec Quality Test

To check if a generated landing page actually used prompts.md:

✅ **Used correctly if:**
- Hero text uses the specified font family (Clash Display, Anton, League Spartan, etc.)
- Background color matches the design's specified bg hex
- Signature technique is visible (echo stack, noise texture, bento grid, etc.)
- Animations use the specified cubic-bezier (not generic ease/linear)
- Copy tone matches the design category (brutalist = short punchy, luxury = refined)

❌ **Ignored if:**
- Uses Inter or Roboto fonts (banned)
- White background with blue accents (generic SaaS default)
- Generic 4-card feature grid with no special components
- "Learn More" CTAs (banned as too generic)
- Zero animation or CSS transitions

---

## Summary

`/mnt/media/prompts.md` is a **36-system design catalog** that defines the complete visual and typographic identity for every landing page the pipeline generates. Each system has a named aesthetic, precise hex palette, specific font pairing, exact animation curves, and 1-3 signature components that make it distinctive.

The current generation pipeline **doesn't properly use this file** because:
1. The parser truncates summaries to 120 chars and specs to 2000 chars
2. The HTML generator likely ignores the spec text and uses generic section renderers
3. The design selection step passes an impoverished 120-char summary to the LLM

**The fix is primarily in `design_catalog.py` (increase truncation limits) and `generator.py` (actually read and apply the selected spec).**

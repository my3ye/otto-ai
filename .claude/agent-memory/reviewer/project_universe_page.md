---
name: universe_page_audit
description: Findings from the Universe page audit at mev.otto.lk/universe (2026-03-13)
type: project
---

Universe page audit completed 2026-03-13. Key findings for reviewer memory:

**Why:** Mev asked to review and enhance everything on the Universe page one by one for public readiness.

**Page architecture:**
- Auth-gated at mev.otto.lk/universe (behind login)
- Two tabs: Projects (18 entries) and Personas (2: maitrieye/active, otto-assist/blocked)
- Grid of cards → slide-out detail sheet → natural language edit interface
- Data source: YAML files in ~/otto/universe/ served via FastAPI /universe/* endpoints

**Critical bug found:**
- ProjectCard displays `project.id.toUpperCase()` (e.g. "ASSISTIVE-TECH", "505-SYSTEMS") instead of the proper `name` field. The `name` field exists in individual YAMLs but NOT in the registry.yaml or the list API response. Fix requires: (1) add name to registry.yaml entries, (2) update frontend to use name.

**Content gaps found:**
- otto-market, otto-properties: only 43 lines each — missing marketing, roadmap, audience
- otto-music, otto-travel: thin — missing marketing, roadmap
- otto-cars, otto-billboards, shakrah, panik: partially thin — need audit
- Core projects (my3ye, otto, oneon, tusita, 505-systems, ottolabs): rich and complete

**Persona gaps:**
- Only 2 personas for 18 projects — thin
- otto-assist status "blocked" is internal ops (226 X API error) — confusing for public
- PiPi persona planned in pipi.yaml but YAML doesn't exist yet; registry has commented-out entry

**Missing UI features:**
- No category filtering (18 projects flat grid is hard to navigate)
- `next_action` field exists in YAMLs but not displayed in detail sheet
- Page header copy is flat/generic

**Public access decision needed from Mev:**
- Universe is auth-gated; "public readiness" likely means a separate public explorer URL

**8 tasks created (all pending):**
1. Fix project name display in cards (P2, $3)
2. Add category filter tabs (P3, $4)
3. Enhance page header copy + stats (P3, $3)
4. Display next_action in detail sheet (P3, $2)
5. Fix otto-assist status + create PiPi persona (P3, $4)
6. Enrich 4 thin concept projects (P3, $5)
7. Add SEO metadata for /universe route (P3, $2)
8. Audit 4 remaining concept projects (P3, $5)

**How to apply:** When reviewing any Universe-related task, check that: (1) project name uses `name` field not ID, (2) YAML enrichment preserves existing fields and only adds missing sections, (3) persona statuses are public-appropriate.

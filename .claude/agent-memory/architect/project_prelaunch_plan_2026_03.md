---
name: MY3YE Pre-Launch Architecture Plan (March 2026)
description: Comprehensive pre-launch plan covering OMS improvements, system review, phased release (0-3), 18-project readiness, and 32 implementation tasks. Commit c8dca81.
type: project
---

Pre-launch architecture document written 2026-03-19 at `~/otto/docs/prelaunch-architecture-2026-03-19.md` (527 lines). Semantic memory: `95d6a5df`. Commit: `c8dca81`.

**Why:** Mev needs full visibility into ecosystem readiness and a concrete execution plan for the MY3YE launch sprint. 18 projects, 4 capital paths, 5 Mev-dependent blockers.

**How to apply:**
- Phase 0 requires Mev action (Stripe keys, X API keys, CDP wallet secret, investor auth, DNS verification)
- Phase 1 (Week 1): 10 tasks, ~$13 budget, focused on first revenue + OMS ecosystem dashboard
- Phase 2 (Weeks 2-4): 12 tasks, ~$21 budget, capital raise activation + site content
- Phase 3 (Month 2-3): 10 tasks, ~$24.50 budget, ecosystem expansion
- Key architectural decisions: keep OMS static export (solve WebSocket at API layer), no API refactor yet, Universe data population is P1 blocker
- Critical gaps: Stripe keys (#1), broadcast credentials (#2), Universe data (#3), WebAssist ToS (#4), investor auth (#5)

## OMS New Pages Needed
- `/ecosystem` — Ecosystem Health Dashboard (needs `GET /universe/health` API endpoint in universe.py)
- `/capital` — Capital Raise Tracker (4 paths: WebAssist, KOIN, grants, VC)
- `/roadmap` — Release phase timeline

## OMS Fixes Needed
- Chat WebSocket: add `@router.websocket("/gateway/ws")` in `gateway/routes.py`
- Investor auth: move to server-side `POST /investors/auth` endpoint
- Social calendar mobile: responsive breakpoints in `social-calendar/my3ye/page.tsx` + `pipi/page.tsx`
- Sidebar: add Ecosystem, Capital, Roadmap entries to `app-sidebar.tsx`

## Architecture Decisions
- Keep OMS as static export (`output: "export"` in next.config.ts) — simpler operationally
- Solve chat WebSocket via Memory API, not by switching Next.js to server mode
- No api.py refactor until 80+ routes
- No gateway classifier refactor unless changes exceed 2/week

# OMS (Otto Management System) — Comprehensive Roadmap
*Full visibility and control for Mev. The cockpit of the civilization.*
*Last updated: 2026-03-16*

## Current Status
**LIVE** at mev.otto.lk | 10+ pages functional. Contacts, Universe, Orders, Social Calendar built.

## Dependencies
- **Hard deps:** Otto AI (API backend), Memory API (:8100)
- **Soft deps:** ONEON (SSO planned), All other projects (data sources)
- **Blocks:** Mev's ability to manage the ecosystem efficiently

---

## Phase 1 — Core Visibility (COMPLETE)
**Goal:** Mev can see everything Otto is doing.

### Completed
- [x] Dashboard with live system status
- [x] Task queue — view all tasks, statuses, outputs
- [x] Universe browser — all 15+ projects visible and editable
- [x] Contact system — contact list with conversation threading
- [x] Orders page — WebAssist order tracking
- [x] Social calendar — content planning
- [x] Hello/onboarding page
- [x] CTRL/LIVE mode tab switcher
- [x] Navigation logically grouped by product area

### Success Criteria (met)
- Mev can see system status, tasks, and projects from one URL
- No critical pages returning 404/500

---

## Phase 2 — Control Capabilities (NOW → 30 days)
**Goal:** Mev can act through OMS, not just observe.

### Milestones
1. **Task creation UI** — Mev creates Otto tasks from browser (no CLI needed)
2. **Message Mev** → **Reply from OMS** — Mev can respond to WhatsApp threads from OMS UI
3. **Whiteboard** — Excalidraw embedded for live planning
4. **Article versioning** — All articles with edit history visible
5. **Universe natural language edit** — Already partially built; polish to be reliable

### Success Criteria
- Mev can create a task without touching CLI
- Mev can respond to a WhatsApp thread from OMS
- 0 page crashes in a 24-hour session

---

## Phase 3 — Ecosystem Dashboard (30→90 days)
**Goal:** OMS becomes single pane of glass for all 15 projects.

### Milestones
1. **Revenue dashboard** — WebAssist orders, Stripe revenue, MRR trend
2. **Project health** — Each of 15 projects shows: status, next action, open blockers
3. **Broadcast management** — Post content to X/Telegram/WhatsApp from OMS
4. **Memory explorer** — Search semantic memory, see episodic timeline
5. **RL2F + system health** — Heartbeat stats, RL2F score, task completion rate

### Success Criteria
- Revenue visible in real time from OMS
- All 15 project health visible from /universe
- Mev completes ≥80% of Otto management tasks from OMS (vs CLI)

---

## Phase 4 — Team & Multi-User (6→12 months)
**Goal:** OMS can be used by a small team, not just Mev.

### Milestones
1. **ONEON SSO** — Login via ONEON identity instead of hardcoded auth
2. **Role-based access** — Admin (Mev), Operator (trusted team), Viewer
3. **Audit log** — Every action logged with who/when/what
4. **Alerts & notifications** — OMS sends mobile push when task fails, revenue drops, system alerts
5. **Multi-project workspaces** — Each Ottolabs project gets its own OMS view

### Success Criteria
- 3+ team members using OMS daily
- Zero unauthorized access incidents
- All critical Otto actions have OMS alternative to CLI

---

## Tech Stack
- **Frontend:** Next.js 15 (static export), deployed to Vercel
- **Backend:** Memory API (FastAPI :8100)
- **Repo:** `/home/web3relic/interfaces/web-next`
- **Domain:** mev.otto.lk

## Design Principles
- Ship over perfection — working beats beautiful
- OMS is Mev's tool — optimize for Mev's workflow, not general users
- LIVE mode is the future dashboard; CTRL mode is the current ops view

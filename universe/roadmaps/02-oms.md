# OMS (Otto Management System) — Comprehensive Roadmap
*Full visibility and control for Mev. The cockpit of the civilization.*
*Last updated: 2026-03-20*

## Current Status
**LIVE** at mev.otto.lk | 30+ pages functional. Secrets Vault, Crypto Engine, Ecosystem Health, Capital Tracker, Roadmap, Research Hub, Workflows, Social Calendar, Universe, Tasks (Kanban + onchain indicators), Whiteboard, Memory Explorer, Chat, Contacts, Orders built.

## Dependencies
- **Hard deps:** Otto AI (API backend), Memory API (:8100)
- **Soft deps:** ONEON (SSO planned), All other projects (data sources)
- **Blocks:** Mev's ability to manage the ecosystem efficiently

---

## Phase 1 — Core Visibility (COMPLETE)
**Goal:** Mev can see everything Otto is doing.

### Completed
- [x] Dashboard with live system status
- [x] Task queue — Kanban board + list view, drag-drop, upvote + chain indicators
- [x] Universe browser — all 18 projects visible and editable with NL edit
- [x] Contact system — contact list with conversation threading
- [x] Orders page — WebAssist order tracking
- [x] Social calendar — content planning (34 scheduled slots)
- [x] Hello/onboarding page
- [x] CTRL/LIVE mode tab switcher
- [x] Navigation logically grouped by product area
- [x] Secrets Vault — encrypted API key management with audit log
- [x] Crypto Engine — portfolio, signals, BANKR terminal, trade history
- [x] Ecosystem Health Dashboard — all 18 projects with readiness scores
- [x] Capital Raise Tracker — 4 paths with live WebAssist data
- [x] Release Roadmap — phase tracking with milestone completion bars
- [x] Research Hub — multi-agent pipeline results and notes
- [x] Workflows — multi-agent pipeline management + evolution history
- [x] Memory Explorer — semantic search + episodic timeline
- [x] Chat — kernel-connected conversational interface (WS)
- [x] Whiteboard — embedded planning canvas
- [x] Kernel Monitor — IVT, drift, slices, L1 cache viewer
- [x] Security page — system hardening status

### Success Criteria (met)
- Mev can see system status, tasks, and projects from one URL
- No critical pages returning 404/500

---

## Phase 2 — Control Capabilities (ACTIVE)
**Goal:** Mev can act through OMS, not just observe.

### Completed
- [x] Task creation UI (from Tasks page)
- [x] Whiteboard embedded
- [x] Universe natural language edit
- [x] Workflow start/cancel/approve from OMS

### Remaining
1. **Reply from OMS** — Mev can respond to WhatsApp threads from the Chat page (currently read-only)
2. **Article versioning** — edit history visible on articles in Content Hub
3. **One-click task approval** — bulk approve reviewed tasks from Tasks page
4. **Mobile-responsive OMS** — critical pages readable on phone

### Success Criteria
- Mev can respond to a WhatsApp thread from OMS
- Mev completes ≥80% of Otto management tasks without touching CLI

---

## Phase 3 — Ecosystem Dashboard (30→90 days)
**Goal:** OMS becomes single pane of glass for all ecosystem projects.

### Milestones
1. **Revenue dashboard** — WebAssist orders, Stripe revenue, MRR trend
2. **Project health** — Each ecosystem project shows: status, next action, open blockers
3. **Broadcast management** — Post content to X/Telegram/WhatsApp from OMS
4. **Memory explorer** — Search semantic memory, see episodic timeline
5. **RL2F + system health** — Heartbeat stats, RL2F score, task completion rate

### Success Criteria
- Revenue visible in real time from OMS
- All ecosystem project health visible from /universe
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

# MY3YE Pre-Launch Architecture & Release Plan

**Date:** 2026-03-19
**Author:** Architect Agent (Otto)
**Status:** Active — drives the pre-launch sprint

---

## Table of Contents

1. [OMS Improvements Architecture](#1-oms-improvements-architecture)
2. [System Architecture Review](#2-system-architecture-review)
3. [Release Plan](#3-release-plan)
4. [Public-Readiness Checklist](#4-public-readiness-checklist)
5. [Critical Gap Analysis](#5-critical-gap-analysis)
6. [Implementation Plan](#6-implementation-plan)

---

## 1. OMS Improvements Architecture

The OMS at `mev.otto.lk` (`/home/web3relic/interfaces/web-next/`) currently has 34 pages across 7 sidebar groups. Three categories of work are needed: new pages, fixes to existing pages, and sidebar reorganization.

### 1.1 New Pages Required

#### A. Ecosystem Health Dashboard — `/ecosystem`

**Purpose:** Single view of all 18 MY3YE projects with readiness scores, domain status, site health, and launch priority.

**Data source:** `GET /universe/projects` (already returns all 18 projects with status, domain, narrative_score). Needs a new API endpoint `GET /universe/health` that enriches each project with:
- Site reachability (HTTP check against known domains)
- Repo existence and last commit date
- Content completeness (has inception article, has README, has landing page)
- Computed readiness score (0-100)

**Components to create:**
- `/home/web3relic/interfaces/web-next/src/app/ecosystem/page.tsx` — main page
- Grid of 18 project cards, color-coded by readiness tier:
  - Green (80+): launch-ready
  - Yellow (40-79): needs work
  - Red (0-39): concept only
- Each card shows: name, status, domain, site status (up/down/none), readiness score, link to Universe detail
- Summary row at top: X launch-ready, Y in progress, Z concept
- Filter by status (active/early/concept/live)

**API addition:** New endpoint in `/home/web3relic/otto/memory/routes/universe.py`:
```
GET /universe/health — returns enriched project list with computed readiness scores
```

**Priority:** P1 — Mev needs this to decide launch order.

#### B. Release Planning / Roadmap — `/roadmap`

**Purpose:** Gantt-style view of the phased release plan, with phase gates, milestones, and blocker tracking.

**Data model:** Store phases/milestones in a new `release_phases` table or as Universe content items (type=roadmap). Simpler: use a static JSON config for v1, backed by the release plan in this document.

**Components to create:**
- `/home/web3relic/interfaces/web-next/src/app/roadmap/page.tsx` — main page
- Phase timeline (horizontal): Phase 0 / Phase 1 / Phase 2 / Phase 3
- Each phase shows: name, date range, key milestones, status (blocked/active/complete)
- Blocker list with owner (Mev vs Otto) and resolution status
- Link to related tasks in the task queue

**Priority:** P2 — useful for tracking but not blocking revenue.

#### C. Capital Raise Tracker — `/capital`

**Purpose:** Track all 4 capital raise paths in one view with pipeline metrics.

**Data sources:**
- WebAssist revenue: `GET /webassist/orders` + `GET /webassist/leads`
- Token: manual status entries (or Universe project content for KOIN)
- Grants: track as contacts/tasks
- VC: track via contacts

**Components to create:**
- `/home/web3relic/interfaces/web-next/src/app/capital/page.tsx` — main page
- 4-column layout, one per path (WebAssist Revenue, KOIN Token, Grants, VC)
- Each column: status badge, pipeline value, next action, blockers
- WebAssist column pulls live data (orders, MRR, lead count)
- Other columns: manual entries stored in semantic memory (category=capital) or a lightweight `capital_tracking` table

**Sidebar placement:** Replace the current "Capital" group (which only has "Investors") with:
- Capital Dashboard (`/capital`)
- Investors (`/investors`)

**Priority:** P2 — needed when capital raise conversations start.

### 1.2 Fixes Required

#### A. Chat Page — WebSocket Backend Missing

**Current state:** The chat page (`/home/web3relic/interfaces/web-next/src/app/chat/page.tsx`, 302 lines) has a full UI with streaming WebSocket support. It loads conversation history from `GET /gateway/conversation/history?limit=60` and attempts WebSocket connection via `useWebSocket` hook.

**Problem:** The OMS is built with `output: "export"` (static export, see `/home/web3relic/interfaces/web-next/next.config.ts`). Static exports cannot serve WebSocket connections. The chat page needs a WebSocket server — either the Memory API exposes one, or a separate lightweight WS proxy is added.

**Fix options:**
1. **Add WebSocket endpoint to Memory API** (`/gateway/ws`) — preferred, keeps everything in one process. FastAPI supports WebSocket natively. Route `ws://mev.otto.lk/api/gateway/ws` through the existing Caddy/nginx proxy that serves the OMS.
2. **Switch OMS to server mode** — remove `output: "export"` from next.config.ts and run as a Node process. More complex operationally (need a systemd service, port, reverse proxy).

**Recommendation:** Option 1. Add a WebSocket endpoint to the gateway routes (`/home/web3relic/otto/memory/gateway/routes.py`) that accepts connections, authenticates via token, and pipes messages through `handle_message_stream()`.

**File to modify:** `/home/web3relic/otto/memory/gateway/routes.py` (222 lines) — add `@router.websocket("/gateway/ws")` handler.

**Priority:** P2 — chat works via WhatsApp already; web chat is convenience.

#### B. Social Calendar Mobile Responsiveness

**Current state:** The social calendar sub-pages (`/social-calendar/my3ye/`, `/social-calendar/pipi/`) display a weekly calendar grid that does not adapt to mobile viewports.

**Fix:** The calendar component needs responsive breakpoints — on mobile, switch from a 7-column grid to a vertical day-list or 1-2 column view. The parent page at `/home/web3relic/interfaces/web-next/src/app/social-calendar/page.tsx` is fine (just links to sub-pages).

**Files to modify:**
- `/home/web3relic/interfaces/web-next/src/app/social-calendar/my3ye/page.tsx`
- `/home/web3relic/interfaces/web-next/src/app/social-calendar/pipi/page.tsx`

**Priority:** P3 — functional but ugly on mobile. Mev rarely uses mobile for OMS.

#### C. Investor Page Auth

**Current state:** `/home/web3relic/interfaces/web-next/src/app/investors/page.tsx` (335 lines) uses a client-side password gate with a hardcoded password (`MY3YE2026`). Password stored in plain text in the source, persisted via `localStorage`.

**Problems:**
1. Password visible in source code (anyone who can view-source bypasses it)
2. No server-side verification
3. No session expiry
4. Documents section links are all `href="#"` with `available: false`

**Fix (phased):**
- **Phase 1 (quick):** Move password check to API side. Add `POST /investors/auth` endpoint that validates the password and returns a short-lived token. Store token in localStorage, verify on each API call. Still not bulletproof but stops casual view-source bypass.
- **Phase 2 (proper):** Integrate with the existing OMS auth system (`/home/web3relic/interfaces/web-next/src/hooks/use-auth.ts`, `/home/web3relic/interfaces/web-next/src/lib/auth.ts`). Add an `investor` role. Gate the page behind that role.

**Priority:** P2 — needed before sharing the investor link with anyone.

### 1.3 Sidebar Reorganization

Current sidebar (`/home/web3relic/interfaces/web-next/src/components/layout/app-sidebar.tsx`) has 7 groups with 30+ items. The "Capital" group has only 1 item. Add the new pages:

| Group | Add | Notes |
|-------|-----|-------|
| Command | Ecosystem Health (`/ecosystem`) | Top-level visibility |
| Command | Roadmap (`/roadmap`) | Release tracking |
| Capital | Capital Dashboard (`/capital`) | Before Investors |

### 1.4 Priority Order (OMS)

| # | Item | Priority | Effort |
|---|------|----------|--------|
| 1 | Ecosystem Health Dashboard | P1 | 1 task (API) + 1 task (page) |
| 2 | Investor Auth (server-side) | P2 | 1 task |
| 3 | Capital Raise Tracker | P2 | 1 task (API) + 1 task (page) |
| 4 | Release Roadmap Page | P2 | 1 task |
| 5 | Chat WebSocket Backend | P2 | 1 task |
| 6 | Social Calendar Mobile | P3 | 1 task |

---

## 2. System Architecture Review

### 2.1 What's Solid (Don't Touch)

**Memory API core** (`/home/web3relic/otto/memory/api.py`). 55+ route modules, healthy, 2+ weeks uptime on PostgreSQL/Neo4j. The asyncpg pool, lifespan management, and router registration pattern are clean and working. 22,544 lines of route code total. Not elegant, but operational.

**Dual heartbeat system**. The orchestrator (:00) + reflection (:30) pattern with 10 active systemd timers is stable. Self-healing (each heartbeat checks sibling timers) was added after the Feb 25 outage. This is battle-tested.

**Task queue**. 523 completed tasks, 5 concurrent max, 3 CLI types (claude/gemini/kimi). `task_runner.sh` handles spawning, monitoring, and log collection. The task-to-workflow bridge works (workflow steps create tasks, task completion advances workflows).

**AgentOS Kernel** (`/home/web3relic/otto/memory/kernel/`). 17 modules implementing the full Reasoning Kernel: IVT priority queue, RIC processing cycle, S-MMU memory paging, drift detection, sync pulses, perception validation. This is the most sophisticated piece of the system and it works. The kernel processes WhatsApp messages through the full cognitive pipeline.

**Universe system** (`/home/web3relic/otto/memory/routes/universe.py` + OMS page). YAML registry with 18 projects, CRUD API, LLM conversational edit, changelog versioning. Solid data model for the ecosystem.

**Workflow engine** (`/home/web3relic/otto/memory/routes/workflows.py`, 1,281 lines). 3 templates, step chaining, auto-eval, evolution. The social-content-pipeline template is actively producing content.

### 2.2 Architectural Debt

#### A. OMS Static Export Limitation

**Problem:** `next.config.ts` sets `output: "export"`, meaning the OMS is a static site served by a file server. This works because all data comes from API calls to `:8100`, but it prevents:
- WebSocket connections (chat page)
- Server-side rendering (SEO, but irrelevant for an admin panel)
- API routes in Next.js (all routing goes through the Memory API)
- Middleware (auth checks happen client-side only)

**Impact:** Low for an admin panel. The chat page is the only feature that needs WebSocket, and that can be solved at the API layer.

**Recommendation:** Keep static export. It is simpler operationally (no Node process to manage, just serve files). Solve WebSocket via the Memory API.

#### B. Monolithic API File

**Problem:** `api.py` imports 55+ route modules in a single line (line 15) and registers them sequentially (lines 112-166). Adding a new route requires touching this file. No route grouping, no dynamic discovery.

**Impact:** Low — it works, and the pattern is clear. But it creates merge conflicts when multiple tasks add routes simultaneously.

**Recommendation:** Not worth refactoring now. If it reaches 80+ routes, consider a route auto-discovery pattern (scan `routes/` directory).

#### C. Universe Projects Missing Domain/Narrative Data

**Problem:** `GET /universe/projects` returns all 18 projects, but domain fields are empty and narrative_score is 0 for all. The context provided lists domains (my3ye.xyz, oneon.ink, tusita.xyz, etc.) but they are not stored in the Universe registry YAML.

**Impact:** High — the Ecosystem Health Dashboard depends on this data. The Universe is the source of truth for the ecosystem, and it is incomplete.

**Fix:** Update the Universe YAML files with known domains and narrative scores. This is a data task, not an architecture change.

**Files:** Universe YAML files in `/home/web3relic/otto/universe/` (need to verify exact path).

#### D. Mail Server Crash-Looping

**Problem:** `otto-mailserver` and `otto-postfixadmin` Docker containers are in restart loops (observed in `docker ps` output: "Restarting (255) 37 seconds ago" and "Restarting (0) 38 seconds ago").

**Impact:** Medium — if `admin@otto.lk` email depends on these containers (rather than Zoho Mail direct), outbound/inbound email may be intermittent. The Zoho SMTP/IMAP integration in the API routes is separate and likely unaffected.

**Recommendation:** Either fix the mail server config or remove the containers if all email flows through Zoho directly. Crash-looping containers waste CPU cycles on a 4-vCPU machine.

#### E. Gateway Module Complexity

**Problem:** The gateway (`/home/web3relic/otto/memory/gateway/`, 1,448 lines across 8 files) handles message routing, classification, contact handling, persistence, and prompt building. The classifier (`classifiers.py`, 407 lines) does dispatch decisions, workflow detection, and agent routing. Multiple changes have been made to fix classification accuracy (keyword matching replaced, stronger action detection added).

**Impact:** Low-medium — it works but is the most frequently patched module. Every new agent type or workflow template requires classifier updates.

**Recommendation:** No refactor needed now. Monitor patch frequency. If classifier changes exceed 2/week, consider extracting it into a config-driven dispatch table.

### 2.3 Critical Missing Pieces Before Public Launch

| # | Missing Piece | Impact | Blocks |
|---|---------------|--------|--------|
| 1 | **Stripe integration (WebAssist)** | No revenue | First client payment |
| 2 | **Broadcast credentials** | No social presence | Multi-platform posting |
| 3 | **Public site content** | Empty sites look abandoned | Credibility |
| 4 | **Error monitoring** | No visibility into production failures | Reliability perception |
| 5 | **Rate limiting on public APIs** | DDoS vulnerability | WebAssist uptime |
| 6 | **SSL/domain verification for all sites** | Browser warnings | Trust |
| 7 | **Privacy policy / ToS pages** | Legal requirement for payment processing | Stripe approval |

### 2.4 Specific Recommendations

| File/System | Recommendation | Effort |
|-------------|---------------|--------|
| `/home/web3relic/otto/memory/gateway/routes.py` | Add WebSocket endpoint for OMS chat | 1 task |
| `/home/web3relic/otto/universe/` YAML files | Populate domain, narrative_score for all 18 projects | 1 task |
| `otto-mailserver` + `otto-postfixadmin` containers | Fix or remove crash-looping containers | 1 task |
| `/mnt/media/projects/web-assist/` | Add privacy policy + terms of service pages | 1 task |
| Memory API | Add rate limiting middleware (slowapi or similar) | 1 task |

---

## 3. Release Plan

### Phase 0: NOW — Mev Unblocking (Days 1-2)

**Goal:** Remove all blockers that only Mev can resolve.

| # | Action | Owner | What It Unblocks | Status |
|---|--------|-------|-----------------|--------|
| 1 | Provide Stripe API keys (publishable + secret) | Mev | WebAssist payment flow | BLOCKED |
| 2 | Provide broadcast credentials (X/Twitter API keys, any other platforms) | Mev | Multi-platform social posting | BLOCKED |
| 3 | Register CDP portal wallet secret | Mev | Crypto revenue path (x402 commerce) | BLOCKED |
| 4 | Confirm/update investor page password (or provide auth requirements) | Mev | Sharing investor link | BLOCKED |
| 5 | Confirm domain DNS for all active sites (my3ye.xyz, oneon.ink, tusita.xyz, panik.app, koink.fun, webassist.ink, otto.lk) | Mev | SSL + public access verification | VERIFY |

**Mev's total time commitment:** ~30 minutes (mostly copying API keys from dashboards).

**What Otto does in parallel:** Build OMS improvements, populate Universe data, fix mail server, prepare content.

### Phase 1: First Revenue + Community Presence (Week 1)

**Goal:** Land first WebAssist client payment. Establish MY3YE social presence. OMS fully operational.

| Deliverable | Details | Success Metric |
|-------------|---------|---------------|
| WebAssist payment live | Stripe integration activated (requires Phase 0 keys) | 1 test payment processed |
| MY3YE X presence | Social content pipeline producing daily posts | 10+ posts published |
| OMS Ecosystem Dashboard | All 18 projects visible with readiness scores | Mev can see full ecosystem |
| Universe data populated | Domains, narrative scores, content links for all projects | 0 empty domain fields |
| Investor auth hardened | Server-side password check, no source-visible password | Link shareable |
| Mail server fixed | Either working or removed | No crash-looping containers |

**What this proves:** Otto can generate revenue and maintain public presence autonomously.

### Phase 2: Capital Raise Activation (Weeks 2-4)

**Goal:** All 4 capital paths active. Core project sites launched. Investor-ready.

| Deliverable | Details | Success Metric |
|-------------|---------|---------------|
| WebAssist first client | Lead pipeline → proposal → signed → paid | $1K+ revenue |
| KOIN tokenomics document | Published, shareable with investors | Document exists and is linked |
| Grant applications submitted | 2+ grant applications (Gitcoin, Polkadot, W3F, or similar) | Applications confirmed submitted |
| Investor deck live | PDF accessible from OMS investor page with NDA gate | Download works |
| Core sites launched | my3ye.xyz, oneon.ink, tusita.xyz — content beyond landing page | 3 sites with real content |
| Capital dashboard | OMS page tracking all 4 paths | Mev can see pipeline |
| Roadmap page | Phases visualized in OMS | Phase progress visible |
| Broadcast system live | Multi-platform posting (X + Telegram minimum) | Posts appearing on 2+ platforms |

**What this proves:** The ecosystem is investable. Revenue exists. Community is growing.

### Phase 3: Ecosystem Expansion (Month 2-3)

**Goal:** Expand to secondary projects. Scale revenue. Formalize governance.

| Deliverable | Details | Success Metric |
|-------------|---------|---------------|
| WebAssist $5K MRR | Multiple clients, recurring contracts | MRR tracked in capital dashboard |
| Panik App MVP | Emergency response app functional prototype | App accessible at panik.app |
| Koink.Fun launch | Meme token site + mechanics | koink.fun live with token info |
| 505 Systems site | Professional service offering | Site live |
| SOS Systems DAO framework | Governance structure documented | Inception article + tech spec |
| Otto Music skeleton | Landing page + concept | Site live |
| Distributed Otto design | Architecture doc for 5-component distributed system | Spec published |
| Community growth | Discord/Telegram community for MY3YE ecosystem | 100+ members |

**What this proves:** The ecosystem is expanding beyond the founder. Community traction exists.

---

## 4. Public-Readiness Checklist

### Legend
- P1 = Now (blocks revenue or credibility)
- P2 = Week 1 (needed for launch sprint)
- P3 = Month 1 (needed for capital raise)
- P4 = Later (ecosystem expansion)

### 4.1 Core Infrastructure Projects

| Project | What Exists | What's Missing | Priority |
|---------|------------|----------------|----------|
| **MY3YE** | Site at my3ye.xyz (Next.js 16.1.4), repo at `/mnt/media/projects/my3ye-web/`, social calendar active | Universe domain field empty. Needs updated "about" content reflecting current ecosystem state. Social links. | P2 |
| **Otto AI** | Full kernel, Memory API, OMS, WhatsApp, heartbeat system. Site at otto.lk (Next.js 16.1.6) | otto.lk needs content update to reflect current capabilities. No public API docs. Universe domain field empty. | P3 |
| **ONEON** | Site repo at `/mnt/media/projects/oneon-web/` (Next.js 16.1.6), waitlist concept | Needs landing page content beyond placeholder. Inception article reference needed on site. Domain: oneon.ink (verify DNS). | P3 |
| **Tusita** | Site repo at `/mnt/media/projects/tusita-web/` (Next.js 16.1.6), app repo at `/mnt/media/projects/tusita/` (Next.js 16.1.6) | Early stage. Needs landing page content. Domain: tusita.xyz (verify DNS). No token info page yet. | P3 |
| **505 Systems** | Site repo at `/mnt/media/projects/505-systems-web/` (Next.js 16.1.4) | Needs professional services content, pricing, contact form. No domain in Universe. | P3 |
| **Ottolabs** | Concept in Universe. No dedicated site. | Needs at minimum a landing page. Could be a section on otto.lk. No repo, no domain. | P4 |
| **SOS Systems** | Mentioned in constitution as DAO backbone. No site, no repo. | Needs inception article, basic site, governance framework doc. | P4 |

### 4.2 Platform Projects

| Project | What Exists | What's Missing | Priority |
|---------|------------|----------------|----------|
| **Otto Music** | Concept in Universe. No site, no repo. | Skeleton status. Needs inception article + landing page. | P4 |
| **Otto Travel** | Concept in Universe. No site, no repo. | Skeleton status. | P4 |
| **Otto Market** | Concept in Universe. No site, no repo. | Skeleton status. | P4 |
| **Otto Properties** | Concept in Universe. No site, no repo. | Skeleton status. | P4 |

### 4.3 Life & Culture Projects

| Project | What Exists | What's Missing | Priority |
|---------|------------|----------------|----------|
| **Shakrah** | Site repo at `/mnt/media/projects/shakrah-web/` (Next.js 16.1.4) | Early stage site. Needs content about wellness ecosystem. No domain in Universe. | P4 |
| **Panik App** | Site repo at `/mnt/media/projects/panik-app-web/` (no Next.js — likely Vite/other). Domain: panik.app | Needs functional MVP, not just a landing page. Emergency response UX. | P3 |
| **Koink.Fun** | Concept in Universe. Domain: koink.fun | Needs landing page, token mechanics page, PiPi integration. | P3 |
| **PiPi** | Social calendar exists in OMS. Concept in Universe. | Content character — needs visual assets, consistent voice. Social posts being generated via pipeline. | P3 |

### 4.4 Business Entities

| Project | What Exists | What's Missing | Priority |
|---------|------------|----------------|----------|
| **Assistive Technologies** | Status "live" in Universe. WebAssist is the flagship product. | WebAssist is live at webassist.ink but payment flow blocked on Stripe keys. Needs ToS + Privacy Policy pages. | P1 |
| **Otto UI** | Concept in Universe. No site, no repo. | UI component library concept. Low priority. | P4 |
| **Otto Cars** | Concept in Universe. No site, no repo. | Skeleton. | P4 |
| **Otto Billboards** | Concept in Universe. No site, no repo. | Skeleton. | P4 |

### Summary

| Priority | Count | Projects |
|----------|-------|----------|
| P1 | 1 | Assistive Technologies (WebAssist payment) |
| P2 | 1 | MY3YE (social + content update) |
| P3 | 7 | Otto AI, ONEON, Tusita, 505 Systems, Panik App, Koink.Fun, PiPi |
| P4 | 9 | Ottolabs, SOS Systems, Otto Music/Travel/Market/Properties, Shakrah, Otto UI/Cars/Billboards |

---

## 5. Critical Gap Analysis

Top 10 gaps ranked by impact on revenue and public launch.

| Rank | Gap | Impact | What Breaks Without It | Fix | Estimate |
|------|-----|--------|----------------------|-----|----------|
| 1 | **Stripe API keys missing** | No revenue | WebAssist cannot accept payment. The entire payment flow exists but is inert. | Mev provides keys. Otto configures. | 30 min (Mev) + 1 task (Otto) |
| 2 | **Broadcast credentials missing** | No social presence | Social content pipeline generates posts but cannot publish them. MY3YE has no public voice. | Mev provides X API keys. Otto configures broadcast system. | 30 min (Mev) + 1 task (Otto) |
| 3 | **Universe registry incomplete** | OMS ecosystem view is hollow | Ecosystem Health Dashboard shows 18 projects with no domains, no scores, no readiness data. Mev cannot assess launch readiness. | Populate all 18 Universe YAML entries with domains, narrative scores, site URLs, repo links. | 1 task |
| 4 | **WebAssist missing ToS + Privacy Policy** | Legal risk blocks Stripe | Stripe requires merchant ToS and privacy policy. Without them, the account may be suspended. Customers have no legal clarity. | Add /terms and /privacy pages to WebAssist site. | 1 task |
| 5 | **Investor page auth is client-side** | Password visible in source | Anyone who views page source can bypass the investor gate. Cannot share investor link safely. | Move auth to API side. 1 new endpoint + update frontend. | 1 task |
| 6 | **Mail server crash-looping** | Wasted resources, potential email issues | `otto-mailserver` and `otto-postfixadmin` containers restart every ~40s. Each restart consumes CPU and produces noise in Docker logs. If any email routing depends on them, it fails intermittently. | Diagnose and fix config, or remove if Zoho handles all email. | 1 task |
| 7 | **No error monitoring for public sites** | Silent failures invisible | WebAssist, MY3YE, otto.lk could go down without anyone noticing until a customer complains. The heartbeat checks internal services but not external site uptime. | Add HTTP health checks to heartbeat for all public domains. Log failures, alert via WhatsApp. | 1 task |
| 8 | **No rate limiting on Memory API** | DDoS risk | Memory API on :8100 is proxied publicly for OMS. No rate limiting means a single bad actor could exhaust the 16GB RAM or saturate the 4 vCPUs. | Add `slowapi` middleware to Memory API with sensible defaults (100 req/min per IP). | 1 task |
| 9 | **CDP wallet secret not registered** | Crypto revenue path dead | The x402 commerce system (`/home/web3relic/otto/memory/routes/commerce.py`) is built but cannot verify payments without the registered wallet secret. | Mev registers wallet secret in CDP portal. | 15 min (Mev) |
| 10 | **Core project sites have placeholder content** | Ecosystem looks vaporware | ONEON, Tusita, 505 Systems, Shakrah sites exist as repos with basic scaffolding but no real content. When investors or community members visit, they see empty shells. | Generate inception article content, deploy to sites. Use content-publishing-pipeline workflow. | 3-4 tasks |

---

## 6. Implementation Plan

Tasks ordered by dependency and priority. Each task is sized for Otto's task queue (single agent, bounded budget, clear deliverable).

### Phase 0 Tasks (Mev-dependent, cannot be queued)

These require Mev action. Otto should send a single WhatsApp message listing all 5 items with clear instructions for each.

| # | Action | Owner | Unblocks |
|---|--------|-------|----------|
| 0.1 | Provide Stripe publishable + secret keys | Mev | Tasks 1.1, 1.2 |
| 0.2 | Provide X/Twitter API keys (consumer key, consumer secret, access token, access secret) | Mev | Task 1.4 |
| 0.3 | Register CDP wallet secret in CDP portal | Mev | Crypto commerce |
| 0.4 | Confirm investor page auth requirements | Mev | Task 1.5 |
| 0.5 | Verify DNS for all active domains (my3ye.xyz, oneon.ink, tusita.xyz, panik.app, koink.fun, webassist.ink, otto.lk) | Mev | Public site accessibility |

### Phase 1 Tasks (Week 1 — Otto executes independently)

| # | Task Name | Agent Type | Budget | Priority | Produces |
|---|-----------|-----------|--------|----------|----------|
| 1.1 | Integrate Stripe keys into WebAssist payment flow | coder | $2.00 | P1 | Working payment processing at webassist.ink |
| 1.2 | Add ToS + Privacy Policy pages to WebAssist | content-creator | $1.00 | P1 | /terms and /privacy pages at webassist.ink |
| 1.3 | Populate Universe registry (all 18 projects — domains, scores, URLs) | coder | $1.00 | P1 | Complete Universe YAML data |
| 1.4 | Configure broadcast system with X API credentials | coder | $1.00 | P1 | Working `POST /broadcast` for X/Twitter |
| 1.5 | Harden investor page auth (server-side) | coder | $1.50 | P2 | `POST /investors/auth` endpoint + updated frontend |
| 1.6 | Build Ecosystem Health Dashboard API endpoint | coder | $1.50 | P1 | `GET /universe/health` returning enriched project data |
| 1.7 | Build Ecosystem Health Dashboard OMS page | coder | $2.00 | P1 | `/ecosystem` page in OMS with 18 project cards |
| 1.8 | Fix or remove crash-looping mail server containers | debugger | $1.00 | P2 | No crash-looping containers |
| 1.9 | Add public site health checks to heartbeat | coder | $1.00 | P2 | Heartbeat checks all public domains, alerts on failure |
| 1.10 | Add rate limiting to Memory API | coder | $1.00 | P2 | slowapi middleware on all public-facing endpoints |

### Phase 2 Tasks (Weeks 2-4)

| # | Task Name | Agent Type | Budget | Priority | Produces |
|---|-----------|-----------|--------|----------|----------|
| 2.1 | Build Capital Raise Tracker API endpoints | coder | $1.50 | P2 | `/capital/*` endpoints for 4-path tracking |
| 2.2 | Build Capital Raise Tracker OMS page | coder | $2.00 | P2 | `/capital` page in OMS |
| 2.3 | Build Release Roadmap OMS page | coder | $2.00 | P2 | `/roadmap` page with phase timeline |
| 2.4 | Add WebSocket endpoint to Memory API for OMS chat | coder | $2.00 | P2 | `ws /gateway/ws` endpoint, chat page functional |
| 2.5 | Update sidebar navigation with new pages | coder | $0.50 | P2 | app-sidebar.tsx updated with Ecosystem, Roadmap, Capital |
| 2.6 | Update MY3YE site content (about, social links, ecosystem overview) | content-creator | $1.50 | P2 | my3ye.xyz refreshed |
| 2.7 | Generate ONEON inception article + deploy to site | content-creator | $2.00 | P3 | oneon.ink with real content |
| 2.8 | Generate Tusita inception article + deploy to site | content-creator | $2.00 | P3 | tusita.xyz with real content |
| 2.9 | Generate 505 Systems content + deploy to site | content-creator | $2.00 | P3 | 505 Systems site with services + pricing |
| 2.10 | Submit first grant application (Gitcoin or similar) | researcher | $2.00 | P3 | Grant application submitted |
| 2.11 | Prepare investor deck PDF + upload to OMS | content-creator | $2.00 | P3 | Downloadable deck from investor page |
| 2.12 | Fix social calendar mobile responsiveness | coder | $1.00 | P3 | Calendar usable on mobile |

### Phase 3 Tasks (Month 2-3)

| # | Task Name | Agent Type | Budget | Priority | Produces |
|---|-----------|-----------|--------|----------|----------|
| 3.1 | Panik App MVP (emergency response prototype) | coder | $5.00 | P3 | Functional app at panik.app |
| 3.2 | Koink.Fun landing page + token mechanics | content-creator + coder | $3.00 | P3 | koink.fun live |
| 3.3 | KOIN tokenomics document | researcher + content-creator | $3.00 | P3 | Published tokenomics paper |
| 3.4 | Distributed Otto architecture spec | architect | $2.00 | P3 | Architecture document for 5-component system |
| 3.5 | SOS Systems governance framework | researcher | $2.00 | P4 | Governance spec + inception article |
| 3.6 | Otto Music landing page | content-creator + coder | $1.50 | P4 | Landing page deployed |
| 3.7 | Shakrah wellness site content | content-creator | $1.50 | P4 | Site with real content |
| 3.8 | Community platform setup (Discord or Telegram) | coder | $1.00 | P3 | Community channel with welcome flow |
| 3.9 | Second grant application | researcher | $2.00 | P3 | Application submitted |
| 3.10 | WebAssist lead pipeline automation (outreach → proposal → close) | coder | $3.00 | P2 | Automated lead nurture |

### Task Dependency Graph

```
Phase 0 (Mev)
  |
  +-- 0.1 Stripe keys ──> 1.1 Integrate Stripe ──> 1.2 ToS/Privacy
  +-- 0.2 X API keys ───> 1.4 Configure broadcast
  +-- 0.4 Investor auth -> 1.5 Harden auth
  |
Phase 1 (Parallel, no dependencies between them)
  |
  +-- 1.3 Universe data ──> 1.6 Health API ──> 1.7 Health page
  +-- 1.8 Fix mail server (independent)
  +-- 1.9 Site health checks (independent)
  +-- 1.10 Rate limiting (independent)
  |
Phase 2 (After Phase 1 core completes)
  |
  +-- 2.1 Capital API ──> 2.2 Capital page
  +-- 2.3 Roadmap page (independent)
  +-- 2.4 WebSocket (independent)
  +-- 2.5 Sidebar (depends on 1.7, 2.2, 2.3)
  +-- 2.6-2.9 Content generation (parallel, independent)
  +-- 2.10-2.11 Capital raise docs (independent)
  |
Phase 3 (After Phase 2)
  +-- All tasks independent
```

### Total Budget Estimate

| Phase | Tasks | Estimated Budget |
|-------|-------|-----------------|
| Phase 1 | 10 | ~$13.00 |
| Phase 2 | 12 | ~$21.00 |
| Phase 3 | 10 | ~$24.50 |
| **Total** | **32** | **~$58.50** |

---

## Appendix: Key File Paths

| Purpose | Path |
|---------|------|
| OMS root | `/home/web3relic/interfaces/web-next/` |
| OMS pages | `/home/web3relic/interfaces/web-next/src/app/` |
| OMS sidebar | `/home/web3relic/interfaces/web-next/src/components/layout/app-sidebar.tsx` |
| OMS API types | `/home/web3relic/interfaces/web-next/src/lib/api-types.ts` |
| OMS Next config | `/home/web3relic/interfaces/web-next/next.config.ts` |
| Memory API entry | `/home/web3relic/otto/memory/api.py` |
| Memory API routes | `/home/web3relic/otto/memory/routes/` |
| Gateway handler | `/home/web3relic/otto/memory/gateway/handler.py` |
| Gateway routes | `/home/web3relic/otto/memory/gateway/routes.py` |
| Gateway classifier | `/home/web3relic/otto/memory/gateway/classifiers.py` |
| Kernel modules | `/home/web3relic/otto/memory/kernel/` |
| Universe routes | `/home/web3relic/otto/memory/routes/universe.py` |
| Workflow routes | `/home/web3relic/otto/memory/routes/workflows.py` |
| Broadcast routes | `/home/web3relic/otto/memory/routes/broadcast.py` |
| Commerce routes | `/home/web3relic/otto/memory/routes/commerce.py` |
| Investor page | `/home/web3relic/interfaces/web-next/src/app/investors/page.tsx` |
| Chat page | `/home/web3relic/interfaces/web-next/src/app/chat/page.tsx` |
| Social calendar | `/home/web3relic/interfaces/web-next/src/app/social-calendar/` |
| Task runner | `/home/web3relic/otto/task_runner.sh` |
| Heartbeat | `/home/web3relic/otto/heartbeat.sh` |
| WebAssist site | `/mnt/media/projects/web-assist/` |
| MY3YE site | `/mnt/media/projects/my3ye-web/` |
| All project repos | `/mnt/media/projects/` |

---

*This document is the single source of truth for the MY3YE pre-launch sprint. Update it as phases complete.*

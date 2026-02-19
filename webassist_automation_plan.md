# WebAssist — Automation Architecture Plan

**Status:** Draft — Prepared by Otto, 2026-02-19
**Purpose:** Map the full WebAssist pipeline from lead → delivery, identify what can be automated, and define what Otto needs from Mev to proceed.

---

## Current State (What's Built)

| Component | Status | Notes |
|---|---|---|
| Lead scraper (Google Places API) | ✅ Running | 2,447 leads, hourly scrape, scored |
| Outreach message generator | ✅ Built | Gemini-powered, personalized WA messages |
| Outreach queue + approval gate | ✅ Built | 80 messages pending Mev go-ahead |
| Intake form | ✅ Live | otto.505.systems/start (4-step flow) |
| Intake API + WA notification | ✅ Built | POST /intake → WA alert to Otto |
| Outreach sender script | ✅ Built | Rate-limited WA blast tool |
| Sample site builder | ✅ Built | Awwwards-style, per-lead, via Claude Code |
| Review hub | ✅ Live | otto.505.systems/review/ |

---

## Full Pipeline Vision

```
[1] DISCOVERY → [2] OUTREACH → [3] INTAKE → [4] BUILD → [5] DELIVERY → [6] PAYMENT
```

### Step 1: Discovery (AUTOMATED ✅)
- Google Places API scraper → scored lead DB
- Runs hourly, dedups by place_id
- Scores: no-website (85+) > revamp (65+) > strong-web (40)

### Step 2: Outreach (SEMI-AUTOMATED, BLOCKED)
- Gemini generates personalized WA messages per lead
- Otto queues them, Mev approves batch
- **Blocked:** Need Mev approval + dedicated WebAssist WA number
- **Target:** Send 20-50 outreach/day, track response rate

### Step 3: Intake (AUTOMATED ✅, needs testing)
- Client submits intake form at /start
- Otto gets WA notification immediately
- **Gap:** No auto-follow-up, no slot booking, no consultation scheduling

### Step 4: Build (MANUAL → TARGET: SEMI-AUTOMATED)
- **Today:** Mev builds manually on local machine
- **Target:** Otto spins up Claude Code task → builds site in detached terminal
- Inputs needed: intake form data + any brand assets from client
- **Key questions for Mev:**
  - What's your build stack? (HTML/CSS/JS? Webflow? WordPress?)
  - What does the client delivery look like? (Staging URL, zip, hosted?)
  - What's the review/feedback loop with the client?

### Step 5: Delivery (UNKNOWN — need Mev's local workflow)
- **Questions:**
  - Do you hand over source files or host it?
  - How does the client pay? (Bank transfer, Stripe, crypto?)
  - What happens post-launch? (Maintenance retainer? One-shot?)
  - Who does client comms — Mev directly, or Otto via WA?

### Step 6: Payment (UNKNOWN)
- No payment infra built yet
- Options: Stripe, PayHere (LK), bank transfer
- **Recommendation:** Start with manual bank transfer for MVP, build PayHere integration later

---

## Automation Roadmap

### Phase 1 (This Week — If Blocked Items Resolve)
- [ ] Mev approves outreach batch → send 80 messages
- [ ] Set up dedicated WebAssist WA number
- [ ] Route client WA replies to intake form / Otto notification
- [ ] Auto-book consultation slot (Calendly or custom)

### Phase 2 (Next 2 Weeks)
- [ ] Otto auto-builds draft site from intake form data
- [ ] Staging URL generated automatically → sent to client for review
- [ ] Feedback loop via WA → revision requests queued
- [ ] Payment link generated on approval

### Phase 3 (Month 2)
- [ ] Full pipeline automated end-to-end for "standard" sites
- [ ] Mev only reviews quality, edge cases, and high-touch clients
- [ ] Metrics dashboard: leads → outreach → intake → build → delivered → paid

---

## What Otto Needs From Mev (Priority Order)

1. **Go-ahead to send outreach** — 80 messages ready now, 750+ more can be queued
2. **WebAssist WA number** — dedicated line so clients reach WebAssist, not Ottolabs
3. **Local workflow handoff** — screencast or walkthrough of steps 3-5
4. **Build stack clarity** — what tools, hosting, file format for delivery
5. **Assistive Tech domain** — webassist.otto.lk or dedicated domain for public-facing site

---

## Sample Site Strategy

Currently: 9 bespoke client demos live at otto.505.systems/review/
- These are for Mev's review, not client-facing

**Proposed: Per-lead sample sites as outreach closer**
- When a lead replies to outreach with interest, auto-build a mock of their site
- Send them the link: "Here's what your site could look like — free mockup"
- Dramatically increases conversion (tangible value before they pay)
- Otto can do this autonomously via task queue + Claude Code

---

## Metrics to Track (Once Running)

| Metric | Target | Current |
|---|---|---|
| Leads scraped | 500+/week | ~700/week |
| Outreach sent | 50/day | 0 (blocked) |
| Reply rate | 10-20% | N/A |
| Intake conversions | 5-10% of replies | N/A |
| Site builds per week | 3-5 | 0 |
| Revenue | LKR 100k+/mo | 0 |

---

*Otto's take: The pipeline is 70% built. The main bottleneck is Mev's approval to start sending + the local workflow handoff. Once unblocked, Otto can run this autonomously with Mev reviewing only exceptions.*

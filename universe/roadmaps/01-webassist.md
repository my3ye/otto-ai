# WebAssist — Comprehensive Roadmap
*Web services for startups and SMBs. First revenue product.*
*Last updated: 2026-03-16*

## Current Status
**LIVE** at webassist.ink | Status: Mev-blocked on payments (bank/Wise/Stripe)

## Dependencies
- **Hard deps:** None (standalone product)
- **Soft deps:** Otto AI (for quality improvement), OMS (admin visibility)
- **Blocks:** First revenue → funds all other projects

---

## Phase 1 — Revenue Activation (NOW → 30 days)
**Goal:** First paying customer. Money in the bank.

### Milestones
1. **Stripe/Wise activated** — Payment processor live, accepting cards or bank transfer
2. **First paid order** — Customer pays through webassist.ink, money lands in account
3. **Order → delivery workflow** — Manual-to-automated: client submits, Otto gets notified, delivery tracked
4. **Invoice system** — Automated invoice generation and delivery
5. **Confirmation emails** — Customer flow: submit → confirm → update → deliver

### Success Criteria
- ≥1 paying customer
- ≥$500 first month revenue
- Delivery cycle ≤5 business days for WebAssist (website build)
- Zero failed payments due to missing infrastructure

### Key Actions (Mev must unblock)
- [ ] Activate Wise or Stripe account
- [ ] Set Supabase env vars for payment webhook
- [ ] Configure payment webhook endpoint

### Blockers
- **Bank/Wise/Stripe** — Mev action required to activate payment processing

---

## Phase 2 — Product Quality & Automation (30→90 days)
**Goal:** Repeatable delivery. 10+ customers/month.

### Milestones
1. **Otto AI integration** — Otto reviews briefs, drafts project scopes, flags ambiguity before delivery starts
2. **Template library** — 5 proven site templates across industries (SaaS, local business, restaurant, agency, portfolio)
3. **Client portal** — Customers can check order status, upload assets, approve drafts
4. **QA automation** — Otto runs automated checks on deliverables (accessibility, performance, mobile)
5. **Testimonials + case studies** — First 3 case studies live on webassist.ink

### Success Criteria
- ≥10 active orders/month
- Customer satisfaction score ≥4.5/5
- Average delivery time ≤3 business days
- Repeat customer rate ≥30%

---

## Phase 3 — Service Expansion (90 days → 6 months)
**Goal:** Full Ottolabs service suite live. $5K MRR.

### Milestones
1. **App Assist launched** — Mobile app design/development service
2. **Brand Assist launched** — Branding, identity, logo service
3. **Tech Assist launched** — Business ops automation service
4. **Service bundles** — WebAssist + Brand Assist package pricing
5. **Referral program** — Clients refer clients, earn credit

### Success Criteria
- All 4 services live with real customers
- $5,000 MRR
- Net Promoter Score ≥50

---

## Phase 4 — Platform & Scale (6→12 months)
**Goal:** Semi-autonomous service delivery. $20K MRR.

### Milestones
1. **Otto-assisted delivery** — Otto handles 80% of routine build tasks autonomously
2. **Self-serve tier** — Customers can configure and purchase lower-tier packages without sales interaction
3. **Agency API** — White-label WebAssist for other agencies
4. **OMS integration** — Full Mev visibility from OMS: revenue, pipeline, delivery status
5. **International expansion** — Pricing localized. Accepting customers from 5+ countries.

### Success Criteria
- $20,000 MRR
- Delivery cost per project down 60% from Phase 1
- ≥3 white-label agency partners

---

## Revenue Targets

| Phase | Timeline | MRR Target |
|-------|----------|------------|
| Phase 1 | Now → 30d | $500 |
| Phase 2 | 30→90d | $2,000 |
| Phase 3 | 90d→6mo | $5,000 |
| Phase 4 | 6→12mo | $20,000 |

## Risk Factors
- Payment processing delays (Mev dependency — single largest blocker)
- Delivery quality consistency at scale
- Competition from Webflow, Squarespace DIY

## Notes
- webassist.ink is the client front end — leave untouched
- All admin functionality goes into OMS (mev.otto.lk)
- App Assist, Brand Assist, Tech Assist are future sub-brands under the Ottolabs services umbrella

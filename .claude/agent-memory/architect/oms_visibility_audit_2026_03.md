---
name: oms_visibility_audit_2026_03
description: OMS visibility gap audit findings and implementation plan (March 2026)
type: project
---

Audit of OMS display surfaces vs Otto-generated artifacts (2026-03-20).

**Why:** Mev needs to see all Otto work in OMS. Multiple artifacts were invisible.

**4 gaps found:**
1. `outreach_queue`: 2273 pending messages, API exists, NO OMS page → build `/webassist/outreach`
2. Grant drafts in `content` table (type=research/plan): 6 docs, Content Hub shows them but needs grant filter
3. Project roadmaps: 18 entries in `content` (type=roadmap), `/roadmap` page shows static data only
4. `agent_activity_log`: 2580 entries, no API endpoint, no OMS page → add tab to `/agents`

**What's adequate:** Tasks (detail page shows output), Memory (comprehensive), Workflows (step progress visible)

**Full design:** `~/otto/docs/oms-visibility-architecture-2026-03-20.md`

**How to apply:** When building new OMS pages in this workflow, follow the implementation plan in the design doc. Step 1 = outreach queue (highest priority). Each step is one page/feature, committed independently.

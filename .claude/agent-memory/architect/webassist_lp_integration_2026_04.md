---
name: WebAssist Landing Page Integration
description: WebAssist + landing page generator integration architecture (2026-04-07). 3-phase plan: API webhook + project_id link, WebAssist dashboard preview card, OMS management page. Fire-and-forget trigger on wizard submit, proxy API to avoid CORS. Migration 084. $5-8 total.
type: project
---

WebAssist landing page integration designed (2026-04-07). Three integration points:

1. **Otto API** — new `GET /by-project/{project_id}` + `POST /webhook/wizard-complete` endpoints. Migration 084 adds `project_id` column to `landing_pages`. Webhook maps wizard submission fields (company→business_name, industry+purpose→description) to existing generate pipeline.

2. **WebAssist** — wizard submit calls Otto webhook (fire-and-forget). Dashboard gets `LandingPageCard` component that polls via API proxy route (`/api/projects/[projectId]/landing-page`). API key stays server-side only.

3. **OMS** — `/landing-pages` page with list view, generate dialog, detail view with preview iframe. Uses existing shadcn patterns.

**Why:** Auto-generated landing page is the WebAssist "wow moment" — submit wizard, get a live page in ~3 minutes. Gives customer immediate value while full site is being built.

**How to apply:** This is the reference design for implementation. Phase 1 (API) is independent of Phase 2 (WebAssist) which is independent of Phase 3 (OMS). Full spec at ~/otto/docs/webassist-landing-page-integration-architecture-2026-04-07.md.

# WebAssist Landing Page Integration — Architecture

**Date:** 2026-04-07
**Author:** Architect Agent
**Status:** Design Complete — Ready for Implementation

---

## Design: WebAssist + Landing Page Generator Integration

### Problem

Two systems exist independently and need to be connected:

1. **Landing Page Generator** (Otto Memory API :8100) — fully functional agent-driven pipeline that takes a business name/URL/description and produces a live HTML page at `webassist.otto.lk/{uuid}/`. 15 pages generated, API key auth, BackgroundTask pipeline.

2. **WebAssist** (webassist.ink, Vercel) — customer-facing website builder with a 10-step wizard (email → business info → design style → features → review → submit). Stores projects in Supabase. Dashboard shows stage progress, approvals, activity feed.

**The gap:** When a customer completes the WebAssist wizard, nothing happens automatically with landing pages. There's no way for:
- Customers to see a landing page preview in their dashboard
- Mev to manage landing pages from the OMS
- The wizard flow to trigger automatic landing page generation as a "quick win" deliverable

**Value:** A landing page generated in ~3 minutes gives the customer an immediate tangible result while their full website is being built (days/weeks). This is the WebAssist "wow moment" — submit your info, get a professional landing page before you close the tab.

### Approach

**Three integration points, each independently deployable:**

1. **Otto API webhook** — new endpoint that receives wizard completions and auto-triggers landing page generation. WebAssist's existing `notifyMev()` pattern extended to also call this endpoint.

2. **WebAssist dashboard card** — a "Landing Page" card in the project dashboard that polls Otto API for generation status and shows an iframe preview when ready.

3. **OMS management page** — `/landing-pages` route in OMS for Mev to view all generated pages, trigger regeneration, manage status.

**Key constraint:** WebAssist runs on Vercel (public internet), Otto API runs on otto-machine (`:8100`). The API must be reachable from Vercel. Currently it IS accessible via `otto.505.systems:8100` or the machine's public IP — but we need explicit auth.

---

### Key Decisions

1. **Communication pattern: Direct API call from Vercel to Otto API**: WebAssist's serverless functions call Otto's `/landing-pages/generate` endpoint directly. The existing API key auth (`X-API-Key` header) is sufficient.

   - *Alternative rejected: Supabase trigger → Otto polls Supabase.* Adds latency (polling interval), complexity (Otto now depends on Supabase schema), and a second source of truth. Direct API is simpler.
   - *Alternative rejected: Shared queue (Redis/SQS).* Over-engineering for a flow that happens once per customer per session.

2. **Landing page linked to WebAssist project via `project_id`**: Add an optional `project_id` column to `landing_pages` table (TEXT, maps to Supabase project UUID). This is the join key — WebAssist dashboard queries Otto API by project_id to find the associated landing page.

   - *Alternative rejected: Store landing page data in Supabase.* Creates data duplication. Otto API is the source of truth for landing pages; Supabase is source of truth for projects. They reference each other by ID.

3. **WebAssist dashboard polls Otto API for status**: The dashboard card calls `GET /landing-pages/by-project/{project_id}/status` every 5 seconds while generating, stops on terminal state. No websockets, no SSE — polling is simple and works through Vercel's serverless architecture.

   - *Alternative rejected: WebSocket connection.* Vercel serverless functions don't maintain persistent connections. Would need a separate WebSocket server.
   - *Alternative rejected: Callback/webhook from Otto to WebAssist.* WebAssist has no webhook receiver. Adding one creates a circular dependency.

4. **Auto-generate vs. opt-in**: Auto-generate for every wizard completion. The cost is ~$1.50/page and provides immediate value. Customers don't choose — they just get it. If landing page generation is an explicit option, most will skip it (paradox of choice).

   - *Alternative rejected: Checkbox in wizard ("Want a quick landing page?").* Adds a step, most won't understand the difference between a landing page and the full site they're ordering. Auto-generate and delight.

5. **Serve at webassist.otto.lk/{uuid}/ (existing)**: No changes to serving infrastructure. The existing nginx config works. For client-facing previews, this URL is fine — it's a preview, not the final product.

   - *Alternative rejected: Serve under webassist.ink/preview/{slug}.* Would require proxying from Vercel to nginx, adding complexity for marginal URL aesthetics.

6. **OMS page uses existing shadcn patterns**: Follow the same layout as other OMS pages (e.g., /content-hub, /workflows). Card list + detail view + action buttons.

---

### API Changes

#### Otto Memory API (`:8100`)

##### New: `GET /landing-pages/by-project/{project_id}`

Lookup landing page by WebAssist project ID. Returns the most recent non-archived landing page for this project.

**Response (200):**
```json
{
  "id": "uuid",
  "slug": "cafe-kinross",
  "business_name": "Cafe Kinross",
  "status": "generating",
  "progress_percent": 50,
  "preview_url": null,
  "error_text": null,
  "created_at": "2026-04-07T10:00:00Z",
  "updated_at": "2026-04-07T10:01:30Z"
}
```

**Response (404):** `{"detail": "No landing page for this project"}`

**Implementation:** ~10 lines in `landing_pages.py`

##### Modified: `POST /landing-pages/generate`

Add optional `project_id` field to `GenerateRequest`:

```python
class GenerateRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    business_url: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    target_audience: Optional[str] = Field(None, max_length=500)
    project_id: Optional[str] = Field(None, max_length=100)  # NEW
    api_key: Optional[str] = Field(None, exclude=True)
```

The `project_id` is stored in the `landing_pages` table for cross-system linking.

##### New: `POST /landing-pages/webhook/wizard-complete`

Convenience endpoint that accepts WebAssist wizard submission payload and maps it to a `/generate` call. This is the endpoint WebAssist calls on wizard submit.

**Request:**
```json
{
  "project_id": "supabase-uuid",
  "name": "John Doe",
  "email": "john@example.com",
  "company": "Cafe Kinross",
  "industry": "Food & Beverage",
  "websiteType": "business",
  "websitePurpose": "Generate leads and showcase menu",
  "designStyle": "modern-minimal",
  "features": ["contact-form", "menu", "gallery"],
  "pagesNeeded": ["home", "about", "menu", "contact"]
}
```

**Logic:**
1. Extract `business_name` from `company`
2. Build `description` from `industry` + `websitePurpose` + `features`
3. Build `target_audience` from `websiteType` context
4. Call `generate_landing_page()` internally (reuse existing logic)
5. Return `202 Accepted` with `{id, status_url}`

**Auth:** Same API key as `/generate`. WebAssist sets this in `OTTO_LP_API_KEY` env var.

#### DB Migration: `084_landing_pages_project_id.sql`

```sql
ALTER TABLE landing_pages ADD COLUMN IF NOT EXISTS project_id TEXT;
CREATE INDEX IF NOT EXISTS idx_landing_pages_project_id ON landing_pages(project_id) WHERE project_id IS NOT NULL;
```

Nullable — most existing pages have no project association. Index is partial (WHERE NOT NULL) since most rows won't have it initially.

---

### WebAssist Changes

#### 1. Wizard Submit — Trigger Landing Page Generation

**File:** `app/api/wizard/submit/route.ts`

After the existing `notifyMev()` call, add a `triggerLandingPage()` fire-and-forget call:

```typescript
function triggerLandingPage(data: {
  project_id: string;
  company: string;
  industry?: string;
  websiteType?: string;
  websitePurpose?: string;
  designStyle?: string;
  features?: string[];
}): void {
  const ottoApiUrl = process.env.OTTO_API_URL;  // e.g., "https://otto.505.systems:8100"
  const apiKey = process.env.OTTO_LP_API_KEY;
  if (!ottoApiUrl || !apiKey) return;

  fetch(`${ottoApiUrl}/landing-pages/webhook/wizard-complete`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': apiKey,
    },
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(8000),
  }).catch((err) => {
    console.warn('Landing page trigger failed (non-blocking):', err?.message);
  });
}
```

**Critical:** Fire-and-forget. Never block the wizard submit response on landing page generation. The customer doesn't know about this — they just see it appear in their dashboard.

#### 2. Dashboard — Landing Page Preview Card

**File:** `app/dashboard/[projectId]/page.tsx` (add to existing dashboard)

New component: `LandingPageCard` — renders in the dashboard alongside existing cards.

```
┌─────────────────────────────────────────────────────┐
│ Your Landing Page                                   │
│                                                     │
│ [Generating... ████████░░░░ 50%]    ← polling state │
│ Estimated: ~2 minutes remaining                     │
│                                                     │
│ — OR (when ready) —                                 │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │          [iframe preview of page]               │ │
│ │                                                 │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ [View Full Page ↗]              [Request Changes]   │
└─────────────────────────────────────────────────────┘
```

**Behavior:**
- On mount, `GET /landing-pages/by-project/{projectId}` via API route proxy
- If 404: show nothing (landing page not triggered yet or feature disabled)
- If `generating`: show progress bar, poll every 5s
- If `review` or `published`: show iframe preview + "View Full Page" link
- If error: show "We're working on your preview page" (no error details to customer)

**API proxy route (to avoid CORS):**
`app/api/projects/[projectId]/landing-page/route.ts` — proxies to Otto API, adds API key server-side.

```typescript
// GET /api/projects/[projectId]/landing-page
export async function GET(req, { params }) {
  const { projectId } = await params;
  const res = await fetch(
    `${process.env.OTTO_API_URL}/landing-pages/by-project/${projectId}`,
    { headers: { 'X-API-Key': process.env.OTTO_LP_API_KEY } }
  );
  if (!res.ok) return NextResponse.json(null, { status: res.status });
  return NextResponse.json(await res.json());
}
```

#### 3. Environment Variables (Vercel)

| Variable | Value | Purpose |
|----------|-------|---------|
| `OTTO_API_URL` | `https://otto.505.systems:8100` | Otto Memory API base URL |
| `OTTO_LP_API_KEY` | (matches `settings.landing_page_api_key`) | Auth for landing page endpoints |

---

### OMS Landing Pages Management Page

**Location:** `interfaces/web-next/src/app/landing-pages/page.tsx`

#### List View

```
┌───────────────────────────────────────────────────────────────┐
│ Landing Pages                                   [+ Generate]  │
│───────────────────────────────────────────────────────────────│
│ Filter: [All ▾] [Status ▾]                     15 total       │
│                                                               │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Cafe Kinross                                    [review]  │ │
│ │ webassist.otto.lk/d3fa5524...                             │ │
│ │ Created Apr 6, 2026                [Preview] [Regenerate] │ │
│ └───────────────────────────────────────────────────────────┘ │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Otto Market                                  [generating] │ │
│ │ Step: HTML Generation (45s elapsed)                       │ │
│ │ Created Apr 6, 2026                                       │ │
│ └───────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

**shadcn/ui components:** Card, Badge, Button, Select, Dialog (generate form), Input, Textarea, Label

#### Detail View (click on card)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Back    Summit Event Productions                  [review]  │
│───────────────────────────────────────────────────────────────│
│                                                               │
│ Tabs: [Overview] [Preview]                                    │
│                                                               │
│ ┌─ Overview ────────────────────────────────────────────────┐ │
│ │ Business: Summit Event Productions                        │ │
│ │ URL: summitevents.com                                     │ │
│ │ Status: Review                                            │ │
│ │ Preview: webassist.otto.lk/d3fa5524.../                   │ │
│ │ Created: Apr 6, 2026 4:33 PM                              │ │
│ │                                                           │ │
│ │ [Publish]  [Regenerate]  [Archive]                        │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                               │
│ ┌─ Preview ─────────────────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │           [full-width iframe of page]               │   │ │
│ │ │                                                     │   │ │
│ │ │                                                     │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ │                              [Open in New Tab ↗]          │ │
│ └───────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────┘
```

**shadcn/ui components:** Tabs, Card, Badge, Button, Separator, Dialog

#### Generate Dialog

Same as original arch doc design. Form with: business_name (required), business_url, description, target_audience. Calls `POST /landing-pages/generate`.

---

### Implementation Plan

#### Phase 1: API + DB ($1-2)

1. **Migration 084** — Add `project_id` column to `landing_pages`
2. **New endpoint** — `GET /landing-pages/by-project/{project_id}` 
3. **New endpoint** — `POST /landing-pages/webhook/wizard-complete`
4. **Modify** — Add `project_id` to `GenerateRequest` model and INSERT query
5. **Test** — Curl the webhook endpoint with sample wizard data, verify page generates

**Files changed:**
| File | Action | Est. Lines |
|------|--------|------------|
| `memory/migrations/084_landing_pages_project_id.sql` | CREATE | ~5 |
| `memory/routes/landing_pages.py` | MODIFY | ~50 (new endpoints + model field) |

#### Phase 2: WebAssist Integration ($2-3)

6. **Wizard submit** — Add `triggerLandingPage()` to `app/api/wizard/submit/route.ts`
7. **API proxy** — Create `app/api/projects/[projectId]/landing-page/route.ts`
8. **Dashboard card** — Create `components/dashboard/landing-page-card.tsx`
9. **Wire card** — Add `LandingPageCard` to `app/dashboard/[projectId]/page.tsx`
10. **Env vars** — Set `OTTO_API_URL` and `OTTO_LP_API_KEY` in Vercel
11. **Test** — Full wizard submit → landing page appears in dashboard flow

**Files changed:**
| File | Action | Est. Lines |
|------|--------|------------|
| `app/api/wizard/submit/route.ts` | MODIFY | ~25 |
| `app/api/projects/[projectId]/landing-page/route.ts` | CREATE | ~25 |
| `components/dashboard/landing-page-card.tsx` | CREATE | ~120 |
| `app/dashboard/[projectId]/page.tsx` | MODIFY | ~10 (add card import) |

#### Phase 3: OMS Management ($2-3)

12. **OMS page** — Create `interfaces/web-next/src/app/landing-pages/page.tsx`
13. **Test** — Generate from OMS, verify list/detail/preview/regenerate

**Files changed:**
| File | Action | Est. Lines |
|------|--------|------------|
| `interfaces/web-next/src/app/landing-pages/page.tsx` | CREATE | ~350 |

#### Phase 4: Polish (future)

14. **Publish flow** — "Publish" button in OMS sets status, optionally notifies customer
15. **Custom domains** — Map client domain → landing page via nginx server block
16. **Analytics** — Track page views via simple hit counter
17. **Revision loop** — "Request Changes" button → creates revision task

---

### Data Flow

```
                         CUSTOMER FLOW
                         ─────────────
WebAssist Wizard (webassist.ink)
  │
  ├── Submit wizard form → Supabase INSERT (project record)
  │                      → notifyMev() (WhatsApp)
  │                      → triggerLandingPage() [NEW, fire-and-forget]
  │                            │
  │                            ▼
  │                   Otto API :8100
  │                   POST /landing-pages/webhook/wizard-complete
  │                     │ maps wizard data → business profile
  │                     │ INSERT landing_pages (project_id set)
  │                     │ BackgroundTask: _run_pipeline()
  │                     │   → agent_generator.py
  │                     │   → writes /var/www/webassist/{uuid}/index.html
  │                     │   → updates status: generating → review
  │                     │
  │                     ▼
  │                   nginx: webassist.otto.lk/{uuid}/
  │
  ├── Dashboard (webassist.ink/dashboard/[projectId])
  │     │
  │     └── LandingPageCard polls:
  │           GET /api/projects/[projectId]/landing-page
  │             │ (proxy to Otto API)
  │             ▼
  │           GET /landing-pages/by-project/{project_id}
  │             → shows progress bar while generating
  │             → shows iframe preview when done
  │
  │
                         MEV FLOW
                         ────────
OMS (mev.otto.lk/landing-pages)
  │
  ├── List all pages: GET /landing-pages
  ├── Generate new:   POST /landing-pages/generate
  ├── View detail:    GET /landing-pages/{id}
  ├── Regenerate:     POST /landing-pages/{id}/regenerate
  ├── Publish:        PATCH /landing-pages/{id}/status?status=published
  └── Archive:        DELETE /landing-pages/{id}
```

---

### Network / Auth

| From | To | Auth | Protocol |
|------|----|------|----------|
| WebAssist (Vercel) | Otto API (:8100) | `X-API-Key` header | HTTPS via otto.505.systems |
| OMS (mev.otto.lk) | Otto API (:8100) | Same-origin (localhost) | HTTP |
| Customer browser | webassist.otto.lk | None (public static) | HTTPS |
| Customer browser | WebAssist API proxy | Session cookie | HTTPS |

**CORS consideration:** The WebAssist dashboard never calls Otto API directly. All calls go through WebAssist's own API routes (`/api/projects/[id]/landing-page`) which proxy server-side. No CORS issues.

**Port exposure:** Otto API (:8100) must be reachable from Vercel. Verify:
```bash
curl -sf https://otto.505.systems:8100/health
```
If not reachable, add nginx reverse proxy for `:8100` on `otto.505.systems`.

---

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Otto API unreachable from Vercel | Medium | Medium | Fire-and-forget pattern. If trigger fails, Mev can generate manually from OMS. Add nginx proxy as fallback path. |
| Rate limiting on agent generation | Low | Medium | BackgroundTask queue is sequential per-request. Max 5 concurrent tasks. No thundering herd — wizard completions are low-volume (1-5/day). |
| Customer sees "generating" forever | Low | High | 5-minute timeout on polling. After timeout, hide the card gracefully ("Your preview is being prepared"). |
| Supabase project_id doesn't match | Low | Low | project_id is opaque string — no FK enforcement. Mismatch means landing page just isn't shown in dashboard. |
| API key leaked in client JS | Low | High | API key ONLY in server-side env vars. WebAssist API proxy handles auth. Never exposed to browser. |

---

### Cost Summary

| Component | Cost |
|-----------|------|
| Phase 1: API + DB | ~$1-2 implementation |
| Phase 2: WebAssist integration | ~$2-3 implementation |
| Phase 3: OMS management page | ~$2-3 implementation |
| Per landing page (ongoing) | ~$1.50 (agent generation) |
| **Total implementation** | **~$5-8** |

---

### Appendix: Existing Files Reference

| Component | File | Status |
|-----------|------|--------|
| Landing page API routes | `~/otto/memory/routes/landing_pages.py` | Complete (276 lines) |
| Agent HTML generator | `~/otto/services/landing_page/agent_generator.py` | Complete (253 lines) |
| Design catalog parser | `~/otto/services/landing_page/design_catalog.py` | Complete (283 lines) |
| Design synthesizer | `~/otto/services/landing_page/design.py` | Complete (~400 lines) |
| Business research | `~/otto/memory/services/landing_page/research.py` | Complete (699 lines) |
| Legacy template generator | `~/otto/services/landing_page/generator.py` | Complete (1573 lines, fallback) |
| Landing page agent | `~/otto/.claude/agents/landing-page.md` | Complete (238 lines) |
| DB migration | `~/otto/memory/migrations/083_landing_pages.sql` | Applied |
| Design catalog | `/mnt/media/prompts.md` | Complete (3112 lines, 33 designs) |
| WebAssist wizard submit | `/mnt/media/projects/web-assist/app/api/wizard/submit/route.ts` | Existing (modify) |
| WebAssist dashboard | `/mnt/media/projects/web-assist/app/dashboard/[projectId]/page.tsx` | Existing (modify) |
| WebAssist projects API | `/mnt/media/projects/web-assist/app/api/projects/[projectId]/route.ts` | Existing (reference) |
| OMS app directory | `~/otto/interfaces/web-next/src/app/` | Existing (add route) |

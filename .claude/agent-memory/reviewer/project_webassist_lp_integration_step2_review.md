---
name: WebAssist LP Integration Step 2 Code Review
description: Integration of landing page generator with WebAssist (2026-04-07, WF Step 2): NEEDS_CHANGES. 2 criticals: unauthenticated by-project endpoint; zombie state on pipeline failure.
type: project
---

WebAssist landing page integration reviewed (2026-04-07). NEEDS_CHANGES — 2 criticals.

**Why:** Auth gap allows unauthenticated project_id enumeration on new endpoint; zombie state means customers see spinner forever on generation failure.

**How to apply:** Fix both criticals before customer-facing deployment. Auth gap: add `Depends(verify_api_key)` to `/by-project/{project_id}`. Zombie state: add `status = 'failed'` update in `_run_pipeline` exception handler, add 'failed' to VALID_STATUSES and progress map, update card to stop polling on 'failed'.

## Critical Issues

1. **`by-project` endpoint unauthenticated** (`memory/routes/landing_pages.py:272`) — No `Depends(verify_api_key)`. The proxy at `web-assist` correctly sends `X-API-Key` header, but the server ignores it. Any caller with a valid project UUID (Supabase UUID, not secret) can read business_name, status, error_text, preview_url. Pattern: existing auth gap from 2026-04-06 review continues into new endpoints.

2. **Zombie state on pipeline failure** (`memory/routes/landing_pages.py:81–84` + `landing-page-card.tsx:44–46`) — `_run_pipeline` sets `error_text` on exception but does NOT update `status` from 'generating'. `LandingPageCard` stops polling only when `status !== 'pending' && status !== 'generating'` (line 45). Result: customer sees "Building your preview..." spinner forever on any generation error. Error UI (line 160) is gated on `!isGenerating` so it never shows. Fix: add `status = 'failed'` to the exception UPDATE in `_run_pipeline`.

## Warnings

3. **TOCTOU in duplicate check** (`memory/routes/landing_pages.py:337–357`) — `SELECT id ... WHERE project_id = $1` then `INSERT` without a transaction. Concurrent wizard submissions for the same project (e.g. double-click) could create two landing pages. Fix: use `INSERT ... ON CONFLICT (project_id) DO NOTHING` or wrap in a transaction.

4. **`triggerLandingPage` skipped on Supabase DB error path** (`web-assist/app/api/wizard/submit/route.ts:209–244`) — On DB error fallback, `project.id` is undefined so `triggerLandingPage` is never called. Some wizard submissions miss the landing page wow moment silently. Low risk (DB errors rare) but worth documenting.

5. **Hidden state logic incomplete in LandingPageCard** (`landing-page-card.tsx:33`) — Card hides on 404 or 503 but NOT on 502/500/429. On other errors, `setLoading(false)` runs with `data=null`, which hits the `loading === false && !data → return null` guard (line 65). So it actually does hide on all errors — behavior is correct but the explicit 503 check is misleading (implies other errors aren't handled).

## What's Good

- Architecture plan followed completely — all 3 phases implemented
- `triggerLandingPage` correctly fire-and-forget (mirrors `notifyMev` pattern)
- API key stays server-side (proxy route is the right pattern)
- `clearInterval` on unmount and terminal states
- Duplicate project check before creating new page  
- Route depth conflict doesn't actually exist (2-segment vs 3-segment paths)
- Partial index on `project_id` is correct (sparse, many NULLs)
- `encodeURIComponent` on projectId in proxy
- TypeScript types correctly added to all 3 interfaces

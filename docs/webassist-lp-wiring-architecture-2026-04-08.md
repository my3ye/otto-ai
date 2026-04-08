# Architecture: Wire Landing Page Generator to WebAssist

**Date:** 2026-04-08
**Status:** Design Complete
**Author:** Architect Agent

---

## Design: WebAssist ↔ Landing Page Generator Wiring

### Problem

The landing page generator and WebAssist wizard are **95% integrated in code** but **not functional end-to-end** due to infrastructure gaps. All three systems (Otto LP API, WebAssist Vercel app, OMS) have the right code, but the plumbing between them is incomplete.

### Current State Audit

| Component | Code | Infrastructure | Working E2E |
|-----------|------|---------------|-------------|
| LP API (`/landing-pages/*`) | Complete (9 endpoints) | Running on :8100 | Yes (OMS can use it) |
| WebAssist wizard trigger | Complete (`triggerLandingPage()`) | **BROKEN** — env vars not set on Vercel | No |
| WebAssist dashboard card | Complete (`LandingPageCard`) | **BROKEN** — API proxy can't reach Otto | No |
| Nginx LP API proxy | **MISSING** | otto.505.systems only serves static files at `/landing-pages/` | No |
| API key | **NOT CONFIGURED** | `landing_page_api_key=""` in config, no env var in `.env` | No |
| HTML serving | Complete | nginx at `webassist.otto.lk/{id}/` | Yes |
| OMS management page | Complete | mev.otto.lk/webassist/landing-pages | Yes |

### Root Cause

Three infrastructure gaps prevent the integration from working:

1. **No nginx proxy for LP API endpoints.** `otto.505.systems` has a `location /landing-pages/` block that serves **static files** from `/var/www/html/landing-pages/`. The actual API endpoints (`POST /landing-pages/webhook/wizard-complete`, `GET /landing-pages/by-project/{id}`) are never proxied to `:8100`.

2. **No API key configured.** `settings.landing_page_api_key` defaults to `""`. The webhook and proxy endpoints check `X-API-Key` header. With no key set, auth either always passes (empty == skip) or always fails depending on the check logic.

3. **Vercel env vars not set.** `OTTO_API_URL` and `OTTO_LP_API_KEY` are not configured in the WebAssist Vercel project. The `triggerLandingPage()` function silently returns if either is missing.

### Approach

No code changes needed. This is a **pure infrastructure/config wiring task**.

#### Fix 1: Add nginx proxy for LP API (otto.505.systems)

Add these location blocks to `/etc/nginx/sites-available/otto.505.systems` **above** the existing static `location /landing-pages/` block:

```nginx
# Landing page API — proxied to Otto Memory API
location /landing-pages/webhook/ {
    proxy_pass http://127.0.0.1:8100/landing-pages/webhook/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 120s;  # generation can take time
}

location /landing-pages/by-project/ {
    proxy_pass http://127.0.0.1:8100/landing-pages/by-project/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

location = /landing-pages/generate {
    proxy_pass http://127.0.0.1:8100/landing-pages/generate;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 120s;
}

# Landing page status/detail API (UUID paths)
location ~ ^/landing-pages/([0-9a-f-]{36}) {
    proxy_pass http://127.0.0.1:8100;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}

# Landing page list API
location = /landing-pages {
    proxy_pass http://127.0.0.1:8100/landing-pages;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

**Important:** The existing `location /landing-pages/` static block should be removed or moved to a non-conflicting path — it will never match now that API routes take precedence. The generated HTML is served from `webassist.otto.lk`, not `otto.505.systems`.

Then: `sudo nginx -t && sudo systemctl reload nginx`

#### Fix 2: Configure API key

Generate a key and set it in both systems:

```bash
# Generate key
LP_KEY=$(openssl rand -hex 32)

# Add to Otto's .env
echo "LANDING_PAGE_API_KEY=$LP_KEY" >> ~/memory/.env

# Restart Memory API to pick up new config
sudo systemctl restart otto-memory
```

**Verify:** The auth check in `landing_pages.py` (lines ~141, ~293, ~325) compares `X-API-Key` header against `settings.landing_page_api_key`. With the key set, webhook calls will authenticate.

#### Fix 3: Set Vercel env vars

```bash
cd /mnt/media/projects/web-assist

# Set the env vars (production + preview)
npx vercel env add OTTO_API_URL production <<< "https://otto.505.systems"
npx vercel env add OTTO_LP_API_KEY production <<< "$LP_KEY"

# Also set for preview deployments
npx vercel env add OTTO_API_URL preview <<< "https://otto.505.systems"
npx vercel env add OTTO_LP_API_KEY preview <<< "$LP_KEY"

# Redeploy to pick up new env vars
npx vercel --prod
```

Alternative: Set via Vercel dashboard at https://vercel.com/ottomev/web-assist/settings/environment-variables

### Key Decisions

- **No code changes**: All code is already written and correct. This is purely config/infra. Alternative: refactor the API proxy to use a different URL pattern (rejected — unnecessary complexity).
- **Proxy via otto.505.systems (not direct :8100)**: WebAssist on Vercel can't reach :8100 directly (not exposed). The existing otto.505.systems nginx with SSL is the correct gateway. Alternative: expose :8100 via a separate domain (rejected — one more cert to manage).
- **Single API key for all LP operations**: One key shared between webhook trigger and status polling. Alternative: separate keys per operation (rejected — over-engineering for current scale).
- **Keep static `/landing-pages/` block removed**: The generated HTML lives at `webassist.otto.lk/{uuid}/`, not at `otto.505.systems/landing-pages/`. The static alias was likely a leftover. Alternative: keep both and use regex precedence (rejected — confusing).

### Data Flow (After Fix)

```
CUSTOMER SUBMITS WIZARD (webassist.ink)
  │
  ├─ Supabase: project created
  │
  └─ triggerLandingPage() [fire-and-forget]
      │
      └─ POST https://otto.505.systems/landing-pages/webhook/wizard-complete
          │  Headers: X-API-Key: $LP_KEY
          │  Body: {project_id, company, industry, ...}
          │
          └─ nginx → :8100 → landing_pages.py webhook handler
              │
              ├─ INSERT landing_pages (status: pending, project_id: linked)
              │
              └─ BackgroundTask: _run_pipeline()
                  ├─ Research business (DDG)
                  ├─ Research competitors
                  └─ Generate HTML via Claude Code agent
                      └─ Output: /var/www/webassist/{uuid}/index.html
                         Served at: https://webassist.otto.lk/{uuid}/

CUSTOMER DASHBOARD (webassist.ink/dashboard/{projectId})
  │
  └─ LandingPageCard polls every 5s:
      │
      └─ GET /api/projects/{projectId}/landing-page [Next.js API route]
          │
          └─ GET https://otto.505.systems/landing-pages/by-project/{projectId}
              │  Headers: X-API-Key: $LP_KEY
              │
              └─ nginx → :8100 → landing_pages.py
                  └─ Returns: {id, status, progress_percent, preview_url, ...}

  When status == "review":
    → iframe loads https://webassist.otto.lk/{uuid}/
    → "View Full Page" link opens in new tab
```

### Implementation Plan

**Phase 1: Infrastructure Wiring (~15 min, $0)**

1. Generate API key, add to `~/memory/.env` as `LANDING_PAGE_API_KEY`
2. Add nginx proxy blocks to `otto.505.systems` config (above static block)
3. Remove or comment out the static `/landing-pages/` alias block
4. `sudo nginx -t && sudo systemctl reload nginx`
5. `sudo systemctl restart otto-memory`
6. Test: `curl -s -H "X-API-Key: $KEY" https://otto.505.systems/landing-pages` should return `[]`

**Phase 2: Vercel Configuration (~5 min, $0)**

7. Set `OTTO_API_URL=https://otto.505.systems` and `OTTO_LP_API_KEY` on Vercel
8. Redeploy WebAssist

**Phase 3: End-to-End Verification (~5 min, ~$0.50 for one generation)**

9. Submit a test wizard on webassist.ink
10. Verify: webhook fires → Otto creates landing page → status polling works → preview renders in dashboard
11. Verify: OMS at mev.otto.lk/webassist/landing-pages shows the same page

### Verification Checklist

After wiring:

- [ ] `curl https://otto.505.systems/landing-pages` → 200 (list endpoint)
- [ ] `curl -X POST https://otto.505.systems/landing-pages/webhook/wizard-complete -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"project_id":"test","company":"Test Co"}'` → 200 (webhook fires)
- [ ] WebAssist wizard submit triggers landing page generation
- [ ] Dashboard card shows progress → preview when ready
- [ ] OMS landing pages page shows all generated pages

### Risks

- **API key leak in Vercel logs**: Mitigated — key is server-side only (Next.js API routes), never sent to browser.
- **Generation cost per wizard submit**: ~$0.50-1.50 per page. At current volume (low), acceptable. If volume increases, add rate limiting or a queue gate.
- **Generation failures silent to customer**: By design — `LandingPageCard` shows "We're working on your preview page" on error. Customer sees stages/updates even without the LP card.
- **Nginx location ordering**: Regex and exact-match locations take precedence over prefix matches. The API proxy blocks (exact match, regex) will correctly override any remaining prefix block. Test with `nginx -t`.

### Estimated Effort

| Phase | Time | Cost |
|-------|------|------|
| Infrastructure wiring | 15 min | $0 |
| Vercel config | 5 min | $0 |
| E2E verification | 5 min | ~$0.50 |
| **Total** | **~25 min** | **~$0.50** |

### Files Affected

| File | Change | Type |
|------|--------|------|
| `/etc/nginx/sites-available/otto.505.systems` | Add API proxy blocks, remove static alias | Config |
| `~/memory/.env` | Add `LANDING_PAGE_API_KEY` | Config |
| Vercel env vars (web-assist project) | Add `OTTO_API_URL`, `OTTO_LP_API_KEY` | Config |
| **No application code changes** | — | — |

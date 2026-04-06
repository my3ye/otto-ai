---
name: Landing Page Pipeline Integration Review
description: Full integration review of landing page generation pipeline — routes, services, DB, nginx, OMS (2026-04-06)
type: project
---

NEEDS_CHANGES 7.5/10 — 3 criticals, 2 warnings. Core pipeline connectivity is sound.

**Why:** New sellable endpoint. Auth gap and XSS must be fixed before exposing to external clients.

**How to apply:** Do not publish API docs or expose the endpoint externally until criticals 1 and 3 are resolved.

Criticals:
1. verify_api_key defined but never applied via Depends — all endpoints except /generate are fully open (landing_pages.py:52 vs every route)
2. business_name (user input) injected raw into HTML body at lines 1182, 1188, 1198, 1215, 602 — XSS risk in generated pages
3. copy_data not persisted to DB — re-generate (POST /{id}/generate) retrieves from `_copy_data` key that is never written, falls to empty dict, generates HTML with no copy

Warnings:
1. LANDING_PAGE_API_KEY not set in memory/.env — production runs in open-access dev mode
2. Migration 083 comment references wrong paths (otto.505.systems, /var/www/html/landing-pages) — actual serving is webassist.otto.lk / /var/www/webassist/{uuid}

What's good:
- Pipeline connectivity: research → design → copy → HTML → file → DB all wire correctly
- DB schema clean: UUID PK, JSONB for research/design, trigger for updated_at, correct indexes
- nginx config: correct try_files pattern, SSL via certbot, security headers, gzip, dotfile protection
- Status polling: progress_percent map is clean; workflow step enrichment is solid
- OMS page: polling interval (3s), cleanup on unmount, iframe preview, debug panel — all correct
- Error handling per stage: each try/except block writes error_text and returns — pipeline halts correctly
- Fallback designs/copy: design.py and copy fallbacks are reasonable defaults when LLM fails

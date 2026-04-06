---
name: Landing Page Workflow Integration Review
description: Full integration review of WebAssist landing page pipeline (2026-04-06). NEEDS_CHANGES — 3 criticals before external exposure.
type: project
---

Landing page generation pipeline reviewed (2026-04-06). NEEDS_CHANGES — do not expose externally until criticals are fixed.

**Why:** 3 criticals make this unsafe as a paid service: auth gap allows unauthenticated enumeration/deletion; XSS allows injected scripts via business_name; copy_data loss degrades re-generated pages silently.

**How to apply:** Block external exposure (webassist.ink) until auth is patched across all routes, XSS is fixed in generator.py body sections, and copy_data persistence is added.

## Critical Issues

1. **Auth gap** (`memory/routes/landing_pages.py:52`) — `verify_api_key` defined but never applied as `Depends()` to any route except inline in `/generate`. All other routes (GET /, GET /{id}, status, PATCH, DELETE, research endpoints) fully unauthenticated. Fix: add `Depends(verify_api_key)` to every route decorator.

2. **Stored XSS** (`services/landing_page/generator.py:602, 1182, 1188, 1198, 1215`) — `business_name` raw in HTML body (nav logo, footer copyright). Only escaped in `<title>` and meta tags. Fix: pass `business_name` through `_escape()` at all body insertion points.

3. **copy_data never persisted** (`memory/routes/landing_pages.py:759–767`) — Re-generate path tries `design_decisions.pop("_copy_data")` and `competitor_data.get("_copy_data")` — neither is ever set. Re-generation always produces placeholder copy. Fix: add `copy_data JSONB` column (migration needed) or embed under `design_decisions["_copy_data"]` before DB write at line 240.

## Warnings

4. `LANDING_PAGE_API_KEY` not set in `~/memory/.env` — server in open dev mode
5. Migration 083 comment + architecture doc still reference `otto.505.systems` (correct: `webassist.otto.lk`)

## What's Good

- Pipeline connectivity clean (research → design → HTML → nginx)
- DB schema well-designed (UUID PK, JSONB, status CHECK constraint matches code)
- nginx config correct (security headers, SSL, gzip, dotfile blocking)
- OMS page production-quality (polling with clearInterval on unmount, iframe preview)
- Fallback handling for LLM failures solid (`_fallback_design`, `_fallback_copy`)

## Deliverable

API_DOCS.md written to `/home/web3relic/otto/docs/API_DOCS.md` — covers POST /generate, GET /status, GET / with auth, schemas, error codes, rate limits, and pre-production checklist.

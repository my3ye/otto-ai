# Landing Page Generation API

**Version:** 1.0  
**Base URL:** `http://localhost:8100` (internal) | served via Memory API  
**Last updated:** 2026-04-06

---

## Authentication

All write endpoints require an `X-API-Key` header.

Set `LANDING_PAGE_API_KEY` in `~/memory/.env`. If unset, the server runs in dev mode (no auth enforced).

```
X-API-Key: <your-api-key>
```

Alternatively, pass `api_key` in the request body. Header takes precedence.

**Missing or invalid key returns HTTP 401.**

> ⚠️ **Important:** Set `LANDING_PAGE_API_KEY` before exposing this endpoint externally. Dev mode (empty key) accepts all requests.

---

## POST /landing-pages/generate

Generate a complete AI-powered landing page for a business.

Starts an async pipeline and returns immediately with a job ID. Poll the `status_url` for progress.

**Auth:** Required

**Request**

```json
POST /landing-pages/generate
Content-Type: application/json
X-API-Key: <your-key>

{
  "business_name": "Acme Consulting",
  "business_url": "https://acme.com",
  "description": "B2B strategy consulting for SMBs",
  "target_audience": "SMB founders"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `business_name` | string | Yes | Name of the business (1–200 chars) |
| `business_url` | string | No | Website URL — scraped for brand info |
| `description` | string | No | Business description — fallback when no URL |
| `target_audience` | string | No | Shapes copy tone and messaging |
| `api_key` | string | No | Alternative to `X-API-Key` header |

**Response — 202 Accepted**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "acme-consulting",
  "status": "pending",
  "preview_url": null,
  "estimated_time_seconds": 120,
  "status_url": "/landing-pages/550e8400-e29b-41d4-a716-446655440000/status"
}
```

`preview_url` is `null` until the pipeline completes (status = `review`).

**Pipeline stages**

| Status | Stage | Description |
|---|---|---|
| `pending` | Queued | Record created, pipeline about to start |
| `researching` | Research | Scraping business website + DDG competitor search |
| `designing` | Design | LLM selects layout, fonts, colors, section structure |
| `generating` | Build | Synthesizing HTML file and writing to nginx |
| `review` | Complete | Preview URL populated, page live at `webassist.otto.lk/{slug}` |
| `published` | Published | Explicitly marked published by operator |
| `archived` | Archived | Soft-deleted |

**Error codes**

| Code | Reason |
|---|---|
| 401 | Missing or invalid `X-API-Key` |
| 422 | Validation error (e.g. `business_name` missing or too long) |
| 500 | Internal error creating the DB record |

> **Note:** Pipeline failures do NOT return HTTP errors. They set `error_text` on the record and halt the pipeline at the failing stage. Always check `error_text` when polling status.

**Timing**

Typical end-to-end time: 90–150 seconds depending on research depth and LLM latency.

---

## GET /landing-pages/{id}/status

Lightweight polling endpoint to track pipeline progress.

**Auth:** None  
**Recommended poll interval:** 3–5 seconds

**Path params**

| Param | Type | Description |
|---|---|---|
| `id` | UUID | Landing page ID from the generate response |

**Response — 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "designing",
  "progress_percent": 50,
  "preview_url": null,
  "error_text": null,
  "created_at": "2026-04-06T10:30:00+00:00",
  "updated_at": "2026-04-06T10:31:45+00:00",
  "current_step": 2,
  "total_steps": 5,
  "step_name": "Design Synthesis"
}
```

`progress_percent` mapping:

| Status | Progress |
|---|---|
| `pending` | 0% |
| `researching` | 25% |
| `designing` | 50% |
| `generating` | 75% |
| `review` / `published` | 100% |

When `error_text` is non-null, the pipeline has failed at the indicated `status` stage.

**Error codes**

| Code | Reason |
|---|---|
| 404 | Landing page ID not found |

---

## GET /landing-pages

List all landing pages. Used by the OMS dashboard and operator tooling.

**Auth:** None (internal use — protect externally if needed)

**Query params**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | — | Filter by status value |
| `limit` | int | 20 | Results per page (max 100) |
| `offset` | int | 0 | Pagination offset |

**Valid `status` filter values:** `pending`, `researching`, `designing`, `generating`, `review`, `published`, `archived`

**Response — 200 OK**

```json
{
  "count": 42,
  "landing_pages": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "slug": "acme-consulting",
      "business_name": "Acme Consulting",
      "status": "review",
      "preview_url": "https://webassist.otto.lk/acme-consulting",
      "created_at": "2026-04-06T10:30:00+00:00",
      "updated_at": "2026-04-06T10:32:10+00:00"
    }
  ]
}
```

`count` is the total matching records (respects `status` filter).

---

## GET /landing-pages/{id}

Get full record for a single landing page, including research and design data.

**Auth:** None (internal use)

**Response — 200 OK**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "acme-consulting",
  "business_name": "Acme Consulting",
  "business_url": "https://acme.com",
  "description": "B2B strategy consulting",
  "target_audience": "SMB founders",
  "status": "review",
  "preview_url": "https://webassist.otto.lk/acme-consulting",
  "html_path": "/var/www/webassist/acme-consulting/index.html",
  "research_data": { ... },
  "competitor_data": { ... },
  "design_decisions": { ... },
  "error_text": null,
  "workflow_instance_id": "uuid-or-null",
  "created_at": "2026-04-06T10:30:00+00:00",
  "updated_at": "2026-04-06T10:32:10+00:00"
}
```

---

## Rate Limits

Global: **120 requests/minute per IP** (enforced by SlowAPI across all endpoints).

Recommended client-side limit on `/generate`: max 5 submissions/minute to avoid pipeline saturation.

---

## Serving Infrastructure

Generated pages are served at:

```
https://webassist.otto.lk/{slug}/
```

- Backed by nginx on the otto-machine VM
- Files written to `/var/www/webassist/{slug}/index.html`
- SSL via Let's Encrypt (auto-renews, expires 2026-07-05)
- No nginx reload needed when adding pages — files are picked up immediately

---

## Known Issues / Pre-Production Checklist

Before exposing externally:

- [ ] Set `LANDING_PAGE_API_KEY` in `~/memory/.env` — server currently runs in dev mode (no auth)
- [ ] Apply auth middleware to all routes (currently only `/generate` enforces the key — all other routes are unauthenticated)
- [ ] Escape `business_name` in HTML body sections to prevent stored XSS (currently only escaped in `<title>` and meta tags)
- [ ] Add `copy_data` column to DB or persist it under `design_decisions["_copy_data"]` — re-generation currently produces degraded placeholder copy
- [ ] Set a per-endpoint rate limit on `/generate` (5/min recommended)

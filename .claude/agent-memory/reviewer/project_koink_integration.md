---
name: project_koink_integration
description: Koink Standard integration module (Phase 0) code review — commit 20411ba, 2026-03-23. NEEDS_CHANGES (1 critical bug, 5 warnings).
type: project
---

Koink Standard integration Phase 0 review — commit 20411ba (2026-03-23).

**Verdict: NEEDS_CHANGES** — one critical bug, 5 warnings, implementation otherwise solid.

**Critical bug:** Invalid UUID in path parameter produces HTTP 500 instead of 400/422.
Routes `GET /koink/launches/{token_id}`, `GET /koink/dhm/{token_id}`, `GET /koink/treasury/{token_id}` all accept `token_id: str` and call `UUID(token_id)` without try/except. Fix: type path params as `UUID` directly so FastAPI validates and returns 422, or wrap in try/except → 400.

**Warnings:**
1. No CHECK constraint on `koink_tokens.status` — any string accepted at DB level
2. `snapshot_dhm_positions` N+1 queries — one UPDATE per position, will slow with scale
3. `validate_koink_params` allows blank/whitespace name and symbol (falsy check passes for spaces)
4. `koink_tokens` table missing `archived`/`deleted_at` — inconsistent with codebase pattern
5. `/koink/status` endpoint exposes `phase_1_blocker` text publicly (minor opsec)

**What's good:** All SQL parameterized (no injection), VRF provider per-chain logic correct, dual-insert transaction correct, feature flag gates all mutation endpoints, validate_koink_params has cross-field constraint (floor ≤ initial), architecture plan matched faithfully.

**Why:** NEEDS_CHANGES before Phase 1 to prevent 500 errors on malformed requests.
**How to apply:** UUID path param validation is a recurring pattern to watch in this codebase — always type FastAPI path params as `UUID` not `str` when they're IDs.

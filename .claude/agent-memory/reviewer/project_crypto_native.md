---
name: crypto_native_phase1_review
description: Code review of native crypto engine Phase 1 (commit 8cef2fb, 2026-03-19) — patterns and issues to watch in Phase 2/3
type: project
---

Native crypto engine Phase 1 reviewed 2026-03-19. VERDICT: NEEDS_CHANGES (minor — no blockers for Phase 2).

**Why:** Phase 1 is deliberately incomplete stubs, but several patterns introduced here will carry forward into Phase 2 execution code and need fixing before they become real bugs.

**How to apply:** When reviewing Phase 2 (executor wiring, monitor polling), check these same files for the outstanding issues.

## Patterns that recur in this codebase (watch in Phase 2)

1. **No `limit` cap on list endpoints** — routes/crypto.py lines 257, 314, 351, 383 all accept unbounded `limit` integer. Add `Query(default=50, le=500)` FastAPI constraint.
2. **UUID inputs not validated before DB** — monitors.py:54, signals.py:60 pass string IDs directly to asyncpg. If non-UUID is passed, asyncpg raises DataError which bubbles as 500. Add try/except UUID parse or use Pydantic UUID type in route params.
3. **ERC-20 decimal assumption** — portfolio.py:120 hardcodes `/ 1e18` for all tokens. USDC=6 decimals will show values 1e12x wrong. Needs metadata call (alchemy_getTokenMetadata) in Phase 2.
4. **Module-level settings access** — portfolio.py:18-22, executor.py:17 build URLs at import time. Fragile but acceptable for Phase 1. Watch if settings become dynamic.
5. **`hasattr` config check** — routes/crypto.py:121 uses `hasattr(settings, 'cdp_api_key_name')`. This suggests the config attribute was added inconsistently. Verify CDP config is fully in config.py.
6. **`req.dict()` in routes/crypto.py:373** — Pydantic v2 deprecation. Should be `req.model_dump()`. Check which Pydantic version is running.
7. **No input validation on enum-like fields** — `direction` (signal), `monitor_type`, `chain` accept arbitrary strings. DB has no CHECK constraints on these in the migration. Phase 2 should add Pydantic validators.
8. **No rate limiting on /crypto/parse** — calls LLM on every request. Should add per-IP or global rate limiting before any public exposure.

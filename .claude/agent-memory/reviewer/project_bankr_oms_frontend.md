---
name: bankr_oms_frontend_review
description: Code review of BANKR OMS frontend page (commit c0e25a3, 2026-03-19) — crypto engine page at /crypto
type: project
---

OMS Crypto Engine frontend reviewed 2026-03-19. VERDICT: NEEDS_CHANGES (minor — no blockers).

**Why:** Page is functionally complete and builds clean. Three issues found: one React bug causing console warnings, one silent error suppression gap, one duplicate fetch inefficiency.

## Issues Found

1. **React key on fragment** (page.tsx:850): data.signals.map() uses <> fragment as outermost element without key. Console warnings + potential reconciliation issues with inline close form. Fix: use <React.Fragment key={s.id}>.

2. **Silent error suppression** (page.tsx:564, 806): handleCancel and handleClose catch errors silently. Mev gets no feedback on failure. Fix: add per-action error state.

3. **Duplicate /crypto/status fetch**: CryptoPage (line 1165) and StatusSection (line 208) both poll independently at 30s. Top-level fetch only derives 2 boolean flags. Fix: lift or eliminate duplicate.

## Suggestions
- Portfolio chains hardcoded to base,eth (line 433)
- data.features.launch not shown in status grid

## What's Good
- All 13 endpoints matched correctly
- Build clean, TypeScript clean
- Good empty states, graceful degradation
- useApi deps pattern used correctly

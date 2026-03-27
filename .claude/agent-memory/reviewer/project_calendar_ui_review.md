---
name: Unified Calendar UI review
description: Content calendar view Step 2 code review (commit 2342254, 2026-03-27, WF Step 2) — NEEDS_CHANGES (minor). 1 correctness bug, 3 warnings, 4 suggestions. Core architecture is solid.
type: project
---

Unified calendar UI + API (commit 2342254, 2026-03-27, WF Step 2): NEEDS_CHANGES (minor).

**Verdict**: No blockers. 1 correctness bug, 3 actionable warnings.

## Critical (must fix)
None — no security issues, no data loss paths.

## Warnings
1. **Unvalidated date strings → 500**: `date.fromisoformat()` raises ValueError on bad input in list_slots, get_stats, create_slot, generate_schedule. Returns 500 instead of 422. Pattern: wrap with try/except ValueError → HTTPException(422).
2. **TOCTOU in position auto-compute**: create_slot does SELECT MAX(slot_position) then INSERT separately. Two concurrent creates on same date can get same position. No UNIQUE constraint on (slot_date, platform, slot_position).
3. **Dead prop**: `stats` is in UnifiedCalendarViewProps interface but not destructured or used inside the component body. CalendarStatsResponse fetch is wasted.
4. **Silent failure**: handleMarkPosted uses `.then(refreshSlots)` with no `.catch()`. Error is swallowed. Consistent with existing codebase pattern but worth fixing.

## Suggestions
- Duplicate PLATFORM_BADGE/STATUS_BADGE constants in page.tsx and DayDetailPanel.tsx — extract to shared file
- `strategy` field in GenerateRequest is dead code (only "balanced" implemented, field never read)
- `<a>` inside `<DropdownMenuItem>` without `asChild` creates nested interactive elements — use asChild pattern
- ContentSlotPicker has no debounce on search — fires API on every keystroke after 2 chars

## What's Good
- Reorder endpoint uses proper transaction (async with conn.transaction())
- All path params typed as UUID (no 500 on invalid UUIDs in PUT/DELETE/POST routes)
- Today view nails the UX requirement: pinned "Start Here" section + single-click Posted button
- Migration CHECK constraints match frontend platform/action/status enums exactly
- SLOT_QUERY content join avoids N+1 fetch

**Pattern**: date string validation in query params + body strings (not UUID params) needs try/except → 422.

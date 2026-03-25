---
name: diff_versioning_content_hub_2026_03
description: Diff-based versioning architecture for OMS Content Hub — migration 076, /diff endpoint upgrade, VersionHistorySheet redesign
type: project
---

Content Hub diff-based versioning architecture designed (2026-03-25). This is a completion task — backend infrastructure already existed, gap was entirely in frontend.

**What exists (unchanged):**
- `content_versions` table: full snapshots, max 100 versions, auto-triggered on title/body/metadata/status/tags changes
- `GET /content/{id}/diff?v1=X&v2=Y` endpoint: functional, returns `{content_id, v1, v2, changes, fields_changed}`
- `VersionHistorySheet`: shows version list + full body preview, never calls `/diff`

**Three changes to implement:**
1. Migration 076: `ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS label TEXT;`
2. Backend: upgrade `/diff` — add `?mode=word|line` param, add `raw_old`/`raw_new` to body diff
3. Frontend: VersionHistorySheet — Diff/Preview tabs, auto-compare with v-1, `react-diff-viewer-continued`

**Critical implementation constraint:**
Frontend MUST pass raw body text to `react-diff-viewer-continued` (`oldValue=prev.body`, `newValue=curr.body`) — do NOT use `changes.body.diff` from the `/diff` endpoint. The library runs its own diff. Using the pre-computed unified diff string as input produces garbled output.

**Next migration number:** 076

**Why:** Full doc at ~/otto/docs/diff-versioning-architecture-2026-03-25.md
**How to apply:** Any implementation task for this feature must read the doc first. The `changed_fields` column semantics are non-obvious (points FORWARD, not backward) — document in code.

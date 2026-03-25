---
name: project_diff_versioning_final_review
description: Diff-based versioning engine final review (Step 3 fix pass, 2026-03-25): verdict, race condition, performance, edge cases
type: project
---

# Diff-Based Versioning — Final Review (Step 3 post-fix)

**Verdict: NEEDS_CHANGES (1 critical)**

Commits reviewed: fd16689 (content.py char-mode fix), 2af75ef (page.tsx double-save fix).
Prior issues from Step 2 review (char mode, double-save, silent error suppression, parallel fetch) are ALL confirmed fixed.

## Critical Issue

**Concurrent saves race condition — `content.py:362-419`**
`update_content` does: fetch existing → _snapshot → UPDATE, all inside a single `pool.acquire()` connection but **without a transaction or SELECT FOR UPDATE**. Two simultaneous PATCH requests can:
1. Both read the same version number
2. Both call `_snapshot()` at the same version — second INSERT hits `ON CONFLICT DO NOTHING`, silently discards the snapshot
3. Both increment to the same version number — last write wins, one edit is silently lost

Fix: wrap body in `async with conn.transaction():` and change the existing row fetch to `SELECT ... FOR UPDATE`.

## Warnings

- **3 separate DB queries in diff_versions without a transaction** (`content.py:576-601`): ver1, ver2, and current fetched separately. Concurrent restores between fetches could return inconsistent state. Low probability.
- **raw_old/raw_new doubles wire size for large articles** (`content.py:621-622`): Both raw bodies sent in every diff response even though frontend (ReactDiffViewer) re-diffs them client-side. The server-computed `word_diff` is then unused. Architecturally redundant — either drop `word_diff` or make `raw_old`/`raw_new` opt-in.
- **_snapshot prune uses NOT IN subquery** (`content.py:157-164`): `NOT IN` has surprising NULL behavior and is slower than EXISTS/CTE on large tables. Bounded by MAX_VERSIONS=100 so low impact now.
- **No auth on set_version_label** (`content.py:696`): Any caller can label any content version. Consistent with the rest of the API (gateway-level auth assumed) but worth noting.

## What's Good

- `ON CONFLICT DO NOTHING` in _snapshot prevents duplicate version noise
- Word-level SequenceMatcher with `autojunk=False` correct for prose
- `dynamic(..., {ssr: false})` for ReactDiffViewer is correct Next.js SSR pattern
- Migration 076 uses IF NOT EXISTS — fully idempotent
- Label length validation (100 chars) correct
- Promise.all parallel fetch for full version + diff is good perf pattern
- First version edge case correctly handled: prevVersion === null → "no previous version" message
- MAX_VERSIONS=100 pruning prevents unbounded growth

## Pattern

Read-modify-write in content routes consistently lacks transactions. All routes doing fetch-then-write should use `async with conn.transaction()` + `FOR UPDATE` to prevent phantom reads and version collisions.

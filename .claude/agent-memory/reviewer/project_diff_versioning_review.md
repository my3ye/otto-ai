---
name: project_diff_versioning_review
description: Diff-based versioning engine Step 2 code review (2026-03-25, commit 421a6f8): NEEDS_CHANGES (minor). 2 bugs flagged in label editing. char mode API contract misleading.
type: project
---

Diff-based versioning implementation Step 2 review (2026-03-25, commit 421a6f8): NEEDS_CHANGES (minor).

**Why:** Step 2 of WF "Implement diff-based versioning engine and storage layer" — code review pass.

**How to apply:** Step 3 should address the double-save bug and char mode before frontend is considered complete.

## Verdict: NEEDS_CHANGES (minor)

### Warnings (must fix before shipping)
1. **Double-save on Enter+blur** (`page.tsx:771-772`): label `onKeyDown` calls `handleSaveLabel(v)` on Enter; blur fires immediately after, calling it again. Two concurrent PATCH requests. Fix: add `if (savingLabel) return` guard to `onBlur`, or `e.preventDefault()` approach.
2. **`char` mode accepted but produces word-level output** (`content.py:572, 632`): API accepts `?mode=char`, validates it, but the `else` branch runs word-level `split()` for both "word" and "char". Callers get word diff when they requested char diff. Either implement char-level `list(old_body)` tokenization or remove "char" from accepted values.

### Suggestions
- Silent error suppression `catch { /* ignore */ }` in `handleSaveLabel` (page.tsx:705) — user gets no feedback if label save fails. Add toast or at least restore editingLabelId.
- `handleSelect` fetches full version then diff sequentially — parallelize with `Promise.all` to reduce latency.
- `DiffData` type doesn't include `word_diff?: ...` from API response body (unused but inaccurate).

### What's Good
- Migration 076: correct, `IF NOT EXISTS` guard, sparse partial index.
- `set_version_label`: proper 100-char validation, empty→null coercion, existence check before UPDATE, parameterized query (no injection risk).
- `VersionDiffView`: `dynamic()` + `ssr: false` is correct and required for browser-DOM diff viewer.
- Passes `raw_old`/`raw_new` as `oldValue`/`newValue` to `ReactDiffViewer` — NOT the pre-computed diff string. Correct.
- `DiffMethod` static import (not dynamic) is correct — enum value, no DOM APIs.
- Backward compat: `?mode=line` returns unified diff string as before.
- `_version_to_dict` uses `dict(row)` so `label` from `SELECT *` is included automatically.

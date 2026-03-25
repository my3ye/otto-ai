# Diff-Based Versioning System — Content Hub Architecture

**Date:** 2026-03-25
**Status:** Approved for implementation
**Source:** Research pipeline output (tasks e244d874, 45f0c9d4, 8d9a6309)
**Target:** OMS Content Hub (`mev.otto.lk/content-hub`)

---

## Design: Diff-Based Versioning for Content Hub

### Problem

Mev requested "a fine-grained view of exactly what changed in each version" in the OMS content hub. The backend versioning infrastructure is already complete and functional — `content_versions` table with full snapshots, a `/diff` endpoint using Python `difflib`. The entire gap is in the frontend: `VersionHistorySheet` shows version list and full body preview but never renders what changed between versions. Additionally, the backend diff is line-level only (one word change shows the entire paragraph as changed), and there are no named version labels.

**Scope: this is a completion task, not a new system.** ~1 day total effort.

---

### Current State (verified in codebase)

**Backend (fully implemented, no changes needed for MVP):**
```
content_versions table:
  id, content_id, version (int), title, body, metadata (JSONB),
  status, tags (text[]), changed_fields (text[]), change_note,
  changed_by, created_at

  UNIQUE(content_id, version)
  MAX_VERSIONS = 100 (oldest pruned automatically)
  Snapshot triggered by: title, body, metadata, status, tags changes
```

**Existing API (all implemented and working):**
```
GET /content/{id}/versions          — list (body truncated to 200 chars)
GET /content/{id}/versions/{v}      — full version content
POST /content/{id}/restore/{v}      — restore (auto-snapshots current first)
GET /content/{id}/diff?v1=X&v2=Y   — line-level unified diff
```

**Frontend gap (VersionHistorySheet, content-hub/page.tsx:600-742):**
- Left panel: version list (version number, timestamp, change_note, changed_fields)
- Right panel: full body rendered as Markdown (NO diff rendering)
- Restore button: works correctly
- **Never calls `/diff` endpoint**

---

### Approach

Three-layer change: one lightweight DB migration, one backend endpoint upgrade, one frontend component enhancement.

**Design principle:** Full snapshots stay (no delta-only migration). Industry standard for CMS. Snapshots enable arbitrary version reconstruction without chain traversal. The `/diff` endpoint remains a comparison utility, not the source of truth for reconstruction.

---

## 1. Data Model Changes

### Migration 076 — `content_versions` label column

```sql
-- Migration 076: Add named version labels to content_versions
ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS label TEXT;
CREATE INDEX idx_content_versions_label ON content_versions(content_id, label)
  WHERE label IS NOT NULL;
```

**Why:** Mev's original 2026-03-16 research request specified "named versions with timestamps." `change_note` is auto-generated, `label` is a user-assigned permanent name (e.g., "Post-review", "Published", "v2.0").

**Fields after migration:**

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Row PK |
| `content_id` | UUID | FK to content |
| `version` | INTEGER | Monotonic version number |
| `title` | TEXT | Snapshot of title |
| `body` | TEXT | Full snapshot of body (markdown prose) |
| `metadata` | JSONB | Snapshot of metadata fields |
| `status` | TEXT | Snapshot of status |
| `tags` | TEXT[] | Snapshot of tags |
| `changed_fields` | TEXT[] | Fields changed in the **next** version (points forward) |
| `change_note` | TEXT | Auto-generated or user-supplied change description |
| `changed_by` | TEXT | Who made the change |
| `label` | TEXT | **NEW** — optional named checkpoint |
| `created_at` | TIMESTAMPTZ | When this snapshot was taken |

**⚠️ `changed_fields` semantics:** This column is stored on the *old* snapshot pointing forward — it describes what changed when the system moved *away* from this version, not what changed *to produce* this version. When displaying "what changed to reach v5", look at the `changed_fields` on **v4** (the snapshot before it). The UI already handles this correctly.

**No other schema changes.** Pre-computed diff storage (`diff_json` column) is explicitly deferred — articles average ~3KB, recompute cost is ~1ms, premature optimization.

---

## 2. Versioning Lifecycle

### When snapshots are taken (current, unchanged)

| Event | Trigger | Behavior |
|-------|---------|----------|
| **Save** | `PUT /content/{id}` | Snapshots current state BEFORE applying changes, only if `_VERSIONABLE` fields changed |
| **Restore** | `POST /content/{id}/restore/{v}` | Auto-snapshots current state before overwrite |
| **Status change** | Part of save | `status` is in `_VERSIONABLE`, so publish/unpublish always snapshots |

### Autosave (proposed, not implemented yet)

Autosave (debounced, ~30s) would use the same `PUT /content/{id}` path with `change_note: "autosave"`. No special handling needed — the existing snapshot trigger fires on any versionable field change. Add `changed_by: "autosave"` to distinguish autosave snapshots in the UI (grey vs primary color in list).

### Named label checkpoints

Users can assign labels at any time via new `PATCH /content/{id}/versions/{v}/label`. A label marks a snapshot as a named milestone without triggering a new version. Labels persist across restores.

---

## 3. Diff Engine Interface

### Upgrade: line-level → word-level body diff

**Current:** `difflib.unified_diff(old.splitlines(), new.splitlines())` — entire paragraphs flagged when one word changes.

**Upgrade:** Word-token diff using `difflib.ndiff(old.split(), new.split())` with output restructured to HTML/token format. This is a built-in stdlib call, no new dependencies.

**Diff modes exposed via `?mode` param:**
- `word` (**default**) — word-level tokens. Best for prose articles.
- `line` — legacy line-level unified diff (backward compat, raw `diff` string)
- `char` — character-level via `difflib.SequenceMatcher` (for very short fields like titles)

### Fields diffed

| Field | Diff Method | Output |
|-------|-------------|--------|
| `body` | Word-level ndiff | `{old: str, new: str, word_diff: [{op, text}]}` |
| `title` | Simple equality | `{old: str, new: str}` |
| `status` | Simple equality | `{old: str, new: str}` |
| `tags` | Set diff | `{added: [...], removed: [...], unchanged: [...]}` |
| `metadata` | JSON key diff | `{added: {...}, removed: {...}, changed: {k: {old, new}}}` |

### Word diff token format

```python
# Word diff output token — used in body.word_diff array
{
  "op": "equal" | "insert" | "delete",
  "text": "word "
}
```

This maps directly to `react-diff-viewer-continued`'s word highlight model. The frontend does NOT use the token array for rendering — it passes raw `old`/`new` body strings directly to the library (which runs its own word diff internally). The token array is available for backend-side rendering or future export.

---

## 4. API Shape

### Existing endpoints (unchanged)

```
GET /content/{id}/versions
GET /content/{id}/versions/{v}
POST /content/{id}/restore/{v}
```

### Modified: GET /content/{id}/diff

**Current response** (verified in content.py:634-640):
```json
{
  "content_id": "uuid",
  "v1": 1,
  "v2": 2,
  "changes": {
    "body": { "old_length": 1200, "new_length": 1350, "diff": "--- v1\n+++ v2\n..." },
    "title": { "old": "Draft Title", "new": "Final Title" },
    "tags": { "added": ["web3"], "removed": [] },
    "metadata": { "old": {...}, "new": {...} }
  },
  "fields_changed": ["body", "title"]
}
```

**Upgraded response** (adds `raw_old`, `raw_new`, word diff, mode echo):
```json
{
  "content_id": "uuid",
  "v1": 1,
  "v2": 2,
  "mode": "word",
  "changes": {
    "body": {
      "old_length": 1200,
      "new_length": 1350,
      "raw_old": "The full previous body text...",
      "raw_new": "The full new body text...",
      "word_diff": [
        { "op": "equal", "text": "The " },
        { "op": "delete", "text": "old " },
        { "op": "insert", "text": "new " },
        { "op": "equal", "text": "body text..." }
      ],
      "diff": "--- v1\n+++ v2\n..."
    },
    "title": { "old": "Draft Title", "new": "Final Title" },
    "tags": { "added": ["web3"], "removed": [], "unchanged": ["article"] },
    "metadata": {
      "added": { "platform": "paragraph" },
      "removed": {},
      "changed": { "word_count": { "old": 820, "new": 950 } }
    }
  },
  "fields_changed": ["body", "title", "tags"]
}
```

**Query params:**
```
GET /content/{id}/diff?v1=3&v2=5          → mode=word (default)
GET /content/{id}/diff?v1=3&v2=5&mode=line → legacy line-level unified diff
GET /content/{id}/diff?v1=3&v2=5&mode=char → character-level (for titles)
```

**Backward compatibility:** `changes.body.diff` (unified diff string) remains in all modes. Existing callers are unaffected.

### New: PATCH /content/{id}/versions/{v}/label

```
PATCH /content/{id}/versions/{v}/label
Content-Type: application/json

{ "label": "Post-review draft" }

→ 200 { "ok": true, "version": 5, "label": "Post-review draft" }
→ 400 { "detail": "Label too long (max 100 chars)" }
→ 404 { "detail": "Version not found" }
```

To clear a label: `{ "label": null }`.

### Updated: GET /content/{id}/versions (includes label)

```json
{
  "versions": [
    {
      "id": "uuid",
      "content_id": "uuid",
      "version": 7,
      "title": "Final Title",
      "body_preview": "First 200 chars...",
      "status": "published",
      "tags": ["web3", "article"],
      "changed_fields": ["body", "tags"],
      "change_note": "Editorial pass",
      "changed_by": "mev",
      "label": "Published",
      "created_at": "2026-03-25T14:30:00Z"
    }
  ],
  "total": 7
}
```

### Updated: GET /content/{id}/versions/{v} (includes label)

Returns full version content including `label` field. Used by frontend to fetch raw body text for diff rendering.

---

## 5. UI Data Contract

### VersionHistorySheet — enhanced state

```typescript
// Additional state in VersionHistorySheet
const [viewMode, setViewMode] = useState<"preview" | "diff">("diff")
const [compareVersion, setCompareVersion] = useState<ContentVersion | null>(null)
const [diffData, setDiffData] = useState<DiffResult | null>(null)
const [loadingDiff, setLoadingDiff] = useState(false)
const [labelInput, setLabelInput] = useState("")
```

### On version select — auto-diff behavior

```typescript
async function handleSelect(v: ContentVersion) {
  setSelected(v)
  setViewMode("diff")  // default to diff view when selecting

  // Fetch full body for selected version
  const full = await apiGet<ContentVersion>(`/content/${item.id}/versions/${v.version}`)
  setFullVersion(full)

  // Auto-compare with previous version (v-1)
  const prevVersion = versions.find(ver => ver.version === v.version - 1)
  if (prevVersion) {
    setLoadingDiff(true)
    const prevFull = await apiGet<ContentVersion>(
      `/content/${item.id}/versions/${prevVersion.version}`
    )
    setCompareVersion(prevFull)
    setLoadingDiff(false)
  }
}
```

### Diff rendering contract

```typescript
// DO NOT use diffData.changes.body.diff (unified diff string)
// PASS raw body strings directly to react-diff-viewer-continued
// The library runs its own diff — passing a pre-diffed string produces garbage

import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued"

// Dynamic import required in Next.js (SSR incompatible)
const DiffViewer = dynamic(() => import("react-diff-viewer-continued"), { ssr: false })

// Render:
<DiffViewer
  oldValue={compareVersion?.body ?? ""}
  newValue={fullVersion?.body ?? ""}
  splitView={false}          // inline/unified view (prose-friendly)
  compareMethod={DiffMethod.WORDS}  // word-level diff
  hideLineNumbers={true}     // prose doesn't need line numbers
  useDarkTheme={true}        // match OMS dark theme
  styles={{
    contentText: { fontFamily: "var(--font-mono)", fontSize: "11px" },
    diffContainer: { background: "transparent" },
  }}
/>
```

### Field-level change badges (from /diff metadata)

The `/diff` endpoint `changes` object provides title/tags/status/metadata diffs. These render as compact badges above the diff view:

```typescript
// Fetch diff for field-level change metadata
async function loadFieldDiff(v1: number, v2: number) {
  const diff = await apiGet<DiffResponse>(
    `/content/${item.id}/diff?v1=${v1}&v2=${v2}`
  )
  setDiffData(diff)
}

// Render changed fields summary:
// [TITLE: "Draft" → "Final"] [TAGS: +web3] [STATUS: draft → published]
```

### Compare selector (manual override)

Clicking "Compare with..." reveals a version selector dropdown. Selecting any version from the list re-runs the comparison against the currently selected version. This is a simple state update — no new API endpoint needed.

### Label editing

Clicking the version label area (or an edit icon) shows an inline text input. On blur/enter: `PATCH /content/{id}/versions/{v}/label`. The label updates in the versions list in-place.

### Summary: what the frontend receives

| Data | Source | How used |
|------|--------|----------|
| Version list | `GET /versions` | Left panel list |
| Full body (selected version) | `GET /versions/{v}` | `newValue` for diff viewer |
| Full body (compare version) | `GET /versions/{v-1}` | `oldValue` for diff viewer |
| Field changes metadata | `GET /diff?v1&v2` | Change badges above diff |
| Label | `GET /versions` → `PATCH label` | Inline edit in list |

---

## Implementation Plan

### Phase 1 — Backend upgrades (2h)

**Step 1.1 — Migration 076**
```bash
# File: otto/memory/migrations/076_content_version_label.sql
ALTER TABLE content_versions ADD COLUMN IF NOT EXISTS label TEXT;
CREATE INDEX idx_content_versions_label ON content_versions(content_id, label)
  WHERE label IS NOT NULL;
```

**Step 1.2 — Upgrade `/diff` endpoint** (`content.py`)
- Add `mode: str = Query("word", ...)` param
- Add `raw_old`, `raw_new` to body diff response
- Add word-level diff: `difflib.ndiff(old_body.split(), new_body.split())`
- Add metadata structural diff (key-level, not just old/new)
- Add `unchanged` to tags diff
- Return `mode` in response

**Step 1.3 — Add PATCH label endpoint** (`content.py`)
- `PATCH /content/{id}/versions/{v}/label`
- Validate: max 100 chars, null to clear
- Return updated version row

**Step 1.4 — Include label in list/get endpoints**
- `GET /versions` query: add `label` to SELECT
- `GET /versions/{v}` query: already `SELECT *`, no change needed

### Phase 2 — Frontend (4-5h, includes SSR setup)

**Step 2.1 — Install library**
```bash
cd /home/web3relic/interfaces/web-next
pnpm add react-diff-viewer-continued
```

**Step 2.2 — Create DiffView component** (`components/content/VersionDiffView.tsx`)
- Dynamic import wrapper for SSR safety
- Accepts `oldBody`, `newBody`, `fieldChanges`
- Renders `ReactDiffViewer` with word diff + OMS dark theme
- Renders field change badges (title, status, tags)
- Loading skeleton

**Step 2.3 — Upgrade VersionHistorySheet** (`content-hub/page.tsx`)
- Add `viewMode` state (`"diff" | "preview"`)
- Add `compareVersion` state
- Add Diff/Preview toggle (Tabs component from shadcn/ui)
- On version select: auto-fetch v-1 for comparison, load diff metadata
- Wire DiffView into diff tab
- Keep existing Preview tab (Markdown render, unchanged)
- Add label inline edit: click label → input → blur/enter saves
- Add "Compare with..." dropdown for manual version selection

**Step 2.4 — Update ContentVersion type**
```typescript
// Add to ContentVersion interface
label?: string | null
```

### Phase 3 — Optional refinements (future)

- Autosave trigger (debounced 30s, `changed_by: "autosave"`)
- Collapse unchanged regions in diff view (long articles)
- Export diff as PDF/Markdown

---

## Key Decisions

- **Full snapshots retained, not replaced with diffs**: Reconstruction is O(1), no chain traversal. At ~3KB avg body and max 100 versions, storage is ~300KB per content item — negligible. Alternatives: delta-only (complex recovery), hybrid (premature complexity).

- **Frontend fetches raw body text, NOT the `/diff` endpoint body field**: `react-diff-viewer-continued` runs its own word diff from `oldValue`+`newValue`. Using the pre-computed `changes.body.diff` (a unified diff string) as input would produce garbled output ("diff of a diff"). The `/diff` endpoint is used only for field metadata (title/tags/status/metadata changes).

- **`word` mode as default**: Prose articles have long paragraphs. Line-level diff (current) flags entire paragraphs for single-word changes — not fine-grained. Word-level is what "exactly what changed" means for prose. `line` mode kept for backward compatibility.

- **Dynamic import for diff viewer**: `react-diff-viewer-continued` uses browser DOM APIs not available in SSR. Next.js requires `dynamic(() => import(...), { ssr: false })`. Missing this causes hydration errors — budget 30min for this.

- **Migration 076 not 077**: Last confirmed migration is 075 (reflection_versions from EMRS). 076 is available.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| SSR hydration error from diff viewer | Dynamic import with `ssr: false`, test in dev before pushing |
| `changed_fields` semantic confusion in diff UI | Document clearly: show `v.changed_fields` from the PREVIOUS version entry (not the selected) |
| Word diff for very long bodies (10KB+) | `difflib.ndiff` is O(n²) in worst case. At 10KB body = ~1500 words, this is ~0.5ms. No issue at current article sizes. |
| Version list order vs `changed_fields` direction | `changed_fields` on version N describes "what will change in N+1". Always display N+1's label as context when showing N. The list renders newest-first — this is already correct. |

---

## File Locations

| File | Change |
|------|--------|
| `otto/memory/migrations/076_content_version_label.sql` | New migration |
| `otto/memory/routes/content.py` | Upgrade `/diff`, add PATCH label, include label in list/get |
| `interfaces/web-next/src/app/content-hub/page.tsx` | VersionHistorySheet upgrade |
| `interfaces/web-next/src/components/content/VersionDiffView.tsx` | New diff view component |
| `interfaces/web-next/package.json` | `react-diff-viewer-continued` added |

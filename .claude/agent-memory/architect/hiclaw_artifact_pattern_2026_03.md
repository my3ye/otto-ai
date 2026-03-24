---
name: hiclaw_artifact_pattern_2026_03
description: HiClaw GAP-2 implementation design: artifact path references for large task outputs. 3-file change, no migration. Full doc location.
type: project
---

Artifact path reference pattern (HiClaw GAP-2) fully designed (2026-03-24).

**What it solves:** Task outputs > 2KB stored verbatim in DB cause context inflation in task chaining. `_inject_dep_outputs()` in task_plans.py injects 3000-char truncated output per dep; workflow step chaining injects 8000 chars per step. Large research outputs (3-20KB) get mangled.

**Pattern:** Write large outputs to `~/otto/logs/tasks/{task_id}/output.md`. Store path in `metadata.artifact_path`. Store summary (first 500 chars + path) in DB `output` field. Inject code reads file for full content when chaining.

**3 files to modify:**
1. `task_runner.sh` (~line 777): write artifact after truncation check; rewrite OUTPUT to summary; pass artifact_path to RESULT_JSON metadata
2. `memory/routes/task_plans.py` `_inject_dep_outputs()`: read artifact file up to 6000 chars if metadata.artifact_path exists
3. `memory/routes/workflows.py` `_interpolate_step_prompt()`: resolve `[ARTIFACT: path]` values before 8000-char truncation

**No DB migration needed** — uses existing `metadata` JSONB column.
**Backward compatible** — falls back to current behavior if no artifact_path.
**Threshold:** 2048 chars.

**Why:** Mirrors HiClaw MinIO pattern on local FS. Solves DB bloat + context inflation without infrastructure overhead.
**How to apply:** When touching task completion flows or output injection, respect artifact_path pattern. Full design at ~/otto/docs/hiclaw-artifact-path-architecture-2026-03-24.md.

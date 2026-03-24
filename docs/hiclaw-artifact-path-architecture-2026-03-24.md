# HiClaw GAP-2 Implementation: Artifact Path References
## Architecture Design
### Date: 2026-03-24

---

## Design: Artifact Path References for Large Task Outputs

### Problem

Task outputs > 2KB (common for research, code diffs, architecture docs) are stored verbatim in PostgreSQL's `output TEXT` column and injected wholesale into dependent tasks' prompts. This creates:

1. **DB bloat** — large TEXT values go to TOAST storage; routine fetches load full output even when only a summary is needed
2. **Context inflation** — `_inject_dep_outputs()` injects up to 3000 chars of truncated output per dependency; workflows inject up to 8000 chars per step. A 4-task chain where each step produces 5KB of output injects 12-32KB of injected context into the final task.
3. **Loss of fidelity** — truncation is lossy. Step 3 of a pipeline may need the full step-1 research output, but only gets 3000 chars of it.
4. **No persistent artifact storage** — output only lives in DB; if cleaned, it's gone.

This mirrors HiClaw's MinIO artifact pattern: workers write large outputs to object storage and reference the path, rather than embedding full content in the coordination layer.

### Approach

**When task output > ARTIFACT_THRESHOLD (2048 chars):**

1. `task_runner.sh` writes full output to `~/otto/logs/tasks/{task_id}/output.md`
2. The DB `output` field stores a brief summary: first 500 chars + path reference
3. DB `metadata.artifact_path` stores the full path for programmatic access
4. `_inject_dep_outputs()` (task_plans.py) reads the artifact file when available, injecting up to 6000 chars (vs current 3000 of truncated text)
5. `_interpolate_step_prompt()` (workflows.py) reads artifact files for step outputs

**No DB migration needed** — uses existing `metadata` JSONB column.

**Backward compatible** — if `metadata.artifact_path` is absent, existing truncation behavior is preserved.

### Key Decisions

- **Threshold: 2048 chars**: Research outputs average 3-20KB. Code diffs similar. 2KB is a comfortable cut-off below which inline storage is fine. Alternative (8KB) was rejected — too permissive, still causes context inflation on 4+ step chains.

- **Location: `~/otto/logs/tasks/{task_id}/output.md`**: Stays with existing per-task log infrastructure. `{task_id}` is already the log directory key. Alternative (flat file by short ID) was rejected — UUID directories prevent collisions.

- **Summary format in DB output field**: `[ARTIFACT: {path}]\n\n{first 500 chars of output}\n...[truncated, see artifact]`. This lets heartbeat/review quickly see the start without loading the file, while the path is always machine-readable.

- **Artifact injection limit: 6000 chars**: Higher than current 3000-char truncated injection because we're reading from the full artifact file, not from the already-truncated DB field. Still bounded to avoid context explosion. Workflows retain their existing 8000-char cap.

- **File is primary, DB is index**: The artifact file is the authoritative output. The DB `output` field is the summary + pointer. This is the same pattern as HiClaw's MinIO + task status table.

### API / Interface

No API changes needed. Existing `GET /tasks/{id}` returns:
```json
{
  "output": "[ARTIFACT: /home/web3relic/otto/logs/tasks/{id}/output.md]\n\n{first 500 chars}...",
  "metadata": {
    "artifact_path": "/home/web3relic/otto/logs/tasks/{id}/output.md",
    "artifact_bytes": 12345,
    "sofai_lm": {...}
  }
}
```

The OMS task detail page already renders `output` as text — the artifact path in the summary makes it human-readable. A future OMS enhancement could add a "View Full Artifact" button, but that's not in scope here.

### Affected Files

| File | Change | Risk |
|---|---|---|
| `~/otto/task_runner.sh` | After output capture (~line 770), check length; if > 2KB write to artifact file, rewrite OUTPUT to summary+path | Low — only changes output representation, not control flow |
| `~/otto/memory/routes/task_plans.py` | `_inject_dep_outputs()`: if dep has `artifact_path` in metadata, read file up to 6000 chars instead of using DB `output` column | Low — falls back to current behavior if no artifact |
| `~/otto/memory/routes/workflows.py` | `_interpolate_step_prompt()`: step_outputs values that look like artifact paths get resolved to file content | Low — falls back to existing behavior |

### Implementation Plan

#### Step 1 — task_runner.sh artifact write (smallest, most impactful)

After line 777 (after truncation check), insert:

```bash
# ── HiClaw GAP-2: Artifact Path References ─────────────────────────────────
# When output > 2KB, write full output to a persistent artifact file.
# Store only a summary + path reference in the DB output field.
# This prevents DB bloat and context inflation in task chaining.
ARTIFACT_THRESHOLD=2048
ARTIFACT_PATH=""
if [ ${#OUTPUT} -gt $ARTIFACT_THRESHOLD ] && [ "$EXIT_CODE" -eq 0 ]; then
    ARTIFACT_DIR="${LOG_DIR}/${TASK_ID}"
    mkdir -p "$ARTIFACT_DIR"
    ARTIFACT_PATH="${ARTIFACT_DIR}/output.md"
    echo "$OUTPUT" > "$ARTIFACT_PATH"
    ARTIFACT_BYTES=${#OUTPUT}
    ARTIFACT_SUMMARY="${OUTPUT:0:500}"
    OUTPUT="[ARTIFACT: ${ARTIFACT_PATH}]

${ARTIFACT_SUMMARY}
...[${ARTIFACT_BYTES} bytes total — full output at: ${ARTIFACT_PATH}]"
    log "GAP-2: artifact written (${ARTIFACT_BYTES} bytes) → ${ARTIFACT_PATH}"
fi
# ── End Artifact Path References ────────────────────────────────────────────
```

Then in the RESULT_JSON python3 call, add `artifact_path` to metadata:

```bash
RESULT_JSON=$(python3 -c "
import json, sys
meta = json.loads(sys.argv[4])
if sys.argv[5]:
    meta['artifact_path'] = sys.argv[5]
    meta['artifact_bytes'] = int(sys.argv[6])
print(json.dumps({
    'output': sys.argv[1] if sys.argv[1] else None,
    'error': sys.argv[2] if sys.argv[2] else None,
    'exit_code': int(sys.argv[3]),
    'metadata': meta,
}))
" "$OUTPUT" "$STDERR" "$EXIT_CODE" "$META_PAYLOAD" "$ARTIFACT_PATH" "${ARTIFACT_BYTES:-0}")
```

#### Step 2 — task_plans.py _inject_dep_outputs()

Replace the `LEFT(output, 3000)` query with a function that reads the artifact file if available:

```python
async def _inject_dep_outputs(pool, task_id: UUID):
    """Enrich a task's prompt with outputs from its completed dependencies."""
    row = await pool.fetchrow(
        "SELECT depends_on, prompt FROM tasks WHERE id = $1",
        task_id,
    )
    if not row or not row["depends_on"]:
        return

    deps = await pool.fetch("""
        SELECT title, LEFT(output, 6000) as output, metadata
        FROM tasks
        WHERE id = ANY($1) AND status = 'completed' AND output IS NOT NULL
    """, row["depends_on"])

    if not deps:
        return

    enrichment = "\n\n--- Context from completed prerequisites ---\n"
    for dep in deps:
        dep_meta = dep['metadata'] or {}
        if isinstance(dep_meta, str):
            try:
                dep_meta = json.loads(dep_meta)
            except Exception:
                dep_meta = {}

        artifact_path = dep_meta.get('artifact_path')
        if artifact_path and os.path.exists(artifact_path):
            try:
                with open(artifact_path, 'r') as f:
                    dep_output = f.read(6000)  # read up to 6000 chars
                log.debug(f"GAP-2: injecting artifact {artifact_path[:60]} for dep {dep['title'][:40]}")
            except Exception:
                dep_output = dep['output']  # fallback to DB output
        else:
            dep_output = dep['output']

        enrichment += f"\n### {dep['title']}\n{dep_output}\n"

    new_prompt = row["prompt"] + enrichment
    await pool.execute(
        "UPDATE tasks SET prompt = $2 WHERE id = $1",
        task_id, new_prompt,
    )
```

#### Step 3 — workflows.py _interpolate_step_prompt()

In the step_outputs loop (around line 147), resolve artifact paths before truncation:

```python
for pos, output in step_outputs.items():
    output_str = str(output)
    # GAP-2: if output is an artifact reference, try to read the file
    if output_str.startswith("[ARTIFACT:"):
        import re, os
        m = re.search(r'\[ARTIFACT: ([^\]]+)\]', output_str)
        if m:
            artifact_path = m.group(1)
            if os.path.exists(artifact_path):
                try:
                    with open(artifact_path, 'r') as f:
                        output_str = f.read(8000)
                except Exception:
                    pass
    values[f"step_{pos}_output"] = output_str[:8000]
```

#### Step 4 — Verify with a test

After deployment, monitor the next large-output task (research sweep, architecture doc) to confirm:
- Artifact file exists at expected path
- DB output field contains summary + path
- Dependent task prompt contains artifact content (not just the truncated summary)

### Risks

- **Disk space**: Each artifact write consumes local disk. At 42% disk usage with 68GB boot disk, this is ~39GB free. A 20KB artifact per task × 100 tasks/day = 2MB/day — negligible. Existing log rotation (if any) should be extended to cover artifact files.

- **File access from API**: `task_plans.py` and `workflows.py` now do file I/O in async FastAPI handlers. This is a minor anti-pattern (sync I/O in async context). Mitigation: use `asyncio.get_event_loop().run_in_executor()` for the file read, or accept the small blocking penalty (< 1ms for 6KB file read).

- **Artifact unavailability**: If the log disk is full or the file is deleted, artifact-reading code falls back to DB output. No data loss, just degraded injection quality.

- **QA runner**: `qa_runner.sh` reads task output from the API. If output now contains `[ARTIFACT: ...]` prefix, the QA diff comparison still works — it sees the summary + path reference. For large code-change tasks, QA reviewer already uses git diff, not the output field. No regression.

### Implementation Cost

- Step 1 (task_runner.sh): ~25 lines bash, 30 minutes, ~$0.50
- Step 2 (task_plans.py): ~20 lines Python, 20 minutes, ~$0.40
- Step 3 (workflows.py): ~15 lines Python, 15 minutes, ~$0.30
- Step 4 (verify): 15 minutes, ~$0.30

**Total: ~$1.50, ~1.5 hours**

---

## What We're NOT Implementing (from gap analysis)

**GAP-3 (prompt fix)**: Heartbeat using direct `/tasks` POST instead of `/task-plans` for multi-step work. This is a 2-line prompt edit in `heartbeat.md`. Implementation agent should add:
> "When creating multiple related tasks, ALWAYS use POST /task-plans instead of multiple POST /tasks calls. Direct /tasks POST is only for single independent tasks."

**GAP-1 (credential isolation)**: Low risk on single-tenant VM. Skip for now.

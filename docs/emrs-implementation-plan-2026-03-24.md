# EMRS Implementation Plan
**Step 0 output — Architecture & Planning**
**Date:** 2026-03-24
**Source design:** docs/evolvable-meta-reflection-architecture-2026-03-24.md

---

## Codebase State (verified)

| Fact | Value |
|------|-------|
| reflection.md lines | 1249 |
| Step 0 (workspace handoff) | lines 98–110 |
| Step 7c (AutoEvolve) | line 1093 |
| Step 7b/handoff (CAT protocol) | line 1167 |
| Last migration | 074_workflow_gates.sql |
| autoevolve.py endpoints | /experiments, /generation, /insights (NO /versions) |
| meta_memory.json | DOES NOT EXIST |
| self_patch.py | staged-only, never auto-applies |

---

## Phase 1: Fix Root Cause (~$3–4)

### 1a. Insert Step 0.5 into reflection.md

**File:** `otto/.claude/agents/reflection.md`

**Where:** After line 110 (end of Step 0 block — after the closing ``` of the curl commands, before the `---` separator at line 111).

**What to insert** (~45 lines):

```markdown
---

### Step 0.5: Cycle Classification (ALWAYS RUN — 2 min max)

Read meta-state for this cycle:

```bash
# Load meta memory (cross-session causal state)
META=$(cat ~/otto/meta_memory.json 2>/dev/null || echo '{"rl2f_trend":{"direction":"unknown","cycles_since_improvement":0},"autoevolve_state":{"generation":1,"experiments_this_generation":0},"reflection_versions":{"pending_patches":[]}}')
echo "$META" | python3 -m json.tool 2>/dev/null | head -30

# Queue state
curl -sf http://localhost:8100/tasks/queue/status | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Queue: pending={d.get(\"pending\",0)} running={d.get(\"running\",0)}')"

# RL2F accuracy
curl -sf http://localhost:8100/rl2f/accuracy | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'RL2F: {d.get(\"accuracy\",\"?\")}')" 2>/dev/null || echo "RL2F: unavailable"
```

**Classify this cycle (write into Current State scratchpad):**

```
CYCLE_TYPE = IDLE      if: queue pending=0 AND rl2f not worsening this cycle
CYCLE_TYPE = DEGRADED  if: rl2f_trend.direction="declining" AND cycles_since_improvement >= 3
                           OR autoevolve_state.experiments_this_generation=0 AND generation stuck > 5 cycles
CYCLE_TYPE = CRITICAL  if: system health failure (disk >90%, memory OOM, timer down)
CYCLE_TYPE = HEALTHY   otherwise
```

**Branch:**
- **IDLE or DEGRADED** → Set `GOTO_AUTOEVOLVE_FIRST=true` in Current State. After completing Steps 1–3 (reconcile, quick MARS, health), **jump to Step 7c (AutoEvolve) before Steps 4–6.**
- **CRITICAL** → Set `GOTO_AUTOEVOLVE_FIRST=false`. Skip Steps 4–5, focus on Step 6 health + blockers only.
- **HEALTHY** → Standard linear flow. AutoEvolve at Step 7c as usual.

Record classification: `Cycle type: [IDLE|DEGRADED|HEALTHY|CRITICAL] — reason: [brief]`
```

### 1b. Add meta_memory read to Step 0 and write to Step 8

**Step 0 addition** (after the workspace handoff reads, line ~107):
```markdown
Also load meta_memory (cross-cycle causal state — do not skip):
```bash
cat ~/otto/meta_memory.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'meta_memory: rl2f={d[\"rl2f_trend\"][\"direction\"]}, autoevolve_gen={d[\"autoevolve_state\"][\"generation\"]}, experiments={d[\"autoevolve_state\"][\"experiments_this_generation\"]}')" 2>/dev/null || echo "meta_memory: not found (will bootstrap)"
```
```

**Step 8 / Handoff addition** (at end of reflection cycle, after the episodic log):
```markdown
### Update meta_memory.json

Write back cross-cycle state atomically:

```bash
# Get current RL2F accuracy
RL2F_NOW=$(curl -sf http://localhost:8100/rl2f/accuracy | python3 -c "import sys,json; print(json.load(sys.stdin).get('accuracy', 0.30))" 2>/dev/null || echo "0.30")
# Get autoevolve generation
AE_GEN=$(curl -sf http://localhost:8100/autoevolve/generation | python3 -c "import sys,json; print(json.load(sys.stdin).get('current_generation', 1))" 2>/dev/null || echo "1")
# Get experiment count this generation
AE_EXP=$(curl -sf "http://localhost:8100/autoevolve/experiments?status=active&limit=20" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

# Write atomically
python3 -c "
import json, os, datetime

meta_path = os.path.expanduser('~/otto/meta_memory.json')
tmp_path = os.path.expanduser('~/otto/.meta_memory.json.tmp')

# Load existing or defaults
try:
    with open(meta_path) as f:
        m = json.load(f)
except:
    m = {'schema_version': 1, 'rl2f_trend': {'historical': []}, 'autoevolve_state': {}, 'causal_hypotheses': [], 'reflection_versions': {'pending_patches': []}}

now = datetime.datetime.utcnow().isoformat() + 'Z'
rl2f = float('$RL2F_NOW')
prev = m.get('rl2f_trend', {}).get('last_7d_accuracy', rl2f)
direction = 'declining' if rl2f < prev - 0.02 else ('improving' if rl2f > prev + 0.02 else 'stable')

m['last_updated'] = now
m['rl2f_trend']['last_7d_accuracy'] = rl2f
m['rl2f_trend']['direction'] = direction
cycles_since = m.get('rl2f_trend', {}).get('cycles_since_improvement', 0)
m['rl2f_trend']['cycles_since_improvement'] = 0 if direction == 'improving' else cycles_since + 1
if not m['rl2f_trend'].get('historical'):
    m['rl2f_trend']['historical'] = []
m['rl2f_trend']['historical'].append({'date': now[:10], 'accuracy': rl2f})
m['rl2f_trend']['historical'] = m['rl2f_trend']['historical'][-30:]  # keep last 30

m['autoevolve_state']['generation'] = int('$AE_GEN')
m['autoevolve_state']['experiments_this_generation'] = int('$AE_EXP')

with open(tmp_path, 'w') as f:
    json.dump(m, f, indent=2)
os.rename(tmp_path, meta_path)
print(f'meta_memory updated: rl2f={rl2f:.2f} ({direction}), ae_gen={AE_GEN}')
"
```
```

### 1c. Bootstrap meta_memory.json

**File:** `~/otto/meta_memory.json` (CREATE)

```json
{
  "schema_version": 1,
  "last_updated": "2026-03-24T17:00:00Z",
  "rl2f_trend": {
    "last_7d_accuracy": 0.30,
    "direction": "declining",
    "cycles_since_improvement": 12,
    "last_improvement_date": null,
    "historical": [
      {"date": "2026-03-17", "accuracy": 0.60},
      {"date": "2026-03-24", "accuracy": 0.30}
    ]
  },
  "autoevolve_state": {
    "generation": 1,
    "active_experiment_id": null,
    "last_experiment_date": null,
    "experiments_this_generation": 0,
    "outcomes": {"keep": 0, "discard": 0}
  },
  "causal_hypotheses": [
    {
      "id": "h001",
      "hypothesis": "AutoEvolve never fires because it sits at Step 7c (line 1093 of 1249), which budget cannot reach in a $1.00 session",
      "confidence": 0.9,
      "supporting_evidence": ["generation stuck at 1 since 2026-03-18", "budget logs show ~$0.95 spent before step 7"],
      "created_at": "2026-03-24",
      "tested": false,
      "outcome": null
    }
  ],
  "best_cycle_analysis": {
    "best_rl2f_score": 0.60,
    "best_cycle_date": "2026-03-17",
    "what_was_different": "Initial RL2F calibration — entries were novel, no plateau"
  },
  "forward_plans": [
    {
      "priority": 1,
      "action": "Move AutoEvolve to Step 1 on IDLE/DEGRADED cycles via Step 0.5 classifier",
      "expected_impact": "AutoEvolve fires at least 1x per 48h instead of 0x",
      "status": "in_progress",
      "proposed_patch_id": null
    }
  ],
  "reflection_versions": {
    "current_version": 0,
    "pending_patches": [],
    "auto_apply_enabled": false,
    "veto_window_hours": 48
  }
}
```

---

## Phase 2: Versioned Manifest (~$4–5)

### 2a. Migration 075

**File:** `otto/memory/migrations/075_reflection_versions.sql`

```sql
-- Migration 075: reflection_versions
-- Tracks self-modifications to core agent files for auditability + auto-rollback

CREATE TABLE IF NOT EXISTS reflection_versions (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version         INTEGER NOT NULL,
    target_file     TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    diff            TEXT NOT NULL,
    patch_summary   TEXT NOT NULL,
    hypothesis      TEXT,
    experiment_id   UUID,  -- no FK constraint — experiments table may not exist

    rl2f_before     FLOAT,
    rl2f_after      FLOAT,

    status          TEXT NOT NULL DEFAULT 'pending_veto',
    -- pending_veto | active | rolled_back | kept | auto_rolled_back | vetoed

    applied_at      TIMESTAMPTZ,
    veto_expires_at TIMESTAMPTZ,
    evaluated_at    TIMESTAMPTZ,
    reverted_at     TIMESTAMPTZ,
    revert_reason   TEXT,

    source          TEXT DEFAULT 'autoevolve',
    approved_by     TEXT,

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ DEFAULT NULL,
    archived        BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_rv_target ON reflection_versions(target_file);
CREATE INDEX idx_rv_status ON reflection_versions(status);
CREATE INDEX idx_rv_version ON reflection_versions(version, target_file);

CREATE VIEW rollback_candidates AS
    SELECT *
    FROM reflection_versions
    WHERE status = 'active'
      AND rl2f_after IS NOT NULL
      AND rl2f_before IS NOT NULL
      AND (rl2f_before - rl2f_after) > 0.15
      AND archived = FALSE
      AND deleted_at IS NULL;
```

### 2b. autoevolve.py — version endpoints

**File:** `otto/memory/routes/autoevolve.py`

Add after existing endpoints (after line 360):

```python
# ── Reflection Versions ─────────────────────────────────────────────────────

class ReflectionVersionCreate(BaseModel):
    target_file: str
    version: int
    content_hash: str
    diff: str
    patch_summary: str
    hypothesis: Optional[str] = None
    experiment_id: Optional[UUID] = None
    rl2f_before: Optional[float] = None
    source: str = "autoevolve"

class ReflectionVersionOut(BaseModel):
    id: UUID
    version: int
    target_file: str
    content_hash: str
    diff: str
    patch_summary: str
    hypothesis: Optional[str]
    rl2f_before: Optional[float]
    rl2f_after: Optional[float]
    status: str
    applied_at: Optional[datetime]
    veto_expires_at: Optional[datetime]
    evaluated_at: Optional[datetime]
    created_at: datetime

@router.post("/versions", response_model=ReflectionVersionOut, status_code=201)
async def create_version(body: ReflectionVersionCreate):
    """Record a self-modification patch — enters pending_veto state."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = datetime.now(timezone.utc)
        veto_exp = now + timedelta(hours=48)
        row = await conn.fetchrow("""
            INSERT INTO reflection_versions
              (version, target_file, content_hash, diff, patch_summary, hypothesis,
               experiment_id, rl2f_before, source, applied_at, veto_expires_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING *
        """, body.version, body.target_file, body.content_hash, body.diff,
            body.patch_summary, body.hypothesis, body.experiment_id,
            body.rl2f_before, body.source, now, veto_exp)
        return dict(row)

@router.get("/versions", response_model=list[ReflectionVersionOut])
async def list_versions(target_file: Optional[str] = None, status: Optional[str] = None, limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        q = "SELECT * FROM reflection_versions WHERE archived=FALSE AND deleted_at IS NULL"
        params = []
        if target_file:
            params.append(target_file); q += f" AND target_file=${len(params)}"
        if status:
            params.append(status); q += f" AND status=${len(params)}"
        params.append(limit); q += f" ORDER BY created_at DESC LIMIT ${len(params)}"
        rows = await conn.fetch(q, *params)
        return [dict(r) for r in rows]

@router.get("/versions/{version_id}", response_model=ReflectionVersionOut)
async def get_version(version_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM reflection_versions WHERE id=$1", version_id)
        if not row: raise HTTPException(404, "Version not found")
        return dict(row)

@router.post("/versions/{version_id}/veto")
async def veto_version(version_id: UUID):
    """Mev rejects a pending patch within the veto window."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE reflection_versions SET status='vetoed', evaluated_at=NOW() WHERE id=$1 RETURNING id, status",
            version_id)
        if not row: raise HTTPException(404, "Version not found")
        return {"id": str(row["id"]), "status": row["status"]}

@router.post("/versions/check-rollbacks")
async def check_rollbacks():
    """Called by reflection Step 6. Returns patches that need rolling back."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM rollback_candidates ORDER BY created_at ASC")
        return {"rollback_needed": [dict(r) for r in rows]}

@router.get("/meta-state")
async def get_meta_state():
    """Current EMRS summary for OMS dashboard."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM reflection_versions WHERE status='pending_veto' AND archived=FALSE AND deleted_at IS NULL")
        active = await conn.fetchval(
            "SELECT COUNT(*) FROM reflection_versions WHERE status='active' AND archived=FALSE AND deleted_at IS NULL")
        rollbacks = await conn.fetchval(
            "SELECT COUNT(*) FROM rollback_candidates")
        gen_row = await conn.fetchrow(
            "SELECT current_generation FROM autoevolve_experiments ORDER BY created_at DESC LIMIT 1")
        return {
            "pending_patches": pending,
            "active_patches": active,
            "rollback_candidates": rollbacks,
            "current_generation": gen_row["current_generation"] if gen_row else 1,
        }
```

### 2c. self_patch.py — version recording

**File:** `otto/tools/self_patch.py`

After applying a patch successfully, add a call to record the version:

```python
def record_version(target_rel: str, diff: str, patch_summary: str, hypothesis: str = None) -> Optional[str]:
    """Record applied patch to reflection_versions table via Memory API."""
    import subprocess, hashlib
    try:
        target_path = OTTO_ROOT / target_rel
        content_hash = hashlib.sha256(target_path.read_bytes()).hexdigest()
        # Get next version number for this file
        resp = requests.get(f"{MEMORY_API}/autoevolve/versions",
                           params={"target_file": target_rel, "limit": 1}, timeout=5)
        existing = resp.json() if resp.ok else []
        next_version = (existing[0]["version"] + 1) if existing else 1

        payload = {
            "version": next_version,
            "target_file": target_rel,
            "content_hash": content_hash,
            "diff": diff,
            "patch_summary": patch_summary,
            "hypothesis": hypothesis,
            "source": "self_patch",
        }
        r = requests.post(f"{MEMORY_API}/autoevolve/versions", json=payload, timeout=5)
        if r.ok:
            return r.json().get("id")
    except Exception as e:
        logger.warning(f"Failed to record version: {e}")
    return None
```

Call `record_version()` after the successful `_apply_patch()` in the `apply` command handler.

### 2d. reflection.md Step 6 — rollback check

**File:** `otto/.claude/agents/reflection.md`

In Step 6 (health check section), add after system health checks:

```markdown
**Check for auto-rollback candidates:**
```bash
ROLLBACKS=$(curl -sf -X POST http://localhost:8100/autoevolve/versions/check-rollbacks)
echo "$ROLLBACKS" | python3 -c "import sys,json; d=json.load(sys.stdin); n=len(d.get('rollback_needed',[])); print(f'Rollback candidates: {n}')"
```

If rollback_needed count > 0, for each candidate:
1. Note the `target_file` and `diff` from the record
2. Revert by applying the diff in reverse: `patch -R target_file < diff`
3. PATCH the record: `curl -sf -X POST http://localhost:8100/autoevolve/versions/{id}/veto` (reuse veto to close it)
4. Log to episodic: "Auto-rolled back version N of [file] — RL2F drop exceeded 15% threshold"
```

---

## Phase 3: OMS Visibility (~$3)

Out of scope for this workflow step. Separate task to add `/system` page tab.

---

## Execution Order for Implementation Agent

1. Create `~/otto/meta_memory.json` (bootstrap — no deps)
2. Apply reflection.md Step 0.5 insert (Phase 1a) — most critical fix
3. Apply reflection.md Step 0 meta_memory read addition (Phase 1b)
4. Apply reflection.md Step 8 meta_memory write addition (Phase 1b)
5. Run migration 075 (Phase 2a)
6. Add version endpoints to autoevolve.py (Phase 2b)
7. Add record_version to self_patch.py (Phase 2c)
8. Add rollback check to reflection.md Step 6 (Phase 2d)

**Minimum viable delivery:** Steps 1–4 only (Phase 1). AutoEvolve will fire on next idle cycle.

---

## Guardrails Summary

| Guardrail | Rule |
|-----------|------|
| G1 Budget floor | Core steps (MARS, GLOVE, health, handoff) always run — ~$0.30 total |
| G2 Scope cap | Max 50 lines per self-mod, max 3 pending patches |
| G3 Constitutional lock | CONSTITUTION.md / personality.md require Mev approval |
| G4 Version cap | AutoEvolve pauses if ≥3 patches in pending_veto |
| G5 Rollback trigger | 15% RL2F drop over 5 cycles → auto-revert |
| G6 Diversity | Next experiment must target different file than previous 3 |

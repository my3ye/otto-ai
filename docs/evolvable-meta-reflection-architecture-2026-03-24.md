# Evolvable Meta-Reflection System (EMRS)
**Design Author:** architect agent
**Date:** 2026-03-24
**Inputs:** reflection-meta-layer-gap-analysis-2026-03-24.md, HyperAgents arXiv:2603.19461, autoevolve.py, rl2f.py, reflection.md (1220 lines)
**Status:** Design ready for implementation

---

## Design: Evolvable Meta-Reflection System (EMRS)

### Problem

`reflection.md` is Otto's DGM bottleneck — a frozen meta-layer. The domain agent (heartbeat/orchestrator) improves via RL2F and MARS. The meta-agent (reflection.md itself) has never completed a self-modification cycle:

- AutoEvolve: **generation 1**, 0 active experiments since inception (2026-03-18)
- RL2F accuracy: **30% and declining** — trigger condition met but no response
- Root cause: AutoEvolve lives at Step 7c of a 1220-line document. Budget ($1.00) and time (10 min) are exhausted before reaching it.
- Secondary root cause: No cross-session causal memory — reflection cannot reason about *why* previous cycles scored higher or lower.

Per HyperAgents (2603.19461): when the meta-level is frozen (DGM-custom), self-improvement stalls at the domain it was engineered for. When the meta-level is editable (DGM-H), the system breaks out of that ceiling. Otto's gap is not in modification capability (self_patch.py exists) — it's in **execution priority** and **causal continuity**.

### Approach

Three interlocking components, each independently useful and incrementally deployable:

```
┌────────────────────────────────────────────────────────────────────┐
│                    EMRS Architecture                               │
│                                                                    │
│  ┌──────────────────┐    ┌─────────────────────┐                  │
│  │  meta_memory.json │    │ Cycle Classifier    │                  │
│  │  (causal memory)  │───▶│ (Step 0.5 in        │                  │
│  │                   │    │  reflection.md)      │                  │
│  │ - causal_hypotheses│   └────────┬────────────┘                  │
│  │ - best_cycle_data  │            │                               │
│  │ - forward_plans    │    IDLE    │  DEGRADED   │  HEALTHY         │
│  │ - rl2f_trend       │     ▼      │     ▼       │     ▼            │
│  └──────────────────┘  AutoEvolve  │  AutoEvolve │  Normal flow    │
│                        FIRST       │  FIRST      │  AutoEvolve     │
│                                    │             │  at end         │
│                                    ▼             │                  │
│           ┌──────────────────────────────────────┘                 │
│           │         Versioned Reflection Manifest                   │
│           │         (reflection_versions table)                     │
│           │                                                         │
│           │  version, content_hash, diff, applied_at               │
│           │  rl2f_before, rl2f_after, status                       │
│           │  auto_rollback trigger if rl2f drops >15%/5 cycles     │
│           └──────────────────────────────────────────────────────── │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component 1: `meta_memory.json` — Cross-Session Causal Learning

**What it is:** A persistent JSON file that survives across reflection cycles. The DGM-H insight: cross-domain transfer happens because the meta agent accumulates causal hypotheses across episodes. Otto's episodic substrate (S-MMU) exists, but nothing writes a cross-session causal layer for the meta-level itself.

**Location:** `~/otto/meta_memory.json`

**Schema:**
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
    "outcomes": {
      "keep": 0,
      "discard": 0
    }
  },
  "causal_hypotheses": [
    {
      "id": "h001",
      "hypothesis": "AutoEvolve never fires because it sits at Step 7c, which budget cannot reach",
      "confidence": 0.9,
      "supporting_evidence": ["generation stuck at 1 for 6 days", "budget logs show ~$0.95 spent before step 7"],
      "created_at": "2026-03-24",
      "tested": false,
      "outcome": null
    }
  ],
  "best_cycle_analysis": {
    "best_rl2f_score": 0.60,
    "best_cycle_date": "2026-03-17",
    "what_was_different": "Initial RL2F calibration period — entries were novel, no plateau",
    "steps_completed": ["0", "1", "2", "3", "4", "5", "5a", "5b", "5c"]
  },
  "forward_plans": [
    {
      "priority": 1,
      "action": "Move AutoEvolve to Step 1 on idle cycles",
      "expected_impact": "AutoEvolve fires at least 1x per 48h instead of 0x",
      "status": "proposed",
      "proposed_patch_id": null
    }
  ],
  "reflection_versions": {
    "current_version": 1,
    "pending_patches": [],
    "auto_apply_enabled": true,
    "veto_window_hours": 48
  }
}
```

**Read/write protocol:**
- **Read:** At reflection Step 0 (first action before any other step), load meta_memory.json via `cat ~/otto/meta_memory.json`
- **Write:** At Step 8 (handoff), update and write back with `python3 -c "import json; ..."`
- **Bootstrap:** If file absent, reflection creates it with defaults on first run
- **Conflict safety:** JSON write is atomic (write to `.meta_memory.json.tmp`, then `mv`)

**Why JSON over DB:** This file is read by the reflection agent (Claude Code session). Direct file reads are faster and more reliable in the Claude Code context than HTTP calls to the Memory API during an already-constrained 10-minute session.

---

## Component 2: Cycle Classifier — Adaptive Step Ordering

**What it is:** A new Step 0.5 inserted at the very top of the reflection cycle (after the ReflAct block). It reads system state and classifies the cycle type, then branches execution.

**Cycle types:**

| Type | Conditions | Action |
|------|-----------|--------|
| `IDLE` | Queue = 0, no Mev messages in 2h, RL2F stable | Jump to AutoEvolve → self_patch FIRST, then standard steps |
| `DEGRADED` | RL2F < 40% for 3+ consecutive cycles OR AutoEvolve stuck (>5 cycles, 0 experiments) | AutoEvolve as Step 1, compress other steps |
| `HEALTHY` | Normal operation, RL2F ≥ 40%, active task queue | Standard linear flow, AutoEvolve at end |
| `CRITICAL` | System health failures, blocker unresolved | Skip AutoEvolve entirely, focus on health + blocker |

**Step 0.5 implementation** (to insert in reflection.md after the ReflAct block):

```markdown
## Step 0.5: Cycle Classification (ALWAYS RUN — 2 min max)

Read meta_memory.json:
```bash
cat ~/otto/meta_memory.json 2>/dev/null || echo '{"rl2f_trend":{"direction":"unknown"},"autoevolve_state":{"generation":1}}'
```

Read queue status:
```bash
curl -s http://localhost:8100/tasks/queue/status
```

**Classify this cycle:**
- If queue=0 AND no Mev messages in 2h AND RL2F not declining: **IDLE → go to Step 7c FIRST**
- If rl2f_trend.direction="declining" AND cycles_since_improvement >= 3: **DEGRADED → go to Step 7c FIRST**
- If autoevolve_state.experiments_this_generation=0 AND generation stuck >5 cycles: **DEGRADED → go to Step 7c FIRST**
- If any system health failure: **CRITICAL → skip to Step 6**
- Otherwise: **HEALTHY → proceed linearly**

Record classification in Current State scratchpad.
```

**Why this fixes the root cause:** The only thing preventing AutoEvolve from running is execution order. Putting the classifier at the top and branching directly to AutoEvolve on IDLE/DEGRADED cycles means AutoEvolve fires every idle cycle instead of never.

---

## Component 3: Versioned Reflection Manifest

**What it is:** A DB table that tracks every self-modification to reflection.md (and any other core agent file), with version numbers, diffs, before/after metrics, and auto-rollback capability.

### Database Schema (Migration 075)

```sql
-- Migration 075: reflection_versions
-- Tracks all self-modifications to core agent files

CREATE TABLE IF NOT EXISTS reflection_versions (
    id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    version         INTEGER NOT NULL,
    target_file     TEXT NOT NULL,   -- e.g. '.claude/agents/reflection.md'
    content_hash    TEXT NOT NULL,   -- SHA256 of file content after patch
    diff            TEXT NOT NULL,   -- unified diff of what changed
    patch_summary   TEXT NOT NULL,   -- human-readable description
    hypothesis      TEXT,            -- why this change was made (links to autoevolve)
    experiment_id   UUID REFERENCES autoevolve_experiments(id),

    -- Metrics at time of patch
    rl2f_before     FLOAT,
    rl2f_after      FLOAT,           -- filled in after evaluation period

    -- Lifecycle
    status          TEXT NOT NULL DEFAULT 'pending_veto',
    -- pending_veto | active | rolled_back | kept | auto_rolled_back

    applied_at      TIMESTAMPTZ,     -- when patch was applied to file
    veto_expires_at TIMESTAMPTZ,     -- when auto-apply window opens (applied_at + 48h)
    evaluated_at    TIMESTAMPTZ,     -- when outcome was determined
    reverted_at     TIMESTAMPTZ,
    revert_reason   TEXT,

    -- Authorship
    source          TEXT DEFAULT 'autoevolve',  -- autoevolve | self_patch | manual
    approved_by     TEXT,            -- 'mev' | 'auto' | null

    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_reflection_versions_target ON reflection_versions(target_file);
CREATE INDEX idx_reflection_versions_status ON reflection_versions(status);
CREATE INDEX idx_reflection_versions_version ON reflection_versions(version);

-- Track rollback candidates: active patches where rl2f dropped significantly
CREATE VIEW rollback_candidates AS
    SELECT *
    FROM reflection_versions
    WHERE status = 'active'
      AND rl2f_after IS NOT NULL
      AND rl2f_before IS NOT NULL
      AND (rl2f_before - rl2f_after) > 0.15;  -- >15% degradation triggers auto-rollback
```

### Versioning Strategy

**Version number:** monotonically increasing integer per `target_file`. Each file has its own version counter.

**Diff format:** Unified diff (standard `diff -u` output) — stored as TEXT. Allows replay and reversal.

**Content hash:** SHA256 of file content after patch applied. Used to detect out-of-band modifications.

**Status machine:**
```
[proposed] → [pending_veto] → [active] → [kept]
                                       ↘ [rolled_back] (manual by Mev)
                                       ↘ [auto_rolled_back] (metric trigger)
```

**Auto-apply rule:** If `status = pending_veto` AND `veto_expires_at < NOW()` AND no Mev rejection → status transitions to `active`, patch applied to file.

**Auto-rollback rule:** Checked by reflection Step 6 (health check). If any `active` patch has `rl2f_before - rl2f_after > 0.15` after 5+ cycles of measurement → revert file to pre-patch content, status → `auto_rolled_back`.

### API Endpoints (add to autoevolve.py)

```python
# GET /autoevolve/versions?target_file=reflection.md
# List version history for a file

# GET /autoevolve/versions/{id}
# Get single version record with full diff

# POST /autoevolve/versions/{id}/veto
# Mev rejects pending patch (within veto window)

# POST /autoevolve/versions/{id}/approve
# Mev approves patch (skips veto window)

# POST /autoevolve/versions/check-rollbacks
# Called by reflection Step 6 — checks all active patches for metric degradation
# Returns list of patches that need rolling back, reflection handles the actual file ops
```

---

## Guardrails

### G1: Budget Floor — Core Steps Always Run
The following steps can NEVER be skipped even on CRITICAL cycles:
- MARS sweep (Step 5c) — normative principle extraction
- GLOVE verification (Step 5c-post) — memory accuracy
- System health (Step 6) — disk/memory/timer liveness
- Handoff write (Step 8) — cross-cycle continuity

Total budget for these: ~$0.30. This leaves ~$0.70 for variable steps.

### G2: Modification Scope Cap
- Max **50 lines changed** per self-modification cycle
- Max **1 patch pending per target file** at any time (queue cap)
- Max **3 total patches pending** across all files
- Patches to `reflection.sh`, `heartbeat.sh`, `task_runner.sh` require explicit RL2F degradation evidence (not just low accuracy)

### G3: Constitutional Lock
Modifications to these files require Mev approval (no auto-apply, no 48h veto window):
- `CONSTITUTION.md`
- `otto_core/personality.md`
- `otto_core/system_prompt.md`
- Any file containing identity or boundary definitions

Implementation: `self_patch.py` checks target_file against this list and sets `approved_by = 'mev_required'` status instead of `pending_veto`.

### G4: Version Cap
If ≥ 3 patches are in `pending_veto` status, AutoEvolve pauses experiment creation until at least 1 resolves. Prevents patch queue overflow.

### G5: Rollback Trigger
If RL2F 7-day accuracy drops > 15 percentage points over 5 consecutive cycles after a patch was applied → auto-revert. Reflection Step 6 checks `rollback_candidates` view and handles reversion.

### G6: Exploration Diversity Constraint
Each experiment must target a *different* component than the previous experiment. Enforced by checking `autoevolve_experiments` table — if the last 3 experiments all targeted `reflection.md`, the next must target a different file. This implements DGM-H's open-ended exploration component: the system is forced to search the modification space broadly, not fixate on one file.

---

## Trigger Conditions

| Trigger | Condition | Action |
|---------|-----------|--------|
| **AutoEvolve on IDLE** | queue=0, no Mev msgs 2h | Run AutoEvolve as Step 1 |
| **AutoEvolve on DEGRADED** | RL2F < 40% for 3+ cycles | Run AutoEvolve as Step 1 |
| **AutoEvolve stuck** | 0 experiments in 5+ cycles | Force Step 1 regardless of cycle type |
| **meta_memory update** | Every reflection cycle | Write causal hypotheses at Step 8 |
| **Auto-apply patch** | pending_veto AND veto_expires_at passed | Apply patch, set status=active |
| **Auto-rollback** | active patch AND rl2f_before - rl2f_after > 0.15 | Revert file, set status=auto_rolled_back |
| **Pause AutoEvolve** | 3+ patches pending | Skip experiment creation, drain queue first |

---

## API / Interface

### Memory API additions

```
GET  /autoevolve/versions            → list version history
GET  /autoevolve/versions/{id}       → single version + diff
POST /autoevolve/versions/{id}/veto  → Mev reject (sets status=vetoed)
POST /autoevolve/versions/check-rollbacks → reflection calls this at Step 6
GET  /autoevolve/meta-state          → current EMRS state summary
```

### meta_memory.json (file-based, not HTTP)
- Read via `cat` at reflection Step 0
- Write via atomic python3 JSON dump at Step 8
- No HTTP overhead — critical for 10-min budget

### OMS integration
- Add `reflection_versions` tab to OMS `/system` page
- Show: version history, pending patches with veto countdown, auto-rollback alerts
- "Approve" and "Veto" buttons per pending patch → POST to Memory API

---

## Implementation Plan

### Phase 1 — Fix the Root Cause (Highest ROI, ~$3–4)
*Can ship independently. Unblocks AutoEvolve immediately.*

**1a. Insert Step 0.5 into reflection.md** (~5 lines added at top)
Add cycle classifier after ReflAct block. Branch to Step 7c on IDLE/DEGRADED.
File: `otto/.claude/agents/reflection.md`
Test: Next IDLE reflection cycle should show "Cycle type: IDLE → jumping to AutoEvolve"

**1b. Bootstrap meta_memory.json**
Create initial file with current RL2F state and known causal hypothesis.
File: `~/otto/meta_memory.json`
Test: `cat ~/otto/meta_memory.json | python3 -m json.tool` succeeds

**1c. Add meta_memory read to Step 0 of reflection.md**
Prepend `cat ~/otto/meta_memory.json` before ReflAct.
Add meta_memory write to Step 8 (handoff).

### Phase 2 — Versioned Manifest (~$4–5)
*Adds safety/auditability to self-modification. Required before AutoEvolve auto-applies patches.*

**2a. Migration 075** — `reflection_versions` table + `rollback_candidates` view
File: `otto/memory/migrations/075_reflection_versions.sql`

**2b. Add version endpoints to autoevolve.py**
`GET /autoevolve/versions`, `POST /autoevolve/versions/{id}/veto`, `POST /autoevolve/versions/check-rollbacks`

**2c. Update self_patch.py** to write a `reflection_versions` record on every patch apply

**2d. Update reflection Step 6** to call `POST /autoevolve/versions/check-rollbacks` and handle any returned rollback candidates

### Phase 3 — OMS Visibility (~$3)
*Makes the system observable. Required for Mev to audit and veto patches.*

**3a. Add `reflection_versions` API to OMS** — new tab on `/system` page
Shows: version history, pending patches (with veto countdown timer), rollback alerts
Components: shadcn/ui Table + Badge + Button (Approve/Veto)

**3b. WhatsApp notification on pending patch**
When a patch enters `pending_veto`, send Mev a WhatsApp: "New reflection self-patch pending. 48h veto window. [summary]. Approve/veto at mev.otto.lk/system."

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Runaway self-modification loop | G2 (50-line cap) + G4 (3 patch queue cap) + G3 (constitutional lock) |
| AutoEvolve degrades reflection quality | G5 (auto-rollback at 15% RL2F drop over 5 cycles) |
| meta_memory.json corruption | Atomic write (tmp + mv), fallback to defaults on parse failure |
| Budget consumed by AutoEvolve before core steps | G1 (budget floor: core steps always run); AutoEvolve gets leftover budget |
| Patch queue deadlock (all 3 slots full, nothing resolves) | After 96h with no Mev veto, oldest patch auto-expires (not applied, just dropped) |
| Reflection freezes on reading large diffs | Store diff as TEXT, truncate display to 2000 chars in OMS; full diff always available via API |
| False RL2F rollback (noise, not signal) | Rollback only triggers after 5 consecutive declining cycles (not 1-2 which could be noise) |

---

## Relationship to Existing Systems

| Existing System | EMRS Interaction |
|----------------|-----------------|
| `autoevolve.py` | EMRS uses existing endpoints; adds `/versions` routes alongside existing `/experiments` |
| `self_patch.py` | EMRS wraps self_patch calls with version recording; no changes to self_patch logic |
| `rl2f.py` | EMRS reads RL2F accuracy as primary feedback signal; no changes to rl2f routes |
| MARS sweep | Unaffected; always runs (G1 budget floor) |
| workflow_gates | Could gate Phase 2 patches via DAO vote; out of scope for Phase 1 |
| S-MMU / smmu.py | meta_memory.json is separate from S-MMU L1/L2/L3 — simpler persistence for meta-level |

---

## Success Criteria

| Metric | Current | Target (after Phase 1) | Target (after Phase 2) |
|--------|---------|----------------------|----------------------|
| AutoEvolve generation | 1 | 2+ (at least 1 experiment completes) | 5+ (compounding) |
| AutoEvolve experiments (total) | 0 | 1+ per week | 2+ per week |
| RL2F accuracy | 30% declining | Stabilized | 40%+ improving |
| meta_memory.json | absent | Present, updated every cycle | Causal hypotheses accumulating |
| Self-patch applied (auto) | 0 | 1+ (with veto window cleared) | Regular cadence |
| Rollback events | 0 | 0 (patches should improve) | 0 (auto-rollback catches regressions) |

---

## Key Decisions

1. **File-based meta_memory vs DB:** Chose file. DB requires HTTP call during budget-constrained session. File is read in <100ms, no network dependency. Risk: no concurrent write safety — mitigated by single-writer design (only reflection writes it).

2. **48h veto window vs longer:** Chose 48h. Shorter (24h) risks Mev missing notifications. Longer (72h+) makes the evolution loop too slow. 48h gives 2 heartbeat review cycles.

3. **Step 0.5 classifier vs reordering entire document:** Chose classifier. Reordering 1220 lines is fragile and conflicts with established step numbering used in episodic logs. Classifier is a 20-line addition that branches execution without restructuring.

4. **Auto-rollback at 15% threshold:** Chosen to distinguish signal from noise. RL2F fluctuates ±5% naturally. 15% over 5 cycles is a clear regression signal, not noise. Alternative: 10% — rejected, too sensitive to normal variance.

5. **No human approval for AutoEvolve experiments, only for patch auto-apply:** AutoEvolve *proposing* experiments has no operational risk — the experiment records a hypothesis, not a file change. Approval gate is only when the patch is about to be applied to a live file.

---

## DGM-H Alignment

| DGM-H Component | EMRS Implementation |
|----------------|-------------------|
| Self-referential meta-agent | reflection.md edits itself via self_patch.py + version tracking |
| Metacognitive self-modification | Component 3 (versioned manifest) + GuardRail system |
| Open-ended exploration | G6 (exploration diversity constraint) forces search across file space |
| Cross-domain transfer | meta_memory.json accumulates causal hypotheses across sessions |
| Dual-component requirement | Both self-modification (existing) + exploration diversity (G6 new) |

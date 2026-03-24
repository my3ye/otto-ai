# Reflection Meta-Layer Gap Analysis
**Generated:** 2026-03-24 (task audit-04cee04a)
**Source files:** reflection.md (1220 lines), heartbeat.md, reflection.sh, autoevolve API, RL2F accuracy data, HyperAgents arXiv:2603.19461
**Analyst:** architect agent

---

## 1. What reflection.md Currently Governs

The reflection heartbeat (every hour at :30) runs as a Claude Code CLI session against `reflection.md`. It governs:

| Section | Function |
|---|---|
| ReflAct loop (Steps 0–2) | State reconciliation: validates blockers, corrects working memory, mission alignment audit |
| Step 3: Memory consolidation | Semantic dedup, stale fact removal, agent swarm review, workflow evolution monitoring, task plan monitoring |
| Step 4: Procedural memory growth | Encodes reusable skills from completed tasks |
| Step 5: Self-evaluation | Capability growth assessment, RL2F accuracy check |
| Step 5a: Metacognitive Gap Check | Calls `/eval/gaps` to surface capability weaknesses → creates improvement tasks |
| Step 5b: Memory Evolution | Calls `/memory/evolve` (decay → dedup → compress) |
| Step 5c: MARS Sweep | Extracts normative principles + procedures from episodic events (RL2F Layer 2) |
| Step 5c-post: GLOVE | Probes stored memories against current reality, flags mismatches |
| Step 5d: Collaboration Quality | Audits orchestrator–Mev collaboration health, generates proactive questions |
| Step 5d: TAME Evaluator | Checks recent task results against evaluator memory patterns |
| Step 5e: PreFlect | Prospective task critique: scores pending tasks against failure pattern DB |
| Step 6: System health | Disk, memory, timer liveness |
| Step 7: Proactive growth tasks | Creates research/implementation tasks |
| Step 7b: SELF-MODIFICATION (Gödel Agent) | Proposes staged patches to core files via `self_patch.py` |
| Step 7c: AutoEvolve | Structured experiment loop: hypothesis → patch → measure → keep/discard |
| Handoff: CAT protocol | Writes `reflection_handoff` workspace key for next cycles |
| Step 8: Log reflection | Stores episodic event summary |

---

## 2. How reflection.md is Invoked

**Invocation chain:**
```
systemd timer (otto-reflection.timer, :30/hr)
  → otto-reflection.service
  → reflection.sh
    → Rate-limit check (skips if hit within 3600s)
    → Lock file guard (prevents concurrent runs)
    → claude --model claude-opus-4-5 --budget 1.00
         --prompt "Run your reflection cycle. MARS_ENABLED=${MARS_ENABLED}..."
         --agent reflection.md
```

**Key constraints hardcoded in reflection.sh:**
- `$1.00` budget ceiling (can be reduced to `$0.50` in conservative mode)
- 10-minute timeout (`timeout 600 claude ...`)
- MARS_ENABLED flag (env var, `true` by default)
- Skips entirely if rate-limited within past hour

**What reflection.md cannot change about its own invocation:**
- The budget ceiling (`$1.00`) — hardcoded in `reflection.sh`
- The model (`claude-opus-4-5`) — hardcoded in frontmatter AND shell
- The trigger schedule (`:30/hr`) — systemd timer, not in-file
- The prompt prefix injected by the shell
- The rate-limit skip behavior
- The lock file mechanism

---

## 3. What the Meta-Layer Can Change About Itself

**Via self_patch.py (staged, review-required):**
- Its own prompt text in `reflection.md` (up to 50 lines at a time)
- `heartbeat.md` prompt text
- Shell scripts: `heartbeat.sh`, `reflection.sh`, `task_runner.sh`
- Tools: `tools/self_patch.py`, `tools/lead_scraper.py`, etc.

**Via AutoEvolve:**
- Can propose and track experiments that modify its own behavior
- Current generation: **1** (extremely low — only 1 generation since inception ~March 18)
- Active experiments: **0** (no active autoevolve loop running)

**Via MARS sweep:**
- Can add normative principles to the DB (`/principles`)
- Can add procedures to procedural memory
- These feed into future context briefings but do NOT auto-modify the prompt

**What it CANNOT directly change:**
- The systemd timer schedule
- The budget/timeout in `reflection.sh` (requires self_patch with allowed targets — `reflection.sh` IS in the allowed list)
- Its own model (self_patch could technically change the frontmatter `model:` field)
- The rate-limit skip logic (can propose a patch to `reflection.sh`)

---

## 4. Where Self-Improvement Currently Stalls

### GAP-1: AutoEvolve is effectively frozen
**Evidence:** Generation = 1, last updated 2026-03-18 (6 days ago). Zero active or proposed experiments. The AutoEvolve loop was implemented but has never completed a full experiment cycle.

**Root cause (HyperAgents diagnosis):** The reflection.md's AutoEvolve section (7c) has a trigger condition requiring RL2F accuracy < 70% OR 10+ cycles since last experiment. The trigger fires — RL2F is at 30% — but the loop still doesn't run because:
1. Each reflection cycle costs ~$0.50–$1.00. Spending ~$0.30 of that budget on AutoEvolve setup reduces budget available for core steps.
2. The 10-minute session timeout cuts off long cycles before Step 7c is reached.
3. There is no evidence in episodic events that the autoevolve trigger has fired even once.

**Impact:** Otto is stuck in the exact pattern HyperAgents identifies as the DGM bottleneck: the domain-level agent (orchestrator) improves via RL2F/MARS, but the **meta-level agent (reflection.md itself) never evolves**.

---

### GAP-2: RL2F accuracy at 30% with declining trend — no systemic response
**Evidence:** RL2F: 30% (15/50 matched, 32 partial, 3 miss). Prior was 60% — a 50% drop. Trend: declining.

**Expected meta-layer response:** AutoEvolve should trigger, analyze the root cause (likely idle cycles generating structurally different outcomes than predicted), and either:
- Propose a patch to reduce EXPECTED field ambiguity
- Propose a change to how partial matches are scored
- Propose a prompt change to make ACTUAL reporting more precise

**Actual response:** MARS sweeps log "0 new principles (dup)" for idle cycles. RL2F accuracy stays at 30% for multiple consecutive reflection cycles. No experiment proposed. No patch proposed. The meta-layer is witnessing its own performance degradation and not acting.

---

### GAP-3: Reflection budget exhaustion before reaching growth steps
**Evidence:** Reflection cycles routinely log "Rate limit respected — consolidation only." Steps 7b (self_patch) and 7c (AutoEvolve) are at the END of a 1220-line document. The $1.00 budget is nearly consumed by Steps 0–5 (reconcile, MARS, GLOVE, TAME, PreFlect).

**The architecture creates a structural bias:** Self-improvement (the meta-layer's primary purpose) is ordered after operational maintenance. The agent reliably executes maintenance steps because they appear first. Growth steps (7, 7b, 7c) are reliably skipped because budget is gone.

**Frozen assumption:** The current ordering assumes maintenance must come before improvement. The HyperAgents model inverts this: the meta-agent's PRIMARY job is to change the domain agent's behavior, not to do maintenance itself.

---

### GAP-4: Self-patch is human-gated with no auto-approval path
**Evidence:** 4 patches in `~/otto/projects/self_patches/` (the oldest from 2026-02-21). The self_patch system proposes patches, which are then marked `status: "approved"` manually before application.

**The gap:** The heartbeat is supposed to apply approved patches, but there is no evidence in recent logs that this loop is completing. The review gate was designed for safety, but without automatic progression, patches sit staged.

**Per HyperAgents:** A meta-agent that cannot apply its own modifications — even after a waiting period with no human veto — is operating with a fundamentally shorter arm than its design intends. The DGM model requires the meta-agent to be able to actually modify the domain agent, not just propose modifications.

---

### GAP-5: Reflection has no mechanism to update its own step ordering or budget allocation
**The structural problem:** reflection.md hardcodes step ordering (0→1→2→3→4→5→5a→5b→5c→6→7→7b→7c→8). There is no adaptive path where:
- The reflection agent decides "I'm in an idle period — skip Steps 1–3 and go straight to AutoEvolve"
- Budget is front-loaded to growth steps when no operational fires exist
- Step ordering shifts based on context (e.g., "RL2F declining → run AutoEvolve first")

**Frozen assumption:** Every cycle needs the same linear progression. The HyperAgents meta-layer would select which sub-routines to activate based on current system state and meta-goals, not a fixed sequential order.

---

### GAP-6: Reflection cannot modify the heartbeat's task-creation strategy
**The gap:** When reflection detects that the orchestrator is creating the wrong types of tasks (e.g., operational maintenance when it should create growth tasks), the ONLY lever is:
1. Rewrite `active_mission` in working memory (text instruction, no structural force)
2. Propose a patch to `heartbeat.md`

But `active_mission` rewrite is a soft signal — the heartbeat reads it but can override it based on its own judgment. And self_patch proposals require human review.

**Per HyperAgents:** The meta-agent needs a stronger binding mechanism to the domain agent. Currently, the meta-agent can advise but cannot compel. A proper meta-layer would have enforcement primitives: task queue manipulation, budget allocation, forced routing — not just text suggestions.

---

### GAP-7: No meta-memory about the reflection process itself
**Evidence:** Reflection's semantic memory primarily contains domain knowledge (infrastructure facts, project status, research findings). There is minimal meta-knowledge:
- How often does each reflection step execute to completion?
- Which steps generate the most value?
- What is the budget distribution across steps over time?

**The gap:** The reflection agent cannot reason about its own behavior patterns because it doesn't store structured self-observations. Without this, AutoEvolve's hypothesis generation (`/autoevolve/insights`) is based on general system signals, not specific reflection execution telemetry.

---

## 5. Summary: Frozen Assumptions vs. DGM/HyperAgents Ideal

| Frozen Assumption | Current State | HyperAgents Ideal |
|---|---|---|
| Step ordering is fixed | Linear 0→8 every cycle | Dynamic — meta-agent selects steps based on system state |
| Budget is fixed at $1.00 | Hardcoded in shell | Meta-agent allocates budget per-step based on priorities |
| Self-modification requires human approval | Staged patches, manually approved | Auto-apply after N cycles without veto (time-locked gate) |
| Meta-agent improves domain agent via text | WM updates, optional patches | Meta-agent directly restructures domain agent's strategy |
| AutoEvolve is a step in the cycle | Rarely reached (step 7c) | AutoEvolve IS the outer loop; current cycle is inner loop |
| Reflection cannot update its own structure | Can only patch via staged process | Meta-agent can reorganize its own routines each generation |
| No step-level performance tracking | No step telemetry | Meta-agent tracks value-per-step and prunes low-value steps |

---

## 6. Recommended Interventions (Prioritized)

### P1 — Reorder reflection.md: move AutoEvolve to Step 1 during idle periods
**Implementation:** Add a conditional branch at Step 0 — if system is idle (no tasks, no blockers), run Steps 7b and 7c FIRST, then do maintenance. Cost: ~3 lines of logic at the top of the file.

### P2 — Enable auto-apply of self_patches after 48h timeout
**Implementation:** Add logic in heartbeat.md Step 0: check `self_patch.py list` for patches older than 48h with no rejection → auto-approve and apply. This closes the human-gating gap without removing safety.

### P3 — Add step telemetry: log which steps execute and estimated cost
**Implementation:** After each numbered step, log an episodic event with step name + budget remaining. Over time, `/autoevolve/insights` can use this to find which steps have the best value-per-dollar.

### P4 — Create an initial AutoEvolve experiment targeting RL2F accuracy
**Implementation:** RL2F is at 30% (trigger condition met: < 70%). The reflection agent should launch one experiment NOW: hypothesis = "EXPECTED field predictions are too deterministic for idle cycles — adding explicit idle-cycle variance language will improve partial→match conversion." Apply via self_patch to heartbeat.md's EXPECTED section format.

### P5 — Add a meta-binding primitive: reflection can add tasks to queue with P10 override
**Implementation:** Allow reflection to create tasks with `created_by: "reflection_override"` that cannot be deprioritized by the orchestrator. Currently reflection creates tasks but the orchestrator can simply not launch them.

---

## 7. Key Finding for HyperAgents Integration

The HyperAgents paper identifies the meta-agent freeze as the central bottleneck. Otto's reflection.md IS the meta-agent. It is frozen in these specific ways:

1. **Cannot self-execute** (AutoEvolve is never reached)
2. **Cannot self-bind** (its outputs are advisory, not compulsory)
3. **Cannot self-order** (step sequence is static regardless of system state)
4. **Cannot self-measure** (no telemetry on its own execution)

The domain agent (heartbeat/orchestrator) has improved significantly via RL2F/MARS/memory systems. The meta-agent has not evolved since its prompt was written. This is the definition of the DGM bottleneck that HyperAgents solves.

**The fix is not complex.** The HyperAgents insight is that a frozen meta-agent only needs a few primitives to unlock recursive improvement:
- Dynamic step selection (P1 above)
- Auto-apply with timeout-gated approval (P2 above)
- Self-telemetry (P3 above)

These are all achievable within Otto's existing architecture.

# Research Pipeline Architecture
**Date:** 2026-03-19
**Author:** Otto Architect
**Status:** Approved for implementation

---

## Design: Robust Multi-Agent Research Workflow

### Problem

Otto has a generalist `researcher` agent that does everything in one shot: retrieve, synthesize, validate, and store. This creates three failure modes:
1. **Lost-in-middle**: Long research prompts produce long outputs that exceed useful context — key findings get buried
2. **No validation**: Single agent has no adversarial check on its own claims
3. **No persistence**: Research findings aren't systematically stored back into semantic memory for future retrieval

There is no `research-pipeline` workflow template — all research runs as ad-hoc single tasks.

### Approach

A 4-step multi-agent pipeline with explicit agent specialization:

```
Orchestrator
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  STEP 0: Retrieval (researcher agent)               │
│  Multi-source gather: web + semantic memory +       │
│  knowledge graph + papers DB + codebase             │
│  Output: structured raw findings (≤3000 tokens)     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 1: Synthesis (research-synthesizer agent)     │
│  Consolidate findings, remove duplication, rank     │
│  by confidence + actionability, identify patterns   │
│  Output: structured synthesis report (≤1500 tokens) │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 2: Validation (reviewer agent)                │
│  Adversarial check: are claims supported by         │
│  evidence? Are sources reliable? Contradictions?    │
│  Output: validated findings + confidence scores     │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 3: Storage + Report (researcher agent)        │
│  Persist to semantic memory + /research/notes       │
│  Surface actionable summary to orchestrator         │
│  Output: storage confirmation + report              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  STEP 4: Notify (notify action)                     │
│  Compact summary to orchestrator/Mev                │
└─────────────────────────────────────────────────────┘
```

### Key Decisions

- **Researcher → Synthesizer → Reviewer**: Separation of concerns. Retrieval agents search broadly (high recall). Synthesis agents compress and structure. Reviewers challenge and validate. Each role benefits from a different mindset — forcing them into one agent degrades all three.

- **Output compression at boundaries**: Each step MUST return ≤2000 tokens to orchestrator. This is the 2026 best practice from memory — 15x token overhead of multi-agent vs single-agent must be managed aggressively. Without this, multi-agent pipelines have worse performance than single-agent.

- **Reuse `reviewer` for validation** (not a new "validation agent"): The reviewer agent is already designed for adversarial analysis. Cheaper than building a new agent, and the pattern (read → challenge → report) maps directly to research validation.

- **Reuse `researcher` for storage**: The storage step is logically part of research completion. The researcher agent already has access to memory API endpoints. Alternative (new `memory-curator` step) adds a step and cost without benefit.

- **New `research-synthesizer` agent** IS justified: Synthesis requires a fundamentally different approach from retrieval — it must cross-reference multiple sources, detect contradictions, weight by confidence, and compress aggressively. Giving this to the researcher produces a second retrieval pass, not a synthesis.

- **4 steps, not 5**: Skip explicit scoping step. The workflow variables (`topic`, `scope`, `requirements`) replace the scoping step. Scoping within a task just adds latency without new information.

### New Agent: research-synthesizer

**Location:** `~/otto/.claude/agents/research-synthesizer.md`

**Role:** Receive raw multi-source research findings, consolidate into structured actionable synthesis. Does NOT do new retrieval — synthesis only.

**Output contract:**
```
## Key Insights (ranked by confidence + actionability)
1. [Insight] — Confidence: HIGH/MEDIUM/LOW | Sources: N
2. ...

## Contradictions / Uncertainties
- [Any conflicting data points]

## Recommended Actions (top 3)
1. [Specific, implementable action]
2. ...

## Evidence Quality
[Brief assessment of source quality and coverage]

## Compressed Context for Next Step
[1000 token max summary for handoff]
```

### Workflow Template: `research-pipeline`

**Variables:**
- `topic` — What to research
- `scope` — Boundaries (what to include/exclude)
- `requirements` — Specific deliverables or questions to answer
- `store_findings` — Whether to persist to semantic memory (default: true)
- `research_depth` — "quick" (1 web pass) | "standard" (default) | "deep" (multiple passes)

**Step configuration:**

| Step | Agent | Budget | Timeout | On Failure |
|------|-------|--------|---------|------------|
| 0: Retrieval | researcher | $4 | 900s | retry_once |
| 1: Synthesis | research-synthesizer | $2 | 600s | retry_once |
| 2: Validation | reviewer | $2 | 600s | skip |
| 3: Storage + Report | researcher | $2 | 600s | pause |
| 4: Notify | (action) | — | — | — |

**Total max cost:** ~$10 per deep research run. Typical: ~$6.

### Files to Create/Modify

1. **NEW:** `~/otto/.claude/agents/research-synthesizer.md`
   - Synthesis-only agent, strict output format, compression rules

2. **NEW (via API):** `research-pipeline` workflow template in DB
   - POST `/workflows/templates` with 5-step spec

3. **MODIFY:** `~/otto/memory/routes/skills.py`
   - Register `research-synthesizer` in skills registry
   - Register `research-pipeline` as a workflow skill

4. **MODIFY:** `~/otto/.claude/agents/researcher.md`
   - Add explicit output compression rule (≤2000 tokens when in pipeline)
   - Add Step 3 (Storage) instructions: how to POST to `/semantic/remember` and `/research/notes`

5. **NEW (optional):** `~/otto/memory/routes/research.py` extension
   - Add `POST /research/findings` endpoint for structured pipeline output storage
   - Stores: topic, synthesis, confidence scores, validated_at, pipeline_instance_id

### Implementation Plan

**This task (Step 0 — Architecture):**
1. ✅ Audit current agent setup and workflow engine
2. ✅ Design pipeline architecture
3. ✅ Write architecture doc (this file)
4. Create `research-synthesizer.md` agent ← **start here**
5. Update `researcher.md` with compression + storage instructions

**Next task (Step 1 — Implementation):**
1. Register `research-synthesizer` in `skills.py`
2. Create `research-pipeline` workflow template via API
3. Add `POST /research/findings` endpoint to `research.py`
4. Test pipeline with a real research topic
5. Verify findings are stored in semantic memory

### Risks

- **Context overflow at synthesis step**: If retrieval returns too much, synthesis agent gets overloaded. Mitigation: enforce ≤3000 token output rule in retrieval step prompt.

- **Validation step is slow/expensive**: Reviewer doing adversarial analysis on research is thorough but adds 600s+. Mitigation: `on_failure: skip` — if validation times out, pipeline continues. The synthesis output is still valuable.

- **Research topics that need iteration**: Single-pass research may miss information that would be found in a second pass. Mitigation: `research_depth: deep` variable triggers researcher to do multiple search strategies before returning.

- **Storage step fails silently**: If semantic memory is down, Step 3 exits 0 but nothing is stored. Mitigation: Researcher in Step 3 must verify storage by reading back what was written.

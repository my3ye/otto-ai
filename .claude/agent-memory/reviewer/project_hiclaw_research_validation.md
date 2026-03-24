---
name: hiclaw_research_validation
description: HiClaw architecture synthesis validation (2026-03-24) — APPROVED with adjustments. 7.5/10. Anti-swarming claim misapplied; source count inflated; credential gap confirmed real.
type: project
---

HiClaw synthesis validated 2026-03-24. VERDICT: APPROVED (7.5/10) — no blockers for implementation dispatch.

**Why:** Mev directed deep analysis of HiClaw (github.com/alibaba/hiclaw); research-pipeline workflow ran retrieval → synthesis → this validation step.

**How to apply:** When heartbeat dispatches the 3 recommended implementation tasks, prioritize: (1) acceptance criteria standard, (2) artifact-path references, (3) credential isolation. Deprioritize anti-swarming (based on mischaracterized Otto dispatch model).

## What Was Verified (codebase checks)
- `/gateway/incoming` EXISTS at memory/gateway/routes.py — synthesis correct
- Per-agent memory EXISTS at .claude/agent-memory/ (13 agents) — synthesis correct
- DAG task plans EXIST at memory/routes/task_plans.py with depends_on — synthesis correct
- Max concurrent = 5, no idle-stop — synthesis correct
- Multi-model support (claude/gemini/kimi) — synthesis correct
- No acceptance criteria standard in task prompts — gap confirmed

## Adjustments to Synthesis Claims
1. **Anti-swarming claim is imprecise**: Synthesis says "Otto's async dispatch sends to all agents simultaneously." FALSE — Otto dispatches ONE task to ONE agent via task_runner.sh. HiClaw's @mention trigger solves a different problem (persistent worker processes). The anti-swarming pattern does NOT apply to Otto's ephemeral task runner model.
2. **Source count inflated**: "11 sources" is 4 web (real HiClaw data) + 2 graph (indirect Otto meta) + 5 code (Otto self-comparison). Not 11 independent HiClaw sources. Confidence claims need this context.
3. **"80% cost reduction" unverified**: Single first-party Alibaba blog claim, no independent corroboration.
4. **Credential isolation gap is real and confirmed**: task_runner.sh spawns claude CLI as subprocess that inherits system env (including ANTHROPIC_API_KEY). HiClaw's gateway-token proxy is the right fix.

## Confirmed High-Value Patterns (with confidence adjustments)
1. Acceptance criteria in task prompts — HIGH confidence, HIGH actionability (zero-cost fix)
2. Credential isolation via gateway proxy — HIGH confidence, MEDIUM actionability (requires implementation work)
3. Artifact-path references vs full output content — HIGH confidence, MEDIUM actionability
4. Per-agent isolated MEMORY.md — ALREADY PARTIALLY DONE (13 agents have dirs)
5. Task-specific model allocation — MEDIUM confidence (80% claim unverified), HIGH actionability

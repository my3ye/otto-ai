---
name: CORAL arXiv 2604.01658 Validation
description: Validation of CORAL multi-agent synthesis (2026-04-11, WF Step 2): MINOR_CHANGES 8.5/10. 1 critical LLM misattribution (Kimi not Gemini Flash), 1 warning on worktree claim scope. All gap claims grep-verified correct.
type: project
---

CORAL (arXiv 2604.01658) synthesis validation completed 2026-04-11, WF Step 2.

**Verdict:** MINOR_CHANGES — 8.5/10

**Why:** Strong synthesis overall. All major gap claims verified via grep. One factual misattribution of LLM backend (Kimi not Gemini Flash) and one inflated code match claim.

**How to apply:** When reviewing future syntheses that cite code line numbers, always verify the LLM model name claimed matches what the code actually calls. The `llm_chat()` function in Otto routes to Kimi, not Gemini or Gemini Flash — this is a recurring misattribution risk.

## Critical (must fix before storage/action)
- `_extract_skill_from_task` uses **Kimi** (via `llm_chat()` + `settings.kimi_api_key` guard), NOT "Gemini Flash" as the synthesis claims. Factual misattribution at tasks.py:1351/1382. Conclusion unchanged (function IS implemented) but model attribution wrong.

## Warnings
- `isolation: "worktree"` match claim is scoped to qa_runner.sh QA isolation step, not the primary task_runner.sh agent spawning path. The synthesis presents this as a general "agent spawning" pattern MATCH — it's partial at best. Does not negate the conclusion but should be stated as "QA path" not "agent spawning."

## Verified Correct
- Stagnation detection gap: CONFIRMED via grep. autoevolve.py:359 is a static string comment, not a live mechanism.
- Cross-task leaderboard gap: CONFIRMED. education.py leaderboard is XP-only (unrelated). No best-attempt/cross-agent registry in otto/memory/.
- `_extract_skill_from_task` implementation: CONFIRMED at tasks.py:1346. Fires on status==completed AND exit_code==0 only.
- ZK routing error identification: logically sound, zero ZK content in CORAL paper.
- Performance metrics (17% vs 9%, 36%, 55%) correctly attributed to paper source.
- Recommended actions all specific and implementable.

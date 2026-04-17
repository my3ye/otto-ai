---
name: failure_branch_implementation_review
description: Failure-branch adaptation module review (2026-03-28, WF Step 2): NEEDS_CHANGES. Coder still running — partial implementation reviewed. 2 critical DB schema issues, 1 architecture mismatch vs spec. autoevolve.py fix is correct.
type: project
---

Failure-branch adaptation module review (2026-03-28, task e40284d3, WF Step 2): NEEDS_CHANGES

**Why:** RL2F accuracy at 32% (50-cycle), 34 partials, declining trend. Architecture spec (synthesis t3) produced specific bash-level implementation actions. Coder (t4) over-engineered: building new Python module + DB table instead of ~15 lines bash additions to task_runner.sh.

**Critical issues:**
1. migration 079 `failure_branch_adaptations` missing `agent_type VARCHAR(50)` column — synthesis spec explicitly requires storing `(agent_type, task_category, failure_mode)` tuple for cross-session learning
2. `task_id` column in migration has no FK constraint → `REFERENCES tasks(id)` missing
3. Architecture mismatch: spec (t3) calls for bash changes to `task_runner.sh` permanent-failure block; coder building a new Python module with LLM calls — over-engineered but acceptable IF LLM call is non-blocking

**What's good:**
- `autoevolve.py` fix (reasoning_chain vs rl2f_feedback) is correct, well-documented, low-risk
- DB migration schema is otherwise well-structured with proper indexes
- Pydantic models (6 new) are clean and properly typed
- heartbeat.md STATE DELTA section is autoevolve gen-2 experiment (correctly non-destructive)

**Pattern:** Synthesis specs say "5 lines bash" — implementation task interprets as "new module." Always validate implementation scope against synthesis before coder runs.

**How to apply:** When reviewing implementations that follow a research synthesis, check that scope wasn't inflated. The synthesis recommended a minimum-viable fix; if the coder builds something larger, validate that the existing loops are not corrupted and the new module doesn't duplicate existing SMART_RETRY logic.

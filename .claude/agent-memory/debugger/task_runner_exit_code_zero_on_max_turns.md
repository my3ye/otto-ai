---
name: task_runner_exit_code_zero_on_max_turns
description: Claude CLI exits 0 when max_turns is hit — tasks marked 'completed' instead of 'failed'
type: project
---

When Claude CLI hits `--max-turns`, it outputs "Error: Reached max turns" to stdout but exits with code 0. The task_runner.sh previously detected this text and replaced OUTPUT, but did NOT change EXIT_CODE. Result: `/tasks/{id}/complete` was called with exit_code=0 → API set status='completed'.

**Fix applied (commit 6970146)**: After detecting "Error: Reached max turns" in output, task_runner.sh now sets `EXIT_CODE=1`. Also added a guard: if exit_code=0 but output is empty, override to EXIT_CODE=1 (silent budget exhaustion case).

**Why:** The API endpoint at tasks.py line 759 correctly maps `exit_code=0 → completed` and `exit_code≠0 → failed`. Exit 124 (hard timeout from `timeout` command) was already correctly propagated. The only gap was the max_turns soft failure.

**How to apply:** If future tasks show as 'completed' when they should be 'failed', check: (1) Did the agent hit max_turns? (2) Did the CLI exit 0 with empty output? Both now correctly set exit_code=1.

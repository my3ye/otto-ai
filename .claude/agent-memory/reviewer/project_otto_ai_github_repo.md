---
name: otto-ai public GitHub repo review
description: Code review of my3ye/otto-ai public developer SDK (2026-03-22, commit 69d0178). NEEDS_CHANGES (minor). 5 issues flagged — 1 critical UX bug, 2 warnings, 2 suggestions.
type: project
---

Review of `my3ye/otto-ai` public repo, commit 69d0178, 2026-03-22.

Verdict: NEEDS_CHANGES (minor — no blockers for EasyA outreach, but Docker task runner is broken)

**Critical UX Bug:**
- `routes/tasks.py` lines 101–115: `/tasks/{id}/run` marks the task as `running` before checking if `task_runner.sh` exists. Docker build context is `./memory/`, so `task_runner.sh` (at repo root) is NOT in the image. Any Docker user hitting `POST /tasks/{id}/run` gets a zombie task permanently stuck as "running". The path computation `../../task_runner.sh` from `/app/memory/routes/` resolves to `/app/task_runner.sh` which doesn't exist in the container.

**Warnings:**
- `memory/requirements.txt` line 8: `pgvector>=0.3.0` is listed but never imported anywhere. Dead dependency — vectors are handled via SQL casting (`::text::vector`). Should be removed.
- `api.py` lines 34-40: CORS middleware has `allow_origins=["*"]` AND `allow_credentials=True`. The CORS spec forbids this combination — browsers will reject credentialed requests when origin is `*`. Low impact for CLI-first users but will confuse web frontend builders.
- `memory/routes/procedural.py` line 17: `import json` inside function body instead of top-level. Minor style inconsistency — all other routes have top-level imports.

**Suggestions:**
- `task_runner.sh` line 62: `--dangerously-skip-permissions` should have a prominent warning comment. Public repo users may not understand the security implications.
- IVFFlat index in init SQL (`WITH (lists = 100)`) needs `ANALYZE` after first data load to be effective. Worth a note in the quickstart.
- README line 37: `{id}` literal placeholder in curl command should be `$TASK_ID` or a sample UUID.

**What's good:**
- Parameterized queries everywhere — no SQL injection risk
- `archived = FALSE AND deleted_at IS NULL` double-check pattern used correctly
- Docker ports bound to `127.0.0.1` only — not exposed to internet
- `.env` correctly gitignored, `.env.example` has no real secrets
- `on_exit` trap in `task_runner.sh` prevents zombie tasks on crash
- Internal business routes (40+) correctly excluded from public SDK
- Health endpoint actually checks DB with `SELECT 1` — good practice

**How to apply:** Flag zombie-task bug and dead `pgvector` dependency for the next implementation pass.

---
name: otto_ai_public_repo_2026_03
description: Architecture for my3ye/otto-ai public GitHub repo — EasyA developer entry point, curated Memory API SDK
type: project
---

Account **my3ye** (not ottomev) owns this repo: `my3ye/otto-ai` (public). Created to unblock EasyA outreach email which had `[[NEEDS_MEV_INPUT: public GitHub repo URL]]` placeholder.

**Why:** EasyA outreach cannot send without a public GitHub URL. Getting-started README already uses `github.com/my3ye/otto-ai`. `my3ye` is the public ecosystem identity (name="MY3YE").

**Repo structure:** README.md + docker-compose.yml + .env.example + Makefile + MIT LICENSE + docs/ (quickstart, architecture, api-reference, hackathon-tracks) + examples/ (hello-memory, task-runner, multi-agent) + memory/ (curated public API — 6 route files only) + init-db/000_init.sql

**Public routes (15 endpoints):** health, sessions (start/end), semantic (remember/search/forget), episodic (events/timeline), procedural (CRUD/outcome), tasks (CRUD/run/queue-status)

**Excluded routes:** webassist, athena, leads, investors, outreach, bankr, crypto, commerce, trading, virtuals, broadcast, contacts, email, whatsapp, social_calendar, workspace, universe, thought_vault, etc.

**After creating repo:** Update two files:
- `projects/easya/getting-started-readme.md` line 94: replace draft URL
- `projects/easya/outreach-email-v2.md`: replace `[[NEEDS_MEV_INPUT: public GitHub repo URL]]` with `https://github.com/my3ye/otto-ai`

**Git identity for my3ye repo:** `git config user.email my3ye.otto@gmail.com`

**Full design doc:** ~/otto/docs/otto-ai-github-architecture-2026-03-22.md

**How to apply:** Any task creating or modifying the otto-ai repo must: (1) switch to my3ye account first, (2) set git email to my3ye.otto@gmail.com, (3) never commit .env files.

---
name: Phase 0 DPC Scoring Engine review
description: DPC engine + contributor dashboard review (2026-04-13, WF Step 2): MINOR_CHANGES 8.0/10. 3 criticals: ingest/compute endpoints unauthenticated on 0.0.0.0; _insert_event always returns True (duplicate = "inserted" in stats); Dv metric broken in bootstrap phase (all contributors registered same day → everyone caps at 2.0). Formula verified correct vs SPEC. Service live, 12/12 endpoints, 12/12 tests pass.
type: project
---

Phase 0 DPC Scoring Engine (2026-04-13, WF Step 2): MINOR_CHANGES 8.0/10. Engine live at port 8202 with 3 real contributors scored.

## 3 Criticals

1. **Unauthenticated endpoints on 0.0.0.0:8202**
   - POST /dpc/ingest/github and POST /dpc/compute are open to the network
   - Risk: anyone can drain GitHub token rate limit or trigger expensive CPU computation
   - Fix: Add simple API key header validation or bind to 127.0.0.1

2. **_insert_event() always returns True** (github.py:69-89)
   - ON CONFLICT DO NOTHING does not raise exception, so stats["events"] counts duplicate-skips as inserted
   - Misleading success signal in ingest logs
   - Fix: use RETURNING id to detect whether insert actually occurred

3. **compute_dv_digital Dv metric broken in bootstrap** (scorer.py:189)
   - Uses c.registered_at (system registration date) instead of first-contribution-to-repo date
   - All founders registered same day (2026-04-13) → all Dv values cap at 2.0
   - Accepted as Phase 0 limitation per SPEC, but blocks Phase 1 Dv differentiation
   - Fix: add contributor.first_event_date column, populate from GitHub ingestion

## 2 Warnings

- Misleading comment "Upsert score — keep latest per contributor" (scorer.py:294) — code does plain INSERT keeping full history, not upsert. Acceptable for Phase 0 since scores are immutable per run.
- compute_dv_digital has N+1 queries (one DB call per event). Acceptable for founding cohort (<20 contributors). Will need caching/batch for 1000+ contributors.

## What's Correct

- All 5 formulas (Is, Ec, Dv, P_gov, GovernanceWeight) match SPEC exactly
- All 12 SPEC endpoints present and working (9 score + 3 admin)
- .env NOT committed to git (gitignore correct)
- asyncpg pool pattern consistent with Otto codebase
- Error handling in ingest loop is comprehensive (timeout, malformed JSON, missing fields)
- Test coverage: 12/12 endpoints passing, including edge cases (null scores, zero contributors)
- Service health check working (GET /dpc/health)
- Contributor dashboard rendering correctly (demo mode with 3 bootstrap contributors)

## Score Breakdown

- Formula correctness: 10/10
- API completeness: 10/10
- Security: 6/10 (unauthenticated + bootstrap Dv = 4 points deducted)
- Code quality: 9/10 (N+1, misleading comment = 1 point deducted)
- Test coverage: 10/10
- **Overall: 8.0/10 MINOR_CHANGES**

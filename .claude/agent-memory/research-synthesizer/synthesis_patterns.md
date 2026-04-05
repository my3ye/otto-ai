---
name: synthesis_patterns
description: Effective synthesis patterns observed from successful research-synthesizer runs
type: feedback
---

Effective synthesis patterns observed:

1. **Code-first grounding**: When retrieval includes direct codebase observation, lead the synthesis with those findings — they are highest confidence and most actionable.

2. **Gap identification over description**: The most actionable insight in a CMS versioning synthesis was not "here's how versioning works" but "the backend exists and the frontend never calls it." Frame gaps explicitly.

3. **Library comparison framing**: When multiple frontend libraries are candidates, compare on: bundle size, maintenance status, API fit for the data format (unified diff string vs old/new strings). This directly informs implementation decisions.

4. **Contradictions = implementation risks**: Surface format mismatches early (e.g., library expects old/new strings, backend returns unified diff format). These become blockers during implementation if not flagged.

5. **Gap verification protocol**: Before finalizing any "gap" claim, run a targeted grep/glob. If a file exists: downgrade to "needs extension" with file path. If absent: gap stands with search evidence. This prevents false gap claims that waste implementation effort on already-solved problems. Applied in AI landscape synthesis (2026-04-05): `routes/a2a.py` and `mcp_server.py` both existed, downgraded from "absent" to "needs extension."

6. **Episodic fallback when semantic/remember is blocked**: When OpenAI quota is exhausted (a known recurring blocker), `POST /episodic/events` still works (no embedding needed). Use as fallback + save synthesis to `docs/` file. Always note the episodic event ID and file path in the synthesis output so the next step can find the data.

7. **Anchor document pattern**: When retrieval surfaces a pre-existing synthesis document (e.g., a dated comparison matrix), treat it as the highest-confidence anchor. Cross-verify its claims with fresh grep/codebase reads. In the AI landscape synthesis, `otto-vs-ai-harnesses-comparison-2026-03-28.md` provided a verified 13-dimension matrix — this made the synthesis ~3x faster and more reliable than web-only synthesis.

**Why:** Code-grounded synthesis closes the loop between retrieval and implementation — avoids the case where synthesis recommends something the codebase already has, or misses a critical gap.

**How to apply:** Always check retrieval output for "directly observed in code" markers and prioritize those over web-sourced claims when they conflict.

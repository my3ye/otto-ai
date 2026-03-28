---
name: project_agent_harness_validation
description: AI agent harnesses research synthesis validation (2026-03-28, WF Step 2): NEEDS_CHANGES (5/10). 3 criticals: A2A already implemented, MCP already implemented, HyperAgents license wrong (CC BY-NC-SA not CC BY 4.0). Recurring pattern: synthesis did not check if prior gaps were already closed before this step ran.
type: project
---

AI agent harnesses synthesis validation — 2026-03-28, WF Step 2:

**Verdict: NEEDS_CHANGES (5/10)**

**Why:** 3 of the synthesis's top claims and 2 of 3 recommended actions are factually wrong due to the synthesis not detecting that A2A and MCP were already implemented in a parallel task (STEM gaps review, same day) before this validation step ran.

**Critical errors:**

1. **A2A protocol: synthesis says ABSENT — FALSE.** `memory/routes/a2a.py` is a full implementation with 5 message types, channel-scoped routing, PostgreSQL mailbox. STEM gaps review (same day) confirmed A2A=APPROVE. Action 1 is a re-implementation of existing code.

2. **MCP: synthesis says ABSENT — FALSE.** `memory/mcp_server.py` + `mcp_auth.py` exist. 15 tools, 4 resources, 3 prompt templates via SSE on :8100/mcp. STEM gaps review confirmed MCP=APPROVE. Action 2 is a re-implementation of existing code.

3. **HyperAgents license: "CC BY 4.0" — FALSE.** Confirmed prior review (project_hyperagents_synthesis.md): license is CC BY-NC-SA 4.0. Commercial use NOT permitted. Share-alike required on derivatives. This is the 3rd time this error has appeared in the pipeline.

**Warnings:**

4. **DGM-H "frozen" claim is overclaimed.** autoevolve.py exists and implements experiment loop (propose hypothesis → one file → evaluate → keep/discard). This is a partial DGM-H equivalent. Action 3 (have reflection.md propose its own diffs) is a valid extension but not a gap from zero.

5. **Source count inflation.** "44 data points across 6 source types" conflates overlapping sources (same paper in semantic memory AND research papers DB). Directionally correct but inflated. Recurring pattern in synthesis agent.

**Confirmed correct:**
- Provider types: 3 confirmed (claude_code_stream, openai_compatible, claude_cli)
- Agent count: 21 active files — correct
- rl2f.py, task_plans.py, Neo4j/pgvector stack — all confirmed
- Otto moat description accurate
- 60% Fortune 500 CrewAI correctly flagged as unverified
- HyperAgents benchmark (0.710 vs 0.590) correctly flagged as single paper

**Root cause of failure:** Synthesis and retrieval ran before STEM gap implementations completed. No mechanism to invalidate gap claims when implementations ship mid-pipeline. Gap assertions must be re-verified at validation step.

**How to apply:** When validating a synthesis about Otto gaps: always grep for the implementation before accepting "ABSENT" claims, regardless of how confident the retrieval sounds. Same-day gap closure is common.

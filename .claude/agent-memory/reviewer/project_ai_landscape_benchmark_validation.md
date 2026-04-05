---
name: AI Landscape Benchmark Validation (2026-04-05)
description: Step 2 validation of AI agent orchestration landscape synthesis for Otto benchmarking — MINOR_CHANGES 8.0/10
type: project
---

Otto AI agent orchestration landscape benchmark synthesis validated (2026-04-05, WF Step 2): MINOR_CHANGES 8.0/10.

**Why:** Research task for LinkedIn article comparing Otto vs LangGraph/CrewAI/Google ADK/etc. Synthesis at /home/web3relic/otto/docs/ai-landscape-synthesis-2026-04-05.md.

2 criticals:
1. Agent catalog count stale — synthesis says "138-agent catalog" but actual count is 182 agents in agency-agents/ (verified with find). Also "21 active" vs actual 22. Fix before LinkedIn publish.
2. Blockchain/ERC-8004 tense confusion — Insight #7 presents LaborAttestation + ERC-8004 + capital_governance_weight=0 + 40% agent tax as live Otto features. All are DESIGNED/PLANNED (Phase 3 in crypto-native-architecture-2026-03-19.md, smart contract design docs only). Must add "designed/planned" qualifier before publishing externally.

2 warnings:
- Bittensor "$3.44B mcap" — single source (kucoin.com), point-in-time, market cap volatile. Add "as of early 2026" qualifier.
- Memory write BLOCKED (OpenAI quota) — findings in episodic event fbc29257 only, not semantic memory. May not surface in future retrieval.

5 HIGH claims verified against codebase:
- OTel absent in core: CONFIRMED (grep → only peripherals)
- a2a.py exists but internal-only: CONFIRMED
- mcp_server.py: 15 tools, 4 resources, 3 prompts: CONFIRMED (docstring matches)
- autoevolve.py gen-2 active: CONFIRMED
- rl2f.py exists: CONFIRMED (14 functions)

Do not touch: all 6 framework tier assignments (verified against comparison doc), memory stack analysis, OTel gap diagnosis, recommended action #1 (OTel implementation), action #3 (A2A extension).

**How to apply:** When next Otto-benchmark article dispatched, check agent count against agency-agents/ before publish. Pattern: internal agent/project counts change faster than docs — always grep-verify before citing.

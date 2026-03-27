---
name: STEM Gap Implementations Review
description: Review of Dynamic Tool Composition, MCP Externalization, and A2A Protocol (2026-03-28). NEEDS_CHANGES — composition engine produces zero chains in practice.
type: project
---

STEM Gap Implementations sprint reviewed 2026-03-28. 3 implementations: A2A Protocol (APPROVE), MCP Externalization (APPROVE), Dynamic Tool Composition (NEEDS_CHANGES).

**Critical #1**: Composition engine always returns empty. `find_compositions()` filters intermediate agents by task-description relevance, but intermediates aren't relevant to the user task — only to their upstream inputs. Verified live: "research and build a defi integration" → 0 chains. Fix: don't apply relevance threshold to non-terminal agents.

**Critical #2** (strategic): Gap analysis prescribed P2/P3/P4 (Skills Maturation, Caller Profiler, Self-Adaptation). Implemented items were P5/P6/P7. Caller Profiler (full gap, highest novelty) unimplemented. Self-Adaptation addressed separately.

**Warnings**: `in_reply_to` FK no ON DELETE action (cleanup risk), MCP `skill_suggest` tool missing `compose=True` passthrough, MCP `whatsapp_send` no rate limit.

**Pattern**: backward-chaining composition engines must score intermediate agents by input/output compatibility, not by task-level relevance. Task relevance is only valid for the terminal (output-producing) agent.

**Why**: Task-relevance-based filtering worked in toy examples but breaks in all real cases because the task mentions the end goal (e.g., "write article"), not the intermediate steps (e.g., researcher).

**How to apply**: When reviewing composition/routing engines, always test with multi-step task descriptions and verify intermediate agents aren't filtered prematurely.

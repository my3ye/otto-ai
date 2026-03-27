---
name: dynamic_tool_composition_2026_03
description: Dynamic Tool Composition architecture — capability declarations + backward-chaining composition engine for agent chains. No migration, ~155 lines.
type: project
---

Dynamic Tool Composition architecture designed (2026-03-28). From STEM Agent gap analysis.

**Why:** Current agent selection (dispatch classifier + Tool RAG) picks ONE agent per task. No structured capability introspection. No automatic chain composition. Plan classifier decomposes via LLM guessing, not capability matching.

**How to apply:** 3 layers: (1) Add inputs/outputs/capabilities to SKILL_REGISTRY entries (data), (2) new memory/composition.py with backward-chaining find_compositions() (~80 lines), (3) wire into /skills/suggest?compose=true + plan classifier hint injection. No migration, no new service. Phase 1 ~$2, Phase 2 ~$1. Prerequisite for MCP externalization (Phase 3). Full spec at ~/otto/docs/arch-dynamic-tool-composition.md.

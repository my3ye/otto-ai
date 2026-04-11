---
name: Mid-Task Context Injection Feasibility
description: Claude Code CLI does not support mid-task injection natively; Otto's current --print mode is optimal; PreToolUse/PostToolUse are settings.json hooks (not SDK); tmux bracketed paste is best-documented workaround
type: project
---

**Research date:** 2026-04-11 | **Validation score:** 8.0/10 | **Research note ID:** daa2cef4-dc42-4de9-afd7-19dea754be69

## Core Verdict
True mid-task context injection into Claude Code CLI is **NOT natively supported**.
- Ink library blocks programmatic stdin writes
- No Unix socket or named pipe IPC in CLI
- GitHub issue #24947 "COMPLETED" closure was for VS Code extension only — CLI was never fixed

## Three Viable Approaches (ranked by Otto relevance)

1. **`--print` mode + file injection** — ALREADY IMPLEMENTED (optimal for automated tasks)
   - task_runner.sh: RL2F L179-247, Chain-of-Hindsight L250-279, semantic memory L330-378, A2A L520-566, progress files L440-460
   - All 3 CLI variants (claude/kimi/gemini) use `--print` (lines 645, 699, 753)
   - **No change needed**

2. **PreToolUse/PostToolUse hooks** — NOT IMPLEMENTED (highest-value gap)
   - These are **Claude Code CLI shell hooks in settings.json** — NOT Python SDK callbacks
   - Same mechanism as existing SessionStart/Stop hooks in `/home/web3relic/otto/.claude/settings.json`
   - Response format: `{"decision": "block", "reason": "..."}`
   - Enable tool-boundary injection without restart cost (~5-15s saved per correction)
   - **Action: add PreToolUse/PostToolUse entries to settings.json**

3. **tmux bracketed paste** — NOT IMPLEMENTED in Otto tools
   - ESC[200~...ESC[201~ + explicit Enter, ~0.4s latency, tmux ≥ 3.3 required
   - Fragile (autocomplete timing interference)
   - Useful only for human-supervised interactive sessions (Mev watching long runs)
   - **Action: build ~/otto/tools/inject_context.sh (~20 lines)**

## SMART_RETRY (task_runner.sh L1185-1295)
Approximates mid-task injection via restart. Failure-specific context injected at restart (error mode, timeout, QA rejection). Restart cost ~5-15s. Functionally equivalent for error recovery.

## What Does NOT Work
Direct stdin writes, `/proc/<pid>/fd/0`, signals, named pipes — all blocked by Ink.
MCP Elicitation: mid-task structured input via dialog (tool-boundary only, not arbitrary injection).

## Patches Applied (from validator review)
- **CRITICAL:** Insight 4 mechanism corrected — PreToolUse/PostToolUse = settings.json hooks (was incorrectly described as sdk_runner.py Python file)
- Insight 3: "only" → "best-documented" (2 sources insufficient for universal negative)
- Insight 5: SMART_RETRY line range corrected 1189-1291 → 1185-1295

**Why:** Prevents wasted implementation effort building a Python file that doesn't match how Claude Code hooks actually work.
**How to apply:** If anyone asks about implementing PreToolUse/PostToolUse for Otto — it's settings.json shell scripts, same pattern as SessionStart hook.

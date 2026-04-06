---
name: Landing Page Agent Pipeline Fix Review
description: Code review + live validation of agent-driven HTML generation fix (2026-04-06). PARTIAL PASS — pipeline works, quality significantly improved but layout issues remain.
type: project
---

Agent-driven landing page generation fix (commits 7dd5482, b24d828, 3a0d35e). All t2 criticals fixed. Live validation run completed (task f2eb2bb4, 2026-04-06).

**Summary of all steps:**
- t2 (Step 2 review): NEEDS_CHANGES — model name wrong, --bare missing
- t3 (Step 3 fix): Fixed all 5 issues (model, bare, auth, size, sys.path)
- Post-commit: uncommitted change replaces --bare with --print + --dangerously-skip-permissions (absolute claude path, HOME env set — better for service env)
- Final validation: PARTIAL PASS — pipeline works end-to-end, quality improved

**Live test (2d6a3ba4, Dhash Entertainment, 2026-04-06 ~17:10 IST):**
- Pipeline completed in ~90s: pending → researching → designing → generating → review ✓
- File: 29KB (>10KB floor) ✓
- DESIGN_34 "Event Showcase Professional" selected from prompts.md ✓
- Custom colors (#3D7068 sage green, #FF6B35, #FFA500), non-banned fonts ✓
- Hero: "Unforgettable events start here" — NOT "Welcome to X" ✓
- Real content: events, services, testimonials, process steps ✓
- Remaining issues: spurious nav section as content cards, "None" heading in trust signals, empty stats h3 tags, hero still centered not split_image_text

**Why:** The model name mismatch and missing --bare flag mean every primary path likely fails silently and falls back to the garbage template generator, defeating the entire fix. The auth gap on re-generate exposes $1-2 per unauthorized call.

**How to apply:** Fix model name to `claude-sonnet-4-6` (or `sonnet`), add `--bare` flag to agent subprocess. Auth on `/{page_id}/generate` is follow-up.

## Critical Issues

1. **Wrong model name** (`services/landing_page/agent_generator.py:212`) — Uses `claude-sonnet-4-20250514` (Anthropic API ID for Sonnet 4 base). Claude Code CLI 2.1.88 uses short-name format as shown in `--help`: `claude-sonnet-4-6`. If unrecognized, every invocation fails and falls back to the garbage template generator, defeating the entire fix. Fix: `--model claude-sonnet-4-6` or `--model sonnet`.

2. **Missing `--bare` flag** (`services/landing_page/agent_generator.py:210-216`) — Without `--bare`, each agent subprocess loads full Otto CLAUDE.md files, runs SessionStart hooks (memory API call to register a new Otto session), and runs background prefetches. Per-page: extra ~2000 token overhead + 1 spurious Otto session in DB. If the memory API is slow or down, the hook failure blocks generation. Fix: add `--bare` to the cmd list. Add `--system-prompt` with a one-liner identifying the task if needed.

## Warnings (should fix)

3. **Unauthenticated re-generate endpoint** (`memory/routes/landing_pages.py:753`) — `POST /{page_id}/generate` has no auth protection. Any caller who knows a UUID can trigger a $1-2 agent generation run. Pre-existing from prior review (2026-04-06) but not addressed here. Fix: add `Depends(verify_api_key)` to this endpoint decorator.

4. **Minimum file size check too low** (`services/landing_page/agent_generator.py:268`) — Checks `file_size < 1024` (1KB). A complete landing page with inline CSS, JS, animations, and full content should be 20-80KB. 1KB only catches nearly empty files, not severely truncated ones (e.g. agent stopped mid-generation). Fix: raise threshold to `10240` (10KB) minimum.

5. **`sys.path.insert()` called on every execution** (`memory/routes/landing_pages.py:219, 763`) — `sys.path.insert(0, "/home/web3relic/otto")` is called inside `_run_pipeline()` and `generate_landing_page_html()`, appending the path on every call. Should be at module level. Not breaking, just accumulates duplicates in `sys.path` over time.

## What's Good

- Design spec extraction (`_extract_design_spec`) correctly normalizes `DESIGN_06` → `DESIGN 06` and handles zero-padding edge cases
- Fallback chain is correctly implemented: agent fails → old copy_generator+generate_and_save runs. No data loss path.
- Timeout handler correctly kills the subprocess AND awaits it (`proc.kill()` + `await proc.wait()`) — architecture doc was missing the wait, implementation fixed it
- `_prompts_cache` prevents re-reading the 3112-line file on every generation
- Business context passthrough (description/target_audience fallback in research.py) is exactly the 5-line fix the architecture called for
- Async subprocess pattern is correct for non-blocking generation
- Error messages contain useful context (exit code, stderr tail)

---
name: rl2f_research_apply_loop_broken
description: Research pipeline findings never persisted to live config — hardcoded TP/SL + missing apply step caused 155 iterations of repeated findings
type: project
---

Research pipeline (research_pipeline.py) had two bugs creating a broken feedback loop:

1. **Hardcoded TP/SL values** (TP1=5.5%, TP2=25%, TP3=50%, SL=-15%) instead of reading from strategy_config.json. Research measured against stale thresholds, so Claude kept finding "targets unreachable" even after config was manually patched.

2. **No code path to apply findings**: Claude's `top_action` was stored in research_state.json but never written to strategy_config.json. pipeline_executor.py's `apply_strategy_updates()` only adjusts min_quality_score via rule-based thresholds. spawn_fix_task is a bandaid.

**Why:** The pipeline was designed as a measurement + analysis loop but the write-back step was never implemented. The only auto-update was a simple quality_score adjuster in pipeline_executor.py.

**How to apply:** When building feedback loops, always verify the write-back step exists end-to-end. Structured output from LLM → validated patch → write to config → reload config. Added `apply_config_patch()` with whitelist + bounds checking.

---
name: smmu_threshold_fallback_missing
description: S-MMU similarity threshold loop exits silently when all slices filtered — legacy fallback not triggered
type: project
---

When `_load_relevant_slices()` in `smmu.py` filters all slices via `SIMILARITY_THRESHOLD` (because no
slice has centroid similarity ≥ threshold), `loaded_ids` ends up empty and the function returns silently
— leaving L1 context with only always-resident content and no dynamic memories.

**Why:** The existing exception-path fallback (`except Exception`) only triggers on DB/network errors, not on
a valid "everything below threshold" result. This is the classic "guard only the error path" gap.

**Fix applied (commit 93a18f4, 2026-03-23):** After the threshold loop, check `if not loaded_ids` and
call `_load_legacy_context()` explicitly. This ensures L1 always gets relevant memories even when the
similarity threshold is too strict for the current query.

**How to apply:** Any time a filtering loop in a fallback-safe function can produce an empty result without
raising an exception — add a post-loop empty-result guard that triggers the fallback path, not just the
exception handler.

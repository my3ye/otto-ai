---
name: project_gate_notifier
description: Gate notification system review (commit 6f66694, 2026-03-24): NEEDS_CHANGES. 2 critical call-site misses — gate engine uses _whastsapp_notify bypass in 2 of 3 notification points; _resolve_gate never calls gate_resolved().
type: project
---

Gate notification system (memory/gate_notifier.py) — commit 6f66694, 2026-03-24.
**Verdict: NEEDS_CHANGES**

**Why:** The notifier module itself is well-built (Protocol, Composite, soft-fail). But the same commit that added the module also added 5 gate engine functions to workflows.py, and 2 of those bypass the notifier entirely with `_whastsapp_notify()`.

**Critical issues:**
1. `_check_gate_timeouts` escalation path (line 1493): calls `_whastsapp_notify(msg)` instead of `gate_notifier.gate_escalated(gate, instance)` — webhook subscribers never see escalation events.
2. Pre-step gate block (line 623): calls `_whastsapp_notify(msg)` instead of `gate_notifier.gate_pending(gate, instance, step)` — again bypasses webhook.
3. `_resolve_gate` never calls `gate_notifier.gate_resolved()` — approvals/rejections are completely silent.

**Warnings:**
- `Protocol` imported in workflows.py (line 21) but unused there.
- Synthetic gate in human_approval block (line 800) uses `instance_id` as gate ID — resolve URL will 404 since no gate record in DB for this legacy path.
- Typo: `_whastsapp_notify` (double-s) persists in helper name and 2 call sites.

**How to apply:** When reviewing multi-channel notification abstractions, always trace EVERY call site in the same file — not just the one listed in the task description.

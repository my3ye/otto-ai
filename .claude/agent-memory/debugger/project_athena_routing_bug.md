---
name: athena_routing_priority_bug
description: Athena WhatsApp number responded as Otto (kernel) instead of as Athena — admin check ran before account routing
type: project
---

Athena line routing bug: gateway/handler.py checked `is_admin(msg)` BEFORE `account == "athena"`. Mev (admin) testing Athena's number got Otto's full kernel response instead of Athena's persona.

**Why:** Admin check was first in the routing chain — Athena account check only ran for non-admin messages. This was a routing priority error from the original implementation.

**How to apply:** When adding any specialized WhatsApp account (like Athena), its routing MUST come BEFORE the admin check in `gateway/handler.py`. Otherwise the admin/owner always bypasses it.

**Fix:** Commit 7970c8c — moved Athena account check to top of `handle_message()`, before `is_admin()`.

**Tools/permissions:** athena_handler.py already had zero system access — uses `provider_chat()` (pure LLM API call). No Claude Code tools, no filesystem. The only fix needed was routing order.

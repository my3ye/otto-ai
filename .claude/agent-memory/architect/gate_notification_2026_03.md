---
name: gate_notification_system_2026_03
description: Gate notification system design: WhatsApp + webhook for workflow gates. Standalone module gate_notifier.py with Protocol + CompositeGateNotifier.
type: project
---

Gate notification system designed (2026-03-24) as part of workflow gating Phase 1.

**Why:** workflows.py had 4 inline subprocess calls to whatsapp_send.sh — no abstraction, no extensibility, no webhook support. Needed a clean notification layer for the new gate engine.

**Key decisions:**
- Separate module `memory/gate_notifier.py` (not inline in workflows.py)
- `GateNotifier` Protocol + `WhatsAppGateNotifier` + `WebhookGateNotifier` + `CompositeGateNotifier`
- Module-level singleton `gate_notifier` built from config at import time
- Webhook: async httpx POST, 10s timeout, bearer auth (`Authorization: Bearer <token>`)
- WhatsApp: async subprocess → whatsapp_send.sh (matches existing pattern)
- Soft failure: all notifiers catch+log, never raise — notification failures cannot block gate engine

**Config additions (config.py):**
- `gate_whatsapp_enabled: bool = True`
- `gate_webhook_urls: str = ""` (comma-separated list)
- `gate_webhook_secret: str = ""` (bearer token)

**Webhook payload envelope:** standardized JSON with `event` field distinguishing gate_pending / gate_resolved / gate_escalated. Includes `resolve_url` and `vote_url` for DAO gates.

**Files:**
1. `memory/gate_notifier.py` — CREATE (new module)
2. `memory/config.py` — MODIFY (3 settings)
3. `memory/routes/workflows.py` — MODIFY (import + wire in gate engine)

**How to apply:** When implementing or extending gate notifications, the singleton pattern means only gate_notifier.py needs updating. Call sites in workflows.py stay clean.

Full design at: ~/otto/docs/gate-notification-architecture-2026-03-24.md
Parent design: ~/otto/docs/workflow-gating-architecture-2026-03-24.md

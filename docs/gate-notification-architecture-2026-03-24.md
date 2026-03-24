# Gate Notification System — Architecture Spec
*Architect: Otto | Date: 2026-03-24*
*Parent design: ~/otto/docs/workflow-gating-architecture-2026-03-24.md*

---

## Design: Gate Notification System (WhatsApp + Webhook)

### Problem

The workflow gating architecture defines a `GateNotifier` protocol (three methods: `gate_pending`, `gate_resolved`, `gate_escalated`) but the implementation was left as a stub. The existing `workflows.py` has 4 inline subprocess calls to `whatsapp_send.sh` — no abstraction, no extensibility, no webhook support.

We need:
1. A **standalone notification module** (`gate_notifier.py`) — not inline in the 1500-line `workflows.py`
2. **WhatsApp delivery** via the existing `whatsapp_send.sh` subprocess pattern
3. **Webhook delivery** — POST JSON event payloads to configurable URLs (for OMS integration, Zapier, on-chain hooks later)
4. **Composite fanout** — a single notifier that dispatches to all active channels
5. **Config-driven** — toggle each channel without code changes

---

### Approach

**Single module, three implementations, one singleton export.**

```
memory/gate_notifier.py
├── GateNotifier (typing.Protocol)
├── WhatsAppGateNotifier   — subprocess → whatsapp_send.sh
├── WebhookGateNotifier    — async httpx → N URLs, bearer auth
└── CompositeGateNotifier  — fans out to [WhatsApp, Webhook, ...]
    └── gate_notifier: GateNotifier  ← module-level singleton, built at import
```

Consumers (workflows.py) import the singleton:
```python
from ..gate_notifier import gate_notifier
```

Then call:
```python
await gate_notifier.gate_pending(gate, instance, step)
await gate_notifier.gate_resolved(gate, instance, resolution)
await gate_notifier.gate_escalated(gate, instance)
```

No changes to call sites needed if/when a channel is added or removed.

---

### Key Decisions

- **Separate module (not in workflows.py)**: `workflows.py` is 1500+ lines. Inline notification code is already duplicated 4 times. A dedicated `gate_notifier.py` is independently testable and swap-friendly. Alternative: add to workflows.py — rejected (increases maintenance surface, already messy).

- **Async subprocess for WhatsApp**: Matches the existing pattern in workflows.py (`asyncio.create_subprocess_exec`). Avoids introducing a new HTTP client dependency for the WhatsApp channel. Alternative: POST directly to `localhost:3001/send` via httpx — viable but adds dependency coupling and bypasses the shell script's error handling.

- **httpx for webhooks**: `httpx` supports async with connection pooling and timeout control. Already used elsewhere in Otto's stack. Alternative: `aiohttp` — not already installed, no benefit.

- **Bearer token auth for webhooks**: Matches the pattern in `notify.py` (`OTTO_WEBHOOK_SECRET`). Consistent security model. Alternative: HMAC signature on payload — higher integrity but more complex to configure; out of scope for Phase 1.

- **Comma-separated `gate_webhook_urls`**: Pydantic BaseSettings parses env vars as strings. A comma-sep string in `.env` is simple and doesn't require JSON array quoting in the env file. Alternative: JSON array — harder to write in `.env`.

- **Soft failure — never raise**: Notification failures must NOT propagate to the gate engine. A failed WhatsApp ping must not unblock or re-block a workflow gate. All notifier implementations catch exceptions and log a warning.

- **Message format**: Human-readable WhatsApp messages with emojis and key facts (workflow name, step, expires_at, resolve URL). Webhook payload is a structured JSON envelope with all gate fields — machine-parseable, not human-formatted.

---

### Config (config.py additions)

```python
# ── Gate Notification System ─────────────────────────────────────────────
gate_whatsapp_enabled: bool = True
# Comma-separated list of webhook URLs to POST gate events to
gate_webhook_urls: str = ""
# Optional bearer token sent as Authorization: Bearer <token> in webhook POSTs
gate_webhook_secret: str = ""
```

Add to `~/memory/.env` when needed:
```
GATE_WEBHOOK_URLS=https://oms.mev.otto.lk/hooks/gate,https://hooks.zapier.com/...
GATE_WEBHOOK_SECRET=<token>
```

---

### Webhook Payload Envelope

All three notification events POST the same envelope shape, with `event` distinguishing them:

```json
{
  "event": "gate_pending | gate_resolved | gate_escalated",

  "gate_id": "uuid",
  "gate_type": "human | dao",
  "gate_position": "pre | post",
  "gate_status": "pending | approved | rejected | timed_out | skipped",

  "instance_id": "uuid",
  "instance_name": "Workflow Name",

  "step_position": 2,
  "step_name": "Security Audit",

  "expires_at": "2026-03-25T04:39:25+00:00",
  "timeout_seconds": 86400,
  "timeout_action": "escalate",

  "context_snapshot": { "step_output": "...", "variables": {} },

  "resolved_by": null,
  "resolved_at": null,
  "resolution_reason": null,

  "quorum_required": null,
  "approval_threshold": 0.5,

  "resolve_url": "http://otto.lk:8100/workflows/gates/{gate_id}/resolve",
  "vote_url":    "http://otto.lk:8100/workflows/gates/{gate_id}/vote",

  "timestamp": "2026-03-24T04:39:25+00:00"
}
```

For `gate_resolved`, `resolved_by`, `resolved_at`, and `resolution_reason` are populated.
For `gate_escalated`, `context_snapshot` includes escalation count.

---

### WhatsApp Message Templates

#### gate_pending — human type
```
🔒 Gate pending: 'Security Audit Workflow'
Step 2: Security Audit (post-step)
Type: Human approval
Expires: 2026-03-25 04:39 UTC (24h)

Approve: POST /workflows/gates/{id}/resolve
  {"action": "approve", "reason": "..."}

Gate ID: abc12345
```

#### gate_pending — DAO type
```
🗳️ DAO vote open: 'Security Audit Workflow'
Step 2: Security Audit
Quorum needed: 3 votes | Threshold: 60%
Expires: 2026-03-25 04:39 UTC

Vote: POST /workflows/gates/{id}/vote
  {"vote": "approve", "reason": "..."}

Gate ID: abc12345
```

#### gate_resolved — approved
```
✅ Gate approved: 'Security Audit Workflow'
Step 2: Security Audit
By: mev | Reason: Looks good
```

#### gate_resolved — rejected
```
❌ Gate rejected: 'Security Audit Workflow'
Step 2: Security Audit
By: mev | Reason: Needs revision
```

#### gate_resolved — skipped
```
⏭️ Gate skipped: 'Security Audit Workflow'
Step 2: Security Audit
```

#### gate_escalated
```
⚠️ Gate timed out — escalated: 'Security Audit Workflow'
Step 2: Security Audit (post-step)
Extended 1h. Please review and approve.

Gate ID: abc12345
```

---

### Module Code: gate_notifier.py

```python
"""
Gate notification system — WhatsApp + outbound webhooks.

Three implementations:
  WhatsAppGateNotifier  — async subprocess → whatsapp_send.sh
  WebhookGateNotifier   — async httpx POST to configured URLs
  CompositeGateNotifier — fans out to all active notifiers

Usage:
    from ..gate_notifier import gate_notifier
    await gate_notifier.gate_pending(gate, instance, step)
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Protocol, runtime_checkable

log = logging.getLogger("otto.gate_notifier")

WHATSAPP_SEND = "/home/web3relic/otto/tools/whatsapp_send.sh"
MEMORY_API_BASE = "http://localhost:8100"
WA_MAX_CHARS = 3500


# ── Protocol ──────────────────────────────────────────────────────────────

@runtime_checkable
class GateNotifier(Protocol):
    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None: ...
    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None: ...
    async def gate_escalated(self, gate: dict, instance: dict) -> None: ...


# ── WhatsApp Notifier ──────────────────────────────────────────────────────

class WhatsAppGateNotifier:

    async def _send(self, msg: str) -> None:
        try:
            if len(msg) > WA_MAX_CHARS:
                msg = msg[:WA_MAX_CHARS - 20] + "\n...[truncated]"
            proc = await asyncio.create_subprocess_exec(
                WHATSAPP_SEND, msg,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=15)
        except Exception as e:
            log.warning(f"WhatsApp gate notification failed: {e}")

    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None:
        gate_id = str(gate.get("id", ""))[:8]
        gate_type = gate.get("gate_type", "human")
        gate_pos = gate.get("gate_position", "post")
        step_name = step.get("name", f"Step {gate.get('step_position', '?')}")
        inst_name = instance.get("name", "Workflow")
        expires = (gate.get("expires_at") or "")[:16].replace("T", " ")

        resolve_url = f"POST /workflows/gates/{gate.get('id', '')}/resolve"
        vote_url    = f"POST /workflows/gates/{gate.get('id', '')}/vote"

        if gate_type == "dao":
            quorum = gate.get("quorum_required", "?")
            threshold = int(float(gate.get("approval_threshold", 0.5)) * 100)
            msg = (
                f"🗳️ *DAO vote open:* '{inst_name}'\n"
                f"Step: {step_name} ({gate_pos}-step)\n"
                f"Quorum needed: {quorum} votes | Threshold: {threshold}%\n"
                f"Expires: {expires} UTC\n\n"
                f"Vote:\n{vote_url}\n"
                f'  {{"vote": "approve", "reason": "..."}}\n\n'
                f"Gate: {gate_id}"
            )
        else:
            timeout_h = int(gate.get("timeout_seconds", 86400)) // 3600
            msg = (
                f"🔒 *Gate pending:* '{inst_name}'\n"
                f"Step: {step_name} ({gate_pos}-step)\n"
                f"Type: Human approval | Timeout: {timeout_h}h\n"
                f"Expires: {expires} UTC\n\n"
                f"Approve:\n{resolve_url}\n"
                f'  {{"action": "approve", "reason": "..."}}\n\n'
                f"Gate: {gate_id}"
            )
        await self._send(msg)

    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None:
        emoji = {"approved": "✅", "rejected": "❌", "skipped": "⏭️"}.get(resolution, "ℹ️")
        inst_name = instance.get("name", "Workflow")
        step_pos = gate.get("step_position", "?")
        by = gate.get("resolved_by", "unknown")
        reason = gate.get("resolution_reason", "")

        msg = (
            f"{emoji} *Gate {resolution}:* '{inst_name}'\n"
            f"Step {step_pos}"
        )
        if by:
            msg += f" | By: {by}"
        if reason:
            msg += f"\nReason: {reason}"
        await self._send(msg)

    async def gate_escalated(self, gate: dict, instance: dict) -> None:
        inst_name = instance.get("name", "Workflow")
        step_pos = gate.get("step_position", "?")
        step_name = f"Step {step_pos}"
        gate_pos = gate.get("gate_position", "post")
        gate_id_short = str(gate.get("id", ""))[:8]
        resolve_url = f"POST /workflows/gates/{gate.get('id', '')}/resolve"

        msg = (
            f"⚠️ *Gate timed out — escalated:* '{inst_name}'\n"
            f"{step_name} ({gate_pos}-step)\n"
            f"Extended 1h. Please review and approve.\n\n"
            f"Approve:\n{resolve_url}\n"
            f'  {{"action": "approve", "reason": "..."}}\n\n'
            f"Gate: {gate_id_short}"
        )
        await self._send(msg)


# ── Webhook Notifier ───────────────────────────────────────────────────────

class WebhookGateNotifier:

    def __init__(self, urls: List[str], secret: str = ""):
        self.urls = [u.strip() for u in urls if u.strip()]
        self.secret = secret

    def _build_payload(self, event: str, gate: dict, instance: dict,
                       step: Optional[dict] = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        gate_id = str(gate.get("id", ""))
        return {
            "event": event,
            "gate_id": gate_id,
            "gate_type": gate.get("gate_type", "human"),
            "gate_position": gate.get("gate_position", "post"),
            "gate_status": gate.get("status", "pending"),
            "instance_id": str(instance.get("id", "")),
            "instance_name": instance.get("name", ""),
            "step_position": gate.get("step_position"),
            "step_name": (step or {}).get("name", f"Step {gate.get('step_position', '?')}"),
            "expires_at": (gate.get("expires_at") or now),
            "timeout_seconds": gate.get("timeout_seconds", 86400),
            "timeout_action": gate.get("timeout_action", "escalate"),
            "context_snapshot": gate.get("context_snapshot") or {},
            "resolved_by": gate.get("resolved_by"),
            "resolved_at": gate.get("resolved_at"),
            "resolution_reason": gate.get("resolution_reason"),
            "quorum_required": gate.get("quorum_required"),
            "approval_threshold": float(gate.get("approval_threshold") or 0.5),
            "resolve_url": f"{MEMORY_API_BASE}/workflows/gates/{gate_id}/resolve",
            "vote_url":    f"{MEMORY_API_BASE}/workflows/gates/{gate_id}/vote",
            "timestamp": now,
        }

    async def _post(self, payload: dict) -> None:
        try:
            import httpx
            headers = {"Content-Type": "application/json"}
            if self.secret:
                headers["Authorization"] = f"Bearer {self.secret}"
            body = json.dumps(payload)
            async with httpx.AsyncClient(timeout=10) as client:
                for url in self.urls:
                    try:
                        resp = await client.post(url, content=body, headers=headers)
                        log.info(f"Gate webhook → {url}: {resp.status_code}")
                    except Exception as e:
                        log.warning(f"Gate webhook failed → {url}: {e}")
        except ImportError:
            log.warning("httpx not installed — webhook notifications disabled")
        except Exception as e:
            log.warning(f"Gate webhook error: {e}")

    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None:
        if not self.urls:
            return
        payload = self._build_payload("gate_pending", gate, instance, step)
        await self._post(payload)

    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None:
        if not self.urls:
            return
        payload = self._build_payload("gate_resolved", gate, instance)
        payload["gate_status"] = resolution
        await self._post(payload)

    async def gate_escalated(self, gate: dict, instance: dict) -> None:
        if not self.urls:
            return
        payload = self._build_payload("gate_escalated", gate, instance)
        await self._post(payload)


# ── Composite Notifier (fanout) ────────────────────────────────────────────

class CompositeGateNotifier:

    def __init__(self, notifiers: List):
        self.notifiers = notifiers

    async def gate_pending(self, gate: dict, instance: dict, step: dict) -> None:
        for n in self.notifiers:
            try:
                await n.gate_pending(gate, instance, step)
            except Exception as e:
                log.warning(f"Notifier {n.__class__.__name__} gate_pending failed: {e}")

    async def gate_resolved(self, gate: dict, instance: dict, resolution: str) -> None:
        for n in self.notifiers:
            try:
                await n.gate_resolved(gate, instance, resolution)
            except Exception as e:
                log.warning(f"Notifier {n.__class__.__name__} gate_resolved failed: {e}")

    async def gate_escalated(self, gate: dict, instance: dict) -> None:
        for n in self.notifiers:
            try:
                await n.gate_escalated(gate, instance)
            except Exception as e:
                log.warning(f"Notifier {n.__class__.__name__} gate_escalated failed: {e}")


# ── Singleton (built at import time from config) ───────────────────────────

def _build_notifier() -> GateNotifier:
    from .config import settings

    active: list = []

    if settings.gate_whatsapp_enabled:
        active.append(WhatsAppGateNotifier())
        log.debug("Gate notifier: WhatsApp enabled")

    urls = [u for u in settings.gate_webhook_urls.split(",") if u.strip()]
    if urls:
        active.append(WebhookGateNotifier(urls, secret=settings.gate_webhook_secret))
        log.debug(f"Gate notifier: Webhook enabled ({len(urls)} URLs)")

    if not active:
        log.warning("Gate notifier: no channels configured — gate events will be silent")
        # Return a no-op composite
        return CompositeGateNotifier([])

    if len(active) == 1:
        return active[0]

    return CompositeGateNotifier(active)


gate_notifier: GateNotifier = _build_notifier()
```

---

### Integration into workflows.py

Two call sites to add (once gate engine is implemented in the parallel task):

**1. In `_create_gate` (after inserting the gate row):**
```python
from ..gate_notifier import gate_notifier

# ... after INSERT + UPDATE workflow_instances ...
asyncio.create_task(
    gate_notifier.gate_pending(
        {"id": str(gate_id), **gate_cfg,
         "expires_at": expires_at.isoformat(),
         "step_position": step_position,
         "gate_type": gate_cfg.get("type", "human"),
         "gate_position": gate_position,
         "timeout_seconds": timeout_s},
        inst_dict,
        step_dict,
    )
)
```

**2. In `_resolve_gate` (after UPDATE workflow_gates):**
```python
asyncio.create_task(
    gate_notifier.gate_resolved(gate_dict, inst_dict, gate_status)
)
```

**3. In `_check_gate_timeouts` (escalate branch):**
```python
asyncio.create_task(
    gate_notifier.gate_escalated(dict(gate), {"name": gate["workflow_name"]})
)
```

**4. Remove the 4 inline `whatsapp_send.sh` subprocess calls** that currently handle `review_mode="human_approval"` in workflows.py — those will be replaced by the gate engine + notifier once the gate checkpoint engine task completes.

---

### Files to Create/Modify

| File | Action | What |
|---|---|---|
| `memory/gate_notifier.py` | **CREATE** | Full module: Protocol + 3 implementations + singleton |
| `memory/config.py` | **MODIFY** | Add 3 gate notification settings |
| `memory/routes/workflows.py` | **MODIFY** (later) | Import + use `gate_notifier` in gate engine functions |

**This step (Step 0) only produces the design.**
Steps 1+ implement `gate_notifier.py`, then config.py, then workflows.py integration.

---

### Implementation Plan (for downstream coder task)

1. **Create `memory/gate_notifier.py`** — exact code above, as a standalone file
2. **Edit `memory/config.py`** — add `gate_whatsapp_enabled`, `gate_webhook_urls`, `gate_webhook_secret` settings
3. **Verify httpx installed** — `pip show httpx`; install if missing: `pip install httpx`
4. **Smoke test** — `python3 -c "from otto.memory.gate_notifier import gate_notifier; print(gate_notifier)"`
5. **Wire into workflows.py** — import `gate_notifier`, add call sites in `_create_gate`, `_resolve_gate`, `_check_gate_timeouts`
6. **Remove duplication** — delete the 4 inline subprocess WhatsApp calls for `review_mode=human_approval` (only after gate engine is wired in — coordinate with parallel task)

---

### Risks

- **httpx availability**: Used for webhook POSTs. May not be installed. **Mitigation**: graceful ImportError fallback already in code; add to requirements.txt / install check.
- **WhatsApp send latency**: subprocess startup is ~200ms. Gates created in hot paths. **Mitigation**: `asyncio.create_task()` wraps all notifications — non-blocking.
- **Message length**: Workflow names + step names can be long. **Mitigation**: WA_MAX_CHARS=3500 cap with smart truncation.
- **Config import at module load**: `_build_notifier()` imports `settings` when `gate_notifier.py` is first imported. If config is broken, import fails. **Mitigation**: wrap in try/except, fall back to `CompositeGateNotifier([])` with a warning.

---

*Full design at: ~/otto/docs/gate-notification-architecture-2026-03-24.md*
*Parent design: ~/otto/docs/workflow-gating-architecture-2026-03-24.md*
*Next step: implement gate_notifier.py*

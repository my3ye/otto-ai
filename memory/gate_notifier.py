"""
Gate notification system — WhatsApp + outbound webhooks.

Three implementations:
  WhatsAppGateNotifier  — async subprocess → whatsapp_send.sh
  WebhookGateNotifier   — async httpx POST to configured URLs
  CompositeGateNotifier — fans out to all active notifiers

Usage:
    from ..gate_notifier import gate_notifier
    await gate_notifier.gate_pending(gate, instance, step)

    # Or fire-and-forget (non-blocking):
    asyncio.create_task(gate_notifier.gate_pending(gate, instance, step))
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
            threshold = int(float(gate.get("approval_threshold") or 0.5) * 100)
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
            timeout_h = int(gate.get("timeout_seconds") or 86400) // 3600
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
        by = gate.get("resolved_by", "")
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
            "expires_at": gate.get("expires_at") or now,
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

def _build_notifier() -> "GateNotifier":
    try:
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
            return CompositeGateNotifier([])

        if len(active) == 1:
            return active[0]

        return CompositeGateNotifier(active)

    except Exception as e:
        log.warning(f"Gate notifier: failed to build from config ({e}) — using no-op")
        return CompositeGateNotifier([])


gate_notifier: GateNotifier = _build_notifier()

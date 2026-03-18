"""WhatsApp channel adapter — thin wrapper over the gateway.

Translates WhatsAppIncoming → GatewayMessage, calls handle_message(),
then delivers the response via the WhatsApp service on :3001.
"""

import logging
import os
import httpx
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import WhatsAppIncoming
from ..gateway.models import GatewayMessage
from ..gateway.handler import handle_message

log = logging.getLogger("otto.whatsapp")

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

OWNER_JID = "94743806705@s.whatsapp.net"


@router.post("/incoming")
async def handle_incoming(req: WhatsAppIncoming):
    """WhatsApp incoming → gateway → deliver reply via WhatsApp service."""
    # Translate to normalized gateway message
    gw_msg = GatewayMessage(
        channel="whatsapp",
        sender_id=req.from_jid,
        sender_name=req.push_name,
        content=req.message,
    )

    # Process through the gateway
    response = await handle_message(gw_msg)

    # If ignored (not admin), return early
    if response.metadata.get("status") == "ignored":
        return {"status": "ignored", "reason": response.metadata.get("reason")}

    # Deliver reply via WhatsApp service
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(
                f"{settings.whatsapp_url}/send",
                json={"jid": req.from_jid, "message": response.content},
            )
    except Exception as e:
        return {"status": "generated", "reply": response.content, "send_error": str(e)}

    return {
        "status": "sent",
        "reply": response.content,
        "resolved_question": response.metadata.get("resolved_question", False),
        "cross_brain_note": response.metadata.get("cross_brain_note", False),
        "claude_delegated": response.metadata.get("claude_delegated", False),
    }


@router.get("/accounts")
async def get_whatsapp_accounts():
    """Returns connection status for all WhatsApp accounts (Otto + Athena)."""
    accounts = []

    # ── Otto account (Ottolabs line, :3001) ─────────────────────────────────
    otto_status = {
        "id": "otto",
        "name": "Otto",
        "display_name": "Ottolabs (Otto)",
        "phone": "+94703100654",
        "purpose": "Main Otto communication line — handles incoming commands from Mev",
        "service": "whatsapp.service",
        "port": 3001,
        "auth_dir": "/home/web3relic/interfaces/whatsapp/auth_state",
        "connected": False,
        "silent_seconds": None,
        "status": "unknown",
        "error": None,
    }
    try:
        async with httpx.AsyncClient(timeout=3.0) as http:
            resp = await http.get("http://localhost:3001/health")
            if resp.status_code == 200:
                data = resp.json()
                otto_status["connected"] = data.get("connected", False)
                otto_status["silent_seconds"] = data.get("silent_seconds")
                otto_status["status"] = "connected" if data.get("connected") else "disconnected"
            else:
                otto_status["status"] = "error"
                otto_status["error"] = f"HTTP {resp.status_code}"
    except Exception as e:
        otto_status["status"] = "unreachable"
        otto_status["error"] = str(e)
    accounts.append(otto_status)

    # ── Athena account (WebAssist line) ─────────────────────────────────────
    athena_auth_dir = "/home/web3relic/interfaces/athena-whatsapp/auth_state"
    athena_creds = os.path.join(athena_auth_dir, "creds.json")
    athena_has_creds = os.path.exists(athena_creds)
    athena_creds_mtime = None
    if athena_has_creds:
        import datetime
        mtime = os.path.getmtime(athena_creds)
        athena_creds_mtime = datetime.datetime.fromtimestamp(mtime).isoformat()

    athena_status = {
        "id": "athena",
        "name": "Athena",
        "display_name": "Athena (WebAssist)",
        "phone": "+94743768830",
        "purpose": "WebAssist customer line — handles leads and client communication",
        "service": "athena-whatsapp.service",
        "port": None,
        "auth_dir": athena_auth_dir,
        "connected": False,
        "silent_seconds": None,
        "status": "no_service",
        "has_credentials": athena_has_creds,
        "credentials_saved_at": athena_creds_mtime,
        "error": "Athena service not running — auth_state exists but no systemd service",
    }

    # Check if athena service is actually running on some port
    for port in [3002, 3003, 3004]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as http:
                resp = await http.get(f"http://localhost:{port}/health")
                if resp.status_code == 200:
                    data = resp.json()
                    athena_status["connected"] = data.get("connected", False)
                    athena_status["needs_auth"] = data.get("needs_auth", False)
                    athena_status["silent_seconds"] = data.get("silent_seconds")
                    # Use status from health endpoint directly if available
                    svc_status = data.get("status", "")
                    if svc_status == "ok" or data.get("connected"):
                        athena_status["status"] = "connected"
                        athena_status["error"] = None
                    elif svc_status == "needs_qr" or data.get("has_qr"):
                        athena_status["status"] = "needs_qr"
                        athena_status["error"] = "QR code ready — scan from WhatsApp to link Athena"
                    elif svc_status == "needs_auth" or data.get("needs_auth"):
                        athena_status["status"] = "needs_auth"
                        athena_status["error"] = "Session expired — trigger reconnect to get new QR"
                    else:
                        athena_status["status"] = "disconnected"
                    athena_status["has_qr"] = data.get("has_qr", False)
                    athena_status["port"] = port
                    break
        except Exception:
            continue

    accounts.append(athena_status)

    return {
        "accounts": accounts,
        "total": len(accounts),
        "connected": sum(1 for a in accounts if a.get("connected")),
    }


@router.get("/accounts/athena/qr")
async def get_athena_qr():
    """Proxy the QR code from the Athena WhatsApp service for OMS display."""
    for port in [3002, 3003, 3004]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"http://localhost:{port}/qr")
                if resp.status_code in (200, 202):
                    return resp.json()
        except Exception:
            continue
    return {"status": "no_service", "qr": None}


@router.post("/accounts/athena/reconnect")
async def reconnect_athena():
    """Trigger Athena reconnect to generate a fresh QR code."""
    for port in [3002, 3003, 3004]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"http://localhost:{port}/qr")
                if resp.status_code in (200, 202):
                    return {"status": "triggered", "port": port}
        except Exception:
            continue
    return {"status": "no_service"}


@router.post("/accounts/send-test")
async def send_test_message(account_id: str = "otto"):
    """Send a test message to verify WhatsApp connection."""
    if account_id == "otto":
        port = 3001
    else:
        return {"status": "error", "error": "Athena service not running"}

    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            resp = await http.post(
                f"http://localhost:{port}/send",
                json={"jid": OWNER_JID, "message": "🔧 Test message from OMS WhatsApp Accounts page"},
            )
            if resp.status_code == 200:
                return {"status": "sent", "account": account_id}
            return {"status": "error", "error": f"HTTP {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


class WhatsAppSearchQuery(BaseModel):
    query: str
    limit: int = 10


@router.post("/search")
async def search_whatsapp(req: WhatsAppSearchQuery):
    """Semantic search over stored WhatsApp messages."""
    pool = await get_pool()
    embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    rows = await pool.fetch(
        """SELECT id, direction, content, jid, push_name, created_at, metadata,
                  1 - (embedding <=> $1::halfvec) AS score
           FROM whatsapp_messages
           WHERE embedding IS NOT NULL
           ORDER BY embedding <=> $1::halfvec
           LIMIT $2""",
        embedding_str, req.limit,
    )
    return {
        "query": req.query,
        "results": [
            {
                "id": str(r["id"]),
                "direction": r["direction"],
                "content": r["content"],
                "jid": r["jid"],
                "push_name": r["push_name"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "score": float(r["score"]),
                "metadata": r["metadata"],
            }
            for r in rows
        ],
        "count": len(rows),
    }

"""
Broadcast System API routes.
Provides HTTP endpoints to trigger and inspect broadcast operations.
"""

import sys
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

# Add broadcast project to path so we can import from it
_BROADCAST_PATH = Path("/home/web3relic/otto/projects/broadcast")
if str(_BROADCAST_PATH.parent) not in sys.path:
    sys.path.insert(0, str(_BROADCAST_PATH.parent))

log = logging.getLogger("otto.broadcast")
router = APIRouter(prefix="/broadcast", tags=["broadcast"])


class BroadcastRequest(BaseModel):
    content: str
    format: str = "short"           # short | article
    title: Optional[str] = None
    tags: list[str] = []
    media_urls: list[str] = []
    platform_overrides: dict = {}
    platforms: Optional[list[str]] = None   # None = all enabled


class BroadcastSendResponse(BaseModel):
    id: str
    timestamp: str
    content: str
    platforms_attempted: int
    platforms_succeeded: int
    results: list[dict]


@router.post("/send", response_model=BroadcastSendResponse)
async def broadcast_send(req: BroadcastRequest):
    """Send a broadcast message to all (or specified) platforms."""
    try:
        from broadcast.broadcast import BroadcastEngine
        from broadcast.models import BroadcastMessage
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Broadcast module not available: {e}")

    msg = BroadcastMessage(
        content=req.content,
        format=req.format,
        title=req.title,
        tags=req.tags,
        media_urls=req.media_urls,
        platform_overrides=req.platform_overrides,
    )

    try:
        engine = BroadcastEngine()
        record = await engine.send(msg, platforms=req.platforms)
    except Exception as e:
        log.exception("Broadcast failed")
        raise HTTPException(status_code=500, detail=str(e))

    from dataclasses import asdict
    return asdict(record)


@router.get("/status")
async def broadcast_status(limit: int = 20):
    """Return recent broadcast history."""
    try:
        from broadcast.broadcast import BroadcastEngine
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Broadcast module not available: {e}")

    engine = BroadcastEngine()
    history = engine.get_history(limit=limit)
    return {"broadcasts": history, "count": len(history)}


@router.get("/platforms")
async def broadcast_platforms():
    """Return all platforms with their enabled/credential status."""
    try:
        from broadcast.config import get_all_platforms
        from broadcast.adapters import list_adapters
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Broadcast module not available: {e}")

    platforms = get_all_platforms()
    implemented = set(list_adapters())

    result = {}
    for name, info in platforms.items():
        result[name] = {
            **info,
            "adapter_implemented": name in implemented,
            "ready": info["enabled"] and info["has_credentials"] and name in implemented,
        }

    return {"platforms": result, "implemented": sorted(implemented)}

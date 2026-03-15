"""
Broadcast System API routes.
Provides HTTP endpoints to trigger, inspect, and configure broadcast operations.

Platform config management lets Mev add credentials from OMS Settings without
touching the filesystem directly. Credentials are stored in
~/otto/projects/broadcast/configs/platforms.json.
"""

import sys
import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add broadcast project to path so we can import from it
_BROADCAST_PATH = Path("/home/web3relic/otto/projects/broadcast")
_CONFIG_PATH = _BROADCAST_PATH / "configs" / "platforms.json"
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


class PlatformConfigUpdate(BaseModel):
    """Update credentials + enabled state for a single platform.
    Only provided fields are updated — others are left unchanged.
    """
    enabled: Optional[bool] = None
    credentials: Optional[dict[str, Any]] = None  # key→value pairs merged into platform config


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


@router.get("/platforms/{platform}/config")
async def get_platform_config(platform: str):
    """Get platform configuration (credentials redacted to boolean presence).

    Returns which fields are configured without exposing actual secret values.
    """
    if not _CONFIG_PATH.exists():
        raise HTTPException(500, "Platform config file not found")

    with open(_CONFIG_PATH) as f:
        cfg = json.load(f)

    platforms = cfg.get("platforms", {})
    if platform not in platforms:
        raise HTTPException(404, f"Platform '{platform}' not in config")

    pcfg = platforms[platform]
    # Redact non-boolean credential fields — show presence only
    redacted = {}
    for k, v in pcfg.items():
        if k == "enabled":
            redacted[k] = v
        elif isinstance(v, bool):
            redacted[k] = v
        elif isinstance(v, str):
            redacted[k] = "***" if v else ""
        elif isinstance(v, list):
            redacted[k] = f"[{len(v)} items]" if v else []
        elif isinstance(v, dict):
            redacted[k] = {dk: ("***" if dv else "") for dk, dv in v.items()}
        else:
            redacted[k] = v

    return {"platform": platform, "config": redacted}


@router.patch("/platforms/{platform}/config")
async def update_platform_config(platform: str, body: PlatformConfigUpdate):
    """Update credentials and/or enabled state for a platform.

    Credentials are merged (not replaced) — only provided keys are updated.
    Stored in ~/otto/projects/broadcast/configs/platforms.json.
    """
    if not _CONFIG_PATH.exists():
        raise HTTPException(500, "Platform config file not found")

    with open(_CONFIG_PATH) as f:
        cfg = json.load(f)

    platforms = cfg.get("platforms", {})
    if platform not in platforms:
        raise HTTPException(404, f"Platform '{platform}' not in config")

    pcfg = platforms[platform]

    if body.enabled is not None:
        pcfg["enabled"] = body.enabled

    if body.credentials:
        for k, v in body.credentials.items():
            # Only update keys that already exist in the platform config schema
            # This prevents adding arbitrary junk keys
            if k in pcfg:
                pcfg[k] = v
            else:
                # Allow new credential keys (some platforms have dynamic fields)
                pcfg[k] = v
                log.info("New credential key added to %s: %s", platform, k)

    platforms[platform] = pcfg
    cfg["platforms"] = platforms

    with open(_CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)

    log.info("Updated config for platform: %s (enabled=%s)", platform, pcfg.get("enabled"))

    # Return redacted confirmation
    has_creds = _check_credentials(platform, pcfg)
    return {
        "platform": platform,
        "enabled": pcfg.get("enabled", False),
        "has_credentials": has_creds,
        "updated": True,
    }


def _check_credentials(platform: str, cfg: dict) -> bool:
    """Same heuristic as broadcast.config._has_credentials but inline."""
    checks = {
        "telegram": ["bot_token"],
        "bluesky": ["handle", "app_password"],
        "discord": [],
        "mastodon": ["access_token"],
        "devto": ["api_key"],
        "nostr": ["private_key_hex"],
        "lemmy": ["username", "password"],
        "hashnode": ["token", "publication_id"],
        "threads": ["access_token", "user_id"],
        "x": [],
    }
    fields = checks.get(platform, [])
    if platform == "discord":
        return any(v for v in cfg.get("webhooks", {}).values())
    if platform == "x":
        return len(cfg.get("accounts", [])) > 0
    return all(bool(cfg.get(f)) for f in fields)

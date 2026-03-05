"""Bluesky AT Protocol adapter."""

import httpx
from datetime import datetime, timezone
from ..models import BroadcastMessage, PlatformResult

CHAR_LIMIT = 300


class BlueskyAdapter:
    name = "bluesky"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        handle = cfg.get("handle", "")
        app_password = cfg.get("app_password", "")
        pds = cfg.get("pds_url", "https://bsky.social").rstrip("/")

        if not handle or not app_password:
            return PlatformResult(platform=self.name, success=False, error="Missing handle or app_password in config")

        text = message.platform_overrides.get("bluesky", {}).get("content", message.content)
        text = text[:CHAR_LIMIT]  # Bluesky hard limit

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                # Step 1: create session
                sess_r = await client.post(
                    f"{pds}/xrpc/com.atproto.server.createSession",
                    json={"identifier": handle, "password": app_password},
                )
                sess = sess_r.json()
                if "accessJwt" not in sess:
                    return PlatformResult(
                        platform=self.name, success=False, status_code=sess_r.status_code,
                        error=sess.get("message", "Auth failed"),
                    )

                # Step 2: create post record
                r = await client.post(
                    f"{pds}/xrpc/com.atproto.repo.createRecord",
                    headers={"Authorization": f"Bearer {sess['accessJwt']}"},
                    json={
                        "repo": sess["did"],
                        "collection": "app.bsky.feed.post",
                        "record": {
                            "$type": "app.bsky.feed.post",
                            "text": text,
                            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                        },
                    },
                )
            data = r.json()
            if r.status_code == 200:
                rkey = data.get("uri", "").split("/")[-1]
                post_url = f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else None
                return PlatformResult(
                    platform=self.name, success=True, status_code=r.status_code, url=post_url,
                )
            return PlatformResult(
                platform=self.name, success=False, status_code=r.status_code,
                error=data.get("message", f"HTTP {r.status_code}"),
            )
        except Exception as e:
            return PlatformResult(platform=self.name, success=False, error=str(e))

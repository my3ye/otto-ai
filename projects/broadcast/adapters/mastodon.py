"""Mastodon REST API adapter."""

import httpx
from ..models import BroadcastMessage, PlatformResult

CHAR_LIMIT = 500


class MastodonAdapter:
    name = "mastodon"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        instance = cfg.get("instance", "https://mastodon.social").rstrip("/")
        access_token = cfg.get("access_token", "")
        visibility = cfg.get("visibility", "public")

        if not access_token:
            return PlatformResult(platform=self.name, success=False, error="Missing access_token in config")

        text = message.platform_overrides.get("mastodon", {}).get("content", message.content)
        text = text[:CHAR_LIMIT]

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(
                    f"{instance}/api/v1/statuses",
                    headers={"Authorization": f"Bearer {access_token}"},
                    data={"status": text, "visibility": visibility},
                )
            if r.status_code == 200:
                data = r.json()
                return PlatformResult(
                    platform=self.name, success=True, status_code=r.status_code,
                    url=data.get("url"),
                )
            return PlatformResult(
                platform=self.name, success=False, status_code=r.status_code,
                error=r.text[:200],
            )
        except Exception as e:
            return PlatformResult(platform=self.name, success=False, error=str(e))

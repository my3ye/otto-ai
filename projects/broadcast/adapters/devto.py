"""Dev.to article publishing adapter."""

import httpx
from ..models import BroadcastMessage, PlatformResult


class DevtoAdapter:
    name = "devto"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        api_key = cfg.get("api_key", "")
        if not api_key:
            return PlatformResult(platform=self.name, success=False, error="Missing api_key in config")

        # Dev.to requires a title — use provided or generate from content
        title = message.title or message.content[:80].split("\n")[0].strip("# ").strip()
        body = message.platform_overrides.get("devto", {}).get("content", message.content)
        tags = message.tags[:4] or ["ai", "opensource", "decentralized", "future"]
        org_id = cfg.get("organization_id")

        article_payload: dict = {
            "title": title,
            "body_markdown": body,
            "tags": tags,
            "published": True,
        }
        if org_id:
            article_payload["organization_id"] = org_id

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                r = await client.post(
                    "https://dev.to/api/articles",
                    headers={"api-key": api_key},
                    json={"article": article_payload},
                )
            if r.status_code == 201:
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

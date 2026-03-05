"""Discord webhook adapter. Posts to all configured webhooks."""

import httpx
from ..models import BroadcastMessage, PlatformResult


class DiscordAdapter:
    name = "discord"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        webhooks: dict = cfg.get("webhooks", {})
        active = {name: url for name, url in webhooks.items() if url}

        if not active:
            return PlatformResult(platform=self.name, success=False, error="No webhook URLs configured")

        text = message.platform_overrides.get("discord", {}).get("content", message.content)

        # Discord max 2000 chars for content field
        payload = {"content": text[:2000]}

        results = []
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                for name, url in active.items():
                    r = await client.post(url, json=payload)
                    results.append({
                        "webhook": name,
                        "status": r.status_code,
                        "ok": r.status_code in (200, 204),
                    })

            all_ok = all(r["ok"] for r in results)
            failed = [r["webhook"] for r in results if not r["ok"]]
            return PlatformResult(
                platform=self.name,
                success=all_ok,
                error=f"Failed webhooks: {failed}" if failed else None,
                extra={"webhooks": results},
            )
        except Exception as e:
            return PlatformResult(platform=self.name, success=False, error=str(e))

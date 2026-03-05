"""Telegram Bot API adapter."""

import httpx
from ..models import BroadcastMessage, PlatformResult


class TelegramAdapter:
    name = "telegram"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        token = cfg.get("bot_token", "")
        channel = cfg.get("channel", "")
        if not token or not channel:
            return PlatformResult(platform=self.name, success=False, error="Missing bot_token or channel in config")

        # Use platform override if provided
        text = message.platform_overrides.get("telegram", {}).get("content", message.content)

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": channel,
            "text": text,
            "parse_mode": cfg.get("parse_mode", "HTML"),
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.post(url, json=payload)
            data = r.json()
            if r.status_code == 200 and data.get("ok"):
                msg_id = data.get("result", {}).get("message_id")
                chan = channel.lstrip("@")
                post_url = f"https://t.me/{chan}/{msg_id}" if msg_id else None
                return PlatformResult(
                    platform=self.name, success=True,
                    status_code=r.status_code, url=post_url,
                )
            return PlatformResult(
                platform=self.name, success=False,
                status_code=r.status_code,
                error=data.get("description", f"HTTP {r.status_code}"),
            )
        except Exception as e:
            return PlatformResult(platform=self.name, success=False, error=str(e))

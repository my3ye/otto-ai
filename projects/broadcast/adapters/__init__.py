"""
Platform adapter registry.
Each adapter implements: async def post(message: BroadcastMessage, cfg: dict) -> PlatformResult
"""

from .telegram import TelegramAdapter
from .bluesky import BlueskyAdapter
from .discord import DiscordAdapter
from .mastodon import MastodonAdapter
from .devto import DevtoAdapter

_REGISTRY = {
    "telegram": TelegramAdapter(),
    "bluesky": BlueskyAdapter(),
    "discord": DiscordAdapter(),
    "mastodon": MastodonAdapter(),
    "devto": DevtoAdapter(),
}


def get_adapter(platform: str):
    """Return the adapter for a platform, or None if not implemented."""
    return _REGISTRY.get(platform)


def list_adapters() -> list[str]:
    """List all platforms with implemented adapters."""
    return list(_REGISTRY.keys())

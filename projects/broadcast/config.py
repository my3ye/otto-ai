"""
Broadcast System configuration loader.
Reads from configs/platforms.json — credentials live there, never in source.
"""

import json
from pathlib import Path
from typing import Any

CONFIG_PATH = Path(__file__).parent / "configs" / "platforms.json"
HISTORY_PATH = Path(__file__).parent / "broadcast_history.jsonl"


def load_platform_config() -> dict[str, Any]:
    """Load the full platform config dict."""
    with open(CONFIG_PATH) as f:
        return json.load(f)["platforms"]


def get_platform_cfg(platform: str) -> dict:
    """Get config for a single platform."""
    return load_platform_config().get(platform, {})


def get_enabled_platforms() -> list[str]:
    """Return list of platform names that are enabled in config."""
    return [p for p, cfg in load_platform_config().items() if cfg.get("enabled")]


def get_all_platforms() -> dict[str, dict]:
    """Return all platforms with their enabled status and credential presence."""
    raw = load_platform_config()
    result = {}
    for name, cfg in raw.items():
        # Check if credentials are present (non-empty critical fields)
        has_creds = _has_credentials(name, cfg)
        result[name] = {
            "enabled": cfg.get("enabled", False),
            "has_credentials": has_creds,
        }
    return result


def _has_credentials(platform: str, cfg: dict) -> bool:
    """Heuristic check — are the critical credentials filled in?"""
    checks = {
        "telegram": ["bot_token"],
        "bluesky": ["handle", "app_password"],
        "discord": [],  # webhooks dict check below
        "mastodon": ["access_token"],
        "devto": ["api_key"],
        "nostr": ["private_key_hex"],
        "lemmy": ["username", "password"],
        "hashnode": ["token", "publication_id"],
        "threads": ["access_token", "user_id"],
    }
    fields = checks.get(platform, [])
    if platform == "discord":
        return any(v for v in cfg.get("webhooks", {}).values())
    return all(bool(cfg.get(f)) for f in fields)

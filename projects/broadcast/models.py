"""
Broadcast System data models.
Kept in a separate file to avoid circular imports between broadcast.py and adapters/.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BroadcastMessage:
    """A message to be broadcast across platforms."""
    content: str
    format: str = "short"           # short | article
    title: Optional[str] = None     # Used for article posts (Dev.to, Hashnode, etc.)
    tags: list = field(default_factory=list)
    media_urls: list = field(default_factory=list)
    platform_overrides: dict = field(default_factory=dict)  # Per-platform content overrides


@dataclass
class PlatformResult:
    """Result of posting to a single platform."""
    platform: str
    success: bool
    url: Optional[str] = None
    error: Optional[str] = None
    status_code: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass
class BroadcastRecord:
    """A complete broadcast event — stored in broadcast_history.jsonl."""
    id: str
    content: str
    format: str
    title: Optional[str]
    tags: list
    timestamp: str
    results: list          # list of PlatformResult as dicts
    platforms_attempted: int
    platforms_succeeded: int

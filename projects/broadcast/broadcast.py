"""
Broadcast System core engine.
Orchestrates posting to all configured platforms simultaneously.
"""

import asyncio
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone

from .config import load_platform_config, get_enabled_platforms, HISTORY_PATH
from .models import BroadcastMessage, PlatformResult, BroadcastRecord


class BroadcastEngine:
    """
    Central engine for multi-platform content distribution.

    Usage:
        engine = BroadcastEngine()
        msg = BroadcastMessage(content="Hello world", tags=["ai", "sovereign"])
        record = await engine.send(msg)
        print(record.platforms_succeeded, "/", record.platforms_attempted)
    """

    def __init__(self):
        self.history_path = HISTORY_PATH

    def _get_adapter(self, platform: str):
        """Lazy-load adapter for a platform. Returns None if not implemented."""
        from .adapters import get_adapter
        return get_adapter(platform)

    async def send(
        self,
        message: BroadcastMessage,
        platforms: list[str] | None = None,
    ) -> BroadcastRecord:
        """
        Send message to all specified (or all enabled) platforms concurrently.
        Returns a BroadcastRecord with per-platform results.
        """
        cfg = load_platform_config()
        targets = platforms if platforms is not None else get_enabled_platforms()

        tasks = []
        task_platforms = []

        for platform in targets:
            pcfg = cfg.get(platform, {})
            if not pcfg:
                continue
            # If no explicit list given, skip disabled platforms
            if platforms is None and not pcfg.get("enabled"):
                continue
            adapter = self._get_adapter(platform)
            if not adapter:
                # Record as skipped
                tasks.append(_skip(platform, "no adapter implemented"))
            else:
                tasks.append(adapter.post(message, pcfg))
            task_platforms.append(platform)

        raw = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[PlatformResult] = []
        for i, result in enumerate(raw):
            if isinstance(result, Exception):
                results.append(PlatformResult(
                    platform=task_platforms[i],
                    success=False,
                    error=str(result),
                ))
            else:
                results.append(result)

        record = BroadcastRecord(
            id=str(uuid.uuid4()),
            content=message.content,
            format=message.format,
            title=message.title,
            tags=message.tags,
            timestamp=datetime.now(timezone.utc).isoformat(),
            results=[asdict(r) for r in results],
            platforms_attempted=len(results),
            platforms_succeeded=sum(1 for r in results if r.success),
        )

        self._append_history(record)
        return record

    def _append_history(self, record: BroadcastRecord) -> None:
        """Append record to JSONL history file."""
        with open(self.history_path, "a") as f:
            f.write(json.dumps(asdict(record)) + "\n")

    def get_history(self, limit: int = 50) -> list[dict]:
        """Return recent broadcast records (newest first)."""
        if not self.history_path.exists():
            return []
        text = self.history_path.read_text().strip()
        if not text:
            return []
        lines = [l for l in text.split("\n") if l.strip()]
        records = [json.loads(l) for l in lines]
        return list(reversed(records[-limit:]))


async def _skip(platform: str, reason: str) -> PlatformResult:
    return PlatformResult(platform=platform, success=False, error=f"skipped: {reason}")

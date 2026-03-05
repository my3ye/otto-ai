#!/usr/bin/env python3
"""
MY3YE Broadcast CLI

Usage:
    python3 cli.py "Your message here"
    python3 cli.py "Article title" --content path/to/content.md --format article --tags ai sovereign
    python3 cli.py --status
    python3 cli.py --platforms
    python3 cli.py "Test" --to telegram bluesky
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Ensure the broadcast package is importable when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from broadcast.broadcast import BroadcastEngine
from broadcast.models import BroadcastMessage
from broadcast.config import get_all_platforms


def print_record(record) -> None:
    from dataclasses import asdict
    data = asdict(record) if hasattr(record, "__dataclass_fields__") else record
    print(f"\nBroadcast ID: {data['id']}")
    print(f"Timestamp:    {data['timestamp']}")
    print(f"Result:       {data['platforms_succeeded']}/{data['platforms_attempted']} platforms OK\n")
    for r in data["results"]:
        icon = "OK" if r["success"] else "FAIL"
        line = f"  [{icon}] {r['platform']:15}"
        if r.get("url"):
            line += f" {r['url']}"
        if r.get("error"):
            line += f" ERROR: {r['error']}"
        if r.get("status_code"):
            line += f" (HTTP {r['status_code']})"
        print(line)


async def run(args) -> None:
    engine = BroadcastEngine()

    if args.status:
        history = engine.get_history(limit=10)
        if not history:
            print("No broadcast history found.")
            return
        for record in history:
            print(f"[{record['timestamp'][:19]}] {record['platforms_succeeded']}/{record['platforms_attempted']} OK | {record['content'][:60]}...")
        return

    if args.platforms:
        platforms = get_all_platforms()
        print("\nPlatform Status:")
        print(f"  {'Platform':15} {'Enabled':8} {'Credentials'}")
        print("  " + "-" * 40)
        for name, info in platforms.items():
            enabled = "YES" if info["enabled"] else "no"
            creds = "set" if info["has_credentials"] else "MISSING"
            print(f"  {name:15} {enabled:8} {creds}")
        return

    if not args.message:
        print("Error: provide a message or use --status / --platforms")
        sys.exit(1)

    # Build message
    content = args.message
    if args.content:
        p = Path(args.content)
        if p.exists():
            content = p.read_text()
        else:
            print(f"Error: file not found: {args.content}")
            sys.exit(1)

    msg = BroadcastMessage(
        content=content,
        format=args.format,
        title=args.title or (args.message if args.format == "article" else None),
        tags=args.tags or [],
    )

    targets = args.to or None
    print(f"Broadcasting to: {targets or 'all enabled'}")

    record = await engine.send(msg, platforms=targets)
    print_record(record)


def main():
    parser = argparse.ArgumentParser(description="MY3YE Broadcast System CLI")
    parser.add_argument("message", nargs="?", help="Short message or article title to post")
    parser.add_argument("--content", "-c", help="Path to markdown file for article body")
    parser.add_argument("--title", "-T", help="Article title (for Dev.to / Hashnode)")
    parser.add_argument("--format", "-f", choices=["short", "article"], default="short",
                        help="Post format: short (default) or article")
    parser.add_argument("--tags", "-t", nargs="+", help="Tags for the post")
    parser.add_argument("--to", nargs="+", metavar="PLATFORM",
                        help="Target platforms (default: all enabled)")
    parser.add_argument("--status", "-s", action="store_true",
                        help="Show recent broadcast history")
    parser.add_argument("--platforms", "-p", action="store_true",
                        help="List all platforms and their status")
    args = parser.parse_args()

    asyncio.run(run(args))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MY3YE Broadcast System — Main Orchestrator
Distributes content across all configured platforms simultaneously.

Usage:
    python3 broadcaster.py --message "Short post text" --platforms telegram bluesky discord
    python3 broadcaster.py --file content.md --platforms all --type article
    python3 broadcaster.py --list-platforms
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "configs" / "platforms.json"


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)["platforms"]


async def post_telegram(cfg: dict, message: str) -> dict:
    import httpx
    token = cfg["bot_token"]
    channel = cfg["channel"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    r = httpx.post(url, json={"chat_id": channel, "text": message, "parse_mode": cfg.get("parse_mode", "HTML")})
    return {"platform": "telegram", "status": r.status_code, "ok": r.status_code == 200}


async def post_bluesky(cfg: dict, message: str) -> dict:
    import httpx
    from datetime import datetime, timezone
    pds = cfg["pds_url"]
    # Get session
    sess = httpx.post(f"{pds}/xrpc/com.atproto.server.createSession",
        json={"identifier": cfg["handle"], "password": cfg["app_password"]}).json()
    if "accessJwt" not in sess:
        return {"platform": "bluesky", "status": 401, "ok": False, "error": sess.get("message")}
    r = httpx.post(f"{pds}/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {sess['accessJwt']}"},
        json={
            "repo": sess["did"],
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": message[:300],
                "createdAt": datetime.now(timezone.utc).isoformat()
            }
        })
    return {"platform": "bluesky", "status": r.status_code, "ok": r.status_code == 200}


async def post_discord(cfg: dict, message: str) -> dict:
    import httpx
    results = []
    for name, url in cfg["webhooks"].items():
        if not url:
            continue
        r = httpx.post(url, json={"content": message})
        results.append({"webhook": name, "status": r.status_code})
    return {"platform": "discord", "results": results, "ok": all(r["status"] in (200, 204) for r in results)}


async def post_mastodon(cfg: dict, message: str) -> dict:
    import httpx
    instance = cfg["instance"].rstrip("/")
    r = httpx.post(f"{instance}/api/v1/statuses",
        headers={"Authorization": f"Bearer {cfg['access_token']}"},
        data={"status": message[:500], "visibility": cfg.get("visibility", "public")})
    return {"platform": "mastodon", "status": r.status_code, "ok": r.status_code == 200}


async def post_devto(cfg: dict, title: str, content: str, tags: list = None) -> dict:
    import httpx
    r = httpx.post("https://dev.to/api/articles",
        headers={"api-key": cfg["api_key"]},
        json={"article": {
            "title": title,
            "body_markdown": content,
            "tags": tags or ["opensource", "ai", "decentralized", "future"],
            "published": True
        }})
    return {"platform": "devto", "status": r.status_code, "ok": r.status_code == 201}


PLATFORM_HANDLERS = {
    "telegram": post_telegram,
    "bluesky": post_bluesky,
    "discord": post_discord,
    "mastodon": post_mastodon,
    "devto": post_devto,
}


async def broadcast(message: str, platforms: list = None):
    config = load_config()
    targets = platforms or [p for p, cfg in config.items() if cfg.get("enabled")]

    print(f"Broadcasting to: {targets}")
    tasks = []
    for platform in targets:
        cfg = config.get(platform)
        if not cfg:
            print(f"  [SKIP] {platform}: unknown platform")
            continue
        if not cfg.get("enabled") and platforms is None:
            print(f"  [SKIP] {platform}: disabled in config")
            continue
        handler = PLATFORM_HANDLERS.get(platform)
        if not handler:
            print(f"  [SKIP] {platform}: no handler implemented yet")
            continue
        tasks.append(handler(cfg, message))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception):
            print(f"  [ERROR] {result}")
        else:
            status = "OK" if result.get("ok") else "FAIL"
            print(f"  [{status}] {result['platform']}: {result.get('status', '')}")

    return results


def main():
    parser = argparse.ArgumentParser(description="MY3YE Broadcast System")
    parser.add_argument("--message", "-m", help="Short message to post")
    parser.add_argument("--file", "-f", help="Markdown file to publish as article")
    parser.add_argument("--platforms", "-p", nargs="+", help="Platforms to post to (default: all enabled)")
    parser.add_argument("--list-platforms", action="store_true", help="List all platforms and their status")
    args = parser.parse_args()

    if args.list_platforms:
        config = load_config()
        print("\nPlatform Status:")
        for name, cfg in config.items():
            status = "ENABLED" if cfg.get("enabled") else "disabled"
            print(f"  {name:15} {status}")
        return

    if not args.message and not args.file:
        parser.print_help()
        sys.exit(1)

    content = args.message
    if args.file:
        content = Path(args.file).read_text()

    asyncio.run(broadcast(content, args.platforms))


if __name__ == "__main__":
    main()

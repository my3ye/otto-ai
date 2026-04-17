# MY3YE Broadcast System

Programmatic content distribution across all free platforms — taking the full civilization stack vision to the public.

## Quick Reference

| Platform | Method | Status |
|----------|--------|--------|
| Telegram | Bot API | Ready (needs token) |
| Bluesky | AT Protocol REST | Ready (needs app password) |
| Discord | Webhooks | Ready (needs webhook URL) |
| Mastodon | REST API | Ready (needs access token) |
| Dev.to | REST API | Ready (needs API key) |
| Nostr | Relay WebSocket | Ready (generate keypair) |
| Lemmy | REST API | Ready (needs account) |

See `PLATFORM_RESEARCH.md` for full analysis of 20 platforms.

## Directory Structure

- `scripts/` — Per-platform posting scripts + main broadcaster
- `templates/` — Content templates (short, long, thread)
- `configs/` — Credentials (gitignored)

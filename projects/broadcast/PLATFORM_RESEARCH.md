# Broadcast System — Platform Research
**Date:** 2026-03-05
**Purpose:** Map every free programmatic posting channel for the MY3YE civilization stack Broadcast System.
**Scope:** Mev handles X/Twitter manually. This covers everything else.

---

## Summary Table (Ranked by Reach × Automation Score)

| # | Platform | Reach (1-5) | Automation (1-5) | Composite | Cost | Verdict |
|---|----------|-------------|------------------|-----------|------|---------|
| 1 | **Telegram** | 5 | 5 | **10** | Free | LAUNCH FIRST |
| 2 | **Bluesky** | 4 | 5 | **9** | Free | LAUNCH FIRST |
| 3 | **Discord** | 4 | 5 | **9** | Free | LAUNCH FIRST |
| 4 | **Mastodon/Fediverse** | 3 | 5 | **8** | Free | HIGH PRIORITY |
| 5 | **Dev.to** | 3 | 5 | **8** | Free | HIGH PRIORITY |
| 6 | **Nostr** | 2 | 5 | **7** | Free | HIGH PRIORITY |
| 7 | **Reddit** | 5 | 3 | **8** | Free | HIGH PRIORITY |
| 8 | **Threads (Meta)** | 4 | 3 | **7** | Free | MEDIUM (requires approval) |
| 9 | **Hashnode** | 2 | 4 | **6** | Free | MEDIUM |
| 10 | **Ghost (self-hosted)** | 2 | 4 | **6** | Free | MEDIUM |
| 11 | **LinkedIn** | 5 | 2 | **7** | Free | MEDIUM (restrictive) |
| 12 | **Lemmy** | 2 | 4 | **6** | Free | MEDIUM |
| 13 | **WordPress.com** | 3 | 3 | **6** | Free | MEDIUM |
| 14 | **Tumblr** | 2 | 3 | **5** | Free | LOW |
| 15 | **Pinterest** | 3 | 3 | **6** | Free | LOW (image-heavy) |
| 16 | **Hacker News** | 3 | 2 | **5** | Free | LOW (scraping only) |
| 17 | **Matrix** | 2 | 3 | **5** | Free | LOW (small reach) |
| 18 | **Medium** | 3 | 1 | **4** | Free | SKIP (no post API) |
| 19 | **YouTube Community** | 5 | 1 | **6** | Free | SKIP (no API) |
| 20 | **Substack** | 2 | 1 | **3** | Free | SKIP (no API) |

---

## Phase 1 Targets (Launch Now — Minimal Friction)

These platforms have clean APIs, no approval process, and significant reach.

### 1. Telegram Channel (Bot API)
**Score: 10/10 — Launch First**

- **API:** `https://api.telegram.org/bot{TOKEN}/sendMessage`
- **Auth:** Create a bot via @BotFather → get HTTP API token (free, instant)
- **Posting:** POST `sendMessage` with `chat_id` (channel username) + `text`
- **Formats:** Plain text, HTML, Markdown (MarkdownV2), media (photo, video, document)
- **Rate limits:** 30 messages/second global; 1 message/second per chat (channels = ~20/min)
- **Account req:** Telegram account → create channel → create bot → add bot as channel admin
- **Reach:** Massive global reach — 900M+ monthly active users. Tech/crypto communities very active.
- **Ease:** Trivial. Single HTTP POST. No OAuth flow.
- **Implementation:**
  ```python
  import httpx
  bot_token = "YOUR_BOT_TOKEN"
  channel = "@my3ye_official"
  url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
  httpx.post(url, json={"chat_id": channel, "text": message, "parse_mode": "HTML"})
  ```

---

### 2. Bluesky (AT Protocol)
**Score: 9/10 — Launch First**

- **API:** `https://bsky.social/xrpc/com.atproto.repo.createRecord`
- **Auth:** Username + app password (create at Settings > App Passwords). Session auth via `createSession`.
- **Posting:** POST to `com.atproto.repo.createRecord` with collection `app.bsky.feed.post`
- **Formats:** Plain text up to 300 chars; rich text with facets (links, mentions, hashtags); images
- **Rate limits:** 5,000 points/hour, 35,000/day. Creating a post = 3 points. ~1,666 posts/hour max.
- **Account req:** Free signup at bsky.app. App password created in settings.
- **Reach:** 35M+ users, growing fast. Tech/builder/creator communities very engaged.
- **Ease:** Very easy. REST API, no approval required.
- **Implementation:**
  ```python
  import httpx
  # Step 1: Get session
  session = httpx.post("https://bsky.social/xrpc/com.atproto.server.createSession",
      json={"identifier": "handle.bsky.social", "password": "app-password"}).json()

  # Step 2: Post
  httpx.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",
      headers={"Authorization": f"Bearer {session['accessJwt']}"},
      json={
          "repo": session["did"],
          "collection": "app.bsky.feed.post",
          "record": {"$type": "app.bsky.feed.post", "text": message, "createdAt": iso_timestamp}
      })
  ```

---

### 3. Discord (Webhooks)
**Score: 9/10 — Launch First**

- **API:** Webhook URL (unique per channel)
- **Auth:** No auth required — webhook URL is the secret. Create via Server Settings > Integrations.
- **Posting:** POST JSON to webhook URL with `content` field
- **Formats:** Text, embeds (rich cards with title/desc/color/image), files
- **Rate limits:** 30 requests/60 seconds per webhook. 5 requests/2 seconds burst.
- **Account req:** Discord account → create server → create webhook in a channel
- **Reach:** 150M+ monthly users. Extremely tech/creator/community focused.
- **Ease:** Absolute simplest method — single POST, no OAuth, no approval.
- **Implementation:**
  ```python
  import httpx
  webhook_url = "https://discord.com/api/webhooks/WEBHOOK_ID/WEBHOOK_TOKEN"
  httpx.post(webhook_url, json={
      "content": message,
      "embeds": [{"title": "MY3YE Update", "description": body, "color": 0x7B2FBE}]
  })
  ```

---

## Phase 2 Targets (High Priority — Some Setup Required)

### 4. Mastodon / ActivityPub Fediverse
**Score: 8/10**

- **API:** `https://{instance}/api/v1/statuses`
- **Auth:** Register app on instance → OAuth 2.0 access token (or generate directly via UI)
- **Posting:** POST with `status` (text), optional `media_ids`, `visibility` (public/unlisted/private)
- **Formats:** Plain text up to 500 chars (instance-configurable); HTML subset; media attachments
- **Rate limits:** 300 requests/5 minutes default (instance-specific). Conservative: 1 post/minute.
- **Account req:** Free account on any public instance (mastodon.social, fosstodon.org, etc.)
- **Reach:** 10M+ active users across fediverse. Technically-minded, engaged community.
- **Ease:** Clean REST API. Mastodon.py library makes it trivial.
- **Recommended instance:** mastodon.social (largest), or fossil.social, fosstodon.org
- **Implementation:**
  ```python
  from mastodon import Mastodon
  m = Mastodon(access_token='TOKEN', api_base_url='https://mastodon.social')
  m.status_post("MY3YE: Building the civilization stack. #decentralized #sovereign")
  ```
- **Bonus:** Posts federate to ALL ActivityPub instances (Pixelfed, Lemmy, Misskey, etc.)

---

### 5. Dev.to
**Score: 8/10**

- **API:** `https://dev.to/api/articles`
- **Auth:** API key from Settings > Extensions. Single key, no OAuth.
- **Posting:** POST JSON with `title`, `body_markdown`, `tags` (up to 4), `published: true/false`
- **Formats:** Markdown. Supports frontmatter. Images via URL.
- **Rate limits:** Not officially published. Community reports ~10-30 requests/minute.
- **Account req:** Free signup at dev.to
- **Reach:** 1M+ registered devs, 10M+ monthly page views. High SEO value.
- **Ease:** Simplest blog API. API key in header, REST POST.
- **Implementation:**
  ```python
  import httpx
  httpx.post("https://dev.to/api/articles",
      headers={"api-key": "YOUR_KEY"},
      json={"article": {
          "title": "MY3YE: The Civilization Stack",
          "body_markdown": content,
          "tags": ["opensource", "decentralized", "ai", "society"],
          "published": True
      }})
  ```

---

### 6. Nostr
**Score: 7/10**

- **Protocol:** WebSocket-based relay broadcasting. No central server.
- **Auth:** Generate secp256k1 keypair. Sign all events with private key.
- **Posting:** Create event `{kind: 1, content: "...", tags: [], created_at: unix_ts}` → sign → broadcast to relays
- **Formats:** Plain text. NIP-01 basic notes. Rich formatting via NIP-23 (long-form).
- **Rate limits:** Relay-specific. Most public relays accept ~1 event/second.
- **Account req:** None — generate a keypair locally. No registration.
- **Reach:** ~1M users, growing. Bitcoin/cypherpunk/sovereign tech community. Highly aligned with MY3YE mission.
- **Ease:** Moderate. Requires WebSocket library and cryptographic signing.
- **Python lib:** `pynostr` or `nostr-sdk`
- **Key relays:** wss://relay.damus.io, wss://relay.nostr.band, wss://nos.lol
- **Implementation:**
  ```python
  from pynostr.key import PrivateKey
  from pynostr.relay_manager import RelayManager
  pk = PrivateKey()  # or load from file
  event = pk.sign_event(Event(content=message, kind=1))
  # broadcast to multiple relays simultaneously
  ```
- **Strategic note:** Nostr audience is VERY aligned with MY3YE — decentralized, sovereign, anti-surveillance.

---

### 7. Reddit
**Score: 8/10 (reach) but requires navigation**

- **API:** `https://oauth.reddit.com/api/submit`
- **Auth:** OAuth 2.0. Register app at reddit.com/prefs/apps. Script-type app for bots.
- **Posting:** POST with `kind` (link/self), `sr` (subreddit), `title`, `text`/`url`
- **Formats:** Text (markdown), link posts. Images via Imgur/external URL.
- **Rate limits:** 60 requests/minute authenticated. 10 posts/subreddit/day (karma-dependent).
- **Account req:** Free Reddit account with age/karma requirements per subreddit.
- **Reach:** 1B+ monthly users. Best reach of any platform. Community-specific targeting.
- **Ease:** Medium. OAuth required. Subreddit rules vary wildly. New accounts face karma walls.
- **Best subreddits for MY3YE:** r/Futurology, r/Decentralized, r/Solarpunk, r/EffectiveAltruism, r/AIAssistants, r/singularity
- **Caution:** Reddit bans automation quickly. Need aged, karma'd accounts. Post manually first.
- **Implementation (PRAW):**
  ```python
  import praw
  r = praw.Reddit(client_id='ID', client_secret='SECRET', username='U', password='P', user_agent='MY3YE/1.0')
  r.subreddit('Futurology').submit('MY3YE: A Civilization Stack for Sovereign Humanity', selftext=content)
  ```

---

## Phase 3 Targets (Medium Priority)

### 8. Threads (Meta)
**Score: 7/10**

- **API:** Meta Graph API — `https://graph.threads.net/v1.0/`
- **Auth:** Meta Developer Account + app approval required. OAuth 2.0.
- **Posting:** Two-step: create media container → publish container
- **Formats:** Text (up to 500 chars), images, video
- **Rate limits:** 250 posts/day per user
- **Account req:** Meta Developer account, app review/approval needed
- **Reach:** 200M+ active users (Meta-backed, Instagram integration). Large audience.
- **Ease:** Medium. Meta's approval process adds friction. But API is clean once approved.
- **Note:** Requires business verification with Meta.

---

### 9. Hashnode
**Score: 6/10**

- **API:** GraphQL at `https://gql.hashnode.com/`
- **Auth:** Personal Access Token from Settings > Developer
- **Posting:** GraphQL mutation `publishPost` with title, content (markdown), tags
- **Formats:** Markdown, rich embeds
- **Rate limits:** Not published; generous for normal use
- **Account req:** Free signup at hashnode.com
- **Reach:** 500K+ devs. SEO-optimized. Good distribution through Hashnode feed.
- **Ease:** Good. GraphQL requires slightly more setup than REST.
- **Implementation:**
  ```python
  import httpx
  query = """mutation PublishPost($input: PublishPostInput!) {
    publishPost(input: $input) { post { url } }
  }"""
  httpx.post("https://gql.hashnode.com/",
      headers={"Authorization": "TOKEN"},
      json={"query": query, "variables": {"input": {
          "title": "Building the Civilization Stack",
          "contentMarkdown": content,
          "publicationId": "YOUR_PUB_ID"
      }}})
  ```

---

### 10. Ghost (Self-hosted)
**Score: 6/10**

- **API:** `http://your-ghost-instance/ghost/api/admin/posts/`
- **Auth:** Admin API key (created in Ghost Admin > Integrations)
- **Posting:** POST JSON with `title`, `html` or `mobiledoc`, `status: "published"`
- **Formats:** HTML, Markdown (via mobiledoc), rich embeds
- **Rate limits:** Self-hosted → no rate limits
- **Account req:** Self-host Ghost on otto-machine (Docker) — free
- **Reach:** Your own subscriber base + SEO. Ghost has newsletter built in.
- **Ease:** Easy. Clean REST API. Can self-host for zero cost.
- **Strategic value:** Own your distribution. Ghost blog = the official MY3YE content hub.
- **Implementation:** Can run Ghost in Docker on otto-machine alongside existing services.

---

### 11. LinkedIn
**Score: 7/10 (reach), 2/10 (ease)**

- **API:** `https://api.linkedin.com/v2/ugcPosts`
- **Auth:** OAuth 2.0. LinkedIn Partner Program or marketing API approval needed for company pages.
- **Posting:** POST with `author` (urn:li:person:ID), `specificContent.shareCommentary.text`
- **Formats:** Text up to 3,000 chars, images, articles
- **Rate limits:** ~100 requests/day free tier. Strict.
- **Account req:** LinkedIn account. App approval for company posting.
- **Reach:** 1B+ users. Best professional audience on earth.
- **Ease:** Very low. LinkedIn actively restricts automation. Approval process is bureaucratic.
- **Note:** Worth pursuing for the professional/investor audience, but not automated — use for SEO-value articles via official API only.

---

### 12. Lemmy (Fediverse Reddit)
**Score: 6/10**

- **API:** `https://{instance}/api/v3/post`
- **Auth:** Username/password login → JWT token
- **Posting:** POST with `community_id`, `name` (title), `body` (markdown), optional URL
- **Formats:** Markdown text, link posts
- **Rate limits:** Instance-specific, generally generous
- **Account req:** Free signup on any Lemmy instance (lemmy.world, lemmy.ml, beehaw.org)
- **Reach:** 2M+ users, growing. Federated with Mastodon via ActivityPub.
- **Ease:** Simple REST API, similar to Reddit but without karma walls.
- **Best communities:** !technology@lemmy.ml, !opensource@lemmy.ml, !decentralized@lemmy.ml

---

### 13. WordPress.com
**Score: 6/10**

- **API:** `https://public-api.wordpress.com/rest/v1.1/sites/{site}/posts/new`
- **Auth:** OAuth 2.0 or Application Password
- **Posting:** POST with `title`, `content` (HTML), `status: "publish"`
- **Formats:** HTML, Markdown via Jetpack
- **Rate limits:** Not published; generous for normal use
- **Account req:** Free WordPress.com account + free blog
- **Reach:** High SEO value. WordPress powers 43% of the web.
- **Ease:** Medium. OAuth setup required. Free subdomain (yoursite.wordpress.com).

---

## Phase 4 / Low Priority

### 14. Tumblr
**Score: 5/10**

- **API:** `https://api.tumblr.com/v2/blog/{blogname}/posts`
- **Auth:** OAuth 1.0a. Register app at tumblr.com/oauth/apps.
- **Formats:** text, photo, link, video, quote, audio
- **Rate limits:** 250 posts/day
- **Account req:** Free Tumblr account
- **Reach:** 135M monthly users. Niche culture communities. Declining overall but strong in specific niches.
- **Ease:** Medium. OAuth 1.0a is more complex than OAuth 2.0.

---

### 15. Pinterest
**Score: 6/10 (visual content only)**

- **API:** `https://api.pinterest.com/v5/pins`
- **Auth:** OAuth 2.0. App review required.
- **Posting:** POST with `board_id`, `media_source` (image URL), `title`, `description`
- **Formats:** Images required. Text description optional.
- **Rate limits:** Varies by tier; basic tier generous for low volume
- **Account req:** Pinterest business account. App review before going live.
- **Reach:** 450M+ users. Visual discovery engine. Excellent for infographics, diagrams, vision boards.
- **Ease:** Medium. Image-first means content must be visual.
- **Strategic note:** Create MY3YE civilization stack infographics → massive organic reach.

---

### 16. Hacker News
**Score: 5/10**

- **API:** No official post API. Read-only official API.
- **Posting:** HTTP form submission (unofficial, requires CSRF token extraction)
- **Rate limits:** Karma-gated. New accounts can't post to front page.
- **Account req:** Free HN account. Need 20+ karma to post links.
- **Reach:** 4M+ monthly. Highest quality tech/startup/founder audience. Even 1 front page post = massive impact.
- **Ease:** Low. No official API. Requires session-based form scraping.
- **Recommendation:** Build account organically by commenting. Post MY3YE inception articles manually when karma allows. The audience is PERFECT for the mission.

---

### 17. Matrix Protocol
**Score: 5/10**

- **API:** `https://matrix.org/_matrix/client/v3/rooms/{roomId}/send/m.room.message`
- **Auth:** Matrix account + access token (or bot registration)
- **Posting:** PUT/POST with `msgtype: m.text`, `body`
- **Rate limits:** Server-specific
- **Account req:** Free account on matrix.org or any homeserver
- **Reach:** 80M+ addressable Matrix accounts (government adoption growing). Small but quality.
- **Ease:** Medium. Bot SDK (matrix-bot-sdk) makes it manageable.
- **Channels:** #decentralized, #ai, #opensource rooms on matrix.org

---

## Platforms to Skip (Now)

| Platform | Reason |
|----------|---------|
| **Medium** | Official post API no longer available for programmatic publishing |
| **YouTube Community Posts** | Not in YouTube Data API v3. No official endpoint. |
| **Substack** | No official publishing API. Newsletter-pull only. |
| **Hacker News** | No official write API. Form-scraping fragile and karma-gated. |

---

## Recommended Launch Order

```
Week 1 — Zero-friction launch:
  1. Telegram channel + Bot API
  2. Bluesky account + API
  3. Discord server + webhooks
  4. Dev.to account + API key
  5. Mastodon account (mastodon.social) + access token

Week 2 — Fediverse expansion:
  6. Nostr keypair + relay broadcasting
  7. Lemmy accounts on 2-3 instances
  8. Hashnode account + API

Week 3 — Owned media:
  9. Ghost blog on otto-machine (Docker)
  10. Reddit account + PRAW (manual posting initially, karma-build)

Week 4+ — Higher friction:
  11. Threads (Meta approval process)
  12. LinkedIn (approval + article strategy)
  13. Pinterest (visual content batch)
```

---

## Content Strategy Notes

- **Short-form** (Telegram, Bluesky, Mastodon, Discord, Nostr): Mission fragments, daily insights, quotes from the manifesto
- **Long-form** (Dev.to, Hashnode, Ghost, Medium-import): Full civilization stack essays, technical breakdowns of each project
- **Community** (Reddit, Lemmy, Hacker News): Discussion-first — never spam, add value to existing threads
- **Visual** (Pinterest): Infographics of the 14-project stack, ecosystem diagrams

## API Keys Needed (from Mev)

None for Phase 1. All Phase 1 platforms are self-service with free account creation:
- [ ] Create Telegram bot via @BotFather → store token
- [ ] Create Bluesky account at bsky.app → generate app password
- [ ] Create Discord server → create webhook
- [ ] Create Dev.to account → generate API key
- [ ] Create Mastodon account → generate access token

---

## Directory Structure

```
~/otto/projects/broadcast/
├── PLATFORM_RESEARCH.md    ← This file
├── scripts/
│   ├── post_telegram.py    ← Telegram Bot API poster
│   ├── post_bluesky.py     ← AT Protocol poster
│   ├── post_discord.py     ← Discord webhook poster
│   ├── post_mastodon.py    ← Mastodon poster (Mastodon.py)
│   ├── post_devto.py       ← Dev.to article publisher
│   ├── post_nostr.py       ← Nostr relay broadcaster
│   └── broadcaster.py      ← Main orchestrator (multi-platform)
├── templates/
│   ├── short_post.md       ← Short-form template (280-500 chars)
│   ├── long_article.md     ← Long-form essay template
│   └── vision_thread.md    ← Thread template for Bluesky/Mastodon
└── configs/
    └── platforms.json      ← Platform credentials + toggles (gitignored)
```

---

*Research completed 2026-03-05. Ready to implement Phase 1 (5 platforms, zero external approval required).*

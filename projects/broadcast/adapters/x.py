"""X (Twitter) adapter — multi-account posting via twikit.

Uses twikit library for safer session management + anti-detection.
Supports both cookie-based auth (from browser) and login auth (username/password).
Cookies are persisted per-account to avoid re-auth on every post.
"""

import asyncio
import json
import logging
import random
from pathlib import Path

from twikit import Client

from ..models import BroadcastMessage, PlatformResult

log = logging.getLogger("otto.broadcast.x")

CHAR_LIMIT = 280
COOKIES_DIR = Path(__file__).parent.parent / "configs" / "x_cookies"
COOKIES_DIR.mkdir(exist_ok=True)

# Delay range (seconds) between posting to different accounts
# Staggering reduces pattern detection
MIN_DELAY = 10
MAX_DELAY = 30


def _cookie_path(handle: str) -> str:
    return str(COOKIES_DIR / f"{handle}.json")


async def _get_client(account: dict) -> Client:
    """Create a twikit Client for an account, loading saved cookies if available."""
    handle = account.get("handle", "unknown")
    client = Client(language="en-US")

    cookie_file = _cookie_path(handle)

    # Try loading persisted cookies first
    if Path(cookie_file).exists():
        try:
            client.load_cookies(cookie_file)
            log.info(f"Loaded saved cookies for @{handle}")
            return client
        except Exception as e:
            log.warning(f"Failed to load cookies for @{handle}: {e}")

    # Fall back to setting cookies from config (browser-extracted)
    auth_token = account.get("auth_token", "")
    ct0 = account.get("ct0", "")

    if auth_token and ct0:
        client.set_cookies({
            "auth_token": auth_token,
            "ct0": ct0,
        })
        # Save for future use
        try:
            client.save_cookies(cookie_file)
        except Exception:
            pass
        log.info(f"Set browser cookies for @{handle}")
        return client

    # Try username/password login as last resort
    username = account.get("username", "")
    password = account.get("password", "")
    email = account.get("email", "")

    if username and password:
        try:
            await client.login(
                auth_info_1=username,
                auth_info_2=email or None,
                password=password,
                cookies_file=cookie_file,
            )
            log.info(f"Logged in via credentials for @{handle}")
            return client
        except Exception as e:
            log.error(f"Login failed for @{handle}: {e}")
            raise

    raise ValueError(f"No auth method available for @{handle}")


class XAdapter:
    name = "x"

    async def post(self, message: BroadcastMessage, cfg: dict) -> PlatformResult:
        """Post to X. cfg contains 'accounts' list.

        Posts to ALL enabled accounts with staggered delays.
        """
        accounts = cfg.get("accounts", [])
        if not accounts:
            return PlatformResult(platform=self.name, success=False, error="No X accounts configured")

        text = message.platform_overrides.get("x", {}).get("content", message.content)
        text = text[:CHAR_LIMIT]

        enabled = [a for a in accounts if a.get("enabled", True)]
        if not enabled:
            return PlatformResult(platform=self.name, success=False, error="No enabled X accounts")

        results = []
        for i, account in enumerate(enabled):
            # Stagger posts between accounts
            if i > 0:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                log.info(f"Waiting {delay:.1f}s before next account...")
                await asyncio.sleep(delay)

            result = await self._post_single(text, account)
            results.append(result)

        succeeded = sum(1 for r in results if r["success"])
        failed = sum(1 for r in results if not r["success"])

        if succeeded == 0 and failed > 0:
            errors = "; ".join(f"{r['handle']}: {r['error']}" for r in results if r.get("error"))
            return PlatformResult(platform=self.name, success=False, error=errors)

        return PlatformResult(
            platform=self.name,
            success=succeeded > 0,
            extra={"accounts": results, "succeeded": succeeded, "failed": failed},
        )

    async def _post_single(self, text: str, account: dict) -> dict:
        """Post a tweet from a single account using twikit."""
        handle = account.get("handle", "unknown")

        try:
            client = await _get_client(account)
            tweet = await client.create_tweet(text=text)

            tweet_id = tweet.id if tweet else ""
            url = f"https://x.com/{handle}/status/{tweet_id}" if tweet_id else None

            # Save refreshed cookies after successful post
            try:
                client.save_cookies(_cookie_path(handle))
            except Exception:
                pass

            log.info(f"X post success: @{handle} -> {url or 'posted'}")
            return {"handle": handle, "success": True, "url": url, "tweet_id": str(tweet_id)}

        except Exception as e:
            error_msg = str(e)
            log.warning(f"X post failed: @{handle} -> {error_msg}")
            return {"handle": handle, "success": False, "error": error_msg}

    async def post_single_account(self, text: str, account: dict) -> PlatformResult:
        """Post to a specific single account. Used for targeted posting."""
        result = await self._post_single(text, account)
        return PlatformResult(
            platform=f"x:{result['handle']}",
            success=result["success"],
            url=result.get("url"),
            error=result.get("error"),
        )

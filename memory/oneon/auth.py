"""ONEON Auth — magic link and session token management.

Phase 1A: Magic link email flow via admin@otto.lk (Zoho).
Phase 1C: WebAuthn passkey registration/verification.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from ..db import get_pool
from ..config import settings

log = logging.getLogger("otto.oneon.auth")

# Magic link token expiry
MAGIC_LINK_TTL = timedelta(hours=1)
# Session token expiry
SESSION_TTL = timedelta(days=30)


def _hash_token(token: str) -> str:
    """SHA-256 hash a token for safe DB storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def send_magic_link(identity_id: str, email: str) -> dict:
    """Generate a magic link token and send it via email.

    Returns the token info (token itself is only returned for dev/testing —
    in production, only the email delivery matters).
    """
    pool = await get_pool()

    # Generate secure random token
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + MAGIC_LINK_TTL

    # Store hashed token
    await pool.execute("""
        INSERT INTO oneon_auth_tokens (identity_id, token_hash, token_type, expires_at)
        VALUES ($1, $2, 'magic_link', $3)
    """, UUID(identity_id), token_hash, expires_at)

    # Build magic link URL
    magic_url = f"{settings.oneon_magic_link_base_url}?token={raw_token}"

    # Send email via Otto's email service
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            await session.post(
                "http://localhost:8100/email/send",
                json={
                    "to": email,
                    "subject": "Sign in to ONEON",
                    "body": (
                        f"Click this link to sign in to ONEON:\n\n"
                        f"{magic_url}\n\n"
                        f"This link expires in 1 hour.\n\n"
                        f"If you didn't request this, ignore this email."
                    ),
                },
                timeout=aiohttp.ClientTimeout(total=10),
            )
        log.info(f"Magic link sent to email for identity {identity_id}")
    except Exception as e:
        log.warning(f"Email send failed (non-fatal): {e}")
        # Token is still valid — user can retry or use alternate delivery

    return {
        "identity_id": identity_id,
        "expires_at": expires_at.isoformat(),
        "magic_link": magic_url,  # Include for dev; strip in production
    }


async def verify_magic_link(token: str) -> Optional[dict]:
    """Verify a magic link token. Returns session info or None if invalid.

    Single-use: marks token as used on success.
    """
    pool = await get_pool()
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    # Find valid, unused, non-expired token
    row = await pool.fetchrow("""
        UPDATE oneon_auth_tokens
        SET used_at = $2
        WHERE token_hash = $1
          AND token_type = 'magic_link'
          AND used_at IS NULL
          AND expires_at > $2
        RETURNING identity_id
    """, token_hash, now)

    if not row:
        return None

    identity_id = row["identity_id"]

    # Mark email as verified
    await pool.execute("""
        UPDATE oneon_identities
        SET email_verified = TRUE, updated_at = NOW()
        WHERE id = $1
    """, identity_id)

    # Create a session token
    session_token = await create_session_token(str(identity_id))

    log.info(f"Magic link verified for identity {identity_id}")
    return {
        "identity_id": str(identity_id),
        "session_token": session_token["token"],
        "expires_at": session_token["expires_at"],
    }


async def create_session_token(identity_id: str) -> dict:
    """Create a session token for authenticated API access."""
    pool = await get_pool()

    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + SESSION_TTL

    await pool.execute("""
        INSERT INTO oneon_auth_tokens (identity_id, token_hash, token_type, expires_at)
        VALUES ($1, $2, 'session', $3)
    """, UUID(identity_id), token_hash, expires_at)

    return {
        "token": raw_token,
        "expires_at": expires_at.isoformat(),
    }


async def verify_session_token(token: str) -> Optional[str]:
    """Verify a session token. Returns identity_id or None."""
    pool = await get_pool()
    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    row = await pool.fetchrow("""
        SELECT identity_id FROM oneon_auth_tokens
        WHERE token_hash = $1
          AND token_type = 'session'
          AND used_at IS NULL
          AND expires_at > $2
    """, token_hash, now)

    return str(row["identity_id"]) if row else None


async def invalidate_session(token: str) -> bool:
    """Invalidate a session token (logout)."""
    pool = await get_pool()
    token_hash = _hash_token(token)

    result = await pool.execute("""
        UPDATE oneon_auth_tokens
        SET used_at = NOW()
        WHERE token_hash = $1 AND token_type = 'session' AND used_at IS NULL
    """, token_hash)

    return "UPDATE 1" in result

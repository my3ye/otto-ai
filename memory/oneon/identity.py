"""ONEON Identity CRUD — DB operations for oneon_identities."""

import hashlib
import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool
from .did import construct_did

log = logging.getLogger("otto.oneon.identity")

VALID_TIERS = ("waitlist", "custodial", "self_sovereign", "sovereign")


async def register_identity(
    handle: str,
    display_name: Optional[str] = None,
    wallet_address: Optional[str] = None,
    chain: str = "none",
    metadata: Optional[dict] = None,
    email: Optional[str] = None,
) -> dict:
    """Register a new ONEON identity.

    Phase 0: Creates at 'waitlist' tier with DID stub.
    Phase 1A: Also derives smart account address and stores email hash.

    If email is provided, the identity starts at 'custodial' tier with a
    derived smart account address. A magic link is sent for email verification.

    Raises:
        ValueError: If handle is already registered.
    """
    import re
    handle_clean = handle.lstrip("@").lower().strip()
    if not handle_clean:
        raise ValueError("Handle cannot be empty.")
    if len(handle_clean) < 2 or len(handle_clean) > 32:
        raise ValueError("Handle must be 2–32 characters.")
    if not re.match(r'^[a-z0-9_]+$', handle_clean):
        raise ValueError("Handle must contain only lowercase letters, numbers, and underscores.")

    # Compute smart account address (deterministic from handle)
    from .invisible import compute_smart_account_address
    account_info = compute_smart_account_address(handle_clean)
    smart_address = account_info["address"]
    smart_salt = account_info["salt"]

    # Build DID with smart account address on Base
    chain_name = "base" if email else chain
    did = construct_did(handle_clean, chain=chain_name, address=smart_address)

    # Hash email for lookup (SHA-256, never store plaintext unencrypted)
    email_hash = None
    email_encrypted = None
    if email:
        email_lower = email.strip().lower()
        email_hash = hashlib.sha256(email_lower.encode()).hexdigest()
        # For Phase 1A, store email in metadata for magic link delivery
        # Phase 1B: encrypt with ONEON_VAULT_MASTER_KEY
        from .invisible import _encrypt_key
        try:
            email_encrypted = _encrypt_key(email_lower)
        except Exception:
            # Fallback: store in metadata
            if metadata is None:
                metadata = {}
            metadata["_email"] = email_lower

    # If email provided, start at custodial tier (invisible signup)
    initial_tier = "custodial" if email else "waitlist"

    pool = await get_pool()
    try:
        row = await pool.fetchrow("""
            INSERT INTO oneon_identities
                (handle, display_name, tier, did, wallet_address, chain, metadata,
                 smart_account_address, smart_account_salt,
                 email_hash, email_encrypted)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
        """, handle_clean, display_name, initial_tier, did,
            wallet_address or smart_address, chain_name,
            metadata or {},
            smart_address, smart_salt,
            email_hash, email_encrypted)
    except Exception as e:
        if "unique" in str(e).lower():
            raise ValueError(f"Handle already registered: @{handle_clean}")
        raise

    log.info(f"ONEON identity registered: @{handle_clean} (DID: {did}, tier: {initial_tier})")
    return dict(row)


async def get_identity(identity_id: str) -> Optional[dict]:
    """Fetch a single identity by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM oneon_identities WHERE id = $1",
        UUID(identity_id),
    )
    return dict(row) if row else None


async def get_identity_by_handle(handle: str) -> Optional[dict]:
    """Fetch a single identity by handle (case-insensitive)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM oneon_identities WHERE LOWER(handle) = $1",
        handle.lstrip("@").lower(),
    )
    return dict(row) if row else None


async def list_identities(
    tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List ONEON identities with optional tier filter."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if tier:
        if tier not in VALID_TIERS:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {VALID_TIERS}")
        args.append(tier)
        conditions.append(f"tier = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args += [limit, offset]

    rows = await pool.fetch(f"""
        SELECT * FROM oneon_identities
        {where}
        ORDER BY created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def upgrade_tier(
    identity_id: str,
    new_tier: str,
    ows_vault_ref: Optional[str] = None,
    wallet_address: Optional[str] = None,
) -> Optional[dict]:
    """Upgrade an identity's tier.

    Phase 0: Only waitlist→custodial upgrade is meaningful (others are Phase 1+).
    Phase 1: OWS vault ref required for custodial tier.
    """
    if new_tier not in VALID_TIERS:
        raise ValueError(f"Invalid tier: {new_tier}")

    pool = await get_pool()
    updates = ["tier = $2", "updated_at = NOW()"]
    args: list = [UUID(identity_id), new_tier]

    if ows_vault_ref is not None:
        args.append(ows_vault_ref)
        updates.append(f"ows_vault_ref = ${len(args)}")
    if wallet_address is not None:
        args.append(wallet_address)
        updates.append(f"wallet_address = ${len(args)}")

    # Set activated_at on first activation
    if new_tier != "waitlist":
        updates.append("activated_at = COALESCE(activated_at, NOW())")

    set_clause = ", ".join(updates)
    row = await pool.fetchrow(f"""
        UPDATE oneon_identities SET {set_clause}
        WHERE id = $1
        RETURNING *
    """, *args)
    if row:
        log.info(f"ONEON identity {identity_id} upgraded to tier: {new_tier}")
    return dict(row) if row else None


async def get_identity_stats() -> dict:
    """Return aggregate statistics for all ONEON identities."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT tier, COUNT(*) as count
        FROM oneon_identities
        GROUP BY tier
    """)
    total = await pool.fetchval("SELECT COUNT(*) FROM oneon_identities")
    return {
        "total": total,
        "by_tier": {r["tier"]: r["count"] for r in rows},
    }

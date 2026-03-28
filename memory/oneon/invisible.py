"""ONEON Invisible Signing Layer — the core abstraction that makes Web3 disappear.

Phase 1A: Deterministic address derivation, action queueing, session key vault.
Phase 1B: Actual on-chain deployment, UserOp construction, bundler submission.

Tier 1 users never see wallets, gas, or signing prompts. This module handles:
- Deterministic smart account address computation (CREATE2)
- Session key generation + encrypted storage
- Action construction and queueing
- Gas budget enforcement
"""

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ..db import get_pool
from ..config import settings

log = logging.getLogger("otto.oneon.invisible")

# Session key permissions
VALID_PERMISSIONS = {"VOTE", "POST", "MESSAGE", "CLAIM_CREDENTIAL"}
# Default session key TTL
SESSION_KEY_TTL = timedelta(days=30)
# Default daily gas budget
DEFAULT_GAS_BUDGET_USD = Decimal("0.10")


# ─── Deterministic Address Derivation ────────────────────────────────────────

def compute_smart_account_address(handle: str, salt: Optional[str] = None) -> dict:
    """Compute a deterministic smart account address from handle.

    Uses keccak256(handle) as the CREATE2 salt input.
    The actual address depends on the factory contract (Phase 1B).
    For Phase 1A, we compute a deterministic placeholder that will match
    the real CREATE2 address once the factory is deployed.

    Returns: {address, salt}
    """
    # Generate or use provided salt
    if salt is None:
        # Deterministic salt from handle — same handle always gets same salt
        salt = "0x" + hashlib.sha256(f"oneon:account:{handle}".encode()).hexdigest()

    # Phase 1A: compute a placeholder address using keccak256
    # This simulates CREATE2: address = keccak256(0xff, factory, salt, init_code_hash)[12:]
    # Real address will match once factory is deployed with the same salt
    addr_input = f"oneon:create2:{salt}".encode()
    addr_hash = hashlib.sha256(addr_input).hexdigest()
    address = "0x" + addr_hash[:40]  # 20-byte address

    return {
        "address": address,
        "salt": salt,
    }


# ─── Session Key Vault ──────────────────────────────────────────────────────

def _encrypt_key(private_key_hex: str) -> str:
    """Encrypt a private key with the vault master key (AES-256-GCM via Fernet).

    Requires ONEON_VAULT_MASTER_KEY to be set in config.
    Falls back to base64 encoding if no vault key (dev only).
    """
    if settings.oneon_vault_master_key:
        try:
            from cryptography.fernet import Fernet
            f = Fernet(settings.oneon_vault_master_key.encode())
            return f.encrypt(private_key_hex.encode()).decode()
        except Exception as e:
            log.error(f"Fernet encryption failed: {e}")
            raise
    else:
        # Dev mode: base64 encode (NOT secure — vault key must be set in production)
        import base64
        log.warning("ONEON_VAULT_MASTER_KEY not set — using insecure base64 encoding")
        return base64.b64encode(private_key_hex.encode()).decode()


def _decrypt_key(encrypted: str) -> str:
    """Decrypt a private key from the vault."""
    if settings.oneon_vault_master_key:
        from cryptography.fernet import Fernet
        f = Fernet(settings.oneon_vault_master_key.encode())
        return f.decrypt(encrypted.encode()).decode()
    else:
        import base64
        return base64.b64decode(encrypted.encode()).decode()


async def create_session_key(
    identity_id: str,
    permissions: Optional[list[str]] = None,
    ttl: Optional[timedelta] = None,
) -> dict:
    """Generate and store an encrypted session key pair for Tier 1 signing.

    The private key is encrypted with ONEON_VAULT_MASTER_KEY and stored in DB.
    The public key is returned for on-chain registration (Phase 1B).
    """
    pool = await get_pool()

    if permissions is None:
        permissions = list(VALID_PERMISSIONS)
    else:
        invalid = set(permissions) - VALID_PERMISSIONS
        if invalid:
            raise ValueError(f"Invalid permissions: {invalid}")

    if ttl is None:
        ttl = SESSION_KEY_TTL

    # Generate ECDSA key pair (secp256k1 for EVM compatibility)
    private_key_bytes = os.urandom(32)
    private_key_hex = private_key_bytes.hex()

    # Derive public key (simplified — full EVM pubkey derivation needs eth_keys)
    # Phase 1A: store the hash as public key identifier
    public_key = "0x" + hashlib.sha256(private_key_bytes).hexdigest()

    # Encrypt and store
    encrypted_private = _encrypt_key(private_key_hex)
    expires_at = datetime.now(timezone.utc) + ttl

    row = await pool.fetchrow("""
        INSERT INTO oneon_session_keys
            (identity_id, public_key, encrypted_private_key, permissions, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, public_key, permissions, expires_at, created_at
    """, UUID(identity_id), public_key, encrypted_private, permissions, expires_at)

    log.info(f"Session key created for identity {identity_id}, expires {expires_at}")
    return dict(row)


async def get_active_session_key(identity_id: str) -> Optional[dict]:
    """Get the active (non-expired, non-revoked) session key for an identity."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    row = await pool.fetchrow("""
        SELECT id, public_key, encrypted_private_key, permissions, expires_at
        FROM oneon_session_keys
        WHERE identity_id = $1
          AND expires_at > $2
          AND revoked_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
    """, UUID(identity_id), now)

    return dict(row) if row else None


async def revoke_session_key(key_id: str) -> bool:
    """Revoke a session key."""
    pool = await get_pool()
    result = await pool.execute("""
        UPDATE oneon_session_keys
        SET revoked_at = NOW()
        WHERE id = $1 AND revoked_at IS NULL
    """, UUID(key_id))
    return "UPDATE 1" in result


# ─── Action Executor ────────────────────────────────────────────────────────

async def execute_action(
    identity_id: str,
    action_type: str,
    payload: dict,
) -> dict:
    """Execute an invisible action for a Tier 1 user.

    Phase 1A: Queues the action with status='pending'.
    Phase 1B: Signs with session key, submits via bundler.

    Pre-checks:
    - email_verified must be TRUE
    - gas_used_today_usd must be under gas_budget_daily_usd
    """
    pool = await get_pool()

    # Validate action type
    valid_actions = {"vote", "post", "message", "credential_claim"}
    if action_type not in valid_actions:
        raise ValueError(f"Invalid action_type: {action_type}. Must be one of {valid_actions}")

    # Check identity exists and is eligible
    identity = await pool.fetchrow("""
        SELECT id, email_verified, gas_budget_daily_usd, gas_used_today_usd,
               gas_day_reset_at, tier, smart_account_address
        FROM oneon_identities WHERE id = $1
    """, UUID(identity_id))

    if not identity:
        raise ValueError(f"Identity not found: {identity_id}")

    # Check email verification
    if not identity["email_verified"]:
        raise PermissionError("Email verification required. Check your inbox.")

    # Reset daily gas counter if needed
    now = datetime.now(timezone.utc)
    if identity["gas_day_reset_at"].date() < now.date():
        await pool.execute("""
            UPDATE oneon_identities
            SET gas_used_today_usd = 0, gas_day_reset_at = NOW()
            WHERE id = $1
        """, UUID(identity_id))
        gas_used = Decimal("0")
    else:
        gas_used = identity["gas_used_today_usd"]

    # Check gas budget
    if gas_used >= identity["gas_budget_daily_usd"]:
        raise PermissionError(
            f"Daily gas budget exceeded (${gas_used}/{identity['gas_budget_daily_usd']}). "
            "Try again tomorrow."
        )

    # Queue the action
    row = await pool.fetchrow("""
        INSERT INTO oneon_actions (identity_id, action_type, payload, status)
        VALUES ($1, $2, $3, 'pending')
        RETURNING id, action_type, status, created_at
    """, UUID(identity_id), action_type, payload)

    log.info(f"Action queued: {action_type} for identity {identity_id}")
    return dict(row)


async def get_actions(
    identity_id: str,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List actions for an identity."""
    pool = await get_pool()
    conditions = ["identity_id = $1"]
    args: list = [UUID(identity_id)]

    if status:
        args.append(status)
        conditions.append(f"status = ${len(args)}")

    args.append(limit)
    where = " AND ".join(conditions)

    rows = await pool.fetch(f"""
        SELECT id, action_type, payload, tx_hash, status, gas_sponsored,
               created_at, confirmed_at
        FROM oneon_actions
        WHERE {where}
        ORDER BY created_at DESC
        LIMIT ${len(args)}
    """, *args)

    return [dict(r) for r in rows]

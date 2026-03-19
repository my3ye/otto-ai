"""
Secrets Vault — Fernet-encrypted credential storage with audit logging.

Usage:
    from .vault import get_secret, set_secret

    # Read (falls back to settings.* if not in vault)
    value = await get_secret("openai_api_key", service="llm", pool=pool)

    # Write
    await set_secret("openai_api_key", "sk-...", display_name="OpenAI API Key",
                     service_group="llm", allowed_services=["*"], pool=pool)

Master key lives in VAULT_MASTER_KEY env var (~/memory/.env).
If VAULT_MASTER_KEY is empty, vault is in passthrough mode (no encryption, no storage).
"""

import json
import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from .config import settings

logger = logging.getLogger(__name__)

# Module-level Fernet instance (lazy init)
_fernet: Optional[Fernet] = None


def _get_fernet() -> Optional[Fernet]:
    """Return Fernet instance, or None if master key not configured.

    VAULT_MASTER_KEY must be a valid Fernet key: URL-safe base64-encoded 32 bytes.
    Generate with: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    This is NOT a human-readable passphrase — it is a raw cryptographic key.
    """
    global _fernet
    if _fernet is not None:
        return _fernet
    key = settings.vault_master_key
    if not key:
        logger.warning("VAULT_MASTER_KEY not set — vault is in passthrough mode")
        return None
    try:
        _fernet = Fernet(key.encode())
        return _fernet
    except Exception as e:
        logger.error(f"Failed to init Fernet: {e}")
        return None


def encrypt_value(plaintext: str) -> str:
    """Encrypt a plaintext string. Returns base64-encoded ciphertext."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("VAULT_MASTER_KEY not configured — cannot encrypt")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    """Decrypt a ciphertext string back to plaintext."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("VAULT_MASTER_KEY not configured — cannot decrypt")
    try:
        return f.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        raise ValueError("Invalid or tampered ciphertext — decryption failed")


async def get_secret(
    key_name: str,
    service: str = "*",
    pool=None,
    agent_task_id: Optional[str] = None,
) -> Optional[str]:
    """
    Fetch decrypted secret from vault.

    Falls back to settings.* attribute if not found in vault (migration path).
    Logs an audit event on successful vault read.

    Args:
        key_name: Vault key name (e.g. "openai_api_key")
        service: Calling service identity (for scope check + audit log)
        pool: asyncpg pool (required for vault lookup; skipped if None)
        agent_task_id: Optional task_id from task_runner for audit trail

    Returns:
        Decrypted string value, or None if not found anywhere.
    """
    if pool is not None:
        try:
            row = await pool.fetchrow(
                """
                SELECT id, encrypted_value, allowed_services
                FROM secrets_vault
                WHERE key_name = $1 AND revoked_at IS NULL
                """,
                key_name,
            )
            if row:
                # Scope check
                allowed = row["allowed_services"]
                if isinstance(allowed, str):
                    allowed = json.loads(allowed)
                if "*" not in allowed and service not in allowed:
                    logger.warning(f"Secret '{key_name}' denied for service '{service}' (allowed: {allowed})")
                    return None

                # Decrypt
                plaintext = decrypt_value(row["encrypted_value"])

                # Audit log (fire and forget)
                try:
                    await pool.execute(
                        """
                        INSERT INTO secrets_audit_log (secret_id, key_name, action, service, agent_task_id)
                        VALUES ($1, $2, 'read', $3, $4)
                        """,
                        row["id"], key_name, service, agent_task_id,
                    )
                except Exception as audit_err:
                    logger.warning(f"Audit log failed for '{key_name}': {audit_err}")

                return plaintext
        except Exception as e:
            logger.warning(f"Vault lookup failed for '{key_name}': {e}")

    # Fallback: settings.* attribute (backwards compat during migration)
    settings_value = getattr(settings, key_name, None)
    if settings_value:
        logger.debug(f"Secret '{key_name}' served from settings fallback")
        return str(settings_value)

    return None


async def set_secret(
    key_name: str,
    value: str,
    display_name: str,
    service_group: str = "general",
    allowed_services: Optional[list] = None,
    description: Optional[str] = None,
    pool=None,
    service: str = "oms",
    agent_task_id: Optional[str] = None,
) -> str:
    """
    Encrypt and upsert a secret into the vault. Returns the secret UUID.

    Args:
        key_name: Slug identifier (e.g. "openai_api_key")
        value: Plaintext value to encrypt and store
        display_name: Human-readable label
        service_group: Category grouping (llm, crypto, email, webassist, general)
        allowed_services: List of service names that can read this. ["*"] = all.
        description: Optional notes
        pool: asyncpg pool
        service: Who is writing this (for audit)
        agent_task_id: Optional task_id for audit trail

    Returns:
        UUID of the created/updated secret.
    """
    if pool is None:
        raise RuntimeError("pool is required for set_secret")

    if allowed_services is None:
        allowed_services = ["*"]

    encrypted = encrypt_value(value)

    row = await pool.fetchrow(
        """
        INSERT INTO secrets_vault
            (key_name, display_name, description, service_group, allowed_services,
             encrypted_value, last_rotated_at, updated_at)
        VALUES ($1, $2, $3, $4, $5::jsonb, $6, NOW(), NOW())
        ON CONFLICT (key_name) DO UPDATE
            SET display_name       = EXCLUDED.display_name,
                description        = EXCLUDED.description,
                service_group      = EXCLUDED.service_group,
                allowed_services   = EXCLUDED.allowed_services,
                encrypted_value    = EXCLUDED.encrypted_value,
                last_rotated_at    = NOW(),
                updated_at         = NOW(),
                revoked_at         = NULL
        RETURNING id, (xmax = 0) AS is_new
        """,
        key_name,
        display_name,
        description,
        service_group,
        json.dumps(allowed_services),
        encrypted,
    )

    secret_id = row["id"]
    # Use xmax = 0 to reliably detect INSERT vs UPDATE (avoids audit log race conditions
    # and revoke→re-create cycles that previously caused mis-classification)
    action = "created" if row["is_new"] else "updated"

    try:
        await pool.execute(
            """
            INSERT INTO secrets_audit_log (secret_id, key_name, action, service, agent_task_id)
            VALUES ($1, $2, $3, $4, $5)
            """,
            secret_id, key_name, action, service, agent_task_id,
        )
    except Exception as audit_err:
        logger.warning(f"Audit log failed for set '{key_name}': {audit_err}")

    return str(secret_id)

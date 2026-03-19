"""
Secrets Vault API routes.

Endpoints:
  POST   /secrets                    Create or update a secret (Mev-only)
  GET    /secrets                    List all secrets (names/metadata, NO values)
  GET    /secrets/{id}               Get secret metadata (no value)
  DELETE /secrets/{id}               Revoke (soft delete)
  GET    /secrets/get/{key_name}     Decrypt + return value (scoped by X-Otto-Service)
  POST   /secrets/{id}/rotate        Update encrypted value, log rotation event
  GET    /secrets/audit              Recent access/rotation log

Authentication:
  - Write operations (POST, DELETE, rotate) require Authorization: Bearer <web_auth_token>
  - Read /secrets/get/{key_name} uses X-Otto-Service header for scope check
  - Listing metadata requires Authorization: Bearer <web_auth_token>
"""

import json
import logging
import re
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Header, Query, Request  # Header kept for x_otto_service
from pydantic import BaseModel, field_validator

from ..config import settings
from ..db import get_pool
from ..vault import get_secret, set_secret, encrypt_value

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/secrets", tags=["secrets"])


# ── Auth helper ───────────────────────────────────────────────────────────────

def _check_auth(request: Request):
    """Raise 401 if Authorization: Bearer token doesn't match web_auth_token.

    Deny-by-default: if web_auth_token is not configured, all requests are rejected
    (prevents accidental exposure in misconfigured deployments). Set
    ALLOW_UNAUTHENTICATED=true in .env to explicitly allow unauthenticated access
    in dev/test environments where no secrets are stored.
    """
    if not settings.web_auth_token:
        if getattr(settings, "allow_unauthenticated", False):
            logger.warning("Secrets API: unauthenticated access allowed (ALLOW_UNAUTHENTICATED=true)")
            return
        raise HTTPException(
            status_code=503,
            detail="Secrets vault: WEB_AUTH_TOKEN not configured. Set it in memory/.env to enable access.",
        )
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
    if token != settings.web_auth_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_bearer_token(request: Request) -> Optional[str]:
    """Extract bearer token from Authorization header, or None."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.removeprefix("Bearer ").strip()
    return None


# ── Pydantic models ───────────────────────────────────────────────────────────

_KEY_NAME_RE = re.compile(r"^[a-z0-9_]{1,128}$")


class SecretCreate(BaseModel):
    key_name: str
    display_name: str
    value: str
    service_group: str = "general"
    allowed_services: List[str] = ["*"]
    description: Optional[str] = None

    @field_validator("key_name")
    @classmethod
    def validate_key_name(cls, v: str) -> str:
        if not _KEY_NAME_RE.match(v):
            raise ValueError(
                "key_name must be lowercase alphanumeric and underscores only (e.g. 'openai_api_key')"
            )
        return v


class SecretRotate(BaseModel):
    value: str


class SecretResponse(BaseModel):
    id: str
    key_name: str
    display_name: str
    description: Optional[str]
    service_group: str
    allowed_services: List[str]
    encryption_version: int
    last_rotated_at: Optional[str]
    revoked_at: Optional[str]
    created_at: str
    updated_at: str


class AuditEntry(BaseModel):
    id: str
    secret_id: Optional[str]
    key_name: str
    action: str
    service: Optional[str]
    agent_task_id: Optional[str]
    created_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _row_to_response(row) -> dict:
    allowed = row["allowed_services"]
    if isinstance(allowed, str):
        allowed = json.loads(allowed)
    return {
        "id": str(row["id"]),
        "key_name": row["key_name"],
        "display_name": row["display_name"],
        "description": row["description"],
        "service_group": row["service_group"],
        "allowed_services": allowed,
        "encryption_version": row["encryption_version"],
        "last_rotated_at": row["last_rotated_at"].isoformat() if row["last_rotated_at"] else None,
        "revoked_at": row["revoked_at"].isoformat() if row["revoked_at"] else None,
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", summary="Create or update a secret")
async def create_secret(
    request: Request,
    body: SecretCreate,
):
    """Create or update a secret. Requires Mev auth."""
    _check_auth(request)
    pool = await get_pool()
    secret_id = await set_secret(
        key_name=body.key_name,
        value=body.value,
        display_name=body.display_name,
        service_group=body.service_group,
        allowed_services=body.allowed_services,
        description=body.description,
        pool=pool,
        service="oms",
    )
    return {"id": secret_id, "key_name": body.key_name, "status": "saved"}


@router.get("", summary="List all secrets (metadata only, no values)")
async def list_secrets(
    request: Request,
    service_group: Optional[str] = Query(None),
    include_revoked: bool = Query(False),
):
    """List vault secrets — metadata only, no decryption."""
    _check_auth(request)
    pool = await get_pool()

    conditions = []
    params = []
    if not include_revoked:
        conditions.append("revoked_at IS NULL")
    if service_group:
        params.append(service_group)
        conditions.append(f"service_group = ${len(params)}")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows = await pool.fetch(
        f"""
        SELECT id, key_name, display_name, description, service_group,
               allowed_services, encryption_version, last_rotated_at,
               revoked_at, created_at, updated_at
        FROM secrets_vault
        {where}
        ORDER BY service_group, key_name
        """,
        *params,
    )
    return {"count": len(rows), "secrets": [_row_to_response(r) for r in rows]}


@router.get("/audit", summary="Recent audit log")
async def get_audit_log(
    request: Request,
    limit: int = Query(50, le=200),
    key_name: Optional[str] = Query(None),
):
    """Get recent secret access/rotation events."""
    _check_auth(request)
    pool = await get_pool()

    if key_name:
        rows = await pool.fetch(
            """
            SELECT id, secret_id, key_name, action, service, agent_task_id, created_at
            FROM secrets_audit_log
            WHERE key_name = $1
            ORDER BY created_at DESC LIMIT $2
            """,
            key_name, limit,
        )
    else:
        rows = await pool.fetch(
            """
            SELECT id, secret_id, key_name, action, service, agent_task_id, created_at
            FROM secrets_audit_log
            ORDER BY created_at DESC LIMIT $1
            """,
            limit,
        )

    return {
        "count": len(rows),
        "entries": [
            {
                "id": str(r["id"]),
                "secret_id": str(r["secret_id"]) if r["secret_id"] else None,
                "key_name": r["key_name"],
                "action": r["action"],
                "service": r["service"],
                "agent_task_id": r["agent_task_id"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/get/{key_name}", summary="Decrypt and return secret value")
async def get_secret_value(
    request: Request,
    key_name: str,
    x_otto_service: Optional[str] = Header(None),
    agent_task_id: Optional[str] = Query(None),
):
    """
    Return decrypted secret value.

    For OMS/Mev use: pass Authorization: Bearer <token> for full access.
    For agent use: pass X-Otto-Service header; scope check is enforced.
    """
    # Either valid auth token OR a service header (for agent access)
    bearer = _get_bearer_token(request)
    is_admin = bool(bearer and settings.web_auth_token and bearer == settings.web_auth_token)

    # Reject if neither a valid bearer token nor a service identity header is present.
    # This prevents unauthenticated clients from reading ["*"]-scoped secrets.
    if not is_admin and not x_otto_service:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: provide Authorization: Bearer <token> or X-Otto-Service header",
        )

    # Admin bypass: full access regardless of service scope
    service = "*" if is_admin else x_otto_service

    pool = await get_pool()
    value = await get_secret(key_name, service=service, pool=pool, agent_task_id=agent_task_id)

    if value is None:
        raise HTTPException(status_code=404, detail=f"Secret '{key_name}' not found or access denied")

    return {"key_name": key_name, "value": value}


@router.get("/{secret_id}", summary="Get secret metadata by ID")
async def get_secret_meta(
    request: Request,
    secret_id: str,
):
    """Get secret metadata (no value)."""
    _check_auth(request)
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, key_name, display_name, description, service_group,
               allowed_services, encryption_version, last_rotated_at,
               revoked_at, created_at, updated_at
        FROM secrets_vault WHERE id = $1
        """,
        secret_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found")
    return _row_to_response(row)


@router.delete("/{secret_id}", summary="Revoke a secret (soft delete)")
async def revoke_secret(
    request: Request,
    secret_id: str,
):
    """Soft-delete a secret. Keeps audit history."""
    _check_auth(request)
    pool = await get_pool()
    row = await pool.fetchrow(
        "UPDATE secrets_vault SET revoked_at = NOW(), updated_at = NOW() "
        "WHERE id = $1 AND revoked_at IS NULL RETURNING id, key_name",
        secret_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found or already revoked")

    await pool.execute(
        "INSERT INTO secrets_audit_log (secret_id, key_name, action, service) VALUES ($1, $2, 'revoked', 'oms')",
        row["id"], row["key_name"],
    )
    return {"status": "revoked", "id": secret_id, "key_name": row["key_name"]}


@router.post("/{secret_id}/rotate", summary="Rotate (update) encrypted value")
async def rotate_secret(
    request: Request,
    secret_id: str,
    body: SecretRotate,
):
    """Update the encrypted value of an existing secret."""
    _check_auth(request)
    pool = await get_pool()

    encrypted = encrypt_value(body.value)
    row = await pool.fetchrow(
        """
        UPDATE secrets_vault
        SET encrypted_value = $1, last_rotated_at = NOW(), updated_at = NOW()
        WHERE id = $2 AND revoked_at IS NULL
        RETURNING id, key_name
        """,
        encrypted, secret_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Secret not found or revoked")

    await pool.execute(
        "INSERT INTO secrets_audit_log (secret_id, key_name, action, service) VALUES ($1, $2, 'rotated', 'oms')",
        row["id"], row["key_name"],
    )
    return {"status": "rotated", "id": secret_id, "key_name": row["key_name"]}

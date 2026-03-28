"""ONEON Credentials — W3C VCs surfaced as achievements.

Users see badges and achievements. Under the hood, these are W3C Verifiable
Credentials — portable, verifiable, standards-compliant.

Phase 1A: Off-chain VC storage + achievement UI.
Phase 1B: On-chain credential hash anchoring via ONEONCredentials.sol.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.oneon.credentials")

# ─── Built-in credential types with user-friendly badge metadata ────────────

CREDENTIAL_TYPES = {
    "first_identity": {
        "badge_name": "Pioneer",
        "badge_description": "Created an ONEON identity",
        "badge_image_url": None,  # TODO: badge artwork
    },
    "email_verified": {
        "badge_name": "Verified",
        "badge_description": "Verified email address",
        "badge_image_url": None,
    },
    "first_vote": {
        "badge_name": "Citizen",
        "badge_description": "Cast first governance vote",
        "badge_image_url": None,
    },
    "first_post": {
        "badge_name": "Voice",
        "badge_description": "Published first post on ONEON",
        "badge_image_url": None,
    },
    "community_builder": {
        "badge_name": "Community Builder",
        "badge_description": "Significant contribution to the ONEON community",
        "badge_image_url": None,
    },
    "mentor": {
        "badge_name": "Mentor",
        "badge_description": "Helped onboard new members to ONEON",
        "badge_image_url": None,
    },
    "tier_upgrade": {
        "badge_name": "Sovereign Path",
        "badge_description": "Advanced to a higher sovereignty tier",
        "badge_image_url": None,
    },
}


async def issue_credential(
    subject_id: str,
    credential_type: str,
    claims: Optional[dict] = None,
    issuer_id: Optional[str] = None,
    badge_name: Optional[str] = None,
    badge_description: Optional[str] = None,
) -> dict:
    """Issue a credential (achievement) to an identity.

    Uses built-in badge metadata for known types. Custom types require
    explicit badge_name.
    """
    pool = await get_pool()

    # Resolve badge metadata
    type_meta = CREDENTIAL_TYPES.get(credential_type, {})
    final_badge_name = badge_name or type_meta.get("badge_name") or credential_type.replace("_", " ").title()
    final_badge_desc = badge_description or type_meta.get("badge_description")
    badge_image = type_meta.get("badge_image_url")

    # Build W3C VC structure (simplified — no JWT signing in Phase 1A)
    vc_payload = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", f"ONEON{credential_type.title().replace('_', '')}"],
        "issuer": f"did:oneon:system" if not issuer_id else f"did:oneon:issuer:{issuer_id}",
        "issuanceDate": datetime.now(timezone.utc).isoformat(),
        "credentialSubject": {
            "id": f"did:oneon:subject:{subject_id}",
            "type": credential_type,
            **(claims or {}),
        },
    }

    # Compute credential hash for future on-chain anchoring
    vc_json = json.dumps(vc_payload, sort_keys=True)
    credential_hash = "0x" + hashlib.sha256(vc_json.encode()).hexdigest()

    row = await pool.fetchrow("""
        INSERT INTO oneon_credentials
            (subject_id, issuer_id, credential_type, claims, vc_jwt,
             credential_hash, badge_name, badge_description, badge_image_url)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING *
    """,
        UUID(subject_id),
        UUID(issuer_id) if issuer_id else None,
        credential_type,
        claims or {},
        vc_json,  # Store full VC as "JWT" (real signing in Phase 1B)
        credential_hash,
        final_badge_name,
        final_badge_desc,
        badge_image,
    )

    log.info(f"Credential issued: {credential_type} to {subject_id}")
    return dict(row)


async def list_achievements(identity_id: str) -> list[dict]:
    """List credentials as user-friendly achievements (Tier 1 view)."""
    pool = await get_pool()

    rows = await pool.fetch("""
        SELECT id, credential_type, badge_name, badge_description,
               badge_image_url, issued_at, revoked_at
        FROM oneon_credentials
        WHERE subject_id = $1 AND revoked_at IS NULL
        ORDER BY issued_at DESC
    """, UUID(identity_id))

    return [
        {
            "id": str(r["id"]),
            "name": r["badge_name"],
            "description": r["badge_description"],
            "image_url": r["badge_image_url"],
            "earned_at": r["issued_at"].isoformat() if r["issued_at"] else None,
            "verifiable": True,
        }
        for r in rows
    ]


async def list_raw_credentials(identity_id: str) -> list[dict]:
    """List full W3C VCs for Tier 2+ export."""
    pool = await get_pool()

    rows = await pool.fetch("""
        SELECT id, credential_type, vc_jwt, credential_hash,
               issued_at, revoked_at, anchored_at
        FROM oneon_credentials
        WHERE subject_id = $1 AND revoked_at IS NULL
        ORDER BY issued_at DESC
    """, UUID(identity_id))

    return [dict(r) for r in rows]


async def revoke_credential(credential_id: str, issuer_id: str) -> bool:
    """Revoke a credential. Only the issuer can revoke."""
    pool = await get_pool()

    result = await pool.execute("""
        UPDATE oneon_credentials
        SET revoked_at = NOW()
        WHERE id = $1 AND issuer_id = $2 AND revoked_at IS NULL
    """, UUID(credential_id), UUID(issuer_id))

    return "UPDATE 1" in result


async def get_credential(credential_id: str) -> Optional[dict]:
    """Get a single credential by ID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM oneon_credentials WHERE id = $1",
        UUID(credential_id),
    )
    return dict(row) if row else None

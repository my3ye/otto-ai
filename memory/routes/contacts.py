"""
OMS Contact Management routes — internal contacts for Mev + Otto relationship tracking.
"""

import subprocess
import shlex
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from ..db import get_pool

router = APIRouter(prefix="/oms/contacts", tags=["contacts"])


# ── Models ──────────────────────────────────────────────────────────────────

class ContactCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    mev_context: Optional[str] = None
    otto_context: Optional[str] = None
    tags: list[str] = []


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mev_context: Optional[str] = None
    otto_context: Optional[str] = None
    tags: Optional[list[str]] = None


class InteractionCreate(BaseModel):
    type: str  # e.g. "whatsapp", "email", "note", "meeting"
    content: str


class ContactMessageSend(BaseModel):
    content: str  # message to send


# ── Helpers ──────────────────────────────────────────────────────────────────

def _row_to_contact(row) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "mev_context": row["mev_context"],
        "otto_context": row["otto_context"],
        "tags": row["tags"] or [],
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


def _row_to_interaction(row) -> dict:
    return {
        "id": str(row["id"]),
        "contact_id": str(row["contact_id"]),
        "type": row["type"],
        "content": row["content"],
        "created_at": row["created_at"].isoformat(),
    }


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_contacts(
    q: Optional[str] = Query(None, description="Search by name/email/phone"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """List contacts with optional search and tag filter."""
    pool = await get_pool()

    conditions = []
    params = []
    idx = 1

    if q:
        conditions.append(
            f"(name ILIKE ${idx} OR email ILIKE ${idx} OR phone ILIKE ${idx})"
        )
        params.append(f"%{q}%")
        idx += 1

    if tag:
        conditions.append(f"${idx} = ANY(tags)")
        params.append(tag)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    rows = await pool.fetch(
        f"SELECT * FROM oms_contacts {where} ORDER BY name ASC LIMIT ${idx} OFFSET ${idx+1}",
        *params, limit, offset,
    )
    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM oms_contacts {where}", *params
    )

    return {
        "contacts": [_row_to_contact(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("", status_code=201)
async def create_contact(body: ContactCreate):
    """Create a new contact."""
    pool = await get_pool()

    row = await pool.fetchrow(
        """
        INSERT INTO oms_contacts (name, email, phone, mev_context, otto_context, tags)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        body.name, body.email, body.phone,
        body.mev_context, body.otto_context, body.tags,
    )
    return _row_to_contact(row)


@router.get("/{contact_id}")
async def get_contact(contact_id: str):
    """Get a single contact with recent interactions."""
    pool = await get_pool()

    row = await pool.fetchrow(
        "SELECT * FROM oms_contacts WHERE id = $1", contact_id
    )
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")

    interactions = await pool.fetch(
        "SELECT * FROM oms_contact_interactions WHERE contact_id = $1 ORDER BY created_at DESC LIMIT 50",
        contact_id,
    )

    contact = _row_to_contact(row)
    contact["interactions"] = [_row_to_interaction(i) for i in interactions]
    return contact


@router.put("/{contact_id}")
async def update_contact(contact_id: str, body: ContactUpdate):
    """Update contact fields."""
    pool = await get_pool()

    existing = await pool.fetchrow(
        "SELECT * FROM oms_contacts WHERE id = $1", contact_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")

    updates = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.email is not None:
        updates["email"] = body.email
    if body.phone is not None:
        updates["phone"] = body.phone
    if body.mev_context is not None:
        updates["mev_context"] = body.mev_context
    if body.otto_context is not None:
        updates["otto_context"] = body.otto_context
    if body.tags is not None:
        updates["tags"] = body.tags

    if not updates:
        return _row_to_contact(existing)

    updates["updated_at"] = "NOW()"
    set_parts = []
    params = []
    idx = 1
    for key, val in updates.items():
        if val == "NOW()":
            set_parts.append(f"{key} = NOW()")
        else:
            set_parts.append(f"{key} = ${idx}")
            params.append(val)
            idx += 1

    params.append(contact_id)
    row = await pool.fetchrow(
        f"UPDATE oms_contacts SET {', '.join(set_parts)} WHERE id = ${idx} RETURNING *",
        *params,
    )
    return _row_to_contact(row)


@router.delete("/{contact_id}", status_code=204)
async def delete_contact(contact_id: str):
    """Delete a contact (cascade deletes interactions)."""
    pool = await get_pool()

    result = await pool.execute(
        "DELETE FROM oms_contacts WHERE id = $1", contact_id
    )
    if result == "DELETE 0":
        raise HTTPException(status_code=404, detail="Contact not found")


@router.post("/{contact_id}/interactions", status_code=201)
async def add_interaction(contact_id: str, body: InteractionCreate):
    """Log an interaction with this contact."""
    pool = await get_pool()

    exists = await pool.fetchval(
        "SELECT 1 FROM oms_contacts WHERE id = $1", contact_id
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Contact not found")

    row = await pool.fetchrow(
        """
        INSERT INTO oms_contact_interactions (contact_id, type, content)
        VALUES ($1, $2, $3)
        RETURNING *
        """,
        contact_id, body.type, body.content,
    )

    # Update the contact's updated_at
    await pool.execute(
        "UPDATE oms_contacts SET updated_at = NOW() WHERE id = $1", contact_id
    )

    return _row_to_interaction(row)


@router.get("/{contact_id}/conversations")
async def get_conversations(
    contact_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get conversation history between Otto and a contact."""
    pool = await get_pool()

    exists = await pool.fetchval(
        "SELECT 1 FROM oms_contacts WHERE id = $1", contact_id
    )
    if not exists:
        raise HTTPException(status_code=404, detail="Contact not found")

    rows = await pool.fetch(
        """SELECT id, contact_id, direction, content, jid, created_at, metadata
           FROM contact_conversations
           WHERE contact_id = $1
           ORDER BY created_at ASC
           LIMIT $2 OFFSET $3""",
        contact_id, limit, offset,
    )
    total = await pool.fetchval(
        "SELECT COUNT(*) FROM contact_conversations WHERE contact_id = $1",
        contact_id,
    )

    return {
        "messages": [
            {
                "id": str(r["id"]),
                "contact_id": str(r["contact_id"]),
                "direction": r["direction"],
                "content": r["content"],
                "jid": r["jid"],
                "created_at": r["created_at"].isoformat(),
                "metadata": r["metadata"] or {},
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post("/{contact_id}/send", status_code=201)
async def send_message_to_contact(contact_id: str, body: ContactMessageSend):
    """Send a WhatsApp message to a contact (proactive outreach from Otto/Mev)."""
    pool = await get_pool()

    contact = await pool.fetchrow(
        "SELECT * FROM oms_contacts WHERE id = $1", contact_id
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    phone = contact["phone"]
    if not phone:
        raise HTTPException(status_code=400, detail="Contact has no phone number")

    # Normalize phone for WhatsApp JID
    jid = contact["whatsapp_jid"] or _phone_to_jid(phone)

    # Send via whatsapp_send.sh
    try:
        result = subprocess.run(
            ["/home/web3relic/otto/tools/whatsapp_send.sh", body.content, jid],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            raise HTTPException(
                status_code=502,
                detail=f"WhatsApp send failed: {result.stderr[:200]}"
            )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="WhatsApp send timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="WhatsApp send tool not found")

    # Log outgoing message
    msg_row = await pool.fetchrow(
        """INSERT INTO contact_conversations (contact_id, jid, direction, content, metadata)
           VALUES ($1, $2, 'outgoing', $3, '{"source": "manual"}')
           RETURNING *""",
        contact_id, jid, body.content,
    )
    await pool.execute(
        """INSERT INTO oms_contact_interactions (contact_id, type, content)
           VALUES ($1, 'whatsapp', $2)""",
        contact_id, f"[Otto → Contact] {body.content[:500]}"
    )
    await pool.execute(
        "UPDATE oms_contacts SET updated_at = NOW() WHERE id = $1", contact_id
    )

    return {
        "id": str(msg_row["id"]),
        "contact_id": contact_id,
        "direction": "outgoing",
        "content": body.content,
        "jid": jid,
        "created_at": msg_row["created_at"].isoformat(),
    }


def _phone_to_jid(phone: str) -> str:
    """Convert phone number to WhatsApp JID format."""
    # Strip non-digits and leading +
    digits = phone.replace("+", "").replace(" ", "").replace("-", "")
    return f"{digits}@s.whatsapp.net"

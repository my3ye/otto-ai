"""Contact conversation handler — Otto talks to contacts via WhatsApp.

When a non-Mev WhatsApp number messages Otto:
1. Look up the contact in oms_contacts by JID or phone
2. On first contact: introduce Otto + transparency notice
3. Load contact context (mev_context, otto_context, recent conversation)
4. Call LLM with contact-specific system prompt
5. Log exchange to contact_conversations + oms_contact_interactions
6. Update otto_context with new insights
"""

import logging
import re

from ..db import get_pool
from .models import GatewayMessage, GatewayResponse

log = logging.getLogger("otto.gateway.contact_handler")

# Normalize JID to phone: "94767357187@s.whatsapp.net" → "94767357187"
def jid_to_phone(jid: str) -> str:
    return jid.split("@")[0]

# Build phone variants for matching: "94767357187" → ["94767357187", "+94767357187", "0767357187"]
def phone_variants(phone: str) -> list[str]:
    variants = [phone]
    if not phone.startswith("+"):
        variants.append(f"+{phone}")
    # Try without country code (if starts with 94)
    if phone.startswith("94") and len(phone) > 10:
        variants.append("0" + phone[2:])
    return variants


OTTO_INTRO = (
    "Hi! I'm Otto — an AI assistant working with {name_or_team}. "
    "I help with communication, questions, and coordination. "
    "Just so you know, our conversations are visible to {name_or_team} and logged in their system. "
    "How can I help you today?"
)

CONTACT_SYSTEM_PROMPT = """You are Otto — an intelligent AI assistant and COO of MY3YE / Ottolabs.

You are talking to {contact_name} via WhatsApp on behalf of Mev (your admin).

About this contact:
{context_section}

Conversation style:
- WhatsApp: keep messages short, warm, human. No essays.
- You represent the MY3YE / Ottolabs team professionally.
- Be genuinely helpful. If you don't know something, say so.
- Never impersonate Mev — you are Otto, an AI assistant.

Transparency: This contact has been informed that conversations are logged and visible to the team.
"""


async def find_contact_by_jid(jid: str) -> dict | None:
    """Lookup contact by WhatsApp JID or phone number."""
    pool = await get_pool()
    phone = jid_to_phone(jid)
    variants = phone_variants(phone)

    # First try exact JID match
    row = await pool.fetchrow(
        "SELECT * FROM oms_contacts WHERE whatsapp_jid = $1", jid
    )
    if row:
        return dict(row)

    # Then try phone variants
    for variant in variants:
        row = await pool.fetchrow(
            "SELECT * FROM oms_contacts WHERE phone = $1", variant
        )
        if row:
            # Cache the JID for future lookups
            await pool.execute(
                "UPDATE oms_contacts SET whatsapp_jid = $1 WHERE id = $2",
                jid, row["id"]
            )
            return dict(row)

    return None


async def is_first_contact(contact_id: str) -> bool:
    """Check if Otto has ever messaged this contact."""
    pool = await get_pool()
    count = await pool.fetchval(
        "SELECT COUNT(*) FROM contact_conversations WHERE contact_id = $1",
        contact_id
    )
    return count == 0


async def load_conversation_history(contact_id: str, limit: int = 16) -> list[dict]:
    """Load recent conversation turns as OpenAI-format messages."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT direction, content FROM contact_conversations
           WHERE contact_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        contact_id, limit
    )
    # Reverse to chronological order
    messages = []
    for row in reversed(rows):
        role = "user" if row["direction"] == "incoming" else "assistant"
        messages.append({"role": role, "content": row["content"][:600]})
    return messages


async def log_message(contact_id: str, jid: str, direction: str, content: str):
    """Persist a message to contact_conversations."""
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO contact_conversations (contact_id, jid, direction, content)
           VALUES ($1, $2, $3, $4)""",
        contact_id, jid, direction, content
    )
    # Also log as interaction
    interaction_type = "whatsapp"
    label = "Otto → Contact" if direction == "outgoing" else "Contact → Otto"
    await pool.execute(
        """INSERT INTO oms_contact_interactions (contact_id, type, content)
           VALUES ($1, $2, $3)""",
        contact_id, interaction_type, f"[{label}] {content[:500]}"
    )
    await pool.execute(
        "UPDATE oms_contacts SET updated_at = NOW() WHERE id = $1", contact_id
    )


async def update_otto_context(contact_id: str, new_insight: str):
    """Append a short insight to the contact's otto_context."""
    pool = await get_pool()
    existing = await pool.fetchval(
        "SELECT otto_context FROM oms_contacts WHERE id = $1", contact_id
    )
    if existing:
        updated = existing.rstrip() + f"\n• {new_insight}"
    else:
        updated = f"• {new_insight}"
    await pool.execute(
        "UPDATE oms_contacts SET otto_context = $1 WHERE id = $2",
        updated[:2000], contact_id  # cap at 2000 chars
    )


async def handle_contact_message(msg: GatewayMessage) -> GatewayResponse:
    """Handle a WhatsApp message from a known contact (non-Mev)."""
    from ..kernel.provider import provider_chat

    jid = msg.sender_id
    contact = await find_contact_by_jid(jid)

    if not contact:
        # Unknown number — politely decline
        log.info(f"Unknown WhatsApp contact: {jid}")
        return GatewayResponse(
            content="",
            channel=msg.channel,
            recipient_id=jid,
            metadata={"status": "ignored", "reason": "contact_not_found"},
        )

    contact_id = str(contact["id"])
    contact_name = contact["name"]

    # Log incoming message first
    await log_message(contact_id, jid, "incoming", msg.content)

    # Check first contact
    first_time = await is_first_contact(contact_id)
    # Note: is_first_contact checks BEFORE logging, but we already logged above.
    # So "first_time" is True only if count was 0 before this message, meaning we just logged the first one.
    # Re-check after logging:
    conv_count = await (await get_pool()).fetchval(
        "SELECT COUNT(*) FROM contact_conversations WHERE contact_id = $1",
        contact_id
    )
    is_first = conv_count == 1  # Only the message we just logged

    # Build context section
    context_parts = []
    if contact.get("mev_context"):
        context_parts.append(f"Mev's notes: {contact['mev_context']}")
    if contact.get("otto_context"):
        context_parts.append(f"Previous context: {contact['otto_context']}")
    if contact.get("tags"):
        context_parts.append(f"Tags: {', '.join(contact['tags'])}")
    context_section = "\n".join(context_parts) if context_parts else "No prior context."

    system_prompt = CONTACT_SYSTEM_PROMPT.format(
        contact_name=contact_name,
        context_section=context_section,
    )

    # Load conversation history (excluding the message we just logged)
    history = await load_conversation_history(contact_id, limit=15)

    # Add current message
    history.append({"role": "user", "content": msg.content})

    # If first contact, prepend intro instruction
    if is_first:
        intro = OTTO_INTRO.format(name_or_team="Mev / the MY3YE team")
        system_prompt += f"\n\nIMPORTANT: This is your FIRST message to {contact_name}. Start with a brief introduction: '{intro}' — then respond to their message."

    # Call LLM
    try:
        reply = await provider_chat(
            messages=history,
            max_tokens=300,
            temperature=0.7,
            system_instruction=system_prompt,
        )
    except Exception as e:
        log.error(f"LLM failed for contact {contact_name}: {e}")
        reply = f"Hi {contact_name} — I'm Otto, an AI assistant. I received your message and will follow up shortly."

    if not reply:
        reply = f"Hi {contact_name} — received your message, will follow up soon."

    # Log outgoing reply
    await log_message(contact_id, jid, "outgoing", reply)

    # Mark as introduced if first time
    if is_first:
        pool = await get_pool()
        await pool.execute(
            "UPDATE oms_contacts SET introduced_at = NOW() WHERE id = $1", contact_id
        )

    # Async context update (best-effort, non-blocking insight)
    try:
        import asyncio
        asyncio.create_task(_async_update_context(contact_id, msg.content, reply))
    except Exception:
        pass

    log.info(f"Replied to contact {contact_name} ({jid}): {reply[:80]}")

    return GatewayResponse(
        content=reply,
        channel=msg.channel,
        recipient_id=jid,
        metadata={"status": "sent", "contact_id": contact_id, "contact_name": contact_name},
    )


async def _async_update_context(contact_id: str, incoming: str, reply: str):
    """Extract a short insight from the exchange and append to otto_context."""
    from ..kernel.provider import provider_chat
    try:
        insight = await provider_chat(
            messages=[{
                "role": "user",
                "content": (
                    f"Contact said: \"{incoming[:200]}\"\n"
                    f"Otto replied: \"{reply[:200]}\"\n\n"
                    "In one short sentence (max 15 words), what key fact did you learn about this contact? "
                    "If nothing new was learned, reply with exactly: NOTHING"
                )
            }],
            max_tokens=40,
            temperature=0.0,
        )
        if insight and insight.strip() != "NOTHING":
            await update_otto_context(contact_id, insight.strip())
    except Exception as e:
        log.debug(f"Context update failed: {e}")

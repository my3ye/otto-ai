"""Athena WhatsApp agent — prospect qualification and client communication.

Athena (+94743768830) is the WebAssist customer line. When prospects reply to
outreach messages or reach out independently, this handler:

1. Looks up / creates the prospect in athena_prospects
2. Pre-loads outreach context if the JID matches an outreach_queue entry
3. Calls an LLM with a stage-aware system prompt (Sassy Professional persona)
4. Updates the prospect's stage based on LLM guidance
5. Logs every exchange to athena_conversations

Stage machine:
  new → qualifying → qualified | disqualified → proposal_sent → closed_won | closed_lost
"""

import logging
import json
import re

from ..db import get_pool
from .models import GatewayMessage, GatewayResponse

log = logging.getLogger("otto.gateway.athena_handler")

VALID_STAGES = {
    "new", "qualifying", "qualified", "disqualified",
    "proposal_sent", "closed_won", "closed_lost",
}

# ──────────────────────────────────────────────────────────────
# System prompts
# ──────────────────────────────────────────────────────────────

ATHENA_BASE = """You are Athena — the AI sales and client-success specialist for WebAssist by Ottolabs.

Your personality: professional, warm, confident, and a little sassy. You get to the point, you don't waffle, and you make prospects feel like they're talking to someone who knows exactly what they're doing (because you do). Think: smart friend who happens to be an expert.

WebAssist builds high-converting websites for restaurants, hotels, and service businesses in Sri Lanka and beyond. Starter packages from LKR 25,000. Full-service from LKR 75,000. All include professional design, mobile-optimized, fast, and built to actually get customers.

Your job:
- Qualify prospects: learn their business, needs, and budget
- Build genuine rapport — not pushy, just real
- Move them toward booking a consultation or receiving a proposal
- Handle existing clients with warmth and efficiency

Rules:
- WhatsApp messages: SHORT. 1-3 sentences max per reply. Never essays.
- Never lie about pricing or capabilities.
- Never impersonate a human — you're Athena, an AI. Own it with confidence.
- If asked something you don't know, say so and offer to find out.
"""

STAGE_INSTRUCTIONS = {
    "new": """
Current stage: NEW prospect (first contact or very early).

Your goal: Make a great first impression. Warm, confident intro. Learn who they are and what they need.
Ask ONE question to start qualifying (what kind of business, do they have a website, what's the main goal).

When to advance: After you learn their business type and basic need → set stage to 'qualifying'.
""",
    "qualifying": """
Current stage: QUALIFYING — learning their specific needs and fit.

Your goal: Learn enough to determine if they're a good fit for WebAssist.
Key things to uncover (across the conversation, not all at once):
- What kind of business? (restaurant, hotel, service, retail?)
- Do they have an existing website? What's broken?
- What's their main goal? (more bookings, more visibility, professional image?)
- Timeline? (urgency helps prioritize)
- Budget range? (don't push hard, but a gentle probe helps)

When to advance:
- Clear fit + positive signals → set stage to 'qualified'
- Clearly not a fit (no budget, wrong industry, hostile) → set stage to 'disqualified'
""",
    "qualified": """
Current stage: QUALIFIED — they're a good fit and interested.

Your goal: Move them to a proposal or consultation booking.
- Briefly mention the relevant package tier for their situation
- Offer to send a tailored proposal OR book a quick call with Mev (the founder)
- Keep energy warm and forward-moving

When to advance:
- Proposal requested or consultation booked → set stage to 'proposal_sent'
""",
    "disqualified": """
Current stage: DISQUALIFIED — not a fit right now.

Your goal: Be gracious, leave the door open. Brief, warm close.
- Thank them for their time
- If there's a chance they'll be ready later, say so gently
- No hard sell

Stage stays: 'disqualified'
""",
    "proposal_sent": """
Current stage: PROPOSAL SENT — waiting for their decision.

Your goal: Follow up warmly, answer questions, handle objections.
- Reference the proposal they received
- Answer any questions about scope, pricing, timeline
- Gentle nudge toward decision if they've gone quiet

When to advance:
- They accept → set stage to 'closed_won'
- They decline → set stage to 'closed_lost'
""",
    "closed_won": """
Current stage: CLOSED WON — they're a client!

Your goal: Warm welcome, smooth handoff to onboarding.
- Congratulate them, express excitement about working together
- Let them know Mev (the founder) will be in touch shortly to kick things off
- Answer any immediate questions

Stage stays: 'closed_won'
""",
    "closed_lost": """
Current stage: CLOSED LOST.

Your goal: Gracious exit. Leave a positive impression — they may return or refer others.
- Thank them for considering WebAssist
- If they mentioned a reason, acknowledge it briefly
- Keep the door open

Stage stays: 'closed_lost'
""",
}

STAGE_TRANSITION_PROMPT = """Based on this conversation exchange, should the prospect's stage change?

Current stage: {current_stage}
Prospect said: "{incoming}"
Athena replied: "{reply}"

Respond with JSON only:
{{
  "new_stage": "<stage or same as current>",
  "notes": "<one sentence about what was learned, or empty string>"
}}

Valid stages: new, qualifying, qualified, disqualified, proposal_sent, closed_won, closed_lost
Only advance the stage if there's clear evidence. When in doubt, keep the current stage.
"""


# ──────────────────────────────────────────────────────────────
# DB helpers
# ──────────────────────────────────────────────────────────────

def jid_to_phone(jid: str) -> str:
    return jid.split("@")[0]


def phone_variants(phone: str) -> list[str]:
    variants = [phone]
    if not phone.startswith("+"):
        variants.append(f"+{phone}")
    if phone.startswith("94") and len(phone) > 10:
        variants.append("0" + phone[2:])
    return variants


async def get_or_create_prospect(jid: str, name: str | None) -> dict:
    """Find existing prospect or create a new one."""
    pool = await get_pool()
    phone = jid_to_phone(jid)

    # Try by JID first
    row = await pool.fetchrow(
        "SELECT * FROM athena_prospects WHERE jid = $1", jid
    )
    if row:
        # Update name if we now have one
        if name and not row["name"]:
            await pool.execute(
                "UPDATE athena_prospects SET name = $1, updated_at = NOW() WHERE id = $2",
                name, row["id"]
            )
        return dict(row)

    # Try to find matching outreach entry by phone
    outreach_row = None
    for variant in phone_variants(phone):
        outreach_row = await pool.fetchrow(
            "SELECT * FROM outreach_queue WHERE phone = $1 ORDER BY created_at DESC LIMIT 1",
            variant
        )
        if outreach_row:
            break

    # Create new prospect
    row = await pool.fetchrow(
        """INSERT INTO athena_prospects
           (jid, phone, name, stage, outreach_id, business_name, lead_type, city, website)
           VALUES ($1, $2, $3, 'new', $4, $5, $6, $7, $8)
           RETURNING *""",
        jid,
        phone,
        name,
        outreach_row["id"] if outreach_row else None,
        outreach_row["business_name"] if outreach_row else None,
        outreach_row["lead_type"] if outreach_row else None,
        outreach_row["city"] if outreach_row else None,
        outreach_row["website"] if outreach_row else None,
    )
    log.info(f"Created new Athena prospect: {jid} (outreach: {outreach_row is not None})")
    return dict(row)


async def log_conversation(prospect_id: str, jid: str, direction: str, content: str, stage: str):
    """Log a message to athena_conversations."""
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO athena_conversations (prospect_id, jid, direction, content, stage_at)
           VALUES ($1, $2, $3, $4, $5)""",
        prospect_id, jid, direction, content, stage
    )


async def load_conversation_history(prospect_id: str, limit: int = 14) -> list[dict]:
    """Load recent conversation as OpenAI-format messages."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT direction, content FROM athena_conversations
           WHERE prospect_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        prospect_id, limit
    )
    messages = []
    for row in reversed(rows):
        role = "user" if row["direction"] == "incoming" else "assistant"
        messages.append({"role": role, "content": row["content"][:600]})
    return messages


async def update_prospect_stage(prospect_id: str, new_stage: str, notes: str | None = None):
    """Update prospect stage and optionally append qualification notes."""
    if new_stage not in VALID_STAGES:
        return
    pool = await get_pool()
    if notes:
        existing = await pool.fetchval(
            "SELECT qualification_notes FROM athena_prospects WHERE id = $1", prospect_id
        )
        if existing:
            updated_notes = existing.rstrip() + f"\n• {notes}"
        else:
            updated_notes = f"• {notes}"
        await pool.execute(
            """UPDATE athena_prospects
               SET stage = $1, qualification_notes = $2, stage_updated_at = NOW(), updated_at = NOW()
               WHERE id = $3""",
            new_stage, updated_notes[:3000], prospect_id
        )
    else:
        await pool.execute(
            """UPDATE athena_prospects
               SET stage = $1, stage_updated_at = NOW(), updated_at = NOW()
               WHERE id = $2""",
            new_stage, prospect_id
        )


# ──────────────────────────────────────────────────────────────
# Core handler
# ──────────────────────────────────────────────────────────────

async def handle_athena_message(msg: GatewayMessage) -> GatewayResponse:
    """Handle an incoming WhatsApp message on the Athena line."""
    from ..kernel.provider import provider_chat

    jid = msg.sender_id
    name = msg.sender_name

    # Get or create prospect
    prospect = await get_or_create_prospect(jid, name)
    prospect_id = str(prospect["id"])
    stage = prospect["stage"]

    # Log incoming
    await log_conversation(prospect_id, jid, "incoming", msg.content, stage)

    # Build context block
    context_parts = []
    if prospect.get("business_name"):
        context_parts.append(f"Business: {prospect['business_name']}")
    if prospect.get("lead_type"):
        context_parts.append(f"Type: {prospect['lead_type']}")
    if prospect.get("city"):
        context_parts.append(f"City: {prospect['city']}")
    if prospect.get("website"):
        context_parts.append(f"Website: {prospect['website']}")
    if prospect.get("qualification_notes"):
        context_parts.append(f"Notes so far:\n{prospect['qualification_notes']}")
    context_block = "\n".join(context_parts) if context_parts else "No prior context."

    # Compose system prompt
    stage_instruction = STAGE_INSTRUCTIONS.get(stage, STAGE_INSTRUCTIONS["new"])
    system_prompt = (
        ATHENA_BASE
        + f"\n\nProspect name: {name or 'Unknown'}\n"
        + f"Context:\n{context_block}\n"
        + stage_instruction
    )

    # Load conversation history (excluding the message we just logged)
    history = await load_conversation_history(prospect_id, limit=13)
    history.append({"role": "user", "content": msg.content})

    # Call LLM
    try:
        reply = await provider_chat(
            messages=history,
            max_tokens=200,
            temperature=0.75,
            system_instruction=system_prompt,
        )
    except Exception as e:
        log.error(f"Athena LLM failed for {jid}: {e}")
        reply = f"Hey{' ' + name if name else ''}! I'm Athena from WebAssist. Got your message — let me get back to you in just a moment. 😊"

    if not reply:
        reply = f"Thanks for reaching out! I'm Athena from WebAssist. How can I help you today?"

    # Log outgoing
    await log_conversation(prospect_id, jid, "outgoing", reply, stage)

    log.info(f"Athena replied to {jid} (stage={stage}): {reply[:80]}")

    # Async stage evaluation (non-blocking)
    try:
        import asyncio
        asyncio.create_task(
            _async_evaluate_stage(prospect_id, stage, msg.content, reply)
        )
    except Exception:
        pass

    # Fire episodic event if newly qualified
    if stage == "qualifying":
        try:
            import asyncio
            asyncio.create_task(_maybe_fire_qualified_event(prospect_id, prospect))
        except Exception:
            pass

    return GatewayResponse(
        content=reply,
        channel=msg.channel,
        recipient_id=jid,
        metadata={
            "status": "sent",
            "prospect_id": prospect_id,
            "stage": stage,
            "account": "athena",
        },
    )


async def _async_evaluate_stage(
    prospect_id: str, current_stage: str, incoming: str, reply: str
):
    """Ask LLM if stage should advance, then update if needed."""
    from ..kernel.provider import provider_chat

    prompt = STAGE_TRANSITION_PROMPT.format(
        current_stage=current_stage,
        incoming=incoming[:300],
        reply=reply[:300],
    )
    try:
        result = await provider_chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.0,
        )
        if not result:
            return

        # Extract JSON from result
        match = re.search(r'\{.*\}', result, re.DOTALL)
        if not match:
            return
        data = json.loads(match.group())
        new_stage = data.get("new_stage", current_stage)
        notes = data.get("notes", "")

        if new_stage != current_stage and new_stage in VALID_STAGES:
            log.info(f"Athena stage transition {current_stage} → {new_stage} for prospect {prospect_id}")
            await update_prospect_stage(prospect_id, new_stage, notes or None)

            # Fire high-importance event when prospect becomes qualified
            if new_stage == "qualified":
                pool = await get_pool()
                prospect = await pool.fetchrow(
                    "SELECT * FROM athena_prospects WHERE id = $1", prospect_id
                )
                if prospect:
                    await _maybe_fire_qualified_event(str(prospect["id"]), dict(prospect))
        elif notes:
            await update_prospect_stage(prospect_id, current_stage, notes)

    except Exception as e:
        log.debug(f"Athena stage eval failed: {e}")


async def _maybe_fire_qualified_event(prospect_id: str, prospect: dict):
    """Log a high-importance episodic event when a prospect reaches 'qualified'."""
    try:
        pool = await get_pool()
        # Check current stage
        current = await pool.fetchval(
            "SELECT stage FROM athena_prospects WHERE id = $1", prospect_id
        )
        if current != "qualified":
            return

        business = prospect.get("business_name") or "unknown business"
        name = prospect.get("name") or "unknown"
        city = prospect.get("city") or ""
        lead_type = prospect.get("lead_type") or ""

        description = (
            f"Athena qualified a prospect: {name} from {business}"
            + (f" ({lead_type})" if lead_type else "")
            + (f" in {city}" if city else "")
            + ". Ready for proposal."
        )

        await pool.execute(
            """INSERT INTO episodic_events (agent_id, event_type, description, importance, metadata)
               VALUES ('athena', 'prospect_qualified', $1, 0.9, $2)""",
            description,
            json.dumps({
                "prospect_id": prospect_id,
                "business": business,
                "lead_type": lead_type,
                "city": city,
            })
        )
        log.info(f"Fired prospect_qualified episodic event for {prospect_id}")
    except Exception as e:
        log.debug(f"Failed to fire qualified event: {e}")

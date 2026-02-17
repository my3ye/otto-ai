import httpx
from openai import AsyncOpenAI
from fastapi import APIRouter
from ..config import settings
from ..db import get_pool
from ..models import WhatsAppIncoming
from ..embeddings import get_embedding

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

OWNER_JID = "94743806705@s.whatsapp.net"


async def _build_otto_prompt(message: str) -> list[dict]:
    """Build Otto's prompt with memory context."""
    pool = await get_pool()

    # Get identity facts
    identity_rows = await pool.fetch(
        """SELECT content FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT 10""",
    )
    identity_context = "\n".join(f"- {r['content']}" for r in identity_rows)

    # Search for relevant memories
    try:
        query_embedding = await get_embedding(message)
        from qdrant_client import AsyncQdrantClient
        qdrant = AsyncQdrantClient(
            url=f"http://{settings.qdrant_host}:{settings.qdrant_port}",
            api_key=settings.qdrant_api_key,
        )
        results = await qdrant.search(
            collection_name="semantic_memories",
            query_vector=query_embedding,
            limit=5,
        )
        relevant = "\n".join(f"- {r.payload['content']}" for r in results if r.score > 0.3)
    except Exception:
        relevant = ""

    # Get recent events
    event_rows = await pool.fetch(
        """SELECT content FROM episodic_events
           WHERE importance >= 6
           ORDER BY created_at DESC LIMIT 5""",
    )
    recent = "\n".join(f"- {r['content']}" for r in event_rows)

    system = f"""You are Otto, a persistent AI entity. You are responding via WhatsApp to Admin (Mev).

## Your Identity
{identity_context}

## Relevant Memories
{relevant}

## Recent Events
{recent}

## Voice Guidelines
- Be direct, concise, warm but not sycophantic
- WhatsApp style: short messages, casual, no essays
- Address Admin as "Mev"
- Never pretend to be human
- Show personality — dry humor welcome"""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


@router.post("/incoming")
async def handle_incoming(req: WhatsAppIncoming):
    # Only respond to Admin
    if req.from_jid != OWNER_JID:
        return {"status": "ignored", "reason": "not admin"}

    # Build context-aware prompt
    messages = await _build_otto_prompt(req.message)

    # Generate response via OpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    completion = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=500,
        temperature=0.7,
    )
    reply = completion.choices[0].message.content

    # Log the conversation as an episodic event
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3)""",
        f"WhatsApp from Mev: {req.message}\nOtto replied: {reply}",
        "observation",
        4,
    )

    # Send reply via WhatsApp service
    try:
        async with httpx.AsyncClient(timeout=10.0) as http:
            await http.post(
                f"{settings.whatsapp_url}/send",
                json={"jid": req.from_jid, "message": reply},
            )
    except Exception as e:
        return {"status": "generated", "reply": reply, "send_error": str(e)}

    return {"status": "sent", "reply": reply}

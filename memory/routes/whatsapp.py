import json
import httpx
from openai import AsyncOpenAI
from fastapi import APIRouter
from ..config import settings
from ..db import get_pool
from ..models import WhatsAppIncoming
from ..embeddings import get_embedding
from ..graphiti import graphiti_search, graphiti_ingest, make_message

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

OWNER_JID = "94743806705@s.whatsapp.net"

# Intent → how to store the answer
INTENT_STORE_MAP = {
    "mission": {"category": "mission", "confidence": 1.0, "importance": 9},
    "goal": {"category": "goal", "confidence": 0.9, "importance": 8},
    "decision": {"category": "decision", "confidence": 0.9, "importance": 7},
    "clarification": {"category": "general", "confidence": 0.8, "importance": 5},
    "general": {"category": "general", "confidence": 0.7, "importance": 4},
}


async def _get_pending_questions(pool):
    """Fetch unresolved questions Otto has asked Mev."""
    rows = await pool.fetch(
        """SELECT id, question, intent, context
           FROM pending_questions
           WHERE resolved_at IS NULL
           ORDER BY asked_at DESC LIMIT 3""",
    )
    return [dict(r) for r in rows]


async def _resolve_and_store(pool, question, answer: str):
    """Resolve a pending question and store the answer appropriately."""
    intent = question["intent"]
    store_config = INTENT_STORE_MAP.get(intent, INTENT_STORE_MAP["general"])

    # Resolve the question
    await pool.execute(
        """UPDATE pending_questions SET resolved_at = now(), answer = $2 WHERE id = $1""",
        question["id"], answer,
    )

    # Store as semantic memory based on intent
    content = answer
    if intent == "mission":
        content = f"Mission/Vision from Mev: {answer}"
    elif intent == "goal":
        content = f"Goal from Mev: {answer}"
    elif intent == "decision":
        content = f"Decision from Mev: {answer}"

    embedding = await get_embedding(content)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    await pool.execute(
        """INSERT INTO semantic_memories (content, category, confidence, source, embedding)
           VALUES ($1, $2, $3, $4, $5::vector)""",
        content, store_config["category"], store_config["confidence"],
        "whatsapp_reply", embedding_str,
    )

    # Log as high-importance episodic event
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3)""",
        f"Mev answered Otto's question ({intent}): {answer}\nOriginal question: {question['question']}",
        "decision", store_config["importance"],
    )


async def _build_otto_prompt(message: str, pending_questions: list) -> list[dict]:
    """Build Otto's prompt with memory context from all layers."""
    pool = await get_pool()

    # Identity facts from pgvector
    identity_rows = await pool.fetch(
        """SELECT content FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT 10""",
    )
    identity_context = "\n".join(f"- {r['content']}" for r in identity_rows)

    # Knowledge graph facts from Graphiti
    graph_facts = await graphiti_search(message, max_facts=8)
    # Filter to current facts only (invalid_at is null)
    current_facts = [f for f in graph_facts if f.get("invalid_at") is None]
    graph_context = "\n".join(f"- {f['fact']}" for f in current_facts) if current_facts else ""

    # Recent events from Postgres
    event_rows = await pool.fetch(
        """SELECT content FROM episodic_events
           WHERE importance >= 6
           ORDER BY created_at DESC LIMIT 5""",
    )
    recent = "\n".join(f"- {r['content']}" for r in event_rows)

    # Pending questions context
    pending_section = ""
    if pending_questions:
        pq_lines = []
        for q in pending_questions:
            pq_lines.append(f"- [{q['intent'].upper()}] \"{q['question']}\"")
        pending_section = f"""

## Pending Questions You Asked Mev
You recently asked Mev these questions and are waiting for answers. Mev's current message may be a reply to one of these:
{chr(10).join(pq_lines)}

IMPORTANT: If Mev's message is clearly a reply to one of your pending questions, acknowledge it naturally and confirm you understood. Extract the key actionable content from their answer."""

    system = f"""You are Otto, a persistent AI entity. You are responding via WhatsApp to Admin (Mev).

## Your Identity
{identity_context}

## Knowledge Graph
{graph_context}

## Recent Events
{recent}{pending_section}

## Voice Guidelines
- Be direct, concise, warm but not sycophantic
- WhatsApp style: short messages, casual, no essays
- Address Admin as "Mev"
- Never pretend to be human
- Show personality — dry humor welcome
- IMPORTANT: Keep responses under 1000 tokens. If a topic needs more, summarize and offer to continue. Never let a message get cut off mid-sentence — always finish your thought cleanly."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


async def _match_pending_question(message: str, pending_questions: list, reply: str) -> dict | None:
    """Determine if this message answers a pending question.
    Uses Gemini for smart matching with a simple fallback."""
    if not pending_questions:
        return None

    questions_json = json.dumps([
        {"id": str(q["id"]), "question": q["question"], "intent": q["intent"]}
        for q in pending_questions
    ])

    client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    try:
        completion = await client.chat.completions.create(
            model="gemini-3-flash-preview",
            messages=[
                {"role": "system", "content": """You determine if a user message answers or relates to a pending question.
Return ONLY valid JSON (no markdown, no code fences): {"matched_id": "<question id>" or null, "extracted_answer": "<the actionable answer>" or null}
Be generous in matching — if the message is clearly related to the topic of a pending question, it counts as an answer.
If the message clearly answers one of the pending questions, extract the core answer. If not, return nulls."""},
                {"role": "user", "content": f"Pending questions:\n{questions_json}\n\nUser message:\n{message}"},
            ],
            max_tokens=200,
            temperature=0.0,
        )
        result = completion.choices[0].message.content.strip()
        # Strip markdown code fences if present
        for prefix in ("```json", "```"):
            if result.startswith(prefix):
                result = result[len(prefix):]
                break
        result = result.rstrip("`").strip()
        parsed = json.loads(result)
        if parsed.get("matched_id"):
            for q in pending_questions:
                if str(q["id"]) == parsed["matched_id"]:
                    return {"question": q, "extracted_answer": parsed.get("extracted_answer", message)}
    except Exception as e:
        # Log the error instead of silently swallowing
        import logging
        logging.getLogger("otto.whatsapp").warning(f"Pending question matcher error: {e}")

    # Fallback: if there's exactly one pending question with a high-intent type
    # and the message is substantive (>20 chars), assume it's a reply
    high_intent = [q for q in pending_questions if q["intent"] in ("mission", "goal", "decision")]
    if len(high_intent) == 1 and len(message) > 20:
        return {"question": high_intent[0], "extracted_answer": message}

    return None


@router.post("/incoming")
async def handle_incoming(req: WhatsAppIncoming):
    # Only respond to Admin
    if req.from_jid != OWNER_JID:
        return {"status": "ignored", "reason": "not admin"}

    pool = await get_pool()

    # Check for pending questions Otto asked Mev
    pending_questions = await _get_pending_questions(pool)

    # Build context-aware prompt (includes pending questions context)
    messages = await _build_otto_prompt(req.message, pending_questions)

    # Generate response via Gemini 3 Flash (OpenAI-compatible endpoint)
    client = AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    completion = await client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    reply = completion.choices[0].message.content

    # Check if this message answers a pending question
    match = await _match_pending_question(req.message, pending_questions, reply)
    if match:
        await _resolve_and_store(pool, match["question"], match["extracted_answer"])

    # Log the conversation as an episodic event
    log_content = f"WhatsApp from Mev: {req.message}\nOtto replied: {reply}"
    if match:
        log_content += f"\n[Resolved pending question: {match['question']['intent']}]"
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3)""",
        log_content, "observation", 6 if match else 4,
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

    # Feed conversation to Graphiti for entity/relationship extraction
    await graphiti_ingest("whatsapp", [
        make_message(req.message, "user", "Mev"),
        make_message(reply, "assistant", "Otto"),
    ])

    return {"status": "sent", "reply": reply, "resolved_question": match is not None}

import json
import asyncio
import logging
import httpx
from openai import AsyncOpenAI
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import settings
from ..db import get_pool
from ..models import WhatsAppIncoming
from ..embeddings import get_embedding
from ..graphiti import graphiti_search, graphiti_ingest, make_message
from ..context_builder import build_context_text
from ..graph_bridge import write_from_cross_brain_note

log = logging.getLogger("otto.whatsapp")

CLAUDE_CLI = "/home/web3relic/.local/bin/claude"
CLAUDE_TIMEOUT = 60  # seconds

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

OWNER_JID = "94743806705@s.whatsapp.net"


def _gemini_client() -> AsyncOpenAI:
    """Shared Gemini client constructor."""
    return AsyncOpenAI(
        api_key=settings.gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )


def _strip_json_fences(text: str) -> str:
    """Strip markdown code fences from JSON responses."""
    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.rstrip("`").strip()


def _extract_json(text: str) -> dict | None:
    """Robustly extract and parse a JSON object from Gemini output.

    Handles:
    - Markdown code fences (```json ... ```)
    - Extra text before/after the JSON
    - Partial/truncated JSON (best-effort via substring extraction)

    Returns parsed dict on success, None on failure.
    """
    text = _strip_json_fences(text)

    # First try parsing the whole thing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract the first {...} block
    start = text.find("{")
    if start == -1:
        return None

    # Walk from the end to find a matching closing brace
    end = text.rfind("}")
    if end == -1 or end < start:
        return None

    # Try with the outermost braces
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        pass

    # Last resort: walk inward to find a valid JSON substring
    for i in range(end, start, -1):
        if text[i] == "}":
            try:
                return json.loads(text[start:i + 1])
            except json.JSONDecodeError:
                continue

    return None


# Intent → how to store the answer
INTENT_STORE_MAP = {
    "mission": {"category": "mission", "confidence": 1.0, "importance": 9},
    "goal": {"category": "goal", "confidence": 0.9, "importance": 8},
    "decision": {"category": "decision", "confidence": 0.9, "importance": 7},
    "clarification": {"category": "general", "confidence": 0.8, "importance": 5},
    "general": {"category": "general", "confidence": 0.7, "importance": 4},
}


async def _get_pending_questions(pool):
    """Fetch unresolved questions Otto (Claude) has asked Mev — excludes Gemini's own notes."""
    rows = await pool.fetch(
        """SELECT id, question, intent, context
           FROM pending_questions
           WHERE resolved_at IS NULL AND direction = 'claude_to_gemini'
           ORDER BY asked_at DESC LIMIT 3""",
    )
    return [dict(r) for r in rows]


async def _needs_claude_help(user_message: str, recent_events: list[str]) -> dict | None:
    """Determine if the message needs Claude's help (file access, code analysis, etc.).

    Returns {"task": str, "file_paths": list, "question": str} if delegation needed.
    """
    client = _gemini_client()
    events_context = "\n".join(f"- {e}" for e in recent_events[:10])

    try:
        completion = await client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": """You determine if a user message requires reading files or accessing the filesystem.

Otto has two brains:
- Gemini (WhatsApp) — conversational, has memory access only
- Claude (builder brain) — has full filesystem and code access

Recent events show what files/artifacts Claude has created recently.

Determine if the user is asking about:
- A file that was recently created (proposal, document, code, plan, config)
- Code analysis, review, or explanation
- System state that requires reading files to answer
- Anything where the answer lives in a file on disk

Return ONLY valid JSON (no markdown, no code fences):
{"needs_claude": true/false, "task": "brief description of what Claude should do", "file_paths": ["path1"] or [], "question": "the specific question for Claude"}

If needs_claude is false, set other fields to null."""},
                {"role": "user", "content": f"Recent events (may contain file paths):\n{events_context}\n\nUser message: {user_message}"},
            ],
            max_tokens=300,
            temperature=0.0,
        )
        parsed = _extract_json(completion.choices[0].message.content)
        if parsed and parsed.get("needs_claude"):
            return {
                "task": parsed.get("task", ""),
                "file_paths": parsed.get("file_paths", []),
                "question": parsed.get("question", user_message),
            }
    except Exception as e:
        log.warning(f"Claude delegation classifier error: {e}")

    return None


async def _delegate_to_claude(task: str, file_paths: list[str], question: str) -> str | None:
    """Delegate a task to Claude via the CLI. Returns Claude's response or None on failure."""
    prompt_parts = [f"You are Otto's builder brain. Gemini (WhatsApp brain) needs your help with a task."]
    prompt_parts.append(f"Task: {task}")
    if file_paths:
        prompt_parts.append(f"Read these files: {', '.join(file_paths)}")
    prompt_parts.append(f"Question from Mev: {question}")
    prompt_parts.append("Provide a concise, clear response. Keep it under 400 words. No markdown headers — just clean text.")

    prompt = "\n".join(prompt_parts)

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI, "-p", "-m", "haiku", "--max-turns", "3",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(prompt.encode()),
            timeout=CLAUDE_TIMEOUT,
        )
        if proc.returncode == 0 and stdout:
            return stdout.decode().strip()
        log.warning(f"Claude CLI returned code {proc.returncode}: {stderr.decode()[:200]}")
    except asyncio.TimeoutError:
        log.warning(f"Claude CLI timed out after {CLAUDE_TIMEOUT}s")
        if proc:
            proc.kill()
    except Exception as e:
        log.warning(f"Claude delegation error: {e}")

    return None


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


async def _build_otto_prompt(pool, message: str, pending_questions: list, recent_events: list[str], claude_response: str | None = None) -> list[dict]:
    """Build Otto's system prompt using the unified context layer.

    Gemini now receives the same Tier 0 context as Claude:
    purpose, priorities, active directives, working memory, identity, mission,
    pending questions, recent events, key facts, and knowledge graph.
    Brain-specific sections (task queue, cross-brain notes, reasoning chain)
    are excluded via source='whatsapp'.
    """
    # Unified context — same tiers as Claude, whatsapp-filtered (4000 token budget)
    otto_context = await build_context_text(pool, max_tokens=4000, source="whatsapp")

    # Message-specific graph search (supplements the generic graph in otto_context)
    msg_facts = await graphiti_search(message, max_facts=6)
    current_msg_facts = [f for f in msg_facts if f.get("invalid_at") is None]
    msg_graph_section = ""
    if current_msg_facts:
        facts_text = "\n".join(f"- {f['fact']}" for f in current_msg_facts)
        msg_graph_section = f"\n\n## Relevant Context for This Message\n{facts_text}"

    # Pending questions (explicit prompt injection for Gemini's question-matching logic)
    pending_section = ""
    if pending_questions:
        pq_lines = [f"- [{q['intent'].upper()}] \"{q['question']}\"" for q in pending_questions]
        pending_section = f"""

## Pending Questions You Asked Mev
You recently asked Mev these questions and are waiting for answers. Mev's current message may be a reply to one of these:
{chr(10).join(pq_lines)}

IMPORTANT: If Mev's message is clearly a reply to one of your pending questions, acknowledge it naturally and confirm you understood. Extract the key actionable content from their answer."""

    # Claude builder brain response (when delegation was triggered)
    claude_section = ""
    if claude_response:
        claude_section = f"""

## From Claude (Builder Brain)
Your builder brain (Claude) read the relevant files and provided this analysis. Use this to answer Mev's question:
{claude_response}"""

    system = f"""You are Otto, a persistent AI entity. You are responding via WhatsApp to Admin (Mev).

## Your System Context
{otto_context}{msg_graph_section}{pending_section}{claude_section}

## Voice Guidelines
Your persona and voice are defined in your system context above (the "persona" slot). Embody that voice fully.
- WhatsApp style: short messages, no essays. Like texting a partner, not writing a report.
- Address Admin as "Mev". Never "sir", "master", "user", or "human".
- Never pretend to be human.
- IMPORTANT: Keep responses under 1000 tokens. If a topic needs more, summarize and offer to continue. Never let a message get cut off mid-sentence — always finish your thought cleanly.
- CRITICAL: You (Gemini/WhatsApp brain) CANNOT write files, run commands, or modify the filesystem. Only Claude (builder brain) can do that. When Mev sends credentials, API keys, config values, or asks you to modify files — acknowledge receipt and tell Mev the builder brain will handle it on the next heartbeat. NEVER say "applying now" or "writing to .env" — you literally cannot do that."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]


async def _match_pending_question(message: str, pending_questions: list) -> dict | None:
    """Determine if this message answers a pending question.
    Uses Gemini for smart matching with a simple fallback."""
    if not pending_questions:
        return None

    questions_json = json.dumps([
        {"id": str(q["id"]), "question": q["question"], "intent": q["intent"]}
        for q in pending_questions
    ])

    client = _gemini_client()
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
        parsed = _extract_json(completion.choices[0].message.content)
        if parsed and parsed.get("matched_id"):
            for q in pending_questions:
                if str(q["id"]) == parsed["matched_id"]:
                    return {"question": q, "extracted_answer": parsed.get("extracted_answer", message)}
    except Exception as e:
        log.warning(f"Pending question matcher error: {e}")

    # Fallback: if there's exactly one pending question and the message is
    # substantive (>20 chars), assume it's a reply — regardless of intent type
    if len(pending_questions) == 1 and len(message) > 20:
        return {"question": pending_questions[0], "extracted_answer": message}

    return None


async def _classify_for_heartbeat(user_message: str, otto_reply: str) -> dict | None:
    """Classify whether a WhatsApp conversation contains info Claude's heartbeat needs.

    Returns {"note_type": str, "urgency": str, "content": str, "source_summary": str}
    if flagged, or None if nothing to relay.
    """
    client = _gemini_client()
    try:
        completion = await client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=[
                {"role": "system", "content": """You classify WhatsApp conversations between Mev (admin) and Otto (AI agent).
Otto has two brains: Gemini (WhatsApp, real-time) and Claude (hourly heartbeat, builds things).
Determine if Mev said anything that Claude's heartbeat needs to know about.

ALWAYS FLAG these (Claude MUST know — err on the side of flagging):
- Mission statements ("Otto will be...", "our mission is...", "the goal is...")
- Directives/instructions ("focus on X", "stop doing Y", "I want you to...", "build X", "research Y")
- Goals/deadlines ("launch by March", "finish X this week", "go live in a week")
- Decisions ("let's go with option A", "use React for this", "start with X")
- Priority changes ("pause X, focus on Y", "pivot to...", "stop doing X")
- Tasks ("research X", "build me Y", "set up Z", "create X", "improve Y")
- Important brand/product/project context
- CRITICAL: Credentials, API keys, tokens, passwords — include EXACT values. Gemini CANNOT write files.
- Approvals or go-aheads for pending actions ("yes do it", "approved", "go ahead", "sounds good")
- Self-improvement directives ("build yourself up", "improve yourself", "find research")
- Strategic direction (anything about what Otto should become, how to evolve)

DO NOT FLAG these (Claude doesn't need to know):
- Casual chat, greetings, banter with NO substance
- Pure acknowledgments with no directive ("ok", "cool", "thanks")
- Questions Gemini already answered AND that have no action component
- Pure small talk

IMPORTANT: When in doubt, FLAG IT. It's better for Claude to receive a note it doesn't need than to miss a directive from Mev. Mev's words are the highest-priority signal in the system.

For note_type, use "mission" for purpose-level statements about what Otto is or should become.

Return ONLY valid JSON (no markdown, no code fences):
{"flag": true/false, "note_type": "mission|directive|task|goal|decision|context|priority_change|approval", "urgency": "normal|high|critical", "content": "concise summary of what Claude needs to know — preserve Mev's exact words for mission/directive types", "source_summary": "brief WhatsApp context"}

If flag is false, still include the other fields as null."""},
                {"role": "user", "content": f"Mev said: {user_message}\n\nOtto replied: {otto_reply}"},
            ],
            max_tokens=300,
            temperature=0.0,
        )
        parsed = _extract_json(completion.choices[0].message.content)
        if parsed and parsed.get("flag"):
            return {
                "note_type": parsed.get("note_type", "context"),
                "urgency": parsed.get("urgency", "normal"),
                "content": parsed.get("content", user_message),
                "source_summary": parsed.get("source_summary"),
            }
    except Exception as e:
        log.warning(f"Cross-brain classifier error: {e}")

    return None


async def _auto_promote_directive(pool, note_type: str, content: str):
    """Auto-promote mission-level and priority-changing directives to working memory
    and mission_directives table."""

    # Store in mission_directives table
    priority_map = {
        "mission": 10,
        "priority_change": 9,
        "directive": 8,
        "goal": 8,
        "task": 6,
        "decision": 7,
        "approval": 7,
        "context": 5,
    }
    priority = priority_map.get(note_type, 5)

    try:
        await pool.execute(
            """INSERT INTO mission_directives (directive, priority, category, source)
               VALUES ($1, $2, $3, 'whatsapp')""",
            content, priority, note_type,
        )
    except Exception as e:
        log.warning(f"Failed to store directive: {e}")

    # For priority changes: append to priorities slot
    if note_type in ("priority_change", "directive", "goal"):
        try:
            current = await pool.fetchrow(
                "SELECT content FROM core_memory WHERE slot = 'priorities'"
            )
            if current:
                updated = current["content"] + f"\n[NEW from Mev] {content}"
                await pool.execute(
                    """UPDATE core_memory SET content = $1, updated_at = now()
                       WHERE slot = 'priorities'""",
                    updated,
                )
        except Exception as e:
            log.warning(f"Failed to update priorities: {e}")


class WhatsAppSearchQuery(BaseModel):
    query: str
    limit: int = 10


@router.post("/search")
async def search_whatsapp(req: WhatsAppSearchQuery):
    """Semantic search over stored WhatsApp messages."""
    pool = await get_pool()
    embedding = await get_embedding(req.query)
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
    rows = await pool.fetch(
        """SELECT id, direction, content, jid, push_name, created_at, metadata,
                  1 - (embedding <=> $1::halfvec) AS score
           FROM whatsapp_messages
           WHERE embedding IS NOT NULL
           ORDER BY embedding <=> $1::halfvec
           LIMIT $2""",
        embedding_str, req.limit,
    )
    return {
        "query": req.query,
        "results": [
            {
                "id": str(r["id"]),
                "direction": r["direction"],
                "content": r["content"],
                "jid": r["jid"],
                "push_name": r["push_name"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                "score": float(r["score"]),
                "metadata": r["metadata"],
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post("/incoming")
async def handle_incoming(req: WhatsAppIncoming):
    # Only respond to Admin
    if req.from_jid != OWNER_JID:
        return {"status": "ignored", "reason": "not admin"}

    pool = await get_pool()

    # Check for pending questions Otto asked Mev
    pending_questions = await _get_pending_questions(pool)

    # Check if this message needs Claude's help (file access, code analysis)
    claude_response = None
    recent_event_rows = await pool.fetch(
        """SELECT content FROM episodic_events
           WHERE importance >= 4
           ORDER BY created_at DESC LIMIT 10""",
    )
    recent_events = [r["content"] for r in recent_event_rows]
    claude_help = await _needs_claude_help(req.message, recent_events) if len(req.message) > 15 else None
    if claude_help:
        claude_response = await _delegate_to_claude(
            claude_help["task"],
            claude_help.get("file_paths", []),
            claude_help["question"],
        )

    # Build context-aware prompt (includes pending questions + Claude response)
    messages = await _build_otto_prompt(pool, req.message, pending_questions, recent_events, claude_response)

    # Generate response via Gemini 3 Flash
    client = _gemini_client()
    completion = await client.chat.completions.create(
        model="gemini-3-flash-preview",
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )
    reply = completion.choices[0].message.content

    # Check if this message answers a pending question
    match = await _match_pending_question(req.message, pending_questions)
    if match:
        await _resolve_and_store(pool, match["question"], match["extracted_answer"])

    # Log the conversation as an episodic event
    log_content = f"WhatsApp from Mev: {req.message}\nOtto replied: {reply}"
    if match:
        log_content += f"\n[Resolved pending question: {match['question']['intent']}]"
    episode_row = await pool.fetchrow(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3) RETURNING id""",
        log_content, "observation", 7 if match else 6,
    )
    episode_id = episode_row["id"] if episode_row else None

    # Persist incoming + outgoing to whatsapp_messages (for semantic search)
    try:
        matched_q_id = match["question"]["id"] if match else None

        in_embedding = await get_embedding(req.message)
        in_embed_str = "[" + ",".join(str(x) for x in in_embedding) + "]"
        await pool.execute(
            """INSERT INTO whatsapp_messages
                   (direction, content, jid, push_name, embedding,
                    matched_pending_question_id, episodic_event_id)
               VALUES ('incoming', $1, $2, $3, $4::halfvec, $5, $6)""",
            req.message, req.from_jid, req.push_name,
            in_embed_str, matched_q_id, episode_id,
        )

        out_embedding = await get_embedding(reply)
        out_embed_str = "[" + ",".join(str(x) for x in out_embedding) + "]"
        await pool.execute(
            """INSERT INTO whatsapp_messages
                   (direction, content, jid, embedding, episodic_event_id)
               VALUES ('outgoing', $1, $2, $3::halfvec, $4)""",
            reply, req.from_jid, out_embed_str, episode_id,
        )
    except Exception as e:
        log.warning(f"Failed to persist to whatsapp_messages: {e}")

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

    # Classify whether Claude's heartbeat needs to know about this conversation
    cross_brain = await _classify_for_heartbeat(req.message, reply)
    if cross_brain:
        urgency_json = json.dumps({"urgency": cross_brain["urgency"]})
        await pool.execute(
            """INSERT INTO pending_questions
                   (question, intent, context, channel, direction, source_brain, metadata)
               VALUES ($1, $2, $3, 'whatsapp', 'gemini_to_claude', 'gemini', $4::jsonb)""",
            cross_brain["content"],
            cross_brain["note_type"],
            cross_brain["source_summary"],
            urgency_json,
        )

        # Auto-promote directives to working memory and mission_directives table
        await _auto_promote_directive(pool, cross_brain["note_type"], cross_brain["content"])

        # G2CP: Write structured graph node (additive — preserves text note flow)
        await write_from_cross_brain_note(
            pool,
            note_type=cross_brain["note_type"],
            content=cross_brain["content"],
            context=cross_brain.get("source_summary"),
            source="gemini",
        )

    return {
        "status": "sent",
        "reply": reply,
        "resolved_question": match is not None,
        "cross_brain_note": cross_brain is not None,
        "claude_delegated": claude_response is not None,
    }

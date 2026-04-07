"""Message persistence, event logging, and directive promotion.

Extracted from whatsapp.py — all channel-agnostic.
"""

import json
import logging

from ..embeddings import get_embedding
from ..graphiti import graphiti_ingest, make_message
from ..graph_bridge import write_from_classified_note

log = logging.getLogger("otto.gateway.persistence")

# Intent → how to store the answer
INTENT_STORE_MAP = {
    "mission": {"category": "mission", "confidence": 1.0, "importance": 9},
    "goal": {"category": "goal", "confidence": 0.9, "importance": 8},
    "decision": {"category": "decision", "confidence": 0.9, "importance": 7},
    "clarification": {"category": "general", "confidence": 0.8, "importance": 5},
    "general": {"category": "general", "confidence": 0.7, "importance": 4},
}


async def get_pending_questions(pool):
    """Fetch unresolved questions Otto has asked Mev."""
    rows = await pool.fetch(
        """SELECT id, question, intent, context
           FROM pending_questions
           WHERE resolved_at IS NULL
           ORDER BY asked_at DESC LIMIT 3""",
    )
    return [dict(r) for r in rows]


async def resolve_and_store(pool, question, answer: str):
    """Resolve a pending question and store the answer appropriately."""
    intent = question["intent"]
    store_config = INTENT_STORE_MAP.get(intent, INTENT_STORE_MAP["general"])

    await pool.execute(
        """UPDATE pending_questions SET resolved_at = now(), answer = $2 WHERE id = $1""",
        question["id"], answer,
    )

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
        "gateway_reply", embedding_str,
    )

    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3)""",
        f"Mev answered Otto's question ({intent}): {answer}\nOriginal question: {question['question']}",
        "decision", store_config["importance"],
    )


async def get_open_proposals(pool) -> list[dict]:
    """Fetch open decision proposals waiting for Mev's response."""
    rows = await pool.fetch(
        """SELECT id, question, context, options, recommendation,
                  recommendation_reason, source, source_task_id, urgency
           FROM decision_proposals
           WHERE status = 'open'
           ORDER BY created_at DESC LIMIT 5""",
    )
    return [dict(r) for r in rows]


async def match_and_resolve_proposal(pool, message: str, proposals: list) -> dict | None:
    """Check if Mev's message resolves an open decision proposal.

    Uses LLM to match — similar to match_pending_question but for structured proposals.
    Returns {proposal: dict, resolution: str} or None.
    """
    if not proposals:
        return None

    from ..llm import llm_chat

    proposals_text = "\n".join(
        f"[{i}] {p['question']} (options: {p.get('options', [])})"
        for i, p in enumerate(proposals)
    )

    system_msg = (
        "You determine if a user message answers or relates to a pending decision proposal. "
        "Return ONLY valid JSON (no markdown): {\"matched_index\": <0-based index or null>, "
        "\"resolution\": \"<Mev's choice or directive>\" or null}. "
        "Be generous — if the message is clearly about one of these decisions, extract the answer."
    )
    user_msg = f"Open proposals:\n{proposals_text}\n\nMev's message:\n{message}"

    try:
        raw = await llm_chat(
            [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}],
            max_tokens=200, temperature=0.1,
        )
        import re
        json_match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            idx = data.get("matched_index")
            resolution = data.get("resolution")
            if idx is not None and resolution and 0 <= idx < len(proposals):
                proposal = proposals[idx]
                # Resolve in DB
                await pool.execute(
                    """UPDATE decision_proposals
                       SET status = 'resolved', resolution = $2, resolved_at = NOW()
                       WHERE id = $1""",
                    proposal["id"], resolution,
                )
                # Log as episodic event
                await pool.execute(
                    """INSERT INTO episodic_events (content, event_type, importance, metadata)
                       VALUES ($1, 'decision', 7, $2::jsonb)""",
                    f"Mev resolved proposal: {proposal['question']} → {resolution}",
                    json.dumps({"proposal_id": str(proposal["id"]), "source": proposal.get("source")}),
                )
                log.info(f"Proposal resolved via gateway: {proposal['question'][:60]} → {resolution[:60]}")
                return {"proposal": proposal, "resolution": resolution}
    except Exception as e:
        log.warning(f"Proposal matching failed: {e}")

    return None


async def log_conversation(pool, channel: str, user_message: str, reply: str, match=None):
    """Log the conversation as an episodic event. Returns episode_id."""
    log_content = f"{channel.title()} from Mev: {user_message}\nOtto replied: {reply}"
    if match:
        log_content += f"\n[Resolved pending question: {match['question']['intent']}]"
    episode_row = await pool.fetchrow(
        """INSERT INTO episodic_events (content, event_type, importance)
           VALUES ($1, $2, $3) RETURNING id""",
        log_content, "observation", 7 if match else 6,
    )
    return episode_row["id"] if episode_row else None


async def persist_messages(pool, channel: str, sender_id: str, sender_name: str | None,
                           user_message: str, reply: str, episode_id, match=None):
    """Persist outgoing reply + backfill embedding on the early-persisted incoming message.

    The incoming message is now persisted early (before LLM call) in ric.py
    to prevent the race condition where rapid follow-up messages miss prior
    history. This Phase 5 hook:
    1. Backfills the embedding on the already-persisted incoming message
    2. Persists the outgoing reply with embedding
    """
    try:
        matched_q_id = match["question"]["id"] if match else None

        # Backfill embedding + metadata on the early-persisted incoming message
        in_embedding = await get_embedding(user_message)
        in_embed_str = "[" + ",".join(str(x) for x in in_embedding) + "]"
        updated = await pool.execute(
            """UPDATE whatsapp_messages
               SET embedding = $1::halfvec,
                   matched_pending_question_id = $2,
                   episodic_event_id = $3
               WHERE id = (
                   SELECT id FROM whatsapp_messages
                   WHERE direction = 'incoming' AND content = $4 AND channel = $5
                     AND embedding IS NULL
                   ORDER BY created_at DESC LIMIT 1
               )""",
            in_embed_str, matched_q_id, episode_id, user_message, channel,
        )
        # Fallback: if UPDATE matched nothing (edge case), INSERT as before
        if updated and "UPDATE 0" in str(updated):
            await pool.execute(
                """INSERT INTO whatsapp_messages
                       (direction, content, jid, push_name, embedding,
                        matched_pending_question_id, episodic_event_id, channel)
                   VALUES ('incoming', $1, $2, $3, $4::halfvec, $5, $6, $7)""",
                user_message, sender_id, sender_name,
                in_embed_str, matched_q_id, episode_id, channel,
            )

        # Persist the outgoing reply
        out_embedding = await get_embedding(reply)
        out_embed_str = "[" + ",".join(str(x) for x in out_embedding) + "]"
        await pool.execute(
            """INSERT INTO whatsapp_messages
                   (direction, content, jid, embedding, episodic_event_id, channel)
               VALUES ('outgoing', $1, $2, $3::halfvec, $4, $5)""",
            reply, sender_id, out_embed_str, episode_id, channel,
        )
    except Exception as e:
        log.warning(f"Failed to persist messages: {e}")


async def ingest_to_graph(channel: str, user_message: str, reply: str):
    """Feed conversation to Graphiti for entity/relationship extraction."""
    await graphiti_ingest(channel, [
        make_message(user_message, "user", "Mev"),
        make_message(reply, "assistant", "Otto"),
    ])


async def store_classified_directive(pool, channel: str, classified: dict):
    """Store a classified directive from gateway and auto-promote it.

    Called from the legacy handler path when classify_for_heartbeat() detects
    a directive, task, or decision in Mev's message.
    """
    urgency_json = json.dumps({"urgency": classified["urgency"]})
    await pool.execute(
        """INSERT INTO pending_questions
               (question, intent, context, channel, direction, source_brain, metadata)
           VALUES ($1, $2, $3, $4, 'inbound', 'kernel', $5::jsonb)""",
        classified["content"],
        classified["note_type"],
        classified["source_summary"],
        channel,
        urgency_json,
    )

    await auto_promote_directive(pool, classified["note_type"], classified["content"])

    await write_from_classified_note(
        pool,
        note_type=classified["note_type"],
        content=classified["content"],
        context=classified.get("source_summary"),
        source="gateway",
    )


# Backward-compatible alias
store_cross_brain_note = store_classified_directive


async def auto_promote_directive(pool, note_type: str, content: str):
    """Auto-promote mission-level and priority-changing directives to working memory
    and mission_directives table."""
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
               VALUES ($1, $2, $3, 'gateway')""",
            content, priority, note_type,
        )
    except Exception as e:
        log.warning(f"Failed to store directive: {e}")

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

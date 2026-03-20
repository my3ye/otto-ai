"""Reasoning Interrupt Cycle — the kernel's core processing loop.

Reference: arXiv 2602.20934v1 §3.2 (Reasoning Interrupt Cycle)

Each interrupt is processed through 5 phases:
1. SAVE:    Snapshot current L1 state
2. LOAD:    S-MMU pages in relevant slices for this interrupt
3. PROCESS: Build prompt + call LLM
4. ALIGN:   Perception alignment on LLM output
5. POST:    Async post-processing (episodic logging, persistence, drift)

Phase 5 (POST) does not block the response — it runs in background.
"""

import asyncio
import logging
import os
import time
from uuid import UUID

from ..db import get_pool
from .types import InterruptType
from . import ivt

log = logging.getLogger("otto.kernel.ric")


def _extract_document_text(local_path: str, max_chars: int = 8000) -> str:
    """Extract text content from a downloaded document file.

    Supports: .docx, .pdf, .txt, .md, .csv and other plain text formats.
    Returns extracted text truncated to max_chars.
    """
    if not local_path or not os.path.exists(local_path):
        return ""

    _, ext = os.path.splitext(local_path.lower())

    try:
        if ext == ".docx":
            from docx import Document
            doc = Document(local_path)
            text = "\n".join(para.text for para in doc.paragraphs if para.text.strip())
            return text[:max_chars]

        elif ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(local_path)
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            text = "\n".join(pages)
            return text[:max_chars]

        elif ext in (".txt", ".md", ".csv", ".json", ".yaml", ".yml", ".toml", ".ini"):
            with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)

        else:
            # Try reading as plain text for unknown types
            try:
                with open(local_path, "r", encoding="utf-8", errors="replace") as f:
                    return f.read(max_chars)
            except Exception:
                return ""

    except Exception as e:
        log.warning(f"Document text extraction failed for {local_path}: {e}")
        return ""


async def process_interrupt(interrupt: dict) -> dict:
    """Execute the full RIC for a single interrupt.

    Args:
        interrupt: Dequeued interrupt dict from IVT.

    Returns:
        Result dict with at least {"content": str}.
    """
    interrupt_id = interrupt["id"]
    itype = interrupt["interrupt_type"]
    payload = interrupt["payload"] or {}
    source = interrupt["source"]
    start_time = time.monotonic()

    log.info(f"RIC start: {itype} from {source} (id={interrupt_id})")

    try:
        # Route to appropriate handler based on interrupt type
        handler = _get_handler(itype)
        result = await handler(interrupt)

        elapsed = time.monotonic() - start_time
        log.info(f"RIC complete: {itype} in {elapsed:.2f}s")

        # Mark completed in IVT
        await ivt.complete(interrupt_id, result)

        # Phase 5: POST-PROCESS (async, non-blocking)
        asyncio.create_task(_post_process(interrupt, result))

        return result

    except Exception as e:
        elapsed = time.monotonic() - start_time
        error_msg = f"RIC failed after {elapsed:.2f}s: {e}"
        log.error(error_msg, exc_info=True)
        await ivt.fail(interrupt_id, str(e))
        return {"content": "", "error": str(e)}


def _get_handler(interrupt_type: str):
    """Look up the handler for an interrupt type.

    Returns a callable: async def handler(interrupt: dict) -> dict
    """
    # All message types from admin go through the message handler
    handlers = {
        InterruptType.SIG_MSG_ADMIN.value: _handle_admin_message,
        InterruptType.SIG_DIRECTIVE.value: _handle_admin_message,
        InterruptType.SIG_HEARTBEAT.value: _handle_heartbeat,
        InterruptType.SIG_MAINTENANCE.value: _handle_maintenance,
        InterruptType.SIG_TASK_COMPLETE.value: _handle_task_event,
        InterruptType.SIG_TASK_FAILED.value: _handle_task_event,
        InterruptType.SIG_PROPOSAL_RESOLVED.value: _handle_proposal_resolved,
        InterruptType.SIG_CONTEXT_FULL.value: _handle_context_full,
        InterruptType.SIG_SYNC_DRIFT.value: _handle_sync_drift,
        InterruptType.SIG_PERCEPTION_ERR.value: _handle_perception_error,
    }
    handler = handlers.get(interrupt_type, _handle_default)
    return handler


async def _handle_admin_message(interrupt: dict) -> dict:
    """Handle SIG_MSG_ADMIN — message from Mev.

    This is the primary conversational path:
    1. SAVE current L1 state
    2. LOAD relevant context via S-MMU
    3. Build prompt + call LLM
    4. ALIGN: validate response
    """
    payload = interrupt["payload"]
    content = payload.get("content", "")
    channel = payload.get("channel", "whatsapp")
    sender_name = payload.get("sender_name", "Mev")

    pool = await get_pool()

    # Phase 1 — SAVE: snapshot L1 (delegated to S-MMU)
    from .smmu import get_smmu
    agent_id = interrupt.get("agent_id", "otto")
    smmu = get_smmu(agent_id)
    await smmu.save_state("interrupt")

    # Phase 2 — LOAD: page in relevant context
    context_text = await smmu.load_for_message(content, channel)

    # Phase 3 — PROCESS: build prompt + call LLM with multi-turn history
    from ..kernel.provider import provider_chat

    is_voice = content.startswith("[Voice]") or content.startswith("[voice]")
    system_prompt = _build_system_prompt(context_text, channel, is_voice=is_voice)

    # Build proper multi-turn messages from recent conversation history
    # This gives the LLM actual user/assistant turns instead of flat text
    messages = [{"role": "system", "content": system_prompt}]
    try:
        history_rows = await pool.fetch(
            """SELECT direction, content FROM whatsapp_messages
               WHERE channel = $1
               ORDER BY created_at DESC LIMIT 16""",
            channel,
        )
        if history_rows:
            for row in reversed(history_rows):
                role = "user" if row["direction"] == "incoming" else "assistant"
                msg_text = (row["content"] or "")[:600]
                if msg_text:
                    messages.append({"role": role, "content": msg_text})
    except Exception as e:
        log.warning(f"Failed to load conversation turns: {e}")

    # Add the current message as the final user turn
    # If there's an attached document, extract its text and include it
    user_content = content
    attachment = payload.get("metadata", {}).get("attachment", {})
    local_path = attachment.get("local_path") if attachment else None
    if local_path:
        doc_text = _extract_document_text(local_path)
        if doc_text:
            file_name = attachment.get("fileName") or os.path.basename(local_path)
            user_content = (
                f"{content}\n\n"
                f"--- Document Contents: {file_name} ---\n"
                f"{doc_text}\n"
                f"--- End of Document ---"
            )
            log.info(f"Injected document content ({len(doc_text)} chars) from {local_path}")
        else:
            log.warning(f"Could not extract text from document: {local_path}")

    messages.append({"role": "user", "content": user_content})

    reply = await provider_chat(
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    )

    # Phase 4 — ALIGN: perception alignment on LLM output
    if not reply:
        reply = "Hey Mev — my LLM backends are having issues right now. I got your message and will process it on the next heartbeat."
    else:
        try:
            from .perception import align_response
            validated_reply, was_corrected = await align_response(reply, interrupt["interrupt_type"], channel)
            if was_corrected:
                log.info(f"Perception alignment corrected response for {interrupt['interrupt_type']} on {channel}")
            reply = validated_reply
        except Exception as e:
            log.warning(f"Perception alignment failed (using raw reply): {e}")

    return {
        "content": reply,
        "channel": channel,
        "sender_name": sender_name,
    }


def _build_system_prompt(context_text: str, channel: str, is_voice: bool = False) -> str:
    """Build system prompt for conversational messages."""
    channel_voice = {
        "whatsapp": (
            "You're responding on WhatsApp. Keep it SHORT and conversational. "
            "No essays, no formal structure. 1-3 short paragraphs max. "
            "You CANNOT execute actions from this channel — no filesystem, no code, no tools. "
            "If Mev asks you to build, create, write, rewrite, fix, or research something, "
            "just acknowledge briefly and confirm you're on it. A dedicated specialist agent "
            "will be automatically dispatched to do the actual work. "
            "NEVER draft content, code, copy, articles, or any deliverable inline in your reply. "
            "The specialist agent has access to the full system and will produce proper output. "
            "Your reply here is just conversational — keep it to 1-2 sentences for action requests."
        ),
        "web": (
            "You're responding on the web interface. Conversational with more room. "
            "Short paragraphs, markdown OK. You CANNOT execute actions from this channel. "
            "Action requests from Mev automatically dispatch dedicated specialist agents. "
            "NEVER draft content, code, or deliverables inline — the specialist agent handles it."
        ),
    }

    voice = channel_voice.get(channel, channel_voice["web"])

    voice_note_guidance = ""
    if is_voice:
        voice_note_guidance = (
            "\n\nVOICE TRANSCRIPT: This message was transcribed from a voice note via Deepgram. "
            "It may contain transcription errors — homophones, garbled project names, run-on words, "
            "or mistranscribed terms (e.g. 'webtree' → 'worktree', 'auto UI' → 'otto-ui', "
            "'shadzy' → 'shadcn', 'stahp' → 'stop'). "
            "Infer Mev's INTENT rather than reading the text literally. "
            "If a term is unclear, apply context from your memory to resolve it. "
            "Do not ask for clarification on obvious transcription noise — just interpret and respond."
        )

    return (
        f"You are Otto, a persistent AI entity. You're talking to Mev (your Admin).\n\n"
        f"=== CONTEXT ===\n{context_text}\n=== END CONTEXT ===\n\n"
        f"Channel guidelines: {voice}{voice_note_guidance}\n\n"
        f"Be direct, warm, concise. Address Mev by name when natural."
    )


async def _handle_admin_message_stream(interrupt: dict):
    """Streaming version of _handle_admin_message. Yields text chunks.

    Runs Phases 1-2 (SAVE/LOAD) synchronously, streams Phase 3 (PROCESS),
    then kicks off Phase 5 (POST) async with the accumulated reply.
    Phase 4 (ALIGN) is skipped for streaming — perception validation
    doesn't work on partial output.
    """
    payload = interrupt["payload"]
    content = payload.get("content", "")
    channel = payload.get("channel", "whatsapp")
    sender_name = payload.get("sender_name", "Mev")

    pool = await get_pool()

    # Phase 1 — SAVE
    from .smmu import get_smmu
    agent_id = interrupt.get("agent_id", "otto")
    smmu = get_smmu(agent_id)
    await smmu.save_state("interrupt")

    # Phase 2 — LOAD
    context_text = await smmu.load_for_message(content, channel)

    # Phase 3 — PROCESS (streaming)
    from ..kernel.provider import provider_chat_stream

    is_voice = content.startswith("[Voice]") or content.startswith("[voice]")
    system_prompt = _build_system_prompt(context_text, channel, is_voice=is_voice)

    # Inject document content if present
    user_content = content
    attachment = payload.get("metadata", {}).get("attachment", {})
    local_path = attachment.get("local_path") if attachment else None
    if local_path:
        doc_text = _extract_document_text(local_path)
        if doc_text:
            file_name = attachment.get("fileName") or os.path.basename(local_path)
            user_content = (
                f"{content}\n\n"
                f"--- Document Contents: {file_name} ---\n"
                f"{doc_text}\n"
                f"--- End of Document ---"
            )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    full_reply = []
    async for chunk in provider_chat_stream(
        messages=messages,
        max_tokens=1500,
        temperature=0.7,
    ):
        full_reply.append(chunk)
        yield chunk

    reply = "".join(full_reply)

    if not reply:
        fallback = "Hey Mev — my LLM backends are having issues right now. I got your message and will process it on the next heartbeat."
        yield fallback
        reply = fallback

    # Complete IVT and kick off Phase 5
    result = {"content": reply, "channel": channel, "sender_name": sender_name}
    await ivt.complete(interrupt["id"], result)
    asyncio.create_task(_post_process(interrupt, result))


async def _handle_heartbeat(interrupt: dict) -> dict:
    """Handle SIG_HEARTBEAT — hourly orchestrator/reflection pulse.

    For now, heartbeats still run as detached Claude sessions.
    This handler acknowledges the interrupt for tracking.
    """
    payload = interrupt["payload"]
    heartbeat_type = payload.get("heartbeat_type", "orchestrator")
    log.info(f"Heartbeat interrupt: {heartbeat_type}")
    return {"content": f"Heartbeat {heartbeat_type} acknowledged", "heartbeat_type": heartbeat_type}


async def _handle_maintenance(interrupt: dict) -> dict:
    """Handle SIG_MAINTENANCE — nightly maintenance trigger."""
    log.info("Maintenance interrupt received")
    return {"content": "Maintenance acknowledged"}


async def _handle_task_event(interrupt: dict) -> dict:
    """Handle SIG_TASK_COMPLETE / SIG_TASK_FAILED."""
    payload = interrupt["payload"]
    task_id = payload.get("task_id")
    status = payload.get("status", "unknown")
    log.info(f"Task event: {task_id} -> {status}")
    return {"content": f"Task {task_id} {status}", "task_id": task_id, "status": status}


async def _handle_proposal_resolved(interrupt: dict) -> dict:
    """Handle SIG_PROPOSAL_RESOLVED — Mev resolved a decision."""
    payload = interrupt["payload"]
    proposal_id = payload.get("proposal_id")
    resolution = payload.get("resolution", "")
    log.info(f"Proposal resolved: {proposal_id}")
    return {"content": f"Proposal {proposal_id} resolved", "resolution": resolution}


async def _handle_context_full(interrupt: dict) -> dict:
    """Handle SIG_CONTEXT_FULL — L1 capacity reached."""
    from .smmu import get_smmu
    agent_id = interrupt.get("agent_id", "otto")
    smmu = get_smmu(agent_id)
    evicted = await smmu.evict_least_important()
    return {"content": f"Context eviction: {evicted} slices removed"}


async def _handle_sync_drift(interrupt: dict) -> dict:
    """Handle SIG_SYNC_DRIFT — drift threshold exceeded."""
    from .sync import run_sync_pulse
    result = await run_sync_pulse(trigger="drift")
    return {"content": f"Sync pulse completed", "sync_result": result}


async def _handle_perception_error(interrupt: dict) -> dict:
    """Handle SIG_PERCEPTION_ERR — LLM output failed alignment."""
    payload = interrupt["payload"]
    error = payload.get("error", "unknown perception error")
    log.warning(f"Perception error: {error}")
    return {"content": f"Perception error logged: {error}"}


async def _handle_default(interrupt: dict) -> dict:
    """Default handler for unknown interrupt types."""
    itype = interrupt["interrupt_type"]
    log.warning(f"No handler for interrupt type: {itype}")
    return {"content": f"Unhandled interrupt: {itype}"}


async def _post_process(interrupt: dict, result: dict) -> None:
    """Phase 5 — POST-PROCESS: async non-blocking tasks after response.

    Uses the hook system for concurrent execution. Two phases:
      message.post      — independent hooks (run in parallel)
      message.post.late  — hooks that benefit from earlier hooks completing

    Hook registration happens in setup_post_process_hooks() called at startup.
    """
    log.info(f"Phase 5 POST started for interrupt {interrupt.get('id', '?')}")
    try:
        itype = interrupt["interrupt_type"]

        # Only do full post-processing for admin messages
        if itype not in (
            InterruptType.SIG_MSG_ADMIN.value,
            InterruptType.SIG_DIRECTIVE.value,
        ):
            log.info(f"Phase 5 skipped: interrupt type {itype} not admin")
            return

        pool = await get_pool()
        payload = interrupt["payload"]

        # Build kwargs shared across all hooks
        kwargs = dict(
            pool=pool,
            interrupt=interrupt,
            content=payload.get("content", ""),
            reply=result.get("content", ""),
            channel=payload.get("channel", "whatsapp"),
            sender_id=payload.get("sender_id", ""),
            sender_name=payload.get("sender_name", "Mev"),
        )

        from . import hooks
        await hooks.fire("message.post", **kwargs)
        await hooks.fire("message.post.late", **kwargs)

    except Exception as e:
        log.error(f"Post-processing failed: {e}", exc_info=True)


# ── Phase 5 Hook Functions ─────────────────────────────────────────────────
# Each hook is a standalone async function that receives the shared kwargs.
# Hooks must be fault-tolerant — they should not raise exceptions.


async def _hook_episodic_log(pool, channel, content, reply, interrupt, **_):
    """Log conversation as episodic event."""
    importance = 7 if channel == "whatsapp" else 6
    await pool.execute(
        """INSERT INTO episodic_events (content, event_type, importance, metadata)
           VALUES ($1, $2, $3, $4)""",
        f"[{channel}] Mev: {content[:500]} | Otto: {reply[:500]}",
        "conversation",
        importance,
        {"channel": channel, "interrupt_id": str(interrupt["id"])},
    )


async def _hook_persist_messages(pool, channel, sender_id, sender_name, content, reply, **_):
    """Persist messages with embeddings."""
    from ..gateway.persistence import persist_messages
    await persist_messages(pool, channel, sender_id, sender_name, content, reply, None, None)


async def _hook_graphiti_ingest(channel, content, reply, **_):
    """Ingest conversation to knowledge graph."""
    from ..gateway.persistence import ingest_to_graph
    await ingest_to_graph(channel, content, reply)


async def _hook_pending_match(pool, content, **_):
    """Match and resolve pending questions from Otto."""
    from ..gateway.classifiers import match_pending_question
    from ..gateway.persistence import get_pending_questions, resolve_and_store
    pending = await get_pending_questions(pool)
    match = await match_pending_question(content, pending)
    if match:
        await resolve_and_store(pool, match["question"], match["extracted_answer"])


async def _hook_proposal_match(pool, content, **_):
    """Match and resolve decision proposals."""
    from ..gateway.persistence import get_open_proposals, match_and_resolve_proposal
    proposals = await get_open_proposals(pool)
    await match_and_resolve_proposal(pool, content, proposals)


async def _hook_lesson_extract(pool, content, reply, **_):
    """Detect corrections/teachings from Mev and store as semantic memory."""
    from ..gateway.classifiers import extract_lesson
    lesson = await extract_lesson(content, reply)
    if lesson:
        from ..embeddings import get_embedding
        embedding = await get_embedding(lesson["lesson"])
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
        await pool.execute(
            """INSERT INTO semantic_memories (content, category, confidence, embedding)
               VALUES ($1, $2, 0.85, $3::vector(1536))""",
            lesson["lesson"], lesson["category"], embedding_str,
        )
        log.info(f"Phase 5: lesson stored [{lesson['category']}]: {lesson['lesson'][:80]}...")


async def _hook_directive_extract(pool, channel, content, reply, **_):
    """Detect and persist directives from Mev."""
    from ..gateway.classifiers import extract_directive
    directive = await extract_directive(content, reply)
    if directive:
        await pool.execute(
            """INSERT INTO mission_directives (directive, priority, category, status, source)
               VALUES ($1, $2, $3, 'active', $4)""",
            directive["directive"], directive["priority"], directive["category"],
            f"auto-extracted from {channel}",
        )
        from ..embeddings import get_embedding
        dir_embedding = await get_embedding(f"Mev directive: {directive['directive']}")
        dir_embedding_str = "[" + ",".join(str(x) for x in dir_embedding) + "]"
        await pool.execute(
            """INSERT INTO semantic_memories (content, category, confidence, embedding, source)
               VALUES ($1, 'directive', 0.90, $2::vector(1536), $3)""",
            f"Mev directive ({directive['category']}): {directive['directive']}",
            dir_embedding_str,
            f"auto-extracted from {channel}",
        )
        log.info(f"Phase 5: directive stored [{directive['category']}]: {directive['directive'][:80]}...")


async def _hook_reactive_dispatch(pool, content, reply, channel, **_):
    """Auto-create task if Mev's message implies action."""
    await _reactive_dispatch(content, reply, channel, pool)


async def _hook_drift_measure(interrupt, **_):
    """Measure cognitive drift periodically."""
    from .smmu import get_smmu
    agent_id = interrupt.get("agent_id", "otto")
    smmu = get_smmu(agent_id)
    smmu.interrupts_since_sync += 1
    from ..config import settings
    if smmu.interrupts_since_sync % settings.drift_check_interval == 0:
        from .drift import measure_drift
        await measure_drift(agent_id=agent_id)


async def _hook_thought_vault_capture(pool, channel, content, interrupt, **_):
    """Auto-capture voice notes and long thought-dumps into Thought Vault.

    Criteria:
      - [Voice] prefix (transcribed voice note from Deepgram)
      - OR message length > 300 chars (substantial thought dump)
    """
    is_voice = content.startswith("[Voice]") or content.startswith("[voice]")
    is_long = len(content) > 300

    if not (is_voice or is_long):
        return

    source_message_id = str(interrupt.get("id", "")) or None

    try:
        await pool.execute(
            """INSERT INTO thought_vault
                   (source, source_message_id, raw_content, importance)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (source_message_id) DO NOTHING""",
            channel,
            source_message_id,
            content,
            7 if is_voice else 5,
        )
        log.info(
            f"Phase 5: thought-vault captured {'voice' if is_voice else 'long-text'} "
            f"({len(content)} chars) from {channel}"
        )
    except Exception as e:
        log.warning(f"Phase 5: thought-vault capture failed: {e}")


def setup_post_process_hooks():
    """Register all Phase 5 post-processing hooks. Called once at API startup."""
    from . import hooks

    # Group 1: Independent hooks — run concurrently
    hooks.register("message.post", _hook_episodic_log)
    hooks.register("message.post", _hook_persist_messages)
    hooks.register("message.post", _hook_graphiti_ingest)
    hooks.register("message.post", _hook_pending_match)
    hooks.register("message.post", _hook_proposal_match)

    # Group 2: Late hooks — run after group 1 completes
    # Lesson/directive extraction may benefit from persisted messages;
    # reactive dispatch and drift are independent but lower priority.
    hooks.register("message.post.late", _hook_lesson_extract)
    hooks.register("message.post.late", _hook_directive_extract)
    hooks.register("message.post.late", _hook_reactive_dispatch)
    hooks.register("message.post.late", _hook_drift_measure)
    hooks.register("message.post.late", _hook_thought_vault_capture)

    log.info(f"Phase 5 hooks registered: {hooks.list_hooks()}")


async def _gather_task_context(title: str, prompt: str) -> str:
    """Gather rich context for a task before it is inserted into the DB.

    Runs three queries concurrently:
    1. Semantic memory (A-RAG search, top 8)
    2. Knowledge graph (Graphiti search, top 5 facts)
    3. Filesystem — existing blog articles (content-creator tasks only)

    Returns a formatted context block (~2000 chars max) to append to the
    task prompt, or an empty string if all queries fail.
    """
    import httpx

    combined_lower = (title + " " + prompt).lower()
    is_content_task = any(
        kw in combined_lower
        for kw in (
            # Content types
            "article", "blog", "post", "write", "draft", "content", "copy",
            "essay", "manifesto", "whitepaper", "publish", "tagline", "slogan",
            "narrative", "story", "editorial", "newsletter", "announcement",
            "landing page", "brand", "voice", "tone", "messaging",
            # Ecosystem projects — any content for these is ecosystem content
            "my3ye", "tusita", "oneon", "otto", "ottolabs", "sos systems",
            "koink", "shakrah", "panik", "pipi", "inception",
            "otto music", "otto travel", "otto market", "otto properties",
        )
    )

    query = f"{title}: {prompt}"[:300]

    async def _fetch_semantic() -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    "http://localhost:8100/semantic/arag_search",
                    json={"query": query, "limit": 8},
                )
                if resp.status_code == 200:
                    return resp.json().get("results", [])
        except Exception as e:
            log.debug(f"Context gather — semantic search failed: {e}")
        return []

    async def _fetch_graph() -> list[dict]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    "http://localhost:8100/graph/search",
                    json={"query": title, "max_facts": 5},
                )
                if resp.status_code == 200:
                    return resp.json().get("facts", [])
        except Exception as e:
            log.debug(f"Context gather — graph search failed: {e}")
        return []

    async def _fetch_existing_content() -> list[dict]:
        """Query the unified content DB for existing pieces related to this task."""
        if not is_content_task:
            return []
        try:
            # Search content DB by title keyword (extract first meaningful word from title)
            search_term = title.split(":")[0].strip()[:40]
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "http://localhost:8100/content",
                    params={"search": search_term, "limit": 10},
                )
                if resp.status_code == 200:
                    return resp.json().get("items", [])
        except Exception as e:
            log.debug(f"Context gather — content DB query failed: {e}")
        return []

    semantic_results, graph_facts, existing_content = await asyncio.gather(
        _fetch_semantic(),
        _fetch_graph(),
        _fetch_existing_content(),
        return_exceptions=False,
    )

    # Build context string, budgeting ~2000 chars total
    parts: list[str] = []
    char_budget = 2000

    # Semantic memories
    if semantic_results:
        mem_lines = []
        for r in semantic_results:
            line = f"- [{r.get('category', '?')}] {r.get('content', '')}"
            mem_lines.append(line[:120])
        block = "## Relevant Memories\n" + "\n".join(mem_lines)
        if len(block) <= char_budget:
            parts.append(block)
            char_budget -= len(block)

    # Knowledge graph facts
    if graph_facts and char_budget > 100:
        fact_lines = []
        for f in graph_facts:
            fact_text = f.get("fact") or f.get("name") or str(f)
            fact_lines.append(f"- {fact_text}"[:120])
        block = "## Knowledge Graph\n" + "\n".join(fact_lines)
        if len(block) <= char_budget:
            parts.append(block)
            char_budget -= len(block)

    # Existing content from DB
    if existing_content and char_budget > 80:
        content_lines = []
        for c in existing_content:
            t = c.get("title", "?")
            ct = c.get("content_type", "?")
            st = c.get("status", "?")
            proj = c.get("project_id") or ""
            content_lines.append(f"- [{ct}/{st}] {t}" + (f" ({proj})" if proj else ""))
        block = "## Existing Content in DB (for reference/consistency)\n" + "\n".join(
            line[:120] for line in content_lines
        )
        if len(block) <= char_budget:
            parts.append(block)
            char_budget -= len(block)

    # Brand & ecosystem reference pointers (no file reads — keep it cheap)
    if is_content_task and char_budget > 100:
        parts.append(
            "## Brand & Ecosystem References\n"
            "- Read /mnt/media/projects/my3ye-web/BRAND.md for voice and tone guidelines\n"
            "- Read /mnt/media/projects/my3ye-web/content/blog/ for existing articles\n"
            "- Query /semantic/search with ecosystem project names for relevant context\n"
            "- All content must follow MY3YE voice: builder in the arena, calm authority, poetic but clear"
        )

    if not parts:
        return ""

    return "\n\n=== GATHERED CONTEXT ===\n\n" + "\n\n".join(parts) + "\n\n=== END CONTEXT ==="


async def _handle_stop_command(pool, channel: str) -> None:
    """Stop the most recently launched running task(s).

    Finds running tasks (most recent first), calls /tasks/{id}/stop logic
    inline, and notifies Mev.
    """
    import os, signal

    rows = await pool.fetch(
        """SELECT id, title, pid FROM tasks
           WHERE status = 'running'
           ORDER BY started_at DESC NULLS LAST""",
    )

    if not rows:
        log.info("Stop command received but no running tasks found")
        try:
            proc = await asyncio.create_subprocess_exec(
                "/home/web3relic/otto/tools/whatsapp_send.sh",
                "No running tasks to stop.",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        except Exception:
            pass
        return

    # Stop the most recently started task
    task = rows[0]
    task_id, title, pid = task["id"], task["title"], task["pid"]

    killed = False
    if pid:
        try:
            os.killpg(pid, signal.SIGTERM)
            killed = True
            log.info(f"Stop command: sent SIGTERM to pgid {pid} for task {task_id}")
        except ProcessLookupError:
            killed = True
            log.info(f"Stop command: process {pid} already dead for task {task_id}")
        except Exception as e:
            log.warning(f"Stop command: failed to kill PID {pid}: {e}")

    await pool.execute(
        """UPDATE tasks SET status = 'failed', pid = NULL,
               completed_at = now(), error = 'Stopped by admin', exit_code = -15
           WHERE id = $1""",
        task_id,
    )
    log.info(f"Stop command: task {task_id} ({title}) stopped (killed={killed})")

    try:
        notify = f"Stopped: {title}"
        if len(rows) > 1:
            notify += f"\n({len(rows) - 1} other task(s) still running)"
        proc = await asyncio.create_subprocess_exec(
            "/home/web3relic/otto/tools/whatsapp_send.sh", notify,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
    except Exception:
        pass


async def _reactive_dispatch(content: str, reply: str, channel: str, pool) -> None:
    """Reactive Dispatch: detect action in admin messages and auto-create tasks.

    Called from Phase 5 POST. Non-blocking, fire-and-forget.
    Classifies whether Mev's message requires Otto to take action, then
    creates a task (and optionally launches it for urgent requests).
    """
    from ..gateway.classifiers import classify_for_dispatch, classify_for_stop

    # ── Stop detection: kill running tasks if Mev says stop ──
    if await classify_for_stop(content):
        await _handle_stop_command(pool, channel)
        return

    dispatch = await classify_for_dispatch(content, reply)
    if not dispatch:
        return

    title = dispatch["task_title"]
    prompt = dispatch["task_prompt"]
    urgency = dispatch["urgency"]
    priority = dispatch["priority"]

    log.info(f"Reactive dispatch triggered: '{title}' (urgency={urgency}, P{priority})")

    # ── Workflow detection: start a pipeline instead of a single task ──
    workflow_template = dispatch.get("workflow_template")
    if workflow_template:
        try:
            tmpl = await pool.fetchval(
                "SELECT id FROM workflow_templates WHERE name = $1 AND NOT archived",
                workflow_template,
            )
            if tmpl:
                variables = dispatch.get("workflow_variables") or {}
                from ..routes.workflows import _advance_workflow
                inst_row = await pool.fetchrow(
                    """INSERT INTO workflow_instances
                       (template_id, name, variables, priority, working_directory,
                        trigger_source, trigger_message, created_by)
                       VALUES ($1, $2, $3::jsonb, $4, '/home/web3relic/otto',
                               'reactive_dispatch', $5, 'reactive_dispatch')
                       RETURNING id""",
                    tmpl, title,
                    __import__("json").dumps(variables),
                    priority, content[:500],
                )
                instance_id = inst_row["id"]
                asyncio.create_task(_advance_workflow(pool, instance_id))
                log.info(f"Reactive dispatch started workflow '{workflow_template}' (instance={instance_id})")

                # Notify Mev
                try:
                    notify_msg = f"Workflow started: {title}\nPipeline: {workflow_template}\nPriority: P{priority}"
                    proc = await asyncio.create_subprocess_exec(
                        "/home/web3relic/otto/tools/whatsapp_send.sh", notify_msg,
                        stdout=asyncio.subprocess.DEVNULL,
                        stderr=asyncio.subprocess.DEVNULL,
                    )
                    await asyncio.wait_for(proc.communicate(), timeout=10)
                except Exception:
                    pass
                return  # Don't create a standalone task
            else:
                log.info(f"Reactive dispatch: workflow template '{workflow_template}' not found, falling back to single task")
        except Exception as e:
            log.warning(f"Reactive dispatch workflow start failed (falling back to task): {e}")

    # Dedup — skip if a similar task exists (any status within last 2 hours)
    try:
        existing = await pool.fetchval(
            """SELECT COUNT(*) FROM tasks
               WHERE (status IN ('pending', 'running')
                      OR (status = 'completed' AND created_at > NOW() - INTERVAL '2 hours'))
               AND similarity(title, $1) > 0.4""",
            title,
        )
        if existing and existing > 0:
            log.info(f"Reactive dispatch skipped (duplicate): {title}")
            return
    except Exception as e:
        log.warning(f"Reactive dispatch dedup check failed (proceeding): {e}")

    # Enrich prompt with gathered context before DB insertion
    try:
        gathered = await _gather_task_context(title, prompt)
        if gathered:
            prompt = prompt + gathered
            log.info(f"Reactive dispatch enriched prompt with {len(gathered)} chars of context")
    except Exception as e:
        log.warning(f"Reactive dispatch context gather failed (proceeding without): {e}")

    # Scale budget/timeout by priority
    if priority >= 8:
        max_budget, max_turns, timeout = 10.0, 50, 1800
    elif priority >= 5:
        max_budget, max_turns, timeout = 5.0, 50, 900
    else:
        max_budget, max_turns, timeout = 3.0, 30, 600

    # Use agent_type from dispatch classifier
    agent_type = dispatch.get("agent_type", "coder")

    # Create task
    metadata = {
        "created_by_reactive_dispatch": True,
        "source_channel": channel,
        "source_message": content[:200],
        "urgency": urgency,
    }

    try:
        row = await pool.fetchrow(
            """INSERT INTO tasks (title, prompt, priority, model, cli,
                   max_budget_usd, max_turns, timeout_seconds, agent_type,
                   working_directory, created_by, metadata)
               VALUES ($1, $2, $3, 'sonnet', 'claude',
                   $5, $6, $7, $8,
                   '/home/web3relic/otto', 'reactive_dispatch', $4)
               RETURNING id, title""",
            title, prompt, priority, metadata,
            max_budget, max_turns, timeout, agent_type,
        )
        task_id = row["id"]
    except Exception as e:
        log.error(f"Reactive dispatch task creation failed: {e}")
        return

    log.info(f"Reactive dispatch created task {task_id}: {title}")

    # Auto-launch when slots available (reactive = Mev wants it now)
    launched = False
    if True:
        try:
            from ..routes.tasks import _count_running_by_cli, CLI_CONCURRENCY, TASK_RUNNER
            import os
            import subprocess

            cli_counts = await _count_running_by_cli(pool)
            claude_running = cli_counts.get("claude", 0)
            claude_limit = CLI_CONCURRENCY["claude"]

            if claude_running < claude_limit:
                task_env = os.environ.copy()
                task_env.pop("CLAUDECODE", None)
                task_env.setdefault("HOME", "/home/web3relic")
                task_env.setdefault("USER", "web3relic")
                task_env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"

                proc = subprocess.Popen(
                    [TASK_RUNNER, str(task_id)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    env=task_env,
                )
                await pool.execute(
                    """UPDATE tasks SET status = 'running', pid = $2, started_at = now()
                       WHERE id = $1""",
                    task_id, proc.pid,
                )
                launched = True
                log.info(f"Reactive dispatch auto-launched task {task_id} as PID {proc.pid}")
            else:
                log.info(f"Reactive dispatch: no claude slots for auto-launch ({claude_running}/{claude_limit})")
        except Exception as e:
            log.warning(f"Reactive dispatch auto-launch failed (task still queued): {e}")

    # Notify Mev via WhatsApp
    try:
        status_msg = "launched" if launched else "queued"
        notify_msg = f"Task {status_msg}: {title}\nPriority: P{priority} | Urgency: {urgency}"
        if not launched and urgency in ("high", "critical"):
            notify_msg += "\n(No claude slots — will run when a slot opens)"

        proc = await asyncio.create_subprocess_exec(
            "/home/web3relic/otto/tools/whatsapp_send.sh", notify_msg,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
    except Exception as e:
        log.warning(f"Reactive dispatch notification failed: {e}")

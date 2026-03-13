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
import time
from uuid import UUID

from ..db import get_pool
from .types import InterruptType
from . import ivt

log = logging.getLogger("otto.kernel.ric")


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

    system_prompt = _build_system_prompt(context_text, channel)

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
    messages.append({"role": "user", "content": content})

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


def _build_system_prompt(context_text: str, channel: str) -> str:
    """Build system prompt for conversational messages."""
    channel_voice = {
        "whatsapp": (
            "You're responding on WhatsApp. Keep it SHORT and conversational. "
            "No essays, no formal structure. 1-3 short paragraphs max. "
            "You can't directly access the filesystem from this channel, but if Mev "
            "asks you to build, create, fix, or research something, acknowledge it "
            "and confirm you're on it — a task will be automatically created and launched."
        ),
        "web": (
            "You're responding on the web interface. Conversational with more room. "
            "Short paragraphs, markdown OK. You can't directly access the filesystem, "
            "but action requests from Mev automatically create and launch tasks."
        ),
    }

    voice = channel_voice.get(channel, channel_voice["web"])

    return (
        f"You are Otto, a persistent AI entity. You're talking to Mev (your Admin).\n\n"
        f"=== CONTEXT ===\n{context_text}\n=== END CONTEXT ===\n\n"
        f"Channel guidelines: {voice}\n\n"
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

    system_prompt = _build_system_prompt(context_text, channel)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
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

    - Log episodic event
    - Persist messages
    - Graphiti entity extraction
    - Match/resolve pending questions
    - Measure drift
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
        content = payload.get("content", "")
        reply = result.get("content", "")
        channel = payload.get("channel", "whatsapp")
        sender_id = payload.get("sender_id", "")
        sender_name = payload.get("sender_name", "Mev")

        # Episodic event logging
        try:
            importance = 7 if channel == "whatsapp" else 6
            await pool.execute(
                """INSERT INTO episodic_events (content, event_type, importance, metadata)
                   VALUES ($1, $2, $3, $4)""",
                f"[{channel}] Mev: {content[:500]} | Otto: {reply[:500]}",
                "conversation",
                importance,
                {"channel": channel, "interrupt_id": str(interrupt["id"])},
            )
        except Exception as e:
            log.warning(f"Post-process episodic logging failed: {e}")

        # Message persistence (embeddings)
        try:
            from ..gateway.persistence import persist_messages
            await persist_messages(pool, channel, sender_id, sender_name, content, reply, None, None)
        except Exception as e:
            log.warning(f"Post-process message persistence failed: {e}")

        # Graphiti ingestion
        try:
            from ..gateway.persistence import ingest_to_graph
            await ingest_to_graph(channel, content, reply)
        except Exception as e:
            log.warning(f"Post-process graph ingestion failed: {e}")

        # Pending question matching
        try:
            from ..gateway.classifiers import match_pending_question
            from ..gateway.persistence import get_pending_questions, resolve_and_store
            pending = await get_pending_questions(pool)
            match = await match_pending_question(content, pending)
            if match:
                await resolve_and_store(pool, match["question"], match["extracted_answer"])
        except Exception as e:
            log.warning(f"Post-process pending matching failed: {e}")

        # Decision proposal matching
        try:
            from ..gateway.persistence import get_open_proposals, match_and_resolve_proposal
            proposals = await get_open_proposals(pool)
            await match_and_resolve_proposal(pool, content, proposals)
        except Exception as e:
            log.warning(f"Post-process proposal matching failed: {e}")

        # Lesson extraction — detect corrections, teachings, operational knowledge
        try:
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
        except Exception as e:
            log.warning(f"Post-process lesson extraction failed: {e}")

        # Directive extraction — detect and persist directives from Mev
        try:
            from ..gateway.classifiers import extract_directive
            directive = await extract_directive(content, reply)
            if directive:
                # Store in mission_directives table
                await pool.execute(
                    """INSERT INTO mission_directives (directive, priority, category, status, source)
                       VALUES ($1, $2, $3, 'active', $4)""",
                    directive["directive"], directive["priority"], directive["category"],
                    f"auto-extracted from {channel}",
                )
                # Also store as semantic memory for retrieval
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
        except Exception as e:
            log.warning(f"Post-process directive extraction failed: {e}")

        # Reactive dispatch — auto-create task if Mev's message implies action
        try:
            log.info(f"Phase 5: running reactive dispatch classifier")
            await _reactive_dispatch(content, reply, channel, pool)
            log.info(f"Phase 5: reactive dispatch complete")
        except Exception as e:
            log.warning(f"Post-process reactive dispatch failed: {e}")

        # Drift measurement (every N interrupts)
        try:
            from .smmu import get_smmu
            agent_id = interrupt.get("agent_id", "otto")
            smmu = get_smmu(agent_id)
            smmu.interrupts_since_sync += 1
            from ..config import settings
            if smmu.interrupts_since_sync % settings.drift_check_interval == 0:
                from .drift import measure_drift
                await measure_drift(agent_id=agent_id)
        except Exception as e:
            log.warning(f"Post-process drift measurement failed: {e}")

    except Exception as e:
        log.error(f"Post-processing failed: {e}", exc_info=True)


async def _reactive_dispatch(content: str, reply: str, channel: str, pool) -> None:
    """Reactive Dispatch: detect action in admin messages and auto-create tasks.

    Called from Phase 5 POST. Non-blocking, fire-and-forget.
    Classifies whether Mev's message requires Otto to take action, then
    creates a task (and optionally launches it for urgent requests).
    """
    from ..gateway.classifiers import classify_for_dispatch

    dispatch = await classify_for_dispatch(content, reply)
    if not dispatch:
        return

    title = dispatch["task_title"]
    prompt = dispatch["task_prompt"]
    urgency = dispatch["urgency"]
    priority = dispatch["priority"]

    log.info(f"Reactive dispatch triggered: '{title}' (urgency={urgency}, P{priority})")

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
                   max_budget_usd, max_turns, timeout_seconds,
                   working_directory, created_by, metadata)
               VALUES ($1, $2, $3, 'sonnet', 'claude',
                   5.00, 50, 600,
                   '/home/web3relic/otto', 'reactive_dispatch', $4)
               RETURNING id, title""",
            title, prompt, priority, metadata,
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

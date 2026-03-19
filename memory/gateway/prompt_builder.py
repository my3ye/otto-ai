"""Channel-aware prompt construction for Otto's LLM responses.

Used by the legacy (non-kernel) handler path. In kernel mode, the RIC
builds prompts directly in kernel/ric.py.
"""

import logging

from ..graphiti import graphiti_search
from ..context_builder import build_context_text

log = logging.getLogger("otto.gateway.prompt_builder")

# Channel-specific voice guidelines
CHANNEL_VOICE = {
    "whatsapp": (
        "- WhatsApp style: short messages, no essays. Like texting a partner, not writing a report.\n"
        "- You are responding in real-time via the gateway LLM. For filesystem operations, tasks, "
        "or anything requiring code execution, acknowledge the request and note it will be handled "
        "by the heartbeat or task queue. NEVER say \"applying now\" or \"writing to .env\" in this context."
    ),
    "web": (
        "- Web chat: slightly more room to elaborate, but stay conversational.\n"
        "- Use short paragraphs. Markdown formatting is OK for code or lists.\n"
        "- For filesystem or code execution tasks, note they will be handled by the task queue."
    ),
}


async def build_otto_prompt(
    pool,
    message: str,
    channel: str,
    pending_questions: list,
    recent_events: list[str],
    claude_response: str | None = None,
) -> list[dict]:
    """Build Otto's system prompt using the unified context layer.

    Channel-aware: adjusts voice guidelines and context budget per channel.
    """
    source = channel if channel in ("whatsapp",) else "web"
    max_tokens = 4000 if channel == "whatsapp" else 6000

    # Unified context — same tiers as Claude, filtered by source
    otto_context = await build_context_text(pool, max_tokens=max_tokens, source=source)

    # Message-specific graph search
    msg_facts = await graphiti_search(message, max_facts=6)
    current_msg_facts = [f for f in msg_facts if f.get("invalid_at") is None]
    msg_graph_section = ""
    if current_msg_facts:
        facts_text = "\n".join(f"- {f['fact']}" for f in current_msg_facts)
        msg_graph_section = f"\n\n## Relevant Context for This Message\n{facts_text}"

    # Pending questions
    pending_section = ""
    if pending_questions:
        pq_lines = [f"- [{q['intent'].upper()}] \"{q['question']}\"" for q in pending_questions]
        pending_section = f"""

## Pending Questions You Asked Mev
You recently asked Mev these questions and are waiting for answers. Mev's current message may be a reply to one of these:
{chr(10).join(pq_lines)}

IMPORTANT: If Mev's message is clearly a reply to one of your pending questions, acknowledge it naturally and confirm you understood. Extract the key actionable content from their answer."""

    # Claude CLI response (when delegation was triggered in legacy path)
    claude_section = ""
    if claude_response:
        claude_section = f"""

## From Claude CLI
The Claude CLI read the relevant files and provided this analysis. Use this to answer Mev's question:
{claude_response}"""

    voice = CHANNEL_VOICE.get(channel, CHANNEL_VOICE["web"])

    system = f"""You are Otto, a persistent AI entity. You are responding via {channel} to Admin (Mev).

## Your System Context
{otto_context}{msg_graph_section}{pending_section}{claude_section}

## Voice Guidelines
Your persona and voice are defined in your system context above (the "persona" slot). Embody that voice fully.
{voice}
- Address Admin as "Mev". Never "sir", "master", "user", or "human".
- Never pretend to be human.
- IMPORTANT: Keep responses under 1000 tokens. If a topic needs more, summarize and offer to continue. Never let a message get cut off mid-sentence — always finish your thought cleanly."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": message},
    ]

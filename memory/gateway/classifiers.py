"""LLM-based classifiers for the gateway pipeline.

Extracted from whatsapp.py — all channel-agnostic.

Note: needs_claude_help() and delegate_to_claude() are legacy functions
from the pre-kernel architecture. They remain for backward compatibility
when kernel_enabled=False but are not used in the kernel path.
"""

import asyncio
import json
import logging

from ..llm import llm_chat, extract_json, provider_chat

log = logging.getLogger("otto.gateway.classifiers")

CLAUDE_CLI = "/home/web3relic/.local/bin/claude"
CLAUDE_TIMEOUT = 60


async def needs_claude_help(user_message: str, recent_events: list[str]) -> dict | None:
    """[Legacy] Determine if a message needs filesystem access via Claude CLI.

    Deprecated: In the kernel architecture, the reasoning kernel handles
    all message processing directly. This is only used in legacy fallback.

    Returns {"task": str, "file_paths": list, "question": str} if delegation needed.
    """
    events_context = "\n".join(f"- {e}" for e in recent_events[:10])

    system_msg = """You determine if a user message requires reading files or accessing the filesystem.

Recent events show what files/artifacts have been created recently.

Determine if the user is asking about:
- A file that was recently created (proposal, document, code, plan, config)
- Code analysis, review, or explanation
- System state that requires reading files to answer
- Anything where the answer lives in a file on disk

Return ONLY valid JSON (no markdown, no code fences):
{"needs_claude": true/false, "task": "brief description of what to do", "file_paths": ["path1"] or [], "question": "the specific question"}

If needs_claude is false, set other fields to null."""
    user_msg = f"Recent events (may contain file paths):\n{events_context}\n\nUser message: {user_message}"
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]

    try:
        response = await llm_chat(messages, max_tokens=300)
        parsed = extract_json(response)
        if parsed and parsed.get("needs_claude"):
            return {
                "task": parsed.get("task", ""),
                "file_paths": parsed.get("file_paths", []),
                "question": parsed.get("question", user_message),
            }
    except Exception as e:
        log.warning(f"Claude delegation classifier error: {e}")

    return None


async def delegate_to_claude(task: str, file_paths: list[str], question: str) -> str | None:
    """[Legacy] Delegate a task to Claude via the CLI. Returns Claude's response or None on failure."""
    prompt_parts = ["You are Otto. Help with this task that requires filesystem access."]
    prompt_parts.append(f"Task: {task}")
    if file_paths:
        prompt_parts.append(f"Read these files: {', '.join(file_paths)}")
    prompt_parts.append(f"Question from Mev: {question}")
    prompt_parts.append("Provide a concise, clear response. Keep it under 400 words. No markdown headers — just clean text.")

    prompt = "\n".join(prompt_parts)

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI, "-p", "--model", "haiku", "--max-turns", "3",
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


async def match_pending_question(message: str, pending_questions: list) -> dict | None:
    """Determine if this message answers a pending question.
    Uses LLM for smart matching, then simple heuristic fallback."""
    if not pending_questions:
        return None

    questions_json = json.dumps([
        {"id": str(q["id"]), "question": q["question"], "intent": q["intent"]}
        for q in pending_questions
    ])

    system_msg = """You determine if a user message answers or relates to a pending question.
Return ONLY valid JSON (no markdown, no code fences): {"matched_id": "<question id>" or null, "extracted_answer": "<the actionable answer>" or null}
Be generous in matching — if the message is clearly related to the topic of a pending question, it counts as an answer.
If the message clearly answers one of the pending questions, extract the core answer. If not, return nulls."""
    user_msg = f"Pending questions:\n{questions_json}\n\nUser message:\n{message}"
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]

    def _check_match(parsed):
        if parsed and parsed.get("matched_id"):
            for q in pending_questions:
                if str(q["id"]) == parsed["matched_id"]:
                    return {"question": q, "extracted_answer": parsed.get("extracted_answer", message)}
        return None

    try:
        response = await llm_chat(messages, max_tokens=200)
        parsed = extract_json(response)
        result = _check_match(parsed)
        if result:
            return result
    except Exception as e:
        log.warning(f"Pending question matcher error: {e}")

    # Fallback: if there's exactly one pending question and the message is
    # substantive (>20 chars), assume it's a reply
    if len(pending_questions) == 1 and len(message) > 20:
        return {"question": pending_questions[0], "extracted_answer": message}

    return None


async def classify_for_heartbeat(user_message: str, otto_reply: str) -> dict | None:
    """[Legacy] Classify whether a conversation contains directives for the heartbeat.

    Used in the legacy (non-kernel) path to detect directives, tasks, and decisions
    from Mev's messages that should be persisted for the heartbeat agent.

    Returns {"note_type": str, "urgency": str, "content": str, "source_summary": str}
    if flagged, or None if nothing to relay.
    """
    system_msg = """You classify conversations between Mev (admin) and Otto (AI agent).
Determine if Mev said anything that should be persisted as a directive, task, or decision.

ALWAYS FLAG these (err on the side of flagging):
- Mission statements ("Otto will be...", "our mission is...", "the goal is...")
- Directives/instructions ("focus on X", "stop doing Y", "I want you to...", "build X", "research Y")
- Goals/deadlines ("launch by March", "finish X this week", "go live in a week")
- Decisions ("let's go with option A", "use React for this", "start with X")
- Priority changes ("pause X, focus on Y", "pivot to...", "stop doing X")
- Tasks ("research X", "build me Y", "set up Z", "create X", "improve Y")
- Important brand/product/project context
- CRITICAL: Credentials, API keys, tokens, passwords — include EXACT values
- Approvals or go-aheads for pending actions ("yes do it", "approved", "go ahead", "sounds good")
- Self-improvement directives ("build yourself up", "improve yourself", "find research")
- Strategic direction (anything about what Otto should become, how to evolve)
- Descriptions of characters, products, features, or things to create

DO NOT FLAG these:
- Casual chat, greetings, banter with NO substance
- Pure acknowledgments with no directive ("ok", "cool", "thanks")
- Questions already answered AND that have no action component
- Pure small talk

IMPORTANT: When in doubt, FLAG IT. It's better to persist a directive unnecessarily than to miss one from Mev.

For note_type, use "mission" for purpose-level statements about what Otto is or should become.
When Mev describes something to build/create, classify as "task" not "context".

Return ONLY valid JSON (no markdown, no code fences):
{"flag": true/false, "note_type": "mission|directive|task|goal|decision|context|priority_change|approval", "urgency": "normal|high|critical", "content": "concise summary — preserve Mev's exact words for mission/directive types", "source_summary": "brief context"}

If flag is false, still include the other fields as null."""
    user_msg = f"Mev said: {user_message}\n\nOtto replied: {otto_reply}"
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]

    def _extract_result(parsed):
        if parsed and parsed.get("flag"):
            return {
                "note_type": parsed.get("note_type", "context"),
                "urgency": parsed.get("urgency", "normal"),
                "content": parsed.get("content", user_message),
                "source_summary": parsed.get("source_summary"),
            }
        return None

    try:
        response = await llm_chat(messages, max_tokens=300)
        parsed = extract_json(response)
        return _extract_result(parsed)
    except Exception as e:
        log.warning(f"Directive classifier error: {e}")

    return None


_DISPATCH_SYSTEM = """You classify whether a conversation between Mev (admin) and Otto (AI agent) requires Otto to take ACTION — meaning Otto needs to create and run a task (write code, build something, research something, fix something, set something up).

DISPATCH (action_needed=true) when Mev:
- Asks Otto to BUILD, CREATE, or IMPLEMENT something
- Asks Otto to RESEARCH or INVESTIGATE something
- Asks Otto to FIX or DEBUG something
- Asks Otto to SET UP or CONFIGURE something
- Asks Otto to WRITE or UPDATE code/docs
- Gives a directive that implies work ("we need X", "let's add Y", "start working on Z")
- Approves a previously proposed action that requires execution ("yes do it", "go ahead", "approved")

IMPORTANT: Otto's conversational reply CANNOT actually perform actions — it can only talk.
If Mev asks Otto to BUILD, RESEARCH, FIX, CREATE, WRITE, REWRITE, or DO anything, it MUST be dispatched
as a task regardless of what Otto says in the reply. Otto saying "on it", "I'll handle it",
or even drafting content/code in the reply is just conversational — the actual work requires
a task to be created. IGNORE Otto's reply when deciding — focus ONLY on Mev's message.
If Mev's message contains an action request, action_needed MUST be true.

DO NOT DISPATCH when:
- Casual conversation, greetings, banter
- Questions that Otto already answered with factual information (not action)
- Status checks ("how's X going?") unless they imply new work
- Pure acknowledgments ("ok", "cool", "thanks", "got it")
- Mev is just providing context or information with no action implied

For agent_type, pick the most appropriate specialist based on the nature of the work:
- "content-creator" — writing ANY content: articles, blog posts, copy, manifestos, taglines, landing page text, whitepapers, newsletters, announcements, brand messaging, storytelling, or any written content for the MY3YE ecosystem (MY3YE, TUSITA, ONEON, OTTO, OTTOLABS, KOINK, SHAKRAH, PANIK, PIPI, etc.)
- "researcher" — research, investigation, finding information, exploration
- "coder" — writing code, building features, implementing, setting up
- "debugger" — fixing bugs, debugging errors, diagnosing failures
- "architect" — system design, architecture decisions, planning implementations
- "reviewer" — code review, PR review, quality checks
- "memory-curator" — memory organization, knowledge management
- "landing-page" — building landing pages, web design
- "security-audit" — security review, vulnerability assessment
Default to "coder" if unclear.

WORKFLOW DETECTION: If the request clearly involves multi-step work that would benefit from
a pipeline (draft→review→revise→implement, or design→build→review→fix), also return:
- "workflow_template": name of the matching template (one of: "content-publishing-pipeline", "feature-development", "social-content-pipeline", "research-pipeline"), or null
- "workflow_variables": dict of variables for the template (e.g. {"topic": "...", "content_type": "...", "requirements": "..."})

Use "content-publishing-pipeline" for: writing articles, blog posts, landing page copy, content rewrites, any content that should be reviewed before publishing.
Use "feature-development" for: building features, implementing systems, code changes that should be architected and reviewed.
Use "social-content-pipeline" for: creating social media posts, X/Twitter content, social calendars, posting schedules, content plans for social platforms. Variables: {platform, account, brand, objective, timeframe, audience, requirements, character}.
Use "research-pipeline" for: deep research investigations, market research, competitive analysis, technical investigation requiring synthesis + validation + storage. Variables: {topic, scope, requirements, research_depth}. research_depth: "surface" (web only), "standard" (web + memory), "deep" (all sources + papers).
Use null (no workflow) for: simple fixes, quick lookups, small config changes, one-off tasks.

Return ONLY valid JSON (no markdown, no code fences):
{"action_needed": true/false, "task_title": "<imperative title, max 80 chars>", "task_prompt": "<detailed task prompt, 100-400 chars>", "urgency": "normal|high|critical", "priority": <5-9>, "agent_type": "<one of the types above>", "workflow_template": "<template name or null>", "workflow_variables": {<variables or null>}}

If action_needed is false, set other fields to null.
Keep task_prompt actionable and specific — this will be the prompt given to a Claude Code session."""


async def classify_for_dispatch(user_message: str, otto_reply: str) -> dict | None:
    """Classify whether an admin message requires Otto to take action.

    Lightweight classifier run in Phase 5 POST to enable reactive task creation.
    Returns action spec if task creation is needed, None otherwise.
    """
    user_msg = f"Mev said: {user_message[:500]}\n\nOtto replied: {otto_reply[:500]}"
    log.info(f"Dispatch classifier input ({len(user_msg)} chars): {user_msg[:200]}")
    messages = [
        {"role": "system", "content": _DISPATCH_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        response = await provider_chat(messages, max_tokens=350, temperature=0.0)
        log.info(f"Dispatch classifier raw response: {response[:300] if response else 'EMPTY'}")
        parsed = extract_json(response)
        log.info(f"Dispatch classifier parsed: {parsed}")
        if parsed and parsed.get("action_needed"):
            return {
                "task_title": str(parsed.get("task_title", ""))[:80],
                "task_prompt": str(parsed.get("task_prompt", ""))[:2000],
                "urgency": parsed.get("urgency", "normal"),
                "priority": min(max(int(parsed.get("priority", 5)), 1), 10),
                "agent_type": parsed.get("agent_type", "coder"),
                "workflow_template": parsed.get("workflow_template"),
                "workflow_variables": parsed.get("workflow_variables"),
            }
        else:
            log.info(f"Dispatch classifier: no action needed")
    except Exception as e:
        log.warning(f"Reactive dispatch classifier error: {e}")

    return None


_LESSON_SYSTEM = """You analyze conversations between Mev (admin) and Otto (AI agent) to extract LESSONS that Otto must remember permanently.

EXTRACT A LESSON when Mev:
- CORRECTS a mistake ("that's the wrong X", "use Y not Z", "it failed because...")
- Teaches a process or rule ("always do X before Y", "X requires Y")
- Gives operational knowledge ("that account is for X", "deploy with Y")
- States a preference or convention ("I want X format", "we use Y for Z", "don't ever do X")
- Explains WHY something failed and how to prevent it
- Provides credentials, API keys, config values, account info

DO NOT EXTRACT when:
- Casual conversation, greetings, banter
- One-off task requests (those go through dispatch, not lessons)
- Information Otto already demonstrates knowing in the reply
- Pure questions from Mev with no teaching component

CRITICAL RULES for the lesson content:
- Make it GENERAL, not specific to one instance. Extract the underlying principle.
- Include the WHY — not just what to do, but why it matters.
- Preserve exact values (account names, emails, paths, credentials).
- Keep it concise but complete — this will be stored as a permanent memory.

Return ONLY valid JSON (no markdown, no code fences):
{"has_lesson": true/false, "lesson": "<the operational lesson to remember>", "category": "procedure|decision|directive|credential|convention"}

If has_lesson is false, set other fields to null."""


async def extract_lesson(user_message: str, otto_reply: str) -> dict | None:
    """Extract operational lessons from admin messages.

    Detects corrections, teachings, and operational knowledge from Mev
    and returns them for storage in semantic memory.
    """
    user_msg = f"Mev said: {user_message[:500]}\n\nOtto replied: {otto_reply[:500]}"
    messages = [
        {"role": "system", "content": _LESSON_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        response = await provider_chat(messages, max_tokens=200, temperature=0.0)
        parsed = extract_json(response)
        if parsed and parsed.get("has_lesson"):
            lesson = str(parsed.get("lesson", "")).strip()
            category = parsed.get("category", "decision")
            if lesson:
                log.info(f"Lesson extracted [{category}]: {lesson[:100]}...")
                return {"lesson": lesson, "category": category}
        else:
            log.info("Lesson extractor: no lesson found")
    except Exception as e:
        log.warning(f"Lesson extraction error: {e}")

    return None


_DIRECTIVE_SYSTEM = """You analyze conversations between Mev (admin) and Otto (AI agent) to extract DIRECTIVES — strategic commands that shape Otto's mission, priorities, and behavior.

EXTRACT A DIRECTIVE when Mev:
- States a MISSION ("our mission is...", "Otto will be...", "what we're building is...")
- Changes PRIORITIES ("focus on X", "stop doing Y", "pivot to...", "pause X")
- Sets STRATEGIC DIRECTION ("we need to...", "the plan is...", "the strategy is...")
- Gives OPERATIONAL ORDERS ("always do X", "never do Y", "from now on...", "make sure to...")
- Sets BUDGET/RESOURCE constraints ("limit spending to...", "use X model for...", "cap at...")

DO NOT EXTRACT when:
- Casual conversation, greetings, banter
- One-off task requests ("build me X", "fix Y") — those go to dispatch, not directives
- Pure questions from Mev with no directive component
- Information or context with no imperative/command element

PRIORITY GUIDE:
- 10: Mission-level ("Otto's purpose is...", "our mission is...")
- 8-9: Strategic direction ("we're pivoting to...", "the plan going forward is...")
- 6-7: Operational orders ("always do X", "from now on...", "never do Y")
- 5-6: Priority changes ("focus more on X", "deprioritize Y")

Return ONLY valid JSON (no markdown, no code fences):
{"has_directive": true/false, "directive": "<the directive text>", "priority": <5-10>, "category": "mission|strategic|operational|priority_change"}

If has_directive is false, set other fields to null."""


async def extract_directive(user_message: str, otto_reply: str) -> dict | None:
    """Extract directives from admin messages.

    Detects mission statements, priority changes, strategic direction,
    and operational orders from Mev and returns them for storage
    in the mission_directives table and semantic memory.
    """
    user_msg = f"Mev said: {user_message[:500]}\n\nOtto replied: {otto_reply[:500]}"
    messages = [
        {"role": "system", "content": _DIRECTIVE_SYSTEM},
        {"role": "user", "content": user_msg},
    ]

    try:
        response = await provider_chat(messages, max_tokens=200, temperature=0.0)
        parsed = extract_json(response)
        if parsed and parsed.get("has_directive"):
            directive = str(parsed.get("directive", "")).strip()
            priority = min(max(int(parsed.get("priority", 7)), 5), 10)
            category = parsed.get("category", "operational")
            if directive:
                log.info(f"Directive extracted [{category}, P{priority}]: {directive[:100]}...")
                return {"directive": directive, "priority": priority, "category": category}
        else:
            log.info("Directive extractor: no directive found")
    except Exception as e:
        log.warning(f"Directive extraction error: {e}")

    return None

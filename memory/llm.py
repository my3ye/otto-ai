"""Shared LLM client for Otto's memory API.

Centralizes all LLM access: Kimi (primary) with Claude Haiku CLI fallback.
All routes should use this instead of direct google.generativeai or openai calls.
"""

import asyncio
import json
import logging

from openai import AsyncOpenAI

from .config import settings

log = logging.getLogger("otto.llm")

CLAUDE_CLI = "/home/web3relic/.local/bin/claude"
CLAUDE_TIMEOUT = 60


def get_llm_client() -> AsyncOpenAI:
    """Return an AsyncOpenAI client pointed at Kimi."""
    return AsyncOpenAI(
        api_key=settings.kimi_api_key,
        base_url=settings.kimi_base_url,
        default_headers={"User-Agent": "claude-code/1.0"},
    )


async def llm_chat(
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.0,
    model: str | None = None,
    system_instruction: str | None = None,
) -> str:
    """Call Kimi (primary) with Claude Haiku CLI fallback.

    Args:
        messages: OpenAI-format messages list.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.
        model: Override model name (defaults to settings.kimi_model).
        system_instruction: If provided, prepended as a system message
            (convenience for callers migrating from genai SDK which used
            system_instruction as a GenerativeModel param).

    Returns:
        LLM response text. Empty string if all backends fail.
    """
    model = model or settings.kimi_model

    # If system_instruction provided, prepend as system message
    if system_instruction:
        messages = [{"role": "system", "content": system_instruction}] + messages

    # Primary: Kimi
    try:
        client = get_llm_client()
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = completion.choices[0].message.content or ""
        if text:
            return text
        log.warning("Kimi returned empty response")
    except Exception as e:
        log.warning(f"Kimi LLM call failed: {e}")

    # Fallback 2: OpenAI (gpt-4o-mini — cheap, reliable)
    if settings.openai_api_key:
        try:
            openai_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
            )
            completion = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            text = completion.choices[0].message.content or ""
            if text:
                log.info("OpenAI fallback succeeded")
                return text
            log.warning("OpenAI returned empty response")
        except Exception as e:
            log.warning(f"OpenAI fallback failed: {e}")

    # Fallback 3: Claude Haiku via CLI
    return await _claude_chat(messages, max_tokens=max_tokens)


async def _claude_chat(
    messages: list[dict],
    max_tokens: int = 500,
) -> str:
    """Call Claude Haiku via CLI as fallback.

    Converts OpenAI-style messages to a single prompt for the Claude CLI.
    """
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"<system>\n{content}\n</system>")
        else:
            parts.append(content)
    prompt = "\n\n".join(parts)

    try:
        proc = await asyncio.create_subprocess_exec(
            CLAUDE_CLI, "-p", "--model", "haiku", "--max-turns", "1",
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
        log.warning(f"Claude chat fallback returned code {proc.returncode}: {stderr.decode()[:200]}")
    except asyncio.TimeoutError:
        log.warning("Claude chat fallback timed out")
        try:
            proc.kill()
        except Exception:
            pass
    except Exception as e:
        log.warning(f"Claude chat fallback error: {e}")

    return ""


async def provider_chat(
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.0,
    model: str | None = None,
    system_instruction: str | None = None,
    preferred_provider: str | None = None,
) -> str:
    """Call LLM through the AgentOS provider registry with automatic fallback.

    This is the kernel-aware version of llm_chat(). Falls through providers
    in priority order from the llm_providers DB table.

    When the kernel is not initialized, falls back to llm_chat().
    """
    try:
        from .kernel.provider import provider_chat as _provider_chat
        return await _provider_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            system_instruction=system_instruction,
            preferred_provider=preferred_provider,
        )
    except Exception as e:
        log.warning(f"provider_chat failed, falling back to llm_chat: {e}")
        return await llm_chat(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
            system_instruction=system_instruction,
        )


def strip_json_fences(text: str) -> str:
    """Strip markdown code fences from JSON responses."""
    text = text.strip()
    for prefix in ("```json", "```"):
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    return text.rstrip("`").strip()


def extract_json(text: str) -> dict | None:
    """Robustly extract and parse a JSON object from LLM output.

    Handles markdown code fences, extra text, partial/truncated JSON.
    """
    text = strip_json_fences(text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        return None

    end = text.rfind("}")
    if end == -1 or end < start:
        return None

    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        pass

    for i in range(end, start, -1):
        if text[i] == "}":
            try:
                return json.loads(text[start:i + 1])
            except json.JSONDecodeError:
                continue

    return None


def extract_json_array(text: str) -> list | None:
    """Robustly extract and parse a JSON array from LLM output."""
    text = strip_json_fences(text)

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    if start == -1:
        return None

    end = text.rfind("]")
    if end == -1 or end < start:
        return None

    try:
        result = json.loads(text[start:end + 1])
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    return None

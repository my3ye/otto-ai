"""LLM Provider Registry — pluggable backends with automatic fallback.

Reads provider configuration from the llm_providers DB table.
Falls back through providers in priority order (lowest number = most preferred).

Preserves backward compatibility: existing llm_chat() keeps working.
New code can use provider_chat() for richer control.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field

from openai import AsyncOpenAI

from ..config import settings

log = logging.getLogger("otto.kernel.provider")

CLAUDE_CLI = "/home/web3relic/.local/bin/claude"
CLAUDE_TIMEOUT = 60
CLAUDE_CODE_TIMEOUT = 90


@dataclass
class ProviderConfig:
    """Runtime provider configuration loaded from DB or defaults."""
    name: str
    provider_type: str  # openai_compatible, claude_code_stream, claude_cli
    base_url: str | None = None
    model_name: str = ""
    api_key_env: str | None = None
    priority: int = 5
    max_tokens: int = 4096
    temperature: float = 0.0
    enabled: bool = True
    metadata: dict = field(default_factory=dict)


# ── In-memory provider cache ─────────────────────────────────────────────────

_providers: list[ProviderConfig] = []
_providers_loaded: bool = False


async def load_providers(pool) -> list[ProviderConfig]:
    """Load enabled providers from DB, sorted by priority (ascending)."""
    global _providers, _providers_loaded

    rows = await pool.fetch(
        """SELECT name, provider_type, base_url, model_name, api_key_env,
                  priority, max_tokens, temperature, enabled, metadata
           FROM llm_providers
           WHERE enabled = TRUE
           ORDER BY priority ASC"""
    )

    _providers = [
        ProviderConfig(
            name=r["name"],
            provider_type=r["provider_type"],
            base_url=r["base_url"],
            model_name=r["model_name"],
            api_key_env=r["api_key_env"],
            priority=r["priority"],
            max_tokens=r["max_tokens"] or 4096,
            temperature=r["temperature"] or 0.0,
            enabled=r["enabled"],
            metadata=r["metadata"] or {},
        )
        for r in rows
    ]
    _providers_loaded = True

    if not _providers:
        # Fallback: use hardcoded Kimi + Claude defaults
        log.warning("No providers in DB, using hardcoded defaults")
        _providers = _default_providers()

    log.info(f"Loaded {len(_providers)} LLM providers: {[p.name for p in _providers]}")
    return _providers


def _default_providers() -> list[ProviderConfig]:
    """Hardcoded fallback when DB table is empty or unavailable."""
    return [
        ProviderConfig(
            name="claude_code_sonnet",
            provider_type="claude_code_stream",
            model_name="sonnet",
            priority=0,
            max_tokens=4096,
            temperature=0.7,
        ),
        ProviderConfig(
            name="kimi",
            provider_type="openai_compatible",
            base_url=settings.kimi_base_url,
            model_name=settings.kimi_model,
            api_key_env="KIMI_API_KEY",
            priority=1,
            max_tokens=4096,
        ),
        ProviderConfig(
            name="claude_haiku",
            provider_type="claude_cli",
            model_name="haiku",
            priority=5,
            max_tokens=4096,
        ),
    ]


def get_providers() -> list[ProviderConfig]:
    """Return cached providers, or defaults if not yet loaded."""
    if not _providers_loaded or not _providers:
        return _default_providers()
    return _providers


def get_provider_by_name(name: str) -> ProviderConfig | None:
    """Get a specific provider by name."""
    for p in get_providers():
        if p.name == name:
            return p
    return None


# ── Provider call implementations ────────────────────────────────────────────

def _resolve_api_key(provider: ProviderConfig) -> str:
    """Resolve API key from environment variable name."""
    import os
    if provider.api_key_env:
        key = os.environ.get(provider.api_key_env, "")
        if key:
            return key
    # Fallback to settings
    if "kimi" in provider.name.lower():
        return settings.kimi_api_key
    return ""


async def _call_openai_compatible(
    provider: ProviderConfig,
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    """Call an OpenAI-compatible API (Kimi, OpenRouter, etc.)."""
    api_key = _resolve_api_key(provider)
    base_url = provider.base_url or settings.kimi_base_url
    model_name = model or provider.model_name

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={"User-Agent": "claude-code/1.0"},
    )

    completion = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens or provider.max_tokens,
        temperature=temperature if temperature is not None else provider.temperature,
    )
    return completion.choices[0].message.content or ""


async def _stream_openai_compatible(
    provider: ProviderConfig,
    messages: list[dict],
    max_tokens: int | None = None,
    temperature: float | None = None,
    model: str | None = None,
):
    """Stream from an OpenAI-compatible API. Yields text chunks."""
    api_key = _resolve_api_key(provider)
    base_url = provider.base_url or settings.kimi_base_url
    model_name = model or provider.model_name

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        default_headers={"User-Agent": "claude-code/1.0"},
    )

    stream = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=max_tokens or provider.max_tokens,
        temperature=temperature if temperature is not None else provider.temperature,
        stream=True,
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def _call_claude_cli(
    provider: ProviderConfig,
    messages: list[dict],
    max_tokens: int | None = None,
) -> str:
    """Call Claude via CLI as fallback."""
    parts = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            parts.append(f"<system>\n{content}\n</system>")
        else:
            parts.append(content)
    prompt = "\n\n".join(parts)

    model = provider.model_name or "haiku"

    proc = await asyncio.create_subprocess_exec(
        CLAUDE_CLI, "-p", "--model", model, "--max-turns", "1",
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
    log.warning(f"Claude CLI ({model}) returned code {proc.returncode}: {stderr.decode()[:200]}")
    return ""


# ── Claude Code stream provider ─────────────────────────────────────────────

def _build_claude_code_env() -> dict:
    """Build clean environment for Claude Code subprocess."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.setdefault("HOME", "/home/web3relic")
    env.setdefault("USER", "web3relic")
    env["PATH"] = "/home/web3relic/.local/bin:/usr/local/bin:/usr/bin:/bin"
    return env


def _build_claude_code_cmd(
    model: str,
    system_prompt: str | None = None,
    stream_partials: bool = False,
    disable_tools: bool = True,
) -> list[str]:
    """Build Claude Code CLI command list.

    disable_tools=True (default) prevents Claude from trying to use tools
    in conversational mode, which avoids stop_reason=tool_use with empty results.
    """
    cmd = [
        CLAUDE_CLI, "-p",
        "--model", model,
        "--max-turns", "1",
        "--no-session-persistence",
        "--output-format", "stream-json",
        "--verbose",
    ]
    if disable_tools:
        cmd.extend(["--tools", ""])
    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])
    if stream_partials:
        cmd.append("--include-partial-messages")
    return cmd


def _parse_ndjson_line(line: bytes) -> dict | None:
    """Parse a single NDJSON line, returning None on failure."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _extract_prompt_and_system(messages: list[dict], system_instruction: str | None = None) -> tuple[str, str | None]:
    """Split messages into (user_prompt, system_prompt)."""
    system_parts = []
    user_parts = []

    if system_instruction:
        system_parts.append(system_instruction)

    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(content)

    system_prompt = "\n\n".join(system_parts) if system_parts else None
    user_prompt = "\n\n".join(user_parts) if user_parts else ""
    return user_prompt, system_prompt


async def _call_claude_code_stream(
    provider: ProviderConfig,
    messages: list[dict],
    max_tokens: int | None = None,
    system_instruction: str | None = None,
) -> str:
    """Call Claude Code CLI (non-streaming). Returns full response text."""
    user_prompt, system_prompt = _extract_prompt_and_system(messages, system_instruction)
    if not user_prompt:
        return ""

    model = provider.model_name or "sonnet"
    cmd = _build_claude_code_cmd(model, system_prompt, stream_partials=False)
    env = _build_claude_code_env()

    log.info(f"Claude Code call: model={model}, prompt={len(user_prompt)} chars")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd="/tmp",
    )

    timeout = provider.metadata.get("timeout_seconds", CLAUDE_CODE_TIMEOUT)
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(user_prompt.encode()),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        log.warning(f"Claude Code timed out after {timeout}s")
        raise

    if proc.returncode != 0:
        log.warning(f"Claude Code exited {proc.returncode}: {stderr.decode()[:300]}")
        return ""

    # Parse NDJSON output — find the result line
    result_text = ""
    assistant_text = ""
    for raw_line in stdout.split(b"\n"):
        parsed = _parse_ndjson_line(raw_line)
        if not parsed:
            continue

        msg_type = parsed.get("type")

        # Capture text from assistant messages (backup extraction)
        if msg_type == "assistant":
            try:
                for block in parsed.get("message", {}).get("content", []):
                    if block.get("type") == "text":
                        assistant_text += block.get("text", "")
            except (TypeError, AttributeError):
                pass

        if msg_type == "result":
            if parsed.get("is_error"):
                log.warning(f"Claude Code error: {parsed.get('error', 'unknown')}")
                return ""
            result_text = parsed.get("result") or ""
            cost = parsed.get("total_cost_usd")
            if cost:
                log.info(f"Claude Code cost: ${cost:.4f}")
            if not result_text:
                log.info(f"Claude Code result field empty, stop_reason={parsed.get('stop_reason')}")
            break

    # Fallback: if result field was empty but assistant message had text
    if not result_text and assistant_text:
        log.info(f"Claude Code: using assistant message text ({len(assistant_text)} chars)")
        result_text = assistant_text

    return result_text


async def _stream_claude_code_stream(
    provider: ProviderConfig,
    messages: list[dict],
    max_tokens: int | None = None,
    system_instruction: str | None = None,
):
    """Stream from Claude Code CLI. Yields text chunks as they arrive."""
    user_prompt, system_prompt = _extract_prompt_and_system(messages, system_instruction)
    if not user_prompt:
        return

    model = provider.model_name or "sonnet"
    cmd = _build_claude_code_cmd(model, system_prompt, stream_partials=True)
    env = _build_claude_code_env()

    log.info(f"Claude Code stream: model={model}, prompt={len(user_prompt)} chars")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd="/tmp",
    )

    # Write prompt and close stdin
    proc.stdin.write(user_prompt.encode())
    await proc.stdin.drain()
    proc.stdin.close()

    timeout = provider.metadata.get("timeout_seconds", CLAUDE_CODE_TIMEOUT)

    try:
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                log.warning(f"Claude Code stream timed out after {timeout}s")
                break

            if not line:  # EOF
                break

            parsed = _parse_ndjson_line(line)
            if not parsed:
                continue

            msg_type = parsed.get("type")

            # Extract text deltas from stream events
            if msg_type == "stream_event":
                event = parsed.get("event", {})
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta" and delta.get("text"):
                        yield delta["text"]

            # Check for completion
            elif msg_type == "result":
                if parsed.get("is_error"):
                    log.warning(f"Claude Code stream error: {parsed.get('error', 'unknown')}")
                cost = parsed.get("total_cost_usd")
                if cost:
                    log.info(f"Claude Code stream cost: ${cost:.4f}")
                break

    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()


# ── Main entry point ─────────────────────────────────────────────────────────

async def provider_chat(
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.0,
    model: str | None = None,
    system_instruction: str | None = None,
    preferred_provider: str | None = None,
) -> str:
    """Call LLM through provider registry with automatic fallback.

    Falls through providers in priority order. If preferred_provider is set,
    tries that first before falling back to others.

    Args:
        messages: OpenAI-format messages list.
        max_tokens: Max response tokens.
        temperature: Sampling temperature.
        model: Override model name for the provider.
        system_instruction: Prepended as system message if set.
        preferred_provider: Name of preferred provider (tried first).

    Returns:
        LLM response text. Empty string if all providers fail.
    """
    if system_instruction:
        messages = [{"role": "system", "content": system_instruction}] + messages

    providers = get_providers()

    # If preferred, move it to front
    if preferred_provider:
        preferred = [p for p in providers if p.name == preferred_provider]
        others = [p for p in providers if p.name != preferred_provider]
        providers = preferred + others

    for provider in providers:
        if not provider.enabled:
            continue
        try:
            if provider.provider_type == "openai_compatible":
                result = await _call_openai_compatible(
                    provider, messages, max_tokens, temperature, model
                )
            elif provider.provider_type == "claude_code_stream":
                result = await _call_claude_code_stream(
                    provider, messages, max_tokens
                )
            elif provider.provider_type == "claude_cli":
                result = await _call_claude_cli(provider, messages, max_tokens)
            else:
                log.warning(f"Unknown provider type: {provider.provider_type}")
                continue

            if result:
                log.info(f"Provider {provider.name} responded ({len(result)} chars)")
                return result
            log.warning(f"Provider {provider.name} returned empty response")
        except asyncio.TimeoutError:
            log.warning(f"Provider {provider.name} timed out")
        except Exception as e:
            log.warning(f"Provider {provider.name} failed: {e}")

    log.error("All LLM providers failed")
    return ""


async def provider_chat_stream(
    messages: list[dict],
    max_tokens: int = 500,
    temperature: float = 0.0,
    model: str | None = None,
    system_instruction: str | None = None,
    preferred_provider: str | None = None,
):
    """Streaming version of provider_chat(). Yields text chunks.

    Falls back to non-streaming if the provider doesn't support streaming.
    """
    if system_instruction:
        messages = [{"role": "system", "content": system_instruction}] + messages

    providers = get_providers()

    if preferred_provider:
        preferred = [p for p in providers if p.name == preferred_provider]
        others = [p for p in providers if p.name != preferred_provider]
        providers = preferred + others

    for provider in providers:
        if not provider.enabled:
            continue
        try:
            if provider.provider_type == "openai_compatible":
                yielded = False
                async for chunk in _stream_openai_compatible(
                    provider, messages, max_tokens, temperature, model
                ):
                    yielded = True
                    yield chunk
                if yielded:
                    return
                log.warning(f"Provider {provider.name} stream returned empty")
            elif provider.provider_type == "claude_code_stream":
                yielded = False
                async for chunk in _stream_claude_code_stream(
                    provider, messages, max_tokens
                ):
                    yielded = True
                    yield chunk
                if yielded:
                    return
                log.warning(f"Provider {provider.name} stream returned empty")
            elif provider.provider_type == "claude_cli":
                # CLI doesn't support streaming — fall back to full response
                result = await _call_claude_cli(provider, messages, max_tokens)
                if result:
                    yield result
                    return
                log.warning(f"Provider {provider.name} returned empty response")
            else:
                log.warning(f"Unknown provider type: {provider.provider_type}")
                continue
        except asyncio.TimeoutError:
            log.warning(f"Provider {provider.name} timed out")
        except Exception as e:
            log.warning(f"Provider {provider.name} failed: {e}")

    log.error("All LLM providers failed (stream)")
    yield ""

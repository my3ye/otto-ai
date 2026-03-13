"""Perception Alignment — validate and filter LLM outputs.

Reference: arXiv 2602.20934v1 §5 (Perception Alignment)

Validates that LLM responses meet quality thresholds before delivery.
If validation fails, attempts one correction retry.
"""

import logging

from ..llm import llm_chat

log = logging.getLogger("otto.kernel.perception")


async def align_response(
    response: str,
    interrupt_type: str,
    channel: str = "whatsapp",
    max_retries: int = 1,
) -> tuple[str, bool]:
    """Validate and potentially correct an LLM response.

    Args:
        response: Raw LLM output.
        interrupt_type: Type of interrupt being handled.
        channel: Output channel (affects validation rules).
        max_retries: Max correction attempts.

    Returns:
        (validated_response, was_corrected)
    """
    # Basic validation
    issues = _check_basic_issues(response, channel)

    if not issues:
        return response, False

    log.warning(f"Perception alignment: {len(issues)} issue(s) found: {issues}")

    # Attempt correction
    for attempt in range(max_retries):
        corrected = await _correct_response(response, issues, channel)
        if corrected:
            new_issues = _check_basic_issues(corrected, channel)
            if not new_issues:
                log.info(f"Perception correction succeeded on attempt {attempt + 1}")
                return corrected, True
            issues = new_issues

    # If correction failed, return original with any obvious fixes
    cleaned = _emergency_clean(response)
    return cleaned, False


def _check_basic_issues(response: str, channel: str) -> list[str]:
    """Check for basic quality issues in the response."""
    issues = []

    if not response or not response.strip():
        issues.append("empty_response")
        return issues

    # Check for obvious LLM artifacts
    if response.strip().startswith("```"):
        issues.append("starts_with_code_fence")

    # Check for role confusion
    lower = response.lower()
    if "as an ai" in lower or "i'm an ai language model" in lower:
        issues.append("role_confusion")

    # Check for leaked system prompt
    if "[otto]" in lower and "purpose" in lower and "immutable" in lower:
        issues.append("leaked_system_prompt")

    # Channel-specific checks
    if channel == "whatsapp":
        # WhatsApp should be concise
        if len(response) > 3000:
            issues.append("too_long_for_whatsapp")

    # Check for privacy violations
    if "mevan abeydeera" in lower:
        issues.append("privacy_violation_real_name")

    return issues


async def _correct_response(
    response: str,
    issues: list[str],
    channel: str,
) -> str | None:
    """Attempt to correct a response with issues."""
    issue_text = ", ".join(issues)

    system_msg = (
        "You are editing a response from Otto (an AI agent) to fix quality issues. "
        f"Issues found: {issue_text}. "
        f"Channel: {channel}. "
        "Fix the issues while preserving the core message. "
        "Return ONLY the corrected response text, nothing else."
    )

    try:
        corrected = await llm_chat(
            [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": f"Original response:\n{response}"},
            ],
            max_tokens=1500,
            temperature=0.3,
        )
        return corrected if corrected else None
    except Exception as e:
        log.warning(f"Perception correction failed: {e}")
        return None


def _emergency_clean(response: str) -> str:
    """Last-resort cleaning: remove obvious problems without LLM call."""
    # Strip code fences
    if response.strip().startswith("```"):
        lines = response.strip().split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines)

    # Remove real name if leaked
    response = response.replace("Mevan Abeydeera", "Mev")
    response = response.replace("mevan abeydeera", "Mev")

    return response.strip()

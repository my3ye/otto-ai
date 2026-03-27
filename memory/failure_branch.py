"""Failure-Branch Adaptation Module for RL2F.

Provides in-task failure detection, root-cause analysis, correction generation,
and retest validation. Hooks into the existing RL2F feedback loop to enable
mid-execution adaptation (STEM Agent arXiv 2603.22359 gap).

Three phases:
  1. Detection — classify task output into failure types with confidence
  2. Correction — LLM-powered root-cause analysis + prompt adjustment
  3. Retest — validate the correction resolved the failure

Keeps existing RL2F feedback logging intact; this module adds a parallel
adaptation path that works *during* task execution, not just across retries.
"""

import re
import logging
from dataclasses import dataclass, field

log = logging.getLogger("failure_branch")

# ── Failure type taxonomy ──────────────────────────────────────────────
FAILURE_TYPES = {
    "timeout": "Task exceeded time/budget limits",
    "error": "Runtime error, crash, or exception",
    "quality": "Output produced but does not meet quality bar",
    "approach": "Wrong strategy or methodology for the problem",
    "dependency": "Missing dependency, service, or external resource",
}

# ── Detection patterns ────────────────────────────────────────────────
_ERROR_PATTERNS = [
    (r"(?i)traceback \(most recent call last\)", "error", 0.9),
    (r"(?i)error:|exception:|fatal:", "error", 0.7),
    (r"(?i)command not found|no such file|permission denied", "dependency", 0.8),
    (r"(?i)connection refused|timeout|ETIMEDOUT|ECONNREFUSED", "dependency", 0.75),
    (r"(?i)budget exceeded|max.turns|rate.limit", "timeout", 0.85),
    (r"(?i)import error|module not found|ModuleNotFoundError", "dependency", 0.85),
    (r"(?i)exit.code.*[1-9]|exited with code [1-9]", "error", 0.65),
    (r"(?i)SIGKILL|SIGTERM|OOM|out of memory", "timeout", 0.9),
    (r"(?i)assertion.?error|assert.*failed", "quality", 0.7),
    (r"(?i)test.*fail|tests? failed", "quality", 0.75),
]

_APPROACH_PATTERNS = [
    (r"(?i)I'm (not sure|uncertain|unable to determine)", "approach", 0.5),
    (r"(?i)this approach (won't work|doesn't|isn't)", "approach", 0.7),
    (r"(?i)need(?:s)? a different (strategy|approach|method)", "approach", 0.75),
    (r"(?i)blocked|cannot proceed|stuck", "approach", 0.6),
]


@dataclass
class DetectionResult:
    """Result of failure detection scan."""
    detected: bool
    failure_type: str | None = None
    failure_signal: str | None = None
    confidence: float = 0.0


@dataclass
class RootCauseAnalysis:
    """LLM-generated root-cause analysis."""
    root_cause: str = ""
    category: str = "unknown"  # prompt, scope, dependency, environment, logic
    correction_strategy: str = ""
    corrected_prompt: str = ""


@dataclass
class RetestResult:
    """Outcome of a retest after correction."""
    passed: bool
    details: str = ""


def detect_failure(
    task_output: str,
    exit_code: int = 0,
    task_metadata: dict | None = None,
) -> DetectionResult:
    """Scan task output for failure signals.

    Uses pattern matching against known failure signatures.
    Returns the highest-confidence match, or detected=False if clean.

    Does NOT modify any existing feedback data — detection only.
    """
    if not task_output and exit_code == 0:
        return DetectionResult(detected=False)

    metadata = task_metadata or {}
    best_type = None
    best_signal = None
    best_confidence = 0.0

    # Non-zero exit code is a strong signal
    if exit_code != 0:
        best_type = "error"
        best_signal = f"Non-zero exit code: {exit_code}"
        best_confidence = 0.8

    # Scan output against known patterns
    all_patterns = _ERROR_PATTERNS + _APPROACH_PATTERNS
    for pattern, ftype, confidence in all_patterns:
        match = re.search(pattern, task_output)
        if match and confidence > best_confidence:
            # Extract context around match
            start = max(0, match.start() - 50)
            end = min(len(task_output), match.end() + 100)
            signal = task_output[start:end].strip()
            best_type = ftype
            best_signal = signal[:300]
            best_confidence = confidence

    # Check metadata for retry signals (lower confidence — let RL2F handle)
    retry_count = metadata.get("retry_count", 0)
    if retry_count >= 2 and best_confidence < 0.5:
        best_type = best_type or "approach"
        best_signal = best_signal or f"Multiple retries ({retry_count}) without resolution"
        best_confidence = max(best_confidence, 0.55)

    # Threshold: only flag if confidence >= 0.5
    if best_confidence >= 0.5:
        return DetectionResult(
            detected=True,
            failure_type=best_type,
            failure_signal=best_signal,
            confidence=round(best_confidence, 3),
        )

    return DetectionResult(detected=False)


async def analyze_root_cause(
    failure_type: str,
    failure_signal: str,
    original_prompt: str,
    task_output: str = "",
) -> RootCauseAnalysis:
    """Use LLM to analyze root cause and generate correction.

    This is the core of the correction sub-process:
    1. Classify the root cause into a category
    2. Generate a correction strategy
    3. Produce a corrected prompt that addresses the failure

    Keeps the original task intent intact — only adjusts approach.
    """
    from .llm import llm_chat, extract_json

    # Truncate large outputs
    output_excerpt = task_output[-2000:] if len(task_output) > 2000 else task_output
    prompt_excerpt = original_prompt[:3000]

    analysis_prompt = f"""Analyze this task failure and produce a correction.

FAILURE TYPE: {failure_type}
FAILURE SIGNAL: {failure_signal}

ORIGINAL PROMPT (excerpt):
{prompt_excerpt}

TASK OUTPUT (tail):
{output_excerpt}

Respond in JSON:
{{
  "root_cause": "One sentence describing WHY this failed",
  "category": "One of: prompt, scope, dependency, environment, logic",
  "correction_strategy": "One sentence describing HOW to fix it",
  "corrected_prompt_additions": "Specific instructions to prepend to the original prompt to prevent this failure"
}}"""

    response = await llm_chat(
        messages=[{"role": "user", "content": analysis_prompt}],
        system_instruction="You are a failure analysis system. Analyze task failures concisely. Return valid JSON only.",
        max_tokens=500,
        temperature=0.0,
    )

    parsed = extract_json(response)
    if not parsed:
        # Fallback: basic analysis without LLM
        return RootCauseAnalysis(
            root_cause=f"{failure_type} failure: {failure_signal[:200]}",
            category=_infer_category(failure_type),
            correction_strategy=f"Address {failure_type} by reviewing approach",
            corrected_prompt=_build_fallback_correction(failure_type, failure_signal, original_prompt),
        )

    corrected_prompt = original_prompt
    additions = parsed.get("corrected_prompt_additions", "")
    if additions:
        corrected_prompt = f"=== FAILURE-BRANCH CORRECTION ===\n{additions}\n=== END CORRECTION ===\n\n{original_prompt}"

    return RootCauseAnalysis(
        root_cause=parsed.get("root_cause", f"{failure_type}: {failure_signal[:200]}"),
        category=parsed.get("category", _infer_category(failure_type)),
        correction_strategy=parsed.get("correction_strategy", ""),
        corrected_prompt=corrected_prompt,
    )


def validate_retest(
    retest_output: str,
    retest_passed: bool,
    original_failure_type: str,
) -> RetestResult:
    """Validate whether a correction resolved the original failure.

    Simple validation: check that the original failure pattern is absent
    AND the caller reports success.
    """
    if not retest_passed:
        return RetestResult(
            passed=False,
            details=f"Retest reported failure. Output tail: {retest_output[-300:] if retest_output else 'empty'}"
        )

    # Double-check: scan for the same failure type recurring
    recheck = detect_failure(retest_output, exit_code=0)
    if recheck.detected and recheck.failure_type == original_failure_type:
        return RetestResult(
            passed=False,
            details=f"Original failure type '{original_failure_type}' still present after correction: {recheck.failure_signal}"
        )

    return RetestResult(
        passed=True,
        details="Correction resolved the failure. No recurrence detected."
    )


# ── Helpers ────────────────────────────────────────────────────────────

def _infer_category(failure_type: str) -> str:
    """Map failure type to root-cause category when LLM unavailable."""
    mapping = {
        "timeout": "environment",
        "error": "logic",
        "quality": "prompt",
        "approach": "scope",
        "dependency": "dependency",
    }
    return mapping.get(failure_type, "unknown")


def _build_fallback_correction(failure_type: str, failure_signal: str, original_prompt: str) -> str:
    """Build a corrected prompt without LLM assistance."""
    corrections = {
        "timeout": "Work within a smaller scope. Break the task into steps and complete the most critical one first.",
        "error": "Check all imports, file paths, and API endpoints before executing. Handle errors gracefully.",
        "quality": "Focus on correctness over completeness. Verify your output matches requirements exactly.",
        "approach": "Reconsider the approach. List alternatives before proceeding and choose the simplest viable one.",
        "dependency": "Verify all required services, packages, and files exist before attempting the main work.",
    }
    correction = corrections.get(failure_type, "Review the previous failure and adjust approach.")
    return (
        f"=== FAILURE-BRANCH CORRECTION ===\n"
        f"Previous attempt failed: {failure_signal[:200]}\n"
        f"Correction: {correction}\n"
        f"=== END CORRECTION ===\n\n"
        f"{original_prompt}"
    )

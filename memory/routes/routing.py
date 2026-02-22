"""AdaptOrch rule-based task routing module for Otto.

Implements topology routing based on task characteristics, mapping tasks to
optimal execution strategies. Based on AdaptOrch (2025) adaptive orchestration
research — routes tasks based on complexity signals to improve success rate.

Strategies:
  express          — Lookup / cheap / quick tasks: capped turns + timeout
  research_chunked — Research tasks: extended turns + timeout for thoroughness
  full_budget_build— High-priority (P8+) build tasks: max budget + LATS retry
  eval_focused     — Evaluation tasks: long timeout, structured execution
  lats_fallback    — Previously-failed tasks with LATS alternative in metadata
  standard         — Default: use task params as-is
"""

import re
import logging

from ..models import TaskRouteRequest, ExecutionStrategy

log = logging.getLogger("otto.routing")

# ── Task Type Keyword Sets ──────────────────────────────────────────

RESEARCH_KEYWORDS = frozenset([
    "research", "find", "analyze", "analyse", "survey", "search",
    "explore", "study", "investigate", "discover", "gather", "collect",
    "review", "scan", "crawl", "pull", "paper", "papers", "literature",
    "fetch", "lookup", "look",
])

BUILD_KEYWORDS = frozenset([
    "implement", "build", "create", "write", "add", "fix", "refactor",
    "develop", "setup", "configure", "deploy", "install", "integrate",
    "generate", "construct", "design", "architect", "launch", "push",
    "update", "upgrade", "extend", "modify", "patch", "migrate", "wire",
    # UI/frontend build signals
    "dashboard", "ui", "page", "component", "view", "filter", "feature",
    "endpoint", "api", "route", "handler", "migration", "schema", "script",
])

LOOKUP_KEYWORDS = frozenset([
    "check", "verify", "status", "list", "get", "count",
    "show", "display", "report", "monitor", "watch", "inspect", "confirm",
    "ping", "health", "what", "how",
])

EVAL_KEYWORDS = frozenset([
    "eval", "evaluate", "test", "benchmark", "score", "assess",
    "measure", "validate", "metric", "performance", "capability",
    "harness", "capability", "push", "improve", "increase",
])


def detect_task_type(title: str, prompt: str | None = None) -> str:
    """Classify task into: research | build | lookup | eval | standard.

    Uses keyword intersection scoring with title-weighting. Title keywords
    count 3x because the title reflects true task intent, while prompt
    descriptions often contain lookup-style words ("show", "verify", "check")
    even for build tasks. Ties go to the type listed last (build > research > lookup > eval).
    """
    title_lower = title.lower()
    prompt_lower = (prompt or "").lower()
    title_words = set(re.findall(r'\b\w+\b', title_lower))
    prompt_words = set(re.findall(r'\b\w+\b', prompt_lower))

    keyword_sets = {
        "eval":     EVAL_KEYWORDS,
        "lookup":   LOOKUP_KEYWORDS,
        "research": RESEARCH_KEYWORDS,
        "build":    BUILD_KEYWORDS,
    }

    scores = {}
    for task_type, kw_set in keyword_sets.items():
        # Title matches count 3x — title is the reliable intent signal
        title_hits = len(title_words & kw_set)
        prompt_hits = len(prompt_words & kw_set)
        scores[task_type] = title_hits * 3 + prompt_hits

    best_type, best_score = "standard", 0
    for task_type, score in scores.items():
        if score >= best_score and score > 0:
            best_type, best_score = task_type, score

    log.debug(f"Task type detection: '{title[:40]}' → {best_type} (scores: {scores})")
    return best_type


def route_task(req: TaskRouteRequest) -> ExecutionStrategy:
    """Apply AdaptOrch rule-based routing to determine optimal execution strategy.

    Rules evaluated in priority order:
    1. lats_fallback    — metadata has failure_fallback AND attempt_count > 0
    2. express          — lookup type OR cheap/short params (budget≤0.5 OR timeout≤180s)
    3. full_budget_build— high priority (P8+) build task
    4. research_chunked — research type
    5. eval_focused     — eval type
    6. standard         — default (use task params as-is)
    """
    title = req.title or ""
    prompt = req.prompt or ""
    task_type = detect_task_type(title, prompt)

    lats_fallback_prompt = (
        req.metadata.get("failure_fallback")
        or req.metadata.get("lats_fallback_prompt")
    )
    attempt_count = int(req.metadata.get("attempt_count", 0))
    previously_failed = attempt_count > 0

    # ── Rule 1: LATS fallback ──────────────────────────────────────
    if previously_failed and lats_fallback_prompt:
        log.info(f"Routing '{title[:40]}' → lats_fallback (attempt {attempt_count})")
        return ExecutionStrategy(
            strategy="lats_fallback",
            task_type=task_type,
            recommended_model="sonnet",
            recommended_max_turns=max(req.max_turns, 40),
            recommended_timeout_seconds=max(req.timeout_seconds, 600),
            recommended_max_budget_usd=max(req.max_budget_usd, 3.0),
            reasoning=(
                f"Task previously failed ({attempt_count} attempt(s)). "
                "Switching to LATS alternative approach to avoid repeating failure pattern."
            ),
            lats_fallback_prompt=str(lats_fallback_prompt),
        )

    # ── Rule 2: Express (fast/cheap single-shot) ───────────────────
    # Never express-route high-priority tasks — they need full resources
    is_cheap_or_quick = req.max_budget_usd <= 0.5 or req.timeout_seconds <= 180
    is_high_priority = req.priority >= 8
    if (task_type == "lookup" and not is_high_priority) or (is_cheap_or_quick and not is_high_priority):
        log.info(f"Routing '{title[:40]}' → express (type={task_type})")
        return ExecutionStrategy(
            strategy="express",
            task_type=task_type,
            recommended_model="sonnet",
            recommended_max_turns=min(req.max_turns, 15),
            recommended_timeout_seconds=min(max(req.timeout_seconds, 120), 300),
            recommended_max_budget_usd=min(max(req.max_budget_usd, 0.5), 2.0),
            reasoning=(
                f"Task classified as '{task_type}'. "
                "Fast single-shot strategy: capped at 15 turns, 300s timeout, $2 budget."
            ),
        )

    # ── Rule 3: Full budget build ──────────────────────────────────
    if task_type == "build" and req.priority >= 8:
        log.info(f"Routing '{title[:40]}' → full_budget_build (P{req.priority})")
        return ExecutionStrategy(
            strategy="full_budget_build",
            task_type=task_type,
            recommended_model="sonnet",
            recommended_max_turns=max(req.max_turns, 60),
            recommended_timeout_seconds=max(req.timeout_seconds, 900),
            recommended_max_budget_usd=max(req.max_budget_usd, 5.0),
            reasoning=(
                f"High-priority (P{req.priority}) build task. "
                "Allocating full budget: 60 turns, 900s, $5. LATS retry on failure."
            ),
        )

    # ── Rule 4: Research chunked ───────────────────────────────────
    if task_type == "research":
        log.info(f"Routing '{title[:40]}' → research_chunked")
        return ExecutionStrategy(
            strategy="research_chunked",
            task_type=task_type,
            recommended_model="sonnet",
            recommended_max_turns=max(req.max_turns, 40),
            recommended_timeout_seconds=max(req.timeout_seconds, 900),
            recommended_max_budget_usd=max(req.max_budget_usd, 2.0),
            reasoning=(
                "Research task detected. Extended turns (40+) and 900s+ timeout "
                "for thorough web search and information gathering."
            ),
        )

    # ── Rule 5: Eval focused ───────────────────────────────────────
    if task_type == "eval":
        log.info(f"Routing '{title[:40]}' → eval_focused")
        return ExecutionStrategy(
            strategy="eval_focused",
            task_type=task_type,
            recommended_model="sonnet",
            recommended_max_turns=max(req.max_turns, 30),
            recommended_timeout_seconds=max(req.timeout_seconds, 900),
            recommended_max_budget_usd=max(req.max_budget_usd, 3.0),
            reasoning=(
                "Evaluation task detected. 900s timeout (eval harness runs are slow), "
                "structured execution to ensure complete scoring."
            ),
        )

    # ── Rule 6: Standard (default) ─────────────────────────────────
    log.info(f"Routing '{title[:40]}' → standard (type={task_type}, P{req.priority})")
    return ExecutionStrategy(
        strategy="standard",
        task_type=task_type,
        recommended_model="sonnet",
        recommended_max_turns=req.max_turns,
        recommended_timeout_seconds=req.timeout_seconds,
        recommended_max_budget_usd=req.max_budget_usd,
        reasoning=(
            f"Standard task (type: {task_type}, P{req.priority}). "
            "Using task parameters as-is."
        ),
    )

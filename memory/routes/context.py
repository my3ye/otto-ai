from fastapi import APIRouter, Query
from ..db import get_pool
from ..graphiti import graphiti_search
from ..models import (
    ContextBriefing, SessionOut, SemanticMemoryOut,
    EpisodicEventOut, ProcedureOut,
)

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/briefing", response_model=ContextBriefing)
async def get_briefing(session_id: str | None = None):
    """Aggregate all memory layers into a single context briefing."""
    pool = await get_pool()

    # Current session (if provided)
    current_session = None
    if session_id:
        row = await pool.fetchrow(
            """SELECT id, session_type, started_at, ended_at, summary, key_decisions
               FROM sessions WHERE id = $1""",
            session_id,
        )
        if row:
            current_session = SessionOut(**dict(row))

    # Last completed session
    last_row = await pool.fetchrow(
        """SELECT id, session_type, started_at, ended_at, summary, key_decisions
           FROM sessions WHERE ended_at IS NOT NULL
           ORDER BY ended_at DESC LIMIT 1""",
    )
    last_session = SessionOut(**dict(last_row)) if last_row else None

    # Identity facts from pgvector
    identity_rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at
           FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT 20""",
    )
    identity_facts = [SemanticMemoryOut(**dict(r)) for r in identity_rows]

    # High-confidence semantic facts
    fact_rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at
           FROM semantic_memories
           WHERE category != 'identity' AND confidence >= 0.7
           ORDER BY confidence DESC, updated_at DESC LIMIT 30""",
    )
    high_confidence_facts = [SemanticMemoryOut(**dict(r)) for r in fact_rows]

    # Recent important events
    event_rows = await pool.fetch(
        """SELECT id, session_id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE importance >= 5
           ORDER BY created_at DESC LIMIT 20""",
    )
    recent_events = [EpisodicEventOut(**dict(r)) for r in event_rows]

    # Active procedures
    proc_rows = await pool.fetch(
        """SELECT id, name, description, steps, success_count, failure_count, last_used, created_at
           FROM procedures ORDER BY last_used DESC NULLS LAST LIMIT 10""",
    )
    procedures = [ProcedureOut(**dict(r)) for r in proc_rows]

    # Graph facts from Graphiti — search for Otto, Mev, and infrastructure
    graph_facts = []
    for query in ["Otto Mev projects and decisions", "infrastructure services and systems"]:
        facts = await graphiti_search(query, max_facts=10)
        graph_facts.extend(facts)
    # Deduplicate by uuid, keep current facts only
    seen = set()
    unique_facts = []
    for f in graph_facts:
        if f.get("invalid_at") is None and f["uuid"] not in seen:
            seen.add(f["uuid"])
            unique_facts.append(f)
    graph_facts = unique_facts

    return ContextBriefing(
        session=current_session,
        last_session=last_session,
        identity_facts=identity_facts,
        high_confidence_facts=high_confidence_facts,
        recent_events=recent_events,
        procedures=procedures,
        graph_facts=graph_facts,
    )


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


@router.get("/inject")
async def get_injection(
    max_tokens: int = Query(default=15000, description="Token budget for injection (30% of 200k = 60k ceiling)"),
    source: str = Query(default="startup", description="Session source: startup, compact, resume"),
):
    """Token-budgeted context injection for hooks.

    Returns a plain text string with prioritized context that fits within
    the token budget. Priority order:

    1. Identity core (mission, who Otto is) — always included
    2. Active mission & goals — always included
    3. Pending questions — always included
    4. Last session summary — included if budget allows
    5. Recent high-importance events — filled until budget
    6. High-confidence semantic facts — filled until budget
    7. Knowledge graph facts — filled until budget
    8. Procedures — filled until budget

    Budget scales: query limits grow with budget so the endpoint can fill
    larger budgets when there's enough content.
    """
    pool = await get_pool()
    lines = []
    used = 0

    # Scale query limits with budget
    is_large = max_tokens >= 5000
    is_xlarge = max_tokens >= 10000

    def _add(text: str) -> bool:
        """Add text if it fits within budget. Returns False if budget exceeded."""
        nonlocal used
        cost = _estimate_tokens(text)
        if used + cost > max_tokens:
            return False
        lines.append(text)
        used += cost
        return True

    # ── Tier 1: Identity core (always) ──────────────────────────────
    identity_rows = await pool.fetch(
        """SELECT content FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT $1""",
        10 if is_large else 5,
    )
    if identity_rows:
        _add("[Otto] Identity:")
        for r in identity_rows:
            if not _add(f"  - {r['content']}"):
                break
        _add("")

    # ── Tier 2: Mission & goals (always) ────────────────────────────
    mission_rows = await pool.fetch(
        """SELECT content FROM semantic_memories
           WHERE category IN ('mission', 'goal', 'decision') AND confidence >= 0.7
           ORDER BY confidence DESC, created_at DESC LIMIT $1""",
        15 if is_large else 5,
    )
    if mission_rows:
        _add("[Otto] Mission & Goals:")
        for r in mission_rows:
            if not _add(f"  - {r['content']}"):
                break
        _add("")

    # ── Tier 3: Pending questions (always) ──────────────────────────
    pending_rows = await pool.fetch(
        """SELECT question, intent FROM pending_questions
           WHERE resolved_at IS NULL ORDER BY asked_at DESC LIMIT 5""",
    )
    if pending_rows:
        _add("[Otto] Pending questions (awaiting Mev):")
        for r in pending_rows:
            if not _add(f"  [{r['intent'].upper()}] {r['question']}"):
                break
        _add("")

    # ── Tier 4: Last session (if budget) ────────────────────────────
    last_row = await pool.fetchrow(
        """SELECT summary FROM sessions
           WHERE ended_at IS NOT NULL AND summary IS NOT NULL
           ORDER BY ended_at DESC LIMIT 1""",
    )
    if last_row and last_row["summary"]:
        max_summary = 500 if is_large else 200
        summary = last_row["summary"][:max_summary]
        _add(f"[Otto] Last session: {summary}")
        _add("")

    # ── Tier 5: Recent events (fill budget) ─────────────────────────
    if used < max_tokens * 0.5:
        event_limit = 20 if is_xlarge else (10 if is_large else 5)
        min_importance = 5 if is_xlarge else 6
        event_rows = await pool.fetch(
            """SELECT content, event_type, importance FROM episodic_events
               WHERE importance >= $1
               ORDER BY created_at DESC LIMIT $2""",
            min_importance, event_limit,
        )
        if event_rows:
            snippet_len = 300 if is_large else 150
            _add("[Otto] Recent events:")
            for r in event_rows:
                snippet = r["content"][:snippet_len]
                if not _add(f"  [{r['event_type']}] {snippet}"):
                    break
            _add("")

    # ── Tier 6: High-confidence semantic facts (fill budget) ────────
    if used < max_tokens * 0.6:
        fact_limit = 20 if is_xlarge else (10 if is_large else 5)
        fact_rows = await pool.fetch(
            """SELECT content, category FROM semantic_memories
               WHERE category NOT IN ('identity', 'mission', 'goal', 'decision')
                 AND confidence >= 0.7
               ORDER BY confidence DESC, updated_at DESC LIMIT $1""",
            fact_limit,
        )
        if fact_rows:
            _add("[Otto] Key facts:")
            for r in fact_rows:
                if not _add(f"  [{r['category']}] {r['content'][:200]}"):
                    break
            _add("")

    # ── Tier 7: Knowledge graph (fill budget) ───────────────────────
    if used < max_tokens * 0.8:
        graph_max = 10 if is_xlarge else 5
        graph_facts = []
        queries = ["Otto Mev projects decisions", "brands products goals"]
        if is_xlarge:
            queries.append("infrastructure services systems")
        for query in queries:
            facts = await graphiti_search(query, max_facts=graph_max)
            graph_facts.extend(facts)
        # Deduplicate, current only
        seen = set()
        unique = []
        for f in graph_facts:
            uid = f.get("uuid", "")
            if f.get("invalid_at") is None and uid not in seen:
                seen.add(uid)
                unique.append(f)
        if unique:
            _add("[Otto] Knowledge graph:")
            for f in unique:
                if not _add(f"  - {f['fact']}"):
                    break
            _add("")

    # ── Tier 8: Procedures (fill budget) ────────────────────────────
    if used < max_tokens * 0.9:
        proc_rows = await pool.fetch(
            """SELECT name, success_count, failure_count FROM procedures
               ORDER BY last_used DESC NULLS LAST LIMIT 10""",
        )
        if proc_rows:
            _add("[Otto] Procedures:")
            for r in proc_rows:
                total = r["success_count"] + r["failure_count"]
                rate = f" ({r['success_count']}/{total})" if total > 0 else ""
                if not _add(f"  - {r['name']}{rate}"):
                    break
            _add("")

    # On compact, add a reminder
    if source == "compact":
        _add("[Otto] Context was compacted. Full memory available via API at localhost:8100.")

    pct = round(used / 200000 * 100, 1)
    _add(f"[Otto] Context: ~{used} tokens ({pct}% of 200k context, budget: {max_tokens})")

    return "\n".join(lines)

"""Shared context building logic — same core context for Claude and Gemini brains.


Both brains read from the same memory tiers. The source parameter controls
which brain-specific sections are included:

  source="startup"|"compact"|"resume"  → full Claude context (all tiers)
  source="whatsapp"                     → Gemini-optimized: Tiers 0-6, skip
                                          task queue, cross-brain notes, reasoning chain
"""

import json
import logging
from .graphiti import graphiti_search
from .routes.semantic import arag_search_internal
from .config import settings

log = logging.getLogger("otto.context_builder")


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


# ── Focus compression helpers (arXiv 2601.07190) ─────────────────────────────
# Ordered from least-critical → most-critical: compress earlier entries first.
_SECTION_COMPRESS_LIMITS: list[tuple[str, int]] = [
    ("Procedures",        3),   # just names, rarely needed mid-session
    ("Knowledge graph",   5),   # graphiti facts
    ("Principles",        3),   # learned principles
    ("Key facts",         5),   # A-RAG semantic facts
    ("Structured Graph",  5),   # G2CP cross-brain nodes
    ("Recent reasoning",  2),   # reasoning chain entries
    ("Recent events",     3),   # episodic events
    ("Mission & Goals",   5),   # mission/goal facts
]


def _parse_sections(text: str) -> list[dict]:
    """Split context text into sections on [Otto] header lines."""
    lines = text.split("\n")
    sections: list[dict] = []
    current_name = "_pre"
    current_lines: list[str] = []

    for line in lines:
        is_otto_header = line.startswith("[Otto] ")
        is_separator = line.startswith("=") and len(line) >= 10
        if is_otto_header or is_separator:
            sections.append({"name": current_name, "lines": list(current_lines)})
            current_name = line[7:].rstrip(": ") if is_otto_header else line
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({"name": current_name, "lines": list(current_lines)})

    return sections


def _compress_section_lines(lines: list[str], max_items: int) -> tuple[list[str], int]:
    """Trim a section to at most max_items bullet/bracket entries.

    Returns (new_lines, num_dropped).
    """
    item_lines = [
        l for l in lines
        if (l.startswith("  - ") or (l.startswith("  [") and not l.startswith("  [+")))
    ]
    n_items = len(item_lines)
    if n_items <= max_items:
        return lines, 0

    new_lines: list[str] = []
    item_count = 0
    for l in lines:
        is_item = l.startswith("  - ") or (l.startswith("  [") and not l.startswith("  [+"))
        if is_item:
            if item_count < max_items:
                new_lines.append(l)
                item_count += 1
            # else: drop the excess entry
        else:
            new_lines.append(l)

    dropped = n_items - max_items
    # Insert compression note before any trailing blank lines
    insert_idx = len(new_lines)
    while insert_idx > 0 and not new_lines[insert_idx - 1].strip():
        insert_idx -= 1
    new_lines.insert(insert_idx, f"  [+{dropped} items compressed by Focus]")

    return new_lines, dropped


def compress_context_text(text: str, target_tokens: int) -> tuple[str, int, int]:
    """Rule-based context compression (Focus paper — autonomous memory management).

    Compresses least-critical sections first until the result fits within
    target_tokens.  High-priority sections (PURPOSE, PRIORITIES, Directives,
    Working Memory, Identity, Task Queue, Cross-brain notes) are never touched.

    Returns (compressed_text, original_token_count, compressed_token_count).
    """
    original_tokens = _estimate_tokens(text)
    if original_tokens <= target_tokens:
        return text, original_tokens, original_tokens

    sections = _parse_sections(text)

    for section_key, max_items in _SECTION_COMPRESS_LIMITS:
        for sec in sections:
            if section_key in sec["name"]:
                new_lines, dropped = _compress_section_lines(sec["lines"], max_items)
                if dropped > 0:
                    sec["lines"] = new_lines

        # Re-measure after each section type is compressed
        current_text = "\n".join(l for s in sections for l in s["lines"])
        if _estimate_tokens(current_text) <= target_tokens:
            break

    compressed_text = "\n".join(l for s in sections for l in s["lines"])
    compressed_tokens = _estimate_tokens(compressed_text)
    return compressed_text, original_tokens, compressed_tokens


async def build_context_text(
    pool,
    max_tokens: int = 15000,
    source: str = "startup",
) -> str:
    """Build token-budgeted context text for Claude or Gemini.

    Priority tiers (same order for both brains):
      0a  PURPOSE — immutable identity anchor
      0b  PRIORITIES — ranked what Mev wants
      0c  Active Directives from Mev
      0d  Working Memory (other core_memory slots)
      1   Identity facts (semantic_memories.category='identity')
      2   Mission & goals (semantic_memories.category in mission/goal/decision)
      3   Pending questions (Claude→Mev)
      3b  Cross-brain notes (Gemini→Claude) — Claude only
      3c  Task queue — Claude only
      3d  Reasoning chain — Claude only
      4   Last session summary
      5   Recent high-importance events
      6   High-confidence semantic facts
      7   Knowledge graph
      8   Procedures
    """
    is_whatsapp = source == "whatsapp"
    is_large = max_tokens >= 5000
    is_xlarge = max_tokens >= 10000

    lines: list[str] = []
    used = 0

    def _add(text: str) -> bool:
        nonlocal used
        cost = _estimate_tokens(text)
        if used + cost > max_tokens:
            return False
        lines.append(text)
        used += cost
        return True

    # ── Tier 0a: PURPOSE — non-negotiable, always first ──────────────────
    try:
        purpose_row = await pool.fetchrow(
            "SELECT content FROM core_memory WHERE slot = 'purpose'"
        )
        if purpose_row and purpose_row["content"]:
            _add("=" * 60)
            _add("[Otto] PURPOSE (immutable — only Admin can change this):")
            _add(f"  {purpose_row['content']}")
            _add("=" * 60)
            _add("")
    except Exception:
        pass

    # ── Tier 0b: PRIORITIES ───────────────────────────────────────────────
    try:
        priorities_row = await pool.fetchrow(
            "SELECT content FROM core_memory WHERE slot = 'priorities'"
        )
        if priorities_row and priorities_row["content"]:
            _add("[Otto] PRIORITIES (from Mev, ranked):")
            for line in priorities_row["content"].split("\n"):
                if line.strip():
                    _add(f"  {line.strip()}")
            _add("")
    except Exception:
        pass

    # ── Tier 0c: Active Directives from Mev ──────────────────────────────
    try:
        directive_rows = await pool.fetch(
            """SELECT directive, priority, category FROM mission_directives
               WHERE status = 'active'
               ORDER BY priority DESC LIMIT 10"""
        )
        if directive_rows:
            _add("[Otto] Active Directives from Mev:")
            for r in directive_rows:
                _add(f"  [P{r['priority']}] [{r['category'].upper()}] {r['directive']}")
            if not is_whatsapp:
                _add("  IMPORTANT: Every heartbeat action should serve one of these directives.")
            _add("")
    except Exception:
        pass

    # ── Tier 0d: Working memory (other core_memory slots) ────────────────
    try:
        wm_rows = await pool.fetch(
            "SELECT slot, content FROM core_memory "
            "WHERE content != '' AND slot NOT IN ('purpose', 'priorities') "
            "ORDER BY priority DESC"
        )
        if wm_rows:
            _add("[Otto] Working Memory:")
            for r in wm_rows:
                snippet = r["content"][:400]
                if not _add(f"  [{r['slot']}] {snippet}"):
                    break
            _add("")
    except Exception:
        pass

    # ── Tier 1: Identity facts (always) ──────────────────────────────────
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

    # ── Tier 2: Mission & goals (always) ─────────────────────────────────
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

    # ── Tier 3: Pending questions (Claude→Mev, always) ───────────────────
    pending_rows = await pool.fetch(
        """SELECT question, intent FROM pending_questions
           WHERE resolved_at IS NULL AND direction = 'claude_to_gemini'
           ORDER BY asked_at DESC LIMIT 5""",
    )
    if pending_rows:
        _add("[Otto] Pending questions (awaiting Mev):")
        for r in pending_rows:
            if not _add(f"  [{r['intent'].upper()}] {r['question']}"):
                break
        _add("")

    # ── Tier 3b: Cross-brain notes (Claude only) ─────────────────────────
    if not is_whatsapp:
        crossbrain_rows = await pool.fetch(
            """SELECT id, question, intent, context, metadata FROM pending_questions
               WHERE resolved_at IS NULL AND direction = 'gemini_to_claude'
               ORDER BY asked_at DESC LIMIT 10""",
        )
        if crossbrain_rows:
            _add("[Otto] Messages from WhatsApp brain (Gemini -> Claude):")
            _add("  These are things Mev said via WhatsApp that need your attention:")
            for r in crossbrain_rows:
                urgency = "NORMAL"
                if r["metadata"] and isinstance(r["metadata"], dict):
                    urgency = r["metadata"].get("urgency", "normal").upper()
                ctx = f"\n    Context: {r['context']}" if r["context"] else ""
                if not _add(f"  [{r['intent'].upper()}] [{urgency}] {r['question']}{ctx}"):
                    break
            _add("  ACTION: Read these, act on them, then acknowledge via POST /pending/<id>/resolve")
            _add("")

    # ── Tier 3c: Task queue (Claude only) ────────────────────────────────
    if not is_whatsapp:
        running_rows = await pool.fetch(
            """SELECT id, title, model, started_at FROM tasks
               WHERE status = 'running' ORDER BY started_at ASC LIMIT 5"""
        )
        done_rows = await pool.fetch(
            """SELECT id, title, exit_code FROM tasks
               WHERE status IN ('completed', 'failed') AND reviewed = FALSE
               ORDER BY completed_at DESC LIMIT 10"""
        )
        pending_count = await pool.fetchval(
            "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
        )
        if running_rows or done_rows or pending_count:
            _add("[Otto] Task Queue:")
            if running_rows:
                for r in running_rows:
                    _add(f"  [RUNNING] {r['title']} (model: {r['model']}, since: {r['started_at']})")
            if done_rows:
                for r in done_rows:
                    label = "DONE" if (r["exit_code"] or 0) == 0 else "FAIL"
                    _add(f"  [{label}] {r['title']} (id: {r['id']}) — NEEDS REVIEW")
                _add("  ACTION: Review output with GET /tasks/{id}, then POST /tasks/{id}/review")
            if pending_count:
                _add(f"  [QUEUE] {pending_count} pending task(s)")
            _add("")

    # ── Tier 3d: Reasoning chain (Claude only) ───────────────────────────
    if not is_whatsapp:
        try:
            chain_rows = await pool.fetch(
                """SELECT heartbeat_type, cycle_ts, reasoning, decisions,
                          expected, actual, outcome_match
                   FROM reasoning_chain
                   ORDER BY cycle_ts DESC LIMIT 5"""
            )
            if chain_rows:
                _add("[Otto] Recent reasoning chain (oldest → newest):")
                for r in reversed(chain_rows):
                    ts = r["cycle_ts"].strftime("%Y-%m-%d %H:%M") if r["cycle_ts"] else "?"
                    htype = r["heartbeat_type"]
                    lines_entry = [f"  [{htype} @ {ts}]"]
                    lines_entry.append(f"    WHY: {r['reasoning'][:300]}")
                    if r["decisions"]:
                        lines_entry.append(f"    DECIDED: {r['decisions'][:200]}")
                    if r["expected"]:
                        lines_entry.append(f"    EXPECTED: {r['expected'][:200]}")
                    if r["actual"]:
                        match_label = r["outcome_match"] or "?"
                        lines_entry.append(f"    ACTUAL [{match_label.upper()}]: {r['actual'][:200]}")
                    if not _add("\n".join(lines_entry)):
                        break
                _add("")
        except Exception:
            pass

    # ── Tier 4: Last session (if budget) ─────────────────────────────────
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

    # ── Tier 5: Recent events (fill budget) ──────────────────────────────
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

    # ── Tier 6: High-confidence semantic facts via A-RAG (fill budget) ──────
    # A-RAG surfaces broader, more diverse facts than static SQL ordering:
    # semantic strategy finds conceptually relevant items,
    # keyword strategy finds category-labeled facts,
    # structured strategy ensures high-importance items always surface.
    if used < max_tokens * 0.6:
        fact_limit = 20 if is_xlarge else (10 if is_large else 5)
        try:
            arag_result = await arag_search_internal(
                pool=pool,
                query="Otto mission priorities active work infrastructure current state decisions",
                limit=fact_limit,
                min_confidence=0.7,
                # Exclude tiers already covered by identity/mission sections
            )
            arag_facts = [
                r for r in arag_result["results"]
                if r["category"] not in ("identity", "mission", "goal", "decision")
            ]
            if arag_facts:
                _add("[Otto] Key facts:")
                for r in arag_facts:
                    if not _add(f"  [{r['category']}] {r['content'][:200]}"):
                        break
                _add("")
        except Exception as e:
            log.warning(f"A-RAG context retrieval failed, falling back to SQL: {e}")
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

    # ── Tier 6b: Active principles (MARS — fill budget) ──────────────────
    if used < max_tokens * 0.65:
        try:
            prin_rows = await pool.fetch(
                """SELECT principle, category, confidence FROM principles
                   WHERE confidence > 0.3
                   ORDER BY confidence DESC LIMIT 5""",
            )
            if prin_rows:
                _add("[Otto] Principles:")
                for r in prin_rows:
                    cat = r["category"]
                    conf = round(float(r["confidence"]), 2)
                    if not _add(f"  [{cat}] ({conf}) {r['principle']}"):
                        break
                _add("")
        except Exception:
            pass

    # ── Tier 6c: Structured cross-brain graph (G2CP — both brains) ───────
    if used < max_tokens * 0.75:
        try:
            graph_rows = await pool.fetch(
                """SELECT node_type, name, content, source_brain, priority, created_at
                   FROM cross_brain_graph
                   WHERE active = TRUE
                   ORDER BY priority DESC, created_at DESC
                   LIMIT 15""",
            )
            if graph_rows:
                _add("[Otto] Structured Graph (cross-brain nodes):")
                for r in graph_rows:
                    node_type = r["node_type"]
                    raw = r["content"]
                    if isinstance(raw, dict):
                        content = raw
                    elif isinstance(raw, str):
                        try:
                            content = json.loads(raw)
                        except Exception:
                            content = {"text": raw}
                    else:
                        content = {}
                    text = content.get("text") or content.get("value") or r["name"]
                    brain = r["source_brain"]
                    if node_type == "directive":
                        cat = content.get("category", "directive").upper()
                        if not _add(f"  [DIRECTIVE/{cat}] (from {brain}, P{r['priority']}) {text[:200]}"):
                            break
                    elif node_type == "decision":
                        by = content.get("decided_by", "?")
                        if not _add(f"  [DECISION] (by {by}, from {brain}) {text[:200]}"):
                            break
                    elif node_type == "task_state":
                        status = content.get("status", "?")
                        if not _add(f"  [TASK/{status.upper()}] {r['name'][:100]}"):
                            break
                    else:
                        key = content.get("key", r["name"])
                        if not _add(f"  [CONTEXT/{key}] {text[:150]}"):
                            break
                _add("")
        except Exception:
            pass

    # ── Tier 7: Knowledge graph (fill budget) ────────────────────────────
    if used < max_tokens * 0.8:
        graph_max = 10 if is_xlarge else 5
        graph_facts = []
        queries = ["Otto Mev projects decisions", "brands products goals"]
        if is_xlarge:
            queries.append("infrastructure services systems")
        for query in queries:
            facts = await graphiti_search(query, max_facts=graph_max)
            graph_facts.extend(facts)
        seen: set[str] = set()
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

    # ── Tier 8: Procedures (fill budget) ─────────────────────────────────
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

    if source == "compact":
        _add("[Otto] Context was compacted. Full memory available via API at localhost:8100.")

    pct = round(used / 200000 * 100, 1)
    _add(f"[Otto] Context: ~{used} tokens ({pct}% of 200k context, budget: {max_tokens})")

    result = "\n".join(lines)

    # ── Focus compression (arXiv 2601.07190) ─────────────────────────────
    # If the assembled context exceeds the compression threshold, apply
    # rule-based compression on least-critical sections first.
    threshold = settings.context_compression_threshold
    comp_target = settings.context_max_tokens
    if used > threshold and used > comp_target:
        compressed, orig_tok, comp_tok = compress_context_text(result, comp_target)
        if comp_tok < orig_tok:
            result = compressed
            result += f"\n[Context compressed: {orig_tok} → {comp_tok} tokens (Focus)]"
            log.info(f"Focus compression: {orig_tok} → {comp_tok} tokens ({round(comp_tok/orig_tok*100)}% of original)")

    return result

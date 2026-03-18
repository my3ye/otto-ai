from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..db import get_pool
from ..graphiti import graphiti_search
from ..context_builder import build_context_text, compress_context_text
from ..models import (
    ContextBriefing, SessionOut, SemanticMemoryOut,
    EpisodicEventOut, ProcedureOut,
)
from ..config import settings
from ..simplemem import compress_for_context
import logging

log = logging.getLogger("otto.context")

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
        """SELECT id, content, category, confidence, source, created_at, summary_content
           FROM semantic_memories
           WHERE category = 'identity' AND confidence >= 0.8
           ORDER BY confidence DESC LIMIT 20""",
    )
    identity_facts_raw = [SemanticMemoryOut(**dict(r)) for r in identity_rows]

    # High-confidence semantic facts
    fact_rows = await pool.fetch(
        """SELECT id, content, category, confidence, source, created_at, summary_content
           FROM semantic_memories
           WHERE category != 'identity' AND confidence >= 0.7
           ORDER BY confidence DESC, updated_at DESC LIMIT 30""",
    )
    high_confidence_facts_raw = [SemanticMemoryOut(**dict(r)) for r in fact_rows]

    # SimpleMem: apply 3-stage compression to reduce context token usage
    orig_id_chars = sum(len(m.content or '') for m in identity_facts_raw)
    orig_hc_chars = sum(len(m.content or '') for m in high_confidence_facts_raw)

    identity_facts_compressed, _, comp_id_chars = compress_for_context(
        identity_facts_raw, dedup_threshold=0.82
    )
    high_confidence_facts_compressed, _, comp_hc_chars = compress_for_context(
        high_confidence_facts_raw, dedup_threshold=0.82
    )
    identity_facts = identity_facts_compressed
    high_confidence_facts = high_confidence_facts_compressed

    total_orig = orig_id_chars + orig_hc_chars
    total_comp = comp_id_chars + comp_hc_chars
    log.info(
        f"SimpleMem briefing: identity {len(identity_facts_raw)}→{len(identity_facts)}, "
        f"facts {len(high_confidence_facts_raw)}→{len(high_confidence_facts)} | "
        f"chars {total_orig}→{total_comp} "
        f"({round(100*(1-total_comp/total_orig),1) if total_orig > 0 else 0}% reduction)"
    )

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


@router.get("/inject")
async def get_injection(
    max_tokens: int = Query(default=15000, description="Token budget for injection (30% of 200k = 60k ceiling)"),
    source: str = Query(default="startup", description="Session source: startup, compact, resume, whatsapp"),
):
    """Token-budgeted context injection for hooks.

    Returns a plain text string with prioritized context that fits within
    the token budget. The source parameter controls which sections are
    included (task queue, pending directives, and reasoning chain are
    omitted for source=whatsapp lightweight contexts).

    Priority order (all sources):
    0a. PURPOSE — always first
    0b. PRIORITIES — always included
    0c. Active directives from Mev
    0d. Working memory slots
    1.  Identity facts — always included
    2.  Mission & goals — always included
    3.  Pending questions — always included
    3b. Pending directives (full context only)
    3c. Task queue (full context only)
    3d. Reasoning chain (full context only)
    4.  Last session summary — if budget allows
    5.  Recent high-importance events — filled until budget
    6.  High-confidence semantic facts — filled until budget
    7.  Knowledge graph facts — filled until budget
    8.  Procedures — filled until budget
    """
    pool = await get_pool()
    context_text = await build_context_text(pool, max_tokens=max_tokens, source=source)

    # Persist injection asynchronously (fire-and-forget, never block the hook)
    token_estimate = len(context_text) // 4
    # Map source to a human-readable trigger label
    trigger_map = {
        "startup": "startup",
        "compact": "compact",
        "resume": "resume",
        "whatsapp": "whatsapp",
        "heartbeat": "heartbeat",
        "reflection": "reflection",
        "task": "task",
    }
    trigger = trigger_map.get(source, source)
    try:
        await pool.execute(
            """INSERT INTO context_injections (trigger, source, max_tokens, token_estimate, context_text)
               VALUES ($1, $2, $3, $4, $5)""",
            trigger, source, max_tokens, token_estimate, context_text,
        )
    except Exception as _persist_err:
        log.warning(f"context injection persist failed (non-fatal): {_persist_err}")

    return context_text


@router.get("/unified")
async def get_unified_context(
    max_tokens: int = Query(default=15000, description="Token budget for context"),
    source: str = Query(default="startup", description="Brain source: startup/compact/resume (Claude) or whatsapp (Gemini)"),
):
    """Unified structured context payload.

    Returns both a machine-readable structured payload AND the full context_text
    string for prompt injection. The source parameter controls which tiers are
    included (task queue, pending directives, reasoning chain are omitted for
    source=whatsapp lightweight contexts).

    Compare /context/unified?source=startup vs ?source=whatsapp to see tier differences.
    """
    pool = await get_pool()
    is_whatsapp = source == "whatsapp"

    # ── Tier 0: Core memory ───────────────────────────────────────────────
    purpose_row = None
    priorities_row = None
    wm_rows = []
    try:
        purpose_row = await pool.fetchrow(
            "SELECT content FROM core_memory WHERE slot = 'purpose'"
        )
        priorities_row = await pool.fetchrow(
            "SELECT content FROM core_memory WHERE slot = 'priorities'"
        )
        wm_raw = await pool.fetch(
            "SELECT slot, content, updated_at FROM core_memory "
            "WHERE content != '' AND slot NOT IN ('purpose', 'priorities') "
            "ORDER BY priority DESC"
        )
        wm_rows = [{"slot": r["slot"], "content": r["content"],
                    "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None}
                   for r in wm_raw]
    except Exception as e:
        log.warning(f"core_memory fetch error: {e}")

    # ── Tier 0c: Active directives ────────────────────────────────────────
    directives = []
    try:
        d_rows = await pool.fetch(
            """SELECT directive, priority, category FROM mission_directives
               WHERE status = 'active' ORDER BY priority DESC LIMIT 10"""
        )
        directives = [{"directive": r["directive"], "priority": r["priority"],
                       "category": r["category"]} for r in d_rows]
    except Exception as e:
        log.warning(f"mission_directives fetch error: {e}")

    # ── Tier 1+2: Identity and mission facts ──────────────────────────────
    identity_facts = []
    mission_facts = []
    try:
        id_rows = await pool.fetch(
            """SELECT content, category, confidence FROM semantic_memories
               WHERE category = 'identity' AND confidence >= 0.8
               ORDER BY confidence DESC LIMIT 10"""
        )
        identity_facts = [{"content": r["content"], "confidence": float(r["confidence"])}
                          for r in id_rows]

        m_rows = await pool.fetch(
            """SELECT content, category, confidence FROM semantic_memories
               WHERE category IN ('mission', 'goal', 'decision') AND confidence >= 0.7
               ORDER BY confidence DESC, created_at DESC LIMIT 15"""
        )
        mission_facts = [{"content": r["content"], "category": r["category"],
                          "confidence": float(r["confidence"])} for r in m_rows]
    except Exception as e:
        log.warning(f"semantic facts fetch error: {e}")

    # ── Tier 3: Pending questions (Otto→Mev) ──────────────────────────────
    pending_questions = []
    try:
        pq_rows = await pool.fetch(
            """SELECT question, intent, asked_at FROM pending_questions
               WHERE resolved_at IS NULL AND direction IN ('claude_to_gemini', 'outbound')
               ORDER BY asked_at DESC LIMIT 5"""
        )
        pending_questions = [{"question": r["question"], "intent": r["intent"],
                              "asked_at": r["asked_at"].isoformat() if r["asked_at"] else None}
                             for r in pq_rows]
    except Exception as e:
        log.warning(f"pending questions fetch error: {e}")

    # ── Tier 3b/3c/3d: Full-context-only sections ────────────────────────
    pending_directives = []
    task_queue = {"running": [], "unreviewed": [], "pending_count": 0}
    reasoning_chain = []
    if not is_whatsapp:
        try:
            cb_rows = await pool.fetch(
                """SELECT question, intent, context, metadata, asked_at
                   FROM pending_questions
                   WHERE resolved_at IS NULL AND direction IN ('gemini_to_claude', 'inbound')
                   ORDER BY asked_at DESC LIMIT 10"""
            )
            pending_directives = [
                {"content": r["question"], "type": r["intent"],
                 "context": r["context"],
                 "urgency": (r["metadata"] or {}).get("urgency", "normal"),
                 "asked_at": r["asked_at"].isoformat() if r["asked_at"] else None}
                for r in cb_rows
            ]
        except Exception as e:
            log.warning(f"pending directives fetch error: {e}")

        try:
            t_running = await pool.fetch(
                "SELECT id, title, model, started_at FROM tasks "
                "WHERE status = 'running' ORDER BY started_at ASC LIMIT 5"
            )
            t_done = await pool.fetch(
                "SELECT id, title, exit_code FROM tasks "
                "WHERE status IN ('completed', 'failed') AND reviewed = FALSE "
                "ORDER BY completed_at DESC LIMIT 10"
            )
            t_pending = await pool.fetchval(
                "SELECT COUNT(*) FROM tasks WHERE status = 'pending'"
            )
            task_queue = {
                "running": [{"id": str(r["id"]), "title": r["title"],
                             "model": r["model"],
                             "since": r["started_at"].isoformat() if r["started_at"] else None}
                            for r in t_running],
                "unreviewed": [{"id": str(r["id"]), "title": r["title"],
                                "status": "done" if (r["exit_code"] or 0) == 0 else "failed"}
                               for r in t_done],
                "pending_count": t_pending or 0,
            }
        except Exception as e:
            log.warning(f"task queue fetch error: {e}")

        try:
            rc_rows = await pool.fetch(
                """SELECT heartbeat_type, cycle_ts, reasoning, decisions, expected
                   FROM reasoning_chain ORDER BY cycle_ts DESC LIMIT 5"""
            )
            reasoning_chain = [
                {"type": r["heartbeat_type"],
                 "ts": r["cycle_ts"].isoformat() if r["cycle_ts"] else None,
                 "reasoning": r["reasoning"][:300] if r["reasoning"] else None,
                 "decisions": r["decisions"][:200] if r["decisions"] else None,
                 "expected": r["expected"][:200] if r["expected"] else None}
                for r in reversed(rc_rows)
            ]
        except Exception as e:
            log.warning(f"reasoning chain fetch error: {e}")

    # ── Tier 4: Last session ──────────────────────────────────────────────
    last_session_summary = None
    try:
        ls_row = await pool.fetchrow(
            """SELECT summary, ended_at FROM sessions
               WHERE ended_at IS NOT NULL AND summary IS NOT NULL
               ORDER BY ended_at DESC LIMIT 1"""
        )
        if ls_row:
            last_session_summary = {
                "summary": ls_row["summary"][:500],
                "ended_at": ls_row["ended_at"].isoformat() if ls_row["ended_at"] else None,
            }
    except Exception as e:
        log.warning(f"last session fetch error: {e}")

    # ── G2CP: Structured graph nodes ──────────────────────────────────────
    structured_graph = []
    try:
        sg_rows = await pool.fetch(
            """SELECT id, node_type, name, content, source_brain, priority, created_at
               FROM cross_brain_graph
               WHERE active = TRUE
               ORDER BY priority DESC, created_at DESC
               LIMIT 20"""
        )
        import json as _json
        structured_graph = []
        for r in sg_rows:
            raw = r["content"]
            if isinstance(raw, dict):
                content = raw
            elif isinstance(raw, str):
                try:
                    content = _json.loads(raw)
                except Exception:
                    content = {"text": raw}
            else:
                content = {}
            structured_graph.append({
                "id": str(r["id"]),
                "node_type": r["node_type"],
                "name": r["name"],
                "content": content,
                "source_brain": r["source_brain"],
                "priority": r["priority"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            })
    except Exception as e:
        log.warning(f"structured_graph fetch error: {e}")

    # ── Tier 5: Recent events ─────────────────────────────────────────────
    recent_events = []
    try:
        ev_rows = await pool.fetch(
            """SELECT content, event_type, importance, created_at FROM episodic_events
               WHERE importance >= 5 ORDER BY created_at DESC LIMIT 20"""
        )
        recent_events = [
            {"content": r["content"][:300], "type": r["event_type"],
             "importance": r["importance"],
             "ts": r["created_at"].isoformat() if r["created_at"] else None}
            for r in ev_rows
        ]
    except Exception as e:
        log.warning(f"recent events fetch error: {e}")

    # ── Full text (same as /context/inject, for prompt injection) ─────────
    context_text = await build_context_text(pool, max_tokens=max_tokens, source=source)
    token_estimate = len(context_text) // 4

    return {
        "source": source,
        "max_tokens": max_tokens,
        "token_estimate": token_estimate,
        "parity_note": (
            "Lightweight (source=whatsapp) receives tiers 0a-0d, 1-6 + structured_graph (no task queue / directives / reasoning). "
            "Full (source=startup) receives all tiers. Core identity+mission+directives+WM+structured_graph are shared."
        ),
        # Shared tiers (both brains)
        "purpose": purpose_row["content"] if purpose_row else None,
        "priorities": priorities_row["content"] if priorities_row else None,
        "working_memory": wm_rows,
        "active_directives": directives,
        "identity_facts": identity_facts,
        "mission_facts": mission_facts,
        "pending_questions": pending_questions,
        "last_session": last_session_summary,
        "recent_events": recent_events,
        # G2CP: Structured graph nodes
        "structured_graph": structured_graph,
        # Full-context-only tiers
        "pending_directives": pending_directives,
        "cross_brain_notes": pending_directives,  # backward compat alias
        "task_queue": task_queue if not is_whatsapp else None,
        "reasoning_chain": reasoning_chain if not is_whatsapp else None,
        # Full text for prompt injection
        "context_text": context_text,
    }


# ── /context/compress ─────────────────────────────────────────────────────────

class CompressRequest(BaseModel):
    text: str
    target_tokens: int = settings.context_max_tokens


class CompressResponse(BaseModel):
    compressed_text: str
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    was_compressed: bool


@router.post("/compress", response_model=CompressResponse)
async def compress_context(req: CompressRequest):
    """Focus-style rule-based context compression (arXiv 2601.07190).

    Accepts raw context text and compresses it to target_tokens by
    trimming least-critical sections (events, facts, graph, procedures)
    first. High-priority sections (PURPOSE, PRIORITIES, Directives,
    Working Memory, Identity, Task Queue) are never modified.
    """
    compressed, orig, comp = compress_context_text(req.text, req.target_tokens)
    return CompressResponse(
        compressed_text=compressed,
        original_tokens=orig,
        compressed_tokens=comp,
        compression_ratio=round(comp / orig, 3) if orig > 0 else 1.0,
        was_compressed=comp < orig,
    )


# ── /context/injections — history browsing ────────────────────────────────────

@router.get("/injections")
async def list_injections(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    trigger: str | None = Query(default=None),
):
    """List context injection history (newest first).

    Returns summary rows (no full context_text) for efficient pagination.
    """
    pool = await get_pool()
    where = "WHERE trigger = $3" if trigger else ""
    params: list = [limit, offset]
    if trigger:
        params.append(trigger)

    rows = await pool.fetch(
        f"""SELECT id, trigger, source, max_tokens, token_estimate,
                   LEFT(context_text, 200) AS preview,
                   LENGTH(context_text) AS char_len,
                   created_at
            FROM context_injections
            {where}
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2""",
        *params,
    )
    total = await pool.fetchval(
        f"SELECT COUNT(*) FROM context_injections {where}",
        *(params[2:] if trigger else []),
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": str(r["id"]),
                "trigger": r["trigger"],
                "source": r["source"],
                "max_tokens": r["max_tokens"],
                "token_estimate": r["token_estimate"],
                "char_len": r["char_len"],
                "preview": r["preview"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ],
    }


@router.get("/injections/{injection_id}")
async def get_injection_detail(injection_id: str):
    """Get full context text for a single injection."""
    import uuid as _uuid
    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT id, trigger, source, max_tokens, token_estimate, context_text, created_at
           FROM context_injections WHERE id = $1""",
        _uuid.UUID(injection_id),
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Injection not found")
    return {
        "id": str(row["id"]),
        "trigger": row["trigger"],
        "source": row["source"],
        "max_tokens": row["max_tokens"],
        "token_estimate": row["token_estimate"],
        "context_text": row["context_text"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.get("/injections/{injection_id}/diff")
async def get_injection_diff(injection_id: str):
    """Compute unified diff between this injection and the previous one (same trigger type)."""
    import uuid as _uuid
    import difflib
    pool = await get_pool()

    row = await pool.fetchrow(
        """SELECT id, trigger, source, token_estimate, context_text, created_at
           FROM context_injections WHERE id = $1""",
        _uuid.UUID(injection_id),
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Injection not found")

    # Find previous injection of same trigger type
    prev_row = await pool.fetchrow(
        """SELECT id, token_estimate, context_text, created_at
           FROM context_injections
           WHERE trigger = $1 AND created_at < $2
           ORDER BY created_at DESC
           LIMIT 1""",
        row["trigger"],
        row["created_at"],
    )

    current_lines = row["context_text"].splitlines(keepends=True)

    if not prev_row:
        return {
            "has_previous": False,
            "diff": None,
            "token_delta": None,
            "current": {
                "id": str(row["id"]),
                "trigger": row["trigger"],
                "token_estimate": row["token_estimate"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            },
            "previous": None,
        }

    prev_lines = prev_row["context_text"].splitlines(keepends=True)
    diff_lines = list(difflib.unified_diff(
        prev_lines,
        current_lines,
        fromfile=f"injection/{str(prev_row['id'])[:8]}",
        tofile=f"injection/{str(row['id'])[:8]}",
        lineterm="",
    ))

    return {
        "has_previous": True,
        "diff": "".join(diff_lines),
        "token_delta": row["token_estimate"] - prev_row["token_estimate"],
        "lines_added": sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++")),
        "lines_removed": sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---")),
        "current": {
            "id": str(row["id"]),
            "trigger": row["trigger"],
            "token_estimate": row["token_estimate"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        },
        "previous": {
            "id": str(prev_row["id"]),
            "token_estimate": prev_row["token_estimate"],
            "created_at": prev_row["created_at"].isoformat() if prev_row["created_at"] else None,
        },
    }

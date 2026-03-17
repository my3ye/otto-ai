"""
Omnisearch — cross-system search and cleanup for Otto's full memory stack.

POST /search/all
  Queries across ALL memory systems in a single call:
    - semantic_memories (vector + text search)
    - episodic_events (text search)
    - tasks (title + prompt search)
    - procedures (name + description)
    - whatsapp_messages / conversations (text search)
    - mission_directives (text search)
    - principles (text search)
    - research_notes (text search)
    - filesystem task logs (grep)

GET /cleanup/audit
  Surfaces:
    - Duplicate semantic memories (high cosine similarity)
    - Orphaned tasks (completed but no review record)
    - Stale directives (contradicted by newer ones)
    - Stale pending questions (open for >7 days)
    - Tasks with no progress / stuck in running state
"""

import logging
import os
import subprocess
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_pool
from ..embeddings import get_embedding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["omnisearch"])
cleanup_router = APIRouter(prefix="/cleanup", tags=["cleanup"])


# ── Models ──────────────────────────────────────────────────────────

class OmniSearchRequest(BaseModel):
    query: str
    limit_per_source: int = 5
    sources: Optional[List[str]] = None  # None = all sources
    include_logs: bool = False  # filesystem log grep (slower)


class SearchHit(BaseModel):
    source: str       # e.g. "semantic", "episodic", "tasks"
    id: Optional[str]
    content: str
    score: Optional[float]   # similarity score if available
    created_at: Optional[str]
    metadata: Optional[dict] = None


class OmniSearchResponse(BaseModel):
    query: str
    total_hits: int
    sources_searched: List[str]
    results: List[SearchHit]
    elapsed_ms: Optional[float]


# ── Helpers ──────────────────────────────────────────────────────────

def _row_to_str(row) -> str:
    """Safely convert a DB row value to string."""
    if row is None:
        return ""
    return str(row)


def _ilike_conditions(column: str, query: str, param_start: int) -> tuple:
    """
    Build AND ILIKE conditions for a multi-word query.
    For "encrypt three levels", returns:
      ("col ILIKE $N AND col ILIKE $M AND col ILIKE $K", ["%encrypt%", "%three%", "%levels%"])
    For single words: ("col ILIKE $N", ["%word%"])
    """
    words = [w.strip() for w in query.split() if len(w.strip()) >= 3]
    if not words:
        words = [query]
    params = [f"%{w}%" for w in words]
    conditions = " AND ".join(
        f"{column} ILIKE ${param_start + i}" for i in range(len(params))
    )
    return conditions, params


async def _search_semantic(pool, query: str, embedding: list, limit: int) -> List[SearchHit]:
    """Search semantic memories via vector similarity + text fallback."""
    hits = []
    # Try vector search first, fall back to text
    if embedding:
        try:
            rows = await pool.fetch(
                """
                SELECT id, content, category, source, created_at,
                       1 - (summary_embedding_hv <=> $1::halfvec) AS score
                FROM semantic_memories
                WHERE archived = FALSE AND deleted_at IS NULL
                  AND summary_embedding_hv IS NOT NULL
                ORDER BY summary_embedding_hv <=> $1::halfvec
                LIMIT $2
                """,
                embedding, limit
            )
            for r in rows:
                hits.append(SearchHit(
                    source="semantic",
                    id=str(r["id"]),
                    content=r["content"][:500],
                    score=round(float(r["score"]), 4) if r["score"] else None,
                    created_at=str(r["created_at"]),
                    metadata={"category": r["category"], "mem_source": r["source"]},
                ))
            return hits
        except Exception as e:
            logger.warning(f"semantic vector search failed: {e}")
    # Text fallback (multi-word AND ILIKE)
    try:
        conds, wparams = _ilike_conditions("content", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, content, category, source, created_at
            FROM semantic_memories
            WHERE archived = FALSE AND deleted_at IS NULL
              AND {conds}
            ORDER BY created_at DESC LIMIT ${len(wparams) + 1}
            """,
            *wparams, limit
        )
        for r in rows:
            hits.append(SearchHit(
                source="semantic",
                id=str(r["id"]),
                content=r["content"][:500],
                score=None,
                created_at=str(r["created_at"]),
                metadata={"category": r["category"], "mem_source": r["source"]},
            ))
    except Exception as e2:
        logger.warning(f"semantic text fallback failed: {e2}")
    return hits


async def _search_episodic(pool, query: str, limit: int) -> List[SearchHit]:
    conds, wparams = _ilike_conditions("content", query, 1)
    rows = await pool.fetch(
        f"""
        SELECT id, content, event_type, importance, created_at
        FROM episodic_events
        WHERE {conds}
        ORDER BY created_at DESC LIMIT ${len(wparams) + 1}
        """,
        *wparams, limit
    )
    return [
        SearchHit(
            source="episodic",
            id=str(r["id"]),
            content=r["content"][:500],
            score=None,
            created_at=str(r["created_at"]),
            metadata={"event_type": r["event_type"], "importance": r["importance"]},
        )
        for r in rows
    ]


async def _search_tasks(pool, query: str, limit: int) -> List[SearchHit]:
    conds, wparams = _ilike_conditions("title", query, 1)
    pconds, _ = _ilike_conditions("prompt", query, 1)
    rows = await pool.fetch(
        f"""
        SELECT id, title, prompt, status, priority, created_at
        FROM tasks
        WHERE ({conds}) OR ({pconds})
        ORDER BY created_at DESC LIMIT ${len(wparams) + 1}
        """,
        *wparams, limit
    )
    return [
        SearchHit(
            source="tasks",
            id=str(r["id"]),
            content=f"[{r['status']}] {r['title']}: {(r['prompt'] or '')[:300]}",
            score=None,
            created_at=str(r["created_at"]),
            metadata={"status": r["status"], "priority": r["priority"]},
        )
        for r in rows
    ]


async def _search_procedures(pool, query: str, limit: int) -> List[SearchHit]:
    conds, wparams = _ilike_conditions("name", query, 1)
    dconds, _ = _ilike_conditions("description", query, 1)
    sconds, _ = _ilike_conditions("steps::text", query, 1)
    rows = await pool.fetch(
        f"""
        SELECT id, name, description, steps, created_at
        FROM procedures
        WHERE ({conds}) OR ({dconds}) OR ({sconds})
        ORDER BY created_at DESC LIMIT ${len(wparams) + 1}
        """,
        *wparams, limit
    )
    return [
        SearchHit(
            source="procedures",
            id=str(r["id"]),
            content=f"{r['name']}: {r['description'] or ''}",
            score=None,
            created_at=str(r["created_at"]),
        )
        for r in rows
    ]


async def _search_conversations(pool, query: str, limit: int) -> List[SearchHit]:
    """Search whatsapp_messages and conversations tables."""
    hits = []
    # WhatsApp messages
    try:
        conds, wparams = _ilike_conditions("body", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, body, sender, timestamp
            FROM whatsapp_messages
            WHERE {conds}
            ORDER BY timestamp DESC LIMIT ${len(wparams) + 1}
            """,
            *wparams, limit
        )
        for r in rows:
            hits.append(SearchHit(
                source="whatsapp",
                id=str(r["id"]),
                content=f"[{r['sender']}] {r['body'][:400]}",
                score=None,
                created_at=str(r["timestamp"]),
            ))
    except Exception as e:
        logger.warning(f"whatsapp search failed: {e}")

    # conversations table
    try:
        cconds, cwparams = _ilike_conditions("content", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, content, role, created_at
            FROM conversations
            WHERE {cconds}
            ORDER BY created_at DESC LIMIT ${len(cwparams) + 1}
            """,
            *cwparams, limit
        )
        for r in rows:
            hits.append(SearchHit(
                source="conversations",
                id=str(r["id"]),
                content=f"[{r['role']}] {r['content'][:400]}",
                score=None,
                created_at=str(r["created_at"]),
            ))
    except Exception as e:
        logger.warning(f"conversations search failed: {e}")
    return hits


async def _search_directives(pool, query: str, limit: int) -> List[SearchHit]:
    try:
        dconds, dparams = _ilike_conditions("directive_text", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, directive_text, priority, status, created_at
            FROM mission_directives
            WHERE {dconds}
            ORDER BY created_at DESC LIMIT ${len(dparams) + 1}
            """,
            *dparams, limit
        )
        return [
            SearchHit(
                source="directives",
                id=str(r["id"]),
                content=f"[P{r['priority']}][{r['status']}] {r['directive_text'][:400]}",
                score=None,
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"directives search failed: {e}")
        return []


async def _search_principles(pool, query: str, limit: int) -> List[SearchHit]:
    try:
        pconds, pparams = _ilike_conditions("content", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, content, category, weight, created_at
            FROM principles
            WHERE {pconds}
            ORDER BY weight DESC, created_at DESC LIMIT ${len(pparams) + 1}
            """,
            *pparams, limit
        )
        return [
            SearchHit(
                source="principles",
                id=str(r["id"]),
                content=f"[{r['category']}] {r['content'][:400]}",
                score=None,
                created_at=str(r["created_at"]),
                metadata={"weight": r["weight"]},
            )
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"principles search failed: {e}")
        return []


async def _search_research_notes(pool, query: str, limit: int) -> List[SearchHit]:
    try:
        rconds, rparams = _ilike_conditions("title", query, 1)
        rcconds, _ = _ilike_conditions("content", query, 1)
        rtconds, _ = _ilike_conditions("topic", query, 1)
        rows = await pool.fetch(
            f"""
            SELECT id, title, content, topic, created_at
            FROM research_notes
            WHERE ({rconds}) OR ({rcconds}) OR ({rtconds})
            ORDER BY created_at DESC LIMIT ${len(rparams) + 1}
            """,
            *rparams, limit
        )
        return [
            SearchHit(
                source="research_notes",
                id=str(r["id"]),
                content=f"[{r['topic']}] {r['title']}: {r['content'][:300]}",
                score=None,
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
    except Exception as e:
        logger.warning(f"research_notes search failed: {e}")
        return []


def _search_logs(query: str, limit: int) -> List[SearchHit]:
    """Grep task logs and heartbeat logs for the query."""
    hits = []
    log_dirs = [
        os.path.expanduser("~/otto/logs/tasks"),
        os.path.expanduser("~/otto/logs"),
    ]
    for log_dir in log_dirs:
        if not os.path.isdir(log_dir):
            continue
        try:
            result = subprocess.run(
                ["grep", "-r", "-i", "-l", "--include=*.log", query, log_dir],
                capture_output=True, text=True, timeout=5
            )
            files = result.stdout.strip().split("\n")[:limit]
            for fpath in files:
                if not fpath.strip():
                    continue
                try:
                    # Get matching lines
                    grep_result = subprocess.run(
                        ["grep", "-i", "-m", "3", query, fpath],
                        capture_output=True, text=True, timeout=3
                    )
                    excerpt = grep_result.stdout[:400].strip()
                    mtime = os.path.getmtime(fpath)
                    dt = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
                    hits.append(SearchHit(
                        source="log_file",
                        id=None,
                        content=f"{os.path.basename(fpath)}: {excerpt}",
                        score=None,
                        created_at=dt,
                        metadata={"path": fpath},
                    ))
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"log search failed for {log_dir}: {e}")
    return hits[:limit]


# ── Routes ──────────────────────────────────────────────────────────

ALL_SOURCES = [
    "semantic", "episodic", "tasks", "procedures",
    "conversations", "directives", "principles", "research_notes"
]


@router.post("/all", response_model=OmniSearchResponse)
async def cross_system_search(req: OmniSearchRequest):
    """
    Cross-system search across Otto's full memory stack.

    Queries: semantic memories, episodic events, tasks, procedures,
    conversations (WhatsApp + DB), mission directives, principles,
    research notes, and optionally filesystem task/heartbeat logs.

    Results are returned ranked by source relevance and recency.
    Use `sources` to restrict to specific subsystems.
    Use `include_logs=true` to also grep filesystem logs (slower).
    """
    import time
    t0 = time.monotonic()
    pool = await get_pool()

    sources = req.sources or ALL_SOURCES
    limit = req.limit_per_source
    query = req.query

    # Get embedding for semantic search
    embedding = None
    if "semantic" in sources:
        try:
            embedding = await get_embedding(query)
        except Exception as e:
            logger.warning(f"embedding failed, semantic search will use text fallback: {e}")

    results: List[SearchHit] = []
    sources_searched: List[str] = []

    source_fns = {
        "semantic": lambda: _search_semantic(pool, query, embedding or [], limit) if "semantic" in sources else None,
        "episodic": lambda: _search_episodic(pool, query, limit),
        "tasks": lambda: _search_tasks(pool, query, limit),
        "procedures": lambda: _search_procedures(pool, query, limit),
        "conversations": lambda: _search_conversations(pool, query, limit),
        "directives": lambda: _search_directives(pool, query, limit),
        "principles": lambda: _search_principles(pool, query, limit),
        "research_notes": lambda: _search_research_notes(pool, query, limit),
    }

    for src in sources:
        if src not in source_fns:
            continue
        try:
            fn = source_fns[src]
            if fn is None:
                continue
            hits = await fn()
            results.extend(hits)
            if hits:
                sources_searched.append(src)
        except Exception as e:
            logger.warning(f"source {src} search failed: {e}")

    # Filesystem log search (optional, slower)
    if req.include_logs:
        log_hits = _search_logs(query, limit)
        results.extend(log_hits)
        if log_hits:
            sources_searched.append("logs")

    # Sort: scored hits first (by score desc), then by recency
    scored = sorted([h for h in results if h.score is not None], key=lambda h: h.score or 0, reverse=True)
    unscored = sorted(
        [h for h in results if h.score is None],
        key=lambda h: h.created_at or "",
        reverse=True
    )
    final = scored + unscored

    elapsed = round((time.monotonic() - t0) * 1000, 1)
    return OmniSearchResponse(
        query=query,
        total_hits=len(final),
        sources_searched=sources_searched,
        results=final,
        elapsed_ms=elapsed,
    )


# ── Cleanup / Audit ─────────────────────────────────────────────────

class CleanupIssue(BaseModel):
    issue_type: str     # duplicate|orphan|stale|stuck|contradiction
    severity: str       # low|medium|high
    description: str
    affected_ids: List[str]
    suggested_action: str


class CleanupAuditResponse(BaseModel):
    total_issues: int
    issues: List[CleanupIssue]
    stats: dict
    generated_at: str


@cleanup_router.get("/audit", response_model=CleanupAuditResponse)
async def cleanup_audit():
    """
    Automated cleanup audit across Otto's memory stack.

    Surfaces:
      - Duplicate semantic memories (cosine sim > 0.95)
      - Orphaned tasks (no review, completed >24h ago)
      - Stale pending questions (open >7 days)
      - Stuck tasks (status=running >2h)
      - Semantic memories with very low utility score (<0.1)
      - Tasks failed with no retry
    """
    pool = await get_pool()
    issues: List[CleanupIssue] = []
    stats = {}

    # 1. Duplicate semantic memories (high similarity pairs)
    try:
        dupes = await pool.fetch(
            """
            SELECT a.id AS id_a, b.id AS id_b,
                   a.content AS content_a,
                   1 - (a.summary_embedding_hv <=> b.summary_embedding_hv) AS sim
            FROM semantic_memories a
            JOIN semantic_memories b ON a.id < b.id
            WHERE a.archived = FALSE AND a.deleted_at IS NULL
              AND b.archived = FALSE AND b.deleted_at IS NULL
              AND a.summary_embedding_hv IS NOT NULL
              AND b.summary_embedding_hv IS NOT NULL
              AND 1 - (a.summary_embedding_hv <=> b.summary_embedding_hv) > 0.95
            LIMIT 30
            """
        )
        if dupes:
            for d in dupes:
                issues.append(CleanupIssue(
                    issue_type="duplicate",
                    severity="medium",
                    description=f"Semantic memory duplicate pair (sim={round(float(d['sim']),3)}): '{d['content_a'][:120]}...'",
                    affected_ids=[str(d["id_a"]), str(d["id_b"])],
                    suggested_action="Archive the older/lower-confidence entry via DELETE /semantic/{id}",
                ))
        stats["semantic_duplicates"] = len(dupes)
    except Exception as e:
        logger.warning(f"duplicate check failed: {e}")
        stats["semantic_duplicates"] = "error"

    # 2. Orphaned tasks (completed but never reviewed, >24h old)
    try:
        orphans = await pool.fetch(
            """
            SELECT id, title, status, updated_at
            FROM tasks
            WHERE status = 'completed'
              AND reviewed = FALSE
              AND updated_at < NOW() - INTERVAL '24 hours'
            ORDER BY updated_at DESC
            LIMIT 20
            """
        )
        if orphans:
            issues.append(CleanupIssue(
                issue_type="orphan",
                severity="low",
                description=f"{len(orphans)} tasks completed >24h ago with no review",
                affected_ids=[str(r["id"]) for r in orphans],
                suggested_action="Review each via POST /tasks/{id}/review or bulk-mark as reviewed",
            ))
        stats["orphaned_tasks"] = len(orphans)
    except Exception as e:
        logger.warning(f"orphan task check failed: {e}")
        stats["orphaned_tasks"] = "error"

    # 3. Stale pending questions (open > 7 days)
    try:
        stale_q = await pool.fetch(
            """
            SELECT id, question, asked_at
            FROM pending_questions
            WHERE resolved_at IS NULL
              AND asked_at < NOW() - INTERVAL '7 days'
            ORDER BY asked_at ASC
            LIMIT 10
            """
        )
        if stale_q:
            issues.append(CleanupIssue(
                issue_type="stale",
                severity="medium",
                description=f"{len(stale_q)} pending questions unresolved for >7 days",
                affected_ids=[str(r["id"]) for r in stale_q],
                suggested_action="Resolve or archive via PATCH /pending/{id}",
            ))
        stats["stale_pending_questions"] = len(stale_q)
    except Exception as e:
        logger.warning(f"stale question check failed: {e}")
        stats["stale_pending_questions"] = "error"

    # 4. Stuck tasks (status=running for >2 hours)
    try:
        stuck = await pool.fetch(
            """
            SELECT id, title, status, updated_at, pid
            FROM tasks
            WHERE status = 'running'
              AND updated_at < NOW() - INTERVAL '2 hours'
            ORDER BY updated_at ASC
            LIMIT 10
            """
        )
        if stuck:
            issues.append(CleanupIssue(
                issue_type="stuck",
                severity="high",
                description=f"{len(stuck)} tasks have been in 'running' state for >2 hours",
                affected_ids=[str(r["id"]) for r in stuck],
                suggested_action="Check process with `kill -0 <pid>`, mark failed if dead via POST /tasks/{id}/complete with exit_code=1",
            ))
        stats["stuck_tasks"] = len(stuck)
    except Exception as e:
        logger.warning(f"stuck task check failed: {e}")
        stats["stuck_tasks"] = "error"

    # 5. Low-utility semantic memories (utility_score < 0.1, not recently accessed)
    try:
        low_util = await pool.fetch(
            """
            SELECT id, content, utility_score, last_retrieved_at, created_at
            FROM semantic_memories
            WHERE archived = FALSE AND deleted_at IS NULL
              AND utility_score < 0.1
              AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '14 days')
              AND created_at < NOW() - INTERVAL '7 days'
            ORDER BY utility_score ASC, created_at ASC
            LIMIT 20
            """
        )
        if low_util:
            issues.append(CleanupIssue(
                issue_type="stale",
                severity="low",
                description=f"{len(low_util)} semantic memories with utility_score <0.1, not accessed in 14+ days",
                affected_ids=[str(r["id"]) for r in low_util],
                suggested_action="Archive via POST /memory/maintenance or DELETE /semantic/{id}",
            ))
        stats["low_utility_memories"] = len(low_util)
    except Exception as e:
        logger.warning(f"low-utility memory check failed: {e}")
        stats["low_utility_memories"] = "error"

    # 6. Failed tasks with no retry / marked reviewed
    try:
        failed_no_retry = await pool.fetch(
            """
            SELECT id, title, created_at, exit_code
            FROM tasks
            WHERE status = 'failed'
              AND reviewed = FALSE
              AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
        if failed_no_retry:
            issues.append(CleanupIssue(
                issue_type="orphan",
                severity="medium",
                description=f"{len(failed_no_retry)} failed tasks in last 7 days with no review or retry",
                affected_ids=[str(r["id"]) for r in failed_no_retry],
                suggested_action="Review failure reason, retry if recoverable, or mark reviewed if accepted",
            ))
        stats["failed_unreviewed_tasks"] = len(failed_no_retry)
    except Exception as e:
        logger.warning(f"failed task check failed: {e}")
        stats["failed_unreviewed_tasks"] = "error"

    # 7. Memory count summary
    try:
        mem_counts = await pool.fetchrow(
            """
            SELECT
                COUNT(*) FILTER (WHERE archived = FALSE AND deleted_at IS NULL) AS active,
                COUNT(*) FILTER (WHERE archived = TRUE OR deleted_at IS NOT NULL) AS archived,
                COUNT(*) AS total
            FROM semantic_memories
            """
        )
        stats["memory_total"] = mem_counts["total"]
        stats["memory_active"] = mem_counts["active"]
        stats["memory_archived"] = mem_counts["archived"]
    except Exception as e:
        logger.warning(f"memory count failed: {e}")

    # 8. Episodic event count
    try:
        ep_count = await pool.fetchval("SELECT COUNT(*) FROM episodic_events")
        stats["episodic_events"] = ep_count
    except Exception:
        pass

    # 9. Task summary
    try:
        task_stats = await pool.fetch(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        )
        stats["tasks"] = {r["status"]: r["cnt"] for r in task_stats}
    except Exception:
        pass

    return CleanupAuditResponse(
        total_issues=len(issues),
        issues=issues,
        stats=stats,
        generated_at=datetime.now(tz=timezone.utc).isoformat(),
    )

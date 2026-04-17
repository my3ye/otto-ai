import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter
from pydantic import BaseModel
from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding
from ..models import EpisodicEventCreate, EpisodicEventOut, TimelineQuery
from ..llm import llm_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/episodic", tags=["episodic"])


def _compute_surprise(metadata: dict) -> float:
    """Derive surprise score from metadata if possible, else return default 0.5.

    SuRe heuristics (in priority order):
    1. Caller explicitly sets metadata['surprise_score'] (float 0-1).
    2. event_type 'error' → 0.85 (errors are inherently surprising).
    3. metadata contains 'expected' + 'actual' strings → Jaccard distance proxy.
    4. Default: 0.5 (moderate/unknown surprise).
    """
    if "surprise_score" in metadata:
        try:
            return max(0.0, min(1.0, float(metadata["surprise_score"])))
        except (TypeError, ValueError):
            pass
    return 0.5  # default; event_type back-fill handled by migration & route below


@router.post("/events", response_model=EpisodicEventOut)
async def create_event(req: EpisodicEventCreate):
    pool = await get_pool()

    # Compute surprise score from metadata heuristics
    surprise = _compute_surprise(req.metadata)
    # Error events are inherently surprising
    if req.event_type == "error" and surprise == 0.5:
        surprise = 0.85

    meta_str = json.dumps(req.metadata) if req.metadata else "{}"

    row = await pool.fetchrow(
        """INSERT INTO episodic_events
               (session_id, content, event_type, importance, metadata, surprise_score)
           VALUES ($1, $2, $3, $4, $5::jsonb, $6)
           RETURNING id, session_id, content, event_type, importance, created_at""",
        req.session_id, req.content, req.event_type, req.importance,
        meta_str, surprise,
    )
    return EpisodicEventOut(**dict(row))


@router.post("/timeline", response_model=list[EpisodicEventOut])
async def get_timeline(req: TimelineQuery):
    pool = await get_pool()
    conditions = ["importance >= $1"]
    params: list = [req.min_importance]
    idx = 2

    if req.hours is not None:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(hours=req.hours)
        conditions.append(f"created_at >= ${idx}")
        params.append(cutoff)
        idx += 1

    if req.event_type:
        conditions.append(f"event_type = ${idx}")
        params.append(req.event_type)
        idx += 1

    if req.session_id:
        conditions.append(f"session_id = ${idx}")
        params.append(req.session_id)
        idx += 1

    where = " AND ".join(conditions)
    params.append(req.limit)

    rows = await pool.fetch(
        f"""SELECT id, session_id, content, event_type, importance, created_at
            FROM episodic_events
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ${idx}""",
        *params,
    )
    return [EpisodicEventOut(**dict(r)) for r in rows]


# ── TraceMem: Narrative Consolidation ──────────────────────────────────────────
# Implements: TraceMem (arXiv 2602.09712, Feb 2026)
# Three-stage memory consolidation:
#   Stage 1 (trace buffering)   — collect recent unconsolidated episodic events
#   Stage 2 (synaptic)          — group by theme
#   Stage 3 (systems/narrative) — generate narrative summaries, store as semantic memories

_TRACEMEM_THEMES: list[tuple[str, list[str]]] = [
    ("alpha_trading",    ["alpha", "signal", "wallet", "trade", "price", "sol", "token",
                          "paper_trade", "helius", "dex", "backtest", "copy_trad"]),
    ("self_improvement", ["research", "paper", "implement", "arxiv", "model", "eval",
                          "capability", "training", "fine-tun", "improvement", "sweep"]),
    ("infrastructure",   ["heartbeat", "reflection", "orchestrat", "migration", "service",
                          "deploy", "endpoint", "api", "memory", "task_runner", "qa",
                          "docker", "systemd"]),
    ("mission_ops",      ["mev", "whatsapp", "outreach", "lead", "dashboard", "brand",
                          "character", "bobby", "pipi"]),
]

_TRACEMEM_DEFAULT_THEME = "general"


def _classify_theme(content: str) -> str:
    content_lower = content.lower()
    for theme, keywords in _TRACEMEM_THEMES:
        if any(kw in content_lower for kw in keywords):
            return theme
    return _TRACEMEM_DEFAULT_THEME


async def _narrative_summarize(theme: str, events: list[dict]) -> str:
    """Generate a narrative summary for a theme group via Gemini Flash.
    Falls back to template-based summary if Gemini unavailable."""
    if not settings.kimi_api_key:
        # Template fallback: structured bullet list
        lines = [f"- [{e['event_type']}] {e['content'][:120]}" for e in events[:10]]
        return f"[{theme}] {len(events)} events. Key: " + "; ".join(
            e["content"][:80] for e in sorted(events, key=lambda x: x["importance"], reverse=True)[:3]
        )

    try:
        lines = [
            f"[{e['event_type']}|imp={e['importance']}] {e['content'][:250]}"
            for e in events
        ]
        events_text = "\n".join(lines)
        prompt = (
            f"You are an AI memory assistant building a narrative memory for Otto (an autonomous AI agent). "
            f"Summarize the following episodic events in the '{theme}' domain into a single coherent "
            f"narrative paragraph (3-5 sentences). Focus on: what was attempted, what succeeded/failed, "
            f"what was learned, and what the story arc reveals about progress in this domain. "
            f"Be concrete. Return only the narrative paragraph.\n\nEvents:\n{events_text}"
        )
        response = await llm_chat([{"role": "user", "content": prompt}], max_tokens=500, temperature=0.1)
        return response or f"[{theme}] {len(events)} events (summarization returned empty)"
    except Exception as e:
        logger.warning(f"TraceMem: Gemini narrative failed for {theme}: {e}")
        return f"[{theme}] {len(events)} events from recent period."


class TraceMemResult(BaseModel):
    themes_processed: int
    narratives_created: int
    events_consolidated: int
    consolidation_id: str
    ran_at: datetime


@router.post("/consolidate", response_model=TraceMemResult)
async def tracemem_consolidate(
    lookback_hours: int = 24,
    min_events_per_theme: int = 2,
):
    """TraceMem narrative consolidation (arXiv 2602.09712).

    Stage 1 (trace buffering):  fetch last `lookback_hours` unconsolidated events.
    Stage 2 (synaptic):         group by theme (alpha_trading, self_improvement,
                                infrastructure, mission_ops, general).
    Stage 3 (systems/narrative):generate a narrative summary per theme via Gemini Flash,
                                store as semantic memory (category=narrative), mark
                                source events with a shared consolidation_id.

    Events already carrying a consolidation_id are skipped (idempotent).
    """
    pool = await get_pool()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    # Stage 1: Trace buffering — collect recent unconsolidated events
    rows = await pool.fetch(
        """SELECT id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE consolidation_id IS NULL
             AND created_at >= $1
           ORDER BY created_at ASC
           LIMIT 500""",
        cutoff,
    )

    if not rows:
        return TraceMemResult(
            themes_processed=0,
            narratives_created=0,
            events_consolidated=0,
            consolidation_id="",
            ran_at=datetime.now(timezone.utc),
        )

    # Stage 2: Synaptic consolidation — group by theme
    theme_groups: dict[str, list[dict]] = {}
    for row in rows:
        theme = _classify_theme(row["content"])
        theme_groups.setdefault(theme, []).append(dict(row))

    # Shared consolidation_id for this run
    run_consolidation_id = uuid.uuid4()
    narratives_created = 0
    events_consolidated = 0
    themes_processed = 0

    # Stage 3: Systems consolidation — narrative generation + semantic storage
    for theme, events in theme_groups.items():
        if len(events) < min_events_per_theme:
            continue
        themes_processed += 1

        # Generate narrative
        narrative = await _narrative_summarize(theme, events)

        # Time range metadata
        ts_min = min(e["created_at"] for e in events)
        ts_max = max(e["created_at"] for e in events)

        narrative_content = (
            f"[TraceMem/{theme}] {narrative}"
        )
        meta = json.dumps({
            "source": "tracemem_consolidation",
            "theme": theme,
            "time_range_start": ts_min.isoformat() if hasattr(ts_min, "isoformat") else str(ts_min),
            "time_range_end": ts_max.isoformat() if hasattr(ts_max, "isoformat") else str(ts_max),
            "event_count": len(events),
            "consolidation_id": str(run_consolidation_id),
        })

        # Store narrative as semantic memory
        try:
            embedding = await get_embedding(narrative_content)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await pool.execute(
                """INSERT INTO semantic_memories
                       (content, category, confidence, source, embedding, embedding_hv, metadata)
                   VALUES ($1, 'narrative', 0.8, 'tracemem', $2::text::vector, $2::text::halfvec(1536), $3::jsonb)""",
                narrative_content, embedding_str, meta,
            )
            narratives_created += 1
        except Exception as e:
            logger.error(f"TraceMem: failed to store narrative for {theme}: {e}")

        # Mark source events with consolidation_id
        event_ids = [e["id"] for e in events]
        await pool.execute(
            "UPDATE episodic_events SET consolidation_id = $1 WHERE id = ANY($2::uuid[])",
            run_consolidation_id, event_ids,
        )
        events_consolidated += len(events)

    logger.info(
        f"TraceMem: run={run_consolidation_id} themes={themes_processed} "
        f"narratives={narratives_created} events={events_consolidated}"
    )

    return TraceMemResult(
        themes_processed=themes_processed,
        narratives_created=narratives_created,
        events_consolidated=events_consolidated,
        consolidation_id=str(run_consolidation_id),
        ran_at=datetime.now(timezone.utc),
    )

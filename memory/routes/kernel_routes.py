"""Kernel API routes — expose AgentOS operations as HTTP endpoints.

These endpoints provide observability and manual control over the kernel:
- Interrupt submission and polling
- L1 cache inspection
- Drift monitoring
- Sync pulse triggers
- Provider status
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..db import get_pool
from ..kernel import ivt
from ..kernel.types import InterruptType, INTERRUPT_PRIORITIES

log = logging.getLogger("otto.routes.kernel")

router = APIRouter(prefix="/kernel", tags=["kernel"])


# ── Request/Response Models ──────────────────────────────────────────────────

class InterruptRequest(BaseModel):
    interrupt_type: str
    source: str = "api"
    payload: dict = Field(default_factory=dict)
    priority: int | None = None
    correlation_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)


class InterruptResponse(BaseModel):
    interrupt_id: UUID
    status: str


class KernelStatus(BaseModel):
    kernel_enabled: bool
    queue: dict
    providers: list[dict]
    l1_summary: dict
    drift: dict


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/status")
async def kernel_status():
    """Kernel state: queue depth, provider status, L1 summary, drift."""
    from ..config import settings

    # Queue depth
    queue = await ivt.queue_depth()

    # Providers
    from ..kernel.provider import get_providers
    providers = [
        {"name": p.name, "type": p.provider_type, "model": p.model_name,
         "priority": p.priority, "enabled": p.enabled}
        for p in get_providers()
    ]

    # L1 summary
    l1_summary = {"status": "not_initialized"}
    try:
        from ..kernel.smmu import get_smmu
        smmu = get_smmu()
        l1_summary = {
            "slice_count": len(smmu.l1_slice_ids),
            "token_count": smmu.l1_token_count,
            "capacity": settings.l1_capacity_tokens,
            "utilization_pct": round(smmu.l1_token_count / settings.l1_capacity_tokens * 100, 1)
            if settings.l1_capacity_tokens > 0 else 0,
        }
    except Exception:
        pass

    # Drift
    pool = await get_pool()
    drift_row = await pool.fetchrow(
        "SELECT delta_psi, measured_at FROM kernel_drift_log ORDER BY measured_at DESC LIMIT 1"
    )
    drift = {
        "current": drift_row["delta_psi"] if drift_row else 0.0,
        "threshold": settings.drift_threshold,
        "measured_at": drift_row["measured_at"].isoformat() if drift_row else None,
    }

    return {
        "kernel_enabled": settings.kernel_enabled,
        "queue": queue,
        "providers": providers,
        "l1": l1_summary,
        "drift": drift,
    }


@router.post("/interrupt", response_model=InterruptResponse)
async def submit_interrupt(req: InterruptRequest):
    """Submit an interrupt to the IVT."""
    interrupt_id = await ivt.enqueue(
        interrupt_type=req.interrupt_type,
        source=req.source,
        payload=req.payload,
        priority=req.priority,
        correlation_id=req.correlation_id,
        metadata=req.metadata,
    )
    return InterruptResponse(interrupt_id=interrupt_id, status="pending")


@router.get("/interrupt/{interrupt_id}/result")
async def get_interrupt_result(interrupt_id: UUID):
    """Poll for an interrupt's result."""
    result = await ivt.get_result(interrupt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interrupt not found")
    return result


@router.post("/process")
async def force_process():
    """Force-process the next pending interrupt."""
    interrupt = await ivt.dequeue()
    if not interrupt:
        return {"status": "empty", "message": "No pending interrupts"}

    from ..kernel.ric import process_interrupt
    result = await process_interrupt(interrupt)
    return {"status": "processed", "interrupt_id": str(interrupt["id"]), "result": result}


@router.post("/sync")
async def trigger_sync():
    """Trigger a Cognitive Sync Pulse manually."""
    try:
        from ..kernel.sync import run_sync_pulse
        result = await run_sync_pulse(trigger="manual")
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/l1")
async def view_l1(agent_id: str = "otto"):
    """View current L1 cache (loaded slices) for an agent."""
    try:
        from ..kernel.smmu import get_smmu
        smmu = get_smmu(agent_id)
        return {
            "agent_id": agent_id,
            "slice_ids": [str(s) for s in smmu.l1_slice_ids],
            "token_count": smmu.l1_token_count,
            "always_resident": smmu.always_resident_text[:500] if smmu.always_resident_text else "",
        }
    except Exception as e:
        return {"status": "not_initialized", "error": str(e)}


@router.get("/drift")
async def drift_history(limit: int = 20, agent_id: str | None = None):
    """Current drift value + recent history, optionally filtered by agent."""
    pool = await get_pool()

    if agent_id:
        rows = await pool.fetch(
            """SELECT id, delta_psi, l1_slice_count, triggered_sync, measured_at, agent_id
               FROM kernel_drift_log WHERE agent_id = $1
               ORDER BY measured_at DESC LIMIT $2""",
            agent_id, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT id, delta_psi, l1_slice_count, triggered_sync, measured_at, agent_id
               FROM kernel_drift_log ORDER BY measured_at DESC LIMIT $1""",
            limit,
        )

    return {
        "history": [
            {
                "delta_psi": r["delta_psi"],
                "l1_slices": r["l1_slice_count"],
                "triggered_sync": r["triggered_sync"],
                "at": r["measured_at"].isoformat(),
                "agent_id": r.get("agent_id", "otto"),
            }
            for r in rows
        ],
    }


@router.get("/providers")
async def list_providers():
    """List LLM providers and their status."""
    from ..kernel.provider import get_providers
    providers = get_providers()
    return {
        "providers": [
            {
                "name": p.name,
                "type": p.provider_type,
                "model": p.model_name,
                "priority": p.priority,
                "enabled": p.enabled,
                "base_url": p.base_url or "(default)",
            }
            for p in providers
        ]
    }


@router.get("/slices")
async def list_slices(limit: int = 50):
    """List semantic slices with page table status."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT s.id, s.label, s.token_count, s.category,
                  s.created_at, s.updated_at,
                  p.level, p.importance_score, p.access_count, p.last_accessed_at
           FROM semantic_slices s
           LEFT JOIN semantic_page_table p ON p.slice_id = s.id
           ORDER BY p.importance_score DESC NULLS LAST, s.created_at DESC
           LIMIT $1""",
        limit,
    )
    return {
        "slices": [
            {
                "id": str(r["id"]),
                "label": r["label"],
                "tokens": r["token_count"],
                "category": r["category"],
                "level": r["level"] or "L2",
                "importance": r["importance_score"],
                "accesses": r["access_count"],
                "last_accessed": r["last_accessed_at"].isoformat() if r["last_accessed_at"] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post("/slices/rebuild")
async def rebuild_slices():
    """Recompute CID boundaries and rebuild semantic slices."""
    try:
        from ..kernel.slicing import rebuild_all_slices
        result = await rebuild_all_slices()
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/interrupts")
async def recent_interrupts(limit: int = 20):
    """Get recent interrupts for monitoring."""
    interrupts = await ivt.recent_interrupts(limit)
    return {
        "interrupts": [
            {
                "id": str(i["id"]),
                "type": i["interrupt_type"],
                "priority": i["priority"],
                "source": i["source"],
                "status": i["status"],
                "created_at": i["created_at"].isoformat(),
                "started_at": i["started_at"].isoformat() if i.get("started_at") else None,
                "completed_at": i["completed_at"].isoformat() if i.get("completed_at") else None,
                "error": i.get("error"),
                "agent_id": i.get("agent_id", "otto"),
            }
            for i in interrupts
        ]
    }


# ── Agent Registry Endpoints ────────────────────────────────────────────────

@router.get("/agents")
async def list_agents():
    """List all registered kernel agents and their status."""
    from ..kernel.agents import get_all_agents
    agents = get_all_agents()
    return {
        "agents": [a.to_dict() for a in agents.values()],
        "count": len(agents),
    }


@router.get("/agents/{agent_id}")
async def get_agent_detail(agent_id: str):
    """Get details for a specific agent."""
    from ..kernel.agents import get_agent
    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return agent.to_dict()


@router.post("/agents/{agent_id}/started")
async def agent_started(agent_id: str):
    """CLI agent reports that it has started execution."""
    from ..kernel.agents import get_agent
    from ..kernel.scheduler import get_scheduler

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    scheduler = get_scheduler()
    await scheduler.record_cli_agent_start(agent_id)
    return {"status": "ok", "agent_id": agent_id, "event": "started"}


@router.post("/agents/{agent_id}/completed")
async def agent_completed(agent_id: str, success: bool = True):
    """CLI agent reports that it has completed execution."""
    from ..kernel.agents import get_agent
    from ..kernel.scheduler import get_scheduler

    agent = get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    scheduler = get_scheduler()
    await scheduler.record_cli_agent_end(agent_id, success=success)
    return {"status": "ok", "agent_id": agent_id, "event": "completed", "success": success}


@router.get("/agents/{agent_id}/activity")
async def agent_activity(agent_id: str, limit: int = 20):
    """Get recent activity log for an agent."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, event_type, interrupt_id, details, created_at
           FROM agent_activity_log
           WHERE agent_id = $1
           ORDER BY created_at DESC LIMIT $2""",
        agent_id, limit,
    )
    return {
        "agent_id": agent_id,
        "activity": [
            {
                "id": str(r["id"]),
                "event_type": r["event_type"],
                "interrupt_id": str(r["interrupt_id"]) if r["interrupt_id"] else None,
                "details": r["details"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ],
    }


@router.get("/providers/rate-limited")
async def check_rate_limit():
    """Check if any provider is currently rate-limited (replaces sentinel file)."""
    import os
    sentinel = "/tmp/otto-rate-limited"
    if os.path.exists(sentinel):
        try:
            with open(sentinel) as f:
                ts = int(f.read().strip())
            import time
            elapsed = int(time.time()) - ts
            if elapsed < 3600:
                return {"rate_limited": True, "elapsed_seconds": elapsed, "remaining_seconds": 3600 - elapsed}
        except Exception:
            pass
    return {"rate_limited": False}


@router.post("/providers/rate-limited")
async def report_rate_limit():
    """Report that a rate limit was hit (writes sentinel)."""
    import time
    sentinel = "/tmp/otto-rate-limited"
    with open(sentinel, "w") as f:
        f.write(str(int(time.time())))
    return {"status": "ok", "sentinel": sentinel}


# ── Unified Context & Post-Processing ──────────────────────────────────────

class PostProcessRequest(BaseModel):
    agent_id: str
    summary: str
    source: str  # "heartbeat" or "reflection"


ROLE_QUERIES = {
    "orchestrator": "mission review tasks directives priorities blockers Mev communication",
    "reflection": "self-improvement memory consolidation performance evaluation drift alignment",
    "worker": "task execution code implementation debugging research",
}


@router.get("/context")
async def unified_context(role: str = "orchestrator", query: str | None = None, max_tokens: int = 12000):
    """Unified context endpoint — S-MMU quality context for any agent role.

    Heartbeat, reflection, and task_runner can all get rich context
    through one API call instead of ad-hoc queries.
    """
    from ..config import settings
    from ..kernel.smmu import get_smmu

    try:
        smmu = get_smmu()

        # Use provided query or construct a role-specific synthetic one
        effective_query = query if query else ROLE_QUERIES.get(role, role)

        # Load context via S-MMU (same path as conversational messages)
        context_text = await smmu.load_for_message(effective_query, channel="internal")

        capacity = settings.l1_capacity_tokens
        token_count = smmu.l1_token_count
        utilization_pct = round(token_count / capacity * 100, 1) if capacity > 0 else 0

        # Truncate if caller requested fewer tokens than L1 capacity
        if max_tokens < token_count:
            # Rough truncation by character estimate (4 chars ≈ 1 token)
            char_limit = max_tokens * 4
            context_text = context_text[:char_limit]
            token_count = max_tokens

        return {
            "context_text": context_text,
            "token_count": token_count,
            "capacity": capacity,
            "utilization_pct": utilization_pct,
            "role": role,
            "source": "smmu" if query else f"smmu:synthetic:{role}",
        }
    except Exception as e:
        log.error(f"Unified context failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Context loading failed: {e}")


@router.post("/post-process")
async def unified_post_process(req: PostProcessRequest):
    """Unified post-processing — Phase 5 stages for heartbeat/reflection agents.

    Runs episodic logging, lesson extraction, and drift measurement
    so heartbeat.sh and reflection.sh get the same post-processing
    that WhatsApp messages get automatically.
    """
    from datetime import datetime, timezone

    result = {
        "status": "ok",
        "episodic_logged": False,
        "lesson_extracted": False,
        "lesson_category": None,
    }

    pool = await get_pool()

    # Stage A: Episodic event logging
    try:
        await pool.execute(
            """INSERT INTO episodic_events (content, event_type, importance, metadata)
               VALUES ($1, $2, $3, $4)""",
            f"[{req.source}] agent={req.agent_id}: {req.summary[:500]}",
            req.source,
            6,
            {"agent_id": req.agent_id, "source": req.source,
             "timestamp": datetime.now(timezone.utc).isoformat()},
        )
        result["episodic_logged"] = True
        log.info(f"Post-process episodic logged for {req.source}/{req.agent_id}")
    except Exception as e:
        log.warning(f"Post-process episodic logging failed: {e}")

    # Stage B+C: Lesson extraction from summary
    try:
        from ..gateway.classifiers import extract_lesson

        # Treat summary as if it were a conversation (Mev context + Otto summary)
        lesson = await extract_lesson(req.summary, "")
        if lesson:
            from ..embeddings import get_embedding
            embedding = await get_embedding(lesson["lesson"])
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await pool.execute(
                """INSERT INTO semantic_memories (content, category, confidence, embedding)
                   VALUES ($1, $2, 0.85, $3::vector(1536))""",
                lesson["lesson"], lesson["category"], embedding_str,
            )
            result["lesson_extracted"] = True
            result["lesson_category"] = lesson["category"]
            log.info(f"Post-process lesson stored [{lesson['category']}]: {lesson['lesson'][:80]}...")
    except Exception as e:
        log.warning(f"Post-process lesson extraction failed: {e}")

    # Stage D: Drift measurement
    try:
        from ..kernel.drift import measure_drift
        delta_psi = await measure_drift(agent_id=req.agent_id)
        result["drift"] = round(delta_psi, 4)
        log.info(f"Post-process drift measured: Δψ={delta_psi:.4f} for {req.agent_id}")
    except Exception as e:
        log.warning(f"Post-process drift measurement failed: {e}")

    return result

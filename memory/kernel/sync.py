"""Cognitive Sync Pulses — periodic state reconciliation.

Reference: arXiv 2602.20934v1 §7 (Sync Pulses)

Sync pulses ensure the kernel's cognitive state stays aligned with
ground truth. Triggered by:
- Drift threshold exceeded (event-driven)
- Scheduled intervals (alongside heartbeat timers)
- Nightly maintenance
- Manual trigger (POST /kernel/sync)
- Session boundaries

Multi-agent sync:
- If agent_id provided: single-agent sync (existing logic, scoped)
- If agent_id is None: multi-agent sync across all registered agents
"""

import logging

from ..config import settings
from ..db import get_pool
from .smmu import get_smmu
from .state import CognitiveState

log = logging.getLogger("otto.kernel.sync")


async def run_sync_pulse(trigger: str = "manual", agent_id: str | None = None) -> dict:
    """Execute a Cognitive Sync Pulse.

    Args:
        trigger: What initiated this sync (manual, drift, scheduled, maintenance, session_boundary)
        agent_id: If provided, sync only this agent. If None, sync all agents.

    Returns:
        dict with sync results.
    """
    if agent_id is not None:
        return await _sync_single_agent(trigger, agent_id)
    else:
        return await _sync_all_agents(trigger)


async def _sync_single_agent(trigger: str, agent_id: str) -> dict:
    """Sync pulse for a single agent."""
    pool = await get_pool()
    smmu = get_smmu(agent_id)

    log.info(f"Sync Pulse starting (trigger={trigger}, agent={agent_id})")

    results = {
        "trigger": trigger,
        "agent_id": agent_id,
        "snapshot_saved": False,
        "importance_updated": 0,
        "l1_reloaded": False,
        "episodic_consolidated": 0,
    }

    # 1. Snapshot current state
    try:
        snapshot_id = await smmu.save_state(trigger=f"sync_{trigger}")
        results["snapshot_saved"] = snapshot_id is not None
    except Exception as e:
        log.warning(f"Sync snapshot failed: {e}")

    # 2. Recalculate importance scores for L2 slices
    try:
        updated = await _recalc_importance_scores(pool)
        results["importance_updated"] = updated
    except Exception as e:
        log.warning(f"Sync importance recalc failed: {e}")

    # 3. Reload always-resident content into L1
    try:
        smmu.l1_slice_ids = []
        smmu.l1_token_count = 0
        smmu.l1_context_text = ""
        results["l1_reloaded"] = True
    except Exception as e:
        log.warning(f"Sync L1 reload failed: {e}")

    # 4. Episodic consolidation (TraceMem-style)
    if trigger in ("maintenance", "drift", "manual"):
        try:
            consolidated = await _consolidate_episodic(pool)
            results["episodic_consolidated"] = consolidated
        except Exception as e:
            log.warning(f"Sync episodic consolidation failed: {e}")

    # 5. Reset interrupt counter
    smmu.interrupts_since_sync = 0

    # 6. Log sync event
    try:
        await pool.execute(
            """INSERT INTO episodic_events (content, event_type, importance, metadata)
               VALUES ($1, $2, $3, $4)""",
            f"Cognitive Sync Pulse completed (trigger={trigger}, agent={agent_id})",
            "system",
            4,
            results,
        )
    except Exception:
        pass

    log.info(f"Sync Pulse complete: agent={agent_id} {results}")
    return results


async def _sync_all_agents(trigger: str) -> dict:
    """Multi-agent sync: reconcile state across all registered agents."""
    from .masking import critical_section
    from .types import InterruptType
    from .agents import get_all_agents
    from .drift import measure_drift

    log.info(f"Multi-agent Sync Pulse starting (trigger={trigger})")

    results = {
        "trigger": trigger,
        "agents_synced": [],
        "drift_measurements": {},
        "episodic_consolidated": 0,
    }

    # Mask non-critical interrupts during multi-agent sync
    async with critical_section(
        InterruptType.SIG_HEARTBEAT.value,
        InterruptType.SIG_MAINTENANCE.value,
    ):
        pool = await get_pool()
        agents = get_all_agents()

        # 1. Snapshot all agents' L1 state
        for aid, agent in agents.items():
            try:
                smmu = get_smmu(aid)
                await smmu.save_state(trigger=f"multi_sync_{trigger}")
            except Exception as e:
                log.warning(f"Multi-sync snapshot failed for {aid}: {e}")

        # 2. Reload shared ground truth for all agents
        for aid in agents:
            try:
                smmu = get_smmu(aid)
                smmu.l1_slice_ids = []
                smmu.l1_token_count = 0
                smmu.l1_context_text = ""
                smmu.interrupts_since_sync = 0
                results["agents_synced"].append(aid)
            except Exception as e:
                log.warning(f"Multi-sync L1 reload failed for {aid}: {e}")

        # 3. Recalculate importance scores (shared across all agents)
        try:
            await _recalc_importance_scores(pool)
        except Exception as e:
            log.warning(f"Multi-sync importance recalc failed: {e}")

        # 4. Measure per-agent drift
        for aid in agents:
            try:
                delta_psi = await measure_drift(agent_id=aid)
                results["drift_measurements"][aid] = delta_psi
            except Exception as e:
                log.warning(f"Multi-sync drift failed for {aid}: {e}")

        # 5. Consolidate episodic events
        if trigger in ("maintenance", "drift", "manual", "scheduled"):
            try:
                consolidated = await _consolidate_episodic(pool)
                results["episodic_consolidated"] = consolidated
            except Exception as e:
                log.warning(f"Multi-sync episodic consolidation failed: {e}")

    # Log sync event
    try:
        await pool.execute(
            """INSERT INTO episodic_events (content, event_type, importance, metadata)
               VALUES ($1, $2, $3, $4)""",
            f"Multi-agent Sync Pulse completed (trigger={trigger}, agents={len(results['agents_synced'])})",
            "system",
            5,
            results,
        )
    except Exception:
        pass

    log.info(f"Multi-agent Sync Pulse complete: {results}")
    return results


async def _recalc_importance_scores(pool) -> int:
    """Recalculate importance scores for all slices in semantic_page_table.

    importance = avg(member_importance_scores) * recency_weight * access_weight

    recency_weight = 1 / (1 + days_since_access / 30)
    access_weight = min(1.0, access_count / 50)
    """
    rows = await pool.fetch(
        """SELECT p.id, p.slice_id, p.importance_score, p.access_count, p.last_accessed_at,
                  s.memory_ids
           FROM semantic_page_table p
           JOIN semantic_slices s ON s.id = p.slice_id"""
    )

    updated = 0
    for r in rows:
        memory_ids = r["memory_ids"]
        if not memory_ids:
            continue

        # Get average importance of member memories
        avg_row = await pool.fetchrow(
            "SELECT AVG(COALESCE(importance_score, 0.5)) as avg_imp FROM semantic_memories WHERE id = ANY($1)",
            memory_ids,
        )
        avg_importance = float(avg_row["avg_imp"]) if avg_row and avg_row["avg_imp"] else 0.5

        # Recency weight
        if r["last_accessed_at"]:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            days_since = (now - r["last_accessed_at"].replace(tzinfo=timezone.utc if r["last_accessed_at"].tzinfo is None else r["last_accessed_at"].tzinfo)).total_seconds() / 86400
            recency_weight = 1.0 / (1.0 + days_since / 30.0)
        else:
            recency_weight = 0.5

        # Access weight
        access_weight = min(1.0, (r["access_count"] or 0) / 50.0)

        # Combined importance
        new_importance = avg_importance * 0.5 + recency_weight * 0.3 + access_weight * 0.2
        new_importance = max(0.0, min(1.0, new_importance))

        if abs(new_importance - (r["importance_score"] or 0.5)) > 0.01:
            await pool.execute(
                "UPDATE semantic_page_table SET importance_score = $1 WHERE id = $2",
                new_importance, r["id"],
            )
            updated += 1

    return updated


async def _consolidate_episodic(pool, max_age_days: int = 7, min_importance: int = 3) -> int:
    """Consolidate old episodic events into semantic memories (TraceMem-style).

    Groups related low-importance events and creates a summary memory.
    Returns number of events consolidated.
    """
    # Find old low-importance events not yet consolidated
    rows = await pool.fetch(
        """SELECT id, content, event_type, importance, created_at
           FROM episodic_events
           WHERE importance <= $1
             AND created_at < NOW() - INTERVAL '1 day' * $2
             AND (metadata IS NULL OR NOT (metadata ? 'consolidated'))
           ORDER BY created_at ASC
           LIMIT 50""",
        min_importance,
        max_age_days,
    )

    if len(rows) < 5:
        return 0  # Not enough to consolidate

    # Group by event type
    groups: dict[str, list] = {}
    for r in rows:
        etype = r["event_type"]
        if etype not in groups:
            groups[etype] = []
        groups[etype].append(r)

    consolidated = 0
    for etype, events in groups.items():
        if len(events) < 3:
            continue

        # Create summary
        contents = [e["content"][:150] for e in events[:10]]
        summary = f"Consolidated {len(events)} {etype} events: " + " | ".join(contents)
        summary = summary[:800]

        # Store as semantic memory
        try:
            from ..embeddings import get_embedding
            embedding = await get_embedding(summary)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            await pool.execute(
                """INSERT INTO semantic_memories (content, category, confidence, source, embedding)
                   VALUES ($1, 'observation', 0.6, 'sync_consolidation', $2::vector)""",
                summary, embedding_str,
            )

            # Mark events as consolidated
            event_ids = [e["id"] for e in events]
            await pool.execute(
                """UPDATE episodic_events
                   SET metadata = COALESCE(metadata, '{}'::jsonb) || '{"consolidated": true}'::jsonb
                   WHERE id = ANY($1)""",
                event_ids,
            )
            consolidated += len(events)
        except Exception as e:
            log.warning(f"Episodic consolidation failed for {etype}: {e}")

    return consolidated

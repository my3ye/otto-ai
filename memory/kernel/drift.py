"""Cognitive Drift Detection — Δψ measurement and threshold monitoring.

Reference: arXiv 2602.20934v1 §6 (Cognitive Drift)

Drift measures how far the kernel's current L1 context has drifted from
the ground truth (purpose, priorities, directives). High drift indicates
the kernel is operating with stale or irrelevant context.

Δψ = 1 - cosine_similarity(L1_centroid, ground_truth_embedding)

When Δψ exceeds the threshold, a SIG_SYNC_DRIFT interrupt fires.

Multi-agent: drift is measured per-agent, each with its own threshold.
"""

import logging
import numpy as np

from ..config import settings
from ..db import get_pool
from ..embeddings import get_embedding
from .smmu import get_smmu
from . import ivt
from .types import InterruptType

log = logging.getLogger("otto.kernel.drift")


async def measure_drift(agent_id: str = "otto") -> float:
    """Measure current cognitive drift Δψ for an agent.

    Compares L1 context embedding against ground truth embedding.
    Logs the measurement and triggers sync if threshold exceeded.

    Returns the drift value.
    """
    pool = await get_pool()
    smmu = get_smmu(agent_id)

    # Get agent-specific drift threshold
    drift_threshold = settings.drift_threshold
    try:
        from .agents import get_agent
        agent = get_agent(agent_id)
        if agent:
            drift_threshold = agent.config.drift_threshold
    except Exception:
        pass

    # Get ground truth: purpose + priorities (always-resident content)
    ground_truth_parts = []
    try:
        row = await pool.fetchrow("SELECT content FROM core_memory WHERE slot = 'purpose'")
        if row and row["content"]:
            ground_truth_parts.append(row["content"])
    except Exception:
        pass

    try:
        row = await pool.fetchrow("SELECT content FROM core_memory WHERE slot = 'priorities'")
        if row and row["content"]:
            ground_truth_parts.append(row["content"])
    except Exception:
        pass

    try:
        rows = await pool.fetch(
            "SELECT directive FROM mission_directives WHERE status = 'active' ORDER BY priority DESC LIMIT 5"
        )
        for r in rows:
            ground_truth_parts.append(r["directive"])
    except Exception:
        pass

    if not ground_truth_parts:
        log.warning("No ground truth available for drift measurement")
        return 0.0

    ground_truth_text = "\n".join(ground_truth_parts)

    # Get L1 context embedding
    l1_text = smmu.l1_context_text
    if not l1_text:
        # No L1 content loaded yet — no drift to measure
        delta_psi = 0.0
    else:
        try:
            gt_embedding = await get_embedding(ground_truth_text[:2000])
            l1_embedding = await get_embedding(l1_text[:2000])

            gt_arr = np.array(gt_embedding)
            l1_arr = np.array(l1_embedding)
            dot = np.dot(gt_arr, l1_arr)
            norm = np.linalg.norm(gt_arr) * np.linalg.norm(l1_arr)
            if norm > 1e-10:
                similarity = float(dot / norm)
            else:
                similarity = 0.0

            delta_psi = 1.0 - similarity
        except Exception as e:
            log.warning(f"Drift embedding computation failed: {e}")
            delta_psi = 0.0

    # Log drift measurement (with agent_id)
    l1_count = len(smmu.l1_slice_ids)
    triggered_sync = delta_psi > drift_threshold

    await pool.execute(
        """INSERT INTO kernel_drift_log (delta_psi, l1_slice_count, triggered_sync, agent_id)
           VALUES ($1, $2, $3, $4)""",
        delta_psi,
        l1_count,
        triggered_sync,
        agent_id,
    )

    log.info(f"Drift measured: agent={agent_id} Δψ={delta_psi:.4f} (threshold={drift_threshold}, triggered={triggered_sync})")

    # Trigger sync if threshold exceeded
    if triggered_sync:
        log.warning(f"Drift threshold exceeded! agent={agent_id} Δψ={delta_psi:.4f} > {drift_threshold}")
        await ivt.enqueue(
            interrupt_type=InterruptType.SIG_SYNC_DRIFT,
            source="drift",
            payload={
                "delta_psi": delta_psi,
                "l1_slice_count": l1_count,
                "agent_id": agent_id,
            },
            agent_id=agent_id,
        )

    return delta_psi


async def get_drift_history(limit: int = 20, agent_id: str | None = None) -> list[dict]:
    """Get recent drift measurements, optionally filtered by agent."""
    pool = await get_pool()

    if agent_id:
        rows = await pool.fetch(
            """SELECT delta_psi, l1_slice_count, triggered_sync, measured_at, agent_id
               FROM kernel_drift_log WHERE agent_id = $1
               ORDER BY measured_at DESC LIMIT $2""",
            agent_id, limit,
        )
    else:
        rows = await pool.fetch(
            """SELECT delta_psi, l1_slice_count, triggered_sync, measured_at, agent_id
               FROM kernel_drift_log ORDER BY measured_at DESC LIMIT $1""",
            limit,
        )

    return [
        {
            "delta_psi": float(r["delta_psi"]),
            "l1_slices": r["l1_slice_count"],
            "triggered_sync": r["triggered_sync"],
            "at": r["measured_at"].isoformat(),
            "agent_id": r.get("agent_id", "otto"),
        }
        for r in rows
    ]

"""Education Engine API — Gamified skill learning for the MY3YE builder ecosystem.

Serves 10 skill cluster trees with curated resources. Tracks per-user XP and
node completion. Powers the S0S Systems self-education mission.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..db import get_pool

log = logging.getLogger("otto.education")

router = APIRouter(prefix="/education", tags=["education"])

# ── Skill Data ─────────────────────────────────────────────────────────────────
_SKILLS_PATH = Path(__file__).parent.parent.parent / "education" / "skills.json"
_skills_cache: dict | None = None


def _load_skills() -> dict:
    global _skills_cache
    if _skills_cache is None:
        with open(_SKILLS_PATH) as f:
            _skills_cache = json.load(f)
    return _skills_cache


def _get_cluster(cluster_id: str) -> dict | None:
    data = _load_skills()
    for c in data["clusters"]:
        if c["id"] == cluster_id:
            return c
    return None


# ── Models ─────────────────────────────────────────────────────────────────────

class CompleteResourceRequest(BaseModel):
    cluster_id: str
    node_id: str
    resource_url: str
    user_id: str = "mev"


class CompleteNodeRequest(BaseModel):
    cluster_id: str
    node_id: str
    user_id: str = "mev"


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/clusters")
async def list_clusters():
    """List all skill clusters with metadata and total XP."""
    data = _load_skills()
    clusters = []
    for c in data["clusters"]:
        clusters.append({
            "id": c["id"],
            "title": c["title"],
            "emoji": c["emoji"],
            "color": c["color"],
            "description": c["description"],
            "total_xp": c["total_xp"],
            "node_count": len(c["nodes"]),
        })
    return {"version": data["version"], "clusters": clusters}


@router.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    """Get full skill tree for a cluster including all nodes and resources."""
    cluster = _get_cluster(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{cluster_id}' not found")
    return cluster


@router.get("/progress")
async def get_progress(user_id: str = Query("mev")):
    """Get a user's full learning progress — XP per cluster, completed nodes."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT cluster_id, node_id, completed, xp_earned,
               resources_completed, completed_at
        FROM education_progress
        WHERE user_id = $1
        ORDER BY cluster_id, node_id
        """,
        user_id,
    )

    # Build per-cluster summary
    data = _load_skills()
    cluster_map = {c["id"]: c for c in data["clusters"]}

    progress_by_cluster: dict[str, dict] = {}
    for row in rows:
        cid = row["cluster_id"]
        if cid not in progress_by_cluster:
            c = cluster_map.get(cid, {})
            progress_by_cluster[cid] = {
                "cluster_id": cid,
                "title": c.get("title", cid),
                "emoji": c.get("emoji", ""),
                "color": c.get("color", "#666"),
                "total_xp": c.get("total_xp", 0),
                "xp_earned": 0,
                "nodes_completed": 0,
                "node_count": len(c.get("nodes", [])),
                "nodes": {},
            }
        progress_by_cluster[cid]["xp_earned"] += row["xp_earned"]
        if row["completed"]:
            progress_by_cluster[cid]["nodes_completed"] += 1
        progress_by_cluster[cid]["nodes"][row["node_id"]] = {
            "completed": row["completed"],
            "xp_earned": row["xp_earned"],
            "resources_completed": row["resources_completed"],
            "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
        }

    # Add zeroed-out clusters not yet started
    for cid, cluster in cluster_map.items():
        if cid not in progress_by_cluster:
            progress_by_cluster[cid] = {
                "cluster_id": cid,
                "title": cluster["title"],
                "emoji": cluster["emoji"],
                "color": cluster["color"],
                "total_xp": cluster["total_xp"],
                "xp_earned": 0,
                "nodes_completed": 0,
                "node_count": len(cluster["nodes"]),
                "nodes": {},
            }

    total_xp = sum(v["xp_earned"] for v in progress_by_cluster.values())
    total_nodes_completed = sum(v["nodes_completed"] for v in progress_by_cluster.values())
    total_nodes = sum(v["node_count"] for v in progress_by_cluster.values())

    level_thresholds = [0, 500, 1500, 3500, 7000, 13000, 22000]
    current_level = 1
    for i, threshold in enumerate(level_thresholds):
        if total_xp >= threshold:
            current_level = i + 1

    level_names = ["Initiate", "Apprentice", "Journeyman", "Expert", "Master", "Grand Master", "Sovereign"]
    level_name = level_names[min(current_level - 1, len(level_names) - 1)]

    next_threshold = level_thresholds[current_level] if current_level < len(level_thresholds) else None
    prev_threshold = level_thresholds[current_level - 1]
    xp_in_level = total_xp - prev_threshold
    xp_to_next = (next_threshold - total_xp) if next_threshold else 0
    level_progress_pct = int((xp_in_level / (next_threshold - prev_threshold) * 100)) if next_threshold else 100

    return {
        "user_id": user_id,
        "total_xp": total_xp,
        "current_level": current_level,
        "level_name": level_name,
        "level_progress_pct": level_progress_pct,
        "xp_to_next_level": xp_to_next,
        "nodes_completed": total_nodes_completed,
        "total_nodes": total_nodes,
        "clusters": list(progress_by_cluster.values()),
    }


@router.post("/complete-resource")
async def complete_resource(req: CompleteResourceRequest):
    """Mark a resource as completed, award XP fraction for the node."""
    pool = await get_pool()

    # Find the node and resource
    cluster = _get_cluster(req.cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{req.cluster_id}' not found")

    node = next((n for n in cluster["nodes"] if n["id"] == req.node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{req.node_id}' not found")

    resource = next((r for r in node["resources"] if r["url"] == req.resource_url), None)
    if not resource:
        raise HTTPException(status_code=404, detail=f"Resource not found in node")

    # XP per resource = node XP / number of resources (partial credit)
    xp_per_resource = max(1, node["xp"] // len(node["resources"]))

    # Get or create progress row
    existing = await pool.fetchrow(
        "SELECT id, xp_earned, resources_completed FROM education_progress WHERE user_id=$1 AND node_id=$2",
        req.user_id, req.node_id
    )

    if existing:
        completed_list = list(existing["resources_completed"] or [])
        if req.resource_url in completed_list:
            return {"status": "already_completed", "xp_delta": 0, "total_node_xp": existing["xp_earned"]}

        completed_list.append(req.resource_url)
        new_xp = existing["xp_earned"] + xp_per_resource
        all_resources = [r["url"] for r in node["resources"]]
        node_complete = all(r in completed_list for r in all_resources)

        await pool.execute(
            """
            UPDATE education_progress
            SET xp_earned=$1, resources_completed=$2, completed=$3,
                completed_at=CASE WHEN $3 AND completed_at IS NULL THEN now() ELSE completed_at END,
                updated_at=now()
            WHERE user_id=$4 AND node_id=$5
            """,
            new_xp, json.dumps(completed_list), node_complete,
            req.user_id, req.node_id,
        )
    else:
        completed_list = [req.resource_url]
        new_xp = xp_per_resource
        all_resources = [r["url"] for r in node["resources"]]
        node_complete = all(r in completed_list for r in all_resources)

        await pool.execute(
            """
            INSERT INTO education_progress (user_id, cluster_id, node_id, xp_earned, resources_completed, completed, completed_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            req.user_id, req.cluster_id, req.node_id,
            new_xp, json.dumps(completed_list), node_complete,
            datetime.now(timezone.utc) if node_complete else None,
        )

    # Log XP event
    await pool.execute(
        """
        INSERT INTO education_xp_log (user_id, cluster_id, node_id, resource_url, xp_delta, reason)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        req.user_id, req.cluster_id, req.node_id,
        req.resource_url, xp_per_resource, f"Completed resource: {resource['title']}"
    )

    log.info(f"User {req.user_id} completed resource in {req.node_id}: +{xp_per_resource} XP")
    return {
        "status": "completed",
        "xp_delta": xp_per_resource,
        "total_node_xp": new_xp,
        "node_completed": node_complete,
        "resources_completed": completed_list,
    }


@router.post("/complete-node")
async def complete_node(req: CompleteNodeRequest):
    """Mark an entire node as complete (all XP awarded)."""
    pool = await get_pool()

    cluster = _get_cluster(req.cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail=f"Cluster '{req.cluster_id}' not found")

    node = next((n for n in cluster["nodes"] if n["id"] == req.node_id), None)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node '{req.node_id}' not found")

    existing = await pool.fetchrow(
        "SELECT id, xp_earned, completed FROM education_progress WHERE user_id=$1 AND node_id=$2",
        req.user_id, req.node_id
    )

    all_resources = [r["url"] for r in node["resources"]]
    xp_delta = node["xp"] - (existing["xp_earned"] if existing else 0)

    if existing:
        if existing["completed"]:
            return {"status": "already_completed", "xp_delta": 0}
        await pool.execute(
            """
            UPDATE education_progress
            SET xp_earned=$1, resources_completed=$2, completed=TRUE,
                completed_at=now(), updated_at=now()
            WHERE user_id=$3 AND node_id=$4
            """,
            node["xp"], json.dumps(all_resources), req.user_id, req.node_id,
        )
    else:
        await pool.execute(
            """
            INSERT INTO education_progress (user_id, cluster_id, node_id, xp_earned, resources_completed, completed, completed_at)
            VALUES ($1, $2, $3, $4, $5, TRUE, now())
            """,
            req.user_id, req.cluster_id, req.node_id, node["xp"], json.dumps(all_resources),
        )

    if xp_delta > 0:
        await pool.execute(
            """
            INSERT INTO education_xp_log (user_id, cluster_id, node_id, xp_delta, reason)
            VALUES ($1, $2, $3, $4, $5)
            """,
            req.user_id, req.cluster_id, req.node_id, xp_delta, f"Node completed: {node['title']}"
        )

    return {
        "status": "completed",
        "xp_delta": xp_delta,
        "total_node_xp": node["xp"],
    }


@router.get("/xp-log")
async def get_xp_log(user_id: str = Query("mev"), limit: int = Query(50, le=200)):
    """Get XP history for a user."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT cluster_id, node_id, resource_url, xp_delta, reason, created_at
        FROM education_xp_log
        WHERE user_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """,
        user_id, limit
    )
    return {
        "user_id": user_id,
        "events": [
            {
                "cluster_id": r["cluster_id"],
                "node_id": r["node_id"],
                "resource_url": r["resource_url"],
                "xp_delta": r["xp_delta"],
                "reason": r["reason"],
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/leaderboard")
async def get_leaderboard(limit: int = Query(10, le=50)):
    """XP leaderboard across all users."""
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT user_id, SUM(xp_earned) as total_xp, COUNT(*) FILTER (WHERE completed) as nodes_completed
        FROM education_progress
        GROUP BY user_id
        ORDER BY total_xp DESC
        LIMIT $1
        """,
        limit
    )
    return {
        "leaderboard": [
            {
                "rank": i + 1,
                "user_id": r["user_id"],
                "total_xp": r["total_xp"],
                "nodes_completed": r["nodes_completed"],
            }
            for i, r in enumerate(rows)
        ]
    }

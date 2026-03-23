"""SOS Systems Learner CRUD — education ladder registry."""

import logging
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.sos.learners")

VALID_TIERS = ("seed", "sprout", "apprentice", "journeyman", "master", "elder")
VALID_ORIGINS = ("general", "refugee", "displaced", "homeless", "underprivileged")
VALID_CONTRIBUTION_TYPES = ("learning", "code", "content", "mentorship", "infrastructure", "outreach")

# XP thresholds for each tier
TIER_XP_THRESHOLDS = {
    "seed": 0,
    "sprout": 100,
    "apprentice": 500,
    "journeyman": 2000,
    "master": 10000,
    "elder": 50000,
}


def get_tier_for_xp(xp: int) -> str:
    """Return the tier name that corresponds to a given XP total.

    Iterates thresholds in ascending XP order so adding new tiers in any
    dict order won't silently produce wrong results.
    """
    tier = "seed"
    for t, threshold in sorted(TIER_XP_THRESHOLDS.items(), key=lambda kv: kv[1]):
        if xp >= threshold:
            tier = t
    return tier


async def register_learner(
    handle: str,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    origin_type: str = "general",
    oneon_id: Optional[str] = None,
    tusita_location: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Register a new SOS learner at 'seed' tier."""
    handle_clean = handle.lstrip("@").lower().strip()
    if not handle_clean:
        raise ValueError("Handle cannot be empty.")
    if origin_type not in VALID_ORIGINS:
        raise ValueError(f"Invalid origin_type: {origin_type}")

    pool = await get_pool()
    try:
        row = await pool.fetchrow("""
            INSERT INTO sos_learners
                (handle, display_name, email, tier, origin_type,
                 oneon_id, tusita_location, metadata)
            VALUES ($1, $2, $3, 'seed', $4, $5, $6, $7)
            RETURNING *
        """, handle_clean, display_name, email, origin_type,
            UUID(oneon_id) if oneon_id else None,
            UUID(tusita_location) if tusita_location else None,
            metadata or {})
    except Exception as e:
        if "unique" in str(e).lower():
            raise ValueError(f"Handle already registered: @{handle_clean}")
        raise

    log.info(f"SOS learner registered: @{handle_clean} (origin: {origin_type})")
    return dict(row)


async def get_learner(learner_id: str) -> Optional[dict]:
    """Fetch a learner by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sos_learners WHERE id = $1",
        UUID(learner_id),
    )
    return dict(row) if row else None


async def get_learner_by_handle(handle: str) -> Optional[dict]:
    """Fetch a learner by handle (case-insensitive)."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM sos_learners WHERE LOWER(handle) = $1",
        handle.lstrip("@").lower(),
    )
    return dict(row) if row else None


async def list_learners(
    tier: Optional[str] = None,
    origin_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List SOS learners with optional filters."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if tier:
        args.append(tier)
        conditions.append(f"tier = ${len(args)}")
    if origin_type:
        args.append(origin_type)
        conditions.append(f"origin_type = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args += [limit, offset]

    rows = await pool.fetch(f"""
        SELECT * FROM sos_learners
        {where}
        ORDER BY xp_total DESC, created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def award_contribution(
    learner_id: str,
    contribution_type: str,
    title: str,
    description: Optional[str] = None,
    xp_awarded: int = 0,
    reviewer_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Record an accepted contribution and update learner XP + tier.

    Atomically:
    1. Insert contribution record (status=accepted)
    2. Add XP to learner
    3. Advance tier if XP threshold reached
    """
    if contribution_type not in VALID_CONTRIBUTION_TYPES:
        raise ValueError(f"Invalid contribution_type: {contribution_type}")
    if xp_awarded < 0:
        raise ValueError("xp_awarded cannot be negative")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            contrib_row = await conn.fetchrow("""
                INSERT INTO sos_contributions
                    (learner_id, contribution_type, title, description,
                     xp_awarded, status, reviewer_id, metadata, reviewed_at)
                VALUES ($1, $2, $3, $4, $5, 'accepted', $6, $7, NOW())
                RETURNING *
            """, UUID(learner_id), contribution_type, title, description,
                xp_awarded, UUID(reviewer_id) if reviewer_id else None,
                metadata or {})

            # Update XP and contribution count, then recalculate tier
            learner_row = await conn.fetchrow("""
                UPDATE sos_learners
                SET xp_total    = xp_total + $2,
                    contributions = contributions + 1,
                    updated_at  = NOW(),
                    activated_at = COALESCE(activated_at, NOW())
                WHERE id = $1
                RETURNING *
            """, UUID(learner_id), xp_awarded)

            if learner_row:
                new_tier = get_tier_for_xp(learner_row["xp_total"])
                if new_tier != learner_row["tier"]:
                    learner_row = await conn.fetchrow("""
                        UPDATE sos_learners SET tier = $2 WHERE id = $1 RETURNING *
                    """, UUID(learner_id), new_tier)
                    log.info(f"SOS learner {learner_id} advanced to tier: {new_tier}")

    return {
        "contribution": dict(contrib_row),
        "learner": dict(learner_row) if learner_row else None,
    }


async def get_learner_stats() -> dict:
    """Aggregate stats for all SOS learners."""
    pool = await get_pool()
    tier_rows = await pool.fetch("""
        SELECT tier, COUNT(*) as count, SUM(xp_total) as total_xp
        FROM sos_learners GROUP BY tier
    """)
    origin_rows = await pool.fetch("""
        SELECT origin_type, COUNT(*) as count FROM sos_learners GROUP BY origin_type
    """)
    total = await pool.fetchval("SELECT COUNT(*) FROM sos_learners")
    return {
        "total": total,
        "by_tier": {r["tier"]: {"count": r["count"], "total_xp": r["total_xp"] or 0} for r in tier_rows},
        "by_origin": {r["origin_type"]: r["count"] for r in origin_rows},
    }

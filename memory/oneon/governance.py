"""ONEON Governance — proposals and voting CRUD."""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.oneon.governance")

VALID_STATUSES = ("draft", "open", "closed", "executed", "rejected")
VALID_TYPES = ("general", "upgrade", "parameter", "emergency")
VALID_VOTES = ("for", "against", "abstain")


async def create_proposal(
    proposer_id: str,
    title: str,
    body: str,
    proposal_type: str = "general",
    quorum_required: int = 10,
    voting_ends_at: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """Create a governance proposal."""
    if proposal_type not in VALID_TYPES:
        raise ValueError(f"Invalid proposal_type: {proposal_type}")

    pool = await get_pool()
    row = await pool.fetchrow("""
        INSERT INTO oneon_governance_proposals
            (proposer_id, title, body, proposal_type, status,
             quorum_required, voting_ends_at, metadata)
        VALUES ($1, $2, $3, $4, 'draft', $5, $6, $7)
        RETURNING *
    """, UUID(proposer_id), title, body, proposal_type,
        quorum_required, voting_ends_at, metadata or {})

    log.info(f"Governance proposal created: {row['id']} by {proposer_id}")
    return dict(row)


async def get_proposal(proposal_id: str) -> Optional[dict]:
    """Fetch a single proposal by UUID."""
    pool = await get_pool()
    row = await pool.fetchrow(
        "SELECT * FROM oneon_governance_proposals WHERE id = $1",
        UUID(proposal_id),
    )
    return dict(row) if row else None


async def list_proposals(
    status: Optional[str] = None,
    proposal_type: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List proposals with optional filters."""
    pool = await get_pool()
    conditions: list[str] = []
    args: list = []

    if status:
        args.append(status)
        conditions.append(f"status = ${len(args)}")
    if proposal_type:
        args.append(proposal_type)
        conditions.append(f"proposal_type = ${len(args)}")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    args.append(limit)

    rows = await pool.fetch(f"""
        SELECT p.*, i.handle as proposer_handle
        FROM oneon_governance_proposals p
        LEFT JOIN oneon_identities i ON i.id = p.proposer_id
        {where}
        ORDER BY p.created_at DESC
        LIMIT ${len(args)}
    """, *args)
    return [dict(r) for r in rows]


async def update_proposal_status(
    proposal_id: str,
    status: str,
) -> Optional[dict]:
    """Update proposal status."""
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")
    pool = await get_pool()
    executed_at = "NOW()" if status == "executed" else "NULL"
    row = await pool.fetchrow(f"""
        UPDATE oneon_governance_proposals
        SET status = $2,
            updated_at = NOW(),
            executed_at = CASE WHEN $2 = 'executed' THEN NOW() ELSE executed_at END
        WHERE id = $1
        RETURNING *
    """, UUID(proposal_id), status)
    return dict(row) if row else None


async def cast_vote(
    proposal_id: str,
    voter_id: str,
    vote: str,
    weight: int = 1,
) -> dict:
    """Cast a vote on a proposal.

    Updates vote tallies on the proposal atomically.
    Raises ValueError if proposal is not in 'open' status.
    """
    if vote not in VALID_VOTES:
        raise ValueError(f"Invalid vote: {vote}. Must be one of {VALID_VOTES}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Verify proposal is open
            proposal = await conn.fetchrow(
                "SELECT status FROM oneon_governance_proposals WHERE id = $1",
                UUID(proposal_id),
            )
            if not proposal:
                raise ValueError(f"Proposal not found: {proposal_id}")
            if proposal["status"] != "open":
                raise ValueError(
                    f"Cannot vote on proposal with status '{proposal['status']}'. "
                    "Only 'open' proposals accept votes."
                )

            # Upsert vote record
            try:
                vote_row = await conn.fetchrow("""
                    INSERT INTO oneon_governance_votes
                        (proposal_id, voter_id, vote, weight)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (proposal_id, voter_id)
                    DO UPDATE SET vote = EXCLUDED.vote, weight = EXCLUDED.weight
                    RETURNING *
                """, UUID(proposal_id), UUID(voter_id), vote, weight)
            except Exception as e:
                raise ValueError(f"Vote failed: {e}")

            # Recalculate tallies
            await conn.execute("""
                UPDATE oneon_governance_proposals
                SET votes_for     = (SELECT COALESCE(SUM(weight), 0) FROM oneon_governance_votes
                                     WHERE proposal_id = $1 AND vote = 'for'),
                    votes_against = (SELECT COALESCE(SUM(weight), 0) FROM oneon_governance_votes
                                     WHERE proposal_id = $1 AND vote = 'against'),
                    updated_at    = NOW()
                WHERE id = $1
            """, UUID(proposal_id))

    log.info(f"Vote cast: {voter_id} voted '{vote}' on {proposal_id}")
    return dict(vote_row)


async def get_votes(proposal_id: str) -> list[dict]:
    """Fetch all votes for a proposal."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT v.*, i.handle as voter_handle
        FROM oneon_governance_votes v
        LEFT JOIN oneon_identities i ON i.id = v.voter_id
        WHERE v.proposal_id = $1
        ORDER BY v.created_at DESC
    """, UUID(proposal_id))
    return [dict(r) for r in rows]

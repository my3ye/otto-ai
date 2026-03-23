-- Migration 069: ONEON Identity Network
-- Creates oneon_identities and oneon_governance_proposals tables
-- Phase 0: DB/API only — no DID resolution, no OWS signing

-- 1. ONEON Identity table
CREATE TABLE IF NOT EXISTS oneon_identities (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle           TEXT NOT NULL UNIQUE,                         -- @handle (case-insensitive canonical)
    display_name     TEXT,
    tier             TEXT NOT NULL DEFAULT 'waitlist',             -- waitlist | custodial | self_sovereign | sovereign
    did              TEXT,                                         -- DID stub (Phase 2: real DID resolution)
    ows_vault_ref    TEXT,                                         -- OWS vault reference (Phase 1: real signing)
    wallet_address   TEXT,                                         -- linked EVM/Solana address
    chain            TEXT DEFAULT 'none',                          -- primary chain (none until Phase 1)
    metadata         JSONB DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at     TIMESTAMPTZ,                                  -- NULL until tier > waitlist
    CONSTRAINT oneon_identities_tier_check
        CHECK (tier IN ('waitlist', 'custodial', 'self_sovereign', 'sovereign'))
);

CREATE INDEX IF NOT EXISTS idx_oneon_identities_handle    ON oneon_identities(LOWER(handle));
CREATE INDEX IF NOT EXISTS idx_oneon_identities_tier      ON oneon_identities(tier);
CREATE INDEX IF NOT EXISTS idx_oneon_identities_created   ON oneon_identities(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_oneon_identities_wallet    ON oneon_identities(wallet_address) WHERE wallet_address IS NOT NULL;

-- 2. Governance proposals table
CREATE TABLE IF NOT EXISTS oneon_governance_proposals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposer_id     UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    proposal_type   TEXT NOT NULL DEFAULT 'general',               -- general | upgrade | parameter | emergency
    status          TEXT NOT NULL DEFAULT 'draft',                 -- draft | open | closed | executed | rejected
    votes_for       INTEGER NOT NULL DEFAULT 0,
    votes_against   INTEGER NOT NULL DEFAULT 0,
    quorum_required INTEGER NOT NULL DEFAULT 10,                   -- minimum votes needed
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    voting_ends_at  TIMESTAMPTZ,
    executed_at     TIMESTAMPTZ,
    CONSTRAINT oneon_governance_status_check
        CHECK (status IN ('draft', 'open', 'closed', 'executed', 'rejected')),
    CONSTRAINT oneon_governance_type_check
        CHECK (proposal_type IN ('general', 'upgrade', 'parameter', 'emergency'))
);

CREATE INDEX IF NOT EXISTS idx_oneon_governance_proposer  ON oneon_governance_proposals(proposer_id);
CREATE INDEX IF NOT EXISTS idx_oneon_governance_status    ON oneon_governance_proposals(status);
CREATE INDEX IF NOT EXISTS idx_oneon_governance_created   ON oneon_governance_proposals(created_at DESC);

-- 3. Governance votes (join table — Phase 1 gets on-chain verification)
CREATE TABLE IF NOT EXISTS oneon_governance_votes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id     UUID NOT NULL REFERENCES oneon_governance_proposals(id) ON DELETE CASCADE,
    voter_id        UUID NOT NULL REFERENCES oneon_identities(id) ON DELETE SET NULL,
    vote            TEXT NOT NULL,    -- for | against | abstain
    weight          INTEGER NOT NULL DEFAULT 1,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(proposal_id, voter_id),
    CONSTRAINT oneon_vote_check CHECK (vote IN ('for', 'against', 'abstain'))
);

CREATE INDEX IF NOT EXISTS idx_oneon_votes_proposal ON oneon_governance_votes(proposal_id);
CREATE INDEX IF NOT EXISTS idx_oneon_votes_voter    ON oneon_governance_votes(voter_id);

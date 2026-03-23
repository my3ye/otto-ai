-- Migration 072: Fix FK constraints and revenue column naming
-- Fixes identified in code review (Step 3):
--   1. proposer_id FK: ON DELETE SET NULL contradicts NOT NULL — change to RESTRICT
--   2. voter_id FK: same contradiction — change to RESTRICT
--   3. tusita revenue_ytd: rename to revenue_total (column was misleadingly named
--      "year-to-date" but never resets; total is the correct semantic)

-- 1. Fix proposer_id FK on oneon_governance_proposals
ALTER TABLE oneon_governance_proposals
    DROP CONSTRAINT oneon_governance_proposals_proposer_id_fkey;

ALTER TABLE oneon_governance_proposals
    ADD CONSTRAINT oneon_governance_proposals_proposer_id_fkey
    FOREIGN KEY (proposer_id) REFERENCES oneon_identities(id) ON DELETE RESTRICT;

-- 2. Fix voter_id FK on oneon_governance_votes
ALTER TABLE oneon_governance_votes
    DROP CONSTRAINT oneon_governance_votes_voter_id_fkey;

ALTER TABLE oneon_governance_votes
    ADD CONSTRAINT oneon_governance_votes_voter_id_fkey
    FOREIGN KEY (voter_id) REFERENCES oneon_identities(id) ON DELETE RESTRICT;

-- 3. Rename revenue_ytd → revenue_total on tusita_locations
ALTER TABLE tusita_locations RENAME COLUMN revenue_ytd TO revenue_total;

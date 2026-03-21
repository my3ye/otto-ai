-- Add CHECK constraint on athena_prospects.stage to enforce valid values at DB level
-- Valid stages: new, qualifying, qualified, disqualified, proposal_sent, closed_won, closed_lost

ALTER TABLE athena_prospects
    ADD CONSTRAINT athena_prospects_stage_check
    CHECK (stage IN ('new', 'qualifying', 'qualified', 'disqualified', 'proposal_sent', 'closed_won', 'closed_lost'));

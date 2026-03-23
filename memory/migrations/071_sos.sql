-- Migration 071: SOS Systems — Education Ladder + Refuge Network
-- Unified learner registry and case management for the education+refuge ladder.
-- Phase 0: DB/API only. No merit scoring engine, no tier advancement automation.

-- 1. SOS Learner registry
--    "Arrive from anywhere, learn by contributing what matters most, rise through effort and impact."
CREATE TABLE IF NOT EXISTS sos_learners (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handle          TEXT NOT NULL UNIQUE,                      -- may match ONEON handle
    display_name    TEXT,
    email           TEXT,
    tier            TEXT NOT NULL DEFAULT 'seed',              -- seed | sprout | apprentice | journeyman | master | elder
    origin_type     TEXT NOT NULL DEFAULT 'general',           -- general | refugee | displaced | homeless | underprivileged
    oneon_id        UUID,                                      -- link to ONEON identity (optional)
    tusita_location UUID,                                      -- current/home Tusita location (optional)
    xp_total        INTEGER NOT NULL DEFAULT 0,                -- total experience points earned
    contributions   INTEGER NOT NULL DEFAULT 0,               -- count of accepted contributions
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activated_at    TIMESTAMPTZ,
    CONSTRAINT sos_learners_tier_check
        CHECK (tier IN ('seed', 'sprout', 'apprentice', 'journeyman', 'master', 'elder')),
    CONSTRAINT sos_learners_origin_check
        CHECK (origin_type IN ('general', 'refugee', 'displaced', 'homeless', 'underprivileged'))
);

CREATE INDEX IF NOT EXISTS idx_sos_learners_handle      ON sos_learners(LOWER(handle));
CREATE INDEX IF NOT EXISTS idx_sos_learners_tier        ON sos_learners(tier);
CREATE INDEX IF NOT EXISTS idx_sos_learners_origin      ON sos_learners(origin_type);
CREATE INDEX IF NOT EXISTS idx_sos_learners_oneon       ON sos_learners(oneon_id) WHERE oneon_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_sos_learners_xp          ON sos_learners(xp_total DESC);

-- 2. SOS Contributions — learning contributions and impact records
CREATE TABLE IF NOT EXISTS sos_contributions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    learner_id      UUID NOT NULL REFERENCES sos_learners(id) ON DELETE CASCADE,
    contribution_type TEXT NOT NULL DEFAULT 'learning',        -- learning | code | content | mentorship | infrastructure | outreach
    title           TEXT NOT NULL,
    description     TEXT,
    xp_awarded      INTEGER NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending',           -- pending | accepted | rejected
    reviewer_id     UUID REFERENCES sos_learners(id),          -- peer reviewer
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ,
    CONSTRAINT sos_contributions_type_check
        CHECK (contribution_type IN ('learning', 'code', 'content', 'mentorship', 'infrastructure', 'outreach')),
    CONSTRAINT sos_contributions_status_check
        CHECK (status IN ('pending', 'accepted', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_sos_contributions_learner ON sos_contributions(learner_id);
CREATE INDEX IF NOT EXISTS idx_sos_contributions_status  ON sos_contributions(status);
CREATE INDEX IF NOT EXISTS idx_sos_contributions_type    ON sos_contributions(contribution_type);

-- 3. SOS Cases — refuge/displacement cases needing support
CREATE TABLE IF NOT EXISTS sos_cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_type       TEXT NOT NULL DEFAULT 'general',           -- general | war_zone | homelessness | underprivileged
    requester_name  TEXT NOT NULL,
    requester_email TEXT,
    location        TEXT,                                      -- approximate location / country
    description     TEXT NOT NULL,
    urgency         TEXT NOT NULL DEFAULT 'standard',          -- standard | urgent | critical
    status          TEXT NOT NULL DEFAULT 'open',              -- open | in_review | matched | resolved | closed
    tusita_ref      UUID,                                      -- matched Tusita location (cross-ref)
    learner_id      UUID REFERENCES sos_learners(id),          -- if requester becomes a learner
    assigned_to     UUID REFERENCES sos_learners(id),          -- case handler
    notes           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ,
    CONSTRAINT sos_cases_type_check
        CHECK (case_type IN ('general', 'war_zone', 'homelessness', 'underprivileged')),
    CONSTRAINT sos_cases_urgency_check
        CHECK (urgency IN ('standard', 'urgent', 'critical')),
    CONSTRAINT sos_cases_status_check
        CHECK (status IN ('open', 'in_review', 'matched', 'resolved', 'closed'))
);

CREATE INDEX IF NOT EXISTS idx_sos_cases_status   ON sos_cases(status);
CREATE INDEX IF NOT EXISTS idx_sos_cases_urgency  ON sos_cases(urgency);
CREATE INDEX IF NOT EXISTS idx_sos_cases_type     ON sos_cases(case_type);
CREATE INDEX IF NOT EXISTS idx_sos_cases_learner  ON sos_cases(learner_id) WHERE learner_id IS NOT NULL;

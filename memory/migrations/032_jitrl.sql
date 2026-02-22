-- JitRL: Just-In-Time Reinforcement Learning experience memory
-- Non-parametric experience buffer for test-time policy optimization
-- Based on arXiv:2601.18510 (Yibo Li et al., Jan 2026)
--
-- Core mechanism: store (state, action, reward) tuples.
-- At inference: embed current context, find similar past states,
-- estimate action advantages, recommend optimal action via
-- additive update rule (exact closed-form KL-constrained solution).
-- Training-free — no gradient updates required.

CREATE TABLE IF NOT EXISTS jitrl_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- State: what was the situation
    state_description TEXT NOT NULL,
    state_embedding VECTOR(1536),
    context_tags TEXT[] DEFAULT '{}',

    -- Action: what was done
    action TEXT NOT NULL,
    action_type TEXT NOT NULL DEFAULT 'generic',

    -- Outcome / reward signal (-1 to +1)
    reward FLOAT NOT NULL DEFAULT 0.0,
    outcome_label TEXT NOT NULL DEFAULT 'unknown',
    outcome_details TEXT,

    -- Policy metadata
    policy_logit FLOAT,
    advantage FLOAT,

    -- Provenance
    source TEXT DEFAULT 'task',
    source_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Vector index for fast similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS jitrl_experience_embedding_idx
    ON jitrl_experience USING ivfflat (state_embedding vector_cosine_ops)
    WITH (lists = 50);

CREATE INDEX IF NOT EXISTS jitrl_experience_action_type_idx
    ON jitrl_experience (action_type);

CREATE INDEX IF NOT EXISTS jitrl_experience_source_idx
    ON jitrl_experience (source, source_id);

CREATE INDEX IF NOT EXISTS jitrl_experience_created_idx
    ON jitrl_experience (created_at DESC);

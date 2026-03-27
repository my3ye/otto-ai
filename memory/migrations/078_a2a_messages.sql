-- A2A (Agent-to-Agent) messaging for inter-agent coordination
-- Agents in plans/workflows can send messages to peers via PostgreSQL mailbox

CREATE TABLE IF NOT EXISTS a2a_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID NOT NULL,
    sender_id TEXT NOT NULL,
    sender_agent_type TEXT,
    recipient_id TEXT,
    message_type TEXT NOT NULL DEFAULT 'message',
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    in_reply_to UUID REFERENCES a2a_messages(id),
    read_by TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT chk_message_type CHECK (message_type IN ('message', 'question', 'artifact', 'signal', 'completion'))
);

CREATE INDEX idx_a2a_channel ON a2a_messages(channel_id, created_at);
CREATE INDEX idx_a2a_recipient ON a2a_messages(recipient_id, created_at) WHERE recipient_id IS NOT NULL;
CREATE INDEX idx_a2a_unread ON a2a_messages(channel_id, created_at) WHERE array_length(read_by, 1) IS NULL OR array_length(read_by, 1) = 0;

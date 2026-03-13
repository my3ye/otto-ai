-- Add Claude Code CLI as primary streaming provider
-- Uses Mev's Claude Max subscription via CLI subprocess
INSERT INTO llm_providers (name, provider_type, base_url, model_name, api_key_env, priority, max_tokens, temperature, enabled, metadata)
VALUES (
    'claude_code_sonnet',
    'claude_code_stream',
    NULL,
    'sonnet',
    NULL,
    0,
    4096,
    0.7,
    TRUE,
    '{"timeout_seconds": 90}'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    priority = EXCLUDED.priority,
    provider_type = EXCLUDED.provider_type,
    enabled = EXCLUDED.enabled,
    temperature = EXCLUDED.temperature,
    metadata = EXCLUDED.metadata;

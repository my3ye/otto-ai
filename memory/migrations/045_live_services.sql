-- Migration 045: Live Services Monitoring
-- Two-tier model: Tasks (finite) vs Live Services (persistent/infinite)
-- Live services are monitored by service_monitor.sh daemon (no Claude budget)
BEGIN;

CREATE TABLE IF NOT EXISTS live_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT,
    service_type TEXT NOT NULL
        CHECK (service_type IN ('systemd', 'docker', 'http', 'process', 'script')),
    description TEXT,

    -- Health check config
    check_method TEXT NOT NULL,   -- same as service_type for most; 'http' for graphiti
    check_target TEXT NOT NULL,   -- URL, systemd unit, container name, process name, script path
    check_timeout_s INT NOT NULL DEFAULT 10,
    failure_threshold INT NOT NULL DEFAULT 3,   -- consecutive failures before status=down
    heartbeat_interval_s INT NOT NULL DEFAULT 300,  -- expected check interval (seconds)

    -- Data flow monitoring (optional — for services that produce output)
    expected_output_interval_s INT,    -- NULL = not monitored
    last_output_at TIMESTAMPTZ,

    -- Current state (updated by service_monitor.sh via POST /services/{id}/heartbeat)
    status TEXT NOT NULL DEFAULT 'unknown'
        CHECK (status IN ('healthy', 'degraded', 'down', 'recovering', 'unknown')),
    consecutive_failures INT NOT NULL DEFAULT 0,
    last_check_at TIMESTAMPTZ,
    last_healthy_at TIMESTAMPTZ,
    down_since TIMESTAMPTZ,

    -- Alerting
    alert_mev BOOLEAN NOT NULL DEFAULT TRUE,
    mev_alerted_at TIMESTAMPTZ,        -- tracks dedup: don't re-alert within 30min
    priority INT NOT NULL DEFAULT 5 CHECK (priority BETWEEN 1 AND 10),

    -- Lifecycle
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    auto_restart BOOLEAN NOT NULL DEFAULT FALSE,
    restart_command TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Rolling health check history (pruned to 7 days by maintenance job)
CREATE TABLE IF NOT EXISTS service_health_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES live_services(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    response_time_ms INT,
    details TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_service_health_service_id
    ON service_health_logs (service_id, checked_at DESC);

CREATE INDEX IF NOT EXISTS idx_live_services_status
    ON live_services (status) WHERE enabled = TRUE;

-- Pre-seed known infrastructure services
-- These are the services Otto depends on — monitor them from day 1
INSERT INTO live_services (name, display_name, service_type, description, check_method, check_target, failure_threshold, priority)
VALUES
    ('otto-memory',        'Memory API',          'systemd', 'Otto memory API (FastAPI :8100)',  'systemd', 'otto-memory',          3, 10),
    ('otto-memory-http',   'Memory API HTTP',     'http',    'Memory API health endpoint',        'http',    'http://localhost:8100/health', 3, 10),
    ('whatsapp',           'WhatsApp Bridge',     'systemd', 'WhatsApp interface (Baileys :3001)','systemd', 'whatsapp',             3, 9),
    ('otto-heartbeat',     'Heartbeat Timer',     'systemd', 'Orchestrator heartbeat timer',      'systemd', 'otto-heartbeat.timer', 3, 9),
    ('otto-reflection',    'Reflection Timer',    'systemd', 'Reflection heartbeat timer',        'systemd', 'otto-reflection.timer',3, 8),
    ('postgres',           'PostgreSQL',          'docker',  'PostgreSQL + pgvector (:5432)',     'docker',  'memory-postgres-1',    3, 10),
    ('neo4j',              'Neo4j',               'docker',  'Knowledge graph (:7474/:7687)',     'docker',  'memory-neo4j-1',       3, 8),
    ('graphiti',           'Graphiti',            'docker',  'Temporal knowledge graph API (:8000)','docker','memory-graphiti-1',   3, 8),
    ('graphiti-http',      'Graphiti HTTP',       'http',    'Graphiti API health check',         'http',    'http://localhost:8000/healthcheck', 3, 7)
ON CONFLICT (name) DO NOTHING;

COMMIT;

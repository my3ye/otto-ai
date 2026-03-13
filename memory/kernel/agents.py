"""Agent Registry — multi-agent configuration and lifecycle management.

Reference: arXiv 2602.20934v1 §8 (Multi-Agent Coordination)

Each agent has:
- A unique ID and role description
- Configuration (L1 capacity, drift threshold, interrupt types, CLI settings)
- Lifecycle status (idle, active, suspended, error)
- Activity log for observability
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from ..db import get_pool

log = logging.getLogger("otto.kernel.agents")


@dataclass
class AgentConfig:
    """Configuration for a kernel agent."""
    l1_capacity: int = 12000
    drift_threshold: float = 0.3
    interrupt_types: list[str] = field(default_factory=list)
    cli_agent: str | None = None       # Claude Code agent name (heartbeat, reflection)
    cli_model: str | None = None       # CLI model override
    timeout_seconds: int = 600
    max_concurrent: int = 1

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        return cls(
            l1_capacity=data.get("l1_capacity", 12000),
            drift_threshold=data.get("drift_threshold", 0.3),
            interrupt_types=data.get("interrupt_types", []),
            cli_agent=data.get("cli_agent"),
            cli_model=data.get("cli_model"),
            timeout_seconds=data.get("timeout_seconds", 600),
            max_concurrent=data.get("max_concurrent", 1),
        )


@dataclass
class KernelAgent:
    """A registered kernel agent."""
    id: str
    name: str
    role: str
    status: str = "idle"  # idle, active, suspended, error
    config: AgentConfig = field(default_factory=AgentConfig)
    last_active_at: datetime | None = None
    last_interrupt_id: UUID | None = None
    error_message: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "config": {
                "l1_capacity": self.config.l1_capacity,
                "drift_threshold": self.config.drift_threshold,
                "interrupt_types": self.config.interrupt_types,
                "cli_agent": self.config.cli_agent,
                "cli_model": self.config.cli_model,
                "timeout_seconds": self.config.timeout_seconds,
                "max_concurrent": self.config.max_concurrent,
            },
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "error_message": self.error_message,
        }


# ── In-memory cache ─────────────────────────────────────────────────────────

_agents: dict[str, KernelAgent] = {}
_loaded: bool = False


async def load_agents() -> dict[str, KernelAgent]:
    """Load all agents from DB into in-memory cache."""
    global _agents, _loaded
    pool = await get_pool()

    rows = await pool.fetch(
        """SELECT id, name, role, status, config, last_active_at,
                  last_interrupt_id, error_message
           FROM kernel_agents ORDER BY id"""
    )

    _agents = {}
    for r in rows:
        config_data = r["config"] or {}
        agent = KernelAgent(
            id=r["id"],
            name=r["name"],
            role=r["role"],
            status=r["status"] or "idle",
            config=AgentConfig.from_dict(config_data),
            last_active_at=r["last_active_at"],
            last_interrupt_id=r["last_interrupt_id"],
            error_message=r["error_message"],
        )
        _agents[agent.id] = agent

    _loaded = True
    log.info(f"Loaded {len(_agents)} kernel agents: {list(_agents.keys())}")
    return _agents


def get_agent(agent_id: str) -> KernelAgent | None:
    """Get a cached agent by ID."""
    return _agents.get(agent_id)


def get_all_agents() -> dict[str, KernelAgent]:
    """Get all cached agents."""
    return dict(_agents)


async def update_agent_status(
    agent_id: str,
    status: str,
    error_message: str | None = None,
    last_interrupt_id: UUID | None = None,
) -> None:
    """Update an agent's status in both cache and DB."""
    pool = await get_pool()
    now = datetime.now(timezone.utc)

    await pool.execute(
        """UPDATE kernel_agents
           SET status = $1, last_active_at = $2, error_message = $3,
               last_interrupt_id = $4, updated_at = $2
           WHERE id = $5""",
        status, now, error_message, last_interrupt_id, agent_id,
    )

    agent = _agents.get(agent_id)
    if agent:
        agent.status = status
        agent.last_active_at = now
        agent.error_message = error_message
        if last_interrupt_id:
            agent.last_interrupt_id = last_interrupt_id

    log.info(f"Agent {agent_id} status → {status}")


async def log_agent_activity(
    agent_id: str,
    event_type: str,
    interrupt_id: UUID | None = None,
    details: dict | None = None,
) -> None:
    """Write to agent_activity_log."""
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO agent_activity_log (agent_id, event_type, interrupt_id, details)
           VALUES ($1, $2, $3, $4)""",
        agent_id, event_type, interrupt_id, details or {},
    )


def route_interrupt_to_agent(interrupt_type: str) -> str:
    """Determine which agent should handle an interrupt type.

    Checks each agent's config.interrupt_types list.
    Falls back to 'otto' (primary agent) if no match.
    """
    for agent_id, agent in _agents.items():
        if interrupt_type in agent.config.interrupt_types:
            return agent_id
    return "otto"

"""
Live Services Monitoring — /services routes

Two-tier model: Tasks (finite) vs Live Services (persistent/infinite).
Live services are registered here and monitored by service_monitor.sh daemon.

Health check results are posted by the daemon via POST /services/{id}/heartbeat.
"""

import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..db import get_pool

log = logging.getLogger("otto.services")
router = APIRouter(prefix="/services", tags=["services"])


# ── Models ────────────────────────────────────────────────────────────

class ServiceCreate(BaseModel):
    name: str
    display_name: str | None = None
    service_type: str  # systemd | docker | http | process | script
    description: str | None = None
    check_method: str
    check_target: str
    check_timeout_s: int = 10
    failure_threshold: int = 3
    heartbeat_interval_s: int = 300
    expected_output_interval_s: int | None = None
    alert_mev: bool = True
    priority: int = Field(default=5, ge=1, le=10)
    auto_restart: bool = False
    restart_command: str | None = None
    metadata: dict = Field(default_factory=dict)


class ServiceUpdate(BaseModel):
    display_name: str | None = None
    description: str | None = None
    check_timeout_s: int | None = None
    failure_threshold: int | None = None
    heartbeat_interval_s: int | None = None
    expected_output_interval_s: int | None = None
    alert_mev: bool | None = None
    priority: int | None = None
    auto_restart: bool | None = None
    restart_command: str | None = None
    enabled: bool | None = None
    metadata: dict | None = None


class ServiceOut(BaseModel):
    id: UUID
    name: str
    display_name: str | None
    service_type: str
    description: str | None
    check_method: str
    check_target: str
    check_timeout_s: int
    failure_threshold: int
    heartbeat_interval_s: int
    expected_output_interval_s: int | None
    last_output_at: datetime | None
    status: str
    consecutive_failures: int
    last_check_at: datetime | None
    last_healthy_at: datetime | None
    down_since: datetime | None
    alert_mev: bool
    priority: int
    enabled: bool
    auto_restart: bool
    created_at: datetime
    updated_at: datetime
    metadata: dict


class HeartbeatIn(BaseModel):
    """Posted by service_monitor.sh after each health check."""
    status: str  # healthy | degraded | down | unknown
    response_time_ms: int | None = None
    details: str | None = None
    checked_at: datetime | None = None


class OutputActivity(BaseModel):
    """Posted by a live service when it produces output (data flow monitoring)."""
    details: str | None = None
    metadata: dict = Field(default_factory=dict)


class ServiceSummary(BaseModel):
    healthy: int
    degraded: int
    down: int
    recovering: int
    unknown: int
    total: int
    enabled: int


# ── Helpers ───────────────────────────────────────────────────────────

_COLS = """id, name, display_name, service_type, description,
    check_method, check_target, check_timeout_s, failure_threshold,
    heartbeat_interval_s, expected_output_interval_s, last_output_at,
    status, consecutive_failures, last_check_at, last_healthy_at,
    down_since, alert_mev, priority, enabled, auto_restart,
    created_at, updated_at, metadata"""


def _row_to_dict(row) -> dict:
    return dict(row)


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/summary", response_model=ServiceSummary)
async def get_summary():
    """Dashboard widget: counts by status for enabled services."""
    pool = await get_pool()
    rows = await pool.fetch("""
        SELECT status, COUNT(*) as cnt
        FROM live_services
        WHERE enabled = TRUE
        GROUP BY status
    """)
    counts = {r["status"]: r["cnt"] for r in rows}
    total_row = await pool.fetchrow("SELECT COUNT(*) FROM live_services WHERE enabled = TRUE")
    return ServiceSummary(
        healthy=counts.get("healthy", 0),
        degraded=counts.get("degraded", 0),
        down=counts.get("down", 0),
        recovering=counts.get("recovering", 0),
        unknown=counts.get("unknown", 0),
        total=total_row["count"] if total_row else 0,
        enabled=total_row["count"] if total_row else 0,
    )


@router.get("", response_model=list[ServiceOut])
async def list_services(include_disabled: bool = False):
    """List all registered live services with current status."""
    pool = await get_pool()
    where = "" if include_disabled else "WHERE enabled = TRUE"
    rows = await pool.fetch(f"SELECT {_COLS} FROM live_services {where} ORDER BY priority DESC, name")
    return [ServiceOut(**_row_to_dict(r)) for r in rows]


@router.post("", response_model=ServiceOut, status_code=201)
async def register_service(body: ServiceCreate):
    """Register a new live service for monitoring."""
    pool = await get_pool()
    import json
    row = await pool.fetchrow(
        f"""INSERT INTO live_services
            (name, display_name, service_type, description, check_method, check_target,
             check_timeout_s, failure_threshold, heartbeat_interval_s,
             expected_output_interval_s, alert_mev, priority, auto_restart,
             restart_command, metadata)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
            RETURNING {_COLS}""",
        body.name, body.display_name, body.service_type, body.description,
        body.check_method, body.check_target, body.check_timeout_s,
        body.failure_threshold, body.heartbeat_interval_s,
        body.expected_output_interval_s, body.alert_mev, body.priority,
        body.auto_restart, body.restart_command, json.dumps(body.metadata)
    )
    log.info(f"Registered live service: {body.name}")
    return ServiceOut(**_row_to_dict(row))


@router.get("/{service_id}", response_model=ServiceOut)
async def get_service(service_id: UUID):
    pool = await get_pool()
    row = await pool.fetchrow(f"SELECT {_COLS} FROM live_services WHERE id = $1", service_id)
    if not row:
        raise HTTPException(404, "Service not found")
    return ServiceOut(**_row_to_dict(row))


@router.put("/{service_id}", response_model=ServiceOut)
async def update_service(service_id: UUID, body: ServiceUpdate):
    """Update service configuration."""
    pool = await get_pool()
    import json
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No fields to update")
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
    sets += f", updated_at = now()"
    vals = list(updates.values())
    if "metadata" in updates:
        vals[list(updates.keys()).index("metadata")] = json.dumps(updates["metadata"])
    row = await pool.fetchrow(
        f"UPDATE live_services SET {sets} WHERE id = $1 RETURNING {_COLS}",
        service_id, *vals
    )
    if not row:
        raise HTTPException(404, "Service not found")
    return ServiceOut(**_row_to_dict(row))


@router.delete("/{service_id}", status_code=204)
async def deregister_service(service_id: UUID):
    """Deregister (disable) a service. Does not delete history."""
    pool = await get_pool()
    result = await pool.execute(
        "UPDATE live_services SET enabled = FALSE, updated_at = now() WHERE id = $1",
        service_id
    )
    if result == "UPDATE 0":
        raise HTTPException(404, "Service not found")


@router.post("/{service_id}/heartbeat")
async def record_heartbeat(service_id: UUID, body: HeartbeatIn):
    """
    Record a health check result from service_monitor.sh.
    Updates live_services status and appends to service_health_logs.
    Handles consecutive failure counting and down_since tracking.
    """
    pool = await get_pool()
    checked_at = body.checked_at or datetime.now(timezone.utc)

    svc = await pool.fetchrow(
        "SELECT id, name, status, consecutive_failures, down_since, "
        "failure_threshold, alert_mev, mev_alerted_at FROM live_services WHERE id = $1",
        service_id
    )
    if not svc:
        raise HTTPException(404, "Service not found")

    prev_status = svc["status"]
    new_failures = svc["consecutive_failures"]
    new_status = body.status
    down_since = svc["down_since"]
    last_healthy_at = None

    if body.status in ("healthy", "recovering"):
        new_failures = 0
        last_healthy_at = checked_at
        down_since = None
        # Mark recovering if coming back from down
        if prev_status == "down":
            new_status = "recovering"
            log.info(f"Service {svc['name']} recovered from down state")
            # Log recovery event
            await pool.execute(
                """INSERT INTO episodic_events (content, event_type, importance)
                   VALUES ($1, 'service_recovered', 6)""",
                f"Service recovered: {svc['name']} (was down since {svc['down_since']})"
            )
    else:
        # Failed check
        new_failures += 1
        if new_failures >= svc["failure_threshold"]:
            new_status = "down"
            if down_since is None:
                down_since = checked_at
                log.warning(f"Service {svc['name']} is DOWN (failures={new_failures})")
                # Log down event
                await pool.execute(
                    """INSERT INTO episodic_events (content, event_type, importance)
                       VALUES ($1, 'wink_critical', 8)""",
                    f"Live service DOWN: {svc['name']} — {body.details or 'no details'}"
                )

    # Check if we need to alert Mev (down 30+ min, alert_mev, not alerted recently)
    should_alert_mev = False
    if (new_status == "down" and down_since and svc["alert_mev"]):
        down_duration = (checked_at - down_since).total_seconds()
        last_alerted = svc["mev_alerted_at"]
        if down_duration >= 1800:  # 30 minutes
            if not last_alerted or (checked_at - last_alerted).total_seconds() > 1800:
                should_alert_mev = True

    # Build update query
    update_fields = {
        "status": new_status,
        "consecutive_failures": new_failures,
        "last_check_at": checked_at,
        "down_since": down_since,
        "updated_at": datetime.now(timezone.utc),
    }
    if last_healthy_at:
        update_fields["last_healthy_at"] = last_healthy_at
    if should_alert_mev:
        update_fields["mev_alerted_at"] = checked_at

    await pool.execute(
        """UPDATE live_services SET
            status = $2,
            consecutive_failures = $3,
            last_check_at = $4,
            down_since = $5,
            updated_at = $6
            WHERE id = $1""",
        service_id, new_status, new_failures, checked_at, down_since,
        update_fields["updated_at"]
    )
    if last_healthy_at:
        await pool.execute(
            "UPDATE live_services SET last_healthy_at = $2 WHERE id = $1",
            service_id, last_healthy_at
        )
    if should_alert_mev:
        await pool.execute(
            "UPDATE live_services SET mev_alerted_at = $2 WHERE id = $1",
            service_id, checked_at
        )

    # Append to health log
    await pool.execute(
        """INSERT INTO service_health_logs (service_id, status, response_time_ms, details, checked_at)
           VALUES ($1, $2, $3, $4, $5)""",
        service_id, new_status, body.response_time_ms, body.details, checked_at
    )

    return {
        "service": svc["name"],
        "status": new_status,
        "consecutive_failures": new_failures,
        "alert_mev": should_alert_mev,
    }


@router.post("/{service_id}/output")
async def record_output(service_id: UUID, body: OutputActivity):
    """
    Record data flow activity from a live service.
    Resets the data flow stall timer. Call this whenever the service produces output.
    """
    pool = await get_pool()
    now = datetime.now(timezone.utc)
    result = await pool.execute(
        """UPDATE live_services
           SET last_output_at = $2,
               status = CASE WHEN status = 'degraded' THEN 'healthy' ELSE status END,
               updated_at = $2
           WHERE id = $1""",
        service_id, now
    )
    if result == "UPDATE 0":
        raise HTTPException(404, "Service not found")
    return {"last_output_at": now.isoformat()}


@router.get("/{service_id}/health-log")
async def get_health_log(service_id: UUID, limit: int = 50):
    """Get recent health check history for a service."""
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, status, response_time_ms, details, checked_at
           FROM service_health_logs
           WHERE service_id = $1
           ORDER BY checked_at DESC
           LIMIT $2""",
        service_id, limit
    )
    return [dict(r) for r in rows]

"""
Central OpenTelemetry setup for Otto Memory API.
Called once from api.py lifespan. Env-var gated via OTEL_ENABLED.
"""
import logging

logger = logging.getLogger(__name__)


def _server_request_hook(span, scope):
    """Enrich auto-instrumented spans with route-specific attributes.

    Called by FastAPIInstrumentor for every request. Adds business context
    to key routes: /tasks, /semantic/search, /episodic/timeline, /kernel/status.
    """
    if not span or not span.is_recording():
        return
    path = scope.get("path", "")
    method = scope.get("method", "")

    # Tag high-value routes for easier filtering in trace analysis
    if "/tasks" in path:
        span.set_attribute("otto.domain", "tasks")
        span.set_attribute("otto.route_group", "task_queue")
    elif "/semantic" in path:
        span.set_attribute("otto.domain", "semantic_memory")
        span.set_attribute("otto.route_group", "memory")
    elif "/episodic" in path:
        span.set_attribute("otto.domain", "episodic_memory")
        span.set_attribute("otto.route_group", "memory")
    elif "/kernel" in path:
        span.set_attribute("otto.domain", "kernel")
        span.set_attribute("otto.route_group", "agentos")
    elif "/workflows" in path:
        span.set_attribute("otto.domain", "workflows")
        span.set_attribute("otto.route_group", "orchestration")


def setup_telemetry(app, settings) -> bool:
    """Initialize OTel tracing. Returns True if enabled, False otherwise.

    Safe to call even if OTel packages are not installed — returns False.
    """
    if not settings.otel_enabled:
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from .telemetry_exporters import JSONLFileExporter
    except ImportError as e:
        logger.warning(f"OTel packages not installed, skipping instrumentation: {e}")
        return False

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "0.1.0",
        "deployment.environment": settings.otel_environment,
    })

    provider = TracerProvider(resource=resource)

    # File exporter (JSONL) — always active when OTel is enabled
    provider.add_span_processor(
        BatchSpanProcessor(JSONLFileExporter(settings.otel_log_dir))
    )

    # Optional OTLP exporter for future collector
    if settings.otel_export_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=settings.otel_export_endpoint)
                )
            )
        except ImportError:
            logger.warning("OTLP exporter not installed, skipping remote export")

    trace.set_tracer_provider(provider)

    # Auto-instrument FastAPI — covers ALL routes with zero route changes
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="hello,mcp-status",
        server_request_hook=_server_request_hook,
    )

    # Prune old trace files on startup
    cleanup_old_traces(settings.otel_log_dir, settings.otel_trace_retention_days)

    logger.info(
        f"OpenTelemetry enabled: service={settings.otel_service_name}, "
        f"traces_dir={settings.otel_log_dir}"
    )
    return True


def cleanup_old_traces(log_dir: str, retention_days: int = 30) -> int:
    """Delete trace files older than retention_days. Returns count of files removed."""
    import os
    from datetime import datetime, timedelta, timezone

    if not os.path.isdir(log_dir):
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for fname in os.listdir(log_dir):
        if not fname.startswith("traces-") or not fname.endswith(".jsonl"):
            continue
        # Extract date from traces-YYYY-MM-DD.jsonl
        try:
            date_str = fname[7:-6]  # strip "traces-" and ".jsonl"
            file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if file_date < cutoff:
            try:
                os.remove(os.path.join(log_dir, fname))
                removed += 1
            except OSError:
                pass
    if removed:
        logger.info(f"Cleaned up {removed} trace files older than {retention_days} days")
    return removed


def shutdown_telemetry():
    """Flush pending spans and shutdown the tracer provider."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    except Exception as e:
        logger.warning(f"OTel shutdown error (non-fatal): {e}")

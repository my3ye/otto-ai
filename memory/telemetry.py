"""
Central OpenTelemetry setup for Otto Memory API.
Called once from api.py lifespan. Env-var gated via OTEL_ENABLED.
"""
import logging

logger = logging.getLogger(__name__)


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
        "deployment.environment": "production",
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
        excluded_urls="health,hello",
    )

    logger.info(
        f"OpenTelemetry enabled: service={settings.otel_service_name}, "
        f"traces_dir={settings.otel_log_dir}"
    )
    return True


def shutdown_telemetry():
    """Flush pending spans and shutdown the tracer provider."""
    try:
        from opentelemetry import trace

        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
    except Exception as e:
        logger.warning(f"OTel shutdown error (non-fatal): {e}")

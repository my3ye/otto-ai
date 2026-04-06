"""
Reusable OTel tracing helpers for route-level custom spans.
Import `get_tracer` and use `tracer.start_as_current_span(...)` in routes.
"""
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_NOOP_TRACER = None


class _NoopSpan:
    """Minimal no-op span for when OTel is disabled."""
    def set_attribute(self, key, value): pass
    def set_status(self, status): pass
    def record_exception(self, exc): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


class _NoopTracer:
    """Returns no-op spans so route code doesn't need if/else guards."""
    def start_as_current_span(self, name, **kwargs):
        return _NoopSpan()


def get_tracer(name: str = "otto.routes"):
    """Get an OTel tracer, or a no-op if OTel is not enabled."""
    global _NOOP_TRACER
    try:
        from opentelemetry import trace
        provider = trace.get_tracer_provider()
        # If no real provider is set, OTel isn't configured
        if hasattr(provider, 'get_tracer'):
            tracer = provider.get_tracer(name)
            if tracer:
                return tracer
    except ImportError:
        pass
    if _NOOP_TRACER is None:
        _NOOP_TRACER = _NoopTracer()
    return _NOOP_TRACER


def inject_trace_headers() -> dict[str, str]:
    """Extract current trace context as HTTP headers for propagation.

    Returns dict like {"traceparent": "00-<trace_id>-<span_id>-01"}.
    Empty dict if OTel is not active or no current span.
    """
    try:
        from opentelemetry import context
        from opentelemetry.propagate import inject
        headers: dict[str, str] = {}
        inject(headers)
        return headers
    except ImportError:
        return {}

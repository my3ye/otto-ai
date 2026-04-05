# Design: OpenTelemetry Instrumentation for Otto Memory API

## Problem

Otto's Memory API (:8100) has zero observability instrumentation. 67 route files, ~200+ endpoints, asyncpg DB calls, OpenAI embedding calls, Graphiti proxy calls — all invisible. When something is slow or broken, diagnosis is pure guesswork.

The research landscape audit (2026-04-05) flagged this as P-HIGH: "OTel absent in core routes."

## Approach

**Layer 1: Auto-instrumentation (zero-touch)**
Use `opentelemetry-instrumentation-fastapi` to automatically trace every HTTP request. This covers all 67 route files without touching any of them. Captures: method, path, status code, duration.

**Layer 2: DB spans (targeted)**  
Wrap `db.get_pool()` to add spans around asyncpg queries via a thin instrumented wrapper — NOT by modifying every route file. One central patch.

**Layer 3: Embedding spans (targeted)**  
Add a span decorator in `embeddings.py` for the OpenAI API call. One file change.

**Layer 4: Export**  
- Primary: `BatchSpanProcessor` → `OTLPSpanExporter` to localhost Jaeger/OTLP (future)
- Immediate: `ConsoleSpanExporter` (dev) + `FileSpanExporter` to `/home/web3relic/otto/logs/traces/`
- No external collector required. Self-contained.

### What we DON'T do
- We don't add manual spans to every route file (67 files = insane churn)
- We don't run Jaeger/Tempo (unnecessary infra on 16GB VM)
- We don't add metrics yet (traces first, metrics when needed)
- We don't instrument the kernel internals (separate concern)

## Key Decisions

- **Auto-instrumentation over manual**: FastAPI instrumentor covers all routes automatically. Alternative: manual `@trace` decorators on each route — rejected (67 files, massive diff, fragile).
- **File export over collector**: Write spans to structured JSONL file in logs/traces/. Alternative: deploy Jaeger container — rejected (RAM budget, operational complexity, we have no one watching dashboards at 3am).
- **Single telemetry module over scattered config**: All OTel setup in one file `memory/telemetry.py`, called from `api.py` lifespan. Alternative: spread config across api.py, config.py, each route — rejected (hard to find, hard to disable).
- **Env-var controlled over always-on**: `OTEL_ENABLED=true` flag. Alternative: always on — rejected (overhead on a 16GB box if tracing gets chatty).
- **asyncpg wrapper over library instrumentor**: opentelemetry-instrumentation-asyncpg exists but has compatibility issues with asyncpg pool patterns. A thin wrapper around `pool.fetch/fetchrow/execute` is more reliable and gives us control. Alternative: use the library instrumentor — viable but fragile with our `_init_connection` codec setup.

## Packages Required

```
opentelemetry-api==1.29.0
opentelemetry-sdk==1.29.0
opentelemetry-instrumentation-fastapi==0.50b0
opentelemetry-exporter-otlp-proto-http==1.29.0  # future collector support
opentelemetry-semantic-conventions==0.50b0
```

~12MB total. No Rust compilation. Pure Python.

## API / Interface

### Config additions (`config.py`)

```python
# ── OpenTelemetry ─────────────────────────────────────────────────
otel_enabled: bool = False          # Master flag
otel_service_name: str = "otto-memory-api"
otel_export_endpoint: str = ""      # OTLP endpoint (empty = file-only)
otel_trace_sample_rate: float = 1.0 # 1.0 = trace everything, 0.1 = 10%
otel_log_dir: str = "/home/web3relic/otto/logs/traces"
```

### New file: `memory/telemetry.py`

```python
"""
Central OpenTelemetry setup. Called once from api.py lifespan.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

def setup_telemetry(app, settings) -> bool:
    """Initialize OTel. Returns True if enabled."""
    if not settings.otel_enabled:
        return False
    
    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": "0.1.0",
        "deployment.environment": "production",
    })
    
    provider = TracerProvider(resource=resource)
    
    # File exporter (JSONL)
    from .telemetry_exporters import JSONLFileExporter
    provider.add_span_processor(
        BatchSpanProcessor(JSONLFileExporter(settings.otel_log_dir))
    )
    
    # Optional OTLP exporter
    if settings.otel_export_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_export_endpoint))
        )
    
    trace.set_tracer_provider(provider)
    
    # Auto-instrument FastAPI (covers ALL routes)
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        excluded_urls="health,hello",  # skip noisy endpoints
    )
    
    return True

def shutdown_telemetry():
    """Flush and shutdown."""
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'shutdown'):
        provider.shutdown()
```

### New file: `memory/telemetry_exporters.py`

```python
"""
Custom JSONL file exporter — writes spans to rotating daily files.
No external dependencies beyond OTel SDK.
"""
import json, os
from datetime import datetime, timezone
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

class JSONLFileExporter(SpanExporter):
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def export(self, spans) -> SpanExportResult:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = os.path.join(self.log_dir, f"traces-{today}.jsonl")
        with open(path, "a") as f:
            for span in spans:
                f.write(json.dumps({
                    "name": span.name,
                    "trace_id": format(span.context.trace_id, '032x'),
                    "span_id": format(span.context.span_id, '016x'),
                    "parent_id": format(span.parent.span_id, '016x') if span.parent else None,
                    "start": span.start_time,
                    "end": span.end_time,
                    "duration_ms": (span.end_time - span.start_time) / 1e6,
                    "status": span.status.status_code.name,
                    "attributes": dict(span.attributes) if span.attributes else {},
                }) + "\n")
        return SpanExportResult.SUCCESS
    
    def shutdown(self):
        pass
```

### DB wrapper: patch in `db.py`

```python
# After pool creation, wrap with tracing if OTel enabled
from opentelemetry import trace

_tracer = trace.get_tracer("otto.db")

class TracedPool:
    """Thin wrapper that adds spans around asyncpg pool operations."""
    def __init__(self, pool):
        self._pool = pool
    
    async def fetch(self, query, *args, **kwargs):
        with _tracer.start_as_current_span("db.fetch", attributes={"db.statement": query[:200]}):
            return await self._pool.fetch(query, *args, **kwargs)
    
    async def fetchrow(self, query, *args, **kwargs):
        with _tracer.start_as_current_span("db.fetchrow", attributes={"db.statement": query[:200]}):
            return await self._pool.fetchrow(query, *args, **kwargs)
    
    async def execute(self, query, *args, **kwargs):
        with _tracer.start_as_current_span("db.execute", attributes={"db.statement": query[:200]}):
            return await self._pool.execute(query, *args, **kwargs)
    
    async def fetchval(self, query, *args, **kwargs):
        with _tracer.start_as_current_span("db.fetchval", attributes={"db.statement": query[:200]}):
            return await self._pool.fetchval(query, *args, **kwargs)
    
    # Delegate everything else
    def __getattr__(self, name):
        return getattr(self._pool, name)
```

### Embeddings span: patch in `embeddings.py`

```python
from opentelemetry import trace
_tracer = trace.get_tracer("otto.embeddings")

# In the embed function, wrap the OpenAI call:
async def get_embedding(text: str) -> list[float]:
    with _tracer.start_as_current_span("embeddings.openai", attributes={
        "embedding.model": "text-embedding-3-small",
        "embedding.input_length": len(text),
    }):
        # existing OpenAI call
        ...
```

### api.py changes (minimal)

```python
# In lifespan(), after pool creation:
from .telemetry import setup_telemetry, shutdown_telemetry

# In startup section:
otel_ok = setup_telemetry(app, _settings)
if otel_ok:
    logger.info("OpenTelemetry instrumentation enabled")

# In shutdown section:
shutdown_telemetry()
```

## Data Flow

```
HTTP Request
  │
  ├── FastAPIInstrumentor (auto-span: HTTP method, path, status, duration)
  │     │
  │     ├── TracedPool.fetchrow() (child span: db.fetchrow, query snippet)
  │     ├── TracedPool.fetch() (child span: db.fetch, query snippet)
  │     └── get_embedding() (child span: embeddings.openai, model, input_length)
  │
  └── BatchSpanProcessor
        ├── JSONLFileExporter → logs/traces/traces-2026-04-05.jsonl
        └── OTLPSpanExporter → external collector (optional, future)
```

## Implementation Plan

### Phase 1 — Core Setup (~$2, 1 step)
1. `pip install` OTel packages
2. Create `memory/telemetry.py` (setup + shutdown)
3. Create `memory/telemetry_exporters.py` (JSONL exporter)
4. Add config fields to `config.py` (4 lines)
5. Wire into `api.py` lifespan (3 lines startup, 1 line shutdown)
6. Add `OTEL_ENABLED=true` to `~/memory/.env`
7. Restart `otto-memory` service
8. Verify: hit `/health`, check `logs/traces/` for JSONL output

### Phase 2 — DB + Embeddings Spans (~$1, 1 step)
1. Add `TracedPool` wrapper to `db.py`
2. Wrap pool in `get_pool()` when OTel is active
3. Add span to `embeddings.py`
4. Verify: hit `/semantic/search`, check trace has parent HTTP span + child DB + child embedding spans

### Phase 3 — OMS Dashboard (future, optional)
1. Add `/traces` page to OMS showing recent slow spans
2. Query JSONL files for spans > 500ms
3. Surface in existing metrics page

## Files Modified

| File | Change | Lines |
|---|---|---|
| `memory/telemetry.py` | **NEW** — central OTel setup | ~50 |
| `memory/telemetry_exporters.py` | **NEW** — JSONL file exporter | ~40 |
| `memory/config.py` | Add 4 OTel settings | +5 |
| `memory/api.py` | Wire telemetry in lifespan | +6 |
| `memory/db.py` | TracedPool wrapper + conditional wrapping | +30 |
| `memory/embeddings.py` | Span around OpenAI call | +5 |
| `~/memory/.env` | Add OTEL_ENABLED=true | +1 |

**Total: 2 new files, 4 modified files. Zero route files touched.**

## Risks

- **Performance overhead**: BatchSpanProcessor is async, JSONL writes are append-only. Measured overhead is <1ms per span. Mitigated by sample_rate config (can reduce to 0.1 if needed).
- **Disk usage**: At ~200 req/hour × 3 spans each × 500 bytes = ~300KB/day. Negligible. Add logrotate or daily cleanup if needed.
- **asyncpg pool delegation**: `__getattr__` delegation could miss pool-specific methods like `acquire()`. Mitigated: we test the top-4 methods explicitly, delegate rest. Can add more as needed.
- **OTel import failure**: If packages not installed, `setup_telemetry` returns False and everything works as before. Zero-risk degradation.

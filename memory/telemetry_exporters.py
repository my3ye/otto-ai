"""
Custom JSONL file exporter for OpenTelemetry spans.
Writes to daily rotating files in logs/traces/.
No external dependencies beyond OTel SDK.
"""
import json
import os
from datetime import datetime, timezone

from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class JSONLFileExporter(SpanExporter):
    """Append-only JSONL exporter — one file per day."""

    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def export(self, spans) -> SpanExportResult:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = os.path.join(self.log_dir, f"traces-{today}.jsonl")
        try:
            with open(path, "a") as f:
                for span in spans:
                    f.write(json.dumps({
                        "name": span.name,
                        "trace_id": format(span.context.trace_id, "032x"),
                        "span_id": format(span.context.span_id, "016x"),
                        "parent_id": (
                            format(span.parent.span_id, "016x") if span.parent else None
                        ),
                        "start": span.start_time,
                        "end": span.end_time,
                        "duration_ms": round((span.end_time - span.start_time) / 1e6, 2),
                        "status": span.status.status_code.name,
                        "attributes": dict(span.attributes) if span.attributes else {},
                    }) + "\n")
            return SpanExportResult.SUCCESS
        except Exception:
            return SpanExportResult.FAILURE

    def shutdown(self):
        pass

"""OpenTelemetry bootstrap for traces, metrics, and logs.

Call setup_telemetry() once at service startup. All supported libraries
(FastAPI, httpx, Redis, psycopg2) are auto-instrumented with zero code changes.
"""

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_telemetry(
    service_name: str,
    otlp_endpoint: str = "http://localhost:4317",
    enabled: bool = True,
) -> None:
    """Initialize OpenTelemetry for the service.

    Args:
        service_name: Identifies this service in traces and metrics.
        otlp_endpoint: OTEL Collector gRPC endpoint.
        enabled: Set False to disable telemetry (e.g., in unit tests).
    """
    if not enabled:
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "0.1.0",
        }
    )

    # ── Traces ─────────────────────────────────────────────────────────
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # ── Metrics ────────────────────────────────────────────────────────
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True),
        export_interval_millis=30_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # ── Auto-instrument libraries ──────────────────────────────────────
    _auto_instrument()


def _auto_instrument() -> None:
    """Auto-instrument supported libraries. Safe to call if library not installed."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor.instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except ImportError:
        pass

    try:
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

        Psycopg2Instrumentor().instrument()
    except ImportError:
        pass


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for creating custom spans."""
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for creating custom metrics."""
    return metrics.get_meter(name)

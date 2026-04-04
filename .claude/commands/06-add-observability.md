# Phase 6: Observability -- Build Full-Stack Tracing, Metrics, and Logging

## What You Will Learn
- OpenTelemetry (OTEL) for vendor-neutral, unified telemetry
- Three pillars: traces (Tempo), logs (Loki), metrics (Mimir)
- OTEL Collector as a telemetry pipeline
- Custom business metrics (inference latency, cache hit rate, cost/inference)
- Grafana dashboards with pre-built JSON models
- Trace context propagation across async microservice boundaries

## Prerequisites
- Phase 5 complete (All services running, LLM inference working)
- Understanding of HTTP headers and distributed systems concepts

## Background: Why OTEL Over Langfuse/OpenLIT?
The reference app uses Langfuse and OpenLIT -- LLM-specific observability tools.
In a production system with 6 microservices, a mesh, and a CI/CD pipeline, LLM
traces are only one signal among many. OTEL provides a vendor-neutral, unified
pipeline for ALL telemetry. LLM-specific attributes (model_name, token_count, cost)
are added as custom span attributes on OTEL traces. The Grafana stack provides the
backend. This avoids vendor lock-in and gives correlated traces from the frontend
click through the mesh to the LLM inference -- something Langfuse alone cannot do.

## Step-by-Step Instructions

### Step 1: Implement the Telemetry Bootstrap

Update `libs/py-common/src/agent_platform_common/telemetry.py`:

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor

def setup_telemetry(service_name: str) -> None:
    resource = Resource.create({"service.name": service_name})

    # Traces -> OTEL Collector -> Tempo
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics -> OTEL Collector -> Mimir
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument libraries
    FastAPIInstrumentor.instrument()
    HTTPXClientInstrumentor.instrument()
    RedisInstrumentor.instrument()
    Psycopg2Instrumentor.instrument()
```

**Key insight:** Auto-instrumentation means every FastAPI request, every httpx call
between services, every Redis command, and every Postgres query automatically creates
a trace span. Zero code changes in your business logic.

### Step 2: Add Custom Span Attributes for LLM Calls

In `services/agent-engine/src/agent_engine/llm_client.py`, add:
```python
from opentelemetry import trace

tracer = trace.get_tracer("agent-engine.llm")

async def chat(self, messages, **kwargs):
    with tracer.start_as_current_span("llm.inference") as span:
        span.set_attribute("llm.model", kwargs.get("model", "unknown"))
        span.set_attribute("llm.provider", "vllm" if primary_healthy else "llama-cpp")
        result = await client.chat.completions.create(...)
        span.set_attribute("llm.prompt_tokens", result.usage.prompt_tokens)
        span.set_attribute("llm.completion_tokens", result.usage.completion_tokens)
        span.set_attribute("llm.cost_usd", self.estimate_cost(...))
        return result
```

### Step 3: Create Custom Business Metrics

```python
meter = metrics.get_meter("agent-platform")

inference_latency = meter.create_histogram(
    "llm.inference.latency_ms",
    description="LLM inference latency in milliseconds",
    unit="ms",
)
cache_hit_counter = meter.create_counter(
    "cache.semantic.hits",
    description="Semantic cache hit count",
)
cache_miss_counter = meter.create_counter(
    "cache.semantic.misses",
    description="Semantic cache miss count",
)
inference_cost = meter.create_histogram(
    "llm.inference.cost_usd",
    description="Cost per inference in USD",
    unit="usd",
)
```

### Step 4: Deploy the OTEL Collector

Create `infra/helm/values/otel-collector.yaml`:
```yaml
config:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
  processors:
    batch:
      timeout: 5s
      send_batch_size: 1024
  exporters:
    otlp/tempo:
      endpoint: tempo:4317
      tls:
        insecure: true
    loki:
      endpoint: http://loki:3100/loki/api/v1/push
    prometheusremotewrite:
      endpoint: http://mimir:9009/api/v1/push
  service:
    pipelines:
      traces:
        receivers: [otlp]
        processors: [batch]
        exporters: [otlp/tempo]
      logs:
        receivers: [otlp]
        processors: [batch]
        exporters: [loki]
      metrics:
        receivers: [otlp]
        processors: [batch]
        exporters: [prometheusremotewrite]
```

**The Collector is a pipeline:** Receive OTLP from all services -> batch for efficiency
-> fan out to Tempo (traces), Loki (logs), Mimir (metrics). One pipeline, three backends.

### Step 5: Deploy Grafana Stack

Create `infra/helm/values/grafana-stack.yaml` with Tempo, Loki, Mimir, and Grafana.

From merit-aiml docker-compose (for local dev):
- `grafana/tempo:2.6.1` -- Distributed tracing backend
- `grafana/loki:3.3.2` -- Log aggregation
- `prom/prometheus:v2.54.1` -- Metrics (Mimir for production)
- `grafana/grafana:11.4.0` -- Visualization

### Step 6: Create Grafana Dashboards

Create pre-built dashboard JSON models for:
1. **Service Map** -- Request flow between services (auto-generated from traces)
2. **Inference Latency** -- p50/p95/p99 histogram by model and provider
3. **Cache Hit Rate** -- Semantic cache effectiveness over time
4. **Cost per Inference** -- USD per request broken down by model
5. **Error Rate** -- 5xx errors by service with drill-down to traces

### Step 7: Add Frontend Observability

Update `frontend/src/app/observability/page.tsx` to embed Grafana dashboards via iframe
with authentication passthrough.

## Verification
```bash
# Make a request through the full stack
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{"query":"mutation { sendMessage(agentId:\"weather\", content:\"Weather in Paris?\") { response } }"}'

# Open Grafana at http://localhost:3001
# Navigate to Explore -> Tempo -> Search for recent traces
# You should see: gateway -> agent-engine -> llm-runtime (with all custom attributes)

# Check Loki for structured logs
# Check Prometheus/Mimir for custom metrics
```

## Key Concepts Taught
1. **Three pillars** -- Traces (what happened), Logs (why it happened), Metrics (how much happened)
2. **OTEL Collector** -- Central telemetry pipeline decoupling producers from backends
3. **Auto-instrumentation** -- Zero-code observability for FastAPI, httpx, Redis, Postgres
4. **Custom span attributes** -- Business context (model, tokens, cost) on technical traces
5. **Trace context propagation** -- Correlated trace IDs across async service boundaries

## What's Next
Phase 7 (`/07-setup-mesh`) adds Istio ambient mesh for zero-trust networking with
mTLS between all services, plus Contour/Envoy for ingress routing.

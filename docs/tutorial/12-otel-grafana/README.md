# Tutorial 12: OpenTelemetry + Grafana Stack (Tempo, Loki, Mimir)

> **Objective:** Learn full-stack observability — traces, logs, and metrics — across the entire AI platform.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [OpenTelemetry Concepts](#2-opentelemetry-concepts)
3. [Grafana Stack](#3-grafana-stack)
4. [Installation & Setup](#4-installation--setup)
5. [Exercises](#5-exercises)
6. [How It's Used in Our Project](#6-how-its-used-in-our-project)
7. [Further Reading](#7-further-reading)

---

## 1. Introduction

### Three Pillars of Observability

| Pillar | What | Tool |
|--------|------|------|
| **Traces** | Request path across services | Grafana Tempo |
| **Logs** | Text records of events | Grafana Loki |
| **Metrics** | Numerical measurements over time | Grafana Mimir |

### What is OpenTelemetry?

**OpenTelemetry (OTEL)** is a vendor-neutral standard for collecting telemetry data. You instrument once, send to any backend.

```
Your App → [OTEL SDK] → [OTEL Collector] → Tempo (traces)
                                          → Loki (logs)
                                          → Mimir (metrics)
```

---

## 2. OpenTelemetry Concepts

### 2.1 Traces and Spans

A **trace** tracks a request across services. Each step is a **span**:

```
Trace: user-query-abc123
├── Span: API Gateway (50ms)
│   ├── Span: Auth middleware (5ms)
│   └── Span: GraphQL resolver (45ms)
│       ├── Span: Cache lookup (2ms) [MISS]
│       ├── Span: Agent engine (200ms)
│       │   ├── Span: LangGraph execution (180ms)
│       │   └── Span: Tool call: search (20ms)
│       └── Span: vLLM inference (1500ms)
│           ├── Span: Token generation (1450ms)
│           └── Span: Response formatting (50ms)
└── Total: 1750ms
```

### 2.2 Context Propagation

Trace context flows across services via HTTP headers:

```
Service A                        Service B
  │                                │
  ├─ traceparent: 00-abc123...  ──►│
  │                                ├─ Creates child span
  │                                │   with same trace ID
```

### 2.3 OTEL Collector

The Collector receives, processes, and exports telemetry:

```
Apps → [Receivers] → [Processors] → [Exporters]
         │              │               │
         OTLP         Batch          Tempo
         Jaeger       Filter         Loki
         Zipkin       Attributes     Mimir
         Prometheus   Sampling       Jaeger
```

---

## 3. Grafana Stack

| Component | Purpose | Data Type |
|-----------|---------|-----------|
| **Tempo** | Distributed tracing backend | Traces |
| **Loki** | Log aggregation (like Prometheus for logs) | Logs |
| **Mimir** | Long-term metrics storage | Metrics |
| **Grafana** | Visualization and dashboards | All |

---

## 4. Installation & Setup

### Docker Compose

```yaml
# docker-compose.yml
version: "3.8"
services:
  # OTEL Collector
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports:
      - "4317:4317"   # OTLP gRPC
      - "4318:4318"   # OTLP HTTP
    volumes:
      - ./otel-config.yaml:/etc/otel/config.yaml
    command: ["--config=/etc/otel/config.yaml"]

  # Grafana Tempo (traces)
  tempo:
    image: grafana/tempo:latest
    ports:
      - "3200:3200"
    volumes:
      - ./tempo.yaml:/etc/tempo.yaml
    command: ["-config.file=/etc/tempo.yaml"]

  # Grafana Loki (logs)
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  # Grafana Mimir (metrics)
  mimir:
    image: grafana/mimir:latest
    ports:
      - "9009:9009"
    command: ["-config.file=/etc/mimir/mimir.yaml"]

  # Grafana (dashboards)
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    volumes:
      - ./grafana-datasources.yaml:/etc/grafana/provisioning/datasources/ds.yaml
```

```yaml
# otel-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
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

```bash
docker compose up -d
# Grafana: http://localhost:3000 (admin/admin)
```

---

## 5. Exercises

### Exercise 1: Auto-Instrument a FastAPI App

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install  # Auto-install instrumentors
```

```python
# app.py
from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/chat")
async def chat(prompt: str):
    time.sleep(0.1)  # Simulate processing
    return {"response": f"Reply to: {prompt}"}
```

```bash
# Run with auto-instrumentation
opentelemetry-instrument \
  --service_name ai-api \
  --traces_exporter otlp \
  --metrics_exporter otlp \
  --logs_exporter otlp \
  --exporter_otlp_endpoint http://localhost:4317 \
  uvicorn app:app --port 8000

# Make requests — traces appear in Grafana automatically!
curl http://localhost:8000/health
curl -X POST "http://localhost:8000/chat?prompt=hello"
```

---

### Exercise 2: Manual Span Creation

```python
# manual_spans.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Setup
resource = Resource.create({"service.name": "ai-api"})
provider = TracerProvider(resource=resource)
exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
provider.add_span_processor(BatchSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer("ai-platform")

# Manual instrumentation
async def process_query(prompt: str):
    with tracer.start_as_current_span("process_query") as span:
        span.set_attribute("prompt.length", len(prompt))
        span.set_attribute("prompt.text", prompt[:100])

        # Cache lookup
        with tracer.start_as_current_span("cache_lookup") as cache_span:
            cached = check_cache(prompt)
            cache_span.set_attribute("cache.hit", cached is not None)
            if cached:
                return cached

        # LLM inference
        with tracer.start_as_current_span("llm_inference") as llm_span:
            llm_span.set_attribute("model.name", "llama-3-70b")
            result = await call_llm(prompt)
            llm_span.set_attribute("tokens.generated", result.tokens)
            llm_span.set_attribute("latency_ms", result.latency)

        # Record event
        span.add_event("query_completed", {
            "tokens": result.tokens,
            "cache_hit": False,
        })

        return result
```

---

### Exercise 3: Structured Logging with Loki

```python
# structured_logging.py
import logging
import json
from opentelemetry import trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter

# Setup OTEL log exporter
log_provider = LoggerProvider()
log_exporter = OTLPLogExporter(endpoint="http://localhost:4317", insecure=True)
log_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
set_logger_provider(log_provider)

# Configure Python logger
handler = LoggingHandler(level=logging.DEBUG, logger_provider=log_provider)
logger = logging.getLogger("ai-platform")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Structured logging (automatically correlated with traces)
def log_inference(model: str, prompt: str, latency_ms: float, tokens: int):
    logger.info(
        "Inference completed",
        extra={
            "model": model,
            "prompt_length": len(prompt),
            "latency_ms": latency_ms,
            "tokens": tokens,
        },
    )

# Logs in Loki can be queried:
# {service_name="ai-platform"} |= "Inference completed" | json | latency_ms > 500
```

---

### Exercise 4: Custom Metrics

```python
# custom_metrics.py
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Setup
exporter = OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True)
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=5000)
provider = MeterProvider(metric_readers=[reader])
metrics.set_meter_provider(provider)

meter = metrics.get_meter("ai-platform")

# Counter — total count of events
request_counter = meter.create_counter(
    "ai.requests.total",
    description="Total inference requests",
    unit="requests",
)

# Histogram — distribution of values
latency_histogram = meter.create_histogram(
    "ai.inference.latency",
    description="Inference latency in milliseconds",
    unit="ms",
)

# Gauge — current value
active_requests = meter.create_up_down_counter(
    "ai.requests.active",
    description="Currently active requests",
)

# Usage
def record_inference(model: str, latency_ms: float, tokens: int):
    attrs = {"model": model}
    request_counter.add(1, attrs)
    latency_histogram.record(latency_ms, attrs)

# Track active requests
active_requests.add(1, {"model": "llama-3"})   # Request starts
# ... inference ...
active_requests.add(-1, {"model": "llama-3"})  # Request ends
```

---

### Exercise 5: Distributed Tracing Across Services

```python
# service_a.py (API Gateway)
from opentelemetry import trace
from opentelemetry.propagate import inject
import httpx

tracer = trace.get_tracer("api-gateway")

async def handle_request(prompt: str):
    with tracer.start_as_current_span("api.handle_request") as span:
        span.set_attribute("prompt", prompt[:100])

        # Propagate context to downstream service
        headers = {}
        inject(headers)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://agent-service:8001/process",
                json={"prompt": prompt},
                headers=headers,  # Trace context in headers!
            )
        return response.json()

# service_b.py (Agent Service)
from opentelemetry import trace
from opentelemetry.propagate import extract
from fastapi import FastAPI, Request

tracer = trace.get_tracer("agent-service")
app = FastAPI()

@app.post("/process")
async def process(request: Request):
    # Extract trace context from incoming headers
    context = extract(dict(request.headers))

    with tracer.start_as_current_span("agent.process", context=context) as span:
        span.set_attribute("service", "agent-engine")
        # This span is a child of the API gateway span!
        result = await run_agent(request)
        return result
```

---

### Exercise 6: Grafana Dashboard

```json
{
  "dashboard": {
    "title": "AI Platform Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(ai_requests_total[5m])",
          "legendFormat": "{{model}}"
        }]
      },
      {
        "title": "P99 Latency",
        "type": "timeseries",
        "targets": [{
          "expr": "histogram_quantile(0.99, rate(ai_inference_latency_bucket[5m]))",
          "legendFormat": "{{model}}"
        }]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [{
          "expr": "rate(ai_requests_total{status='error'}[5m]) / rate(ai_requests_total[5m]) * 100"
        }]
      },
      {
        "title": "Active Requests",
        "type": "gauge",
        "targets": [{
          "expr": "ai_requests_active"
        }]
      }
    ]
  }
}
```

PromQL queries for the dashboard:

```promql
# Request throughput per model
rate(ai_requests_total[5m])

# P50/P99 latency
histogram_quantile(0.50, rate(ai_inference_latency_bucket[5m]))
histogram_quantile(0.99, rate(ai_inference_latency_bucket[5m]))

# Error rate percentage
rate(ai_requests_total{status="error"}[5m]) / rate(ai_requests_total[5m]) * 100

# Cache hit rate
rate(ai_cache_hits_total[5m]) / rate(ai_requests_total[5m]) * 100

# Cost per hour
sum(rate(ai_inference_cost_total[1h]))
```

---

### Exercise 7: Alerts

```yaml
# alert-rules.yaml (Prometheus/Mimir alerting rules)
groups:
  - name: ai-platform-alerts
    rules:
      - alert: HighLatency
        expr: histogram_quantile(0.99, rate(ai_inference_latency_bucket[5m])) > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency above 5s for {{ $labels.model }}"

      - alert: HighErrorRate
        expr: rate(ai_requests_total{status="error"}[5m]) / rate(ai_requests_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5% for {{ $labels.model }}"

      - alert: GPUMemoryHigh
        expr: vllm_gpu_cache_usage_perc > 0.95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU cache utilization above 95%"

      - alert: CostSpike
        expr: sum(rate(ai_inference_cost_total[1h])) > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Inference cost exceeding $100/hour"
```

---

### Exercise 8: Trace LLM Pipeline End-to-End

```python
# e2e_trace.py
from opentelemetry import trace

tracer = trace.get_tracer("ai-platform")

async def traced_inference_pipeline(prompt: str):
    with tracer.start_as_current_span("inference_pipeline") as root:
        root.set_attribute("prompt.length", len(prompt))

        # Step 1: Embed query
        with tracer.start_as_current_span("embed_query"):
            embedding = await get_embedding(prompt)

        # Step 2: Check semantic cache
        with tracer.start_as_current_span("semantic_cache_lookup") as cache_span:
            cached = await redis_cache.get(embedding)
            cache_span.set_attribute("cache.hit", cached is not None)
            if cached:
                root.set_attribute("cache.hit", True)
                return cached

        # Step 3: Retrieve context (RAG)
        with tracer.start_as_current_span("rag_retrieval") as rag_span:
            docs = await pgvector_search(embedding, top_k=5)
            rag_span.set_attribute("docs.count", len(docs))

        # Step 4: LLM inference
        with tracer.start_as_current_span("llm_inference") as llm_span:
            llm_span.set_attribute("model", "llama-3-70b")
            result = await vllm_generate(prompt, context=docs)
            llm_span.set_attribute("tokens.prompt", result.prompt_tokens)
            llm_span.set_attribute("tokens.completion", result.completion_tokens)
            llm_span.set_attribute("latency_ms", result.latency_ms)

        # Step 5: Cache result
        with tracer.start_as_current_span("cache_store"):
            await redis_cache.set(embedding, result.text)

        root.set_attribute("total_tokens", result.prompt_tokens + result.completion_tokens)
        return result.text
```

---

## 6. How It's Used in Our Project

- **Traces** — Every request traced from Next.js → Envoy → FastAPI → Agent → vLLM
- **Logs** — Structured JSON logs collected by Loki, correlated with trace IDs
- **Metrics** — Request rates, latency histograms, GPU utilization, cache hit rates
- **Dashboards** — Grafana dashboards for real-time monitoring
- **Alerts** — High latency, error rate spikes, GPU memory pressure, cost anomalies

---

## 7. Further Reading

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Tempo Documentation](https://grafana.com/docs/tempo/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [PromQL Cheat Sheet](https://promlabs.com/promql-cheat-sheet/)

# C4 Level 2: Container Diagram

## Overview

All containers (services and infrastructure) within the AI Agent Platform and their relationships.

```
 +----------------------------------------------------------------------------------+
 |                            AI Agent Platform                                      |
 |                                                                                   |
 |  +-----------+     +----------------+     +------------------+                    |
 |  |  Next.js  |     |  Contour /     |     |   FastAPI +      |                    |
 |  |  Frontend +---->+  Envoy Ingress +---->+   Strawberry GQL |                    |
 |  |  (3000)   |     |  (80/443)      |     |   (8000)         |                    |
 |  +-----------+     +----------------+     +--------+---------+                    |
 |                                                    |                              |
 |                                                    v                              |
 |                    +----------------+     +------------------+                    |
 |                    |  Redis VSS     |<----+  Cache Service   |                    |
 |                    |  (6379)        |     |                  |                    |
 |                    +----------------+     +--------+---------+                    |
 |                                                    |                              |
 |                                                    v                              |
 |  +-----------+     +----------------+     +------------------+                    |
 |  |  Prefect  |<----+  Agent Engine  +---->+  LLM Runtime     |                    |
 |  |  Server   |     |  (LangGraph)   |     |  (vLLM / llama)  |                    |
 |  |  (4200)   |     +--------+-------+     |  (8080/8081)     |                    |
 |  +-----------+              |             +------------------+                    |
 |                             v                                                     |
 |                    +----------------+     +------------------+                    |
 |                    |  PostgreSQL +  |     |  MinIO           |                    |
 |                    |  pgvector     |     |  (S3-compatible)  |                    |
 |                    |  (5432)       |     |  (9000)           |                    |
 |                    +----------------+     +------------------+                    |
 |                                                                                   |
 |  --- Observability ---    --- Mesh ---         --- GitOps ---                     |
 |  +-----------+            +-----------+        +-------------+                    |
 |  | Grafana   |            | Istio     |        | Argo CD     |                    |
 |  | Prometheus|            | ztunnel   |        | Tekton      |                    |
 |  | Loki      |            | (ambient) |        |             |                    |
 |  | Tempo     |            +-----------+        +-------------+                    |
 |  | OTEL      |                                                                    |
 |  | Collector |            --- Policy ---                                          |
 |  +-----------+            +-----------+                                           |
 |                           | OPA       |                                           |
 |                           | Gatekeeper|                                           |
 |                           | OpenCost  |                                           |
 |                           +-----------+                                           |
 +----------------------------------------------------------------------------------+
```

## Container Descriptions

| Container | Technology | Purpose |
|---|---|---|
| Frontend | Next.js, Tailwind, Shadcn/ui | Chat UI, document upload, bot selector |
| Ingress | Contour / Envoy | TLS termination, path-based routing |
| API Gateway | FastAPI + Strawberry | GraphQL API, WebSocket subscriptions |
| Cache Service | Application layer | Semantic cache lookup via Redis VSS |
| Redis VSS | Redis + RediSearch | Vector similarity cache, session store |
| Agent Engine | LangGraph + Prefect | Orchestrates multi-step agent workflows |
| Prefect Server | Prefect | Flow scheduling, retries, run history |
| LLM Runtime | vLLM / llama.cpp | Local model inference, OpenAI-compat API |
| PostgreSQL + pgvector | PostgreSQL 16 | Relational data + vector embeddings |
| MinIO | MinIO | S3-compatible object storage for documents |
| Observability Stack | Grafana, Prometheus, Loki, Tempo, OTEL | Metrics, logs, traces, dashboards |
| Service Mesh | Istio ambient (ztunnel) | mTLS, traffic management, authz |
| GitOps / CI/CD | Argo CD, Tekton | Declarative deploys, build pipelines |
| Policy / Governance | OPA Gatekeeper, OpenCost | Admission control, cost monitoring |

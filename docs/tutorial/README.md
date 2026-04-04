# AI Agent Platform: Building Production AI Applications with Claude Code

## What You'll Build

A full-stack **AI Agent Platform** featuring three production-ready bots:

- **Weather Bot** -- real-time weather queries via external APIs
- **Quiz Bot** -- interactive quiz generation powered by LLMs
- **RAG Assistant** -- retrieval-augmented generation over your own documents

The platform includes a Next.js frontend, FastAPI/GraphQL backend, GPU-accelerated LLM inference, vector search, observability, GitOps, and a service mesh -- all running in containers.

## Prerequisites

| Requirement | Minimum Version |
|---|---|
| Docker (with Compose) | 24.x |
| Git | 2.40+ |
| Python knowledge | Basic (functions, async) |
| TypeScript knowledge | Basic (React components) |

## Tutorial Phases

Open Claude Code in the project directory and run the corresponding slash command to begin each phase.

| Phase | Title | Slash Command | Estimated Time |
|---|---|---|---|
| 0 | Environment Setup | `/00-setup-env` | 20 min |
| 1 | API Layer | `/01-api-layer` | 45 min |
| 2 | Frontend | `/02-frontend` | 45 min |
| 3 | Data Layer | `/03-data-layer` | 40 min |
| 4 | Agent Orchestration | `/04-agent-orchestration` | 50 min |
| 5 | LLM Runtime | `/05-llm-runtime` | 40 min |
| 6 | Observability | `/06-observability` | 45 min |
| 7 | Service Mesh | `/07-service-mesh` | 40 min |
| 8 | GitOps & CI/CD | `/08-gitops-cicd` | 45 min |
| 9 | Policy & Governance | `/09-policy-governance` | 35 min |
| 10 | Production Hardening | `/10-production-hardening` | 50 min |

**Total estimated time: ~7.5 hours**

## Tech Stack

| # | Component | Role |
|---|---|---|
| 1 | FastAPI | Python async API server |
| 2 | Strawberry GraphQL | GraphQL layer over FastAPI |
| 3 | Next.js | React frontend framework |
| 4 | Tailwind CSS | Utility-first CSS |
| 5 | Shadcn/ui | Accessible UI component library |
| 6 | pgvector | Vector similarity search in Postgres |
| 7 | Redis VSS | In-memory vector and cache layer |
| 8 | MinIO | S3-compatible object storage |
| 9 | Prefect | Workflow orchestration |
| 10 | LangGraph | Stateful agent graphs |
| 11 | vLLM | High-throughput LLM serving |
| 12 | llama.cpp | CPU/GPU LLM inference engine |
| 13 | OpenTelemetry (OTEL) | Distributed tracing and metrics |
| 14 | Grafana Stack | Dashboards, logs, and alerting |
| 15 | Istio Ambient | Service mesh (ztunnel, no sidecars) |
| 16 | Contour | Kubernetes ingress via Envoy |

## How to Use

```
Open Claude Code in the project directory and run /00-setup-env to begin.
```

Each phase builds on the previous one. Follow them in order for the best experience. The slash commands scaffold code, explain concepts, and validate your progress automatically.

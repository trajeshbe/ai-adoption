# Agent Platform -- AI Adoption Tutorial

## Project Overview
FAANG-grade AI Agent Platform built as a step-by-step tutorial teaching engineers
how to build production AI applications using Claude Code. Monorepo with 5 Python
microservices, 1 Next.js frontend, shared libraries, and full Infrastructure as Code.

Built entirely with Claude Code (Anthropic's AI-assisted CLI). Every service, component,
K8s manifest, and test was generated through natural language prompts, demonstrating
how AI pair programming accelerates enterprise software development.

Reference: github.com/TechNTomorrow/agent-end-to-end (simple demo we're rebuilding)
Source images: github.com/trajeshbe/merit-aiml (kiaa-gpu branch)

## Tech Stack (16 Components)
```
1.  Frontend       → Next.js 14 + Tailwind CSS + Shadcn/ui
2.  Ingress        → Envoy (via Contour HTTPProxy CRDs)
3.  Service Mesh   → Istio ambient mode (ztunnel, no sidecars)
4.  API Gateway    → FastAPI + Strawberry GraphQL (schema-first)
5.  LLM Runtime    → vLLM on KubeRay (GPU, continuous batching)
6.  CPU Fallback   → llama.cpp server (circuit breaker failover)
7.  Vector DB      → PostgreSQL + pgvector (cosine similarity)
8.  Object Store   → MinIO (S3-compatible, Ozone-ready)
9.  Cache          → Redis 7.2 + VSS semantic cache (RediSearch)
10. Agent DAG      → Prefect 3 + LangGraph state machines
11. Feature Store  → Feast on Flink (deferred to post-Phase 10)
12. Observability  → OpenTelemetry → Grafana Tempo/Loki/Mimir
13. Cost Tracking  → OpenCost (real-time $/inference)
14. GitOps         → Argo CD + Tekton pipelines
15. Policy         → OPA Gatekeeper (constraint templates)
16. Dev Loop       → DevContainer + Skaffold + mirrord
```

## Architecture
```
Contour/Envoy (Ingress) -> Gateway (FastAPI+Strawberry GraphQL :8050)
                        -> Frontend (Next.js+Tailwind :8055)
Gateway -> Agent Engine (Prefect+LangGraph :8053) -> LLM (Ollama/vLLM :20434)
        -> Document Service (MinIO+pgvector :8051) -> Postgres
        -> Cache Service (Redis 7.2 VSS :8052)
        -> Cost Tracker (OpenCost :8054)
Cross-cutting: Istio ambient mesh, OTEL->Grafana, Argo CD+Tekton, OPA Gatekeeper

K8s Cluster (minikube profile: aiadopt):
  Namespace: agent-platform
  Deployments: gateway, agent-engine, frontend (proxy pods -> host services)
  HPA: gateway (1-5 replicas), agent-engine (1-5 replicas) @ 50% CPU
  Scaling Dashboard: /scaling (live K8s data via kubectl)
```

## Monorepo Layout
```
services/     Python microservices (gateway, agent-engine, document-service, cache-service, cost-tracker)
frontend/     Next.js 14 App Router + Tailwind + Shadcn/ui
libs/         Shared Python (py-common) and TypeScript (ts-common)
infra/        k8s/ (Kustomize + demo/), helm/, argocd/, tekton/, policy/, terraform/
tests/        Cross-service: e2e, integration, load (Locust+k6), chaos (Litmus), security
docs/         ADRs, C4 architecture, tutorial phases 0-10, runbooks, tech stack guide
scripts/      bootstrap.sh, seed-data.sh, port-forward.sh, load-test.sh
```

## Conventions
- **Python**: 3.11+, uv for deps, ruff lint+format, mypy strict, pytest
- **TypeScript**: strict mode, ESLint+Prettier, Vitest+Playwright
- **Services**: /healthz and /readyz endpoints, OTEL traces via libs/py-common/telemetry.py
- **Config**: Environment variables via Pydantic Settings (12-factor)
- **API**: GraphQL schema-first -- edit services/gateway/src/gateway/schema.py first
- **K8s**: Kustomize base/overlays. Never raw `kubectl apply`. Helm for third-party only.
- **GitOps**: All changes via Argo CD sync. Git is the single source of truth.
- **LLM**: Circuit breaker pattern -- vLLM (GPU) primary, Ollama/llama.cpp fallback
- **Metrics**: In-memory MetricsCollector + /metrics endpoint for live traffic stats
- **Scaling**: HPA auto-scaling with /k8s endpoint for live cluster state

## Build & Run
```bash
make dev              # Start DevContainer + local infra (PG, Redis, MinIO)
make test             # Run all unit tests (pytest + vitest)
make lint             # Ruff + mypy + eslint
make build            # Build all container images
make test-integration # Integration tests (requires local infra)
make test-e2e         # End-to-end tests (Playwright + pytest)
make test-load        # Load tests (Locust)
skaffold dev          # Full local K8s dev loop with hot reload
```

### Quick Start (Local Development)
```bash
# Start services individually:
cd services/gateway && AGENT_ENGINE_URL=http://localhost:8053 \
  uv run uvicorn gateway.main:create_app --factory --host 0.0.0.0 --port 8050
cd services/agent-engine && PREFECT_API_URL='' LLM_PRIMARY_URL=http://localhost:20434/v1 \
  uv run uvicorn agent_engine.main:create_app --factory --host 0.0.0.0 --port 8053
cd frontend && NEXT_PUBLIC_GRAPHQL_URL=http://<host-ip>:8050/graphql \
  npx next build && npx next start -p 8055 -H 0.0.0.0

# K8s scaling demo:
minikube start --cpus=4 --memory=8192 --driver=docker --profile=aiadopt
kubectl apply -f infra/k8s/demo/
bash scripts/load-test.sh  # 10 concurrent users, 60s
```

## Testing Strategy
| Layer       | Tool              | Scope                    | Runs in   |
|-------------|-------------------|--------------------------|-----------|
| Unit        | pytest / Vitest   | Single function/component| CI always |
| Integration | pytest+testcontainers | Service contracts    | CI always |
| E2E         | Playwright+pytest | Full user workflows      | CI on PR  |
| Load        | scripts/load-test.sh | 10 concurrent users   | Manual    |
| Chaos       | LitmusChaos       | Pod kill, network delay  | Manual    |
| Security    | Trivy + OWASP ZAP | Container + DAST scan    | CI always |
| Scaling     | HPA + load-test.sh | K8s auto-scaling demo   | Manual    |

## Tutorial Phases (Claude Code slash commands)
```
/00-setup-env          Phase 0: DevContainer + toolchain bootstrap
/01-scaffold-api       Phase 1: FastAPI + Strawberry GraphQL gateway
/02-scaffold-frontend  Phase 2: Next.js + Tailwind frontend
/03-setup-data-layer   Phase 3: Postgres/pgvector, Redis VSS, MinIO
/04-build-agent-dag    Phase 4: Prefect + LangGraph agent orchestration
/05-setup-llm-runtime  Phase 5: vLLM on KubeRay + llama.cpp fallback
/06-add-observability  Phase 6: OTEL -> Grafana Tempo/Loki/Mimir
/07-setup-mesh         Phase 7: Istio ambient + Contour/Envoy ingress
/08-setup-gitops       Phase 8: Argo CD + Tekton CI/CD
/09-add-policy         Phase 9: OPA Gatekeeper + OpenCost
/10-harden             Phase 10: Load, chaos, security, runbooks, SLOs
```

## Documentation
```
docs/tutorial/tech-stack-complete-guide.md   -- All 16 components explained for fresh graduates
docs/tutorial/kubernetes-scaling-guide.md    -- K8s concepts, HPA, minikube, scaling demo
docs/tutorial/claude-code-guide.md           -- How Claude Code built this entire app
docs/architecture/                           -- C4 diagrams, ADRs, data flow, network topology
docs/runbooks/                               -- Incident response, scaling, cost mitigation
```

## Key Dependencies
FastAPI 0.115+, Strawberry 0.230+, Prefect 3.x, LangGraph 0.2+,
Next.js 14+, Tailwind 3.4+, Redis 7.2 (RediSearch), pgvector 0.7+,
vLLM 0.6+, Ollama 0.11+ (qwen2.5:1.5b), OpenTelemetry 1.25+,
minikube 1.38+, kubectl 1.35+

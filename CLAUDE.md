# Agent Platform -- AI Adoption Tutorial

## Project Overview
FAANG-grade AI Agent Platform built as a step-by-step tutorial teaching engineers
how to build production AI applications using Claude Code. Monorepo with 5 Python
microservices, 1 Next.js frontend, shared libraries, and full Infrastructure as Code.

Reference: github.com/TechNTomorrow/agent-end-to-end (simple demo we're rebuilding)
Source images: github.com/trajeshbe/merit-aiml (kiaa-gpu branch)

## Architecture
```
Contour/Envoy (Ingress) -> Gateway (FastAPI+Strawberry GraphQL)
                        -> Frontend (Next.js+Tailwind)
Gateway -> Agent Engine (Prefect+LangGraph) -> LLM Runtime (vLLM GPU / llama.cpp CPU)
        -> Document Service (MinIO+pgvector) -> Postgres
        -> Cache Service (Redis 7.2 VSS)
        -> Cost Tracker (OpenCost)
Cross-cutting: Istio ambient mesh, OTEL->Grafana, Argo CD+Tekton, OPA Gatekeeper
```

## Monorepo Layout
```
services/     Python microservices (gateway, agent-engine, document-service, cache-service, cost-tracker)
frontend/     Next.js 14 App Router + Tailwind + Shadcn/ui
libs/         Shared Python (py-common) and TypeScript (ts-common)
infra/        k8s/ (Kustomize), helm/, argocd/, tekton/, policy/, terraform/
tests/        Cross-service: e2e, integration, load (Locust+k6), chaos (Litmus), security
docs/         ADRs, C4 architecture, tutorial phases 0-10, runbooks
scripts/      bootstrap.sh, seed-data.sh, port-forward.sh, generate-graphql.sh
```

## Conventions
- **Python**: 3.11+, uv for deps, ruff lint+format, mypy strict, pytest
- **TypeScript**: strict mode, ESLint+Prettier, Vitest+Playwright
- **Services**: /healthz and /readyz endpoints, OTEL traces via libs/py-common/telemetry.py
- **Config**: Environment variables via Pydantic Settings (12-factor)
- **API**: GraphQL schema-first -- edit services/gateway/src/gateway/schema.py first
- **K8s**: Kustomize base/overlays. Never raw `kubectl apply`. Helm for third-party only.
- **GitOps**: All changes via Argo CD sync. Git is the single source of truth.

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

## Testing Strategy
| Layer       | Tool              | Scope                    | Runs in   |
|-------------|-------------------|--------------------------|-----------|
| Unit        | pytest / Vitest   | Single function/component| CI always |
| Integration | pytest+testcontainers | Service contracts    | CI always |
| E2E         | Playwright+pytest | Full user workflows      | CI on PR  |
| Load        | Locust + k6       | Gateway GraphQL endpoint | Manual    |
| Chaos       | LitmusChaos       | Pod kill, network delay  | Manual    |
| Security    | Trivy + OWASP ZAP | Container + DAST scan    | CI always |

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

## Key Dependencies
FastAPI 0.115+, Strawberry 0.230+, Prefect 3.x, LangGraph 0.2+,
Next.js 14+, Tailwind 3.4+, Redis 7.2 (RediSearch), pgvector 0.7+,
vLLM 0.6+, Ollama 0.11+, OpenTelemetry 1.25+

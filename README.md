# AI Agent Platform

A production-grade AI Agent Platform built as a step-by-step tutorial, demonstrating
how Claude Code accelerates enterprise software development. Every service, component,
Kubernetes manifest, and test was generated through natural language prompts.

**Live Demo:** [https://ai-adoption.uk](https://ai-adoption.uk)

---

## Architecture

```
Contour/Envoy (Ingress)
    ├── Frontend (Next.js + Tailwind :3000)
    └── Gateway (FastAPI + Strawberry GraphQL :8000)
            ├── Agent Engine (Prefect + LangGraph :8003) → Ollama/vLLM
            ├── Document Service (MinIO + pgvector :8001) → PostgreSQL
            ├── Cache Service (Redis 7.2 VSS :8002)
            └── Cost Tracker (OpenCost :8004) → PostgreSQL
```

**16 components:** Next.js, Envoy, Istio, FastAPI/GraphQL, vLLM, llama.cpp,
PostgreSQL/pgvector, MinIO, Redis Stack, Prefect/LangGraph, OpenTelemetry,
Grafana, OpenCost, Argo CD/Tekton, OPA Gatekeeper, DevContainer/Skaffold.

---

## Quick Start

### Local Development (Docker Compose)

```bash
# Clone the repository
git clone https://github.com/merit-data-tech/ai-adoption.git
cd ai-adoption

# Start all services
docker compose up -d

# Access the platform
open http://localhost:8055          # Frontend
open http://localhost:8050/graphql  # GraphQL Playground
```

### Cloud Deployment (GCP VM + HTTPS)

```bash
# Start the GCP VM
bash scripts/gcp-vm-start.sh cpu

# SSH in and deploy
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption
docker compose --profile web up -d --build

# Access via domain (after Cloudflare DNS update)
open https://ai-adoption.uk
```

See [docs/runbooks/deploy-gcp-full-guide.md](docs/runbooks/deploy-gcp-full-guide.md)
for the complete deployment guide.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 + Tailwind + Shadcn/ui | Web UI (chat, agents, dashboard) |
| API Gateway | FastAPI + Strawberry GraphQL | Schema-first API |
| Agent Engine | Prefect 3 + LangGraph | Agent orchestration (weather, quiz, RAG) |
| LLM Runtime | Ollama (CPU) / vLLM (GPU) | Inference with circuit breaker failover |
| Vector DB | PostgreSQL + pgvector | Document embeddings + cosine similarity |
| Cache | Redis Stack 7.2 (RediSearch) | Semantic cache for LLM responses |
| Object Store | MinIO (S3-compatible) | Document storage |
| Observability | OpenTelemetry + Grafana | Traces, logs, metrics |
| Service Mesh | Istio Ambient Mode | Zero-trust networking (no sidecars) |
| Ingress | Contour + Envoy | HTTP/2 ingress with HTTPProxy CRDs |
| GitOps | Argo CD + Tekton | Declarative deployment + CI/CD pipelines |
| Policy | OPA Gatekeeper | Admission control (resource limits, probes) |
| Cost Tracking | OpenCost | Real-time $/inference monitoring |

---

## CI/CD Pipeline

Every code change follows this automated pipeline:

```
Feature Branch → Pull Request → CI (lint, test, scan) → Code Review
    → Merge to master → UAT Approval → Deploy to GCP VM → Smoke Test
```

| Stage | Tool | Automated? |
|-------|------|------------|
| Lint | ruff + eslint + mypy | Yes (on PR) |
| Unit Tests | pytest + vitest | Yes (on PR) |
| Integration Tests | pytest + Postgres + Redis | Yes (on PR) |
| Security Scan | Trivy (HIGH/CRITICAL) | Yes (on PR) |
| Code Review | CODEOWNERS-based | Manual |
| UAT Approval | GitHub Environments | Manual |
| Deploy | SSH + Docker Compose | Yes (on merge) |
| Smoke Test | curl public endpoints | Yes (post-deploy) |

See [docs/runbooks/cicd-pipeline.md](docs/runbooks/cicd-pipeline.md) for the
complete pipeline documentation.

---

## Project Structure

```
ai-adoption/
├── services/                 # Python microservices
│   ├── gateway/              #   FastAPI + GraphQL API
│   ├── agent-engine/         #   Prefect + LangGraph agents
│   ├── document-service/     #   RAG pipeline (MinIO + pgvector)
│   ├── cache-service/        #   Redis semantic cache
│   └── cost-tracker/         #   Inference cost tracking
├── frontend/                 # Next.js 14 + Tailwind
├── libs/                     # Shared libraries (py-common, ts-common)
├── infra/                    # Infrastructure as Code
│   ├── k8s/                  #   Kustomize (base + overlays)
│   ├── argocd/               #   GitOps (app-of-apps)
│   ├── tekton/               #   CI/CD pipelines
│   ├── policy/               #   OPA Gatekeeper
│   ├── terraform/            #   Cloud provisioning (GCP/AWS/Azure)
│   └── helm/                 #   Third-party chart values
├── tests/                    # Cross-service tests (e2e, load, chaos)
├── docs/                     # Architecture, tutorials, runbooks
├── scripts/                  # Operations scripts
├── .github/workflows/        # GitHub Actions (CI, deploy, release)
└── docker-compose.yml        # Full standalone deployment
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started: Enterprise AI Adoption](docs/getting-started-enterprise-ai-adoption.md) | Complete onboarding guide with learning paths, enterprise roadmap, and all doc references |
| [Claude Code Guide](docs/tutorial/claude-code-guide.md) | Developer roadmap: install → configure → develop → test → deploy |
| [Claude Code Tips](docs/tutorial/claude-code-tips.md) | 45 practical tips from basics to advanced (context, Git, testing, research) |
| [CI/CD Pipeline](docs/runbooks/cicd-pipeline.md) | Pipeline overview, branch strategy, deployment paths |
| [GCP Deployment](docs/runbooks/deploy-gcp-full-guide.md) | Step-by-step GCP VM deployment |
| [Domain Setup](docs/runbooks/domain-setup.md) | Cloudflare + Caddy HTTPS configuration |
| [VM Operations](docs/runbooks/gcp-vm-operations.md) | Start/stop VMs, service management |
| [Auto-Scaling](docs/architecture/autoscaling-deep-dive.md) | HPA control loop, metrics pipeline |
| [Tech Stack Guide](docs/tutorial/tech-stack-complete-guide.md) | All 16 components explained |
| [K8s Scaling Guide](docs/tutorial/kubernetes-scaling-guide.md) | Kubernetes concepts + HPA demo |

---

## Tutorial Phases

This project is structured as a 10-phase tutorial. Each phase has a Claude Code
slash command that builds the corresponding layer:

| Phase | Command | What It Builds |
|-------|---------|---------------|
| 0 | `/00-setup-env` | DevContainer + toolchain bootstrap |
| 1 | `/01-scaffold-api` | FastAPI + Strawberry GraphQL gateway |
| 2 | `/02-scaffold-frontend` | Next.js + Tailwind + Shadcn/ui |
| 3 | `/03-setup-data-layer` | PostgreSQL/pgvector, Redis, MinIO |
| 4 | `/04-build-agent-dag` | Prefect + LangGraph agent orchestration |
| 5 | `/05-setup-llm-runtime` | vLLM + llama.cpp CPU fallback |
| 6 | `/06-add-observability` | OpenTelemetry + Grafana |
| 7 | `/07-setup-mesh` | Istio ambient + Contour/Envoy ingress |
| 8 | `/08-setup-gitops` | Argo CD + Tekton CI/CD |
| 9 | `/09-add-policy` | OPA Gatekeeper + OpenCost |
| 10 | `/10-harden` | Load tests, chaos tests, security, SLOs |

---

## Contributing

1. **Create a feature branch:** `git checkout -b feature/my-change`
2. **Make your changes** and write tests
3. **Run checks locally:** `make lint && make test`
4. **Push and create a PR:** `git push origin feature/my-change`
5. **Wait for CI** to pass and get a code review
6. **Merge** -- deployment happens automatically

See the [CI/CD Pipeline guide](docs/runbooks/cicd-pipeline.md) for the full workflow.

---

## License

This project is for educational purposes -- demonstrating AI-assisted enterprise
software development with Claude Code.

Built with [Claude Code](https://claude.ai/code) by Anthropic.

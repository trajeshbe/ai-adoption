# Getting Started: Enterprise AI-Powered Development

> **A practical guide for adopting AI-assisted development at enterprise scale,
> using this repository as a reference implementation.**
>
> Informed by Turing's [Scaling AI-Powered Development: An Enterprise Roadmap for Claude Code](https://www.turing.com/resources/scaling-ai-powered-development-an-enterprise-roadmap-for-claude-code)
> and built with real production deployments at [ai-adoption.uk](https://ai-adoption.uk).

---

## Table of Contents

1. [Who This Is For](#1-who-this-is-for)
2. [The Paradigm Shift: From Copilot to Co-Developer](#2-the-paradigm-shift-from-copilot-to-co-developer)
3. [Quick Start: Run the Platform in 5 Minutes](#3-quick-start-run-the-platform-in-5-minutes)
4. [Learning Path: Choose Your Track](#4-learning-path-choose-your-track)
5. [Enterprise Adoption Roadmap](#5-enterprise-adoption-roadmap)
6. [Lane A — Local Exploration (Start Here)](#6-lane-a--local-exploration-start-here)
7. [Lane B — CI-Backed Development](#7-lane-b--ci-backed-development)
8. [Lane C — Production Release & Deployment](#8-lane-c--production-release--deployment)
9. [Governance, Traceability & Accountability](#9-governance-traceability--accountability)
10. [Measuring What Matters](#10-measuring-what-matters)
11. [Repository Documentation Map](#11-repository-documentation-map)
12. [What To Build First](#12-what-to-build-first)
13. [Frequently Asked Questions](#13-frequently-asked-questions)

---

## 1. Who This Is For

| You are... | Start here |
|------------|-----------|
| **Fresh graduate / new to the stack** | [Section 4: Learning Path](#4-learning-path-choose-your-track) → Beginner Track |
| **Developer adopting Claude Code** | [Section 6: Lane A](#6-lane-a--local-exploration-start-here) → hands-on exploration |
| **Tech lead / architect** | [Section 5: Enterprise Roadmap](#5-enterprise-adoption-roadmap) → adoption strategy |
| **DevOps / platform engineer** | [Section 8: Lane C](#8-lane-c--production-release--deployment) → CI/CD + deployment |
| **Engineering manager** | [Section 9: Governance](#9-governance-traceability--accountability) + [Section 10: Metrics](#10-measuring-what-matters) |

---

## 2. The Paradigm Shift: From Copilot to Co-Developer

Traditional AI coding tools (autocomplete, inline suggestions) are **reactive** — they wait
for you to write code, then suggest the next line. Claude Code is fundamentally different.

> *"Developers state the desired final outcome, and Claude Code assumes the task —
> analyzing the codebase, making architectural decisions, and implementing multi-file
> modifications."*
> — [Turing Enterprise Roadmap](https://www.turing.com/resources/scaling-ai-powered-development-an-enterprise-roadmap-for-claude-code)

**What changes for the developer:**

| Before (Copilot) | After (Claude Code) |
|-------------------|---------------------|
| "How do I write this function?" | "Add input validation to all API endpoints following the gateway pattern" |
| Write code line by line | Define success criteria, constraints, edge cases |
| Review syntax | Review architecture and intent |
| Manual file-by-file changes | Multi-file coordinated changes |

**This entire repository was built with Claude Code.** Every service, component, Kubernetes
manifest, test, and document was generated through natural language prompts. The
[Claude Code Guide](docs/tutorial/claude-code-guide.md) walks through exactly how.

### How This Repo Demonstrates It

```
Natural Language Prompt:
  "Build a FastAPI gateway with Strawberry GraphQL, health endpoints,
   rate limiting, and metrics collection"

Claude Code Output:
  ├── services/gateway/src/gateway/main.py        (app factory + routes)
  ├── services/gateway/src/gateway/schema.py       (GraphQL types)
  ├── services/gateway/src/gateway/resolvers/      (domain resolvers)
  ├── services/gateway/src/gateway/middleware/      (auth, rate limit)
  ├── services/gateway/src/gateway/health.py       (healthz, readyz)
  ├── services/gateway/src/gateway/metrics.py      (MetricsCollector)
  ├── services/gateway/Dockerfile                  (multi-stage build)
  ├── services/gateway/pyproject.toml              (dependencies)
  └── services/gateway/tests/                      (unit + integration)
```

---

## 3. Quick Start: Run the Platform in 5 Minutes

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker + Compose | 24.x+ | Container runtime |
| Git | 2.40+ | Version control |
| Claude Code | Latest | AI co-developer ([install guide](docs/tutorial/claude-code-guide.md#2-installation--platforms)) |

### Local (Docker Compose)

```bash
git clone https://github.com/merit-data-tech/ai-adoption.git
cd ai-adoption

# Start all services (CPU mode, no GPU needed)
docker compose up -d

# Verify health
curl http://localhost:8050/healthz   # Gateway
curl http://localhost:8055/          # Frontend

# Open in browser
open http://localhost:8055           # Chat UI
open http://localhost:8050/graphql   # GraphQL Playground
```

### Cloud (GCP VM + HTTPS)

```bash
# Full guide: docs/runbooks/deploy-gcp-full-guide.md
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption
docker compose --profile web up -d --build

# Live at: https://ai-adoption.uk
```

> **Detailed deployment:** [`docs/runbooks/deploy-gcp-full-guide.md`](docs/runbooks/deploy-gcp-full-guide.md)
> **VM operations:** [`docs/runbooks/gcp-vm-operations.md`](docs/runbooks/gcp-vm-operations.md)
> **Domain/HTTPS setup:** [`docs/runbooks/domain-setup.md`](docs/runbooks/domain-setup.md)

---

## 4. Learning Path: Choose Your Track

### Track A: Beginner (Fresh Graduate / New to Stack)

**Goal:** Understand what each component does and why it exists.

| Step | Resource | Time |
|------|----------|------|
| 1 | Read the [Stack Guide for Freshers](docs/stack-guide-for-freshers.md) — explains all 16 components in plain language with examples from this codebase | 2h |
| 2 | Read the [Tech Stack Complete Guide](docs/tutorial/tech-stack-complete-guide.md) — deeper dive into each technology | 3h |
| 3 | Follow tutorials 01-16, each covering one component: | 8h |
| | - [01: Next.js + Tailwind](docs/tutorial/01-nextjs-tailwind/README.md) | |
| | - [04: FastAPI + GraphQL](docs/tutorial/04-fastapi-graphql/README.md) | |
| | - [07: PostgreSQL + pgvector](docs/tutorial/07-postgres-pgvector/README.md) | |
| | - [09: Redis Semantic Cache](docs/tutorial/09-redis-semantic-cache/README.md) | |
| | - [10: Prefect + LangGraph](docs/tutorial/10-prefect-langgraph/README.md) | |
| 4 | Trace a full request through the system: [End-to-End Request Trace](docs/tutorial/00-end-to-end-request-trace/README.md) | 1.5h |
| 5 | Understand the database layer: [Database Guide](docs/tutorial/database-guide.md) | 1h |

### Track B: Developer (Ready to Build with Claude Code)

**Goal:** Set up Claude Code and use it to develop features.

| Step | Resource | Time |
|------|----------|------|
| 1 | Install Claude Code: [Claude Code Guide — Installation](docs/tutorial/claude-code-guide.md#2-installation--platforms) | 15m |
| 2 | Configure for this repo: [Claude Code Guide — Rules & Memory](docs/tutorial/claude-code-guide.md#5-rules-that-shape-behavior) | 15m |
| 3 | Run the 10-phase tutorial using slash commands: [Tutorial Phases](docs/tutorial/README.md) | 7.5h |
| | Phase 0: `/00-setup-env` — Environment setup | |
| | Phase 1: `/01-scaffold-api` — API gateway | |
| | Phase 2: `/02-scaffold-frontend` — Frontend | |
| | Phase 3: `/03-setup-data-layer` — Data layer | |
| | Phase 4: `/04-build-agent-dag` — Agent orchestration | |
| | Phase 5: `/05-setup-llm-runtime` — LLM runtime | |
| | Phase 6-10: Observability, mesh, GitOps, policy, hardening | |
| 4 | Understand the full development lifecycle: [Claude Code Guide — End-to-End Lifecycle](docs/tutorial/claude-code-guide.md#13-end-to-end-lifecycle-walkthrough) | 30m |

### Track C: Architect / DevOps (Production Focus)

**Goal:** Understand the architecture, CI/CD, and deployment patterns.

| Step | Resource | Time |
|------|----------|------|
| 1 | Architecture overview: [C4 Context](docs/architecture/c4-context.md) + [C4 Container](docs/architecture/c4-container.md) | 30m |
| 2 | Data flow: [Data Flow Diagram](docs/architecture/data-flow.md) | 20m |
| 3 | Architecture decisions: read all 7 ADRs in [`docs/architecture/adr/`](docs/architecture/adr/) | 1h |
| 4 | CI/CD pipeline: [Pipeline Runbook](docs/runbooks/cicd-pipeline.md) | 30m |
| 5 | Deployment: [GCP Deploy Guide](docs/runbooks/deploy-gcp-full-guide.md) | 30m |
| 6 | Auto-scaling: [Autoscaling Deep Dive](docs/architecture/autoscaling-deep-dive.md) + [K8s Scaling Guide](docs/tutorial/kubernetes-scaling-guide.md) | 1h |
| 7 | Cloud migration: [Cloud Migration Guide](docs/tutorial/cloud-migration-guide.md) | 1h |
| 8 | Incident response: [Incident Runbook](docs/runbooks/incident-response.md) + [Cost Mitigation](docs/runbooks/cost-runaway-mitigation.md) | 30m |

---

## 5. Enterprise Adoption Roadmap

The Turing Enterprise Roadmap defines three lanes for scaling Claude Code in an
organization. This repository implements all three, and you can trace the exact
implementation for each.

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE ADOPTION LANES                     │
│                                                                  │
│  Lane A: LOCAL EXPLORATION          Minimal friction             │
│  ─────────────────────────          Developer sandbox            │
│  Claude Code CLI + repo             Propose diffs, run tests     │
│  No prod impact                     Learn patterns               │
│                                                                  │
│  Lane B: CI-BACKED CHANGES          Standard operating procedure │
│  ──────────────────────────         PR → CI → Review → Merge     │
│  Feature branches + PRs             Lint, test, scan gates       │
│  Automated quality gates            Auditable artifacts          │
│                                                                  │
│  Lane C: RELEASE & DEPLOYMENT       Maximal assurance            │
│  ─────────────────────────────      Human approval gates         │
│  UAT → Deploy → Smoke test          Rollback capability          │
│  Argo CD GitOps (K8s path)          Production monitoring        │
│                                                                  │
│  ─────────────────────────────────────────────────── Time ──→    │
│  Week 1-2        Week 3-6           Week 7+                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Lane A — Local Exploration (Start Here)

**Goal:** Developers use Claude Code in a sandbox to analyze code, propose changes,
and run tests — with zero production risk.

### 6.1 Install Claude Code

```bash
# npm
npm install -g @anthropic-ai/claude-code

# Or homebrew
brew install claude-code
```

> **Full installation guide** with all platforms (CLI, VS Code, JetBrains, web):
> [`docs/tutorial/claude-code-guide.md` §2](docs/tutorial/claude-code-guide.md#2-installation--platforms)

### 6.2 Explore the Codebase

Open the terminal in the project root and start a conversation:

```bash
cd ai-adoption
claude

# Example prompts to explore:
> "Explain the architecture of the gateway service"
> "How does the circuit breaker work in llm_client.py?"
> "What GraphQL mutations are available?"
> "Trace a chat message from frontend to LLM response"
```

Claude Code reads `CLAUDE.md` files at each level of the repo for context:

| File | Scope | What it provides |
|------|-------|-----------------|
| [`CLAUDE.md`](CLAUDE.md) | Root | Project overview, tech stack, conventions, build commands |
| [`services/CLAUDE.md`](services/CLAUDE.md) | All services | Shared patterns, port map, testing conventions |
| [`services/gateway/CLAUDE.md`](services/gateway/CLAUDE.md) | Gateway | Endpoints, middleware, GraphQL schema |
| [`services/agent-engine/CLAUDE.md`](services/agent-engine/CLAUDE.md) | Agent Engine | LangGraph, Prefect, LLM client, agent registry |
| [`frontend/CLAUDE.md`](frontend/CLAUDE.md) | Frontend | Pages, components, GraphQL client, build-time env vars |
| [`infra/CLAUDE.md`](infra/CLAUDE.md) | Infrastructure | K8s, Helm, Argo CD, Tekton, Terraform structure |
| [`libs/CLAUDE.md`](libs/CLAUDE.md) | Libraries | Shared config, logging, telemetry, auth, middleware |
| [`tests/CLAUDE.md`](tests/CLAUDE.md) | Tests | E2E, load, chaos, security test organization |

### 6.3 Use Slash Commands (Tutorial Mode)

The repo includes 11 Claude Code slash commands that build the platform phase by phase:

```bash
claude
> /00-setup-env          # Bootstrap environment
> /01-scaffold-api       # Build the GraphQL API gateway
> /02-scaffold-frontend  # Build the Next.js frontend
# ... see full list in docs/tutorial/README.md
```

Each command scaffolds code, explains concepts, and validates progress automatically.

> **Tutorial details:** [`docs/tutorial/README.md`](docs/tutorial/README.md)
> **All 16 component tutorials:** [`docs/tutorial/01-nextjs-tailwind/`](docs/tutorial/01-nextjs-tailwind/README.md) through [`docs/tutorial/16-devcontainer-skaffold-mirrord/`](docs/tutorial/16-devcontainer-skaffold-mirrord/README.md)

### 6.4 Run Tests Locally

```bash
# Python unit tests (per-service)
cd services/gateway && uv run pytest tests/unit/ -v

# Frontend tests
cd frontend && pnpm test

# Full lint check
uv run ruff check services/ libs/py-common/
```

### 6.5 Best Practices for Prompt Engineering

The Turing roadmap emphasizes **shared prompt conventions** for team consistency:

```
Good prompts (reusable, specific, constrained):
  "Refactor the weather agent to follow the same error-handling pattern
   as the quiz agent in services/agent-engine/src/agent_engine/agents/quiz.py"

  "Add input validation to the SendMessageInput in schema.py following
   the existing CreateAgentInput pattern"

  "Update all service health endpoints to include version information,
   following the gateway /healthz pattern"

Bad prompts (vague, unconstrained):
  "Make the code better"
  "Add some tests"
  "Fix the bug"
```

> **Prompt patterns and examples:** [`docs/tutorial/claude-code-guide.md` §13](docs/tutorial/claude-code-guide.md#13-end-to-end-lifecycle-walkthrough)

---

## 7. Lane B — CI-Backed Development

**Goal:** All production changes go through the CI/CD pipeline — automated quality gates
with auditable artifacts (PRs, build logs, test results).

### 7.1 Branch Strategy

```
master (protected)
  ├── feature/add-openai-provider    ← New features
  ├── fix/health-check-timeout       ← Bug fixes
  ├── docs/update-readme             ← Documentation
  └── infra/add-gpu-override         ← Infrastructure
```

### 7.2 The CI Pipeline

Every PR triggers 5 parallel CI jobs:

```
Pull Request to master
  ├── Lint          → ruff (Python) + ESLint (TypeScript)
  ├── Type Check    → mypy --strict
  ├── Python Tests  → pytest per-service (unit + integration)
  ├── Frontend Tests → vitest
  └── Security Scan → Trivy (CRITICAL blocks, HIGH advisory)
```

**Implementation:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
**Documentation:** [`docs/runbooks/cicd-pipeline.md`](docs/runbooks/cicd-pipeline.md)

### 7.3 Creating a Change with Claude Code

Here's the actual workflow this repo uses (demonstrated with the OpenAI provider feature):

```bash
# 1. Create feature branch
git checkout -b feature/add-openai-provider

# 2. Open Claude Code and describe the change
claude
> "Add OpenAI as a selectable LLM provider in the chat config panel.
    Users should be able to switch between Ollama and OpenAI, select
    a model, and enter their API key. The config should flow through
    GraphQL → Gateway → Agent Engine."

# 3. Claude Code modifies files across the stack:
#    - frontend/src/app/chat/page.tsx     (UI provider selector)
#    - services/gateway/src/gateway/schema.py     (GraphQL types)
#    - services/gateway/src/gateway/resolvers/chat.py  (pass config)
#    - services/agent-engine/src/agent_engine/main.py  (accept config)
#    - services/agent-engine/src/agent_engine/llm_client.py  (factory)
#    - services/agent-engine/src/agent_engine/flows/agent_flow.py  (wire)
#    - libs/py-common/src/agent_platform_common/config.py  (settings)

# 4. Push and create PR
git push origin feature/add-openai-provider
gh pr create --title "Add OpenAI as selectable LLM provider"

# 5. CI runs automatically → review → merge
# 6. Deploy workflow triggers on merge to master
```

### 7.4 Review Practices for AI-Generated Code

Per the Turing roadmap, AI-generated commits should be:

1. **Clearly tagged** — this repo uses `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` in every commit
2. **Reviewed by domain experts** — engineers who understand both the codebase and how the agent behaves
3. **Subject to automated gates** — lint, type check, tests, and security scans must pass

> *"Accountability for defects in AI-generated code rests with the human, not the AI.
> A developer delegated the task, reviewed the output, and approved the merge."*
> — Turing Enterprise Roadmap

---

## 8. Lane C — Production Release & Deployment

**Goal:** Maximum assurance. Human approval gates, automated deployment with rollback,
production smoke tests.

### 8.1 The Deploy Pipeline

```
Merge to master
  │
  ├── CI Gate (5 jobs must pass)
  │     ├── Lint
  │     ├── Type Check
  │     ├── Python Tests
  │     ├── Frontend Tests
  │     └── Security Scan
  │
  ├── UAT Approval (manual, GitHub Environments)
  │     └── Required reviewer approves in GitHub Actions UI
  │
  ├── Deploy to Production (SSH → GCP VM)
  │     ├── GPU auto-detection (nvidia-smi check)
  │     ├── docker compose --profile web up -d --build
  │     ├── Health checks (gateway, agent-engine, cache, cost-tracker, frontend)
  │     └── Auto-rollback on failure (git reset to previous commit)
  │
  └── Smoke Test (Public URL)
        ├── https://ai-adoption.uk/healthz
        ├── https://ai-adoption.uk/
        └── https://ai-adoption.uk/graphql
```

**Implementation:** [`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)
**Documentation:** [`docs/runbooks/cicd-pipeline.md`](docs/runbooks/cicd-pipeline.md)

### 8.2 Two Deployment Paths

This repo supports two deployment models — use whichever matches your infrastructure:

| | Path 1: VM (Current) | Path 2: K8s/GitOps (Future) |
|---|---|---|
| **Trigger** | Merge to master | Image push to GHCR |
| **Mechanism** | SSH + Docker Compose | Argo CD auto-sync |
| **Rollback** | `git reset --hard` + rebuild | Argo CD rollback / K8s rollout undo |
| **Scaling** | Manual (VM resize) | HPA auto-scaling |
| **Config** | `.env` on VM | ConfigMaps + Secrets |
| **Implementation** | [deploy.yml](.github/workflows/deploy.yml) | [infra/argocd/](infra/argocd/) |
| **Docs** | [deploy-gcp-full-guide.md](docs/runbooks/deploy-gcp-full-guide.md) | [phase-08-gitops.md](docs/tutorial/phase-08-gitops-cicd.md) |

### 8.3 Argo CD GitOps (K8s Path)

When running on Kubernetes, Argo CD provides declarative, Git-based deployments:

```
infra/argocd/
  ├── app-of-apps.yaml              # Root application
  └── apps/
      ├── gateway.yaml              # Per-service Argo CD Application
      ├── agent-engine.yaml
      ├── frontend.yaml
      ├── cache-service.yaml
      ├── cost-tracker.yaml
      ├── document-service.yaml
      ├── redis.yaml
      └── postgres.yaml
```

**How it works:**
1. Developer merges PR → `release.yml` builds Docker images → pushes to GHCR
2. Update image tags in `infra/k8s/overlays/prod/` kustomization
3. Argo CD detects the manifest change in git (auto-sync enabled)
4. Rolling update with health checks via K8s liveness/readiness probes

> **Argo CD + Tekton tutorial:** [`docs/tutorial/14-argocd-tekton/README.md`](docs/tutorial/14-argocd-tekton/README.md)
> **GitOps phase guide:** [`docs/tutorial/phase-08-gitops-cicd.md`](docs/tutorial/phase-08-gitops-cicd.md)

### 8.4 Rollback Procedures

**VM path (automatic):**
```bash
# The deploy.yml script auto-rolls back on health check failure:
# 1. Records PREV_COMMIT before deploy
# 2. If any health check fails → git reset --hard $PREV_COMMIT
# 3. Rebuilds with previous code
```

**Manual rollback:**
```bash
ssh merit@<VM_IP>
cd ~/kiaa/ai-adoption
git log --oneline -5          # Find the commit to roll back to
git reset --hard <commit>
docker compose --profile web up -d --build
```

> **Full rollback procedures:** [`docs/runbooks/cicd-pipeline.md`](docs/runbooks/cicd-pipeline.md)
> **Incident response:** [`docs/runbooks/incident-response.md`](docs/runbooks/incident-response.md)

---

## 9. Governance, Traceability & Accountability

The Turing roadmap emphasizes that **speed without traceability is a liability**. This repo
implements the governance mechanisms they recommend:

### 9.1 Git Attribution

Every AI-generated commit includes co-authorship:

```
commit ba2b70a
Author: Your Name <you@example.com>

    Add OpenAI as selectable LLM provider in chat config panel

    Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

This makes AI contributions visible in `git log` and `git blame`, answering the question:
*"Was this code human-written or AI-generated?"*

### 9.2 Constraint Enforcement via CLAUDE.md

The `CLAUDE.md` files at every level of the repo enforce architectural constraints
directly in the AI's context:

```markdown
# From CLAUDE.md (root):
- API: GraphQL schema-first — edit schema.py BEFORE implementing resolvers
- K8s: Kustomize base/overlays. Never raw kubectl apply.
- GitOps: All changes via Argo CD sync. Git is the single source of truth.
- Services: /healthz and /readyz endpoints required
```

These rules shape Claude Code's output before a human reviewer ever sees it — equivalent
to the Turing roadmap's recommendation to *"inject hard constraints into prompts."*

> **How CLAUDE.md rules work:** [`docs/tutorial/claude-code-guide.md` §5](docs/tutorial/claude-code-guide.md#5-rules-that-shape-behavior)

### 9.3 Automated Quality Gates

| Gate | Tool | Blocks Merge? | Implementation |
|------|------|---------------|----------------|
| Python lint | ruff | Warning | CI: `ruff check --select E,W,F,I` |
| TypeScript lint | ESLint | Yes | CI: `pnpm lint` |
| Type safety | mypy --strict | Warning | CI: `mypy --strict --ignore-missing-imports` |
| Unit tests | pytest + vitest | Yes (on failure) | CI: per-service test execution |
| Integration tests | pytest + Postgres/Redis | Yes (on failure) | CI: service containers |
| Security scan | Trivy | CRITICAL blocks | CI: `severity: CRITICAL, exit-code: 1` |
| Code review | CODEOWNERS | Required (1 approval) | GitHub branch protection |
| UAT approval | GitHub Environments | Required (on deploy) | `production` environment |

### 9.4 Architecture Decision Records

Every significant architectural choice is documented with rationale:

| ADR | Decision | Key rationale |
|-----|----------|---------------|
| [001](docs/architecture/adr/001-monorepo-structure.md) | Monorepo structure | Shared tooling, atomic cross-service changes |
| [002](docs/architecture/adr/002-graphql-over-rest.md) | GraphQL over REST | Type-safe contract, frontend flexibility |
| [003](docs/architecture/adr/003-vllm-with-cpu-fallback.md) | vLLM with CPU fallback | GPU primary + circuit breaker to llama.cpp |
| [004](docs/architecture/adr/004-prefect-over-airflow.md) | Prefect over Airflow | Pythonic API, lightweight, no DAG scheduler |
| [005](docs/architecture/adr/005-istio-ambient-mesh.md) | Istio ambient mesh | Zero-trust without sidecar overhead |
| [006](docs/architecture/adr/006-pgvector-over-dedicated-vectordb.md) | pgvector over Pinecone | Single database, SQL + vector, no extra infra |
| [007](docs/architecture/adr/007-redis-semantic-cache.md) | Redis semantic cache | Sub-ms latency, RediSearch VSS, cache LLM responses |

### 9.5 OPA Gatekeeper Policies

The repo includes admission control policies for Kubernetes deployments:

```
infra/policy/
  ├── constraint-templates/
  │   ├── required-labels.yaml        # Every workload must have team/env labels
  │   ├── resource-limits.yaml        # CPU/memory limits required
  │   └── required-probes.yaml        # liveness/readiness probes required
  └── constraints/
      └── agent-platform-constraints.yaml
```

> **Policy tutorial:** [`docs/tutorial/15-opa-gatekeeper/README.md`](docs/tutorial/15-opa-gatekeeper/README.md)
> **Policy phase guide:** [`docs/tutorial/phase-09-policy-governance.md`](docs/tutorial/phase-09-policy-governance.md)

---

## 10. Measuring What Matters

The Turing roadmap warns against measuring AI tools with traditional metrics
(lines of code, commits per day). Instead, focus on:

### Metrics This Repo Demonstrates

| Metric | How to measure | Where to look |
|--------|---------------|---------------|
| **Feature cycle time** | Time from spec → tested implementation | Git history: the OpenAI provider feature (7 files across 4 layers) was implemented in a single session |
| **Reduction in repetitive work** | Time on boilerplate vs. novel logic | The 10-phase tutorial: each phase generates 500-1500 lines of production code from natural language |
| **Code review efficiency** | Review time per PR | AI-generated code follows consistent patterns (CLAUDE.md rules), making reviews predictable |
| **Test coverage** | Tests generated alongside features | Every service has `tests/unit/` and `tests/integration/` — generated with the feature code |
| **Innovation capacity** | Time freed for architecture and design | Developers focus on *what* to build (schema.py) while Claude Code handles *how* (resolvers, middleware, tests) |

### What This Repo Built with Claude Code

| Metric | Value |
|--------|-------|
| Total services | 5 Python microservices + 1 Next.js frontend |
| Total lines of code | ~15,000+ across services, infra, tests |
| Documentation pages | 55+ (tutorials, architecture, runbooks, guides) |
| K8s manifests | Kustomize base + overlays, 8 Argo CD apps |
| CI/CD pipelines | GitHub Actions (CI + Deploy + Sync) + Tekton |
| Tutorial phases | 11 (0-10), each with Claude Code slash commands |
| Component tutorials | 16 deep-dive technology guides |

---

## 11. Repository Documentation Map

### Getting Started & Overview

| Document | Lines | Description |
|----------|-------|-------------|
| [README.md](README.md) | 193 | Project overview, quick start, architecture |
| [Stack Guide for Freshers](docs/stack-guide-for-freshers.md) | 1,352 | All 16 components explained for new graduates |
| [Tech Stack Complete Guide](docs/tutorial/tech-stack-complete-guide.md) | 3,242 | Deep-dive into every technology |
| [Claude Code Guide](docs/tutorial/claude-code-guide.md) | 1,990 | Install → configure → develop → test → deploy with Claude Code |

### Architecture

| Document | Lines | Description |
|----------|-------|-------------|
| [C4 Context Diagram](docs/architecture/c4-context.md) | 51 | System context view |
| [C4 Container Diagram](docs/architecture/c4-container.md) | 69 | Container-level architecture |
| [Data Flow](docs/architecture/data-flow.md) | 116 | Request flow between services |
| [Network Topology](docs/architecture/network-topology.md) | 151 | Network architecture and service mesh |
| [Autoscaling Deep Dive](docs/architecture/autoscaling-deep-dive.md) | 905 | HPA, metrics pipeline, scaling behavior |
| [Architecture Analysis 2026](docs/tutorial/architecture-analysis-2026.md) | 445 | Current state and evolution |
| [ADRs](docs/architecture/adr/) (7 records) | 480 | All architectural decisions with rationale |

### Tutorials

| Document | Lines | Description |
|----------|-------|-------------|
| [Tutorial Overview](docs/tutorial/README.md) | 69 | Phase map with slash commands |
| [00: End-to-End Request Trace](docs/tutorial/00-end-to-end-request-trace/README.md) | 1,370 | Full request lifecycle walkthrough |
| [01: Next.js + Tailwind](docs/tutorial/01-nextjs-tailwind/README.md) | 1,199 | Frontend framework |
| [02: Envoy + Contour](docs/tutorial/02-envoy-contour/README.md) | 712 | Kubernetes ingress |
| [03: Istio Ambient](docs/tutorial/03-istio-ambient/README.md) | 667 | Service mesh |
| [04: FastAPI + GraphQL](docs/tutorial/04-fastapi-graphql/README.md) | 1,132 | API gateway |
| [05: vLLM + KubeRay](docs/tutorial/05-vllm-kuberay/README.md) | 697 | GPU LLM serving |
| [06: llama.cpp](docs/tutorial/06-llamacpp/README.md) | 635 | CPU LLM fallback |
| [07: PostgreSQL + pgvector](docs/tutorial/07-postgres-pgvector/README.md) | 653 | Vector database |
| [08: MinIO](docs/tutorial/08-minio/README.md) | 577 | Object storage |
| [09: Redis Semantic Cache](docs/tutorial/09-redis-semantic-cache/README.md) | 646 | LLM response caching |
| [10: Prefect + LangGraph](docs/tutorial/10-prefect-langgraph/README.md) | 682 | Agent orchestration |
| [11: Feast + Flink](docs/tutorial/11-feast-flink/README.md) | 573 | Feature store |
| [12: OTEL + Grafana](docs/tutorial/12-otel-grafana/README.md) | 603 | Observability |
| [13: OpenCost](docs/tutorial/13-opencost/README.md) | 463 | Cost tracking |
| [14: Argo CD + Tekton](docs/tutorial/14-argocd-tekton/README.md) | 693 | GitOps & CI/CD |
| [15: OPA Gatekeeper](docs/tutorial/15-opa-gatekeeper/README.md) | 691 | Policy enforcement |
| [16: DevContainer + Skaffold](docs/tutorial/16-devcontainer-skaffold-mirrord/README.md) | 729 | Developer experience |
| [Database Guide](docs/tutorial/database-guide.md) | 709 | PostgreSQL + pgvector patterns |
| [K8s Scaling Guide](docs/tutorial/kubernetes-scaling-guide.md) | 994 | Kubernetes + HPA tutorial |
| [Cloud Migration Guide](docs/tutorial/cloud-migration-guide.md) | 1,999 | Multi-cloud deployment |

### Operations & Runbooks

| Document | Lines | Description |
|----------|-------|-------------|
| [CI/CD Pipeline](docs/runbooks/cicd-pipeline.md) | 491 | Pipeline overview, branch strategy, both deploy paths |
| [GCP Deploy Guide](docs/runbooks/deploy-gcp-full-guide.md) | 481 | Step-by-step VM deployment |
| [Domain Setup](docs/runbooks/domain-setup.md) | 324 | Cloudflare + Caddy HTTPS |
| [GCP VM Operations](docs/runbooks/gcp-vm-operations.md) | 294 | Start/stop VM, service management |
| [Incident Response](docs/runbooks/incident-response.md) | 90 | Incident handling procedures |
| [Cost Mitigation](docs/runbooks/cost-runaway-mitigation.md) | 138 | LLM cost runaway prevention |
| [Scaling vLLM](docs/runbooks/scaling-vllm.md) | 112 | GPU LLM scaling guide |

### Testing

| Document | Lines | Description |
|----------|-------|-------------|
| [GCP GPU Setup & Scaling](docs/testing/gcp-gpu-setup-scaling-testing.md) | 667 | GPU testing procedures |
| [Load Test Results (30 users)](docs/testing/load-test-gcp-gpu-30-users.md) | 408 | Performance benchmarks |

### API

| Document | Lines | Description |
|----------|-------|-------------|
| [GraphQL Schema](docs/api/graphql-schema.md) | 371 | Full API contract documentation |

**Total documentation: ~23,000+ lines across 55+ files.**

---

## 12. What To Build First

Based on the Turing roadmap's guidance on use case selection, here are recommended
starting points ranked by risk and learning value:

### Good First Tasks (Low Risk, High Learning)

| Task | Why it's a good start | Key files |
|------|----------------------|-----------|
| Add a new agent type (e.g., "Code Review Bot") | Follows established pattern in registry | `services/agent-engine/src/agent_engine/agents/`, `registry.py` |
| Add a field to the GraphQL schema | Schema-first workflow, touches 3 layers | `schema.py` → `resolvers/` → `frontend/` |
| Improve a runbook | Low risk, learn the documentation style | `docs/runbooks/` |
| Add a new health check metric | Simple, observable, follows existing pattern | `services/gateway/src/gateway/metrics.py` |

### Medium Tasks (Established Patterns)

| Task | Complexity | Key resources |
|------|-----------|---------------|
| Add a new tool to the weather agent | Agent + tool registration + LLM function calling | [10: Prefect + LangGraph](docs/tutorial/10-prefect-langgraph/README.md) |
| Add caching for LLM responses | Redis VSS semantic cache | [09: Redis Semantic Cache](docs/tutorial/09-redis-semantic-cache/README.md) |
| Add document upload flow | MinIO + pgvector + document-service | [07: pgvector](docs/tutorial/07-postgres-pgvector/README.md), [08: MinIO](docs/tutorial/08-minio/README.md) |

### Tasks to Avoid Initially

Per the Turing roadmap: *"Mission-critical systems with unpredictable state are poor
early candidates."*

- Payment processing or authentication changes
- Core database schema migrations without rollback plans
- Infrastructure changes that affect all services simultaneously

---

## 13. Frequently Asked Questions

### "Do I need a GPU to run this?"

No. The platform runs on CPU with Ollama (qwen2.5:1.5b). GPU mode is optional and
auto-detected by the deploy pipeline. You can also use the OpenAI provider (select it
in the chat config panel) which requires no local GPU at all.

### "How was this entire project built with Claude Code?"

See [`docs/tutorial/claude-code-guide.md`](docs/tutorial/claude-code-guide.md) — it
walks through the complete developer lifecycle from installation to production deployment.
Every service was scaffolded using Claude Code slash commands (phases 0-10).

### "How do I switch between Ollama and OpenAI?"

In the chat UI at [ai-adoption.uk/chat](https://ai-adoption.uk/chat):
1. Click the gear icon (Config)
2. Select "OpenAI" as the provider
3. Choose a model (gpt-4o, gpt-4o-mini, etc.)
4. Enter your OpenAI API key (stored in browser only)

### "Where are the Kubernetes manifests?"

```
infra/k8s/
  ├── base/           # Kustomize base (one dir per service)
  ├── overlays/       # Environment-specific patches (dev, prod)
  └── demo/           # Quick-start demo manifests
```

See [K8s Scaling Guide](docs/tutorial/kubernetes-scaling-guide.md) for setup.

### "How does the CI/CD pipeline work?"

```
PR → CI (lint, test, scan) → Review → Merge → UAT Approval → Deploy → Smoke Test
```

Full details: [`docs/runbooks/cicd-pipeline.md`](docs/runbooks/cicd-pipeline.md)

### "What does the Turing article recommend that this repo implements?"

| Turing Recommendation | This Repo's Implementation |
|----------------------|---------------------------|
| Shared prompt conventions | CLAUDE.md files at every level + slash commands |
| AI commit attribution | `Co-Authored-By: Claude Opus 4.6` in every commit |
| CI/CD quality gates | 5-job CI pipeline (lint, type check, test, security) |
| Human approval points | UAT approval via GitHub Environments |
| Constraint enforcement | CLAUDE.md rules + OPA Gatekeeper policies |
| Risk scoring by scope | Trivy: CRITICAL blocks, HIGH advisory |
| Three adoption lanes | Local dev → CI-backed PRs → Production deploy |
| Rollback procedures | Auto-rollback on health check failure |
| Architecture decisions | 7 ADRs documenting every major choice |
| Traceability | Git attribution + structured logging + OTEL |

---

## Further Reading

- **Turing Enterprise Roadmap:** [Scaling AI-Powered Development: An Enterprise Roadmap for Claude Code](https://www.turing.com/resources/scaling-ai-powered-development-an-enterprise-roadmap-for-claude-code)
- **Claude Code Documentation:** [docs.anthropic.com/claude-code](https://docs.anthropic.com/en/docs/claude-code)
- **This Repository:** [github.com/merit-data-tech/ai-adoption](https://github.com/merit-data-tech/ai-adoption)
- **Live Demo:** [ai-adoption.uk](https://ai-adoption.uk)

---

*This document was generated with [Claude Code](https://claude.ai/code) — the same tool
used to build the entire platform it describes.*

# Phase 0: Environment Setup -- Build a Reproducible Dev Environment from Scratch

## What You Will Learn
- Why reproducible environments matter (DevContainers eliminate "works on my machine")
- How to set up a monorepo with Python + Node.js workspaces
- Docker Compose for local infrastructure (Postgres, Redis, MinIO)
- Pre-commit hooks for code quality gates
- The 12-factor app methodology for configuration

## Prerequisites
- Docker Desktop installed and running
- VS Code or Claude Code CLI
- Git installed
- No prior project files needed -- this is step zero

## Background: Why This Architecture?
We are building an AI Agent Platform -- a system where users can create, manage, and
interact with AI agents (weather bots, quiz bots, RAG-powered assistants). Instead of
a monolith, we use microservices because each concern (API gateway, agent execution,
document processing, caching, cost tracking) has different scaling requirements. An
LLM inference service needs GPUs; a cache service needs memory; a document processor
needs CPU. Separating them lets us scale independently.

The monorepo pattern (all services in one git repo) gives us atomic cross-service
changes, shared libraries, and a single CI/CD pipeline. Google, Meta, and Netflix
all use monorepos at scale.

## Step-by-Step Instructions

### Step 1: Initialize the Git Repository
```bash
cd /home/merit/kiaa/ai_adoption
git init
```
**Why:** Everything in this project is version-controlled. GitOps (Phase 8) requires
git as the single source of truth for all infrastructure and application code.

### Step 2: Verify the Directory Structure
The monorepo skeleton should already exist with these top-level directories:
- `.claude/commands/` -- Tutorial slash commands (you're reading one now)
- `.devcontainer/` -- Reproducible development environment
- `services/` -- 5 Python microservices
- `frontend/` -- Next.js application
- `libs/` -- Shared Python and TypeScript libraries
- `infra/` -- Kubernetes manifests, Helm values, Argo CD, Tekton, OPA
- `tests/` -- Cross-service e2e, integration, load, chaos, security tests
- `docs/` -- Architecture Decision Records, tutorial, runbooks
- `scripts/` -- Bootstrap and utility scripts

### Step 3: Understand the DevContainer Configuration
Read these files to understand the dev environment:
- `.devcontainer/Dockerfile` -- Base image with all CLI tools
- `.devcontainer/devcontainer.json` -- VS Code settings, port forwards, env vars
- `.devcontainer/docker-compose.yml` -- DevContainer + Postgres, Redis, MinIO
- `.devcontainer/post-create.sh` -- One-time setup after container creation

**Key Docker images used (from merit-aiml kiaa-gpu branch):**
- `pgvector/pgvector:pg16` -- Postgres with vector similarity search
- `redis/redis-stack:7.2.0-v10` -- Redis with RediSearch module for VSS
- `minio/minio:latest` -- S3-compatible object storage
- `ollama/ollama:0.11.0` -- Local LLM inference

### Step 4: Understand the Root Configuration Files
- `Makefile` -- Top-level commands (make dev, make test, make build)
- `pyproject.toml` -- Python workspace config (uv), ruff, mypy, pytest settings
- `pnpm-workspace.yaml` -- Node.js workspace for frontend + ts-common
- `turbo.json` -- Turborepo for frontend build caching
- `skaffold.yaml` -- Kubernetes dev loop (build, deploy, watch, port-forward)
- `.pre-commit-config.yaml` -- Code quality hooks (ruff, mypy, eslint, prettier)
- `.editorconfig` -- Consistent formatting across editors

### Step 5: Start the DevContainer
```bash
# Option A: VS Code
# Open the project folder, click "Reopen in Container" when prompted

# Option B: CLI
docker compose -f .devcontainer/docker-compose.yml up -d
```

### Step 6: Verify Infrastructure
```bash
# Postgres with pgvector
PGPASSWORD=agent_platform psql -h localhost -U agent_platform -d agent_platform \
  -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"

# Redis with RediSearch
redis-cli -h localhost PING
redis-cli -h localhost MODULE LIST  # Should show 'search' module

# MinIO
curl -sf http://localhost:9000/minio/health/live && echo "MinIO OK"

# MinIO Console: http://localhost:9001 (minioadmin/minioadmin)
```

### Step 7: Verify the CLAUDE.md Hierarchy
Read the root `CLAUDE.md` -- this is what Claude Code reads every time you start a
conversation in this project. It tells Claude the project structure, conventions,
and available commands. As we build each phase, we'll add service-level CLAUDE.md
files that provide deeper context for each service.

## Verification Checklist
- [ ] Git repo initialized
- [ ] Docker Compose starts without errors
- [ ] Postgres accepts connections and has pgvector extension
- [ ] Redis responds to PING and has RediSearch module
- [ ] MinIO health check passes
- [ ] `make help` shows all available commands

## Key Concepts Taught
1. **DevContainers** -- Declarative, reproducible dev environments in Docker
2. **12-Factor App** -- Config via environment variables, not files (see .devcontainer/devcontainer.json remoteEnv)
3. **Monorepo** -- Single repo for all services, shared libs, infra code
4. **Infrastructure as Code** -- Even local dev infra is declared in docker-compose.yml
5. **Pre-commit hooks** -- Shift-left quality: catch issues before they reach CI

## What's Next
Phase 1 (`/01-scaffold-api`) builds the FastAPI + GraphQL gateway service, the
single entry point for all client requests. You'll learn schema-first API design
and the app factory pattern.

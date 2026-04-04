.PHONY: help dev test lint build deploy-local e2e clean

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ──────────────────────────────────────────────
# Development
# ──────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start DevContainer + local infra (PG, Redis, MinIO)
	docker compose -f .devcontainer/docker-compose.yml up -d

dev-down: ## Stop local infra
	docker compose -f .devcontainer/docker-compose.yml down

# ──────────────────────────────────────────────
# Quality
# ──────────────────────────────────────────────

lint: ## Run all linters (ruff, mypy, eslint)
	uv run ruff check services/ libs/py-common/
	uv run ruff format --check services/ libs/py-common/
	uv run mypy services/ libs/py-common/ --strict --ignore-missing-imports
	cd frontend && pnpm lint

fmt: ## Auto-format all code
	uv run ruff check --fix services/ libs/py-common/
	uv run ruff format services/ libs/py-common/
	cd frontend && pnpm format

# ──────────────────────────────────────────────
# Testing
# ──────────────────────────────────────────────

test: ## Run all unit tests
	uv run pytest services/*/tests/unit/ libs/py-common/tests/ -v --tb=short
	cd frontend && pnpm test

test-integration: ## Run integration tests (requires local infra)
	uv run pytest services/*/tests/integration/ tests/integration/ -v --tb=short

test-e2e: ## Run end-to-end tests
	uv run pytest tests/e2e/ -v --tb=short
	cd frontend && pnpm test:e2e

test-load: ## Run load tests with Locust
	uv run locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s

test-all: test test-integration test-e2e ## Run all test suites

# ──────────────────────────────────────────────
# Build
# ──────────────────────────────────────────────

build: ## Build all container images
	@for svc in gateway agent-engine document-service cache-service cost-tracker; do \
		echo "Building services/$$svc..."; \
		docker build -t agent-platform-$$svc:latest services/$$svc/; \
	done
	docker build -t agent-platform-frontend:latest frontend/

# ──────────────────────────────────────────────
# Deploy
# ──────────────────────────────────────────────

deploy-local: ## Deploy to local K8s cluster via Skaffold
	skaffold dev --port-forward

deploy-dev: ## Deploy to dev overlay via Kustomize
	kubectl apply -k infra/k8s/overlays/dev/

# ──────────────────────────────────────────────
# Codegen
# ──────────────────────────────────────────────

graphql-codegen: ## Generate GraphQL client types
	./scripts/generate-graphql.sh

# ──────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────

bootstrap: ## One-command project setup
	./scripts/bootstrap.sh

seed: ## Load seed data into PG/MinIO
	./scripts/seed-data.sh

port-forward: ## Forward all K8s services to localhost
	./scripts/port-forward.sh

clean: ## Remove build artifacts, caches, temp files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .next -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true

#!/bin/bash
# ============================================================================
# Bootstrap: One-command project setup
# Usage: ./scripts/bootstrap.sh
# ============================================================================
set -euo pipefail

echo "=========================================="
echo "  Agent Platform -- Bootstrap"
echo "=========================================="

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "ERROR: docker is required"; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is required"; exit 1; }

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "==> Initializing git repository..."
    git init
    git add -A
    git commit -m "Initial commit: Phase 0 scaffold"
fi

# Install pre-commit hooks
if command -v pre-commit >/dev/null 2>&1; then
    echo "==> Installing pre-commit hooks..."
    pre-commit install
fi

# Start local infrastructure
echo "==> Starting local infrastructure (Postgres, Redis, MinIO)..."
docker compose -f .devcontainer/docker-compose.yml up -d postgres redis minio

# Wait for services
echo "==> Waiting for services to be healthy..."
until docker compose -f .devcontainer/docker-compose.yml exec -T postgres pg_isready -U agent_platform 2>/dev/null; do
    sleep 1
done
echo "  Postgres: OK"

until docker compose -f .devcontainer/docker-compose.yml exec -T redis redis-cli ping 2>/dev/null | grep -q PONG; do
    sleep 1
done
echo "  Redis: OK"

until curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; do
    sleep 1
done
echo "  MinIO: OK"

# Initialize Postgres extensions
echo "==> Initializing pgvector extension..."
PGPASSWORD=agent_platform psql -h localhost -U agent_platform -d agent_platform \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

# Install Python dependencies
if command -v uv >/dev/null 2>&1; then
    echo "==> Installing Python dependencies..."
    uv sync --all-packages 2>/dev/null || echo "  (No packages to install yet -- run after Phase 1)"
fi

# Install Node.js dependencies
if command -v pnpm >/dev/null 2>&1; then
    echo "==> Installing Node.js dependencies..."
    pnpm install 2>/dev/null || echo "  (No packages to install yet -- run after Phase 2)"
fi

echo ""
echo "=========================================="
echo "  Bootstrap complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  make help              -- Show all commands"
echo "  make dev               -- Start full dev stack"
echo "  claude /00-setup-env   -- Start the tutorial"
echo ""

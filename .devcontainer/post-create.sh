#!/bin/bash
# ============================================================================
# Post-create setup script for DevContainer
# Runs once after the container is created
# ============================================================================
set -euo pipefail

echo "==> Installing Python dependencies (uv)..."
cd /workspace
uv sync --all-packages 2>/dev/null || echo "No uv workspace lock yet -- run 'uv sync' after Phase 1"

echo "==> Installing Node.js dependencies (pnpm)..."
pnpm install 2>/dev/null || echo "No pnpm workspace yet -- run 'pnpm install' after Phase 2"

echo "==> Setting up pre-commit hooks..."
pre-commit install 2>/dev/null || echo "pre-commit not configured yet"

echo "==> Creating MinIO buckets..."
until curl -sf http://minio:9000/minio/health/live; do sleep 1; done
mc alias set local http://minio:9000 minioadmin minioadmin 2>/dev/null || true
mc mb local/documents --ignore-existing 2>/dev/null || true
mc mb local/models --ignore-existing 2>/dev/null || true
mc mb local/artifacts --ignore-existing 2>/dev/null || true

echo "==> Initializing PostgreSQL extensions..."
PGPASSWORD=agent_platform psql -h postgres -U agent_platform -d agent_platform -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true

echo "==> DevContainer setup complete!"
echo ""
echo "Quick start:"
echo "  make help          -- Show all available commands"
echo "  make dev           -- Start local infra"
echo "  make test          -- Run all unit tests"
echo "  skaffold dev       -- Full K8s dev loop"
echo ""
echo "Tutorial commands (Claude Code):"
echo "  /00-setup-env      -- Phase 0: Environment setup"
echo "  /01-scaffold-api   -- Phase 1: API layer"
echo "  /02-scaffold-frontend  -- Phase 2: Frontend"

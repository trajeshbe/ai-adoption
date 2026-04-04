#!/bin/bash
# ============================================================================
# Generate GraphQL: Run codegen for TypeScript client types
# Usage: ./scripts/generate-graphql.sh
# ============================================================================
set -euo pipefail

echo "==> Generating GraphQL types from gateway schema..."

# Ensure gateway is running for introspection
if ! curl -sf http://localhost:8000/graphql >/dev/null 2>&1; then
    echo "ERROR: Gateway must be running at localhost:8000 for schema introspection."
    echo "Start it with: cd services/gateway && uv run uvicorn gateway.main:create_app --factory --port 8000"
    exit 1
fi

cd frontend
pnpm graphql-codegen

echo "==> GraphQL types generated in libs/ts-common/src/api-client.ts"

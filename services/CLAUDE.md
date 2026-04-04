# Services -- Backend Microservices

## Overview
Five Python microservices, each with its own pyproject.toml, Dockerfile, and tests.
All share `libs/py-common` for config, logging, telemetry, and error handling.

## Services
| Service           | Dev Port | K8s Port | Purpose                              |
|-------------------|----------|----------|--------------------------------------|
| gateway           | 8050     | 8000     | FastAPI + Strawberry GraphQL + /metrics + /k8s |
| agent-engine      | 8053     | 8003     | Prefect + LangGraph agent execution  |
| document-service  | 8051     | 8001     | Document ingestion + RAG retrieval   |
| cache-service     | 8052     | 8002     | Redis VSS semantic cache             |
| cost-tracker      | 8054     | 8004     | OpenCost aggregation + $/inference   |

## Conventions
- Every service uses FastAPI with the app factory pattern (`create_app()`)
- Every service exposes `/healthz` (liveness) and `/readyz` (readiness)
- Config via Pydantic Settings loading from environment variables
- Structured JSON logging via structlog
- OTEL auto-instrumentation via `setup_telemetry(service_name)`
- Tests in `tests/unit/` and `tests/integration/`
- Run with: `cd services/<name> && uv run uvicorn <name>.main:create_app --factory --port <port>`
- Test with: `cd services/<name> && uv run pytest tests/ -v`

# Gateway Service

## Purpose
GraphQL API gateway. Single entry point for all client requests. Delegates to
agent-engine, document-service, cache-service, cost-tracker via internal HTTP.

## Tech
FastAPI 0.115+, Strawberry GraphQL 0.230+, uvicorn, httpx (async HTTP client)

## Key Files
- `src/gateway/main.py` -- App factory, mounts GraphQL + REST health routes
- `src/gateway/schema.py` -- Root GraphQL schema (Query, Mutation, Subscription)
- `src/gateway/resolvers/` -- One file per domain (agent, chat, document, cost)
- `src/gateway/subscriptions/chat_stream.py` -- WebSocket streaming for chat
- `src/gateway/middleware/` -- Auth, rate limiting, telemetry
- `src/gateway/dependencies.py` -- FastAPI dependency injection

## Patterns
- Schema-first: define types in schema.py, implement in resolvers/
- All resolvers use dependency injection via dependencies.py
- Internal service calls use httpx.AsyncClient with circuit breaker
- Every resolver is traced via OTEL auto-instrumentation

## Run
`uv run uvicorn gateway.main:create_app --factory --reload --port 8000`

## Test
`uv run pytest tests/ -v`

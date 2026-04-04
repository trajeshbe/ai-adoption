# Gateway Service

## Purpose
GraphQL API gateway. Single entry point for all client requests. Delegates to
agent-engine, document-service, cache-service, cost-tracker via internal HTTP.
Also serves live metrics (/metrics) and Kubernetes cluster state (/k8s).

## Tech
FastAPI 0.115+, Strawberry GraphQL 0.230+, uvicorn, httpx (async HTTP client)

## Key Files
- `src/gateway/main.py` -- App factory, GraphQL + REST + /metrics + /k8s endpoints
- `src/gateway/schema.py` -- Root GraphQL schema (Query, Mutation, Subscription)
- `src/gateway/resolvers/` -- One file per domain (agent, chat, document, cost)
- `src/gateway/metrics.py` -- Thread-safe MetricsCollector (requests, latency, connections)
- `src/gateway/subscriptions/chat_stream.py` -- WebSocket streaming for chat
- `src/gateway/middleware/` -- Auth, rate limiting (60 req/min), MetricsMiddleware
- `src/gateway/health.py` -- /healthz and /readyz endpoints
- `src/gateway/dependencies.py` -- FastAPI dependency injection

## Endpoints
- `POST /graphql` -- Strawberry GraphQL (queries, mutations, subscriptions)
- `GET /healthz` -- Liveness check
- `GET /readyz` -- Readiness check
- `GET /metrics` -- Live traffic metrics + service health checks (6 services)
- `GET /k8s` -- Live Kubernetes cluster state (pods, HPAs, nodes via kubectl)
- `GET /docs` -- Swagger UI (debug mode only)

## Patterns
- Schema-first: define types in schema.py, implement in resolvers/
- MetricsMiddleware records request latency, status, active connections
- /metrics endpoint health-checks all 6 services (gateway, agent-engine,
  document-service, cache-service, cost-tracker, ollama)
- /k8s endpoint shells out to kubectl for live cluster data
- Rate limiter: 60 requests/minute (disabled in debug mode)
- CORS: allow_origins=["*"], allow_credentials=False
- send_message mutation is async (awaits agent-engine HTTP call)

## Run
```bash
AGENT_ENGINE_URL=http://localhost:8053 \
  uv run uvicorn gateway.main:create_app --factory --host 0.0.0.0 --port 8050
```

## Test
`uv run pytest tests/ -v`

# ADR-002: GraphQL over REST for Frontend API

## Status: Accepted

## Date: 2026-04-04

## Context

The KIAA frontend presents composite views that aggregate heterogeneous data: agent
execution status alongside real-time chat streams alongside cost breakdowns and usage
analytics. A typical dashboard page requires data from 4 different backend services.
Under a traditional REST approach, the frontend would either make N sequential/parallel
requests (increasing latency and complexity) or we would build a Backend-for-Frontend
(BFF) layer that pre-aggregates responses -- adding another service to maintain.

Additionally, the chat interface requires streaming responses from LLM inference, which
demands a persistent connection model (WebSockets or SSE) regardless of the API paradigm.

## Decision

We adopt Strawberry GraphQL mounted on FastAPI as the unified API gateway. Strawberry is
chosen as the GraphQL framework because its code-first, type-annotation-driven approach
aligns with our existing Pydantic model ecosystem. The gateway resolves queries by
calling downstream services via async HTTP (httpx) and gRPC where latency is critical.

GraphQL subscriptions over WebSocket (graphql-ws protocol) handle real-time chat token
streaming and agent execution status updates.

## Consequences

**Positive:**
- The frontend fetches exactly the fields it needs in a single round-trip, eliminating
  over-fetching and under-fetching. This is particularly impactful for mobile clients
  where bandwidth is constrained.
- Subscriptions provide a unified real-time mechanism for chat streaming and live
  dashboard updates without maintaining separate WebSocket infrastructure.
- Strawberry's code-first schema generation from Python type annotations means our
  GraphQL types stay synchronized with Pydantic models automatically, reducing drift.
- Schema introspection enables powerful developer tooling: auto-generated TypeScript
  types for the frontend via graphql-codegen, interactive schema explorer via GraphiQL.

**Negative:**
- GraphQL introduces complexity in caching -- HTTP-level caching (CDN, reverse proxy)
  is less effective because all queries hit a single POST endpoint. We mitigate this
  with persisted queries and response-level caching in Redis.
- N+1 query problems require explicit use of DataLoaders for batching downstream
  service calls. Every resolver that fetches related entities must use a DataLoader.
- Error handling semantics differ from REST -- partial responses are valid in GraphQL,
  which requires frontend code to handle mixed success/error states per field.
- Query complexity analysis and depth limiting are required to prevent abusive queries
  from overwhelming downstream services.

## Alternatives Considered

- **REST with BFF pattern:** Would solve the aggregation problem but introduces a
  dedicated BFF service that duplicates routing logic and must be updated whenever
  downstream APIs change. Does not natively solve real-time streaming.
- **gRPC-web:** Excellent performance and strong typing, but browser support requires
  a proxy (Envoy), and the protobuf ecosystem is less ergonomic for rapid frontend
  iteration compared to GraphQL's self-documenting schema.
- **tRPC:** Strong TypeScript-native option, but our backend is Python-based. tRPC
  assumes a TypeScript server, making it architecturally incompatible without a
  dedicated Node.js gateway layer.

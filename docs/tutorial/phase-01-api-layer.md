# Phase 1: API Layer

## Summary

Build the backend API using FastAPI with a Strawberry GraphQL schema. This phase creates the core query and mutation endpoints that the frontend and agent engine will consume, including health checks, authentication stubs, and WebSocket subscriptions for streaming responses.

## Learning Objectives

- Scaffold a FastAPI application with async route handlers
- Define a Strawberry GraphQL schema with types, queries, and mutations
- Implement WebSocket subscriptions for real-time chat streaming
- Write integration tests using httpx and pytest-asyncio

## Key Commands

```bash
# Start the API server in development mode
uvicorn app.main:app --reload --port 8000

# Open the GraphQL playground
open http://localhost:8000/graphql

# Run API tests
pytest tests/api/ -v
```

## Slash Command

Run `/01-api-layer` in Claude Code to begin this phase.

## Next Phase

[Phase 2: Frontend](phase-02-frontend.md)

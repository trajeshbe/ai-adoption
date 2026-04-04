# Phase 1: API Layer -- Build a FastAPI + GraphQL Gateway from Scratch

## What You Will Learn
- Schema-first API design with Strawberry GraphQL
- FastAPI app factory pattern for testability
- Dependency injection for clean service composition
- Shared library patterns for configuration and logging
- Unit testing GraphQL resolvers

## Prerequisites
- Phase 0 complete (DevContainer running, Postgres/Redis/MinIO up)
- Familiarity with Python type hints and async/await

## Background: Why GraphQL + FastAPI?
REST works for simple CRUD, but our frontend needs to fetch heterogeneous data in
single views (agent config + chat history + cost metrics). GraphQL lets the client
request exactly what it needs in one query. FastAPI gives us automatic OpenAPI docs,
Pydantic validation, and async support. Strawberry is chosen because it's code-first
with Python type hints -- it feels native to the FastAPI/Pydantic ecosystem.

See: docs/architecture/adr/002-graphql-over-rest.md

## Step-by-Step Instructions

### Step 1: Create the Shared Python Library (libs/py-common)

Create `libs/py-common/pyproject.toml`:
```toml
[project]
name = "agent-platform-common"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.8",
  "pydantic-settings>=2.4",
  "structlog>=24.0",
  "opentelemetry-api>=1.25",
  "opentelemetry-sdk>=1.25",
  "opentelemetry-exporter-otlp>=1.25",
  "opentelemetry-instrumentation-fastapi>=0.46b0",
]
```

**Why a shared library?** Every service needs config loading, structured logging,
and telemetry. Without a shared library, each service duplicates this boilerplate.
DRY principle at the monorepo level.

Create these files in `libs/py-common/src/agent_platform_common/`:
1. `config.py` -- Pydantic Settings class loading from env vars (DATABASE_URL, REDIS_URL, etc.)
2. `logging.py` -- structlog configuration with JSON output for machine parsing
3. `telemetry.py` -- OpenTelemetry TracerProvider, MeterProvider, LoggerProvider bootstrap
4. `errors.py` -- Structured error hierarchy (AgentPlatformError -> NotFoundError, ValidationError, etc.)
5. `types.py` -- Shared Pydantic models (AgentType enum, MessageRole enum, etc.)

### Step 2: Create the Gateway Service

Create `services/gateway/pyproject.toml`:
```toml
[project]
name = "agent-platform-gateway"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "strawberry-graphql[fastapi]>=0.230",
  "uvicorn[standard]>=0.30",
  "httpx>=0.27",
  "agent-platform-common",
]
```

### Step 3: Define the GraphQL Schema (schema-first)

Create `services/gateway/src/gateway/schema.py` with these types:

```python
import strawberry
from datetime import datetime
from enum import Enum

@strawberry.enum
class AgentType(Enum):
    WEATHER = "weather"
    QUIZ = "quiz"
    RAG = "rag"
    CUSTOM = "custom"

@strawberry.type
class Agent:
    id: str
    name: str
    agent_type: AgentType
    instructions: str
    created_at: datetime

@strawberry.type
class ChatMessage:
    id: str
    role: str  # "user" | "assistant" | "system"
    content: str
    tool_calls: list[str] | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None
    created_at: datetime

@strawberry.type
class ChatSession:
    id: str
    agent_id: str
    messages: list[ChatMessage]
    created_at: datetime

@strawberry.type
class Document:
    id: str
    filename: str
    content_type: str
    chunk_count: int
    created_at: datetime

@strawberry.type
class InferenceCost:
    total_cost_usd: float
    prompt_tokens: int
    completion_tokens: int
    model: str
```

**Principle:** Define your data types BEFORE implementing resolvers. This is the
contract between frontend and backend. The frontend team can start building against
these types immediately.

### Step 4: Implement Stub Resolvers

Create resolver files in `services/gateway/src/gateway/resolvers/`:
- `agent.py` -- Query: agents, agent(id). Mutation: createAgent, deleteAgent
- `chat.py` -- Query: chatSessions, chatSession(id). Mutation: sendMessage
- `document.py` -- Query: documents. Mutation: uploadDocument
- `cost.py` -- Query: inferenceCosts, totalCost

Each resolver returns **mock data** for now. The real backends (agent-engine,
document-service, etc.) will be wired in later phases.

### Step 5: Create the FastAPI App Factory

Create `services/gateway/src/gateway/main.py`:
```python
from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

def create_app() -> FastAPI:
    app = FastAPI(title="Agent Platform Gateway", version="0.1.0")
    # Mount GraphQL
    schema = strawberry.Schema(query=Query, mutation=Mutation)
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")
    # Health endpoints
    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}
    @app.get("/readyz")
    async def readyz():
        return {"status": "ready"}
    return app
```

**Why app factory?** It allows creating fresh app instances in tests without
module-level side effects. FastAPI's dependency injection + app factory = testable services.

### Step 6: Add Middleware

Create middleware in `services/gateway/src/gateway/middleware/`:
- `telemetry.py` -- Adds trace ID to every request, records request duration
- `auth.py` -- JWT validation (stub for now, real implementation in later phase)
- `rate_limit.py` -- In-memory rate limiter (Redis-backed in Phase 3)

### Step 7: Create the Dockerfile

Create `services/gateway/Dockerfile`:
```dockerfile
FROM python:3.11-slim AS base
WORKDIR /app
RUN pip install --no-cache-dir uv

FROM base AS deps
COPY libs/py-common/pyproject.toml /libs/py-common/pyproject.toml
COPY services/gateway/pyproject.toml .
RUN uv pip install --system -r pyproject.toml

FROM deps AS runtime
COPY libs/py-common/src /libs/py-common/src
COPY services/gateway/src ./src
EXPOSE 8000
CMD ["uvicorn", "gateway.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 8: Write Unit Tests

Create `services/gateway/tests/unit/test_resolvers.py`:
```python
import strawberry
from strawberry.test.client import GraphQLTestClient

def test_list_agents(test_client):
    result = test_client.query("{ agents { id name agentType } }")
    assert result.errors is None
    assert len(result.data["agents"]) > 0

def test_create_agent(test_client):
    result = test_client.query('''
        mutation {
            createAgent(name: "Weather Bot", agentType: WEATHER, instructions: "...") {
                id name agentType
            }
        }
    ''')
    assert result.errors is None
    assert result.data["createAgent"]["name"] == "Weather Bot"
```

### Step 9: Create the Service CLAUDE.md

Create `services/gateway/CLAUDE.md` with service-specific context: purpose, tech stack,
key files, patterns, run/test commands.

## Verification
```bash
# Start the gateway
cd services/gateway && uv run uvicorn gateway.main:create_app --factory --port 8000

# Open GraphQL Playground at http://localhost:8000/graphql
# Run a test query:
# { agents { id name agentType createdAt } }

# Run tests
cd services/gateway && uv run pytest tests/ -v
```

## Key Concepts Taught
1. **Schema-first design** -- Define data contracts before implementation
2. **App factory pattern** -- Testable FastAPI applications
3. **Dependency injection** -- FastAPI's Depends() for clean composition
4. **Shared libraries** -- DRY across microservices via monorepo packages
5. **Structured logging** -- JSON logs for machine parsing (Loki in Phase 6)
6. **Health endpoints** -- /healthz (liveness) vs /readyz (readiness) for Kubernetes

## What's Next
Phase 2 (`/02-scaffold-frontend`) builds the Next.js frontend that consumes this
GraphQL API. You'll learn App Router, server components, and real-time chat via
GraphQL subscriptions.

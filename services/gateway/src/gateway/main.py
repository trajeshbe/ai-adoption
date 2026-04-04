"""FastAPI application factory.

The app factory pattern creates a fresh app instance per call, enabling:
- Clean test isolation (each test gets its own app)
- No module-level side effects
- Configuration injection at creation time
"""

from typing import AsyncGenerator
from uuid import UUID

import strawberry
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from agent_platform_common.config import Settings
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware

from gateway.health import router as health_router
from gateway.middleware.auth import AuthMiddleware
from gateway.middleware.rate_limit import RateLimitMiddleware
from gateway.resolvers.agent import (
    resolve_agent,
    resolve_agents,
    resolve_create_agent,
    resolve_delete_agent,
)
from gateway.resolvers.chat import (
    resolve_chat_session,
    resolve_chat_sessions,
    resolve_send_message,
)
from gateway.resolvers.cost import resolve_cost_summary, resolve_inference_costs
from gateway.resolvers.document import (
    resolve_document,
    resolve_documents,
    resolve_upload_document,
)
from gateway.schema import (
    Agent,
    ChatMessage,
    ChatSession,
    CostSummary,
    CreateAgentInput,
    Document,
    InferenceCost,
    SendMessageInput,
)
from gateway.subscriptions.chat_stream import ChatToken, subscribe_chat_stream


# ── GraphQL Schema Assembly ───────────────────────────────────────────


@strawberry.type
class Query:
    """Root GraphQL query type."""

    @strawberry.field
    def agents(self) -> list[Agent]:
        """List all configured agents."""
        return resolve_agents()

    @strawberry.field
    def agent(self, agent_id: UUID) -> Agent | None:
        """Get a single agent by ID."""
        return resolve_agent(agent_id)

    @strawberry.field
    def chat_sessions(self) -> list[ChatSession]:
        """List all chat sessions."""
        return resolve_chat_sessions()

    @strawberry.field
    def chat_session(self, session_id: UUID) -> ChatSession | None:
        """Get a single chat session with messages."""
        return resolve_chat_session(session_id)

    @strawberry.field
    def documents(self) -> list[Document]:
        """List all uploaded documents."""
        return resolve_documents()

    @strawberry.field
    def document(self, document_id: UUID) -> Document | None:
        """Get a single document by ID."""
        return resolve_document(document_id)

    @strawberry.field
    def inference_costs(self, limit: int = 10) -> list[InferenceCost]:
        """Get recent inference cost records."""
        return resolve_inference_costs(limit)

    @strawberry.field
    def cost_summary(self, period: str = "24h") -> CostSummary:
        """Get aggregated cost summary for a time period."""
        return resolve_cost_summary(period)


@strawberry.type
class Mutation:
    """Root GraphQL mutation type."""

    @strawberry.mutation
    def create_agent(self, input: CreateAgentInput) -> Agent:
        """Create a new AI agent."""
        return resolve_create_agent(input)

    @strawberry.mutation
    def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent by ID."""
        return resolve_delete_agent(agent_id)

    @strawberry.mutation
    def send_message(self, input: SendMessageInput) -> ChatMessage:
        """Send a message to an agent and get a response."""
        return resolve_send_message(input)

    @strawberry.mutation
    def upload_document(self, filename: str, content_type: str) -> Document:
        """Upload a document for RAG processing."""
        return resolve_upload_document(filename, content_type)


@strawberry.type
class Subscription:
    """Root GraphQL subscription type."""

    @strawberry.subscription
    async def chat_stream(
        self, session_id: UUID
    ) -> AsyncGenerator[ChatToken, None]:
        """Stream chat response tokens in real-time."""
        async for token in subscribe_chat_stream(session_id):
            yield token


# ── App Factory ────────────────────────────────────────────────────────


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing).
    """
    if settings is None:
        settings = Settings(service_name="gateway")

    # ── Logging ────────────────────────────────────────────────────────
    setup_logging(
        service_name=settings.service_name,
        log_level=settings.log_level,
        debug=settings.debug,
    )

    # ── Telemetry (OTEL) ───────────────────────────────────────────────
    # Deferred to Phase 6 -- uncomment when OTEL Collector is deployed
    # setup_telemetry(settings.service_name, settings.otel_exporter_otlp_endpoint)

    # ── FastAPI App ────────────────────────────────────────────────────
    app = FastAPI(
        title="Agent Platform Gateway",
        description="GraphQL API gateway for the AI Agent Platform",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
    )

    # ── Middleware (order matters: outermost first) ─────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=60,
        enabled=not settings.debug,
    )
    app.add_middleware(
        AuthMiddleware,
        jwt_secret=settings.jwt_secret,
        enforce=False,  # Set True in production
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── GraphQL ────────────────────────────────────────────────────────
    schema = strawberry.Schema(
        query=Query,
        mutation=Mutation,
        subscription=Subscription,
    )
    graphql_router = GraphQLRouter(schema, path="/graphql")
    app.include_router(graphql_router)

    # ── REST Health Endpoints ──────────────────────────────────────────
    app.include_router(health_router)

    return app

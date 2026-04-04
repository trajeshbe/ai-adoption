"""FastAPI application factory for the agent-engine service.

The app factory pattern creates a fresh app instance per call, enabling:
- Clean test isolation (each test gets its own app)
- No module-level side effects
- Configuration injection at creation time
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from agent_platform_common.config import Settings
from agent_platform_common.errors import AgentPlatformError, NotFoundError
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware

from agent_engine.llm_client import LLMClient
from agent_engine.registry import AgentRegistry  # noqa: F401 (triggers auto-register)

logger = structlog.get_logger()


# ── Request / Response Schemas ────────────────────────────────────────


class ExecuteRequest(BaseModel):
    """POST body for /agents/execute."""

    agent_type: str
    message: str = Field(..., min_length=1, max_length=50000)
    history: list[dict[str, Any]] = Field(default_factory=list)
    session_id: str | None = None


class ToolCallOut(BaseModel):
    """Serialised tool call in the response."""

    tool_name: str
    arguments: str
    result: str


class ExecuteResponse(BaseModel):
    """Response from /agents/execute."""

    content: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


# ── App Factory ───────────────────────────────────────────────────────


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing).
    """
    if settings is None:
        settings = Settings(service_name="agent-engine")

    # ── Logging ────────────────────────────────────────────────────────
    setup_logging(
        service_name=settings.service_name,
        log_level=settings.log_level,
        debug=settings.debug,
    )

    # ── Telemetry (OTEL) ───────────────────────────────────────────────
    # Deferred to Phase 6 -- uncomment when OTEL Collector is deployed
    # from agent_platform_common.telemetry import setup_telemetry
    # setup_telemetry(settings.service_name, settings.otel_exporter_otlp_endpoint)

    # ── Lifespan ───────────────────────────────────────────────────────

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        app.state.settings = settings
        app.state.llm_client = LLMClient(
            primary_url=settings.llm_primary_url,
            fallback_url=settings.llm_fallback_url,
            model=settings.llm_model,
        )
        app.state.http_client = httpx.AsyncClient(
            base_url=settings.document_service_url,
            timeout=30.0,
        )
        await logger.ainfo("agent_engine_started", llm_model=settings.llm_model)
        yield
        # Shutdown
        await app.state.llm_client.close()
        await app.state.http_client.aclose()
        await logger.ainfo("agent_engine_stopped")

    # ── FastAPI App ────────────────────────────────────────────────────
    app = FastAPI(
        title="Agent Engine",
        description="AI agent orchestration via Prefect + LangGraph",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
    )

    # ── Middleware (order matters: outermost first) ─────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # ── Health Endpoints ──────────────────────────────────────────────

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> dict[str, str]:
        return {"status": "ready"}

    # ── Agent Endpoints ───────────────────────────────────────────────

    @app.get("/agents/types")
    async def list_agent_types() -> dict[str, list[str]]:
        """Return all registered agent types."""
        return {"types": AgentRegistry.list_types()}

    @app.post("/agents/execute", response_model=ExecuteResponse)
    async def execute_agent(body: ExecuteRequest, request: Request) -> ExecuteResponse:
        """Execute an agent turn: send a message and get a response."""
        try:
            from agent_engine.flows.agent_flow import agent_flow

            response = await agent_flow(
                agent_type=body.agent_type,
                user_message=body.message,
                history=body.history,
                settings=request.app.state.settings,
            )

            return ExecuteResponse(
                content=response.content,
                tool_calls=[
                    ToolCallOut(
                        tool_name=tc.tool_name,
                        arguments=tc.arguments,
                        result=tc.result,
                    )
                    for tc in response.tool_calls
                ],
                model=response.model,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                latency_ms=response.latency_ms,
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc
        except AgentPlatformError as exc:
            raise HTTPException(status_code=502, detail=exc.message) from exc
        except Exception as exc:
            await logger.aexception("agent_execution_failed")
            raise HTTPException(
                status_code=500, detail=f"Agent execution failed: {exc}"
            ) from exc

    return app

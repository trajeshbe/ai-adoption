"""FastAPI application factory for the cost-tracker service.

The app factory pattern creates a fresh app instance per call, enabling:
- Clean test isolation (each test gets its own app)
- No module-level side effects
- Configuration injection at creation time
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
import structlog
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse

from agent_platform_common.config import Settings
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware

from cost_tracker.calculator import CostCalculator
from cost_tracker.collector import OpenCostCollector
from cost_tracker.models import CostBreakdown, CostSummary, InferenceCost, PodCost

logger = structlog.get_logger()


class CostTrackerSettings(Settings):
    """Cost-tracker specific settings."""

    opencost_url: str = "http://opencost.opencost:9003"
    prometheus_url: str = "http://prometheus:9090"


def create_app(settings: CostTrackerSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing).
    """
    if settings is None:
        settings = CostTrackerSettings(service_name="cost-tracker")

    # -- Logging ---------------------------------------------------------------
    setup_logging(
        service_name=settings.service_name,
        log_level=settings.log_level,
        debug=settings.debug,
    )

    # -- Telemetry (OTEL) ------------------------------------------------------
    # Deferred to Phase 6 -- uncomment when OTEL Collector is deployed
    # from agent_platform_common.telemetry import setup_telemetry
    # setup_telemetry(settings.service_name, settings.otel_exporter_otlp_endpoint)

    # -- Lifespan --------------------------------------------------------------
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage httpx client, collector, and calculator lifecycle."""
        http_client = httpx.AsyncClient(timeout=30.0)
        collector = OpenCostCollector(
            opencost_url=settings.opencost_url,
            http_client=http_client,
        )
        calculator = CostCalculator(
            collector=collector,
            prometheus_url=settings.prometheus_url,
            http_client=http_client,
        )

        app.state.http_client = http_client
        app.state.collector = collector
        app.state.calculator = calculator

        await logger.ainfo(
            "cost_tracker_started",
            opencost_url=settings.opencost_url,
            prometheus_url=settings.prometheus_url,
        )
        yield

        # Shutdown
        await http_client.aclose()
        await logger.ainfo("cost_tracker_stopped")

    # -- FastAPI App ------------------------------------------------------------
    app = FastAPI(
        title="Agent Platform Cost Tracker",
        description="OpenCost aggregation and $/inference tracking",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
    )

    # -- Middleware (order matters: outermost first) ----------------------------
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # -- Health Endpoints ------------------------------------------------------

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness probe -- returns healthy if the process is running."""
        return {"status": "healthy"}

    @app.get("/readyz")
    async def readyz(request: Request) -> JSONResponse:
        """Readiness probe -- checks OpenCost connectivity."""
        try:
            collector: OpenCostCollector = request.app.state.collector
            # A lightweight check: try to reach OpenCost
            response = await collector._client.get(
                f"{collector.opencost_url}/healthz",
            )
            if response.status_code < 500:
                return JSONResponse({"status": "ready"})
            return JSONResponse(
                {"status": "not_ready", "error": f"OpenCost returned {response.status_code}"},
                status_code=503,
            )
        except Exception as exc:
            return JSONResponse(
                {"status": "not_ready", "error": str(exc)},
                status_code=503,
            )

    # -- Cost Endpoints --------------------------------------------------------

    @app.get("/costs/pods", response_model=list[PodCost])
    async def get_pod_costs(
        request: Request,
        namespace: str = Query(default="agent-platform"),
        window: str = Query(default="1h"),
    ) -> list[PodCost]:
        """Get per-pod cost allocations from OpenCost."""
        collector: OpenCostCollector = request.app.state.collector
        return await collector.get_pod_costs(namespace=namespace, window=window)

    @app.get("/costs/inference", response_model=list[InferenceCost])
    async def get_inference_costs(
        request: Request,
        period: str = Query(default="24h"),
    ) -> list[InferenceCost]:
        """Get per-model $/inference cost breakdown."""
        calculator: CostCalculator = request.app.state.calculator
        return await calculator.calculate_inference_costs(period=period)

    @app.get("/costs/summary", response_model=CostSummary)
    async def get_cost_summary(
        request: Request,
        period: str = Query(default="24h"),
    ) -> CostSummary:
        """Get aggregated cost summary across all models."""
        calculator: CostCalculator = request.app.state.calculator
        return await calculator.get_summary(period=period)

    @app.get("/costs/breakdown", response_model=CostBreakdown)
    async def get_cost_breakdown(
        request: Request,
        namespace: str = Query(default="agent-platform"),
        window: str = Query(default="24h"),
    ) -> CostBreakdown:
        """Get cost breakdown by resource type."""
        collector: OpenCostCollector = request.app.state.collector
        return await collector.get_total_cost(namespace=namespace, window=window)

    return app

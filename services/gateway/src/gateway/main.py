"""FastAPI application factory.

The app factory pattern creates a fresh app instance per call, enabling:
- Clean test isolation (each test gets its own app)
- No module-level side effects
- Configuration injection at creation time
"""

from typing import AsyncGenerator
from uuid import UUID

import strawberry
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
from starlette.middleware.base import BaseHTTPMiddleware

from agent_platform_common.config import Settings
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware

from gateway.health import router as health_router
from gateway.metrics import metrics_collector
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


# ── Metrics Middleware ─────────────────────────────────────────────────


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware that records request metrics for every incoming request."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        import time as _time

        metrics_collector.increment_connections()
        start = _time.perf_counter()
        try:
            response = await call_next(request)
            latency_ms = (_time.perf_counter() - start) * 1000
            metrics_collector.record_request(
                path=request.url.path,
                status=response.status_code,
                latency_ms=round(latency_ms, 2),
            )
            return response
        except Exception:
            latency_ms = (_time.perf_counter() - start) * 1000
            metrics_collector.record_request(
                path=request.url.path,
                status=500,
                latency_ms=round(latency_ms, 2),
            )
            raise
        finally:
            metrics_collector.decrement_connections()


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
    async def send_message(self, input: SendMessageInput) -> ChatMessage:
        """Send a message to an agent and get a response."""
        return await resolve_send_message(input)

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
    app.add_middleware(MetricsMiddleware)
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
        allow_origins=["*"],
        allow_credentials=False,
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

    # ── Metrics Endpoint ──────────────────────────────────────────────
    @app.get("/metrics")
    async def metrics_endpoint() -> JSONResponse:
        """Return live system metrics and service health checks."""
        import time as _time

        import httpx

        service_checks = [
            {"name": "gateway", "url": "http://localhost:8050/healthz", "port": 8050},
            {"name": "agent-engine", "url": "http://localhost:8053/healthz", "port": 8053},
            {"name": "document-service", "url": "http://localhost:8051/healthz", "port": 8051},
            {"name": "cache-service", "url": "http://localhost:8052/healthz", "port": 8052},
            {"name": "cost-tracker", "url": "http://localhost:8054/healthz", "port": 8054},
            {"name": "ollama", "url": "http://localhost:20434/api/tags", "port": 20434},
        ]

        services = []
        async with httpx.AsyncClient(timeout=2.0) as client:
            for svc in service_checks:
                start = _time.perf_counter()
                try:
                    resp = await client.get(svc["url"])
                    elapsed = (_time.perf_counter() - start) * 1000
                    services.append({
                        "name": svc["name"],
                        "url": f":{svc['port']}",
                        "status": "healthy" if resp.status_code < 400 else "unhealthy",
                        "response_time_ms": round(elapsed, 1),
                        "uptime_seconds": round(metrics_collector.get_metrics()["uptime_seconds"], 1),
                    })
                except Exception:
                    elapsed = (_time.perf_counter() - start) * 1000
                    services.append({
                        "name": svc["name"],
                        "url": f":{svc['port']}",
                        "status": "unhealthy",
                        "response_time_ms": round(elapsed, 1),
                        "uptime_seconds": 0,
                    })

        current = metrics_collector.get_metrics()
        return JSONResponse({
            "services": services,
            "total_requests": current["total_requests"],
            "total_errors": current["total_errors"],
            "active_connections": current["active_connections"],
            "avg_latency_ms": current["avg_latency_ms"],
            "requests_per_second": current["requests_per_second"],
            "error_rate": current["error_rate"],
            "uptime_seconds": current["uptime_seconds"],
            "scaling_events": current["scaling_events"],
            "instance_distribution": current["instance_distribution"],
        })

    # ── K8s Cluster Endpoint ────────────────────────────────────────────
    @app.get("/k8s")
    async def k8s_endpoint() -> JSONResponse:
        """Return live Kubernetes cluster state: pods, HPA, node info."""
        import asyncio
        import json as _json

        async def run_kubectl(args: str) -> dict | list | None:
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"{_kubectl_path()} {args} -o json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
                if proc.returncode == 0:
                    return _json.loads(stdout)
            except Exception:
                pass
            return None

        pods_data = await run_kubectl("get pods -n agent-platform")
        hpa_data = await run_kubectl("get hpa -n agent-platform")
        nodes_data = await run_kubectl("get nodes")

        pods = []
        if pods_data and "items" in pods_data:
            for p in pods_data["items"]:
                cs = p.get("status", {}).get("containerStatuses", [{}])
                pods.append({
                    "name": p["metadata"]["name"],
                    "app": p["metadata"].get("labels", {}).get("app", ""),
                    "status": p["status"]["phase"],
                    "ready": all(c.get("ready", False) for c in cs),
                    "restarts": sum(c.get("restartCount", 0) for c in cs),
                    "ip": p["status"].get("podIP", ""),
                    "node": p["spec"].get("nodeName", ""),
                    "age_seconds": 0,
                })

        hpas = []
        if hpa_data and "items" in hpa_data:
            for h in hpa_data["items"]:
                spec = h.get("spec", {})
                status = h.get("status", {})
                current_metrics = status.get("currentMetrics", [])
                cpu_pct = None
                for m in current_metrics:
                    if m.get("resource", {}).get("name") == "cpu":
                        cpu_pct = m["resource"].get("current", {}).get("averageUtilization")
                hpas.append({
                    "name": h["metadata"]["name"],
                    "min_replicas": spec.get("minReplicas", 1),
                    "max_replicas": spec.get("maxReplicas", 1),
                    "current_replicas": status.get("currentReplicas", 0),
                    "desired_replicas": status.get("desiredReplicas", 0),
                    "cpu_utilization": cpu_pct,
                })

        nodes = []
        if nodes_data and "items" in nodes_data:
            for n in nodes_data["items"]:
                cap = n.get("status", {}).get("capacity", {})
                alloc = n.get("status", {}).get("allocatable", {})
                nodes.append({
                    "name": n["metadata"]["name"],
                    "status": "Ready" if any(
                        c["type"] == "Ready" and c["status"] == "True"
                        for c in n.get("status", {}).get("conditions", [])
                    ) else "NotReady",
                    "cpu_capacity": cap.get("cpu", "0"),
                    "memory_capacity": cap.get("memory", "0"),
                    "cpu_allocatable": alloc.get("cpu", "0"),
                    "memory_allocatable": alloc.get("memory", "0"),
                })

        return JSONResponse({
            "cluster": "aiadopt (minikube)",
            "pods": pods,
            "hpas": hpas,
            "nodes": nodes,
        })

    return app


def _kubectl_path() -> str:
    """Find kubectl binary."""
    import os
    for p in [os.path.expanduser("~/.local/bin/kubectl"), "/usr/local/bin/kubectl", "kubectl"]:
        if os.path.isfile(p):
            return p
    return "kubectl"

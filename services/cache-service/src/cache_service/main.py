"""FastAPI application factory for the cache service.

The app factory pattern creates a fresh app instance per call, enabling:
- Clean test isolation (each test gets its own app)
- No module-level side effects
- Configuration injection at creation time
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis

from agent_platform_common.config import Settings
from agent_platform_common.logging import setup_logging
from agent_platform_common.middleware import RequestIdMiddleware, RequestLoggingMiddleware

from cache_service.embeddings import EmbeddingClient
from cache_service.models import CacheHit, CacheStats
from cache_service.semantic_cache import SemanticCache

logger = structlog.get_logger()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (useful for testing).
    """
    if settings is None:
        settings = Settings(service_name="cache-service")

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
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage Redis client, embedding client, and semantic cache lifecycle."""
        redis_client = Redis.from_url(
            settings.redis_url,
            decode_responses=False,  # We need raw bytes for vectors
        )
        embedding_client = EmbeddingClient()
        semantic_cache = SemanticCache(
            redis_client=redis_client,
            embedding_client=embedding_client,
        )

        # Create the RediSearch index if it doesn't exist
        try:
            await semantic_cache.ensure_index()
        except Exception as exc:
            await logger.awarning(
                "failed_to_create_index_will_retry_on_first_request",
                error=str(exc),
            )

        app.state.redis = redis_client
        app.state.embedding_client = embedding_client
        app.state.semantic_cache = semantic_cache

        await logger.ainfo("cache_service_started", redis_url=settings.redis_url)
        yield

        # Shutdown
        await embedding_client.close()
        await redis_client.aclose()
        await logger.ainfo("cache_service_stopped")

    # ── FastAPI App ────────────────────────────────────────────────────
    app = FastAPI(
        title="Agent Platform Cache Service",
        description="Redis VSS semantic cache for LLM responses",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
    )

    # ── Middleware (order matters: outermost first) ─────────────────────
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    # ── Health Endpoints ───────────────────────────────────────────────

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Liveness probe -- returns healthy if the process is running."""
        return {"status": "healthy"}

    @app.get("/readyz")
    async def readyz(request: Request) -> JSONResponse:
        """Readiness probe -- checks Redis connectivity."""
        try:
            redis: Redis = request.app.state.redis
            await redis.ping()
            return JSONResponse({"status": "ready"})
        except Exception as exc:
            return JSONResponse(
                {"status": "not_ready", "error": str(exc)},
                status_code=503,
            )

    # ── Cache Endpoints ────────────────────────────────────────────────

    @app.post("/cache/lookup")
    async def cache_lookup(request: Request) -> JSONResponse:
        """Look up a semantically similar cached LLM response.

        Request body: {"query": "user question text"}
        Returns: CacheHit if found, or {"hit": false}
        """
        body = await request.json()
        query = body.get("query", "")
        if not query:
            return JSONResponse(
                {"error": "query is required"}, status_code=400
            )

        cache: SemanticCache = request.app.state.semantic_cache
        hit: CacheHit | None = await cache.get(query)

        if hit is not None:
            return JSONResponse({"hit": True, **hit.model_dump(mode="json")})
        return JSONResponse({"hit": False})

    @app.post("/cache/store")
    async def cache_store(request: Request) -> JSONResponse:
        """Store an LLM response in the semantic cache.

        Request body: {"query": str, "response": str, "model": str, "ttl": int?}
        """
        body = await request.json()
        query = body.get("query", "")
        response = body.get("response", "")
        model = body.get("model", "")
        ttl = body.get("ttl")

        if not query or not response or not model:
            return JSONResponse(
                {"error": "query, response, and model are required"},
                status_code=400,
            )

        cache: SemanticCache = request.app.state.semantic_cache
        key = await cache.put(
            query=query,
            response=response,
            model=model,
            ttl=ttl,
        )

        return JSONResponse({"stored": True, "key": key})

    @app.delete("/cache/invalidate")
    async def cache_invalidate(request: Request) -> JSONResponse:
        """Invalidate (delete) cached entries.

        Query param: ?pattern=* (glob pattern, defaults to all)
        """
        pattern = request.query_params.get("pattern", "*")
        cache: SemanticCache = request.app.state.semantic_cache
        deleted = await cache.invalidate(pattern=pattern)

        return JSONResponse({"invalidated": True, "deleted": deleted})

    @app.get("/cache/stats")
    async def cache_stats(request: Request) -> JSONResponse:
        """Return cache index statistics."""
        cache: SemanticCache = request.app.state.semantic_cache
        stats: CacheStats = await cache.stats()
        return JSONResponse(stats.model_dump(mode="json"))

    return app

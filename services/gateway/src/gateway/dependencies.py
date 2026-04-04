"""FastAPI dependency injection.

Central place for all injectable dependencies. Services, clients, and
configuration are injected here, making resolvers testable by overriding deps.
"""

from functools import lru_cache

import httpx

from agent_platform_common.config import Settings


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment variables (cached)."""
    return Settings(service_name="gateway")


async def get_http_client() -> httpx.AsyncClient:
    """Get an async HTTP client for internal service calls.

    In production, this would include:
    - Circuit breaker configuration
    - Retry policies
    - Timeout settings
    - mTLS certificates (handled by Istio mesh)
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        follow_redirects=True,
    )

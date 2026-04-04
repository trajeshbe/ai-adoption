"""In-memory rate limiting middleware.

Simple token bucket rate limiter for development. In production (Phase 3+),
replace with Redis-backed rate limiting for distributed enforcement.
"""

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token bucket rate limiter per client IP."""

    def __init__(
        self,
        app: object,
        requests_per_minute: int = 60,
        enabled: bool = True,
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.rpm = requests_per_minute
        self.enabled = enabled
        self._buckets: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self.enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60

        # Clean expired entries
        self._buckets[client_ip] = [
            t for t in self._buckets[client_ip] if t > window_start
        ]

        if len(self._buckets[client_ip]) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content={"error": f"Rate limit exceeded: {self.rpm} requests/minute"},
                headers={"Retry-After": "60"},
            )

        self._buckets[client_ip].append(now)
        return await call_next(request)

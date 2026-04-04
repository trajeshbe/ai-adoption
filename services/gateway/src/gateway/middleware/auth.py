"""Authentication middleware.

Validates JWT tokens on incoming requests. Skips auth for health endpoints
and GraphQL introspection. Stub implementation for development -- in production,
replace with OIDC provider integration.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

# Paths that don't require authentication
PUBLIC_PATHS = {"/healthz", "/readyz", "/docs", "/openapi.json"}


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT authentication middleware."""

    def __init__(self, app: object, jwt_secret: str, enforce: bool = False) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self.jwt_secret = jwt_secret
        self.enforce = enforce  # Set True in production

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip auth for public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # In development mode, skip auth enforcement
        if not self.enforce:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"error": "Missing or invalid Authorization header"},
            )

        token = auth_header.removeprefix("Bearer ")
        try:
            from agent_platform_common.auth import decode_token

            payload = decode_token(token, self.jwt_secret)
            request.state.user_id = payload.sub
            request.state.roles = payload.roles
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or expired token"},
            )

        return await call_next(request)
